# XText to textX Grammar Conversion

## Overview

sysml2py parses SysML v2 using [textX](https://github.com/textX/textX), a Python
parser generator. The SysML v2 grammar is officially defined in
[XText](https://www.eclipse.org/Xtext/) format in the
[SysML v2 Pilot Implementation](https://github.com/Systems-Modeling/SysML-v2-Pilot-Implementation).

This directory contains the tooling to convert the official XText grammar files
into textX format for use in sysml2py.

## Source Files

The 3 XText grammar files form a hierarchy:

```
KerMLExpressions.xtext   (base expressions - literals, operators, invocations)
        |
    KerML.xtext          (Kernel Modeling Language - features, types, classifiers)
        |
    SysML.xtext          (Systems Modeling Language - parts, ports, actions, etc.)
```

These are sourced from:

- **Repository:** https://github.com/Systems-Modeling/SysML-v2-Pilot-Implementation
- **Paths:**
  - `org.omg.kerml.expressions.xtext/src/org/omg/kerml/expressions/xtext/KerMLExpressions.xtext`
  - `org.omg.kerml.xtext/src/org/omg/kerml/xtext/KerML.xtext`
  - `org.omg.sysml.xtext/src/org/omg/sysml/xtext/SysML.xtext`
- **Current version:** `2026-03` tag (released 2026-04-08, Eclipse plugin v0.58.0)
- **License:** LGPL-3.0-or-later

## Conversion Process

### Step 1: Download .xtext files

Download the 3 `.xtext` files from the desired tag of the Pilot Implementation
repository and place them in this directory (`src/sysml2py/textx/`).

### Step 2: Convert XText to textX

Run the converter from this directory:

```bash
cd src/sysml2py/textx/
python xtext_to_textx.py
```

This produces 3 `.tx` files in the current directory:

- `KerMLExpressions.tx`
- `KerML.tx`
- `SysML.tx`

#### What the converter does

The converter (`xtext_to_textx.py`) performs these transformations:

1. **Strip XText-specific syntax:**
   - `grammar` declarations
   - `import` statements (EMF model imports)
   - `returns SysML::TypeName` clauses (EMF type annotations)
   - `terminal`, `fragment`, `enum` keywords
   - `@Override` annotations

2. **Remove EMF/SysML type references:**
   - `{SysML::ClassName}` empty object instantiations
   - `[SysML::Type | QualifiedName]` cross-references (replaced with `[QualifiedName]`)

3. **Strip XText syntactic predicates:**
   - `=>` used as parser hints (NOT the `'=>'` keyword string for `crosses`)

4. **Patch problematic rules:**
   - `MultiplicityExpressionMember` - textX can't handle inline alternatives
   - `ActionBodyItem` - restructured for textX compatibility
   - `IfNode` - else clause alternative extraction
   - `MultiplicityPart` - ordered/nonunique handling
   - Empty EMF rules (`EmptyTargetEnd`, `EmptySourceEnd`, `EmptyUsage`, etc.) -
     replaced with placeholder string matches

5. **Replace terminal rules:**
   - `ID`, `DECIMAL_VALUE`, `UNRESTRICTED_NAME`, `STRING_VALUE` etc. replaced
     with textX-compatible regex patterns

### Step 3: Copy .tx files to grammar directory

```bash
cp *.tx ../grammar/
```

### Step 4: Compile into single grammar file

Run the compile script from the project root:

```bash
python src/sysml2py/textx/compile_grammar.py
```

This produces `src/sysml2py/grammar/SysML_compiled.tx` which:

- Reads `KerMLExpressions.tx`, `KerML.tx`, `SysML.tx` (in that order)
- Strips comments
- Extracts individual rules
- Deduplicates (SysML rules take precedence over KerML rules of the same name)
- Writes a single flat grammar file

The compiled grammar is what sysml2py uses at runtime via
`metamodel_from_file("SysML_compiled.tx")`.

### Step 5: Manual fixes (post-compilation)

Some rules in the compiled grammar need manual addition of named attributes
for textX to produce structured parse results instead of plain strings.
Without named attributes, textX returns the matched text as a string rather
than a dictionary with named fields.

Rules that typically need `prefix=`, `declaration=`, `body=` attribute names
added after compilation:

- `UseCaseDefinition`
- `UseCaseUsage`
- `Message`

Check for other rules that parse as strings instead of dicts by testing
round-trip parsing of SysML text.

## Known Issues: Named Attributes

The biggest challenge in the XText-to-textX conversion is **named attributes**.

In XText, grammar rules use `fragment` to inline rule content into a parent,
and `returns SysML::Type` to specify the EMF object type. These mechanisms
cause attributes to be automatically propagated to parent rules. For example:

```xtext
// XText: 'fragment' inlines these attributes into the parent rule
fragment DefinitionDeclaration returns SysML::Definition :
    Identification? SubclassificationPart?
;
```

In textX, there are no fragments or EMF types. Each rule must explicitly name
its attributes for textX to produce structured parse results:

```textx
// textX: needs explicit named attributes
PartDefinition:
    prefix=OccurrenceDefinitionPrefix PartDefKeyword
    definition=Definition
;
```

Without named attributes, textX returns matched text as a plain string instead
of a structured object, causing `classes.py` to fail with `NotImplementedError`.

The current `.tx` files in `grammar/` have named attributes carefully placed
by hand. When regenerating from new `.xtext` files, these named attributes
must be re-applied. This is the most labor-intensive part of a grammar update.

## Updating to a New Version

1. Check the latest tag at https://github.com/Systems-Modeling/SysML-v2-Pilot-Implementation/releases
2. Download the 3 new `.xtext` files into this directory
3. Diff against the previous `.xtext` files to understand changes
4. Update `xtext_to_textx.py` if new XText patterns need handling
5. Run the conversion: `python3 xtext_to_textx.py`
6. Copy generated `.tx` files to `../grammar/`
7. **Critical:** Re-apply named attributes from the old `.tx` files to the new
   ones. Compare old and new `.tx` files side by side and carry over all
   `name=Rule`, `declaration=Rule`, `body=Rule`, `prefix=Rule` patterns.
8. Run `python3 compile_grammar.py` to produce `SysML_compiled.tx`
9. Apply post-compilation fixes (see Step 5 above)
10. Update `grammar/classes.py` for new/renamed/removed grammar rules
11. Update dispatch tables in `DefinitionElement`, `StructureUsageElement`,
    `BehaviorUsageElement`, etc.
12. Run tests and fix breakage

### Key changes from 2023 to 2026-03

- `FlowConnectionUsage` renamed to `FlowUsage`
- `FlowConnectionDefinition` renamed to `FlowDefinition`
- `SuccessionFlowConnectionUsage` renamed to `SuccessionFlowUsage`
- `ItemFeature` renamed to `PayloadFeature`
- `CalculationUsageDeclaration` removed, replaced by `ActionUsageDeclaration`
  and `ConstraintUsageDeclaration`
- `LifeClass` removed, replaced by `EmptyMultiplicity`
- `readonly` keyword removed, replaced by `constant`
- `crosses` / `'=>'` added as new relationship type
- `terminate` added as new action node
- `locale` added to Comment and Documentation
- `new` constructor expressions added
- `$::` global qualification added

## Version History

| Date | Pilot Impl Tag | Notes |
|------|----------------|-------|
| 2023-06 | ~2023-02 to 2023-06 | Original conversion by Christopher Cox |
| 2026-04 | 2026-03 | .xtext files updated, converter updated, .tx files pending full migration |
