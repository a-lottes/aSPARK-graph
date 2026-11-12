# Plan: qa-multi-table

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Engineering Manager (`/sprint-plan`) |
| **Input** | `.spark/qa-multi-table/spec.md` (must be `approved`) |
| **Status** | `approved` |
| **Date** | 2026-11-12 |

<!-- Handoff: read this block first, the numbered sections below by exception. Whoever
     writes to this plan updates it in the same edit that changes a task's status or
     the plan's own status: overwrite in place, never append. The block holds one
     current state, never a per-round log; a stale block is a defect, not a cosmetic
     issue. -->

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Summary:** new `_tables()` generator in `artifacts.py` yields every separator-valid pipe-table in the QA verification section; `_parse_qa` loops over them with one running row index and the same per-table drift checks; `_first_table` and its plan/review callers stay byte-for-byte untouched.
- **Open:** `5 tasks not done` — see §3 Task Breakdown for which
- **Binding ruling:** §3 Task Breakdown for current task status; a plan revision after review/QA findings updates §1/§3 in place, never a new section
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Architecture Decision

- **Context:** `_parse_qa` (`src/aspark_graph/artifacts.py:279`) calls `_first_table(section, unescape_pipes=True)` (`:362`). That function collects the first run of pipe lines and stops at the first non-pipe line, so every later per-story table (`### US-n` sub-headings, which do not end the section: `_section` only stops at `#`/`##`) is never seen. `_first_table` is also used by `_parse_plan` (`:211`) and `_parse_review` (`:252`), and spec §6 keeps those first-table only. Artifacts are re-parsed on every build (`build.py:176`, not part of the parse cache), so no cache-version bump is needed. All five `qa*.md` trails in this repo have exactly one table in the verification section (checked by grep for separator rows), so the repo's own graph must not move.
- **Decision:** Add a private generator `_tables(block, unescape_pipes=False)` next to `_first_table`. It splits `block` into contiguous runs of pipe lines; a run whose second line is a separator row is yielded as `{header, rows}` in the same shape `_first_table` returns, a run without one is skipped (C4), and everything else (prose, `###` headings, blank lines) is ignored (C3). `_parse_qa` then iterates `_tables(section, unescape_pipes=True)`, runs the existing id-column and `Result`-column checks on **every** table (same messages, C2), and numbers rows with one counter that keeps running across tables, rows without an AC id included (C1). No table at all still returns 0. `_first_table`, `_split_row`, `_qa_id_column`, `_normalise_result` and the QACheck id scheme are not changed.
- **Alternatives considered:**
  | Alternative | Why rejected |
  |---|---|
  | Make `_first_table` take a `first_only`/`all` flag, or rewrite it on top of `_tables` | It would change the code path for plan and review parsing, which spec §6 rules out. And `_first_table` returns `None` when its first pipe run has no separator, while `_tables` skips that run (C4). Rebuilding one on top of the other changes edge cases for callers that never asked for it. Leaving it as is costs about 12 duplicated lines, and in return the byte-identity of plan and review parsing holds by construction. |
  | Split the section on `### ` sub-headings and call `_first_table` once per chunk | This ties correctness to a heading convention the spec does not require (AC-1.4 says to read every table, whatever sits between them). Two tables under one sub-heading, or a table before the first `###`, would be lost without any signal. That is the same silent under-count we are fixing. |
  | Skip later tables whose header lacks `AC`/`Spec ID`/`Result` instead of raising | Rejected in spec §6 and C2: a silent skip breaks the constitution §6 rule that template drift fails loudly. |
  | Index restarts per table, with the table ordinal added to the QACheck id | This changes the id scheme (out of scope, spec §6) and breaks byte-identity for single-table files. A running index meets AC-1.2 without either problem. |
- **Consequences:** Easier: Core's per-story `qa.md` files report every AC verified in them, and the later-table drift path is the same code as the first-table path. Harder: a non-verification table placed inside the verification section (e.g. an NFR table without an AC column) now raises `TemplateDriftError` where it used to be ignored. This is the intended, loud trade-off from C2, and R1 tracks it. MCP rendering of drift is unchanged: `server.build_graph` does not catch `TemplateDriftError`, so FastMCP returns it as a one-line tool error carrying `str(exc)`. Turning that into a structured result is BACKLOG G7 and is deliberately not done here (NFR-3: no new plumbing).

