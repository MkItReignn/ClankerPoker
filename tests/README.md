# Test Organization Policy

## ⚠️ CRITICAL: DO NOT WRITE TESTS IN THIS DIRECTORY

**ALL TESTS MUST BE WRITTEN IN CLOSE PROXIMITY TO THE CODE BEING TESTED.**

### Test Location Rules

1. **Tests belong next to the code they test**
   - If testing `src/domain/rules/action_applier.py`
   - Write tests in `src/domain/rules/tests/test_action_applier.py`

2. **This `tests/` directory is for:**
   - Integration tests that span multiple modules
   - End-to-end tests
   - Test fixtures and shared utilities
   - **NOT for unit tests of individual modules**

3. **Why this matters:**
   - Keeps tests close to implementation (easier to find and maintain)
   - Reduces coupling between test and source code locations
   - Makes refactoring safer (tests move with code)
   - Follows Python testing best practices

### For LLMs and AI Assistants

**DO NOT CREATE NEW TEST FILES IN `tests/unit/` OR ANY SUBDIRECTORY OF `tests/`.**

**ONLY CREATE TESTS IN `src/**/tests/` DIRECTORIES, NEXT TO THE CODE BEING TESTED.**

If you need to write tests for a module:
1. Locate the source file (e.g., `src/domain/rules/available_action_calculator.py`)
2. Create or update tests in `src/domain/rules/tests/test_available_action_calculator.py`
3. Use the existing test fixtures from `src/domain/rules/tests/conftest.py`

### Existing Test Structure

```
src/
  domain/
    rules/
      available_action_calculator.py          # Source code
      tests/
        test_available_action_calculator.py   # ✅ Tests here
        conftest.py                            # Test fixtures
```

**NOT:**
```
tests/
  unit/
    domain/
      rules/
        test_available_action_calculator.py   # ❌ DO NOT WRITE HERE
```
