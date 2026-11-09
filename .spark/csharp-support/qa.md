# QA Report: csharp-support

| | |
|---|---|
| **Phase** | Review (hands-on) |
| **Owner** | QA Tester (`/demo-day`) |
| **Input** | Working tree of `factory/issue-12` |
| **Status** | `passed` |
| **Round** | 1 |
| **Date** | 2026-11-09 |

## 1. Test Environment

N/A for a browser: aspark-graph is a headless CLI/MCP tool with no UI (CLAUDE.md: QA-equivalent is hands-on CLI). Tested by running `aspark-graph build` and `query impact` over a scratch git repo with two `.cs` files.

## 2. Acceptance Criteria Verification

| Spec ID | Steps performed | Expected | Observed | Result |
|---|---|---|---|---|
| AC-1.1 | Built a scratch repo with `.cs` files | Parsed File nodes | 7 code entities, none unparsed | ✅ pass |
| AC-1.2 | Inspected graph.json | Class nodes | `Helper`, `W` present | ✅ pass |
| AC-1.3 | Inspected graph.json | Function nodes incl. local | `W.Go`, `W.Go.L`, `Helper.Run` present | ✅ pass |
| AC-2.1 | `using Acme.Util;` in App/W.cs | imports edge | covered by `test_build_resolves_csharp_using` | ✅ pass |
| AC-2.2 | `using System;` / third-party | no edge | covered by the same test | ✅ pass |
| AC-3.1 | Read `pyproject.toml` | `==` pin | `tree-sitter-c-sharp==0.23.5` | ✅ pass |
| AC-3.2 | Ran suite | Tests exist and pass | 391 passed | ✅ pass |
| AC-3.3 | Read README | C# listed | Supported languages and design guarantees name C# | ✅ pass |

## 3. Exploratory Findings

Rebuild with `--full` is byte-identical to the incremental build; `impact Util/Helper.cs` returns the file's code entities. No findings.

## 4. Console & Network

N/A (no UI, offline tool).

## 5. Verdict

Passed.
