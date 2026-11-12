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
- **Summary:** New `_tables()` helper returns every pipe-table in a block; `_first_table` delegates to it, unchanged. `_parse_qa` loops over all tables in the verification section: the first table stays strict, later non-verification tables are skipped, and the QA-check index keeps counting across tables. Single-table output stays byte-identical.
- **Open:** `none` — all tasks done
- **Binding ruling:** §3 Task Breakdown for current task status; a plan revision after review/QA findings updates §1/§3 in place, never a new section
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Architecture Decision

- **Context:** `_parse_qa` (`src/aspark_graph/artifacts.py:279`) reads only `_first_table(section, unescape_pipes=True)`. `_first_table` collects the first run of `|…|` lines, stops at the first non-pipe line, and returns `None` if there is no separator row. `_section` ends only at `#`/`##`, so `### US-n` sub-tables already sit inside the section (spec A1). QA-check ids are `qacheck_id(feature, ac, index)`, where `index` comes from `enumerate` over **all** data rows of that table, including skipped non-AC rows, and `order=index`. The constitution binds us to these: byte-identical rebuild (§6), loud `TemplateDriftError` (§6), and stash round-trip proof for output-affecting changes (§4).
- **Decision:**
  1. Add `_tables(block, unescape_pipes=False) -> list[dict | None]`. It splits `block` into consecutive pipe-line runs and parses each one with today's shape logic. A run without a separator row comes back as `None`.
  2. `_first_table` becomes `runs[0] if runs else None`. That is exactly today's semantics, including "first run malformed → None", so the plan/review/QA callers are unaffected.
  3. `_parse_qa` treats the **first run** as today: `None` → return 0, and a missing id or Result column raises `TemplateDriftError` with the unchanged message.
  4. Later runs are skipped silently when they are `None`, `_qa_id_column` is `None`, or they have no `result` header.
  5. `index` is a single running counter. It advances once per data row of every accepted table, in file order, exactly as `enumerate` does today within one table. Single-table files therefore get identical ids and `order`, and ids never collide across tables.
  6. A repeated AC across tables produces two checks. The later check has the higher `order`, so it is the "latest" result, the same as repeated rows today (AC-1.5). No change to `queries.py`.
- **Alternatives considered:**
  | Alternative | Why rejected |
  |---|---|
  | Merge all tables into one synthetic table (concatenate rows under the first header) | Silently mis-maps columns when later headers differ (e.g. a bug table). It also hides which table a row came from, so A2's per-table skip can't be expressed. |
  | Strict on every table (drift error on any later table lacking AC/Result) | Rejected by spec C1/A2. Real Core `qa.md` files place summary and bug tables in the section, so this would turn today's silent undercount into a build failure for those repos. |
  | Per-table index namespace (`qa:<f>:<ac>#<table>.<row>`) | Changes every existing QA-check id, which breaks AC-1.3 byte identity. A running counter gives uniqueness for free. |
  | First *valid* table is strict (skip malformed leading pipe runs) | Could turn a file that builds today (first run malformed → 0 checks) into a new drift error. Mirroring today's "first run governs" guarantees no file goes from building to failing. |
- **Consequences:** Easier: per-story QA layouts in Core work with no template change, and G6 closes. Harder: a later table that is really a mis-headed verification table is skipped silently. This is accepted by spec A2 and documented in a test. The QA check count rises for affected repos, which is intended.

## 2. Affected Components

- **System facts** come from `constitution.md §9` (module structure; the `artifacts.py` parser is behind the thin adapters). Rule (a) applied: the feature touches the parser, so `artifacts.py:279-404` was re-read from source; the facts in §1 Context come from there.
- `src/aspark_graph/artifacts.py`: `_tables` (new), `_first_table` (delegates), `_parse_qa` (loop). No changes to `queries.py`, `cli.py`, `server.py` or `model.py`.
- `tests/test_qa_multi_table.py` (new): fixture built in `tmp_path` with its own `.git` marker (confinement rule, no bypass).
- `.spark/BACKLOG.md`: mark G6 resolved. `README.md` does not mention the first-table limit (grep: no match), so it is untouched. The G6 "known limit" note in `CLAUDE.md` is left to the release ceremony.
- No new dependencies, services or patterns.
- Blast-radius query: no tool file was passed, so the work was scoped by hand.

