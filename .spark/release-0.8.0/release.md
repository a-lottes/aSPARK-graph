# Release: release-0.8.0

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Keep |
| **Owner** | Release Manager (`/go-live`) |
| **Input** | `.spark/csharp-support/review.md` and `qa.md`; issue #46 (`impact --brief`, PR #49) |
| **Status** | `handed-off` |
| **Version** | v0.8.0 (minor: a sixth language and a new optional `brief` form of `impact`; no breaking change) |
| **Date** | 2026-11-13 |
| **Commit** | release commit on `claude/project-thread-6tuvqo`, on top of `ab437e8` (PR #49); tag `v0.8.0` on the merge commit after the merge |
| **PR** | see `.spark/releases.md` |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status` and `Version`).
- **Summary:** bundle release of C# extraction and the bounded `impact --brief`.
- **Open:** `3 outstanding` — merge by a person, tag `v0.8.0`, publish to PyPI (needs the maintainer's token) and run the post-release smoke check against a real PyPI install.
- **On conflict:** the numbered body below wins for everything except `Status`/`Version`.

## 1. Pre-Flight Checks

- [x] `csharp-support`: `review.md` `passed`, `qa.md` `passed`
- [ ] `impact --brief` (#46, PR #49): no `.spark/` trail of its own; covered by `tests/test_impact_brief.py`. Disclosed, not hidden
- [x] Test suite: `uv run pytest` → 403 passed, 1 skipped, 4 deselected (2026-11-13, on `ab437e8` plus this version bump)
- [x] Determinism against the previous release: the graph repo's own `v0.7.3` tree, committed into a scratch repo, built `--full` under `v0.7.3` and under this branch → `graph.json` byte-identical (597,391 bytes). A repo without `.cs` files sees no change
- [x] Version: `pyproject.toml` and `uv.lock` 0.7.3 → 0.8.0
- [x] Caps unchanged: `mcp>=1.12,<1.20`, `pydantic<2.14`
- [x] Diff fence: this report, `.spark/releases.md`, `pyproject.toml`, `uv.lock`, `CLAUDE.md`

## 2. Changelog

### Added
- **C# extraction** (`csharp-support`, issue #12, PR #14): `.cs` files yield `File`, `Class` and `Function` nodes; `using` directives resolve to in-repo namespaces, best-effort. Grammar pinned `tree-sitter-c-sharp==0.23.5`. Six languages are now supported.
- **`impact --brief`** (MCP `brief=true`, issue #46, PR #49): one entry per story, grouped by feature, with confidence, ACs by tier and the changed files that reach the story. With `--feature`, other features' stories come first. Bounded by counts, and says when it was cut. Measured on real agent runs, the full answer was 63–98 KB and mostly not read.

### Changed
- Nothing. The full `impact` form is byte-stable.

### Known limitations
- C#: partial classes across files, generics beyond naming and Razor files are out of scope.
- `--brief` has no trail of its own and no measurement yet of whether agents read it more often.

## 3. Release Actions

| Action | Result |
|---|---|
| Version bump & tag | 0.7.3 → 0.8.0. Tag `v0.8.0` on the merge commit after the merge (set locally; the cloud sandbox cannot push tags). |
| PR / merge | PR into `main`; a person merges it. |
| Deploy | PyPI: `uv build` and `uv publish` by the maintainer with his own token. The Factory pin `ASPARK_GRAPH_VERSION` moves to 0.8.0 in a separate Factory PR. |
| Post-release smoke check | Pending: `uvx aspark-graph@0.8.0 serve` from PyPI must boot, plus a `build` and `impact --brief` (CLAUDE.md: hit `serve` from a real PyPI install). |

Rollback: before merge, close the PR; after a PyPI publish, yank 0.8.0 on PyPI (a version cannot be reused) and revert via a new PR.

## 4. Learnings (Keep!)

- **What went well:** the old-versus-new build on a fixed tree is cheap and settles the determinism question in one command.
- **What we'd do differently:** `--brief` came straight from a measurement and still skipped its own trail.
