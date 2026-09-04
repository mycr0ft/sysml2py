#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PlantUML generator for SysML v2 models parsed by sysmlpy.

Follows the approach of the official SysML v2 Pilot Implementation:
maps SysML v2 relationships to PlantUML arrow approximations with
thickness/color differentiation and stereotype-based element styling.

Supports multiple rendering styles per SysML v2 View semantics:
- Graphical rendering (default): elements as shapes with relationship arrows
- Interconnection diagram: focus on connectors, bindings, and flows
- Tree diagram: hierarchical containment structure
- Element table: tabular listing of elements and properties
- Textual notation: structured text representation
"""

from sysmlpy.usage import Usage
from sysmlpy.definition import Model, Package


# ============================================================
# Relationship Arrow Mappings
# Ground truth: the official org.omg.sysml.plantuml reference impl
# (SysML2PlantUMLStyle.StyleRelDefaultSwitch, B&W default style) and
# the OMG "Intro to the SysML v2 Language — Graphical Notation"
# figures (v0.67.0 — Goal 6 notation fidelity).
# ============================================================

ARROW_STYLES = {
    # Containment / Membership
    "composite":      "*--",       # filled diamond (isComposite=True)
    "shared":         "o--",       # hollow diamond (isComposite=False)
    "owning":         "+--",       # plus sign (owning membership)
    "non_owning":     "+..",       # dotted plus (non-owning membership)
    "variant":        "+---",      # variant membership (official: +---)

    # Typing / Specialization
    "typing":         "--:|>",     # colon + block arrow (feature typing)
    "specialization": "--|>",      # block arrow (general specialization)
    "redefinition":   "--||>",     # double bar + block arrow (distinct!)

    # Connections
    "binding":        "-[thickness=5]-",   # thick plain line: «bind»/=
                                           # (both sides asserted equal)
    "connector":      "-[thickness=3]-",   # thick plain line, no arrowhead
                                           # (arrow only when it carries
                                           # metadata — official convention)
    "connector_directed": "-[thickness=3]->",
    "flow":           "-->",       # solid thin arrow (item flow)
    "succession":     "-->",       # solid thin arrow (succession)
    "succession_flow": "..>",      # dotted arrow (SuccessionFlowUsage)
    "allocation":     "-[thickness=5,dotted]->",  # thick dotted arrow

    # Dependencies
    "dependency":     "..>>",      # dotted double-arrow
    "satisfy":        "-->",       # solid arrow (SatisfyRequirementUsage)
    "verify":         "-->",       # solid arrow
    "derive":         "..>",       # dashed line, «derive»/#derive label
                                   # (spec figure; official pilot omits it)
    "refine":         "..>>",      # dotted double-arrow
    "perform":        "-->",       # PerformActionUsage
    "exhibit":        "-->",       # ExhibitStateUsage
    "include_use_case": "-->",     # IncludeUseCaseUsage

    # Actions (asynchronous messages)
    "send_action":    "..>>",      # send action: dotted double-arrow out
    "accept_action":  "<<..",      # accept action: reversed (arrives here)

    # Requirements extras
    "objective":      "-->>",      # objective membership (req objectives)

    # Comments / Annotations
    "comment":        "..",        # dotted line, no arrowhead
    "metadata":       "..@",       # metadata annotation
    "import":         "..>",       # dotted arrow
}


# ============================================================
# Stereotype Mappings
# Maps sysml_type to PlantUML stereotype badges
# ============================================================

DEFINITION_STEREOTYPES = {
    "part":       "part def",
    "item":       "item def",
    "attribute":  "attribute def",
    "port":       "port def",
    "action":     "action def",
    "state":      "state def",
    "constraint": "constraint def",
    "requirement": "requirement def",
    "use_case":   "use case def",
    "case":       "case def",
    "analysis_case": "analysis case def",
    "verification_case": "verification case def",
    "connection": "connection def",
    "flow":       "flow def",
    "allocation": "allocation def",
    "metadata":   "metadata def",
    "view":       "view def",
    "viewpoint":  "viewpoint def",
    "concern":    "concern def",
    "interface":  "interface def",
    "enumeration": "enumeration def",
}

USAGE_STEREOTYPES = {
    "part":       "part",
    "item":       "item",
    "attribute":  "attribute",
    "port":       "port",
    "action":     "action",
    "state":      "state",
    "constraint": "constraint",
    "requirement": "requirement",
    "use_case":   "use case",
    "case":       "case",
    "analysis_case": "analysis case",
    "verification_case": "verification case",
    "connection": "connection",
    "flow":       "flow",
    "allocation": "allocation",
    "metadata":   "metadata",
    "view":       "view",
    "viewpoint":  "viewpoint",
    "concern":    "concern",
    "interface":  "interface",
    "enumeration": "enumeration",
}

# Color scheme for stereotypes (letter, color)
#
# The default palette predates any accessibility pass and pairs lime
# green (#32CD32) against red (#E74C3C) — indistinguishable under
# protanopia/deuteranopia.  ``set_stereotype_palette("okabe-ito")``
# switches every view to the Okabe-Ito colorblind-safe palette (the
# de-facto standard from Okabe & Ito 2008); ``"default"`` restores the
# original.  ``style="bw"`` (the default for all views) renders no
# colors at all and is unaffected.
STEREOTYPE_COLORS = {
    "part":       ("P", "#32CD32"),
    "item":       ("I", "#32CD32"),
    "attribute":  ("A", "#32CD32"),
    "port":       ("P", "#4169E1"),
    "action":     ("A", "#F39C12"),
    "state":      ("S", "#9B59B6"),
    "constraint": ("C", "#E67E22"),
    "requirement": ("R", "#E74C3C"),
    "use_case":   ("UC", "#16A085"),
    "case":       ("C", "#16A085"),
    "analysis_case": ("AC", "#16A085"),
    "verification_case": ("VC", "#16A085"),
    "connection": ("C", "#3498DB"),
    "flow":       ("F", "#27AE60"),
    "allocation": ("A", "#9B59B6"),
    "metadata":   ("M", "#95A5A6"),
    "view":       ("V", "#8E44AD"),
    "viewpoint":  ("VP", "#8E44AD"),
    "concern":    ("CN", "#7F8C8D"),
    "interface":  ("IF", "#3498DB"),
    "enumeration": ("E", "#F1C40F"),
}

# Okabe-Ito colorblind-safe palette (Okabe & Ito 2008): the eight
# colors below stay distinguishable under protanopia, deuteranopia and
# tritanopia.  Hue families follow the default palette where they can
# (blue ports, orange actions) so switching does not scramble mental
# maps; collisions are resolved in favour of kinds that co-occur in
# the same views (parts/flows in iv, actions/flows in afv).
STEREOTYPE_COLORS_OKABEITO = {
    "part":       ("P", "#009E73"),   # bluish green
    "item":       ("I", "#009E73"),
    "attribute":  ("A", "#009E73"),
    "port":       ("P", "#0072B2"),   # blue
    "action":     ("A", "#E69F00"),   # orange
    "state":      ("S", "#CC79A7"),   # reddish purple
    "constraint": ("C", "#56B4E9"),   # sky blue
    "requirement": ("R", "#D55E00"),  # vermillion
    "use_case":   ("UC", "#F0E442"),  # yellow
    "case":       ("C", "#F0E442"),
    "analysis_case": ("AC", "#F0E442"),
    "verification_case": ("VC", "#F0E442"),
    "connection": ("C", "#56B4E9"),   # sky blue
    "flow":       ("F", "#0072B2"),   # blue (parts keep bluish green)
    "allocation": ("A", "#CC79A7"),
    "metadata":   ("M", "#95A5A6"),   # gray
    "view":       ("V", "#CC79A7"),
    "viewpoint":  ("VP", "#CC79A7"),
    "concern":    ("CN", "#95A5A6"),  # gray
    "interface":  ("IF", "#56B4E9"),
    "enumeration": ("E", "#F0E442"),  # yellow
}

_ACTIVE_PALETTE = "default"


def set_stereotype_palette(name: str) -> None:
    """Select the stereotype color palette used by ``style="color"``.

    ``"default"`` — the historical palette; ``"okabe-ito"`` — the
    colorblind-safe palette.  Unknown names raise ValueError.  The
    default for every view remains ``style="bw"``, which renders no
    colors regardless of this setting.
    """
    global _ACTIVE_PALETTE
    if name not in ("default", "okabe-ito"):
        raise ValueError(
            f"unknown palette {name!r}; expected 'default' or "
            "'okabe-ito'")
    _ACTIVE_PALETTE = name


def _stereotype_colors() -> dict:
    """The active stereotype color table (see set_stereotype_palette)."""
    if _ACTIVE_PALETTE == "okabe-ito":
        return STEREOTYPE_COLORS_OKABEITO
    return STEREOTYPE_COLORS


def _get_typedby_name(element):
    """Extract the typed-by type name from an element's grammar structure."""
    g = getattr(element, 'grammar', None)
    if g is None:
        return None

    # Navigate: PartUsage -> usage -> declaration -> declaration -> specialization
    # -> specializations[0] -> relationship -> typing -> relationships[0]
    # -> relationship -> type -> type -> names
    try:
        usage = getattr(g, 'usage', None)
        if usage is None:
            return None
        decl = getattr(usage, 'declaration', None)
        if decl is None:
            return None
        inner_decl = getattr(decl, 'declaration', None)
        if inner_decl is None:
            return None
        spec_part = getattr(inner_decl, 'specialization', None)
        if spec_part is None:
            return None
        specs = getattr(spec_part, 'specializations', None)
        if not specs:
            return None

        for spec in specs:
            rel = getattr(spec, 'relationship', None)
            if rel is None:
                continue
            typing = getattr(rel, 'typing', None)
            if typing is None:
                continue
            relationships = getattr(typing, 'relationships', None)
            if not relationships:
                continue

            for r in relationships:
                rr = getattr(r, 'relationship', None)
                if rr is None:
                    continue
                ft = getattr(rr, 'type', None)
                if ft is None:
                    continue
                qn = getattr(ft, 'type', None)
                if qn is None:
                    continue
                names = getattr(qn, 'names', None)
                if names:
                    return names[0]
    except (AttributeError, IndexError):
        pass

    return None


def _get_specializes_names(element):
    """Extract specialization (superclass) names from a definition's grammar."""
    g = getattr(element, 'grammar', None)
    if g is None:
        return []

    names = []
    try:
        # For definitions: get_definition -> definition -> declaration -> subclassificationpart
        defn_method = getattr(g, 'get_definition', None)
        if defn_method is None:
            return []

        d = defn_method() if callable(defn_method) else defn_method
        if not isinstance(d, dict):
            return []

        definition = d.get('definition') or d.get('usage')
        if not definition:
            return []

        declaration = definition.get('declaration')
        if not declaration:
            return []

        # The subclassificationpart is directly under declaration for definitions
        subclass_part = declaration.get('subclassificationpart')
        if not subclass_part:
            return []

        owned_rel = subclass_part.get('ownedRelationship', [])
        for rel in owned_rel:
            if rel.get('name') == 'OwnedSubclassification':
                sc = rel.get('superclassifier')
                if sc and sc.get('names'):
                    names.extend(sc['names'])
    except (AttributeError, TypeError):
        pass

    return names


def _get_redefines_names(element):
    """Extract redefinition names from an element's grammar."""
    g = getattr(element, 'grammar', None)
    if g is None:
        return []

    names = []
    try:
        usage = getattr(g, 'usage', None)
        if usage is None:
            return []
        decl = getattr(usage, 'declaration', None)
        if decl is None:
            return []
        inner_decl = getattr(decl, 'declaration', None)
        if inner_decl is None:
            return []
        spec_part = getattr(inner_decl, 'specialization', None)
        if spec_part is None:
            return []
        specs = getattr(spec_part, 'specializations', None)
        if not specs:
            return []

        for spec in specs:
            rel = getattr(spec, 'relationship', None)
            if rel is None:
                continue
            # Check for Redefinitions
            if hasattr(rel, 'children'):
                for child in rel.children:
                    if hasattr(child, 'redefinedFeature'):
                        rf = child.redefinedFeature
                        if hasattr(rf, 'names'):
                            names.extend(rf.names)
    except (AttributeError, IndexError):
        pass

    return names


def _get_multiplicity_label(element):
    """Extract multiplicity string like '[4]' from an element's grammar."""
    grammar = getattr(element, 'grammar', None)
    if not grammar:
        return ''
    try:
        usage = getattr(grammar, 'usage', None)
        if usage is None:
            return ''
        decl = getattr(usage, 'declaration', None)
        if decl is None:
            return ''
        inner_decl = getattr(decl, 'declaration', None)
        if inner_decl is None:
            return ''
        spec = getattr(inner_decl, 'specialization', None)
        if spec is None:
            return ''
        mp = getattr(spec, 'multiplicity', None)
        if mp is None:
            return ''
        return mp.dump()
    except AttributeError:
        return ''


def _get_stereotype(element, style="bw"):
    """Get the stereotype string for an element."""
    sysml_type = getattr(element, 'sysml_type', None)
    if sysml_type is None:
        return ""

    is_def = getattr(element, 'is_definition', False)
    stereotype_map = DEFINITION_STEREOTYPES if is_def else USAGE_STEREOTYPES
    label = stereotype_map.get(sysml_type, sysml_type)

    # Check for portionKind and individual in the grammar prefix
    prefix = _get_grammar_prefix(element)
    if prefix is not None:
        parts = []
        if getattr(prefix, 'isIndividual', None):
            parts.append("individual")
        pk = getattr(prefix, 'portionKind', None)
        if pk is not None:
            pk_kind = getattr(pk, 'kind', None)
            if pk_kind:
                parts.append(pk_kind)
        if parts:
            label = " ".join(parts) + " " + label

    if style == "bw":
        return f"<<{label}>>"

    color_info = _stereotype_colors().get(sysml_type, ("T", "#56B4E9"))
    letter, color = color_info

    return f"<<({letter},{color}) {label}>>"


def _get_grammar_prefix(element):
    """Navigate element.grammar to find the OccurrenceUsagePrefix."""
    grammar = getattr(element, 'grammar', None)
    if grammar is None:
        return None
    return getattr(grammar, 'prefix', None)


def _get_element_name(element):
    """Get a safe PlantUML name for an element."""
    name = getattr(element, 'name', None)

    # If no declared name, check for redefinition target
    if name is None or len(name) > 30:  # UUID heuristic
        redefines = _get_redefines_names(element)
        if redefines:
            return f":>> {redefines[0]}"

    if name is None:
        return "unnamed"

    # Escape quotes and special chars
    name = name.replace('"', "''").replace("\n", "\\n")
    return name


def _get_element_id(element, id_map):
    """Get or create a unique PlantUML alias for an element."""
    elem_id = id(element)
    if elem_id not in id_map:
        alias = f"E{len(id_map) + 1}"
        id_map[elem_id] = alias
    return id_map[elem_id]


def _arrow_to_rel_type(arrow):
    """Map a PlantUML arrow string back to a relationship type name."""
    for rel_type, pattern in ARROW_STYLES.items():
        if pattern in arrow or arrow in pattern:
            return rel_type
    return None


def _extract_flow_endpoints(flow_element):
    """Extract (from_names, to_names) from a flow element's grammar.

    Navigates the FlowConnectionDeclaration structure to recover
    the source and target qualified name references.

    Returns:
        (from_names, to_names) where each is a list of name strings
        (e.g. ["actionName", "portName"]) or None if not available.
    """
    g = getattr(flow_element, 'grammar', None)
    if g is None:
        return None, None

    declaration = getattr(g, 'declaration', None)
    if declaration is None:
        return None, None

    children = getattr(declaration, 'children', None)
    if not children or len(children) < 3:
        return None, None

    from_names = None
    to_names = None

    for end_idx, result in [(1, 'from'), (2, 'to')]:
        end_member = children[end_idx]
        if end_member is None:
            continue
        if not hasattr(end_member, 'children'):
            continue

        flow_end = end_member.children
        if flow_end is None:
            continue
        if not hasattr(flow_end, 'children'):
            continue

        # FlowEnd children (v0.68+): FlowEndSubsetting carries the base
        # reference (``s``); FlowFeatureMember -> FlowFeature ->
        # FlowRedefinition -> redefinedFeature carries chained segments
        # (``output``).  Combine into the full feature path so flows
        # resolve port-to-port (``s.output``) rather than collapsing to
        # the owning part (``s``).
        names = []
        for child in flow_end.children:
            child_class = child.__class__.__name__
            if child_class == 'FlowEndSubsetting':
                ref = getattr(child, 'referencedFeature', None)
                ref_names = getattr(ref, 'names', None) if ref is not None else None
                if not ref_names and hasattr(child, 'children') \
                        and hasattr(child.children, 'names'):
                    ref_names = child.children.names
                if ref_names:
                    names.extend(ref_names)
            elif child_class == 'FlowFeatureMember':
                ff = getattr(child, 'children', None)
                if ff is None:
                    continue
                # Grammar classes may hold a single child object rather
                # than a list — normalize before iterating.
                if not isinstance(ff, (list, tuple)):
                    ff = [ff]
                for item in ff:
                    if item.__class__.__name__ != 'FlowFeature':
                        if hasattr(item, 'children') and hasattr(item.children, 'names'):
                            names.extend(item.children.names)
                        continue
                    subs = getattr(item, 'children', None)
                    if subs is not None and not isinstance(subs, (list, tuple)):
                        subs = [subs]
                    for sub in (subs or []):
                        if sub.__class__.__name__ == 'FlowRedefinition':
                            # FlowRedefinition carries the chained name as
                            # its child QualifiedName (redefinedFeature is
                            # not populated on the grammar object).
                            rd = getattr(sub, 'redefinedFeature', None)
                            rd_names = getattr(rd, 'names', None) if rd is not None else None
                            if not rd_names:
                                sub_child = getattr(sub, 'children', None)
                                rd_names = getattr(sub_child, 'names', None) \
                                    if sub_child is not None else None
                            if rd_names:
                                names.extend(rd_names)
            elif hasattr(child, 'children') and hasattr(child.children, 'names'):
                names.extend(child.children.names)

        if names:
            if result == 'from':
                from_names = names
            else:
                to_names = names

    return from_names, to_names


