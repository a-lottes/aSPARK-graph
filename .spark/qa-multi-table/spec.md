# Spec: qa-multi-table

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (`/story-time`) |
| **Status** | `approved` |
| **Date** | 2026-11-11 |
| **Ticket** | #44 (seeded from the issue text supplied by the Factory; BACKLOG G6) |
| **Gate comment** | skipped, no GitHub CLI in this environment |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Summary:** `_parse_qa` reads only the first table under `## … Acceptance Criteria Verification`. Several aSPARK Core `qa.md` files split that section into `### US-n` sub-tables, so every AC after the first table reads as unverified, silently. Goal: read every table of that section; each must carry an AC/`Spec ID` and a `Result` column or it is template drift. A single-table report builds a byte-identical graph. Target: next patch release (version bump belongs to `/go-live`).
- **Open:** `none`. Autonomous run: details decided from the issue and CLAUDE.md (C1–C3).
- **Binding ruling:** §4 User Stories; §7 Clarifications.
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Problem & Goal

- **Problem:** `artifacts.py::_parse_qa` calls `_first_table`. 4 of 13 Core `qa.md` files (BACKLOG G6: `graph-gates`, `lean-artifacts`, `project-kickoff`, `tracker-handoff`) put one table per story under `### US-n`. All ACs verified after the first sub-table show as `unverified` in `gate_health` and `story_trace`. No error, no hint: honest-looking, wrong numbers.
- **Goal:** `story_trace` and `gate_health` see the QA checks of every table in the verification section. A table that cannot be read is named as template drift, never skipped.
- **Success signal:** a `qa.md` with a `### US-1` and a `### US-2` table yields QA checks for the ACs of both; a single-table `qa.md` yields the same graph.json bytes as before.
- **Why now:** open since v0.7.1 (B2/G6); it makes the QA gate figures wrong for real Core repos.

## 2. Target Users

- **Agent or reviewer running `gate_health` / `story_trace`** on a repo whose QA report is split by story.

## 3. Assumptions & Open Questions

| # | Assumption / Question | Resolution |
|---|---|---|
| A1 | The verification section ends at the next `#`/`##` heading, so `###` sub-headings stay inside it (existing `_section` rule). | accepted |
| A2 | QACheck ids carry a row index; across tables the index continues, so ids stay unique and a single table keeps today's ids. | accepted (C1) |

## 4. User Stories

### US-1 (Must): Every QA table in the verification section is read

> As an agent asking `gate_health` or `story_trace`, I want the QA checks of every table in the verification section, so that ACs verified in a later `### US-n` sub-table are not reported as unverified.

**Acceptance criteria:**

- [ ] AC-1.1: Given a `qa.md` whose verification section holds two or more tables (for example one per `### US-n`), when the graph is built, then a QACheck exists for each AC row of every table, and `gate_health` counts an AC verified in a later table as verified.
- [ ] AC-1.2: Given a `qa.md` whose verification section holds a single table and no other pipe block, when the graph is built, then graph.json is byte-identical to the one built by the previous release.
- [ ] AC-1.3: Given tables in other sections of `qa.md`, when the graph is built, then they contribute no QACheck.

### US-2 (Must): Every table must be a QA table

> As a maintainer, I want a malformed sub-table named, so that nothing is silently under-counted again.

**Acceptance criteria:**

- [ ] AC-2.1: Given a table in the verification section with no `AC` or `Spec ID` column, when the graph is built, then a `TemplateDriftError` names the file and the missing column.
- [ ] AC-2.2: Given a table in the verification section with no `Result` column, when the graph is built, then a `TemplateDriftError` names the file and the missing column.

### US-3 (Should): The old limit is no longer documented

> As a reader, I want docs to match behaviour.

**Acceptance criteria:**

- [ ] AC-3.1: Given the repo docs, when searched for the "only the first QA table is read" limit, then `CLAUDE.md`, `.spark/constitution.md` and `.spark/BACKLOG.md` no longer state it as current.

## 5. Non-Functional Requirements

| # | Category | Requirement (measurable) | How it's verified |
|---|---|---|---|
| NFR-1 | Reliability / determinism | Two builds of a multi-table fixture are byte-identical; single-table graphs equal the previous release's, proven against pre-change code (`git stash`/worktree round-trip), not only a double build. | tests + /peer-review |
| NFR-2 | Architecture | The change lives in `artifacts.py` only; adapters and `queries.py` are untouched (CLI≡MCP parity free). | /peer-review |
| NFR-3 | Performance / accessibility | N/A: headless; parsing is linear in the section size. | – |

## 6. Out of Scope

- Reading tables of other sections, or tables in `review.md` (still first-table only).
- Any column-name aliasing beyond today's `AC` / `Spec ID` rule.
- Version bump and release.

## 7. Clarifications

| # | Date | Question | Answer |
|---|---|---|---|
| C1 | 2026-11-11 | How are QACheck ids numbered across tables? | The row index runs on across tables (counting every row, as today), so a single table is unchanged. |
| C2 | 2026-11-11 | A table in the section that is not a QA table (e.g. a legend)? | The issue says every table there must carry the columns; it is drift. |
| C3 | 2026-11-11 | A pipe block without a separator row? | Not a table, skipped, as `_first_table` did. |
| C4 | 2026-11-11 | (Plan revision) A non-table pipe block before the only QA table: old code recorded no checks, new code (C3) reads the table. | Accepted, a deliberate fix of the same silent under-count. AC-1.2 is narrowed to a section with one table and no other pipe block. No real Core `qa.md` hits this (34 files scanned in review). |

## 8. Design Review

- **Overall impression:** N/A. Headless tool, no UI.

---

## ✅ SPEC GATE

- [x] Problem, goal and success signal are concrete
- [x] Every story has testable Given/When/Then acceptance criteria
- [x] Stories are prioritized (MoSCoW) and at least one is a Must
- [x] Non-functional requirements are stated and measurable (or marked N/A with reason)
- [x] Clarify pass done: no ambiguity left unresolved or unparked
- [x] Open questions are resolved or explicitly accepted as risk
- [x] Out-of-scope section is filled
- [x] Constitution respected (determinism, thin adapters, fail loudly on drift)
- [x] Design review N/A: no UI
- [x] Status set to `approved` (autonomous mode: recommended option taken)
