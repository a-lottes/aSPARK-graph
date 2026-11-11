# Plan: mcp-drift-result

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Engineering Manager (`/sprint-plan`) |
| **Input** | `.spark/mcp-drift-result/spec.md` (must be `approved`) |
| **Status** | `approved` |
| **Date** | 2026-11-11 |

<!-- Handoff: read this block first, the numbered sections below by exception. Whoever
     writes to this plan updates it in the same edit that changes a task's status or
     the plan's own status: overwrite in place, never append. The block holds one
     current state, never a per-round log; a stale block is a defect, not a cosmetic
     issue. -->

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Summary:** Catch `artifacts.TemplateDriftError` once in the `server.build_graph` adapter and return `{"built": false, "reason": "template_drift", "file", "message"}`; no change to `artifacts.py`, `build.py`, `queries.py` or `cli.py`. Implementation already committed (6cf4a95); remaining work is verification only.
- **Open:** `none` — all 8 tasks `done` (§3)
- **Binding ruling:** §3 Task Breakdown for current task status; a plan revision after review/QA findings updates §1/§3 in place, never a new section
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

<!-- Budget: ~300 lines. -->

## 1. Architecture Decision

- **Context:** `artifacts.py` raises `TemplateDriftError(file, mismatch)` on drift (`constitution.md §6`). `build.build_graph` calls `confinement.ensure_repo` first (line 110), then `artifacts.extract_features` (line 176), and only afterwards `parse_cache.save` (line 192); `graph.save` is called by the adapter after `build_graph` returns. So a drift raise already leaves `graph.json` and the parse cache untouched. `cli._cmd_build` already catches the error and prints one stderr line, exit 1. `server.build_graph` caught only `RepoRefused`, so drift reached the MCP client as a generic tool error (BACKLOG G7). Adapter rule from `constitution.md §3` / CLAUDE.md: raise in the shared module, catch and render once per adapter. Stack and module facts are taken from `constitution.md §9` (stack, entry points, module structure); `server.py`, `cli.py` and `build.py` were re-read from source because the feature touches exactly that area (§9 exception (a)).
- **Decision:** Add one `except artifacts.TemplateDriftError` branch in `server.build_graph`, directly after the `RepoRefused` branch. It returns `{"built": False, "reason": "template_drift", "file": exc.file, "message": str(exc)}`. `message` is the same string the CLI prints, so both adapters render one exception text. Nothing else changes: the success dict, the CLI, and the shared modules stay as they are. This is committed as 6cf4a95. The plan covers the proof the spec still asks for.
- **Alternatives considered:**
  | Alternative | Why rejected |
  |---|---|
  | Catch drift in `build.py` (or `queries.py`) and return a result object/flag instead of raising | Breaks "fail loudly" (`constitution.md §6`): every caller, including the CLI, would have to remember to check a flag. Also puts rendering logic into a shared module, which goes against the existing exception-to-adapter pattern (AC-2.2). |
  | Unify shapes: return `{"found": false, "reason": "template_drift", ...}` like `RepoRefused` (or add `built: false` to `RepoRefused`) | Spec A3/C1 accepts the mismatch and puts unification Out of Scope. It changes every tool's error contract, so it is a separate decision. |
  | Let FastMCP surface the exception (status quo) and document it | The README promises a structured dict for domain errors. A generic tool error makes the agent parse prose to find the file, which is what G7 is about. |
  | Shared helper `queries.drift_result(exc)` used by the server | Adds a shared function with one caller to save one line. Also edges toward shaping MCP output inside `queries.py`. YAGNI. |
- **Consequences:** Easier: agents get the file and reason as keys. The CLI and graph bytes are untouched by construction. Harder: MCP error results now come in two shapes (`found: false` vs `built: false`). Clients have to branch on the key. This is recorded as accepted debt (spec A3), not hidden.

## 2. Affected Components

