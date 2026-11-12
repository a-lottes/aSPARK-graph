# Plan: qa-multi-table

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Engineering Manager (`/sprint-plan`) |
| **Input** | `.spark/qa-multi-table/spec.md` (must be `approved`) |
| **Status** | `approved` |
| **Date** | 2026-11-12 |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Summary:** new `_tables` helper (all pipe-tables in the section, same parse rules as `_first_table`); `_parse_qa` loops over them with one running row index and validates each table's header; `_first_table` untouched for tasks/findings. Change confined to `artifacts.py`.
- **Open:** `7 tasks not done` — see §3 Task Breakdown for which
- **Binding ruling:** §3 Task Breakdown for current task status; a plan revision after review/QA findings updates §1/§3 in place, never a new section
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Architecture Decision

- **Context:** `_parse_qa` (`src/aspark_graph/artifacts.py`) takes the section from `_section(lines, "acceptance criteria verification")` and reads only `_first_table(section, unescape_pipes=True)`. `_section` already ends at the next `#`/`##`, so `### US-n` sub-tables are inside the section — the parser simply stops after the first table. `_first_table` is also used by the plan task table and review findings parsers, which must not change (spec §6). Fact sources: stack and module structure from `constitution.md §9`; `artifacts.py` re-read because the feature touches it (§9 reason (a)). Own trails checked: every `.spark/*/qa*.md` holds exactly one table in its verification section (the second tables in `aspark-graph`, `current-artifact-names`, `shallow-clone-warning` sit under `## 3.`), so AC-1.4 on this repo is expected to hold byte-for-byte.
- **Decision:** Add `_tables(block, unescape_pipes=False) -> list[dict]` next to `_first_table`: it splits `block` into contiguous pipe-line runs and returns, in document order, every run that has a header plus a separator row, built exactly as `_first_table` builds one (same `_split_row`, same padding, same lower-cased keys). `_parse_qa` calls `_tables(section, unescape_pipes=True)`, validates each table's header with the existing two drift checks (moved into a small `_check_qa_header(path, table)`), and enumerates rows with one counter that runs across tables (`index` = rows seen so far, skipped NFR rows included, exactly as today's `enumerate`). Zero tables returns 0 as today. No adapter, model, query or dependency change.
- **Alternatives considered:**
  | Alternative | Why rejected |
  |---|---|
  | Reimplement `_first_table` as `_tables(...)[0]` | Not equivalent: today a first pipe block without a separator makes `_first_table` return `None` (it never looks further). Changing it would silently alter plan/review parsing, which is out of scope (spec §6). |
  | Split the section on `###` headings and call `_first_table` per sub-section | Couples parsing to heading layout the spec explicitly does not use (§6); misses two tables under one heading or tables with no sub-heading. |
  | Per-table index restarting at 0 (id includes a table number) | Changes `qacheck_id` shape and so every single-table graph — violates AC-1.4 / C1. |
  | Skip a later table that fails the header rules | Rejected by spec (§6, C2): honest failure over silent skip; constitution §6 "drift fails loudly". |
- **Consequences:** Easier: per-story QA reports count fully; one helper serves any future "all tables" need. Harder: a section that today has a stray non-QA table after the first (e.g. a notes table) now raises `TemplateDriftError` where it used to be ignored — intended by US-2, but a new failure mode on real repos (see §5). Narrow behaviour change also intended: a section whose *first* pipe block is not a table but a later one is, now yields that later table's rows (today: 0).

## 2. Affected Components

- `src/aspark_graph/artifacts.py` — new `_tables`, new `_check_qa_header`, `_parse_qa` loop. `_first_table`, `_section`, `_split_row`, `_normalise_result`, `_qa_id_column` unchanged.
- `tests/test_artifacts.py` — unit tests for `_tables`.
- `tests/test_current_names.py` — build-level tests built from a tmp copy of `tests/fixtures/current_names_repo` (existing `_copy_repo` helper) with its `qa.md` rewritten into per-story tables; no new fixture directory.
- Not touched: `cli.py`, `server.py`, `queries.py`, `model.py` (NFR-2: CLI/MCP parity is free because only the parser changes; `TemplateDriftError` already flows through the existing exception seam).
- No new dependency, service or pattern.
- Blast radius: no tool file was passed; scoped by hand from the code and the callers of `_first_table` (lines 211, 252, 284).

