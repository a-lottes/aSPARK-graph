# Plan: distributable-install

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Engineering Manager (`/sprint-plan`) |
| **Input** | `.spark/distributable-install/spec.md` (must be `approved`) |
| **Status** | `approved` |
| **Date** | 2026-07-16 |

> **Retroactive plan.** This work was fast-tracked at the user's request; the
> increment is already built and green (103 tests passing, clean-env install
> proven on Intel macOS x86_64). This plan documents the architecture that was
> actually chosen — with the alternatives that were genuinely tried and rejected
> during the spike — so the `.spark/` trail is honest and `/peer-review` has a
> plan to audit against. Every task below is marked `done` because it is executed
> and verified. Next step is **`/peer-review`**, not `/increment`.

## 1. Architecture Decision

<!-- Mini-ADR. The EM decides — but shows the alternatives that were rejected and why. -->

- **Context:** The MCP server dependency dragged a native transitive dependency
  (`cryptography`) into the runtime tree via a server-side auth path aspark-graph
  does not use. `cryptography` has **no macOS x86_64 wheel** and its sdist needs a
  Rust/OpenSSL toolchain, so `uv sync` fails outright on the author's Intel macOS
  13.7 host (no toolchain) — a total install block, not a nuisance (US-1, A2).
  `cryptography` is imported nowhere in `src/` (dead weight). The spec deliberately
  leaves the *mechanism* to Plan (A1/C1): it demands the outcome — a clean,
  toolchain-free cross-platform install with no unused native dependency — not a
  specific dependency edit.

  A spike established the root cause is broader than "drop the `[server]` extra".
  Candidate dependency expressions were resolved with `uv pip compile` and
  installed into throwaway envs to measure exactly where `cryptography` enters:
  - `fastmcp>=2.0` → `fastmcp==3.4.4` → `fastmcp-slim[server]` → `joserfc` →
    `cryptography==49.0.0`. Broken.
  - `fastmcp<3` (2.14.7) still pulls `joserfc` + `cryptography`. `fastmcp-slim`
    with **no** extra drops crypto but has **no server** (`from fastmcp import
    FastMCP` raises "server support not installed").
  - Even the bare official `mcp` SDK pulls `cryptography` **directly** from
    `mcp==1.20`+ (added for server-side OAuth). Measured clean boundary:
    `mcp<=1.19` is crypto-free, `mcp>=1.20` pulls it.

- **Decision:** Replace the `fastmcp` dependency with the **official `mcp` SDK,
  capped `mcp>=1.8,<1.20`**, and use its `mcp.server.fastmcp.FastMCP` class — the
  same high-level API (upstreamed FastMCP 1.0). The `<1.20` cap is the measured
  boundary below which the SDK stays crypto-free. `server.py`'s change was minimal:
  `from fastmcp import FastMCP` → `from mcp.server.fastmcp import FastMCP`, and
  `@mcp.tool` → `@mcp.tool()` (the `mcp` SDK requires the call form); `mcp.run()`
  (stdio) unchanged. Bump the package to `0.3.0` (Q1).

- **Alternatives considered:**

  | Alternative | Why rejected |
  |---|---|
  | Keep fastmcp, pin an older version without joserfc (`fastmcp==2.5.0`) + `mcp<1.17` | Resolves clean, but fastmcp 2.5.0 is incompatible with current pydantic — `TypeError: cannot specify both default and default_factory` on tool registration. Version-archaeology fragility; a pin we could not move off without re-breaking. |
  | Use `fastmcp-slim` without the `[server]` extra | Drops `cryptography`, but has **no server support at all** — `from fastmcp import FastMCP` raises "server support not installed". Removes the tool's whole reason for the dependency. |
  | Keep fastmcp latest, exclude `cryptography` via resolver constraints | Impossible: `joserfc` (any version) hard-depends on `cryptography`, and `fastmcp[server]≥2.6` hard-depends on `joserfc`. No constraint can sever a hard edge. |

- **Consequences:**
  - *Easier:* Toolchain-free install on every platform with a pure-Python wheel
    (Intel macOS x86_64, Apple Silicon, Linux manylinux, and asserted Windows);
    the runtime dependency count drops (fastmcp + joserfc + cryptography gone);
    the MCP server is finally installable on the witness host. The high-level
    `FastMCP` API and the CLI≡MCP parity contract are preserved intact.
  - *Harder:* The `<1.20` cap is a standing liability — any real auth/remote-
    transport feature must lift it deliberately and will re-pull `cryptography`
    (out of scope per Q4, and recorded as a comment in `pyproject.toml`). We now
    track the `mcp` SDK's own version churn instead of fastmcp's.

## 2. Affected Components

<!-- Files, modules, services, external dependencies. New dependencies need a justification. -->