## 3. Task Breakdown

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | Add `_tables` helper, make `_first_table` delegate to it, and loop `_parse_qa` over all tables (strict first run, lenient later runs, running index) | US-1 | AC-1.1, AC-1.2, AC-1.4, AC-1.5, NFR-2 | – | `done` | Existing `uv run pytest` is fully green with no test edits (proves `_first_table` behaviour and single-table output are unchanged). A multi-table `qa.md` built locally yields one QA check per AC row across all tables. No new exception type: the only raise is the existing `TemplateDriftError` on the first table — files: src/aspark_graph/artifacts.py |
| T2 | Multi-table tests | US-1 | AC-1.1, AC-1.2, AC-1.4, AC-1.5, NFR-1 | T1 | `done` | New tests pass: (a) a 3-table `### US-n` fixture gives every AC a QA check with its recorded result; (b) `gate_health` and `story_trace` report the second/third-table ACs as their result, not `unverified`; (c) a first table without an AC/Spec ID column, and one without a Result column, each raise `TemplateDriftError`; (d) a later bug table without those columns is skipped with no error and adds no checks; (e) the same AC in tables 1 and 3 gives two checks, and the table-3 result is the latest; (f) ids/`order` run continuously and are unique; (g) a double build of the fixture is byte-identical. The fixture lives in `tmp_path` with a `.git` marker — files: tests/test_qa_multi_table.py |
| T3 | Pre- vs post-change determinism proof (manual stash round-trip) | US-1 | AC-1.3, NFR-1 | T1 | `done` | Build `tests/fixtures/current_names_repo` (single-table `qa.md`) and the repo itself under pre-change code (`git stash`), then under post-change code. `diff` of each graph.json pair is empty. Commands, HEAD SHA and the diff result are recorded in the T3 commit message / review evidence |
| T4 | Mark BACKLOG G6 resolved | US-1 | AC-1.1 | T2 | `done` | The G6 heading in `.spark/BACKLOG.md` carries a resolved marker naming `qa-multi-table`, in the file's existing (German) style, and no other entry changes — files: .spark/BACKLOG.md |

Walking skeleton: T1 alone is runnable end-to-end (`aspark-graph build` on a multi-table repo shows the new checks via `gate_health`).

## 4. Test Strategy

- **Unit (T2):** parser-level assertions on the graph from `build`: QA-check nodes, ids, `order`, `result`, and `verifies` edges for every table; strict first table; lenient later tables; a repeated AC.
- **Integration (T2):** `queries.gate_health` and `queries.story_trace` on the fixture (AC-1.2), plus a byte-identical double build (NFR-1). CLI/MCP parity needs no new test because no adapter changes, and the existing parity suite stays green.
- **Regression (T1, T3):** the full existing suite unchanged, plus the stash round-trip on a single-table fixture and on the live repo (constitution §4).
- **Real-repo check at `/peer-review`:** build a scratch clone of Core and confirm that the 4 multi-table `qa.md` files (G6: `graph-gates`, `lean-artifacts`, `project-kickoff`, `tracker-handoff`) now report their later ACs. Record the SHA and counts (CLAUDE.md "read a wide set of real files").
- **`/demo-day`:** N/A (headless tool, constitution §8).

## 5. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| This feature's own `qa.md` uses several tables, so the shipped tool reads it differently from v0.7.3 and the repo-level byte-identity proof is void | AC-1.3 proof on the live repo breaks | Keep this trail's QA verification as **one** table. T3 diffs the live repo too. |
| A later table is a real verification table with an unusual header (e.g. `Criterion`) and is skipped silently | Undercount persists for that layout | Accepted per spec A2. T2(d) pins the behaviour. The Core clone check at `/peer-review` surfaces real headers. |
| Index semantics drift (e.g. counting only AC rows) changes single-table ids | Byte identity lost | T1 keeps `enumerate`-equivalent counting over all data rows. Pre-existing tests and T3 catch any drift. |
| A first pipe run that is malformed while later tables are valid still yields 0 checks | Rare undercount | Deliberate (§1 alternative 4): no new drift failures. Revisit only on a real report. |
| Inherited A1: content after a `#`/`##` heading is outside the section | Tables under a stray `##` are not read | Out of scope (spec §6). |

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
- [x] Line budget respected: Ist 74 / Soll ~300 (excluding HTML comments)
- [x] Status set to `approved` by the user

## Deviations

- T3: on the live repo the pre/post graph.json differ only by the two new `def:` nodes (`_tables`, `_parse_run`) and their edges from the changed source itself; no QA/artifact node or edge changed. `tests/fixtures/current_names_repo` is byte-identical.
- `_parse_run` split out of `_tables` as a small helper (same logic as the old `_first_table` body).
