#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jun 30 23:23:31 2023

@author: mycr0ft
"""


# import os

# os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import uuid as uuidlib

import pint
import os

ureg = pint.UnitRegistry()


def _is_uuid(s: str) -> bool:
    """Return True if *s* looks like an auto-generated UUID4 string."""
    if not isinstance(s, str) or len(s) != 36:
        return False
    parts = s.split('-')
    if len(parts) != 5:
        return False
    lengths = [8, 4, 4, 4, 12]
    return all(
        len(p) == n and all(c in '0123456789abcdef' for c in p.lower())
        for p, n in zip(parts, lengths)
    )


def _declaration_name(elem):
    """Extract a declared name from a grammar usage/definition object (v0.62.0).

    Handles both declaration layouts: ``UsageDeclaration`` (identification
    directly) and ``CalculationUsageDeclaration`` (nested ``declaration``).
    Returns None when no declared name is present.
    """
    decl = getattr(elem, "declaration", None)
    if decl is None:
        return None
    ident = getattr(decl, "identification", None)
    if ident is not None and getattr(ident, "declaredName", None):
        return ident.declaredName
    inner = getattr(decl, "declaration", None)
    if inner is not None:
        ident = getattr(inner, "identification", None)
        if ident is not None and getattr(ident, "declaredName", None):
            return ident.declaredName
    return None


def _resolve_name_from_specialization(specialization):
    """Find the most user-visible identifier in a ``FeatureSpecializationPart``.

    Walks ``Redefinitions`` / ``Subsettings`` / ``References`` and returns
    the last identifier segment of the first chain. Used by
    ``Usage.load_from_grammar`` as a fallback when no identification was
    given on the feature declaration (e.g. ``attribute :>> ea;`` instead
    of ``attribute ea :>> Base;``).

    Returns ``None`` if nothing usable is found; callers should treat that
    as "no resolved name" and keep their existing default (typically a
    UUID sentinel).
    """
    if specialization is None:
        return None
    for fs in getattr(specialization, "specializations", None) or []:
        rel = getattr(fs, "relationship", None)
        if rel is None:
            continue
        for child in getattr(rel, "children", None) or []:
            # OwnedRedefinition / OwnedReferenceSubsetting / OwnedSubsetting:
            # a dotted chain (:> base.x) keeps the head QualifiedName plus
            # one OwnedFeatureChain per remaining segment. Collect every
            # segment in order and resolve to the last one.
            segments = []
            qn = (
                getattr(child, "redefinedFeature", None)
                or getattr(child, "referencedFeature", None)
            )
            if qn is not None and getattr(qn, "names", None):
                segments.extend(qn.names)
            for el in getattr(child, "elements", None) or []:
                if hasattr(el, "names") and el.names:
                    segments.extend(el.names)
                elif hasattr(el, "feature"):
                    for seg in getattr(el.feature, "children", []) or []:
                        cf = getattr(seg, "chainingFeature", None)
                        if cf is not None and getattr(cf, "names", None):
                            segments.extend(cf.names)
            if segments:
                return segments[-1]
        # First chain resolved; stop looking further.
        return None
    return None

# Load custom US Customary unit definitions
_us_customary_path = os.path.join(os.path.dirname(__file__), "us_customary_units.txt")
if os.path.exists(_us_customary_path):
    with open(_us_customary_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                ureg.define(line)

from sysmlpy.formatting import classtree
from sysmlpy.navigate import Searchable
from sysmlpy.validator import validate_unit_conformance

from sysmlpy.grammar.classes import (
    Identification,
    DefinitionBody,
    DefinitionBodyItem,
    FeatureSpecializationPart,
    SubclassificationPart,
)

from sysmlpy.grammar.classes import (
    AttributeUsage,
    AttributeDefinition,
    ValuePart,
    PartUsage,
    PartDefinition,
    ItemUsage,
    ItemDefinition,
    PortUsage,
    PortDefinition,
    DefaultReferenceUsage,
    RefPrefix,
    ActionUsage,
    ActionDefinition,
    RequirementDefinition,
    UseCaseDefinition,
    StateUsage,
    StateDefinition,
    ConstraintUsage,
    ConstraintDefinition,
    ConnectionUsage,
    ConnectionDefinition,
    FlowConnectionUsage,
    FlowConnectionDefinition,
    CalculationUsage,
    CalculationDefinition,
    EnumerationDefinition,
    AllocationDefinition,
    AllocationUsage,
    MetadataDefinition,
    MetadataUsage,
    RenderingDefinition,
    RenderingUsage,
    IndividualDefinition,
    IndividualUsageSimple,
    FlowDefinition,
    ViewDefinition,
    ViewUsage,
    ViewpointDefinition,
    ViewpointUsage,
    ConcernDefinition,
    ConcernUsage,
    CaseDefinition,
    CaseUsage,
    AnalysisCaseDefinition,
    AnalysisCaseUsage,
    VerificationCaseDefinition,
    VerificationCaseUsage,
)


class Usage(Searchable):
    """Base class for all SysML v2 usage and definition wrapper objects."""

    #: SysML type keyword for this element (overridden by each subclass).
    sysml_type = None

    def __init__(self):
        """Initialize a base Usage element with default attributes.

        Sets a UUID-based name, empty children list, and null references
        for typedby and parent.
        """
        self.name = str(uuidlib.uuid4())
        self.children = []
        self.typedby = None
        self._is_definition = None  # overridden via the setter below
        self.parent = None
        # Re-declaration chains captured from grammar (v0.57.0).
        # Previously only Action initialized these; all other usage kinds
        # loaded from grammar lost their typing / subsetting information.
        self._typed_by_name = None
        self._specializes_names = []
        self._redefined_refs = []
        self._referenced_refs = []

    @property
    def is_definition(self):
        """``True`` when this object wraps a *definition* (e.g. ``part def``)
        rather than a usage (``part``).

        Subclass ``__init__`` methods assign ``self.is_definition = True/False``
        which is stored via the setter so we never mask existing instance
        variable semantics.
        """
        if self._is_definition is not None:
            return self._is_definition
        # Fallback: infer from the grammar class name
        return type(getattr(self, "grammar", None)).__name__.endswith("Definition")

    @is_definition.setter
    def is_definition(self, value):
        self._is_definition = bool(value)

    def _ensure_body(self, subgrammar="usage"):
        # Add children
        body = []
        for abc in self.children:
            body.append(
                DefinitionBodyItem(
                    abc._get_definition(child="DefinitionBody")
                ).get_definition()
            )

        if len(body) > 0:
            # Most usages (Part, Item, Attribute, ...) nest their body under
            # ``grammar.usage.completion.body.body`` (a DefinitionBody).  Prefixed
            # usages such as ViewUsage carry the body directly on ``grammar.body``
            # (a ViewBody / ViewDefinitionBody) whose ``children`` are the
            # DefinitionBodyItem objects themselves.
            target = getattr(self.grammar, subgrammar, None)
            if target is not None and hasattr(target, 'completion'):
                target.completion.body.body = DefinitionBody(
                    {"name": "DefinitionBody", "ownedRelatedElement": body}
                )
            elif target is not None and hasattr(target, 'body'):
                target.body = DefinitionBody(
                    {"name": "DefinitionBody", "ownedRelatedElement": body}
                )
            elif hasattr(self.grammar, 'body') and hasattr(self.grammar.body, 'children'):
                self.grammar.body.children = [
                    DefinitionBodyItem(item) for item in body
                ]
        return self

    def usage_dump(self, child):
        """Serialize this element as a usage for grammar tree output.

        Wraps the grammar definition in the appropriate nesting layers
        (OccurrenceUsageElement, UsageElement, PackageMember, etc.)
        depending on the target context.

        Parameters
        ----------
        child : str or None
            Target context: "DefinitionBody", "PackageBody", or None.

        Returns
        -------
        dict
            Nested dict representing the serialized usage.
        """

        self._ensure_body("usage")

        # Add packaging
        package = {
            "name": "StructureUsageElement",
            "ownedRelatedElement": self.grammar.get_definition(),
        }
        package = {"name": "OccurrenceUsageElement", "ownedRelatedElement": package}

        if child == "DefinitionBody":
            package = {
                "name": "OccurrenceUsageMember",
                "prefix": None,
                "ownedRelatedElement": [package],
            }

            package = {"name": "DefinitionBodyItem", "ownedRelationship": [package]}
        elif "PackageBody":
            package = {"name": "UsageElement", "ownedRelatedElement": package}
            package = {
                "name": "PackageMember",
                "ownedRelatedElement": package,
                "prefix": None,
            }

        return package

    def definition_dump(self, child):
        """Serialize this element as a definition for grammar tree output.

        Wraps the grammar definition in DefinitionElement/DefinitionMember
        layers depending on the target context.

        Parameters
        ----------
        child : str or None
            Target context: "DefinitionBody", "PackageBody", or None.

        Returns
        -------
        dict
            Nested dict representing the serialized definition.
        """
        # This is a definition.

        self._ensure_body("definition")

        package = {
            "name": "DefinitionElement",
            "ownedRelatedElement": self.grammar.get_definition(),
        }

        if child == "DefinitionBody":
            package = {
                "name": "DefinitionMember",
                "prefix": None,
                "ownedRelatedElement": [package],
            }

            package = {"name": "DefinitionBodyItem", "ownedRelationship": [package]}

        elif child == "PackageBody" or child == None:
            # Add these packets to make this dump without parents

            package = {
                "name": "PackageMember",
                "ownedRelatedElement": package,
                "prefix": None,
            }

        return package

    @property
    def redefined_name(self):
        """The last identifier segment of the first re-declaration chain.

        Returns ``""`` (not None) when no redefinition / subset / reference
        is present so callers can use the property as a plain string.
        """
        spec = None
        g = getattr(self, 'grammar', None)
        if g is None:
            return ""
        ud = getattr(g, 'usage', None)
        if ud is not None and hasattr(ud, 'declaration') and ud.declaration is not None:
            spec = getattr(ud.declaration, 'specialization', None) if not hasattr(ud.declaration, 'declaration') else getattr(ud.declaration.declaration, 'specialization', None)
        else:
            d = getattr(g, 'declaration', None)
            if d is not None:
                # Walk to the FeatureDeclaration: some grammars nest
                # declaration -> declaration -> declaration (e.g.
                # ActionUsageDeclaration -> UsageDeclaration ->
                # FeatureDeclaration).
                node = d
                for _ in range(3):
                    if node is None or hasattr(node, 'specialization'):
                        break
                    node = getattr(node, 'declaration', None)
                spec = getattr(node, 'specialization', None) if node is not None else None
        resolved = _resolve_name_from_specialization(spec)
        return resolved or ""

    @property
    def display_name(self):
        """User-meaningful name for this element.

        Identical to ``self.name`` when that field holds a real identifier;
        suppresses the auto-generated UUID sentinel so UI / log output
        stays clean. The original sentinel is still reachable via
        ``self.name``.
        """
        n = getattr(self, 'name', None)
        if n and not _is_uuid(n):
            return n
        rn = self.redefined_name
        if rn:
            return rn
        return ""

    @property
    def typed_by_name(self):
        """The declared type of this usage as a name string (v0.57.0).

        Populated by ``load_from_grammar`` from the grammar's feature
        specialization (``part engine : Engine`` → ``"Engine"``,
        ``attribute mass : ScalarValues::Real`` → ``"ScalarValues::Real"``).
        ``None`` when the element was not loaded from grammar or carries
        no typing relationship.

        Note: this is the *declared name*; ``self.typedby`` holds the
        resolved definition object (only when set programmatically via
        ``set_typed_by`` or when a second resolution pass has run).
        """
        return getattr(self, '_typed_by_name', None)

    def _typedby_serialized_elsewhere(self):
        """True when ``self.typedby`` is already a member of the model tree.

        The ``_get_definition`` output inserts the typed-by definition
        as a sibling member so that a *standalone* programmatic usage
        (one wired via ``set_typed_by`` whose definition was never
        added to a package) still serializes completely.  When the
        definition is already part of the enclosing tree — the case
        for every parsed model, where ``resolve_types()`` fills in
        ``typedby`` — the insertion would duplicate it (the definition
        is serialized by its own package), so it must be skipped.

        Walks up ``parent`` to the tree root, then searches the tree
        excluding this element's own subtree.  O(model size) per typed
        usage; ``dump()`` is not a hot path.
        """
        target = self.typedby
        if target is None:
            return False
        root = self
        depth = 0
        while getattr(root, "parent", None) is not None and depth < 1000:
            root = root.parent
            depth += 1
        stack = [root]
        while stack:
            node = stack.pop()
            for child in getattr(node, "children", []) or []:
                if child is self:
                    # Don't descend into our own subtree: the question
                    # is whether the definition is serialized anywhere
                    # *else*.
                    continue
                if child is target:
                    return True
                stack.append(child)
        return False

    def _get_definition(self, child=None):
        """Build the grammar tree dict for this element.

        Automatically detects whether this is a definition or usage based
        on the grammar class name and delegates to the appropriate dump method.

        Parameters
        ----------
        child : str or None
            Target context for nesting.

        Returns
        -------
        dict
            Nested dict ready for serialization.
        """
        grammar_cls_name = type(self.grammar).__name__
        is_def = grammar_cls_name.endswith('Definition')
        
        if is_def:
            package = self.definition_dump(child)
        else:
            package = self.usage_dump(child)

        if child is None:
            package = {
                "name": "PackageBodyElement",
                "ownedRelationship": [package],
                "prefix": None,
            }

        # Add the typed by definition to the package output — but only
        # when it is not already part of the tree (a parsed model whose
        # ``typedby`` was filled in by ``Model.resolve_types()`` already
        # serializes the definition from its own package; inserting it
        # again would duplicate it).
        if self.typedby is not None and not self._typedby_serialized_elsewhere():
            if child is None:
                package["ownedRelationship"].insert(
                    0, self.typedby._get_definition(child="PackageBody")
                )
            elif child == "PackageBody":
                package = [self.typedby._get_definition(child="PackageBody"), package]
            else:
                package["ownedRelationship"].insert(
                    0, self.typedby._get_definition(child=child)["ownedRelationship"][0]
                )

        return package

    def dump(self, child=None) -> str:
        """Serialize this element to SysML v2 textual notation.

        Parameters
        ----------
        child : bool, optional
            If True, wraps output for embedding in a parent element.

        Returns
        -------
        str
            SysML v2 source code representing this element.
        """
        return classtree(self._get_definition(child)).dump()

    def __str__(self) -> str:
        """Return the SysML v2 text representation of this element."""
        try:
            return self.dump()
        except Exception:
            return repr(self)

    def __repr__(self):
        """Return a constructor-mirroring string representation.

        Output can be passed back to the class constructor to recreate an
        equivalent (though unpopulated-grammar) instance::

            Part(definition=True, name='Engine')
            Part(name='wheel', shortname='w')
            Action()

        Returns
        -------
        str
        """
        # Use the is_definition property — reliable across all 29 subclasses
        is_def = self.is_definition

        # Suppress auto-generated UUID names (they are meaningless to callers)
        name = getattr(self, 'name', None)
        if name and _is_uuid(name):
            name = None

        # Shortname from grammar when present — path differs by definition vs usage
        shortname = None
        try:
            id_obj = getattr(self.grammar, 'usage', None)
            if id_obj:
                id_obj = getattr(id_obj.declaration, 'declaration', None)
                if id_obj:
                    shortname = getattr(id_obj.identification, 'declaredShortName', None)
            if not shortname:
                # Definition path: grammar.definition.declaration.identification.declaredShortName
                def_obj = getattr(self.grammar, 'definition', None)
                if def_obj:
                    id_obj = getattr(def_obj, 'declaration', None)
                    if id_obj:
                        shortname = getattr(id_obj.identification, 'declaredShortName', None)
            if shortname:
                shortname = shortname.strip('<').strip('>')
        except (AttributeError, TypeError):
            shortname = None

        cls_name = self.__class__.__name__
        parts = []
        if is_def:
            parts.append('definition=True')
        if name:
            parts.append(f'name={name!r}')
        if shortname:
            parts.append(f'shortname={shortname!r}')
        return f"{cls_name}({', '.join(parts)})"

    def _set_name(self, name, short=False):
        """Set the declared name or short name on the grammar element.

        Parameters
        ----------
        name : str
            The name to set.
        short : bool
            If True, sets the short name (declaredShortName). Otherwise sets
            the declared name.

        Returns
        -------
        Usage
            Self for chaining.
        """
        if hasattr(self.grammar, "usage"):
            path = self.grammar.usage.declaration.declaration
        elif hasattr(self.grammar, "definition"):
            path = self.grammar.definition.declaration
        else:
            # Navigate recursively through .declaration chain to find identification
            path = self.grammar.declaration
            while hasattr(path, "declaration") and not hasattr(path, "identification"):
                path = path.declaration

        if path.identification is None:
            path.identification = Identification()

        if short:
            path.identification.declaredShortName = "<" + name + ">"
        else:
            self.name = name
            path.identification.declaredName = name

        return self

    set_name = _set_name

    def _get_name(self):
        """Retrieve the declared name from the grammar element.

        Returns
        -------
        str
            The declared name.
        """
        return self.grammar.usage.declaration.declaration.identification.declaredName

    def _set_child(self, child):
        """Add a child element and set its parent reference.

        Parameters
        ----------
        child : Usage
            Child element to add.

        Returns
        -------
        Usage
            Self for chaining.
        """
        self.children.append(child)
        child.parent = self
        return self

    add_child = _set_child

    def _get_child(self, featurechain):
        """Retrieve a nested child by dot-separated name path.

        Parameters
        ----------
        featurechain : str
            Dot-separated path like "x.y.z".

        Returns
        -------
        Usage or None
            The matching child element, or None if not found.
        """
        if isinstance(featurechain, str):
            fc = featurechain.split(".")
        else:
            raise TypeError

        if fc[0] == self.name:
            # This first one must match self name, otherwise pass it all
            featurechain = ".".join(fc[1:])

        for child in self.children:
            fcs = featurechain.split(".")
            if child.name == fcs[0]:
                if len(fcs) == 1:
                    return child
                else:
                    return child._get_child(featurechain)

    get_child = _get_child

    def _set_typed_by(self, typed):
        """Set the typing relationship for this usage element.

        Only accepts definition elements as the type source. Creates the
        appropriate OwnedFeatureTyping grammar structure.

        Parameters
        ----------
        typed : Usage
            A definition element to type this usage by.

        Returns
        -------
        Usage
            Self for chaining.

        Raises
        ------
        ValueError
            If the typed element is not a definition, or if this element
            is itself a definition.
        """
        if "definition" in typed.grammar.__dict__:
            self.typedby = typed
            if "definition" in self.grammar.__dict__:
                raise ValueError("A definition element cannot be defined.")
            else:
                if self.grammar.usage.declaration.declaration.specialization is None:
                    package = {
                        "name": "QualifiedName",
                        "names": [typed.name],
                    }
                    package = {
                        "name": "FeatureType",
                        "type": package,
                        "ownedRelatedElement": [],
                    }
                    package = {"name": "OwnedFeatureTyping", "type": package}
                    package = {"name": "FeatureTyping", "ownedRelationship": package}
                    package = {"name": "TypedBy", "ownedRelationship": [package]}
                    package = {
                        "name": "Typings",
                        "typedby": package,
                        "ownedRelationship": [],
                    }
                    package = {
                        "name": "FeatureSpecialization",
                        "ownedRelationship": package,
                    }
                    package = {
                        "name": "FeatureSpecializationPart",
                        "specialization": [package],
                        "multiplicity": None,
                        "specialization2": [],
                        "multiplicity2": None,
                    }
                    self.grammar.usage.declaration.declaration.specialization = (
                        FeatureSpecializationPart(package)
                    )
        else:
            raise ValueError("Typed by element was not a definition.")
        return self

    set_typed_by = _set_typed_by

    def _set_specializes(self, *parents):
        """Set specialization (`:>`) for definitions.
        
        In SysML v2: `part def Car :> Vehicle;`
        
        Args:
            *parents: One or more definition elements to specialize.
        """
        if "definition" not in self.grammar.__dict__:
            raise ValueError(
                "Only definition elements can use specializes. "
                "Use _set_subsets() for usage elements."
            )
        
        names = [p.name for p in parents]
        relationships = []
        for name in names:
            relationships.append({
                "name": "OwnedSubclassification",
                "superclassifier": {
                    "name": "QualifiedName",
                    "names": [name],
                },
            })
        
        package = {
            "name": "SubclassificationPart",
            "ownedRelationship": relationships,
        }
        self.grammar.definition.declaration.subclassificationpart = (
            SubclassificationPart(package)
        )
        return self

    set_specializes = _set_specializes

    def _set_subsets(self, *parents):
        """Set subsetting (`:>`) for usage elements.
        
        In SysML v2: `part myEng :> eng;`
        
        Args:
            *parents: One or more elements to subset.
        """
        if "definition" in self.grammar.__dict__:
            raise ValueError(
                "Definition elements cannot use subsets. "
                "Use _set_specializes() for definitions."
            )
        
        names = [p.name if hasattr(p, 'name') else str(p) for p in parents]
        relationships = []
        for name in names:
            relationships.append({
                "name": "OwnedSubsetting",
                "subsettedFeature": {
                    "name": "QualifiedName",
                    "names": [name],
                },
                "ownedRelatedElement": [],
            })
        
        package = {
            "name": "Subsettings",
            "ownedRelationship": relationships,
        }
        package = {
            "name": "FeatureSpecialization",
            "ownedRelationship": package,
        }
        package = {
            "name": "FeatureSpecializationPart",
            "specialization": [package],
            "multiplicity": None,
            "specialization2": [],
            "multiplicity2": None,
        }
        self.grammar.usage.declaration.declaration.specialization = (
            FeatureSpecializationPart(package)
        )
        return self

    set_subsets = _set_subsets

    def _set_redefines(self, parent):
        """Set redefinition (`:>>`) for usage elements.
        
        In SysML v2: `attribute :>> mass = 100;`
        
        Args:
            parent: The element being redefined.
        """
        if "definition" in self.grammar.__dict__:
            raise ValueError("Definition elements cannot use redefines.")
        
        name = parent.name if hasattr(parent, 'name') else str(parent)
        
        package = {
            "name": "OwnedRedefinition",
            "redefinedFeature": {
                "name": "QualifiedName",
                "names": [name],
            },
            "ownedRelatedElement": [],
        }
        package = {
            "name": "Redefinitions",
            "ownedRelationship": [package],
        }
        package = {
            "name": "FeatureSpecialization",
            "ownedRelationship": package,
        }
        package = {
            "name": "FeatureSpecializationPart",
            "specialization": [package],
            "multiplicity": None,
            "specialization2": [],
            "multiplicity2": None,
        }
        self.grammar.usage.declaration.declaration.specialization = (
            FeatureSpecializationPart(package)
        )
        return self

    set_redefines = _set_redefines

    def _get_grammar(self):
        """Ensure the grammar tree is up to date and return it.

        Triggers body serialization before returning the grammar object.

        Returns
        -------
        Grammar object
            The underlying grammar instance.
        """
        self._ensure_body()
        return self.grammar

    def load_from_grammar(self, grammar):
        """Populate this element from a parsed grammar object.

        Extracts name, children, and nested structure from the ANTLR-parsed
        grammar tree. Recursively creates child elements for known types.

        Parameters
        ----------
        grammar : object
            Parsed grammar object (e.g., PartDefinition, PartUsage).

        Returns
        -------
        Usage
            Self for chaining.
        """
        self.__init__()
        self.grammar = grammar
        children = []

        # Check if this is a definition or usage
        # Some definition types use 'definition' (PartDefinition, AttributeDefinition)
        # Others use 'declaration' directly (RequirementDefinition, UseCaseDefinition)
        # PartDefinition: has .definition which is a Definition object
        # Usage: has .declaration directly

        # First check if grammar has 'definition' (for definitions like PartDefinition)
        defn = getattr(grammar, 'definition', None)
        if defn:
            # This type uses 'definition' (PartDefinition, etc.)
            # Get name from definition.declaration.identification.declaredName
            u_name = defn.declaration.identification.declaredName

            # Get body from definition.body
            body = defn.body if hasattr(defn, 'body') else None

            # body is DefinitionBody with .children
            if body and hasattr(body, 'children') and body.children:
                children_list = []
                for body_item in body.children:
                    if hasattr(body_item, 'children') and body_item.children:
                        member = body_item.children[0]
                        if hasattr(member, 'children') and member.children:
                            inner = member.children[0]
                            # Handle DefinitionElement wrapping
                            if inner.__class__.__name__ == 'DefinitionElement' and hasattr(inner, 'children') and inner.children:
                                inner = inner.children[0]
                            if hasattr(inner, 'children'):
                                children_list.append(inner)
                            else:
                                children_list.append(inner)
                    elif hasattr(body_item, 'ownedRelatedElement'):
                        children_list.append(body_item)
                children = children_list
            else:
                children = []
        elif hasattr(grammar, 'usage'):
            # This is a usage (like PartUsage, ItemUsage)
            # Get name from grammar.usage.declaration.declaration.identification.declaredName
            usage = grammar.usage
            if hasattr(usage, 'declaration') and hasattr(usage.declaration, 'declaration'):
                decl = usage.declaration.declaration
                if hasattr(decl, 'identification') and decl.identification:
                    u_name = decl.identification.declaredName
                else:
                    u_name = None
            else:
                u_name = None

            # Extract children from usage body: grammar.usage.completion.body.body.children
            # This mirrors the PartDefinition path: grammar.definition.body.children
            try:
                body = usage.completion.body.body
                if hasattr(body, 'children') and body.children:
                    children_list = []
                    for body_item in body.children:
                        if hasattr(body_item, 'children') and body_item.children:
                            member = body_item.children[0]
                            mc = member.children if isinstance(member.children, list) else [member.children]
                            for inner in mc:
                                if inner is None:
                                    continue
                                # Handle DefinitionElement wrapping
                                if inner.__class__.__name__ == 'DefinitionElement' and hasattr(inner, 'children') and inner.children:
                                    inner = inner.children[0]
                                children_list.append(inner)
                    children = children_list
                else:
                    children = []
            except AttributeError:
                children = []
        elif hasattr(grammar, 'declaration'):
            # This type uses 'declaration' directly (RequirementDefinition, UseCaseDefinition, some usages)
            decl = grammar.declaration
            u_name = None

            # Check nested declaration for Usage (UsageDeclaration -> FeatureDeclaration)
            nested_decl = getattr(decl, 'declaration', None)
            if nested_decl and hasattr(nested_decl, 'identification') and nested_decl.identification:
                u_name = nested_decl.identification.declaredName
            # Check direct identification (for RequirementDefinition, UseCaseDefinition)
            elif hasattr(decl, 'identification') and decl.identification:
                u_name = decl.identification.declaredName
            # Prefixed usages (e.g. ViewUsage, ViewDefinition) and other
            # declaration-based types carry their body directly on
            # ``grammar.body`` rather than nested under
            # ``grammar.usage.completion.body.body``.  Extract children the
            # same way the usage path does when the body exposes a
            # ``children`` list (ViewBody / ViewDefinitionBody /
            # DefinitionBody).  Bodies that use ``items`` instead
            # (RequirementBody, CaseBody) are left untouched here.
            children = []
            body = getattr(grammar, 'body', None)
            if body is not None and hasattr(body, 'children') and body.children:
                children_list = []
                for body_item in body.children:
                    if hasattr(body_item, 'children') and body_item.children:
                        member = body_item.children[0]
                        # View-body members like Expose carry their payload
                        # directly (Expose.children = [MembershipExpose])
                        # and have no model children of their own — treat a
                        # missing/payload member gracefully instead of
                        # raising AttributeError.
                        mc = getattr(member, 'children', None)
                        if not isinstance(mc, list):
                            mc = [mc] if mc is not None else []
                        for inner in mc:
                            if inner is None:
                                continue
                            if inner.__class__.__name__ == 'DefinitionElement' and hasattr(inner, 'children') and inner.children:
                                inner = inner.children[0]
                            children_list.append(inner)
                children = children_list
        else:
            u_name = None
            children = []

        if u_name is not None:
            self.name = u_name

        for child in children:
            # Handle different child types
            if hasattr(child, 'definition'):
                # It's a Definition (PartDefinition, ItemDefinition, etc.)
                sc = child
            elif child.__class__.__name__ in (
                "CalculationDefinition", "ConstraintDefinition",
            ):
                # v0.64.0 (Goal 4): definitions without a .definition
                # wrapper (calc def / constraint def) — dispatch on the
                # class itself rather than falling into the .children
                # branch which turns ``sc`` into a list.
                sc = child
            elif hasattr(child, 'children'):
                # It's a StructureUsageElement or similar
                sc = child.children if hasattr(child, 'children') else child
            else:
                continue

            # Process the child
            class_name = sc.__class__.__name__ if not hasattr(sc, '__class__') else sc.__class__.__name__

            if class_name == "PartDefinition":
                c = Part(definition=True).load_from_grammar(sc)
                c.parent = self
                self.children.append(c)
            elif class_name == "CalculationDefinition":
                # v0.64.0 (Goal 4): calc defs inside part/item bodies were
                # dropped from the object tree (and thus from dump()); the
                # evaluator needs their result expressions.
                c = Calculation(definition=True).load_from_grammar(sc)
                c.parent = self
                self.children.append(c)
            elif class_name == "ItemDefinition":
                c = Item(definition=True).load_from_grammar(sc)
                c.parent = self
                self.children.append(c)
            elif class_name == "PartUsage":
                c = Part().load_from_grammar(sc)
                c.parent = self
                self.children.append(c)
            elif class_name == "ItemUsage":
                c = Item().load_from_grammar(sc)
                c.parent = self
                self.children.append(c)
            elif class_name == "PortionUsage":
                c = Part().load_from_grammar(sc)
                c.parent = self
                self.children.append(c)
            elif class_name == "AttributeUsage":
                c = Attribute().load_from_grammar(sc)
                c.parent = self
                self.children.append(c)
            elif class_name == "ReferenceUsage":
                # v0.79.1: nested `ref driver : Person;` inside part/item
                # bodies was dropped from the object tree.
                c = Reference().load_from_grammar(sc)
                c.parent = self
                self.children.append(c)
            elif class_name == "AttributeDefinition":
                c = Attribute(definition=True).load_from_grammar(sc)
                c.parent = self
                self.children.append(c)
            elif class_name == "StructureUsageElement":
                if hasattr(sc, 'children'):
                    inner = sc.children
                    if inner.__class__.__name__ == "PartUsage":
                        c = Part().load_from_grammar(inner)
                        c.parent = self
                        self.children.append(c)
                    elif inner.__class__.__name__ == "ItemUsage":
                        c = Item().load_from_grammar(inner)
                        c.parent = self
                        self.children.append(c)
                    elif inner.__class__.__name__ == "PortUsage":
                        c = Port().load_from_grammar(inner)
                        c.parent = self
                        self.children.append(c)
                    elif inner.__class__.__name__ == "ConnectionUsage":
                        c = Connection().load_from_grammar(inner)
                        c.parent = self
                        self.children.append(c)
                    elif inner.__class__.__name__ == "FlowConnectionUsage":
                        c = Flow().load_from_grammar(inner)
                        c.parent = self
                        self.children.append(c)
                    elif inner.__class__.__name__ == "AllocationUsage":
                        # Phase 0: allocation usages inside a definition
                        # body live in StructureUsageElement -> AllocationUsage.
                        a = Allocation()
                        a.grammar = inner
                        a.parent = self
                        self.children.append(a)
                    elif inner.__class__.__name__ == "RenderingUsage":
                        # v0.88.0: nested ``rendering r2 : E;`` inside a
                        # part/item body was dumped (via the grammar
                        # tree) but never surfaced as a public-API
                        # Rendering child.
                        r = Rendering().load_from_grammar(inner)
                        r.parent = self
                        self.children.append(r)
                    elif inner.__class__.__name__ == "PortionUsage":
                        c = Part().load_from_grammar(inner)
                        c.parent = self
                        self.children.append(c)
            elif class_name == "BehaviorUsageElement":
                # Phase 0 of docs/v0.46.0_expression_capture_plan.md:
                # assert / constraint / calc / state / action / requirement /
                # satisfy / allocation usages live inside a BehaviorUsageElement
                # when they appear in a definition body. The previous
                # dispatch dropped the entire BehaviorUsageElement.
                if hasattr(sc, 'children'):
                    inner = sc.children
                    inner_name = inner.__class__.__name__
                    c = _load_behavior_child(self, inner, inner_name)
                    if c is not None:
                        c.parent = self
                        self.children.append(c)
            elif class_name == "InterfaceUsage":
                # Same phase 0: interface usages are wrapped as
                # OccurrenceUsageElement -> InterfaceUsage directly (not
                # through StructureUsageElement).
                c = Interface().load_from_grammar(sc)
                c.parent = self
                self.children.append(c)
            elif class_name == "StructureDefinitionElement":
                if hasattr(sc, 'children'):
                    inner = sc.children
                    if inner.__class__.__name__ == "PartDefinition":
                        c = Part(definition=True).load_from_grammar(inner)
                        c.parent = self
                        self.children.append(c)
                    elif inner.__class__.__name__ == "ItemDefinition":
                        c = Item(definition=True).load_from_grammar(inner)
                        c.parent = self
                        self.children.append(c)
                    elif inner.__class__.__name__ == "PortDefinition":
                        c = Port(definition=True).load_from_grammar(inner)
                        c.parent = self
                        self.children.append(c)
            elif class_name == "Definition":
                # Unwrap Definition to get the inner type
                if hasattr(sc, 'body') and hasattr(sc.body, 'children') and sc.body.children:
                    for body_item in sc.body.children:
                        if hasattr(body_item, 'children') and body_item.children:
                            inner = body_item.children[0]
                            if hasattr(inner, 'children'):
                                inner = inner.children
                            if inner.__class__.__name__ == 'PartDefinition':
                                c = Part(definition=True).load_from_grammar(inner)
                            else:
                                c = Item(definition=True).load_from_grammar(inner)
                            c.parent = self
                            self.children.append(c)

        self._extract_specialization_info(grammar)

        return self

    def _extract_specialization_info(self, grammar):
        """Capture Typings / Subsettings / Redefinitions / References names
        from the grammar's feature specialization so ``_typed_by_name`` and
        friends are populated on every usage kind loaded from grammar
        (v0.57.0 — previously only ``Action`` did this, leaving ``Part``,
        ``Attribute``, ``Item``, ``Port``, etc. without typing information
        on the public-API object even though the grammar object kept it).

        Handles both grammar layouts:
          - usage-style: ``grammar.usage.declaration.declaration.specialization``
            (PartUsage, AttributeUsage, ItemUsage, PortUsage, ...)
          - behavior-style: ``grammar.declaration.declaration.declaration.specialization``
            (ActionUsage, ...)

        Idempotent (v0.87.0): re-running on the same object would append
        duplicate names to ``_specializes_names`` and friends (a
        subsetting-only usage has ``_typed_by_name`` None, so callers
        that guard on that attribute alone would re-extract).
        """
        if getattr(self, '_spec_info_extracted', False):
            return
        self._spec_info_extracted = True
        spec = None
        g = getattr(grammar, 'grammar', grammar)
        ud = getattr(g, 'usage', None)
        if ud is not None and getattr(ud, 'declaration', None) is not None:
            d = ud.declaration
            if not hasattr(d, 'declaration'):
                spec = getattr(d, 'specialization', None)
            else:
                inner = getattr(d, 'declaration', None)
                spec = getattr(inner, 'specialization', None) if inner is not None else None
        else:
            node = getattr(g, 'declaration', None)
            for _ in range(3):
                if node is None or hasattr(node, 'specialization'):
                    break
                node = getattr(node, 'declaration', None)
            spec = getattr(node, 'specialization', None) if node is not None else None
        if spec is None:
            return
        for fs in getattr(spec, 'specializations', None) or []:
            rel = getattr(fs, 'relationship', None)
            kind = rel.__class__.__name__ if rel is not None else None
            if kind == 'Typings':
                tb = getattr(rel, 'typing', None)
                for ft in getattr(tb, 'relationships', []) or []:
                    rel2 = getattr(ft, 'relationship', None)
                    ftype = getattr(rel2, 'type', None)
                    qn = getattr(ftype, 'type', None)
                    names = getattr(qn, 'names', None)
                    if names:
                        self._typed_by_name = '::'.join(names)
                        break
                    elements = getattr(ftype, 'elements', None) or []
                    seg_names = []
                    for el in elements:
                        if hasattr(el, 'names') and el.names:
                            seg_names.extend(el.names)
                        elif hasattr(el, 'feature'):
                            for seg in getattr(el.feature, 'children', []) or []:
                                cf = getattr(seg, 'chainingFeature', None)
                                if cf is not None and getattr(cf, 'names', None):
                                    seg_names.extend(cf.names)
                    if seg_names:
                        self._typed_by_name = '.'.join(seg_names)
                        break
            elif kind in ('Subsettings', 'Redefinitions', 'References'):
                target = (
                    self._specializes_names if kind == 'Subsettings'
                    else self._redefined_refs if kind == 'Redefinitions'
                    else self._referenced_refs
                )
                for child in getattr(rel, 'children', None) or []:
                    qn = (
                        getattr(child, 'redefinedFeature', None)
                        or getattr(child, 'referencedFeature', None)
                    )
                    if qn is not None and getattr(qn, 'names', None):
                        target.append('::'.join(qn.names))
                        continue
                    elements = getattr(child, 'elements', None) or []
                    seg_names = []
                    for el in elements:
                        if hasattr(el, 'names') and el.names:
                            seg_names.extend(el.names)
                        elif hasattr(el, 'feature'):
                            for seg in getattr(el.feature, 'children', []) or []:
                                cf = getattr(seg, 'chainingFeature', None)
                                if cf is not None and getattr(cf, 'names', None):
                                    seg_names.extend(cf.names)
                    if seg_names:
                        target.append('.'.join(seg_names))

        return self

    def add_directed_feature(self, direction, name=str(uuidlib.uuid4())):
        """Add a directional reference (in/out/inout) as a child.

        Parameters
        ----------
        direction : str
            One of 'in', 'out', or 'inout'.
        name : str
            Name for the reference. Defaults to a UUID.

        Returns
        -------
        Usage
            Self for chaining.
        """
        self._set_child(DefaultReference()._set_name(name).set_direction(direction))
        return self

    # def modify_directed_feature(self, direction, name):
    #     child = self._get_child(name)
    #     if child is not None:
    #         pass
    #     else:
    #         raise AttributeError("Invalid Feature Name or Chain")


def _load_behavior_child(parent, inner, inner_name):
    """Construct a public-API element for a usage that lives inside a
    ``BehaviorUsageElement`` when it appears in a definition body.

    Phase 0 of docs/v0.46.0_expression_capture_plan.md: this helper
    closes the gap that caused ``assert constraint``, ``constraint``,
    ``calc``, ``state``, ``action``, ``requirement``, ``satisfy``, and
    ``allocate`` usages to be silently dropped when they appeared inside
    a ``part def``, ``item def``, etc. body.

    Parameters
    ----------
    parent : Usage
        The Part / Item / / etc. that owns the new child (for ``.parent``).
    inner : object
        The inner grammar element (e.g. ``AssertConstraintUsage``,
        ``ConstraintUsage``, ``CalculationUsage`` ...). Used for
        ``.grammar`` so the existing round-trip machinery keeps working.
    inner_name : str
        Class name of ``inner`` — selects which public-API class to
        instantiate.

    Returns
    -------
    Usage or None
        A fresh public-API element (e.g. ``Constraint``, ``Calculation``,
        ``State``, ``Action``, ``Requirement``, ``Allocation``) with
        ``.grammar`` wired up and ``.parent`` set. Returns ``None`` if
        the inner kind is unknown to this helper — the caller treats that
        as a no-op.
    """
    def _name_from_declaration(elem):
        """Extract a human-readable name from an element's declaration,
        mirroring the pattern at definition.py:1269-1290.

        Declaration chains differ per kind — e.g. ``ConstraintUsage``
        nests one level deeper than ``Usage``
        (CalculationUsageDeclaration -> UsageDeclaration ->
        FeatureDeclaration -> Identification) — so walk ``.declaration``
        until an Identification is found.
        """
        # AssertConstraintUsage has a different layout: declaration may
        # be wrapped under .usageDeclaration.
        decl = getattr(elem, "declaration", None)
        if decl is not None and callable(getattr(decl, "usageDeclaration", None)) \
                and decl.usageDeclaration():
            inner_decl = decl.usageDeclaration()
            if getattr(inner_decl, "identification", None):
                ident = inner_decl.identification
                if hasattr(ident, "declaredName"):
                    return ident.declaredName
                if hasattr(ident, "name"):
                    name_obj = ident.name()
                    if name_obj:
                        if isinstance(name_obj, list):
                            return name_obj[-1].getText()
                        return name_obj.getText()
        node = decl
        depth = 0
        while node is not None and depth < 4:
            ident = getattr(node, "identification", None)
            if ident is not None:
                declared = getattr(ident, "declaredName", None)
                if declared:
                    return declared
            node = getattr(node, "declaration", None)
            depth += 1
        return None

    # Behavior usages created without load_from_grammar still capture their
    # typing from the grammar's feature specialization (v0.57.0).
    if inner_name == "AssertConstraintUsage":
        c = Constraint()
        c.grammar = inner
        c.name = _name_from_declaration(inner)
        c._extract_specialization_info(inner)
        return c
    if inner_name == "ConstraintUsage":
        c = Constraint()
        c.grammar = inner
        c.name = _name_from_declaration(inner)
        c._extract_specialization_info(inner)
        return c
    if inner_name == "CalculationUsage":
        c = Calculation()
        c.grammar = inner
        c.name = _name_from_declaration(inner)
        c._extract_specialization_info(inner)
        return c
    if inner_name == "StateUsage":
        c = State()
        c.grammar = inner
        c.name = _name_from_declaration(inner)
        c._extract_specialization_info(inner)
        return c
    if inner_name == "ActionUsage":
        c = Action(grammar=inner).load_from_grammar(inner)
        return c
    if inner_name == "RequirementUsage":
        c = Requirement()
        c.grammar = inner
        c.name = _name_from_declaration(inner)
        c._extract_specialization_info(inner)
        return c
    if inner_name == "SatisfyRequirementUsage":
        c = Requirement()
        c.grammar = inner
        c.name = _name_from_declaration(inner)
        c._extract_specialization_info(inner)
        return c
    if inner_name == "VerificationCaseUsage":
        c = VerificationCase()
        c.grammar = inner
        c.name = _name_from_declaration(inner)
        c._extract_specialization_info(inner)
        return c
    if inner_name == "VerifyRequirementUsage":
        c = Requirement()
        c.grammar = inner
        c.name = _name_from_declaration(inner)
        c._extract_specialization_info(inner)
        return c
    if inner_name == "AllocationUsage":
        c = Allocation()
        c.grammar = inner
        c.name = _name_from_declaration(inner)
        c._extract_specialization_info(inner)
        return c
    return None



class Attribute(Usage):
    """SysML v2 Attribute usage/definition.

    Represents a property or characteristic of an element with an optional value.

    Usage:
        Attribute()                                  # attribute ;
        Attribute(name='mass')                       # attribute mass;
        Attribute(definition=True, name='MassValue') # attribute def MassValue;
        Attribute(name='radius').set_value(5 * ureg.metre)  # attribute radius = 5 m;
    """
    sysml_type = 'attribute'
    def __init__(self, definition=False, name=None):
        Usage.__init__(self)

        if definition:
            self.grammar = AttributeDefinition()
        else:
            self.grammar = AttributeUsage()

        if name is not None:
            self._set_name(name)

    def usage_dump(self, child):
        # Override - base output

        # Add children
        body = []
        for abc in self.children:
            body.append(DefinitionBodyItem(abc._get_definition(child="DefinitionBody")).get_definition())
        if len(body) > 0:
            self.grammar.usage.completion.body.body = DefinitionBody(
                {"name": "DefinitionBody", "ownedRelatedElement": body}
            )

        # Add packaging
        package = {
            "name": "NonOccurrenceUsageElement",
            "ownedRelatedElement": self.grammar.get_definition(),
        }

        if child == "DefinitionBody":
            package = {
                "name": "NonOccurrenceUsageMember",
                "prefix": None,
                "ownedRelatedElement": [package],
            }
            package = {"name": "DefinitionBodyItem", "ownedRelationship": [package]}
        else:
            # Add these packets to make this dump without parents
            package = {"name": "UsageElement", "ownedRelatedElement": package}
            package = {
                "name": "PackageMember",
                "ownedRelatedElement": package,
                "prefix": None,
            }
        return package

    def set_value(self, value):
        """Set the value of this attribute with optional unit validation.

        If the attribute is typed by an ISQ type, the unit is validated
        for dimensional conformance. Dimensionless values skip validation.

        Parameters
        ----------
        value : float, int, or pint.Quantity
            The value to set. Non-Quantity values are treated as dimensionless.

        Raises
        ------
        ValueError
            If the attribute is typed and the unit is not conformant to the
            expected ISQ type dimension.

        Examples
        --------
        >>> attr = Attribute(name='mass')
        >>> attr.set_value(5.0 * ureg.kilogram)
        >>> attr.get_value()
        <Quantity(5.0, 'kilogram')>
        """
        if not isinstance(value, pint.Quantity):
            value = value * ureg.dimensionless
        if isinstance(value, pint.Quantity):
            # Validate unit conformance to ISQ type if attribute is typed
            if self.typedby is not None and not value.units.dimensionless:
                type_name = getattr(self.typedby, 'name', None)
                if type_name is not None:
                    # Convert type name to ISQ value type format (e.g., 'mass' -> 'MassValue')
                    isq_type = type_name.capitalize() + 'Value'
                    is_conformant, message = validate_unit_conformance(isq_type, value)
                    if not is_conformant:
                        raise ValueError(message)

            # Only add units if not dimensionless
            if not value.units.dimensionless:
                package_units = {
                    "name": "QualifiedName",
                    "names": [str(value.units)],
                }
                package_units = {
                    "name": "FeatureReferenceMember",
                    "memberElement": package_units,
                }
                package_units = {
                    "name": "FeatureReferenceExpression",
                    "ownedRelationship": [package_units],
                }
                package_units = {
                    "name": "BaseExpression",
                    "ownedRelationship": package_units,
                }
                package_units = {
                    "name": "PrimaryExpression",
                    "operand": [],
                    "base": package_units,
                    "operator": [],
                    "ownedRelationship1": [],
                    "ownedRelationship2": [],
                }
                package_units = {
                    "name": "ExtentExpression",
                    "operator": "",
                    "ownedRelationship": [],
                    "primary": package_units,
                }
                package_units = {
                    "name": "UnaryExpression",
                    "operand": [],
                    "operator": None,
                    "extent": package_units,
                }
                package_units = {
                    "name": "ExponentiationExpression",
                    "operand": [],
                    "operator": [],
                    "unary": package_units,
                }
                package_units = {
                    "name": "MultiplicativeExpression",
                    "operation": [],
                    "exponential": package_units,
                }
                package_units = {
                    "name": "AdditiveExpression",
                    "operation": [],
                    "multiplicitive": package_units,
                }
                package_units = {
                    "name": "RangeExpression",
                    "operand": None,
                    "additive": package_units,
                }
                package_units = {
                    "name": "RelationalExpression",
                    "operation": [],
                    "range": package_units,
                }
                package_units = {
                    "name": "ClassificationExpression",
                    "operand": [],
                    "operator": None,
                    "ownedRelationship": [],
                    "relational": package_units,
                }
                package_units = {
                    "name": "EqualityExpression",
                    "operation": [],
                    "classification": package_units,
                }
                package_units = {
                    "name": "AndExpression",
                    "operation": [],
                    "equality": package_units,
                }
                package_units = {
                    "name": "XorExpression",
                    "operand": [],
                    "operator": [],
                    "and": package_units,
                }
                package_units = {
                    "name": "OrExpression",
                    "xor": package_units,
                    "operand": [],
                    "operator": [],
                }
                package_units = {
                    "name": "ImpliesExpression",
                    "operand": [],
                    "operator": [],
                    "or": package_units,
                }
                package_units = {
                    "name": "NullCoalescingExpression",
                    "implies": package_units,
                    "operator": [],
                    "operand": [],
                }
                package_units = {
                    "name": "ConditionalExpression",
                    "operator": None,
                    "operand": [package_units],
                }
                package_units = {"name": "OwnedExpression", "expression": package_units}
                package_units = {
                    "name": "SequenceExpression",
                    "operation": [],
                    "ownedRelationship": package_units,
                }
                package_units = [package_units]
                operator = ["["]
            else:
                package_units = []
                operator = []

            package = {
                "name": "BaseExpression",
                "ownedRelationship": {
                    "name": "LiteralInteger",
                    "value": str(value.magnitude),
                },
            }
            package = {
                "name": "PrimaryExpression",
                "operand": package_units,
                "base": package,
                "operator": operator,
                "ownedRelationship1": [],
                "ownedRelationship2": [],
            }
            package = {
                "name": "ExtentExpression",
                "operator": "",
                "ownedRelationship": [],
                "primary": package,
            }
            package = {
                "name": "UnaryExpression",
                "operand": [],
                "operator": None,
                "extent": package,
            }
            package = {
                "name": "ExponentiationExpression",
                "operand": [],
                "operator": [],
                "unary": package,
            }
            package = {
                "name": "MultiplicativeExpression",
                "operation": [],
                "exponential": package,
            }
            package = {
                "name": "AdditiveExpression",
                "operation": [],
                "multiplicitive": package,
            }
            package = {
                "name": "RangeExpression",
                "operand": None,
                "additive": package,
            }
            package = {
                "name": "RelationalExpression",
                "operation": [],
                "range": package,
            }
            package = {
                "name": "ClassificationExpression",
                "operand": [],
                "operator": None,
                "ownedRelationship": [],
                "relational": package,
            }
            package = {
                "name": "EqualityExpression",
                "operation": [],
                "classification": package,
            }
            package = {
                "name": "AndExpression",
                "operation": [],
                "equality": package,
            }
            package = {
                "name": "XorExpression",
                "operand": [],
                "operator": [],
                "and": package,
            }
            package = {
                "name": "OrExpression",
                "xor": package,
                "operand": [],
                "operator": [],
            }
            package = {
                "name": "ImpliesExpression",
                "operand": [],
                "operator": [],
                "or": package,
            }
            package = {
                "name": "NullCoalescingExpression",
                "implies": package,
                "operator": [],
                "operand": [],
            }
            package = {
                "name": "ConditionalExpression",
                "operator": None,
                "operand": [package],
            }
            package = {"name": "OwnedExpression", "expression": package}
            package = {
                "name": "FeatureValue",
                "isDefault": False,
                "isEqual": False,
                "isInitial": False,
                "ownedRelatedElement": package,
            }
            package = {"name": "ValuePart", "ownedRelationship": [package]}
            self.grammar.usage.completion.valuepart = ValuePart(package)
            # value.unit

        return self

    def get_value(self):
        """Get the current value of this attribute as a pint.Quantity.

        Returns
        -------
        pint.Quantity
            The attribute's value with units. Returns dimensionless if no
            value has been set.
        """
        valuepart = self.grammar.usage.completion.valuepart
        if valuepart is None:
            raise AttributeError("No valuepart found in grammar")
        
        feature_value = valuepart.relationships[0]
        primary = (
            feature_value.element.expression.operands[0]
            .implies.orexpression.xor.andexpression.equality.classification.relational.range.additive.left_hand.exponential.unary.extent.primary
        )
        
        base = primary.base.relationship
        base_name = base.__class__.__name__
        
        has_unit = hasattr(primary, 'operand') and primary.operand and len(primary.operand) > 0
        
        if has_unit:
            unit = primary.operand[0]
            unit_name = None
            if hasattr(unit, 'relationship'):
                unit_expr = unit.relationship.expression
                if hasattr(unit_expr, 'operands') and unit_expr.operands:
                    primary2 = unit_expr.operands[0]
                    if hasattr(primary2, 'implies'):
                        primary2 = primary2.implies.orexpression.xor.andexpression.equality.classification.relational.range.additive.left_hand.exponential.unary.extent.primary
                    if hasattr(primary2, 'base'):
                        unit_rel = primary2.base.relationship
                        if hasattr(unit_rel, 'children') and unit_rel.children:
                            unit_name = unit_rel.children[0].memberElement.dump()
                        elif hasattr(unit_rel, 'dump'):
                            unit_name = unit_rel.dump()
            if unit_name:
                if base_name == "LiteralInteger":
                    return int(base.dump()) * ureg(unit_name)
                elif base_name == "LiteralReal":
                    return float(base.dump()) * ureg(unit_name)
        
        base_dump = base.dump()
        
        if base_name == "LiteralString":
            return base_dump.strip('"')
        elif base_name == "LiteralInteger":
            return int(base_dump)
        elif base_name == "LiteralReal":
            return float(base_dump)
        elif base_name in ("LiteralTrue", "LiteralFalse"):
            return base_name == "LiteralTrue"
        elif base_name == "LiteralNull":
            return None
        elif base_name == "FeatureReferenceExpression":
            return base_dump
        else:
            return base_dump


class Part(Usage):
    """SysML v2 Part usage/definition.

    Represents a physical or conceptual component within a system structure.

    Usage:
        Part()                                 # part ;
        Part(name='engine')                    # part engine;
        Part(definition=True, name='Engine')   # part def Engine;
        Part(name='wheel', shortname='w')      # part w : Wheel;
    """
    sysml_type = 'part'
    def __init__(self, definition=False, name=None, shortname=None):
        """Initialize a Part usage or definition.

        Parameters
        ----------
        definition : bool
            If True, creates a PartDefinition. Otherwise creates PartUsage.
        name : str, optional
            Element name.
        shortname : str, optional
            Abbreviated name (rendered as `<shortname>`).
        """
        Usage.__init__(self)
        if definition:
            self.grammar = PartDefinition()
        else:
            self.grammar = PartUsage()

        if name is not None:
            self._set_name(name)
        if shortname is not None:
            self._set_name(shortname, short=True)


class Item(Usage):
    """SysML v2 Item usage/definition.

    Represents a discrete entity that can flow through connectors or be
    contained within parts.

    Usage:
        Item()                                # item ;
        Item(name='fuel')                     # item fuel;
        Item(definition=True, name='Fuel')    # item def Fuel;
    """
    sysml_type = 'item'
    def __init__(self, definition=False, name=None, shortname=None):
        """Initialize an Item usage or definition.

        Parameters
        ----------
        definition : bool
            If True, creates an ItemDefinition. Otherwise creates ItemUsage.
        name : str, optional
            Element name.
        shortname : str, optional
            Abbreviated name.
        """
        Usage.__init__(self)
        if definition:
            self.grammar = ItemDefinition()
        else:
            self.grammar = ItemUsage()

        if name is not None:
            self._set_name(name)
        if shortname is not None:
            self._set_name(shortname, short=True)


class Port(Usage):
    """SysML v2 Port usage/definition.

    Represents an interaction point through which a part exchanges flows,
    signals, or other interactions with its environment.

    Usage:
        Port()                                  # port ;
        Port(name='input')                      # port input;
        Port(definition=True, name='PowerPort') # port def PowerPort;
        Port(name='ctrl', conjugated=True)      # port ~ctrl;  (conjugated)
    """
    sysml_type = 'port'
    def __init__(self, definition=False, name=None, shortname=None, conjugated=False):
        """Initialize a Port usage or definition.

        Parameters
        ----------
        definition : bool
            If True, creates a PortDefinition. Otherwise creates PortUsage.
        name : str, optional
            Element name.
        shortname : str, optional
            Abbreviated name.
        conjugated : bool
            If True, marks the port as conjugated (reversed direction).
        """
        Usage.__init__(self)
        if definition:
            self.grammar = PortDefinition()
        else:
            self.grammar = PortUsage()

        self.is_definition = definition
        self.conjugated = conjugated
        self.port_attributes = []  # list of (name, type_name)
        self.port_in_items = []  # list of (name, type_name)
        self.port_out_items = []  # list of (name, type_name)
        self.port_inout_items = []  # list of (name, type_name)

        if name is not None:
            self._set_name(name)
        if shortname is not None:
            self._set_name(shortname, short=True)

    def add_attribute(self, name, type_name=None):
        """Add an attribute to the port definition.

        Args:
            name: Attribute name
            type_name: Optional type
        """
        self.port_attributes.append((name, type_name))
        return self

    def add_in_item(self, name, type_name=None):
        """Add an input item to the port definition.

        Args:
            name: Item name
            type_name: Optional type
        """
        self.port_in_items.append((name, type_name))
        return self

    def add_out_item(self, name, type_name=None):
        """Add an output item to the port definition.

        Args:
            name: Item name
            type_name: Optional type
        """
        self.port_out_items.append((name, type_name))
        return self

    def add_inout_item(self, name, type_name=None):
        """Add an inout item to the port definition.

        Args:
            name: Item name
            type_name: Optional type
        """
        self.port_inout_items.append((name, type_name))
        return self

    def dump(self, child=None):
        # Check if we have enhanced features
        has_port_features = (
            self.port_attributes or self.port_in_items
            or self.port_out_items or self.port_inout_items
        )

        if not has_port_features:
            # Use standard grammar dump for basic ports
            return classtree(self._get_definition(child)).dump()

        # Enhanced dump with in/out items
        keyword = "port def" if self.is_definition else "port"
        name_str = getattr(self, 'name', "") or ""

        body_items = []
        for attr_name, attr_type in self.port_attributes:
            if attr_type:
                body_items.append(f"attribute {attr_name} : {attr_type}")
            else:
                body_items.append(f"attribute {attr_name}")

        for item_name, item_type in self.port_out_items:
            if item_type:
                body_items.append(f"out item {item_name} : {item_type}")
            else:
                body_items.append(f"out item {item_name}")

        for item_name, item_type in self.port_in_items:
            if item_type:
                body_items.append(f"in item {item_name} : {item_type}")
            else:
                body_items.append(f"in item {item_name}")

        for item_name, item_type in self.port_inout_items:
            if item_type:
                body_items.append(f"inout item {item_name} : {item_type}")
            else:
                body_items.append(f"inout item {item_name}")

        return f"{keyword} {name_str} {{\n   " + ";\n   ".join(body_items) + ";\n}"


class Interface(Usage):
    """SysML v2 Interface usage/definition.

    Represents a set of interaction points (ends) and the connections
    between them, defining how parts interact.

    Usage:
        Interface()                                    # interface ;
        Interface(name='PowerInterface')               # interface PowerInterface;
        Interface(definition=True, name='DataLink')    # interface def DataLink;
    """
    sysml_type = 'interface'
    def __init__(self, definition=False, name=None, shortname=None):
        """Initialize an Interface usage or definition.

        Parameters
        ----------
        definition : bool
            If True, creates an interface definition. Otherwise creates usage.
        name : str, optional
            Element name.
        shortname : str, optional
            Abbreviated name.
        """
        # Base-Usage state — see Requirement.__init__ (v0.82.0).
        Usage.__init__(self)
        self.is_definition = definition
        self.name = name if name else str(uuidlib.uuid4())
        self.children = []
        self.typedby = None
        self.parent = None
        self.grammar = None
        self.iface_shortname = shortname
        self.ends = []  # list of (name, type_name, multiplicity, children)
        self.iface_connections = []  # list of (from_path, to_path)

        if definition:
            self.keyword = "interface def"
        else:
            self.keyword = "interface"

    def add_end(self, name, type_name=None, multiplicity=None):
        """Add an end to the interface definition.

        Args:
            name: End name
            type_name: Optional type (e.g., 'FuelOutPort')
            multiplicity: Optional multiplicity (e.g., '1', '1..*')
        """
        self.ends.append((name, type_name, multiplicity))
        return self

    def add_connection(self, from_path, to_path):
        """Add a connection between ends.

        Args:
            from_path: Source path (e.g., 'suppliedBy.hot')
            to_path: Target path (e.g., 'deliveredTo.hot')
        """
        self.iface_connections.append((from_path, to_path))
        return self

    def _set_typed_by(self, typed):
        """Set typing (`:`) for interface usage."""
        self._typed_by_name = typed.name if hasattr(typed, 'name') else str(typed)
        return self

    set_typed_by = _set_typed_by

    def _set_specializes(self, *parents):
        """Set specialization (`:>`) for interface definitions."""
        self._specializes_names = [
            p.name if hasattr(p, 'name') else str(p) for p in parents
        ]
        return self

    set_specializes = _set_specializes

    def dump(self):
        name_str = getattr(self, 'name', "") or ""
        keyword = getattr(self, 'keyword', 'interface')

        # Build type/specialization suffix
        suffix_parts = []
        if getattr(self, '_typed_by_name', None):
            suffix_parts.append(f" : {self._typed_by_name}")
        if getattr(self, '_specializes_names', None):
            suffix_parts.append(" :> " + ", ".join(self._specializes_names))
        if getattr(self, '_redefined_refs', None):
            suffix_parts.append(" :>> " + ", ".join(self._redefined_refs))
        if getattr(self, '_referenced_refs', None):
            suffix_parts.append(" ::> " + ", ".join(self._referenced_refs))
        type_suffix = "".join(suffix_parts)

        body_items = []

        for end_name, end_type, end_mult in self.ends:
            mult_str = f"[{end_mult}]" if end_mult else ""
            if end_type:
                body_items.append(f"end {end_name} : {end_type}{mult_str};")
            else:
                body_items.append(f"end {end_name}{mult_str};")

        for from_path, to_path in self.iface_connections:
            body_items.append(f"connect {from_path} to {to_path};")

        if body_items:
            body = " {\n   " + "\n   ".join(body_items) + "\n}"
            return f"{keyword} {name_str}{type_suffix}{body}"
        else:
            return f"{keyword} {name_str}{type_suffix};"

    def load_from_grammar(self, grammar):
        """Load interface from a parsed grammar object.
        
        Parameters
        ----------
        grammar : InterfaceUsage or InterfaceDefinition
            Parsed grammar object.
        
        Returns
        -------
        Interface
            Self for chaining.
        """
        self.grammar = grammar
        
        class_name = grammar.__class__.__name__
        if class_name == "InterfaceDefinition":
            self.is_definition = True
            self.keyword = "interface def"
            if hasattr(grammar, 'declaration') and grammar.declaration:
                if hasattr(grammar.declaration, 'identification') and grammar.declaration.identification:
                    self.name = grammar.declaration.identification.declaredName
        else:
            # InterfaceUsage
            self.is_definition = False
            self.keyword = "interface"
            if hasattr(grammar, 'declaration') and grammar.declaration:
                decl = grammar.declaration
                if hasattr(decl, 'declaration') and decl.declaration:
                    inner_decl = decl.declaration
                    if hasattr(inner_decl, 'declaration') and inner_decl.declaration:
                        feat_decl = inner_decl.declaration
                        if hasattr(feat_decl, 'identification') and feat_decl.identification:
                            self.name = feat_decl.identification.declaredName

        self._extract_specialization_info(grammar)

        return self


class Action(Usage):
    """SysML v2 Action usage/definition.

    Represents a behavior that transforms inputs to outputs, potentially
    with nested sub-actions and control flow.

    Usage:
        Action()                                  # action ;
        Action(name='compute')                    # action compute;
        Action(definition=True, name='Compute')   # action def Compute;
        Action(name='start', shortname='s')       # action s : StartAction;
    """
    sysml_type = 'action'
    def __init__(self, definition=False, name=None, shortname=None, grammar=None):
        """Initialize an Action usage or definition.

        Parameters
        ----------
        definition : bool
            If True, creates an ActionDefinition. Otherwise creates ActionUsage.
        name : str, optional
            Element name.
        shortname : str, optional
            Abbreviated name.
        grammar : object, optional
            Pre-parsed grammar object (used by load_from_grammar).
        """
        if grammar is not None:
            self.grammar = grammar
        else:
            # Initialize grammar properly (like Part does)
            if definition:
                self.grammar = ActionDefinition()
                self.grammar.declaration.identification.declaredName = name if name else None
            else:
                self.grammar = ActionUsage(None)
                if self.grammar.declaration and hasattr(self.grammar.declaration, 'declaration') and self.grammar.declaration.declaration:
                    if hasattr(self.grammar.declaration.declaration, 'identification') and self.grammar.declaration.declaration.identification:
                        self.grammar.declaration.declaration.identification.declaredName = name if name else None
        
        self.is_definition = definition
        self.action_shortname = shortname
        self.name = name if name else str(uuidlib.uuid4())
        self.children = []
        self.typedby = None
        self.parent = None
        self.action_inputs = []  # List of (name, type_name)
        self.action_outputs = []
        self._succession_source = None
        self._succession_targets = []
        self._succession_condition = None
        self._control_flow_nodes = []
        # Re-declaration chains captured from grammar (v0.41.0)
        self._typed_by_name = None
        self._specializes_names = []
        self._redefined_refs = []
        self._referenced_refs = []
        
        if definition:
            self.keyword = "action def"
        else:
            self.keyword = "action"

    def add_input(self, name, type_name=None):
        """Add an input parameter (in) to the action.
        
        Args:
            name: Name of the input
            type_name: Optional type (e.g., 'Scene')
        """
        self.action_inputs.append((name, type_name))
        return self
    
    def add_output(self, name, type_name=None):
        """Add an output parameter (out) to the action.
        
        Args:
            name: Name of the output  
            type_name: Optional type (e.g., 'Image')
        """
        self.action_outputs.append((name, type_name))
        return self

    def _get_definition(self, child=None):
        if self.is_definition:
            keyword = "action def"
        else:
            keyword = "action"
        
        decl = {
            "name": "UsageDeclaration",
            "identification": {
                "name": "Identification",
                "declaredName": self.name if self.name else "",
                "declaredShortName": None
            }
        }
        
        # Build action body with in/out parameters
        body_items = []
        
        # Add inputs
        for inp_name, inp_type in self.action_inputs:
            if inp_type:
                item = f"in {inp_name} : {inp_type};"
            else:
                item = f"in {inp_name};"
            body_items.append(item)
        
        # Add outputs  
        for out_name, out_type in self.action_outputs:
            if out_type:
                item = f"out {out_name} : {out_type};"
            else:
                item = f"out {out_name};"
            body_items.append(item)
        
        body = {"name": "ActionBody", "items": body_items}
        
        if self.is_definition:
            grammar_type = "ActionDefinition"
        else:
            grammar_type = "ActionUsage"
        
        return {
            "name": grammar_type,
            "declaration": decl,
            "body": body
        }

    def load_from_grammar(self, grammar):
        # Set the grammar
        self.grammar = grammar
        
        self.is_definition = False
        self.action_inputs = []
        self.action_outputs = []
        self._nested_actions = []
        
        # Check for 'declaration' directly (for definitions like ActionDefinition, RequirementDefinition)
        decl = getattr(grammar, 'declaration', None)
        if decl and hasattr(decl, 'identification') and decl.identification:
            self.name = decl.identification.declaredName
            self.is_definition = True
            self.keyword = "action def"
        elif hasattr(grammar, 'declaration') and grammar.declaration:
            # Handle nested declaration structure (ActionUsageDeclaration -> UsageDeclaration -> FeatureDeclaration)
            decl = getattr(grammar.declaration, 'declaration', None)
            if decl:
                # Try nested: declaration.declaration.declaration.identification (for ANTLR)
                nested_decl = getattr(decl, 'declaration', None)
                if nested_decl and hasattr(nested_decl, 'identification') and nested_decl.identification:
                    self.name = nested_decl.identification.declaredName
                    self.is_definition = False
                    self.keyword = "action"
                elif hasattr(decl, 'identification') and decl.identification:
                    self.name = decl.identification.declaredName
                    self.is_definition = False
                    self.keyword = "action"
        
        # Extract parameters and nested actions from body
        body = getattr(grammar, 'body', None)
        if body and hasattr(body, 'children'):
            for item in body.children:
                if hasattr(item, 'children'):
                    for child in item.children:
                        child_name = child.__class__.__name__
                        # Extract in/out parameters from NonOccurrenceUsageMember -> DefaultReferenceUsage
                        if child_name == "NonOccurrenceUsageMember":
                            self._extract_parameter_from_non_occurrence(child)
                        elif child_name == "BehaviorUsageMember":
                            self._extract_behavior_usage(child)
                        elif child_name == "ActionNodeMember":
                            self._extract_nested_action(child)
                        elif child_name == "InitialNodeMember":
                            self._extract_initial_node(child)
                        elif child_name == "ActionTargetSuccessionMember":
                            self._extract_action_target_succession(child)
                        elif child_name == "GuardedSuccessionMember":
                            self._extract_guarded_succession(child)

        self._extract_specialization_info(grammar)

        return self

    def _extract_initial_node(self, node):
        """Extract the source name from an InitialNodeMember."""
        if hasattr(node, 'child') and node.child:
            name = getattr(node.child, 'declaredName', None)
            if name:
                if not hasattr(self, '_succession_source'):
                    self._succession_source = name
    
    def _extract_action_target_succession(self, node):
        """Extract the target name from an ActionTargetSuccessionMember."""
        if hasattr(node, 'child') and node.child:
            name = getattr(node.child, 'declaredName', None)
            if name:
                if not hasattr(self, '_succession_targets'):
                    self._succession_targets = []
                self._succession_targets.append(name)
    
    def _extract_guarded_succession(self, node):
        """Extract source, condition, target from a GuardedSuccessionMember."""
        if hasattr(node, 'child') and node.child:
            gs = node.child
            source = getattr(gs, 'sourceName', None)
            condition = getattr(gs, 'condition', None)
            target = getattr(gs, 'targetName', None)
            self._succession_source = source
            self._succession_condition = condition
            if not hasattr(self, '_succession_targets'):
                self._succession_targets = []
            if target:
                self._succession_targets.append(target)
    
    def _extract_parameter_from_non_occurrence(self, non_occ_member):
        """Extract in/out parameter from NonOccurrenceUsageMember -> NonOccurrenceUsageElement -> DefaultReferenceUsage."""
        if hasattr(non_occ_member, 'children'):
            children = non_occ_member.children
            if not isinstance(children, list):
                children = [children]
            for elem in children:
                # elem is NonOccurrenceUsageElement
                if hasattr(elem, 'children'):
                    # elem.children is DefaultReferenceUsage (not a list)
                    usage = elem.children
                    if isinstance(usage, list):
                        usage = usage[0] if usage else None
                    if usage and hasattr(usage, 'declaration') and usage.declaration:
                        # UsageDeclaration has a 'declaration' attribute which is FeatureDeclaration
                        usage_decl = usage.declaration
                        if hasattr(usage_decl, 'declaration') and usage_decl.declaration:
                            feat_decl = usage_decl.declaration
                            if hasattr(feat_decl, 'identification') and feat_decl.identification:
                                name = feat_decl.identification.declaredName
                                # Extract direction from prefix (RefPrefix has direction directly)
                                direction = None
                                if hasattr(usage, 'prefix') and usage.prefix:
                                    prefix = usage.prefix
                                    # RefPrefix has direction directly
                                    if hasattr(prefix, 'direction') and prefix.direction:
                                        dir_obj = prefix.direction
                                        if hasattr(dir_obj, 'isIn') and dir_obj.isIn:
                                            direction = 'in'
                                        elif hasattr(dir_obj, 'isOut') and dir_obj.isOut:
                                            direction = 'out'
                                    # OccurrenceUsagePrefix has nested prefix
                                    elif hasattr(prefix, 'prefix') and prefix.prefix:
                                        inner_prefix = prefix.prefix
                                        if hasattr(inner_prefix, 'direction') and inner_prefix.direction:
                                            dir_obj = inner_prefix.direction
                                            if hasattr(dir_obj, 'isIn') and dir_obj.isIn:
                                                direction = 'in'
                                            elif hasattr(dir_obj, 'isOut') and dir_obj.isOut:
                                                direction = 'out'
                                # Extract type from specialization
                                type_name = None
                                if hasattr(feat_decl, 'specialization') and feat_decl.specialization:
                                    for spec in feat_decl.specialization.specializations:
                                        if hasattr(spec, 'relationship') and spec.relationship:
                                            rel = spec.relationship
                                            type_name = self._extract_type_from_typings(rel)
                                if direction == 'in' and name:
                                    self.action_inputs.append((name, type_name))
                                elif direction == 'out' and name:
                                    self.action_outputs.append((name, type_name))
    
    def _extract_type_from_typings(self, rel):
        """Extract type name from a Typings relationship."""
        if not hasattr(rel, 'typing') or not rel.typing:
            return None
        
        typing = rel.typing
        
        # Direct type attribute (simple case)
        if hasattr(typing, 'type') and typing.type:
            return typing.type.dump()
        
        # TypedBy case: typing.relationships -> FeatureTyping -> relationship -> OwnedFeatureTyping -> type
        if hasattr(typing, 'relationships') and typing.relationships:
            for ft in typing.relationships:
                if hasattr(ft, 'relationship') and ft.relationship:
                    owned = ft.relationship
                    if hasattr(owned, 'type') and owned.type:
                        return owned.type.dump()
        
        return None
    
    def _extract_nested_action(self, action_node_member):
        """Extract nested action from ActionNodeMember."""
        if hasattr(action_node_member, 'children'):
            node = action_node_member.children
            if hasattr(node, 'children'):
                action_node = node.children
                node_type = action_node.__class__.__name__
                
                # Handle control flow nodes (if/while/for/control)
                if node_type in ("IfNode", "WhileLoopNode", "ForLoopNode", "ControlNode"):
                    self._control_flow_nodes.append(action_node)
                    self.children.append(action_node)
                    return
                
                # Handle SendNode - extract signal name from nodeParameter
                if node_type == "SendNode":
                    name = None
                    if hasattr(action_node, 'declaration') and action_node.declaration:
                        decl = action_node.declaration
                        if hasattr(decl, 'nodeParameter') and decl.nodeParameter:
                            name = self._extract_signal_name_from_node_parameter(decl.nodeParameter)
                    if name:
                        nested_action = Action(name=f"send_{name}")
                        nested_action.load_from_grammar(action_node)
                        self._nested_actions.append(nested_action)
                        self.children.append(nested_action)
                    return
                
                # Handle AcceptNode - extract event name from acceptParameter
                if node_type == "AcceptNode":
                    name = None
                    if hasattr(action_node, 'declaration') and action_node.declaration:
                        decl = action_node.declaration
                        if hasattr(decl, 'acceptParameter') and decl.acceptParameter:
                            name = self._extract_event_name_from_accept_parameter(decl.acceptParameter)
                    if name:
                        nested_action = Action(name=f"accept_{name}")
                        nested_action.load_from_grammar(action_node)
                        self._nested_actions.append(nested_action)
                        self.children.append(nested_action)
                    return
                
                # Handle action nodes with declaration (send/accept/assignment)
                if hasattr(action_node, 'declaration'):
                    decl = action_node.declaration
                    if hasattr(decl, 'identification') and decl.identification:
                        name = decl.identification.declaredName
                        if name:
                            nested_action = Action(name=name)
                            nested_action.load_from_grammar(action_node)
                            self._nested_actions.append(nested_action)
                            self.children.append(nested_action)
    
    def _extract_signal_name_from_node_parameter(self, node_param):
        """Extract signal/event name from NodeParameterMember."""
        if not hasattr(node_param, 'children') or not node_param.children:
            return None
        # NodeParameterMember.children -> NodeParameter
        node_parameter = node_param.children
        if not hasattr(node_parameter, 'children') or not node_parameter.children:
            return None
        # NodeParameter.children -> FeatureBinding
        feature_binding = node_parameter.children
        if not hasattr(feature_binding, 'children') or not feature_binding.children:
            return None
        # FeatureBinding.children -> OwnedExpression
        owned_expr = feature_binding.children
        if not hasattr(owned_expr, 'expression') or not owned_expr.expression:
            return None
        # Navigate through expression tree to find FeatureReferenceMember
        expr = owned_expr.expression
        depth = 0
        while expr and depth < 30:
            depth += 1
            # Check for PrimaryExpression with FeatureReferenceMember
            if hasattr(expr, 'primary') and expr.primary:
                primary = expr.primary
                if hasattr(primary, 'base') and primary.base:
                    base = primary.base
                    # BaseExpression has 'relationship' not 'ownedRelationship'
                    if hasattr(base, 'relationship') and base.relationship:
                        fr_expr = base.relationship
                        # FeatureReferenceExpression has 'children' list
                        if hasattr(fr_expr, 'children') and fr_expr.children and len(fr_expr.children) > 0:
                            fr_member = fr_expr.children[0]
                            if hasattr(fr_member, 'memberElement') and fr_member.memberElement:
                                qname = fr_member.memberElement
                                if hasattr(qname, 'names') and qname.names and len(qname.names) > 0:
                                    return qname.names[-1]
            # Navigate through expression chain - try all possible attributes
            next_expr = None
            for attr in ['operands', 'operand', 'operations', 'left_hand', 'right_hand', 'or', 'orexpression', 'xor', 'andexpression', 'and', 
                        'equality', 'classification', 'relational', 'range', 'additive', 'multiplicitive', 
                        'exponential', 'unary', 'extent', 'implies']:
                if hasattr(expr, attr):
                    val = getattr(expr, attr)
                    if val:
                        if isinstance(val, list) and len(val) > 0:
                            next_expr = val[0]
                            break
                        elif not isinstance(val, list):
                            next_expr = val
                            break
            expr = next_expr
        return None
    
    def _extract_event_name_from_accept_parameter(self, accept_param):
        """Extract event name from AcceptParameterPart."""
        if not hasattr(accept_param, 'children') or not accept_param.children or len(accept_param.children) == 0:
            return None
        # AcceptParameterPart.children[0] -> PayloadParameterMember
        payload_param_member = accept_param.children[0]
        if not hasattr(payload_param_member, 'children') or not payload_param_member.children:
            return None
        # PayloadParameterMember.children -> PayloadParameter
        payload_param = payload_param_member.children
        if not hasattr(payload_param, 'children') or not payload_param.children:
            return None
        # PayloadParameter.children -> PayloadFeature
        payload_feature = payload_param.children
        if not hasattr(payload_feature, 'children') or not payload_feature.children:
            return None
        # PayloadFeature.children -> OwnedFeatureTyping
        owned_typing = payload_feature.children
        if not hasattr(owned_typing, 'type') or not owned_typing.type:
            return None
        # OwnedFeatureTyping.type -> FeatureType
        feature_type = owned_typing.type
        if not hasattr(feature_type, 'type') or not feature_type.type:
            return None
        # FeatureType.type -> QualifiedName
        qname = feature_type.type
        if hasattr(qname, 'names') and qname.names and len(qname.names) > 0:
            return qname.names[-1]
        return None
    
    def _extract_behavior_usage(self, behavior_usage_member):
        """Extract behavior usage (nested action/state) from BehaviorUsageMember."""
        if hasattr(behavior_usage_member, 'children'):
            for child in behavior_usage_member.children:
                if hasattr(child, 'children'):
                    # child is BehaviorUsageElement, its children contain the actual usage
                    behavior_element = child.children
                    if isinstance(behavior_element, list):
                        usage_list = behavior_element
                    else:
                        usage_list = [behavior_element]
                    for usage in usage_list:
                        if not usage:
                            continue
                        # Check if BehaviorUsageElement has children with the actual usage
                        if hasattr(usage, 'children') and usage.children:
                            inner = usage.children
                            if isinstance(inner, list):
                                inner_list = inner
                            else:
                                inner_list = [inner]
                            for actual_usage in inner_list:
                                if not actual_usage:
                                    continue
                                self._process_nested_usage(actual_usage)
                        elif hasattr(usage, 'declaration'):
                            self._process_nested_usage(usage)
    
    def _process_nested_usage(self, usage):
        """Process a nested usage element (ActionUsage, StateUsage, etc.)."""
        usage_type = usage.__class__.__name__
        
        # Get name from declaration
        name = None
        if hasattr(usage, 'declaration') and usage.declaration:
            decl = usage.declaration
            # Handle nested declaration structure
            while hasattr(decl, 'declaration') and not hasattr(decl, 'identification'):
                decl = decl.declaration
            if hasattr(decl, 'identification') and decl.identification:
                name = decl.identification.declaredName
        
        if not name:
            return
        
        if 'Action' in usage_type:
            nested_action = Action(name=name)
            nested_action.parent = self
            nested_action.load_from_grammar(usage)
            self._nested_actions.append(nested_action)
            self.children.append(nested_action)
    
    def _get_definition(self, child=None):
        # Sync self.name to grammar before getting definition
        if hasattr(self.grammar, 'declaration') and hasattr(self.grammar.declaration, 'identification'):
            self.grammar.declaration.identification.declaredName = self.name
        
        # Get the grammar's get_definition output
        if hasattr(self.grammar, 'get_definition'):
            grammar_def = self.grammar.get_definition()
        else:
            # Fallback - shouldn't happen now
            grammar_def = {"name": "ActionDefinition", "declaration": {}, "body": {}}
        
        if self.is_definition:
            package = {
                "name": "DefinitionElement",
                "ownedRelatedElement": grammar_def,
            }
        else:
            package = {
                "name": "BehaviorUsageElement",
                "ownedRelationship": grammar_def,
            }
            package = {"name": "OccurrenceUsageElement", "ownedRelatedElement": package}

        if child == "DefinitionBody":
            if self.is_definition:
                package = {
                    "name": "DefinitionMember",
                    "prefix": None,
                    "ownedRelatedElement": [package],
                }
            else:
                package = {
                    "name": "OccurrenceUsageMember",
                    "prefix": None,
                    "ownedRelatedElement": [package],
                }
            package = {"name": "DefinitionBodyItem", "ownedRelationship": [package]}
        elif child == "PackageBody" or child == None:
            if self.is_definition:
                package = {
                    "name": "PackageMember",
                    "ownedRelatedElement": package,
                    "prefix": None,
                }
            else:
                package = {"name": "UsageElement", "ownedRelatedElement": package}
                package = {
                    "name": "PackageMember",
                    "ownedRelatedElement": package,
                    "prefix": None,
                }

        return package

    def dump(self):
        name_str = getattr(self, 'name', "") or ""
        keyword = getattr(self, 'keyword', 'action')
        
        # Build output with in/out parameters
        parts = [keyword, name_str]
        
        # Add in/out parameters
        params = []
        for inp_name, inp_type in self.action_inputs:
            if inp_type:
                params.append(f"in {inp_name} : {inp_type}")
            else:
                params.append(f"in {inp_name}")
        
        for out_name, out_type in self.action_outputs:
            if out_type:
                params.append(f"out {out_name} : {out_type}")
            else:
                params.append(f"out {out_name}")
        
        # Build type/specialization suffix
        suffix_parts = []
        if getattr(self, '_typed_by_name', None):
            suffix_parts.append(f" : {self._typed_by_name}")
        if getattr(self, '_specializes_names', None):
            suffix_parts.append(" :> " + ", ".join(self._specializes_names))
        if getattr(self, '_redefined_refs', None):
            suffix_parts.append(" :>> " + ", ".join(self._redefined_refs))
        if getattr(self, '_referenced_refs', None):
            suffix_parts.append(" ::> " + ", ".join(self._referenced_refs))
        type_suffix = "".join(suffix_parts)
        
        if params:
            return f"{keyword} {name_str}{type_suffix} {{ " + "; ".join(params) + "; }"
        else:
            return f"{keyword} {name_str}{type_suffix};"

    def _set_typed_by(self, typed):
        """Set typing (`:`) for action usage typed by action definition."""
        self._typed_by_name = typed.name if hasattr(typed, 'name') else str(typed)
        return self

    set_typed_by = _set_typed_by

    def _set_specializes(self, *parents):
        """Set specialization (`:>`) for action definitions."""
        self._specializes_names = [
            p.name if hasattr(p, 'name') else str(p) for p in parents
        ]
        return self

    set_specializes = _set_specializes


class UseCase(Usage):
    """SysML v2 UseCase usage/definition.

    Represents a scenario describing interactions between actors and the
    system to achieve a specific goal.

    Usage:
        UseCase()                                      # use case ;
        UseCase(name='login')                          # use case login;
        UseCase(definition=True, name='Login')         # use case def Login;
    """
    sysml_type = 'use_case'
    def __init__(self, definition=False, name=None, shortname=None):
        if definition:
            self.grammar = UseCaseDefinition()
            self.grammar.declaration.identification.declaredName = name if name else None
        else:
            self.grammar = None
        
        self.is_definition = definition
        self.name = name if name else str(uuidlib.uuid4())
        self.children = []
        self.typedby = None
        self.parent = None
        self.subject = None  # (name, type_name)
        self.actors = []  # list of (name, type_name)
        self.includes = []  # list of use case names
        
        if definition:
            self.keyword = "use case def"
        else:
            self.keyword = "use case"

    def _get_definition(self, child=None):
        # Sync name to grammar
        if hasattr(self.grammar, 'declaration') and hasattr(self.grammar.declaration, 'identification'):
            self.grammar.declaration.identification.declaredName = self.name
        
        if hasattr(self.grammar, 'get_definition'):
            grammar_def = self.grammar.get_definition()
        else:
            grammar_def = {"name": "UseCaseDefinition", "declaration": {}, "body": {}}
        
        # Wrap based on whether this is a definition or usage
        if self.is_definition:
            package = {
                "name": "DefinitionElement",
                "ownedRelatedElement": grammar_def,
            }
        else:
            package = {
                "name": "UsageElement",
                "ownedRelatedElement": {
                    "name": "OccurrenceUsageElement",
                    "ownedRelatedElement": {
                        "name": "BehaviorUsageElement",
                        "ownedRelationship": grammar_def
                    }
                }
            }

        if child == "DefinitionBody":
            package = {
                "name": "DefinitionMember",
                "prefix": None,
                "ownedRelatedElement": [package],
            }
            package = {"name": "DefinitionBodyItem", "ownedRelationship": [package]}
        elif child == "PackageBody" or child == None:
            package = {
                "name": "PackageMember",
                "ownedRelatedElement": package,
                "prefix": None,
            }

        return package

    def set_subject(self, name, type_name=None):
        """Set the subject of the use case.
        
        Args:
            name: Name of the subject
            type_name: Optional type (e.g., 'Vehicle')
        """
        self.subject = (name, type_name)
        return self

    def add_actor(self, name, type_name=None):
        """Add an actor to the use case.
        
        Args:
            name: Name of the actor
            type_name: Optional type (e.g., 'Driver')
        """
        self.actors.append((name, type_name))
        return self

    def add_include(self, use_case):
        """Add an included use case.
        
        Args:
            use_case: UseCase object or name string to include
        """
        name = use_case.name if hasattr(use_case, 'name') else str(use_case)
        self.includes.append(name)
        return self

    def _set_typed_by(self, typed):
        """Set typing (`:`) for use case usage."""
        self._typed_by_name = typed.name if hasattr(typed, 'name') else str(typed)
        return self

    set_typed_by = _set_typed_by

    def _set_specializes(self, *parents):
        """Set specialization (`:>`) for use case definitions."""
        self._specializes_names = [
            p.name if hasattr(p, 'name') else str(p) for p in parents
        ]
        return self

    set_specializes = _set_specializes

    def dump(self):
        name_str = getattr(self, 'name', "") or ""
        keyword = getattr(self, 'keyword', 'use case')
        
        # Build type/specialization suffix
        suffix_parts = []
        if getattr(self, '_typed_by_name', None):
            suffix_parts.append(f" : {self._typed_by_name}")
        if getattr(self, '_specializes_names', None):
            suffix_parts.append(" :> " + ", ".join(self._specializes_names))
        if getattr(self, '_redefined_refs', None):
            suffix_parts.append(" :>> " + ", ".join(self._redefined_refs))
        if getattr(self, '_referenced_refs', None):
            suffix_parts.append(" ::> " + ", ".join(self._referenced_refs))
        type_suffix = "".join(suffix_parts)
        
        # Build body members
        body_items = []
        
        if self.subject:
            subj_name, subj_type = self.subject
            if subj_type:
                body_items.append(f"subject {subj_name} : {subj_type};")
            else:
                body_items.append(f"subject {subj_name};")
        
        for actor_name, actor_type in self.actors:
            if actor_type:
                body_items.append(f"actor {actor_name} : {actor_type};")
            else:
                body_items.append(f"actor {actor_name};")
        
        for inc in self.includes:
            body_items.append(f"include use case {inc};")
        
        if body_items:
            body = " {\n   " + "\n   ".join(body_items) + "\n}"
            return f"{keyword} {name_str}{type_suffix}{body}"
        else:
            return f"{keyword} {name_str}{type_suffix};"

    def load_from_grammar(self, grammar):
        """Load use case from a parsed grammar object.
        
        Parameters
        ----------
        grammar : UseCaseUsage or UseCaseDefinition
            Parsed grammar object.
        
        Returns
        -------
        UseCase
            Self for chaining.
        """
        self.grammar = grammar
        
        class_name = grammar.__class__.__name__
        if class_name == "UseCaseDefinition":
            self.is_definition = True
            self.keyword = "use case def"
            if hasattr(grammar, 'declaration') and grammar.declaration:
                if hasattr(grammar.declaration, 'identification') and grammar.declaration.identification:
                    self.name = grammar.declaration.identification.declaredName
        else:
            # UseCaseUsage
            self.is_definition = False
            self.keyword = "use case"
            if hasattr(grammar, 'declaration') and grammar.declaration:
                decl = grammar.declaration
                if hasattr(decl, 'declaration') and decl.declaration:
                    inner_decl = decl.declaration
                    if hasattr(inner_decl, 'declaration') and inner_decl.declaration:
                        feat_decl = inner_decl.declaration
                        if hasattr(feat_decl, 'identification') and feat_decl.identification:
                            self.name = feat_decl.identification.declaredName

        self._extract_specialization_info(grammar)

        return self


class Requirement(Usage):
    sysml_type = 'requirement'
    """SysML v2 Requirement usage/definition.

    Represents a condition or capability that must be satisfied by a system,
    including textual documentation, attributes, and constraints.

    Usage:
        Requirement()                                          # requirement ;
        Requirement(name='R1')                                 # requirement R1;
        Requirement(definition=True, name='SafetyRequirement') # requirement def SafetyRequirement;
    """
    def __init__(self, definition=False, name=None, shortname=None):
        # Base-Usage state (_typed_by_name / _specializes_names /
        # _redefined_refs / _referenced_refs) — without it
        # _extract_specialization_info crashes on grammar loads with
        # redefinitions/subsettings (e.g. ``requirement r2 :>> r1;``).
        Usage.__init__(self)
        if definition:
            self.grammar = RequirementDefinition(None)
            if self.grammar.declaration is not None and hasattr(self.grammar.declaration, 'identification'):
                self.grammar.declaration.identification.declaredName = name if name else None
        else:
            self.grammar = None
        
        self.is_definition = definition
        self.name = name if name else str(uuidlib.uuid4())
        self.children = []
        self.typedby = None
        self.parent = None
        self.req_shortname = shortname
        self.subject = None
        self.actors = []
        self.verified_by = []
        self.doc = None
        self.req_attributes = []
        self.req_constraints = []
        self.assume_constraints = []

        if definition:
            self.keyword = "requirement def"
        else:
            self.keyword = "requirement"

    def _get_definition(self, child=None):
        # Sync name to grammar
        if hasattr(self.grammar, 'declaration') and hasattr(self.grammar.declaration, 'identification'):
            self.grammar.declaration.identification.declaredName = self.name
        
        if hasattr(self.grammar, 'get_definition'):
            grammar_def = self.grammar.get_definition()
        else:
            grammar_def = {"name": "RequirementDefinition", "declaration": {}, "body": {}}
        
        package = {
            "name": "DefinitionElement",
            "ownedRelatedElement": grammar_def,
        }

        if child == "DefinitionBody":
            package = {
                "name": "DefinitionMember",
                "prefix": None,
                "ownedRelatedElement": [package],
            }
            package = {"name": "DefinitionBodyItem", "ownedRelationship": [package]}
        elif child == "PackageBody" or child == None:
            package = {
                "name": "PackageMember",
                "ownedRelatedElement": package,
                "prefix": None,
            }

        return package

    def set_subject(self, name, type_name=None):
        """Set the subject of the requirement.

        Args:
            name: Name of the subject
            type_name: Optional type (e.g., 'Vehicle')
        """
        self.subject = (name, type_name)
        return self

    def add_actor(self, name, type_name=None):
        """Add an actor to the requirement.

        Args:
            name: Name of the actor
            type_name: Optional type
        """
        self.actors.append((name, type_name))
        return self

    def set_doc(self, text):
        """Set the documentation string.

        Args:
            text: Documentation text
        """
        self.doc = text
        return self

    def add_attribute(self, name, type_name=None):
        """Add an attribute to the requirement.

        Args:
            name: Attribute name
            type_name: Optional type
        """
        self.req_attributes.append((name, type_name))
        return self

    def add_constraint(self, expr):
        """Add a require constraint expression.

        Args:
            expr: Constraint expression string (e.g., 'massActual <= massReqd')
        """
        self.req_constraints.append(expr)
        return self

    def add_assume_constraint(self, expr):
        """Add an assume constraint expression.

        Args:
            expr: Assume constraint expression string
        """
        self.assume_constraints.append(expr)
        return self

    def _set_typed_by(self, typed):
        """Set typing (`:`) for requirement usage."""
        self._typed_by_name = typed.name if hasattr(typed, 'name') else str(typed)
        return self

    set_typed_by = _set_typed_by

    def _set_specializes(self, *parents):
        """Set specialization (`:>`) for requirement definitions."""
        self._specializes_names = [
            p.name if hasattr(p, 'name') else str(p) for p in parents
        ]
        return self

    set_specializes = _set_specializes

    def dump(self):
        name_str = getattr(self, 'name', "") or ""
        keyword = getattr(self, 'keyword', 'requirement')

        # Add shortname
        shortname_str = ""
        if self.req_shortname:
            shortname_str = f" <{self.req_shortname}>"

        # Build type/specialization suffix
        suffix_parts = []
        if getattr(self, '_typed_by_name', None):
            suffix_parts.append(f" : {self._typed_by_name}")
        if getattr(self, '_specializes_names', None):
            suffix_parts.append(" :> " + ", ".join(self._specializes_names))
        if getattr(self, '_redefined_refs', None):
            suffix_parts.append(" :>> " + ", ".join(self._redefined_refs))
        if getattr(self, '_referenced_refs', None):
            suffix_parts.append(" ::> " + ", ".join(self._referenced_refs))
        type_suffix = "".join(suffix_parts)

        # Build body members
        body_items = []

        if self.doc:
            if '\n' in self.doc:
                lines = self.doc.split('\n')
                doc_block = ['doc /*'] + [f' * {l}' for l in lines] + [' */']
                body_items.append('\n'.join(doc_block))
            else:
                body_items.append(f"doc /* {self.doc} */")

        if self.subject:
            subj_name, subj_type = self.subject
            if subj_type:
                body_items.append(f"subject {subj_name} : {subj_type};")
            else:
                body_items.append(f"subject {subj_name};")

        for actor_name, actor_type in self.actors:
            if actor_type:
                body_items.append(f"actor {actor_name} : {actor_type};")
            else:
                body_items.append(f"actor {actor_name};")

        for attr_name, attr_type in self.req_attributes:
            if attr_type:
                body_items.append(f"attribute {attr_name} : {attr_type};")
            else:
                body_items.append(f"attribute {attr_name};")

        for expr in self.req_constraints:
            body_items.append(f"require constraint {{ {expr} }}")

        for expr in self.assume_constraints:
            body_items.append(f"assume constraint {{ {expr} }}")

        for child in self.children:
            body_items.append(child.dump())

        if body_items:
            indented = [item.replace('\n', '\n   ') for item in body_items]
            body = " {\n   " + "\n   ".join(indented) + "\n}"
            return f"{keyword}{shortname_str} {name_str}{type_suffix}{body}"
        else:
            return f"{keyword}{shortname_str} {name_str}{type_suffix};"

    def load_from_grammar(self, grammar):
        """Load requirement from a parsed grammar object.
        
        Parameters
        ----------
        grammar : RequirementUsage or RequirementDefinition
            Parsed grammar object.
        
        Returns
        -------
        Requirement
            Self for chaining.
        """
        self.grammar = grammar
        
        # Check if this is a definition or usage
        class_name = grammar.__class__.__name__
        if class_name == "RequirementDefinition":
            self.is_definition = True
            self.keyword = "requirement def"
            # Extract name from declaration.identification
            if hasattr(grammar, 'declaration') and grammar.declaration:
                if hasattr(grammar.declaration, 'identification') and grammar.declaration.identification:
                    ident = grammar.declaration.identification
                    self.name = ident.declaredName
                    sn = getattr(ident, 'declaredShortName', None)
                    if sn:
                        sn = sn.strip('<>').strip()
                        if sn:
                            self.req_shortname = sn
        else:
            # RequirementUsage
            self.is_definition = False
            self.keyword = "requirement"
            # Navigate nested declaration structure
            if hasattr(grammar, 'declaration') and grammar.declaration:
                decl = grammar.declaration
                if hasattr(decl, 'declaration') and decl.declaration:
                    inner_decl = decl.declaration
                    if hasattr(inner_decl, 'declaration') and inner_decl.declaration:
                        feat_decl = inner_decl.declaration
                        if hasattr(feat_decl, 'identification') and feat_decl.identification:
                            ident = feat_decl.identification
                            self.name = ident.declaredName
                            sn = getattr(ident, 'declaredShortName', None)
                            if sn:
                                sn = sn.strip('<>').strip()
                                if sn:
                                    self.req_shortname = sn
        
        # Extract body content
        body = getattr(grammar, 'body', None)
        if body and hasattr(body, 'items'):
            for item in body.items:
                if hasattr(item, 'child') and item.child:
                    child_class = item.child.__class__.__name__
                    if child_class == "DefinitionBodyItem":
                        self._extract_nested_requirements(item.child)
                        self._extract_doc_from_body_item(item.child)
                    elif child_class == "RequirementConstraintMember":
                        pass  # could extract constraints
                    elif child_class == "SubjectMember":
                        self._extract_subject_member(item.child)
                    elif child_class == "ActorMember":
                        pass  # could extract actors
                    elif child_class == "RequirementVerificationMember":
                        self._extract_verification_member(item.child)

        self._extract_specialization_info(grammar)

        return self

    def _extract_subject_member(self, subject_member):
        """Extract (name, type) from a SubjectMember grammar object (v0.62.0).

        ``subject v : Vehicle;`` → ("v", "Vehicle"); anonymous
        ``subject : Vehicle;`` → ("Vehicle", "Vehicle") so traceability
        reports still have a usable identifier.
        """
        try:
            usage = subject_member.child          # SubjectUsage
            usage_child = getattr(usage, 'child', None)  # Usage
            if usage_child is None:
                return
            name = None
            typed = None
            decl = getattr(usage_child, 'declaration', None)
            feat = getattr(decl, 'declaration', None)
            ident = getattr(feat, 'identification', None)
            if ident is not None:
                name = getattr(ident, 'declaredName', None)
            # Declared type lives in FeatureDeclaration.specialization
            # (FeatureSpecializationPart dumping like ": Vehicle").
            spec = getattr(feat, 'specialization', None)
            if spec is not None and hasattr(spec, 'dump'):
                text = (spec.dump() or "").strip().rstrip(';').strip()
                if text.startswith(':'):
                    text = text[1:].strip()
                typed = text or None
            if name or typed:
                self.subject = (name or typed, typed)
        except Exception as e:
            print(f"[Requirement._extract_subject_member] {e}")

    def _extract_verification_member(self, verification_member):
        """Extract the verified target from a `verify <ref>` member (v0.62.0)."""
        try:
            child = verification_member.child
            if child is None:
                return
            target = None
            if getattr(child, 'ors', None) is not None:
                target = child.ors.dump().strip()
            elif getattr(child, 'declaration', None) is not None:
                target = _declaration_name(child.declaration)
            if target:
                self.verified_by.append(target)
        except Exception as e:
            print(f"[Requirement._extract_verification_member] {e}")

    def _extract_nested_requirements(self, def_body_item):
        """Find nested requirement usages/definitions inside a DefinitionBodyItem.

        Traversal path (per grammar/classes.py):
            DefinitionBodyItem
              -> OccurrenceUsageMember | NonOccurrenceUsageMember | DefinitionMember
                -> OccurrenceUsageElement | NonOccurrenceUsageElement | DefinitionElement
                  -> BehaviorUsageElement | StructureUsageElement | <Definition>
                    -> RequirementUsage | RequirementDefinition | ...

        Only RequirementUsage and RequirementDefinition are instantiated as
        children; other nested element types are ignored (future work).
        """
        for member in getattr(def_body_item, 'children', []) or []:
            for element in getattr(member, 'children', []) or []:
                inner = getattr(element, 'children', None)
                if inner is None:
                    continue
                # OccurrenceUsageElement / NonOccurrenceUsageElement wrap a
                # single child class in `.children`; DefinitionElement wraps
                # a Definition subclass in `.children`.
                target = getattr(inner, 'children', None) or inner
                target_cls = target.__class__.__name__ if not isinstance(target, list) else None

                if target_cls == "RequirementUsage":
                    c = Requirement().load_from_grammar(target)
                    c.parent = self
                    self.children.append(c)
                elif target_cls == "RequirementDefinition":
                    c = Requirement(definition=True).load_from_grammar(target)
                    c.parent = self
                    self.children.append(c)
                elif target_cls in ("SatisfyRequirementUsage",
                                    "VerifyRequirementUsage"):
                    # satisfy members are extracted from the grammar
                    # dicts by traceability/semantic (nested verify
                    # members ride _extract_verification_member); no
                    # Requirement child belongs here.
                    pass
                elif target_cls and "Requirement" in target_cls:
                    print(f"[Requirement] Unhandled nested requirement type: {target_cls}")

    def _extract_doc_from_body_item(self, def_body_item):
        """Find a Documentation node inside a DefinitionBodyItem and set self.doc.

        Traversal path (per grammar/classes.py):
            DefinitionBodyItem
              -> DefinitionMember          (other member types hold requirements, not docs)
                -> DefinitionElement
                  -> AnnotatingElement
                    -> Documentation  (stored as .children, single object)
        """
        for member in getattr(def_body_item, 'children', []) or []:
            if member.__class__.__name__ != "DefinitionMember":
                continue
            for element in getattr(member, 'children', []) or []:
                for ae in getattr(element, 'children', []) or []:
                    if ae.__class__.__name__ != "AnnotatingElement":
                        continue
                    doc = getattr(ae, 'children', None)
                    if doc is None:
                        continue
                    doc_cls = doc.__class__.__name__
                    if doc_cls in ("Documentation", "CommentSysML"):
                        text = _comment_body_to_text(getattr(doc, 'body', ''))
                        if text:
                            self.doc = text


def _comment_body_to_text(body):
    """Extract plain text from a SysML comment body like '/* ... */'.

    Strips the comment delimiters and the leading '*' marker from each line,
    then collapses to non-empty lines joined by newlines.
    """
    if not body:
        return None
    s = body.strip()
    if s.startswith('/*'):
        s = s[2:]
    if s.endswith('*/'):
        s = s[:-2]
    lines = []
    for line in s.splitlines():
        line = line.strip()
        if line.startswith('*'):
            line = line[1:].lstrip()
        if line:
            lines.append(line)
    return '\n'.join(lines) if lines else None


class Message(Usage):
    sysml_type = 'message'
    def __init__(self, name=None, from_port=None, to_port=None, of_type=None):
        """Create a message.

        Args:
            name: Optional message name
            from_port: Source port/part path (e.g., 'sensor')
            to_port: Target port/part path (e.g., 'controller')
            of_type: Optional item type (e.g., 'SensorData')
        """
        # Base-Usage state — see Requirement.__init__ (v0.82.0).
        Usage.__init__(self)
        self.name = name if name else str(uuidlib.uuid4())
        self.children = []
        self.typedby = None
        self.parent = None
        self.grammar = None
        self.from_port = from_port
        self.to_port = to_port
        self.of_type = of_type

    def set_from(self, from_port):
        """Set the source of the message.

        Args:
            from_port: Source path string or element with .name
        """
        self.from_port = from_port.name if hasattr(from_port, 'name') else str(from_port)
        return self

    def set_to(self, to_port):
        """Set the target of the message.

        Args:
            to_port: Target path string or element with .name
        """
        self.to_port = to_port.name if hasattr(to_port, 'name') else str(to_port)
        return self

    def set_of(self, of_type):
        """Set the item type of the message.

        Args:
            of_type: Item type string or element with .name
        """
        self.of_type = of_type.name if hasattr(of_type, 'name') else str(of_type)
        return self

    def dump(self):
        parts = ["message"]

        # Name (if not a UUID)
        name_str = getattr(self, 'name', "") or ""
        try:
            import uuid as _uuid
            _uuid.UUID(name_str)
            # It's a UUID - anonymous message, skip name
        except ValueError:
            parts.append(name_str)

        if self.of_type:
            parts.append(f"of {self.of_type}")

        if self.from_port and self.to_port:
            parts.append(f"from {self.from_port} to {self.to_port}")
        elif self.to_port:
            parts.append(f"to {self.to_port}")

        return " ".join(parts) + ";"

    def load_from_grammar(self, grammar):
        """Load message from a parsed grammar object.
        
        Parameters
        ----------
        grammar : Message
            Parsed grammar object.
        
        Returns
        -------
        Message
            Self for chaining.
        """
        self.grammar = grammar
        if hasattr(grammar, 'declaration') and grammar.declaration:
            decl = grammar.declaration
            if hasattr(decl, 'declaration') and decl.declaration:
                inner_decl = decl.declaration
                if hasattr(inner_decl, 'declaration') and inner_decl.declaration:
                    feat_decl = inner_decl.declaration
                    if hasattr(feat_decl, 'identification') and feat_decl.identification:
                        self.name = feat_decl.identification.declaredName
        return self


class _BehaviorUsage(Usage):
    """Base class for behavior-style usages (state, action, etc.).
    
    These get wrapped in BehaviorUsageElement rather than StructureUsageElement.
    """
    # Subclasses should set _is_definition_grammar based on grammar class
    _is_definition_grammar = False
    
    def _get_definition(self, child=None):
        # Determine if this is a definition or usage based on grammar class name
        grammar_cls_name = type(self.grammar).__name__
        is_def = grammar_cls_name.endswith('Definition')
        
        if is_def:
            package = self.behavior_definition_dump(child)
        else:
            package = self.usage_dump(child)

        if child is None:
            package = {
                "name": "PackageBodyElement",
                "ownedRelationship": [package],
                "prefix": None,
            }
        return package
    
    def usage_dump(self, child):
        # This is a behavior usage, not a structure usage.
        package = {
            "name": "BehaviorUsageElement",
            "ownedRelationship": self.grammar.get_definition(),
        }
        package = {"name": "OccurrenceUsageElement", "ownedRelatedElement": package}

        if child == "DefinitionBody":
            package = {
                "name": "OccurrenceUsageMember",
                "prefix": None,
                "ownedRelatedElement": [package],
            }
            package = {"name": "DefinitionBodyItem", "ownedRelationship": [package]}
        else:
            package = {"name": "UsageElement", "ownedRelatedElement": package}
            package = {
                "name": "PackageMember",
                "ownedRelatedElement": package,
                "prefix": None,
            }
        return package

    def behavior_definition_dump(self, child):
        package = {
            "name": "DefinitionElement",
            "ownedRelatedElement": self.grammar.get_definition(),
        }

        if child == "DefinitionBody":
            package = {
                "name": "DefinitionMember",
                "prefix": None,
                "ownedRelatedElement": [package],
            }
            package = {"name": "DefinitionBodyItem", "ownedRelationship": [package]}
        else:
            package = {
                "name": "PackageMember",
                "ownedRelatedElement": package,
                "prefix": None,
            }
        return package


class _NonOccurrenceUsage(Usage):
    """Base class for non-occurrence usages (attribute, calculation, constraint, etc.).
    
    These get wrapped in NonOccurrenceUsageElement rather than StructureUsageElement.
    """
    def _get_definition(self, child=None):
        grammar_cls_name = type(self.grammar).__name__
        is_def = grammar_cls_name.endswith('Definition')
        
        if is_def:
            package = self.nonocc_definition_dump(child)
        else:
            package = self.usage_dump(child)

        if child is None:
            package = {
                "name": "PackageBodyElement",
                "ownedRelationship": [package],
                "prefix": None,
            }
        return package
    
    def usage_dump(self, child):
        # Add packaging for non-occurrence usage
        package = {
            "name": "NonOccurrenceUsageElement",
            "ownedRelatedElement": self.grammar.get_definition(),
        }

        if child == "DefinitionBody":
            package = {
                "name": "NonOccurrenceUsageMember",
                "prefix": None,
                "ownedRelatedElement": [package],
            }
            package = {"name": "DefinitionBodyItem", "ownedRelationship": [package]}
        else:
            package = {"name": "UsageElement", "ownedRelatedElement": package}
            package = {
                "name": "PackageMember",
                "ownedRelatedElement": package,
                "prefix": None,
            }
        return package

    def nonocc_definition_dump(self, child):
        package = {
            "name": "DefinitionElement",
            "ownedRelatedElement": self.grammar.get_definition(),
        }

        if child == "DefinitionBody":
            package = {
                "name": "DefinitionMember",
                "prefix": None,
                "ownedRelatedElement": [package],
            }
            package = {"name": "DefinitionBodyItem", "ownedRelationship": [package]}
        else:
            package = {
                "name": "PackageMember",
                "ownedRelatedElement": package,
                "prefix": None,
            }
        return package


class Transition:
    """Represents a state machine transition.
    
    Attributes:
        name: Transition name (if any)
        source: Source state name (for explicit transitions)
        trigger: Trigger event (accept parameter)
        guard: Guard condition expression
        target: Target state name
        effect: Effect action
        is_entry: Whether this is an entry transition
        parent: Parent State element
    """
    def __init__(self):
        self.name = None
        self.source = None
        self.trigger = None
        self.guard = None
        self.target = None
        self.effect = None
        self.is_entry = False
        self.grammar = None
        self.parent = None
    
    def load_from_grammar(self, grammar, is_entry=False):
        """Load transition from grammar element.
        
        Args:
            grammar: TargetTransitionUsage, EntryTransitionMember, TransitionUsageMember, or similar
            is_entry: Whether this is an entry transition
        """
        self.grammar = grammar
        self.is_entry = is_entry
        
        if grammar.__class__.__name__ == 'EntryTransitionMember':
            self.is_entry = True
            self._load_from_entry_transition(grammar)
        elif grammar.__class__.__name__ == 'TargetTransitionUsageMember':
            self._load_from_target_transition(grammar)
        elif grammar.__class__.__name__ == 'TargetTransitionUsage':
            self._load_from_target_transition_usage(grammar)
        elif grammar.__class__.__name__ == 'TransitionUsageMember':
            self._load_from_transition_usage_member(grammar)
        
        return self
    
    def _load_from_transition_usage_member(self, member):
        """Load from TransitionUsageMember (explicit `transition name first X then Y;`)."""
        if hasattr(member, 'children') and member.children:
            usage = member.children
            if hasattr(usage, '__class__') and usage.__class__.__name__ == 'TransitionUsage':
                self._load_from_transition_usage(usage)
    
    def _load_from_transition_usage(self, usage):
        """Load from TransitionUsage."""
        # Extract name from declaration
        if hasattr(usage, 'declaration') and usage.declaration:
            decl = usage.declaration
            while hasattr(decl, 'declaration') and not hasattr(decl, 'identification'):
                decl = decl.declaration
            if hasattr(decl, 'identification') and decl.identification:
                self.name = decl.identification.declaredName
        
        # Extract source and target from ownedRelationship
        if hasattr(usage, 'children'):
            for child in usage.children:
                child_name = child.__class__.__name__
                if child_name == 'TransitionSourceMember':
                    self._extract_source(child)
                elif child_name == 'TransitionSuccessionMember':
                    self._extract_target(child)
                elif child_name == 'TriggerActionMember':
                    self._extract_trigger(child)
                elif child_name == 'GuardExpressionMember':
                    self._extract_guard(child)
                elif child_name == 'EffectBehaviorMember':
                    self._extract_effect(child)
    
    def _extract_source(self, source_member):
        """Extract source from TransitionSourceMember."""
        if hasattr(source_member, 'children') and source_member.children:
            qname = source_member.children
            if isinstance(qname, list):
                qname = qname[0]
            if hasattr(qname, 'names'):
                self.source = '.'.join(qname.names)
    
    def _load_from_entry_transition(self, entry_member):
        """Load from EntryTransitionMember."""
        if hasattr(entry_member, 'children') and entry_member.children:
            child = entry_member.children
            if child.__class__.__name__ == 'GuardedTargetSuccession':
                self._load_from_guarded_succession(child)
            elif child.__class__.__name__ == 'TransitionSuccession':
                self._extract_target_from_succession(child)
    
    def _load_from_target_transition(self, target_member):
        """Load from TargetTransitionUsageMember."""
        if hasattr(target_member, 'children') and target_member.children:
            usage = target_member.children
            if hasattr(usage, '__class__') and usage.__class__.__name__ == 'TargetTransitionUsage':
                self._load_from_target_transition_usage(usage)
    
    def _load_from_target_transition_usage(self, usage):
        """Load from TargetTransitionUsage."""
        if hasattr(usage, 'children'):
            for child in usage.children:
                child_name = child.__class__.__name__
                if child_name == 'TriggerActionMember':
                    self._extract_trigger(child)
                elif child_name == 'GuardExpressionMember':
                    self._extract_guard(child)
                elif child_name == 'EffectBehaviorMember':
                    self._extract_effect(child)
                elif child_name == 'TransitionSuccessionMember':
                    self._extract_target(child)
    
    def _load_from_guarded_succession(self, guarded):
        """Load from GuardedTargetSuccession."""
        if hasattr(guarded, 'children'):
            for child in guarded.children:
                if child.__class__.__name__ == 'GuardExpressionMember':
                    self._extract_guard(child)
                elif child.__class__.__name__ == 'TransitionSuccessionMember':
                    self._extract_target(child)
    
    def _extract_trigger(self, trigger_member):
        """Extract trigger from TriggerActionMember."""
        if hasattr(trigger_member, 'children') and trigger_member.children:
            trigger = trigger_member.children
            if hasattr(trigger, 'children') and trigger.children:
                accept_param = trigger.children
                if hasattr(accept_param, 'children'):
                    for param in accept_param.children:
                        if param.__class__.__name__ == 'PayloadParameterMember':
                            if hasattr(param, 'children') and param.children:
                                payload = param.children
                                # PayloadParameter can have .children (PayloadFeature) or .identification
                                if hasattr(payload, 'children') and payload.children:
                                    feat = payload.children
                                    if hasattr(feat, 'identification') and feat.identification:
                                        self.trigger = feat.identification.declaredName
                                    elif hasattr(feat, 'dump'):
                                        self.trigger = feat.dump()
                                elif hasattr(payload, 'identification') and payload.identification:
                                    self.trigger = payload.identification.declaredName
    
    def _extract_guard(self, guard_member):
        """Extract guard from GuardExpressionMember."""
        if hasattr(guard_member, 'children') and guard_member.children:
            self.guard = guard_member.children.dump()
    
    def _extract_effect(self, effect_member):
        """Extract effect from EffectBehaviorMember."""
        if hasattr(effect_member, 'children') and effect_member.children:
            effect = effect_member.children
            if hasattr(effect, 'declaration') and effect.declaration:
                self.effect = effect.declaration.dump()
    
    def _extract_target(self, succession_member):
        """Extract target from TransitionSuccessionMember."""
        if hasattr(succession_member, 'children') and succession_member.children:
            succession = succession_member.children
            if hasattr(succession, 'children') and succession.children:
                self._extract_target_from_succession(succession)
    
    def _extract_target_from_succession(self, succession):
        """Extract target from TransitionSuccession."""
        if hasattr(succession, 'children') and succession.children:
            connector = succession.children
            if hasattr(connector, 'children'):
                target_list = connector.children
                if isinstance(target_list, list) and target_list:
                    target = target_list[0]
                    if hasattr(target, 'dump'):
                        self.target = target.dump()
                elif hasattr(target_list, 'dump'):
                    self.target = target_list.dump()
    
    def __repr__(self):
        parts = []
        if self.trigger:
            parts.append(f"trigger={self.trigger!r}")
        if self.guard:
            parts.append(f"guard={self.guard!r}")
        if self.target:
            parts.append(f"target={self.target!r}")
        if self.is_entry:
            parts.append("entry=True")
        return f"Transition({', '.join(parts)})"


class State(_BehaviorUsage):
    sysml_type = 'state'
    """SysML v2 State Machine state usage/definition.
    
    Usage:
        State()                              # state ;
        State(name='Idle')                   # state Idle;
        State(definition=True, name='Mode')  # state def Mode;
    """
    def __init__(self, definition=False, name=None, shortname=None):
        """Initialize a State usage or definition.

        Parameters
        ----------
        definition : bool
            If True, creates a StateDefinition. Otherwise creates StateUsage.
        name : str, optional
            Element name.
        shortname : str, optional
            Abbreviated name.
        """
        Usage.__init__(self)
        if definition:
            self.grammar = StateDefinition()
        else:
            self.grammar = StateUsage()

        self.transitions = []
        self.entry_actions = []
        self.exit_actions = []
        self.do_actions = []

        if name is not None:
            self._set_name(name)
        if shortname is not None:
            self._set_name(shortname, short=True)

    def load_from_grammar(self, grammar):
        """Load state from grammar, extracting nested states, transitions, and actions."""
        self.grammar = grammar
        self.children = []
        self.transitions = []
        self.entry_actions = []
        self.exit_actions = []
        self.do_actions = []
        
        # Extract name
        if hasattr(grammar, 'declaration') and grammar.declaration:
            decl = grammar.declaration
            # Handle nested declaration structure
            while hasattr(decl, 'declaration') and not hasattr(decl, 'identification'):
                decl = decl.declaration
            if hasattr(decl, 'identification') and decl.identification:
                self.name = decl.identification.declaredName

        self._extract_specialization_info(grammar)

        # Extract nested states, transitions, and actions from body
        # StateDefinition: grammar.body -> StateDefBody -> children -> StateBodyPart -> children -> items
        # StateUsage: grammar.body -> StateUsageBody -> children -> StateDefBody -> children -> StateBodyPart -> children -> items
        body = getattr(grammar, 'body', None)
        if body is None:
            return self
        
        # Handle StateUsageBody wrapper (has .children -> StateDefBody)
        body_type = body.__class__.__name__
        if body_type == 'StateUsageBody':
            body = body.children
        if body is None:
            return self
        
        if not hasattr(body, 'children'):
            return self
            
        state_body_part = body.children
        if state_body_part is None:
            return self
        
        if hasattr(state_body_part, 'children'):
            items = state_body_part.children
        elif isinstance(state_body_part, list):
            items = state_body_part
        else:
            items = []
        
        if not items:
            return self
        
        for item in items:
            if not hasattr(item, 'children') or not item.children:
                continue
            # Each StateBodyItem can have multiple members (e.g., state + transition)
            for member in item.children:
                member_name = member.__class__.__name__
                
                if member_name == 'BehaviorUsageMember':
                    self._extract_state_from_behavior_member(member)
                elif member_name == 'TargetTransitionUsageMember':
                    self._extract_transition(member)
                elif member_name == 'EntryTransitionMember':
                    self._extract_entry_transition(member)
                elif member_name == 'TransitionUsageMember':
                    self._extract_transition(member)
                elif member_name == 'EntryActionMember':
                    self._extract_entry_action(member)
                elif member_name == 'ExitActionMember':
                    self._extract_exit_action(member)
                elif member_name == 'DoActionMember':
                    self._extract_do_action(member)
        
        return self
    
    def _extract_state_from_behavior_member(self, behavior_member):
        """Extract nested state from BehaviorUsageMember."""
        if hasattr(behavior_member, 'children'):
            for child in behavior_member.children:
                if hasattr(child, 'children'):
                    # child is BehaviorUsageElement, its children is the actual usage (StateUsage, etc.)
                    usage = child.children
                    if not usage:
                        continue
                    
                    usage_type = usage.__class__.__name__
                    if usage_type in ('StateUsage', 'StateDefinition'):
                        is_def = usage_type == 'StateDefinition'
                        nested_state = State(definition=is_def)
                        nested_state.parent = self
                        nested_state.load_from_grammar(usage)
                        self.children.append(nested_state)
    
    def _extract_transition(self, target_member):
        """Extract transition from TargetTransitionUsageMember."""
        transition = Transition()
        transition.parent = self
        transition.load_from_grammar(target_member)
        self.transitions.append(transition)
    
    def _extract_entry_transition(self, entry_member):
        """Extract entry transition from EntryTransitionMember."""
        transition = Transition()
        transition.parent = self
        transition.load_from_grammar(entry_member, is_entry=True)
        self.transitions.append(transition)
    
    def _extract_entry_action(self, entry_member):
        """Extract entry action from EntryActionMember."""
        if hasattr(entry_member, 'children') and entry_member.children:
            action = entry_member.children
            self.entry_actions.append(action)
    
    def _extract_exit_action(self, exit_member):
        """Extract exit action from ExitActionMember."""
        if hasattr(exit_member, 'children') and exit_member.children:
            action = exit_member.children
            self.exit_actions.append(action)
    
    def _extract_do_action(self, do_member):
        """Extract do action from DoActionMember."""
        if hasattr(do_member, 'children') and do_member.children:
            action = do_member.children
            self.do_actions.append(action)


class Constraint(_NonOccurrenceUsage):
    sysml_type = 'constraint'
    """SysML v2 Constraint usage/definition.
    
    Usage:
        Constraint()                              # constraint ;
        Constraint(name='PowerLimit')             # constraint PowerLimit;
        Constraint(definition=True, name='Limit') # constraint def Limit;
    """
    def __init__(self, definition=False, name=None, shortname=None):
        """Initialize a Constraint usage or definition.

        Parameters
        ----------
        definition : bool
            If True, creates a ConstraintDefinition. Otherwise creates ConstraintUsage.
        name : str, optional
            Element name.
        shortname : str, optional
            Abbreviated name.
        """
        Usage.__init__(self)
        if definition:
            self.grammar = ConstraintDefinition()
        else:
            self.grammar = ConstraintUsage()

        Usage.__init__(self)
        if definition:
            self.grammar = ConstraintDefinition()
        else:
            self.grammar = ConstraintUsage()

        if name is not None:
            self._set_name(name)
        if shortname is not None:
            self._set_name(shortname, short=True)

    def textual_representations(self):
        """[(language, text), ...] from `rep language "..." /* ... */` bodies.

        A constraint body expressed in another language (e.g. natural
        language) is a TextualRepresentation inside the CalculationBody.
        The text has the /* */ comment markers stripped.
        """
        out = []
        g = getattr(self, "grammar", None)
        body = getattr(g, "body", None)
        if body is None:
            return out
        for part in getattr(body, "children", []) or []:
            for item in getattr(part, "children", []) or []:
                for abi in getattr(item, "children", []) or []:
                    for ch in getattr(abi, "children", []) or []:
                        if ch.__class__.__name__ == "TextualRepresentation":
                            text = str(ch.body or "")
                            if text.startswith("/*") and text.endswith("*/"):
                                text = text[2:-2].strip()
                            out.append((ch.language or "", text))
        return out

    @property
    def body_text(self):
        """Raw text of the constraint's textual body, or None.

        Populated for natural-language bodies (``rep language "English"
        /* ... */`` and bodies salvaged by the parser's rescue pass).
        """
        reps = self.textual_representations()
        return reps[0][1] if reps else None

    @property
    def body_language(self):
        """Language tag of the constraint's textual body, or None."""
        reps = self.textual_representations()
        return reps[0][0] or None if reps else None


class Connection(Usage):
    sysml_type = 'connection'
    """SysML v2 Connection usage/definition.
    
    Usage:
        Connection()                                  # connection ;
        Connection(name='wire')                       # connection wire;
        Connection(definition=True, name='DataLink')  # connection def DataLink;
    """
    def __init__(self, definition=False, name=None, shortname=None):
        """Initialize a Connection usage or definition.

        Parameters
        ----------
        definition : bool
            If True, creates a ConnectionDefinition. Otherwise creates ConnectionUsage.
        name : str, optional
            Element name.
        shortname : str, optional
            Abbreviated name.
        """
        Usage.__init__(self)
        if definition:
            self.grammar = ConnectionDefinition()
        else:
            self.grammar = ConnectionUsage()

        if name is not None:
            self._set_name(name)
        if shortname is not None:
            self._set_name(shortname, short=True)


class Flow(Usage):
    sysml_type = 'flow'
    """SysML v2 Flow connection usage/definition.
    
    Usage:
        Flow()                                       # flow ;
        Flow(name='fuelFlow')                        # flow fuelFlow;
        Flow(definition=True, name='WaterFlow')      # flow def WaterFlow;
    """
    def __init__(self, definition=False, name=None, shortname=None):
        """Initialize a Flow connection usage or definition.

        Parameters
        ----------
        definition : bool
            If True, creates a FlowConnectionDefinition. Otherwise creates FlowConnectionUsage.
        name : str, optional
            Element name.
        shortname : str, optional
            Abbreviated name.
        """
        Usage.__init__(self)
        if definition:
            self.grammar = FlowConnectionDefinition()
        else:
            self.grammar = FlowConnectionUsage()

        if name is not None:
            self._set_name(name)
        if shortname is not None:
            self._set_name(shortname, short=True)


class Calculation(_NonOccurrenceUsage):
    sysml_type = 'calculation'
    """SysML v2 Calculation usage/definition.
    
    Usage:
        Calculation()                                   # calc ;
        Calculation(name='computeArea')                 # calc computeArea;
        Calculation(definition=True, name='Distance')   # calc def Distance;
    """
    def __init__(self, definition=False, name=None, shortname=None):
        """Initialize a Calculation usage or definition.

        Parameters
        ----------
        definition : bool
            If True, creates a CalculationDefinition. Otherwise creates CalculationUsage.
        name : str, optional
            Element name.
        shortname : str, optional
            Abbreviated name.
        """
        Usage.__init__(self)
        if definition:
            self.grammar = CalculationDefinition()
        else:
            self.grammar = CalculationUsage()

        if name is not None:
            self._set_name(name)
        if shortname is not None:
            self._set_name(shortname, short=True)


class Enumeration(Usage):
    sysml_type = 'enumeration'
    """SysML v2 Enumeration definition.
    
    Note: SysML v2 only has EnumerationDefinition, no EnumerationUsage.
    
    Usage:
        Enumeration(name='Color')  # enum def Color;
    """
    def __init__(self, definition=True, name=None, shortname=None):
        """Initialize an Enumeration definition.

        Note: SysML v2 only has EnumerationDefinition, no EnumerationUsage.

        Parameters
        ----------
        definition : bool
            Always True (ignored). Only definitions are supported.
        name : str, optional
            Enumeration name.
        shortname : str, optional
            Abbreviated name.
        """
        Usage.__init__(self)
        # EnumerationDefinition is the only form
        self.grammar = EnumerationDefinition()
        
        if name is not None:
            self._set_name(name)
        if shortname is not None:
            self._set_name(shortname, short=True)


class Allocation(Usage):
    sysml_type = 'allocation'
    """SysML v2 Allocation usage/definition.
    
    Allocation represents mapping from one model element to another.
    
    Usage:
        Allocation()                                  # allocation ;
        Allocation(name='alloc1')                     # allocation alloc1;
        Allocation(definition=True, name='AllocSpec') # allocation def AllocSpec;
    """
    def __init__(self, definition=False, name=None, shortname=None):
        """Initialize an Allocation usage or definition.

        Parameters
        ----------
        definition : bool
            If True, creates an AllocationDefinition. Otherwise creates AllocationUsage.
        name : str, optional
            Element name.
        shortname : str, optional
            Abbreviated name.
        """
        Usage.__init__(self)
        if definition:
            self.grammar = AllocationDefinition()
        else:
            self.grammar = AllocationUsage()

        if name is not None:
            self._set_name(name)
        if shortname is not None:
            self._set_name(shortname, short=True)


class Metadata(_NonOccurrenceUsage):
    sysml_type = 'metadata'
    """SysML v2 Metadata usage/definition.
    
    Metadata attaches additional information to model elements.
    
    Usage:
        Metadata()                                       # metadata ;
        Metadata(name='tag1')                            # metadata tag1;
        Metadata(definition=True, name='AuthorMeta')     # metadata def AuthorMeta;
    """
    def __init__(self, definition=False, name=None, shortname=None):
        """Initialize a Metadata usage or definition.

        Parameters
        ----------
        definition : bool
            If True, creates a MetadataDefinition. Otherwise creates MetadataUsage.
        name : str, optional
            Element name.
        shortname : str, optional
            Abbreviated name.
        """
        Usage.__init__(self)
        if definition:
            self.grammar = MetadataDefinition()
        else:
            self.grammar = MetadataUsage()

        if name is not None:
            self._set_name(name)
        if shortname is not None:
            self._set_name(shortname, short=True)


class Rendering(Usage):
    sysml_type = 'rendering'
    """SysML v2 Rendering usage/definition.
    
    Rendering specifies how views should be rendered.
    
    Usage:
        Rendering()                                    # rendering ;
        Rendering(name='myRender')                     # rendering myRender;
        Rendering(definition=True, name='DefRender')   # rendering def DefRender;
    """
    def __init__(self, definition=False, name=None, shortname=None):
        """Initialize a Rendering usage or definition.

        Parameters
        ----------
        definition : bool
            If True, creates a RenderingDefinition. Otherwise creates RenderingUsage.
        name : str, optional
            Element name.
        shortname : str, optional
            Abbreviated name.
        """
        Usage.__init__(self)
        if definition:
            self.grammar = RenderingDefinition()
        else:
            self.grammar = RenderingUsage()

        if name is not None:
            self._set_name(name)
        if shortname is not None:
            self._set_name(shortname, short=True)


class Individual(Usage):
    sysml_type = 'individual'
    """SysML v2 Individual usage/definition.
    
    Individual represents a specific instance or occurrence.
    
    Usage:
        Individual()                                     # individual ;
        Individual(name='instance1')                     # individual instance1;
        Individual(definition=True, name='DefIndiv')     # individual def DefIndiv;
    """
    def __init__(self, definition=False, name=None, shortname=None):
        """Initialize an Individual usage or definition.

        Parameters
        ----------
        definition : bool
            If True, creates an IndividualDefinition. Otherwise creates IndividualUsageSimple.
        name : str, optional
            Element name.
        shortname : str, optional
            Abbreviated name.
        """
        Usage.__init__(self)
        if definition:
            self.grammar = IndividualDefinition()
        else:
            self.grammar = IndividualUsageSimple()

        if name is not None:
            self._set_name(name)
        if shortname is not None:
            self._set_name(shortname, short=True)


class FlowDef(Usage):
    sysml_type = 'flow'
    """SysML v2 FlowDefinition alternate form.
    
    Note: This is the simpler 'flow def' form (distinct from FlowConnectionDefinition).
    Usage already provides Flow class for flowConnectionUsage/Definition.
    
    Usage:
        FlowDef(name='DataStream')   # flow def DataStream;
    """
    def __init__(self, name=None, shortname=None):
        """Initialize a FlowDefinition (alternate simpler form).

        Note: This is the simpler 'flow def' form, distinct from FlowConnectionDefinition.

        Parameters
        ----------
        name : str, optional
            Flow name.
        shortname : str, optional
            Abbreviated name.
        """
        Usage.__init__(self)
        self.grammar = FlowDefinition()
        
        if name is not None:
            self._set_name(name)
        if shortname is not None:
            self._set_name(shortname, short=True)


class View(Usage):
    sysml_type = 'view'
    """SysML v2 View usage/definition.
    
    Views define how models are presented and filtered.
    
    Usage:
        View()                                  # view ;
        View(name='systemOverview')             # view systemOverview;
        View(definition=True, name='SysView')   # view def SysView;
    """
    def __init__(self, definition=False, name=None, shortname=None):
        """Initialize a View usage or definition.

        Parameters
        ----------
        definition : bool
            If True, creates a ViewDefinition. Otherwise creates ViewUsage.
        name : str, optional
            Element name.
        shortname : str, optional
            Abbreviated name.
        """
        Usage.__init__(self)
        if definition:
            self.grammar = ViewDefinition()
        else:
            self.grammar = ViewUsage()

        if name is not None:
            self._set_name(name)
        if shortname is not None:
            self._set_name(shortname, short=True)


class Viewpoint(_BehaviorUsage):
    sysml_type = 'viewpoint'
    """SysML v2 Viewpoint usage/definition.
    
    Viewpoints specify viewing perspectives with stakeholder concerns.
    
    Usage:
        Viewpoint()                                   # viewpoint ;
        Viewpoint(name='stakeholderVP')               # viewpoint stakeholderVP;
        Viewpoint(definition=True, name='VPDef')      # viewpoint def VPDef;
    """
    def __init__(self, definition=False, name=None, shortname=None):
        """Initialize a Viewpoint usage or definition.

        Parameters
        ----------
        definition : bool
            If True, creates a ViewpointDefinition. Otherwise creates ViewpointUsage.
        name : str, optional
            Element name.
        shortname : str, optional
            Abbreviated name.
        """
        Usage.__init__(self)
        if definition:
            self.grammar = ViewpointDefinition()
        else:
            self.grammar = ViewpointUsage()

        if name is not None:
            self._set_name(name)
        if shortname is not None:
            self._set_name(shortname, short=True)


class Concern(_BehaviorUsage):
    sysml_type = 'concern'
    """SysML v2 Concern usage/definition.
    
    Concerns represent stakeholder concerns for viewpoints.
    
    Usage:
        Concern()                                  # concern ;
        Concern(name='security')                   # concern security;
        Concern(definition=True, name='Safety')    # concern def Safety;
    """
    def __init__(self, definition=False, name=None, shortname=None):
        """Initialize a Concern usage or definition.

        Parameters
        ----------
        definition : bool
            If True, creates a ConcernDefinition. Otherwise creates ConcernUsage.
        name : str, optional
            Element name.
        shortname : str, optional
            Abbreviated name.
        """
        Usage.__init__(self)
        if definition:
            self.grammar = ConcernDefinition()
        else:
            self.grammar = ConcernUsage()

        if name is not None:
            self._set_name(name)
        if shortname is not None:
            self._set_name(shortname, short=True)


class Case(_BehaviorUsage):
    sysml_type = 'case'
    """SysML v2 Case usage/definition.
    
    A case is a broad classifier for analysis, verification, and use cases.
    
    Usage:
        Case()                                  # case ;
        Case(name='scenario1')                  # case scenario1;
        Case(definition=True, name='CaseSpec')  # case def CaseSpec;
    """
    def __init__(self, definition=False, name=None, shortname=None):
        """Initialize a Case usage or definition.

        Parameters
        ----------
        definition : bool
            If True, creates a CaseDefinition. Otherwise creates CaseUsage.
        name : str, optional
            Element name.
        shortname : str, optional
            Abbreviated name.
        """
        Usage.__init__(self)
        if definition:
            self.grammar = CaseDefinition()
        else:
            self.grammar = CaseUsage()

        if name is not None:
            self._set_name(name)
        if shortname is not None:
            self._set_name(shortname, short=True)


class AnalysisCase(_BehaviorUsage):
    sysml_type = 'analysis'
    """SysML v2 AnalysisCase usage/definition.
    
    Analysis cases represent analytical scenarios or studies.
    
    Usage:
        AnalysisCase()                                  # analysis ;
        AnalysisCase(name='thermal1')                   # analysis thermal1;
        AnalysisCase(definition=True, name='Thermal')   # analysis def Thermal;
    """
    def __init__(self, definition=False, name=None, shortname=None):
        """Initialize an AnalysisCase usage or definition.

        Parameters
        ----------
        definition : bool
            If True, creates an AnalysisCaseDefinition. Otherwise creates AnalysisCaseUsage.
        name : str, optional
            Element name.
        shortname : str, optional
            Abbreviated name.
        """
        Usage.__init__(self)
        if definition:
            self.grammar = AnalysisCaseDefinition()
        else:
            self.grammar = AnalysisCaseUsage()

        if name is not None:
            self._set_name(name)
        if shortname is not None:
            self._set_name(shortname, short=True)


class VerificationCase(_BehaviorUsage):
    sysml_type = 'verification'
    """SysML v2 VerificationCase usage/definition.
    
    Verification cases represent verification scenarios or tests.
    
    Usage:
        VerificationCase()                                    # verification ;
        VerificationCase(name='test1')                        # verification test1;
        VerificationCase(definition=True, name='Verify1')     # verification case def Verify1;
    """
    def __init__(self, definition=False, name=None, shortname=None):
        """Initialize a VerificationCase usage or definition.

        Parameters
        ----------
        definition : bool
            If True, creates a VerificationCaseDefinition. Otherwise creates VerificationCaseUsage.
        name : str, optional
            Element name.
        shortname : str, optional
            Abbreviated name.
        """
        Usage.__init__(self)
        if definition:
            self.grammar = VerificationCaseDefinition()
        else:
            self.grammar = VerificationCaseUsage()

        if name is not None:
            self._set_name(name)
        if shortname is not None:
            self._set_name(shortname, short=True)


class Reference(Usage):
    """SysML v2 Reference usage.

    Represents a reference to another element, optionally with redefinition
    or type specification.

    Usage:
        Reference(name='ref1')                     # ref ref1;
        Reference(name='r', redefines='original')  # ref r :>> original;
    """
    sysml_type = 'reference'
    def __init__(self, name=None, shortname=None, redefines=None):
        # Initialize the full base-Usage state (_is_definition,
        # _typed_by_name, _specializes_names, ...).  Reference used to
        # set only a handful of attributes here, so is_definition/repr
        # crashed with AttributeError on freshly built objects.
        Usage.__init__(self)
        if name is not None:
            self.name = name
        self.shortname = shortname
        self.redefines = redefines  # for redefinition like ref :>> name :
        self.ref_type = None  # type reference

    def set_type(self, type_obj):
        """Set the type this reference points to.
        
        Args:
            type_obj: Another element (Item, Part, etc.) to reference
        """
        self.ref_type = type_obj
        return self

    def _set_typed_by(self, type_obj):
        """Alias for set_type for consistency with other classes."""
        return self.set_type(type_obj)

    set_typed_by = _set_typed_by

    def load_from_grammar(self, grammar):
        """Populate from a parsed grammar ``ReferenceUsage`` object.

        The grammar node (``grammar_classes.ReferenceUsage``) keeps the
        full parse (prefix, usage declaration, specialization); the
        public object extracts name / shortname / typing / redefinition
        for navigation, while ``usage_dump`` re-serializes from the
        grammar so ``dump()`` round-trips byte-identically.

        Parameters
        ----------
        grammar : sysmlpy.grammar.classes.ReferenceUsage
            Parsed grammar object for this reference.

        Returns
        -------
        Reference
            Self for chaining.
        """
        self.__init__()
        self.grammar = grammar
        usage = getattr(grammar, "child", None)  # grammar classes.Usage
        if usage is None:
            return self
        decl = getattr(usage, "declaration", None)
        decl_decl = getattr(decl, "declaration", None)
        ident = getattr(decl_decl, "identification", None) if decl_decl else None
        if ident is not None:
            name = getattr(ident, "declaredName", None)
            short = getattr(ident, "declaredShortName", None)
            if short:
                self._set_name(short, short=True)
            if name:
                self.name = name
        # Typing / subsetting / redefinition names from the specialization
        # (sets _typed_by_name, _redefined_refs, ...).
        self._extract_specialization_info(usage)
        if getattr(self, "_redefined_refs", None):
            # `ref :>> payload : Fuel;` — dump() renders the :>> form
            self.redefines = True
            if not name:
                # For the bare redefinition form declaredName is null in
                # the grammar; the usage's name is the redefined feature.
                self.name = self._redefined_refs[0]
        return self

    def usage_dump(self, child):
        """Serialize as a NonOccurrenceUsageElement (mirrors Attribute).

        Re-serializes from the stored grammar ``ReferenceUsage`` so the
        round-trip preserves prefix, specialization and value parts.
        """
        if self.grammar is None:
            # Programmatic object without grammar: minimal member dict
            inner = {
                "name": "NonOccurrenceUsageElement",
                "ownedRelatedElement": {
                    "name": "ReferenceUsage",
                    "prefix": None,
                    "usage": {
                        "name": "Usage",
                        "declaration": {
                            "name": "UsageDeclaration",
                            "declaration": {
                                "name": "FeatureDeclaration",
                                "identification": {
                                    "name": "Identification",
                                    "declaredShortName": self.shortname,
                                    "declaredName": self.name,
                                },
                                "specialization": None,
                            },
                        },
                        "completion": None,
                    },
                },
            }
        else:
            inner = {
                "name": "NonOccurrenceUsageElement",
                "ownedRelatedElement": self.grammar.get_definition(),
            }

        if child == "DefinitionBody":
            package = {
                "name": "NonOccurrenceUsageMember",
                "prefix": None,
                "ownedRelatedElement": [inner],
            }
            package = {"name": "DefinitionBodyItem", "ownedRelationship": [package]}
        else:
            # "PackageBody" and standalone: package-member wrapping
            package = {"name": "UsageElement", "ownedRelatedElement": inner}
            package = {
                "name": "PackageMember",
                "ownedRelatedElement": package,
                "prefix": None,
            }
        return package

    def dump(self):
        name_str = getattr(self, 'name', "") or ""
        type_str = ""

        # NOTE: `is not None`, not truthiness — elements are falsy when
        # they have no children (Searchable.__len__), so a freshly built
        # typed-by Item would evaluate False and drop the ": Type".
        if self.ref_type is not None:
            type_name = getattr(self.ref_type, 'name', str(self.ref_type))
            type_str = f" : {type_name}"

        if self.redefines:
            return f"ref :>> {name_str}{type_str};"

        return f"ref {name_str}{type_str};"


class DefaultReference(Usage):
    """SysML v2 DefaultReference usage.

    Represents a default reference, typically used for input/output parameters
    in actions and behaviors.

    Usage:
        DefaultReference().set_direction('in')   # in ;
        DefaultReference().set_direction('out')  # out ;
    """
    def __init__(self):
        Usage.__init__(self)
        self.grammar = DefaultReferenceUsage()

    def set_direction(self, direction):
        r = RefPrefix()
        if direction == "in":
            r.direction.isIn = True
        elif direction == "out":
            r.direction.isOut = True
        elif direction == "inout":
            r.direction.isInOut = True
        else:
            raise ValueError
        self.grammar.prefix = r
        return self

    def usage_dump(self, child):
        # This is a usage.

        self._ensure_body("definition")

        # Add packaging
        package = {
            "name": "NonOccurrenceUsageElement",
            "ownedRelatedElement": self.grammar.get_definition(),
        }

        if child == "DefinitionBody":
            package = {
                "name": "NonOccurrenceUsageMember",
                "prefix": None,
                "ownedRelatedElement": [package],
            }

            package = {"name": "DefinitionBodyItem", "ownedRelationship": [package]}
        elif "PackageBody":
            package = {"name": "UsageElement", "ownedRelatedElement": package}
            package = {
                "name": "PackageMember",
                "ownedRelatedElement": package,
                "prefix": None,
            }

        return package

    def _get_definition(self, child=None):
        package = self.usage_dump(child)

        if child is None:
            package = {
                "name": "PackageBodyElement",
                "ownedRelationship": [package],
                "prefix": None,
            }

        # Add the typed by definition to the package output — but only
        # when it is not already part of the tree (a parsed model whose
        # ``typedby`` was filled in by ``Model.resolve_types()`` already
        # serializes the definition from its own package; inserting it
        # again would duplicate it).
        if self.typedby is not None and not self._typedby_serialized_elsewhere():
            if child is None:
                package["ownedRelationship"].insert(
                    0, self.typedby._get_definition(child="PackageBody")
                )
            elif child == "PackageBody":
                package = [self.typedby._get_definition(child="PackageBody"), package]
            else:
                package["ownedRelationship"].insert(
                    0, self.typedby._get_definition(child=child)["ownedRelationship"][0]
                )

        return package

    # def dump(self, child=None):
    #     package = self.usage_dump(child)

    #     if child is None:
    #         package = {
    #             "name": "PackageBodyElement",
    #             "ownedRelationship": [package],
    #             "prefix": None,
    #         }

    #     # Add the typed by definition to the package output
    #     if self.typedby is not None:
    #         if child is None:
    #             package["ownedRelationship"].insert(
    #                 0, self.typedby.dump(child="PackageBody")
    #             )
    #         elif child == "PackageBody":
    #             package = [self.typedby.dump(child="PackageBody"), package]
    #         else:
    #             package["ownedRelationship"].insert(
    #                 0, self.typedby.dump(child=child)["ownedRelationship"][0]
    #             )

    #     return package


class Dependency(Usage):
    """SysML v2 Dependency usage.

    Represents a UML-style dependency between model elements.
    Usage:
        Dependency()                                  # dependency ;
        Dependency(name='D')                         # dependency D from x to y;
    """
    sysml_type = 'dependency'

    def __init__(self, name=None, clients=None, suppliers=None, shortname=None):
        Usage.__init__(self)
        self.grammar = None
        self.clients = clients or []
        self.suppliers = suppliers or []
        # Usage.__init__ assigns a UUID-based name; override to None when
        # the dependency is anonymous (the common case for
        # `dependency b to A;`).
        self.name = name
        if shortname is not None:
            self._set_name(shortname, short=True)

    def dump(self):
        # Issue #4: dependencies are emitted from the grammar tree; this
        # method exists for compatibility with the Usage API.
        if self.grammar is not None and hasattr(self.grammar, 'dump'):
            return self.grammar.dump()
        return "dependency"

    def _get_definition(self, child=None):
        """Build a PackageMember-wrapped Dependency dict for the model tree.

        The Dependency grammar class returns the bare inner shape
        (`{"name": "Dependency", "identification": ..., "clients": ...,
        "suppliers": ..., "body": ...}`). For inclusion in a package body
        we wrap it the same way other definitions are wrapped:
        `PackageMember -> DefinitionElement -> Dependency`.
        """
        if self.grammar is not None and hasattr(self.grammar, 'get_definition'):
            grammar_def = self.grammar.get_definition()
        else:
            grammar_def = {
                "name": "Dependency",
                "identification": None,
                "clients": [],
                "suppliers": [],
                "body": None,
            }
        # Sync identification name
        if self.name is not None and grammar_def.get("identification"):
            grammar_def["identification"]["declaredName"] = self.name
        elif self.name is not None:
            grammar_def["identification"] = {
                "name": "Identification",
                "declaredName": self.name,
                "declaredShortName": None,
            }
        return {
            "name": "PackageMember",
            "prefix": None,
            "ownedRelatedElement": {
                "name": "DefinitionElement",
                "ownedRelatedElement": grammar_def,
            },
        }