## 3. Task Breakdown

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | Add `_tables(block, unescape_pipes=False)` returning every separator-validated pipe table in document order, same row/padding/key rules as `_first_table` | US-1 | AC-1.1, AC-2.3, NFR-3 | – | `todo` | Unit tests pass for: two tables separated by a `### US-2` line -> 2 dicts with correct headers/rows; a pipe block without separator row is skipped and a following real table still returned; empty block -> `[]`; `unescape_pipes=True` keeps an escaped `\|` inside its cell in a later table; `_first_table` and its callers are unchanged (diff shows no edit to it) — files: src/aspark_graph/artifacts.py, tests/test_artifacts.py |
| T2 | Walking skeleton: `_parse_qa` iterates `_tables(section, unescape_pipes=True)` with one running index; extract `_check_qa_header(path, table)` holding today's two drift checks and call it per table | US-1, US-2 | AC-1.1, AC-1.2, AC-1.3, AC-2.2 | T1 | `todo` | Test on a tmp copy of `current_names_repo` whose `qa.md` section is rewritten to `### US-1` (header `Spec ID`, rows AC-1.1, AC-1.2) and `### US-2` (header `AC`, rows AC-2.1, NFR-1): every AC has a `verifies` edge, `gate_health(...)["unverified_acs"] == []`, `story_trace("US-2")` shows AC-2.1 `latest_result == "pass"`, QACheck `order` values are `[0, 1, 2]` for AC rows with the NFR row consuming index 3, all `qacheck_id`s unique; `uv run pytest` green — files: src/aspark_graph/artifacts.py, tests/test_current_names.py |
| T3 | Drift on a malformed later table, with CLI one-line contract | US-2 | AC-2.1, NFR-2 | T2 | `todo` | Two parametrized tests: second table lacks the id column / lacks `Result` -> `build_graph` raises `TemplateDriftError` whose message names the `qa.md` path and the missing column; CLI `build` on the same repo exits non-zero with exactly one stderr line and no `Traceback` — files: tests/test_current_names.py |
| T4 | Scope and empty-section guards | US-1, US-2 | AC-1.5, AC-2.3 | T2 | `todo` | Tests: a well-formed AC table placed under `## 5. Verdict` yields no QACheck for its rows (count of QACheck nodes unchanged vs. without it); a section with prose only and no table yields 0 QACheck nodes and no error — files: tests/test_current_names.py |
| T5 | Single-table regression in the suite | US-1 | AC-1.4, NFR-1 | T2 | `todo` | Test: the unmodified `current_names_repo` QACheck ids/order/result equal the values asserted before the change (pinned literals), and a double build of the multi-table tmp repo from T2 produces byte-identical `graph.json`; existing byte-identical double-build test still green — files: tests/test_current_names.py |
| T6 | Determinism proof against pre-change code (stash round-trip) | US-1 | AC-1.4, NFR-1 | T5 | `todo` | With changes stashed, `uv run aspark-graph build --full` on this repo and on `tests/fixtures/current_names_repo` (copies outside the tree); `git stash pop`, rebuild; `cmp` of each pair of `graph.json` reports identical. Commands, HEAD SHA and sha256 of each pair recorded as an `Evidence` bullet in §4 of this plan — files: .spark/qa-multi-table/plan.md |
| T7 | Real-data check on Core's four affected `qa.md` files | US-1, US-2 | AC-1.2, NFR-4, NFR-3 | T2 | `todo` | Scratch clone of Core outside the repo; for `graph-gates`, `lean-artifacts`, `project-kickoff`, `tracker-handoff`: build succeeds (or a `TemplateDriftError` is raised and logged as a §5 risk hit for the PO), and per feature the number of ACs with a QA result before vs. after the change is recorded; Core SHA and counts recorded as an `Evidence` bullet in §4 of this plan (QA copies them into `qa.md`) — files: .spark/qa-multi-table/plan.md |

## 4. Test Strategy

- **US-1 (Must):** unit tests on `_tables` (T1) in `tests/test_artifacts.py`; integration tests through `build_graph` + `queries.gate_health`/`story_trace` on a tmp copy of the current-names fixture (T2, T4, T5) in `tests/test_current_names.py`. Determinism: in-suite double build (T5) plus the stash round-trip against pre-change code (T6), as the constitution §4 requires for output-perturbing changes.
- **US-2 (Must):** integration tests for drift on a later table, for both missing columns, and the CLI one-line/exit-code contract (T3); mixed `AC`/`Spec ID` headers read (T2).
- **Real data:** T7 on Core's four affected files (NFR-4), recorded with SHA and counts.
- **`/demo-day`:** N/A — headless tool; QA-equivalent runs in `/peer-review` (constitution §8).
- **Trail naming:** this feature does not change which files are read, so the old-names rule does not apply — but this feature's own `qa.md` must keep a single verification table until shipped, or the AC-1.4 own-repo round-trip compares unlike inputs.
- **Evidence:** (filled by T6, T7)

## 5. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| A real report has a non-QA table (notes, legend) inside the verification section after the first table | Builds that passed on v0.7.3 now fail with `TemplateDriftError` | Intended by US-2/C2; T7 measures it on Core's four files. A hit goes back to the PO as a spec question, not a silent skip. Own trails checked: none affected. |
| First pipe block in section is not a table, a later one is | Rows now read where v0.7.3 read none — a graph change outside the "single table" guarantee | Accepted; not a single-table report, so AC-1.4 is not violated. Named in §1 Consequences for the reviewer. |
| Index semantics drift (e.g. counting only AC rows) | All single-table ids change, AC-1.4 broken | One `enumerate`-equivalent counter over all rows; T5 pins literal ids, T6 proves against old code. |
| Code-fenced pipe examples inside the section | Read as tables (already true for the first table today) | Unchanged behaviour; out of scope. |
| Inherited A2/A3 (section boundary, separator rule) | Both are existing behaviour | T1/T4 tests pin them. |

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
- [x] Line budget respected: Ist ~80 / Soll ~300 (excluding HTML comments) — self-reported, no linter checks this
- [x] Status set to `approved` (Factory autonomous mode selected the recommended option at the plan gate)
