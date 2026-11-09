# Spec: csharp-support

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (`/story-time`) |
| **Status** | `approved` |
| **Date** | 2026-11-09 |

## 1. Problem & Goal

- **Problem:** `.cs` files are recorded as unparsed `File` nodes, so `impact` and `story_trace` find no structure in .NET repos.
- **Goal:** Extend the extractor pattern to C#, the way Go and Rust were added (issue #12, autonomous line: the issue text is the approved scope).
- **Out of scope:** partial classes across files, generics beyond naming, Razor files.

## 2. User Stories & Acceptance Criteria

### US-1 (Must): Extract C# source into File/Class/Function nodes

- [ ] AC-1.1: Given a `.cs` file, when the repo is built, then it yields a parsed `File` node (not `unparsed`).
- [ ] AC-1.2: class, struct, interface, record and enum declarations become `Class` nodes; nested types nest under their outer type.
- [ ] AC-1.3: methods, constructors and local functions become `Function` nodes with `contains` edges (a local function nests under its method).

### US-2 (Should): Resolve `using` directives to in-repo files

- [ ] AC-2.1: Given `using A.B;` and an in-repo file declaring namespace `A.B`, then an `imports` edge links the files; `using static`/alias forms resolve via their namespace.
- [ ] AC-2.2: A BCL or third-party `using` yields no edge.

### US-3 (Must): Pinned, tested, documented

- [ ] AC-3.1: `tree-sitter-c-sharp` is pinned with `==` in `pyproject.toml`.
- [ ] AC-3.2: `tests/test_extractor_csharp.py` exists; the multi-language build and determinism tests include C#.
- [ ] AC-3.3: README "Supported languages" and the design guarantees list C#.
