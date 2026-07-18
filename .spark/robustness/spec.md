# Spec: robustness

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (`/story-time`) |
| **Status** | `approved` |
| **Date** | 2026-07-18 |

## 1. Problem & Goal

- **Problem (item 1 — `find_nodes` empty-query guard):** Calling `find_nodes`
  with an empty string returns every node in the graph. This happens because the
  implementation tests whether the query is a substring of each node's haystacks
  (`q in h.lower()`), and the empty string is a substring of every string in
  Python. An agent constructing a query expression dynamically — and accidentally
  producing an empty string — receives the full graph back and may treat it as a
  legitimate, narrowed match set. Correctness silently degrades; the caller has
  no signal that the query was vacuous.

- **Problem (item 2 — skip-dirs depth, investigated):** The concern that
  `_iter_source_files` only prunes `_SKIP_DIRS` at the top level was investigated
  against the live code. The check `any(part in _SKIP_DIRS for part in
  rel_parts[:-1])` iterates over every directory component of the path (all parts
  except the filename), so skip-dir pruning already works at all depths.
  **This is not a bug. No story is needed.** See §6 (Out of Scope).

- **Problem (item 3 — MCP transport smoke test):** Every test in the current
  suite that exercises MCP tools does so by calling the decorated functions
  in-process (the `@mcp.tool()` decorator leaves the underlying function directly
  callable). This strategy correctly proves that the query layer and the MCP
  surface are logically consistent. What it does not prove is that the stdio
  transport boundary itself works: that `aspark-graph serve` can start, receive a
  JSON-RPC `tools/call` over stdin, and return a well-formed response on stdout.
  A future `mcp` SDK version bumped within the allowed range (`>=1.12,<1.20`)
  could change the wire format without breaking any in-process call — and the
  current suite would not catch it. There is no test that does the
  subprocess round-trip today.

- **Goal:** Close the two real gaps with the least possible new code: (a) make
  `find_nodes("")` return an unambiguously empty result instead of the entire
  graph; (b) add one subprocess smoke test that exercises the stdio JSON-RPC
  boundary.

- **Success signal (observable):**
  1. `find_nodes("")` — and `find_nodes("", type="...")` — return a result with
     `count: 0` and `nodes: []`, and a new test asserts this.
  2. A subprocess smoke test spawns `aspark-graph serve`, sends one valid
     JSON-RPC `tools/call`, reads the response, and asserts the response is
     well-formed JSON containing no `error` key — and the test passes in CI
     (or under `pytest -m slow` if marked slow). Transport-level regression
     is now detectable before release.

## 2. Target Users

- **Primary (US-1): the agent or tooling developer** who calls `find_nodes`
  with a dynamically constructed query that may be empty. Today they get the
  whole graph silently; after this fix they get an empty result and can
  distinguish "no match" from "I forgot to fill in the query".

- **Primary (US-2): the aSPARK maintainer / release engineer** who needs
  confidence that `aspark-graph serve` is actually functional as a stdio MCP
  server — not just that its query logic is correct. An `mcp` SDK bump within
  the allowed range (`>=1.12,<1.20`) could break the wire protocol while all
  in-process tests stay green.

- **Explicitly NOT a target this spec:** end-users of other tools that build
  on aspark-graph; users hoping for better error messages elsewhere in the
  API; anyone expecting HTTP/remote transport coverage.

## 3. Assumptions & Open Questions

<!-- Every assumption is a risk. Open questions block the gate until answered or explicitly accepted. -->

| # | Assumption / Question | Resolution |
|---|---|---|
| A1 | `find_nodes("")` should return an empty result (`count: 0, nodes: []`) rather than raising a `ValueError`. The rationale: all other query functions (`story_trace`, `get_node`, `gate_health`, `get_neighbors`) return structured JSON for non-error "no results" cases; introducing an exception here would break the consistent return-data contract at the CLI/MCP adapter boundary and would require callers to add try/except for what is semantically a vacuous query, not a programmer error. The CLI and MCP adapters both pass query strings without validation today; a ValueError would produce a traceback at the adapter layer, which violates the "clean errors, never tracebacks" non-negotiable. | **Accepted (resolved via Q1).** |
| A2 | The MCP subprocess smoke test should be marked `@pytest.mark.slow` and excluded from the default `uv run pytest` run. Spawning a subprocess takes non-trivial wall clock time (estimated 1–3 s), and the `slow` marker + exclusion pattern is already established in `pyproject.toml`. The test will run explicitly during `/peer-review`. | **Accepted (resolved via Q2).** |
| A3 | The smoke test builds a minimal fixture inline inside `tmp_path` (via `build_graph()` + `graph.save()`), then spawns `aspark-graph serve` against that fixture. Self-contained; no external `build` precondition required. | **Accepted (resolved via Q3).** |
| A4 | The MCP wire protocol for `tools/call` follows the JSON-RPC 2.0 envelope that FastMCP (`mcp>=1.12`) speaks over stdio. The exact message structure (method, params, id) is determined from the mcp SDK; the test must send a syntactically valid message. The EM confirms the exact schema during `/sprint-plan`. | Accepted; EM verifies during implementation. |
| A5 | The `_iter_source_files` skip-dirs check was verified against the live code in `src/aspark_graph/build.py` (line 144): `any(part in _SKIP_DIRS for part in rel_parts[:-1])` iterates all directory components, not just the top-level one. No code change is needed. This assumption records that verification so the decision is not revisited without re-reading the code. | Verified and accepted. |

