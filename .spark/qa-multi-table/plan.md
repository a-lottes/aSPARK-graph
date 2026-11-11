# Plan: qa-multi-table

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Engineering Manager (`/sprint-plan`) |
| **Input** | `.spark/qa-multi-table/spec.md` (must be `approved`) |
| **Status** | `approved` |
| **Date** | 2026-11-11 |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Summary:** `_parse_qa` loops over `_all_tables(section)`. Each table's header is validated on its own, and one row index runs across all tables. `_first_table` keeps its exact pre-G6 "first pipe block only" semantics through the shared `_pipe_groups`/`_as_table` split. The only change is in `artifacts.py`. This revision adds the sub-table locator to the drift message (review F3 / QA B1), a C3 guard test and a re-verification pass.
- **Open:** `3 tasks not done` (T5, T6, T7). See §3 Task Breakdown.
- **Binding ruling:** §3 Task Breakdown for current task status. A plan revision after review/QA findings updates §1/§3 in place, never a new section.
- **On conflict:** the numbered body below wins for everything except `Status`. Log the mismatch as a finding at the next `/peer-review` and proceed. Don't stop on it.

## 1. Architecture Decision

- **Context:** `_parse_qa` read only `_first_table` of the `## … Acceptance Criteria Verification` section. 4 of 13 Core reports split that section into `### US-n` tables (BACKLOG G6), so later ACs read as unverified with no warning. `_section` already ends the block at the next `#`/`##` heading, which keeps `###` sub-tables inside it (spec A1; read in `artifacts.py:346`). `_parse_plan` (:211) and `_parse_review` (:252) share `_first_table`, and spec §6 keeps them first-table only. This revision was planned after the fact: the code (6681ded, then d761e9f after review r1) existed before this trail. The sequence is recorded here and was accepted in review §2.
- **Decision:** Split table reading into `_pipe_groups` (consecutive `|…|` lines as cell lists) and `_as_table` (a group becomes `{header, rows}`, or `None` when the separator row is missing). `_first_table` = `_as_table` of the **first group only**, which keeps the pre-G6 behaviour byte for byte. `_all_tables` = every group that is a table, in order (C3: non-tables are skipped). `_parse_qa` validates **each** table's id column (`_qa_id_column`) and `Result` column before it reads that table's rows, and raises `TemplateDriftError` on the first bad table. A single `index` counts every data row across tables, with or without an AC (C1), so single-table ids and `order` values are unchanged. **Revision (F3):** when the section has more than one table, the drift mismatch ends with `(table <n> of <m>, under '<heading>')`. `<heading>` is the nearest preceding `###`-or-deeper heading line inside the section; the `under` clause is dropped when there is none. A single-table message is left unchanged character for character. To find the heading, `_all_tables` tags each table dict with a `heading` key, taken from a heading-tracking walk inside `_pipe_groups`'s loop. The heading is never added to `_first_table`'s result.
- **Alternatives considered:**
  | Alternative | Why rejected |
  |---|---|
  | Restart the row index per table | QACheck ids (`qa:<f>:<AC>#<i>`) would collide when one AC appears in two tables, and later rows would lose their order. C1 rules it out. |
  | Skip a table that lacks the AC/Result columns | This is the same silent under-count that G6 exists to fix. C2 and the issue rule it out, and it contradicts constitution §6 ("never silently skipped"). |
  | Make `_first_table` return a list, or "first *valid* table" | This would change `_parse_review`/`_parse_plan` on edge inputs: a non-table first block would promote a later table. That was review F1 (Major), and the split into `_pipe_groups`/`_as_table` is the fix. |
  | Parse markdown with a library (markdown-it-py, mistune) | It adds a dependency that changes parsing. The repo's own pipe-splitting carries the C14 escaped-pipe rule, and a library could split differently, which would break byte identity (AC-1.2). About 30 lines of our own code are cheaper than that liability. |
  | F3: locate the bad table by file line number | `_section` returns lines without their file offset, so this needs offset plumbing through a helper shared with plan/review parsing. The `### US-n` heading plus the ordinal is what an author searches for anyway. |
  | F3: leave the message as is (QA accepted B1 as Minor) | US-2's story asks for a malformed sub-table to be *named*. Today the message names the file and column only, and a long split report gives no pointer. The fix is cheap and stays inside `artifacts.py`. |
