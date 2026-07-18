# Plan: robustness

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Engineering Manager (`/sprint-plan`) |
| **Input** | `.spark/robustness/spec.md` (approved) |
| **Status** | `approved` |
| **Date** | 2026-07-18 |

## 1. Architecture Decision

### Context

Two small, unrelated robustness gaps in an otherwise stable v0.4.0 codebase:

1. **US-1 — `find_nodes("")` returns the whole graph.** In
   `queries.find_nodes` (`src/aspark_graph/queries.py:313-324`) the match test is
   `any(q in h.lower() for h in haystacks)` where `q = query.lower()`. The empty
   string is a substring of every string, so an empty query matches every node.
   A caller building a query dynamically can get the full graph back and mistake
   it for a narrowed result.

2. **US-2 — no transport-level test.** Every MCP test today calls the decorated
   tool function in-process (`tests/test_cli_mcp_parity.py`,
   `tests/test_mcp_errors.py`) — the `@mcp.tool()` decorator leaves the function
   directly callable. That proves query/MCP logical parity but never exercises
   the stdio JSON-RPC boundary: that `aspark-graph serve` starts, reads a
   JSON-RPC request from stdin, and writes a well-formed response to stdout. An
   `mcp` SDK bump within the allowed range (`>=1.12,<1.20`) could change the wire
   format with every in-process test staying green.

No constitution exists (`.spark/constitution.md` absent). The binding
constraints are the CLAUDE.md non-negotiables: determinism, thin adapters, clean
errors / never tracebacks, the `mcp>=1.12,<1.20` cap, no unjustified deps.

### Decision

**US-1: one early-return guard at the top of `queries.find_nodes`.** Before the
scan loop, return the canonical empty-result dict when the query is empty:

```python
def find_nodes(graph: Graph, query: str, type: str | None = None) -> dict:
    if query == "":
        return {"query": query, "type": type, "count": 0, "nodes": []}
    ...
```

- The guard lives in `queries.py`, **not** in `cli.py` or `server.py` — the
  thin-adapter rule means both adapters inherit the fix for free, which is
  exactly what makes AC-1.4 (CLI ≡ MCP parity) true by construction (NFR-2).
- It returns the **same structured dict** every other `find_nodes` call returns
  (same keys `query`/`type`/`count`/`nodes`, same types), so no caller needs a
  try/except and no traceback can reach the CLI/MCP edge (NFR-3, A1). It is
  **not** a `ValueError`.
- Scope is exactly `query == ""`. Whitespace-only queries (`"   "`) are Out of
  Scope (spec §6, C8); the guard deliberately does not `.strip()`.

**US-2: one subprocess smoke test spawning `aspark-graph serve`, speaking
newline-delimited JSON-RPC 2.0 over stdio, marked `@pytest.mark.slow`.** Stdlib
only (`subprocess`, `json`, `shutil`, `threading`) — no new dependency (NFR-5).
The fixture is built inline in `tmp_path` (A3) so the test is self-contained.

### MCP wire format (verified against the installed SDK — hand this to `/increment`)

Verified by reading the installed `mcp` **1.19.0** (within the `<1.20` cap):
`.venv/.../mcp/server/stdio.py`, `mcp/server/session.py`, `mcp/types.py`,
`mcp/shared/version.py`.

- **Framing: newline-delimited JSON.** `stdio_server.stdin_reader` does
  `async for line in stdin: JSONRPCMessage.model_validate_json(line)` — **one
  JSON object per line**. `stdout_writer` writes `json + "\n"` and flushes after
  every message. So: write one compact JSON object + `"\n"` to the child's
  stdin and flush; read responses with `readline()`. No Content-Length / LSP
  framing.
- **Handshake is enforced.** `session.py:170-172` raises
  `"Received request before initialization was complete"` for any non-`initialize`,
  non-`ping` request received before init. The required sequence is:
  1. **Client → `initialize` request** (has `id`):
     ```json
     {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"smoke","version":"0"}}}
     ```
     `protocolVersion` must be one of `SUPPORTED_PROTOCOL_VERSIONS`
     (`"2024-11-05"`, `"2025-03-26"`, `"2025-06-18"`); use `"2025-06-18"`
     (`LATEST_PROTOCOL_VERSION`, `types.py:26`).
  2. **Server → `InitializeResult` response** on stdout (`id:1`), carrying
     `protocolVersion`, `capabilities`, `serverInfo`.
  3. **Client → `notifications/initialized` notification** (no `id`):
     ```json
     {"jsonrpc":"2.0","method":"notifications/initialized"}
     ```
     Send it to be protocol-correct and forward-robust. (Note: this SDK already
     flips to `Initialized` right after responding to `initialize` at
     `session.py:166`, but do not rely on that — send the notification.)
  4. **Client → `tools/call` request** (has `id`):
     ```json
     {"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"staleness","arguments":{"repo":"<abs tmp_path>"}}}
     ```
     Use the `staleness` tool — it needs only `repo` and is always available on a
     built graph. Pass the **absolute** `tmp_path` as `repo` so the server's cwd
     is irrelevant.
  5. **Server → `CallToolResult` response** (`id:2`): a JSON-RPC envelope
     `{"jsonrpc":"2.0","id":2,"result":{...}}`. FastMCP wraps a dict-returning
     tool as `result.content` (a `TextContent` list) plus `result.structuredContent`.
