# QA Report: kotlin-support

| | |
|---|---|
| **Phase** | Review (QA) |
| **Status** | `passed` |
| **Date** | 2026-11-10 |

Headless tool: `/demo-day` browser QA is structurally N/A (CLAUDE.md); QA-equivalent done hands-on.

## 2. Acceptance Criteria Verification

| AC | Steps performed | Expected | Observed | Result |
|---|---|---|---|---|
| AC-1.1 | `test_kotlin_extractor_finds_package_and_class_kinds` | Test passes | Passed in `uv run pytest` | ✅ pass |
| AC-1.2 | `test_kotlin_extractor_finds_functions_and_nesting`, `test_kotlin_extension_function_is_qualified_by_receiver`, `test_build_creates_kotlin_nodes_and_contains_edges` | Test passes | Passed in `uv run pytest` | ✅ pass |
| AC-1.3 | `test_kotlin_script_file_is_parsed`, `test_kotlin_empty_file_is_not_unparsed` | Test passes | Passed in `uv run pytest` | ✅ pass |
| AC-2.1 | `test_build_resolves_kotlin_import_of_class_and_function`, `test_build_resolves_nested_class_import_to_outer_file` | Test passes | Passed in `uv run pytest` | ✅ pass |
| AC-2.2 | `test_build_kotlin_external_and_wildcard_imports_yield_no_edge`, `test_build_kotlin_ambiguous_import_yields_no_edge` | Test passes | Passed in `uv run pytest` | ✅ pass |
| AC-3.1 | `pyproject.toml` pins `tree-sitter-kotlin==1.1.0` | Test passes | Passed in `uv run pytest` | ✅ pass |
| AC-3.2 | `test_double_build_kotlin_is_deterministic`, seven-language double build | Test passes | Passed in `uv run pytest` | ✅ pass |
| AC-3.3 | module exists; `test_all_languages_in_one_build` covers Kotlin | Test passes | Passed in `uv run pytest` | ✅ pass |
| AC-3.4 | README + `test_readme.py` | Test passes | Passed in `uv run pytest` | ✅ pass |