- **`pyproject.toml`** — swap `fastmcp` → `mcp>=1.8,<1.20`; bump `0.1.0`→`0.3.0`;
  the `<1.20` cap and its rationale documented in a load-bearing comment.
- **`uv.lock`** — regenerated; must contain **zero** `cryptography` / `joserfc` /
  `fastmcp` entries; `mcp` resolves to `1.19.0`.
- **`src/aspark_graph/server.py`** — import swap + `@mcp.tool()` on all 9 tools;
  stays a thin adapter (no query logic — the load-bearing convention).
- **5 MCP-touching tests** — migrated off `fastmcp.Client` to in-process direct
  tool calls: `test_cli_mcp_parity.py`, `test_mcp_errors.py`, `test_impact_diff.py`,
  `test_staleness.py`, `test_walking_skeleton.py`.
- **`README.md`** + `tests/test_readme.py` — install-honesty (US-3): from-source
  only, no `uvx`/PyPI claim (deferred to release/Keep per Q2).
- **Dependency change (not an addition):** `mcp` is the official SDK and the direct
  successor to fastmcp — it *is* fastmcp's upstream `FastMCP`. Net runtime deps
  shrink. Parse-affecting deps (tree-sitter core + 3 grammars) are **untouched**
  and stay pinned `==` (determinism contract, A4/NFR-2).

## 3. Task Breakdown

<!-- Ordered. Every task maps to the spec by ID and has its own definition of done. -->

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | Spike: find a dependency expression that resolves without `cryptography` while keeping a working stdio FastMCP server | US-1 | AC-1.1, AC-1.2, NFR-3 | – | `done` | Measured clean boundary `mcp<1.20`; confirmed `mcp.server.fastmcp.FastMCP` is API-compatible with the existing server. |
| T2 | Swap dependency + bump version in `pyproject.toml` (`mcp>=1.8,<1.20`, `0.1.0`→`0.3.0`), document the `<1.20` cap in a comment, regenerate `uv.lock` | US-1 | AC-1.1, AC-1.2, NFR-3 | T1 | `done` | Lock has zero `cryptography`/`joserfc`/`fastmcp` entries; `mcp` resolves `1.19.0`; version reads `0.3.0`. |
| T3 | Update `server.py` to the `mcp` SDK FastMCP (import + `@mcp.tool()` on all 9 tools) | US-1 | AC-1.5, AC-1.3 | T2 | `done` | `aspark-graph serve` registers all 9 tools (`build_graph`, `story_trace`, `impact`, `gate_health`, `staleness`, `get_node`, `find_nodes`, `get_neighbors`, `shortest_path`) without error; server.py stays a thin adapter. |
| T4 | Migrate the 5 MCP-touching tests off `fastmcp.Client` to in-process direct tool calls (`@mcp.tool()` leaves the function directly callable, returning the same dict) | US-1 | AC-1.3, NFR-4 | T3 | `done` | Full suite green including the 3 formerly-deselected parity tests + `test_mcp_errors.py`; CLI≡MCP parity test passes from the direct-call harness. |
| T5 | Re-enable the full suite on the real env; retire the `.venv-test` workaround | US-1 | AC-1.3, AC-1.4, NFR-2, NFR-4 | T4 | `done` | `uv run pytest` → **103 passed**; double-build byte-identical; tree-sitter deps still `==`-pinned. |
| T6 | Build the distributable and prove a clean-env install | US-2 | AC-2.1, AC-2.2, AC-2.3, AC-2.4, NFR-1 | T5 | `done` | `uv build`; install ONLY the 0.3.0 wheel into a fresh isolated env on Intel macOS x86_64 → `cryptography` absent; `aspark-graph` console script + `build` + `query` + `serve` all work; wheel metadata (name/version/entry-point/description) correct. |
| T7 | README honesty — keep from-source install docs, no `uvx`/PyPI claim (deferred to release) | US-3 | AC-3.1, AC-3.2, AC-3.3 | T5 | `done` | `tests/test_readme.py` green; no dead-end command; MCP-server instructions use only a working entry point. |

