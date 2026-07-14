# 🕸️ aspark-graph

> **A lean, local code-and-artifact knowledge graph that speaks SPARK.**

aspark-graph turns one repository — its code *and* its
[aSPARK](https://github.com/a-lottes/aSPARK) delivery artifacts in `.spark/` —
into a single queryable graph, served over MCP and a CLI. Agents stop grepping
and start asking:

- *"Which code implements US-2, and did its acceptance criteria pass QA?"* → `story_trace`
- *"If I change these files, which stories and acceptance criteria are in the
  blast radius?"* → `impact`

It is deterministic (tree-sitter + declared artifact edges, **no LLM, no
network**) and disposable (the graph is a rebuildable read model, never a source
of truth).

## Why this exists

Generic code graphs (e.g. [Graphify](https://github.com/safishamsi/graphify))
map code broadly. aspark-graph deliberately does **less code** and adds the one
thing they don't have: the **delivery artifacts**. Linking `.spark/` specs,
plans, reviews and QA into the code graph answers questions a pure code graph
cannot — story tracing, gate-aware impact, orphan detection.

**The value starts at "can't hold it in your head" size.** On a small repo, just
read the files. Want a broad semantic code graph too? Run Graphify alongside —
the two don't conflict.

## Install

Requires Python ≥ 3.11 and [uv](https://docs.astral.sh/uv/). aspark-graph is not
yet published to a package index, so install it from a checkout of this
repository:

```bash
git clone <this-repo-url> aspark-graph
cd aspark-graph
uv sync                       # installs into a local .venv
uv run aspark-graph build .   # build the graph for the current repo
```

Add it to Claude Code as an MCP server, pointing at your checkout:

```bash
claude mcp add aspark-graph -- uv run --directory /path/to/aspark-graph aspark-graph serve
```

> Once aspark-graph is published, a `uvx`-based one-liner will be documented
> here. Until then, the from-source path above is the supported install.

## Usage

### Build the graph

```bash
aspark-graph build [path]     # scans code + .spark/, writes .aspark-graph/graph.json
```

The graph is written to `.aspark-graph/graph.json` at the repo root (gitignore
it — it's rebuildable). Re-running `build` on an unchanged repo produces a
byte-identical graph.

### Query (CLI)

Every query is also available on the CLI, so agents and CI work even when the
MCP server isn't running in the session. Output is JSON.

```bash
aspark-graph query story_trace US-2 --feature my-feature
aspark-graph query impact src/foo.py src/bar.py
aspark-graph query impact --diff HEAD~1..HEAD      # blast radius of a change range
aspark-graph query gate_health my-feature
aspark-graph query staleness                       # does the graph still match the repo?
aspark-graph query get_node "file:src/foo.py"
aspark-graph query find_nodes Widget --type Class
aspark-graph query get_neighbors "story:my-feature:US-1" --edge-type has_ac
aspark-graph query shortest_path "task:my-feature:T1" "ac:my-feature:AC-1.1"
```

### Query (MCP)

The same operations are exposed as MCP tools (`build_graph`, `story_trace`,
`impact`, `gate_health`, `staleness`, `get_node`, `find_nodes`, `get_neighbors`,
`shortest_path`) — the CLI and MCP return identical answers by construction.

## Linking code to stories

`impact` and `story_trace` are only as useful as the `implements` (task→code)
links they can find. aspark-graph establishes those links in three ways, from
strongest to weakest confidence:

| Confidence | Source | How to opt in |
|---|---|---|
| `declared` | An explicit `files:` note on a plan task | In `plan.md`, add `files: <path>` to a task's *Definition of Done* cell, e.g. `… ; files: src/foo.py`. The link is created only if the file exists (a dangling path is ignored, never fabricated). |
| `inferred` | Git commit history | Reference the task id **and** its story id in the commit message — subject `T3: add parser (US-1)` or a `Refs: T3, US-1` trailer. Any file touched by that commit is linked to the task at `inferred` confidence. |
| `extracted` | tree-sitter (`contains`/`imports`) | Automatic — no action needed. |

**Recommendation for aSPARK repos:** make one commit per task whose message
names the task and story ids (the same convention aSPARK's own workflow already
encourages). That alone lets `impact` answer on a repo that was never
hand-annotated. `impact` always tags each result with the weakest link on its
path, so you can tell an `inferred` blast-radius hit from a `declared` one.
Inference is deterministic (it reads only committed state, never timestamps) and
offline; if git is unavailable it is simply skipped.

## Supported languages

Code extraction covers **TypeScript/JavaScript, Python and Java** (tree-sitter).
Files in other languages are recorded as unparsed `File` nodes — the build never
fails on an unknown language.

## What it does *not* do (v0.1.0)

More languages, an LLM/natural-language layer, precise call-graph resolution,
incremental updates, a visualization UI, exports (Neo4j/GraphML/Obsidian), and
HTTP/team mode are all out of scope. See `.spark/aspark-graph/spec.md` for the
full, honest Out-of-Scope list.

## Development

```bash
uv sync --extra dev
uv run pytest
```

The project dogfoods itself: its own `.spark/aspark-graph/` trail is the primary
test fixture.

## License

MIT © Andreas Lottes. Part of the aSPARK product family.
Code-graph prior art: [Graphify](https://github.com/safishamsi/graphify) —
different scope.
