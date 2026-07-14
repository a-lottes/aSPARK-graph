# Spec: aspark-graph

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (`/story-time`), Designer (`/look-and-feel`) |
| **Status** | `approved` |
| **Date** | 2026-07-14 |

## 1. Problem & Goal

<!-- The PO's interrogation result. Not what the user asked for — what they actually need. -->

- **Problem:** When an AI agent (or the developer supervising it) works on an
  aSPARK-managed repository that is too large to hold in one's head, it cannot
  cheaply answer two questions that aSPARK's own gates depend on:
  1. *"Which code actually implements this user story / acceptance criterion?"*
  2. *"If I change these files, which stories and acceptance criteria are in the
     blast radius — i.e. what does QA have to re-verify?"*
  Today the only tools are `Grep`/`Glob` and reading `.spark/` files by hand. The
  spec → plan → review → QA trail *is* machine-parseable and *is* linked to code
  by intent, but nothing joins the two, so the agent re-derives the link every
  time by grepping — slowly, incompletely, and non-reproducibly.
- **Goal:** Turn one aSPARK repository (its code *and* its `.spark/` artifacts)
  into a single queryable graph, and expose two answers over that graph:
  the code that realizes a story, and the story/AC blast radius of a code change.
- **Success signal (observable):** On the aSPARK repository itself, for a feature
  that has a full `.spark/` trail:
  - `story_trace(US-n)` returns the story, its ACs, the plan tasks mapped to it,
    the code entities those tasks reference (where an explicit reference exists),
    and the QA results for those ACs — with zero manual grepping — and a human
    confirms the declared trail (story → ACs → tasks → QA) is complete.
  - `impact(<changed files>)` returns the set of stories and ACs reachable from
    those files, and a human confirms no *declared* link (task→story, QA→AC) that
    exists in the artifacts is missing from the result.
- **Why now:** aSPARK already produces the structured artifact trail and is being
  adopted; the linking data is being generated and thrown away at query time.
  Honest caveat: if we never build this, aSPARK still works (agents keep the
  Grep/Glob fallback). This is an accelerant, not a prerequisite — which is
  exactly why scope is cut hard to the two tools that justify it.

## 2. Target Users

<!-- Concrete personas or roles. "Everyone" is not an answer. -->

- **Primary: the aSPARK reviewer/engineering-manager agent** running inside Claude
  Code on a repo large enough that "read every relevant file" is not viable. It
  needs a fast, deterministic answer to scope a review or assess impact before
  reading files.
