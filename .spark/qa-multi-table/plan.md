# Plan: qa-multi-table

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Engineering Manager (`/sprint-plan`) |
| **Input** | `.spark/qa-multi-table/spec.md` (`approved`, 2026-11-12) |
| **Status** | `approved` |
| **Date** | 2026-11-12 |

## 1. Architecture Decision

Add `_tables(block, unescape_pipes)` to `artifacts.py`. It yields one entry per run of contiguous pipe lines in a block: the parsed `{header, rows}` dict, or `None` when the run is not a real table (fewer than 2 rows or no separator). `_first_table` becomes "the first entry `_tables` yields, else `None`", so plan and review parsing behave exactly as before, including a malformed first run that hides a later table. `_parse_qa` loops over every valid table in the section (`_section` already runs through `###` subheadings). The first valid table keeps today's strict checks: no AC/Spec ID column or no Result column raises `TemplateDriftError`. A later table without an id column (`_qa_id_column` returns `None`) is skipped as a notes table. A later table that has an id column but no Result column raises drift, naming the file and the table's position.

The QACheck index runs across tables: each table's offset is the sum of the data-row counts of the tables read before it. A skipped table does not move the offset. With one table the offset is 0, so `qacheck_id` and `order` stay byte-identical. Across tables ids are unique and `order` follows document order, so `_sorted_qa`/`_latest_qa` in `queries.py` need no change.

Rejected alternatives:
- Restart `index` per table and put a table number in the id. This breaks AC-1.3 uniqueness unless `qacheck_id` changes, and changing the id format would perturb every single-table graph (AC-2.1).
- Merge every pipe line in the section into one table. A notes table with different columns would be read with the wrong header, and the drift check could no longer tell a notes table from a broken verification table.
- Change `_first_table` to skip a malformed first run. That would silently change plan and review parsing, which the spec does not cover.

Consequences: a `qa.md` whose first pipe run is malformed but which has a valid later table now produces checks (before, it produced 0). That is in scope (AC-1.1), but it is a behaviour change for an odd input, so R2 tracks it. No new dependency, module or pattern.

## 2. Affected Components

`src/aspark_graph/artifacts.py` (`_tables` new, `_first_table` and `_parse_qa` changed), plus new tests and `.spark/BACKLOG.md`. `queries.py`, the adapters and `model.py` do not change. I scoped this by hand by reading `artifacts.py`, `queries.py` (`_sorted_qa`) and `model.qacheck_id`; the aspark-graph MCP tools were not available in this planning session. System facts come from `constitution.md §9` (module structure, test practice). I re-read the parser source itself because the feature touches that area (reason (a)). `README.md` does not state the limit (I grepped for `table`/`qa.md`; the only hits are the artifact-name table), so it is not touched. `CLAUDE.md` and `constitution.md §9` still name G6 as a known limit. Those are not in this increment's file set; they are left for `/go-live` to update.

## 3. Task Breakdown

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | Add `_tables`; reimplement `_first_table` on top of it. | US-2 | AC-2.1 | – | `todo` | Existing suite green with no test edits. New unit tests check that `_tables` yields every table in order, yields `None` for a malformed run, and that `_first_table` still returns `None` when the first run is malformed even though a valid table follows — files: src/aspark_graph/artifacts.py, tests/test_qa_multi_table.py |
| T2 | `_parse_qa` loops over all tables with a running index; strict first table, skip later tables without an id column, drift for a later table with an id column but no Result column. | US-1, US-2 | AC-1.1, AC-1.3, AC-2.2 | T1 | `todo` | Tests on a `### US-n` multi-table fixture: one QACheck per AC row of every table, each with a `verifies` edge. Ids are unique, and an AC listed in two tables has both checks in document order. A notes table is skipped. A later table missing Result raises `TemplateDriftError` naming the file. First-table drift tests in `test_current_names.py` still pass — files: src/aspark_graph/artifacts.py, tests/test_qa_multi_table.py |
| T3 | Query-level verdicts from later tables. | US-1 | AC-1.2 | T2 | `todo` | A test builds the fixture repo (with a `.git` marker) and asserts that `gate_health` counts a later-table AC as verified (pass), and that `story_trace` shows that AC's `latest_result`, including a fail in a later table — files: tests/test_qa_multi_table.py |
| T4 | Byte-identity proof against pre-change code. | US-2 | AC-2.1 | T2 | `todo` | `git stash` round-trip: build this repo plus `tests/fixtures/current_names_repo` under the old code and the new code; `diff` of the two graph.json files is empty. Commands and SHA are recorded in the review. The double-build test is still green. No file changes. |
| T5 | Mark BACKLOG G6 done. | US-3 | AC-3.1 | T2 | `todo` | The G6 entry carries a done marker naming `qa-multi-table` and the version — files: .spark/BACKLOG.md |

## 4. Test Strategy

- US-1: unit and build-level tests in the new `tests/test_qa_multi_table.py`, using a tmp `.git`-marked repo with a per-story `qa.md`. These cover node count, id uniqueness, order, and `gate_health`/`story_trace` verdicts.
- US-2: the existing `test_artifacts.py`/`test_current_names.py` QA tests are the regression net and stay unedited. New drift cases are added for later tables. The stash round-trip (T4) is the byte-identity proof the constitution requires, because a double build alone cannot show this.
- Hands-on in `/peer-review`: build a scratch clone of one Core per-story report (e.g. `graph-gates`) and confirm its later ACs read verified.
- `/demo-day` is N/A (headless).

## 5. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| R1: The running index perturbs single-table ids | AC-2.1 broken on every repo | The offset is 0 for the first table by construction. The T4 stash diff proves it. |
| R2: The first pipe run is malformed but a later valid table exists | Checks appear where there were none | In scope (AC-1.1). A test pins the behaviour, and `_first_table` callers are unaffected. |
| R3: A later table uses a different but valid header (e.g. `Spec ID` after `AC`) | Mis-read column | The id column is resolved per table with `_qa_id_column`, not reused from the first table. |
| R4: Real Core per-story reports have shapes not seen in fixtures | Silent undercount persists | Hands-on read of the four Core reports named in G6 during `/peer-review`. |

## ✅ PLAN GATE

- [x] Every Must AC (AC-1.1–1.3, AC-2.1–2.2) has a task; the Should AC-3.1 is covered by T5.
- [x] Every DoD is yes/no checkable; `files:` notes are only on tasks with knowable files.
- [x] No new dependency, service or pattern.
- [x] Line budget: about 50 lines (Ist) against the compact csharp-support format (Soll: same shape, under 60).

Approved (autonomous line, gate pre-approved by the caller).
