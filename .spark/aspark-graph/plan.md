# Plan: aspark-graph

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Engineering Manager (`/sprint-plan`) |
| **Input** | `.spark/aspark-graph/spec.md` (`approved`) |
| **Status** | `approved` |
| **Date** | 2026-07-14 |

## 1. Architecture Decision

<!-- Mini-ADR. The EM decides — but shows the alternatives that were rejected and why. -->

- **Context:** The spec asks for a *deterministic, no-LLM, no-network* read model
  that joins a repository's code (TS/JS, Python, Java — all three Must, per A5/A9)
  with its `.spark/` artifacts, and answers two headline queries (`story_trace`,
  `impact`) over a typed graph. The tool ships as an MCP server *and* a CLI (US-5,
  A8), against a ~2-week timebox that A9 flags as tight. This is a brand-new
  standalone repo — no existing codebase culture to inherit, so "respect the
  codebase" here means *establish* a lean, boring one that the aSPARK family can
  recognize (shared `aspark-*` naming, MIT, honest docs). The aSPARK repo itself is
  Python, which makes Python the only language dogfoodable against real fixtures on
  day one.

- **Decision:** Build in **Python ≥3.11 (uv-managed)** with **FastMCP** for the MCP
  stdio server, **py-tree-sitter** + per-language grammar packages for code
  extraction, and **networkx** as the in-memory typed graph — traversal algorithms
  (`get_neighbors`, `shortest_path`, reachability for `impact`) come free and
  battle-tested. Persist the graph as a **single `graph.json`** under
  `.aspark-graph/` at the repo root (gitignorable, node-link JSON via networkx).
  The MCP tools and the CLI are **thin adapters over one shared query module** so
  US-5's "same answer from CLI and MCP" (AC-5.1) is true by construction rather than
  by discipline. Persistence and the extractor set are chosen for the *dullest thing
  that solves the Must stories* — SQLite and incremental rescans are explicitly
  deferred to Tier 1.

