# QA Report: mcp-drift-result

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review (hands-on) |
| **Owner** | QA Tester (`/demo-day`) |
| **Input** | Branch `factory/issue-42` at `19b4398` (clean tree), `.spark/mcp-drift-result/spec.md` (approved) |
| **Status** | `passed` |
| **Round** | 1 |
| **Date** | 2026-11-11 |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Verdict:** Yes. Real MCP stdio `build_graph` returns the four-key drift dict and the CLI keeps its one-line stderr and exit 1; success path and refusal are unchanged.
- **Open:** `none` (Minors: see §3)
- **Binding ruling:** §5 Verdict and the gate checklist below — the only binding location; there is no other round to point to
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/demo-day` and proceed — don't stop on it.

## 1. Test Environment

- **App URL:** N/A (headless). Method declared in `.spark/constitution.md` §8: full + slow suite, clean-env wheel install and `serve` boot, byte-identical build, real-repo `impact`/`story_trace`. Browser and viewport fields: N/A.
- **Browser / viewport(s):** N/A
- **Test data / accounts used:** scratch `.git`-marked repos under `/tmp/qa-fx` (drifted `qa.md`, drifted `review.md`, valid), a `git worktree` of base `dd4b994` (removed afterwards), this repo's own `.spark/` trail. Real `aspark-graph serve` driven over newline-delimited JSON-RPC (as in `tests/test_mcp_transport.py`) by a script kept outside the repo. Graph calls used: `staleness`, `build_graph`, `story_trace` (US-1), `impact` (server.py, artifacts.py) for scoping only.

## 2. Acceptance Criteria Verification

| Spec ID | Steps performed | Expected | Observed | Result |
|---|---|---|---|---|
| AC-1.1 | Real `aspark-graph serve` over stdio; `tools/call build_graph` on a repo whose `qa.md` has no verification section | `isError:false`, dict with exactly `built`, `reason`, `file`, `message` | `{"built":false,"reason":"template_drift","file":"/tmp/qa-fx/a/.spark/demo/qa.md","message":"template drift in …"}`, `isError:false`; suite test also green | ✅ pass |
| AC-1.2 | Same call with no prior graph; then on a repo with a prior valid graph.json, `sha256sum -c` after the failing call | No `.aspark-graph` created; prior file unchanged | No `.aspark-graph` directory after the call; prior graph.json `OK` after the drift call | ✅ pass |
| AC-1.3 | stdio `build_graph` on a repo whose `review.md` findings table lacks `severity` | Same four keys, `file` names `review.md` | `file` = `/tmp/qa-fx/b/.spark/demo/review.md`, reason `template_drift`, message names missing `severity` column | ✅ pass |
| AC-1.4 | Compared `message` and `file` in the AC-1.1/1.3 outputs; unit test asserts `message == str(exc)` | `file` appears inside `message` | Path appears verbatim in `message` in both fixtures; `test_mcp_errors.py` green | ✅ pass |
| AC-2.1 | Valid fixture: base `dd4b994` CLI build and HEAD CLI build, `sha256sum` graph.json; stdio `build_graph` response keys | Identical graph.json; keys unchanged | Both `1730d3d4…4781e`; keys `code_entities, artifact_entities, inferred_edges, unparsed, ignored_legacy_files, graph_path, shallow_history, no_git_history` | ✅ pass |
| AC-2.2 | stdio `build_graph` on `/tmp/qa-fx` (no repo marker) | `{"found":false,"reason":…,"message":…}` | `{"found":false,"reason":"outside_confinement","message":"… refusing to scan it"}` | ✅ pass |
| AC-3.1 | `aspark-graph build` on both drift fixtures at HEAD and on base `dd4b994` (stderr/stdout `cmp`); check rc, stdout bytes, graph.json | One stderr line, rc 1, empty stdout, no traceback, no graph.json; same as base | rc=1, stdout 0 bytes, single-line message, no traceback; stderr and stdout byte-identical to base; prior graph unchanged | ✅ pass |
| AC-4.1 | Read `artifacts.py`, `cli.py:170`, `server.py:29` | `reason` set on the exception only; each adapter catches once, renders only | `reason = "template_drift"` on `TemplateDriftError`; `cli.py` prints `str(exc)`, `server.py` returns `exc.reason`/`exc.file`/`str(exc)`; no drift logic in adapters | ✅ pass |
| AC-4.2 | Read README lines ~224 and ~313 | Result shape and non-zero CLI exit stated | Both state `{"built": false, "reason": "template_drift", "file": …, "message": …}`; Clean-errors principle covers non-zero exit | ✅ pass |
| AC-4.3 | Read CLAUDE.md line 48 and BACKLOG G7 | Trail listed, G7 marked done | Trail listed; G7 has a **Done** note, version "set at /go-live" (version unspecified per C5) | ✅ pass |
| NFR-1 | `uv run pytest -m slow`; re-ran `tests/test_incremental_bench.py` three times | Success path adds no work; bench passes | Slow suite 3 passed, 1 failed (bench 7.8%); reruns: 31.8% fail, then pass, pass. Transport smoke, sdist manifest and unlocked fresh-install `serve` passed. Known load-dependent flake F4 in review.md (fails on base too); no code on the success path changed | ✅ pass |
| NFR-2 | Stdio `build_graph` on non-repo path; read `build.py` order; `test_confinement_guards.py` in the full suite | Confinement refuses before parsing; no extra content | Refusal returned before any artifact parse; drift message identical to CLI line; guards test green | ✅ pass |
| NFR-3 | N/A, headless tool, no UI | N/A | N/A | ✅ pass |
| NFR-4 | Two stdio drift calls per fixture; double build of this repo; base-vs-HEAD graph.json compare; drift runs checked for tracebacks | Equal dicts; byte-identical graph.json; no traceback or tool error | Both drift results equal; self-repo graph.json `24cc3626…` identical across two builds; success graph identical to base `dd4b994`; `isError:false`, no traceback | ✅ pass |
| NFR-5 | Read `server.py:29-31` | `reason` taken from `exc.reason` | `exc.reason` used; no literal in adapter | ✅ pass |
| NFR-6 | Compared CLI stderr with MCP `message` for the same two fixtures; parity test in full suite (393 passed) | Same file and mismatch; CLI exit and format unchanged | Identical text for both fixtures; CLI exit 1, stderr format as base | ✅ pass |

## 3. Exploratory Findings

| # | Severity | Steps to reproduce | Expected vs. observed | Status |
|---|---|---|---|---|
| B1 | Minor | Run `uv run pytest -m slow` repeatedly on a loaded machine | Expected stable; `test_nfr1_incremental_at_least_50_percent_faster` failed 2 of 4 runs (7.8%, 31.8%) and passed 2. Same flake as review F4, reproduces on base, not caused by this diff | open |

## 4. Console & Network

N/A (no browser). Checked instead: stderr of `serve` showed no traceback on drift or refusal calls; CLI drift output has no traceback. `git status` clean after the run; scratch worktree removed.

## 5. Verdict

Yes, I would demo this now. Over a real stdio MCP session a drifted `qa.md` and a drifted `review.md` come back as the four-key structured result with `isError:false`, no `graph.json` is created or altered, and the CLI output is byte-identical to the pre-change release. The success dict, graph.json bytes and the refusal shape match base. Full suite 393 passed; slow suite passes except the known timing flake (B1, Minor, pre-existing).

---

## ✅ QA GATE

- [x] Every Must-story acceptance criterion verified (by the §8 substitute method) and passed
- [x] Every QA-owned NFR verified and passed
- [x] No open Blocker or Major bugs (Minor B1 listed, pre-existing)
- [x] Console free of errors on the tested flows (N/A browser; serve stderr clean)
- [x] Tested on all agreed viewports (N/A, headless)
- [x] Line budget respected: Ist ~68 / Soll ~130 (excluding HTML comments)
- [x] Status set to `passed`
