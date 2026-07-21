<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/aSPARK-graph-logo-dark.png">
  <source media="(prefers-color-scheme: light)" srcset="docs/aSPARK-graph-logo-light.png">
  <img alt="aSPARK-graph logo" src="docs/aSPARK-graph-logo-light.png" width="480">
</picture>

# 🕸️ aspark-graph

> **A lean, local knowledge graph that joins a repo's _code_ to its _delivery artifacts_ — so agents and humans can trace a user story to the code that implements it, and see the story-level blast radius of a change.**

aspark-graph reads one repository — its source code **and** its
[aSPARK](https://github.com/a-lottes/aSPARK) `.spark/` delivery trail (specs,
plans, reviews, QA reports) — and builds a single queryable graph, served over a
CLI **and** an MCP server. It is **deterministic** (tree-sitter + declared
artifact links; **no LLM, no network**) and **disposable** (the graph is a
rebuildable read model, never a source of truth).

---

## The two questions it exists to answer

Everything else is in service of these:

| Question | Tool | Plain meaning |
|---|---|---|
| *"Which code implements this user story, and did its acceptance criteria pass QA?"* | `story_trace US-2` | Follow story → ACs → plan tasks → code → QA results, with zero grepping. |
| *"If I change these files, which stories and acceptance criteria are in the blast radius — what must QA re-verify?"* | `impact src/foo.py` | Walk code → tasks → stories/ACs, tagging each hit with how trustworthy the link is. |

## Why this exists

When an AI agent (or the developer supervising it) works on an aSPARK-managed
repo **too large to hold in your head**, those two questions are exactly the ones
aSPARK's own review and QA gates depend on — and today the only way to answer
them is `Grep`/`Glob` plus reading `.spark/` files by hand.

The spec → plan → review → QA trail *is* machine-parseable, and it *is* linked to
code by intent. But nothing joins the two, so an agent re-derives the link every
time it greps: **slowly, incompletely, and non-reproducibly.** aspark-graph
computes that join once, deterministically, and lets you query it.

It does this by deliberately doing **less** on the code side than a general code
graph, and adding the one thing general graphs don't have: the **delivery
artifacts**. That artifact layer is what makes story tracing, gate-aware impact,
and orphan detection possible at all.

## When to use it — and when not

- ✅ **Use it** on an aSPARK repo big enough that "read every relevant file"
  isn't viable, when you need a fast, reproducible answer *before* opening files.
- ❌ **Skip it** on a repo small enough to hold in your head (just read the
  files), or a repo with no `.spark/` artifacts (the artifact layer is the whole
  point).