- **AC-2.1 assertion target:** parse the line whose `"id"` is `2` and assert
  there is **no top-level `"error"` key** (the JSON-RPC error field, sibling of
  `result`). The server emits the `initialize` response first, so read/skip lines
  until you match `id == 2` rather than assuming the first line is the answer.
  (Optional stronger check: `result.isError` is falsy — but the AC only requires
  the top-level `error` absence.)
- **Clean shutdown for AC-2.2:** when the child's stdin closes, `async for line
  in stdin` ends, the read stream closes, and the server exits cleanly. So
  `proc.stdin.close()` then `proc.wait()` yields returncode `0`. No explicit
  shutdown RPC is required (spec's "`notifications/cancelled` or closes stdin" —
  closing stdin is the simpler, reliable path).
- **10s bound (AC-2.1):** subprocess pipe reads block, so guard the read with a
  watchdog — a `threading.Timer(10, proc.kill)` armed around the read/handshake,
  or `proc.communicate(input=..., timeout=10)` if the whole exchange is written
  up front. Prefer the interactive readline loop with a timer so a hang fails
  loudly instead of deadlocking the suite.
- **PATH check for AC-2.3:** `if shutil.which("aspark-graph") is None:
  pytest.skip("aspark-graph not on PATH; run under 'uv run'")` at the top of the
  test.

### Alternatives considered and rejected

- **Put the empty-query guard in `cli.py` and `server.py`.** Rejected: violates
  the load-bearing thin-adapter rule (adapters compute no answers). It would
  also duplicate the check in two places and risk CLI/MCP divergence — the exact
  failure mode NFR-2/AC-1.4 exist to prevent. The guard belongs at the single
  shared query surface.
- **Raise `ValueError` (or a domain error) for an empty query.** Rejected (A1,
  Q1): breaks the return-data contract every other query honours for
  "no results", forces callers into try/except for a vacuous (not erroneous)
  query, and — because both adapters pass the query through unvalidated — would
  surface as a traceback at the CLI/MCP edge, violating the "clean errors, never
  tracebacks" non-negotiable (NFR-3).
- **`query.strip() == ""` (also guard whitespace-only).** Rejected for now: Out
  of Scope per spec §6 / C8. Whitespace normalization rules (strip only? collapse?)
  are unspecified; adding them is speculative gold-plating (YAGNI). Guard exactly
  `""`.
- **Put the smoke test in the default run.** Rejected (A2, Q2, AC-2.4):
  subprocess spawn is non-trivial and machine-variable (1–3 s). The `slow` marker
  + `addopts = "-m 'not slow'"` exclusion is the established v0.4.0 pattern for
  wall-clock-sensitive tests; the smoke test runs in `/peer-review` via
  `-m slow` (NFR-4).
- **Test HTTP/remote transport instead of stdio.** Rejected: the server has no
  HTTP mode — it is stdio-only FastMCP (`server.py:112` `mcp.run()`). Lifting the
  `mcp` cap to reach OAuth/HTTP is explicitly Out of Scope (spec §6, C9;
  CLAUDE.md cap note).
- **New MCP client library / test dependency to drive the handshake.** Rejected
  (NFR-5): the wire format is newline-delimited JSON we can hand-roll in ~30
  lines of stdlib. A new dep would be a liability that buys nothing.
- **Reuse a committed pre-built graph fixture for US-2.** Rejected (A3, Q3):
  inline `build_graph()` + `graph.save()` into `tmp_path` keeps the test
  self-contained with no external precondition or checked-in binary graph to
  keep in sync.

### Consequences

- **Easier:** empty queries are now unambiguous; a whole class of "silent full
  graph" bugs is closed with one line. Transport regressions from an in-range
  `mcp` bump become detectable before release.
- **Harder / watch:** the smoke test couples to the JSON-RPC handshake shape. If
  a future in-range `mcp` bump changes the handshake, this test will (correctly)
  fail — that is its job, but the failure message must point at the wire format,
  not read as a mystery. Keep the handshake helper small and commented with the
  file:line references above.

## 2. Affected Components

| Component | Change | Non-negotiable in play |
|---|---|---|
| `src/aspark_graph/queries.py` (`find_nodes`, ~line 313) | Add one early-return guard for `query == ""` | Thin adapters; clean errors; determinism |
| `src/aspark_graph/cli.py` | **No change** — adapter inherits the guard | Thin adapters |
| `src/aspark_graph/server.py` | **No change** — adapter inherits the guard | Thin adapters; CLI≡MCP parity |
| `tests/test_navigation.py` | New unit tests for US-1 (AC-1.1/1.2/1.5) | NFR-1 (existing tests stay green) |
| `tests/test_cli_mcp_parity.py` | New parity test for the empty-query case (AC-1.3/1.4, NFR-2) | CLI≡MCP parity |
| `tests/test_mcp_transport.py` (**new**) | Subprocess stdio smoke test, `@pytest.mark.slow` | mcp cap; NFR-4/5 |
| `pyproject.toml` | **No change** (the `slow` marker + `addopts` already exist) | No new deps |

## 3. Task Breakdown

Walking-skeleton note: T1+T2 land a runnable, verified vertical slice (guard +
CLI/MCP parity proof) first; T3 (the heavier subprocess test) builds on the
already-shipped `serve` path and carries the integration risk, so it goes last.

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | Add `query == ""` early-return guard at the top of `queries.find_nodes`, returning `{"query": query, "type": type, "count": 0, "nodes": []}` | US-1 | AC-1.1, AC-1.2, AC-1.5, NFR-3 | – | done | `find_nodes(graph, "")` returns `count: 0, nodes: []` with `type: None`; `find_nodes(graph, "", type="Story")` returns `count: 0, nodes: []` with `type: "Story"`; a non-empty query is byte-for-byte unchanged; no other lines in `find_nodes` touched |
| T2 | Add US-1 tests: unit tests in `tests/test_navigation.py` (AC-1.1/1.2/1.5) + an empty-query parity test in `tests/test_cli_mcp_parity.py` (AC-1.3/1.4) | US-1 | AC-1.1, AC-1.2, AC-1.3, AC-1.4, AC-1.5, NFR-1, NFR-2, NFR-3 | T1 | done | New tests assert the exact empty-result dict for both no-filter and type-filter cases; a CLI run of `query find_nodes --repo <path> ""` exits 0, prints the empty dict, and its stdout equals the MCP tool's dict; a non-empty regression test stays green; full `uv run pytest` green with no edits to existing navigation expectations |
| T3 | Add `tests/test_mcp_transport.py`: build a fixture inline in `tmp_path` (`build_graph()` + `graph.save()`), spawn `aspark-graph serve`, run the `initialize` → `notifications/initialized` → `tools/call staleness` handshake over newline-delimited JSON-RPC, assert a valid JSON response with no top-level `error`, then close stdin and assert exit 0. `@pytest.mark.slow`; skip if `aspark-graph` not on PATH | US-2 | AC-2.1, AC-2.2, AC-2.3, AC-2.4, NFR-4, NFR-5 | – | done | `uv run pytest -m slow -q` runs the test green: response for `id:2` parses as JSON and has no top-level `error` key within 10s (AC-2.1); subprocess exits 0 after stdin close (AC-2.2); `shutil.which("aspark-graph") is None` → `pytest.skip` (AC-2.3); test is `@pytest.mark.slow` and absent from the default `uv run pytest` run (AC-2.4); `pyproject.toml` unchanged, stdlib-only imports (NFR-4/5) |

No task is an orphan; every Must AC (AC-1.1–1.5, AC-2.1–2.4) and every NFR maps
to a task above.

## 4. Test Strategy

### US-1 (find_nodes guard) — unit + parity, fully automatable

- **Unit (`tests/test_navigation.py`, uses the existing `sample_graph` fixture):**
  - AC-1.1: `find_nodes(graph, "")` → exactly `{"query": "", "type": None,
    "count": 0, "nodes": []}`.
  - AC-1.2: `find_nodes(graph, "", type="Story")` → exactly `{"query": "",
    "type": "Story", "count": 0, "nodes": []}` (type filter does not bypass the
    guard).
  - AC-1.5: a known non-empty query (e.g. `"US-1"` with `type="Story"`) still
    returns its match — regression guard, mirrors the existing
    `test_ac_7_1_find_nodes_by_name_and_type`.
- **Parity (`tests/test_cli_mcp_parity.py`, extends the existing pattern):**
  - AC-1.3 + AC-1.4: build the sample repo into `tmp_path`, run the CLI
    `["query", "find_nodes", "--repo", repo, ""]` (assert rc 0, capture stdout
    JSON) and call `server.find_nodes(query="", repo=repo)`; assert the two dicts
    are equal and both are the empty-result dict. Covers NFR-2 and, via rc 0 +
    no stderr traceback, NFR-3.
- **NFR-1** is covered by the whole existing suite staying green with no edits to
  prior `find_nodes` expectations.

### US-2 (stdio transport) — one subprocess smoke test, `slow`

- **`tests/test_mcp_transport.py`, `@pytest.mark.slow`, self-contained inline
  fixture** (A3): write a tiny source file into `tmp_path`, `build_graph(tmp_path)`,
  `graph.save(default_graph_path(tmp_path))`. Then spawn `aspark-graph serve`
  and drive the handshake from §1's wire-format note. Deliberately **one**
  representative round-trip (`staleness`) — the in-process parity suite already
  covers per-tool correctness; this test's job is transport, not coverage
  (spec §6).
  - AC-2.1: response for `id:2` is valid JSON with no top-level `error`, within
    10 s (watchdog timer).
  - AC-2.2: after `proc.stdin.close()`, `proc.wait()` returncode is 0.
  - AC-2.3: `shutil.which("aspark-graph") is None` → `pytest.skip(...)`.
  - AC-2.4: the `@pytest.mark.slow` marker keeps it out of the default run
    (`addopts = "-m 'not slow'"`); verified by NFR-4.
- **Deliberately manual / out of automation:** none beyond the `/peer-review`
  step of actually running `-m slow`. Everything here is machine-checkable.

### How the suite is run

- Default: `uv run pytest` (US-1 tests run; US-2 excluded).
- `/peer-review`: `uv run pytest -m slow -q` (runs the transport smoke test).

## 5. Risks & Mitigations

| # | Risk / assumption inherited | Likelihood | Mitigation |
|---|---|---|---|
| R1 | The subprocess read deadlocks if the handshake is malformed or the server never answers, hanging the suite | Med | Watchdog `threading.Timer(10, proc.kill)` (or `communicate(timeout=10)`); AC-2.1's 10 s bound is enforced in code, not left to CI. On timeout, fail with the last bytes read on stdout/stderr for diagnosis |
| R2 | `aspark-graph` not on PATH when the test runs without `uv run` → spurious failure | Med | AC-2.3: `shutil.which` guard → `pytest.skip` with a descriptive reason. Never a hard failure for a missing entry point |
| R3 | The `initialize` response is read as the `tools/call` answer (off-by-one on the stream), giving a false pass/fail | Med | Match responses by `"id"` (skip until `id == 2`); do not assume the first stdout line is the tool result |
| R4 | A4 (spec): exact JSON-RPC envelope must be right, or the server rejects the request pre-init | Low (now resolved) | Wire format verified against installed `mcp` 1.19.0 with file:line refs in §1; handshake includes `notifications/initialized`; `protocolVersion` drawn from `SUPPORTED_PROTOCOL_VERSIONS` |
| R5 | The guard accidentally changes a non-empty-query result (e.g. wrong dict shape) | Low | AC-1.5 regression test + full existing suite green (NFR-1); the change is a single early return above untouched logic |
| R6 | A future in-range `mcp` bump changes the handshake and the smoke test fails | Low (by design) | This is the test doing its job (US-2's whole purpose). Keep the handshake helper small and commented so the failure is legible and points at the wire format |
| R7 | `staleness` on the inline `tmp_path` graph returns an unexpected shape | Low | AC-2.1 only requires valid JSON with no top-level `error`; `staleness` always returns a structured dict on a built graph. Build the graph against `tmp_path` and pass `repo=str(tmp_path)` so the tool has real files to check |

---

## ✅ PLAN GATE

- [x] Every task traces to a story and an AC/NFR id; no orphan tasks, every Must AC (AC-1.1–1.5, AC-2.1–2.4) is covered
- [x] Every task has a checkable, yes/no Definition of Done
- [x] The earliest tasks (T1+T2) form a runnable, verifiable walking skeleton; integration-risky work (T3) is explicit and ordered last
- [x] Dependencies between tasks are stated
- [x] Architecture decision records context, the decision, ≥2 genuinely-considered rejected alternatives, and consequences
- [x] Test strategy names unit vs. integration vs. slow/`peer-review` for every Must story; nothing load-bearing left to unexplained manual testing
- [x] Risks, unknowns, and inherited spec assumptions (A1–A4) each have a mitigation
- [x] No new pip dependencies (NFR-5); the `mcp>=1.12,<1.20` cap is respected, not lifted
- [x] Thin-adapter, clean-errors, determinism and CLI≡MCP-parity non-negotiables are honoured by the design
- [x] Constitution respected — N/A, no `.spark/constitution.md` exists
- [x] Status set to `approved` by the user
