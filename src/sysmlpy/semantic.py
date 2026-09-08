#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Semantic analysis for SysML v2 models.

Provides undefined symbol detection by building a symbol table from the
parsed model tree and cross-referencing all qualified name references.
"""

from __future__ import annotations

import ast
import dataclasses
import os
import re
from pathlib import Path
from typing import Any, Optional

from sysmlpy.definition import Package


@dataclasses.dataclass
class SemanticIssue:
    """A single semantic issue found during analysis."""

    severity: str
    code: str
    message: str
    element: Any = None
    reference: str = ""


class AnalysisResult(list):
    """A list of SemanticIssue with convenience accessors.

    Backward-compatible with ``list[SemanticIssue]`` — existing code that
    iterates or checks ``isinstance(result, list)`` continues to work.
    """

    @property
    def errors(self) -> list[SemanticIssue]:
        """Return only error-severity issues."""
        return [i for i in self if i.severity == "error"]

    @property
    def warnings(self) -> list[SemanticIssue]:
        """Return only warning-severity issues."""
        return [i for i in self if i.severity == "warning"]

    def raise_on_errors(self, message: str = "Semantic errors found") -> "AnalysisResult":
        """Raise ValueError if any error-severity issues exist.

        Returns self for chaining when no errors are present.
        """
        if self.errors:
            details = "\n".join(f"  [{i.code}] {i.message}" for i in self.errors)
            raise ValueError(f"{message}:\n{details}")
        return self

    def __bool__(self) -> bool:
        """True when there are no errors (warnings are acceptable)."""
        return len(self.errors) == 0


# ---------------------------------------------------------------------------
# Library Symbol Index
# ---------------------------------------------------------------------------

# Regex patterns for extracting symbols from library files
_PACKAGE_RE = re.compile(
    r'(?:standard\s+library\s+)?package\s+(\w+)\s*\{',
    re.IGNORECASE,
)
_DEFINITION_RE = re.compile(
    r'(?:abstract\s+)?'
    r'(?:datatype|class|metaclass|attribute\s+def|part\s+def|item\s+def|port\s+def|'
    r'action\s+def|state\s+def|constraint\s+def|calc\s+def|requirement\s+def|'
    r'interface\s+def|connection\s+def|flow\s+def|enumeration\s+def|enum\s+def|'
    r'use\s+case\s+def|case\s+def|analysis\s+case\s+def|verification\s+case\s+def|'
    r'view\s+def|viewpoint\s+def|concern\s+def|allocation\s+def|metadata\s+def|'
    r'rendering\s+def|individual\s+def|feature\s+def|reference\s+def|'
    r'structure\s+def|behavior\s+def|occurrence\s+def|assertion\s+def|'
    r'typedef|classifier|function)\s+'
    r"""(['"]?\w+['"]?)""",
    re.IGNORECASE,
)


class LibrarySymbolIndex:
    """Index of all symbols defined in the standard library.

    Scans .kerml and .sysml files to extract package-qualified symbol names.
    Results are cached to avoid repeated file I/O.
    """

    _cache: Optional[frozenset[str]] = None
    _simple_names_cache: Optional[frozenset[str]] = None
    _library_roots: Optional[list[Path]] = None

    @classmethod
    def get_symbols(
        cls,
        library_roots: Optional[Path | Sequence[Path]] = None,
    ) -> frozenset[str]:
        """Return all known library symbol names as qualified strings.

        Parameters
        ----------
        library_roots : Path or sequence of Path, optional
            Root directory or directories of the standard library.
            Defaults to the bundled library shipped with sysmlpy.

        Returns
        -------
        frozenset[str]
            Set of qualified names like ``"ScalarValues::Integer"``,
            ``"ISQ::LengthValue"``, etc.
        """
        if cls._cache is not None:
            return cls._cache

        roots = cls._resolve_roots(library_roots)
        if not roots:
            # Fall back to minimal hardcoded set
            cls._cache = _KNOWN_LIBRARY_SYMBOLS
            return cls._cache

        symbols = set()
        for root in roots:
            if not root.is_dir():
                continue
            for ext in ("*.kerml", "*.sysml"):
                for filepath in root.rglob(ext):
                    cls._extract_from_file(filepath, symbols)

        cls._cache = frozenset(symbols)
        return cls._cache

    @classmethod
    def _resolve_roots(
        cls,
        library_roots: Optional[Path | Sequence[Path]],
    ) -> list[Path]:
        """Resolve library roots from the given argument."""
        if library_roots is None:
            default = cls._default_library_root()
            return [default] if default is not None else []

        if isinstance(library_roots, Path):
            return [library_roots]

        return list(library_roots)

    @classmethod
    def _default_library_root(cls) -> Optional[Path]:
        """Find the bundled library directory."""
        try:
            import sysmlpy
            pkg_path = Path(sysmlpy.__file__).parent
            lib_path = pkg_path / "library"
            if lib_path.is_dir():
                return lib_path
        except ImportError:
            pass

        # Fallback: relative to this module
        module_path = Path(__file__).parent
        lib_path = module_path / "library"
        if lib_path.is_dir():
            return lib_path

        return None

    @classmethod
    def _extract_from_file(cls, filepath: Path, symbols: set[str]) -> None:
        """Extract symbol names from a single library file."""
        try:
            content = filepath.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return

        # Track package nesting with brace depth
        package_stack: list[tuple[str, int]] = []  # (name, depth_at_open)
        brace_depth = 0

        for line in content.splitlines():
            # Strip comments
            stripped = line.strip()
            if stripped.startswith("doc") or stripped.startswith("/*") or stripped.startswith("*"):
                continue

            # Count braces in this line
            open_braces = stripped.count("{")
            close_braces = stripped.count("}")

            # Check for package opening (before updating depth)
            pkg_match = _PACKAGE_RE.search(stripped)
            if pkg_match:
                pkg_name = pkg_match.group(1)
                package_stack.append((pkg_name, brace_depth))
                # The package itself is a symbol
                if len(package_stack) > 1:
                    symbols.add("::".join(name for name, _ in package_stack))

            # Check for definitions (use current package context)
            def_match = _DEFINITION_RE.search(stripped)
            if def_match and package_stack:
                def_name = def_match.group(1).strip("'\"")
                qualified = "::".join(name for name, _ in package_stack) + "::" + def_name
                symbols.add(qualified)

            # Update brace depth
            brace_depth += open_braces - close_braces

            # Pop packages that have been closed
            while package_stack and package_stack[-1][1] >= brace_depth:
                package_stack.pop()

    @classmethod
    def get_simple_names(
        cls,
        library_roots: Optional[Path | Sequence[Path]] = None,
    ) -> frozenset[str]:
        """Return all simple (unqualified) symbol names from the library.

        For example, ``"ScalarValues::Integer"`` yields ``"Integer"``.
        """
        if cls._simple_names_cache is not None:
            return cls._simple_names_cache
        qualified = cls.get_symbols(library_roots)
        cls._simple_names_cache = frozenset(
            name.rsplit("::", 1)[-1] for name in qualified
        )
        return cls._simple_names_cache

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the cached symbol index (useful for testing)."""
        cls._cache = None
        cls._simple_names_cache = None


# Backwards-compatible constant (populated lazily from library files)
_KNOWN_LIBRARY_SYMBOLS: frozenset[str] = frozenset({
    # Scalar values
    "ScalarValues::Boolean", "ScalarValues::Integer", "ScalarValues::Natural",
    "ScalarValues::Positive", "ScalarValues::Nonnegative",
    "ScalarValues::Rational", "ScalarValues::Real", "ScalarValues::String",
    "ScalarValues::Complex", "ScalarValues::UnlimitedNatural",
    "ScalarValues::Number", "ScalarValues::ScalarValue",
    # ISQ base quantities
    "ISQ::Length", "ISQ::Mass", "ISQ::Time", "ISQ::ElectricCurrent",
    "ISQ::ThermodynamicTemperature", "ISQ::AmountOfSubstance",
    "ISQ::LuminousIntensity", "ISQ::Angle", "ISQ::SolidAngle",
    "ISQ::Information",
    # ISQ value types
    "ISQ::LengthValue", "ISQ::MassValue", "ISQ::TimeValue",
    "ISQ::ElectricCurrentValue", "ISQ::ThermodynamicTemperatureValue",
    "ISQ::AmountOfSubstanceValue", "ISQ::LuminousIntensityValue",
    "ISQ::AngleValue", "ISQ::SolidAngleValue", "ISQ::InformationValue",
    # Common derived quantities
    "ISQ::Area", "ISQ::Volume", "ISQ::Velocity", "ISQ::Acceleration",
    "ISQ::Force", "ISQ::Pressure", "ISQ::Energy", "ISQ::Power",
    "ISQ::ElectricCharge", "ISQ::Voltage", "ISQ::Capacitance",
    "ISQ::Resistance", "ISQ::Conductance", "ISQ::MagneticFlux",
    "ISQ::MagneticFluxDensity", "ISQ::Inductance", "ISQ::Frequency",
    "ISQ::AreaValue", "ISQ::VolumeValue", "ISQ::VelocityValue",
    "ISQ::AccelerationValue", "ISQ::ForceValue", "ISQ::PressureValue",
    "ISQ::EnergyValue", "ISQ::PowerValue", "ISQ::ElectricChargeValue",
    "ISQ::VoltageValue", "ISQ::CapacitanceValue", "ISQ::ResistanceValue",
    "ISQ::ConductanceValue", "ISQ::MagneticFluxValue",
    "ISQ::MagneticFluxDensityValue", "ISQ::InductanceValue",
    "ISQ::FrequencyValue",
    # Base KerML/SysML types
    "KerML::Element", "KerML::Type", "KerML::Feature",
    "KerML::Namespace", "KerML::Relationship",
    "SysML::Occurrence", "SysML::Item", "SysML::Part",
    "SysML::Port", "SysML::Action", "SysML::State",
    "SysML::Requirement", "SysML::Connection",
    "SysML::Flow", "SysML::Interface",
    "SysML::Calculation", "SysML::Constraint",
    "SysML::Enumeration", "SysML::Case",
    "SysML::UseCase", "SysML::AnalysisCase",
    "SysML::VerificationCase", "SysML::View",
    "SysML::Viewpoint", "SysML::Concern",
    "SysML::Allocation", "SysML::Metadata",
    "SysML::Rendering", "SysML::Individual",
})


# ---------------------------------------------------------------------------
# Symbol Table
# ---------------------------------------------------------------------------

class SymbolTable:
    """Hierarchical symbol table for a parsed SysML model.

    Each scope maps simple names to model elements.  Parent scopes are
    consulted when a name is not found locally.  Imported symbols are
    merged into the scope based on import rules.
    """

    def __init__(self) -> None:
        self._symbols: dict[str, Any] = {}
        self._children: dict[str, SymbolTable] = {}
        self._parent: Optional[SymbolTable] = None
        self._imports: list[Any] = []  # Import grammar objects
        self._imported_symbols: dict[str, Any] = {}  # Resolved imported symbols
        self._import_visibility: dict[str, str] = {}  # symbol_name -> "private"|"public"|"protected"
        self._definition_features: dict[str, dict[str, Any]] = {}  # definition_name -> {element, features, supertypes}
        self._duplicate_names: list[tuple[str, Any]] = []  # (name, element) for duplicates

    def __repr__(self) -> str:
        return (f"SymbolTable(symbols={len(self._symbols)}, "
                f"children={len(self._children)})")

    # -- public API ----------------------------------------------------------

    def register(self, name: str, element: Any) -> None:
        """Register *element* under *name* in this scope.

        If *name* is already registered, the duplicate is tracked in
        ``_duplicate_names`` but the original symbol is kept.
        """
        if name in self._symbols:
            self._duplicate_names.append((name, element))
        else:
            self._symbols[name] = element

    def lookup(self, name: str, from_child: bool = False) -> Optional[Any]:
        """Look up *name*, walking up parent scopes if not found locally.

        Parameters
        ----------
        name : str
            The symbol name to look up.
        from_child : bool
            If True, the lookup is coming from a child scope. This affects
            visibility: private imports are not visible to children.
        """
        if name in self._symbols:
            return self._symbols[name]
        if name in self._imported_symbols:
            visibility = self._import_visibility.get(name, "private")
            # Private imports are not visible from child scopes
            if visibility == "private" and from_child:
                return None
            return self._imported_symbols[name]
        if self._parent is not None:
            return self._parent.lookup(name, from_child=True)
        return None

    def build_from_model(self, model: Any, lib_roots: list[Path] | None = None) -> None:
        """Walk the model tree and populate the symbol table."""
        self._walk_element(model, self)
        self._resolve_imports(self, lib_roots)
        self._propagate_public_imports(self)

    # -- internals -----------------------------------------------------------

    def _walk_element(self, element: Any, table: SymbolTable) -> None:
        if element is None:
            return

        name = getattr(element, "name", None)
        # Skip Model's UUID name (not a real SysML symbol)
        if name is not None and type(element).__name__ != "Model":
            table.register(name, element)

        # Track definitions and their features/supertypes for inheritance resolution
        elem_type = type(element).__name__
        if getattr(element, "is_definition", False) and name is not None:
            self._index_definition(element, name, table)

        # Create child scope for packages and definitions
        # Skip Model (it's just a root container, not a SysML namespace)
        child_table = table
        is_container = getattr(element, "is_definition", False) or elem_type == "Package"
        if is_container and name is not None and elem_type != "Model":
            child_table = table._children.setdefault(name, SymbolTable())
            child_table._parent = table

        # Collect imports from package grammar body
        if elem_type == "Package":
            self._collect_imports(element, child_table)

        # Walk children
        for child in getattr(element, "children", []):
            self._walk_element(child, child_table)

    def _collect_imports(self, package: Any, table: SymbolTable) -> None:
        """Collect Import objects from a package's grammar body."""
        grammar = getattr(package, "grammar", None)
        if grammar is None:
            return
        body = getattr(grammar, "body", None)
        if body is None:
            return
        for child in getattr(body, "children", []):
            child_type = type(child).__name__
            if child_type == "Import":
                table._imports.append(child)

    def _resolve_imports(self, table: SymbolTable, lib_roots: list[Path] | None = None) -> None:
        """Resolve all imports for this scope and its children."""
        for imp in table._imports:
            self._resolve_single_import(imp, table, lib_roots)

        # Recurse into children
        for child_table in table._children.values():
            self._resolve_imports(child_table, lib_roots)

    def _propagate_public_imports(self, table: SymbolTable) -> None:
        """Propagate public and protected imports through the namespace hierarchy.

        - public imports: visible to children AND siblings (re-exported)
        - protected imports: visible to children only
        - private imports: not visible outside the importing namespace
        """
        # First, propagate public imports to siblings
        children = list(table._children.values())
        for i, child_table in enumerate(children):
            # Collect all public imports from siblings
            for other_child in children:
                if other_child is child_table:
                    continue
                for sym_name, element in other_child._imported_symbols.items():
                    visibility = other_child._import_visibility.get(sym_name, "private")
                    if visibility == "public":
                        if sym_name not in child_table._imported_symbols:
                            child_table._imported_symbols[sym_name] = element
                            child_table._import_visibility[sym_name] = "public"

        # Then, propagate public and protected imports from parent to children
        for child_name, child_table in table._children.items():
            for sym_name, element in table._imported_symbols.items():
                visibility = table._import_visibility.get(sym_name, "private")

                if visibility == "public":
                    # Public: visible to children and re-exported
                    if sym_name not in child_table._imported_symbols:
                        child_table._imported_symbols[sym_name] = element
                        child_table._import_visibility[sym_name] = "public"
                elif visibility == "protected":
                    # Protected: visible to children but not re-exported
                    if sym_name not in child_table._imported_symbols:
                        child_table._imported_symbols[sym_name] = element
                        child_table._import_visibility[sym_name] = "protected"

            # Recurse into children
            self._propagate_public_imports(child_table)

    def _resolve_single_import(self, imp: Any, table: SymbolTable, lib_roots: list[Path] | None = None) -> None:
        """Resolve a single Import object into the symbol table."""
        if not imp.children:
            return

        # Extract visibility from the import prefix
        visibility = self._extract_import_visibility(imp)

        import_child = imp.children[0]
        child_type = type(import_child).__name__

        if child_type == "MembershipImport":
            self._resolve_membership_import(import_child, table, visibility, lib_roots)
        elif child_type == "NamespaceImport":
            self._resolve_namespace_import(import_child, table, visibility, lib_roots)

    def _extract_import_visibility(self, imp: Any) -> str:
        """Extract visibility keyword from an Import object.

        Returns 'private', 'public', 'protected', or 'private' (default).
        """
        if not imp.children:
            return "private"

        # The prefix is on the child (MembershipImport or NamespaceImport)
        import_child = imp.children[0]
        prefix = getattr(import_child, "prefix", None)
        if prefix is None:
            return "private"

        vis = getattr(prefix, "visibility", None)
        if vis is None:
            return "private"

        keyword = getattr(vis, "keyword", "")
        if keyword == "public ":
            return "public"
        elif keyword == "protected ":
            return "protected"
        else:
            return "private"

    def _resolve_membership_import(self, mem_import: Any, table: SymbolTable, visibility: str, lib_roots: list[Path] | None = None) -> None:
        """Resolve a MembershipImport (import specific element)."""
        imported_mem = getattr(mem_import, "membership", None)
        if imported_mem is None:
            return

        qn = getattr(imported_mem, "name", None)
        if qn is None:
            return

        names = getattr(qn, "names", [])
        if not names:
            return

        ref_str = "::".join(names)
        element = self._resolve_qualified_name(ref_str, table)
        if element is not None:
            # Use the simple name (last part) as the imported name
            simple_name = names[-1]
            table._imported_symbols[simple_name] = element
            table._import_visibility[simple_name] = visibility
        else:
            # Fall back to LibrarySymbolIndex for library symbols
            if ref_str in LibrarySymbolIndex.get_symbols(lib_roots):
                simple_name = names[-1]
                table._imported_symbols[simple_name] = ref_str
                table._import_visibility[simple_name] = visibility

    def _resolve_namespace_import(self, ns_import: Any, table: SymbolTable, visibility: str, lib_roots: list[Path] | None = None) -> None:
        """Resolve a NamespaceImport (import all from namespace)."""
        imported_ns = getattr(ns_import, "namespace", None)
        if imported_ns is None:
            return

        qn = getattr(imported_ns, "namespaces", None)
        if qn is None:
            return

        names = getattr(qn, "names", [])
        if not names:
            return

        is_recursive = getattr(imported_ns, "isRecursive", False)

        # Find the target namespace table
        ref_str = "::".join(names)
        target_table = self._find_namespace_table(ref_str, table)
        if target_table is not None:
            for sym_name, element in target_table._symbols.items():
                table._imported_symbols[sym_name] = element
                table._import_visibility[sym_name] = visibility

            for sym_name, element in target_table._imported_symbols.items():
                vis = target_table._import_visibility.get(sym_name, "private")
                if vis == "public" and sym_name not in table._imported_symbols:
                    table._imported_symbols[sym_name] = element
                    table._import_visibility[sym_name] = visibility

            # If recursive, also import from all child namespaces
            if is_recursive:
                self._recursive_import(target_table, table, visibility)
        else:
            # Fall back to LibrarySymbolIndex for library namespaces
            prefix = ref_str + "::"
            lib_symbols = LibrarySymbolIndex.get_symbols(lib_roots)
            for sym in lib_symbols:
                if sym.startswith(prefix):
                    simple_name = sym[len(prefix):]
                    # Only import direct children (no nested :: in the remainder)
                    if "::" not in simple_name:
                        table._imported_symbols[simple_name] = sym
                        table._import_visibility[simple_name] = visibility
                    elif is_recursive:
                        # For recursive imports, also import deeply nested symbols
                        # Use the next-level name as the imported name
                        next_name = simple_name.split("::")[0]
                        if next_name not in table._imported_symbols:
                            table._imported_symbols[next_name] = sym
                            table._import_visibility[next_name] = visibility

    def _recursive_import(self, source_table: SymbolTable, dest_table: SymbolTable, visibility: str) -> None:
        """Recursively import symbols from all child namespaces."""
        for child_name, child_table in source_table._children.items():
            for sym_name, element in child_table._symbols.items():
                if sym_name not in dest_table._imported_symbols:
                    dest_table._imported_symbols[sym_name] = element
                    dest_table._import_visibility[sym_name] = visibility
            for sym_name, element in child_table._imported_symbols.items():
                vis = child_table._import_visibility.get(sym_name, "private")
                if vis == "public" and sym_name not in dest_table._imported_symbols:
                    dest_table._imported_symbols[sym_name] = element
                    dest_table._import_visibility[sym_name] = visibility
            self._recursive_import(child_table, dest_table, visibility)

    def _resolve_qualified_name(self, ref_str: str, table: SymbolTable) -> Optional[Any]:
        """Resolve a qualified name reference from the given scope."""
        # Direct lookup
        if "::" not in ref_str:
            return table.lookup(ref_str)

        parts = ref_str.split("::")
        lookup_table = table
        last_found = None
        all_found = True
        for i, part in enumerate(parts):
            found = lookup_table.lookup(part)
            if found is None:
                all_found = False
                break
            if part in lookup_table._imported_symbols:
                vis = lookup_table._import_visibility.get(part, "private")
                if vis != "public":
                    all_found = False
                    break
            last_found = found
            child_scope = lookup_table._children.get(part)
            if child_scope is None:
                owner = lookup_table._find_symbol_owner(part)
                if owner is not None:
                    child_scope = owner._children.get(part)
            if child_scope is not None:
                lookup_table = child_scope
            elif i < len(parts) - 1:
                all_found = False
                break

        if all_found:
            return last_found

        # Fall back to simple name lookup
        return table.lookup(parts[-1])

    def _find_namespace_table(self, ref_str: str, from_table: SymbolTable) -> Optional[SymbolTable]:
        """Find the symbol table for a namespace path."""
        if "::" not in ref_str:
            # Simple name - try direct child first, then via parent lookup
            child = from_table._children.get(ref_str)
            if child is not None:
                return child
            # Try finding via parent chain
            owner = from_table._find_symbol_owner(ref_str)
            if owner is not None:
                return owner._children.get(ref_str)
            return None

        parts = ref_str.split("::")
        lookup_table = from_table
        for part in parts:
            child = lookup_table._children.get(part)
            if child is not None:
                lookup_table = child
            else:
                # Try from parent chain
                owner = lookup_table._find_symbol_owner(part)
                if owner is not None:
                    child = owner._children.get(part)
                    if child is not None:
                        lookup_table = child
                    else:
                        return None
                else:
                    return None
        return lookup_table

    def _find_symbol_owner(self, name: str) -> Optional[SymbolTable]:
        """Find the symbol table that directly contains *name* as a symbol."""
        if name in self._symbols:
            return self
        if name in self._imported_symbols:
            return self
        if self._parent is not None:
            return self._parent._find_symbol_owner(name)
        return None

    def _index_definition(self, element: Any, name: str, table: SymbolTable) -> None:
        """Index a definition's features and supertypes for inheritance resolution."""
        grammar = getattr(element, "grammar", None)
        if grammar is None:
            return

        # Extract supertype names from grammar
        supertypes = self._extract_supertypes(grammar)

        # Extract feature names defined directly in this definition
        features = self._extract_features(grammar)

        self._definition_features[name] = {
            "element": element,
            "features": features,
            "supertypes": supertypes,
            "scope": table,
        }

    def _extract_supertypes(self, grammar: Any) -> list[str]:
        """Extract supertype names from a definition's grammar."""
        supertypes = []

        # Navigate to subclassificationpart
        definition = getattr(grammar, "definition", None)
        if definition is None:
            return supertypes

        declaration = getattr(definition, "declaration", None)
        if declaration is None:
            return supertypes

        scp = getattr(declaration, "subclassificationpart", None)
        if scp is None:
            return supertypes

        for child in getattr(scp, "children", []):
            name_obj = getattr(child, "name", None)
            if name_obj is not None:
                names = getattr(name_obj, "names", [])
                if names:
                    supertypes.append(names[-1])  # Use simple name

        return supertypes

    def _extract_features(self, grammar: Any) -> set[str]:
        """Extract feature names defined directly in a definition's grammar."""
        features = set()

        definition = getattr(grammar, "definition", None)
        if definition is None:
            return features

        body = getattr(definition, "body", None)
        if body is None:
            return features

        for body_item in getattr(body, "children", []):
            for member in getattr(body_item, "children", []):
                for usage_elem in getattr(member, "children", []):
                    struct_elem = getattr(usage_elem, "children", None)
                    if struct_elem is None:
                        continue
                    # struct_elem can be either:
                    # 1. A Usage subclass directly (e.g., AttributeUsage)
                    # 2. A StructureUsageElement wrapper containing a Usage
                    feat_name = self._get_feature_name(struct_elem)
                    if feat_name:
                        features.add(feat_name)

        return features

    def _get_feature_name(self, usage: Any) -> Optional[str]:
        """Extract the declared name from a Usage object or wrapper."""
        try:
            # Case 1: Direct Usage subclass (e.g., AttributeUsage, PartUsage)
            # These have a 'usage' attribute
            usage_attr = getattr(usage, "usage", None)
            if usage_attr is not None:
                decl = getattr(usage_attr, "declaration", None)
                if decl is None:
                    return getattr(usage, "name", None)
                inner_decl = getattr(decl, "declaration", None)
                if inner_decl is None:
                    return None
                ident = getattr(inner_decl, "identification", None)
                if ident is None:
                    return None
                return getattr(ident, "declaredName", None)

            # Case 2: Wrapper with children containing Usage
            children = getattr(usage, "children", None)
            if children is not None:
                return self._get_feature_name(children)

            return getattr(usage, "name", None)
        except AttributeError:
            return None

    def resolve_inherited_feature(self, feature_name: str, defining_type: str, visited: Optional[set] = None) -> Optional[Any]:
        """Resolve a feature name by walking the supertype chain of *defining_type*.

        Returns the element that defines the feature, or None if not found.
        """
        if visited is None:
            visited = set()

        if defining_type in visited:
            return None
        visited.add(defining_type)

        if defining_type not in self._definition_features:
            return None

        def_info = self._definition_features[defining_type]

        # Check if feature is directly defined in this type
        if feature_name in def_info["features"]:
            return def_info["element"]

        # Recursively check supertypes
        for supertype in def_info["supertypes"]:
            result = self.resolve_inherited_feature(feature_name, supertype, visited)
            if result is not None:
                return result

        return None

    def find_defining_type_for_feature(self, feature_name: str, context_type: str) -> Optional[str]:
        """Find which type in the inheritance chain defines *feature_name*.

        Returns the type name that defines the feature, or None.
        """
        if context_type not in self._definition_features:
            return None

        def_info = self._definition_features[context_type]

        if feature_name in def_info["features"]:
            return context_type

        for supertype in def_info["supertypes"]:
            result = self.find_defining_type_for_feature(feature_name, supertype)
            if result is not None:
                return result

        return None


# ---------------------------------------------------------------------------
# Reference Collector
# ---------------------------------------------------------------------------

class ReferenceCollector:
    """Collect all qualified-name references from a model's grammar tree.

    Returns list of ``(qualified_name_str, element, scope_path, kind)`` tuples
    where ``scope_path`` is the list of scope names from root to the element
    and ``kind`` is the reference relationship: ``"typing"``, ``"subsetting"``,
    ``"redefinition"``, or ``"subclassification"``.  The kind lets the
    feature-chain check (v0.60.0) tell genuine feature chains (subsetting /
    redefinition) apart from *type* references (typings / subclassification),
    which are namespace paths and must not be chain-checked.
    """

    def collect(self, model: Any) -> list[tuple[str, Any, list[str], str]]:
        results: list[tuple[str, Any, list[str], str]] = []
        self._walk(model, results, [])
        return results

    def _walk(self, element: Any, results: list[tuple[str, Any, list[str], str]], scope_path: list[str]) -> None:
        if element is None:
            return

        # Compute child scope path
        name = getattr(element, "name", None)
        elem_type = type(element).__name__
        is_container = getattr(element, "is_definition", False) or elem_type == "Package"
        child_scope = scope_path
        if is_container and name is not None and elem_type != "Model":
            child_scope = scope_path + [name]

        grammar = getattr(element, "grammar", None)
        if grammar is not None:
            self._extract_from_grammar(grammar, element, results, scope_path)

        for child in getattr(element, "children", []):
            self._walk(child, results, child_scope)

    def _extract_from_grammar(
        self, grammar: Any, element: Any, results: list[tuple[str, Any, list[str], str]], scope_path: list[str]
    ) -> None:
        usage = getattr(grammar, "usage", None)
        if usage is None:
            usage = grammar

        if usage is None:
            return

        decl = getattr(usage, "declaration", None)
        if decl is None:
            return

        inner_decl = getattr(decl, "declaration", None)
        if inner_decl is None:
            return

        spec = getattr(inner_decl, "specialization", None)
        if spec is None:
            return

        self._collect_specialization_part(spec, element, results, scope_path)

    def _collect_specialization_part(
        self, spec: Any, element: Any, results: list[tuple[str, Any, list[str], str]], scope_path: list[str]
    ) -> None:
        if spec is None:
            return

        for fs in getattr(spec, "specializations", []):
            self._collect_feature_specialization(fs, element, results, scope_path)

        for fs in getattr(spec, "specializations2", []):
            self._collect_feature_specialization(fs, element, results, scope_path)

    def _collect_feature_specialization(
        self, fs: Any, element: Any, results: list[tuple[str, Any, list[str], str]], scope_path: list[str]
    ) -> None:
        if fs is None:
            return

        rel = getattr(fs, "relationship", None)
        if rel is None:
            return

        rel_type = type(rel).__name__

        if rel_type == "Typings":
            self._collect_typings(rel, element, results, scope_path, "typing")
        elif rel_type == "Subsettings":
            self._collect_subsettings(rel, element, results, scope_path)
        elif rel_type == "Redefinitions":
            self._collect_redefinitions(rel, element, results, scope_path)
        elif rel_type == "SubclassificationPart":
            self._collect_subclassification(rel, element, results, scope_path)

    def _collect_typings(
        self, typings: Any, element: Any, results: list[tuple[str, Any, list[str], str]], scope_path: list[str],
        kind: str = "typing",
    ) -> None:
        tb = getattr(typings, "typing", None)
        if tb is not None:
            for ft in getattr(tb, "relationships", []):
                self._collect_feature_typing(ft, element, results, scope_path, kind)

        for ft in getattr(typings, "relationships", []):
            self._collect_feature_typing(ft, element, results, scope_path, kind)

    def _collect_feature_typing(
        self, ft: Any, element: Any, results: list[tuple[str, Any, list[str], str]], scope_path: list[str],
        kind: str = "typing",
    ) -> None:
        if ft is None:
            return

        rel = getattr(ft, "relationship", None)
        if rel is None:
            return

        rel_type = type(rel).__name__

        if rel_type == "OwnedFeatureTyping":
            ftype = getattr(rel, "type", None)
            if ftype is not None:
                qn = getattr(ftype, "type", None)
                if qn is not None:
                    names = getattr(qn, "names", [])
                    if names:
                        results.append(("::".join(names), element, scope_path, kind))

        elif rel_type == "ConjugatedPortTyping":
            qn = getattr(rel, "name", None)
            if qn is not None:
                names = getattr(qn, "names", [])
                if names:
                    results.append(("::".join(names), element, scope_path, kind))

    def _collect_subsettings(
        self, sub: Any, element: Any, results: list[tuple[str, Any, list[str], str]], scope_path: list[str]
    ) -> None:
        for child in getattr(sub, "children", []):
            segments = _chain_segments(child)
            if segments:
                # Namespace qualification joins with '::', feature chains
                # with '.' (e.g. base.x).
                # Namespace qualification stays inside a segment ('A::B');
                # feature-chain segments join with '.'.
                results.append((".".join(segments), element, scope_path, "subsetting"))

    def _collect_redefinitions(
        self, red: Any, element: Any, results: list[tuple[str, Any, list[str], str]], scope_path: list[str]
    ) -> None:
        for child in getattr(red, "children", []):
            segments = _chain_segments(child)
            if segments:
                # Namespace qualification stays inside a segment ('A::B');
                # feature-chain segments join with '.'.
                results.append((".".join(segments), element, scope_path, "redefinition"))

    def _collect_subclassification(
        self, sc: Any, element: Any, results: list[tuple[str, Any, list[str], str]], scope_path: list[str]
    ) -> None:
        for child in getattr(sc, "children", []):
            for el in getattr(child, "elements", []):
                names = getattr(el, "names", [])
                if names:
                    results.append(("::".join(names), element, scope_path, "subclassification"))



def _chain_segments(child: Any) -> list[str]:
    """Reference segments of an Owned*Subsetting/Redefinition child, in order.

    Each returned string is one feature-chain segment: a QualifiedName keeps
    its internal ``::`` namespace qualification (``A::B``), while dotted
    chain steps become separate segments (``:> base.x`` -> ``['base','x']``).
    """
    segments: list[str] = []
    qn = getattr(child, "redefinedFeature", None) or getattr(
        child, "referencedFeature", None
    ) or getattr(child, "subsettedFeature", None)
    if qn is not None:
        names = getattr(qn, "names", [])
        if names:
            segments.append("::".join(names))
    for el in getattr(child, "elements", []) or []:
        if hasattr(el, "names") and getattr(el, "names", []):
            # Bare QualifiedName element (OwnedSubsetting single form)
            segments.append("::".join(el.names))
        elif hasattr(el, "feature"):
            for seg in getattr(el.feature, "children", []) or []:
                cf = getattr(seg, "chainingFeature", None)
                if cf is not None:
                    names = getattr(cf, "names", [])
                    if names:
                        segments.append("::".join(names))
    return segments


# ---------------------------------------------------------------------------
# Expression Identifier Collection (v0.54.0 — Phase B)
# ---------------------------------------------------------------------------

# Grammar element names that own an expression body but should NOT be
# traversed as expression-identifier sources themselves.  The collector
# walks a model's public-API tree and pulls expressions out of each
# element's *own* grammar (get_definition()), so nested usages inside a
# definition body are reached via the tree walk, not by descending into
# a definition's full grammar dict (which would duplicate identifiers).
_EXPRESSION_OWNER_TYPES = frozenset({
    "Constraint",      # constraint / assert constraint bodies
    "Calculation",     # calc bodies (result expressions, return members)
    "Action",          # action bodies with value expressions
    "State",           # guard expressions on transitions
    "Attribute",       # default value expressions (`= expr`)
    "Item",            # default value expressions
    "Port",            # default value expressions
    "Reference",       # default value expressions
    "Requirement",     # requirement constraint bodies
})


def _walk_expression_identifiers(expr_dict: Any) -> list[str]:
    """Recursively extract identifier reference strings from an expression dict.

    Walks the structured per-precedence expression AST emitted by the
    v0.52.0 visitor (``ConditionalExpression`` → ``NullCoalescingExpression``
    → ``ImpliesExpression`` → ``OrExpression`` → ``XorExpression`` →
    ``AndExpression`` → ``EqualityExpression`` → ``ClassificationExpression``
    → ``RelationalExpression`` → ``RangeExpression`` → ``AdditiveExpression``
    → ``MultiplicativeExpression`` → ``ExponentiationExpression`` →
    ``UnaryExpression`` → ``ExtentExpression`` → ``PrimaryExpression``).

    Identifier sources:
    - ``FeatureReferenceExpression`` members → the target QualifiedName
    - ``PrimaryExpression.ownedRelationship1/2`` chains → ``base.step1.step2``
    - ``InvocationExpression`` → the invoked feature name plus nested
      argument expressions
    - ``FeatureChainMember.ownedRelatedElement`` (OwnedFeatureChain)
      → chained feature path

    Returns fully-qualified reference strings, e.g. ``"wheel1.mass"``,
    ``"ScalarValues::Real"``, ``"size"``.
    """
    names: list[str] = []

    def visit(node: Any, owner_base: Optional[list[str]] = None) -> None:
        if isinstance(node, dict):
            node_name = node.get("name")

            if node_name == "FeatureReferenceMember":
                me = node.get("memberElement")
                if isinstance(me, dict):
                    qn = me.get("names", [])
                    if qn:
                        names.append("::".join(str(n) for n in qn))
                return  # memberElement already visited as QualifiedName? no — leaf

            if node_name == "InvocationExpression":
                # The invoked feature is captured in ownedRelationship →
                # OwnedFeatureTyping → FeatureType → QualifiedName
                rel = node.get("ownedRelationship")
                target = None
                if isinstance(rel, dict):
                    ft = rel.get("type")
                    if isinstance(ft, dict):
                        ft_qn = ft.get("type")
                        if isinstance(ft_qn, dict):
                            qn = ft_qn.get("names", [])
                            if qn:
                                target = "::".join(str(n) for n in qn)
                if target:
                    names.append(target)
                # Arguments
                arg_list = node.get("arg_list")
                if isinstance(arg_list, dict):
                    visit(arg_list)
                return

            if node_name == "FeatureChainMember" and owner_base is not None:
                me = node.get("memberElement")
                if isinstance(me, dict):
                    qn = me.get("names", [])
                    if qn:
                        names.append(
                            ".".join(
                                ["::".join(str(n) for n in owner_base)]
                                + [str(x) for x in qn]
                            )
                        )
                    return
                ore = node.get("ownedRelatedElement")
                if isinstance(ore, dict) and ore.get("name") == "OwnedFeatureChain":
                    steps: list[str] = []
                    feature = ore.get("feature")
                    if isinstance(feature, dict):
                        for seg in feature.get("ownedRelationship", []):
                            if isinstance(seg, dict):
                                cf = seg.get("chainingFeature")
                                if isinstance(cf, dict):
                                    seg_qn = cf.get("names", [])
                                    if seg_qn:
                                        steps.append("::".join(str(n) for n in seg_qn))
                    if steps:
                        names.append(
                            ".".join(["::".join(str(n) for n in owner_base)] + steps)
                        )
                return

            # PrimaryExpression combines a base reference with chain steps
            if node_name == "PrimaryExpression":
                base = node.get("base")
                base_names: list[str] = []
                if isinstance(base, dict):
                    base_rel = base.get("ownedRelationship")
                    if isinstance(base_rel, dict) and base_rel.get("name") == "FeatureReferenceExpression":
                        members = base_rel.get("ownedRelationship", [])
                        if members and isinstance(members[0], dict):
                            me = members[0].get("memberElement")
                            if isinstance(me, dict):
                                base_names = [str(n) for n in me.get("names", [])]
                # ownedRelationship1/2 are the chain steps after the base
                for chains in (node.get("ownedRelationship1"), node.get("ownedRelationship2")):
                    if not isinstance(chains, list):
                        continue
                    for chain in chains:
                        me = chain.get("memberElement") if isinstance(chain, dict) else None
                        if owner_base is not None or base_names:
                            head = owner_base if owner_base is not None else base_names
                            if isinstance(me, dict):
                                qn = me.get("names", [])
                                if qn:
                                    names.append(
                                        ".".join(["::".join(head)] + [str(x) for x in qn])
                                    )
                                    continue
                            ore = chain.get("ownedRelatedElement") if isinstance(chain, dict) else None
                            if isinstance(ore, dict) and ore.get("name") == "OwnedFeatureChain":
                                steps = []
                                feature = ore.get("feature")
                                if isinstance(feature, dict):
                                    for seg in feature.get("ownedRelationship", []):
                                        if isinstance(seg, dict):
                                            cf = seg.get("chainingFeature")
                                            if isinstance(cf, dict):
                                                seg_qn = cf.get("names", [])
                                                if seg_qn:
                                                    steps.append("::".join(str(n) for n in seg_qn))
                                if steps:
                                    names.append(
                                        ".".join(["::".join(head)] + steps)
                                    )
                # Recurse into base (handles qualified names + literals)
                if isinstance(base, dict):
                    visit(base)
                # Nested expressions in operand slots (postfix ops etc.)
                for operand in node.get("operand", []) or []:
                    visit(operand)
                for op in node.get("operator", []) or []:
                    visit(op) if isinstance(op, (dict, list)) else None
                return

            # Generic recursion into child dicts/lists, passing chain context
            # into FeatureChainMember nodes that hang off a PrimaryExpression.
            for key, value in node.items():
                if key in ("ownedRelationship1", "ownedRelationship2") and node_name == "PrimaryExpression":
                    continue  # handled above
                if isinstance(value, (dict, list)):
                    visit(value, owner_base)

        elif isinstance(node, list):
            for item in node:
                visit(item, owner_base)

    visit(expr_dict)
    return names


class ExpressionIdentifierCollector:
    """Collect identifiers referenced inside expression bodies.

    Walks the public-API model tree; for every element whose grammar owns
    an expression body (constraints, calc results, attribute defaults,
    guards, invocation arguments), extracts identifier references via
    :func:`_walk_expression_identifiers`.

    Returns ``(qualified_ref, element, scope_path)`` tuples matching the
    ReferenceCollector contract.
    """

    def collect(self, model: Any) -> list[tuple[str, Any, list[str]]]:
        results: list[tuple[str, Any, list[str]]] = []
        self._walk(model, results, [])
        return results

    def _walk(self, element: Any, results: list, scope_path: list[str]) -> None:
        if element is None:
            return

        name = getattr(element, "name", None)
        elem_type = type(element).__name__
        is_container = getattr(element, "is_definition", False) or elem_type == "Package"
        child_scope = scope_path
        if is_container and name is not None and elem_type != "Model":
            child_scope = scope_path + [name]

        grammar = getattr(element, "grammar", None)
        if grammar is not None and elem_type in _EXPRESSION_OWNER_TYPES:
            try:
                grammar_def = grammar.get_definition()
            except Exception:
                grammar_def = None
            if grammar_def is not None:
                for expr in _find_owned_expressions(grammar_def):
                    for ref in _walk_expression_identifiers(expr):
                        results.append((ref, element, scope_path))

        for child in getattr(element, "children", []):
            self._walk(child, results, child_scope)


def _satisfy_by_ref(satisfy_dict: dict):
    """The ``by <part>`` reference of a SatisfyRequirementUsage dict.

    Shape: ``ssm`` = SatisfactionSubjectMember → SatisfactionParameter
    → … → FeatureChainMember.memberElement (QualifiedName) whose last
    segment is the satisfying feature.  ``ors.referencedFeature.names``
    carries the target requirement reference.
    """
    ssm = satisfy_dict.get("ssm")
    if not isinstance(ssm, dict):
        return None
    members = _find_named_dicts(ssm, "FeatureChainMember")
    for m in members:
        me = m.get("memberElement") or {}
        names = me.get("names")
        if isinstance(names, list) and names:
            return "::".join(str(n) for n in names)
    return None


def _find_named_dicts(node: Any, name: str) -> list:
    """Locate every dict with ``dict["name"] == name`` in a tree."""
    out: list = []

    def walk(n: Any) -> None:
        if isinstance(n, dict):
            if n.get("name") == name:
                out.append(n)
            for v in n.values():
                if isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(n, list):
            for item in n:
                if isinstance(item, (dict, list)):
                    walk(item)

    walk(node)
    return out


def _as_list_dicts(v: Any) -> list:
    """Normalize an optional-dict-or-list relationship field to a list."""
    if isinstance(v, list):
        return [x for x in v if isinstance(x, dict)]
    if isinstance(v, dict):
        return [v]
    return []


def _find_declared_name(d: dict):
    """Bounded search for ``identification.declaredName`` in a usage/
    definition dict (the identification nesting varies by shape)."""
    frontier = [d]
    for _ in range(4):
        nxt = []
        for n in frontier:
            if not isinstance(n, dict):
                continue
            ident = n.get("identification")
            if isinstance(ident, dict):
                name = ident.get("declaredName")
                if name:
                    return name
            for v in n.values():
                if isinstance(v, dict):
                    nxt.append(v)
                elif isinstance(v, list):
                    nxt.extend(x for x in v if isinstance(x, dict))
        frontier = nxt
    return None


def _port_direction(port_usage: dict):
    """The explicit direction keyword on a PortUsage dict, if any.

    The prefix chain is
    ``OccurrenceUsagePrefix → BasicUsagePrefix → RefPrefix.direction``
    where ``direction`` is ``{"in": ..., "out": ..., "inout": ...}`` —
    the present keyword is the non-empty string value.
    """
    pre = port_usage.get("prefix")
    while isinstance(pre, dict):
        d = pre.get("direction")
        if isinstance(d, dict):
            for k in ("in", "out", "inout"):
                v = d.get(k)
                if isinstance(v, str) and v.strip():
                    return k
            return None
        pre = pre.get("prefix")
    return None


def _connector_end_chain(end: dict) -> list:
    """Feature-chain segment names of a ConnectorEnd dict."""
    ors = end.get("ownedRelationship") if isinstance(end, dict) else None
    for rel in _as_list_dicts(ors):
        if rel.get("name") != "OwnedReferenceSubsetting":
            continue
        ofc_list = _as_list_dicts(rel.get("ownedRelatedElement"))
        ofc = ofc_list[0] if ofc_list else {}
        if ofc.get("name") != "OwnedFeatureChain":
            continue
        feat = ofc.get("feature") or {}
        names = []
        for chain_rel in _as_list_dicts(feat.get("ownedRelationship")):
            if chain_rel.get("name") != "OwnedFeatureChaining":
                continue
            cf = chain_rel.get("chainingFeature") or {}
            qn = cf.get("names")
            if isinstance(qn, list) and qn:
                names.append(str(qn[-1]))
        return names
    return []


def _usage_typed_by(usage: dict):
    """The last segment of a usage dict's OwnedFeatureTyping, if any.

    The typing rides the declaration/specialization chain, which
    precedes the body in dict order, so a usage's own typing is found
    before any nested member's typing.
    """
    for rel in _find_named_dicts(usage, "OwnedFeatureTyping"):
        ft = rel.get("type") or {}
        qn = ft.get("type") if isinstance(ft, dict) else None
        if isinstance(qn, dict):
            names = qn.get("names")
            if isinstance(names, list) and names:
                return str(names[-1])
    return None


def _find_payload_parameters(node: Any) -> list:
    """Locate every ``PayloadParameter`` dict in a grammar tree."""
    out: list = []

    def walk(n: Any) -> None:
        if isinstance(n, dict):
            if n.get("name") == "PayloadParameter":
                out.append(n)
            for v in n.values():
                if isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(n, list):
            for item in n:
                if isinstance(item, (dict, list)):
                    walk(item)

    walk(node)
    return out


def _payload_reference(payload: Any) -> str | None:
    """The name a ``PayloadParameter`` refers to, if any.

    Bare ``accept Sig`` → the OwnedFeatureTyping QualifiedName.
    Guarded ``accept Sig when ...`` → ``identification.declaredName``
    (only when no typing is present — with both, the identification
    is a fresh declaration, not a reference).
    """
    if not isinstance(payload, dict):
        return None
    feature = payload.get("feature") or {}
    rels = feature.get("ownedRelationship")
    rel_list = rels if isinstance(rels, list) else         [rels] if isinstance(rels, dict) else []
    for rel in rel_list:
        t = ((rel.get("type") or {}).get("type") or {}) \
            if isinstance(rel, dict) else {}
        names = t.get("names")
        if isinstance(names, list) and names:
            return "::".join(str(n) for n in names)
    if rel_list:
        return None  # typed payload — identification is a declaration
    ident = payload.get("identification")
    if isinstance(ident, dict):
        name = ident.get("declaredName")
        if name:
            return str(name)
    return None


def _find_owned_expressions(node: Any) -> list[dict]:
    """Locate every ``OwnedExpression`` dict in a grammar definition tree."""
    out: list[dict] = []

    def walk(n: Any) -> None:
        if isinstance(n, dict):
            if n.get("name") == "OwnedExpression":
                out.append(n)
            for v in n.values():
                if isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(n, list):
            for item in n:
                if isinstance(item, (dict, list)):
                    walk(item)

    walk(node)
    return out


# ---------------------------------------------------------------------------
# Expression type checking & static evaluation (v0.55.0 — Phase C)
# ---------------------------------------------------------------------------

# Dimension-annotated *Value / *Unit definition names extracted from the
# bundled ISQ library docs (``quantity dimension: L^1*M^1*T^-2``).  Built
# once and cached at module level.
_DIMENSION_RE = re.compile(r"quantity\s+dimension:\s*(.+)$", re.MULTILINE)
_DEF_BLOCK_RE = re.compile(r"attribute def (\w+)\s*[^{]*\{")
_ALIAS_RE = re.compile(r"alias\s+(\w+)\s+for\s+(\w+);")

_dimension_index_cache: Optional[dict[str, str]] = None


def _build_dimension_index() -> dict[str, str]:
    """Map library *Value/*Unit definition names → dimension strings.

    Dimension strings look like ``L^1``, ``M^1``, ``1`` (dimensionless),
    or products ``L^1*M^1*T^-2``.
    """
    global _dimension_index_cache
    if _dimension_index_cache is not None:
        return _dimension_index_cache

    index: dict[str, str] = {}
    root = LibrarySymbolIndex._default_library_root()
    if root is None or not root.is_dir():
        _dimension_index_cache = {}
        return index

    for filepath in root.rglob("*.sysml"):
        try:
            src = filepath.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        file_dims: dict[str, str] = {}
        for m in _DEF_BLOCK_RE.finditer(src):
            start = m.end() - 1
            depth, i = 0, start
            while i < len(src) and i - start < 2000:
                if src[i] == "{":
                    depth += 1
                elif src[i] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                i += 1
            block = src[start:i]
            if len(block) > 1500:
                continue
            dm = _DIMENSION_RE.search(block)
            if dm:
                file_dims.setdefault(m.group(1), dm.group(1).strip())
        for name, dim in file_dims.items():
            index.setdefault(name, dim)
        # Aliases inherit the dimension of their target
        for m in _ALIAS_RE.finditer(src):
            target = m.group(2)
            if target in file_dims:
                index.setdefault(m.group(1), file_dims[target])

    _dimension_index_cache = index
    return index


def _parse_dimension(dim: Optional[str]) -> Optional[dict[str, int]]:
    """Parse ``L^1*M^1*T^-2`` → ``{'L': 1, 'M': 1, 'T': -2}``.

    Returns ``{}`` for dimensionless (``1``), None when unparseable.
    """
    if dim is None:
        return None
    dim = dim.strip().rstrip(".")
    if not dim:
        return None
    if dim == "1":
        return {}
    dims: dict[str, int] = {}
    for factor in dim.split("*"):
        factor = factor.strip()
        if not factor:
            continue
        if "^" in factor:
            base, exp = factor.split("^", 1)
            try:
                dims[base.strip()] = int(exp.strip())
            except ValueError:
                return None
        elif re.fullmatch(r"[A-Za-z]+", factor):
            dims[factor] = 1
        else:
            return None
    return dims


def _dims_mul(a: dict[str, int], b: dict[str, int]) -> dict[str, int]:
    """Multiply two dimension dicts (add exponents, drop zeros)."""
    out = dict(a)
    for k, v in b.items():
        out[k] = out.get(k, 0) + v
    return {k: v for k, v in out.items() if v != 0}


def _dims_div(a: dict[str, int], b: dict[str, int]) -> dict[str, int]:
    """Divide two dimension dicts (subtract exponents, drop zeros)."""
    out = dict(a)
    for k, v in b.items():
        out[k] = out.get(k, 0) - v
    return {k: v for k, v in out.items() if v != 0}


def _dimension_to_pint(dims: Optional[dict[str, int]]) -> Optional[Any]:
    """Map a SysML dimension dict to a pint dimensionality.

    Uses pint's base dimensions: L→length, M→mass, T→time,
    I→current, Θ→temperature, J→luminous intensity, N→substance.
    """
    if dims is None:
        return None
    try:
        import pint
    except ImportError:  # pragma: no cover
        return None
    base_map = {
        "L": "[length]",
        "M": "[mass]",
        "T": "[time]",
        "I": "[current]",
        "Θ": "[temperature]",
        "theta": "[temperature]",
        "J": "[luminosity]",
        "N": "[substance]",
    }
    try:
        result = None
        for base, exp in dims.items():
            unit = base_map.get(base)
            if unit is None:
                return None
            term = pint.Unit(unit) ** exp
            result = term if result is None else result * term
        return result if result is not None else pint.Unit("")
    except Exception:
        return None


def _numeric_types() -> frozenset[str]:
    """Simple names of numeric scalar types."""
    return frozenset({
        "Integer", "Natural", "Positive", "Nonnegative", "Negative", "Nonpositive",
        "Rational", "Real", "Number", "Complex", "UnlimitedNatural",
    })


def _string_types() -> frozenset[str]:
    return frozenset({"String"})


def _boolean_types() -> frozenset[str]:
    return frozenset({"Boolean"})


class _Operand:
    """Classification of one operand in a binary/unary expression."""

    __slots__ = ("kind", "type_name", "dimension", "literal_value", "literal_is_int")

    def __init__(
        self,
        kind: str,
        type_name: Optional[str] = None,
        dimension: Optional[dict[str, int]] = None,
        literal_value: Any = None,
        literal_is_int: bool = False,
    ) -> None:
        self.kind = kind  # "literal_int" | "literal_float" | "literal_string" |
                         # "literal_bool" | "typed" | "chain" | "invocation" | "unknown"
        self.type_name = type_name
        self.dimension = dimension
        self.literal_value = literal_value
        self.literal_is_int = literal_is_int

    @property
    def is_numeric_literal(self) -> bool:
        return self.kind in ("literal_int", "literal_float")

    @property
    def is_numeric(self) -> bool:
        if self.is_numeric_literal:
            return True
        if self.kind == "typed" and self.type_name in _numeric_types():
            return True
        if self.kind == "typed" and self.dimension is not None:
            # Quantity values are numeric
            return True
        return False

    @property
    def is_string(self) -> bool:
        return self.kind == "literal_string" or (
            self.kind == "typed" and self.type_name in _string_types()
        )

    @property
    def is_boolean(self) -> bool:
        return self.kind == "literal_bool" or (
            self.kind == "typed" and self.type_name in _boolean_types()
        )

    @property
    def is_ordered(self) -> bool:
        return self.is_numeric or self.is_string


class ExpressionTypeChecker:
    """Operand type compatibility and unit-dimension safety for expressions.

    Shares the identifier-extraction layer with Phase B but resolves each
    operand to a *category* (numeric / string / boolean / quantity /
    unknown) and validates operator combinations.
    """

    # operator -> rule key
    _ARITHMETIC = frozenset({"+", "-", "*", "/", "%", "**", "^"})
    _RELATIONAL = frozenset({"<", ">", "<=", ">="})
    _EQUALITY = frozenset({"==", "!=", "===", "!==", ":=", "=?", ":>=", ":>"})
    _LOGICAL = frozenset({"and", "or", "xor", "implies", "&", "|", "&&"})
    _RANGE = frozenset({".."})

    def __init__(
        self,
        analyzer: "SemanticAnalyzer",
        symtab: SymbolTable,
        lib_roots: list[Path] | None = None,
    ) -> None:
        self._analyzer = analyzer
        self._symtab = symtab
        self._lib_roots = lib_roots
        self._dimensions = _build_dimension_index()

    # -- public API ----------------------------------------------------------

    def check(self, model: Any) -> list[SemanticIssue]:
        """Run type-compatibility checks over all expression owners."""
        issues: list[SemanticIssue] = []
        self._walk_owners(model, issues, [], units_only=False)
        return issues

    def check_units(self, model: Any) -> list[SemanticIssue]:
        """Run unit-dimension checks only."""
        issues: list[SemanticIssue] = []
        self._walk_owners(model, issues, [], units_only=True)
        return issues

    # -- internals -----------------------------------------------------------

    def _walk_owners(
        self,
        element: Any,
        issues: list[SemanticIssue],
        scope_path: list[str],
        units_only: bool,
    ) -> None:
        if element is None:
            return
        name = getattr(element, "name", None)
        elem_type = type(element).__name__
        is_container = getattr(element, "is_definition", False) or elem_type == "Package"
        child_scope = scope_path
        if is_container and name is not None and elem_type != "Model":
            child_scope = scope_path + [name]

        if units_only and elem_type not in _UNIT_CHECK_OWNERS:
            pass
        elif (
            not units_only and elem_type in _EXPRESSION_OWNER_TYPES
        ) or (units_only and elem_type in _UNIT_CHECK_OWNERS):
            grammar = getattr(element, "grammar", None)
            if grammar is not None:
                try:
                    grammar_def = grammar.get_definition()
                except Exception:
                    grammar_def = None
                if grammar_def is not None:
                    for expr in _find_owned_expressions(grammar_def):
                        self._check_expression(
                            expr, element, scope_path, issues, units_only
                        )

        for child in getattr(element, "children", []):
            self._walk_owners(child, issues, child_scope, units_only)

    def _check_expression(
        self,
        expr_dict: dict,
        element: Any,
        scope_path: list[str],
        issues: list[SemanticIssue],
        units_only: bool,
    ) -> None:
        """Check one OwnedExpression dict against operator rules."""
        expr = expr_dict.get("expression")
        if not isinstance(expr, dict):
            return
        nce = self._first_operand(expr)
        if nce is None:
            return
        self._check_nce(nce, element, scope_path, issues, units_only)

    # -- layer navigation -----------------------------------------------

    def _first_operand(self, node: Any) -> Optional[dict]:
        """Return the top expression-layer dict (Conditional or NCE)."""
        if not isinstance(node, dict):
            return None
        return node

    def _check_nce(
        self,
        node: dict,
        element: Any,
        scope_path: list[str],
        issues: list[SemanticIssue],
        units_only: bool,
    ) -> None:
        """Walk NullCoalescing → Implies → Or → Xor → And → Equality → …."""
        if not isinstance(node, dict):
            return
        name = node.get("name")
        if name == "ConditionalExpression":
            for operand in node.get("operand", []) or []:
                self._check_nce(operand, element, scope_path, issues, units_only)
            return
        if name == "OwnedExpression":
            inner = node.get("expression")
            if isinstance(inner, dict):
                self._check_nce(inner, element, scope_path, issues, units_only)
            return
        if name == "NullCoalescingExpression":
            pairs = zip(node.get("operator", []), node.get("operand", []))
            for op, rhs in pairs:
                self._binary(op, node.get("implies"), rhs, element, scope_path, issues, units_only)
            implies = node.get("implies")
            if isinstance(implies, dict):
                self._check_level(implies, "implies", element, scope_path, issues, units_only)
        elif name == "ImpliesExpression":
            self._check_level(node, "implies", element, scope_path, issues, units_only)
        elif name == "OrExpression":
            self._check_level(node, "or", element, scope_path, issues, units_only)
        elif name == "XorExpression":
            self._check_level(node, "xor", element, scope_path, issues, units_only)
        elif name == "AndExpression":
            self._check_level(node, "and", element, scope_path, issues, units_only)
        elif name == "EqualityExpression":
            self._check_equality(node, element, scope_path, issues, units_only)
        elif name == "ClassificationExpression":
            rel = node.get("relational")
            if isinstance(rel, dict):
                self._check_relational(rel, element, scope_path, issues, units_only)
            # postfix ops (istype/hastype/@@/@) — operand type preserved
        elif name == "RangeExpression":
            self._check_range(node, element, scope_path, issues, units_only)
        elif name == "AdditiveExpression":
            self._check_additive(node, element, scope_path, issues, units_only)
        elif name == "MultiplicativeExpression":
            self._check_multiplicative(node, element, scope_path, issues, units_only)
        elif name == "ExponentiationExpression":
            self._check_exponentiation(node, element, scope_path, issues, units_only)
        elif name == "UnaryExpression":
            self._check_unary(node, element, scope_path, issues, units_only)
        elif name == "ExtentExpression":
            primary = node.get("primary")
            if isinstance(primary, dict):
                self._check_primary_postfix(primary, element, scope_path, issues, units_only)
        elif name == "PrimaryExpression":
            self._check_primary_postfix(node, element, scope_path, issues, units_only)

    def _check_level(
        self,
        node: dict,
        op_key: str,
        element: Any,
        scope_path: list[str],
        issues: list[SemanticIssue],
        units_only: bool,
    ) -> None:
        """Shared walker for implies/or/xor/and layers.

        Two shapes occur: keyword-chain layers keep ``operator``/``operand``
        lists (or/xor/implies), and the and layer keeps an ``operation``
        list of ``AndOperand`` dicts.  Both are checked here.
        """
        child_key = {"implies": "or", "or": "xor", "xor": "and", "and": "equality"}[op_key]
        child = node.get(child_key)
        if isinstance(child, dict):
            self._check_nce(child, element, scope_path, issues, units_only)
        if units_only:
            return
        # Form 1: operator/operand lists (or/xor/implies; and since v0.55)
        operator = node.get("operator", [])
        operands = node.get("operand", [])
        if operator and operands:
            lhs = child if isinstance(child, dict) else None
            for op, rhs in zip(operator, operands):
                self._check_logical_pair(op, lhs, rhs, element, scope_path, issues)
            for rhs in operands:
                if isinstance(rhs, dict):
                    self._check_nce(rhs, element, scope_path, issues, units_only)
        # Form 2: operation list of *Operand dicts (and: AndOperand; used when
        # the visitor emits the EqualityExpressionReference membership form)
        for op_dict in node.get("operation", []) or []:
            if not isinstance(op_dict, dict):
                continue
            op = op_dict.get("operator")
            rhs = op_dict.get("operand")
            if isinstance(rhs, dict) and rhs.get("name") == "EqualityExpressionReference":
                member = rhs.get("ownedRelationship")
                if isinstance(member, dict):
                    rhs = member.get("ownedRelatedElement")
            self._check_logical_pair(op, child, rhs, element, scope_path, issues)
            if isinstance(rhs, dict):
                self._check_nce(rhs, element, scope_path, issues, units_only)

    def _check_equality(
        self,
        node: dict,
        element: Any,
        scope_path: list[str],
        issues: list[SemanticIssue],
        units_only: bool,
    ) -> None:
        cls = node.get("classification")
        if isinstance(cls, dict):
            rel = cls.get("relational")
            if isinstance(rel, dict):
                self._check_relational(rel, element, scope_path, issues, units_only)
        if units_only:
            return
        operator = node.get("operation", [])
        lhs = cls if isinstance(cls, dict) else None
        for op_dict in operator:
            if not isinstance(op_dict, dict):
                continue
            op = op_dict.get("operator")
            rhs = op_dict.get("operand")
            if op in ("==", "!=", "===", "!=="):
                self._check_equality_pair(op, lhs, rhs, element, scope_path, issues)
            elif isinstance(rhs, dict):
                self._check_nce(rhs, element, scope_path, issues, units_only)

    def _check_relational(
        self,
        node: dict,
        element: Any,
        scope_path: list[str],
        issues: list[SemanticIssue],
        units_only: bool,
    ) -> None:
        rng = node.get("range")
        if isinstance(rng, dict):
            self._check_range(rng, element, scope_path, issues, units_only)
        if units_only:
            return
        for op_dict in node.get("operation", []):
            if not isinstance(op_dict, dict):
                continue
            op = op_dict.get("operator")
            rhs = op_dict.get("operand")
            if op in _RELATIONAL_OPS:
                self._check_relational_pair(op, rng, rhs, element, scope_path, issues)
            else:
                if isinstance(rhs, dict):
                    # classification-expression operator (istype etc.)
                    self._check_nce(rhs, element, scope_path, issues, units_only)

    def _check_range(
        self,
        node: dict,
        element: Any,
        scope_path: list[str],
        issues: list[SemanticIssue],
        units_only: bool,
    ) -> None:
        additive = node.get("additive")
        if isinstance(additive, dict):
            self._check_additive(additive, element, scope_path, issues, units_only)
        operand = node.get("operand")
        if isinstance(operand, dict):
            self._check_additive(operand, element, scope_path, issues, units_only)
        if units_only or node.get("operator") is None:
            return
        # range: both bounds must be ordered/numeric
        lo = self._classify_operand(operand, scope_path)
        hi = self._classify_operand(operand, scope_path) if operand is node.get("operand") else lo

    def _check_additive(
        self,
        node: dict,
        element: Any,
        scope_path: list[str],
        issues: list[SemanticIssue],
        units_only: bool,
    ) -> None:
        mult = node.get("multiplicitive")
        if isinstance(mult, dict):
            self._check_multiplicative(mult, element, scope_path, issues, units_only)
        for op_dict in node.get("operation", []):
            if not isinstance(op_dict, dict):
                continue
            op = op_dict.get("operator")
            rhs = op_dict.get("operand")
            self._check_arithmetic_pair(
                op, mult, rhs, element, scope_path, issues, units_only
            )

    def _check_multiplicative(
        self,
        node: dict,
        element: Any,
        scope_path: list[str],
        issues: list[SemanticIssue],
        units_only: bool,
    ) -> None:
        exp = node.get("exponential")
        if isinstance(exp, dict):
            self._check_exponentiation(exp, element, scope_path, issues, units_only)
        for op_dict in node.get("operation", []):
            if not isinstance(op_dict, dict):
                continue
            op = op_dict.get("operator")
            rhs = op_dict.get("operand")
            self._check_multiplicative_pair(
                op, exp, rhs, element, scope_path, issues, units_only
            )

    def _check_exponentiation(
        self,
        node: dict,
        element: Any,
        scope_path: list[str],
        issues: list[SemanticIssue],
        units_only: bool,
    ) -> None:
        unary = node.get("unary")
        if isinstance(unary, dict):
            self._check_unary(unary, element, scope_path, issues, units_only)
        for op_dict in node.get("operation", []):
            if not isinstance(op_dict, dict):
                continue
            op = op_dict.get("operator")
            rhs = op_dict.get("operand")
            if op in ("**", "^") and not units_only:
                self._check_power_pair(op, unary, rhs, element, scope_path, issues)
            elif isinstance(rhs, dict):
                # exponent rhs is an ExponentiationExpression dict
                self._check_exponentiation(rhs, element, scope_path, issues, units_only)

    def _check_unary(
        self,
        node: dict,
        element: Any,
        scope_path: list[str],
        issues: list[SemanticIssue],
        units_only: bool,
    ) -> None:
        extent = node.get("extent")
        if isinstance(extent, dict):
            primary = extent.get("primary")
            if isinstance(primary, dict):
                self._check_primary_postfix(primary, element, scope_path, issues, units_only)
        op = node.get("operator")
        if op and not units_only:
            operand = self._classify_operand(extent, scope_path)
            if op == "not":
                cat = self._category_from_operand(operand)
                if cat not in ("unknown", "unknown_type", "boolean"):
                    issues.append(SemanticIssue(
                        severity="error",
                        code="OPERAND_TYPE_MISMATCH",
                        message=f"Unary operator 'not' requires a boolean operand; "
                                f"got '{cat}'",
                        element=element,
                        reference="not",
                    ))
            elif op in ("-", "+"):
                cat = self._category_from_operand(operand)
                if cat in ("boolean", "string"):
                    issues.append(SemanticIssue(
                        severity="error",
                        code="OPERAND_TYPE_MISMATCH",
                        message=f"Unary operator '{op}' requires a numeric "
                                f"operand; got '{cat}'",
                        element=element,
                        reference=str(op),
                    ))

    # -- pair checks ------------------------------------------------------

    def _check_logical_pair(self, op, lhs, rhs, element, scope_path, issues) -> None:
        lhs_cat = self._category_of_operand(lhs, scope_path)
        rhs_cat = self._category_of_operand(rhs, scope_path)
        for cat, label in ((lhs_cat, "left"), (rhs_cat, "right")):
            if cat in ("boolean", "unknown"):
                continue
            issues.append(SemanticIssue(
                severity="error",
                code="OPERAND_TYPE_MISMATCH",
                message=f"Logical operator '{op}' requires boolean operands; "
                        f"{label} operand has type category '{cat}'",
                element=element,
                reference=str(op),
            ))

    def _check_equality_pair(self, op, lhs, rhs, element, scope_path, issues) -> None:
        lhs_cat = self._category_of_operand(lhs, scope_path)
        rhs_cat = self._category_of_operand(rhs, scope_path)
        if "unknown" in (lhs_cat, rhs_cat):
            return
        if lhs_cat == rhs_cat:
            return
        # bool vs non-bool is always a bug
        if {lhs_cat, rhs_cat} & {"boolean"} and {lhs_cat, rhs_cat} - {"boolean"}:
            issues.append(SemanticIssue(
                severity="error",
                code="OPERAND_TYPE_MISMATCH",
                message=f"Equality operator '{op}' compares boolean with "
                        f"'{rhs_cat if lhs_cat == 'boolean' else lhs_cat}'",
                element=element,
                reference=str(op),
            ))

    def _check_relational_pair(self, op, lhs, rhs, element, scope_path, issues) -> None:
        lhs_cat = self._category_of_operand(lhs, scope_path)
        rhs_cat = self._category_of_operand(rhs, scope_path)
        for cat in (lhs_cat, rhs_cat):
            if cat == "unknown" or cat == "unknown_type":
                continue
            if cat not in ("numeric", "quantity", "string"):
                issues.append(SemanticIssue(
                    severity="error",
                    code="OPERAND_TYPE_MISMATCH",
                    message=f"Relational operator '{op}' requires ordered "
                            f"(numeric/string/quantity) operands; got '{cat}'",
                    element=element,
                    reference=str(op),
                ))

    def _check_arithmetic_pair(self, op, lhs, rhs, element, scope_path, issues, units_only) -> None:
        lhs_cat = self._category_of_operand(lhs, scope_path)
        rhs_cat = self._category_of_operand(rhs, scope_path)
        if op == "+":
            ok = {"numeric", "quantity", "unknown", "unknown_type"}
            string_ok = ok | {"string"}
            valid = string_ok if units_only is False else ok
            if lhs_cat in ("boolean",) or rhs_cat in ("boolean",):
                self._emit_mismatch(op, lhs_cat, rhs_cat, element, issues)
                return
            if lhs_cat == "string" and rhs_cat == "string":
                return
            if lhs_cat not in ok or rhs_cat not in ok:
                if "string" in (lhs_cat, rhs_cat) and "numeric" in (lhs_cat, rhs_cat):
                    self._emit_mismatch(op, lhs_cat, rhs_cat, element, issues)
            self._check_unit_dimensions(op, lhs, rhs, element, scope_path, issues)
            return
        if op in ("-",):
            for cat in (lhs_cat, rhs_cat):
                if cat in ("boolean", "string"):
                    self._emit_mismatch(op, lhs_cat, rhs_cat, element, issues)
            self._check_unit_dimensions(op, lhs, rhs, element, scope_path, issues)
            return

    def _check_multiplicative_pair(self, op, lhs, rhs, element, scope_path, issues, units_only) -> None:
        lhs_cat = self._category_of_operand(lhs, scope_path)
        rhs_cat = self._category_of_operand(rhs, scope_path)
        if lhs_cat in ("boolean", "string") or rhs_cat in ("boolean", "string"):
            if op in ("*", "/", "%"):
                self._emit_mismatch(op, lhs_cat, rhs_cat, element, issues)
        self._check_unit_dimensions(op, lhs, rhs, element, scope_path, issues)

    def _check_power_pair(self, op, lhs, rhs, element, scope_path, issues) -> None:
        lhs_cat = self._category_of_operand(lhs, scope_path)
        rhs_cat = self._category_of_operand(rhs, scope_path)
        if lhs_cat in ("boolean", "string") or rhs_cat in ("boolean", "string"):
            self._emit_mismatch(op, lhs_cat, rhs_cat, element, issues)

    # -- unit-dimension derivation (Goal 10) ---------------------------------

    def check_derivations(self, model: Any) -> list[SemanticIssue]:
        """Derive ``*`` / ``/`` dimension algebra and compare with typing.

        For every expression owner whose declared type carries a known
        quantity dimension (library ``*Value`` / ``*Unit`` definitions),
        the initializer's dimension is derived algebraically:

        - ``a * b`` adds exponents, ``a / b`` subtracts them
        - ``a ** n`` (literal integer ``n``) multiplies them
        - ``+`` / ``-`` chains require equal operand dimensions
        - dimensionless literals are the multiplicative identity

        A mismatch between the derived dimension and the declared
        typing is reported as ``UNIT_DIMENSION_DERIVATION_MISMATCH``.
        Conservative skips: any operand with unknown dimension, non-
        literal exponents, ``%``, boolean/string/relational levels,
        and initializers with no quantity-typed operand at all (a bare
        literal like ``= 70`` cannot reveal its intended unit).
        """
        issues: list[SemanticIssue] = []
        self._walk_derivation_owners(model, issues, [])
        return issues

    def _walk_derivation_owners(
        self,
        element: Any,
        issues: list[SemanticIssue],
        scope_path: list[str],
    ) -> None:
        if element is None:
            return
        name = getattr(element, "name", None)
        elem_type = type(element).__name__
        is_container = getattr(element, "is_definition", False) or elem_type == "Package"
        child_scope = scope_path
        if is_container and name is not None and elem_type != "Model":
            child_scope = scope_path + [name]

        if elem_type in _EXPRESSION_OWNER_TYPES:
            grammar = getattr(element, "grammar", None)
            if grammar is not None:
                typed = getattr(element, "typed_by_name", None)
                if typed:
                    declared = self._declared_dimension(str(typed))
                    if declared is not None:
                        try:
                            grammar_def = grammar.get_definition()
                        except Exception:
                            grammar_def = None
                        if grammar_def is not None:
                            for expr in _find_owned_expressions(grammar_def):
                                self._check_derivation(
                                    expr, element, str(typed), declared,
                                    scope_path, issues)

        for child in getattr(element, "children", []):
            self._walk_derivation_owners(child, issues, child_scope)

    def _declared_dimension(self, type_name: str) -> Optional[dict[str, int]]:
        """Dimension dict for a declared type name, or None when unknown."""
        dim_str = self._dimensions.get(type_name)
        if not dim_str:
            simple = type_name.rsplit("::", 1)[-1]
            dim_str = self._dimensions.get(simple)
        if not dim_str:
            return None
        return _parse_dimension(dim_str)

    def _check_derivation(
        self,
        expr_dict: dict,
        element: Any,
        type_name: str,
        declared: dict[str, int],
        scope_path: list[str],
        issues: list[SemanticIssue],
    ) -> None:
        node = expr_dict.get("expression")
        if not isinstance(node, dict):
            return
        derived, contributed = self._derive_dimension(node, scope_path)
        if derived is None or not contributed:
            return
        if derived != declared:
            issues.append(SemanticIssue(
                severity="error",
                code="UNIT_DIMENSION_DERIVATION_MISMATCH",
                message=(
                    f"Initializer of '{getattr(element, 'name', '?')}' derives "
                    f"dimension '{_format_dimension(derived)}' but declared type "
                    f"'{type_name}' has dimension '{_format_dimension(declared)}'"
                ),
                element=element,
                reference=_format_dimension(declared),
            ))

    def _derive_dimension(
        self,
        node: Any,
        scope_path: list[str],
    ) -> tuple:
        """Algebraically derive the dimension of an expression dict.

        Returns ``(dims, contributed)`` where ``dims`` is ``None`` when
        the expression is not statically derivable and ``contributed``
        is True when at least one quantity-typed operand was seen
        (bare-literal initializers stay silent).
        """
        if not isinstance(node, dict):
            return (None, False)
        name = node.get("name")

        if name == "OwnedExpression":
            return self._derive_dimension(node.get("expression"), scope_path)
        if name == "ConditionalExpression":
            operands = node.get("operand", []) or []
            if len(operands) != 1:
                return (None, False)
            return self._derive_dimension(operands[0], scope_path)

        # Operator-less levels are pure wrappers (the visitor always
        # emits the full NullCoalescing → Implies → … chain); with an
        # operator present the level is boolean-valued — not derivable.
        if name == "NullCoalescingExpression":
            if node.get("operator"):
                return (None, False)
            return self._derive_dimension(node.get("implies"), scope_path)
        if name in ("ImpliesExpression", "OrExpression", "XorExpression",
                    "AndExpression"):
            if node.get("operator") or node.get("operand") \
                    or node.get("operation"):
                return (None, False)
            child_key = {"ImpliesExpression": "or",
                         "OrExpression": "xor",
                         "XorExpression": "and",
                         "AndExpression": "equality"}[name]
            return self._derive_dimension(node.get(child_key), scope_path)
        if name == "EqualityExpression":
            if node.get("operation"):
                return (None, False)
            return self._derive_dimension(
                node.get("classification"), scope_path)
        if name == "ClassificationExpression":
            if node.get("operator"):
                return (None, False)
            return self._derive_dimension(
                node.get("relational"), scope_path)
        if name == "RelationalExpression":
            if node.get("operation"):
                return (None, False)
            return self._derive_dimension(node.get("range"), scope_path)

        if name == "RangeExpression":
            if node.get("operator"):
                return (None, False)  # a .. b — bounds may differ
            return self._derive_dimension(node.get("additive"), scope_path)

        if name == "AdditiveExpression":
            dims, contributed = self._derive_dimension(
                node.get("multiplicitive"), scope_path)
            for op_dict in node.get("operation", []) or []:
                if not isinstance(op_dict, dict):
                    continue
                op = op_dict.get("operator")
                rhs, c = self._derive_dimension(
                    op_dict.get("operand"), scope_path)
                if op not in ("+", "-") or dims is None or rhs is None \
                        or dims != rhs:
                    return (None, False)
                contributed = contributed or c
            return (dims, contributed)

        if name == "MultiplicativeExpression":
            dims, contributed = self._derive_dimension(
                node.get("exponential"), scope_path)
            for op_dict in node.get("operation", []) or []:
                if not isinstance(op_dict, dict):
                    continue
                op = op_dict.get("operator")
                rhs, c = self._derive_dimension(
                    op_dict.get("operand"), scope_path)
                if dims is None or rhs is None:
                    return (None, False)
                contributed = contributed or c
                if op == "*":
                    dims = _dims_mul(dims, rhs)
                elif op == "/":
                    dims = _dims_div(dims, rhs)
                else:  # '%' and anything else — not derivable
                    return (None, False)
            return (dims, contributed)

        if name == "ExponentiationExpression":
            dims, contributed = self._derive_dimension(
                node.get("unary"), scope_path)
            if dims is None:
                return (None, False)
            # Two shapes: parallel operator/operand lists (visitor form)
            # or operation entries with nested operator/operand dicts.
            operator_list = node.get("operator")
            if isinstance(operator_list, list) and operator_list:
                operand_list = node.get("operand", []) or []
                for op, rhs_node in zip(operator_list, operand_list):
                    if op not in ("**", "^"):
                        return (None, False)
                    exponent = const_fold(rhs_node)
                    if not isinstance(exponent, int) \
                            or isinstance(exponent, bool):
                        return (None, False)
                    dims = {k: v * exponent for k, v in dims.items()}
                return (dims, contributed)
            for op_dict in node.get("operation", []) or []:
                if not isinstance(op_dict, dict):
                    continue
                op = op_dict.get("operator")
                rhs_node = op_dict.get("operand")
                if op not in ("**", "^"):
                    return (None, False)
                exponent = const_fold(rhs_node)
                if not isinstance(exponent, int) or isinstance(exponent, bool):
                    return (None, False)
                dims = {k: v * exponent for k, v in dims.items()}
            return (dims, contributed)

        if name == "UnaryExpression":
            op = node.get("operator")
            if op and op not in ("-", "+"):
                return (None, False)  # 'not' etc. — boolean
            return self._derive_leaf(node.get("extent"), scope_path)

        if name in ("ExtentExpression", "PrimaryExpression", "BaseExpression"):
            return self._derive_leaf(node, scope_path)

        # Leaf nodes (FeatureReferenceExpression etc.)
        return self._derive_leaf(node, scope_path)

    def _derive_leaf(self, node: Any, scope_path: list[str]) -> tuple:
        """Dimension of a leaf operand: literal, typed reference or unwrap."""
        if not isinstance(node, dict):
            return (None, False)
        if node.get("name") in ("LiteralInteger", "LiteralReal",
                                "LiteralInfinity"):
            return ({}, False)
        dims = self._dimension_of_operand(node, scope_path)
        if dims is not None:
            return (dims, True)
        # Parenthesized / wrapped operands: descend through wrapper keys
        for key in ("primary", "base", "expression", "ownedRelationship"):
            child = node.get(key)
            if isinstance(child, dict):
                result = self._derive_dimension(child, scope_path)
                if result[0] is not None:
                    return result
        return (None, False)

    # -- unit dimension safety ---------------------------------------------

    def _check_unit_dimensions(self, op, lhs, rhs, element, scope_path, issues) -> None:
        """Verify dimensional compatibility of a binary arithmetic pair.

        Rules:
        - ``+`` / ``-``: dimensions must be EQUAL (or unknown) — adding
          ``[m]`` to ``[kg]`` is an error; ``[m] + 5`` is dimensionless-extended
          and allowed
        - ``*`` / ``/``: any dimension combination is type-sound (produces
          derived dimensions); only zero-dimensional-vs-quantity mixes are OK
        """
        if op not in ("+", "-", "*", "/", "%"):
            return
        lhs_dim = self._dimension_of_operand(lhs, scope_path)
        rhs_dim = self._dimension_of_operand(rhs, scope_path)
        if lhs_dim is None or rhs_dim is None:
            return
        if op in ("+", "-"):
            if lhs_dim != rhs_dim:
                lhs_txt = _format_dimension(lhs_dim)
                rhs_txt = _format_dimension(rhs_dim)
                issues.append(SemanticIssue(
                    severity="error",
                    code="UNIT_DIMENSION_MISMATCH",
                    message=f"Operator '{op}' combines incompatible unit dimensions "
                            f"'{lhs_txt}' and '{rhs_txt}'",
                    element=element,
                    reference=_format_dimension(rhs_dim),
                ))

    def _dimension_of_operand(self, node, scope_path):
        """Retrieve the pint dimensionality of an operand node, if any."""
        if not isinstance(node, dict):
            return None
        cat = self._classify_operand(node, scope_path)
        if cat.kind == "typed":
            type_name = cat.type_name
            if type_name:
                dim_str = self._dimensions.get(type_name)
                if dim_str:
                    return _parse_dimension(dim_str)
                # ISQ::MassValue → MassValue
                simple = type_name.rsplit("::", 1)[-1]
                dim_str = self._dimensions.get(simple)
                if dim_str:
                    return _parse_dimension(dim_str)
        return None

    # -- operand classification --------------------------------------------

    def _classify_operand(self, node, scope_path) -> "_Operand":
        """Map an expression-layer dict to an _Operand classification."""
        if not isinstance(node, dict):
            return _Operand("unknown")
        name = node.get("name")
        # A relational/equality/operator-bearing node is itself a
        # comparison — its result category is boolean regardless of the
        # operand types (n > 3 is a boolean expression).
        if name == "RelationalExpression":
            if node.get("operation"):
                return _Operand("literal_bool")
            return self._classify_operand(node.get("range"), scope_path)
        if name == "EqualityExpression":
            if node.get("operation"):
                return _Operand("literal_bool")
            return self._classify_operand(node.get("classification"), scope_path)
        if name in ("LiteralInteger",):
            try:
                return _Operand("literal_int", literal_value=int(node.get("value", 0)), literal_is_int=True)
            except (TypeError, ValueError):
                return _Operand("unknown")
        if name == "LiteralReal":
            try:
                return _Operand("literal_float", literal_value=float(node.get("value", 0)))
            except (TypeError, ValueError):
                return _Operand("unknown")
        if name == "LiteralString":
            return _Operand("literal_string")
        if name == "LiteralInfinity":
            return _Operand("literal_float")
        if name in ("BaseExpression", "ExtentExpression"):
            return self._classify_operand(node.get("primary") or node.get("ownedRelationship"), scope_path)
        if name == "FeatureReferenceExpression":
            members = node.get("ownedRelationship", [])
            if members and isinstance(members[0], dict):
                me = members[0].get("memberElement")
                if isinstance(me, dict):
                    names = me.get("names", [])
                    if names:
                        return self._typed_operand("::".join(str(n) for n in names), scope_path)
            return _Operand("unknown")
        if name == "PrimaryExpression":
            base = node.get("base")
            return self._classify_operand(base, scope_path)
        if name == "InvocationExpression":
            return _Operand("invocation")
        if name == "FeatureChainExpression":
            return _Operand("chain")
        if name in ("NullCoalescingExpression", "ImpliesExpression", "OrExpression",
                    "XorExpression", "AndExpression"):
            # first non-empty child layer
            for key in ("implies", "or", "xor", "and", "equality"):
                child = node.get(key)
                if isinstance(child, dict):
                    return self._classify_operand(child, scope_path)
            return _Operand("unknown")
        if name == "ClassificationExpression":
            child = node.get("classification") or node.get("relational")
            return self._classify_operand(child, scope_path)
        if name == "RangeExpression":
            return self._classify_operand(
                node.get("additive") or node.get("operand"), scope_path
            )
        if name == "AdditiveExpression":
            return self._classify_operand(node.get("multiplicitive"), scope_path)
        if name == "MultiplicativeExpression":
            return self._classify_operand(node.get("exponential"), scope_path)
        if name == "ExponentiationExpression":
            return self._classify_operand(node.get("unary"), scope_path)
        if name == "UnaryExpression":
            return self._classify_operand(node.get("extent"), scope_path)
        if name in ("FeatureChainMember", "FeatureReferenceMember"):
            return _Operand("unknown")
        return _Operand("unknown")

    def _typed_operand(self, ref: str, scope_path) -> "_Operand":
        """Classify an identifier reference by resolving its declared type."""
        # Resolve the element to read its type
        current = self._symtab
        for scope_name in scope_path:
            child = current._children.get(scope_name)
            if child is not None:
                current = child
            else:
                break
        element = current.lookup(ref)
        if element is None:
            return _Operand("unknown")
        type_names = self._declared_type_names(element)
        if not type_names:
            return _Operand("unknown")
        return self._operand_from_type_names(type_names)

    def _declared_type_names(self, element: Any) -> list[str]:
        """Extract the declared type QualifiedNames from an element's grammar."""
        grammar = getattr(element, "grammar", None)
        if grammar is None:
            return []
        try:
            grammar_def = grammar.get_definition()
        except Exception:
            return []
        names: list[str] = []

        def walk(n: Any) -> None:
            if isinstance(n, dict):
                if n.get("name") == "QualifiedName" and "names" in n:
                    # only typing locations: OwnedFeatureTyping/FeatureType parents
                    names.append("::".join(str(x) for x in n["names"]))
                for v in n.values():
                    if isinstance(v, (dict, list)):
                        walk(v)
            elif isinstance(n, list):
                for item in n:
                    if isinstance(item, (dict, list)):
                        walk(item)

        walk(grammar_def)
        return names

    def _operand_from_type_names(self, type_names: list[str]) -> "_Operand":
        """Map declared type names to an operand category."""
        for tname in type_names:
            simple = tname.rsplit("::", 1)[-1]
            if simple in _boolean_types():
                return _Operand("typed", type_name=tname)
            if simple in _string_types():
                return _Operand("typed", type_name=tname)
            if simple in _numeric_types():
                return _Operand("typed", type_name=tname)
            dim_str = self._dimensions.get(simple)
            if dim_str is not None:
                return _Operand("typed", type_name=tname, dimension=_parse_dimension(dim_str))
            if simple.endswith("Value") or simple.endswith("Unit"):
                # Unannotated library quantity: treat as quantity
                return _Operand("typed", type_name=tname)
        return _Operand("typed", type_name=type_names[0] if type_names else None)

    def _category_from_operand(self, operand: "_Operand") -> str:
        """Map an already-classified _Operand to its category string."""
        if operand.kind == "literal_int" or operand.kind == "literal_float":
            return "numeric"
        if operand.kind == "literal_string":
            return "string"
        if operand.kind == "literal_bool":
            return "boolean"
        if operand.kind == "typed":
            if operand.type_name in _boolean_types():
                return "boolean"
            if operand.type_name in _string_types():
                return "string"
            if operand.type_name in _numeric_types():
                return "numeric"
            if operand.dimension is not None:
                return "quantity"
            return "unknown_type"
        return "unknown"

    def _category_of_operand(self, node, scope_path) -> str:
        op = self._classify_operand(node, scope_path)
        return self._category_from_operand(op)

    def _emit_mismatch(self, op, lhs_cat, rhs_cat, element, issues) -> None:
        issues.append(SemanticIssue(
            severity="error",
            code="OPERAND_TYPE_MISMATCH",
            message=f"Operator '{op}' received incompatible operand types "
                    f"'{lhs_cat}' and '{rhs_cat}'",
            element=element,
            reference=str(op),
        ))

    def _check_primary_postfix(self, primary, element, scope_path, issues, units_only) -> None:
        if not isinstance(primary, dict):
            return
        base = primary.get("base")
        if isinstance(base, dict):
            br = base.get("ownedRelationship")
            if isinstance(br, dict):
                if br.get("name") == "InvocationExpression":
                    args = br.get("arg_list")
                    # Arguments are themselves expressions: walk them
                    if isinstance(args, dict):
                        pos = args.get("pos_list")
                        if isinstance(pos, dict):
                            for member in pos.get("ownedRelationship", []) or []:
                                if isinstance(member, dict):
                                    am = member.get("ownedRelatedElement")
                                    if isinstance(am, dict):
                                        av = am.get("ownedRelationship")
                                        if isinstance(av, dict):
                                            oe = av.get("ownedRelatedElement")
                                            if isinstance(oe, dict):
                                                self._check_nce(oe.get("expression"), element, scope_path, issues, units_only)
                        named = args.get("named_list")
                        if isinstance(named, dict):
                            for member in named.get("ownedRelationship", []) or []:
                                if isinstance(member, dict):
                                    am = member.get("ownedRelatedElement")
                                    if isinstance(am, dict):
                                        av = am.get("ownedRelationship")
                                        if isinstance(av, dict):
                                            oe = av.get("ownedRelatedElement")
                                            if isinstance(oe, dict):
                                                self._check_nce(oe.get("expression"), element, scope_path, issues, units_only)


def _format_dimension(dims: Optional[dict[str, int]]) -> str:
    if not dims:
        return "dimensionless"
    return "*".join(f"{b}^{e}" for b, e in sorted(dims.items()))


# Operator sets used above (module-level to avoid re-construction per call)
_RELATIONAL_OPS = frozenset({"<", ">", "<=", ">="})
_UNIT_CHECK_OWNERS = _EXPRESSION_OWNER_TYPES


# ---------------------------------------------------------------------------
# Semantic Analyzer
# ---------------------------------------------------------------------------

# Symbols that are always considered defined (standard library types).
_KNOWN_LIBRARY_SYMBOLS = frozenset({
    # Scalar values
    "ScalarValues::Boolean", "ScalarValues::Integer", "ScalarValues::Natural",
    "ScalarValues::Positive", "ScalarValues::Nonnegative",
    "ScalarValues::Rational", "ScalarValues::Real", "ScalarValues::String",
    "ScalarValues::Complex", "ScalarValues::UnlimitedNatural",
    "ScalarValues::Number", "ScalarValues::ScalarValue",
    # ISQ base quantities
    "ISQ::Length", "ISQ::Mass", "ISQ::Time", "ISQ::ElectricCurrent",
    "ISQ::ThermodynamicTemperature", "ISQ::AmountOfSubstance",
    "ISQ::LuminousIntensity", "ISQ::Angle", "ISQ::SolidAngle",
    "ISQ::Information",
    # ISQ value types
    "ISQ::LengthValue", "ISQ::MassValue", "ISQ::TimeValue",
    "ISQ::ElectricCurrentValue", "ISQ::ThermodynamicTemperatureValue",
    "ISQ::AmountOfSubstanceValue", "ISQ::LuminousIntensityValue",
    "ISQ::AngleValue", "ISQ::SolidAngleValue", "ISQ::InformationValue",
    # Common derived quantities
    "ISQ::Area", "ISQ::Volume", "ISQ::Velocity", "ISQ::Acceleration",
    "ISQ::Force", "ISQ::Pressure", "ISQ::Energy", "ISQ::Power",
    "ISQ::ElectricCharge", "ISQ::Voltage", "ISQ::Capacitance",
    "ISQ::Resistance", "ISQ::Conductance", "ISQ::MagneticFlux",
    "ISQ::MagneticFluxDensity", "ISQ::Inductance", "ISQ::Frequency",
    "ISQ::AreaValue", "ISQ::VolumeValue", "ISQ::VelocityValue",
    "ISQ::AccelerationValue", "ISQ::ForceValue", "ISQ::PressureValue",
    "ISQ::EnergyValue", "ISQ::PowerValue", "ISQ::ElectricChargeValue",
    "ISQ::VoltageValue", "ISQ::CapacitanceValue", "ISQ::ResistanceValue",
    "ISQ::ConductanceValue", "ISQ::MagneticFluxValue",
    "ISQ::MagneticFluxDensityValue", "ISQ::InductanceValue",
    "ISQ::FrequencyValue",
    # Base KerML/SysML types
    "KerML::Element", "KerML::Type", "KerML::Feature",
    "KerML::Namespace", "KerML::Relationship",
    "SysML::Occurrence", "SysML::Item", "SysML::Part",
    "SysML::Port", "SysML::Action", "SysML::State",
    "SysML::Requirement", "SysML::Connection",
    "SysML::Flow", "SysML::Interface",
    "SysML::Calculation", "SysML::Constraint",
    "SysML::Enumeration", "SysML::Case",
    "SysML::UseCase", "SysML::AnalysisCase",
    "SysML::VerificationCase", "SysML::View",
    "SysML::Viewpoint", "SysML::Concern",
    "SysML::Allocation", "SysML::Metadata",
    "SysML::Rendering", "SysML::Individual",
})

_KNOWN_LIBRARY_SIMPLE_NAMES: frozenset[str] = frozenset(
    name.rsplit("::", 1)[-1] for name in _KNOWN_LIBRARY_SYMBOLS
)


class SemanticAnalyzer:
    """Analyzes a parsed SysML model for semantic issues."""

    def __repr__(self) -> str:
        return "SemanticAnalyzer()"

    def analyze(
        self,
        model: Any,
        *,
        library: Path | Sequence[Path] | str | Sequence[str] | None = None,
        filename: str | Path | None = None,
        style_checks: bool = True,
    ) -> list[SemanticIssue]:
        """Run semantic analysis on *model* and return a list of issues."""
        issues: list[SemanticIssue] = []

        # Normalize library paths
        lib_roots = self._normalize_library_paths(library)

        # Step 1: Build symbol table
        symtab = SymbolTable()
        symtab.build_from_model(model, lib_roots)

        # Step 2: Validate imports (check if import targets exist)
        issues.extend(self._validate_imports(symtab, lib_roots))

        # Step 3: Collect all references with scope paths
        collector = ReferenceCollector()
        references = collector.collect(model)

        # Step 4: Cross-reference using scope-aware lookup
        for ref_str, element, scope_path, _kind in references:
            if self._is_resolved(ref_str, symtab, scope_path, lib_roots):
                if self._is_implicit_library_reference(ref_str, symtab, scope_path, lib_roots):
                    issues.append(SemanticIssue(
                        severity="warning",
                        code="IMPLICIT_LIBRARY_IMPORT",
                        message=f"Standard library type '{ref_str}' used without "
                                f"explicit import; add 'import ScalarValues::{ref_str};' "
                                f"or 'import ScalarValues::*;' to suppress this warning",
                        element=element,
                        reference=ref_str,
                    ))
                continue
            # v0.60.0: members of an enclosing usage's declared type are
            # visible features inside the usage's body — resolve chained
            # references (and single members) through the context types
            # before flagging the symbol as undefined.
            if self._resolve_through_context(ref_str, symtab, element):
                continue
            issues.append(SemanticIssue(
                severity="error",
                code="UNDEFINED_SYMBOL",
                message=f"Undefined symbol '{ref_str}' referenced in "
                        f"{type(element).__name__} '{getattr(element, 'name', '<anonymous>')}'",
                element=element,
                reference=ref_str,
            ))

        # Step 4b: Expression identifier resolution (v0.54.0 Phase B) —
        # resolve names used inside constraint/calc/default/guard
        # expression bodies against the symbol table.
        issues.extend(self._check_expression_identifiers(model, symtab, lib_roots))

        # Step 4c: Expression type checking & unit-dimension safety
        # (v0.55.0 Phase C).
        issues.extend(self._check_expression_types(model, symtab, lib_roots))
        issues.extend(
            self._check_expression_derivations(model, symtab, lib_roots))

        # Step 5: OCL well-formedness constraints
        issues.extend(self._check_duplicate_names(symtab))
        issues.extend(self._check_cyclic_specialization(symtab))
        issues.extend(self._check_subsetting_compatible(symtab))
        issues.extend(self._check_part_definition_compatible(model))
        issues.extend(self._check_port_definition_compatible(model))
        issues.extend(self._check_feature_chaining_compatible(model, symtab))
        issues.extend(self._check_connector_ends_compatible(model))
        issues.extend(self._check_multiplicity_bounds_valid(model))
        issues.extend(self._check_state_machines(model))
        issues.extend(self._check_trigger_payloads(model, symtab, lib_roots))
        issues.extend(self._check_requirement_coverage(model))
        issues.extend(self._check_trace_targets(model, symtab, lib_roots))
        issues.extend(self._check_verify_targets(model, symtab, lib_roots))
        issues.extend(self._check_satisfy_parts(model, symtab, lib_roots))
        issues.extend(self._check_connector_directions(model))

        # Step 6: Stylistic checks (warnings, not errors)
        if style_checks:
            issues.extend(self._check_naming_conventions(model))
            if filename is not None:
                issues.extend(self._check_file_package_match(model, filename))

        return issues

    @staticmethod
    def _normalize_library_paths(
        library: Path | Sequence[Path] | str | Sequence[str] | None,
    ) -> list[Path]:
        """Normalize library argument to a list of Path objects.

        An empty/None argument resolves to the bundled standard library so
        that library function symbols (e.g. ``size``) are indexed.  Passing
        ``[]`` explicitly would otherwise poison
        ``LibrarySymbolIndex.get_symbols``'s cache with the hardcoded
        fallback set.
        """
        if library is None or (isinstance(library, (list, tuple)) and len(library) == 0):
            default = LibrarySymbolIndex._default_library_root()
            return [default] if default is not None else []
        if isinstance(library, (str, Path)):
            return [Path(library)]
        return [Path(p) for p in library]

    def _validate_imports(
        self,
        symtab: SymbolTable,
        lib_roots: list[Path] | None = None,
    ) -> list[SemanticIssue]:
        """Validate that all import targets exist in the model."""
        issues: list[SemanticIssue] = []
        self._check_imports_in_scope(symtab, symtab, issues, lib_roots)
        return issues

    def _check_imports_in_scope(
        self,
        symtab: SymbolTable,
        table: SymbolTable,
        issues: list[SemanticIssue],
        lib_roots: list[Path] | None = None,
    ) -> None:
        """Check imports in this scope and recurse into children."""
        for imp in table._imports:
            self._validate_single_import(symtab, table, imp, issues, lib_roots)

        for child_table in table._children.values():
            self._check_imports_in_scope(symtab, child_table, issues, lib_roots)

    def _validate_single_import(
        self,
        symtab: SymbolTable,
        table: SymbolTable,
        imp: Any,
        issues: list[SemanticIssue],
        lib_roots: list[Path] | None = None,
    ) -> None:
        """Validate a single Import object."""
        if not imp.children:
            return

        import_child = imp.children[0]
        child_type = type(import_child).__name__

        if child_type == "MembershipImport":
            self._validate_membership_import(symtab, table, import_child, issues, lib_roots)
        elif child_type == "NamespaceImport":
            self._validate_namespace_import(symtab, table, import_child, issues, lib_roots)

    def _validate_membership_import(
        self,
        symtab: SymbolTable,
        table: SymbolTable,
        mem_import: Any,
        issues: list[SemanticIssue],
        lib_roots: list[Path] | None = None,
    ) -> None:
        """Validate a MembershipImport targets an existing element."""
        imported_mem = getattr(mem_import, "membership", None)
        if imported_mem is None:
            return

        qn = getattr(imported_mem, "name", None)
        if qn is None:
            return

        names = getattr(qn, "names", [])
        if not names:
            return

        ref_str = "::".join(names)
        
        # Check library symbols first
        if ref_str in LibrarySymbolIndex.get_symbols(lib_roots):
            return
        if ref_str in _KNOWN_LIBRARY_SYMBOLS:
            return
        
        element = symtab._resolve_qualified_name(ref_str, table)
        if element is None:
            issues.append(SemanticIssue(
                severity="error",
                code="UNRESOLVED_IMPORT",
                message=f"Import target '{ref_str}' does not exist",
                element=None,
                reference=ref_str,
            ))

    def _validate_namespace_import(
        self,
        symtab: SymbolTable,
        table: SymbolTable,
        ns_import: Any,
        issues: list[SemanticIssue],
        lib_roots: list[Path] | None = None,
    ) -> None:
        """Validate a NamespaceImport targets an existing namespace."""
        imported_ns = getattr(ns_import, "namespace", None)
        if imported_ns is None:
            return

        qn = getattr(imported_ns, "namespaces", None)
        if qn is None:
            return

        names = getattr(qn, "names", [])
        if not names:
            return

        ref_str = "::".join(names)
        
        # Check library symbols first
        if ref_str in LibrarySymbolIndex.get_symbols(lib_roots):
            return
        # Also check if any library symbol starts with this namespace
        lib_symbols = LibrarySymbolIndex.get_symbols(lib_roots)
        if any(sym.startswith(ref_str + "::") for sym in lib_symbols):
            return
        
        target_table = symtab._find_namespace_table(ref_str, table)
        if target_table is None:
            issues.append(SemanticIssue(
                severity="error",
                code="UNRESOLVED_IMPORT",
                message=f"Import namespace '{ref_str}' does not exist",
                element=None,
                reference=ref_str,
            ))

    def _is_resolved(
        self,
        ref_str: str,
        symtab: SymbolTable,
        scope_path: list[str],
        lib_roots: list[Path] | None = None,
    ) -> bool:
        """Check if a qualified name reference can be resolved from the given scope."""
        # Check known library symbols (loaded from .kerml/.sysml files)
        if ref_str in LibrarySymbolIndex.get_symbols(lib_roots):
            return True

        # Also check the hardcoded fallback for backwards compatibility
        if ref_str in _KNOWN_LIBRARY_SYMBOLS:
            return True

        # Get the symbol table for the scope where the reference is
        current = symtab
        for scope_name in scope_path:
            child = current._children.get(scope_name)
            if child is not None:
                current = child
            else:
                break

        # Direct lookup from current scope (walks up parent chain)
        if current.lookup(ref_str) is not None:
            return True

        # Check inherited features from supertypes
        if self._resolve_inherited(ref_str, symtab, scope_path):
            return True

        # Try as qualified name: resolve path P::A
        if "::" in ref_str:
            parts = ref_str.split("::")
            lookup_table = current
            all_found = True
            for i, part in enumerate(parts):
                # Find the element (may be in parent scope)
                found = lookup_table.lookup(part)
                if found is None:
                    all_found = False
                    break
                # Find the child scope for this part
                child_scope = lookup_table._children.get(part)
                if child_scope is None:
                    # The element was found via parent lookup.
                    # Find the table that actually contains this symbol.
                    owner = lookup_table._find_symbol_owner(part)
                    if owner is not None:
                        child_scope = owner._children.get(part)
                if child_scope is not None:
                    lookup_table = child_scope
                else:
                    all_found = False
                    break
            if all_found:
                return True

            # Fall back to simple name lookup for the last part
            return current.lookup(parts[-1]) is not None

        if ref_str in LibrarySymbolIndex.get_simple_names(lib_roots):
            return True
        if ref_str in _KNOWN_LIBRARY_SIMPLE_NAMES:
            return True

        return False

    def _is_implicit_library_reference(
        self,
        ref_str: str,
        symtab: SymbolTable,
        scope_path: list[str],
        lib_roots: list[Path] | None = None,
    ) -> bool:
        """Check if *ref_str* resolves ONLY via the library simple-name fallback.

        Returns True when the reference is a bare name (no ``::``), is not
        found in the model's own symbol table, but matches a standard library
        simple name.  This indicates the user is relying on an implicit import.
        """
        if "::" in ref_str:
            return False

        current = symtab
        for scope_name in scope_path:
            child = current._children.get(scope_name)
            if child is not None:
                current = child
            else:
                break

        if current.lookup(ref_str) is not None:
            return False
        if self._resolve_inherited(ref_str, symtab, scope_path):
            return False

        if ref_str in LibrarySymbolIndex.get_simple_names(lib_roots):
            return True
        if ref_str in _KNOWN_LIBRARY_SIMPLE_NAMES:
            return True

        return False

    def _resolve_inherited(self, ref_str: str, symtab: SymbolTable, scope_path: list[str]) -> bool:
        """Check if *ref_str* is an inherited feature from a supertype in the scope chain."""
        # Walk scope_path to find the nearest definition that has supertypes
        for i in range(len(scope_path) - 1, -1, -1):
            context_type = scope_path[i]
            if context_type in symtab._definition_features:
                result = symtab.find_defining_type_for_feature(ref_str, context_type)
                if result is not None:
                    return True
        return False

    # -- expression identifier resolution (v0.54.0 Phase B) -------------------

    def _check_expression_identifiers(
        self,
        model: Any,
        symtab: SymbolTable,
        lib_roots: list[Path] | None = None,
    ) -> list[SemanticIssue]:
        """Resolve identifiers used inside expression bodies.

        Constraint bodies, calc result expressions, attribute/feature
        default values, and transition guards carry structured expression
        ASTs.  Every identifier inside them must resolve to a symbol
        visible from the enclosing scope: a local feature, an inherited
        feature, an enclosing definition member, an imported symbol, or a
        standard-library type.
        """
        collector = ExpressionIdentifierCollector()
        references = collector.collect(model)
        issues: list[SemanticIssue] = []
        seen: set[tuple[str, int]] = set()  # (ref, id(element)) dedupe

        for ref_str, element, scope_path in references:
            key = (ref_str, id(element))
            if key in seen:
                continue
            seen.add(key)
            if self._is_resolved(ref_str, symtab, scope_path, lib_roots):
                continue
            # Dotted feature chains (`wheel1.mass`): resolve the head, then
            # each successive step as a member of the previous step's element.
            if "." in ref_str and self._resolve_feature_chain(
                ref_str, symtab, scope_path, lib_roots, element=element
            ):
                continue
            # Single identifiers (and chains whose head could not be found
            # from the scope) may still be members of an enclosing usage's
            # declared type (v0.60.0).
            if self._resolve_through_context(ref_str, symtab, element):
                continue
            issues.append(SemanticIssue(
                severity="error",
                code="UNRESOLVED_EXPRESSION_IDENTIFIER",
                message=f"Unresolved identifier '{ref_str}' in expression of "
                        f"{type(element).__name__} "
                        f"'{getattr(element, 'name', None) or '<anonymous>'}'",
                element=element,
                reference=ref_str,
            ))
        return issues

    def _resolve_feature_chain(
        self,
        ref_str: str,
        symtab: SymbolTable,
        scope_path: list[str],
        lib_roots: list[Path] | None = None,
        element: Any = None,
    ) -> bool:
        """Resolve a dotted feature chain like ``wheel1.hub.mass``.

        The head segment must resolve as a symbol from the referencing
        scope; each subsequent segment must exist as a named child of the
        previous segment's element (feature navigation through part
        structure).

        Since v0.60.0, when a segment is not found among the current
        element's structural children, navigation continues through the
        element's *declared type* (``Usage.typed_by_name``): the segment is
        looked up as a member of the type definition, following subsetting
        inheritance.  This resolves chains like ``wheels.hub.mass`` where
        ``hub`` is a feature of ``Wheel`` (the type of ``wheels``) rather
        than a structural child of the ``wheels`` usage.

        When the head itself does not resolve from the symbol-table scope
        (e.g. a chain inside a usage body: ``part myCar : Car { attribute
        w = engine.power; }`` — ``engine`` is a member of ``Car``, the
        declared type of ``myCar``), *element*'s context types are tried
        via :meth:`_resolve_through_context`.
        """
        segments = ref_str.split(".")
        head = segments[0]
        if not self._is_resolved(head, symtab, scope_path, lib_roots):
            return self._resolve_through_context(ref_str, symtab, element)

        # Locate the head element by walking to its scope
        current_table = symtab
        for scope_name in scope_path:
            child = current_table._children.get(scope_name)
            if child is not None:
                current_table = child
            else:
                break
        current_element = current_table.lookup(head)
        if current_element is None:
            current_element = current_table.lookup("::".join(segments[:1]))
        if current_element is None:
            return False

        # Type of the current navigation position (name of its definition).
        current_type = self._get_element_type(current_element)

        return self._walk_chain_segments(
            segments[1:], current_element, current_type, symtab
        )

    def _walk_chain_segments(
        self,
        segments: list[str],
        current_element: Any,
        current_type: Optional[str],
        symtab: SymbolTable,
    ) -> bool:
        """Walk the remaining *segments* of a feature chain.

        Each segment is located first among the current element's
        structural children, then — as a fallback — as a feature of the
        current element's declared type (see
        :meth:`_resolve_segment_through_type`).
        """
        for segment in segments:
            # 1) Structural navigation: find `segment` among the current
            #    element's descendants, stopping at that element's own
            #    subtree boundary.
            next_element = self._find_member(current_element, segment)
            if next_element is not None:
                current_element = next_element
                next_type = self._get_element_type(next_element)
                if next_type is not None:
                    current_type = next_type
                continue

            # 2) Type-definition navigation (v0.60.0): look `segment` up as
            #    a feature of the current element's declared type.
            resolved = self._resolve_segment_through_type(
                segment, current_type, symtab
            )
            if resolved is None:
                return False
            current_element, current_type = resolved
        return True

    def _context_types_for_resolution(self, element: Any) -> list[str]:
        """Declared type names visible to *element* as feature scopes.

        Walks the element's parent chain and collects the declared type of
        each enclosing *usage* (innermost first) — a usage inherits the
        members of its type, so ``part myCar : Car`` makes ``engine`` (a
        member of ``Car``) visible inside myCar's body.  Stops at the first
        enclosing definition: definition members are already visible via
        the symbol table's scope walk.
        """
        types: list[str] = []
        seen: set[str] = set()
        node = element
        while node is not None and type(node).__name__ != "Model":
            if getattr(node, "is_definition", False):
                break
            declared = self._get_element_type(node)
            if declared and declared not in seen:
                seen.add(declared)
                types.append(declared)
            node = getattr(node, "parent", None)
        return types

    def _resolve_through_context(
        self,
        ref_str: str,
        symtab: SymbolTable,
        element: Any,
    ) -> bool:
        """Resolve a chained reference through the element's context types.

        Members of an enclosing usage's declared type are visible features
        inside the usage's body: in

        ``part myCar : Car { attribute carPower :\u003e engine::power; }``

        the head ``engine`` is a member of ``Car`` (myCar's type) and
        ``power`` a member of ``Engine`` (engine's type).  Namespace
        qualifiers (``::``) and feature-chain dots (``.``) are treated
        uniformly as segment separators.  Strictly existence-based: every
        segment must resolve, so typos still produce errors (v0.60.0).
        """
        if element is None:
            return False
        segments = [
            seg
            for part in ref_str.split(".")
            for seg in part.split("::")
            if seg
        ]
        if not segments:
            return False
        head = segments[0]
        for context_type in self._context_types_for_resolution(element):
            resolved = self._resolve_segment_through_type(
                head, context_type, symtab
            )
            if resolved is None:
                continue
            current_element, current_type = resolved
            if len(segments) == 1:
                return True
            if self._walk_chain_segments(
                segments[1:], current_element, current_type, symtab
            ):
                return True
        return False

    def _resolve_segment_through_type(
        self,
        segment: str,
        current_type: Optional[str],
        symtab: SymbolTable,
    ) -> Optional[tuple[Any, Optional[str]]]:
        """Resolve *segment* as a feature of the definition named *current_type*.

        Returns ``(member_element, feature_type_name)`` on success so the
        chain walk can continue from the resolved feature, or ``None`` when
        the feature does not exist on the type (directly or inherited).
        """
        if current_type is None:
            return None

        # Accept qualified type names ('ScalarValues::Real') by trying the
        # full name first, then the simple name.
        def_names = [current_type]
        if "::" in current_type:
            def_names.append(current_type.split("::")[-1])

        for def_name in def_names:
            def_info = symtab._definition_features.get(def_name)
            if def_info is None:
                continue

            if segment in def_info["features"]:
                defining_type = def_name
            else:
                # Inherited feature: walk the supertype chain.
                defining_type = symtab.find_defining_type_for_feature(
                    segment, def_name
                )
                if defining_type is None:
                    continue

            feature_type = self._get_feature_type(
                segment, defining_type, symtab
            )

            # Locate the member element for further structural navigation.
            defining_info = symtab._definition_features.get(defining_type)
            member_element = None
            if defining_info is not None:
                member_element = self._find_member(
                    defining_info["element"], segment
                )

            return member_element, feature_type

        return None

    @staticmethod
    def _find_member(element: Any, name: str) -> Optional[Any]:
        """Find a member named *name* within *element*'s subtree (1 level + nesting)."""
        # Direct children first
        for child in getattr(element, "children", []):
            if getattr(child, "name", None) == name:
                return child
        # Nested usage children (usage parts contain structure)
        for child in getattr(element, "children", []):
            for grand in getattr(child, "children", []):
                if getattr(grand, "name", None) == name:
                    return grand
        return None

    # -- expression type checking & static evaluation (v0.55.0 Phase C) -------

    def _check_expression_types(
        self,
        model: Any,
        symtab: SymbolTable,
        lib_roots: list[Path] | None = None,
    ) -> list[SemanticIssue]:
        """Operator operand type compatibility + unit-dimension safety.

        Walks expression bodies (same sources as
        :meth:`_check_expression_identifiers`) and, for every operator
        node, classifies the operand categories and validates the
        combination:

        - arithmetic (``+ - * / %``): numeric operands (or string for
          ``+``); ``-`` requires both operands (no ``1 - 2 - 3``
          misinterpretation: left-associative)
        - relational (``< > <= >=``): ordered (numeric or string) types
        - equality (``== !=``): compatible categories
        - logical (``and or xor implies not``) and ``..`` range: boolean /
          integral rules respectively
        - unit-dimension compatibility (pint) when both sides carry SI
          quantity types
        """
        checker = ExpressionTypeChecker(self, symtab, lib_roots)
        return checker.check(model)

    def _check_unit_compatibility(
        self,
        model: Any,
        symtab: SymbolTable,
        lib_roots: list[Path] | None = None,
    ) -> list[SemanticIssue]:
        """Unit-dimension compatibility inside expressions (pint-backed)."""
        checker = ExpressionTypeChecker(self, symtab, lib_roots)
        return checker.check_units(model)

    def _check_expression_derivations(
        self,
        model: Any,
        symtab: SymbolTable,
        lib_roots: list[Path] | None = None,
    ) -> list[SemanticIssue]:
        """Derive ``*``/``/`` dimension algebra vs declared typing."""
        checker = ExpressionTypeChecker(self, symtab, lib_roots)
        return checker.check_derivations(model)

    # -- OCL well-formedness constraints ------------------------------------

    def _check_trigger_payloads(
        self,
        model: Any,
        symtab: "SymbolTable",
        lib_roots: list,
    ) -> list[SemanticIssue]:
        """Resolve ``accept <Sig>`` trigger payload references (Goal 9).

        The shorthand ``accept <Sig> [when <expr>]`` binds a transition
        trigger to a payload/signal definition.  A typo there is
        silent today: the transition simply never fires, and nothing
        in analyze() looks at payload names.  Two parse shapes exist
        (both verified against the visitor output):

        - bare ``accept Sig`` — PayloadParameter carries an
          OwnedFeatureTyping → QualifiedName reference;
        - guarded ``accept Sig when expr`` — the visitor parks the
          name in ``identification.declaredName`` with no typing.

        In both the name is meant as a reference to a declared
        definition, so each payload name is resolved against the
        symbol table in the transition's scope.  Unresolved payloads
        produce UNRESOLVED_TRIGGER_PAYLOAD errors.  When both an
        identification and a typing are present (``accept e : T``),
        only the typing is a reference — the identification is a
        fresh declaration.
        """
        issues: list[SemanticIssue] = []
        try:
            from sysmlpy.sim import load_model_grammar
            visit = load_model_grammar(model)
        except Exception:
            return issues

        for element, scope_path in self._walk_usages(model):
            # Transitions live inside State definitions' grammar trees
            # (no TransitionUsage object of their own) — extracting at
            # the State level attributes each payload to exactly one
            # element and keeps the scope path correct.
            if type(element).__name__ != "State":
                continue
            grammar_def = None
            grammar = getattr(element, "grammar", None)
            if grammar is None:
                continue
            try:
                grammar_def = grammar.get_definition()
            except Exception:
                continue
            if not isinstance(grammar_def, dict):
                continue
            for payload in _find_payload_parameters(grammar_def):
                ref = _payload_reference(payload)
                if not ref:
                    continue
                if self._is_resolved(ref, symtab, scope_path, lib_roots):
                    continue
                issues.append(SemanticIssue(
                    severity="error",
                    code="UNRESOLVED_TRIGGER_PAYLOAD",
                    message=(
                        f"Accept trigger payload '{ref}' in "
                        f"{type(element).__name__} "
                        f"'{getattr(element, 'name', '<anonymous>')}' "
                        "does not resolve to a defined symbol; the "
                        "transition can never fire"),
                    element=element,
                    reference=ref,
                ))
        return issues

    @staticmethod
    def _walk_usages(model: Any):
        """Yield ``(element, scope_path)`` for every usage-like element."""
        def walk(element, scope_path):
            name = getattr(element, "name", None)
            elem_type = type(element).__name__
            is_container = getattr(element, "is_definition", False)                 or elem_type == "Package"
            child_scope = scope_path
            if is_container and name is not None and elem_type != "Model":
                child_scope = scope_path + [name]
            yield element, scope_path
            for child in getattr(element, "children", []):
                yield from walk(child, child_scope)

        yield from walk(model, [])

    def _check_requirement_coverage(self, model: Any) -> list[SemanticIssue]:
        """Cross-check requirement traceability coverage (Goal 9).

        Reuses the Goal 2 traceability extractor: every requirement
        *usage* with no ``satisfy`` *and* no ``verify`` relationship
        yields a REQUIREMENT_UNCOVERED warning.  ``requirement def``
        declarations are categories/templates, not traceable
        instances, and are never flagged.  Partially covered
        requirements (satisfied but unverified or vice versa) are not
        flagged — that is a project-progress signal, not a
        well-formedness problem.
        """
        issues: list[SemanticIssue] = []
        try:
            from sysmlpy.traceability import extract_traceability
            report = extract_traceability(model)
        except Exception:
            return issues
        for trace in report.uncovered():
            if getattr(trace, "is_definition", False):
                continue
            issues.append(SemanticIssue(
                severity="warning",
                code="REQUIREMENT_UNCOVERED",
                message=(
                    f"Requirement '{trace.name}' has no satisfy and "
                    "no verify relationships"),
                reference=trace.name,
            ))
        return issues

    def _check_trace_targets(
        self,
        model: Any,
        symtab: "SymbolTable",
        lib_roots: list,
    ) -> list[SemanticIssue]:
        """Resolve ``satisfy <req> by <part>`` targets (Goal 9).

        A typo'd satisfy target is silent today — worse, the Goal 2
        traceability extractor materializes the dangling edge as a
        *phantom requirement* in coverage reports, so the real
        requirement reads uncovered while a fake one appears traced.
        Each satisfy target reference is resolved against the symbol
        table in the satisfying part's scope; unresolved targets
        produce UNRESOLVED_TRACE_TARGET errors.
        """
        issues: list[SemanticIssue] = []
        for element, scope_path in self._walk_usages(model):
            grammar = getattr(element, "grammar", None)
            if grammar is None or \
                    grammar.__class__.__name__ != "SatisfyRequirementUsage":
                continue
            ors = getattr(grammar, "ors", None)
            if ors is None:
                continue
            try:
                ref = ors.dump().strip().rstrip(";").strip()
            except Exception:
                continue
            if not ref:
                continue
            if self._is_resolved(ref, symtab, scope_path, lib_roots):
                # Kind check: the target must be a requirement.
                # (Library-resolved targets yield no element here and
                # are left alone — conservative by design.)
                found = self._resolve_element(ref, symtab, scope_path)
                if found is not None and \
                        type(found).__name__ != "Requirement":
                    issues.append(SemanticIssue(
                        severity="warning",
                        code="TRACE_TARGET_NOT_REQUIREMENT",
                        message=(
                            f"satisfy target '{ref}' resolves to a "
                            f"{type(found).__name__}, not a "
                            "requirement"),
                        element=element,
                        reference=ref,
                    ))
                continue
            issues.append(SemanticIssue(
                severity="error",
                code="UNRESOLVED_TRACE_TARGET",
                message=(
                    f"satisfy target '{ref}' in "
                    f"{type(element).__name__} "
                    f"'{getattr(element, 'name', '<anonymous>')}' does "
                    "not resolve to a defined requirement"),
                element=element,
                reference=ref,
            ))
        return issues

    @staticmethod
    def _resolve_element(
        ref_str: str,
        symtab: "SymbolTable",
        scope_path: list[str],
    ):
        """The model element *ref_str* resolves to, if any.

        Mirrors the symbol-table walk of :meth:`_is_resolved` (without
        the library-index shortcuts, which resolve to no model
        element).
        """
        current = symtab
        for scope_name in scope_path:
            child = current._children.get(scope_name)
            if child is not None:
                current = child
            else:
                break
        found = current.lookup(ref_str)
        if found is not None:
            return found
        if "::" in ref_str:
            parts = ref_str.split("::")
            table = current
            for part in parts[:-1]:
                found = table.lookup(part)
                if found is None:
                    return None
                table = table._children.get(part, table)
            return table.lookup(parts[-1])
        return None

    def _check_satisfy_parts(
        self,
        model: Any,
        symtab: "SymbolTable",
        lib_roots: list,
    ) -> list[SemanticIssue]:
        """Resolve ``satisfy <req> by <part>`` subjects (Goal 9).

        The ``by`` reference names the satisfying part; both
        package-level satisfies (grammar ``SatisfyRequirementUsage``
        wrappers yielded by ``_walk_usages``) and satisfies nested
        inside requirement bodies (extracted from the requirement's
        grammar dict — the visitor surfaces nested verify members but
        not satisfy members) are checked.  An unresolved by-part is a
        UNRESOLVED_SATISFY_PART error.
        """
        issues: list[SemanticIssue] = []

        def issue(obj, ref):
            issues.append(SemanticIssue(
                severity="error",
                code="UNRESOLVED_SATISFY_PART",
                message=(
                    f"satisfy 'by {ref}' does not resolve to a "
                    "defined part"),
                element=obj,
                reference=ref,
            ))

        # superclassifier map for subject-type compatibility: walk
        # part/item definitions and collect ``:>`` targets
        supertypes: dict = {}
        for element, scope_path in self._walk_usages(model):
            if type(element).__name__ not in ("Part", "Item"):
                continue
            if not getattr(element, "is_definition", False):
                continue
            grammar = getattr(element, "grammar", None)
            if grammar is None:
                continue
            try:
                d = grammar.get_definition()
            except Exception:
                continue
            if not isinstance(d, dict):
                continue
            defn = d.get("definition") or {}
            decl = defn.get("declaration") or {}
            scp = decl.get("subclassificationpart") or {}
            sups = set()
            for rel in _as_list_dicts(scp.get("ownedRelationship")):
                if rel.get("name") != "OwnedSubclassification":
                    continue
                sc = rel.get("superclassifier") or {}
                names = sc.get("names")
                if isinstance(names, list) and names:
                    sups.add("::".join(str(n) for n in names))
            if sups and element.name:
                supertypes.setdefault(element.name, set()).update(sups)

        def _is_subtype(sub: str, sup: str, seen=None) -> bool:
            if sub == sup:
                return True
            if seen is None:
                seen = set()
            if sub in seen:
                return False
            seen.add(sub)
            for st in supertypes.get(sub, ()):
                if _is_subtype(st, sup, seen):
                    return True
            return False

        def subject_issue(req_name, subj_type, part_name, part_type):
            issues.append(SemanticIssue(
                severity="warning",
                code="SATISFY_SUBJECT_TYPE_MISMATCH",
                message=(
                    f"satisfy 'by {part_name}' ({part_type}) is not "
                    f"related to requirement '{req_name}' subject "
                    f"type '{subj_type}'"),
                reference=req_name,
            ))

        for element, scope_path in self._walk_usages(model):
            gname = (element.grammar.__class__.__name__
                     if getattr(element, "grammar", None) is not None else "")
            if gname == "SatisfyRequirementUsage":
                # package-level wrapper; .ssm dump is the by reference,
                # .ors dump the target requirement
                g = element.grammar
                ssm = getattr(g, "ssm", None)
                if ssm is None:
                    continue
                ref = ssm.dump().strip().rstrip(";").strip()
                if not ref:
                    continue
                if not self._is_resolved(ref, symtab, scope_path, lib_roots):
                    issue(element, ref)
                ors = getattr(g, "ors", None)
                target = ors.dump().strip().rstrip(";").strip() \
                    if ors is not None else None
                if target:
                    self._check_subject_type(
                        element, target, ref, symtab, scope_path,
                        lib_roots, supertypes, _is_subtype,
                        subject_issue)
                continue
            if gname not in ("RequirementDefinition", "RequirementUsage"):
                continue
            # nested satisfy members: scan the requirement's grammar dict
            grammar = element.grammar
            if grammar is None:
                continue
            try:
                grammar_def = grammar.get_definition()
            except Exception:
                continue
            if not isinstance(grammar_def, dict):
                continue
            for sat in _find_named_dicts(
                    grammar_def, "SatisfyRequirementUsage"):
                by_ref = _satisfy_by_ref(sat)
                if not by_ref:
                    continue
                if not self._is_resolved(
                        by_ref, symtab, scope_path, lib_roots):
                    issue(element, by_ref)
                ors = sat.get("ors") or {}
                rf = ors.get("referencedFeature") or {}
                names = rf.get("names") if isinstance(rf, dict) else None
                if names:
                    target = "::".join(str(n) for n in names)
                    self._check_subject_type(
                        element, target, by_ref, symtab, scope_path,
                        lib_roots, supertypes, _is_subtype,
                        subject_issue)
        return issues

    def _check_subject_type(
        self,
        satisfy_obj: Any,
        target_ref: str,
        by_ref: str,
        symtab: "SymbolTable",
        scope_path: list[str],
        lib_roots: list,
        supertypes: dict,
        is_subtype,
        issue_fn,
    ) -> None:
        """SATISFY_SUBJECT_TYPE_MISMATCH (warning, conservative).

        ``satisfy <req> by <part>`` binds *part* as the satisfying
        element of *req*'s subject.  When both the subject's type and
        the by-part's type are known model definitions and neither is
        a (transitive) specialization of the other, flag a warning.
        Anything unresolvable — library types, untyped parts,
        requirements without a typed subject — is skipped.
        """
        target = self._resolve_element(target_ref, symtab, scope_path)
        if target is None:
            return
        subject = getattr(target, "subject", None)
        if not subject:
            return
        subj_type = subject[1]
        if not subj_type or subj_type not in supertypes and (
                subj_type not in getattr(symtab, "_definition_features",
                                         {})):
            return
        by_el = self._resolve_element(by_ref, symtab, scope_path)
        if by_el is None:
            return
        part_type = self._get_element_type(by_el)
        if not part_type:
            return
        # both sides must be model-known (skip library typings)
        if part_type not in supertypes and (
                part_type not in getattr(symtab, "_definition_features",
                                         {})):
            return
        if is_subtype(part_type, subj_type) or is_subtype(
                subj_type, part_type):
            return
        issue_fn(target_ref, subj_type, by_ref, part_type)

    def _check_verify_targets(
        self,
        model: Any,
        symtab: "SymbolTable",
        lib_roots: list,
    ) -> list[SemanticIssue]:
        """Resolve ``verify <vc>`` members inside requirements (Goal 9).

        ``verify v1 : VC;`` in a requirement body parses as a
        VerifyRequirementUsage whose ``ors`` holds the referenced
        verification-case name.  Notably the visitor drops the
        ``: VC`` typing specialization entirely (``fsp`` is empty), so
        a typo'd verification-case *type* is invisible — but the
        member name reference is checkable: resolve it against the
        symbol table in the requirement's scope.  Unresolved targets
        produce UNRESOLVED_VERIFY_TARGET errors (same contract as
        UNRESOLVED_TRACE_TARGET for satisfy).
        """
        issues: list[SemanticIssue] = []
        for element, scope_path in self._walk_usages(model):
            # verify members live inside Requirement grammar trees
            # (no VerifyRequirementUsage object of their own)
            if type(element).__name__ != "Requirement":
                continue
            grammar = getattr(element, "grammar", None)
            if grammar is None:
                continue
            try:
                grammar_def = grammar.get_definition()
            except Exception:
                continue
            if not isinstance(grammar_def, dict):
                continue
            for vr in _find_named_dicts(grammar_def, "VerifyRequirementUsage"):
                ors = vr.get("ors")
                if not isinstance(ors, dict):
                    continue
                rf = ors.get("referencedFeature") or {}
                # referencedFeature *is* the QualifiedName node here
                names = rf.get("names") if isinstance(rf, dict) else None
                if not names:
                    continue
                ref = "::".join(str(n) for n in names)
                if self._is_resolved(ref, symtab, scope_path, lib_roots):
                    continue
                issues.append(SemanticIssue(
                    severity="error",
                    code="UNRESOLVED_VERIFY_TARGET",
                    message=(
                        f"verify target '{ref}' in requirement "
                        f"'{getattr(element, 'name', '<anonymous>')}' "
                        "does not resolve to a defined element"),
                    element=element,
                    reference=ref,
                ))
        return issues

    def _check_connector_directions(self, model: Any) -> list[SemanticIssue]:
        """Check connection ends: directions (Goal 9) + types (Goal 10).

        ``connection c connect a.p1 to b.p2;`` — when both end ports
        carry explicit directions and neither is ``inout``, wiring
        ``out`` to ``out`` or ``in`` to ``in`` flags
        CONNECTOR_DIRECTION_MISMATCH (warning — conjugated ports and
        exotic flow conventions exist, so this is advisory, not an
        error).  Ends without a direction keyword, ``inout`` ends,
        chains deeper than two segments and unresolvable parts are
        skipped.

        Goal 10 (connector-end compatibility depth): when both ends
        resolve to typings that are local ``port def`` names and
        neither is a (transitive) specialization of the other, the
        connection flags CONNECTOR_END_TYPE_MISMATCH (warning) —
        conjugation only makes ports of the *same* (or related) port
        definition compatible.  Ends typed by library/external port
        definitions are skipped (no local subclass data).
        """
        issues: list[SemanticIssue] = []
        try:
            from sysmlpy.sim import load_model_grammar
            visit = load_model_grammar(model)
        except Exception:
            return issues

        scope_ports: dict = {}   # def/usage name -> {port: direction|None}
        part_typing: dict = {}   # part usage name -> typed-by name
        member_typing: dict = {}  # (container name, member) -> typed-by
        supertypes: dict = {}    # def name -> {superclassifier names}
        port_defs: set = set()   # local port def names (Goal 10)
        connections: list = []   # (name, scope_stack, [chain, ...])

        def walk2(node, scope_stack):
            if isinstance(node, dict):
                nm = node.get("name")
                declared = _find_declared_name(node)
                new_stack = scope_stack
                if declared and isinstance(nm, str) and (
                        nm.endswith("Usage") or nm.endswith("Definition")):
                    if nm != "PortUsage":
                        new_stack = scope_stack + [declared]
                    if nm.endswith("Definition"):
                        # superclassifiers (``part def A :> B``) ride the
                        # definition dict's declaration.subclassificationpart
                        sups = set()
                        defn = node.get("definition") or {}
                        decl = defn.get("declaration") or {}
                        scp = decl.get("subclassificationpart") or {}
                        for rel in _as_list_dicts(
                                scp.get("ownedRelationship")):
                            if rel.get("name") != "OwnedSubclassification":
                                continue
                            sc = rel.get("superclassifier") or {}
                            names = sc.get("names")
                            if isinstance(names, list) and names:
                                sups.add("::".join(
                                    str(n) for n in names))
                        if sups:
                            supertypes.setdefault(declared, set()).update(
                                sups)
                        if nm == "PortDefinition":
                            port_defs.add(declared)
                    if nm == "PortUsage":
                        d = _port_direction(node)
                        if scope_stack:
                            # record even undirected ports: existence
                            # drives end resolution, None direction
                            # just skips the direction check
                            scope_ports.setdefault(
                                scope_stack[-1], {})[declared] = d
                        t = _usage_typed_by(node)
                        if t:
                            part_typing[declared] = t
                            if scope_stack:
                                member_typing[(scope_stack[-1],
                                               declared)] = t
                    elif nm == "ConnectionUsage":
                        chains = []
                        part = node.get("part") or {}
                        bp = part.get("part") or {}
                        for rel in _as_list_dicts(
                                bp.get("ownedRelationship")):
                            if rel.get("name") != "ConnectorEndMember":
                                continue
                            ends = _as_list_dicts(
                                rel.get("ownedRelatedElement"))
                            if not ends:
                                continue
                            chain = _connector_end_chain(ends[0])
                            if chain:
                                chains.append(chain)
                        if len(chains) == 2:
                            connections.append((declared, new_stack, chains))
                    elif nm.endswith("Usage"):
                        t = _usage_typed_by(node)
                        if t:
                            part_typing[declared] = t
                            if scope_stack:
                                member_typing[(scope_stack[-1],
                                               declared)] = t
                for k, v in node.items():
                    if isinstance(v, (dict, list)):
                        walk2(v, new_stack)
            elif isinstance(node, list):
                for x in node:
                    walk2(x, scope_stack)

        walk2(visit, [])

        def end_resolve(chain, scope_stack):
            """(direction|None, fully_resolved) for an end chain.

            ``fully_resolved`` is False only when a segment provably
            does not exist in a *known, non-specializing* container —
            containers typed by library defs, unknown names and
            subclasses (inherited members) resolve as "present but
            direction-unknown" to stay conservative.
            """
            if not chain:
                return None, True
            if len(chain) == 1:
                port_name = chain[0]
                for scope in reversed(scope_stack):
                    ports = scope_ports.get(scope)
                    if ports is not None and port_name in ports:
                        return ports[port_name], True
                    t = part_typing.get(scope)
                    if t:
                        ports = scope_ports.get(t)
                        if ports is not None and port_name in ports:
                            return ports[port_name], True
                        if t not in supertypes and t not in scope_ports:
                            # known library/external type: cannot
                            # verify members
                            return None, True
                return None, False
            first = chain[0]
            cur = part_typing.get(first)
            if cur is None:
                for scope in reversed(scope_stack):
                    t = member_typing.get((scope, first))
                    if t:
                        cur = t
                        break
            if cur is None:
                return None, False
            for seg in chain[1:-1]:
                t = member_typing.get((cur, seg))
                if t is None:
                    # members declared on the seg0 *usage* itself
                    t = member_typing.get((first, seg))
                if t is None:
                    return None, cur in supertypes or (
                            cur not in scope_ports
                            and cur not in part_typing)
                cur = t
            ports = scope_ports.get(cur)
            if ports is not None and chain[-1] in ports:
                return ports[chain[-1]], True
            if cur in supertypes:
                return None, True   # inherited port possible
            if cur in scope_ports:
                return None, False  # known container, no such port
            return None, True       # external/library type: skip

        def end_typing(chain, scope_stack):
            """Typed-by name of an end chain's final segment, or None."""
            if not chain:
                return None
            if len(chain) == 1:
                name = chain[0]
                for scope in reversed(scope_stack):
                    t = member_typing.get((scope, name))
                    if t:
                        return t
                return part_typing.get(name)
            first = chain[0]
            cur = part_typing.get(first)
            if cur is None:
                for scope in reversed(scope_stack):
                    t = member_typing.get((scope, first))
                    if t:
                        cur = t
                        break
            if cur is None:
                return None
            for seg in chain[1:-1]:
                t = member_typing.get((cur, seg))
                if t is None:
                    t = member_typing.get((first, seg))
                if t is None:
                    return None
                cur = t
            t = member_typing.get((cur, chain[-1]))
            if t is None:
                t = member_typing.get((first, chain[-1]))
            return t

        def _sub(a, b):
            """True when a is b or a (transitively) specializes b."""
            if a == b:
                return True
            seen = set()
            stack = [a]
            while stack:
                cur = stack.pop()
                if cur == b:
                    return True
                if cur in seen:
                    continue
                seen.add(cur)
                stack.extend(supertypes.get(cur, ()))
            return False

        for cname, cstack, chains in connections:
            d1, r1 = end_resolve(chains[0], cstack)
            d2, r2 = end_resolve(chains[1], cstack)
            if not r1:
                issues.append(SemanticIssue(
                    severity="error",
                    code="UNRESOLVED_CONNECTOR_END",
                    message=(
                        f"Connection '{cname}' end "
                        f"'{'.'.join(chains[0])}' does not resolve"),
                    reference=cname,
                ))
            if not r2:
                issues.append(SemanticIssue(
                    severity="error",
                    code="UNRESOLVED_CONNECTOR_END",
                    message=(
                        f"Connection '{cname}' end "
                        f"'{'.'.join(chains[1])}' does not resolve"),
                    reference=cname,
                ))
            # Goal 10: end-type compatibility (port defs, local only)
            t1 = end_typing(chains[0], cstack)
            t2 = end_typing(chains[1], cstack)
            if (t1 and t2 and t1 in port_defs and t2 in port_defs
                    and not _sub(t1, t2) and not _sub(t2, t1)):
                issues.append(SemanticIssue(
                    severity="warning",
                    code="CONNECTOR_END_TYPE_MISMATCH",
                    message=(
                        f"Connection '{cname}' binds "
                        f"'{'.'.join(chains[0])}' (typed '{t1}') to "
                        f"'{'.'.join(chains[1])}' (typed '{t2}'); "
                        "connected port definitions are unrelated"
                    ),
                    reference=cname,
                ))
            if not d1 or not d2:
                continue
            if d1 == "inout" or d2 == "inout":
                continue
            if d1 == d2:
                issues.append(SemanticIssue(
                    severity="warning",
                    code="CONNECTOR_DIRECTION_MISMATCH",
                    message=(
                        f"Connection '{cname}' binds two '{d1}' ports "
                        f"({chains[0][-1]} -> {chains[1][-1]}); a "
                        "connection normally pairs 'out' with 'in'"),
                    reference=cname,
                ))
        return issues

    def _check_state_machines(self, model: Any) -> list[SemanticIssue]:
        """OCL well-formedness for ``state def`` machines (Goal 9).

        - UNRESOLVED_TRANSITION_ENDPOINT (error): a transition endpoint
          that names no state in its machine.
        - NO_INITIAL_STATE (warning): a machine with more than one
          state and no ``entry; then X;`` — the entry point is
          undefined, so simulation and execution semantics fall back
          to the first declared state.
        - UNREACHABLE_STATE (warning): a state no transition can reach
          from the initial state (only checked when an initial state
          exists).
        """
        issues: list[SemanticIssue] = []
        try:
            # Lazy import: sim pulls the boxes-view collector and the
            # evaluator; no import cycle at module level.  The sim
            # extra is optional — skip these checks without it.
            from sysmlpy.sim import SimulationError, build_state_machine
        except ImportError:
            return issues
        try:
            machines = self._collect_machines(model)
        except SimulationError:
            return issues
        except Exception:
            # A model that cannot be re-parsed (programmatic models
            # without dump support) — skip state-machine checks.
            return issues

        for sm in machines:
            name = sm.get("name")
            top_states = sm.get("states", [])
            n_states = len(top_states)

            # NO_INITIAL_STATE: undefined entry point
            if sm.get("initial") is None and n_states > 1:
                issues.append(SemanticIssue(
                    severity="warning",
                    code="NO_INITIAL_STATE",
                    message=(
                        f"State machine '{name}' declares "
                        f"{n_states} states but no initial state "
                        "(missing 'entry; then <state>;'); the first "
                        "declared state is assumed on execution"),
                    reference=name,
                ))

            # Endpoint resolution + reachability run against the sim's
            # expanded descriptor (composite retargeting, qualified
            # substates, fall-through order — one source of truth).
            try:
                md = build_state_machine(model, focus=name)
            except SimulationError:
                continue
            for t in md.skipped:
                issues.append(SemanticIssue(
                    severity="error",
                    code="UNRESOLVED_TRANSITION_ENDPOINT",
                    message=(
                        f"Transition '{t.name or '<unnamed>'}' in "
                        f"state machine '{name}' references an "
                        f"endpoint that is not a state "
                        f"(source={t.source!r}, target={t.target!r})"),
                    reference=t.name,
                ))

            if sm.get("initial") is None:
                continue  # reachability is ill-defined without an entry
            reachable = {md.initial}
            changed = True
            while changed:
                changed = False
                for t in md.transitions:
                    if t.source in reachable and t.target not in reachable:
                        reachable.add(t.target)
                        changed = True
            for st in md.states:
                if st not in reachable:
                    issues.append(SemanticIssue(
                        severity="warning",
                        code="UNREACHABLE_STATE",
                        message=(
                            f"State '{st}' in state machine '{name}' "
                            "is not reachable from the initial state"),
                        reference=st,
                    ))
        return issues

    @staticmethod
    def _collect_machines(model: Any) -> list:
        """Collect state-machine descriptors (boxes-view collector)."""
        from sysmlpy.sim import load_model_grammar
        from sysmlpy.boxes_view import _collect_state_machine
        return _collect_state_machine(load_model_grammar(model))

    def _check_duplicate_names(self, symtab: SymbolTable) -> list[SemanticIssue]:
        """Namespace.duplicate_names: No two members may have the same name in a scope."""
        issues: list[SemanticIssue] = []
        self._check_duplicates_in_table(symtab, issues)
        return issues

    def _check_duplicates_in_table(
        self, table: SymbolTable, issues: list[SemanticIssue]
    ) -> None:
        """Check for duplicate names in a single symbol table scope."""
        for name, element in table._duplicate_names:
            issues.append(SemanticIssue(
                severity="error",
                code="DUPLICATE_NAME",
                message=f"Duplicate name '{name}' in namespace",
                element=element,
                reference=name,
            ))

        for child_table in table._children.values():
            self._check_duplicates_in_table(child_table, issues)

    def _check_cyclic_specialization(self, symtab: SymbolTable) -> list[SemanticIssue]:
        """Type.no_cyclic_specialization: A type cannot specialize itself cyclically."""
        issues: list[SemanticIssue] = []

        for def_name, def_info in symtab._definition_features.items():
            visited: set[str] = set()
            chain: list[str] = []
            if self._has_cycle(def_name, symtab, visited, chain):
                cycle_str = " -> ".join(chain)
                issues.append(SemanticIssue(
                    severity="error",
                    code="CYCLIC_SPECIALIZATION",
                    message=f"Cyclic specialization: {cycle_str}",
                    element=def_info["element"],
                    reference=def_name,
                ))

        return issues

    def _has_cycle(
        self, def_name: str, symtab: SymbolTable, visited: set[str], chain: list[str]
    ) -> bool:
        """Detect if there's a cycle starting from *def_name*."""
        if def_name in visited:
            if def_name in chain:
                # Found a cycle - build the cycle path
                cycle_start = chain.index(def_name)
                chain.append(def_name)
                return True
            return False

        if def_name not in symtab._definition_features:
            return False

        visited.add(def_name)
        chain.append(def_name)

        supertypes = symtab._definition_features[def_name]["supertypes"]
        for supertype in supertypes:
            if self._has_cycle(supertype, symtab, visited, chain):
                return True

        chain.pop()
        return False

    def _check_subsetting_compatible(self, symtab: SymbolTable) -> list[SemanticIssue]:
        """Feature.subsetting_compatible: Subsetting feature must be compatible with subsetted feature."""
        issues: list[SemanticIssue] = []
        self._walk_model_for_subsetting(symtab, issues)
        return issues

    def _walk_model_for_subsetting(
        self, symtab: SymbolTable, issues: list[SemanticIssue]
    ) -> None:
        """Walk model to find subsetting relationships and validate compatibility."""
        for def_name, def_info in symtab._definition_features.items():
            element = def_info["element"]
            grammar = getattr(element, "grammar", None)
            if grammar is None:
                continue
            self._check_features_for_subsetting(grammar, def_name, symtab, issues)

    def _check_features_for_subsetting(
        self, grammar: Any, def_name: str, symtab: SymbolTable, issues: list[SemanticIssue]
    ) -> None:
        """Check features in a definition for valid subsetting."""
        definition = getattr(grammar, "definition", None)
        if definition is None:
            return

        body = getattr(definition, "body", None)
        if body is None:
            return

        for body_item in getattr(body, "children", []):
            for member in getattr(body_item, "children", []):
                for usage_elem in getattr(member, "children", []):
                    struct_elem = getattr(usage_elem, "children", None)
                    if struct_elem is None:
                        continue
                    self._check_usage_subsetting(struct_elem, def_name, symtab, issues)

    def _check_usage_subsetting(
        self, usage: Any, def_name: str, symtab: SymbolTable, issues: list[SemanticIssue]
    ) -> None:
        """Check a single usage for valid subsetting relationships."""
        # Get the feature name
        feat_name = symtab._get_feature_name(usage)
        if feat_name is None:
            return

        # Get the typed-by type
        usage_attr = getattr(usage, "usage", None)
        if usage_attr is None:
            return

        decl = getattr(usage_attr, "declaration", None)
        if decl is None:
            return

        inner_decl = getattr(decl, "declaration", None)
        if inner_decl is None:
            return

        # Check for specialization (subsetting/typing)
        spec = getattr(inner_decl, "specialization", None)
        if spec is not None:
            for fs in getattr(spec, "specializations", []):
                self._check_feature_specialization(fs, feat_name, def_name, symtab, issues)
            for fs in getattr(spec, "specializations2", []):
                self._check_feature_specialization(fs, feat_name, def_name, symtab, issues)

    def _check_feature_specialization(
        self, fs: Any, feat_name: str, def_name: str, symtab: SymbolTable, issues: list[SemanticIssue]
    ) -> None:
        """Check a single feature specialization for compatibility."""
        rel = getattr(fs, "relationship", None)
        if rel is None:
            return

        rel_type = type(rel).__name__
        if rel_type == "Subsettings":
            for child in getattr(rel, "children", []):
                for el in getattr(child, "elements", []):
                    names = getattr(el, "names", [])
                    if names:
                        subsetted_name = names[-1]
                        if symtab.find_defining_type_for_feature(subsetted_name, def_name) is None:
                            issues.append(SemanticIssue(
                                severity="error",
                                code="INCOMPATIBLE_SUBSETTING",
                                message=f"Feature '{feat_name}' subsets undefined feature '{subsetted_name}' in '{def_name}'",
                                element=None,
                                reference=subsetted_name,
                            ))
        elif rel_type == "Redefinitions":
            for child in getattr(rel, "children", []):
                # OwnedRedefinition stores the redefined feature in redefinedFeature
                redefined = getattr(child, "redefinedFeature", None)
                if redefined is not None:
                    names = getattr(redefined, "names", [])
                    if names:
                        redefined_name = names[-1]
                        if symtab.find_defining_type_for_feature(redefined_name, def_name) is None:
                            issues.append(SemanticIssue(
                                severity="error",
                                code="INCOMPATIBLE_REDEFINITION",
                                message=f"Feature '{feat_name}' redefines undefined feature '{redefined_name}' in '{def_name}'",
                                element=None,
                                reference=redefined_name,
                            ))
        elif rel_type == "Typings":
            # Typings are handled separately (e.g., part definition compatibility)
            pass

    def _check_part_definition_compatible(self, model: Any) -> list[SemanticIssue]:
        """Part.definition_compatible: A part usage's definition must be a PartDefinition."""
        issues: list[SemanticIssue] = []
        self._walk_for_part_compatibility(model, issues)
        return issues

    def _walk_for_part_compatibility(self, element: Any, issues: list[SemanticIssue]) -> None:
        """Walk model to check part usage definitions."""
        if element is None:
            return

        elem_type = type(element).__name__
        if elem_type == "Part":
            grammar = getattr(element, "grammar", None)
            if grammar is not None:
                self._check_part_grammar(grammar, element, issues)

        for child in getattr(element, "children", []):
            self._walk_for_part_compatibility(child, issues)

    def _check_part_grammar(
        self, grammar: Any, element: Any, issues: list[SemanticIssue]
    ) -> None:
        """Check part usage grammar for definition compatibility."""
        usage = getattr(grammar, "usage", None)
        if usage is None:
            return

        decl = getattr(usage, "declaration", None)
        if decl is None:
            return

        inner_decl = getattr(decl, "declaration", None)
        if inner_decl is None:
            return

        spec = getattr(inner_decl, "specialization", None)
        if spec is None:
            return

        for fs in getattr(spec, "specializations", []):
            rel = getattr(fs, "relationship", None)
            if rel is not None and type(rel).__name__ == "Typings":
                # Navigate through Typings -> typing -> relationships -> relationship -> type -> type -> names
                typing = getattr(rel, "typing", None)
                if typing is None:
                    continue
                for ft in getattr(typing, "relationships", []):
                    relationship = getattr(ft, "relationship", None)
                    if relationship is None:
                        continue
                    type_ref = getattr(relationship, "type", None)
                    if type_ref is None:
                        continue
                    qn = getattr(type_ref, "type", None)
                    if qn is None:
                        continue
                    names = getattr(qn, "names", [])
                    if names:
                        type_name = names[-1]
                        # Find the definition and check its grammar type
                        def_element = self._find_definition_by_name(element, type_name)
                        if def_element is not None:
                            def_grammar = getattr(def_element, "grammar", None)
                            if def_grammar is not None:
                                def_type = type(def_grammar).__name__
                                if def_type != "PartDefinition":
                                    issues.append(SemanticIssue(
                                        severity="error",
                                        code="INCOMPATIBLE_PART_DEFINITION",
                                        message=f"Part '{element.name}' is typed by '{type_name}' which is a {def_type}, not PartDefinition",
                                        element=element,
                                        reference=type_name,
                                    ))

    def _find_definition_by_name(self, element: Any, name: str) -> Optional[Any]:
        """Find a definition by name in the model hierarchy."""
        # Walk up to find the root model
        root = element
        while getattr(root, "parent", None) is not None:
            root = root.parent

        # Walk down to find the definition
        return self._search_for_definition(root, name)

    def _search_for_definition(self, element: Any, name: str) -> Optional[Any]:
        """Search for a definition by name in the model."""
        if element is None:
            return None

        elem_name = getattr(element, "name", None)
        if elem_name == name and getattr(element, "is_definition", False):
            return element

        for child in getattr(element, "children", []):
            result = self._search_for_definition(child, name)
            if result is not None:
                return result

        return None

    def _check_port_definition_compatible(self, model: Any) -> list[SemanticIssue]:
        """Port.definition_compatible: A port usage's definition must be a PortDefinition."""
        issues: list[SemanticIssue] = []
        self._walk_for_port_compatibility(model, issues)
        return issues

    def _walk_for_port_compatibility(self, element: Any, issues: list[SemanticIssue]) -> None:
        """Walk model to check port usage definitions."""
        if element is None:
            return

        elem_type = type(element).__name__
        if elem_type == "Port":
            grammar = getattr(element, "grammar", None)
            if grammar is not None:
                self._check_port_grammar(grammar, element, issues)

        for child in getattr(element, "children", []):
            self._walk_for_port_compatibility(child, issues)

    def _check_port_grammar(
        self, grammar: Any, element: Any, issues: list[SemanticIssue]
    ) -> None:
        """Check port usage grammar for definition compatibility."""
        usage = getattr(grammar, "usage", None)
        if usage is None:
            return

        decl = getattr(usage, "declaration", None)
        if decl is None:
            return

        inner_decl = getattr(decl, "declaration", None)
        if inner_decl is None:
            return

        spec = getattr(inner_decl, "specialization", None)
        if spec is None:
            return

        for fs in getattr(spec, "specializations", []):
            rel = getattr(fs, "relationship", None)
            if rel is not None and type(rel).__name__ == "Typings":
                typing = getattr(rel, "typing", None)
                if typing is None:
                    continue
                for ft in getattr(typing, "relationships", []):
                    relationship = getattr(ft, "relationship", None)
                    if relationship is None:
                        continue
                    type_ref = getattr(relationship, "type", None)
                    if type_ref is None:
                        continue
                    qn = getattr(type_ref, "type", None)
                    if qn is None:
                        continue
                    names = getattr(qn, "names", [])
                    if names:
                        type_name = names[-1]
                        def_element = self._find_definition_by_name(element, type_name)
                        if def_element is not None:
                            def_grammar = getattr(def_element, "grammar", None)
                            if def_grammar is not None:
                                def_type = type(def_grammar).__name__
                                if def_type != "PortDefinition":
                                    issues.append(SemanticIssue(
                                        severity="error",
                                        code="INCOMPATIBLE_PORT_DEFINITION",
                                        message=f"Port '{element.name}' is typed by '{type_name}' which is a {def_type}, not PortDefinition",
                                        element=element,
                                        reference=type_name,
                                    ))

    def _check_connector_ends_compatible(self, model: Any) -> list[SemanticIssue]:
        """Connector.ends_compatible: Connected ends must have compatible types."""
        # This requires checking connector end types for compatibility.
        # For now, we flag connectors where ends reference undefined types.
        issues: list[SemanticIssue] = []
        self._walk_for_connector_compatibility(model, issues)
        return issues

    def _walk_for_connector_compatibility(self, element: Any, issues: list[SemanticIssue]) -> None:
        """Walk model to check connector end compatibility."""
        if element is None:
            return

        elem_type = type(element).__name__
        if elem_type == "Connection":
            # Check that connector ends have valid types
            grammar = getattr(element, "grammar", None)
            if grammar is not None:
                self._check_connector_grammar(grammar, element, issues)

        for child in getattr(element, "children", []):
            self._walk_for_connector_compatibility(child, issues)

    def _check_connector_grammar(
        self, grammar: Any, element: Any, issues: list[SemanticIssue]
    ) -> None:
        """Check connector grammar for end compatibility."""
        definition = getattr(grammar, "definition", None)
        if definition is None:
            return

        body = getattr(definition, "body", None)
        if body is None:
            return

        # Check for connect statements
        for body_item in getattr(body, "children", []):
            for member in getattr(body_item, "children", []):
                conn_elem = getattr(member, "children", None)
                if conn_elem is not None:
                    conn_type = type(conn_elem).__name__
                    if conn_type == "ConnectorEndMember":
                        self._check_connector_end(conn_elem, element, issues)

    def _check_connector_end(
        self, conn_end: Any, element: Any, issues: list[SemanticIssue]
    ) -> None:
        """Check a single connector end for valid type reference."""
        ref = getattr(conn_end, "reference", None)
        if ref is None:
            return

        names = getattr(ref, "names", [])
        if names:
            # The connector end reference should resolve to a valid feature
            # This is a basic check - full type compatibility requires more analysis
            pass

    def _check_feature_chaining_compatible(self, model: Any, symtab: SymbolTable) -> list[SemanticIssue]:
        """Feature.chaining_compatible: Chained features must have compatible types.

        Validates that in a feature chain like 'a.b.c', the type of 'a' has
        feature 'b', and the type of 'b' has feature 'c'.

        Only subsetting / redefinition references are chain-checked: their
        targets are genuinely feature chains (``a::b`` / ``a.b``).  Typing and
        subclassification references carry *type* names (``ScalarValues::Real``
        is a namespace-qualified type, not a chain of features) and are
        validated as plain symbols by the cross-reference pass; chain-checking
        them produced false ``INCOMPATIBLE_FEATURE_CHAIN`` errors on every
        qualified type name (fixed in v0.60.0).
        """
        issues: list[SemanticIssue] = []
        collector = ReferenceCollector()
        references = collector.collect(model)

        for ref_str, element, scope_path, kind in references:
            if kind not in ("subsetting", "redefinition"):
                continue
            if "::" not in ref_str:
                continue

            parts = ref_str.split("::")
            if len(parts) < 2:
                continue

            # Get the context type from the scope path or element
            context_type = self._get_context_type(element, scope_path, symtab)
            if context_type is None:
                continue

            # Check each part in the chain starting from the context type
            current_type = context_type
            for part in parts:
                if current_type not in symtab._definition_features:
                    issues.append(SemanticIssue(
                        severity="error",
                        code="INCOMPATIBLE_FEATURE_CHAIN",
                        message=f"Cannot chain feature '{part}' - '{current_type}' is not a definition",
                        element=element,
                        reference=ref_str,
                    ))
                    break

                features = symtab._definition_features[current_type]["features"]
                if part not in features:
                    # Check inherited features
                    defining = symtab.find_defining_type_for_feature(part, current_type)
                    if defining is None:
                        issues.append(SemanticIssue(
                            severity="error",
                            code="INCOMPATIBLE_FEATURE_CHAIN",
                            message=f"Feature '{part}' not found in type '{current_type}' (chain: {ref_str})",
                            element=element,
                            reference=ref_str,
                        ))
                        break
                    # Advance to the inherited feature's *declared type* so
                    # the next segment is validated against the feature's
                    # type, not against the supertype that declares it
                    # (v0.60.0 — 'engine' declared on Vehicle but typed by
                    # 'Engine' means the next segment must be a member of
                    # Engine, not of Vehicle).
                    next_type = self._get_feature_type(part, defining, symtab)
                    if next_type is None:
                        # Undeclared feature type: remaining chain cannot
                        # be validated.
                        break
                    current_type = next_type
                else:
                    # Feature found - get its type for next iteration
                    next_type = self._get_feature_type(part, current_type, symtab)
                    if next_type is not None:
                        current_type = next_type
                    else:
                        # Can't determine type, stop chaining
                        break

        return issues

    def _get_context_type(self, element: Any, scope_path: list[str], symtab: SymbolTable) -> Optional[str]:
        """Get the context type for a reference (the type of the containing element)."""
        # Try to get the type from the element itself
        elem_type = self._get_element_type(element)
        if elem_type is not None:
            return elem_type

        # Try to find the context from the scope path
        for scope_name in reversed(scope_path):
            if scope_name in symtab._definition_features:
                return scope_name

        # Try to find the context from the element's parent chain
        parent = getattr(element, "parent", None)
        while parent is not None:
            parent_name = getattr(parent, "name", None)
            if parent_name is not None:
                # Check if parent is a definition
                if getattr(parent, "is_definition", False):
                    return parent_name
                # Check if parent has a type
                parent_type = self._get_element_type(parent)
                if parent_type is not None:
                    return parent_type
            parent = getattr(parent, "parent", None)

        return None

    def _get_feature_type(self, feature_name: str, def_name: str, symtab: SymbolTable) -> Optional[str]:
        """Get the type of a feature within a definition."""
        if def_name not in symtab._definition_features:
            return None

        def_info = symtab._definition_features[def_name]
        element = def_info["element"]
        grammar = getattr(element, "grammar", None)
        if grammar is None:
            return None

        # Search for the feature in the grammar and get its type
        definition = getattr(grammar, "definition", None)
        if definition is None:
            return None

        body = getattr(definition, "body", None)
        if body is None:
            return None

        for body_item in getattr(body, "children", []):
            for member in getattr(body_item, "children", []):
                for usage_elem in getattr(member, "children", []):
                    struct_elem = getattr(usage_elem, "children", None)
                    if struct_elem is None:
                        continue
                    
                    # Handle StructureUsageElement wrapper
                    struct_type = type(struct_elem).__name__
                    if struct_type == "StructureUsageElement":
                        inner_usage = getattr(struct_elem, "children", None)
                        if inner_usage is not None:
                            feat_name = symtab._get_feature_name(inner_usage)
                            if feat_name == feature_name:
                                return self._get_element_type_from_grammar(inner_usage)
                    else:
                        feat_name = symtab._get_feature_name(struct_elem)
                        if feat_name == feature_name:
                            return self._get_element_type_from_grammar(struct_elem)

        return None

    def _get_element_type_from_grammar(self, usage: Any) -> Optional[str]:
        """Get the type of an element from its grammar structure."""
        usage_attr = getattr(usage, "usage", None)
        if usage_attr is None:
            return None

        decl = getattr(usage_attr, "declaration", None)
        if decl is None:
            return None

        inner_decl = getattr(decl, "declaration", None)
        if inner_decl is None:
            return None

        spec = getattr(inner_decl, "specialization", None)
        if spec is None:
            return None

        for fs in getattr(spec, "specializations", []):
            rel = getattr(fs, "relationship", None)
            if rel is not None and type(rel).__name__ == "Typings":
                typing = getattr(rel, "typing", None)
                if typing is None:
                    continue
                for ft in getattr(typing, "relationships", []):
                    relationship = getattr(ft, "relationship", None)
                    if relationship is None:
                        continue
                    type_ref = getattr(relationship, "type", None)
                    if type_ref is None:
                        continue
                    qn = getattr(type_ref, "type", None)
                    if qn is None:
                        continue
                    names = getattr(qn, "names", [])
                    if names:
                        return names[-1]

        return None

    def _get_element_type(self, element: Any) -> Optional[str]:
        """Get the type name of an element (for feature chaining)."""
        if getattr(element, "is_definition", False):
            return getattr(element, "name", None)

        grammar = getattr(element, "grammar", None)
        if grammar is None:
            return None

        usage = getattr(grammar, "usage", None)
        if usage is None:
            return None

        decl = getattr(usage, "declaration", None)
        if decl is None:
            return None

        inner_decl = getattr(decl, "declaration", None)
        if inner_decl is None:
            return None

        spec = getattr(inner_decl, "specialization", None)
        if spec is None:
            return None

        for fs in getattr(spec, "specializations", []):
            rel = getattr(fs, "relationship", None)
            if rel is not None and type(rel).__name__ == "Typings":
                typing = getattr(rel, "typing", None)
                if typing is None:
                    continue
                for ft in getattr(typing, "relationships", []):
                    relationship = getattr(ft, "relationship", None)
                    if relationship is None:
                        continue
                    type_ref = getattr(relationship, "type", None)
                    if type_ref is None:
                        continue
                    qn = getattr(type_ref, "type", None)
                    if qn is None:
                        continue
                    names = getattr(qn, "names", [])
                    if names:
                        return names[-1]

        return None

    def _check_multiplicity_bounds_valid(self, model: Any) -> list[SemanticIssue]:
        """Multiplicity.bounds_valid: Lower bound must be <= upper bound.

        Validates that multiplicity ranges like [5..2] are invalid because
        the lower bound (5) is greater than the upper bound (2).
        """
        issues: list[SemanticIssue] = []
        self._walk_for_multiplicity_bounds(model, issues)
        return issues

    def _walk_for_multiplicity_bounds(self, element: Any, issues: list[SemanticIssue]) -> None:
        """Walk model to check multiplicity bounds."""
        if element is None:
            return

        elem_type = type(element).__name__
        if elem_type in ("Part", "Item", "Port", "Attribute", "Action", "Reference", "Constraint", "Requirement"):
            grammar = getattr(element, "grammar", None)
            if grammar is not None:
                self._check_grammar_multiplicity(grammar, element, issues)

        for child in getattr(element, "children", []):
            self._walk_for_multiplicity_bounds(child, issues)

    def _check_grammar_multiplicity(
        self, grammar: Any, element: Any, issues: list[SemanticIssue]
    ) -> None:
        """Check grammar for multiplicity bounds validity."""
        usage = getattr(grammar, "usage", None)
        if usage is None:
            return

        decl = getattr(usage, "declaration", None)
        if decl is None:
            return

        inner_decl = getattr(decl, "declaration", None)
        if inner_decl is None:
            return

        spec = getattr(inner_decl, "specialization", None)
        if spec is None:
            return

        mult = getattr(spec, "multiplicity", None)
        if mult is None:
            return

        self._check_multiplicity_part(mult, element, issues)

    def _check_multiplicity_part(
        self, mult: Any, element: Any, issues: list[SemanticIssue]
    ) -> None:
        """Check a MultiplicityPart for valid bounds."""
        # MultiplicityPart -> children (OwnedMultiplicity) -> children (MultiplicityRange) -> children (MultiplicityExpressionMember)
        for owned_mult in getattr(mult, "children", []):
            for mult_range in getattr(owned_mult, "children", []):
                bounds = getattr(mult_range, "children", [])
                if len(bounds) == 2:
                    # Range: [lower..upper]
                    lower = self._extract_bound_value_from_member(bounds[0])
                    upper = self._extract_bound_value_from_member(bounds[1])
                    if lower is not None and upper is not None:
                        if lower > upper:
                            name = getattr(element, "name", "<anonymous>")
                            issues.append(SemanticIssue(
                                severity="error",
                                code="INVALID_MULTIPLICITY_BOUNDS",
                                message=f"Invalid multiplicity [{lower}..{upper}] on '{name}': lower bound exceeds upper bound",
                                element=element,
                                reference=f"[{lower}..{upper}]",
                            ))

    def _extract_bound_value_from_member(self, member: Any) -> Optional[int]:
        """Extract the numeric value from a MultiplicityExpressionMember.

        Returns None for '*' (infinity) or variable references.
        """
        for elem in getattr(member, "children", []):
            # elem is MultiplicityRelatedElement, which stores the value in .element
            inner = getattr(elem, "element", None)
            if inner is None:
                continue
            inner_type = type(inner).__name__
            if inner_type == "LiteralInteger":
                return getattr(inner, "element", None)
            elif inner_type == "LiteralInfinity":
                return None  # Infinity - can't compare
            # FeatureReferenceExpression (variable) - can't compare
        return None

    # -----------------------------------------------------------------------
    # Stylistic Checks (warnings, not errors)
    # -----------------------------------------------------------------------

    def _check_naming_conventions(self, model: Any) -> list[SemanticIssue]:
        """Check naming conventions across the model.

        Conventions:
        - Definitions (defs) should be CamelCase/PascalCase
        - Usages should be camelCase
        - Packages should be PascalCase
        - Attributes should be camelCase
        - Ports should be camelCase
        """
        issues: list[SemanticIssue] = []
        self._traverse_for_naming(model, [], issues)
        return issues

    def _traverse_for_naming(
        self, element: Any, path: list[str], issues: list[SemanticIssue]
    ) -> None:
        """Recursively traverse and check naming conventions."""
        name = getattr(element, "name", None)
        if name is None or len(name) > 30:  # Skip UUIDs
            children = getattr(element, "children", [])
            for child in children:
                self._traverse_for_naming(child, path, issues)
            return

        is_def = getattr(element, "is_definition", False)
        sysml_type = getattr(element, "sysml_type", "")

        if isinstance(element, Package):
            # Packages should be PascalCase
            if not self._is_pascal_case(name):
                issues.append(SemanticIssue(
                    severity="warning",
                    code="NAMING_CONVENTION",
                    message=f"Package '{name}' should be PascalCase (e.g., '{self._to_pascal_case(name)}')",
                    element=element,
                    reference=name,
                ))
        elif is_def:
            # Definitions should be PascalCase
            if not self._is_pascal_case(name):
                issues.append(SemanticIssue(
                    severity="warning",
                    code="NAMING_CONVENTION",
                    message=f"Definition '{name}' should be PascalCase (e.g., '{self._to_pascal_case(name)}')",
                    element=element,
                    reference=name,
                ))
        elif sysml_type == "attribute":
            # Attributes should be camelCase
            if not self._is_camel_case(name):
                issues.append(SemanticIssue(
                    severity="warning",
                    code="NAMING_CONVENTION",
                    message=f"Attribute '{name}' should be camelCase (e.g., '{self._to_camel_case(name)}')",
                    element=element,
                    reference=name,
                ))
        elif sysml_type == "port":
            # Ports should be camelCase
            if not self._is_camel_case(name):
                issues.append(SemanticIssue(
                    severity="warning",
                    code="NAMING_CONVENTION",
                    message=f"Port '{name}' should be camelCase (e.g., '{self._to_camel_case(name)}')",
                    element=element,
                    reference=name,
                ))
        else:
            # Other usages should be camelCase
            if not self._is_camel_case(name):
                issues.append(SemanticIssue(
                    severity="warning",
                    code="NAMING_CONVENTION",
                    message=f"Usage '{name}' should be camelCase (e.g., '{self._to_camel_case(name)}')",
                    element=element,
                    reference=name,
                ))

        children = getattr(element, "children", [])
        for child in children:
            self._traverse_for_naming(child, path + [name], issues)

    @staticmethod
    def _is_pascal_case(name: str) -> bool:
        """Check if a name is PascalCase (starts with uppercase, no leading underscore)."""
        if not name:
            return False
        return name[0].isupper() and not name.startswith("_")

    @staticmethod
    def _is_camel_case(name: str) -> bool:
        """Check if a name is camelCase (starts with lowercase, no leading underscore)."""
        if not name:
            return False
        return name[0].islower() and not name.startswith("_")

    @staticmethod
    def _to_pascal_case(name: str) -> str:
        """Convert a name to PascalCase suggestion."""
        # Simple conversion: capitalize first letter
        if not name:
            return name
        return name[0].upper() + name[1:]

    @staticmethod
    def _to_camel_case(name: str) -> str:
        """Convert a name to camelCase suggestion."""
        # Simple conversion: lowercase first letter
        if not name:
            return name
        return name[0].lower() + name[1:]

    def _check_file_package_match(
        self, model: Any, filename: str | Path
    ) -> list[SemanticIssue]:
        """Check that the top-level package name matches the filename.

        Per SysML v2 convention, a file named ``MyPackage.sysml`` should
        contain a top-level package named ``MyPackage``.
        """
        issues: list[SemanticIssue] = []
        filename = Path(filename)
        expected_name = filename.stem  # e.g., "MyPackage" from "MyPackage.sysml"

        # Find top-level packages
        for child in getattr(model, "children", []):
            if isinstance(child, Package):
                pkg_name = getattr(child, "name", None)
                if pkg_name is not None and pkg_name != expected_name:
                    issues.append(SemanticIssue(
                        severity="warning",
                        code="FILE_PACKAGE_MISMATCH",
                        message=f"Top-level package '{pkg_name}' does not match filename '{filename.name}'. "
                                f"Expected package name '{expected_name}'.",
                        element=child,
                        reference=pkg_name,
                    ))

        return issues


    def _find_child_scope(self, root: SymbolTable, path: list[str]) -> Optional[SymbolTable]:
        """Find the symbol table scope for a qualified path from the root."""
        current = root
        for part in path:
            child = current._children.get(part)
            if child is None:
                return None
            current = child
        return current


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def analyze(
    model: Any,
    *,
    library: Path | Sequence[Path] | str | Sequence[str] | None = None,
    filename: str | Path | None = None,
    style_checks: bool = True,
    strict: bool = False,
) -> AnalysisResult:
    """Run semantic analysis on *model* and return issues.

    Parameters
    ----------
    model : Model
        A parsed SysML model.
    library : Path, str, sequence, or None, optional
        Path(s) to library directories for resolving standard library symbols.
        Defaults to the bundled library shipped with sysmlpy.
    filename : str or Path, optional
        Source filename for file-package name matching checks.
    style_checks : bool
        If True (default), run stylistic checks (naming conventions,
        file-package matching). Set to False to skip warnings.
    strict : bool
        If True, raises ValueError when any error-severity issues are found.
        Default False.

    Returns
    -------
    AnalysisResult
        List of semantic issues found, wrapped in AnalysisResult for
        convenient access to ``.errors`` and ``.warnings`` properties.
    """
    issues = SemanticAnalyzer().analyze(
        model, library=library, filename=filename, style_checks=style_checks
    )
    result = AnalysisResult(issues)
    if strict:
        result.raise_on_errors()
    return result


# ---------------------------------------------------------------------------
# Constant folding / static expression reduction (v0.55.0 — Phase C)
# ---------------------------------------------------------------------------

def const_fold(expr_dict: Any) -> Optional[Any]:
    """Statically evaluate a deterministic literal expression.

    Walks the structured per-precedence expression dict and reduces any
    sub-expression whose operands are all numeric literals and whose
    operators are the arithmetic set (``+ - * % **``; ``/`` only when the
    result is exact — an int result of int division is accepted, a float
    result of int/int is widened to float).

    A parenthesized operand may appear as a single glued
    FeatureReferenceMember whose text is pure integer arithmetic
    (``-(2-5)`` → ``"-(2-5)"``); such text is evaluated with a small
    safe arithmetic evaluator (digit literals, ``+ - * / % **`` and
    parentheses only — no names, no function calls).

    Returns the folded Python value (``int`` or ``float``), or ``None``
    when the expression (or a sub-expression) is not statically
    evaluable.  The input dict is NOT modified.
    """
    if not isinstance(expr_dict, dict):
        return None

    # Locate the top ConditionalExpression if given an OwnedExpression
    node = expr_dict.get("expression") if expr_dict.get("name") == "OwnedExpression" else expr_dict
    if node.get("name") == "OwnedExpression":
        node = node.get("expression")
    value = _fold_node(node)
    return value


_SAFE_ARITH_RE = re.compile(r"^[0-9+\-*/%().\s]+$")


def _fold_text(text: str) -> Optional[Any]:
    """Evaluate pure integer/real arithmetic text (-(2-5) style)."""
    if not isinstance(text, str):
        return None
    t = text.strip()
    if not t or not _SAFE_ARITH_RE.match(t):
        return None
    # Reject leading zeros ambiguity not needed; eval-guarded:
    if not re.fullmatch(r"[0-9+\-*/%().\s*]+", t):
        return None
    # Guard: only digits/ops — anything else already excluded
    try:
        node = ast.parse(t, mode="eval")
    except (SyntaxError, ValueError):
        return None
    return _eval_arith_ast(node.body)


def _eval_arith_ast(node: Any) -> Optional[Any]:
    """Evaluate a restricted arithmetic AST (numbers, + - * / % **, unary +-, parens)."""
    import ast as _ast
    if isinstance(node, _ast.Constant):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        return None
    if isinstance(node, _ast.BinOp):
        left = _eval_arith_ast(node.left)
        right = _eval_arith_ast(node.right)
        if left is None or right is None:
            return None
        try:
            if isinstance(node.op, _ast.Add):
                return left + right
            if isinstance(node.op, _ast.Sub):
                return left - right
            if isinstance(node.op, _ast.Mult):
                return left * right
            if isinstance(node.op, _ast.Div):
                result = left / right
                if isinstance(result, float) and result.is_integer():
                    return int(result)
                return result
            if isinstance(node.op, _ast.Mod):
                return left % right
            if isinstance(node.op, _ast.Pow):
                return left ** right
        except (TypeError, ZeroDivisionError, OverflowError):
            return None
        return None
    if isinstance(node, _ast.UnaryOp):
        val = _eval_arith_ast(node.operand)
        if val is None:
            return None
        if isinstance(node.op, _ast.USub):
            return -val
        if isinstance(node.op, _ast.UAdd):
            return +val
        return None
    return None


def _fold_node(node: Any) -> Optional[Any]:
    """Recursive fold: return a numeric value or None if not deterministic."""
    if not isinstance(node, dict):
        return None
    name = node.get("name")

    if name == "ConditionalExpression":
        operands = node.get("operand", [])
        if len(operands) != 1:
            return None
        return _fold_node(operands[0])

    if name in ("NullCoalescingExpression",):
        if node.get("operator"):
            return None
        return _fold_node(node.get("implies"))

    if name in ("ImpliesExpression", "OrExpression", "XorExpression", "AndExpression"):
        if node.get("operator") or node.get("operand") or node.get("operation"):
            return None
        child_key = {
            "ImpliesExpression": "or",
            "OrExpression": "xor",
            "XorExpression": "and",
            "AndExpression": "equality",
        }[name]
        return _fold_node(node.get(child_key))

    if name == "EqualityExpression":
        ops = node.get("operation", [])
        if ops:
            return None  # comparisons on literals fold to bool; out of scope
        return _fold_node(node.get("classification"))

    if name == "ClassificationExpression":
        if node.get("operator"):
            return None
        return _fold_node(node.get("relational"))

    if name == "RelationalExpression":
        if node.get("operation"):
            return None
        return _fold_node(node.get("range"))

    if name == "RangeExpression":
        if node.get("operator"):
            return None
        return _fold_node(node.get("additive"))

    if name == "AdditiveExpression":
        left = _fold_node(node.get("multiplicitive"))
        if left is None:
            return None
        result = left
        for op_dict in node.get("operation", []):
            op = op_dict.get("operator")
            rhs = _fold_node(op_dict.get("operand"))
            if rhs is None:
                return None
            try:
                if op == "+":
                    result = result + rhs
                elif op == "-":
                    result = result - rhs
                else:
                    return None
            except (TypeError, ZeroDivisionError):
                return None
        return result

    if name == "MultiplicativeExpression":
        left = _fold_node(node.get("exponential"))
        if left is None:
            return None
        result = left
        for op_dict in node.get("operation", []):
            op = op_dict.get("operator")
            rhs = _fold_node(op_dict.get("operand"))
            if rhs is None:
                return None
            try:
                if op == "*":
                    result = result * rhs
                elif op == "/":
                    result = result / rhs
                    if isinstance(result, float) and result.is_integer():
                        result = int(result)
                elif op == "%":
                    result = result % rhs
                else:
                    return None
            except (TypeError, ZeroDivisionError):
                return None
        return result

    if name == "ExponentiationExpression":
        # unary ( ** | ^ ) ExponentiationExpression operands
        base = _fold_node(node.get("unary"))
        if base is None:
            return None
        ops = node.get("operation", []) or node.get("operator", [])
        if node.get("operator") and isinstance(node.get("operator"), list):
            # operator list / operand pair form
            operand_list = node.get("operand", [])
            result = base
            for op, rhs_dict in zip(node["operator"], operand_list):
                rhs = _fold_node(rhs_dict)
                if rhs is None or not isinstance(rhs, (int, float)):
                    return None
                try:
                    result = result ** rhs
                except (TypeError, OverflowError, ZeroDivisionError):
                    return None
            return result
        for op_dict in node.get("operation", []) or []:
            op = op_dict.get("operator")
            rhs = _fold_node(op_dict.get("operand"))
            if rhs is None:
                return None
            try:
                result = result if False else base  # placeholder replaced below
            except Exception:
                return None
        return base if not (node.get("operation")) else None

    if name == "UnaryExpression":
        op = node.get("operator")
        extent = node.get("extent")
        if isinstance(extent, dict) and isinstance(
            extent.get("ownedRelationship"), dict
        ):
            # parenthesized chain: fold the nested expression
            val = _fold_node(extent.get("ownedRelationship"))
        else:
            val = _fold_node(extent)
        if val is None:
            return None
        if op is None or op == "":
            return val
        if op == "-":
            return -val
        if op == "+":
            return +val
        return None

    if name in ("ExtentExpression",):
        return _fold_node(node.get("primary"))
    if name == "PrimaryExpression":
        # only literals fold
        base = node.get("base")
        if isinstance(base, dict):
            rel = base.get("ownedRelationship")
            if isinstance(rel, dict):
                if rel.get("name") == "LiteralInteger":
                    try:
                        return int(rel.get("value", 0))
                    except (TypeError, ValueError):
                        return None
                if rel.get("name") == "LiteralReal":
                    try:
                        v = float(rel.get("value", 0))
                        return int(v) if float(v).is_integer() else v
                    except (TypeError, ValueError):
                        return None
                if rel.get("name") == "FeatureReferenceExpression":
                    # glued parenthesized arithmetic text, e.g. "-(2-5)"
                    members = rel.get("ownedRelationship", [])
                    if isinstance(members, list) and members:
                        me = members[0].get("memberElement")
                        if isinstance(me, dict):
                            text = "".join(str(n) for n in me.get("names", []))
                            if text:
                                return _fold_text(text)
        return None
    return None


def _extent_primary(node: Any) -> Any:
    """Reach the primary/base node inside an extent (or the operand)."""
    if isinstance(node, dict):
        if isinstance(node.get("primary"), dict):
            return node["primary"]
    return node


def _fold_exponent(base_node, rhs_node):
    base = _fold_node(base_node)
    rhs = _fold_node(rhs_node)
    if base is None or rhs is None:
        return None
    try:
        return base ** rhs
    except (TypeError, OverflowError, ZeroDivisionError):
        return None
