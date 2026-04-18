# SysML v2 Implementation Status

## Overview

This document tracks which SysML v2 grammar elements are implemented as Python classes in sysml2py.

## Implemented Classes (Public API)

| Class | Description |
|-------|-------------|
| `Part` | Parts (definition and usage) |
| `Item` | Items (definition and usage) |
| `Attribute` | Attributes (definition and usage) |
| `Port` | Ports (definition and usage) |
| `Action` | Actions (definition and usage) |
| `Reference` | References |
| `UseCase` | Use cases (definition and usage) |
| `Requirement` | Requirements (definition and usage) |
| `Interface` | Interface definitions |
| `Message` | Messages |
| `Package` | Packages |
| `Model` | Root model |

## Implemented Grammar Classes (Internal)

The following grammar classes have `get_definition()` methods for serialization:

### Core Definitions (30)
- Definition, DefinitionElement, DefinitionMember
- DefinitionDeclaration, DefinitionBody, DefinitionBodyItem
- Usage, UsageElement, UsageMember
- UsageDeclaration, UsageBody, UsageCompletion
- Package, PackageMember, PackageBody
- RootNamespace
- PartDefinition, PartUsage, PartDefinitionDeclaration
- ItemDefinition, ItemUsage
- AttributeDefinition, AttributeUsage
- PortDefinition, PortUsage
- RequirementDefinition, RequirementBody
- UseCaseDefinition, CaseBody
- InterfaceDefinition
- OccurrenceDefinitionPrefix
- BasicDefinitionPrefix, BasicUsagePrefix
- DefinitionPrefix, UsagePrefix, MemberPrefix
- ImportPrefix
- Identification, QualifiedName
- (and more...)

### Unsupported Grammar Classes (188+)

These classes lack `get_definition()` and cannot be serialized to SysML text.

#### HIGH PRIORITY - Need to implement for basic usage

| Grammar Class | Status | Notes |
|--------------|--------|-------|
| `ActionDefinition` | Missing | Core element, needs get_definition |
| `ActionUsage` | Missing | Core element, needs get_definition |
| `CalculationDefinition` | Missing | Calculations |
| `CalculationUsage` | Missing | Calculation usages |
| `ConstraintDefinition` | Missing | Constraints |
| `ConstraintUsage` | Missing | Constraint usages |
| `ConnectionDefinition` | Missing | Connections |
| `ConnectionUsage` | Missing | Connection usages |
| `FlowConnectionDefinition` | Missing | Flow connections |
| `FlowConnectionUsage` | Missing | Flow connection usages |
| `StateDefinition` | Missing | State machines |
| `StateUsage` | Missing | State usages |
| `InterfaceUsage` | Missing | Interface usages |
| `EnumerationDefinition` | Missing | Enumerations |
| `ReferenceUsage` | Missing | References |

#### MEDIUM PRIORITY

| Grammar Class | Status | Notes |
|--------------|--------|-------|
| `AliasMember` | Missing | Import aliases |
| `Import` | Missing | Package imports |
| `Documentation` | Missing | Documentation |
| `CommentSysML` | Missing | Comments |
| `IndividualUsage` | Missing | Individual elements |
| `AnalysisCaseDefinition` | Missing | Analysis cases |
| `AnalysisCaseUsage` | Missing | Analysis case usages |
| `MessageDeclaration` | Missing | Message declarations |
| `LiteralInteger` | Missing | Integer literals |
| `LiteralReal` | Missing | Real literals |
| `LiteralString` | Missing | String literals |
| `EnumeratedValue` | Missing | Enumeration values |
| `ArgumentList` | Missing | Function arguments |
| `NamedArgumentList` | Missing | Named arguments |
| `MultiplicityRange` | Missing | Multiplicity ranges |
| `FeatureTyping` | Missing | Type relationships |
| `FeatureSpecialization` | Missing | Specialization |

#### LOW PRIORITY (Expression/Internal)

These are mostly internal to the grammar and used by the parser:
- All expression classes (AdditiveExpression, etc.)
- Connector-related classes
- Transition-related classes
- Feature chaining classes

## Implementation Plan

### Phase 1: Core Elements (High Priority)

1. **ActionDefinition/ActionUsage** - Fix dump() issue
2. **ConstraintDefinition/ConstraintUsage** - Add support
3. **CalculationDefinition/CalculationUsage** - Add support
4. **ConnectionDefinition/ConnectionUsage** - Add support
5. **ReferenceUsage** - Add support

### Phase 2: Supporting Elements (Medium Priority)

1. **Import/AliasMember** - Package imports
2. **Documentation/CommentSysML** - Documentation
3. **EnumerationDefinition** - Enumerations
4. **Literal values** - For attribute values

### Phase 3: Advanced Elements (Lower Priority)

1. State machines
2. Flow connections
3. Requirements (subject, satisfy)
4. Use cases (objectives)

## Current Issues

1. **188 grammar classes missing get_definition()** - Cannot serialize to text
2. **Incomplete public API** - Users can't create all SysML elements programmatically
3. **Round-trip failures** - Some parsed elements cannot be dumped

## Next Steps

1. Add get_definition() to ActionDefinition/ActionUsage
2. Add remaining definition types to Package.load_from_grammar()
3. Create public Python classes for Constraint, Calculation, Connection, etc.
4. Add dump() methods for all grammar classes that need serialization