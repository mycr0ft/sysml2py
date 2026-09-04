# PlantUML Visual Approximation Assessment

> **Regenerated for v0.68.0** (2026-09-03) with the repaired generators:
> official edge encodings (v0.67.0), nested composite-state blocks,
> boxes-backed iv/afv (braille + SVG, Java-free), UUID flow labels
> suppressed, relationship legends off everywhere (opt-in via
> `include_legend=True`). PNGs rendered with PlantUML 1.2024.7
> (`PLANTUML_JAR`, default `~/tools/plantuml.jar`).

## v0.68.0 example set

| # | Example | Kind | Notes |
|---|---------|------|-------|
| 01 | Usage vs Definition | PlantUML PNG | `gv`-style; monochrome |
| 02 | Relationship Arrows | PlantUML PNG | typing/specialization/composite arrows |
| 03 | Vehicle Structure | PlantUML PNG | bw style |
| 04 | B&W Style | PlantUML PNG | `as_general_view(style="bw")` |
| 06 | Interconnection | PlantUML PNG | flows between ports as edges (`-->`), typing arrows |
| 07 | General View | PlantUML PNG | monochrome default |
| 08 | Package View | PlantUML PNG | nested package rectangles |
| 10 | Action Flow View | PlantUML PNG | action boxes + flow edges, anonymous flows labeled `flow` |
| 11 | State Transition View | PlantUML PNG | nested composite states, initial/final markers, named transitions |
| 12 | Tree Diagram | PlantUML PNG | model containment tree |
| 13 | Element Table | PlantUML PNG | tabular listing |
| 14 | Textual Notation | PlantUML PNG | SysML textual notation dump |
| 15–18 | Tabular / Data Value / Matrix / HTML | text outputs | markdown + one color HTML |
| 19 | State Transition (boxes) | braille .txt + .svg | nested composite boxes, `[*]` markers — **no Java** |
| 20 | Interconnection (boxes) | braille .txt + .svg | ports ON part borders, port-to-port connection edges — **no Java** |
| 21 | Action Flow (boxes) | braille .txt + .svg | parameters as in/out ports, flows port-to-port — **no Java** |

## Original assessment (July, v0.46-era PlantUML approximations)

## Rendering Results

All 9 example diagrams were rendered successfully using PlantUML 1.2024.7:

| # | Example | Status | Notes |
|---|---|---|---|
| 1 | Usage vs Definition | Rendered | Stereotypes render as plain text; colored `(P,#color)` icons did not work |
| 2 | Relationship Arrows | Rendered | All arrow types render correctly; legend table works well |
| 3 | Vehicle Structure | Rendered | Compartments (attributes/ports inside boxes) not supported in `rectangle` |
| 4 | B&W Style | Rendered | Clean monochrome output; binding thickness stands out |
| 5 | Requirements | Rendered | Derivation, satisfaction, verify, refine all visible |
| 6 | Interconnection | Partial | Ports render as detached elements; port-to-port connections don't link properly |
| 7 | CSS Styled | Rendered | Inline arrow styling works; CSS class selectors on elements don't apply via stereotypes |
| 8 | State Machine | Rendered | Excellent — hierarchical states, transitions, guards all perfect |
| 9 | Activity | Rendered | Excellent — control flow, decisions, notes all perfect |

## What Works Well

| Feature | Quality | Notes |
|---|---|---|
| **Composite/Shared aggregation** | Exact | `*--` and `o--` match SysML v2 perfectly |
| **Binding connector** | Good | `-[thickness=4]-` thick line with no arrowhead is clear |
| **State machines** | Excellent | Native PlantUML support is comprehensive |
| **Activity diagrams** | Excellent | Native PlantUML support is comprehensive |
| **Inline arrow styling** | Good | `-[#color,thickness=N]->` works for per-relationship customization |
| **Legend tables** | Good | `legend right` renders clean reference tables |
| **Notes** | Good | `note right/left/over` works well |
| **Rounded corners** | Good | `RoundCorner` in CSS style works |
| **Shadows** | Good | `Shadowing` in CSS style works |

