# CLAUDE.md — aspark-graph

Guidance for AI agents working in this repo. Part of the aSPARK product family.

## What this is

A lean, local **code-and-artifact knowledge graph** served over MCP + a CLI. It
links a repo's code (tree-sitter: TS/JS, Python, Java) with its `.spark/`
delivery artifacts, so agents can ask `story_trace` ("which code implements this
story, and did its ACs pass QA?") and `impact` ("what's the blast radius of
changing these files?"). Deterministic, offline, disposable read model.

The full spec/plan/review/qa/release trail for v0.1.0 lives in
`.spark/aspark-graph/` — read it before changing behaviour.

## Layout & the one load-bearing convention

```
src/aspark_graph/
  model.py       node/edge vocabulary, id schemes, Confidence enum
  graph.py       networkx MultiDiGraph wrapper + canonical graph.json
  build.py       full-rescan walk + per-language import resolution
  artifacts.py   .spark/ template parser (fails loudly on drift)
  queries.py     THE shared query surface — all query logic lives here
  cli.py         thin adapter over queries.py/build.py
  server.py      thin FastMCP adapter over queries.py/build.py
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
- **`implements` (task→code) is best-effort.** Only emitted where an explicit
  inline `files:` note in a plan task resolves to a real file. Its absence is
  expected, not a bug — `story_trace`/`impact` must stay correct without it.
- **Confidence tags.** Every story/AC link from `impact` carries the *weakest*
  edge confidence on its strongest path (`extracted` < `declared`). Don't
  conflate a structural code link with a declared artifact link.

## Working here

```bash
export PATH="/opt/homebrew/bin:$PATH"   # uv lives here on this machine
uv sync --extra dev
uv run pytest                # 65 tests; keep green
uv run aspark-graph build .  # writes .aspark-graph/graph.json (gitignored)
uv run aspark-graph query story_trace US-2 --repo .
```

The tool **dogfoods itself**: its own `.spark/aspark-graph/` trail is the primary
test fixture. When you touch the parser or a query, assert against that trail.

## Out of scope for v0.1.0

More languages, an LLM/NL layer, precise call-graph resolution, incremental
updates, a visualization UI, exports, HTTP/team mode. See the spec's Out-of-Scope
list. Tier-1 candidates (recorded during the build): an explicit `files:` column
in the aSPARK plan template (needs an aSPARK PR), SQLite/incremental builds, and
the F4 review nits (guard `find_nodes("")`, prune skip-dirs during the walk).
