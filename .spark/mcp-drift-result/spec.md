# Spec: mcp-drift-result

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (`/story-time`), Designer (`/look-and-feel`) |
| **Status** | `approved` |
| **Date** | 2026-11-11 |
| **Ticket** | #40 |
| **Gate comment** | none |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Summary:** MCP `build_graph` raises a tool error on a drifted `.spark/` file; it should return a structured result naming file and reason, leaving the on-disk graph untouched and the CLI behavior unchanged.
- **Open:** `none`
- **Binding ruling:** §4 User Stories for the current stories; §7 Clarifications for what changed since the last round and why
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Problem & Goal

- **Problem:** MCP `build_graph` catches only `RepoRefused`. A drifted `qa.md` or `review.md` raises `TemplateDriftError` to the MCP client as a generic tool error, not a result naming the file and reason (BACKLOG G7). The README promises "a structured dict" for domain errors (README "Clean errors"), so the agent calling the tool cannot reliably read which file to fix. Source: `constitution.md §9` (stack, `server.py` as thin adapter), `constitution.md §6` (drift fails loudly, naming the file).
- **Goal:** On template drift, MCP `build_graph` returns `{"built": false, "reason": "template_drift", "file": <path>, "message": <drift message>}`; nothing is written; CLI and successful-build behavior are unchanged.
- **Success signal:** a test builds a repo with a drifted `qa.md` through `server.build_graph` and gets that dict (no exception); `uv run pytest` stays green.
- **Why now:** the behavior and the docs disagree today; agents driving the server hit an opaque error on the exact condition the tool is designed to report.

Note: the implementation (`server.py` catch of `artifacts.TemplateDriftError`, test in `tests/test_mcp_errors.py`) already exists on this branch. This spec records the contract and what must be verified and documented; it is not a request for new design.

## 2. Target Users

- AI agents (and the developers configuring them) calling the `build_graph` MCP tool against a repo whose `.spark/` artifact no longer matches the supported template shape.
- Developers running `aspark-graph build` from a terminal (must see no change).

## 3. Assumptions & Open Questions

| # | Assumption / Question | Resolution |
|---|---|---|
| A1 | Original phrasing: "Return template drift from MCP build_graph as a structured result." Underlying need: agent-readable file and reason. | Accepted. |
| A2 | `TemplateDriftError` already carries the drifted file path (`exc.file`). | Accepted; verified by AC-1.1. |
| A3 | The drift result uses `built: false`, while `RepoRefused` results use `found: false`. The mismatch is accepted for now. | Accepted; unification is Out of Scope. |

## 4. User Stories

### US-1 (Must): MCP build_graph reports template drift as a result

> As an AI agent calling MCP `build_graph`, I want a drifted `.spark/` file returned as a structured result naming the file and reason, so that I can tell the user which file to fix instead of seeing an opaque tool error.

**Acceptance criteria:**

- [ ] AC-1.1: Given a repo whose `qa.md` (or `review.md`) drifts from the supported template, when MCP `build_graph` is called, then it returns without raising `{"built": false, "reason": "template_drift", "file": <path of the drifted file>, "message": <drift message>}`, and `file` names the drifted file.
- [ ] AC-1.2: Given a drifted repo with no prior graph, when MCP `build_graph` is called, then no `.aspark-graph/graph.json` exists afterwards.
- [ ] AC-1.3: Given a drifted repo with an existing `graph.json`, when MCP `build_graph` is called, then `graph.json` is byte-identical to before the call.
- [ ] AC-1.4: Given a repo with no drift, when MCP `build_graph` is called, then the result has the same keys and values as before this change (`code_entities`, `artifact_entities`, `inferred_edges`, `unparsed`, `ignored_legacy_files`, `graph_path`, `shallow_history`, `no_git_history`) and no `built` key.

### US-2 (Must): CLI behavior and documentation stay consistent

> As a developer, I want the CLI unchanged and the docs to match the MCP behavior, so that neither the terminal contract nor the README misleads me.

**Acceptance criteria:**

- [ ] AC-2.1: Given a drifted repo, when `aspark-graph build` runs, then it prints a one-line message naming the file, exits non-zero, and prints no traceback.
- [ ] AC-2.2: Given the change, when the code is reviewed, then `TemplateDriftError` is still raised only in the shared module (`artifacts.py`) and caught and rendered once each in `cli.py` and `server.py`, with no drift-handling logic added to `queries.py`/`build.py` callers beyond that catch.
- [ ] AC-2.3: Given the change, when README's MCP section and `.spark/BACKLOG.md` G7 are read, then both state the `built: false` / `template_drift` / `file` / `message` shape and G7 is marked done with issue #40.

## 5. Non-Functional Requirements

| # | Category | Requirement (measurable) | How it's verified |
|---|---|---|---|
| NFR-1 | Performance | N/A — error-path return only; no new work on the build path. | n/a |
| NFR-2 | Security & privacy | The `file` value is the path of a file inside the confined repo (confinement runs before parsing); no new tool parameter, env var or bypass is added. | /peer-review |
| NFR-3 | Accessibility | N/A — no UI. | n/a |
| NFR-4 | Reliability / scale | Determinism holds: byte-identical double build still passes, and a clean repo's `graph.json` is byte-identical to the pre-change build (stash round-trip). | `uv run pytest`, /peer-review |
| NFR-5 | CLI lens | CLI drift path: single-line stderr message, non-zero exit, no traceback (constitution `cli` lens, "clean errors"). | test + /peer-review |

## 6. Out of Scope

- Unifying CLI and MCP error shapes (e.g. adding `built: false` to `RepoRefused` results, or `found: false` to drift): separate decision, touches every tool's contract.
- Structured drift results for the eight read-only MCP tools (they do not parse `.spark/` at query time).
- Reporting multiple drifted files at once; the first drift stops the build, as today.
- Lenient or partial parsing of drifted files: drift still fails loudly (`constitution.md §6`).
- Changing the template shape the parser supports, or fixing G6 (only the first QA table is read).

## 7. Clarifications

| # | Date | Question | Resolution |
|---|---|---|---|
| C1 | 2026-11-11 | Should `built: false` match `RepoRefused`'s `found: false`? | No; accepted as is, unification cut to Out of Scope (A3). |
| C2 | 2026-11-11 | Does a failed build leave a stale or partial graph? | No: the build raises before `graph.save`; verified by AC-1.2 and AC-1.3. |
| C3 | 2026-11-11 | Does the implementation already exist? | Yes; spec scopes verification and docs, not new design. |

## 8. Design Review

N/A — not UI-facing: a headless MCP tool and CLI with no screens, so the Designer has nothing to review (constitution §8: no browser-observable surface).

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
- [x] Line budget respected: Ist ~100 / Soll ~250 (excluding HTML comments) — self-reported, no linter checks this
- [x] Status set to `approved` by the user (autonomous run: recommended option taken)