- **Consequences:** Split QA reports now give honest `gate_health`/`story_trace` figures. Single-table graphs are unchanged. Any non-QA table inside the verification section (for example a legend) is now drift, where before it was ignored. This is intended (C2) and was checked against 34 real Core `qa.md` files with 0 hits (review §5). `_pipe_groups` is now a shared seam: a change there affects plan, review and QA parsing at once, and the guard test `test_g6_first_table_never_promotes_a_later_block` protects it. Behaviour change on an edge input (spec C3): if a non-table pipe block (e.g. a one-cell `| note |` line) comes *before* the QA table, old code stopped at that block (review F1 probe). New code skips it and reads the table. The graph for such a report is therefore not byte-identical to v0.7.3. See the question in §5.

## 2. Affected Components

- `src/aspark_graph/artifacts.py`: `_parse_qa`, `_first_table`, `_all_tables`, `_pipe_groups`, `_as_table`. Nothing else in `src/` (NFR-2). `queries.py`, `cli.py` and `server.py` are untouched, so CLI≡MCP parity holds without extra work. `TemplateDriftError` already reaches the CLI edge at `cli.py:170`, and the new message text passes through it unchanged.
- `tests/test_current_names.py`: the G6 tests, plus the T5/T6 additions.
- Docs: `CLAUDE.md`, `.spark/constitution.md` §9, `.spark/BACKLOG.md` G6 (US-3).
- No new dependency, service or pattern. Parse-affecting pins are unchanged. Artifacts are not in the parse cache (`build.py:176` calls `extract_features` on every build), so cache invalidation is not a concern.
- **Blast radius:** The `impact` query was **requested and not run** by the planner, because this session exposes no `impact` tool. The ceremony should run it on the union of the indexed `files:` paths, `src/aspark_graph/artifacts.py` and `tests/test_current_names.py` (the Markdown paths are not indexed). Until then, the scope above was **set by hand**: I read the three callers of the table helpers (`artifacts.py:211`, `:252`, `:284`), the single entry point (`extract_features` ← `build.py:176`) and both adapters' error handling. I did not re-derive anything from constitution §9: its system facts (thin adapters, test practice) match what I read, and none of conditions (a)–(c) applied beyond the files this feature touches, which I read directly.

## 3. Task Breakdown

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | Multi-table QA parsing: `_pipe_groups`/`_as_table` split, `_first_table` = first group only, `_all_tables`, `_parse_qa` loop with running index and per-table column check | US-1, US-2 | AC-1.1, AC-1.3, AC-2.1, AC-2.2, NFR-2 | – | `done` | A fixture with a `### US-1` table (`AC` header) and a `### US-2` table (`Spec ID` header) yields a QACheck for each AC row of both. A table under another `##` gives none. A sub-table without a `Result` column, or without an `AC`/`Spec ID` column, raises `TemplateDriftError` naming the file and the column. `_first_table` returns `None` for a non-table first block even when a table follows. Full suite green — files: src/aspark_graph/artifacts.py |
| T2 | Tests for multi-table reading, id continuity, both drift cases and the `_first_table` guard | US-1, US-2 | AC-1.1, AC-1.3, AC-2.1, AC-2.2 | T1 | `done` | The five `test_g6_*` tests in tests/test_current_names.py pass. `test_g6_later_table_pass_counts_as_verified_and_ids_run_on` fails under `6681ded~1` (it discriminates) — files: tests/test_current_names.py |
| T3 | Docs: drop the first-table limit as a current claim | US-3 | AC-3.1 | T1 | `done` | CLAUDE.md, constitution §9 and BACKLOG G6 no longer state "only the first QA table is read" as current behaviour. A grep for the phrase finds it only in historical trails — files: CLAUDE.md, .spark/constitution.md, .spark/BACKLOG.md |
| T4 | Old-code regression sweep (no code change) | US-1 | AC-1.2, NFR-1 | T1 | `done` | `graph.json` built under `6681ded~1` (git worktree) and under the new code, `--full`, on `.git`-marked copies, is `cmp`-identical for this repo, `tests/fixtures/sample_repo` and `tests/fixtures/current_names_repo`. The multi-table fixture builds twice byte-identical. Evidence: review.md §4 (AC-1.2, NFR-1) |
| T5 | Drift message names the bad sub-table (review F3 / QA B1) | US-2 | AC-2.1, AC-2.2 | T1 | `todo` | With 2 or more tables in the section, a bad table's mismatch ends with `(table <n> of <m>, under '<heading>')`. `<heading>` is the nearest preceding `###`+ line inside the section; the `under` clause is dropped when no heading exists. Tests: a bad second table in `SPLIT_QA` gives a message containing `table 2 of 2` and `### US-2` (both drift kinds). The single-table drift message equals the pre-change string exactly (assert `==` in `test_qa_table_with_neither_ac_nor_spec_id_is_drift`). `_first_table`'s return value has no `heading` key, and `test_g6_first_table_never_promotes_a_later_block` stays green — files: src/aspark_graph/artifacts.py, tests/test_current_names.py |
| T6 | Pin the C3 edge: a non-table pipe block before the QA table is skipped, not fatal | US-1 | AC-1.1 | T1 | `todo` | A test whose verification section holds a one-cell pipe line with no separator row, then a QA table, builds without drift and yields the table's QACheck with `order` 0. The test docstring records that this input differs from v0.7.3 output (plan §1 Consequences) — files: tests/test_current_names.py |
| T7 | Re-verify after T5/T6 (no code change) | US-1, US-2 | AC-1.2, NFR-1, NFR-2 | T5, T6 | `todo` | `uv run pytest` is green and `uv run pytest -m slow` passes 4/4. The T4 `cmp` round-trip is re-run against `6681ded~1` for the same three inputs, with 0 byte diffs. `git diff --stat 6681ded~1..HEAD -- src` lists only `src/aspark_graph/artifacts.py`. Results are recorded at the next `/peer-review` |

