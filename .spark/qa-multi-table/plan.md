# Plan: qa-multi-table

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Engineering Manager (`/sprint-plan`) |
| **Input** | `.spark/qa-multi-table/spec.md` (`approved`, 2026-11-11) |
| **Status** | `approved` |
| **Date** | 2026-11-11 |

<!-- Handoff: read this block first, the numbered sections below by exception. Whoever
     writes to this plan updates it in the same edit that changes a task's status or
     the plan's own status: overwrite in place, never append. The block holds one
     current state, never a per-round log; a stale block is a defect, not a cosmetic
     issue. -->

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Summary:** `_all_tables` splits the QA verification section into contiguous pipe-blocks and reuses `_first_table` on each; `_parse_qa` checks drift per table and keeps one running row index across tables.
- **Open:** `none` — all tasks done
- **Binding ruling:** §3 Task Breakdown for current task status; a plan revision after review/QA findings updates §1/§3 in place, never a new section
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Architecture Decision

- **Context:** `_parse_qa` (`src/aspark_graph/artifacts.py`) calls `_first_table` on the `## … Acceptance Criteria Verification` section, so the per-story `### US-n` sub-tables used by 4 of the Core `qa.md` files are dropped silently (BACKLOG G6). `_section` already ends the section at the next `#`/`##` only, so `###` sub-tables already lie inside the block. The fix belongs entirely in the artifact parser: `queries.py`, `cli.py` and `server.py` read `QACheck` nodes and do not change (constitution.md §3 thin-adapter pattern, §9 module structure). Spec C1–C3 settle the index, header-drift and separator questions.
- **Decision:** Add `_all_tables(block)`. It cuts the section into maximal runs of pipe lines and passes each run to the **unchanged** `_first_table`, which keeps a run only if it has a separator row (C3). `_parse_qa` loops over the tables in document order. For **each** table it applies the existing id-column (`_qa_id_column`) and `Result` drift checks, with the same `TemplateDriftError` text. One `index` counter runs across all data rows of all tables (C1/NFR-2). With one table this produces exactly the old `enumerate` ids, so single-table graphs stay byte-identical (AC-3.1).
- **Alternatives considered:**
  | Alternative | Why rejected |
  |---|---|
  | Split the section at `###` headings and take the first table under each | Ties parsing to the heading layout. A second table with no heading of its own, or a table placed directly under `##`, would still be lost. Heading shape is not part of the template contract. |
  | Concatenate every table into one virtual table (union of headers) | Hides a sub-table with a different header. That is the drift case AC-2.1/C2 requires to fail loudly, and it breaks the "fail loudly on template drift" non-negotiable (constitution.md §6). |
  | Restart the row index per table and add the table number to the id (`#t.i`) | Changes the `QACheck` id scheme for **every** report, single-table ones included. That breaks AC-3.1 byte-identity and the downstream ids in `model.py:qacheck_id`. |
  | Rewrite `_first_table` as a general multi-table scanner | Every other artifact parser (spec, plan, review) uses `_first_table`, and impact reaches the `current-artifact-names` and `coverage-current-names` stories through `artifacts.py`. Changing that function widens the blast radius for no gain. A wrapper leaves those parsers untouched. |
- **Consequences:** Easier: a split-by-story `qa.md` now counts every AC. A drifting sub-table is now an error instead of being lost silently. Harder: a build that used to succeed **fails** when a later verification table has a non-QA header, e.g. a legend or environment table placed inside the section (R1). Pipe-tables inside a fenced code block in that section are now read too (R2). No new dependency, module, pattern or I/O.

## 2. Affected Components

- `src/aspark_graph/artifacts.py`: new `_all_tables`; `_parse_qa` loops over its tables. `_first_table`, `_section`, `_split_row`, `_col` and `_qa_id_column` are unchanged.
- `tests/test_qa_multi_table.py`: new suite, built on copies of `tests/fixtures/current_names_repo` in `tmp_path`. The fixture itself is not modified.
- Docs: `CLAUDE.md`, `.spark/BACKLOG.md` (G6 marked implemented), `.spark/constitution.md` §9 (known pain points).
- Unchanged: `queries.py`, `cli.py`, `server.py`, `model.py`. `story_trace` and `gate_health` consume the new nodes as they are.
- **Blast radius (graph `impact`, cited):** `impact` on the union of the §3 `files:` paths (`artifacts.py`, `tests/test_qa_multi_table.py`) reaches, all `declared`: `qa-multi-table` US-1/US-2/US-3, `current-artifact-names` US-1 (AC-1.1–1.4) and US-4 (AC-4.1–4.6), and `coverage-current-names` US-1 (AC-1.1–1.2). The other features' stories come in through shared `artifacts.py` helpers that this change leaves unchanged. Their suites (`tests/test_current_names.py` and the others) must stay green, and the reviewer's real-corpus probe re-checked them (T6). The `.md` paths are `unknown_files`: Markdown is not indexed, so I scoped the docs by hand with a grep for the old limit.
- Re-derived from source rather than taken from constitution.md §9: the `artifacts.py` parse path, because the feature touches that area (reason (a)).