- 🤝 **Want a broad semantic code graph too?** Run
  [Graphify](https://github.com/safishamsi/graphify) alongside it — different
  scope, no conflict. aspark-graph is an accelerant for aSPARK, not a replacement
  for a code-search tool.

**Using aspark-graph in aSPARK gates?** See
[`docs/aspark-integration.md`](docs/aspark-integration.md) for drop-in
`CLAUDE.md` blocks that wire the `/peer-review` and `/demo-day` gates to the
query tools.

---

## The graph model (read this to interpret any result)

The graph is a typed, directed multigraph. Every node id is **stable and
deterministic**, derived only from content and location, so two builds of an
unchanged repo produce byte-identical ids and a byte-identical `graph.json`.

**Node types**

| Layer | Types | Source |
|---|---|---|
| Code | `File`, `Class`, `Function` | tree-sitter extraction |
| Artifact | `Feature`, `Story`, `AcceptanceCriterion`, `Task`, `Finding`, `QACheck` | `.spark/` templates |

**Edge types**

| Edge | Direction | Meaning |
|---|---|---|
| `contains` | File → Class/Function | code structure |
| `imports` | File → File | resolved import |
| `calls` | Function → Function | best-effort, may be absent |
| `has_story` | Feature → Story | artifact structure |
| `has_ac` | Story → AcceptanceCriterion | " |
| `has_task` | Feature → Task | " |
| `maps_to` | Task → Story | plan links a task to the story it serves |
| `implements` | Task → File/Function | **the code↔story bridge** (best-effort; see below) |
| `verifies` | QACheck → AcceptanceCriterion | QA result for an AC |
| `found_in` | Finding → File | a review finding's location |

**Confidence tiers** — every artifact/code link carries a tier, and `impact`
reports the **weakest link on the strongest path** so you can trust a result
appropriately:

| Tier | Rank | Where it comes from |
|---|---|---|
| `declared` | strongest | an explicit `files:` note in a plan task |
| `extracted` | middle | tree-sitter (`contains`/`imports`) — deterministic structure |
| `inferred` | weakest | self-derived from git history — treat as a hint, confirm before acting |

> **Reading a result:** an `impact` hit tagged `inferred` reached the story only
> through a git-history guess; a `declared` hit rests on an author-written link.
> The tier never *raises* confidence — it reports the weakest step, so an
> inferred edge can only ever *lower* a path's trust, never mask a real one.

**Node id schemes** (useful when constructing `get_node`/`shortest_path` queries):

```
file:<relpath>                     e.g. file:src/aspark_graph/queries.py
def:<relpath>::<qualname>          e.g. def:src/foo.py::Widget.render
feature:<name>                     e.g. feature:aspark-graph
story:<feature>:<id>               e.g. story:aspark-graph:US-1
ac:<feature>:<id>                  e.g. ac:aspark-graph:AC-1.2
task:<feature>:<id>                e.g. task:aspark-graph:T3
finding:<feature>:<id>             e.g. finding:aspark-graph:F1
qa:<feature>:<ac>#<index>          e.g. qa:aspark-graph:AC-1.1#0
```

---

## Install

Requires Python ≥ 3.11 and [uv](https://docs.astral.sh/uv/). aspark-graph is not
yet published to a package index, so install it from a checkout of this
repository:

```bash
git clone https://github.com/a-lottes/aSPARK-graph.git aspark-graph
cd aspark-graph
uv sync                       # installs into a local .venv
uv run aspark-graph build .   # build the graph for the current repo
```

Add it to Claude Code as an MCP server, pointing at your checkout:

```bash
claude mcp add aspark-graph -- uv run --directory /path/to/aspark-graph aspark-graph serve
```

Until aspark-graph is published to a package index, the from-source path above is
the supported install.

## Update

```bash
cd /path/to/aspark-graph
git pull
uv sync
uv run aspark-graph build /path/to/your/repo   # rebuild after update
```

The graph is not forwards-compatible across versions: always rebuild after `git pull`.
Incremental builds (v0.4.0+) make this fast — only changed files are re-parsed, so a
routine update rebuild takes seconds on most repos.

## Build the graph

```bash
aspark-graph build [path]     # scans code + .spark/, writes .aspark-graph/graph.json
```

The graph is written to `.aspark-graph/graph.json` at the repo root (gitignore
it — it's rebuildable). Re-running `build` on an unchanged repo produces a
**byte-identical** graph. Parsing fails **loudly** on `.spark/` template drift
(it names the file and the mismatch) rather than silently guessing.

## Query

Every query is available on **both** the CLI and MCP, and they return **identical
answers by construction** (all query logic lives in one shared module; the CLI
and server are thin adapters over it, and a parity test enforces it). Output is
JSON.

### CLI

```bash
# The two headline queries
aspark-graph query story_trace US-2 --feature my-feature
aspark-graph query impact src/foo.py src/bar.py
aspark-graph query impact --diff HEAD~1..HEAD      # blast radius of a change range

# Gate & freshness
aspark-graph query gate_health my-feature          # are this feature's ACs covered / passing?
aspark-graph query staleness                        # does the graph still match the repo on disk?

# Graph navigation
aspark-graph query get_node "file:src/foo.py"
aspark-graph query find_nodes Widget --type Class
aspark-graph query get_neighbors "story:my-feature:US-1" --edge-type has_ac
aspark-graph query shortest_path "task:my-feature:T1" "ac:my-feature:AC-1.1"
```

### MCP

The same operations are exposed as MCP tools: `build_graph`, `story_trace`,
`impact`, `gate_health`, `staleness`, `get_node`, `find_nodes`, `get_neighbors`,
`shortest_path`. Querying before a build (or any domain error) returns a clean
`{"found": false, ...}`-shaped result — never a raw traceback.

## Linking code to stories

`impact` and `story_trace` are only as useful as the `implements` (task→code)
links they can find. aspark-graph establishes those links three ways, strongest
to weakest confidence:

| Confidence | Source | How to opt in |
|---|---|---|
| `declared` | An explicit `files:` note on a plan task | In `plan.md`, add `files: <path>` to a task's *Definition of Done* cell, e.g. `… ; files: src/foo.py`. The link is created only if the file exists — a dangling path is ignored, never fabricated. |
| `inferred` | Git commit history | Reference the task id **and** its story id in the commit message — subject `T3: add parser (US-1)` or a `Refs: T3, US-1` trailer. Any file that commit touched is linked to the task at `inferred` confidence. |
| `extracted` | tree-sitter (`contains`/`imports`) | Automatic — no action needed. |

**Recommendation for aSPARK repos:** make one commit per task whose message names
the task and story ids (the convention aSPARK's own workflow already encourages).
That alone lets `impact` answer on a repo that was never hand-annotated.

Inference is **deterministic** (it reads only committed state — file paths and
message ids, never timestamps) and **offline**; if git is unavailable it is
simply skipped. When multiple `.spark/` features reuse the same `T<n>`/`US-<n>`
numbering, a commit is resolved to a **single** feature before linking (by the
`.spark/<feature>/` tree it touched, or by a unique task→story pairing in its
message); a genuinely ambiguous commit contributes **no** edge — an honest
absence over a wrong cross-feature link.

## Supported languages

Code extraction covers **TypeScript/JavaScript, Python and Java** (tree-sitter).
Files in other languages are recorded as unparsed `File` nodes — the build never
fails on an unknown language.

## Design guarantees (why you can trust the output)

- **Deterministic.** Byte-identical rebuild on an unchanged repo; parse-affecting
  dependencies are pinned exactly; a double-build test enforces it.
- **Offline & LLM-free.** No network, no model calls — just AST parsing and
  artifact-template parsing.
- **Fails loudly, never silently.** Template drift raises a named error; it never
  skips or guesses.
- **Clean errors.** Domain errors (drift, graph-not-built) surface as one-line
  messages with a non-zero exit / a structured dict — never a stack trace.
- **Disposable.** The graph is a read model. Delete `.aspark-graph/` and rebuild;
  the source of truth is always the code and the `.spark/` files.

## Out of scope

Languages beyond the six currently supported, an LLM/natural-language layer, precise
call-graph resolution, a visualization UI, exports (Neo4j/GraphML/Obsidian), HTTP/team
mode, and authenticated or remote MCP transport are out of scope. The current language
support is Python, TypeScript/JavaScript, Java, Go, and Rust.

## Development

```bash
uv sync --extra dev
uv run pytest
```

The project **dogfoods itself**: its own `.spark/aspark-graph/` trail is the
primary test fixture, so touching the parser or a query is checked against a real
aSPARK trail.

## License

MIT © Andreas Lottes. Part of the aSPARK product family.
Code-graph prior art: [Graphify](https://github.com/safishamsi/graphify) —
different scope.
