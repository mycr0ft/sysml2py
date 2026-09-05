#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Expression evaluator binding pint attribute values (v0.64.0 — Goal 4).

Turns ``analyze()`` from "is this well-formed" into "does this model
evaluate": attribute defaults, ``calc`` result expressions and
``constraint`` bodies are evaluated with names resolved against the
model's own attribute values (pint ``Quantity``-aware), enabling
what-if evaluation and trade studies from Python.

Architecture: the evaluator works on the *raw parser dictionary* of the
model (``load_grammar(model.dump())``), which is complete and faithful
(the public-API object tree drops some body content, e.g. ``calc def``
bodies inside ``part def``).  A collector pass builds a namespace tree
(package → part → … → attribute values); an evaluator pass evaluates
expressions lazily with memoization and cycle detection.

Supported expression subset (SysML v2 textual):

- literals: integers, reals, strings, ``true``/``false``, ``null``, ``*``
  (infinity)
- units: ``1200 [kg]`` (value × pint unit)
- arithmetic: ``+ - * / % **`` (pint dimensionality enforced on
  Quantities)
- comparison: ``== != < <= > >=``
- boolean logic: ``and or not`` (short-circuit)
- references: feature names resolved through the ownership chain;
  dotted feature chains (``wheels.mass``) with type fallback
  (``part w : W`` resolves through ``W``'s values)

Not supported (raise :class:`UnsupportedExpressionError` with a clear
message): conditional (``? :``) expressions, sequences/collections,
metadata access, casts, string concatenation, calc ``in`` parameters.

Public surface:

- :func:`collect_values` — evaluate every attribute default in the model
- :func:`evaluate_expression` — evaluate a standalone expression against
  a model scope (optional ``bindings`` overrides for what-if runs)
- :func:`evaluate_calculation` — evaluate a named ``calc def`` result
- :func:`check_constraints` — evaluate every constraint body
- :class:`ConstraintReport` / :class:`ConstraintResult` — results

CLI: ``sysmlpy eval FILE [--expr EXPR] [--set NAME=VALUE ...]
[--constraints]`` (see ``cmd_eval`` in ``__main__.py``).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from sysmlpy.usage import ureg

__all__ = [
    "EvaluationError",
    "UnknownNameError",
    "UnsupportedExpressionError",
    "collect_values",
    "evaluate_expression",
    "evaluate_calculation",
    "check_constraints",
    "ConstraintResult",
    "ConstraintReport",
]


class EvaluationError(Exception):
    """An expression could not be evaluated."""


class UnknownNameError(EvaluationError):
    """A feature reference could not be resolved in scope."""


class UnsupportedExpressionError(EvaluationError):
    """An expression uses a construct outside the supported subset."""


# ---------------------------------------------------------------------------
# built-in functions (pint-aware)
# ---------------------------------------------------------------------------


def _sqrt(x):
    if isinstance(x, ureg.Quantity):
        return x ** 0.5
    return math.sqrt(x)


def _floor(x):
    if isinstance(x, ureg.Quantity):
        return math.floor(x.magnitude) * x.units
    return math.floor(x)


def _ceil(x):
    if isinstance(x, ureg.Quantity):
        return math.ceil(x.magnitude) * x.units
    return math.ceil(x)


_FUNCTIONS = {
    "sqrt": _sqrt,
    "abs": abs,
    "min": min,
    "max": max,
    "floor": _floor,
    "ceil": _ceil,
    "round": round,
    "pow": pow,
}


# ---------------------------------------------------------------------------
# namespace tree
# ---------------------------------------------------------------------------


class _Namespace:
    """A scope node in the collected namespace tree."""

    def __init__(self, name, qname=()):
        self.name = name
        self.qname = qname
        self.parent = None
        self.type_name = None
        self.values = {}    # attr/calc name -> ("expr", dict) / ("calc", dict)
        self.children = {}  # sub-namespace name -> _Namespace


_IN_PROGRESS = object()


# ---------------------------------------------------------------------------
# collection pass
# ---------------------------------------------------------------------------

_CONSTRAINT_TYPES = ("AssertConstraintUsage", "ConstraintUsage")
_CALC_TYPES = ("CalculationDefinition", "CalculationUsage", "FunctionDefinition")
_DEFINITION_CONTAINERS = (
    "Package", "Definition", "CalculationDefinition", "FunctionDefinition",
)


def _declared_name(decl):
    """Extract declaredName from a declaration-shaped dict (best effort).

    Digs through up to three declaration wrappers — e.g. a
    ConstraintUsage's ``CalculationUsageDeclaration → UsageDeclaration →
    FeatureDeclaration → Identification`` chain.
    """
    depth = 0
    while isinstance(decl, dict) and depth < 4:
        ident = decl.get("identification")
        if isinstance(ident, dict) and ident.get("declaredName") is not None:
            return ident.get("declaredName")
        decl = decl.get("declaration")
        depth += 1
    return None


def _find_first(node, want_name):
    """Depth-first search for the first dict with node['name'] == want_name."""
    if isinstance(node, dict):
        if node.get("name") == want_name:
            return node
        for v in node.values():
            found = _find_first(v, want_name)
            if found is not None:
                return found
    elif isinstance(node, list):
        for v in node:
            found = _find_first(v, want_name)
            if found is not None:
                return found
    return None


def _specialization_type_name(decl):
    """Last segment of the declared type name in a declaration dict."""
    if not isinstance(decl, dict):
        return None
    inner = decl.get("declaration")
    spec = None
    if isinstance(inner, dict):
        spec = inner.get("specialization")
    qn = _find_first(spec, "QualifiedName") if spec is not None else None
    if qn is not None:
        names = qn.get("names")
        if isinstance(names, list) and names:
            return names[-1]
    return None


class _Collector:
    """Walk the raw parser dict, building the namespace tree."""

    def __init__(self):
        self.root = _Namespace("", ())
        self.types = {}        # bare type name -> _Namespace (definitions)
        self.calcs = {}        # qname string -> (expr dict, scope namespaces)
        # (qname string, expr dict, scope namespaces,
        #  [(language, text), ...] textual representations)
        self.constraints = []
        self._anon = 0

    # -- entry ---------------------------------------------------------

    def collect(self, root_dict):
        for member in root_dict.get("ownedRelationship", []) or []:
            self._walk(member, self.root, (), [self.root])
        return self

    # -- walking -------------------------------------------------------

    def _walk(self, node, ns, qname, scope):
        if not isinstance(node, dict):
            if isinstance(node, list):
                for item in node:
                    self._walk(item, ns, qname, scope)
            return

        name = node.get("name")

        # attribute-like value carrier
        if name == "Usage":
            self._handle_usage(node, ns)

        # constraint carrier (also a named container below)
        if name in _CONSTRAINT_TYPES:
            self._handle_constraint(node, qname, scope)

        # named container: declaration + body → push a namespace child
        decl = node.get("declaration")
        body = node.get("body")
        if isinstance(decl, dict) and isinstance(body, dict):
            dn = _declared_name(decl) or self._anon_name()
            is_definition = name in (
                "Package", "Definition", "CalculationDefinition",
                "FunctionDefinition",
            )
            child = _Namespace(dn, qname + (dn,))
            child.parent = ns
            child.type_name = _specialization_type_name(decl)
            ns.children.setdefault(dn, child)
            if is_definition:
                self.types.setdefault(dn, child)
            new_scope = [child] + scope
            self._walk_body(body, child, qname + (dn,), new_scope)
            # calc result expressions are evaluated in the *enclosing*
            # scope (calc bodies see their parent's features), so the
            # calc is registered against the parent scope.
            if name in _CALC_TYPES:
                expr = self._body_expression(body)
                if expr is not None:
                    self.calcs["::".join(qname + (dn,))] = (expr, list(scope))
                    ns.values.setdefault(dn, ("calc", expr))
            for k, v in node.items():
                if k not in ("declaration", "body"):
                    self._walk(v, ns, qname, scope)
            return

        # generic descent (valuepart handled by _handle_usage)
        for k, v in node.items():
            if k == "valuepart":
                continue
            self._walk(v, ns, qname, scope)

    def _anon_name(self):
        self._anon += 1
        return f"__anon{self._anon}"

    def _walk_body(self, body, ns, qname, scope):
        for k, v in body.items():
            if k == "name":
                continue
            self._walk(v, ns, qname, scope)

    # -- carriers --------------------------------------------------------

    def _handle_usage(self, node, ns):
        completion = node.get("completion")
        valuepart = (
            completion.get("valuepart")
            if isinstance(completion, dict) else None
        )
        expr = (
            _find_first(valuepart, "OwnedExpression")
            if isinstance(valuepart, dict) else None
        )
        dn = _declared_name(node.get("declaration"))
        if dn is None:
            if expr is None:
                return
            dn = self._anon_name()
        if expr is not None:
            ns.values.setdefault(dn, ("expr", expr))
            return
        # No value — but a typed usage (``part w : W;``) still becomes a
        # chain-resolvable namespace child.
        type_name = _specialization_type_name(node.get("declaration"))
        if type_name is not None and dn not in ns.children:
            child = _Namespace(dn, ns.qname + (dn,))
            child.parent = ns
            child.type_name = type_name
            ns.children[dn] = child

    def _handle_constraint(self, node, qname, scope):
        expr = self._body_expression(node.get("body"))
        textual = self._body_textual_representations(node.get("body"))
        if expr is None and not textual:
            return
        dn = _declared_name(node.get("declaration")) or self._anon_name()
        self.constraints.append(
            ("::".join(qname + (dn,)), expr, list(scope), textual))

    @staticmethod
    def _body_expression(body):
        """First OwnedExpression inside a constraint/calc body."""
        if not isinstance(body, dict):
            return None
        rem = _find_first(body, "ResultExpressionMember")
        if rem is not None:
            oe = rem.get("ownedRelatedElement")
            if isinstance(oe, dict) and oe.get("name") == "OwnedExpression":
                return oe
        return _find_first(body, "OwnedExpression")

    @staticmethod
    def _body_textual_representations(body):
        """[(language, text), ...] from `rep language "..." /* ... */` bodies.

        The visitor places TextualRepresentation dicts at
        body.part[].item[].item.ownedRelationship[] (CalculationBodyPart ->
        CalculationBodyItem -> ActionBodyItem).
        """
        out = []
        if not isinstance(body, dict):
            return out
        for part in body.get("part") or []:
            if not isinstance(part, dict):
                continue
            for item in part.get("item") or []:
                if not isinstance(item, dict):
                    continue
                abi = item.get("item")
                if not isinstance(abi, dict) or \
                        abi.get("name") != "ActionBodyItem":
                    continue
                rel = abi.get("ownedRelationship")
                rels = rel if isinstance(rel, list) else (
                    [rel] if isinstance(rel, dict) else [])
                for r in rels:
                    if isinstance(r, dict) and \
                            r.get("name") == "TextualRepresentation":
                        text = str(r.get("body") or "")
                        # Strip the /* */ comment markers the lexer keeps.
                        if text.startswith("/*") and text.endswith("*/"):
                            text = text[2:-2].strip()
                        out.append((r.get("language") or "", text))
        return out


# ---------------------------------------------------------------------------
# evaluation pass
# ---------------------------------------------------------------------------

# precedence-chain level -> child-level key (grammar nesting)
_LEVEL_CHILD = [
    ("NullCoalescingExpression", "implies"),
    ("ImpliesExpression", "or"),
    ("OrExpression", "xor"),
    ("XorExpression", "and"),
    ("AndExpression", "equality"),
    ("EqualityExpression", "classification"),
    ("ClassificationExpression", "relational"),
    ("RelationalExpression", "range"),
    ("RangeExpression", "additive"),
    ("AdditiveExpression", "multiplicitive"),
    ("MultiplicativeExpression", "exponential"),
    ("ExponentiationExpression", "unary"),
    ("UnaryExpression", "extent"),
    ("ExtentExpression", "primary"),
]

_BOOL_OPS = {"and", "or", "xor"}
_CMP_OPS = {"==", "!=", "<", "<=", ">", ">="}
_ARITH_OPS = {"+", "-", "*", "/", "%", "**"}


class _Evaluator:
    """Evaluate OwnedExpression dicts against a namespace scope."""

    def __init__(self, scope, bindings=None, memo=None, types=None):
        # scope: innermost-first list of _Namespace
        self.scope = list(scope)
        self.bindings = dict(bindings or {})
        self.memo = {} if memo is None else memo
        self.types = types if types is not None else {}

    # -- name resolution -------------------------------------------------

    def resolve(self, names):
        """Resolve a dotted name (list of segments) to a value."""
        first, rest = names[0], list(names[1:])
        if first in self.bindings:
            if rest:
                raise UnknownNameError(
                    f"Cannot chain into binding '{first}' "
                    f"({'.'.join(names)})"
                )
            return self.bindings[first]
        for ns in self.scope:
            if first in ns.values:
                if not rest:
                    return self._materialize(ns.values[first], names)
                raise UnknownNameError(
                    f"Cannot chain into value '{first}' "
                    f"({'.'.join(names)})"
                )
            if first in ns.children:
                return self._descend(ns.children[first], rest, names)
        # type fallback: the first segment may name a definition
        tnode = self.types.get(first)
        if tnode is not None:
            return self._descend(tnode, rest, names)
        # global fallback: the name may be defined in an unrelated
        # namespace (e.g. evaluating a what-if expression at package
        # level).  Use it only when unambiguous.
        hits = [ns for ns in self._all_namespaces() if first in ns.values]
        if len(hits) == 1:
            if not rest:
                return self._materialize(hits[0].values[first], names)
            raise UnknownNameError(
                f"Cannot chain into value '{first}' ({'.'.join(names)})"
            )
        if len(hits) > 1:
            raise UnknownNameError(
                f"Ambiguous name '{first}' — defined in "
                f"{sorted('::'.join(ns.qname + (first,)) for ns in hits)}"
            )
        # Glued-text fallback: the visitor collapses some complex operands
        # (e.g. ``mass / 4 [kg]`` with a unit bracket) into a single
        # QualifiedName string.  If the "name" looks like an expression,
        # re-parse and evaluate it in the current scope (same strategy as
        # ``const_fold`` in semantic.py).
        if first and _looks_like_expression(first):
            value = self._evaluate_glued(first)
            if value is not None:
                return value
        raise UnknownNameError(
            f"Unknown name '{'.'.join(names)}' — available: "
            f"{sorted(self._available_names())}"
        )

    def _evaluate_glued(self, text):
        """Re-parse a glued expression text and evaluate it in scope."""
        try:
            expr_dict = _parse_expression_text(text)
        except EvaluationError:
            return None
        try:
            return self.evaluate(expr_dict)
        except EvaluationError:
            return None

    def _all_namespaces(self):
        seen = set()
        stack = [ns for ns in self.scope]
        while stack:
            ns = stack.pop()
            if id(ns) in seen:
                continue
            seen.add(id(ns))
            yield ns
            stack.extend(ns.children.values())

    def _descend(self, node, rest, full_names):
        """Walk remaining chain segments through namespace nodes."""
        current = node
        for i, seg in enumerate(rest):
            if seg in current.values:
                if i == len(rest) - 1:
                    return self._materialize(current.values[seg], full_names)
                value = self._materialize(current.values[seg], names=None)  # noqa
                raise UnknownNameError(
                    f"Cannot chain into value '{seg}' "
                    f"({'.'.join(str(n) for n in full_names)})"
                )
            if seg in current.children:
                current = current.children[seg]
                continue
            # type fallback: usage namespace → its declared type
            if current.type_name:
                tnode = self.types.get(current.type_name)
                if tnode is not None:
                    if seg in tnode.values:
                        if i == len(rest) - 1:
                            return self._materialize(
                                tnode.values[seg], full_names
                            )
                        current = tnode
                        continue
                    if seg in tnode.children:
                        current = tnode.children[seg]
                        continue
            raise UnknownNameError(
                f"Unknown name '{'.'.join(str(n) for n in full_names)}' "
                f"(no '{seg}' in scope)"
            )
        raise UnknownNameError(
            f"'{'.'.join(str(n) for n in full_names)}' is a structure, "
            "not a value"
        )

    def _materialize(self, entry, full_names):
        if not isinstance(entry, tuple):
            return entry
        kind, payload = entry
        if kind == "value":
            return payload
        key = ("lazy", id(payload))
        if key in self.memo:
            v = self.memo[key]
            if v is _IN_PROGRESS:
                raise EvaluationError(
                    "Circular value dependency evaluating "
                    f"'{'.'.join(str(n) for n in full_names or [])}'"
                )
            return v
        self.memo[key] = _IN_PROGRESS
        try:
            return self.evaluate(payload)
        finally:
            self.memo.pop(key, None)

    def _available_names(self):
        names = set(self.bindings)
        for ns in self.scope:
            names |= set(ns.values)
            names |= set(ns.children)
        return names

    # -- expression evaluation -------------------------------------------

    def evaluate(self, node):
        if not isinstance(node, dict):
            raise EvaluationError(f"Cannot evaluate {node!r}")
        name = node.get("name")
        if name == "OwnedExpression":
            return self.evaluate(node.get("expression"))
        if name == "ConditionalExpression":
            return self._eval_conditional(node)
        for level, child_key in _LEVEL_CHILD:
            if name == level:
                return self._eval_chain(node, child_key)
        if name == "PrimaryExpression":
            return self._eval_primary(node)
        if name == "BaseExpression":
            return self._eval_base(node)
        if isinstance(name, str) and name.endswith("ExpressionReference"):
            # Standalone parses wrap right-hand boolean operands in
            # ``EqualityExpressionReference → EqualityExpressionMember →
            # EqualityExpression``; unwrap one level.
            rel = node.get("ownedRelationship") or {}
            inner = rel.get("ownedRelatedElement")
            if isinstance(inner, dict):
                return self.evaluate(inner)
            raise EvaluationError(f"Empty {name}")
        if name == "SequenceExpression":
            oe = node.get("ownedRelationship")
            return self.evaluate(oe) if isinstance(oe, dict) else None
        if name in ("LiteralInteger", "LiteralReal"):
            return _parse_number(node.get("value"))
        if name == "LiteralBoolean":
            return str(node.get("value")).strip().lower() == "true"
        if name == "LiteralString":
            v = node.get("value", "")
            return v.strip('"') if isinstance(v, str) else v
        if name == "LiteralInfinity":
            return math.inf
        if name == "LiteralNull":
            return None
        raise UnsupportedExpressionError(
            f"Unsupported expression construct: {name}"
        )

    def _eval_conditional(self, node):
        if node.get("operator"):
            raise UnsupportedExpressionError(
                "conditional expressions ('? :' / 'if then else') are not "
                "supported by the evaluator"
            )
        operand = node.get("operand")
        if isinstance(operand, list) and operand:
            return self.evaluate(operand[0])
        raise EvaluationError("Empty conditional expression")

    def _eval_chain(self, node, child_key):
        child = node.get(child_key)
        if not isinstance(child, dict):
            raise EvaluationError(
                f"Malformed {node.get('name')} (no {child_key})"
            )
        result = self.evaluate(child)
        for op in node.get("operation") or []:
            operator = op.get("operator")
            operand = self.evaluate(op.get("operand"))
            result = _apply_binary(operator, result, operand)
        # UnaryExpression carries its operator as a plain string ("not",
        # "-", "+") applying to the extent value.
        if node.get("name") == "UnaryExpression":
            op = node.get("operator")
            if isinstance(op, str) and op.strip():
                result = _apply_unary(op.strip(), result)
        # ExponentiationExpression carries its operators in paired
        # operator/operand lists instead of an operation list.
        if node.get("name") == "ExponentiationExpression":
            for operator, operand in zip(node.get("operator") or [],
                                         node.get("operand") or []):
                result = _apply_binary(operator, result,
                                       self.evaluate(operand))
        return result

    def _eval_primary(self, node):
        base = node.get("base")
        if not isinstance(base, dict):
            raise EvaluationError("PrimaryExpression without base")

        # feature chains (. / ->) via ownedRelationship1/2 — resolve the
        # combined dotted name directly (evaluating the base alone would
        # fail for structure references like ``wheels.radius``).
        names = self._chain_names(node)
        if names:
            base_parts = _base_reference_names(base)
            if base_parts is None:
                raise UnsupportedExpressionError(
                    "feature chains on non-reference values"
                )
            return self.resolve(base_parts + names)

        value = self.evaluate(base)

        # unit suffix: value [unit]
        operator = node.get("operator") or []
        operand = node.get("operand") or []
        if "[" in operator and operand:
            unit_name = _unit_name_from(operand[0])
            if unit_name:
                try:
                    value = value * ureg(unit_name)
                except Exception as e:
                    raise EvaluationError(
                        f"Unknown unit '{unit_name}': {e}"
                    ) from e
        return value

    @staticmethod
    def _chain_names(primary):
        names = []
        for key in ("ownedRelationship1", "ownedRelationship2"):
            rel = primary.get(key)
            # rel may be a dict, a list of dicts, and the chain member
            # may sit directly on the item or one level down (ANTLR
            # shape varies between emits).
            candidates = rel if isinstance(rel, list) else [rel]
            for rel_item in candidates:
                if not isinstance(rel_item, dict):
                    continue
                member = rel_item
                if member.get("name") != "FeatureChainMember":
                    member = member.get("ownedRelationship")
                    if isinstance(member, list):
                        member = member[0] if member else None
                if (isinstance(member, dict)
                        and member.get("name") == "FeatureChainMember"):
                    me = member.get("memberElement")
                    if isinstance(me, dict):
                        qn = me.get("names")
                        if isinstance(qn, list):
                            names.extend(qn)
        return names

    def _eval_base(self, node):
        rel = node.get("ownedRelationship")
        if isinstance(rel, list):
            rel = rel[0] if rel else None
        if not isinstance(rel, dict):
            raise EvaluationError("Empty BaseExpression")
        name = rel.get("name")
        if name == "FeatureReferenceExpression":
            members = rel.get("ownedRelationship") or []
            if isinstance(members, dict):
                members = members.get("ownedRelationship") or []
            parts = []
            for m in members:
                me = m.get("memberElement") if isinstance(m, dict) else None
                qn = me.get("names") if isinstance(me, dict) else None
                if isinstance(qn, list):
                    parts.extend(qn)
            if not parts:
                raise EvaluationError("Empty feature reference")
            return self.resolve(parts)
        if name == "InvocationExpression":
            return self._eval_invocation(rel)
        return self.evaluate(rel)

    def _evaluate_glued(self, text):
        """Evaluate glued expression text in the current scope.

        The visitor collapses some complex operands (e.g.
        ``mass / 4 [kg]`` — a non-literal value with a bracket unit)
        into a single FeatureReferenceMember carrying the raw text.
        Re-parsing that text reproduces the same glue (the structured
        climber does not handle bracket units), so split the unit
        bracket here and evaluate the value part in scope.
        """
        self._glue_depth = getattr(self, "_glue_depth", 0) + 1
        try:
            if self._glue_depth > 8:
                raise EvaluationError(
                    f"Cannot evaluate glued expression {text!r} "
                    "(recursion limit)"
                )
            stripped = text.strip()
            if stripped.endswith("]") and "[" in stripped \
                    and not stripped.startswith('"'):
                idx = stripped.index("[")
                value_text = stripped[:idx].strip()
                unit_text = stripped[idx + 1:-1].strip()
                if value_text and unit_text:
                    try:
                        value = self._eval_text_in_scope(value_text)
                        return value * ureg(unit_text)
                    except EvaluationError:
                        pass
            try:
                expr_dict = _parse_expression_text(text)
            except EvaluationError:
                return None
            try:
                return self.evaluate(expr_dict)
            except EvaluationError:
                return None
        finally:
            self._glue_depth -= 1

    def _eval_text_in_scope(self, text):
        """Parse *text* and evaluate it against this evaluator's scope."""
        expr_dict = _parse_expression_text(text)
        return self.evaluate(expr_dict)

    def _eval_invocation(self, rel):
        owned = rel.get("ownedRelationship") or {}
        type_node = owned.get("type") or {}
        qn = (type_node.get("type") or {}).get("names") or []
        func_name = qn[-1] if qn else None
        func = _FUNCTIONS.get(func_name)
        if func is None:
            raise UnsupportedExpressionError(
                f"Unknown function '{func_name}' — supported: "
                f"{sorted(_FUNCTIONS)}"
            )
        args = []
        arg_list = rel.get("arg_list") or {}
        pos = (arg_list.get("pos_list") or {}).get("ownedRelationship") or []
        for member in pos:
            arg = member.get("ownedRelatedElement")
            if isinstance(arg, dict):
                val = arg.get("ownedRelationship")
                if isinstance(val, dict):
                    oe = val.get("ownedRelatedElement")
                    if isinstance(oe, dict):
                        args.append(self.evaluate(oe))
        return func(*args)


def _looks_like_expression(text):
    """Heuristic: a "name" containing operators is glued expression text."""
    return isinstance(text, str) and any(c in text for c in "+-*/%([") and \
        not text.strip().startswith('"')


def _base_reference_names(base):
    """Name segments of a BaseExpression feature reference, or None."""
    if not isinstance(base, dict) or base.get("name") != "BaseExpression":
        return None
    rel = base.get("ownedRelationship")
    if isinstance(rel, list):
        rel = rel[0] if rel else None
    if not isinstance(rel, dict) or rel.get("name") != "FeatureReferenceExpression":
        return None
    members = rel.get("ownedRelationship") or []
    if isinstance(members, dict):
        members = members.get("ownedRelationship") or []
    parts = []
    for m in members:
        me = m.get("memberElement") if isinstance(m, dict) else None
        qn = me.get("names") if isinstance(me, dict) else None
        if isinstance(qn, list):
            parts.extend(qn)
    return parts or None


def _parse_number(text):
    if isinstance(text, (int, float)):
        return text
    s = str(text).strip()
    try:
        return int(s)
    except ValueError:
        return float(s)


def _unit_name_from(seq_expr):
    """Extract a unit name from a ``[unit]`` operand dict."""
    qn = _find_first(seq_expr, "QualifiedName")
    if qn is None:
        return None
    names = qn.get("names")
    if isinstance(names, list) and names:
        return ".".join(str(n) for n in names)
    return None


def _apply_unary(operator, value):
    if operator == "not":
        if not isinstance(value, bool):
            raise EvaluationError(
                f"'not' requires a boolean operand, got {type(value).__name__}"
            )
        return not value
    if operator == "-":
        return -value
    if operator == "+":
        return +value
    raise UnsupportedExpressionError(f"Unsupported unary operator '{operator}'")


def _apply_binary(operator, left, right):
    if operator in _ARITH_OPS:
        try:
            if operator == "+":
                return left + right
            if operator == "-":
                return left - right
            if operator == "*":
                return left * right
            if operator == "/":
                return left / right
            if operator == "%":
                return left % right
            if operator == "**":
                return left ** right
        except Exception as e:
            raise EvaluationError(
                f"{left!r} {operator} {right!r}: {e}"
            ) from e
    if operator in _CMP_OPS:
        try:
            if operator == "==":
                return left == right
            if operator == "!=":
                return left != right
            if operator == "<":
                return left < right
            if operator == "<=":
                return left <= right
            if operator == ">":
                return left > right
            if operator == ">=":
                return left >= right
        except Exception as e:
            raise EvaluationError(
                f"cannot compare {left!r} {operator} {right!r}: {e}"
            ) from e
    if operator in _BOOL_OPS:
        if not isinstance(left, bool) or not isinstance(right, bool):
            raise EvaluationError(
                f"'{operator}' requires boolean operands, got "
                f"{type(left).__name__} and {type(right).__name__}"
            )
        if operator == "and":
            return left and right
        if operator == "or":
            return left or right
        if operator == "xor":
            return left != right
    raise UnsupportedExpressionError(f"Unsupported operator '{operator}'")


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------


@dataclass
class ConstraintResult:
    """Result of evaluating one constraint body."""

    qualified_name: str
    expression_text: str = ""
    value: object = None
    error: str = None

    @property
    def passed(self):
        return self.value is True and self.error is None

    @property
    def failed(self):
        return self.value is False and self.error is None

    @property
    def errored(self):
        return self.error is not None


@dataclass
class ConstraintReport:
    """All constraint evaluation results for a model."""

    results: list = field(default_factory=list)

    @property
    def passed(self):
        return [r for r in self.results if r.passed]

    @property
    def failed(self):
        return [r for r in self.results if r.failed]

    @property
    def errored(self):
        return [r for r in self.results if r.errored]

    def to_text(self):
        lines = [
            f"Constraint check: {len(self.results)} constraints, "
            f"{len(self.passed)} passed, {len(self.failed)} failed, "
            f"{len(self.errored)} errors"
        ]
        for r in self.results:
            if r.passed:
                status = "PASS"
            elif r.failed:
                status = "FAIL"
            else:
                status = "ERROR"
            lines.append(
                f"- [{status}] {r.qualified_name}: {r.expression_text}"
            )
            if r.error:
                lines.append(f"    {r.error}")
        return "\n".join(lines)

    def to_json(self):
        return {
            "summary": {
                "total": len(self.results),
                "passed": len(self.passed),
                "failed": len(self.failed),
                "errors": len(self.errored),
            },
            "constraints": [
                {
                    "name": r.qualified_name,
                    "expression": r.expression_text,
                    "value": str(r.value) if not _json_safe(r.value) else r.value,
                    "error": r.error,
                }
                for r in self.results
            ],
        }


def _json_safe(v):
    return isinstance(v, (bool, int, float, str, type(None)))


def _expression_text(expr_dict):
    """Human-readable text of an expression dict (via its grammar class)."""
    try:
        import sysmlpy.grammar.classes as gc
        cls = getattr(gc, expr_dict.get("name", ""), None)
        if cls is not None:
            return cls(expr_dict).dump()
    except Exception:
        pass
    return None


def _model_root_dict(model):
    """Raw, faithful parser dictionary for the model."""
    from sysmlpy import load_grammar
    try:
        text = model.dump()
    except ValueError:
        text = ""
    if not text.strip():
        return {"name": "PackageBodyElement", "ownedRelationship": []}
    return load_grammar(text)


def _collect_model(model):
    collector = _Collector()
    collector.collect(_model_root_dict(model))
    return collector


def _iter_namespaces(root):
    stack = [(root, ())]
    while stack:
        ns, qname = stack.pop()
        yield ns, qname
        for child in ns.children.values():
            stack.append((child, qname + (child.name,)))


def collect_values(model, bindings=None):
    """Evaluate every attribute default in the model.

    Returns a dict mapping qualified names (``"Pkg::Part::attr"``) and
    bare names (``"attr"``) to values (pint ``Quantity``, int, float,
    bool, str, or None).  Values referencing other attributes are
    evaluated transitively; cycles raise :class:`EvaluationError`
    (reported as ``<error: ...>`` entries).
    """
    collector = _collect_model(model)
    bindings = bindings or {}
    out = {}
    for ns, qname in _iter_namespaces(collector.root):
        evaluator = _Evaluator(_namespace_scope(ns), bindings=bindings,
                               types=collector.types)
        for name in ns.values:
            full = "::".join(qname + (name,))
            if name in bindings:
                # an explicit binding overrides the attribute's own value
                value = bindings[name]
            else:
                try:
                    value = evaluator._materialize(ns.values[name], [name])
                except EvaluationError as e:
                    value = f"<error: {e}>"
            out[full] = value
            out.setdefault(name, value)
    return out


def _namespace_scope(ns):
    """Innermost-first namespace chain for *ns* (itself included)."""
    chain = []
    node = ns
    while node is not None:
        chain.append(node)
        node = node.parent
    return chain


def _scope_chain_for(collector, element_qname):
    """Namespace chain (innermost first) for a qualified element name."""
    parts = [p for p in element_qname.split("::") if p]
    node = collector.root
    chain = []
    for seg in parts:
        child = node.children.get(seg)
        if child is None:
            raise UnknownNameError(
                f"No element '{seg}' in model scope "
                f"(available under '{node.name or '<root>'}': "
                f"{sorted(node.children)})"
            )
        node = child
        chain.append(node)
    if not chain:
        return [collector.root]
    scope = list(reversed(chain))  # innermost first
    scope.append(collector.root)
    return scope


def evaluate_expression(expr, model=None, element=None, bindings=None):
    """Evaluate a standalone SysML expression against a model scope.

    Parameters
    ----------
    expr : str
        SysML v2 expression text (e.g. ``"mass * speed"``).
    model : Model, optional
        Model providing attribute values for name resolution.
    element : str, optional
        Qualified name of the element whose scope to use (e.g.
        ``"VehicleSpec::Vehicle"``) — names resolve against that
        element's attributes first, then outward.
    bindings : dict, optional
        Explicit name → value overrides (what-if).  Values may be
        numbers, bools, strings or pint Quantities.

    Returns
    -------
    The evaluated value (number, pint Quantity, bool, or str).
    """
    if model is not None:
        collector = _collect_model(model)
        scope = _scope_chain_for(collector, element) if element else [collector.root]
        evaluator = _Evaluator(scope, bindings=bindings,
                               types=collector.types)
    else:
        evaluator = _Evaluator([], bindings=bindings)
    expr_dict = _parse_expression_text(expr)
    return evaluator.evaluate(expr_dict)


def evaluate_calculation(model, calc_name, bindings=None):
    """Evaluate a named ``calc def`` result expression.

    ``bindings`` supplies name overrides (e.g. ``in`` parameter values).
    Returns the evaluated value.
    """
    collector = _collect_model(model)
    entry = collector.calcs.get(calc_name)
    if entry is None:
        for qname, candidate in collector.calcs.items():
            if qname.rsplit("::", 1)[-1] == calc_name:
                entry = candidate
                break
    if entry is None:
        raise UnknownNameError(
            f"No calculation named '{calc_name}' — found: "
            f"{sorted(collector.calcs)}"
        )
    expr, scope = entry
    evaluator = _Evaluator(scope, bindings=bindings, types=collector.types)
    return evaluator.evaluate(expr)


def check_constraints(model, bindings=None):
    """Evaluate every constraint body in the model.

    Returns a :class:`ConstraintReport`.
    """
    collector = _collect_model(model)
    results = []
    for qname, expr, scope, textual in collector.constraints:
        evaluator = _Evaluator(scope, bindings=bindings,
                               types=collector.types)
        result = ConstraintResult(qualified_name=qname)
        if expr is None:
            language, text = textual[0]
            result.expression_text = text
            result.error = (
                "not machine-evaluable \u2014 textual body in language "
                f"'{language or 'unspecified'}': {text!r}"
            )
            results.append(result)
            continue
        result.expression_text = _expression_text(expr)
        try:
            value = evaluator.evaluate(expr)
            if not isinstance(value, bool):
                result.error = (
                    f"constraint did not evaluate to a boolean "
                    f"(got {type(value).__name__}: {value!r})"
                )
                result.value = value
            else:
                result.value = value
        except EvaluationError as e:
            result.error = str(e)
        except Exception as e:  # pint dimensionality errors etc.
            result.error = f"{type(e).__name__}: {e}"
        results.append(result)
    return ConstraintReport(results=results)


def _parse_expression_text(expr):
    """Parse a standalone expression into an OwnedExpression dict."""
    import sys
    from sysmlpy import load_grammar
    from sysmlpy.antlr_parser import SysMLSyntaxError
    wrapper = (
        "package __eval__ { part __p__ { attribute __e : Real := "
        + expr.strip().rstrip(";")
        + "; } }"
    )
    # The parse may happen deep inside evaluator recursion (glued-text
    # fallback); ANTLR's ATN lookahead walks need extra stack headroom.
    old_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(old_limit, 5000))
    try:
        try:
            d = load_grammar(wrapper)
        except SysMLSyntaxError as e:
            raise EvaluationError(
                f"Cannot parse expression {expr!r}: {e}"
            ) from e
    finally:
        sys.setrecursionlimit(old_limit)
    oe = _find_first(d, "OwnedExpression")
    if oe is None:
        raise EvaluationError(f"Cannot parse expression {expr!r}")
    return oe