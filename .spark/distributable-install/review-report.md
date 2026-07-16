# Review Report: distributable-install

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | The diff of `/increment`, `.spark/distributable-install/plan.md` |
| **Status** | `passed` |
| **Date** | 2026-07-16 |

## 1. Scope

Reviewed the `distributable-install` feature (bump to `0.3.0`): the swap of the
MCP dependency from `fastmcp` to the official `mcp` SDK capped `<1.20`, the
resulting `server.py` and test-harness migration, `uv.lock` regeneration, and
README honesty changes.

**In scope (reviewed):**
- `pyproject.toml` — dependency swap, version bump, `<1.20` cap comment
- `uv.lock` — regenerated tree
- `src/aspark_graph/server.py` — import swap + `@mcp.tool()` on all 9 tools
- `tests/test_cli_mcp_parity.py`, `tests/test_mcp_errors.py`,
  `tests/test_impact_diff.py`, `tests/test_staleness.py`,
  `tests/test_walking_skeleton.py` — migration to in-process direct tool calls
- `README.md` — install-honesty prose
- `.gitignore`, `.python-version` — incidental, low-weight

**Not reviewed (out of scope, by instruction):** `src/aspark_graph/inference.py`,
`tests/test_inference.py`, and `.spark/close-the-loop/*` — these belong to the
separate `close-the-loop` feature (already re-reviewed and passed); they are
intermingled in the same uncommitted working tree but are not part of this
increment.

No `.spark/constitution.md` exists; the project non-negotiables from `CLAUDE.md`
(determinism, thin-adapter parity, clean errors) were applied as the standard.

## 2. Plan Conformance

Every task shipped as planned. Verified hands-on where a DoD was checkable.

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ | Spike boundary `mcp<1.20` is reflected in the pin and documented in `pyproject.toml`. Confirmed `mcp.server.fastmcp.FastMCP` is API-compatible with the existing server (all 9 tools register). |
| T2 | ✅ | `pyproject.toml`: `fastmcp>=2.0`→`mcp>=1.8,<1.20`, `0.1.0`→`0.3.0`, cap rationale documented in a load-bearing comment. `uv.lock`: **zero** `cryptography`/`joserfc`/`fastmcp` entries (grep = 0); `mcp` resolves `1.19.0`. Verified. |
| T3 | ✅ | `server.py`: `from mcp.server.fastmcp import FastMCP`; `@mcp.tool()` on all 9 tools; `run()`→`mcp.run()` unchanged. Stays a thin adapter — no query logic (load-bearing convention upheld). All 9 tools register (`server.mcp._tool_manager.list_tools()` = 9). |
| T4 | ✅ | 5 MCP-touching tests migrated to `getattr(server, tool)(**params)`. Full suite green including the formerly-deselected parity tests. See F1 for the fidelity tradeoff. |
| T5 | ✅ | `uv run pytest` → **103 passed** (reproduced). Double-build **byte-identical** (reproduced with `cmp`). Tree-sitter core + 3 grammars still `==`-pinned and untouched (no `+/-` on grammar version lines in the lock diff). |
| T6 | ✅ | Reproduced: `uv build` → `0.3.0` wheel; installed **only** the wheel into a fresh 3.13 venv → `cryptography`/`joserfc`/`fastmcp` **absent**, `aspark-graph` console script present, `build` + `story_trace` + `serve` (stdio boot + 9-tool registration) all work from the packaged install. |
| T7 | ✅ | README documents from-source install only; no `uvx`/`pipx`/PyPI claim; the "add to Claude Code" command uses a working entry point (`uv run --directory … aspark-graph serve`). `tests/test_readme.py` green. |