- **Alternatives considered:**
  | Alternative | Why rejected |
  |---|---|
  | **TypeScript + official MCP SDK** (named in the sketch; nicer `npx` distribution for the Claude Code crowd) | We would hand-roll or wrap graph algorithms that networkx gives for free, and juggle tree-sitter WASM bindings for three grammars. Python's py-tree-sitter + networkx + FastMCP is the shorter path to the two Must queries inside the A9 timebox. `uvx aspark-graph` is an acceptable install today; revisit TS at Tier 1 if `npx` reach matters. Dogfooding is also cheaper in Python — the aSPARK repo is Python. |
  | **SQLite persistence** (sketch's "when size demands it") | v0.1.0 targets "can't hold it in your head" repos, not "won't fit in RAM" repos (A6: full rescan per build is fine). A single `graph.json` is zero-schema, trivially diffable in tests, and disposable (A7 — losing it costs one rebuild). SQLite adds a schema, migrations, and query surface we do not need yet; it is a real Tier-1 upgrade, not a v0.1.0 requirement. |
  | **Custom in-memory graph (dict-of-dicts) instead of networkx** | Saves one dependency but forces us to write and test BFS/shortest-path/reachability ourselves — the exact logic `impact` (AC-3.1/3.2) and US-7 (AC-7.2) depend on. networkx earns its dependency slot: it *replaces* code we would otherwise have to write and verify. |
  | **Regex-only artifact parsing, skip a real Markdown model** | Tempting for speed, but AC-1.3 demands failing loudly and *naming the file and mismatch* on template drift (A2). A structured, version-pinned parser that asserts the expected table shapes is the only way to satisfy "never silently skip or guess". Regex-per-field with explicit shape assertions is acceptable *inside* that parser; a raw scattershot regex pass is not. |

- **Consequences:**
  - *Easier:* Graph algorithms are free (networkx). CLI≡MCP parity is structural.
    JSON persistence is trivially assertable in fixture tests (dogfooding this very
    `.spark/aspark-graph/` trail). Python-first lets US-1/US-2/US-3 be tested against
    real artifacts before any TS/Java fixture exists.
  - *Harder:* Three tree-sitter grammars mean three sets of query patterns and edge
    cases (imports differ sharply across TS/JS vs. Python vs. Java) — this is the A9
    cost, priced into sequencing below. `graph.json` will not scale to huge repos
    (accepted, A6). FastMCP + tree-sitter native wheels must install cleanly under
    `uvx` on the target platforms — an install/packaging risk carried in §5.
    Being greenfield, we own establishing conventions (layout, error style, test
    layout) — recorded here so `/increment` follows them rather than reinventing.

## 2. Affected Components

<!-- Files, modules, services, external dependencies. New dependencies need a justification. -->

New standalone repo `aspark-graph`. Module layout (adopted from the sketch, which
already fits a lean Python package):

```
aspark-graph/
├── README.md                     ← positioning + install + CLI/MCP usage
├── pyproject.toml                ← Python ≥3.11, uv-managed, entry points for cli + serve
├── .gitignore                    ← ignores .aspark-graph/
├── src/aspark_graph/
│   ├── __init__.py
│   ├── model.py                  ← node/edge type constants, id schemes, confidence enum
│   ├── graph.py                  ← networkx wrapper: add/get nodes+edges, save/load graph.json
│   ├── extractors/
│   │   ├── base.py               ← extractor protocol + language dispatch by extension
│   │   ├── code_py.py            ← tree-sitter Python: File, defs, imports
│   │   ├── code_ts.py            ← tree-sitter TypeScript/JavaScript: File, defs, imports
│   │   ├── code_java.py          ← tree-sitter Java: File, package, classes, methods, imports
│   │   └── artifacts.py          ← .spark/ template parser (spec/plan/review/qa/release), version-pinned
│   ├── build.py                  ← orchestrates full rescan: walk repo → extractors → graph
│   ├── queries.py                ← story_trace, impact, gate_health, get_node/find_nodes/get_neighbors/shortest_path
│   ├── cli.py                    ← build / query subcommands (thin over queries.py + build.py)
│   └── server.py                 ← FastMCP stdio server (thin over queries.py + build.py)
└── tests/
    ├── fixtures/                 ← .spark/ artifact fixtures + tiny TS/Py/Java source files
    └── test_*.py
```

**External dependencies — each justified (every dependency is a liability):**

| Dependency | Why it beats writing it ourselves |
|---|---|
| **FastMCP** | The MCP stdio server surface (tool registration, protocol framing) is the integration contract with Claude Code. Re-implementing MCP wire protocol is out of proportion to the task; FastMCP is the boring, maintained choice. |
| **networkx** | Provides `shortest_path`, BFS/reachability, neighbor queries, and node-link JSON (de)serialization — the exact primitives `impact`, `shortest_path`, and persistence need. Replacing hand-written, separately-tested graph code. |
| **py-tree-sitter** | Deterministic, fast, language-agnostic parsing without an LLM (spec mandate). Hand-writing three language parsers is out of the question. |
| **tree-sitter grammar packages** (`tree-sitter-python`, `tree-sitter-typescript` incl. TSX/JS, `tree-sitter-java`) | Required by US-4/A5 — all three are Must. Each is a grammar data package, not logic; pin exact versions for determinism (AC-1.2). |
| **A CLI library** — **prefer Python stdlib `argparse`** | US-5 is a *Should*; the CLI is a thin fallback with two subcommands. stdlib `argparse` covers it with **zero** new dependencies. Adding `typer`/`click` is *not justified* for this surface and is rejected on the "40 lines ourselves" rule. Recorded as a deliberate no-new-dep decision. |

No new *services* (stdio MCP only; no HTTP — explicitly out of scope). No new
*patterns* beyond the standard Python package layout above; the one convention worth
recording is **CLI and MCP must both call `queries.py`/`build.py` and never contain
query logic of their own** — that is what makes AC-5.1 structurally true.

## 3. Task Breakdown

<!-- Ordered. Every task maps to a story from the spec and has its own definition of done.
     /increment works through this table top to bottom — nothing else — and keeps Status current. -->

Ordering principle: the **walking skeleton (T1–T3)** produces something runnable
end-to-end first — build a Python-only graph over one file and answer `get_node`
over both CLI and MCP inside Claude Code — so integration and packaging risk die
before the language matrix widens. Then the two Must queries land on the Python
extractor (dogfoodable immediately), *then* TS/JS and Java widen US-4. This ordering
is the concrete A9 mitigation: correctness of US-1/2/3 does not wait on all three
grammars.

| # | Task | Story | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|
| T1 | Repo scaffold: `pyproject.toml` (Python ≥3.11, uv), package skeleton, `.gitignore` (`.aspark-graph/`), pinned deps (FastMCP, networkx, py-tree-sitter, three grammars), test harness runnable | US-1 | – | `done` | `uv sync` succeeds from clean checkout; `uv run pytest` runs (even with 0 tests) and exits 0; `import aspark_graph` works. |
| T2 | Graph core: `model.py` (node/edge types, id schemes for `File`/`Story`/`AC`/`Task`/`Finding`/`QACheck`, `confidence` enum) + `graph.py` (add/get, save/load `graph.json` via networkx node-link) | US-1 | T1 | `done` | Unit test: build a graph in memory, save to `graph.json`, load it, assert identical nodes+edges. Round-trip is byte-stable for identical input (seeds AC-1.2). |
| T3 | **Walking skeleton**: Python extractor (`code_py.py`) for one file → File + top-level def + import nodes; `build.py` full-rescan walk; `queries.get_node`; wire `cli.py build`/`cli.py query get_node` and `server.py` (FastMCP) `get_node`; verify MCP answers inside Claude Code | US-1, US-7 | T2 | `done` | Against a fixture Python file, `cli build` writes a graph and `cli query get_node <id>` returns the node; the MCP `get_node` tool returns the same node when the server is added to Claude Code. Runs end-to-end. |
| T4 | Build command completeness for US-1: report counts (code vs. artifact entities), no-`.spark/` code-only path, deterministic double-build | US-1 | T3 | `done` | AC-1.1 (build reports both counts), AC-1.2 (two builds → identical node/edge sets, asserted by test), AC-1.4 (repo with no `.spark/` builds code-only, reports zero artifact entities, no error) all covered by tests. |
| T5 | Artifact parser (`artifacts.py`): parse spec/plan/review/qa/release; emit `Feature/Story/AC/Task/Finding/QACheck` nodes and `has_story`/`has_ac`/`has_task`/`maps_to`/`verifies`/`found_in` edges; version-pin templates; fail loudly on drift naming file+mismatch | US-1 | T4 | `done` | AC-1.3: a fixture artifact that violates the pinned template shape makes build fail (or flag that file) with a message naming the file and the mismatch — proven by test. Real `.spark/aspark-graph/spec.md` parses into the expected Story/AC nodes (dogfood fixture). |
| T6 | `story_trace(story_id)` over `queries.py`, exposed on both CLI and MCP | US-2 | T5 | `done` | AC-2.1 (title + all ACs), AC-2.2 (exactly the mapped tasks + their plan status), AC-2.3 (each AC carries most-recent QA pass/fail), AC-2.4 (task with explicit code ref → link tagged `declared`; task with none → task returned, no link, no error; any link carries `extracted`/`declared`), AC-2.5 (unknown id → explicit not-found naming the id) — each an assertion against fixtures incl. the real `.spark/aspark-graph/` trail. |
| T7 | `impact(files)` over `queries.py`, exposed on both CLI and MCP; reachability over declared + `contains`/`imports` edges; weakest-edge confidence tagging | US-3 | T6 | `done` | AC-3.1 (entities in files + reachable stories/ACs), AC-3.2 (no declared/extracted link dropped; absent best-effort `implements` not counted as dropped), AC-3.3 (file with no path → explicit "no affected stories/ACs"), AC-3.4 (unknown path named, known files still answered in same call), AC-3.5 (each link tagged with weakest edge's confidence) — all covered by fixture tests. |
| T8 | CLI-as-fallback hardening (US-5): CLI `story_trace`/`impact` == MCP output for same input; friendly "build first" message | US-5 | T7 | `done` | AC-5.1 (CLI and MCP return same info for same inputs — asserted by a test that calls the shared query fn and compares both adapters), AC-5.2 (query before any build → clear "build first" message, no stack trace). |
| T9 | TypeScript/JavaScript extractor (`code_ts.py`): File, top-level defs, imports; unsupported-language path | US-4 | T4 | `done` | AC-4.1 for TS/JS: a fixture `.ts` and `.js` file yield File + defs + imports nodes/edges. Contributes to AC-4.2 (unsupported file → File node, no defs, reported unparsed, build not failed). Can start once T4 lands (independent of the artifact/query chain). |
| T10 | Java extractor (`code_java.py`): File, package, classes, methods, imports; finalize unsupported-language handling | US-4 | T4 | `done` | AC-4.1 for Java: a fixture `.java` file yields File + class + method + import nodes/edges. AC-4.2 fully satisfied: a fixture file in an unsupported language becomes a `File` node with no defs and is reported unparsed without failing the build. |
| T11 | US-7 completion: `find_nodes(query,type?)`, `get_neighbors(id,edge_types?,depth?)`, `shortest_path(a,b)` on CLI+MCP | US-7 | T7 | `done` | AC-7.1 (lookup by id and search by name/type return matching nodes+attributes), AC-7.2 (connected ids → ordered path of nodes+edges; unconnected ids → explicit "no path"). |
| T12 | US-6 completion: `gate_health(feature)` — orphan tasks, unverified ACs, open findings | US-6 | T7 | `done` | AC-6.1 (task mapped to no story → orphan), AC-6.2 (AC with no passing QA record → unverified), AC-6.3 (`review-report.md` finding with status `open` → listed open) — against fixtures. |
| T13 | Release polish: README (positioning, "value starts at can't-hold-in-your-head size", `uvx`/`claude mcp add` install, CLI usage), clean-checkout install smoke, v0.1.0 tag prep | US-1 | T8, T10, T11, T12 | `done` | `uvx aspark-graph` (or documented equivalent) installs and runs `build`+`query` from a clean environment; README documents both surfaces; full test suite green. |

Story coverage check: US-1 → T1,T2,T3,T4,T5,T13 · US-2 → T6 · US-3 → T7 ·
US-4 → T9,T10 · US-5 → T8 · US-6 → T12 · US-7 → T3,T11. No orphan tasks; every
story has at least one task. Musts (US-1..US-4) all land by T10.

## 4. Test Strategy

<!-- What gets unit tests, what gets integration tests, what is left to /demo-day. -->

Determinism and no-network make this tool unusually testable — the strategy leans
hard on automated tests, with `/demo-day` reserved for what genuinely needs a live
session. **This is an MCP/CLI tool, not a browser app: `/demo-day` QA here is
CLI/MCP-driven, not browser-driven.** The QA template's browser/viewport/console
sections are N/A (matching the spec's Design Review N/A); QA exercises the CLI and
the MCP tools inside a real Claude Code session instead.

**Dogfooding is the backbone.** The first and highest-value fixture is *this feature's
own `.spark/aspark-graph/` trail* (`spec.md`, and `plan.md`/qa/review as they appear).
The real spec's US-n/AC-n.m are parsed and traced by the tests themselves.

- **Unit tests (pure logic):**
  - `graph.py` round-trip and byte-stable save/load (seeds AC-1.2).
  - `model.py` id schemes and confidence enum.
  - `artifacts.py` per-template parsing, incl. the **drift-failure** case naming the
    file+mismatch (AC-1.3) — the crown-jewel test.
  - Each code extractor against a tiny hand-written fixture: Python (AC-4.1 Py),
    TS/JS (AC-4.1 TS/JS), Java (AC-4.1 Java), and the unsupported-language path
    (AC-4.2).
  - Confidence-tagging logic (AC-2.4, AC-3.5) — weakest-edge-on-path computation.
- **Integration / fixture tests (against real `.spark/` artifacts):**
  - Build the graph over a fixture repo that includes a real `.spark/<feature>/` trail
    → assert counts (AC-1.1), determinism across two builds (AC-1.2), code-only build
    with no `.spark/` (AC-1.4).
  - `story_trace` against the dogfood trail: AC-2.1..AC-2.5.
  - `impact` against the dogfood trail + fixture source files: AC-3.1..AC-3.5,
    including the "unknown path + known files in same call" case (AC-3.4) and the
    best-effort-`implements`-absent-is-not-a-drop case (AC-3.2).
  - **CLI≡MCP parity (AC-5.1):** one test drives both adapters over the same shared
    query function and asserts equal output — this is the whole point of the thin-adapter
    architecture. AC-5.2 (build-first message) tested via the CLI.
  - `gate_health` (AC-6.1..6.3) and US-7 navigation (AC-7.1, AC-7.2) against fixtures.
- **Left to `/demo-day` (CLI/MCP, deliberately not automated):**
  - The MCP server actually **answering inside a live Claude Code session** — the
    protocol handshake and tool visibility cannot be fully asserted in-process; a
    human/agent confirms `story_trace`/`impact`/`get_node` respond in Claude Code.
  - The **human confirmation in the spec's success signal** — that the *declared*
    trail (story→AC→tasks→QA) returned by `story_trace` is complete, and that `impact`
    drops no declared/extracted link. This is a judgement call the spec assigns to a
    human, not an assertion; `/demo-day` records it.
  - `uvx`/`claude mcp add` **install from a clean environment** on the target
    platform (packaging + native tree-sitter wheels) — verified hands-on, not in CI
    alone.

Every Must story is covered: US-1 (T2/T4/T5 tests), US-2 (T6 tests), US-3 (T7 tests),
US-4 (T9/T10 tests). No Must relies on "manual testing only".

## 5. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| **A9 — three extractors in a ~2-week box.** US-4 raised TS/JS + Python + Java all to Must; three grammars, three fixture sets, three sets of import/definition edge cases. | High — the single most likely cause of a slipped v0.1.0. | **Sequence Python first** (T3/T5/T6/T7): it is dogfoodable against the real aSPARK/aspark-graph repo immediately, so US-1/US-2/US-3 reach *correct and tested* on Python alone before TS/Java start. TS/JS (T9) and Java (T10) are made **independent** of the query chain (both only `Depends on: T4`), so a slip in one language does not block the Must queries. **Early-cut fallback:** if a language extractor slips the box, ship it as the AC-4.2 "unparsed `File` node" path (build still succeeds, files recorded, reported unparsed) and raise the missing extractor as the first Tier-1 item — this degrades US-4 gracefully instead of failing the release. Java (least dogfoodable, most verbose grammar) is sequenced **last** as the deliberate cut candidate. **User decision (2026-07-14): the graceful-degradation fallback is pre-authorized** — if a language extractor slips the timebox, `/increment` ships it as the AC-4.2 unparsed-`File`-node path and files the full extractor as the first Tier-1 item, without stopping to ask. This means US-4 may be *partially* met at v0.1.0; that is an accepted outcome, not a defect. `/increment` must record any such cut in the plan status and the go-live learnings. |
| **Best-effort `implements` (task→code) edge (A3/Q1).** The plan template has no `files:` column, so most tasks have no declared code link. | Medium — could look like `story_trace`/`impact` are "missing" links. | Spec-sanctioned: AC-2.4/AC-3.2 make the absence *expected*, not a defect. Tests assert the absence is handled, not that the edge exists. **No template change, no aSPARK PR in v0.1.0** (Tier-1 candidate). Confidence tags make best-effort links distinguishable from declared ones. |
| **Static `calls` imprecision (A4).** Dynamic dispatch, re-exports defeat static resolution. | Medium if relied upon. | `impact` correctness rests on `imports`/`contains` + declared edges only (AC-3.2). `calls` edges are **omitted from v0.1.0's impact correctness path** (and may be omitted entirely) — they are never load-bearing. |
| **Template drift breaks the artifact parser (A2).** aSPARK templates could change shape. | Medium — silent wrong answers are the worst outcome. | Version-pin the supported template shape; parser **fails loudly naming the file and the mismatch** (AC-1.3), never guesses. This is a first-class tested behavior (T5), not a nicety. |
| **MCP not available in non-interactive sessions (A8).** Agents/CI can't rely on the server. | Medium. | US-5 CLI fallback (T8) exposes the *same* queries via the shared query module; CLI≡MCP parity is asserted (AC-5.1). Agents keep their Grep/Glob fallback regardless. |
| **Packaging: native tree-sitter wheels under `uvx` on the target platform.** Three grammar packages must install cleanly from a clean environment. | Medium — a broken install blocks adoption even if code is perfect. | Pin exact grammar versions; verify clean-checkout `uvx` install as an explicit `/demo-day` item and in T13; the walking skeleton (T3) forces the FastMCP+grammar install to work end-to-end on day one, surfacing this risk early rather than at release. |
| **Greenfield convention drift.** No existing codebase to imitate; `/increment` could improvise architecture. | Low–Medium. | This plan fixes the layout (§2) and the one load-bearing convention (CLI/MCP are thin adapters over `queries.py`/`build.py`). Deviations are review findings. |

Inherited spec assumptions this plan accepts as-is: A6 (full rescan per build), A7
(disposable read model — no migration/backup work planned), A1 (stack was the EM's
call — made above).

## 6. Deviations (recorded during `/increment`)

All 13 tasks completed as planned; the architecture (§1) and layout (§2) were
followed without change. Four small, in-scope implementation decisions worth
recording:

- **D1 — best-effort `implements` source (Q1).** The plan left the `implements`
  edge best-effort with no source. Implemented as an *optional inline* `files:`
  note inside a task row's DoD text (e.g. `… ; files: src/foo.py`), resolved to a
  `File` node only when it exists. No plan-template change and no aSPARK PR — this
  is exactly the "explicit note happens to exist" path A3/Q1 blessed. Absent note
  → no code link, not an error (AC-2.4).
- **D2 — A9 not exercised.** All three extractors landed; Java parsed cleanly, so
  the pre-authorised graceful-degradation cut was never needed. The AC-4.2 unparsed
  path is still tested (by un-registering an extractor) so the cut path is proven.
- **D3 — runtime is Python 3.14.** `uv` provisioned 3.14; the clean-install smoke
  also verified a fresh **3.11** venv, so the `>=3.11` floor holds. Native
  tree-sitter + FastMCP wheels install cleanly on both (the §5 packaging risk is
  closed).
- **D4 — added `LICENSE`.** MIT file added to match the spec/README positioning
  (not a numbered task; trivial).

---

## ✅ PLAN GATE

*All boxes checked → `/increment` may start. Any box open → back to `/sprint-plan`.*

- [x] Spec status is `approved` (never plan against a draft)
- [x] Architecture decision includes rejected alternatives (a decision without alternatives is a guess)
- [x] Every task maps to a user story — no orphan tasks, no story without tasks
- [x] Every task has a checkable definition of done
- [x] Task order respects dependencies
- [x] Test strategy covers every Must story
- [x] Status set to `approved` by the user
