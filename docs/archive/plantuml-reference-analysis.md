# SysML v2 Reference Implementation — PlantUML Visual Design Analysis

## Overview

The official SysML v2 Pilot Implementation (`org.omg.sysml.plantuml`) generates PlantUML text
from parsed SysML v2 models using a **Visitor pattern** in Java. It does **not** modify PlantUML's
source code. Instead, it maps SysML v2 concepts to the closest available PlantUML syntax, accepting
visual approximations and relying on stereotypes/legends for semantic clarity.

---

## 1. Element Box Shapes: Usage vs Definition

### The Distinction

In SysML v2, every structural element comes in two forms:
- **Definition** (e.g., `part def Wheel`) — a classifier/type
- **Usage** (e.g., `part frontLeft : Wheel`) — an instance/occurrence of a definition

### How the Reference Implementation Renders Them

Both are rendered using PlantUML's `rectangle` keyword. The visual distinction is achieved
through **stereotypes**, not different shapes:

```plantuml
rectangle "Wheel" as E1 <<(D,brown) part def>>
rectangle "frontLeft" as E2 <<(P,limegreen) part>>
```

**Key mechanism:** `styleString(Type typ)` in `SysML2PlantUMLText.java`

1. Determines the metaclass name from the EMF `EClass` (e.g., `PartDefinition`, `PartUsage`)
2. Strips `Definition` → adds ` def` suffix; strips `Usage` → no suffix
3. Wraps in a stereotype with a colored icon letter:
   - `(D,brown)` for Definitions
   - `(P,limegreen)` for Parts (Usage)
   - `(P,blue)` for Ports
   - `(B,green)` for Items
   - `(U,orange)` for generic Usages
   - `(B,lemonchiffon)` for Behaviors
   - `(F,yellow)` for Features

### Rounded Corners

The reference implementation uses PlantUML's `skinparam roundcorner` to give all boxes rounded
corners uniformly. There is **no distinction** in corner radius between Usage and Definition —
both get the same `roundcorner` value (typically 20).

```plantuml
skinparam roundcorner 20
```

### Special Elements

| Element | PlantUML Keyword | Stereotype |
|---|---|---|
| Actor (via `ActorMembership`) | `actor` | `<&person>` icon prefix |
| Stakeholder | `actor` | `<&people>` icon prefix |
| Package | `package` | none |
| Requirement | `rectangle` | `<<requirement>>` |
| State | `state` | state diagram mode |
| Action | `rectangle` | `<<action>>` |

---

## 2. Relationship Arrow Approximations

The reference implementation maps SysML v2 relationships to PlantUML arrows via
`StyleRelDefaultSwitch` in `SysML2PlantUMLStyle.java`. Each relationship type returns a
specific arrow string.

### Mapping Table

| SysML v2 Relationship | PlantUML Arrow | Visual Result | Notes |
|---|---|---|---|
| **OwningMembership** | `+--` | solid line with `+` | Standard containment |
| **Membership** (non-owning) | `+..` | dotted line with `+` | Non-owning membership |
| **FeatureMembership** (composite) | `*--` | solid line with filled diamond | Composite aggregation |
| **FeatureMembership** (non-composite) | `o--` | solid line with hollow diamond | Shared aggregation |
| **FeatureTyping** | `--:|>` | solid line with `:` and block arrow | UML realization-like |
| **Redefinition** | `--||>` | solid line with double bar + block arrow | UML realization-like |
| **Specialization** (general) | `--|>` | solid line with block arrow | UML generalization |
| **BindingConnector** | `-[thickness=5]-` | thick solid line (no arrowhead) | Emphasized connection |
| **Connector** (with metadata) | `-[thickness=3]->` | medium solid arrow | Connection with flow |
| **Connector** (no metadata) | `-[thickness=3]-` | medium solid line (no arrowhead) | Plain connection |
| **Succession** | `-->` | dotted arrow | Temporal ordering |
| **Flow / FlowUsage** | `-->` | dotted arrow | Item flow |
| **SuccessionFlowUsage** | `..>` | dotted arrow (short) | Flow in succession |
| **Dependency** | `..>>` | dotted double-arrow | UML dependency |
| **AllocationUsage** | `-[thickness=5,dotted]->` | thick dotted arrow | Allocation |
| **Comment** | `..` | dotted line (no arrowhead) | Annotation link |
| **MetadataFeature** | `..@` | dotted line with `@` | Metadata annotation |
| **Import** | `..>` | dotted arrow | Import relationship |
| **SendActionUsage** | `..>>` | dotted double-arrow | Message send |
| **AcceptActionUsage** | `<<..` | dotted double-arrow (reverse) | Message accept |
| **SatisfyRequirementUsage** | `-->` | dotted arrow | Satisfaction |
| **PerformActionUsage** | `-->` | dotted arrow | Performance |
| **ExhibitStateUsage** | `-->` | dotted arrow | Exhibition |

