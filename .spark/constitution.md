# Constitution: aspark-graph

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Scope** | Project-wide — binds every SPARK phase and every feature |
| **Owner** | The user (amended via `/charter`) |
| **Status** | `active` |
| **Date** | 2026-11-09 |

## 1. Product Principles

- Deterministic and offline beats clever: same repo state, same graph, byte for byte; no network, no LLM layer.
- Honest absence beats a wrong link: an unknown or ambiguous link is omitted or tagged `inferred`, never guessed.
- CLI and MCP give identical answers, because one shared query surface (`queries.py`) backs both.
- We serve developers and agents working on repos with aSPARK `.spark/` trails. A visualization UI, HTTP/team mode and remote/authenticated MCP are out of scope until amended.

## 2. Project Profile & Active Lenses

- **Project type(s):** `cli` (`pyproject.toml` `[project.scripts] aspark-graph`). It is also a local stdio MCP server, but has no HTTP routes, UI or importable public API.
- **Characteristics:** none detected — no auth, PII, SQL database or i18n; the persisted graph is a disposable JSON file.

| Lens | Why it's active (or off) | Enforced in |
|---|---|---|
| `cli` | active — terminal entrypoint with stdout/stderr and exit-code contracts ("clean errors, never tracebacks") | `/story-time`, `/peer-review` |
| `security` | off — no characteristic trigger met; `SECURITY.md`, the confinement rule and §4/§6 carry the protection | — |
| `library` / `api` / `observability` | off — no importable API, no HTTP; stdio MCP only | — |
| `seo` / `ux` / `data` / `i18n` | off — no UI, database or locales | — |

- **Active-lens load:** 1 lens active.

## 3. Technical Constraints

- **Stack / runtime:** Python >=3.11, hatchling, uv (`uv.lock`), networkx MultiDiGraph, tree-sitter extractors (Python, TS/JS, Java, Go, Rust), MCP via the official `mcp` SDK (stdio, no auth).
- **Patterns to follow:** `cli.py` and `server.py` are thin adapters with no query logic; all query logic lives in `queries.py`. A new refusal is raised in the shared module and caught/rendered once each in `cli.py` and `server.py`.
- **Off-limits:**
  - Lifting the `mcp>=1.12,<1.20` cap or the `pydantic<2.14` cap alone — they are lifted together, only with a real auth/remote-transport feature.
  - Loosening the `==` pins on tree-sitter core and the five grammars.
  - Any environment variable, flag or tool parameter that disables repo confinement.
  - Publishing the sdist by gitignore subtraction — it stays an explicit `include` allowlist.
  - Network access at build or query time.

## 4. Quality Bars (Definition of Done defaults)

- **Testing:** `uv run pytest` is green before merge (a convention; no CI exists). `pytest -m slow` runs for releases. The byte-identical double-build test is kept. Parser/query changes are asserted against the repo's own `.spark/` trails. A change that could perturb graph output is proven against pre-change code (stash round-trip), not only a double build.
- **Accessibility:** n/a — no UI.
- **Performance:** the incremental-build benchmark (NFR-1, slow) stays passing.
- **Security:** repo confinement applies to all nine tools; build bounds (entry-count bound, 5 MB per-file cap, symlink-cycle termination) hold; graph output is untrusted data. `SECURITY.md` claims are held by `tests/test_security_doc.py`.

## 5. Conventions

- **Naming / structure:** modules as laid out in `CLAUDE.md` under `src/aspark_graph/`; extractors under `extractors/`.
- **Commits / branches:** feature branches merged via GitHub PRs; commit styles in use are `T<n>, ...: ... (US-n)` task commits, `feat(x):`, `docs(x):`, `fix(deps):`, `release(vX.Y.Z):`.
- **Language:** all artifacts, code and reports in English.

## 6. Non-Negotiables

- The graph rebuilds byte-for-byte on an unchanged repo (AC-1.2).
- Template drift fails loudly with `TemplateDriftError` naming the file; never silently skipped (AC-1.3).
- Domain errors are one-line messages with a non-zero exit, never tracebacks.
- Git inference attributes a commit to exactly one feature, or contributes no edge (AC-1.4).
- Every `impact` story/AC link carries the weakest edge confidence on its strongest path.
- No confinement bypass, in tests or production.
- Never ask for or handle a credential's value; diagnose by variable name or file existence only.
- Never resume an interrupted `/go-live` from a prior report alone; re-verify version, HEAD, tags and release state from the repo.

## 7. Delivery & Handoff

- **Release mode:** `direct` (default; no external approver declared).
- Other fields: defaults.

## 8. QA Method

- **Browser-observable surface:** `no`
- **Substitute verification method:** performed and recorded in `qa.md` under each AC/NFR ID: full suite plus slow tests, clean-environment install of the built wheel, `serve` boot without the lock (`tests/test_fresh_install.py`), byte-identical double build, and a real-repo `impact`/`story_trace` check.

## 9. Project Context

- **Shape:** `brownfield`

**Product brief**

- **Primary user:** `inferred from README.md` — developers and AI agents on repos carrying aSPARK `.spark/` trails.
- **Problem today:** `inferred from CLAUDE.md` — no deterministic, offline way to ask "which code implements this story, did its ACs pass QA?" or "what is the blast radius of this change?".
- **Smallest version:** `not stated` (v0.1.0 base: see `.spark/aspark-graph/`).
- **Success signal:** `not stated`.
- **Stack:** `inferred from pyproject.toml`.
- **Non-negotiables:** `inferred from CLAUDE.md` — see §6.

**System picture**

- **Stack & entry points:** `inferred from pyproject.toml, src/aspark_graph/cli.py, src/aspark_graph/server.py`.
- **Module structure:** `inferred from CLAUDE.md` — shared `queries.py` behind thin CLI and MCP adapters.
- **Data model:** `inferred from src/aspark_graph/model.py, graph.py` — networkx graph persisted as canonical `.aspark-graph/graph.json` (gitignored, disposable) plus a parse-cache sidecar.
- **Test practice:** `inferred from pyproject.toml, tests/` — pytest (319 default + 4 `slow`), run via `uv run pytest`.
- **Conventions:** `inferred from CLAUDE.md`; no `CONTRIBUTING.md` (`not found`).
- **How to run:** `inferred from CLAUDE.md, README.md` — `uv sync --extra dev`, `uv run aspark-graph build .`, or `uvx aspark-graph serve`.
- **Known pain points:** `inferred from .spark/BACKLOG.md` — git <2.15, monorepo subprojects and `--filter=tree:0` limits (G11); `__version__` stale at 0.1.0; no CI config found.

## 10. Companions

- **Offered in version:** `0.17.0`
- **aspark-graph:** `declared installed`
- **aspark-guard:** `declared installed`

---

## Amendments

| Date | Change | Why |
|---|---|---|
| 2026-11-09 | Initial constitution | Project kickoff |
| 2026-11-12 | §9 Known pain points: G6 dropped | `qa-multi-table` reads every QA table (spec C6) |
