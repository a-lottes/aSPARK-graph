# Plan: qa-multi-table

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Orchestrator (`/sprint-plan`, condensed) |
| **Input** | `spec.md` (`approved`, 2026-11-11) |
| **Status** | `approved` |
| **Date** | 2026-11-11 |

## 1. Architecture Decision

Add `_all_tables(block)` in `artifacts.py`: split the section into contiguous pipe-line chunks and run the existing `_first_table` on each. `_parse_qa` loops over the tables, validates headers per table (drift), and keeps one running row index for QACheck ids.

Rejected: (a) regex per `###` heading — misses tables outside sub-headings and ties parsing to heading shape; (b) concatenating tables into one — hides per-table header drift.

## 2. Affected Components
`src/aspark_graph/artifacts.py`; tests; docs (`CLAUDE.md`, `.spark/constitution.md`, `.spark/BACKLOG.md`). `queries.py`, `cli.py`, `server.py` unchanged.

## 3. Task Breakdown

| # | Task | Story | Covers | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | `_all_tables` + multi-table `_parse_qa` with per-table drift and running index | US-1, US-2, US-3 | AC-1.1, AC-2.1, NFR-2 | — | `done` | suite green — files: src/aspark_graph/artifacts.py |
| T2 | Tests: sub-tables read, story_trace/gate_health, drift per table, other sections ignored, single-table ids | US-1, US-2, US-3 | AC-1.2, AC-1.3, AC-2.1, AC-3.1 | T1 | `done` | new tests fail before T1, pass after — files: tests/test_qa_multi_table.py |
| T3 | Update docs that state the old limit | US-4 | AC-4.1 | T1 | `done` | no doc says first table only — files: CLAUDE.md |

## 4. Test Strategy
Unit tests on fixtures copied to tmp; full suite; byte comparison of graph.json old vs new code on this repo.

## 5. Risks
R1: a trail whose later tables have a different header now fails the build (intended, AC-2.1).
