# Plan — Kotlin support

| | |
|---|---|
| Status | approved |

Add `extractors/code_kotlin.py` (mirrors Java/Go), register in dispatch, `.kt`/`.kts` in `EXTENSION_LANGUAGE`, `_kotlin_symbol_index`/`_resolve_kotlin_import` in `build.py` (package + top-level name, owner fallback), pin the grammar, tests, README.

| Task | Status |
|---|---|
| T1 extractor + dispatch + pin | done |
| T2 import resolution in build.py | done |
| T3 tests/test_extractor_kotlin.py, multi-language build tests | done |
| T4 README | done |