| Q1 | **`find_nodes("")` behavior: empty result or ValueError?** The spec assumes empty result (A1). Is that the intended behavior, or should an empty query string be treated as a caller error and raise `ValueError` with a clean message? | **Resolved: empty result.** Preserves the return-data contract; a vacuous query is not a programmer error. AC-1.1–1.4 reflect this. |
| Q2 | **MCP smoke test: `slow` marker or default run?** If the test can be structured so the subprocess spawn is ≤500 ms on a warmed Python install, it may be fast enough for the default run. Should it be `slow` by default and promoted later, or included in the default run from day one? | **Resolved: `@pytest.mark.slow`.** Subprocess spawn is non-trivially variable; the slow bucket is already established and follows the v0.4.0 precedent for wall-clock-sensitive tests. |
| Q3 | **Smoke test graph precondition:** should the test build its own fixture inline (self-contained, no external state required), or can it reuse an existing fixture and expect `build` to have been run as a precondition? | **Resolved: inline build.** The test builds a minimal fixture inside `tmp_path` using `build_graph()` + `graph.save()`, then spawns the server against that fixture. Self-contained; no external state required. |

## 4. User Stories

<!-- MoSCoW priority: Must / Should / Could / Won't. Every story needs testable acceptance criteria.
     Story and AC IDs (US-n, AC-n.m) are stable — never renumber; add new at the end. -->

### US-1 (Must): Guard `find_nodes` against an empty query string

> As an agent or developer calling `find_nodes`, I want an empty query string
> to return an empty result set rather than the entire graph, so that a
> dynamically constructed vacuous query never silently masquerades as a
> legitimate full-match result.

**Acceptance criteria:**

- [ ] AC-1.1: Given a built graph with at least one node, when `find_nodes` is
  called with `query=""` and no `type` filter, then the response is
  `{"query": "", "type": null, "count": 0, "nodes": []}` — no nodes are
  returned, and the response structure is otherwise identical to a normal
  query response (same keys, same types).
- [ ] AC-1.2: Given a built graph with at least one node, when `find_nodes` is
  called with `query=""` and a valid `type` filter (e.g. `type="Story"`), then
  the response is `{"query": "", "type": "Story", "count": 0, "nodes": []}` —
  the type filter does not bypass the empty-query guard.
- [ ] AC-1.3: Given `find_nodes` is invoked via the CLI (`aspark-graph query
  find_nodes --repo <path> ""`), when the command runs, then it exits 0 and
  prints `{"query": "", ..., "count": 0, "nodes": []}` to stdout — no
  traceback, no partial result, no silent full-graph dump.
- [ ] AC-1.4: Given `find_nodes` is invoked via the MCP surface (via the
  `find_nodes` tool with `query=""`), when the tool call completes, then it
  returns the same empty-result dict as AC-1.1 — CLI ≡ MCP parity is preserved
  for this case.
- [ ] AC-1.5: Given a non-empty query string that is a valid substring of at
  least one node's id or searchable attribute, when `find_nodes` is called,
  then it returns the matching nodes as before — the empty-query guard does not
  affect non-empty queries.

### US-2 (Must): Stdio MCP transport smoke test

> As the aSPARK maintainer, I want a test that spawns `aspark-graph serve` as a
> subprocess, sends a real JSON-RPC `tools/call` message over its stdin, and
> reads the response from stdout, so that transport-level breakage (e.g. from an
> mcp SDK update within the allowed range) is caught before release rather than
> discovered in the field.

**Acceptance criteria:**

- [ ] AC-2.1: Given a repo with a pre-built graph, when the test spawns
  `aspark-graph serve` as a subprocess and sends an MCP `initialize` handshake
  followed by a valid `tools/call` JSON-RPC request (for a simple, always-
  available tool such as `staleness`), then the subprocess returns a response on
  stdout within 10 seconds, the response parses as valid JSON, and there is no
  `error` key at the top level of the result object.
- [ ] AC-2.2: Given the smoke test subprocess exits (after the test sends a
  final `notifications/cancelled` or closes stdin), when the subprocess
  terminates, then it exits with code 0 — no lingering process, no zombie.
