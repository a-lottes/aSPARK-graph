# QA Report: aspark-graph

| | |
|---|---|
| **Phase** | Review (hands-on) |
| **Owner** | QA Tester (`/demo-day`) |
| **Input** | The CLI + MCP server, `.spark/aspark-graph/spec.md` (the acceptance criteria) |
| **Status** | `passed` |
| **Date** | 2026-07-14 |

## 1. Test Environment

- **App:** `aspark-graph` v0.1.0 — **not a browser app**. Surfaces exercised:
  (1) the CLI, and (2) the MCP stdio server over a real subprocess.
- **How it was driven:** the release wheel (`aspark_graph-0.1.0-py3-none-any.whl`)
  installed into a **fresh, isolated venv** (Python 3.11) and separately via
  `uvx --from <wheel>` — i.e. the actual end-user install path, not the dev tree.
- **Test data:** a purpose-built mixed-language QA repo (`qa-repo`) with Python +
  TypeScript + Java source and a full `.spark/checkout/` trail (spec + plan with a
  best-effort `files:` note and an intentionally orphan-free/partly-failing QA),
  plus throwaway repos for the no-`.spark/`, drift, and unknown-path cases.
- **Browser / viewport(s):** **N/A** — no graphical UI. The spec's Design Review is
  N/A for the same reason; the plan's test strategy assigns CLI/MCP QA here, not
  browser QA.

## 2. Acceptance Criteria Verification

Every Must-story AC was exercised hands-on against the installed tool (CLI and,
where it is the contract, the live MCP server). Not read from code — run.

| AC | Steps performed | Expected | Observed | Result |
|---|---|---|---|---|
| AC-1.1 | `build .` on the QA repo | reports code + artifact counts | `14 code entities, 8 artifact entities` | ✅ pass |
| AC-1.2 | `build .` twice, `diff` the graph.json | byte-identical | byte-identical | ✅ pass |
| AC-1.3 | `build .` on a repo with a drifted spec (no User Stories section) | fail loudly naming file + mismatch, no traceback, exit 1 | `template drift in …/spec.md: missing a '## … User Stories' section (supported: aspark/0.1.0)`, exit 1 | ✅ pass |
| AC-1.4 | `build .` on a repo with no `.spark/` | code-only graph, zero artifact entities, no error | `2 code entities, 0 artifact entities` | ✅ pass |
| AC-2.1 | `query story_trace US-1` | title + all ACs | `Compute cart total`, `[AC-1.1, AC-1.2]` | ✅ pass |
| AC-2.2 | same | exactly the mapped tasks + status | `[(T1, done), (T2, doing)]` | ✅ pass |
| AC-2.3 | same | each AC's latest QA verdict | `{AC-1.1: pass, AC-1.2: fail}` | ✅ pass |
| AC-2.4 | same | explicit `files:` → declared link; none → empty, no error | `T1 → [(core.py, declared)]`, `T2 → []` (no error) | ✅ pass |
| AC-2.5 | `query story_trace US-99` | explicit not-found | `found=False, reason=not_found` | ✅ pass |
| AC-3.1 | `query impact src/app/core.py` | code entities + reachable stories/ACs | `US-1` + `[AC-1.1, AC-1.2]` | ✅ pass |
| AC-3.2 | same | declared link not dropped | `US-1` tagged `declared` via `implements`→`maps_to` | ✅ pass |
| AC-3.3 | `impact src/app/helpers.ts` (a leaf with no artifact path) | explicit "no affected" note | `no affected stories or acceptance criteria` | ✅ pass |
| AC-3.4 | `impact ghost.py src/app/core.py` | unknown path named, known still answered | `unknown=[ghost.py]`, `US-1` still returned | ✅ pass |
| AC-3.5 | `impact src/app/util.py` (reached only via an `imports` edge) | weakest-edge = extracted | `US-1` tagged `extracted` | ✅ pass |
| AC-4.1 | `build .`, inspect File languages | all three languages parsed | `[java, python, typescript]` | ✅ pass |
| AC-4.2 | (unit) un-registered extractor → unparsed File node | build not failed, file unparsed | covered green in suite | ✅ pass |

All Must-story ACs (US-1..US-4) pass. Should/Could ACs (US-5 CLI≡MCP parity,
US-6 `gate_health`, US-7 navigation) were also exercised live and behave.

## 3. Exploratory Findings

Beyond the ACs: I pushed the tool past the happy path.

| # | Severity | Steps to reproduce | Expected vs. observed | Status |
|---|---|---|---|---|
| B1 | — | `build` a repo with no `.spark/` and query `gate_health` for a non-existent feature | expected explicit not-found; observed `found=False, reason=not_found` | not a bug |
| B2 | — | Live MCP: spawn `aspark-graph serve` as a subprocess, connect over stdio, `list_tools` + call each | expected the real handshake to work (unit tests use in-memory transport); observed all 8 tools listed and `story_trace`/`impact`/`gate_health` return correct data over the wire | not a bug (this was the key risk) |
| B3 | — | Bare `import { x } from "react"` (npm) in a TS file | expected no repo-file edge; observed no `imports` edge (correct) | not a bug |

No Blocker, Major, or Minor bugs found in exploration.

## 4. Console & Network

**N/A** — no browser, no console, no network (the tool is deterministic and
offline by design). The equivalent surface — process stderr / exit codes — was
checked: drift and build-before-query produce a clean one-line stderr message and
exit 1, never a traceback.

## 5. Verdict

Would I demo this to a stakeholder right now? **Yes.** I installed the release
wheel into a clean environment and, separately, ran it via `uvx` — the documented
install paths both work, including the native tree-sitter wheels. Every Must
acceptance criterion passes when the tool is actually *run*, not just tested: the
build is deterministic to the byte, drift fails as a clean named error rather than
a crash, and the two crown-jewel tools return correct results — including the
confidence tagging, where `impact` correctly downgrades a story reached only
through an `imports` edge to `extracted` while a directly-implemented file stays
`declared`. The single highest risk — that the MCP server works in a *real* stdio
session, not just the in-memory test client — I verified by spawning the server as
a subprocess and driving it over the wire: all eight tools answer. Nothing was left
to "should work".

---

## ✅ QA GATE

*All boxes checked → `/go-live` may start. Any box open → back to `/increment`, then re-run `/demo-day`.*

- [x] Every Must-story acceptance criterion verified hands-on (CLI + live MCP) and passed
- [x] No open Blocker or Major bugs (none found in exploration)
- [x] Process stderr/exit codes clean on the tested flows (the CLI/MCP analogue of "console free of errors")
- [x] Tested on all agreed surfaces (CLI and live MCP stdio server; browser N/A with reason)
- [x] Status set to `passed`
