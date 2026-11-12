# QA Report: qa-multi-table

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review (hands-on) |
| **Owner** | QA Tester (`/demo-day`) |
| **Input** | CLI (`aspark-graph build` / `query gate_health`), `.spark/qa-multi-table/spec.md` |
| **Status** | `passed` |
| **Round** | 1 |
| **Date** | 2026-11-12 |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Verdict:** Yes, demoable. Headless tool: no browser; QA-equivalent run on the CLI, with the byte-identity and Core-clone evidence in `review.md` §2.
- **Open:** `none` — Blockers: none; Majors: none
- **Binding ruling:** §5 Verdict and the gate checklist below
- **On conflict:** the numbered body below wins for everything except `Status`.

## 1. Test Environment

- **App URL:** none (headless). `uv run aspark-graph` from `factory/issue-74`, scratch `.git`-marked repo with a two-table `qa.md`.
- **Browser:** N/A. `/demo-day` is structurally N/A for this repo (CLAUDE.md); QA gate is overridden to the CLI equivalent. Authorizer: project CLAUDE.md. Reason: no UI.

## 2. Acceptance Criteria Verification

| AC | Result | Evidence |
|---|---|---|
| AC-1.1 | ✅ pass | Scratch repo, AC-1.1 in table 1 and AC-1.2 in table 2, both passed: `gate_health` gives `unverified_acs: []`. |
| AC-1.2 | ✅ pass | Tests assert running index and strictly increasing `order`; review confirmed. |
| AC-1.3 | ✅ pass | CLI returns 1 with one stderr line; MCP raises the same text (tested, `qa.md` and `qa-report.md`). |
| AC-1.4 | ✅ pass | Prose, headings, separator-less run and no-table cases tested. |
| AC-1.5 | ✅ pass | `cmp` identical against v0.7.3 on 3 fixtures (`review.md` §2 T4). |
| AC-1.6 | ✅ pass | Marker-first and escaped-pipe cells in a later table tested. |

## 3. Exploratory Findings

None. The Core clone at `2c84ad5` builds the four multi-table files without drift (project-kickoff 6→26 checks); see `review.md`.

## 4. Console & Network

N/A, headless. Suite: 416 passed.

## 5. Verdict

`passed`. No bugs found; no open findings.

- [x] Every Must AC verified
- [x] No open Blocker or Major bugs
