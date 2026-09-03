#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul 11 10:14:18 2023

@author: mycr0ft
"""

import uuid as uuidlib

from typing import TypeVar

from sysmlpy.formatting import classtree
from sysmlpy.navigate import Searchable
from sysmlpy.grammar.classes import (
    Identification,
    PackageMember,
    PackageBody,
    RootNamespace,
)
from sysmlpy.grammar.classes import Package as PackageGrammar

from sysmlpy import Part, Item, Port, Requirement, UseCase, Attribute, Action, Case, AnalysisCase, VerificationCase, Interface, Message, Dependency
from sysmlpy.usage import (
    State, Constraint, Connection, Flow, Calculation, Enumeration,
    Allocation, Metadata, Rendering, Individual, FlowDef,
    View, Viewpoint, Concern,
)

ModelType = TypeVar("Model", bound="Model")


class Model(Searchable):
    """Root model container.  Exposes typed accessors and ``find()`` / ``all()``
    across all child packages and their contents."""

    sysml_type = None  # Model is the root, not a SysML element itself

    def __init__(self):
        """Initialize an empty root model container.

        Creates a UUID-based name and empty children list. The model serves
        as the root namespace for all packages and their contents.
        """
        self.name = str(uuidlib.uuid4())
        self.children = []
        self.typedby = None
        self.grammar = None
        self.parent = None

    def __repr__(self):
        """Return a developer-friendly string representation.

        Returns
        -------
        str
            String showing child elements for debugging.
        """
        cls_name = self.__class__.__name__
        if self.children:
            children_repr = ', '.join(repr(c) for c in self.children)
            return f"{cls_name}(children=[{children_repr}])"
        return f"{cls_name}()"

    def load(self: type[ModelType], s: str, library=None) -> ModelType:
        """Load a SysML model from a string using ANTLR4 parser.
        
        Parameters
        ----------
        s : str
            The SysML source code to parse.
        library : str or Path, optional
            Path to SysML v2 library files for resolving imports.
        
        Returns
        -------
        Model
            The loaded model.
        """
        from sysmlpy import load_grammar_antlr
        
        # Model requires the input to be a package declaration
        # Check if the string starts with a valid SysML keyword that's not 'package' or 'library'
        s_stripped = s.strip() if isinstance(s, str) else s
        if isinstance(s_stripped, str):
            # List of known SysML top-level keywords (definitions and usages that must be wrapped)
            invalid_starts = ['item', 'part', 'port', 'attribute', 'action', 'state',
                              'connection', 'interface', 'requirement', 'case', 'use',
                              'calc', 'constraint', 'concern', 'ref', 'flow', 'allocation',
                              'view', 'viewpoint', 'rendering', 'metadata', 'individual']
            first_word = s_stripped.split(None, 1)[0] if s_stripped.split() else ''
            if first_word in invalid_starts:
                raise ValueError("Base Model must be encapsulated by a package.")
        
        definition = load_grammar_antlr(s, library=library)["ownedRelationship"]

        member_grammar = []
        found_package = False
        for member in definition:
            if "ownedRelatedElement" not in member:
                if member.get("name") in ("Import", "AliasMember"):
                    member_grammar.append(member)
                continue
            elem_type = member["ownedRelatedElement"]["name"]
            if elem_type == "DefinitionElement":
                de = member["ownedRelatedElement"]
                if de["ownedRelatedElement"]["name"] == "Package":
                    found_package = True
                    p = Package().load_from_grammar(
                        PackageGrammar(de["ownedRelatedElement"])
                    )
                    self.children.append(p)
                    member_grammar.append(p._get_definition(child="PackageBody"))
                elif found_package:
                    member_grammar.append(member)
                    p.grammar.body.children.append(PackageMember(member))
            elif elem_type == "UsageElement" and found_package:
                member_grammar.append(member)
                p.grammar.body.children.append(PackageMember(member))

        if not found_package:
            # Wrap bare top-level definitions in a synthetic package
            synthetic_relationships = []
            for member in definition:
                if "ownedRelatedElement" not in member:
                    if member.get("name") in ("Import", "AliasMember"):
                        member_grammar.append(member)
                    continue
                if member["ownedRelatedElement"]["name"] == "DefinitionElement":
                    de = member["ownedRelatedElement"]
                    if de["ownedRelatedElement"]["name"] == "AnnotatingElement":
                        continue
                    synthetic_relationships.append({
                        "name": "PackageMember",
                        "prefix": None,
                        "ownedRelatedElement": de
                    })

            if synthetic_relationships:
                synthetic_definition = {
                    "name": "Package",
                    "declaration": {
                        "name": "PackageDeclaration",
                        "identification": {
                            "name": "Identification",
                            "declaredName": None,
                            "declaredShortName": None,
                        }
                    },
                    "body": {
                        "name": "PackageBody",
                        "ownedRelationship": synthetic_relationships
                    },
                    "ownedRelationship": []
                }
                p = Package().load_from_grammar(
                    PackageGrammar(synthetic_definition)
                )
                self.children.append(p)
                member_grammar.append(p._get_definition(child="PackageBody"))
            else:
                raise ValueError("Base Model must be encapsulated by a package.")

        self.grammar = RootNamespace(
            {"name": "PackageBodyElement", "ownedRelationship": member_grammar}
        )

        return self

    def _ensure_body(self):
        """Rebuild the grammar body from current children and imports.

        Serializes all child elements into PackageMember wrappers while
        preserving ``Import`` and ``AliasMember`` declarations **at their
        original source positions** (v0.58.0).  The existing grammar body
        is used as the ordering template: each ``PackageMember`` slot is
        refilled with the fresh serialization of the next child, and any
        children beyond the recorded slots are appended at the end.

        Returns
        -------
        Model
            Self for chaining.
        """
        # Serialize all current children into PackageMember definitions
        child_defs = []
        for abc in self.children:
            v = abc._get_definition(child="PackageBody")
            if isinstance(v, list):
                for subchild in v:
                    child_defs.append(PackageMember(subchild).get_definition())
            else:
                child_defs.append(PackageMember(v).get_definition())

        existing = getattr(getattr(self, 'grammar', None), 'children', None)

        body = []
        if existing:
            member_iter = iter(child_defs)
            for item in existing:
                cn = item.__class__.__name__
                if cn in ('Import', 'AliasMember'):
                    body.append(item.get_definition())
                elif cn == 'PackageMember':
                    try:
                        body.append(next(member_iter))
                    except StopIteration:
                        break  # children shrank; drop stale members
            # children added programmatically beyond recorded slots
            body.extend(member_iter)
        else:
            body = child_defs

        if len(body) > 0:
            self.grammar = RootNamespace(
                {"name": "PackageBodyElement", "ownedRelationship": body}
            )

        return self

    def _get_definition(self):
        """Return the serialized grammar tree for the model.

        Returns
        -------
        dict
            Grammar tree dict ready for serialization.
        """
        return self.grammar.get_definition()

    def dump(self) -> str:
        """Serialize the model to SysML v2 textual notation.

        Returns
        -------
        str
            SysML v2 source code representing the model.

        Raises
        ------
        ValueError
            If the model has no children to serialize.

        Examples
        --------
        >>> model = sysmlpy.loads('package P { part def Wheel; }')
        >>> print(model.dump())
        package P {
           part def Wheel ;
        }
        """
        if len(self.children) == 0:
            raise ValueError("Base Model has no elements to output.")

        self._ensure_body()
        return classtree(self._get_definition()).dump()

    def __str__(self) -> str:
        """Return the SysML v2 text representation of the model."""
        try:
            return self.dump()
        except Exception:
            return repr(self)

    def _set_child(self, child):
        """Add a child package or element to the model.

        Parameters
        ----------
        child : Package or Usage
            Child element to add.

        Returns
        -------
        Model
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
            Dot-separated path like "pkg.element".

        Returns
        -------
        element or None
            The matching child element, or None if not found.
        """
        return self

    def _get_child(self, featurechain):
        """Retrieve a nested child by dot-separated name path.

        Parameters
        ----------
        featurechain : str
            Dot-separated path like "pkg.element".

        Returns
        -------
        element or None
            The matching child element, or None if not found.
        """
        if isinstance(featurechain, str):
            fc = featurechain.split(".")
        else:
            raise TypeError

        if fc[0] == self.name:
            featurechain = ".".join(fc[1:])

        for child in self.children:
            fcs = featurechain.split(".")
            if child.name == fcs[0]:
                if len(fcs) == 1:
                    return child
                else:
                    return child._get_child(featurechain)

    get_child = _get_child

    # ── Convenience functions ───────────────────────────────────────────

    def find_all(self, type=None, name=None):
        """Recursively find all matching elements across all packages.

        Parameters
        ----------
        type : str or class, optional
            Filter by SysML type (e.g. 'part', Part).
        name : str, optional
            Filter by element name.

        Returns
        -------
        list
            All matching elements across the full tree.
        """
        results = []
        for child in self.children:
            if hasattr(child, "find_all"):
                results.extend(child.find_all(type=type, name=name))
        return results

    def count(self, type=None):
        """Count elements by type across all packages.

        Parameters
        ----------
        type : str or class, optional
            Count only this type. If None, returns a dict of all types.

        Returns
        -------
        int or dict
            Count of matching elements, or dict of {type: count}.
        """
        if type is not None:
            return len(self.find_all(type=type))

        counts = {}
        for child in self.children:
            if hasattr(child, "count"):
                child_counts = child.count()
                for k, v in child_counts.items():
                    counts[k] = counts.get(k, 0) + v
        return counts

    def traverse(self, callback, depth=0):
        """Walk all packages and their trees, calling callback for each element."""
        for child in self.children:
            if hasattr(child, "traverse"):
                child.traverse(callback, depth)

    def to_dict(self):
        """Export the model as a nested dictionary."""
        return {
            "name": "Model",
            "children": [c.to_dict() if hasattr(c, "to_dict") else {"name": getattr(c, "name", None)} for c in self.children],
        }

    def to_graph(self):
        """Export the model as a NetworkX graph.

        Requires: pip install networkx (or: pip install sysmlpy[graph])
        """
        from sysmlpy.store import NetworkXStore, new_id

        store = NetworkXStore()

        def _add_element(elem, parent_id=None):
            eid = new_id()
            data = {
                "name": getattr(elem, "name", None),
                "sysml_type": getattr(elem, "sysml_type", None),
                "python_type": type(elem).__name__,
            }
            store.put(eid, data, parent_id=parent_id)
            if hasattr(elem, "children"):
                for child in elem.children:
                    _add_element(child, eid)

        for child in self.children:
            _add_element(child)
        return store

    def path_between(self, source_name, target_name):
        """Find the path between two elements by name across all packages."""
        for child in self.children:
            if hasattr(child, "path_between"):
                path = child.path_between(source_name, target_name)
                if path is not None:
                    return path
        return None


class Package(Searchable):
    """SysML v2 Package.  Exposes typed accessors and ``find()`` / ``all()``
    across its direct and nested children."""

    sysml_type = "package"

    def __init__(self, name=None, shortname=None):
        """Initialize a SysML v2 Package.

        Parameters
        ----------
        name : str, optional
            Package name.
        shortname : str, optional
            Abbreviated name.
        """
        self.name = str(uuidlib.uuid4())
        self.children = []
        self._imports = []
        self.typedby = None
        self.grammar = PackageGrammar()
        self.parent = None

        if name is not None:
            self._set_name(name)
        if shortname is not None:
            self._set_name(shortname, short=True)

    def __repr__(self):
        """Return a constructor-mirroring string representation.

        Returns
        -------
        str
        """
        name = getattr(self, 'name', None)
        # Suppress auto-generated UUID names
        if name and len(name) == 36 and name.count('-') == 4:
            name = None

        try:
            shortname = getattr(self.grammar.declaration.identification, 'declaredShortName', None)
            if shortname:
                shortname = shortname.strip('<').strip('>')
        except (AttributeError, TypeError):
            shortname = None

        cls_name = self.__class__.__name__
        parts = []
        if name:
            parts.append(f'name={name!r}')
        if shortname:
            parts.append(f'shortname={shortname!r}')
        return f"{cls_name}({', '.join(parts)})"

    def _set_name(self, name, short=False):
        """Set the declared name or short name on the package grammar.

        Parameters
        ----------
        name : str
            The name to set.
        short : bool
            If True, sets the short name. Otherwise sets the declared name.

        Returns
        -------
        Package
            Self for chaining.
        """
        if short:
            if self.grammar.declaration.identification is None:
                self.grammar.declaration.identification = Identification()
            self.grammar.declaration.identification.declaredShortName = name
        else:
            self.name = name
            if self.grammar.declaration.identification is None:
                self.grammar.declaration.identification = Identification()
            self.grammar.declaration.identification.declaredName = name

        return self

    set_name = _set_name

    def _get_name(self):
        """Retrieve the declared name from the package grammar.

        Returns
        -------
        str
            The declared name.
        """
        return self.grammar.declaration.identification.declaredName

    def _set_child(self, child):
        """Add a child element to this package.

        Parameters
        ----------
        child : Usage or Package
            Child element to add.

        Returns
        -------
        Package
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
            Dot-separated path like "pkg.element".

        Returns
        -------
        element or None
            The matching child element, or None if not found.
        """
        return self

    def _get_child(self, featurechain):
        """Retrieve a nested child by dot-separated name path.

        Parameters
        ----------
        featurechain : str
            Dot-separated path like "pkg.element".

        Returns
        -------
        element or None
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

    def _ensure_body(self):
        """Rebuild the package grammar body from current children and imports.

        Serializes all child elements into PackageMember wrappers while
        preserving ``Import`` and ``AliasMember`` declarations **at their
        original source positions** (v0.58.0).  The existing grammar body
        is used as the ordering template: each ``PackageMember`` slot is
        refilled with the fresh serialization of the next child, and any
        children beyond the recorded slots are appended at the end.
        """
        # Serialize all current children into PackageMember definitions
        child_defs = []
        for abc in self.children:
            v = abc._get_definition(child="PackageBody")
            if isinstance(v, list):
                for subchild in v:
                    child_defs.append(PackageMember(subchild).get_definition())
            else:
                child_defs.append(PackageMember(v).get_definition())

        body_children = getattr(
            getattr(getattr(self, 'grammar', None), 'body', None), 'children', None
        )

        body = []
        if body_children:
            member_iter = iter(child_defs)
            for item in body_children:
                cn = item.__class__.__name__
                if cn in ('Import', 'AliasMember'):
                    body.append(item.get_definition())
                elif cn == 'PackageMember':
                    try:
                        body.append(next(member_iter))
                    except StopIteration:
                        break  # children shrank; drop stale members
            # children added programmatically beyond recorded slots
            body.extend(member_iter)
        else:
            body = child_defs

        if len(body) > 0:
            self.grammar.body = PackageBody(
                {"name": "PackageBody", "ownedRelationship": body}
            )

    def _get_definition(self, child=None):
        """Build the grammar tree dict for this package.

        Parameters
        ----------
        child : bool, optional
            If False, wraps output in a PackageBodyElement.

        Returns
        -------
        dict
            Nested dict ready for serialization.
        """
        self._ensure_body()

        package = {
            "name": "DefinitionElement",
            "ownedRelatedElement": self.grammar.get_definition(),
        }
        package = {
            "name": "PackageMember",
            "ownedRelatedElement": package,
            "prefix": None,
        }
        if not child:
            package = {
                "name": "PackageBodyElement",
                "ownedRelationship": [package],
                "prefix": None,
            }

        # Packages cannot be typed; they should import from other packages.
        # If typedby is set, print a warning and ignore it.
        if self.typedby is not None:
            print(f"[Package] Warning: Packages cannot be typed. Ignoring typedby '{self.typedby.name}'. Use imports instead.")  # pragma: no cover

        return package

    def dump(self, child=None) -> str:
        """Serialize the package to SysML v2 textual notation.

        Parameters
        ----------
        child : bool, optional
            If False, wraps output in a PackageBodyElement. Default is None.

        Returns
        -------
        str
            SysML v2 source code representing the package.
        """
        return classtree(self._get_definition(child=False)).dump()

    def __str__(self) -> str:
        """Return the SysML v2 text representation of the package."""
        try:
            return self.dump()
        except Exception:
            return repr(self)

    def add_import(self, namespace, visibility="private", recursive=False, membership=None):
        """Add an import declaration to this package.

        Parameters
        ----------
        namespace : str or list
            Namespace to import (e.g., 'ScalarValues' or ['ISQ', 'Mechanics']).
            For namespace imports, use '::' suffix for wildcard (e.g., 'ScalarValues::*').
        visibility : str, optional
            Visibility keyword: 'private', 'public', or 'protected'. Default is 'private'.
        recursive : bool, optional
            If True, imports recursively (adds '::**' suffix). Default is False.
        membership : str, optional
            If provided, creates a membership import for a specific element
            (e.g., 'SomeElement' imports 'namespace::SomeElement').

        Returns
        -------
        Package
            Self for chaining.

        Examples
        --------
        >>> pkg.add_import('ScalarValues', visibility='private')
        >>> pkg.add_import('ISQ::Mechanics', visibility='public')
        >>> pkg.add_import('BaseTypes', visibility='protected', membership='SomeElement')
        """
        from sysmlpy.grammar.classes import (
            Import, NamespaceImport, MembershipImport, ImportPrefix,
            ImportedNamespace, ImportedMembership, VisibilityIndicator,
            RelationshipBody, QualifiedName
        )

        if visibility not in ('private', 'public', 'protected'):
            raise ValueError(
                f"visibility must be 'private', 'public', or 'protected', not '{visibility}'"
            )

        # Parse namespace string
        if isinstance(namespace, str):
            # Handle wildcard suffix
            is_wildcard = namespace.endswith('::*')
            if is_wildcard:
                namespace = namespace[:-3]  # Remove '::*'
            parts = namespace.split('::')
        elif isinstance(namespace, (list, tuple)):
            parts = list(namespace)
            is_wildcard = False
        else:
            raise TypeError("namespace must be str or list/tuple")

        # Create visibility indicator
        vis_def = {
            "name": "VisibilityIndicator",
            "private": "private" if visibility == "private" else "",
            "protected": "protected" if visibility == "protected" else "",
            "public": "public" if visibility == "public" else "",
        }
        vis = VisibilityIndicator(vis_def)

        # Create import prefix
        prefix_def = {
            "name": "ImportPrefix",
            "visibility": vis_def,
            "isImportAll": False,
        }
        prefix = ImportPrefix(prefix_def)

        if membership is not None:
            # Membership import: import visibility namespace::membership
            if isinstance(membership, str):
                mem_parts = membership.split('::')
            else:
                mem_parts = list(membership)

            mem_name = QualifiedName({"name": "QualifiedName", "names": parts + mem_parts})
            imported_mem = ImportedMembership({
                "name": "ImportedMembership",
                "importedMembership": {"name": "QualifiedName", "names": parts + mem_parts},
                "isRecursive": recursive,
            })
            imported_mem.name = mem_name

            mem_import = MembershipImport({
                "name": "MembershipImport",
                "prefix": prefix_def,
                "membership": imported_mem.get_definition(),
            })
            mem_import.prefix = prefix
            mem_import.membership = imported_mem

            import_rel = Import({
                "name": "Import",
                "body": {"name": "RelationshipBody", "ownedRelationship": []},
                "ownedRelationship": mem_import.get_definition(),
            })
            import_rel.body = RelationshipBody({"name": "RelationshipBody", "ownedRelationship": []})
            import_rel.children = [mem_import]
        else:
            # Namespace import: import visibility namespace::* or namespace
            ns_name = QualifiedName({"name": "QualifiedName", "names": parts})
            imported_ns = ImportedNamespace({
                "name": "ImportedNamespace",
                "namespace": {"name": "QualifiedName", "names": parts},
                "isRecursive": recursive,
            })
            imported_ns.namespaces = ns_name
            imported_ns.isRecursive = recursive

            ns_import = NamespaceImport({
                "name": "NamespaceImport",
                "prefix": prefix_def,
                "ownedRelatedElement": [],
                "namespace": imported_ns.get_definition(),
            })
            ns_import.prefix = prefix
            ns_import.namespace = imported_ns
            ns_import.children = []

            import_rel = Import({
                "name": "Import",
                "body": {"name": "RelationshipBody", "ownedRelationship": []},
                "ownedRelationship": ns_import.get_definition(),
            })
            import_rel.body = RelationshipBody({"name": "RelationshipBody", "ownedRelationship": []})
            import_rel.children = [ns_import]

        # Add to grammar body
        if not hasattr(self.grammar, 'body') or self.grammar.body is None:
            self.grammar.body = PackageBody({"name": "PackageBody", "ownedRelationship": []})

        self.grammar.body.children.append(import_rel)
        self._imports.append(import_rel)
        return self

    @property
    def imports(self):
        """Import and AliasMember declarations in this package.

        Returns
        -------
        list
            Grammar objects (Import or AliasMember) that belong to this package.
        """
        return list(self._imports)

    def load_from_grammar(self, grammar):
        """Load package structure from a parsed grammar object.

        Populates the package's name, children, and imports from the
        ANTLR-parsed grammar tree.

        Parameters
        ----------
        grammar : PackageGrammar
            Parsed grammar object representing a SysML v2 package.

        Returns
        -------
        Package
            Self for chaining.
        """
        # Get the identification values
        declared_name = grammar.declaration.identification.declaredName
        declared_shortname = grammar.declaration.identification.declaredShortName if hasattr(grammar.declaration.identification, 'declaredShortName') else None
        
        # Handle the different cases:
        if declared_shortname and declared_name:
            # Both short and long name provided
            self.name = declared_name
            self._set_name(declared_shortname, short=True)
        elif declared_shortname and not declared_name:
            # Only short name is provided - use it as name
            self.name = declared_shortname
            self._set_name(declared_shortname, short=True)
        elif declared_name:
            # Only long name provided
            self.name = declared_name
        
        self.grammar = grammar
        for child in grammar.body.children:
            # Navigate the nested structure:
            # DefinitionBodyItem -> NonOccurrenceUsageMember -> NonOccurrenceUsageElement -> StructureUsageElement/BehaviorUsageElement
            # Or: DefinitionBodyItem -> PackageMember -> DefinitionElement -> ItemDefinition/PartDefinition
            # Or: DefinitionBodyItem -> PackageMember -> UsageElement -> OccurrenceUsageElement -> StructureUsageElement -> ItemUsage/PartUsage
            # Or: PackageBody -> UsageElement directly (for analysis cases in packages)
            if not hasattr(child, 'children') or not child.children:
                continue
            
            # Handle case where child.children is a single object (not a list)
            if isinstance(child.children, list):
                first_child = child.children[0]
            else:
                first_child = child.children
            
            # Handle NonOccurrenceUsageMember (for usages like item, attribute)
            if first_child.__class__.__name__ == 'NonOccurrenceUsageMember':
                if hasattr(first_child, 'children') and first_child.children:
                    second = first_child.children[0]
                    if hasattr(second, 'children'):
                        # NonOccurrenceUsageElement -> StructureUsageElement or BehaviorUsageElement
                        inner_element = second.children
                    else:
                        inner_element = second
                else:
                    continue
            # Handle OccurrenceUsageMember (for ports, parts, items as occurrence usages)
            elif first_child.__class__.__name__ == 'OccurrenceUsageMember':
                if hasattr(first_child, 'children') and first_child.children:
                    second = first_child.children[0]
                    if hasattr(second, 'children'):
                        # OccurrenceUsageElement -> StructureUsageElement -> PortUsage/PartUsage/etc
                        struct_elem = second.children
                        if hasattr(struct_elem, 'children'):
                            inner_element = struct_elem.children
                        else:
                            inner_element = struct_elem
                    else:
                        inner_element = second
                else:
                    continue
            # Handle DefinitionElement (for definitions like item def, part def)
            elif first_child.__class__.__name__ == 'DefinitionElement':
                if hasattr(first_child, 'children') and first_child.children:
                    inner_element = first_child.children[0]
                else:
                    continue
            # Handle UsageElement (for usages like item Hydrogen : Fuel, action Act1)
            elif first_child.__class__.__name__ == 'UsageElement':
                if hasattr(first_child, 'children') and first_child.children:
                    # Navigate: UsageElement -> OccurrenceUsageElement/NonOccurrenceUsageElement -> Usage
                    # first_child.children can be an object (not a list)
                    occ = first_child.children
                    
                    # Check if it's OccurrenceUsageElement (has children containing Structure/Behavior element)
                    if hasattr(occ, 'children') and occ.children:
                        inner = occ.children
                        # Check if it's StructureUsageElement or BehaviorUsageElement
                        if hasattr(inner, 'children'):
                            inner_element = inner.children
                        else:
                            inner_element = inner
                    # Check if it's NonOccurrenceUsageElement
                    elif hasattr(occ, 'ownedRelationship') or hasattr(occ, 'declaration'):
                        inner_element = occ
                    else:
                        continue
                else:
                    continue
            else:
                continue
            
            inner_class = inner_element.__class__.__name__
            
            if inner_class == "ItemUsage":
                child = Item().load_from_grammar(inner_element)
                child.parent = self
                self.children.append(child)
            elif inner_class == "PartUsage":
                child = Part().load_from_grammar(inner_element)
                child.parent = self
                self.children.append(child)
            elif inner_class == "PortUsage":
                child = Port().load_from_grammar(inner_element)
                child.parent = self
                self.children.append(child)
            elif inner_class == "Package":
                child = Package().load_from_grammar(inner_element)
                child.parent = self
                self.children.append(child)
            elif inner_class == "ItemDefinition":
                child = Item().load_from_grammar(inner_element)
                child.parent = self
                self.children.append(child)
            elif inner_class == "PartDefinition":
                child = Part(definition=True).load_from_grammar(inner_element)
                child.parent = self
                self.children.append(child)
            elif inner_class == "PortDefinition":
                child = Port(definition=True).load_from_grammar(inner_element)
                child.parent = self
                self.children.append(child)
            elif inner_class == "AttributeDefinition":
                child = Attribute(definition=True).load_from_grammar(inner_element)
                child.parent = self
                self.children.append(child)
            elif inner_class == "AttributeUsage":
                child = Attribute().load_from_grammar(inner_element)
                child.parent = self
                self.children.append(child)
            elif inner_class == "ActionDefinition":
                child = Action(definition=True).load_from_grammar(inner_element)
                child.parent = self
                self.children.append(child)
            elif inner_class == "RequirementDefinition":
                child = Requirement(definition=True).load_from_grammar(inner_element)
                child.parent = self
                self.children.append(child)
            elif inner_class == "UseCaseDefinition":
                child = UseCase(definition=True).load_from_grammar(inner_element)
                child.parent = self
                self.children.append(child)
            elif inner_class == "UseCaseUsage":
                child = UseCase().load_from_grammar(inner_element)
                child.parent = self
                self.children.append(child)
            elif inner_class == "Message":
                m = Message().load_from_grammar(inner_element)
                m.parent = self
                self.children.append(m)
            elif inner_class == "ActionUsage":
                child = Action(grammar=inner_element).load_from_grammar(inner_element)
                child.parent = self
                self.children.append(child)
            elif inner_class == "RequirementUsage":
                child = Requirement().load_from_grammar(inner_element)
                child.parent = self
                self.children.append(child)
            elif inner_class == "SatisfyRequirementUsage":
                child = Requirement().load_from_grammar(inner_element)
                child.parent = self
                self.children.append(child)
            elif inner_class == "ConstraintDefinition":
                c = Constraint(definition=True)
                c.grammar = inner_element
                if hasattr(inner_element, 'declaration') and hasattr(inner_element.declaration, 'identification') and inner_element.declaration.identification:
                    c.name = inner_element.declaration.identification.declaredName
                c.parent = self
                self.children.append(c)
            elif inner_class == "ConstraintUsage":
                c = Constraint()
                c.grammar = inner_element
                try:
                    if hasattr(inner_element, 'declaration') and inner_element.declaration:
                        decl = inner_element.declaration
                        if hasattr(decl, 'declaration') and decl.declaration:
                            inner_decl = decl.declaration
                            if hasattr(inner_decl, 'declaration') and inner_decl.declaration:
                                feat_decl = inner_decl.declaration
                                if hasattr(feat_decl, 'identification') and feat_decl.identification:
                                    c.name = feat_decl.identification.declaredName
                except AttributeError:
                    pass
                c.parent = self
                self.children.append(c)
            elif inner_class == "StateDefinition":
                s = State(definition=True).load_from_grammar(inner_element)
                s.parent = self
                self.children.append(s)
            elif inner_class == "StateUsage":
                s = State().load_from_grammar(inner_element)
                s.parent = self
                self.children.append(s)
            elif inner_class == "CalculationDefinition":
                c = Calculation(definition=True)
                c.grammar = inner_element
                if hasattr(inner_element, 'declaration') and hasattr(inner_element.declaration, 'identification') and inner_element.declaration.identification:
                    c.name = inner_element.declaration.identification.declaredName
                c.parent = self
                self.children.append(c)
            elif inner_class == "CalculationUsage":
                c = Calculation()
                c.grammar = inner_element
                try:
                    if hasattr(inner_element, 'declaration') and inner_element.declaration:
                        decl = inner_element.declaration
                        if hasattr(decl, 'declaration') and decl.declaration:
                            inner_decl = decl.declaration
                            if hasattr(inner_decl, 'declaration') and inner_decl.declaration:
                                feat_decl = inner_decl.declaration
                                if hasattr(feat_decl, 'identification') and feat_decl.identification:
                                    c.name = feat_decl.identification.declaredName
                except AttributeError:
                    pass
                c.parent = self
                self.children.append(c)
            elif inner_class == "ConnectionDefinition":
                c = Connection(definition=True)
                c.grammar = inner_element
                if hasattr(inner_element, 'definition') and hasattr(inner_element.definition, 'declaration') and inner_element.definition.declaration:
                    decl = inner_element.definition.declaration
                    if hasattr(decl, 'identification') and decl.identification:
                        c.name = decl.identification.declaredName
                c.parent = self
                self.children.append(c)
            elif inner_class == "ConnectionUsage":
                c = Connection()
                c.grammar = inner_element
                if hasattr(inner_element, 'declaration') and inner_element.declaration:
                    decl = inner_element.declaration
                    if hasattr(decl, 'declaration') and decl.declaration:
                        feat_decl = decl.declaration
                        if hasattr(feat_decl, 'identification') and feat_decl.identification:
                            c.name = feat_decl.identification.declaredName
                c.parent = self
                self.children.append(c)
            elif inner_class == "FlowConnectionDefinition":
                f = Flow(definition=True)
                f.grammar = inner_element
                if hasattr(inner_element, 'definition') and hasattr(inner_element.definition, 'declaration') and inner_element.definition.declaration:
                    decl = inner_element.definition.declaration
                    if hasattr(decl, 'identification') and decl.identification:
                        f.name = decl.identification.declaredName
                f.parent = self
                self.children.append(f)
            elif inner_class == "FlowConnectionUsage":
                f = Flow()
                f.grammar = inner_element
                if hasattr(inner_element, 'declaration') and inner_element.declaration:
                    decl = inner_element.declaration
                    if hasattr(decl, 'declaration') and decl.declaration:
                        feat_decl = decl.declaration
                        if hasattr(feat_decl, 'identification') and feat_decl.identification:
                            f.name = feat_decl.identification.declaredName
                f.parent = self
                self.children.append(f)
            elif inner_class == "EnumerationDefinition":
                e = Enumeration(name=None)
                e.grammar = inner_element
                if hasattr(inner_element, 'declaration') and hasattr(inner_element.declaration, 'identification') and inner_element.declaration.identification:
                    e.name = inner_element.declaration.identification.declaredName
                e.parent = self
                self.children.append(e)
            elif inner_class == "AllocationDefinition":
                a = Allocation(definition=True)
                a.grammar = inner_element
                if hasattr(inner_element, 'definition') and inner_element.definition:
                    if hasattr(inner_element.definition, 'declaration') and inner_element.definition.declaration:
                        decl = inner_element.definition.declaration
                        if hasattr(decl, 'identification') and decl.identification:
                            a.name = decl.identification.declaredName
                a.parent = self
                self.children.append(a)
            elif inner_class == "AllocationUsage":
                a = Allocation()
                a.grammar = inner_element
                if hasattr(inner_element, 'declaration') and inner_element.declaration:
                    decl = inner_element.declaration
                    if hasattr(decl, 'declaration') and decl.declaration:
                        feat_decl = decl.declaration
                        if hasattr(feat_decl, 'identification') and feat_decl.identification:
                            a.name = feat_decl.identification.declaredName
                a.parent = self
                self.children.append(a)
            elif inner_class == "MetadataDefinition":
                m = Metadata(definition=True)
                m.grammar = inner_element
                if hasattr(inner_element, 'definition') and inner_element.definition:
                    if hasattr(inner_element.definition, 'declaration') and inner_element.definition.declaration:
                        decl = inner_element.definition.declaration
                        if hasattr(decl, 'identification') and decl.identification:
                            m.name = decl.identification.declaredName
                m.parent = self
                self.children.append(m)
            elif inner_class == "MetadataUsage":
                m = Metadata()
                m.grammar = inner_element
                if hasattr(inner_element, 'declaration') and inner_element.declaration:
                    decl = inner_element.declaration
                    if hasattr(decl, 'declaration') and decl.declaration:
                        feat_decl = decl.declaration
                        if hasattr(feat_decl, 'identification') and feat_decl.identification:
                            m.name = feat_decl.identification.declaredName
                m.parent = self
                self.children.append(m)
            elif inner_class == "RenderingDefinition":
                r = Rendering()
                r.grammar = inner_element
                if hasattr(inner_element, 'declaration') and inner_element.declaration:
                    decl = inner_element.declaration
                    if hasattr(decl, 'declaration') and decl.declaration:
                        feat_decl = decl.declaration
                        if hasattr(feat_decl, 'identification') and feat_decl.identification:
                            r.name = feat_decl.identification.declaredName
                r.parent = self
                self.children.append(r)
            elif inner_class == "RenderingUsage":
                r = Rendering()
                r.grammar = inner_element
                if hasattr(inner_element, 'declaration') and inner_element.declaration:
                    decl = inner_element.declaration
                    if hasattr(decl, 'declaration') and decl.declaration:
                        feat_decl = decl.declaration
                        if hasattr(feat_decl, 'identification') and feat_decl.identification:
                            r.name = feat_decl.identification.declaredName
                r.parent = self
                self.children.append(r)
            elif inner_class == "IndividualDefinition":
                i = Individual(definition=True)
                i.grammar = inner_element
                if hasattr(inner_element, 'definition') and inner_element.definition:
                    if hasattr(inner_element.definition, 'declaration') and inner_element.definition.declaration:
                        decl = inner_element.definition.declaration
                        if hasattr(decl, 'identification') and decl.identification:
                            i.name = decl.identification.declaredName
                i.parent = self
                self.children.append(i)
            elif inner_class == "IndividualUsage" or inner_class == "IndividualUsageSimple":
                i = Individual()
                i.grammar = inner_element
                if hasattr(inner_element, 'declaration') and inner_element.declaration:
                    decl = inner_element.declaration
                    if hasattr(decl, 'declaration') and decl.declaration:
                        feat_decl = decl.declaration
                        if hasattr(feat_decl, 'identification') and feat_decl.identification:
                            i.name = feat_decl.identification.declaredName
                i.parent = self
                self.children.append(i)
            elif inner_class == "FlowDefinition":
                f = FlowDef(name=None)
                f.grammar = inner_element
                if hasattr(inner_element, 'definition') and inner_element.definition:
                    if hasattr(inner_element.definition, 'declaration') and inner_element.definition.declaration:
                        decl = inner_element.definition.declaration
                        if hasattr(decl, 'identification') and decl.identification:
                            f.name = decl.identification.declaredName
                f.parent = self
                self.children.append(f)
            elif inner_class == "ViewDefinition":
                v = View(definition=True).load_from_grammar(inner_element)
                v.parent = self
                self.children.append(v)
            elif inner_class == "ViewUsage":
                v = View().load_from_grammar(inner_element)
                v.parent = self
                self.children.append(v)
            elif inner_class == "ViewpointDefinition":
                vp = Viewpoint(definition=True)
                vp.grammar = inner_element
                if hasattr(inner_element, 'declaration') and inner_element.declaration:
                    decl = inner_element.declaration
                    if hasattr(decl, 'identification') and decl.identification:
                        vp.name = decl.identification.declaredName
                vp.parent = self
                self.children.append(vp)
            elif inner_class == "ViewpointUsage":
                vp = Viewpoint()
                vp.grammar = inner_element
                if hasattr(inner_element, 'declaration') and inner_element.declaration:
                    decl = inner_element.declaration
                    if hasattr(decl, 'declaration') and decl.declaration:
                        feat_decl = decl.declaration
                        if hasattr(feat_decl, 'identification') and feat_decl.identification:
                            vp.name = feat_decl.identification.declaredName
                vp.parent = self
                self.children.append(vp)
            elif inner_class == "ConcernDefinition":
                c = Concern(definition=True)
                c.grammar = inner_element
                if hasattr(inner_element, 'declaration') and inner_element.declaration:
                    decl = inner_element.declaration
                    if hasattr(decl, 'identification') and decl.identification:
                        c.name = decl.identification.declaredName
                c.parent = self
                self.children.append(c)
            elif inner_class == "ConcernUsage":
                c = Concern()
                c.grammar = inner_element
                if hasattr(inner_element, 'declaration') and inner_element.declaration:
                    decl = inner_element.declaration
                    if hasattr(decl, 'declaration') and decl.declaration:
                        feat_decl = decl.declaration
                        if hasattr(feat_decl, 'identification') and feat_decl.identification:
                            c.name = feat_decl.identification.declaredName
                c.parent = self
                self.children.append(c)
            elif inner_class == "CaseDefinition":
                c = Case(definition=True)
                c.grammar = inner_element
                if hasattr(inner_element, 'declaration') and inner_element.declaration:
                    decl = inner_element.declaration
                    if hasattr(decl, 'identification') and decl.identification:
                        c.name = decl.identification.declaredName
                c.parent = self
                self.children.append(c)
            elif inner_class == "AnalysisCaseDefinition":
                c = AnalysisCase(definition=True)
                c.grammar = inner_element
                if hasattr(inner_element, 'declaration') and inner_element.declaration:
                    decl = inner_element.declaration
                    if hasattr(decl, 'identification') and decl.identification:
                        c.name = decl.identification.declaredName
                c.parent = self
                self.children.append(c)
            elif inner_class == "VerificationCaseDefinition":
                c = VerificationCase(definition=True)
                c.grammar = inner_element
                if hasattr(inner_element, 'declaration') and inner_element.declaration:
                    decl = inner_element.declaration
                    if hasattr(decl, 'identification') and decl.identification:
                        c.name = decl.identification.declaredName
                c.parent = self
                self.children.append(c)
            elif inner_class == "VerificationCaseUsage":
                # v0.62.0: `verification <name> : <Type>` usage at package
                # level (requirement traceability support).
                c = VerificationCase()
                c.grammar = inner_element
                if hasattr(inner_element, 'declaration') and inner_element.declaration:
                    decl = inner_element.declaration
                    # CalculationUsageDeclaration → UsageDeclaration →
                    # FeatureDeclaration → Identification
                    usage_decl = getattr(decl, 'declaration', None)
                    if usage_decl := getattr(usage_decl, 'declaration', None) or usage_decl:
                        feat_decl = usage_decl
                        if hasattr(feat_decl, 'identification') and feat_decl.identification:
                            c.name = feat_decl.identification.declaredName
                c.parent = self
                self.children.append(c)
            elif inner_class == "AnnotatingElement":
                wrapper = _GrammarAnnotationWrapper(inner_element)
                wrapper.parent = self
                self.children.append(wrapper)
            elif inner_class == "InterfaceDefinition":
                i = Interface(definition=True).load_from_grammar(inner_element)
                i.parent = self
                self.children.append(i)
            elif inner_class == "InterfaceUsage":
                i = Interface().load_from_grammar(inner_element)
                i.parent = self
                self.children.append(i)
            elif inner_class == "UseCaseDefinition":
                child = UseCase(definition=True).load_from_grammar(inner_element)
                child.parent = self
                self.children.append(child)
            elif inner_class == "UseCaseUsage":
                child = UseCase().load_from_grammar(inner_element)
                child.parent = self
                self.children.append(child)
            elif inner_class == "Message":
                m = Message().load_from_grammar(inner_element)
                m.parent = self
                self.children.append(m)
            elif inner_class == "AssertConstraintUsage":
                c = Constraint()
                c.grammar = inner_element
                if hasattr(inner_element, 'declaration') and inner_element.declaration:
                    decl = inner_element.declaration
                    if hasattr(decl, 'declaration') and decl.declaration:
                        feat_decl = decl.declaration
                        if hasattr(feat_decl, 'identification') and feat_decl.identification:
                            c.name = feat_decl.identification.declaredName
                c.parent = self
                self.children.append(c)
            elif inner_class == "RequirementUsage":
                r = Requirement()
                r.grammar = inner_element
                if hasattr(inner_element, 'declaration') and inner_element.declaration:
                    decl = inner_element.declaration
                    if hasattr(decl, 'declaration') and decl.declaration:
                        feat_decl = decl.declaration
                        if hasattr(feat_decl, 'identification') and feat_decl.identification:
                            r.name = feat_decl.identification.declaredName
                r.parent = self
                self.children.append(r)
            elif inner_class == "SatisfyRequirementUsage":
                r = Requirement()
                r.grammar = inner_element
                if hasattr(inner_element, 'declaration') and inner_element.declaration:
                    decl = inner_element.declaration
                    if hasattr(decl, 'declaration') and decl.declaration:
                        feat_decl = decl.declaration
                        if hasattr(feat_decl, 'identification') and feat_decl.identification:
                            r.name = feat_decl.identification.declaredName
                r.parent = self
                self.children.append(r)
            elif inner_class == "Dependency":
                # Issue #4: dependency statements were silently dropped
                # because no visitor dispatch produced a Dependency dict and
                # Package.load_from_grammar had no branch for it.
                d = Dependency()
                d.grammar = inner_element
                if hasattr(inner_element, 'identification') and inner_element.identification:
                    d.name = inner_element.identification.declaredName
                d.parent = self
                self.children.append(d)
            else:
                print(f"[Package.load_from_grammar] Unknown class: {inner_class} - skipping")  # pragma: no cover
        
        # Collect Import and AliasMember grammar objects for public API access
        self._imports = []
        for child in grammar.body.children:
            if child.__class__.__name__ in ('Import', 'AliasMember'):
                self._imports.append(child)
        
        return self

    def _get_grammar(self):
        """Ensure the grammar body is up to date and return the grammar object.

        Returns
        -------
        PackageGrammar
            The underlying grammar instance.
        """
        # Force updates to grammar if something has changed.
        self._ensure_body()
        return self.grammar

    # ── Convenience functions ───────────────────────────────────────────

    def find_all(self, type=None, name=None):
        """Recursively find all matching elements in this package and children.

        Parameters
        ----------
        type : str or class, optional
            Filter by SysML type (e.g. 'part', Part).
        name : str, optional
            Filter by element name.

        Returns
        -------
        list
            All matching elements across the full tree.
        """
        results = []
        for child in self.children:
            match = True
            if name is not None and getattr(child, "name", None) != name:
                match = False
            if type is not None:
                child_type = getattr(child, "sysml_type", None)
                if isinstance(type, str):
                    if child_type != type:
                        match = False
                else:
                    if not isinstance(child, type):
                        match = False
            if match:
                results.append(child)
            if hasattr(child, "find_all"):
                results.extend(child.find_all(type=type, name=name))
        return results

    def count(self, type=None):
        """Count elements by type across the full tree.

        Parameters
        ----------
        type : str or class, optional
            Count only this type. If None, returns a dict of all types.

        Returns
        -------
        int or dict
            Count of matching elements, or dict of {type: count}.
        """
        if type is not None:
            return len(self.find_all(type=type))

        counts = {}
        for child in self.children:
            t = getattr(child, "sysml_type", "unknown")
            counts[t] = counts.get(t, 0) + 1
            if hasattr(child, "count"):
                child_counts = child.count()
                for k, v in child_counts.items():
                    counts[k] = counts.get(k, 0) + v
        return counts

    def traverse(self, callback, depth=0):
        """Walk the element tree, calling callback for each element.

        Parameters
        ----------
        callback : callable
            Called as callback(element, depth) for each element.
        depth : int
            Current depth level (internal use).
        """
        for child in self.children:
            callback(child, depth)
            if hasattr(child, "traverse"):
                child.traverse(callback, depth + 1)

    def to_dict(self):
        """Export the package and all children as a nested dictionary.

        Returns
        -------
        dict
            Nested dict representation of the package tree.
        """
        result = {
            "name": getattr(self, "name", None),
            "sysml_type": getattr(self, "sysml_type", None),
            "children": [],
        }
        for child in self.children:
            if hasattr(child, "to_dict"):
                result["children"].append(child.to_dict())
            else:
                result["children"].append({
                    "name": getattr(child, "name", None),
                    "sysml_type": getattr(child, "sysml_type", None),
                })
        return result

    def to_graph(self):
        """Export the package tree as a NetworkX graph.

        Requires: pip install networkx (or: pip install sysmlpy[graph])

        Returns
        -------
        NetworkXStore
            A graph store with elements as nodes and parent-child
            relationships as edges.
        """
        from sysmlpy.store import NetworkXStore, new_id, REL_PARENT_CHILD

        store = NetworkXStore()
        id_map = {}

        def _add_element(elem, parent_id=None):
            eid = new_id()
            id_map[id(elem)] = eid
            data = {
                "name": getattr(elem, "name", None),
                "sysml_type": getattr(elem, "sysml_type", None),
                "python_type": type(elem).__name__,
            }
            store.put(eid, data, parent_id=parent_id)
            if hasattr(elem, "children"):
                for child in elem.children:
                    child_id = _add_element(child, eid)
            return eid

        _add_element(self)
        return store

    def path_between(self, source_name, target_name):
        """Find the path between two elements by name.

        Parameters
        ----------
        source_name : str
            Name of the source element.
        target_name : str
            Name of the target element.

        Returns
        -------
        list or None
            List of element names forming the path, or None if no path exists.
        """
        source = self.find(name=source_name, recursive=True)
        target = self.find(name=target_name, recursive=True)
        if source is None or target is None:
            return None
        # find() returns a list
        if isinstance(source, list):
            source = source[0] if source else None
        if isinstance(target, list):
            target = target[0] if target else None
        if source is None or target is None:
            return None

        # Build parent chain for both
        def parent_chain(elem):
            chain = [elem]
            current = elem
            while hasattr(current, "parent") and current.parent is not None:
                chain.append(current.parent)
                current = current.parent
            return chain

        source_chain = parent_chain(source)
        target_chain = parent_chain(target)

        # Find common ancestor
        source_set = {id(e): e for e in source_chain}
        for e in target_chain:
            if id(e) in source_set:
                common = e
                break
        else:
            return None

        # Build path: source -> ... -> common -> ... -> target
        path = []
        current = source
        while current is not common:
            path.append(getattr(current, "name", "?"))
            current = getattr(current, "parent", None)
        path.append(getattr(common, "name", "?"))

        target_to_common = []
        current = target
        while current is not common:
            target_to_common.append(getattr(current, "name", "?"))
            current = getattr(current, "parent", None)
        path.extend(reversed(target_to_common))

        return path


class _GrammarAnnotationWrapper:
    """Minimal wrapper for grammar-only elements (doc/comment) that need _get_definition."""
    def __init__(self, grammar_obj):
        self.grammar = grammar_obj
        self.name = None

    def _get_definition(self, child=None):
        if hasattr(self.grammar, 'get_definition'):
            inner = self.grammar.get_definition()
        else:
            inner = {"name": type(self.grammar).__name__}
        return {
            "name": "PackageMember",
            "prefix": None,
            "ownedRelatedElement": {
                "name": "DefinitionElement",
                "ownedRelatedElement": inner
            }
        }