## 2. Affected Components

Source: own reading of `artifacts.py`, `build.py`, `cli.py`, `server.py`, `tests/test_artifacts.py`, `tests/test_current_names.py`. `constitution.md §9` was used for test practice and how to run. I re-derived the module facts from source under exception (a): this feature changes `artifacts.py` itself. No tool file was passed, so no blast-radius query was run and scoping was done by hand.

- `src/aspark_graph/artifacts.py`: new `_tables()`, and `_parse_qa` loops over it. No other function changes.
- `tests/test_artifacts.py`: new multi-table fixtures, written inline under `tmp_path` like the existing drift tests. These are pure `extract_features` calls with no confinement involved. CLI and MCP tests use a `.spark`-marked tmp repo (the marker is real, no bypass).
- `cli.py` / `server.py`: **no change**. The CLI already catches `TemplateDriftError` (`cli.py:174`). MCP surfaces it through FastMCP's tool-error path, as described in §1.
- Docs: `CLAUDE.md` (v0.7.1 known-limit line ~42, test count line ~247), `.spark/BACKLOG.md` (G6 marked done), `.spark/constitution.md` (§9 Known pain points plus an Amendments row, required by spec C6).
- No new dependencies, services or patterns. No version bump and no release files (C7: left to `/go-live`).

