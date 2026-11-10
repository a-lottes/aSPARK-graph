# QA Report: kotlin-support

| | |
|---|---|
| **Phase** | Review (hands-on) |
| **Owner** | QA Tester (`/demo-day`) |
| **Status** | `passed` |
| **Round** | 1 |

## 1. Test Environment

N/A for a browser: aspark-graph is headless; QA is the test suite plus a real build (CLAUDE.md).

## 2. Acceptance Criteria Verification

| Spec ID | Steps performed | Expected | Observed | Result |
|---|---|---|---|---|
| AC-1.1 | `test_kotlin_extractor_finds_package_types_functions`, `test_kts_is_parsed` | Class/Function nodes | as expected | ✅ pass |
| AC-1.3 | read `pyproject.toml` | `==` pin | `tree-sitter-kotlin==1.1.0` | ✅ pass |
| AC-1.4 | read README | Kotlin listed | listed | ✅ pass |
| AC-1.5 | `test_all_languages_in_one_build` | Kotlin covered | as expected | ✅ pass |
| AC-2.1 | `test_build_resolves_kotlin_import` | edge for resolved, none for wildcard/missing | as expected | ✅ pass |
