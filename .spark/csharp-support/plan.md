# Plan: csharp-support

| | |
|---|---|
| **Status** | `approved` |

Follow the Go/Rust/Java precedent: pure extractor `code_csharp.py`, registry + extension entry, `_resolve_imports` branch in `build.py` (namespace index from each file's first namespace; `using static` walks up to the namespace; BCL matches nothing).

| ID | Task | Status |
|---|---|---|
| T1 | Pin `tree-sitter-c-sharp==0.23.5`, extractor, registry | done |
| T2 | `using` resolution in `build.py` | done |
| T3 | Tests (`test_extractor_csharp.py`, multi-language + determinism builds) | done |
| T4 | README | done |