## 3. Task Breakdown

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | Walking skeleton: add `_tables()` and loop `_parse_qa` over it with a running index and per-table column checks | US-1 | AC-1.1, AC-1.2 | – | `todo` | `_tables` yields every separator-valid pipe run in document order and `_first_table` is unchanged (`git diff` shows no lines inside it). A new test builds a `qa.md` with three tables under `### US-1/2/3` (2 ACs each, plus one NFR row without an AC id in table 2). The test asserts 6 QACheck nodes, `gate_health(...)["unverified_acs"] == []` for passed rows, `order` strictly increasing across tables, no id collision, and the NFR row consuming an index (the next AC's `order` skips one). `uv run pytest` is green — files: src/aspark_graph/artifacts.py, tests/test_artifacts.py |
| T2 | Drift in a later table fails loudly in the parser, CLI and MCP | US-1 | AC-1.3, NFR-2, NFR-3 | T1 | `todo` | Two parametrised tests, where table 2 lacks the `AC`/`Spec ID` column and then the `Result` column. `extract_features` raises `TemplateDriftError` with `exc.file` ending in `qa.md` and the missing column named in `exc.mismatch`. `cli.main(["build", repo])` returns 1 with exactly one stderr line and no `Traceback`. Calling `server.build_graph(repo)` in process raises `TemplateDriftError` with the same `str(exc)` as the CLI line. The same tests pass for a legacy `qa-report.md` (C5) — files: tests/test_artifacts.py |
| T3 | Lock in the edge cases: prose between tables, separator-less run, empty section, later-table cell normalisation, single-table unchanged, multi-table double build | US-1 | AC-1.4, AC-1.5, AC-1.6, NFR-1 | T1 | `todo` | Tests assert the following. Prose, `###` headings and blank lines between tables are ignored. A pipe run without a separator followed by a real table yields only the real table's rows (C4). A section with no table yields 0 QACheck and no error. In table 3, `✅ pass`, `⚠️ … passed`, `❌ fail` and a cell with an escaped `\|` normalise to `pass`/`unknown`/`fail` with the pipe unescaped, as `_normalise_result` does for table 1. The existing single-table fixtures (`sample_repo`, `current_names_repo`) give the same QACheck ids and `order` values as before. Two builds of the multi-table fixture save byte-identical `graph.json` — files: tests/test_artifacts.py |
| T4 | Stash round-trip byte-identity against pre-change code (verification step, no code) | US-1 | AC-1.5, NFR-1 | T1, T2, T3 | `todo` | In a scratch `.spark`-marked dir, copy this repo's `.spark/`, `tests/fixtures/sample_repo` and `tests/fixtures/current_names_repo`. These cover both `qa.md` and legacy `qa-report.md`, all single-table. Fixed inputs are needed because the tool's own source changes, which would otherwise move this repo's code nodes. Build each under `git stash`ed (pre-change) code, then under the new code, and confirm with `cmp` that each pair of `graph.json` files is identical. Confirm that `git diff v0.7.3 <pre-change HEAD> -- src/aspark_graph/artifacts.py src/aspark_graph/build.py src/aspark_graph/graph.py src/aspark_graph/model.py` touches no graph-building code, so the baseline equals v0.7.3. Record the SHAs, the fixture list and the `cmp` results in the review evidence. `uv run pytest -m slow` passes (NFR-1 benchmark) — files: none (verification only, no repo file changes) |
| T5 | Docs: retire the G6 limit | US-1 | AC-1.1 | T4 | `todo` | In `CLAUDE.md`, the v0.7.1 line no longer says only the first QA table is read; it names `qa-multi-table` as having lifted it, and the `uv run pytest` test count matches the new suite. `.spark/BACKLOG.md` G6 is marked done, with a pointer to `.spark/qa-multi-table/`. In `.spark/constitution.md` §9, G6 is dropped from Known pain points and an Amendments row (2026-11-12, reason: spec C6) is added. A grep for `first QA verification table` and `G6` finds no stale claim. `uv run pytest` is green (doc-introspection tests included) — files: CLAUDE.md, .spark/BACKLOG.md, .spark/constitution.md |

## 4. Test Strategy

- **Unit (`tests/test_artifacts.py`, `extract_features` on `tmp_path` fixtures):** the multi-table happy path, with running index, `order` and NFR-row index use (T1). Drift in a later table for both missing columns, current and legacy file names (T2). Separator-less run, prose and headings, empty section, later-table marker and escaped-pipe normalisation (T3).
- **Integration:** `build_graph` → `gate_health`/`story_trace` on the multi-table fixture (T1). CLI `main(["build", …])` exit code and single stderr line, plus the in-process MCP `server.build_graph` raising the same message (T2). These use a real `.spark` marker and no confinement bypass. Multi-table double-build byte identity (T3).
- **Regression against old code:** the stash round-trip in T4 is the constitution §4 proof that single-table repos do not move. A double build only proves the new code agrees with itself.
- **Kept green:** the full default suite (403 tests plus the new ones) and `pytest -m slow` (NFR-1 benchmark, transport smoke, sdist manifest, fresh install).
- **Left to `/peer-review` (no `/demo-day`: headless, constitution §8):** build a scratch clone of Core and check the spec's success signal. project-kickoff should show 26 ACs, with no passed AC listed as unverified because of where its table sits. graph-gates, lean-artifacts and tracker-handoff should build without drift (this checks A1). Record the Core SHA and the per-file QACheck counts. This step is manual because it needs a network clone, and tests must stay offline.

## 5. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| R1 (inherits A1): a later table in a real Core `qa.md` has a different header, or a non-verification table (NFR, bug list) sits inside the section. The strict C2 check would then fail the **whole build** with `TemplateDriftError`, where today it under-counts silently. | High for affected repos: `gate_health` goes from wrong to unavailable until the file is fixed. This is the intended loud failure, but users will notice it. | The Core-clone check in `/peer-review` covers all 4 multi-table files before release. If one raises, the fix goes back to `/story-time` as a spec question. We do not loosen the check in code. The error names the file and the found header, so the fix is obvious to the author. |
| R2: MCP drift is a FastMCP tool error, not a structured dict (G7). Someone may read AC-1.3's "in CLI and MCP" as asking for new server plumbing. | Low. The message is the same one-line `str(exc)`, and nothing in it is new behaviour. | T2 asserts the MCP message equals the CLI text. The structured form stays in BACKLOG G7, and the plan records this reading (NFR-3: no new plumbing). |
| R3: the byte-identity baseline is the pre-change HEAD, while the spec says v0.7.3. | Low. A commit between the two that touched graph building would weaken AC-1.5. | T4 diffs the graph-building modules between v0.7.3 and the baseline. If they differ, T4 also builds under a v0.7.3 checkout. |
| R4: C4 changes behaviour for malformed files (a pipe run without a separator before a real table). | Low. Only files that are already broken are affected, and they now read more. | Covered by T3 and in scope by spec C4. AC-1.5 is limited to files with exactly one valid table. |
| R5: the same AC appears in two tables. | Low. You get two QACheck nodes, as with a duplicated row in one table today. Which one is "latest" follows `order` (document order). | Out of scope (spec §6). The running index keeps the ids distinct (T1). |

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
- [x] Line budget respected: Ist ~97 / Soll ~300 (excluding HTML comments) — self-reported, no linter checks this
- [x] Status set to `approved` by the user