- **Secondary: the developer supervising that agent**, who runs the CLI directly
  (or reads the agent's tool output) to sanity-check "does this change touch a
  story QA already signed off?".
- **Explicitly NOT a target:** users wanting a broad multi-language semantic code
  graph, natural-language code search, or a visual graph explorer. Those are
  Graphify's job and are run alongside, not replaced (see Out of Scope).
- **Not useful for:** repositories small enough to hold in your head, or repos
  with no `.spark/` artifacts — the artifact layer is the whole point.

## 3. Assumptions & Open Questions

<!-- Every assumption is a risk. Open questions block the gate until answered or explicitly accepted. -->

| # | Assumption / Question | Resolution |
|---|---|---|
| A1 | The idea arrived as a solution (tree-sitter, networkx, FastMCP, stdio-MCP, `graph.json`, Python ≥3.11). This spec deliberately records **none** of those as requirements — they are the Engineering Manager's call in `/sprint-plan`. Recorded here only as the original phrasing. | Accepted as assumption |
| A2 | The aSPARK templates (spec/plan/review/qa/release) are stable and version-identifiable; the parser may pin a supported template version and fail loudly on drift rather than guess. | Accepted as assumption |
| A3 | The plan template's task table has a `#`/Task/Story mapping but **no explicit code/files column**, so the `implements` (task→code) edge has no reliable *declared* source. **Resolved (Q1):** v0.1.0 treats `implements` as **optional/best-effort** — it links to code only where an explicit note happens to exist; `story_trace`/`impact` must be correct on the declared and extracted edges *without* it, and the missing task→code link does not make the tool "broken". **No template change and no aSPARK PR in v0.1.0.** | Resolved (Q1): best-effort in v0.1.0; a later explicit `files:` convention (aSPARK template PR) is a **Tier-1 candidate**, not v0.1.0 |
| A4 | "Blast radius" for v0.1.0 means reachability over *declared* artifact edges (`has_story`/`has_ac`/`has_task`/`maps_to`/`verifies`) and *extracted* structural code edges (`contains`/`imports`), **not** precise call-graph resolution. Static `calls` resolution is best-effort and may be omitted from v0.1.0 without failing the core goal. | Accepted as assumption |
| A5 | The three code languages named (TS/JS, Python, Java) are the v0.1.0 set. **Resolved (Q2):** all three tree-sitter extractors **must** ship in v0.1.0 (US-4 is a Must). The aSPARK repo itself is Python, so the Python extractor is immediately testable against real fixtures; TS/JS and Java need dedicated fixtures. | Resolved (Q2): all three languages are Must in v0.1.0 |
| A6 | A single deterministic full rescan per `build` is acceptable performance for v0.1.0 (no incremental/sub-second updates). | Accepted as assumption |
| A7 | The graph is a read model derived entirely from repo + `.spark/`; it is disposable and never a source of truth. Losing it costs one rebuild. | Accepted as assumption |
| A8 | MCP tools may not run in every non-interactive session; the CLI must expose the same queries so agents/CI are never blocked. | Accepted as assumption |
| A9 | **Scope-vs-timebox risk (user-accepted).** Q2 raises US-4 to a Must, so v0.1.0 must deliver **three** tree-sitter extractors, not one. This tightens the ~2-week target: three language grammars, three fixture sets, and their edge cases (imports/definitions) all in scope. The user has consciously accepted this risk; the Engineering Manager must price it into `/sprint-plan` (sequencing, or an early cut if a language slips). | Accepted as risk by the user |

## 4. User Stories

<!-- MoSCoW priority: Must / Should / Could / Won't. Every story needs testable acceptance criteria. -->

### US-1 (Must): Build a graph from code + artifacts

> As the supervising developer, I want to build a single graph from one repository's
> code and its `.spark/` artifacts with one command, so that the query tools have
> something deterministic to answer from.

**Acceptance criteria:**

- [ ] AC-1.1: Given a repository containing source files and a `.spark/<feature>/`
  directory with a `spec.md`, when I run the build command against the repo root,
  then it completes without error and reports the count of code entities and
  artifact entities added to the graph.
- [ ] AC-1.2: Given the same repository, when I run the build command twice with no
  changes in between, then the second build produces a graph with the identical set
  of nodes and edges as the first (deterministic; no LLM/network dependence).
- [ ] AC-1.3: Given a `.spark/` artifact file whose structure does not match the
  supported template version, when I run the build, then the build fails (or clearly
  flags that file) with a message naming the file and the mismatch — it never
  silently skips or guesses.
- [ ] AC-1.4: Given a repository with **no** `.spark/` directory, when I run the
  build, then it still produces a code-only graph and reports zero artifact entities,
  without error.

### US-2 (Must): Trace a story to its code and verdicts (`story_trace`)

> As the reviewer agent, I want to ask for the full thread of a user story, so that
> I can see which code claims to implement it and whether its acceptance criteria
> have passed QA — without grepping.

**Acceptance criteria:**

- [ ] AC-2.1: Given a built graph for a feature whose `spec.md` defines `US-n` with
  acceptance criteria, when I call `story_trace(US-n)`, then the result includes the
  story's title and every acceptance criterion (`AC-n.m`) declared for it.
- [ ] AC-2.2: Given a `plan.md` in which one or more tasks are mapped to `US-n`, when
  I call `story_trace(US-n)`, then the result includes exactly those tasks and their
  current status as recorded in the plan (this is the declared `has_task`/`maps_to`
  trail and must be complete and correct).
- [ ] AC-2.3: Given a `qa-report.md` that records results for `AC-n.m`, when I call
  `story_trace(US-n)`, then each acceptance criterion in the result carries its most
  recent QA result (pass/fail) as recorded (the declared `verifies` trail).
- [ ] AC-2.4: Given a `story_trace` result, when a task carries an **explicit** code
  reference, then the result links that code entity with confidence `declared`; when
  a task has **no** explicit reference, then the result returns the task with **no**
  code link and this is **not** treated as an error — the task→code (`implements`)
  edge is best-effort in v0.1.0 (see A3). Any code link that is present carries its
  confidence source (`extracted` vs. `declared`) so consumers can tell them apart.
- [ ] AC-2.5: Given a story id that does not exist in the graph, when I call
  `story_trace` with it, then I get an explicit "not found" result naming the id,
  not an empty success and not a crash.

### US-3 (Must): Assess the blast radius of a code change (`impact`)

> As the reviewer agent, I want to give a set of changed files and get back the
> stories and acceptance criteria that depend on them, so that I know what QA must
> re-verify before I approve the increment.

**Acceptance criteria:**

- [ ] AC-3.1: Given a built graph and a set of one or more files present in it, when
  I call `impact(files)`, then the result lists the code entities in those files and
  the stories and acceptance criteria reachable from them over the graph's edges.
- [ ] AC-3.2: Given a link in the artifacts that reaches a story/AC from a changed
  file's code, when I call `impact` on that file, then the corresponding story and AC
  appear in the result **wherever the connecting edges are declared or extracted**
  (`has_story`/`has_ac`/`has_task`/`maps_to`/`verifies` + `contains`/`imports`) — no
  such link is dropped. Where the only possible connection would run through the
  best-effort `implements` (task→code) edge and that edge is absent, its omission is
  **expected** and does not count as a dropped link (see A3).
- [ ] AC-3.3: Given a file that is in the repo but has no path to any story/AC in the
  graph, when I call `impact` on it, then the result explicitly reports "no affected
  stories/ACs" for that file rather than failing.
- [ ] AC-3.4: Given a file path that is not in the graph, when I call `impact` on it,
  then the result names the unknown path and still returns results for the known
  files in the same call.
- [ ] AC-3.5: Given an `impact` result, when I inspect each reported story/AC link,
  then it carries the confidence tag (`extracted`/`declared`) of the weakest edge on
  its path, so consumers never mistake a best-effort structural link for a declared one.

### US-4 (Must): Cover the three named code languages

> As the supervising developer, I want the code layer to parse TypeScript/JavaScript,
> Python, and Java, so that mixed-language aSPARK repos are covered.

<!-- Must (Q2): all three extractors ship in v0.1.0. The aSPARK repo itself is Python,
     so the Python extractor is testable against real fixtures immediately; TS/JS and
     Java are exercised via dedicated fixtures. Timebox impact recorded as A9. -->

**Acceptance criteria:**

- [ ] AC-4.1: Given a source file in **each** of TS/JS, Python, and Java, when I build
  the graph, then files, their top-level definitions (classes/functions/methods), and
  their imports are represented as nodes and edges **for all three languages** — none
  may be missing from v0.1.0.
- [ ] AC-4.2: Given a file in a language the tool does not support, when I build, then
  the file is recorded as a `File` node without definitions and the build reports it as
  unparsed — it does not fail the whole build.

### US-5 (Should): Query the graph from the CLI as an MCP fallback

> As the supervising developer or a non-interactive CI job, I want to run the same
> queries from the command line, so that the answers are available even when the MCP
> server is not running in the session.

**Acceptance criteria:**

- [ ] AC-5.1: Given a built graph, when I run the query command for `story_trace`/`impact`
  from the CLI, then it returns the same information the MCP tool of the same name returns
  for the same inputs.
- [ ] AC-5.2: Given a request for a query before any graph has been built, when I run it,
  then I get a clear message telling me to build first — not a stack trace.

### US-6 (Could): Report gate health for a feature (`gate_health`)

> As the reviewer agent, I want a list of the aSPARK gate invariants as data — orphan
> tasks, unverified ACs, open findings — so that I can flag gate violations without
> reading every artifact.

**Acceptance criteria:**

- [ ] AC-6.1: Given a feature whose plan contains a task mapped to no story, when I call
  `gate_health(feature)`, then that task is listed as an orphan task.
- [ ] AC-6.2: Given a feature with an acceptance criterion that has no passing QA record,
  when I call `gate_health(feature)`, then that AC is listed as unverified.
- [ ] AC-6.3: Given a feature with a `review-report.md` finding whose status is `open`,
  when I call `gate_health(feature)`, then that finding is listed as open.

### US-7 (Could): General graph navigation (`get_node`, `find_nodes`, `get_neighbors`, `shortest_path`)

> As an agent, I want low-level lookup and traversal over the graph, so that I can
> answer ad-hoc "what touches this?" / "how are these connected?" questions beyond the
> two headline tools.

**Acceptance criteria:**

- [ ] AC-7.1: Given a built graph, when I look up a node by id or search by name/type,
  then I get the matching node(s) with their attributes.
- [ ] AC-7.2: Given two node ids that are connected in the graph, when I request a path
  between them, then I get an ordered path of nodes and edges; given two unconnected
  ids, I get an explicit "no path" result.

### US-8 (Won't, this version): Everything on the Out-of-Scope list

> Recorded so the "no" is documented. See section 5.

## 5. Out of Scope

<!-- Explicitly cut. Prevents scope creep in /increment. -->

Consciously cut from v0.1.0 (each is a real request that will be raised — the answer is "not now"):

- **Broad language coverage** beyond the three named languages. Breadth requests →
  "run Graphify alongside; aspark-graph's product is the artifact layer, not language count".
- **An explicit task→code (`files:`) convention in the aSPARK plan template.** The
  `implements` edge stays best-effort in v0.1.0 (see A3); adding a `files:` column is a
  Tier-1 candidate requiring an aSPARK template PR, not part of this spec.
- **LLM semantic layer and natural-language queries.** Deterministic only. This is Graphify's turf.
- **Precise static call-graph resolution** (dynamic dispatch, re-exports). `calls`
  edges, if present at all, are best-effort and must not be relied on for `impact`
  correctness (see A4). Impact correctness rests on `imports`/`contains` + declared edges.
- **Incremental / sub-second updates.** Full rescan per build is the v0.1.0 model (A6).
- **Visualization UI / graph explorer.** At most a later flat dump; not in v0.1.0.
- **Exports** (Neo4j, GraphML, Obsidian) and **HTTP/team/multi-user mode.**
- **Non-code, non-`.spark/` artifact inputs** (PDFs, images, design files).
- **Modifying aSPARK itself** — wiring the graph into aSPARK's EM/reviewer agents
  (the "graph-first" agent sections and install docs) is a separate deliverable in
  the aSPARK repo, not part of this tool's v0.1.0 spec.
- **The graph as a source of truth.** It is a disposable read model; it never
  replaces the repo or the `.spark/` files (A7).

## 6. Design Review

<!-- Filled by /look-and-feel. Empty design review = gate stays red for UI-facing features. -->

**N/A — with reason.** aspark-graph v0.1.0 has no graphical or human-facing visual
interface. Its surfaces are (1) an MCP tool API consumed by agents and (2) a text CLI
for developers/CI. There is nothing to lay out, no visual hierarchy, no accessibility
surface (contrast/focus/keyboard) to review. The relevant "UX" for the CLI — clear
error messages, "build first" guidance, no stack traces to the user — is captured as
acceptance criteria (AC-1.3, AC-3.4, AC-5.2, AC-2.5). If a visualization/HTML dump is
ever brought in scope, this section must be reopened for a real design review.

- **Overall impression:** N/A (no visual UI)
- **Heuristics findings:** N/A — CLI error-handling heuristics covered via ACs above
- **Accessibility notes:** N/A (no visual UI)
- **Design risks & required changes:** None for a non-UI tool

---

## ✅ SPEC GATE

*All boxes checked → `/sprint-plan` may start. Any box open → back to `/story-time` or `/look-and-feel`.*

- [x] Problem, goal and success signal are concrete (no buzzwords, no "everyone")
- [x] Every story has testable Given/When/Then acceptance criteria
- [x] Stories are prioritized (MoSCoW) and at least one is a Must
- [x] Open questions are resolved or explicitly accepted as risk *(Q1 and Q2 resolved; scope-vs-timebox risk accepted by the user as A9)*
- [x] Out-of-scope section is filled (something was consciously cut)
- [x] Design review done for UI-facing features (or marked N/A with reason)
- [x] Status set to `approved` by the user