def _find_element_by_qualified_name(model, names):
    """Resolve a qualified name (e.g. ['a', 'q']) to a model element.

    First tries dot-separated model.find(), then falls back to
    searching by individual segments (action name -> child feature name).
    """
    if not names:
        return None

    # Try full dot-separated name first
    dot_name = '.'.join(names)
    found = model.find(dot_name)
    if found:
        return found[0] if isinstance(found, list) else found

    # Try segment by segment: model -> action -> feature
    for i in range(len(names), 0, -1):
        segment = '.'.join(names[:i])
        found = model.find(segment)
        if found:
            elem = found[0] if isinstance(found, list) else found
            # Walk remaining segments
            remaining = names[i:]
            current = elem
            for part in remaining:
                child = getattr(current, 'children', None)
                if child:
                    match = None
                    for c in child:
                        if getattr(c, 'name', None) == part:
                            match = c
                            break
                    if match:
                        current = match
                    else:
                        break
                else:
                    break
            return current

    return None


def _expand_with_connected_flows(model, included_ids, show_external=False):
    """Expand an inclusion set to include flows connected to selected elements.

    Scans all flow connections in the model (both Usage-level and grammar-level).
    For each flow connected to an already-included element (via its from/to
    endpoints or parent container), adds the flow and its endpoint elements
    to the set.

    Args:
        model: A sysmlpy Model instance
        included_ids: Mutable set of element IDs to expand
        show_external: If True, include all referenced endpoints even
                      if they are outside the original selection
    """
    # Get all flow connections (Usage and grammar level)
    flow_connections = _extract_flow_connections(model)

    for from_names, to_names, flow_name, is_grammar_obj in flow_connections:
        referenced_elements = []

        for names in [from_names, to_names]:
            if not names:
                continue
            elem = _find_element_by_qualified_name(model, names)
            if elem:
                referenced_elements.append(elem)

        # Check if any referenced element is in the inclusion set
        connected = False
        all_endpoint_elements = []

        for ref in referenced_elements:
            all_endpoint_elements.append(ref)
            if id(ref) in included_ids:
                connected = True
            # Also check parent of resolved element
            elem_parent = getattr(ref, 'parent', None)
            if elem_parent:
                all_endpoint_elements.append(elem_parent)
                if id(elem_parent) in included_ids:
                    connected = True

        if connected:
            if show_external:
                for ref in all_endpoint_elements:
                    included_ids.add(id(ref))


# ============================================================
# Diagram Frame Helpers
# ============================================================

RENDERING_KINDS = {
    "as_general_view": "gv",
    "as_interconnection_diagram": "iv",
    "as_interconnection_view": "iv",
    "as_action_flow_view": "av",
    "as_state_transition_view": "stv",
    "as_sequence_view": "sv",
    "as_browser_view": "bv",
    "as_tabular_view": "grv",
    "as_data_value_tabular_view": "grv",
    "as_relationship_matrix_view": "grv",
    "as_package_view": "gv",
    "as_case_view": "gv",
    "as_tree_diagram": "gv",
    "as_element_table": "grv",
    "as_textual_notation": "gv",
}


def _get_element_type_name(element):
    """Get the SysML type name for the diagram header, e.g. 'package', 'part def'."""
    if element is None:
        return "model"
    sysml_type = getattr(element, 'sysml_type', None)
    if sysml_type:
        is_def = getattr(element, 'is_definition', False)
        return f"{sysml_type} def" if is_def else sysml_type
    return type(element).__name__.lower()


def _make_diagram_header(rendering_kind, model, focus=None, elements=None, label=None):
    """Build a spec-compliant diagram header string.

    Format: ``renderingKind [ElementType] Name [Label]``

    Args:
        rendering_kind: Short name e.g. 'gv', 'iv', 'av'
        model: The sysmlpy Model instance
        focus: Optional focused element
        elements: Optional list of specific elements
        label: Optional human-readable label

    Returns:
        str: Header string ready for ``title`` or ``frame``
    """
    anchor = focus if focus is not None else (elements[0] if elements else model)
    elem_type = _get_element_type_name(anchor)
    name = getattr(anchor, 'name', getattr(model, 'name', None)) or ""
    parts = [rendering_kind]
    if elem_type:
        parts.append(f"[{elem_type}]")
    if name:
        parts.append(name)
    if label:
        parts.append(f"[{label}]")
    return " ".join(parts)


class PlantUMLGenerator:
    """
    Generates PlantUML text from a sysmlpy Model.

    Usage:
        # Full model
        model = sysmlpy.loads('package P { part def Car { part engine; } }')
        puml = PlantUMLGenerator(model).generate()

        # Focus on a specific element and its subtree
        car = model.find('Car')[0]
        puml = PlantUMLGenerator(model, focus=car).generate()

        # Select specific elements
        wheel = model.find('Wheel')[0]
        axle = model.find('Axle')[0]
        puml = PlantUMLGenerator(model, elements=[wheel, axle]).generate()
    """

    def __init__(self, model, style="bw", direction="TB", include_legend=False,
                 focus=None, elements=None, max_depth=None, show_external=False,
                 custom_style=None):
        """
        Args:
            model: A sysmlpy Model instance
            style: "bw" for black-and-white (default, journal-ready),
                   "color" for colored stereotypes
            direction: "TB" for top-to-bottom, "LR" for left-to-right
            include_legend: Whether to include a relationship legend
            focus: A single element to focus on (renders it and its subtree)
            elements: A list of specific elements to include (ignores focus if set)
            max_depth: Maximum depth to traverse from focus element (None = unlimited)
            show_external: If True, show relationships to elements outside the selection
                          as dashed/ghosted lines. If False, hide them entirely.
            custom_style: Optional list of PlantUML style lines to append to the
                         default style. Useful for custom formatting while keeping
                         the base style consistent.
        """
        self.model = model
        self.style = style
        self.direction = direction
        self.include_legend = include_legend
        self.focus = focus
        self.elements_filter = elements
        self.max_depth = max_depth
        self.show_external = show_external
        self.custom_style = custom_style or []
        self.id_map = {}
        self.elements = []
        self.relationships = []
        self._visited = set()
        self._included_ids = set()  # Elements that are in the selection

    def _build_inclusion_set(self):
        """Build the set of element IDs that should be included in the diagram."""
        if self.elements_filter is not None:
            # Explicit element list
            for elem in self.elements_filter:
                self._included_ids.add(id(elem))
        elif self.focus is not None:
            # Focus on a single element and its subtree
            self._collect_subtree(self.focus, depth=0)
        else:
            # Include everything
            self._included_ids.add(id(self.model))
            for child in self.model.children:
                self._collect_subtree(child, depth=0)

    def _collect_subtree(self, element, depth):
        """Recursively collect all elements in a subtree up to max_depth."""
        elem_id = id(element)
        if elem_id in self._included_ids:
            return
        self._included_ids.add(elem_id)

        if self.max_depth is not None and depth >= self.max_depth:
            return

        children = getattr(element, 'children', None)
        if children:
            for child in children:
                self._collect_subtree(child, depth + 1)

    def _is_included(self, element):
        """Check if an element is in the inclusion set."""
        return id(element) in self._included_ids

    def generate(self):
        """Generate complete PlantUML text."""
        lines = []

        # Build inclusion set
        self._build_inclusion_set()

        # Header
        lines.append("@startuml")
        lines.append("")

        # Style block
        lines.extend(self._generate_style())
        lines.append("")

        # Direction
        if self.direction == "LR":
            lines.append("left to right direction")
        else:
            lines.append("top to bottom direction")
        lines.append("")

        # Title — spec-compliant header
        header = _make_diagram_header(
            "gv", self.model, focus=self.focus, elements=self.elements_filter
        )
        lines.append(f'title {header}')
        lines.append("")

        # Hide default circle on state diagrams
        lines.append("hide circle")
        lines.append("")

        # Traverse model and collect elements + relationships
        self._traverse(self.model)

        # Output elements
        for alias, name, stereotype, elem, is_included in self.elements:
            lines.append(self._render_element(alias, name, stereotype, elem, is_included))

        lines.append("")

        # Output relationships
        for src, arrow, dst, label, is_external in self.relationships:
            if is_external and not self.show_external:
                continue

            # Style external relationships differently
            if is_external:
                arrow = f"-[dotted,thickness=1,#999999]{arrow.lstrip('-')}"

            if label:
                lines.append(f'{src} {arrow} {dst} : {label}')
            else:
                lines.append(f'{src} {arrow} {dst}')

        lines.append("")

        # Legend
        if self.include_legend:
            lines.extend(self._generate_legend())
            lines.append("")

        lines.append("@enduml")
        return "\n".join(lines)

    def _generate_style(self):
        """Generate CSS style block."""
        if self.style == "bw":
            lines = [
                "skinparam monochrome true",
                "skinparam wrapWidth 300",
                "skinparam defaultFontSize 12",
                "skinparam defaultFontName Helvetica",
                "",
                "' Definitions: sharp corners, plain background",
                "skinparam rectangle<<part def>> {",
                "    RoundCorner 0",
                "    BackgroundColor white",
                "    StereotypeFontSize 11",
                "}",
                "skinparam rectangle<<item def>> {",
                "    RoundCorner 0",
                "    BackgroundColor white",
                "}",
                "skinparam rectangle<<attribute def>> {",
                "    RoundCorner 0",
                "    BackgroundColor white",
                "}",
                "skinparam rectangle<<port def>> {",
                "    RoundCorner 0",
                "    BackgroundColor white",
                "}",
                "skinparam rectangle<<action def>> {",
                "    RoundCorner 0",
                "    BackgroundColor white",
                "}",
                "skinparam rectangle<<state def>> {",
                "    RoundCorner 0",
                "    BackgroundColor white",
                "}",
                "skinparam rectangle<<requirement def>> {",
                "    RoundCorner 0",
                "    BackgroundColor white",
                "}",
                "skinparam rectangle<<view def>> {",
                "    RoundCorner 0",
                "    BackgroundColor white",
                "}",
                "skinparam rectangle<<viewpoint def>> {",
                "    RoundCorner 0",
                "    BackgroundColor white",
                "}",
                "skinparam rectangle<<enumeration def>> {",
                "    RoundCorner 0",
                "    BackgroundColor white",
                "}",
                "",
                "' Usages: rounded corners, plain background",
                "skinparam rectangle<<part>> {",
                "    RoundCorner 15",
                "    BackgroundColor white",
                "}",
                "skinparam rectangle<<item>> {",
                "    RoundCorner 15",
                "    BackgroundColor white",
                "}",
                "skinparam rectangle<<attribute>> {",
                "    RoundCorner 15",
                "    BackgroundColor white",
                "}",
                "skinparam rectangle<<port>> {",
                "    RoundCorner 15",
                "    BackgroundColor white",
                "}",
                "skinparam rectangle<<action>> {",
                "    RoundCorner 15",
                "    BackgroundColor white",
                "}",
                "skinparam rectangle<<state>> {",
                "    RoundCorner 15",
                "    BackgroundColor white",
                "}",
                "skinparam rectangle<<requirement>> {",
                "    RoundCorner 15",
                "    BackgroundColor white",
                "}",
                "skinparam rectangle<<view>> {",
                "    RoundCorner 15",
                "    BackgroundColor white",
                "}",
                "skinparam rectangle<<viewpoint>> {",
                "    RoundCorner 15",
                "    BackgroundColor white",
                "}",
                "skinparam rectangle<<enumeration>> {",
                "    RoundCorner 15",
                "    BackgroundColor white",
                "}",
                "",
                "' Views as folders",
                "skinparam folder<<view def>> {",
                "    BackgroundColor white",
                "}",
                "skinparam folder<<view>> {",
                "    BackgroundColor white",
                "}",
            ]
        else:
            lines = [
                "<style>",
                "root {",
                "    BackGroundColor white",
                "    FontName Helvetica",
                "    FontSize 13",
                "}",
                "rectangle {",
                "    LineColor #444444",
                "    LineThickness 1.5",
                "    BackgroundColor white",
                "    Padding 10",
                "}",
                "arrow {",
                "    LineColor #555555",
                "    LineThickness 1.5",
                "    FontSize 11",
                "}",
                "</style>",
                "",
                "skinparam wrapWidth 400",
                "",
                "skinparam rectangle<<part def>> {",
                "    RoundCorner 0",
                "}",
                "skinparam rectangle<<item def>> {",
                "    RoundCorner 0",
                "}",
                "skinparam rectangle<<attribute def>> {",
                "    RoundCorner 0",
                "}",
                "skinparam rectangle<<port def>> {",
                "    RoundCorner 0",
                "}",
                "skinparam rectangle<<action def>> {",
                "    RoundCorner 0",
                "}",
                "skinparam rectangle<<state def>> {",
                "    RoundCorner 0",
                "}",
                "skinparam rectangle<<requirement def>> {",
                "    RoundCorner 0",
                "}",
                "skinparam rectangle<<part>> {",
                "    RoundCorner 15",
                "}",
                "skinparam rectangle<<item>> {",
                "    RoundCorner 15",
                "}",
                "skinparam rectangle<<attribute>> {",
                "    RoundCorner 15",
                "}",
                "skinparam rectangle<<port>> {",
                "    RoundCorner 15",
                "}",
                "skinparam rectangle<<action>> {",
                "    RoundCorner 15",
                "}",
                "skinparam rectangle<<state>> {",
                "    RoundCorner 15",
                "}",
                "skinparam rectangle<<requirement>> {",
                "    RoundCorner 15",
                "}",
                "skinparam folder<<view def>> {",
                "    BackgroundColor #F5E6FF",
                "    BorderColor #8E44AD",
                "}",
                "skinparam folder<<view>> {",
                "    BackgroundColor #F5E6FF",
                "    BorderColor #8E44AD",
                "}",
            ]

        # Append custom style overrides
        if self.custom_style:
            lines.append("")
            lines.extend(self.custom_style)

        return lines

    def _traverse(self, element, parent=None):
        """Recursively traverse the model tree, collecting elements and relationships."""
        elem_id = id(element)
        if elem_id in self._visited:
            return
        self._visited.add(elem_id)

        # Skip the root Model itself (start from its children)
        if isinstance(element, Model):
            for child in element.children:
                self._traverse(child, parent=None)
            return

        # Skip Package containers (we flatten the structure, don't render packages)
        if isinstance(element, Package):
            for child in element.children:
                self._traverse(child, parent=None)
            return

        # Check if this element is in the inclusion set
        is_included = self._is_included(element)

        # Register this element if included, or if show_external and it's referenced
        if is_included or self.show_external:
            alias = _get_element_id(element, self.id_map)
            name = _get_element_name(element)
            stereotype = _get_stereotype(element, style=self.style)
            self.elements.append((alias, name, stereotype, element, is_included))

        # Containment relationship (parent -> child)
        # Only add if parent is a renderable element (not Model or Package)
        if parent is not None and not isinstance(parent, (Model, Package)):
            parent_included = self._is_included(parent)
            # Only show containment if both parent and child are included
            if is_included and parent_included:
                parent_alias = _get_element_id(parent, self.id_map)
                arrow = ARROW_STYLES["composite"]
                self.relationships.append((parent_alias, arrow, alias, None, False))

        # Typing relationship (element -> typedby)
        # First try the typedby attribute, then extract from grammar
        typedby = getattr(element, 'typedby', None)
        if typedby is None:
            typedby_name = _get_typedby_name(element)
            if typedby_name:
                typedby = self.model.find(typedby_name)
                if typedby:
                    typedby = typedby[0] if isinstance(typedby, list) else typedby

        if typedby is not None:
            typedby_id = id(typedby)
            if typedby_id not in self._visited:
                self._traverse(typedby, parent=None)
            typedby_included = self._is_included(typedby)
            # Show typing if source is included; mark as external if target is not
            if is_included:
                typedby_alias = _get_element_id(typedby, self.id_map)
                arrow = ARROW_STYLES["typing"]
                is_external = not typedby_included
                self.relationships.append((alias, arrow, typedby_alias, "types", is_external))

        # Specialization relationship (definition -> superclass)
        if getattr(element, 'is_definition', False):
            specializes_names = _get_specializes_names(element)
            for super_name in specializes_names:
                super_elem = self.model.find(super_name)
                if super_elem:
                    super_elem = super_elem[0] if isinstance(super_elem, list) else super_elem
                    super_id = id(super_elem)
                    if super_id not in self._visited:
                        self._traverse(super_elem, parent=None)
                    super_included = self._is_included(super_elem)
                    if is_included:
                        super_alias = _get_element_id(super_elem, self.id_map)
                        arrow = ARROW_STYLES["specialization"]
                        is_external = not super_included
                        self.relationships.append((alias, arrow, super_alias, "specializes", is_external))

        # Redefinition relationship (usage -> redefined feature)
        redefines_names = _get_redefines_names(element)
        for redef_name in redefines_names:
            redef_elem = self.model.find(redef_name)
            if redef_elem:
                redef_elem = redef_elem[0] if isinstance(redef_elem, list) else redef_elem
                redef_id = id(redef_elem)
                if redef_id not in self._visited:
                    self._traverse(redef_elem, parent=None)
                redef_included = self._is_included(redef_elem)
                if is_included:
                    redef_alias = _get_element_id(redef_elem, self.id_map)
                    arrow = ARROW_STYLES["redefinition"]
                    is_external = not redef_included
                    self.relationships.append((alias, arrow, redef_alias, "redefines", is_external))

        # Traverse children
        children = getattr(element, 'children', None)
        if children:
            for child in children:
                self._traverse(child, parent=element)

    def _render_element(self, alias, name, stereotype, element, is_included=True):
        """Render a single element as PlantUML text."""
        sysml_type = getattr(element, 'sysml_type', '')

        if sysml_type == 'state':
            keyword = "rectangle"  # avoid PlantUML state-shape constraints
        elif sysml_type == 'view':
            keyword = "folder"
        elif sysml_type == 'action':
            keyword = "rectangle"
        else:
            keyword = "rectangle"

        safe_name = name.replace('"', "''")

        if stereotype:
            return f'{keyword} "{safe_name}" as {alias} {stereotype}'
        else:
            return f'{keyword} "{safe_name}" as {alias}'

    def _generate_legend(self):
        """Generate a relationship legend table."""
        legend = [
            "legend right",
            "  <b>SysML v2 Relationship Legend</b>",
            "  Relationship: Notation",
        ]

        legend_items = [
            ("Feature Typing", "--:|>", "types"),
            ("Specialization", "--|>", "specializes"),
            ("Redefinition", "--||>", "redefines"),
            ("Composite (owns)", "*--", "owns"),
            ("Shared", "o--", "shares"),
            ("Binding", "-[thickness=4]-", "binds"),
            ("Connector", "-[thickness=2]->", "connects"),
            ("Flow", "-->", "flows"),
            ("Dependency", "..>>", "depends"),
        ]

        for rel_name, notation, _ in legend_items:
            legend.append(f"  {rel_name}: {notation}")

        legend.append("endlegend")
        return legend