**Accepted plan consequence (not a finding against the code):** the `<1.20` cap
is a standing liability (plan §5 risk #1). It is honestly and thoroughly
documented in `pyproject.toml` with rationale and a "lift only alongside auth"
note, and gated to a future spec (Q4). Recorded here as accepted, per plan.

## 3. Findings

No Blockers, no Majors. Three Minors — all documentation / accepted-liability
notes; two were already named by the plan as accepted risks.

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Minor | `tests/test_cli_mcp_parity.py:24-30` (and the 4 other migrated tests) | The harness moved from `fastmcp.Client().call_tool()` (real MCP serialize → dispatch-by-name → deserialize) to `getattr(server, tool)(**params)` (direct Python call). This faithfully tests the *thing under contract* — that the `server.py` adapter returns the same dict as the `cli.py` adapter over the shared `queries.py` — but it no longer exercises the SDK transport layer: JSON arg coercion (e.g. `depth: int` arriving as a string), dispatch-by-tool-name, or dict→JSON serialization. **Why it matters:** a regression that only manifests over the wire (a non-JSON-serializable value, a coercion mismatch) would not be caught by the parity/error tests alone. **Mitigations already in place / verified:** (a) the parity tests assert equality against the *JSON-round-tripped* CLI output, so a non-serializable-shaped dict (e.g. a tuple) would diverge and fail — an indirect serializability guard; (b) the "`@mcp.tool()` returns the original callable" reliance is *self-guarding* — if a lock bump broke it, the tests fail loudly rather than passing falsely (verified: `server.story_trace` is a plain, directly-callable function with the original signature); (c) I booted `serve` over stdio from the clean-env packaged install this review — it starts and its JSON-RPC layer handles input, closing the "does it dispatch at all" gap for this cycle. **Suggested fix (optional, next cycle):** keep one thin transport-level smoke test (or a `/demo-day` step) that drives a real client so arg-coercion/serialization stays covered as the SDK version moves. | accepted by user (2026-07-16) — tradeoff documented; a transport-level smoke test is parked for a future cycle |
| F2 | Minor | `pyproject.toml:25` (`mcp>=1.8,<1.20`) | The `>=1.8` floor is **never exercised**: `uv.lock` pins `1.19.0` and every resolution (dev env and the clean wheel install) picks the highest in-range = `1.19.0`. A downstream consumer who `pip install`s the distributed wheel does **not** carry the maintainer's `uv.lock`, so they resolve the open range fresh; if anything in their environment constrains `mcp` lower they could land on an untested version whose `FastMCP` / `@mcp.tool()` surface differs from what the suite validates. **Why it matters:** US-2/US-4 are explicitly about the *distributed artifact*, and the lock's protection does not travel with the wheel. (Risk is modest — `mcp.server.fastmcp` and the `@mcp.tool()` call form have been stable since well below 1.8 — but it is asserted, not tested.) **Suggested fix:** raise the floor toward the version actually tested/known-good, or add a floor-pinned smoke resolution, so "what we ship supports" equals "what we test." **Fixed (post-review, fix-mode):** floor raised `>=1.8` → `>=1.12` — the lowest version verified (in a throwaway env) to expose `mcp.server.fastmcp.FastMCP` with the `@mcp.tool()` API and the "decorated function stays directly callable" contract the in-process test harness relies on (1.12 and 1.14 checked good, 1.16/1.19 already in use). A downstream lock-less `pip install` now resolves an API-compatible mcp. `pyproject.toml` comment updated with the rationale; `uv.lock` regenerated (still `1.19.0`, still crypto-free); full suite **103 passed**; wheel rebuilt. | fixed |
| F3 | Nit | `pyproject.toml:25` / resolved tree | The `mcp` SDK still hard-pulls its HTTP/SSE server-transport stack — `uvicorn`, `starlette`, `sse-starlette`, `httpx`, `httpx-sse`, `python-multipart`, `pydantic-settings` — none of which the stdio-only tool uses. A literal reading of AC-1.2 / NFR-3 ("no dependency present *solely* to serve unused functionality") is therefore not fully met. **Why it's only a Nit:** the spec-targeted acute harm — the *native* `cryptography` with no x86_64 wheel — is gone (verified absent); these ride-alongs are unavoidable hard deps of the official SDK (no stdio-only extras split exists), and they are all pure-Python wheels that install toolchain-free, which is the actual pain point the feature fixed. Recorded for honesty, not actionable this cycle. | accepted by user (2026-07-16) — unavoidable pure-Python SDK hard deps; recorded for honesty |

**Fixed directly by the reviewer:** none. All three findings are design/judgment
or accepted-liability notes with no obvious low-risk mechanical fix; nothing was
edited.

## 4. Requirements Traceability

| Spec ID | Implemented / verified at | Verdict |
|---|---|---|
| AC-1.1 (toolchain-free install, no crypto compile) | `pyproject.toml:25` + `uv.lock` (no crypto/joserfc/fastmcp); reproduced clean wheel install | ✅ met |
| AC-1.2 (crypto & auth-only deps absent) | Clean-env `importlib.metadata` scan: `cryptography`/`joserfc`/`fastmcp` absent | ✅ met (see F3 for the SDK transport ride-alongs) |
| AC-1.3 (no regression; CLI≡MCP parity) | `test_cli_mcp_parity.py` + full suite 103 passed | ✅ met (fidelity caveat F1) |
| AC-1.4 (byte-identical double build; grammars `==`) | Reproduced `cmp` byte-identical; lock grammar pins untouched | ✅ met |
| AC-1.5 (server registers all 9 tools) | `server.mcp._tool_manager.list_tools()` = 9, names match spec | ✅ met |
| AC-2.1 (wheel installs into fresh isolated env, console script on PATH) | Reproduced: `uv build` + wheel-only install into fresh 3.13 venv; `aspark-graph` on PATH | ✅ met |
| AC-2.2 (`build` + a query end-to-end from packaged install) | Reproduced: `build .` (160 code/139 artifact entities) + `story_trace` returned expected result | ✅ met |
| AC-2.3 (`serve` from packaged install) | Reproduced: `serve` boots over stdio, 9 tools registered, JSON-RPC layer live | ✅ met |
| AC-2.4 (metadata: name/version/entry point/description correct) | Wheel metadata `aspark-graph` / `0.3.0` / description present; `aspark-graph` script entry works | ✅ met |
| AC-3.1/3.2/3.3 (README honesty, no dead-end command) | README install = from-source only; MCP command uses working entry point; `test_readme.py` green | ✅ met |
| NFR-2 (determinism) | Byte-identical double build reproduced; grammars `==`-pinned & untouched | ✅ met |
| NFR-3 (dependency hygiene) | No crypto/joserfc/fastmcp; committed lock resolves the trimmed set | ✅ met (F3 caveat noted honestly) |
| NFR-4 (full suite green incl. formerly-skipped MCP tests) | 103 passed, reproduced | ✅ met |
| NFR-5 (clean errors, no traceback) | `test_mcp_errors.py` green; query-before-build returns a clean dict | ✅ met |
| NFR-1 (cross-platform install) | Intel-macOS witness is the plan's evidence; I reproduced the clean-env install on this host. Linux/Windows asserted from wheel availability (Q3) | ✅ met on witness / asserted elsewhere per spec |

## 5. What Was Checked

- [x] Correctness: logic does what the acceptance criteria demand — all 9 tools register and answer; parity holds; clean-env entry points work
- [x] Non-functional: determinism (byte-identical rebuild), dependency hygiene (no crypto), clean errors all hold
- [x] Error handling: query-before-build returns a clean dict, not a traceback; `serve` JSON-RPC errors are the SDK's own (out of NFR-5 scope)
- [x] Security: no secrets, no new input-trust surface; dropping the auth dep removes no offered capability (NFR-6 N/A confirmed)
- [x] Tests: exist, are meaningful, and pass (103) — with the F1 fidelity caveat recorded
- [x] Readability: `server.py` stays a thin adapter; the `<1.20` cap is well-documented; migrated tests carry explanatory comments

## 6. Verdict

**PASS.** This is a small, disciplined dependency swap that does exactly what the
spec demanded and no more: the native `cryptography`/`joserfc`/`fastmcp` chain is
gone, the graph still rebuilds byte-for-byte, all 9 MCP tools register, and I
reproduced the headline proof myself — a `0.3.0` wheel installs alone into a
fresh isolated env on this host with `cryptography` absent and `build` + a query
+ `serve` all working end-to-end. The full suite is green (103). The three
findings are all Minor/Nit and honest-trail notes, not defects: the test-harness
migration genuinely trades away transport-layer fidelity (F1) but the contract it
exists to protect — CLI≡MCP parity over the shared query module — is still
faithfully exercised, the lost dispatch coverage is compensated by the clean-env
`serve` boot I verified, and the risky assumption is self-guarding; the untested
`>=1.8` floor (F2) and the SDK's unused HTTP transport deps (F3) are real but
modest and, in F3's case, unavoidable with the official SDK. None block the gate;
none require a re-spin. The plan's `<1.20` liability is documented, not hidden.
Ship it.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`.*

- [x] No open Blocker findings
- [x] No open Major findings (F1–F3 are Minor/Nit; none require a waiver)
- [x] Every Must AC traces to implementing code; no constitution non-negotiable violated (determinism, thin-adapter parity, clean errors all upheld)
- [x] All plan deviations documented and accepted (no deviations; the `<1.20` cap is an accepted, documented consequence)
- [x] Test suite runs green (103 passed, reproduced)
- [x] Status set to `passed`
