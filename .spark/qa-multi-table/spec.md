# Spec: qa-multi-table

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (`/story-time`) |
| **Status** | `approved` |
| **Date** | 2026-11-12 |

## 1. Problem & Goal

- **Problem:** Some `qa.md` files split "Acceptance Criteria Verification" into one table per story (`### US-1`, `### US-2`, …). `_parse_qa` reads only the first table, so every later AC shows as unverified in `gate_health` and `story_trace` (BACKLOG G6, issue #72).
- **Goal:** Read every table in the section (issue #72, autonomous line: the issue text is the approved scope).
- **Out of scope:** tables outside the Acceptance Criteria Verification section; changing result-cell reading rules.

## 2. User Stories & Acceptance Criteria

### US-1 (Must): All verification tables are read

- [ ] AC-1.1: Given a `qa.md` whose verification section holds several tables (e.g. under `### US-n` subheadings), when built, then a `QACheck` node exists for every AC row of every table, each verifying its AC.
- [ ] AC-1.2: `gate_health` and `story_trace` report ACs from later tables with their real verdicts, not unverified.
- [ ] AC-1.3: QACheck ids stay unique across tables, and an AC verified in several tables keeps every check in document order.

### US-2 (Must): Single-table reports are unchanged

- [ ] AC-2.1: For a `qa.md` with one table, the built graph.json is byte-identical to the pre-change build (existing trails as proof).
- [ ] AC-2.2: Missing AC/Result column in the first table still raises `TemplateDriftError`; a later table without an AC id column (a notes/summary table) is skipped, not an error; a later table with an id column but no Result column raises drift.

### US-3 (Should): Documented

- [ ] AC-3.1: The "only first table read" known limit is removed from docs (CLAUDE.md-independent: README/BACKLOG G6 marked done).