- [ ] AC-2.3: Given the `aspark-graph` entry point is not on `PATH` (e.g. the
  test is run without `uv run`), when the subprocess spawn fails, then the test
  is skipped with a descriptive reason rather than failing with an
  undiagnosable error.
- [ ] AC-2.4: The smoke test is in its own file (`tests/test_mcp_transport.py`)
  and is marked `@pytest.mark.slow` (or an equivalent mechanism), so that it is
  excluded from the default `uv run pytest` run and runs only when `-m slow` is
  explicitly passed — keeping the default suite fast.

## 5. Non-Functional Requirements

<!-- Cross-cutting qualities the feature must meet, separate from functional behavior.
     Inherits the project's non-negotiables rather than restating them entirely. -->

| # | Category | Requirement (measurable) | How it's verified |
|---|---|---|---|
| NFR-1 | Correctness / determinism (non-negotiable inherited) | The empty-query guard does not change the output of any `find_nodes` call with a non-empty query — verified by running the full existing test suite green with no changes to `test_navigation.py` expectations. | /peer-review: `uv run pytest` green; existing navigation tests unchanged |
| NFR-2 | CLI ≡ MCP parity (non-negotiable inherited) | `find_nodes("", ...)` returns identical output from the CLI adapter and the MCP tool — the parity invariant holds for the empty-string case (AC-1.4). | /peer-review: extend or supplement the parity suite to cover the empty-query case |
| NFR-3 | Clean errors, never tracebacks (non-negotiable inherited) | The empty-query guard path produces no Python traceback at the CLI or MCP boundary. If A1's assumption is revisited and a `ValueError` is chosen instead, the CLI adapter must catch it and emit a one-line message + non-zero exit; the MCP adapter must catch it and return a structured `{"found": false, "error": "..."}` dict. | /peer-review: invoke `find_nodes ""` on CLI; confirm no traceback |
| NFR-4 | Test suite default run not slowed | The MCP transport smoke test is excluded from `uv run pytest` (default run via `addopts = "-m 'not slow'"`). The default suite completes with no new wall-clock overhead from subprocess spawning. | /peer-review: run default suite; confirm no new subprocess is spawned |
| NFR-5 | No new pip dependencies | Neither story requires a new dependency. The empty-query guard is a one-line early return. The smoke test uses only Python stdlib (`subprocess`, `json`) plus the existing `pytest` dev dependency. | /peer-review: diff `pyproject.toml` — no additions |
| NFR-6 | Performance | N/A — neither change is on a hot path. `find_nodes("")` returns immediately with an early exit; the smoke test is in the `slow` bucket. | N/A |
| NFR-7 | Security | N/A — no new auth, network, or credential surface. The smoke test is a local subprocess; it uses the same stdio server already in production. | N/A |
| NFR-8 | Accessibility | N/A — no visual UI; headless CLI/MCP tool. | N/A |

## 6. Out of Scope

Consciously cut from this spec (each is a real candidate — the answer is "not now"):

- **Skip-dirs depth pruning fix.** Investigated as item 2 of the feature brief.
  The code at `build.py:144` — `any(part in _SKIP_DIRS for part in
  rel_parts[:-1])` — already iterates all directory components at every depth,
  not just the top-level directory. The pruning is correct as shipped. No code
  change is needed, and no story is written. This entry records the deliberate
  decision so the investigation is not repeated. (A5)

- **`find_nodes` whitespace-only query guard** (e.g. `query="   "`). A
  query of all whitespace, when lower-cased, is still a substring of everything
  and would exhibit the same silent-full-graph behavior as `""`. The minimum
  fix is the empty-string guard (US-1). Extending the guard to strip-and-check
  is a follow-on if the pattern proves valuable; adding it now would require
  specifying the exact normalization rules (strip only? also collapse?) and is
  premature.

- **Full HTTP/remote MCP transport test.** The scope of US-2 is strictly the
  stdio transport, which is the only transport the server uses. There is no
  HTTP mode, no auth, no OAuth in scope (see CLAUDE.md `mcp` cap note). A
  remote-transport test is a separate feature.

- **Structured `ValueError` / typed error response for invalid `find_nodes`
  args.** The spec decides that `find_nodes("")` returns an empty-result dict
  (A1 — open for user confirmation via Q1). A `ValueError` path with a typed
  error envelope is not in scope unless Q1 is resolved to prefer that behavior.

- **Raising the `mcp` version cap (`mcp>=1.12,<1.20`).** The smoke test
  validates the transport within the current cap, not above it. Lifting the cap
  (and thus exposing the `cryptography` wheel problem on Intel macOS) requires
  its own feature and explicit authorization — see CLAUDE.md non-negotiable.