def to_plantuml(model, style="bw", direction="TB", include_legend=False,
                focus=None, elements=None, max_depth=None, show_external=False,
                custom_style=None):
    """
    Convenience function to generate PlantUML text from a sysmlpy Model.

    Args:
        model: A sysmlpy Model instance (from sysmlpy.loads())
        style: "bw" for black-and-white (default, journal-ready),
               "color" for colored stereotypes
        direction: "TB" or "LR"
        include_legend: bool
        focus: A single element to focus on (renders it and its subtree)
        elements: A list of specific elements to include
        max_depth: Maximum depth to traverse from focus (None = unlimited)
        show_external: If True, show relationships to elements outside selection
        custom_style: Optional list of PlantUML style lines to append

    Returns:
        str: PlantUML text
    """
    gen = PlantUMLGenerator(model, style=style, direction=direction,
                            include_legend=include_legend, focus=focus,
                            elements=elements, max_depth=max_depth,
                            show_external=show_external,
                            custom_style=custom_style)
    return gen.generate()


# ============================================================
# View Rendering Convenience Functions
# Per SysML v2 View semantics, views can be rendered in multiple ways.
# These functions provide ready-made configurations for common patterns.
# ============================================================


def as_graphical_rendering(model, focus=None, style="bw", direction="TB",
                           include_legend=False, max_depth=None,
                           show_external=False, custom_style=None):
    """Generate a graphical rendering of a model or view.

    This is the default rendering: elements as shapes (rectangles, folders)
    with relationship arrows (typing, specialization, containment, etc.).

    Corresponds to SysML v2 ``GraphicalRendering``.

    Args:
        model: A sysmlpy Model instance
        focus: Optional element to focus on (renders subtree)
        style: "bw" (default) or "color"
        direction: "TB" or "LR"
        include_legend: Whether to include relationship legend
        max_depth: Maximum depth to traverse from focus
        show_external: Show relationships to elements outside selection
        custom_style: Optional PlantUML style lines to append

    Returns:
        str: PlantUML text
    """
    gen = PlantUMLGenerator(model, style=style, direction=direction,
                            include_legend=include_legend, focus=focus,
                            max_depth=max_depth, show_external=show_external,
                            custom_style=custom_style)
    return gen.generate()


def as_interconnection_diagram(model, focus=None, elements=None, style="bw",
                                direction="TB", include_legend=False,
                                max_depth=None, show_external=False,
                                auto_include_connections=True,
                                custom_style=None):
    """Generate an Interconnection View (IV) diagram.

    Corresponds to SysML v2 ``InterconnectionView``. Presents exposed
    features as nodes, nested features as nested nodes, and connections
    between features as edges. Nested nodes may present boundary features
    (e.g., ports, parameters).

    When ``auto_include_connections=True`` (default), selecting features
    via ``focus`` or ``elements`` automatically discovers and includes all
    binding, connector, and flow connections involving those features.

    Args:
        model: A sysmlpy Model instance
        focus: Optional element to focus on (renders subtree)
        elements: Optional list of specific elements to include
        style: "bw" (default) or "color"
        direction: "TB" or "LR"
        include_legend: Whether to include relationship legend
        max_depth: Maximum depth to traverse from focus
        show_external: Show relationships to elements outside selection
        auto_include_connections: Auto-discover connections for selected
                                  features (bindings, connectors, flows)
        custom_style: Optional PlantUML style lines to append

    Returns:
        str: PlantUML text
    """
    lines = []
    lines.append("@startuml")
    lines.append("")

    # Style
    if style == "bw":
        lines.extend([
            "skinparam monochrome true",
            "skinparam wrapWidth 300",
            "skinparam defaultFontSize 12",
            "skinparam defaultFontName Helvetica",
            "",
            "skinparam rectangle<<part def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<part>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<port def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<port>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<interface def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<interface>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<item def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<item>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<attribute def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<attribute>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<connection def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<connection>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<flow def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<flow>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
        ])
    else:
        lines.extend([
            "<style>",
            "root {",
            "    BackGroundColor white",
            "    FontName Helvetica",
            "    FontSize 13",
            "}",
            "rectangle {",
            "    LineColor #444444",
            "    LineThickness 1.5",
            "    BackgroundColor white",
            "    Padding 10",
            "}",
            "</style>",
            "",
            "skinparam wrapWidth 400",
            "",
            "skinparam rectangle<<part def>> {",
            "    RoundCorner 0",
            "}",
            "skinparam rectangle<<part>> {",
            "    RoundCorner 15",
            "}",
            "skinparam rectangle<<port def>> {",
            "    RoundCorner 0",
            "}",
            "skinparam rectangle<<port>> {",
            "    RoundCorner 15",
            "}",
            "skinparam rectangle<<interface def>> {",
            "    RoundCorner 0",
            "}",
            "skinparam rectangle<<interface>> {",
            "    RoundCorner 15",
            "}",
            "skinparam rectangle<<item def>> {",
            "    RoundCorner 0",
            "}",
            "skinparam rectangle<<item>> {",
            "    RoundCorner 15",
            "}",
            "skinparam rectangle<<attribute>> {",
            "    RoundCorner 15",
            "}",
            "skinparam rectangle<<connection>> {",
            "    RoundCorner 15",
            "}",
            "skinparam rectangle<<flow>> {",
            "    RoundCorner 15",
            "}",
        ])

    if custom_style:
        lines.append("")
        lines.extend(custom_style)

    lines.append("")

    if direction == "LR":
        lines.append("left to right direction")
    else:
        lines.append("top to bottom direction")
    lines.append("")

    header = _make_diagram_header(
        "iv", model, focus=focus, elements=elements,
        label="Interconnection View"
    )
    lines.append(f'title {header}')
    lines.append("")
    lines.append("hide circle")
    lines.append("")

    # Build inclusion set
    gen = PlantUMLGenerator(model, style=style, focus=focus,
                            elements=elements, max_depth=max_depth,
                            include_legend=False,
                            show_external=show_external)
    gen._build_inclusion_set()

    # Auto-expand with connected flows (grammar-level scanning)
    if auto_include_connections:
        _expand_with_connected_flows(model, gen._included_ids,
                                     show_external=show_external)

    # Collect all flow connections for arrow rendering
    flow_connections = _extract_flow_connections(model)
    connector_connections = _extract_connections(model)

    # Traverse
    gen._traverse(gen.model)

    id_map = gen.id_map
    relationships = gen.relationships
    included_ids = gen._included_ids

    # Interconnection-relevant element types.  Flows and connections are
    # EDGES on an iv (official notation), not nodes — they are excluded
    # from element rendering and drawn from the extractions below.
    iv_types = {"part", "port", "interface", "item", "attribute",
                "allocation"}

    def _renders(element):
        st = getattr(element, 'sysml_type', '')
        return (id(element) in included_ids
                and st in iv_types
                and st not in ('flow', 'connection'))

    # Definitions typed by included usages are not drawn: the usage label
    # carries the type (``s : Sensor``, official iv notation) and the
    # definition's ports are inherited onto the usage as boundary boxes.
    consumed_def_ids = set()

    def _collect_consumed(element):
        if (_renders(element)
                and not getattr(element, 'is_definition', False)):
            d = _resolve_typed_def(model, _get_typedby_name(element))
            if d is not None and getattr(d, 'is_definition', False):
                consumed_def_ids.add(id(d))
        for child in getattr(element, 'children', None) or []:
            _collect_consumed(child)

    for child in getattr(model, 'children', None) or []:
        _collect_consumed(child)

    # Typed labels: usages show ``name : Type`` (typing is conveyed in
    # the label on an iv, not as a --:|> arrow).
    def _iv_label(element):
        return _typed_label(element, model)

    # Inherited ports: a usage exposes the ports of its typed definition
    # chain (definition + specializes ancestors) as boundary features.
    synth_ports = {}   # usage_id -> [(alias, label)]
    port_map = {}      # (owner_id, port_name) -> alias
    port_counter = [0]

    def _chain_port_defs(tb_name):
        """Yield port children along the typed definition chain."""
        seen_defs = set()
        while tb_name and tb_name not in seen_defs:
            seen_defs.add(tb_name)
            d = _resolve_typed_def(model, tb_name)
            if d is None:
                return
            for c in getattr(d, 'children', None) or []:
                if getattr(c, 'sysml_type', '') == 'port':
                    yield c
            tb_name = (_get_specializes_names(d) or [None])[0]

    def _collect_ports(element):
        """Register own + inherited ports for a rendered element.

        Own port children render through the normal enclosure walk
        (they are in ``ordered``), so only their alias registration in
        ``port_map`` happens here.  Inherited ports (from the typed
        definition chain) get synthetic aliases and appear in
        ``synth_ports`` for _emit to nest as boundary boxes.
        """
        owner_id = id(element)
        seen = set()
        own = [c for c in getattr(element, 'children', None) or []
               if getattr(c, 'sysml_type', '') == 'port']
        for p in own:
            nm = getattr(p, 'name', None)
            if nm is None or (owner_id, nm) in port_map:
                continue
            alias = id_map.get(id(p))
            if alias is None:
                continue
            port_map[(owner_id, nm)] = alias
            seen.add(nm)
        entries = []
        if not getattr(element, 'is_definition', False):
            for p in _chain_port_defs(_get_typedby_name(element)):
                nm = getattr(p, 'name', None)
                if nm is None or nm in seen or (owner_id, nm) in port_map:
                    continue
                port_counter[0] += 1
                alias = f"P{port_counter[0]}"
                port_map[(owner_id, nm)] = alias
                entries.append((alias, _iv_label(p), True))
                seen.add(nm)
        if entries:
            synth_ports[owner_id] = entries

    # DFS over the model in the generator's order, keeping the nearest
    # rendered ancestor for enclosure.
    ordered = []   # (element, parent_element_or_None) in DFS order

    def _dfs(element, parent_rendered):
        if id(element) in consumed_def_ids:
            return  # consumed definition: ports inherit onto usages
        renders = _renders(element)
        if renders:
            ordered.append((element, parent_rendered))
            _collect_ports(element)
        for child in getattr(element, 'children', None) or []:
            _dfs(child, element if renders else parent_rendered)

    for child in getattr(model, 'children', None) or []:
        _dfs(child, None)

    # Emit elements with containment as enclosure (nested rectangles),
    # not as *-- edges.
    children_of = {}
    for elem, parent in ordered:
        children_of.setdefault(id(parent) if parent is not None else None,
                               []).append(elem)

    def _emit(elem, depth):
        alias = id_map.get(id(elem))
        if alias is None:
            return
        label = _iv_label(elem)
        stereo = _get_stereotype(elem, style=style)
        own_kids = [k for k, par in ordered if par is elem]
        inh = synth_ports.get(id(elem), [])
        pad = "    " * depth
        if own_kids or inh:
            lines.append(f'{pad}rectangle "{label}" as {alias} {stereo} {{')
            for k in own_kids:
                _emit(k, depth + 1)
            for palias, plabel, _is_synth in inh:
                lines.append(f'{pad}    rectangle "{plabel}" as {palias} <<port>>')
            lines.append(pad + "}")
        else:
            lines.append(f'{pad}rectangle "{label}" as {alias} {stereo}')

    top_level = [e for e, par in ordered if par is None]
    for elem in top_level:
        _emit(elem, 0)

    lines.append("")

    # Interconnection edges only: connections and flows.  Containment is
    # conveyed by enclosure above; typing by the ``name : Type`` labels.
    connect_arrows = {ARROW_STYLES["binding"], ARROW_STYLES["connector"],
                      ARROW_STYLES["connector_directed"],
                      ARROW_STYLES["succession_flow"],
                      ARROW_STYLES["allocation"]}
    for src, arrow, dst, label, is_external in relationships:
        if arrow not in connect_arrows:
            continue
        if is_external and not show_external:
            continue
        if is_external:
            arrow = f"-[dotted,thickness=1,#999999]{arrow.lstrip('-')}"
        if label:
            lines.append(f'{src} {arrow} {dst} : {label}')
        else:
            lines.append(f'{src} {arrow} {dst}')

    def _resolve_endpoint(names):
        """Resolve a feature path to a rendered alias.

        Walks segment by segment: ``['s', 'output']`` finds usage ``s``
        then its (own or inherited) port ``output`` via port_map, giving
        port-to-port edges.  Falls back to whole-path element
        resolution for endpoints that are rendered elements themselves.
        """
        if not names:
            return None
        base = _find_element_by_qualified_name(model, names[:1])
        if base is None:
            elem = _find_element_by_qualified_name(model, names)
            if elem is None:
                return None
            return id_map.get(id(elem))
        cur = base
        for seg in names[1:]:
            nxt = None
            for c in getattr(cur, 'children', None) or []:
                if getattr(c, 'name', None) == seg:
                    nxt = c
                    break
            if nxt is not None:
                cur = nxt
                continue
            pa = port_map.get((id(cur), seg))
            if pa is not None:
                return pa
            break
        return id_map.get(id(cur))

    def _clean_label(name):
        if (name and len(name) == 36 and name.count("-") == 4
                and all(c in "0123456789abcdef"
                        for c in name.replace("-", ""))):
            return None
        return name

    # Flow edges (port-to-port when endpoints chain through ports)
    seen_edges = set()
    for from_names, to_names, flow_name, is_grammar_obj in flow_connections:
        fa = _resolve_endpoint(from_names)
        ta = _resolve_endpoint(to_names)
        if not fa or not ta or fa == ta:
            continue
        key = (fa, ta, flow_name)
        if key in seen_edges:
            continue
        seen_edges.add(key)
        fn = _clean_label(flow_name)
        lines.append(f'{fa} {ARROW_STYLES["flow"]} {ta} : {fn or "flow"}')

    # Connection edges (thick plain line per official notation)
    for from_names, to_names, conn_name in connector_connections:
        fa = _resolve_endpoint(from_names)
        ta = _resolve_endpoint(to_names)
        if not fa or not ta or fa == ta:
            continue
        key = (fa, ta, conn_name, "conn")
        if key in seen_edges:
            continue
        seen_edges.add(key)
        cn = _clean_label(conn_name)
        if cn:
            lines.append(f'{fa} {ARROW_STYLES["connector"]} {ta} : {cn}')
        else:
            lines.append(f'{fa} {ARROW_STYLES["connector"]} {ta}')

    lines.append("")

    if include_legend:
        lines.extend([
            "legend right",
            "  <b>Interconnection Legend</b>",
            "  Relationship: Notation",
            "  Binding (==): -[thickness=5]-",
            "  Connection: -[thickness=3]-",
            "  Flow Transfer: -->",
            "  Allocation: -[thickness=5,dotted]->",
            "endlegend",
        ])
        lines.append("")

    lines.append("@enduml")
    return "\n".join(lines)