## 4. Test Strategy

- **US-1 (Must):** Integration tests build the `current_names_repo` fixture (`_copy_repo`, `.git`-marked, no confinement bypass) with a rewritten `qa.md`. They assert QACheck ACs/results/`order` and the `gate_health` `unverified_acs` (T2, T6). Each multi-table test must fail under pre-change code, or it proves nothing (F2's lesson). Determinism: the existing byte-identical double-build test, plus T4/T7's old-code worktree round-trip on three inputs, which is the CLAUDE.md non-negotiable and not only a double build.
- **US-2 (Must):** Integration tests per drift kind on a *second* table, asserting `exc.value.file` and the column in `mismatch` (T2), plus the locator and the unchanged single-table string (T5). A unit test pins `_first_table`'s semantics directly (T2).
- **US-3 (Should):** A grep check in T3. No test, because the claim is prose.
- **Real-file evidence:** review §5 already parsed all 34 Core `qa.md` files under `/opt/aspark/.spark/` (4 gained checks, 0 drift). If T5 touches `_pipe_groups`, T7 should repeat that sweep.
- **Left to `/demo-day`:** nothing browser-based (headless, constitution §8). The QA-equivalent is the CLI and in-process-MCP run recorded in `qa.md`. After T5, rerun its AC-2.2 step to see the new message on the CLI.

## 5. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| A real report keeps a non-QA table (legend, summary) inside the verification section | A repo that built under v0.7.3 now fails with drift | Intended (C2). The message names the file and column, and after T5 also the sub-table. The 34-file Core sweep found 0 such cases. |
| **Spec tension, AC-1.2 vs C3** (question for the PO): a single QA table preceded by a non-table pipe block gave the old "first block only" result and now reads the table | That input's graph is not byte-identical to v0.7.3 | The plan follows C3, the explicit clarification, and the more honest count. T6 pins the behaviour. The PO should confirm or narrow AC-1.2 to "single pipe block". No real Core file hits it (review §5). |
| A change to the shared `_pipe_groups` (T5 heading tracking) leaks into plan/review parsing | A silent change to review/plan graphs, the same class as F1 | Track headings in a separate return path used only by `_all_tables`. The guard test and T7's three-input `cmp` sweep cover plan and review tables too. |
| Index semantics drift (e.g. counting only AC rows) | Ids change for single tables | `index` increments before the AC match, exactly as before. Covered by the T4/T7 byte comparison. |
| Pre-existing, out of scope: MCP `build_graph` (`server.py:25-28`) catches `RepoRefused` but not `TemplateDriftError` | Drift over MCP reaches the client as a raw tool error, not a clean dict. This includes the new multi-table drift. | Not changed here (NFR-2: adapters untouched). Recommend a BACKLOG entry using the existing exception→adapter seam. |

---

## ✅ PLAN GATE

*All boxes checked → `/increment` may start. Any box open → back to `/sprint-plan`.*

- [x] Spec status is `approved` (never plan against a draft)
- [x] Architecture decision includes rejected alternatives (a decision without alternatives is a guess)
- [x] Architecture respects the constitution's technical constraints (or a conflict is recorded): no new dep, adapters untouched, drift stays loud, old-code round-trip required
- [x] Every task maps to a user story — no orphan tasks, no story without tasks
- [x] Every Must AC and every applicable NFR is covered by at least one task (NFR-3 N/A per spec)
- [x] Every task has a checkable definition of done
- [x] Task order respects dependencies
- [x] Test strategy covers every Must story
- [x] Line budget respected: Ist 74 / Soll ~300 (excluding HTML comments)
- [x] Status set to `approved` by the user (autonomous mode: recommended option taken, T5 approved; C4 added to spec)