- **Smoke testing other MCP tools** (beyond one representative call). US-2
  requires one successful round-trip to prove the transport works; it does not
  require exhaustive tool coverage. In-process parity tests already cover tool
  correctness; the smoke test's job is transport-level, not functional.

- **Improvements to `get_neighbors`, `shortest_path`, or other queries.** The
  F4 brief listed `guard find_nodes("")` and `prune skip-dirs` as the
  robustness nits; everything else in the query surface is out of scope for
  this cycle.

- **More languages, LLM/NL layer, visualization, exports, HTTP/team mode,
  published PyPI release.** Unchanged from prior cycles.

## 7. Clarifications

<!-- The record of the Specify-phase Clarify pass. Unresolved → §3 and gate stays closed. -->

| # | Date | Question | Resolution |
|---|---|---|---|
| C1 | 2026-07-17 | Is the `_iter_source_files` skip-dirs pruning actually broken? | Verified against live code (build.py:139-146): `rel_parts[:-1]` includes all directory components at every depth. The pruning is correct. No story needed. Recorded in Out of Scope and A5. |
| C2 | 2026-07-17 | What should `find_nodes("")` return — empty result or ValueError? | Spec assumes empty result (A1) to preserve the return-data contract and the "clean errors, never tracebacks" non-negotiable. Raised as Q1 for user confirmation. |
| C3 | 2026-07-17 | Should the MCP smoke test be in the default run or the `slow` bucket? | Spec assumes `slow` (A2, AC-2.4) because subprocess spawn adds non-trivial wall-clock time. Raised as Q2 for user confirmation. |
| C4 | 2026-07-17 | (Clarify pass) Does the empty-query guard break CLI ≡ MCP parity? | No — both adapters call `queries.find_nodes`, so the guard at the query layer applies to both simultaneously. Parity is preserved by construction. AC-1.4 makes this explicit. |
| C5 | 2026-07-17 | (Clarify pass) Does a `type`-only call (`find_nodes("", type="Story")`) also return empty? | Yes — AC-1.2 covers this. The type filter is applied after the empty-query guard; an empty query string returns nothing regardless of type. |
| C6 | 2026-07-17 | (Clarify pass) What JSON-RPC message structure must the smoke test send? | The exact MCP `initialize` + `tools/call` envelope is defined by the `mcp` SDK. The spec states the observable requirement (valid JSON, no top-level `error` key — AC-2.1). The specific wire format is for the EM to confirm against the SDK during `/sprint-plan`. |
| C7 | 2026-07-17 | (Clarify pass) Does the smoke test need the graph to be pre-built, and is that its own story? | No — it is a test precondition, not a user story. AC-2.1 states "given a repo with a pre-built graph." How that fixture is established (inline build in the test vs. reusing a committed fixture) is an implementation decision raised as Q3 for user confirmation. |
| C8 | 2026-07-17 | (Clarify pass) Is the whitespace-only query (`"   "`) in scope? | No — Out of Scope this cycle. The minimum fix is the empty-string guard. See §6. |
| C9 | 2026-07-17 | (Clarify pass) Could the smoke test accidentally lift the mcp cap? | No — the smoke test runs against whatever `mcp` version is installed per `pyproject.toml`. It validates the current cap, not a newer one. Cap change is explicitly Out of Scope. |

## 8. Design Review

**N/A — with reason.** Both stories are headless: US-1 is a one-line guard in a
Python function; US-2 is a test file. Neither introduces any visual surface,
layout, or user-facing interaction beyond what already exists (a JSON dict on
stdout). There is no graphical UI, no new command, and no change to help text
or output format beyond the empty-result dict. If a `find_nodes` UX improvement
(e.g. a warning message on empty queries alongside the empty result) is ever
brought in scope, this section must be reopened.

- **Overall impression:** N/A (no visual UI)
- **Heuristics findings:** N/A
- **Accessibility notes:** N/A (no visual UI)
- **Design risks & required changes:** None

---

## ✅ SPEC GATE

*All boxes checked → `/sprint-plan` may start. Any box open → back to `/story-time`.*

- [x] Problem, goal and success signal are concrete (no buzzwords, no "everyone")
- [x] Every story has testable Given/When/Then acceptance criteria
- [x] Stories are prioritized (MoSCoW) and at least one is a Must
- [x] Non-functional requirements are stated and measurable (or marked N/A with reason)
- [x] Clarify pass done: no ambiguity left unresolved or unparked
- [x] Open questions are resolved or explicitly accepted as risk *(Q1: empty result; Q2: `@pytest.mark.slow`; Q3: inline fixture build)*
- [x] Out-of-scope section is filled (something was consciously cut)
- [x] Constitution (`.spark/constitution.md`) respected — N/A, no constitution exists
- [x] Design review done for UI-facing features (or marked N/A with reason)
- [x] Status set to `approved` by the user