def as_interconnection_view(model, focus=None, elements=None, style="bw",
                             direction="TB", include_legend=False,
                             max_depth=None, show_external=False,
                             auto_include_connections=True,
                             custom_style=None):
    """Alias for :func:`as_interconnection_diagram`.

    Corresponds to SysML v2 ``InterconnectionView`` (short name ``iv``).
    """
    return as_interconnection_diagram(
        model, focus=focus, elements=elements, style=style,
        direction=direction, include_legend=include_legend,
        max_depth=max_depth, show_external=show_external,
        auto_include_connections=auto_include_connections,
        custom_style=custom_style,
    )








def as_action_flow_view(model, focus=None, elements=None, style="bw", direction="TB",
                        include_legend=False, max_depth=None, show_external=False,
                        auto_include_flows=True, custom_style=None):
    """Generate an Action Flow View (AFV) diagram.

    Corresponds to SysML v2 ``ActionFlowView``, which specializes
    ``InterconnectionView``. Presents connections between actions,
    including:
    - Actions with nested actions
    - Parameters with direction
    - Flow connection usages (transfers from output to input)
    - Binding connections between parameters

    When ``auto_include_flows=True`` (default), selecting actions via
    ``focus`` or ``elements`` automatically discovers and includes all
    flow connections and binding connections that involve those actions.

    Args:
        model: A sysmlpy Model instance
        focus: Optional element to focus on (renders its subtree)
        elements: Optional list of specific elements to include
        style: "bw" (default) or "color"
        direction: "TB" or "LR"
        include_legend: Whether to include relationship legend
        max_depth: Maximum depth to traverse from focus
        show_external: Show relationships to elements outside selection
        auto_include_flows: Auto-discover flows connected to selected actions
        custom_style: Optional PlantUML style lines to append

    Returns:
        str: PlantUML text
    """
    lines = []
    lines.append("@startuml")
    lines.append("")

    # Style block
    if style == "bw":
        lines.extend([
            "skinparam monochrome true",
            "skinparam wrapWidth 300",
            "skinparam defaultFontSize 12",
            "skinparam defaultFontName Helvetica",
            "",
            "skinparam rectangle<<action def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<action>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<flow def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<flow>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<attribute def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<attribute>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<port def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<port>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<part def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<part>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "",
            "' Swim lane styling for actions",
            "skinparam rectangle<<action def>> {",
            "    StereotypeFontSize 11",
            "}",
            "skinparam rectangle<<action>> {",
            "    StereotypeFontSize 11",
            "}",
            "' Control nodes (initial/final/decision/merge/fork/join)",
            "skinparam circle<<initial>> {",
            "    BackgroundColor black",
            "    BorderColor black",
            "}",
            "skinparam circle<<final>> {",
            "    BackgroundColor white",
            "    BorderColor black",
            "}",
            "skinparam hexagon {",
            "    BackgroundColor white",
            "    BorderColor black",
            "}",
        ])
    else:
        lines.extend([
            "<style>",
            "root {",
            "    BackGroundColor white",
            "    FontName Helvetica",
            "    FontSize 13",
            "}",
            "rectangle {",
            "    LineColor #444444",
            "    LineThickness 1.5",
            "    BackgroundColor white",
            "    Padding 10",
            "}",
            "</style>",
            "",
            "skinparam wrapWidth 400",
            "",
            "skinparam rectangle<<action def>> {",
            "    RoundCorner 0",
            "}",
            "skinparam rectangle<<action>> {",
            "    RoundCorner 15",
            "}",
            "skinparam rectangle<<flow def>> {",
            "    RoundCorner 0",
            "}",
            "skinparam rectangle<<flow>> {",
            "    RoundCorner 15",
            "}",
            "skinparam rectangle<<attribute>> {",
            "    RoundCorner 15",
            "}",
            "skinparam rectangle<<port>> {",
            "    RoundCorner 15",
            "}",
            "skinparam rectangle<<part>> {",
            "    RoundCorner 15",
            "}",
        ])

    if custom_style:
        lines.append("")
        lines.extend(custom_style)

    lines.append("")

    if direction == "LR":
        lines.append("left to right direction")
    else:
        lines.append("top to bottom direction")
    lines.append("")

    header = _make_diagram_header(
        "av", model, focus=focus, label="Action Flow View"
    )
    lines.append(f'title {header}')
    lines.append("")
    lines.append("hide circle")
    lines.append("")

    # Build inclusion set
    gen = PlantUMLGenerator(model, style=style, focus=focus,
                            elements=elements, max_depth=max_depth,
                            include_legend=False,
                            show_external=show_external)
    gen._build_inclusion_set()

    # Auto-expand with connected flows
    if auto_include_flows:
        _expand_with_connected_flows(model, gen._included_ids,
                                     show_external=show_external)

    # Collect all flow connections for arrow rendering
    flow_connections = _extract_flow_connections(model)

    # Traverse the model
    gen._traverse(gen.model)

    id_map = gen.id_map
    elements_list = gen.elements
    relationships = gen.relationships

    # Filter for action-flow relevant element types
    afv_types = {"action", "flow", "attribute", "port", "part"}

    declared_aliases = set()
    for alias, name, stereotype, elem, is_included in elements_list:
        sysml_type = getattr(elem, 'sysml_type', '')
        if sysml_type in afv_types:
            keyword = "rectangle"
            if sysml_type == 'state':
                keyword = "rectangle"  # avoid PlantUML state-shape constraints
                stereotype = "<<state>>"
            elif sysml_type == 'view':
                keyword = "folder"
            lines.append(f'{keyword} "{name}" as {alias} {stereotype}')
            declared_aliases.add(alias)

    lines.append("")

    # Render containment and typing relationships. Skip edges whose
    # endpoints were not rendered (e.g. grammar-only ControlNode children
    # of actions — those surface as hexagon chain nodes below instead).
    for src, arrow, dst, label, is_external in relationships:
        if is_external and not show_external:
            continue
        if not is_external and (src not in declared_aliases
                                or dst not in declared_aliases):
            continue
        if is_external:
            arrow = f"-[dotted,thickness=1,#999999]{arrow.lstrip('-')}"
        if label:
            lines.append(f'{src} {arrow} {dst} : {label}')
        else:
            lines.append(f'{src} {arrow} {dst}')

    lines.append("")

    # Render flow connection arrows
    # Grammar-level flows won't have entries in the id_map, so we check
    # if their resolved source/target elements are in the inclusion set.
    for from_names, to_names, flow_name, is_grammar_obj in flow_connections:
        from_elem = _find_element_by_qualified_name(model, from_names) if from_names else None
        to_elem = _find_element_by_qualified_name(model, to_names) if to_names else None

        if from_elem is None or to_elem is None:
            continue

        from_id = id(from_elem)
        to_id = id(to_elem)

        # Only render if at least one endpoint is in the inclusion set
        # (or if auto_include_flows expanded the set to include both)
        from_included = from_id in gen._included_ids
        to_included = to_id in gen._included_ids
        if not (from_included or to_included):
            continue

        from_alias = id_map.get(from_id)
        to_alias = id_map.get(to_id)
        if from_alias and to_alias:
            # Anonymous flows carry UUID names from the visitor — they
            # are unnamed in the source and unlabeled in official
            # notation, so fall back to the neutral "flow" label.
            if (flow_name and len(flow_name) == 36
                    and flow_name.count("-") == 4
                    and all(c in "0123456789abcdef"
                            for c in flow_name.replace("-", ""))):
                flow_name = None
            label_text = flow_name if flow_name else "flow"
            lines.append(f'{from_alias} {ARROW_STYLES["flow"]} {to_alias} : {label_text}')

    lines.append("")

    # Render control-flow chains: initial node, decision/merge/fork/join
    # nodes, final (done/terminate) targets, and their succession edges
    # (dotted ..> per the official successions notation).
    control_chains = _extract_control_chains(model)
    if control_chains:
        _render_control_chains(model, control_chains, gen, id_map, lines,
                               show_external=show_external)

    lines.append("")

    if include_legend:
        lines.extend([
            "legend right",
            "  <b>Action Flow Legend</b>",
            "  Relationship: Notation",
            "  Flow Transfer: -->",
            "  Succession Flow: ..>",
            "  Binding (==): -[thickness=5]-",
            "  Connection: -[thickness=3]-",
            "  Composite (owns): *--",
            "  Feature Typing: --:|> ",
            "endlegend",
        ])
        lines.append("")

    lines.append("@enduml")
    return "\n".join(lines)


def _scan_grammar_body_for_flows(grammar_obj, result_list):
    """Recursively scan a grammar object's body for FlowConnectionUsage/FlowConnectionDefinition.

    Flows inside action bodies are raw grammar objects, not Usage wrappers.
    This function finds them and extracts their from/to endpoint names.

    Appends (from_names, to_names, flow_name) tuples to result_list.
    """
    body = getattr(grammar_obj, 'body', None)
    if body is None:
        return
    children = getattr(body, 'children', None)
    if children is None:
        return
    if not isinstance(children, list):
        children = [children]

    for body_item in children:
        _scan_body_tree(body_item, result_list)


def _scan_body_tree(node, result_list):
    """Recursively walk grammar body tree nodes looking for flow grammar objects."""
    if node is None:
        return

    class_name = node.__class__.__name__
    if class_name in ('FlowConnectionUsage', 'FlowConnectionDefinition',
                      'SuccessionFlowConnectionUsage'):
        from_names, to_names = _extract_flow_endpoints_from_grammar(node)
        # Extract name from declaration
        flow_name = None
        decl = getattr(node, 'declaration', None)
        if decl:
            inner_decl = getattr(decl, 'declaration', None)
            if inner_decl and hasattr(inner_decl, 'identification') and inner_decl.identification:
                flow_name = inner_decl.identification.declaredName
        # Also try usage-level declaration
        if flow_name is None and hasattr(node, 'declaration'):
            d = node.declaration
            if hasattr(d, 'identification') and d.identification:
                flow_name = d.identification.declaredName
        result_list.append((from_names, to_names, flow_name, node))
        return

    children = getattr(node, 'children', None)
    if children is None:
        return
    if not isinstance(children, list):
        children = [children]
    for child in children:
        _scan_body_tree(child, result_list)


def _extract_flow_endpoints_from_grammar(flow_grammar):
    """Extract from/to names from a FlowConnectionUsage/FlowConnectionDefinition grammar object."""
    declaration = getattr(flow_grammar, 'declaration', None)
    if declaration is None:
        return None, None

    children = getattr(declaration, 'children', None)
    if not children or len(children) < 3:
        return None, None

    from_names = None
    to_names = None

    for end_idx, result in [(1, 'from'), (2, 'to')]:
        end_member = children[end_idx]
        if end_member is None:
            continue
        if not hasattr(end_member, 'children'):
            continue
        flow_end = end_member.children
        if flow_end is None:
            continue
        if not hasattr(flow_end, 'children'):
            continue
        for child in flow_end.children:
            if hasattr(child, 'children') and hasattr(child.children, 'names'):
                names = child.children.names
                if result == 'from':
                    from_names = names
                else:
                    to_names = names

    return from_names, to_names


def _resolve_typed_def(model, tb_name):
    """Resolve a typed-by name to its definition element (or None)."""
    if not tb_name:
        return None
    found = model.find(tb_name)
    if isinstance(found, list):
        return found[0] if found else None
    return found


def _typed_label(element, model):
    """Element label with its type (``s : Sensor``) when typed.

    Official SysML v2 notation conveys feature typing in the name
    compartment of usages rather than as ``--:|>`` arrows in
    interconnection/package views.
    """
    name = _get_element_name(element)
    d = _resolve_typed_def(model, _get_typedby_name(element))
    tname = getattr(d, 'name', None) if d is not None else None
    if not tname and d is not None and getattr(d, 'names', None):
        tname = d.names[-1]
    if tname:
        return f"{name} : {tname}"
    return name


def _flow_declared_name(flow_element):
    """Recover a flow's declared name (``flow f1 from ...`` -> ``f1``).

    The visitor assigns anonymous flow usages a UUID name; the declared
    name survives in the grammar's
    FlowConnectionDeclaration -> UsageDeclaration -> FeatureDeclaration
    -> Identification.declaredName chain.  Returns None when absent.
    """
    g = getattr(flow_element, 'grammar', None)
    if g is None:
        return None
    decl = getattr(g, 'declaration', None)
    if decl is None:
        return None
    d = getattr(decl, 'declaration', None)      # UsageDeclaration
    if d is None:
        return None
    d2 = getattr(d, 'declaration', None)        # FeatureDeclaration
    if d2 is None:
        return None
    ident = getattr(d2, 'identification', None)
    return getattr(ident, 'declaredName', None) if ident is not None else None


def _extract_flow_connections(model):
    """Scan the model for all flow connections (Usage-level and grammar-level).

    Returns:
        list of (from_names, to_names, flow_name, is_grammar_obj) tuples.
        is_grammar_obj is True for flows found inside grammar bodies
        (e.g., flows inside action definitions).
    """
    connections = []
    visited = set()

    def _scan_element(element):
        elem_id = id(element)
        if elem_id in visited:
            return
        visited.add(elem_id)

        if isinstance(element, (Model, Package)):
            for child in getattr(element, 'children', []):
                _scan_element(child)
            return

        # Check for Usage-level flow
        if getattr(element, 'sysml_type', '') == 'flow':
            from_names, to_names = _extract_flow_endpoints(element)
            flow_name = getattr(element, 'name', None)
            if (flow_name and len(flow_name) == 36
                    and flow_name.count("-") == 4):
                declared = _flow_declared_name(element)
                if declared:
                    flow_name = declared
            connections.append((from_names, to_names, flow_name, False))

        # Scan every element's grammar body for embedded flows
        grammar = getattr(element, 'grammar', None)
        if grammar:
            _scan_grammar_body_for_flows(grammar, connections)

        # Recurse into children
        for child in getattr(element, 'children', []):
            _scan_element(child)

    for child in getattr(model, 'children', []):
        _scan_element(child)

    return connections


def _extract_control_chains(model):
    """Extract per-action control-flow chains (initial/decide/merge/fork/join
    nodes plus final targets) from action grammar bodies.

    SysML v2 control nodes appear inside action bodies as

    - ``first start;``  -> InitialNodeMember (the initial node)
    - ``decide`` / ``merge`` / ``fork`` / ``join``  -> ControlNode grammar
    - ``then X`` / ``if <cond> then X`` / ``else X``  ->
      ActionTargetSuccessionMember (succession edges)
    - ``done`` (and ``terminate``) as succession targets -> final node

    The body items in source order carry the chain: an
    ``EmptySuccessionMember`` marks that the following declared node
    continues the succession chain; ``ActionTargetSuccessionMember``
    entries reference previously declared (or later declared) nodes
    by name.

    Returns a list of ``(owner_element, nodes, edges)`` where

    - ``nodes`` is ``[(kind, name, ref)]`` with ``kind`` one of
      ``initial``/``final``/``control``/``action`` and ``ref`` the
      grammar object or semantic element;
    - ``edges`` is ``[(src_ref, dst_ref, label)]`` with refs of
      ``('initial',)`` / ``('final',)`` / ``('control', grammar)`` /
      ``('action', element)``.

    Only actions whose bodies actually carry control members produce
    chains.
    """
    chains = []
    sem_by_grammar = {}

    def _index(el):
        g = getattr(el, 'grammar', None)
        if g is not None and id(g) not in sem_by_grammar:
            sem_by_grammar[id(g)] = el
        for child in getattr(el, 'children', None) or []:
            _index(child)

    for child in getattr(model, 'children', []):
        _index(child)

    def _kids(value):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    def _inner_usage(member):
        """First usage-level node under an ActionNodeMember/BehaviorUsageMember."""
        for sub in _kids(getattr(member, 'children', None)):
            for node in _kids(sub):
                return node
        return None

    def _resolve_target(name, registry):
        if name in ('done', 'terminate'):
            return ('final',)
        if name in ('start',):
            return ('initial',)
        return registry.get(name)

    def _scan_body(owner, body):
        items = []
        for item in _kids(getattr(body, 'children', None)):
            for member in _kids(getattr(item, 'children', None)):
                items.append(member)
        if not items:
            return

        # Pass 1: register declared nodes by name for target resolution.
        registry = {}
        for member in items:
            mname = member.__class__.__name__
            if mname not in ('ActionNodeMember', 'BehaviorUsageMember'):
                continue
            for sub in _kids(getattr(member, 'children', None)):
                for node in _kids(getattr(sub, 'children', None)):
                    if node.__class__.__name__ == 'ControlNode':
                        dname = getattr(node, 'declared_name', None)
                        if dname:
                            registry[dname] = ('control', node)
                    else:
                        sem = sem_by_grammar.get(id(node))
                        name = getattr(sem, 'name', None) if sem is not None else None
                        if name:
                            registry.setdefault(name, ('action', sem))

        # Pass 2: walk the chain in source order.
        nodes = []          # (kind, name, ref)
        edges = []          # (src_ref, dst_ref, label)
        last = None         # current chain tail
        last_decision = None
        pending_empty = False
        seen_kinds = set()

        for member in items:
            mname = member.__class__.__name__
            if mname == 'EmptySuccessionMember':
                pending_empty = True
            elif mname == 'InitialNodeMember':
                nodes.append(('initial', None, None))
                last = ('initial',)
                seen_kinds.add('initial')
                pending_empty = False
            elif mname == 'ActionTargetSuccessionMember':
                tgt = getattr(member, 'declared_name', None)
                cond = getattr(member, 'condition', None)
                kw = getattr(member, 'keyword', 'then')
                if tgt is None:
                    continue
                if (cond or kw == 'else') and last_decision is not None:
                    src = last_decision
                else:
                    src = last
                if tgt in ('done', 'terminate'):
                    dst = ('final',)
                else:
                    dst = registry.get(tgt)
                if dst is None:
                    continue
                label = cond if cond else ('else' if kw == 'else' else None)
                edges.append((src, dst, label))
                # Advance the chain on plain 'then'; guarded/else branches
                # fan out from the decision node and do not advance it.
                if not cond and kw == 'then':
                    last = dst
                    if dst[0] == 'control' and getattr(dst[1], 'keyword', None) == 'decide':
                        last_decision = dst
                seen_kinds.add('edges')
            elif mname in ('ActionNodeMember', 'BehaviorUsageMember'):
                ref = None
                for sub in _kids(getattr(member, 'children', None)):
                    for node in _kids(getattr(sub, 'children', None)):
                        if node.__class__.__name__ == 'ControlNode':
                            ref = ('control', node)
                        else:
                            sem = sem_by_grammar.get(id(node))
                            if sem is not None:
                                ref = ('action', sem)
                if ref is None:
                    continue
                nodes.append(ref)
                seen_kinds.add(ref[0])
                if pending_empty:
                    if last is not None:
                        edges.append((last, ref, None))
                    last = ref
                    if (ref[0] == 'control'
                            and getattr(ref[1], 'keyword', None) == 'decide'):
                        last_decision = ref
                pending_empty = False

        if edges:
            chains.append((owner, nodes, edges, seen_kinds))

    def _walk(element, depth=0):
        if depth > 30:
            return
        if getattr(element, 'sysml_type', '') == 'action':
            grammar = getattr(element, 'grammar', None)
            body = getattr(grammar, 'body', None) if grammar is not None else None
            if body is not None:
                _scan_body(element, body)
        for child in getattr(element, 'children', None) or []:
            _walk(child, depth + 1)

    for child in getattr(model, 'children', []):
        _walk(child)

    return chains
    for child in getattr(model, 'children', []):
        _walk(child)

    return chains