## What Doesn't Work / Limitations

| Feature | Issue | Workaround |
|---|---|---|
| **Colored stereotype icons** `(P,#color)` | Does not render in this PlantUML version | Use plain stereotypes + legend |
| **CSS class selectors on elements** | `.definition { BackgroundColor }` doesn't apply via `<<definition>>` | Use inline `#[color]` on each element or skinparam |
| **Compartments in rectangles** | `rectangle { attribute x }` syntax not supported | Use separate elements or `class` syntax instead |
| **Port-to-port connections** | Ports render as detached elements, not connected to boxes | Use component diagram syntax or accept detached rendering |
| **Open triangle arrowhead** | PlantUML only has filled block `|>` | Accept `--|>` approximation + legend |
| **Slash on arrowhead (redefinition)** | No equivalent in PlantUML | Use `--||>` double bar + legend |
| **Open arrowhead (flow)** | PlantUML dotted arrow has filled head | Accept `-->` approximation + legend |
| **Lollipop interface** | Not natively supported | Use stereotypes or custom sprites |

## Recommendations for Our Implementation

### 1. Arrow Mapping (follow the reference implementation)

```python
RELATIONSHIP_ARROWS = {
    "OwningMembership":       "+--",
    "Membership":             "+..",
    "FeatureMembership_comp": "*--",   # isComposite=True
    "FeatureMembership_shared": "o--", # isComposite=False
    "FeatureTyping":          "--:|>",
    "Redefinition":           "--||>",
    "Specialization":         "--|>",
    "BindingConnector":       "-[thickness=4,#E74C3C]-",
    "Connector":              "-[thickness=2,#3498DB]->",
    "Succession":             "-->",
    "Flow":                   "-->",
    "Dependency":             "..>>",
    "Allocation":             "-[thickness=3,dotted,#9B59B6]->",
    "Comment":                "..",
    "Import":                 "..>",
}
```

### 2. Element Rendering

- Use `rectangle` for all structural elements (parts, definitions, ports)
- Distinguish Usage vs Definition via stereotype text only (not color icons)
- Use `state` for state machine elements
- Use activity syntax for action/behavior diagrams
- Always include a legend

### 3. Styling Approach

Use CSS `<style>` blocks for global defaults, inline styling for relationship-specific colors:

```plantuml
<style>
rectangle {
    RoundCorner 15
    LineColor #444
    LineThickness 1.5
}
arrow {
    LineColor #555
    LineThickness 1.5
}
</style>

' Per-relationship inline styling
A -[#E74C3C,thickness=4]-> B : binding
C -[#3498DB,thickness=2]-> D : connector
```

### 4. Compartment Alternative

Since `rectangle { ... }` compartments don't work, use PlantUML's `class` syntax for elements that need internal structure:

```plantuml
class "Wheel" as WheelDef {
  +radius : LengthValue
  +pressure : PressureValue
  +hubPort : Port
}
```

Or use notes adjacent to elements:

```plantuml
rectangle "Wheel" as W <<part def>>
note right of W
  radius : LengthValue
  pressure : PressureValue
  hubPort : Port
end note
```

### 5. Verdict: Acceptable Approximations

The PlantUML approximations are **visually acceptable** for engineering documentation when accompanied by a legend. The key relationships are distinguishable:

- **Binding** (thick red line) is unmistakable
- **Composite vs Shared** (filled vs hollow diamond) is exact
- **Typing** (colon + arrow) is recognizable
- **Specialization** (block arrow) is standard UML
- **Flow/Dependency** (dotted arrows) are conventional

The main gaps (open vs filled arrowheads, slash vs double-bar) are semantic distinctions that matter to SysML v2 purists but are tolerable approximations for most audiences when documented in a legend.
