# sysml2py TODO

## Features to Add

### Reference Class ✓ DONE
- Add `Reference` class to public API ✓
- Support syntax: `ref name : Type;` ✓
- Support redefinition: `ref :>> name : Type;` ✓
- Add `_set_typed_by()` for reference typing ✓

## Known Issues
- Action parsing via `loads()` not fully implemented (grammer pipeline)
- In/out parameters only for programmatic construction

## Documentation
- Add Reference section to README.md
- Add Reference section to quickstart.md

## Tests
- Add tests for Reference class

## Priority
1. Reference class (high)
2. Documentation (medium)
3. Tests (medium)