def _render_control_chains(model, control_chains, gen, id_map, lines,
                           show_external=False):
    """Emit PlantUML nodes + edges for extracted control-flow chains.

    Shapes (monochrome-friendly, no color):

    - initial:   solid black dot (``circle <<initial>>``) — the official
      initial-node notation
    - final:     labeled circle (``circle <<final>>``) for ``done`` /
      ``terminate`` succession targets
    - decision / merge / fork / join: hexagon nodes with stereotypes
      (the graph renderer's stand-in for the official diamond / bar
      shapes)
    - chain edges: dotted ``..>`` successions (pilot ``VAction``),
      with guard conditions / ``else`` as labels
    """
    ctrl_counter = 0

    def _next_alias():
        nonlocal ctrl_counter
        ctrl_counter += 1
        return f"CN{ctrl_counter}"

    def _node_label(kind, name, keyword=None):
        if kind == 'initial':
            return " "
        if kind == 'final':
            return name or "done"
        # control nodes: keep the declared name, else the keyword itself
        return name or keyword or ""

    def _node_stereotype(kind, keyword=None):
        if kind == 'initial':
            return "<<initial>>"
        if kind == 'final':
            return "<<final>>"
        return f"<<{keyword}>>"

    # Per-chain rendering: each action owns its initial / final nodes,
    # so node identity is scoped to the chain being emitted.
    emitted_any = False
    for owner, nodes, edges, seen in control_chains:
        if gen._included_ids and id(owner) not in gen._included_ids:
            continue

        chain_alias = {}   # ref identity -> PlantUML alias (chain-scoped)

        def _alias_of(ref):
            """Alias for an edge endpoint ref, declaring the node if new."""
            nonlocal ctrl_counter
            if ref is None:
                return None
            kind = ref[0]
            if kind == 'initial':
                if 'initial' not in chain_alias:
                    chain_alias['initial'] = _next_alias()
                    lines.append(f'circle " " as {chain_alias["initial"]} '
                                 f'<<initial>>')
                return chain_alias['initial']
            if kind == 'final':
                if 'final' not in chain_alias:
                    chain_alias['final'] = _next_alias()
                    lines.append(f'circle "done" as {chain_alias["final"]} '
                                 f'<<final>>')
                return chain_alias['final']
            if kind == 'control':
                key = ('control', id(ref[1]))
                if key not in chain_alias:
                    chain_alias[key] = _next_alias()
                    kw = getattr(ref[1], 'keyword', None)
                    name = getattr(ref[1], 'declared_name', None)
                    lines.append(f'hexagon "{_node_label(kind, name, kw)}" '
                                 f'as {chain_alias[key]} '
                                 f'{_node_stereotype(kind, kw)}')
                return chain_alias[key]
            if kind == 'action':
                return id_map.get(id(ref[1]))
            return None

        for src, dst, label in edges:
            s_alias = _alias_of(src)
            d_alias = _alias_of(dst)
            if not s_alias or not d_alias:
                continue  # endpoint outside the rendered selection
            arrow = ARROW_STYLES["succession_flow"]
            if label:
                lines.append(f'{s_alias} {arrow} {d_alias} : {label}')
            else:
                lines.append(f'{s_alias} {arrow} {d_alias}')
            emitted_any = True

    if emitted_any:
        lines.append("")



def _extract_connection_endpoints(conn_element):
    """Extract (from_names, to_names) from a ConnectionUsage's grammar.

    Navigates ConnectionUsage → ConnectorPart → BinaryConnectorPart →
    ConnectorEndMember → ConnectorEnd → OwnedReferenceSubsetting to
    recover the endpoint reference name paths (v0.67.0).

    Returns (from_names, to_names) as lists of name segments, or
    (None, None) when the grammar does not carry both ends.
    """
    g = getattr(conn_element, 'grammar', None)
    if g is None:
        return None, None
    part = getattr(g, 'part', None)
    binpart = getattr(part, 'part', None) if part is not None else None
    if binpart is None or binpart.__class__.__name__ != 'BinaryConnectorPart':
        return None, None
    members = getattr(binpart, 'children', None) or []
    ends = []
    for member in members:
        names = None
        for end in (getattr(member, 'children', None) or []):
            for sub in (getattr(end, 'children', None) or []):
                if sub.__class__.__name__ == 'OwnedReferenceSubsetting':
                    seg = []
                    ref = getattr(sub, 'referencedFeature', None)
                    if ref is not None and getattr(ref, 'names', None):
                        seg.extend(ref.names)
                    for chain in (getattr(sub, 'elements', None) or []):
                        fc = getattr(chain, 'feature', None)
                        for oc in (getattr(fc, 'children', None) or []):
                            cf = getattr(oc, 'chainingFeature', None)
                            if cf is not None and getattr(cf, 'names', None):
                                seg.extend(cf.names)
                    if seg:
                        names = seg
        ends.append(names)
    if len(ends) >= 2 and ends[0] and ends[1]:
        return ends[0], ends[1]
    return None, None


def _extract_connections(model):
    """Scan the model for all connector usages (``connection`` elements).

    Returns a list of ``(from_names, to_names, connection_name)``
    tuples.  Connection edges render as a thick plain line
    (``-[thickness=3]-``) per the official notation (v0.67.0).
    """
    connections = []
    visited = set()

    def _scan(element):
        elem_id = id(element)
        if elem_id in visited:
            return
        visited.add(elem_id)

        if getattr(element, 'sysml_type', '') == 'connection':
            from_names, to_names = _extract_connection_endpoints(element)
            if from_names and to_names:
                connections.append((from_names, to_names,
                                    getattr(element, 'name', None)))

        for child in getattr(element, 'children', []) or []:
            _scan(child)

    for child in getattr(model, 'children', []) or []:
        _scan(child)

    return connections


def _find_state_in_children(element, state_name):
    """Find a child state element by name within a parent's children tree."""
    if state_name is None:
        return None
    children = getattr(element, 'children', None)
    if not children:
        return None
    for child in children:
        if getattr(child, 'sysml_type', '') == 'state' and getattr(child, 'name', None) == state_name:
            return child
        # Recurse into nested states
        found = _find_state_in_children(child, state_name)
        if found:
            return found
    return None


def _extract_state_transitions(model):
    """Scan the model for all state transitions with resolved source/target elements.

    Returns:
        list of (from_state_elem, to_state_elem, transition_obj) tuples
        where from/to are resolved State elements, or None if unresolvable.
    """
    transitions = []
    visited = set()

    def _scan(element):
        elem_id = id(element)
        if elem_id in visited:
            return
        visited.add(elem_id)

        if isinstance(element, (Model, Package)):
            for child in getattr(element, 'children', []):
                _scan(child)
            return

        if getattr(element, 'sysml_type', '') == 'state':
            # Extract transitions from this state
            state_transitions = getattr(element, 'transitions', [])
            for trans in state_transitions:
                source_name = getattr(trans, 'source', None)
                target_name = getattr(trans, 'target', None)

                from_elem = None
                to_elem = None

                # Resolve source: look in same parent scope first
                parent = getattr(element, 'parent', None)
                if source_name and parent:
                    from_elem = _find_state_in_children(parent, source_name)
                # Fall back to model-wide search
                if from_elem is None and source_name:
                    found = model.find(source_name)
                    if found:
                        from_elem = found[0] if isinstance(found, list) else found

                # Resolve target: same approach
                if target_name and parent:
                    to_elem = _find_state_in_children(parent, target_name)
                if to_elem is None and target_name:
                    found = model.find(target_name)
                    if found:
                        to_elem = found[0] if isinstance(found, list) else found

                transitions.append((from_elem, to_elem, trans))

            # Recurse into nested states
            for child in getattr(element, 'children', []):
                _scan(child)

        # Also recurse into non-state children (for states inside parts, etc.)
        for child in getattr(element, 'children', []):
            _scan(child)

    for child in getattr(model, 'children', []):
        _scan(child)

    return transitions


def _format_transition_label(transition):
    """Format a transition's trigger, guard, and effect into a PlantUML label."""
    parts = []
    trigger = getattr(transition, 'trigger', None)
    guard = getattr(transition, 'guard', None)
    effect = getattr(transition, 'effect', None)
    name = getattr(transition, 'name', None)

    if trigger:
        parts.append(trigger)
    if guard:
        parts.append(f"[{guard}]")
    if effect:
        parts.append(f"/ {effect}")
    if not parts and name:
        return name
    return " ".join(parts) if parts else "transition"


def _expand_with_state_transitions(model, included_ids):
    """Expand inclusion set to include states connected by transitions."""
    state_transitions = _extract_state_transitions(model)
    for from_elem, to_elem, trans in state_transitions:
        for elem in [from_elem, to_elem]:
            if elem and id(elem) in included_ids:
                # Add the other endpoint too
                other = to_elem if elem is from_elem else from_elem
                if other:
                    included_ids.add(id(other))
                # Also add the parent state that owns this transition
                parent = getattr(trans, 'parent', None)
                if parent:
                    included_ids.add(id(parent))


def as_state_transition_view(model, focus=None, elements=None, style="bw",
                              direction="TB", include_legend=False,
                              max_depth=None, show_external=False,
                              auto_include_transitions=True,
                              custom_style=None):
    """Generate a State Transition View (STV) diagram.

    Corresponds to SysML v2 ``StateTransitionView``, which specializes
    ``InterconnectionView``. Presents states and their transitions,
    including:
    - States with nested states
    - Entry, do, and exit actions
    - Transition usages with triggers, guards, and actions
    - Compartments on states

    When ``auto_include_transitions=True`` (default), selecting states
    via ``focus`` or ``elements`` automatically discovers and includes
    all transitions involving those states.

    Args:
        model: A sysmlpy Model instance
        focus: Optional element to focus on (renders subtree)
        elements: Optional list of specific elements to include
        style: "bw" (default) or "color"
        direction: "TB" or "LR"
        include_legend: Whether to include relationship legend
        max_depth: Maximum depth to traverse from focus
        show_external: Show relationships to elements outside selection
        auto_include_transitions: Auto-discover transitions for selected states
        custom_style: Optional PlantUML style lines to append

    Returns:
        str: PlantUML text
    """
    lines = []
    lines.append("@startuml")
    lines.append("")

    # Style - use state styling
    if style == "bw":
        lines.extend([
            "skinparam monochrome true",
            "skinparam wrapWidth 300",
            "skinparam defaultFontSize 12",
            "skinparam defaultFontName Helvetica",
        ])
    else:
        lines.extend([
            "<style>",
            "root {",
            "    BackGroundColor white",
            "    FontName Helvetica",
            "    FontSize 13",
            "}",
            "state {",
            "    LineColor #444444",
            "    LineThickness 1.5",
            "    BackgroundColor white",
            "    Padding 10",
            "}",
            "arrow {",
            "    LineColor #555555",
            "    LineThickness 1.5",
            "}",
            "</style>",
            "",
            "skinparam wrapWidth 400",
        ])

    if custom_style:
        lines.append("")
        lines.extend(custom_style)

    lines.append("")

    if direction == "LR":
        lines.append("left to right direction")
    else:
        lines.append("top to bottom direction")
    lines.append("")

    header = _make_diagram_header(
        "stv", model, focus=focus, elements=elements, label="State Transition View"
    )
    lines.append(f'title {header}')
    lines.append("")
    lines.append("hide circle")
    lines.append("")

    # Build inclusion set
    gen = PlantUMLGenerator(model, style=style, focus=focus,
                            elements=elements, max_depth=max_depth,
                            include_legend=False,
                            show_external=show_external)
    gen._build_inclusion_set()

    # Auto-expand with state transitions
    if auto_include_transitions:
        _expand_with_state_transitions(model, gen._included_ids)

    # Extract all state transitions for arrow rendering
    state_transitions = _extract_state_transitions(model)

    # Traverse
    gen._traverse(gen.model)

    id_map = gen.id_map
    elements_list = gen.elements
    relationships = gen.relationships

    # Filter for state-relevant elements
    stv_types = {"state", "action", "attribute"}

    # Find first child state for initial state marker and terminal states for final marker
    first_state_alias = None
    terminal_states = []
    focus_name = getattr(focus, 'name', None) if focus else None
    
    # Render state elements using PlantUML state keyword for proper state
    # diagram support; composite states nest their children via state blocks
    # (official stv notation — v0.67.0)
    type_by_alias = {}
    name_by_alias = {}
    for alias, name, stereotype, elem, is_included in elements_list:
        type_by_alias[alias] = getattr(elem, 'sysml_type', '')
        name_by_alias[alias] = name

    # State containment hierarchy (composite edges between states)
    state_children = {}
    for src, arrow, dst, label, is_external in relationships:
        if (not is_external and arrow == ARROW_STYLES["composite"]
                and type_by_alias.get(src) == 'state'
                and type_by_alias.get(dst) == 'state'):
            state_children.setdefault(src, []).append(dst)

    nested_child_aliases = {c for kids in state_children.values()
                            for c in kids}
    emitted = set()

    def _emit_state_block(alias, depth):
        """Recursively emit a state and its nested child states."""
        emitted.add(alias)
        nonlocal first_state_alias
        name = name_by_alias.get(alias, alias)
        pad = "  " * depth
        kids = state_children.get(alias, [])
        if kids:
            lines.append(f'{pad}state "{name}" as {alias} {{')
            for kid in kids:
                _emit_state_block(kid, depth + 1)
            lines.append(f'{pad}}}')
        else:
            lines.append(f'{pad}state "{name}" as {alias}')
        # Track terminal states for final marker
        if name in ('Stopped', 'Error', 'Final'):
            terminal_states.append(alias)
        # Skip the focus element itself (parent container); find first
        # child state for the initial marker
        if (first_state_alias is None
                and name not in ('Stopped', 'Error', 'Final')
                and name != focus_name):
            first_state_alias = alias

    for alias, name, stereotype, elem, is_included in elements_list:
        sysml_type = type_by_alias[alias]
        if sysml_type == 'state':
            if alias in emitted or alias in nested_child_aliases:
                continue
            # Use state keyword for proper state diagram support (initial/final markers)
            _emit_state_block(alias, 0)
        elif sysml_type in stv_types:
            lines.append(f'rectangle "{name}" as {alias}')
        else:
            continue

    lines.append("")

    # Add initial state marker (filled circle) pointing to first child state
    if first_state_alias:
        lines.append("[*] --> " + first_state_alias)
        lines.append("")

    # Render non-containment relationships (state hierarchy is expressed by
    # nesting above, not by transition arrows — v0.67.0)
    for src, arrow, dst, label, is_external in relationships:
        if arrow == ARROW_STYLES["composite"]:
            continue  # containment shown as nested state blocks
        if is_external and not show_external:
            continue
        if is_external:
            lines.append(f'{src} ..> {dst}')
        else:
            lines.append(f'{src} --> {dst}')

    lines.append("")

    # Render transition arrows
    for from_elem, to_elem, trans in state_transitions:
        if from_elem is None or to_elem is None:
            continue
        from_id = id(from_elem)
        to_id = id(to_elem)

        from_included = from_id in gen._included_ids
        to_included = to_id in gen._included_ids
        if not (from_included or to_included):
            continue

        from_alias = id_map.get(from_id)
        to_alias = id_map.get(to_id)
        if from_alias and to_alias:
            label_text = _format_transition_label(trans)
            lines.append(f'{from_alias} --> {to_alias} : {label_text}')

    lines.append("")

    # Add final state marker (bullseye) for terminal states
    for terminal_alias in terminal_states:
        lines.append(f'{terminal_alias} --> [*]')
    if terminal_states:
        lines.append("")

    if include_legend:
        lines.extend([
            "legend right",
            "  <b>State Transition Legend</b>",
            "  State Transition: -->",
            "  Composite states: nested state blocks",
            "endlegend",
        ])
        lines.append("")

    lines.append("@enduml")
    return "\n".join(lines)





