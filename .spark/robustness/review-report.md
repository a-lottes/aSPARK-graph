# Review Report: robustness

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | Working-tree diff, `.spark/robustness/plan.md` |
| **Status** | `passed` |
| **Date** | 2026-07-18 |

## 1. Scope

Working-tree diff against `HEAD` (61d6e88). Exactly four files, matching the plan's Affected-Components table:

| File | Change | Size |
|---|---|---|
| `src/aspark_graph/queries.py` | `find_nodes` empty-query guard (T1) | +2 |
| `tests/test_navigation.py` | 3 unit tests, US-1 (T2) | +22 |
| `tests/test_cli_mcp_parity.py` | 1 parity test, US-1 (T2) | +9 |
| `tests/test_mcp_transport.py` | **new** subprocess stdio smoke test, US-2 (T3) | new file |

Confirmed **unchanged** and verified: `src/aspark_graph/cli.py` (`_handle_find_nodes` still a one-line pass-through to `queries.find_nodes`), `src/aspark_graph/server.py` (`find_nodes` tool still `err or queries.find_nodes(...)`), and `pyproject.toml` (no dependency or config change; `git diff HEAD -- pyproject.toml` is empty). Both adapters remain thin; the guard lives solely at the shared query surface.

## 2. Plan Conformance

| Task | Planned | Delivered | Verdict |
|---|---|---|---|
| T1 | One early-return guard at top of `find_nodes`, exactly `query == ""`, returns `{"query", "type", "count": 0, "nodes": []}` | `queries.py:315-316` — `if query == "": return {"query": query, "type": type, "count": 0, "nodes": []}`, placed above `q = query.lower()`; no other line in the function touched | Conforms |
| T2 | Unit tests (AC-1.1/1.2/1.5) + empty-query parity test (AC-1.3/1.4) asserting the exact dict | Three unit tests assert the exact dict (not merely `count == 0`); parity test asserts `cli_out == mcp_out` AND `== {"query": "", "type": None, "count": 0, "nodes": []}` | Conforms |
| T3 | Inline `tmp_path` fixture, spawn `serve`, `initialize` → `notifications/initialized` → `tools/call staleness` over newline-delimited JSON-RPC, match `id==2`, assert no top-level `error`, close stdin, assert exit 0, `@pytest.mark.slow`, PATH skip, stdlib-only | All present and correct: newline-delimited compact JSON, correct handshake and `protocolVersion` `2025-06-18`, `id==2` matching with initialize-response skip, watchdog `threading.Timer(10, proc.kill)`, `shutil.which` skip, `proc.wait(timeout=5) == 0` | Conforms, with one Minor deviation on the R1 diagnostic (see F1) |

The guard deliberately does **not** `.strip()` — whitespace-only queries stay Out of Scope (spec §6, C8) as designed. No scope drift.

## 3. Findings

No Blockers, no Majors. Three test-hardening observations found in the transport smoke test; all three fixed post-review.

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Minor | `tests/test_mcp_transport.py` | R1 mitigation partially unimplemented: timeout failure message surfaced no stderr, making the test hard to diagnose when it catches a real wire-format break. Fixed: `stderr_drain` thread reads `proc.stderr` concurrently; on timeout, `proc.kill()` is called first (so the thread reaches EOF), then `stderr_drain.join(2)`; assertion message is now `f"No id=2 response within 10 s; server stderr: {stderr_out!r}"`. | fixed |
| F2 | Nit | `tests/test_mcp_transport.py` | `proc.stdout` and `proc.stderr` handles left to GC → potential `ResourceWarning`. Fixed: explicit `proc.stdout.close()` and `proc.stderr.close()` after `proc.wait()` and `stderr_drain.join()`. | fixed |
| F3 | Nit | `tests/test_mcp_transport.py` | `stderr=PIPE` never drained while blocked on `stdout.readline()` — 64 KB deadlock risk (bounded by watchdog). Fixed together with F1 via the `stderr_drain` thread. | fixed |

## 4. Requirements Traceability

