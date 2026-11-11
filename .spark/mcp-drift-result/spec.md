# Spec: mcp-drift-result

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (`/story-time`), Designer (`/look-and-feel`) |
| **Status** | `approved` |
| **Date** | 2026-11-11 |
| **Ticket** | #42 (spec seeded from it; BACKLOG G7) |
| **Gate comment** | `skipped, autonomous run` |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Summary:** MCP `build_graph` catches only `RepoRefused`, so a drifted `qa.md`/`review.md` reaches the agent as a raw tool error instead of a result naming the file and reason. Goal: drift comes back as a structured dict, no `graph.json` is written or changed on failure, the CLI and the successful-build result stay as they are. Implemented in commit `0c8d960` before this spec; the spec states the requirement and is meant to be checked against that commit. Target version unspecified.
- **Open:** `none` — all questions decided autonomously (C1-C5); the user may overrule at approval.
- **Binding ruling:** §4 User Stories for the current stories; §7 Clarifications for what was decided and why
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Problem & Goal

- **Problem:** `server.build_graph` (MCP) renders `confinement.RepoRefused` as a dict but not `artifacts.TemplateDriftError` (`artifacts.py`, raised at ~12 sites for a missing section, table or column). A drifted `qa.md` or `review.md` therefore surfaces as an MCP tool error with no machine-readable file or reason. The README (`## Principles`, "Clean errors") already promises "a structured dict". Since v0.7.1 the `qa.md`/`review.md` of every current project is parsed, so drift is reachable more often (BACKLOG G7, origin: `current-artifact-names` review F1 / plan R4). The CLI already reports drift as one line plus a non-zero exit (`cli.py:170`).
- **Goal:** An agent calling `build_graph` on a drifted repo gets a dict naming the file and the mismatch, and can act on it without parsing an exception string.
- **Success signal:** On a fixture with one drifted `qa.md`, MCP `build_graph` returns `{"built": false, "reason": "template_drift", "file": …, "message": …}` and does not raise; a pre-existing `graph.json` is byte-identical afterwards; the CLI output is as before.
- **Why now:** Cheap and contained (S), and it closes the one place where a documented promise is untrue. Not building it costs little (agents see an error string); the cost is an agent that cannot tell drift from a crash.

## 2. Target Users

- **Agent using the MCP server:** calls `build_graph` and branches on the result; it never sees stderr or a traceback.
- **Developer running the CLI:** unaffected by design (US-3), named so the CLI is not changed by accident.

## 3. Assumptions & Open Questions