def as_tree_diagram(model, focus=None, style="bw", direction="TB",
                    max_depth=None, custom_style=None):
    """Generate a tree diagram showing hierarchical containment.

    Uses nested PlantUML containers to show the ownership hierarchy
    of the model. Definitions have sharp corners, usages have rounded corners.

    Corresponds to SysML v2 tree/structure views.

    Args:
        model: A sysmlpy Model instance
        focus: Optional element to focus on (renders subtree)
        style: "bw" (default) or "color"
        direction: "TB" or "LR"
        max_depth: Maximum depth to traverse from focus
        custom_style: Optional PlantUML style lines to append

    Returns:
        str: PlantUML text
    """
    lines = []
    lines.append("@startuml")
    lines.append("")

    if style == "bw":
        lines.extend([
            "skinparam monochrome true",
            "skinparam wrapWidth 300",
            "skinparam defaultFontSize 12",
            "skinparam defaultFontName Helvetica",
            "",
            "skinparam rectangle<<part def>> {",
            "    RoundCorner 0",
            "}",
            "skinparam rectangle<<part>> {",
            "    RoundCorner 15",
            "}",
            "skinparam rectangle<<item def>> {",
            "    RoundCorner 0",
            "}",
            "skinparam rectangle<<item>> {",
            "    RoundCorner 15",
            "}",
            "skinparam rectangle<<action def>> {",
            "    RoundCorner 0",
            "}",
            "skinparam rectangle<<action>> {",
            "    RoundCorner 15",
            "}",
            "skinparam rectangle<<view def>> {",
            "    RoundCorner 0",
            "}",
            "skinparam rectangle<<view>> {",
            "    RoundCorner 15",
            "}",
        ])
    else:
        lines.extend([
            "<style>",
            "root {",
            "    BackGroundColor white",
            "    FontName Helvetica",
            "    FontSize 13",
            "}",
            "rectangle {",
            "    LineColor #444444",
            "    LineThickness 1.5",
            "    BackgroundColor white",
            "    Padding 10",
            "}",
            "</style>",
            "",
            "skinparam wrapWidth 400",
            "",
            "skinparam rectangle<<part def>> {",
            "    RoundCorner 0",
            "}",
            "skinparam rectangle<<part>> {",
            "    RoundCorner 15",
            "}",
        ])

    if custom_style:
        lines.append("")
        lines.extend(custom_style)

    lines.append("")

    if direction == "LR":
        lines.append("left to right direction")
    else:
        lines.append("top to bottom direction")
    lines.append("")

    header = _make_diagram_header(
        "gv", model, focus=focus, label="Tree Diagram"
    )
    lines.append(f'title {header}')
    lines.append("")
    lines.append("hide circle")
    lines.append("")

    # Build tree structure
    id_map = {}
    visited = set()

    def render_tree(element, depth=0):
        elem_id = id(element)
        if elem_id in visited:
            return []
        visited.add(elem_id)

        if max_depth is not None and depth >= max_depth:
            return []

        result = []
        sysml_type = getattr(element, 'sysml_type', '')
        is_def = getattr(element, 'is_definition', False)

        # Skip Model and Package containers
        if isinstance(element, (Model, Package)):
            children = getattr(element, 'children', [])
            for child in children:
                result.extend(render_tree(child, depth))
            return result

        name = getattr(element, 'name', None) or "unnamed"
        name = name.replace('"', "''")

        stereotype_map = DEFINITION_STEREOTYPES if is_def else USAGE_STEREOTYPES
        label = stereotype_map.get(sysml_type, sysml_type)
        stereotype = f"<<{label}>>"

        keyword = "rectangle"
        if sysml_type == 'state':
            keyword = "rectangle"  # avoid PlantUML state-shape constraints
        elif sysml_type == 'view':
            keyword = "folder"

        alias = _get_element_id(element, id_map)

        children = getattr(element, 'children', [])
        if children:
            result.append(f'{keyword} "{name}" as {alias} {stereotype} {{')
            for child in children:
                child_lines = render_tree(child, depth + 1)
                for cl in child_lines:
                    result.append(f"    {cl}")
            result.append("}")
        else:
            result.append(f'{keyword} "{name}" as {alias} {stereotype}')

        return result

    # Start from focus or model children
    if focus is not None:
        tree_lines = render_tree(focus)
    else:
        tree_lines = []
        for child in model.children:
            tree_lines.extend(render_tree(child))

    lines.extend(tree_lines)
    lines.append("")
    lines.append("@enduml")
    return "\n".join(lines)


def as_element_table(model, focus=None, style="bw", custom_style=None):
    """Generate a tabular element listing.

    Produces a PlantUML table showing elements with their name, type,
    definition/usage status, and parent container.

    Corresponds to SysML v2 ``TabularRendering`` / ``asElementTable``.

    NOTE: Uses rectangle-based layout for PlantUML 1.2024.7+ compatibility.

    Args:
        model: A sysmlpy Model instance
        focus: Optional element to focus on (lists its subtree)
        style: "bw" (default) or "color" (affects header shading)
        custom_style: Optional PlantUML style lines to append

    Returns:
        str: PlantUML text
    """
    lines = []
    lines.append("@startuml")
    lines.append("")

    if style == "bw":
        lines.extend([
            "skinparam monochrome true",
            "skinparam defaultFontSize 12",
            "skinparam defaultFontName Helvetica",
        ])
    else:
        lines.extend([
            "skinparam defaultFontSize 12",
            "skinparam defaultFontName Helvetica",
        ])

    if custom_style:
        lines.append("")
        lines.extend(custom_style)

    lines.append("")

    header = _make_diagram_header(
        "grv", model, focus=focus, label="Element Table"
    )
    lines.append(f'title {header}')
    lines.append("")

    # Collect elements
    elements = []
    visited = set()

    def collect(element, parent_name=None):
        elem_id = id(element)
        if elem_id in visited:
            return
        visited.add(elem_id)

        if isinstance(element, Model):
            for child in element.children:
                collect(child, parent_name=None)
            return

        if isinstance(element, Package):
            for child in element.children:
                collect(child, parent_name=parent_name)
            return

        name = getattr(element, 'name', None) or "unnamed"
        sysml_type = getattr(element, 'sysml_type', '') or ""
        is_def = getattr(element, 'is_definition', False)
        kind = "def" if is_def else "usage"
        stereotype_map = DEFINITION_STEREOTYPES if is_def else USAGE_STEREOTYPES
        label = stereotype_map.get(sysml_type, sysml_type)

        elements.append((name, label, kind, parent_name or "(root)"))

        children = getattr(element, 'children', [])
        for child in children:
            collect(child, parent_name=name)

    if focus is not None:
        collect(focus)
    else:
        for child in model.children:
            collect(child)

    # Generate table using rectangle-based layout for PlantUML 1.2024.7+ compatibility
    if elements:
        # Header row
        lines.append('rectangle "<b>Name</b>|<b>Type</b>|<b>Kind</b>|<b>Parent</b>" as HEADER #LightGray')
        
        # Data rows
        for i, (name, label, kind, parent) in enumerate(elements):
            safe_name = name.replace("|", "\\|").replace('"', "''")
            safe_label = label.replace("|", "\\|")
            safe_kind = kind.replace("|", "\\|")
            safe_parent = parent.replace("|", "\\|")
            lines.append(f'rectangle "{safe_name}|{safe_label}|{safe_kind}|{safe_parent}" as R{i}')
        
        # Connect rows with hidden lines for proper layout
        lines.append(f'HEADER -[hidden]- R0')
        for i in range(len(elements) - 1):
            lines.append(f'R{i} -[hidden]- R{i+1}')

    lines.append("")
    lines.append("@enduml")
    return "\n".join(lines)


def as_textual_notation(model, focus=None, style="bw", custom_style=None):
    """Generate a textual notation rendering.

    Uses PlantUML notes to display the hierarchical structure as
    indented text, similar to the SysML v2 textual concrete syntax.

    Corresponds to SysML v2 ``TextualRendering`` / ``asTextualNotation``.

    Args:
        model: A sysmlpy Model instance
        focus: Optional element to focus on (renders its subtree)
        style: "bw" (default) or "color"
        custom_style: Optional PlantUML style lines to append

    Returns:
        str: PlantUML text
    """
    lines = []
    lines.append("@startuml")
    lines.append("")

    if style == "bw":
        lines.extend([
            "skinparam monochrome true",
            "skinparam defaultFontSize 12",
            "skinparam defaultFontName Helvetica",
            "skinparam defaultFontName Monospaced",
        ])
    else:
        lines.extend([
            "skinparam defaultFontSize 12",
            "skinparam defaultFontName Monospaced",
        ])

    if custom_style:
        lines.append("")
        lines.extend(custom_style)

    lines.append("")

    header = _make_diagram_header(
        "gv", model, focus=focus, label="Textual Notation"
    )
    lines.append(f'title {header}')
    lines.append("")

    # Build textual representation
    text_lines = []
    visited = set()

    def build_text(element, indent=0):
        elem_id = id(element)
        if elem_id in visited:
            return
        visited.add(elem_id)

        if isinstance(element, Model):
            for child in element.children:
                build_text(child, indent)
            return

        if isinstance(element, Package):
            for child in element.children:
                build_text(child, indent)
            return

        name = getattr(element, 'name', None) or "unnamed"
        sysml_type = getattr(element, 'sysml_type', '') or ""
        is_def = getattr(element, 'is_definition', False)
        stereotype_map = DEFINITION_STEREOTYPES if is_def else USAGE_STEREOTYPES
        label = stereotype_map.get(sysml_type, sysml_type)

        prefix = "  " * indent
        text_lines.append(f"{prefix}{label} {name}")

        children = getattr(element, 'children', [])
        for child in children:
            build_text(child, indent + 1)

    if focus is not None:
        build_text(focus)
    else:
        for child in model.children:
            build_text(child)

    # Output as a single note
    lines.append("note as TextualNotation")
    for tl in text_lines:
        lines.append(tl)
    lines.append("end note")
    lines.append("")
    lines.append("@enduml")
    return "\n".join(lines)


def as_general_view(model, focus=None, elements=None, style="bw", direction="TB",
                    include_legend=False, max_depth=None, show_external=False,
                    custom_style=None, show_multiplicity=False,
                    auto_include_connections=False):
    """Generate a General View (GV) diagram.

    Corresponds to SysML v2 ``GeneralView`` (short name ``gv``).
    Presents any members of exposed model element(s) as a graph
    of nodes and edges. This is the most general view, rendering
    all model elements with their relationships.

    Args:
        model: A sysmlpy Model instance
        focus: Optional element to focus on (renders its subtree)
        elements: Optional list of specific elements to include
        style: "bw" (default) or "color"
        direction: "TB" or "LR"
        include_legend: Whether to include relationship legend
        max_depth: Maximum depth to traverse from focus
        show_external: Show relationships to elements outside selection
        custom_style: Optional PlantUML style lines to append
        show_multiplicity: Append multiplicity like [4] to element labels
        auto_include_connections: Render connector edges (``-[thickness=3]-``
            thick plain lines, official notation) between parts whose both
            endpoints are already in the view (v0.67.0)

    Returns:
        str: PlantUML text
    """
    lines = []
    lines.append("@startuml")
    lines.append("")

    if style == "bw":
        lines.extend([
            "skinparam monochrome true",
            "skinparam wrapWidth 300",
            "skinparam defaultFontSize 12",
            "skinparam defaultFontName Helvetica",
            "",
            "skinparam rectangle<<part def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<part>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<action def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<action>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<state def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<state>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<port def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<port>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<interface def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<interface>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<item def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<item>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<attribute def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<attribute>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<connection def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<connection>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<flow def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<flow>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<requirement def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<requirement>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<use case def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<use case>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<constraint def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<constraint>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<calculation def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<calculation>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<enumeration def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<enumeration>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<allocation def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<allocation>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<view def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<view>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam folder<<view def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam folder<<view>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
        ])
    else:
        lines.extend([
            "<style>",
            "root {",
            "    BackGroundColor white",
            "    FontName Helvetica",
            "    FontSize 13",
            "}",
            "rectangle {",
            "    LineColor #444444",
            "    LineThickness 1.5",
            "    BackgroundColor white",
            "    Padding 10",
            "}",
            "folder {",
            "    LineColor #444444",
            "    LineThickness 1.5",
            "    BackgroundColor white",
            "    Padding 10",
            "}",
            "</style>",
            "",
            "skinparam wrapWidth 400",
        ])

    if custom_style:
        lines.append("")
        lines.extend(custom_style)

    lines.append("")

    if direction == "LR":
        lines.append("left to right direction")
    else:
        lines.append("top to bottom direction")
    lines.append("")

    header = _make_diagram_header(
        "gv", model, focus=focus, elements=elements, label="General View"
    )
    lines.append(f'title {header}')
    lines.append("")
    lines.append("hide circle")
    lines.append("")

    gen = PlantUMLGenerator(model, style=style, focus=focus,
                            elements=elements, max_depth=max_depth,
                            include_legend=False,
                            show_external=show_external)
    gen._build_inclusion_set()
    gen._traverse(gen.model)

    id_map = gen.id_map
    elements_list = gen.elements
    relationships = gen.relationships

    gv_types = {"part", "port", "interface", "item", "attribute",
                "connection", "flow", "allocation", "action", "state",
                "requirement", "use_case", "constraint", "calculation",
                "enumeration", "view", "viewpoint", "concern", "metadata"}

    for alias, name, stereotype, elem, is_included in elements_list:
        sysml_type = getattr(elem, 'sysml_type', '')
        if sysml_type in gv_types:
            keyword = "rectangle"
            if sysml_type == 'state':
                keyword = "rectangle"  # avoid PlantUML state-shape constraints
                stereotype = "<<state>>"
            elif sysml_type == 'view':
                keyword = "folder"
            label = name
            if show_multiplicity:
                mul = _get_multiplicity_label(elem)
                if mul:
                    label = f'{name} {mul}'
            lines.append(f'{keyword} "{label}" as {alias} {stereotype}')

    lines.append("")

    for src, arrow, dst, label, is_external in relationships:
        if is_external and not show_external:
            continue
        if is_external:
            arrow = f"-[dotted,thickness=1,#999999]{arrow.lstrip('-')}"
        if label:
            lines.append(f'{src} {arrow} {dst} : {label}')
        else:
            lines.append(f'{src} {arrow} {dst}')

    lines.append("")

    # Render connector edges between parts already in the view
    # (official: thick plain line, no arrowhead — ConnectionUsage)
    if auto_include_connections:
        for from_names, to_names, conn_name in _extract_connections(model):
            from_elem = (_find_element_by_qualified_name(model, from_names)
                         if from_names else None)
            to_elem = (_find_element_by_qualified_name(model, to_names)
                       if to_names else None)
            # NOTE: grammar objects may be falsy (they define __len__ for
            # children) — membership checks must use "is not None" (v0.67.0)
            from_alias = (id_map.get(id(from_elem))
                          if from_elem is not None else None)
            to_alias = (id_map.get(id(to_elem))
                        if to_elem is not None else None)
            if from_alias and to_alias:
                if conn_name:
                    lines.append(
                        f'{from_alias} {ARROW_STYLES["connector"]} '
                        f'{to_alias} : {conn_name}')
                else:
                    lines.append(
                        f'{from_alias} {ARROW_STYLES["connector"]} {to_alias}')
        lines.append("")

    if include_legend:
        lines.extend([
            "legend right",
            "  <b>General View Legend</b>",
            "  Relationship: Notation",
            "  Composite (owns): *--",
            "  Shared (contains): o--",
            "  Owning Membership: +--",
            "  Feature Typing: --:|> ",
            "  | Specialization | --|> |",
            "  | Redefinition | --||> |",
            "  Binding (==): -[thickness=5]-",
            "  Connection: -[thickness=3]-",
            "  Flow Transfer: -->",
            "  Succession Flow: ..>",
            "  Allocation: -[thickness=5,dotted]->",
            "  Dependency: ..>>",
            "  Send Action: ..>>",
            "  Accept Action: <<..",
            "  Variant: +---",
            "  Metadata: ..@",
            "endlegend",
        ])
        lines.append("")

    lines.append("@enduml")
    return "\n".join(lines)