**Coverage check (traceability spine):**
- US-1 (Must): AC-1.1 (T1,T2) · AC-1.2 (T1,T2) · AC-1.3 (T3,T4,T5) · AC-1.4 (T5) · AC-1.5 (T3) — all covered.
- US-2 (Must): AC-2.1..2.4 (T6) — all covered.
- US-3 (Should): AC-3.1..3.3 (T7) — all covered.
- US-4, US-5 (Could) and US-6 (Won't): **Out of Scope this cycle** per spec §6 / Q2 / Q5 — no tasks, by design.
- NFR-1 (T6) · NFR-2 (T5) · NFR-3 (T1,T2) · NFR-4 (T4,T5) · NFR-5 (upheld — clean-error edge unchanged, smoke-verified in T6) · NFR-6/NFR-7 (N/A per spec).

## 4. Test Strategy

<!-- What gets unit tests, what gets integration tests, what is left to /demo-day. -->

- **Unit / in-process (automated, `uv run pytest`):**
  - **MCP tools** are exercised by calling the `@mcp.tool()`-decorated functions
    directly in-process (the decorator leaves the underlying function callable and
    it returns the same dict FastMCP would serialise). This replaces the old
    `fastmcp.Client` harness — a lighter, dependency-free test path that also
    removes the reason the tests were blocked on the witness host.
  - **CLI≡MCP parity** (`test_cli_mcp_parity.py`) asserts identical answers from
    both adapters — the core guardrail that the load-bearing thin-adapter rule
    exists to protect (AC-1.3).
  - **Error surfaces** (`test_mcp_errors.py`) — query-before-build returns a clean
    dict, never a traceback (NFR-5).
  - **Determinism** — the existing byte-identical double-build test stays green
    after the dependency swap (AC-1.4 / NFR-2). Tree-sitter deps untouched.
  - **README honesty** (`test_readme.py`) — asserts no dead-end/fictional command.
- **Integration / clean-env (manual, one-time — the accepted proof per Q5):**
  - Build the 0.3.0 wheel, install it **alone** into a fresh isolated env on the
    witness platform (Intel macOS x86_64), and run `build` + `impact` end-to-end
    plus `serve` (9 tools) from the *packaged* install (US-2, NFR-1). This is the
    headline Review-provable signal (C2) and is deliberately manual — a standing
    multi-OS CI matrix (US-5) is Out of Scope this cycle (Q5).
- **Deliberately left to release/Keep (not this cycle):** live-index (`uvx`/`pipx`)
  install proof (US-4) and Windows demonstration (Q3) — asserted from wheel
  availability, no host available to demonstrate.
- **Evidence already collected:** full suite **103 passed** (incl. the 3 formerly-
  deselected parity tests); double-build byte-identical; clean-env wheel install on
  Intel macOS with `cryptography` absent and both entry points working; resolved
  runtime tree = `mcp<1.20,>=1.8`, `networkx>=3.2`, tree-sitter core + 3 grammars —
  no package present solely for unused functionality (NFR-3).

## 5. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| The `<1.20` cap is a silent liability: a future `mcp`-SDK feature or a real auth/remote-transport story re-pulls `cryptography` and re-breaks Intel-macOS install | High — regresses the exact failure this cycle fixed | Cap documented with rationale in `pyproject.toml`; lifting it is gated to a deliberate auth/remote spec (Q4, Out of Scope). Clean-env install remains the release-gate proof so a regression is caught before publish. |
| `mcp` SDK version churn — a resolver could pick a version whose FastMCP API drifts | Medium — server could fail to register tools | `uv.lock` pins the resolved version (`1.19.0`); the full suite (incl. `serve` tool-registration + parity) must stay green on any lock bump. Floor raised `>=1.8` → **`>=1.12`** (review F2) — the lowest version verified to expose the `FastMCP` / `@mcp.tool()` API + directly-callable-decorator contract, so a lock-less downstream install stays API-compatible. |
| "Runs anywhere" is proven on only one witness platform; Linux manylinux and Windows are asserted from wheel availability, not demonstrated | Medium — an unforeseen platform-specific dep could still surface | All runtime deps are pure-Python or ship manylinux/macOS/Windows wheels (verified in the resolved tree); Q3 explicitly scopes Windows as best-effort/Could; a standing multi-OS matrix (US-5) is a named future story, not a silent gap. |
| Inherited assumption A5 (install honesty): if release later publishes to PyPI, README `uvx`/PyPI docs must not be added until the package is genuinely installable that way | Low — but breaks the honesty rule if violated | `test_readme.py` guards against dead-end commands; US-4 docs are explicitly a release/Keep action (Q2), not this cycle. |

---

## ✅ PLAN GATE

*All boxes checked → `/increment` may start. Any box open → back to `/sprint-plan`.*

*(Retroactive plan: the increment is already built and verified. Hand-off is to
`/peer-review`, which audits the completed work against this plan. The final box
stays open — only the user sets status `approved`.)*

- [x] Spec status is `approved` (never plan against a draft)
- [x] Architecture decision includes rejected alternatives (three real ones from the spike)
- [x] Architecture respects the constitution's technical constraints — N/A, no `.spark/constitution.md`; the project non-negotiables (determinism, thin-adapter parity, clean errors) are upheld
- [x] Every task maps to a user story — no orphan tasks, no story without tasks
- [x] Every Must AC and every applicable NFR is covered by at least one task (see coverage check in §3)
- [x] Every task has a checkable definition of done
- [x] Task order respects dependencies
- [x] Test strategy covers every Must story (US-1, US-2)
- [x] Status set to `approved` by the user *(2026-07-16)*