| # | Assumption / Question | Resolution |
|---|---|---|
| A1 | Original phrasing (issue #42): "Return template drift from MCP build_graph as a structured result." The underlying need is a machine-readable failure, not a new error class. | recorded |
| A2 | Drift is raised during the scan, before `Graph.save`, so "no write on failure" holds without new rollback logic. The parse-cache sidecar is not covered by AC-1.2; only `graph.json` is. | accepted, verified by test (AC-1.2) |
| A3 | `file` carries the path exactly as `TemplateDriftError.file` has it (the path string the CLI message also names), not a normalised or repo-relative form. | accepted (C2) |
| A4 | Only the first drifted file is reported; the scan stops at the first `TemplateDriftError`. | accepted (C3) |

## 4. User Stories

### US-1 (Must): MCP `build_graph` returns drift as a result

> As an agent calling `build_graph`, I want template drift returned as a structured result naming the file and the reason, so that I can report or fix it instead of treating it as a tool crash.

Fixture: a `.git`-marked repo with a `.spark/<feature>/` trail whose `qa.md` has no Acceptance Criteria Verification table (drift).

**Acceptance criteria:**

- [ ] AC-1.1: Given the drift fixture, when MCP `build_graph` is called, then it returns without raising and the dict equals `{"built": false, "reason": "template_drift", "file": <drifted path>, "message": <drift message>}`, with exactly those four keys.
- [ ] AC-1.2: Given the drift fixture with no prior graph, when `build_graph` is called, then no `.aspark-graph/graph.json` exists afterwards. Given the same fixture with a prior valid `graph.json`, then that file is byte-identical afterwards.
- [ ] AC-1.3: Given a drifted `review.md` (findings table missing a required column), when `build_graph` is called, then the result has the same four keys with `file` naming `review.md`.
- [ ] AC-1.4: Given the drift fixture, when `build_graph` is called, then `message` equals `str()` of the `TemplateDriftError`, and `file` appears within it.

### US-2 (Must): Successful and refused builds are unchanged

> As an agent already using `build_graph`, I want today's success result and the existing repo-refusal result untouched, so that my integration does not break.

**Acceptance criteria:**

- [ ] AC-2.1: Given a repo with valid artifacts, when `build_graph` is called, then the response keys and values are identical to the pre-change release's (including `shallow_history`, `no_git_history`, `ignored_legacy_files`) and graph.json is byte-identical to a pre-change build.
- [ ] AC-2.2: Given a path outside confinement, when `build_graph` is called, then the result is still `{"found": false, "reason": …, "message": …}`, unchanged.

### US-3 (Must): The CLI stays as it is

> As a developer running `aspark-graph build`, I want drift to stay a one-line message with a non-zero exit, so that scripts and habits keep working.

**Acceptance criteria:**

- [ ] AC-3.1: Given the drift fixture, when `aspark-graph build .` runs, then stderr is one line naming the file and mismatch, the exit code is non-zero, stdout is empty, no traceback appears, and no `graph.json` is written or changed. Output is identical to the pre-change release's.

### US-4 (Should): Convention and docs follow the change

> As a contributor, I want the refusal convention and the documentation to match behaviour, so that the next refusal is added the same way.

**Acceptance criteria:**

- [ ] AC-4.1: Given the change, when a reviewer reads `artifacts.py`, `cli.py` and `server.py`, then the error is raised only in the shared module with its machine-readable `reason`, and each adapter catches and renders it exactly once, with no drift logic or message formatting in the adapters beyond rendering.
- [ ] AC-4.2: Given the README's `build_graph` description and its "Clean errors" principle, when read, then they state the drift result shape (`built`, `reason`, `file`, `message`) and that the CLI exits non-zero.
- [ ] AC-4.3: Given `CLAUDE.md` and BACKLOG G7, when read, then the shipped trail is listed and G7 is marked done, citing the version it ships in once chosen.

## 5. Non-Functional Requirements

| # | Category | Requirement (measurable) | How it's verified |
|---|---|---|---|
| NFR-1 | Performance | N/A: error path only; the success path adds no work. Existing NFR-1 incremental-build benchmark (slow) still passes. | `pytest -m slow` |
| NFR-2 | Security & privacy | The result adds no content beyond what the CLI message already prints; confinement still runs first (a refused path never reaches artifact parsing). Result is untrusted data per `SECURITY.md`; no new tool parameter or bypass. | /peer-review, `test_confinement_guards.py` |
| NFR-3 | Accessibility | N/A: headless tool, no UI. | none |
| NFR-4 | Reliability / determinism | Two failing builds on an unchanged repo return equal dicts. graph.json from a successful build is byte-identical to pre-change code (proven by stash round-trip, not only a double build). No fixture produces a traceback or an MCP tool error for drift. | tests + /peer-review |
| NFR-5 | Observability / ops | `reason` is the stable key `template_drift`, taken from the exception's own `reason` attribute rather than a literal duplicated in the adapter. | /peer-review |
| NFR-6 | CLI-MCP parity (`cli` lens) | CLI and MCP name the same file and the same mismatch for the same fixture; a parity test asserts it. CLI exit codes and stderr format unchanged. | parity test + /peer-review |

## 6. Out of Scope

- Reporting all drifted files at once, or continuing past the first (A4, C3).
- A new exit code or JSON output mode for the CLI.
- Making drift non-fatal (skip the file, partial graph). Drift stays loud (constitution §6).
- Harmonising the `found: false` shape of refusals with `built: false` (C1).
- Structured results for other uncaught errors, e.g. a directory named `qa.md` (BACKLOG G8 B3).
- Changing what counts as drift, or the supported template version.
- Applying drift results to the eight read-only tools, which read the persisted graph and parse no artifacts.

## 7. Clarifications

| # | Date | Question | Resolution |
|---|---|---|---|
| C1 | 2026-11-11 | Refusals return `{"found": false, …}`; drift is specified as `{"built": false, …}`. Same key? | Keep `built: false` as the issue states: the failing action is a build, and `found` would be wrong for a write. Refusal shape untouched (AC-2.2); unifying is out of scope. |
| C2 | 2026-11-11 | Form of `file`? | The path string carried by the exception (A3), the same one the CLI message names. Parity over prettiness. |
| C3 | 2026-11-11 | One drifted file or all? | First only (A4); the scan stops at the first raise. Listing all is a different feature. |
| C4 | 2026-11-11 | Does a failed build leave a prior graph alone? | Yes (AC-1.2): raised before save; verified rather than assumed. |
| C5 | 2026-11-11 | Version? | Unspecified. Behaviour change in a return shape only; the user or orchestrator picks it at release. |

## 8. Design Review

- **Overall impression:** N/A. Headless tool, no UI.
- **Heuristics findings:** N/A
- **Accessibility notes:** N/A (see NFR-3)
- **Design risks & required changes:** none

---

## ✅ SPEC GATE

*All boxes checked → `/sprint-plan` may start. Any box open → back to `/story-time` or `/look-and-feel`.*

- [x] Problem, goal and success signal are concrete (no buzzwords, no "everyone")
- [x] Every story has testable Given/When/Then acceptance criteria
- [x] Stories are prioritized (MoSCoW) and at least one is a Must
- [x] Non-functional requirements are stated and measurable (or marked N/A with reason)
- [x] Clarify pass done: no ambiguity left unresolved or unparked
- [x] Open questions are resolved or explicitly accepted as risk (A2-A4 accepted; C1-C5 decided autonomously)
- [x] Out-of-scope section is filled (something was consciously cut)
- [x] Constitution (`.spark/constitution.md`) respected, or conflicts recorded as open questions (§3 refusal seam, §6 loud drift and no tracebacks, `cli` lens as NFR-6; constitution §9 used for module structure, no source re-derivation needed beyond the touched `server.py`/`artifacts.py`)
- [x] Design review done for UI-facing features (or marked N/A with reason). N/A: no UI.
- [x] Line budget respected: Ist ~125 / Soll ~250 (excluding HTML comments)
- [x] Status set to `approved` by the user