def as_package_view(model, focus=None, style="bw", direction="TB",
                    include_legend=False, max_depth=None,
                    show_external=False, custom_style=None):
    """Generate a Package View diagram.

    A specialization of GeneralView that filters on Package,
    Package containment, and package Import. Renders the package
    hierarchy showing packages and their contained elements.

    Args:
        model: A sysmlpy Model instance
        focus: Optional Package element to focus on (renders its subtree)
        style: "bw" (default) or "color"
        direction: "TB" or "LR"
        include_legend: Whether to include relationship legend
        max_depth: Maximum depth to traverse from focus
        show_external: Show relationships to elements outside selection
        custom_style: Optional PlantUML style lines to append

    Returns:
        str: PlantUML text
    """
    lines = []
    lines.append("@startuml")
    lines.append("")

    if style == "bw":
        lines.extend([
            "skinparam monochrome true",
            "skinparam wrapWidth 300",
            "skinparam defaultFontSize 12",
            "skinparam defaultFontName Helvetica",
            "",
            "skinparam rectangle<<package>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<part def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<part>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<item def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<item>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<action def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<action>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<attribute def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<attribute>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<requirement def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<requirement>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<view def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam rectangle<<view>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
            "skinparam folder<<view def>> {",
            "    RoundCorner 0",
            "    BackgroundColor white",
            "}",
            "skinparam folder<<view>> {",
            "    RoundCorner 15",
            "    BackgroundColor white",
            "}",
        ])
    else:
        lines.extend([
            "<style>",
            "root {",
            "    BackGroundColor white",
            "    FontName Helvetica",
            "    FontSize 13",
            "}",
            "rectangle {",
            "    LineColor #444444",
            "    LineThickness 1.5",
            "    BackgroundColor white",
            "    Padding 10",
            "}",
            "folder {",
            "    LineColor #444444",
            "    LineThickness 1.5",
            "    BackgroundColor white",
            "    Padding 10",
            "}",
            "</style>",
            "",
            "skinparam wrapWidth 400",
        ])

    if custom_style:
        lines.append("")
        lines.extend(custom_style)

    lines.append("")

    if direction == "LR":
        lines.append("left to right direction")
    else:
        lines.append("top to bottom direction")
    lines.append("")

    header = _make_diagram_header(
        "gv", model, focus=focus, label="Package View"
    )
    lines.append(f'title {header}')
    lines.append("")
    lines.append("hide circle")
    lines.append("")

    elements_seen = []

    def collect_children(element):
        children = getattr(element, 'children', [])
        for child in children:
            if isinstance(child, Package):
                collect_children(child)
            else:
                seen_ids = {id(e) for e in elements_seen}
                if id(child) not in seen_ids:
                    elements_seen.append(child)
                collect_children(child)

    if focus is not None:
        if isinstance(focus, Package):
            collect_children(focus)
        else:
            for child in model.children:
                if isinstance(child, Package):
                    collect_children(child)
    else:
        for child in model.children:
            if isinstance(child, Package):
                collect_children(child)

    all_elements = [elem for elem in elements_seen]

    gen = PlantUMLGenerator(model, style=style, focus=focus,
                            elements=all_elements if all_elements else None,
                            max_depth=max_depth,
                            include_legend=False,
                            show_external=show_external)
    gen._build_inclusion_set()
    gen._traverse(gen.model)

    id_map = gen.id_map
    relationships = gen.relationships
    included_ids = gen._included_ids

    pv_types = {"part", "item", "attribute", "action", "state",
                "requirement", "view", "viewpoint", "port",
                "interface", "connection", "flow", "constraint",
                "calculation", "enumeration", "allocation"}

    # Namespace enclosure (pilot VStructure.casePackage): packages render
    # as ``package "Name" { members }`` blocks with their owned members
    # NESTED inside.  Features of definitions are namespace members of
    # the definition, not of the enclosing package, so a package view
    # shows definitions as leaf boxes without exploding their features.
    # Containment is therefore conveyed entirely by enclosure, matching
    # the official package notation.
    def _renders(element):
        if isinstance(element, Package):
            # Packages ARE the namespace structure being viewed; the
            # inclusion set (built from all_elements) excludes them.
            return True
        return (id(element) in included_ids
                and getattr(element, 'sysml_type', '') in pv_types)

    ordered = []   # (element, parent_package_or_None, depth) in DFS order

    def _dfs(element, parent_pkg, depth):
        if _renders(element):
            ordered.append((element, parent_pkg, depth))
            if isinstance(element, Package):
                if max_depth is not None and depth + 1 > max_depth:
                    return
                for child in getattr(element, 'children', None) or []:
                    _dfs(child, element, depth + 1)
        # Non-package members do not open their namespace here: their
        # features stay inside the definition box on a package view.

    for child in getattr(model, 'children', None) or []:
        _dfs(child, None, 0)

    children_of = {}
    for elem, par, d in ordered:
        children_of.setdefault(id(par) if par is not None else None,
                               []).append((elem, d))

    def _emit(elem, depth):
        # _get_element_id assigns aliases on demand: the traversal does
        # not register packages (the old _render_package created theirs).
        alias = _get_element_id(elem, id_map)
        pad = "    " * depth
        if isinstance(elem, Package):
            name = (getattr(elem, 'name', None) or "unnamed").replace('"', "''")
            kids = children_of.get(id(elem), [])
            if kids:
                lines.append(f'{pad}package "{name}" as {alias} {{')
                for k, _kd in kids:
                    _emit(k, depth + 1)
                lines.append(pad + "}")
            else:
                lines.append(f'{pad}package "{name}" as {alias}')
        else:
            sysml_type = getattr(elem, 'sysml_type', '')
            stereotype = _get_stereotype(elem, style=style)
            label = _typed_label(elem, model)
            keyword = "rectangle"
            if sysml_type == 'view':
                keyword = "folder"
            lines.append(f'{pad}{keyword} "{label}" as {alias} {stereotype}')

    top_level = [e for e, par, _d in ordered if par is None]
    for elem in top_level:
        _emit(elem, 0)

    lines.append("")

    # Keep only relationships between rendered namespace members:
    # typing, specialization, redefinition.  Containment is conveyed by
    # the enclosure above (official notation), not by *-- edges.
    member_arrows = {ARROW_STYLES["typing"], ARROW_STYLES["specialization"],
                     ARROW_STYLES["redefinition"]}
    for src, arrow, dst, label, is_external in relationships:
        if arrow not in member_arrows:
            continue
        if is_external and not show_external:
            continue
        if is_external:
            arrow = f"-[dotted,thickness=1,#999999]{arrow.lstrip('-')}"
        # Typing info already sits in the usage labels (name : Type); the
        # pilot draws typing/specialization arrows unlabeled.
        lines.append(f'{src} {arrow} {dst}')

    lines.append("")

    if include_legend:
        lines.extend([
            "legend right",
            "  <b>Package View Legend</b>",
            "  Relationship: Notation",
            "  Namespace Containment: enclosure",
            "  Feature Typing: --:|> ",
            "  | Specialization | --|> |",
            "endlegend",
        ])
        lines.append("")

    lines.append("@enduml")
    return "\n".join(lines)





# ============================================================
# GridView Specializations
# Per SysML v2 StandardViewDefinitions, GridView presents exposed
# model elements and their relationships in a rectangular grid.
# Three specializations: Tabular View, Data Value Tabular View,
# and Relationship Matrix View.
# ============================================================

# Shared element collection helper for grid views
def _collect_grid_elements(model, focus=None):
    """Collect non-Model non-Package elements recursively.

    Returns:
        list of (element, name, label, kind, parent_name) tuples.
    """
    results = []
    visited = set()

    def collect(element, parent_name=None):
        elem_id = id(element)
        if elem_id in visited:
            return
        visited.add(elem_id)

        if isinstance(element, Model):
            for child in getattr(element, 'children', []):
                collect(child, parent_name=None)
            return

        if isinstance(element, Package):
            for child in getattr(element, 'children', []):
                collect(child, parent_name=parent_name)
            return

        name = getattr(element, 'name', None) or "unnamed"
        sysml_type = getattr(element, 'sysml_type', '') or ""
        is_def = getattr(element, 'is_definition', False)
        kind = "def" if is_def else "usage"
        stereotype_map = DEFINITION_STEREOTYPES if is_def else USAGE_STEREOTYPES
        label = stereotype_map.get(sysml_type, sysml_type)

        results.append((element, name, label, kind, parent_name or "(root)"))

        for child in getattr(element, 'children', []):
            collect(child, parent_name=name)

    if focus is not None:
        collect(focus)
    else:
        for child in getattr(model, 'children', []):
            collect(child)

    return results


def _escape_markdown(text):
    """Escape pipe and other special characters for markdown tables."""
    if text is None:
        return ""
    text = str(text)
    return text.replace("|", "\\|").replace("\n", "<br>")


def _escape_html(text):
    """Escape HTML special characters."""
    if text is None:
        return ""
    text = str(text)
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))


def _format_table_rows_plantuml(header, rows):
    """Format a PlantUML table from header and rows using rectangle-based layout.
    
    Uses rectangle elements with | separated labels connected by [hidden] edges,
    compatible with PlantUML 1.2024.7+ (unlike deprecated salt syntax).
    """
    lines = []
    if not rows:
        return lines
    
    # Header row with bold labels
    safe_header = [str(h).replace("|", "\\|").replace('"', "''") for h in header]
    header_label = "<b>" + "|</b><b>".join(safe_header) + "</b>"
    lines.append(f'rectangle "{header_label}" as HEADER #LightGray')
    
    # Data rows
    for i, row in enumerate(rows):
        safe_row = [str(c).replace("|", "\\|").replace('"', "''") for c in row]
        row_label = "|".join(safe_row)
        lines.append(f'rectangle "{row_label}" as R{i}')
    
    # Connect rows with hidden lines for proper layout
    lines.append('HEADER -[hidden]- R0')
    for i in range(len(rows) - 1):
        lines.append(f'R{i} -[hidden]- R{i+1}')
    
    return lines


def _format_table_rows_csv(header, rows):
    """Format header + rows as CSV text (v0.66.0, Goal 7).

    Uses the ``csv`` module for proper quoting/escaping.  Returns a
    trailing-newline-free string with LF line endings.
    """
    import csv as _csv
    import io as _io

    buf = _io.StringIO()
    writer = _csv.writer(buf, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buf.getvalue().rstrip("\n")


def _format_table_rows_markdown(header, rows, align=None):
    """Format a markdown table from header and rows."""
    if align is None:
        align = ["---"] * len(header)
    lines = []
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(align) + " |")
    for row in rows:
        safe_row = [_escape_markdown(c) for c in row]
        lines.append("| " + " | ".join(safe_row) + " |")
    return lines


def _format_table_rows_html(header, rows, table_class="grid-view"):
    """Format an HTML table from header and rows."""
    lines = []
    lines.append(f'<table class="{table_class}">')
    lines.append("  <thead>")
    lines.append("    <tr>")
    for h in header:
        lines.append(f"      <th>{_escape_html(h)}</th>")
    lines.append("    </tr>")
    lines.append("  </thead>")
    lines.append("  <tbody>")
    for row in rows:
        lines.append("    <tr>")
        for cell in row:
            lines.append(f"      <td>{_escape_html(cell)}</td>")
        lines.append("    </tr>")
    lines.append("  </tbody>")
    lines.append("</table>")
    return lines


def _detect_value_unit(element):
    """Try to extract value and unit from an element (typically an attribute).

    Returns:
        (value_str, unit_str) tuple.
    """
    if getattr(element, 'sysml_type', '') != 'attribute':
        return ("", "")
    try:
        value = element.get_value()
        if hasattr(value, 'magnitude') and hasattr(value, 'units'):
            mag = value.magnitude
            unit_str = str(value.units)
            if isinstance(mag, float):
                mag = f"{mag:g}"
            return (str(mag), unit_str)
        return (str(value), "")
    except (AttributeError, Exception):
        return ("", "")


# ============================================================
# 1. Tabular View
# ============================================================

DEFAULT_TABULAR_COLUMNS = ["Name", "Type", "Kind", "Parent", "Typed By", "Specializes"]


def as_tabular_view(model, focus=None, style="bw", output_format="markdown",
                    columns=None, custom_style=None):
    """Generate a Tabular View — a GridView specialization.

    Presents exposed model elements in a table with configurable columns.
    Default columns: Name, Type, Kind, Parent, Typed By, Specializes.

    Args:
        model: A sysmlpy Model instance
        focus: Optional element to focus on (lists its subtree)
        style: "bw" (default) or "color"
        output_format: "markdown" (default), "html", or "plantuml"
        columns: List of column names to include, or None for defaults
        custom_style: Optional style lines (PlantUML) or CSS (HTML)

    Returns:
        str: Table text in the requested format
    """
    if columns is None:
        columns = DEFAULT_TABULAR_COLUMNS

    elements = _collect_grid_elements(model, focus=focus)

    header = columns[:]
    rows = []
    for element, name, label, kind, parent_name in elements:
        row = []
        for col in columns:
            if col == "Name":
                row.append(name)
            elif col == "Type":
                row.append(label)
            elif col == "Kind":
                row.append(kind)
            elif col == "Parent":
                row.append(parent_name)
            elif col == "Typed By":
                tb = _get_typedby_name(element)
                row.append(tb if tb else "")
            elif col == "Specializes":
                specs = _get_specializes_names(element)
                row.append(", ".join(specs) if specs else "")
            elif col == "Redefines":
                reds = _get_redefines_names(element)
                row.append(", ".join(reds) if reds else "")
            else:
                row.append("")
        rows.append(row)

    if output_format == "csv":
        return _format_table_rows_csv(header, rows)

    if output_format == "markdown":
        align = []
        for col in columns:
            if col in ("Name", "Typed By", "Specializes", "Redefines"):
                align.append(":---")
            else:
                align.append("---")
        parts = _format_table_rows_markdown(header, rows, align=align)
        if custom_style:
            parts = [f"<!-- {custom_style} -->"] + parts
        return "\n".join(parts)

    if output_format == "html":
        parts = _format_table_rows_html(header, rows, table_class="tabular-view")
        if custom_style:
            css_lines = ["<style>"]
            css_lines.extend(custom_style if isinstance(custom_style, list) else [custom_style])
            css_lines.append("</style>")
            parts = css_lines + parts
        return "\n".join(parts)

    # PlantUML output — rectangle-based table for modern PlantUML compatibility
    lines = []
    lines.append("@startuml")
    lines.append("")

    if style == "bw":
        lines.extend([
            "skinparam monochrome true",
            "skinparam defaultFontSize 12",
            "skinparam defaultFontName Helvetica",
        ])
    else:
        lines.extend([
            "skinparam defaultFontSize 12",
            "skinparam defaultFontName Helvetica",
        ])

    if custom_style:
        lines.append("")
        lines.extend(custom_style if isinstance(custom_style, list) else [custom_style])

    lines.append("")

    diagram_title = _make_diagram_header(
        "grv", model, focus=focus, label="Tabular View"
    )
    lines.append(f'title {diagram_title}')
    lines.append("")

    lines.extend(_format_table_rows_plantuml(header, rows))

    lines.append("")
    lines.append("@enduml")
    return "\n".join(lines)


# ============================================================
# 2. Data Value Tabular View
# ============================================================

DATA_VALUE_COLUMNS = ["Element", "Attribute", "Value", "Unit", "Type"]


def as_data_value_tabular_view(model, focus=None, style="bw",
                               output_format="markdown",
                               include_units=True, custom_style=None):
    """Generate a Data Value Tabular View — a GridView specialization.

    Presents attribute elements and their values in a table.
    Shows: parent element, attribute name, value, unit, and attribute type.

    Args:
        model: A sysmlpy Model instance
        focus: Optional element to focus on (lists its subtree)
        style: "bw" (default) or "color"
        output_format: "markdown" (default), "html", or "plantuml"
        include_units: If True, includes unit column (default True)
        custom_style: Optional style lines (PlantUML) or CSS (HTML)

    Returns:
        str: Table text in the requested format
    """
    elements = _collect_grid_elements(model, focus=focus)

    header = ["Element", "Attribute", "Value", "Unit", "Type"]
    rows = []

    for element, name, label, kind, parent_name in elements:
        sysml_type = getattr(element, 'sysml_type', '')
        if sysml_type != 'attribute':
            continue
        val_str, unit_str = _detect_value_unit(element)
        if not include_units:
            unit_str = ""
        typed_by = _get_typedby_name(element) or ""
        row = [parent_name, name, val_str, unit_str, typed_by]
        rows.append(row)

    if output_format == "csv":
        return _format_table_rows_csv(header, rows)

    if output_format == "markdown":
        align = [":---", ":---", ":--", ":--", ":---"]
        parts = _format_table_rows_markdown(header, rows, align=align)
        if custom_style:
            parts = [f"<!-- {custom_style} -->"] + parts
        return "\n".join(parts)

    if output_format == "html":
        parts = _format_table_rows_html(header, rows, table_class="data-value-view")
        if custom_style:
            css_lines = ["<style>"]
            css_lines.extend(custom_style if isinstance(custom_style, list) else [custom_style])
            css_lines.append("</style>")
            parts = css_lines + parts
        return "\n".join(parts)

    # PlantUML output (default)
    lines = []
    lines.append("@startuml")
    lines.append("")

    if style == "bw":
        lines.extend([
            "skinparam monochrome true",
            "skinparam defaultFontSize 12",
            "skinparam defaultFontName Helvetica",
        ])
    else:
        lines.extend([
            "skinparam defaultFontSize 12",
            "skinparam defaultFontName Helvetica",
        ])

    if custom_style:
        lines.append("")
        lines.extend(custom_style if isinstance(custom_style, list) else [custom_style])

    lines.append("")

    diagram_title = _make_diagram_header(
        "grv", model, focus=focus, label="Data Value Tabular View"
    )
    lines.append(f'title {diagram_title}')
    lines.append("")

    lines.extend(_format_table_rows_plantuml(header, rows))

    lines.append("")
    lines.append("@enduml")
    return "\n".join(lines)


