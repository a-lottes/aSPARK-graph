# Plan: csharp-support

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Engineering Manager (`/sprint-plan`) |
| **Input** | `.spark/csharp-support/spec.md` (`approved`, 2026-11-09) |
| **Status** | `approved` |
| **Date** | 2026-11-09 |

## 1. Architecture Decision

Follow the Go/Rust precedent: one bytes-in/`FileExtraction`-out module `code_csharp.py`, registered in the dispatch, `.cs` added to `EXTENSION_LANGUAGE`. The first namespace in a file is stored as `package` (as Java does); `using` resolution is a namespace→files index in `build.py` that fans out like Go, and drops one trailing segment for `using static`/alias type names. Rejected: a new `namespaces` field on `FileExtraction` (would change the parse-cache format for a rare multi-namespace case).

## 2. Affected Components

`extractors/code_csharp.py` (new), `extractors/base.py`, `extractors/__init__.py`, `build.py`, `pyproject.toml`/`uv.lock`, tests, README.

## 3. Task Breakdown

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | Pin `tree-sitter-c-sharp==0.23.5`, map `.cs`, register extractor, write `code_csharp.py`. | US-1, US-3 | AC-1.1, AC-1.2, AC-1.3, AC-3.1 | – | `done` | Types, methods, constructors and local functions extracted from real parsed trees; grammar pinned `==`. |
| T2 | `using` resolution in `build.py`. | US-2 | AC-2.1, AC-2.2 | T1 | `done` | Build test: in-repo namespace yields edges, BCL/third-party none. |
| T3 | Tests: `test_extractor_csharp.py`, multi-language build + determinism. | US-3 | AC-3.2 | T1, T2 | `done` | Suite green. |
| T4 | README. | US-3 | AC-3.3 | T1 | `done` | README and `test_readme.py` name C#. |

## 4. Test Strategy

Unit tests per extractor (Java granularity), build tests for imports, multi-language and double-build tests, plus a hands-on CLI build of a scratch .NET repo.

## 5. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Namespace `using` fans out to many files | Noisy edges | Namespace is the language's real unit; BCL namespaces match nothing. |
| Grammar node shapes | Mis-parented defs | Probed the pinned grammar; tests use real parses. |

## ✅ PLAN GATE

Approved (autonomous line, recommended option).