## 3. Task Breakdown

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | Walking skeleton: `_all_tables` plus a `_parse_qa` loop over every table in the verification section | US-1 | AC-1.1, AC-1.3, NFR-1 | – | `done` | A split-table `qa.md` builds, and checks from the 2nd table appear as `QACheck` nodes. `_first_table` is unchanged, and no import or dependency is added — files: src/aspark_graph/artifacts.py |
| T2 | Tests: every sub-table reaches `story_trace`/`gate_health`; a table under a later `##` with an AC-shaped header is not read | US-1 | AC-1.1, AC-1.2, AC-1.3 | T1 | `done` | `test_every_subtable_is_read` fails on pre-T1 code and passes after. `test_tables_outside_the_section_are_not_read` keeps AC-1.2 unverified while an AC-1.2 `✅ pass` row sits outside the section (review F1) — files: tests/test_qa_multi_table.py |
| T3 | Per-table drift checks (id column, `Result` column) in the `_parse_qa` loop, plus a test for each | US-2 | AC-2.1 | T1 | `done` | A sub-table without `Result`, or without `AC`/`Spec ID`, raises `TemplateDriftError` with the same text as the first-table check. Both tests fail on pre-T1 code — files: src/aspark_graph/artifacts.py, tests/test_qa_multi_table.py |
| T4 | Tighten both drift tests so they assert the file is named, not only the column | US-2 | AC-2.1 | T3 | `done` | Each drift test asserts that `exc.file` ends with `.spark/demo/qa.md` and that the message names the missing column. The suite is green — files: tests/test_qa_multi_table.py |
| T5 | Running row index across tables, with tests for single-table ids and for the same AC in two tables | US-3 | AC-3.1, NFR-2 | T1 | `done` | `test_single_table_unchanged_checks` shows identical `qa:` ids for a single-table report. `test_running_index_keeps_same_ac_in_two_tables_distinct` shows two ids and `latest_result == "pass"`. A per-table index reset fails that test (review F2) — files: src/aspark_graph/artifacts.py, tests/test_qa_multi_table.py |
| T6 | Real-corpus probe: `_parse_qa` over every Core `qa.md` under `/opt/aspark/.spark`, old code vs new code | US-1 | AC-1.1, AC-1.3 | T3 | `done` | Recorded in review.md §4: 34 files; 30 identical; 4 gained checks only (graph-gates, lean-artifacts, project-kickoff, tracker-handoff); 0 new `TemplateDriftError` |
| T7 | Determinism proof at the **final** HEAD against `main` code (`dd4b994`). The review's proof ran at `2706861`, before the F2 fix and before this trail's own `review.md`/`qa.md` existed | US-3 | AC-3.1, NFR-1 | T4, T5 | `done` | `build --full` of this repo under a `dd4b994` worktree and under HEAD gives `cmp`-identical `graph.json`. Both sha256 values and the HEAD SHA are recorded under AC-3.1 in this feature's `qa.md`. `uv run pytest` is green and the count is noted |
| T8 | Remove statements of the old first-table-only limit from the docs | US-4 | AC-4.1 | T1 | `done` | A grep of the repo `*.md` (excluding historical trails) for "first QA"/"first table"/"only the first" finds no current statement of the limit. BACKLOG G6 is marked implemented — files: CLAUDE.md, .spark/BACKLOG.md, .spark/constitution.md |

## 4. Test Strategy

- **US-1 (Must):** integration tests through `build_graph` and `queries` on a `tmp_path` copy of `current_names_repo` with a rewritten §2 (T2). They exercise the real build → graph → query path, the same one the CLI and MCP use. The CLI↔MCP parity test covers adapter identity, so no adapter test is added. Real-corpus probe (T6) per the CLAUDE.md "read a wide set of real files" rule.
- **US-2 (Must):** two negative integration tests, one per missing column, made to assert the file name as well (T3, T4). The one-line CLI rendering of `TemplateDriftError` already has its own tests and is unchanged.
- **US-3 (Must):** an id-equality unit check (T5), plus the constitution.md §4 proof against pre-change code (T7, worktree round-trip). A double build alone does not prove AC-3.1. The existing byte-identical double-build test stays.
- **US-4 (Should):** a grep over the docs, recorded in QA. No automated test, because the claim is about wording and a denylist test would be out of proportion for one sentence.
- **NFR-1:** no new import in the diff, and T7 shows the output is deterministic. **NFR-2:** T5's two-tables test.
- **Not in `/demo-day`:** headless tool (constitution.md §8). The QA-equivalent is hands-on CLI work. The slow tests (sdist, transport, bench, fresh install) are untouched by this diff and run at release per constitution.md §4.

## 5. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| R1: A later table in the verification section has a non-QA header (legend, environment) | A build that used to pass now fails with `TemplateDriftError`. That is intended (C2), but it is a user-visible behaviour change | T6: no Core `qa.md` trips it. `/go-live` must name it in the release notes as a behaviour change |
| R2: A fenced code block in the section holds an example pipe-table | It is now parsed. That gives drift if the header differs, or phantom checks if the header matches. `_all_tables` does not track fences | None of the 34 Core files does this (T6). Accepted as a known limit; record it in BACKLOG if it ever shows up |
| R3: A sub-table without a separator row is skipped (C3) | That table's ACs are under-counted silently, as before | Spec decision C3, unchanged behaviour; noted, not fixed |
| R4: This trail's own `qa.md` gets rewritten into per-story sub-tables before release | The repo-level AC-3.1 proof (T7) breaks, because the old code would read less of it | Keep `.spark/qa-multi-table/qa.md` a single table until shipped (same spirit as the CLAUDE.md v0.7.1 old-names rule). Run T7 last |
| R5: Shared `artifacts.py` helpers reach two other features' stories (impact, §2) | A regression in `current-artifact-names` or `coverage-current-names` parsing | The helpers are unchanged. Their suites are part of `uv run pytest`, and T6 compares the full corpus |
| R6 (inherited): the Story cell links only the **first** story of a multi-story cell | Earlier rows listing "US-1, US-2, US-3" gave US-2 and US-3 no task links in `story_trace` | One story per row in §3 |

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
- [x] Line budget respected: Ist 91 / Soll ~300 (excluding HTML comments)
- [x] Status set to `approved` by the user