### What's Lost in Translation

| SysML v2 Semantics | PlantUML Approximation | Gap |
|---|---|---|
| Redefinition (slash on arrowhead) | `--||>` (double bar) | Different symbol entirely |
| Feature typing (`:|>`) | `--:|>` | Closest available, uses `:` prefix |
| Binding (no arrowhead, thick) | `-[thickness=5]-` | Good approximation |
| Flow (open arrowhead) | `-->` (filled arrowhead) | Arrowhead shape differs |
| Provided/Required interface | Not directly supported | Must use stereotypes |

---

## 3. Redefinition Decoration on Features

When `decoratedRedefined` style is enabled, redefined features get inline decoration:

```plantuml
"featureName" as E1 <<(U,orange) feature>>
E1 :> redefinedFeatureName
```

The code in `VStructure.java` adds `\n//:>>redefinedFeature//` as a note inside the box,
or uses the PlantUML icon `<&bar-trig>` prefix with the redefined name struck through:

```
<&bar-trig> featureName <s>redefinedFeatureName</s>
```

---

## 4. Compartment Rendering

The reference implementation supports **compartments** inside boxes for:
- Attributes
- Ports
- Connections
- Requirements
- States
- Actions

These are rendered as PlantUML compartment sections within `rectangle` or `component` blocks:

```plantuml
rectangle "Wheel" as E1 <<part def>> {
  attribute radius : LengthValue
  port hub : PortDefinition
}
```

---

## 5. Style System

The reference implementation defines three primary styles:

### Standard B&W (`STDBW`)
```plantuml
skin sysmlbw
skinparam monochrome true
skinparam wrapWidth 300
hide circle
```

### Standard Color (`STDCOLOR`)
```plantuml
skin sysmlc
skinparam wrapWidth 300
hide circle
```
Plus custom relationship styling:
- Connectors: `-[thickness=3,#blue]-`
- BindingConnector: `-[thickness=5,#red]-`
- FeatureValue: `-[thickness=5,#red]-`

### PlantUML Style (`PLANTUML`)
Uses standard PlantUML defaults with colored stereotypes.

### Direction & Layout Options
- `TB` — top to bottom direction
- `LR` — left to right direction
- `POLYLINE` — polyline line type
- `ORTHOLINE` — orthogonal line type

---

## 6. Multiplicity

Multiplicity can be shown in three modes:
- **EDGE** — on the relationship arrow (default)
- **NODE** — inside the element box
- **BOTH** — on both
- **NONE** — hidden

Implicit multiplicities are hidden by default unless `implicitMultiplicity` is enabled.

---

## 7. Key Takeaways for Our Implementation

1. **No PlantUML modification needed** — the reference impl uses only standard PlantUML syntax
2. **Stereotypes carry semantic weight** — the colored `(Letter,color)` icons are the primary
   visual differentiator between element types
3. **Arrow approximations are accepted** — `--||>` for redefinition, `--:|>` for typing
4. **Thickness + color differentiate relationships** — binding is thick red, connectors are blue
5. **Rounded corners are uniform** — no shape difference between Usage and Definition
6. **Compartments show internal structure** — attributes, ports, etc. inside boxes
7. **A legend is essential** — without it, the approximations are ambiguous
