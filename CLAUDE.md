# CLAUDE.md — aspark-graph

Guidance for AI agents working in this repo. Part of the aSPARK product family.

## What this is

A lean, local **code-and-artifact knowledge graph** served over MCP + a CLI. It
links a repo's code (tree-sitter: TS/JS, Python, Java) with its `.spark/`
delivery artifacts, so agents can ask `story_trace` ("which code implements this
story, and did its ACs pass QA?") and `impact` ("what's the blast radius of
changing these files?"). Deterministic, offline, disposable read model.

Full SPARK trails live under `.spark/`: `aspark-graph/` (v0.1.0, the base),
`close-the-loop/` (v0.2.0 — git-history inference of `implements` edges,
`staleness`, `impact --diff`, the `inferred` tier), `distributable-install/`
(v0.3.0 — dropped the native `cryptography` dep, MCP now on the official `mcp`
SDK), `gate-integration/` (v0.3.1 — portable aSPARK gate integration blocks,
31-test doc-introspection harness, Reviewer block dogfooded in CLAUDE.md).
**Current shipped version: 0.3.1.** Read the relevant trail before changing
behaviour.

## Layout & the one load-bearing convention

```
src/aspark_graph/
  model.py       node/edge vocabulary, id schemes, Confidence enum
  graph.py       networkx MultiDiGraph wrapper + canonical graph.json
  build.py       full-rescan walk + per-language import resolution
  artifacts.py   .spark/ template parser (fails loudly on drift)
  queries.py     THE shared query surface — all query logic lives here
  cli.py         thin adapter over queries.py/build.py
  server.py      thin adapter over queries.py/build.py (mcp-SDK FastMCP)
  inference.py   git-history inference of implements edges (v0.2.0)
  git.py         offline, deterministic git helpers (no timestamps)
  extractors/    code_py / code_ts / code_java + base + dispatch
```

**Load-bearing rule:** `cli.py` and `server.py` are *thin adapters* — they parse
args / register tools and call `queries.py`. They contain **no query logic**.
This is what makes CLI and MCP return identical answers (a parity test asserts
it). Adding a query = add the function in `queries.py`, then a one-line entry in
each adapter. Never compute an answer in an adapter.

## Non-negotiables (each retired a real risk — don't regress)

- **Determinism (AC-1.2).** The graph must rebuild byte-for-byte on an unchanged
  repo. Persistence is canonical (sorted nodes/edges, `sort_keys`). Parse-
  affecting deps (the three tree-sitter grammars + core) are pinned `==`;
  `uv.lock` covers the rest. There is a byte-identical double-build test — keep it.
- **Fail loudly on template drift (AC-1.3).** `artifacts.py` is pinned to a
  supported template shape and raises `TemplateDriftError` naming the file + the
  mismatch. Never silently skip or guess.
- **Clean errors, never tracebacks.** Domain errors (drift, graph-not-built) are
  caught at the CLI/MCP edge → one-line message + non-zero exit. No stack traces
  to the user.
- **`implements` (task→code) is best-effort, from two sources.** A `declared`
  edge from an explicit inline `files:` note in a plan task, and an `inferred`
  edge derived from git history (`inference.py`: a commit referencing a task/story
  id links the files it touched). Its absence is expected, not a bug —
  `story_trace`/`impact` must stay correct without it.
- **Git inference resolves each commit to ONE feature before id-matching
  (`inference.py`, F1 — don't regress).** When multiple `.spark/` features reuse
  the same `T<n>`/`US<n>` numbering, a commit is attributed only to a single
  feature: a touched `.spark/<feature>/` tree is authoritative (co-touch), else the
  ids must resolve to exactly one feature; an ambiguous id-only commit contributes
  **no** edge. Honest absence beats a wrong cross-feature link (AC-1.4). Reads only
  committed state (paths + message ids, never timestamps), so it stays deterministic.
- **Confidence tags.** Every story/AC link from `impact` carries the *weakest*
  edge confidence on its strongest path (`inferred` < `extracted` < `declared`;
  `inferred` is rank 0). Don't conflate a git-inferred link with a structural code
  link or a declared artifact link.
- **MCP dep is the `mcp` SDK, capped `mcp>=1.12,<1.20` (don't lift the cap).**
  `mcp` 1.20+ hard-pulls `cryptography` (server-side OAuth we don't use), which has
  no macOS x86_64 wheel → made the tool uninstallable on Intel macOS. The stdio
  server uses no auth. Floor `>=1.12` is the lowest version verified to expose
  `mcp.server.fastmcp.FastMCP` + `@mcp.tool()` with the directly-callable-decorator
  contract the in-process test harness relies on. Lift the cap only alongside a real
  auth/remote-transport feature.

## Using aspark-graph in /peer-review (this repo)

**aspark-graph is an accelerant, not a hard dependency.** A peer-review with a
missing or stale graph is no weaker than the manual approach — grep/Read the
`.spark/` files and source directly. Do not block the gate on graph availability.

**QA-Tester half (`/demo-day`): N/A.** aspark-graph is headless (no UI); the
QA-equivalent is done hands-on in `/peer-review` (full suite, clean-env install,
`serve` boot, byte-identical build, real-repo impact check). No active demo-day
block applies here.

### Step 0 — confirm the graph is fresh first

```bash
aspark-graph query staleness
```

- If **absent or stale**: fall back to grep/Read for this run. State that you
  did so. The manual method remains valid.
- If **fresh**: proceed with the steps below.

### Step 1 — scope the blast radius of the diff

```bash
aspark-graph query impact <changed files>
```

Or from a git range:

```bash
aspark-graph query impact --diff <range>
```

### Step 2 — trace each Must-story

```bash
aspark-graph query story_trace <US-n> --feature aspark-graph
```

### Step 3 — check AC coverage and pass state

```bash
aspark-graph query gate_health aspark-graph
```

### Interpreting results

- A graph hit is scoping input, not a verdict — still trace and judge the code.
- Confidence tiers: `inferred` < `extracted` < `declared`. An `inferred` hit is
  a git-history hint; confirm before treating as established.
- An empty or `{"found": false}` result means: fall back and confirm manually.
  Absent ≠ nothing to review.

---

## Working here

```bash
export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"   # uv lives in ~/.local/bin here
uv sync --extra dev
uv run pytest                # 134 tests; keep green
uv run aspark-graph build .  # writes .aspark-graph/graph.json (gitignored)
uv run aspark-graph query story_trace US-2 --repo .
```

The tool **dogfoods itself**: its own `.spark/` trails are the primary test
fixture, and `impact`/`story_trace` on the live repo are the real QA surface. When
you touch the parser or a query, assert against those trails.

**QA gate for this headless tool.** There is no UI, so `/demo-day` (browser QA) is
structurally N/A — the QA-equivalent (full suite, clean-env packaged install,
`serve` boot, byte-identical build, a real-repo `impact` check) is done in
`/peer-review`. Overriding the QA gate at `/go-live` is legitimate here, but record
the authorizer + reason in the release report — never a silent skip.

## Out of scope (through v0.3.0)

More languages, an LLM/NL layer, precise call-graph resolution, incremental
updates, a visualization UI, exports, HTTP/team mode, authenticated/remote MCP
transport, and a live PyPI publish (deferred; the package is install-from-source
only, so keep the README free of `uvx`/PyPI claims until it's actually published).
Tier-1 candidates (recorded during the builds): an explicit `files:` column in the
aSPARK plan template (needs an aSPARK PR), SQLite/incremental builds, the F4 review
nits (guard `find_nodes("")`, prune skip-dirs during the walk), and a thin
transport-level MCP smoke test (the parity suite now calls tools in-process).