- `src/aspark_graph/server.py`: `build_graph` gains the drift `except` branch (done, 6cf4a95). No new dependency, service or pattern; it reuses the existing exception-to-adapter seam.
- `src/aspark_graph/cli.py`: unchanged. `_cmd_build` already catches drift (lines 170-172). Only new tests cover it.
- `src/aspark_graph/artifacts.py`, `build.py`, `queries.py`: unchanged. `TemplateDriftError.file` already exists (A2).
- Tests: `tests/test_mcp_errors.py` (existing drift test plus the new review.md case), `tests/test_cli_mcp_parity.py` (new CLI drift and success-key tests).
- Docs: `README.md` MCP section (lines 222-227) and `.spark/BACKLOG.md` G7 (line 256 ff.), both done.
- **Blast radius (graph):** the `impact` call on the union of the `files:` paths below returned declared or inferred links into `current-artifact-names` US-1/US-4, `coverage-current-names` US-1, `security-posture` US-1, `shallow-clone-warning` US-1..4, `close-the-loop` US-4 and `distributable-install` US-1/2. These come from the shared `server.py`/`cli.py`/`artifacts.py` files. The change touches only the drift branch in `server.py`, so the read-only tools, confinement and history booleans are not affected. The full suite (T7) is the guard for those stories. `story_trace` for US-1/US-2 of this feature showed no tasks and no QA verdicts yet (expected before this plan).
- **CLI drift test:** checked; none exists. `tests/` has drift tests only at the `artifacts` level (`test_artifacts.py`, `test_current_names.py`) and no `cli.main(["build", …])` run against a drifted repo.

## 3. Task Breakdown

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | Catch `TemplateDriftError` in MCP `build_graph`, return the `built:false` dict | US-1 | AC-1.1, AC-1.2, NFR-2 | – | `done` | Committed in 6cf4a95: the `except artifacts.TemplateDriftError` branch returns `built`/`reason`/`file`/`message` and sits before `graph.save`. No new parameter, env var or bypass — files: src/aspark_graph/server.py |
| T2 | MCP drift test for `qa.md`: result dict, no graph written, existing graph unchanged | US-1 | AC-1.1, AC-1.2, AC-1.3 | T1 | `done` | `test_build_graph_template_drift_returns_structured_result` exists in 6cf4a95 and passes. It asserts `built is False`, `reason == "template_drift"`, `file` ends with `qa.md`, no `graph.json` after the first call, and the sentinel `graph.json` unchanged after the second call — files: tests/test_mcp_errors.py |
| T3 | README MCP section and BACKLOG G7 document the shape | US-2 | AC-2.3 | T1 | `done` | `README.md` lines 224-226 state `{"built": false, "reason": "template_drift", "file", "message"}`. BACKLOG G7 reads "umgesetzt (Issue #40)" with the same shape. `uv run pytest tests/test_readme.py tests/test_integration_docs.py` passes — files: README.md, .spark/BACKLOG.md |
| T4 | MCP drift test for a drifted `review.md` (no Findings section) | US-1 | AC-1.1, AC-1.2 | T1 | `done` | A new test builds a `.git`-marked tmp repo with a valid `spec.md` and a `review.md` without a `## … Findings` section. `server.build_graph` returns without raising, with `built is False`, `reason == "template_drift"`, `file` ending in `review.md`, `"Findings" in message`, and no `graph.json` afterwards. The test passes — files: tests/test_mcp_errors.py |
| T5 | CLI drift test plus CLI-to-MCP drift parity | US-2 | AC-2.1, NFR-5 | T1 | `done` | A new test runs `cli.main(["build", str(repo)])` on a drifted `qa.md` fixture (`.git`-marked). It asserts `rc != 0`, stderr is exactly one non-empty line containing the drifted file path, `"Traceback" not in` stderr or stdout, and no `graph.json`. The stderr line equals `server.build_graph(...)["message"]` on an identical copy of the repo. The test passes — files: tests/test_cli_mcp_parity.py |
| T6 | Successful-build key parity: exact keys, no `built` key, values unchanged | US-1 | AC-1.4 | T1 | `done` | A new test builds a copy of `tests/fixtures/sample_repo` (`.git`-marked) via `server.build_graph`. It asserts `set(result) == _V071_BUILD_KEYS ∪ {shallow_history, no_git_history}`, `"built" not in result`, and that `code_entities`/`artifact_entities`/`inferred_edges`/`unparsed`/`ignored_legacy_files` equal the `BuildReport` fields from `build.build_graph` on a second copy. `git show 6cf4a95 -- src/aspark_graph/server.py` shows no lines changed in the success-path `return {…}`. The test passes — files: tests/test_cli_mcp_parity.py |
| T7 | Determinism against pre-change code (round-trip at dd4b994 vs HEAD) | US-1 | AC-1.4, NFR-4 | T1 | `done` | Build fresh copies of `tests/fixtures/sample_repo` and `tests/fixtures/current_names_repo` (each `.git`-marked) through MCP `server.build_graph`, once under the pre-change code (a `git worktree` at dd4b994, or `git stash`/checkout of `server.py` from dd4b994) and once under HEAD. Compare with `cmp`: each `graph.json` pair is byte-identical. The SHA-256 digests and both SHAs are recorded in the review evidence. The byte-identical double-build test (`tests/test_build.py`) and full `uv run pytest` are green. No repo files change |
| T8 | Convention check: drift raised only in `artifacts.py`, caught once per adapter | US-2 | AC-2.2, NFR-2 | T1 | `done` | `rg -n "raise TemplateDriftError" src/` matches only `src/aspark_graph/artifacts.py`. `rg -n "except artifacts.TemplateDriftError" src/` matches exactly once in `cli.py` and once in `server.py`. `rg -n TemplateDriftError src/aspark_graph/{queries,build}.py` returns nothing. `git show 6cf4a95 --stat` lists no file under `src/` other than `server.py`. Results are recorded as review evidence. No repo files change |

