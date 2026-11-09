# Spec: csharp-support

| | |
|---|---|
| **Status** | `approved` |
| **Source** | issue #16 |

## User story
US-1 — As a .NET developer, I want `.cs` files extracted so `impact` and `story_trace` see structure in my repo.

## Acceptance criteria
- AC-1.1 `.cs` → `File`, `Class` (class/struct/interface/record/enum), `Function` (method/constructor/local function) nodes with `contains` edges.
- AC-1.2 `using` directives → best-effort in-repo `imports` edges (namespace-level, like Go).
- AC-1.3 `tree-sitter-c-sharp` pinned `==` in `pyproject.toml`.
- AC-1.4 `tests/test_extractor_csharp.py` exists; the multi-language build tests cover C#.
- AC-1.5 README lists C# under Supported languages and design guarantees.

Out of scope: partial classes across files, generics beyond naming, Razor.
