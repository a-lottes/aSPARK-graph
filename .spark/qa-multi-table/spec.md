# Spec: qa-multi-table

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (`/story-time`), Designer (`/look-and-feel`) |
| **Status** | `approved` |
| **Date** | 2026-11-12 |
| **Ticket** | #74 |
| **Gate comment** | skipped, gh not available |

<!-- Handoff: read this block first, the numbered sections below by exception. Whoever
     writes to this spec updates it in the same edit that resolves a clarification or
     changes status: overwrite in place, never append. The block holds one current
     state, never a per-round log; a stale block is a defect, not a cosmetic issue. -->

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Summary:** qa.md files that split "Acceptance Criteria Verification" into one table per story only have their first table read, so later ACs show as unverified. Read every table in the section; single-table output stays byte-identical.
- **Open:** `none`
- **Binding ruling:** §4 User Stories for the current stories; §7 Clarifications for what changed since the last round and why
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Problem & Goal

- **Problem:** `_parse_qa` (`src/aspark_graph/artifacts.py`) reads only the first pipe-table under `## … Acceptance Criteria Verification`. 4 of 13 Core `qa.md` files (graph-gates, lean-artifacts, project-kickoff, tracker-handoff; 4-7 tables each, `### US-n` sub-headings) split it per story. Every AC after the first table is reported unverified by `gate_health` and `story_trace`; project-kickoff yields 6 QACheck for 26 ACs. No error is raised: a silent under-count, which breaks "honest absence" (constitution §1) in the wrong direction. Source: `.spark/BACKLOG.md` G6, issue #74 (`constitution.md §9` Known pain points).
- **Goal:** every verification table in that section contributes its rows as QACheck nodes.
- **Success signal:** on a qa.md with N tables, `gate_health`/`story_trace` count every AC row across all N tables (a fixture test, plus a check on a scratch clone of Core's project-kickoff: 26 ACs, no passed AC listed unverified because of table position).
- **Why now:** it is the one accepted, documented Major (B2) still shipping, and it hides real QA results from agents using the gate.

## 2. Target Users

- Developers and AI agents who run `gate_health`/`story_trace` on repos whose `qa.md` (or legacy `qa-report.md`) uses per-story tables, notably Core's `.spark/` trails.

## 3. Assumptions & Open Questions

| # | Assumption / Question | Resolution |
|---|---|---|
| A1 | Per-story tables share the same column conventions as the first table (an `AC`/`Spec ID` column and a `Result` column). Verified only from the BACKLOG description, not re-read from Core files here. | Accepted risk. Strict drift check (AC-1.3) makes a violation loud, not silent; QA checks it against a Core clone. |
| A2 | The idea arrived as "read all of them", which is already the need, not a solution. Original phrasing kept. | none needed |

## 4. User Stories

### US-1 (Must): Read every QA verification table

> As a developer or agent querying `gate_health`/`story_trace`, I want all verification tables in a qa.md's "Acceptance Criteria Verification" section read, so that ACs verified in a later per-story table are not reported as unverified.

**Acceptance criteria:**

- [ ] AC-1.1: Given a qa.md whose verification section holds three tables (under `### US-1`, `### US-2`, `### US-3`) with AC rows in each, when the graph is built, then every row with an `AC-n.m` id in any table becomes a QACheck node, and `gate_health` reports those ACs with their table's result instead of unverified.
- [ ] AC-1.2: Given the same qa.md, when QACheck ids are generated, then the row `index` keeps counting across tables in document order (rows without an AC id still consume an index, as today), so no two QACheck ids collide and the node `order` attribute is strictly increasing.
- [ ] AC-1.3: Given a verification section where a later table has a header and separator row but no `AC`/`Spec ID` column, or no `Result` column, when the graph is built, then it raises `TemplateDriftError` naming the file and the missing column, surfaced as a one-line message with non-zero exit (no traceback) in CLI and MCP.
- [ ] AC-1.4: Given prose, headings or blank lines between tables, when the graph is built, then they are ignored and only pipe-tables with a separator row are read; a section with no table still yields 0 QACheck without error.
- [ ] AC-1.5: Given any qa.md or legacy qa-report.md with exactly one verification table, when the graph is built with this change vs. pre-change code (v0.7.3), then `graph.json` is byte-identical.
- [ ] AC-1.6: Given result cells in a later table (`✅`, `⚠️ … passed`, `❌`, an escaped `\|`), when read, then they normalise exactly as in the first table (marker-first, pipes unescaped).

## 5. Non-Functional Requirements

| # | Category | Requirement (measurable) | How it's verified |
|---|---|---|---|
| NFR-1 | Determinism | Double build of a multi-table fixture is byte-identical; single-table fixtures and this repo's own `.spark/` trails build byte-identical to v0.7.3 via stash round-trip (build under old code, then new, diff). | /peer-review |
| NFR-2 | Reliability | Drift in any table fails loudly naming the file; no silent skip. Existing 403-test suite stays green; NFR-1 incremental benchmark (slow) stays passing. | /peer-review |
| NFR-3 | CLI lens | The drift error is one line on stderr, non-zero exit, no traceback, same text via MCP edge (existing exception-to-adapter seam; no new plumbing). | /peer-review |
| NFR-4 | Security & privacy | N/A: no new input surface; same file read under existing confinement and 5 MB cap. | — |
| NFR-5 | Accessibility / observability | N/A: headless, no new logging. | — |

## 6. Out of Scope

- `_first_table` callers for review findings (lines ~211, ~252): they keep first-table behavior; multi-table there is a separate feature if ever needed.
- Merging or de-duplicating the same AC appearing in two tables: each row stays its own QACheck, as within a single table today.
- Tolerating a later table with a different header shape (skipping instead of raising): rejected, silent skip contradicts the constitution.
- Any change to result normalisation, the id-column choice rules, or the QACheck id scheme.
- Reading tables outside the "Acceptance Criteria Verification" section (e.g. summary or bug tables).

## 7. Clarifications

| # | Date | Question | Resolution |
|---|---|---|---|
| C1 | 2026-11-12 | Does `index` restart per table? | No: continues across tables in document order and counts rows without an AC id, matching today's single-table `enumerate`. Prevents id collisions (AC-1.2). |
| C2 | 2026-11-12 | Later table with a different or missing header column? | Raise `TemplateDriftError` per table, same checks as the first (AC-1.3). Chosen over skipping for the constitution's fail-loudly rule. Risk: a non-verification table inside the section would now raise; A1 and QA's Core-clone check cover it. |
| C3 | 2026-11-12 | Prose between tables? | Ignored (AC-1.4). Only blocks with a pipe header plus separator row count as tables. |
| C4 | 2026-11-12 | Pipe block without separator row, followed by a real table? | Today: first block fails, 0 rows. New: such a block is not a table and is skipped, the later real table is read. Only malformed files change; byte-identity (AC-1.5) is scoped to files with exactly one valid table. |
| C5 | 2026-11-12 | Legacy `qa-report.md`? | Same parser, same behavior. |
| C6 | 2026-11-12 | Docs? | Must be updated in the same change: remove/replace the "only the first QA verification table per qa.md is read (BACKLOG G6)" limit in `CLAUDE.md` (v0.7.1 summary line ~42), mark BACKLOG G6 done, update the constitution §9 "Known pain points" mention, and check README for any equivalent statement (none found by grep). |
| C7 | 2026-11-12 | Release/version? | Not decided here; left to `/go-live`. Spec trail is written under the current artifact names (`review.md`/`qa.md`), since this feature adds reading, not new file names. |

## 8. Design Review

N/A: headless tool, no UI.

---

## ✅ SPEC GATE

*All boxes checked → `/sprint-plan` may start. Any box open → back to `/story-time` or `/look-and-feel`.*

- [x] Problem, goal and success signal are concrete (no buzzwords, no "everyone")
- [x] Every story has testable Given/When/Then acceptance criteria
- [x] Stories are prioritized (MoSCoW) and at least one is a Must
- [x] Non-functional requirements are stated and measurable (or marked N/A with reason)
- [x] Clarify pass done: no ambiguity left unresolved or unparked
- [x] Open questions are resolved or explicitly accepted as risk
- [x] Out-of-scope section is filled (something was consciously cut)
- [x] Constitution (`.spark/constitution.md`) respected, or conflicts recorded as open questions
- [x] Design review done for UI-facing features (or marked N/A with reason)
- [x] Line budget respected: Ist ~85 / Soll ~250 (excluding HTML comments) — self-reported, no linter checks this
- [x] Status set to `approved` by the user
