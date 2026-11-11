# Plan: qa-multi-table

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Engineering Manager (`/sprint-plan`) |
| **Input** | `.spark/qa-multi-table/spec.md` (must be `approved`) |
| **Status** | `approved` |
| **Date** | 2026-11-11 |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Summary:** Add `_all_tables` to `artifacts.py` (`_first_table` becomes a wrapper), loop `_parse_qa` over every table with a running row index and per-table column validation. Tests in `tests/test_current_names.py`; docs updated.
- **Open:** `none`. T1–T3 done; increment record at the end.
- **Binding ruling:** §3 Task Breakdown for current task status.
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Architecture Decision

- **Context:** `_first_table` stops at the first table. Review/plan parsers rely on it and must not change (scope, byte identity).
- **Decision:** a new `_all_tables(block, unescape_pipes)` returns every pipe table; `_first_table` returns its first element. `_parse_qa` iterates all tables, validates the header of each, and numbers rows with one running index. Rows are counted whether or not they carry an AC, as before, so a single table keeps its ids.
- **Rejected alternatives:** (1) restart the index per table: QACheck ids would collide for equal ACs across tables. (2) Skip tables lacking the columns: contradicts the issue and re-creates silent under-counting. (3) Change `_first_table` itself to return a list: touches review/plan parsing.

## 2. Affected Components

- `src/aspark_graph/artifacts.py` only. `queries.py`, `cli.py`, `server.py` untouched.

## 3. Task Breakdown

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | Multi-table QA parsing: `_all_tables`, `_parse_qa` loop with running index and per-table drift check | US-1, US-2 | AC-1.1, AC-1.3, AC-2.1, AC-2.2, NFR-2 | – | `done` | Fixture with `### US-1` (AC header) and `### US-2` (Spec ID header) tables gives QACheck for both; a table in another section gives none; a sub-table without Result or AC/Spec ID raises drift naming the file. Full suite green — files: src/aspark_graph/artifacts.py |
| T2 | Tests for multi-table reading and both drift cases | US-1, US-2 | AC-1.1, AC-1.3, AC-2.1, AC-2.2 | T1 | `done` | Three tests in tests/test_current_names.py pass; `gate_health` shows the later-table AC as verified/unverified per its result — files: tests/test_current_names.py |
| T3 | Docs: drop the first-table limit | US-3 | AC-3.1 | T1 | `done` | CLAUDE.md, constitution and BACKLOG G6 no longer state the limit as current — files: CLAUDE.md, .spark/constitution.md, .spark/BACKLOG.md |
| T4 | Old-code regression sweep (no code change) | US-1 | AC-1.2, NFR-1 | T1 | `done` | Single-table inputs (this repo, sample_repo, current Core-style fixture) built under the pre-change commit and the new code give 0 graph.json byte diffs; multi-table fixture builds twice byte-identical. Recorded in review.md |

## 4. Test Strategy

Unit/integration tests build the `demo` fixture with a rewritten `qa.md`. Regression: pre-change worktree vs new code, byte compare. Real-repo check: build this repo (dogfood) and run `gate_health`.

## 5. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| A real report has a non-QA table (legend) in the section | New drift error for a repo that built before | Intended by the issue; named file + column in the message |
| Index change alters ids | Graph diff for single tables | Index counts rows exactly as before; T4 proves it |

---

## ✅ PLAN GATE

- [x] Spec status is `approved`
- [x] Architecture decision includes rejected alternatives
- [x] Architecture respects the constitution's technical constraints
- [x] Every task maps to a user story
- [x] Every Must AC and every applicable NFR is covered by at least one task
- [x] Every task has a checkable definition of done
- [x] Task order respects dependencies
- [x] Test strategy covers every Must story
- [x] Line budget respected
- [x] Status set to `approved` (autonomous mode: recommended option taken)

## Increment record (for `/peer-review`)

- Code: commit 6681ded (`artifacts.py`, tests, docs). 390 passed, slow tests not yet run.
- Deviation: the code was written before this trail existed (process slip, corrected by writing spec and plan afterwards). T4 run: this repo (all trails, single-table qa files) built under `6681ded~1` (git worktree) and under the new code, both on a `.git`-marked copy of the tracked files: graph.json `cmp` identical (607251 bytes).
