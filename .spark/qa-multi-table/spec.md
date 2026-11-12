# Spec: qa-multi-table

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (`/story-time`), Designer (`/look-and-feel`) |
| **Status** | `approved` |
| **Date** | 2026-11-12 |
| **Ticket** | #68 |
| **Gate comment** | none |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Summary:** `_parse_qa` reads only the first table under "Acceptance Criteria Verification", so per-story sub-tables (`### US-n`) lose every later AC as `unverified`; read every table in the section, byte-identical for single-table reports.
- **Open:** `none`
- **Binding ruling:** §4 User Stories for the current stories; §7 Clarifications for what changed since the last round and why
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Problem & Goal

- **Problem:** Some `qa.md` files split the `## … Acceptance Criteria Verification` section into one table per story (`### US-1`, `### US-2`, …). `_parse_qa` (`src/aspark_graph/artifacts.py`, via `_first_table`) reads only the first, so every AC after it shows as `unverified` in `gate_health` and `story_trace`. Silent undercounting, not drift. Measured in BACKLOG G6: 4 of 13 Core `qa.md` files (`graph-gates`, `lean-artifacts`, `project-kickoff`, `tracker-handoff`, 4-7 tables each). Felt by developers and agents on repos with such reports, who read a false "not verified" gate.
- **Goal:** every QA row under the section yields a `QACheck`, regardless of how many tables the section holds.
- **Success signal:** on a fixture with N per-story tables, `gate_health` and `story_trace` report the ACs of all N tables with their recorded results (zero falsely `unverified`); every single-table report builds a byte-identical `graph.json` to v0.7.3.
- **Why now:** it is the one open known limit of QA parsing (BACKLOG G6; constitution §9 pain points), and it distorts the headline question the tool exists to answer ("did its ACs pass QA?"). Fact source: `constitution.md §9` (known pain points); parser code re-read because the feature touches `_parse_qa`.

## 2. Target Users

- Developers and AI agents querying `gate_health`/`story_trace` on repos whose `qa.md` splits verification into per-story tables.

## 3. Assumptions & Open Questions

| # | Assumption / Question | Resolution |
|---|---|---|
| A1 | Issue wording is already a need, not a solution ("read all of them"). | Kept as stated. |
| A2 | Only tables inside the `## … Acceptance Criteria Verification` section count; the section ends at the next `#`/`##` heading, so `###` sub-headings stay inside it. | Existing `_section` behavior, unchanged. |
| A3 | A pipe block without a separator row is not a table and is ignored, as today. | Unchanged. |

## 4. User Stories

### US-1 (Must): Read every verification table in a QA report

> As a developer or agent querying `gate_health`/`story_trace`, I want every table under the Acceptance Criteria Verification section read, so that ACs verified in later per-story tables are not reported as unverified.

**Acceptance criteria:**

- [ ] AC-1.1: Given a `qa.md` whose verification section holds tables under `### US-1` and `### US-2` with AC rows in each, when the graph is built, then each AC row from both tables becomes a `QACheck` linked by `verifies` to its AC.
- [ ] AC-1.2: Given that report, when `gate_health` and `story_trace` run, then ACs from the second and later tables show their recorded result, not `unverified`.
- [ ] AC-1.3: Given a section with several tables, when the graph is built, then QACheck `index`/`order` values are continuous across tables in document order (the running count of all rows seen, starting at 0), so ids from `qacheck_id(feature, ac, index)` are unique and stable.
- [ ] AC-1.4: Given a `qa.md` with exactly one table under the section, when built, then `graph.json` is byte-identical to the one v0.7.3 produces (proven by stash round-trip on this repo's own trails and a fixture).
- [ ] AC-1.5: Given a pipe table located outside the verification section (e.g. under another `##` heading), when built, then none of its rows become QACheck nodes.

### US-2 (Must): Validate every table by the same drift rules

> As a maintainer, I want each verification table checked like the first one, so that a malformed sub-table fails loudly instead of being silently dropped.

**Acceptance criteria:**

- [ ] AC-2.1: Given a section whose second table has no `AC`/`Spec ID` column or no `Result` column, when built, then `TemplateDriftError` is raised naming the file and the missing column, and the CLI prints one line and exits non-zero (no traceback).
- [ ] AC-2.2: Given sub-tables whose headers differ but each satisfy the rules (e.g. one `AC`, one `Spec ID`), when built, then both are read.
- [ ] AC-2.3: Given a section with no table at all, when built, then it yields zero QACheck nodes and no error (unchanged).

## 5. Non-Functional Requirements

| # | Category | Requirement (measurable) | How it's verified |
|---|---|---|---|
| NFR-1 | Determinism | Double build of a multi-table fixture is byte-identical; single-table graphs equal pre-change output (stash round-trip). | /peer-review |
| NFR-2 | CLI contract (lens `cli`) | A drift error in any table is one line on stderr naming the file, exit non-zero, no traceback; CLI and MCP answers stay identical (change only in `artifacts.py`, no adapter logic). | /peer-review |
| NFR-3 | Reliability | Result-cell reading (marker-first, escaped `\|`) is applied identically to every table; full suite green (`uv run pytest`). | /peer-review |
| NFR-4 | Real-data evidence | Verified against a scratch clone of Core's four affected `qa.md` files, with SHA and AC counts recorded in `qa.md`. | /peer-review |
| NFR-5 | Security / Accessibility / Performance | N/A: no new file access or UI; reads the same already-bounded file once. | — |

## 6. Out of Scope

- Reading tables outside the Acceptance Criteria Verification section (e.g. NFR verification tables).
- Per-story table headings becoming graph data (`### US-n` is not used to attribute rows; the AC id in the row is authoritative).
- Tolerating a malformed sub-table by skipping it (rejected: honest failure over silent skip).
- Any change to `review.md` parsing (`_first_table` stays for findings).
- G7 (structured MCP drift result).

## 7. Clarifications

| # | Date | Question | Resolution |
|---|---|---|---|
| C1 | 2026-11-12 | Index across tables? | Continuous running row count across tables; single-table index unchanged (AC-1.3, AC-1.4). |
| C2 | 2026-11-12 | Sub-table with differing/non-matching header? | Each table validated by the same rules; a non-matching one raises `TemplateDriftError` naming the file (US-2). |
| C3 | 2026-11-12 | Tables not under the section? | Ignored (AC-1.5). |
| C4 | 2026-11-12 | Duplicate AC in two tables? | Both become QACheck nodes (distinct index), as duplicates within one table do today. |

## 8. Design Review

- N/A: headless CLI/MCP tool, no UI.

---

## ✅ SPEC GATE

- [x] Problem, goal and success signal are concrete (no buzzwords, no "everyone")
- [x] Every story has testable Given/When/Then acceptance criteria
- [x] Stories are prioritized (MoSCoW) and at least one is a Must
- [x] Non-functional requirements are stated and measurable (or marked N/A with reason)
- [x] Clarify pass done: no ambiguity left unresolved or unparked
- [x] Open questions are resolved or explicitly accepted as risk
- [x] Out-of-scope section is filled (something was consciously cut)
- [x] Constitution (`.spark/constitution.md`) respected, or conflicts recorded as open questions
- [x] Design review done for UI-facing features (or marked N/A with reason)
- [x] Line budget respected: Ist ~95 / Soll ~250 (excluding HTML comments) — self-reported, no linter checks this
- [x] Status set to `approved` by the user (gate pre-approved by the caller's recommended option)