## 4. Test Strategy

- **US-1 (Must):** Unit and integration tests run in-process through the directly callable `server.build_graph`, the same harness `test_mcp_errors.py` already uses. One test per drifting artifact kind: `qa.md` (T2, done) and `review.md` (T4). Each asserts the dict, the absent `graph.json` (AC-1.2) and the sentinel unchanged (AC-1.3, T2). The success-key and value contract is tested in T6. The existing `test_history_notice_iff_mcp_key_on_every_fixture` key-set assertion (`test_cli_mcp_parity.py:297`) stays as a second guard. Determinism (NFR-4) is a manual round-trip against dd4b994 (T7), because a double build under new code cannot prove "unchanged from before" (CLAUDE.md). The transport smoke test (`-m slow`) is unchanged. A FastMCP-serialisation test is deliberately skipped: the dict holds only `bool`/`str` values, the same kinds as the existing `RepoRefused` dict.
- **US-2 (Must):** The CLI drift path is an integration test through `cli.main` with `capsys` (T5): one line, non-zero exit, no traceback, same text as MCP `message`. AC-2.2 is a structural review check, not a runtime behaviour, so T8 verifies it with `rg` + `git show` and records the evidence for `/peer-review`. AC-2.3 is documentation, checked by reading (T3) with the existing doc tests green.
- **`/demo-day`:** N/A. The tool is headless (`constitution.md §8`). The QA equivalent in `/peer-review` adds a hands-on MCP `build_graph` on a scratch clone with a deliberately broken `qa.md`.
- New tests use `.git`-marked tmp dirs. No confinement bypass (`constitution.md §6`).

## 5. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| `file` is an absolute path (`str(path)` under the resolved repo root), not repo-relative | Agents get a machine-specific path. On macOS, tmp paths resolve via `/private`, which breaks naive equality asserts | Spec only demands that it names the drifted file (and NFR-2: inside the confined repo). Tests assert `endswith`, not equality. Repo-relative paths would be a contract change, out of scope |
| Two MCP error shapes (`found:false` vs `built:false`) | Clients must branch on the key | Accepted in spec A3/C1. The README states the drift shape explicitly. Unification stays a future decision |
| A later refactor moves `parse_cache.save` or a partial write before `extract_features` | A failed build could leave a stale or partial cache or graph | T2/T4 assert no `graph.json`. The ordering (build.py 176 before 192) is noted in §1. `/peer-review` re-reads `build.py` if it changes |
| Pre-change round-trip done against the wrong baseline | False determinism proof | T7 pins dd4b994 (parent of 6cf4a95) and records both SHAs alongside the digests |
| Only the first drift is reported | A repo with several drifted files needs several runs | Out of Scope by spec. Same as CLI behaviour today |
| Inherited assumption A2 (`exc.file` always set) | A missing `file` would break the contract | `TemplateDriftError.__init__` requires `file`. Every raise site passes `str(path)`, as T8's `rg` listing shows |

---

## ✅ PLAN GATE

*All boxes checked → `/increment` may start. Any box open → back to `/sprint-plan`.*

- [x] Spec status is `approved` (never plan against a draft)
- [x] Architecture decision includes rejected alternatives (a decision without alternatives is a guess)
- [x] Architecture respects the constitution's technical constraints (or a conflict is recorded)
- [x] Every task maps to a user story — no orphan tasks, no story without tasks
- [x] Every Must AC and every applicable NFR is covered by at least one task
- [x] Every task has a checkable definition of done
- [x] Task order respects dependencies
- [x] Test strategy covers every Must story
- [x] Line budget respected: Ist ~85 / Soll ~300 (excluding HTML comments) — self-reported, no linter checks this; an overage is recorded here with a reason or explicitly waived by the user
- [x] Status set to `approved` by the user (autonomous run: recommended option taken)