| ID | Requirement | Implemented at / verified by | Status |
|---|---|---|---|
| AC-1.1 | `find_nodes("")` → `{"query":"","type":null,"count":0,"nodes":[]}` | `queries.py:315-316`; `test_navigation.py::test_find_nodes_empty_query_returns_empty_result` asserts the exact dict | Pass |
| AC-1.2 | `type` filter does not bypass the guard | Guard returns before the filter loop; `test_find_nodes_empty_query_with_type_filter_returns_empty` asserts `"type":"Story"` passthrough | Pass |
| AC-1.3 | CLI `find_nodes ... ""` exits 0, prints empty dict, no traceback | `test_find_nodes_empty_query_cli_equals_mcp` (`_cli_json` asserts rc 0 + parses stdout) | Pass |
| AC-1.4 | MCP tool returns the same empty dict — CLI≡MCP parity | Same test: `cli_out == mcp_out`. True by construction — both adapters call the shared guard | Pass |
| AC-1.5 | Non-empty query unaffected | `test_find_nodes_nonempty_query_unaffected` (`"US-1"`, type `"Story"` → 1 match) | Pass |
| AC-2.1 | `id==2` response is valid JSON, no top-level `error`, within 10 s | `test_mcp_transport.py:74-82` + watchdog | Pass |
| AC-2.2 | Subprocess exits 0 after stdin close | `test_mcp_transport.py:85-86` `proc.wait(timeout=5) == 0` | Pass |
| AC-2.3 | Not on PATH → skip with reason | `test_mcp_transport.py:23-24` `shutil.which` guard | Pass |
| AC-2.4 | Own file, `@pytest.mark.slow`, out of default run | Marker at line 20; `-m slow` collects 2, default deselects 2 | Pass |
| NFR-1 | Guard changes no non-empty output | Full existing suite green, no edits to prior `find_nodes` expectations | Pass |
| NFR-2 | Empty-query CLI≡MCP parity | Parity test asserts identical dicts | Pass |
| NFR-3 | No traceback on the guard path | Guard returns before `query.lower()`; existing `test_ac_5_2...` still asserts no `Traceback` in stderr | Pass |
| NFR-4 | Smoke test excluded from default run | `165 passed, 2 deselected` default | Pass |
| NFR-5 | No new deps | `pyproject.toml` unchanged; test imports are stdlib + existing `pytest`/`aspark_graph` | Pass |

## 5. What Was Checked

- **Read in full:** the four diff files, plus `cli.py` and `server.py` `find_nodes` handlers and the argparse wiring for context.
- **Default suite:** `uv run pytest -q` → **165 passed, 2 deselected** in 26.8 s.
- **Slow suite:** `uv run pytest -m slow -q` → **2 passed, 165 deselected** in 12.0 s (NFR-1 benchmark + the new transport smoke test).
- **Probe A (guard falsifiability):** commented out the `if query == "":` guard → `test_find_nodes_empty_query_returns_empty_result` and `..._with_type_filter...` both FAIL (`count: 2` — the whole graph — vs expected `0`). Guard restored; suite re-verified.
- **Probe B (transport-test falsifiability):** changed `data.get("id") == 2` to `== 999` → test FAILS with `AssertionError: No response for tools/call (id=2) within 10 s`. Confirms the test genuinely asserts the tool response and is not a tautology. Restored.
- **Guard shape:** returns `type` (original passthrough, e.g. `"Story"`/`None`), matching the normal-path return at `queries.py:326`; guard is exact `== ""`, not `.strip()`.
- **Adapters:** confirmed thin and unchanged; guard is single-sourced in `queries.py`, so parity holds by construction.
- **Determinism / deps:** `pyproject.toml` byte-unchanged; no parse-affecting or dependency change.

No open questions — the plan's verified `mcp` 1.19.0 wire-format notes matched the running behaviour, and both suites are green.

## 6. Verdict

**Pass.** Both Must stories are correctly and minimally implemented: the `find_nodes("")` guard is a single early return at the shared query surface that returns the exact canonical empty-result dict for both the no-filter and type-filter cases, leaving non-empty queries byte-identical, and the transport smoke test performs a real stdio JSON-RPC round-trip against a spawned `serve`, correctly skipping the initialize response to match `id==2`, guarded by a watchdog and a PATH skip, and correctly quarantined to the `slow` bucket. Both suites are green and both falsifiability probes confirm the new tests fail when the code they guard is broken — these are real tests, not decoration. The only findings are three non-blocking test-hardening nits in the transport smoke test (chiefly F1: the R1 plan mitigation to surface stderr on a diagnostic failure was not implemented), none of which affect correctness, parity, determinism, or any acceptance criterion. No new dependencies, no adapter drift, no traceback path. This is ready for QA; the developer may address F1–F3 in fix-mode or the EM may accept them as recorded.

---

## ✅ REVIEW GATE

- [x] `/increment` reported done; plan and spec acceptance criteria read
- [x] Diff obtained from git and reviewed in context (4 files; `cli.py`/`server.py`/`pyproject.toml` confirmed unchanged)
- [x] Plan conformance checked task-by-task (T1/T2/T3) — one Minor deviation recorded (F1)
- [x] Every Must AC (AC-1.1–1.5, AC-2.1–2.4) traced to code and a falsifiable test
- [x] Judgable NFRs (NFR-1..5) verified; NFR-6/7/8 are N/A per spec
- [x] Test suite run by the reviewer: default green (165 passed, 2 deselected), slow green (2 passed)
- [x] Falsifiability probed (A: guard removed → tests fail; B: id mismatch → transport test fails)
- [x] Every finding names location, problem, why it matters, and a suggested fix
- [x] No Blockers; no Majors requiring waiver
- [x] Verdict is a single honest paragraph stating pass
- [x] Status set to `passed`; F1/F2/F3 all fixed; suite re-verified green (165 passed, 2 deselected)