# ============================================================
# 3. Relationship Matrix View
# ============================================================

RELATIONSHIP_LABELS = {
    "composite": "C",
    "shared": "S",
    "typing": "T",
    "specialization": "G",
    "redefinition": "R",
    "binding": "B",
    "connector": "N",
    "flow": "F",
    "succession": "U",
    "allocation": "A",
    "dependency": "D",
    "import": "I",
}


def _get_relationship_between(source, target, model):
    """Check relationships between two elements.

    Returns:
        list of relationship type strings from RELATIONSHIP_LABELS.
    """
    rels = []
    source_id = id(source)
    target_id = id(target)

    if source_id == target_id:
        return []

    # Check composite containment: source is parent of target
    parent = getattr(target, 'parent', None)
    if parent is not None and id(parent) == source_id:
        rels.append("composite")

    # Check typing: source types target
    typedby = getattr(target, 'typedby', None)
    if typedby is not None and id(typedby) == source_id:
        rels.append("typing")

    # Check specialization via grammar
    source_specs = _get_specializes_names(source)
    target_name = getattr(target, 'name', None)
    if target_name and target_name in source_specs:
        rels.append("specialization")

    target_specs = _get_specializes_names(target)
    source_name = getattr(source, 'name', None)
    if source_name and source_name in target_specs:
        rels.append("specialization")

    # Check parent relationship (shared containment - siblings)
    source_parent = getattr(source, 'parent', None)
    target_parent = getattr(target, 'parent', None)
    if source_parent is not None and target_parent is not None and id(source_parent) == id(target_parent):
        if source_id != target_id:
            rels.append("shared")

    return rels


def as_relationship_matrix_view(model, focus=None, style="bw",
                                output_format="markdown",
                                row_type=None, col_type=None,
                                symmetric=True, custom_style=None):
    """Generate a Relationship Matrix View — a GridView specialization.

    Presents a matrix/grid showing relationships between model elements.
    Each cell indicates the type of relationship (C=composite, T=typing,
    G=specialization, B=binding, F=flow, etc.).

    Args:
        model: A sysmlpy Model instance
        focus: Optional element to focus on (lists its subtree)
        style: "bw" (default) or "color"
        output_format: "markdown" (default), "html", or "plantuml"
        row_type: Optional sysml_type filter for row elements
        col_type: Optional sysml_type filter for column elements
        symmetric: If True, uses same elements for rows and columns
        custom_style: Optional style lines (PlantUML) or CSS (HTML)

    Returns:
        str: Matrix text in the requested format
    """
    elements = _collect_grid_elements(model, focus=focus)

    all_elems = [e for e, _, _, _, _ in elements]
    row_elems = all_elems
    col_elems = all_elems if symmetric else all_elems

    if row_type:
        row_elems = [e for e in row_elems if getattr(e, 'sysml_type', '') == row_type]
    if col_type:
        col_elems = [e for e in col_elems if getattr(e, 'sysml_type', '') == col_type]
    if symmetric:
        col_elems = row_elems

    # Build header + rows
    header = [getattr(e, 'name', '?') or '?' for e in col_elems]
    matrix_rows = []
    for src in row_elems:
        src_name = getattr(src, 'name', None) or "unnamed"
        row = [src_name]
        for tgt in col_elems:
            rels = _get_relationship_between(src, tgt, model)
            if rels:
                labels = "".join(RELATIONSHIP_LABELS.get(r, r[0].upper()) for r in rels)
                row.append(labels)
            else:
                row.append("")
        matrix_rows.append(row)

    if output_format == "csv":
        return _format_table_rows_csv(header, matrix_rows)

    if output_format == "markdown":
        parts = _format_table_rows_markdown(header, matrix_rows, align=None)
        if custom_style:
            parts = [f"<!-- {custom_style} -->"] + parts
        return "\n".join(parts)

    if output_format == "html":
        parts = []
        parts.append('<table class="relationship-matrix-view">')
        parts.append("  <thead>")
        parts.append("    <tr>")
        parts.append("      <th></th>")
        for h in header:
            parts.append(f"      <th>{_escape_html(h)}</th>")
        parts.append("    </tr>")
        parts.append("  </thead>")
        parts.append("  <tbody>")
        for row in matrix_rows:
            src_name = row[0]
            cells = row[1:]
            parts.append("    <tr>")
            parts.append(f"      <th>{_escape_html(src_name)}</th>")
            for cell in cells:
                cell_class = ""
                if cell:
                    cell_class = f' class="rel-{cell.lower()}"'
                parts.append(f"      <td{cell_class}>{_escape_html(cell)}</td>")
            parts.append("    </tr>")
        parts.append("  </tbody>")
        parts.append("</table>")
        if custom_style:
            css_lines = ["<style>"]
            css_lines.extend(custom_style if isinstance(custom_style, list) else [custom_style])
            css_lines.append("</style>")
            parts = css_lines + parts
        parts.append("")
        parts.append("<!-- Legend: " + ", ".join(f"{k}={v}" for k, v in RELATIONSHIP_LABELS.items()) + " -->")
        return "\n".join(parts)

    # PlantUML output — rectangle-based matrix for modern PlantUML compatibility
    lines = []
    lines.append("@startuml")
    lines.append("")

    if style == "bw":
        lines.extend([
            "skinparam monochrome true",
            "skinparam defaultFontSize 11",
            "skinparam defaultFontName Helvetica",
        ])
    else:
        lines.extend([
            "skinparam defaultFontSize 11",
            "skinparam defaultFontName Helvetica",
        ])

    if custom_style:
        lines.append("")
        lines.extend(custom_style if isinstance(custom_style, list) else [custom_style])

    lines.append("")

    diagram_title = _make_diagram_header(
        "grv", model, focus=focus, label="Relationship Matrix View"
    )
    lines.append(f'title {diagram_title}')
    lines.append("")

    # Build matrix using rectangle-based layout
    if matrix_rows:
        # Header row — empty corner cell + column names
        safe_header = [str(h).replace("|", "\\|").replace('"', "''") for h in header]
        header_label = "<b>|</b><b>" + "</b>|<b>".join(safe_header) + "</b>"
        lines.append(f'rectangle "{header_label}" as MAT_HEADER #LightGray')
        
        # Data rows
        for i, row in enumerate(matrix_rows):
            safe_row = [str(c).replace("|", "\\|").replace('"', "''") for c in row]
            row_label = "|".join(safe_row)
            lines.append(f'rectangle "{row_label}" as M{i}')
        
        # Connect rows
        lines.append('MAT_HEADER -[hidden]- M0')
        for i in range(len(matrix_rows) - 1):
            lines.append(f'M{i} -[hidden]- M{i+1}')

    lines.append("")

    # Legend
    lines.append("legend bottom")
    lines.append("  <b>Relationship Legend</b>")
    for rel_name, rel_code in RELATIONSHIP_LABELS.items():
        lines.append(f"  {rel_code} = {rel_name}")
    lines.append("endlegend")

    lines.append("")
    lines.append("@enduml")
    return "\n".join(lines)


# ============================================================
# 7. Sequence View
# ============================================================

def as_sequence_view(model, focus=None, elements=None, style="bw",
                     auto_include_flows=True, custom_style=None):
    """Generate a Sequence Diagram View.

    Maps SysML v2 action flows and message passing between parts/actions
    onto PlantUML sequence diagram syntax. Each part or action becomes a
    lifeline; flow connections and action successions become messages.

    Args:
        model: A sysmlpy Model instance
        focus: Optional element to focus on (renders its subtree)
        elements: Optional list of specific elements to include
        style: "bw" (default) or "color"
        auto_include_flows: Auto-discover flows connected to selected elements
        custom_style: Optional PlantUML style lines to append

    Returns:
        str: PlantUML text
    """
    lines = []
    lines.append("@startuml")
    lines.append("")

    if style == "bw":
        lines.extend([
            "skinparam monochrome true",
            "skinparam defaultFontSize 12",
            "skinparam defaultFontName Helvetica",
        ])
    else:
        lines.extend([
            "skinparam defaultFontSize 12",
            "skinparam defaultFontName Helvetica",
        ])

    if custom_style:
        lines.append("")
        lines.extend(custom_style)

    lines.append("")

    header = _make_diagram_header(
        "sv", model, focus=focus, elements=elements, label="Sequence View"
    )
    lines.append(f'title {header}')
    lines.append("")
    
    # Collect participants (lifelines)
    gen = PlantUMLGenerator(model, style=style, focus=focus,
                            elements=elements, max_depth=None,
                            include_legend=False, show_external=True)
    gen._build_inclusion_set()
    gen._traverse(gen.model)

    participants = []
    for alias, name, stereotype, elem, is_included in gen.elements:
        sysml_type = getattr(elem, 'sysml_type', '')
        if sysml_type in ('part', 'action', 'state'):
            participants.append((alias, name, sysml_type))

    # Deduplicate by alias
    seen = set()
    participants = [p for p in participants if not (p[0] in seen or seen.add(p[0]))]

    for alias, name, sysml_type in participants:
        lines.append(f'participant "{name}" as {alias}')

    lines.append("")

    # Collect messages from flow connections
    messages = []
    flow_connections = _extract_flow_connections(model)
    for from_names, to_names, flow_name, is_grammar_obj in flow_connections:
        if not from_names or not to_names:
            continue
        from_name = from_names[0] if isinstance(from_names, list) else from_names
        to_name = to_names[0] if isinstance(to_names, list) else to_names
        label = flow_name or ""
        # Find matching participant aliases
        from_alias = None
        to_alias = None
        for alias, name, _ in participants:
            if name == from_name:
                from_alias = alias
            if name == to_name:
                to_alias = alias
        if from_alias and to_alias:
            arrow = "->"
            msg_line = f'{from_alias} {arrow} {to_alias}'
            if label:
                msg_line += f' : {label}'
            messages.append(msg_line)

    # Also add messages from action successions in grammar bodies
    _add_succession_messages(model, messages, participants)

    if not messages:
        lines.append("note top of **Participants**")
        lines.append("  No interactions found.")
        lines.append("end note")
    else:
        lines.extend(messages)

    lines.append("")
    lines.append("@enduml")
    return "\n".join(lines)


def _add_succession_messages(model, messages, participants):
    """Scan grammar bodies for action successions and add as messages."""
    visited = set()

    def _scan(element):
        elem_id = id(element)
        if elem_id in visited:
            return
        visited.add(elem_id)

        grammar = getattr(element, 'grammar', None)
        if grammar and hasattr(grammar, 'body') and grammar.body:
            _scan_body(grammar.body, element)

        for child in getattr(element, 'children', []):
            _scan(child)

    def _scan_body(body, parent):
        for child in getattr(body, 'children', []):
            if child.__class__.__name__ in ('SuccessionMember', 'GuardedSuccession'):
                _extract_succession(child, parent)
            elif child.__class__.__name__ == 'DefinitionBodyItem':
                for inner in getattr(child, 'children', []):
                    if inner.__class__.__name__ in ('SuccessionMember', 'GuardedSuccession'):
                        _extract_succession(inner, parent)
                    _scan_body(inner, parent)
            else:
                _scan_body(child, parent)

    def _extract_succession(succ, parent):
        source_name = getattr(succ, 'source', None)
        target_name = getattr(succ, 'target', None)
        if not source_name or not target_name:
            if hasattr(succ, 'children') and succ.children:
                for c in succ.children:
                    if hasattr(c, 'source') and c.source:
                        source_name = c.source
                    if hasattr(c, 'target') and c.target:
                        target_name = c.target
        if source_name and target_name:
            from_alias = None
            to_alias = None
            for alias, name, _ in participants:
                if name == source_name:
                    from_alias = alias
                if name == target_name:
                    to_alias = alias
            if from_alias and to_alias:
                msg = f'{from_alias} -> {to_alias} : succession'
                if msg not in messages:
                    messages.append(msg)

    _scan(model)


# ============================================================
# 8. Case / Use-Case View
# ============================================================

def as_case_view(model, focus=None, elements=None, style="bw",
                 custom_style=None):
    """Generate a Case / Use-Case Diagram View.

    Maps SysML v2 actions (as use cases) and external parts (as actors)
    onto PlantUML use-case diagram syntax.

    Args:
        model: A sysmlpy Model instance
        focus: Optional element to focus on (renders its subtree)
        elements: Optional list of specific elements to include
        style: "bw" (default) or "color"
        custom_style: Optional PlantUML style lines to append

    Returns:
        str: PlantUML text
    """
    lines = []
    lines.append("@startuml")
    lines.append("")

    if style == "bw":
        lines.extend([
            "skinparam monochrome true",
            "skinparam defaultFontSize 12",
            "skinparam defaultFontName Helvetica",
        ])
    else:
        lines.extend([
            "skinparam defaultFontSize 12",
            "skinparam defaultFontName Helvetica",
        ])

    if custom_style:
        lines.append("")
        lines.extend(custom_style)

    lines.append("")

    header = _make_diagram_header(
        "gv", model, focus=focus, elements=elements, label="Case View"
    )
    lines.append(f'title {header}')
    lines.append("")
    
    # Collect elements
    gen = PlantUMLGenerator(model, style=style, focus=focus,
                            elements=elements, max_depth=None,
                            include_legend=False, show_external=True)
    gen._build_inclusion_set()
    gen._traverse(gen.model)

    actors = []
    usecases = []
    for alias, name, stereotype, elem, is_included in gen.elements:
        sysml_type = getattr(elem, 'sysml_type', '')
        if sysml_type == 'part':
            parent = getattr(elem, 'parent', None)
            if parent and getattr(parent, 'sysml_type', '') != 'part':
                actors.append((alias, name))
        elif sysml_type == 'action':
            usecases.append((alias, name))

    # Deduplicate
    seen = set()
    actors = [a for a in actors if not (a[0] in seen or seen.add(a[0]))]
    seen = set()
    usecases = [u for u in usecases if not (u[0] in seen or seen.add(u[0]))]

    # System boundary
    focus_name = getattr(focus, 'name', None) if focus else None
    system_name = focus_name or "System"
    lines.append(f'rectangle "{system_name}" {{')

    for alias, name in usecases:
        lines.append(f'  usecase "{name}" as {alias}')

    lines.append("}")
    lines.append("")

    for alias, name in actors:
        lines.append(f'actor "{name}" as {alias}')

    if not usecases and not actors:
        lines.append("note top of **Elements**")
        lines.append("  No use cases or actors found in this scope.")
        lines.append("end note")
    else:
        for a_alias, _ in actors:
            for u_alias, _ in usecases:
                lines.append(f'{a_alias} --> {u_alias}')

    lines.append("")
    lines.append("@enduml")
    return "\n".join(lines)


def as_browser_view(model, focus=None, elements=None, style="bw",
                    custom_style=None):
    """Generate a Browser View (bv) — hierarchical membership tree.

    Walks the model element tree and renders it as a PlantUML Work
    Breakdown Structure diagram (``@startwbs``).  Each element shows its
    SysML keyword and name.  Packages and other containers expand as
    sub-trees.

    Args:
        model: A sysmlpy Model instance.
        focus: Optional element to root the tree at (shows its subtree).
        elements: Optional list of specific elements to include.
        style: ``"bw"`` (default) or ``"color"``.
        custom_style: Optional PlantUML style lines to append.

    Returns:
        str: PlantUML ``@startwbs`` / ``@endwbs`` text.
    """
    lines = []
    lines.append("@startwbs")
    lines.append("")

    if style == "bw":
        lines.extend([
            "skinparam monochrome true",
            "skinparam defaultFontSize 11",
            "skinparam defaultFontName Helvetica",
        ])
    else:
        lines.extend([
            "skinparam defaultFontSize 11",
            "skinparam defaultFontName Helvetica",
        ])

    if custom_style:
        lines.append("")
        lines.extend(custom_style)

    lines.append("")

    header = _make_diagram_header(
        "bv", model, focus=focus, elements=elements, label="Browser View"
    )
    lines.append(f'title {header}')
    lines.append("")
    
    # Determine the root(s) to walk
    roots: list = []
    if focus is not None:
        roots.append(focus)
    elif elements is not None:
        roots.extend(elements)
    else:
        roots.append(model)

    seen: set[int] = set()

    def _walk(element, depth: int = 0) -> None:
        """Recursively emit *element* and its children as WBS items."""
        eid = id(element)
        if eid in seen:
            return  # guard against cycles
        seen.add(eid)

        name = getattr(element, 'name', '') or ''
        sysml_type = getattr(element, 'sysml_type', None)
        if sysml_type is None:
            sysml_type = type(element).__name__

        prefix = '*' * (depth + 1)
        if name:
            label = f'<<{sysml_type}>> {name}'
        else:
            label = f'<<{sysml_type}>>'

        lines.append(f'{prefix} {label}')

        children = getattr(element, 'children', None)
        if children:
            for child in children:
                _walk(child, depth + 1)

    for root in roots:
        _walk(root)

    lines.append("")
    lines.append("@endwbs")
    return "\n".join(lines)
