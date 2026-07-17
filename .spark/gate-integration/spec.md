# Spec: gate-integration

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (`/story-time`), Designer (`/look-and-feel`) |
| **Status** | `approved` |
| **Date** | 2026-07-17 |
| **Target version** | `0.3.1` (patch — docs/prompt-only, no code/API change; Q2) |

## 1. Problem & Goal

<!-- The PO's interrogation result. Not what the user asked for — what they actually need. -->

- **Problem:** aSPARK's own review and QA gates already do, by hand, exactly the
  two things aspark-graph was built to answer — and they reference aspark-graph
  in **zero** places. Concretely:
  - The **Reviewer** (`/peer-review`, `reviewer.md`) is told to "trace each
    Must-story `AC-n.m` to the code that implements it" and to "get the diff"
    via git — then it greps and reads `.spark/` files by hand to find the
    story/AC blast radius of that diff. That is precisely `impact <changed
    files>` + `story_trace <US-n>` per Must-story + `gate_health <feature>`.
  - The **QA-Tester** (`/demo-day`, `qa-tester.md`) is told "the acceptance
    criteria are your test plan" and must verify every AC — re-deriving which
    ACs exist and which have QA checks by reading files. That is
    `story_trace`/`gate_health`.

  So on an aSPARK repo **too large to hold in your head**, the gate agents
  re-derive the code↔story join every run — slowly, incompletely, and
  non-reproducibly — even when a deterministic graph that already computed that
  join is (or could be) connected. Who feels it: the agent (and the developer
  supervising it) running `/peer-review` or `/demo-day` on a large aSPARK
  project, who pays the grep tax every gate and can still miss a blast-radius
  hit a graph would have caught. aspark-graph the tool exists; the on-ramp that
  makes a gate actually *use* it does not.

- **Goal:** Ship, **inside aspark-graph and owned by this repo**, portable
  integration material a target aSPARK project can drop in — a copy-paste
  `CLAUDE.md` block that tells its `/peer-review` Reviewer and `/demo-day`
  QA-Tester to *scope their pass with the aspark-graph query tools instead of
  grepping*, plus honest setup docs — such that adoption is one paste + a
  documented one-time setup, and the block is **correct, portable, and honest
  about its prerequisites**. Prove the block is coherent by dropping the Reviewer
  half into this repo's own `CLAUDE.md` as a live witness. Explicitly **not** by
  editing the aSPARK plugin cache (a separate product, overwritten on update).

- **Success signal (observable):**
  1. A copy-paste-able integration block exists in this repo; every tool name
     and invocation it contains matches the **actual shipped** CLI/MCP surface
     (`impact`, `story_trace`, `gate_health`, `staleness`) with correct syntax —
     a reviewer can check each line against `aspark-graph query --help` / the
     registered MCP tools and find **no fictional tool and no wrong syntax**.
  2. The block makes graceful degradation **first-class**: it instructs the
     agent to confirm graph freshness (via `staleness`) *before* trusting a
     result, and to fall back to the ceremony's existing grep/read method if the
     graph is absent or stale — so a gate run can never come out **weaker** than
     today's manual process.
  3. Setup docs exist and are honest: connect the MCP server, **build the graph
     first**, and the staleness caveat — reusing the README's existing install
     steps rather than duplicating them (no drift).
  4. The block is **portable**: it hardcodes no repo-specific path or feature
     name, so any aSPARK project drops it in unchanged (parameters like `<changed
     files>`, `<US-n>`, `<feature>` are placeholders, not this repo's values).
  5. The Reviewer block is present and correct in **this repo's own `CLAUDE.md`**
     — a live adoption witness that the block is pasteable and coherent in at
     least one real aSPARK project.

- **Why now:** distributable-install (v0.3.0) just made aspark-graph installable
  and its two headline tools return real value. The natural next unit of value is
  *adoption*: a tool nobody's gate actually calls is "waste with a changelog
  entry." If we never build this, aspark-graph stays a tool you *can* run but
  that the gates it was designed for still never invoke — every `/peer-review`
  keeps grepping, and the join the graph computes goes unused. Honest caveat:
  nothing *breaks* without this; the gates keep working by hand. The cost of not
  building it is that the tool's whole reason to exist stays un-wired.

## 2. Target Users

<!-- Concrete personas or roles. "Everyone" is not an answer. -->

- **Primary: the maintainer/agent adopting aspark-graph into a *different*
  aSPARK-managed project** — a repo that has aspark-graph connected as an MCP
  server and a built graph, whose `/peer-review` and `/demo-day` runs should
  scope themselves with the query tools. They need a correct, honest,
  drop-in-and-go block; they are the consumer of the shipped material.
- **Secondary: the `/peer-review` Reviewer agent** (in that target project) —
  gets, via the dropped-in block, an instruction to run `impact <changed files>`
  + `story_trace <US-n>` per Must-story + `gate_health <feature>` to scope its
  correctness pass, with an explicit freshness-check-and-fallback rule.
- **Secondary: the `/demo-day` QA-Tester agent** (in that target project) — gets
  an instruction to use `story_trace`/`gate_health` to build and scope its AC
  test plan (which ACs exist, which have QA checks, their pass state), again with
  the freshness-and-fallback rule.
- **This repo itself as a live adoption witness (in scope — Q1):** aspark-graph
  drops its own Reviewer block into its own `CLAUDE.md` to dogfood the Reviewer
  wiring. The QA half is N/A here: aspark-graph is headless, so its own
  `/demo-day` does not run.
- **Explicitly NOT a target this cycle:** the aSPARK plugin/ceremony maintainer
  (editing `reviewer.md`/`qa-tester.md` or an upstream aSPARK PR is Out of
  Scope — Q4); and any project *without* aspark-graph connected and a fresh
  graph (for them the block degrades to "keep grepping", by design).

## 3. Assumptions & Open Questions

<!-- Every assumption is a risk. Open questions block the gate until answered or explicitly accepted. -->

| # | Assumption / Question | Resolution |
|---|---|---|
| A1 | The idea arrived describing a **deliverable shape** ("a CLAUDE.md integration block" + "setup docs"). This spec treats the underlying need — *the aSPARK gates should scope their pass with the aspark-graph tools instead of grepping, adoptably and honestly* — as the requirement, and leaves the exact prose, file layout and where the block physically lives (README section vs standalone drop-in file vs both) to `/sprint-plan`, except where format is load-bearing for acceptance (portability, copy-paste-ability). Original phrasing kept here. | Accepted as assumption |
| A2 | The tools the block names are **real and shipped** (v0.3.0): `impact <files>` / `impact --diff <range>`, `story_trace <US-n> [--feature f]`, `gate_health <feature>`, `staleness` — on both CLI and MCP, identical answers by construction. Verified in README/grounding. | Accepted as fact (the block references only these) |
| A3 | **Honesty is a non-negotiable** (inherited F4/US-6): docs describe only what works today. The block/setup docs must state the prerequisites plainly (MCP connected + freshly built graph) and must not imply the tools work with no setup. | Accepted as assumption (binding — US-2, US-4) |
| A4 | **Graceful degradation is a hard requirement, not a footnote.** The integration is an *accelerant*, never a hard dependency of the gate; if the graph is absent/stale the ceremony's existing grep/read fallback stays valid and the gate must not get weaker. | Accepted as assumption (binding — US-2) |
| A5 | The ceremonies run in a **separate session/agent in a separate project**, so this repo's Review gate **cannot** prove "an agent running `/peer-review` demonstrably called `impact`." What is provable here is narrower: the block exists, is copy-paste-able, names only real tools with correct syntax, is portable, and contains the freshness-and-fallback + setup instructions. Same boundary distributable-install drew ("publish-ready vs live publish"). | Accepted as assumption (defines the acceptance boundary — Q5, resolved) |
| Q1 | **Is self-dogfooding in scope this cycle?** Primary consumers are *other* aSPARK projects. Should aspark-graph also drop the Reviewer block into its **own** `CLAUDE.md` as a live adoption witness (US-5), or keep this cycle to shipping the portable material only? | **RESOLVED (2026-07-17): YES.** Also drop the Reviewer block into this repo's own `CLAUDE.md` as a live witness. US-5 promoted **Could → Must**; its DoD = the Reviewer block is present and correct in this repo's `CLAUDE.md`. |
| Q2 | **Versioning.** aspark-graph is v0.3.0 (released). This is a docs/prompt-only, additive change (no code, no graph-behaviour change). Ship as **0.3.1** (patch/docs) or **0.4.0** (new adoption feature)? | **RESOLVED (2026-07-17): `0.3.1`** (patch — docs/prompt-only, no code/API change). Affects the version string and release trail only; recorded in the header. |
| Q3 | **Is the QA-Tester half (US-3) in scope this cycle, and at what priority?** aspark-graph's own `/demo-day` is N/A (headless), so the QA wiring delivers value **only** to other projects. Keep it as a Should, defer, or promote to Must? | **RESOLVED (2026-07-17): IN, as a `Should`.** The user asked for "review AND QA gates", so it ships this cycle — but after the Reviewer core (US-1/US-2), which is the Must. |
| Q4 | **Confirm the plugin cache / upstream aSPARK PR is Out of Scope.** The user decided the deliverable is repo-owned, drop-in material — not edits to `reviewer.md`/`qa-tester.md` in the cache, nor an upstream aSPARK PR. Confirm this is a firm boundary this cycle. | **RESOLVED (2026-07-17): Out of Scope (repo-owned material only).** Confirmed firm; listed in §6. |
| Q5 | **What is the accepted proof this cycle?** The Review-provable signal is "block exists, is correct against the shipped surface, is portable, carries freshness-and-fallback + setup" (A5). An **end-to-end demonstration** in a real connected target project can be *asserted* but only *demonstrated* with a witness project and a cross-session run. Is the narrower signal the accepted DoD? | **RESOLVED (2026-07-17): the narrower DoD is accepted.** Block(s) exist, are copy-paste-able, name only real tools with correct syntax (checkable against `aspark-graph query --help`), are portable, and carry the staleness-check + grep/read fallback + setup instructions. Cross-session end-to-end behaviour is **asserted-not-demonstrated** (accepted, like distributable-install's publish boundary). US-6's live demo stays Out of Scope. |

## 4. User Stories

<!-- MoSCoW priority: Must / Should / Could / Won't. Every story needs testable acceptance criteria.
     Story and AC IDs (US-n, AC-n.m) are stable — never renumber; add new at the end. -->

### US-1 (Must): Drop-in Reviewer integration block wiring `/peer-review` to the query tools

> As the maintainer adopting aspark-graph into an aSPARK project, I want a
> copy-paste `CLAUDE.md` block that tells my `/peer-review` Reviewer to scope its
> correctness pass with `impact`/`story_trace`/`gate_health` instead of grepping,
> so that the review of a large diff finds the story/AC blast radius fast and
> reproducibly.

<!-- The core value. The block's EXISTENCE and CORRECTNESS are the deliverable;
     it names the real tools with real syntax so a target project's Reviewer can
     act on it verbatim. -->

**Acceptance criteria:**

- [ ] AC-1.1: Given this repo, when I look for the Reviewer integration material,
  then a **single copy-paste-able block** exists that a target aSPARK project can
  drop into its `CLAUDE.md` unchanged.
- [ ] AC-1.2: Given the block, when I read its Reviewer instructions, then it
  directs the Reviewer to run **`impact <changed files>` (or `impact --diff
  <range>`) on the diff**, **`story_trace <US-n>` per Must-story**, and
  **`gate_health <feature>`** to scope the correctness pass — mapping onto
  `reviewer.md`'s "trace each Must-story `AC-n.m` to the code" and "get the diff"
  steps.
- [ ] AC-1.3: Given the block, when I check every tool name and invocation it
  contains against the **actually shipped** CLI/MCP surface (`aspark-graph query
  --help` / the registered MCP tools), then **every one matches** — no fictional
  tool, no wrong flag, no wrong argument shape.
- [ ] AC-1.4: Given the block, when I inspect it for repo-specific values, then it
  contains **no** hardcoded path or feature name from this repo — invocations use
  placeholders (`<changed files>`, `<US-n>`, `<feature>`) so any aSPARK project
  uses it unchanged (portability; see NFR-3).
- [ ] AC-1.5: Given the block, when I read how it tells the Reviewer to interpret a
  result, then it states that a graph hit is **scoping input, not a verdict** — the
  Reviewer still traces and judges the code — and it references the confidence
  tiers (`inferred` < `extracted` < `declared`) so an `inferred` hit is treated as
  a hint to confirm, not a fact.

### US-2 (Must): Graceful degradation and honesty baked into the block

> As the maintainer, I want the integration block to make the agent confirm the
> graph is fresh before trusting it and fall back to grep/read otherwise, so that
> adopting aspark-graph can never make a gate weaker than doing it by hand.

<!-- First-class requirement, not a footnote. The gate must not silently degrade
     because the graph was stale/missing and the agent trusted it. This cuts
     across US-1, US-3 and US-5. -->

**Acceptance criteria:**

- [ ] AC-2.1: Given the block, when I read its preconditions, then it instructs the
  agent to **check `staleness` (and that a graph is built at all) *before*** relying
  on any `impact`/`story_trace`/`gate_health` result.
- [ ] AC-2.2: Given the block, when the graph is **absent or stale**, then the block
  instructs the agent to **fall back to the ceremony's existing grep/read method**
  and to say so — the fallback is explicitly stated to remain valid, and the pass
  proceeds without the tools.
- [ ] AC-2.3: Given the block, when I read how it frames the integration, then it
  states plainly that the tools are an **accelerant, never a hard dependency** of
  the gate — a run with no/stale graph is **no weaker** than today's manual pass.
- [ ] AC-2.4: Given the block, when the tools return a clean empty/`{"found":
  false}`-shaped result, then the block tells the agent to treat that as **"fall
  back / confirm manually", not as "there is nothing"** — an honest absence never
  silently narrows the review or the test plan.

### US-3 (Should): Drop-in QA-Tester integration block wiring `/demo-day` to the query tools

> As the maintainer adopting aspark-graph into an aSPARK project, I want the block
> to also tell my `/demo-day` QA-Tester to build its AC test plan from
> `story_trace`/`gate_health`, so that the tester scopes coverage (which ACs exist,
> which have QA checks, their pass state) instead of re-deriving it by reading files.

<!-- The second half of the deliverable (Q3: IN as a Should, after the Reviewer
     core). Value accrues only to OTHER (UI-bearing) projects — aspark-graph's own
     /demo-day is N/A (headless). -->

**Acceptance criteria:**

- [ ] AC-3.1: Given the block, when I read its QA-Tester instructions, then it
  directs the QA-Tester to use **`story_trace <US-n>`** and **`gate_health
  <feature>`** to enumerate the ACs to test and their existing QA-check/pass
  state — scoping the test plan `qa-tester.md` builds from "the acceptance
  criteria are your test plan".
- [ ] AC-3.2: Given the block, when I read the QA-Tester instructions, then they are
  explicit that graph output **scopes** the test plan but **never replaces
  performing the steps** — an AC is `pass` only after observed browser steps
  (preserving `qa-tester.md`'s "if you didn't see it, it didn't happen").
- [ ] AC-3.3: Given the QA-Tester instructions, when the graph is absent/stale, then
  the same freshness-check-and-fallback rule as US-2 applies (the tester falls back
  to reading the spec's ACs directly).
- [ ] AC-3.4: Given the block, when I check the QA-Tester tool references against the
  shipped surface, then every tool name and invocation matches (as US-1's AC-1.3,
  for the QA half).

### US-4 (Must): Honest setup & adoption docs

> As the maintainer, I want setup docs that tell me to connect the MCP server and
> build the graph first, with the staleness caveat, so that I don't paste the block
> and then get nothing/stale answers because the prerequisites weren't met.

<!-- The deliverable's (b) half. The block is dangerous without honest prerequisite
     docs. Reuse the README's existing install/build steps — do not duplicate and
     drift. -->

**Acceptance criteria:**

- [ ] AC-4.1: Given the repo, when I look for adoption instructions for the block,
  then setup docs exist that state the two prerequisites — **(1) aspark-graph's MCP
  server connected in the target project**, and **(2) the graph built first
  (`aspark-graph build .`)** — as an ordered, followable sequence.
- [ ] AC-4.2: Given the setup docs, when I read the freshness guidance, then the
  **staleness caveat is stated**: the graph is a rebuildable read model that can go
  stale, `staleness` reports whether it still matches the repo, and a stale graph
  must be rebuilt (or the block's fallback applies).
- [ ] AC-4.3: Given the setup docs, when I compare them to the README, then they
  **reference/reuse** the README's existing "Install", "Add to Claude Code as an MCP
  server", and "Build the graph" steps rather than **restating** them — no second
  copy of the install commands that could drift from the README.
- [ ] AC-4.4: Given the setup docs, when I follow them exactly on a target project,
  then I reach a state where the block's tools would work (server connected, graph
  built) **with no dead end and no step that only works in *this* repo**.

### US-5 (Must): Dogfood the Reviewer block in aspark-graph's own `CLAUDE.md`

> As the maintainer, I want aspark-graph to drop its own Reviewer block into its own
> `CLAUDE.md` as a live adoption witness, so that the block is proven pasteable and
> coherent in at least one real aSPARK project (this one).

<!-- Promoted Could → Must (Q1: YES). The QA half is N/A here (headless). This is the
     one concrete, in-repo adoption proof the narrower DoD (Q5) accepts. -->

**Acceptance criteria:**

- [ ] AC-5.1: Given this repo, when I read its `CLAUDE.md`, then the Reviewer
  integration block is **present** and **matches** the shipped drop-in block (US-1)
  — same tool references and syntax, verified against `aspark-graph query --help`.
- [ ] AC-5.2: Given this repo's `CLAUDE.md`, when I read how the block applies here,
  then it is **honest** that a `/peer-review` in *this* repo must have a built,
  fresh graph to use the tools, and otherwise falls back per US-2 (no implication
  that it works with no local graph).
- [ ] AC-5.3: Given this repo's `CLAUDE.md`, when I check for the QA half, then the
  QA-Tester block is **absent or explicitly marked N/A here** — aspark-graph is
  headless, so its own `/demo-day` does not run; only the Reviewer wiring is
  dogfooded (no dead QA instruction pointing at a ceremony this repo never runs).

### US-6 (Won't, this version): Everything on the Out-of-Scope list

> Recorded so the "no" is documented. See section 6. Includes editing the aSPARK
> plugin cache / an upstream aSPARK PR (Q4, Out of Scope), and any live end-to-end
> demonstration of a real *other* target project's gate calling the tools
> cross-session (Q5 — asserted-not-demonstrated).

## 5. Non-Functional Requirements

<!-- Each NFR is falsifiable and downstream-traceable. Inherits the project's
     honesty and clean-error non-negotiables rather than restating them. -->

| # | Category | Requirement (measurable) | How it's verified |
|---|---|---|---|
| NFR-1 | Honesty / correctness (non-negotiable, inherited F4/US-6) | **Every** tool name and invocation in the block, the setup docs, and this repo's `CLAUDE.md` corresponds to a capability that works **today** on the shipped v0.3.0 surface; no fictional tool, no unshipped flag, no "works with zero setup" implication. | /peer-review checks each reference against `aspark-graph query --help` / registered MCP tools |
| NFR-2 | Graceful degradation / no gate weakening (first-class) | The block contains an **explicit** freshness precondition (`staleness`/build check) **and** a grep/read fallback path; a gate run with an absent/stale graph is demonstrably **no weaker** than the current manual ceremony (the fallback is the current ceremony). | /peer-review of the block text against US-2 ACs |
| NFR-3 | Portability across aSPARK projects | The **shipped** drop-in block contains **zero** hardcoded repo paths or this repo's feature names; all project-specific values are placeholders, so the block dropped into two different projects is identical. (The copy embedded in *this* repo's own `CLAUDE.md` per US-5 may resolve those placeholders to this repo's values — that is the point of a witness, not a portability breach.) | /peer-review: grep the shipped block for repo-specific literals; confirm placeholder-only |
| NFR-4 | Maintainability / no doc drift | Setup docs **reference** the README's install/build/MCP-add steps rather than duplicating them; there is a single source of truth for those commands. | /peer-review of the docs diff against the README |
| NFR-5 | Determinism (non-negotiable) | N/A — this cycle ships **prose/prompt material only**; it does not change the build, the graph model, serialization, or any pinned parse-affecting dependency. The double-build determinism contract is untouched. | /peer-review confirms no code/dependency change |
| NFR-6 | Security & privacy | N/A — no new data path, no network, no auth surface; the block only instructs an agent to call already-local, offline, read-only query tools. | /peer-review |
| NFR-7 | Accessibility | N/A — no graphical/human-visual interface; the artifact is Markdown prose consumed by agents and read by maintainers (same as prior cycles). | N/A |

## 6. Out of Scope

<!-- Explicitly cut. Prevents scope creep in /increment. -->

Consciously cut this cycle:

- **Editing the aSPARK plugin cache or opening an upstream aSPARK PR (Q4,
  confirmed).** The deliverable is **repo-owned, drop-in material** by explicit
  user decision. Not touching `reviewer.md`/`qa-tester.md` in
  `~/.claude/plugins/cache/...` (a separate product, overwritten on update), and
  not upstreaming the wiring into aSPARK, this cycle.
- **Any live end-to-end demonstration that a real *other* target project's
  `/peer-review` or `/demo-day` observably called the tools cross-session (Q5).**
  That requires a witness project and a separate agent session; it is
  *asserted-not-demonstrated*. The in-repo dogfood (US-5) is the one concrete
  adoption proof this cycle carries; broader cross-session proof is deferred.
- **Modifying the tools themselves** to serve the gates (new query, new output
  field, a "gate mode"). This cycle wires the *existing* v0.3.0 surface; any tool
  change is a separate spec.
- **Making aspark-graph a *hard* dependency of the gate** — e.g. instructing the
  gate to block if the graph is missing. The integration is an accelerant; the
  manual fallback always remains valid (US-2). Enforcing graph presence is
  explicitly not wanted.
- **A staleness/CI hook that auto-rebuilds the target project's graph before a
  gate.** Automating "keep the graph fresh" is a larger, separate investment; this
  cycle's honesty rule handles staleness by *instruction* (check + fall back), not
  automation.
- **Dogfooding the QA-Tester half in this repo.** aspark-graph is headless — its
  own `/demo-day` does not run — so only the Reviewer block is dogfooded (US-5,
  AC-5.3). The QA block (US-3) still ships as portable material for other
  projects.
- **Everything already Out of Scope in v0.1.0–v0.3.0** — more languages, LLM/NL
  layer, call-graph precision, incremental builds, visualization, exports,
  HTTP/team mode. Unchanged.

## 7. Clarifications

<!-- The record of the Specify-phase Clarify pass. Each resolution sharpens a
     story/NFR above or lands in Out of Scope. Unresolved → §3 and gate stays closed. -->

| # | Date | Question | Resolution |
|---|---|---|---|
| C1 | 2026-07-17 | What is the falsifiable acceptance signal for a docs/prompt deliverable with no code path to unit-test? | Narrowed to Review-provable facts: the block exists and is copy-paste-able (AC-1.1), every tool/syntax it names matches the shipped surface (AC-1.3/AC-3.4/AC-5.1), it is portable (AC-1.4/NFR-3), and it carries the freshness-and-fallback (US-2) and setup docs (US-4). Cross-session "agent actually called it" is asserted, not demonstrated (A5, Q5). |
| C2 | 2026-07-17 | Is graceful degradation a footnote or a first-class requirement? | First-class: its own Must story (US-2) with a freshness precondition + grep/read fallback + "accelerant, not a hard dependency" framing, and NFR-2. The gate must never come out weaker. |
| C3 | 2026-07-17 | Does the setup material duplicate the README (install/build/MCP-add already exist there)? | No — setup docs must **reference/reuse** the README steps, not restate them (AC-4.3, NFR-4). The new content is the gate-specific ordering (build first) + the staleness caveat. |
| C4 | 2026-07-17 | Self-dogfood scope (Q1)? | **RESOLVED: YES.** Reviewer block also lands in this repo's own `CLAUDE.md`; US-5 promoted Could → Must with a concrete DoD (AC-5.1..5.3). |
| C5 | 2026-07-17 | Versioning (Q2)? | **RESOLVED: `0.3.1`** — docs/prompt-only patch; recorded in the header. No code/API change. |
| C6 | 2026-07-17 | QA-Tester half scope/priority (Q3)? | **RESOLVED: IN as a Should** (US-3) — "review AND QA gates", but after the Reviewer core (US-1/US-2 Must). |
| C7 | 2026-07-17 | Plugin-cache edits / upstream aSPARK PR (Q4)? | **RESOLVED: Out of Scope** — repo-owned material only (§6). |
| C8 | 2026-07-17 | Accepted proof this cycle (Q5)? | **RESOLVED: narrower DoD** — block(s) exist, correct against the shipped surface, portable, carry staleness-check + grep/read fallback + setup; cross-session behaviour asserted-not-demonstrated. |
| C9 | 2026-07-17 | (Clarify pass) Does the portability NFR conflict with self-dogfooding (US-5), where this repo's `CLAUDE.md` copy *would* carry concrete values? | No — sharpened NFR-3: the **shipped** drop-in block is placeholder-only and portable; the US-5 witness copy may resolve placeholders to this repo's values without breaching portability. |
| C10 | 2026-07-17 | (Clarify pass) With the QA half dogfooded nowhere here, could a dead QA instruction land in this repo's `CLAUDE.md`? | No — AC-5.3 requires the QA block to be **absent or explicitly N/A** in this repo's `CLAUDE.md`, so no ceremony this repo never runs is pointed at. |
| C11 | 2026-07-17 | (Clarify pass) Are the per-tool argument shapes pinned so "correct syntax" is checkable? | Yes, from README/grounding: `impact <files>` / `impact --diff <range>`; `story_trace <US-n> [--feature f]`; `gate_health <feature>`; `staleness` (no args). AC-1.3/AC-3.4/AC-5.1 check each against `aspark-graph query --help`. No new question. |
| C12 | 2026-07-17 | (Clarify pass) Which Must-stories should the Reviewer block scope `story_trace`/`gate_health` on — all stories, or only Musts? | Reviewer block scopes `story_trace` per **Must-story** (AC-1.2), mirroring `reviewer.md`'s "trace each **Must-story** `AC-n.m`", and `gate_health` at the **feature** level for AC coverage. Not a new user question — folded into AC-1.2 wording. |

## 8. Design Review

<!-- Filled by /look-and-feel. Empty design review = gate stays red for UI-facing features. -->

**N/A — with reason.** Like v0.1.0–v0.3.0, this cycle adds no graphical or
human-visual interface. The deliverable is Markdown prose (an integration block +
setup docs + an entry in this repo's `CLAUDE.md`) consumed by agents and read by
maintainers. The only human-facing text — the block's instructions and the setup
docs — is captured as falsifiable acceptance criteria (US-1..US-5) and
NFR-1/NFR-4. There is no layout, visual hierarchy, or accessibility surface to
review.

- **Overall impression:** N/A (no visual UI)
- **Heuristics findings:** N/A — doc honesty and clean-error heuristics covered via ACs (NFR-1, US-2)
- **Accessibility notes:** N/A (no visual UI)
- **Design risks & required changes:** None for a prose/prompt-only change

---

## ✅ SPEC GATE

*All boxes checked → `/sprint-plan` may start. Any box open → back to `/story-time` or `/look-and-feel`.*

- [x] Problem, goal and success signal are concrete (no buzzwords, no "everyone")
- [x] Every story has testable Given/When/Then acceptance criteria
- [x] Stories are prioritized (MoSCoW) and at least one is a Must
- [x] Non-functional requirements are stated and measurable (or marked N/A with reason)
- [x] Clarify pass done: no ambiguity left unresolved or unparked
- [x] Open questions are resolved or explicitly accepted as risk *(Q1–Q5 all RESOLVED 2026-07-17 — see §3)*
- [x] Out-of-scope section is filled (something was consciously cut)
- [x] Constitution (`.spark/constitution.md`) respected — N/A, no constitution exists
- [x] Design review done for UI-facing features (or marked N/A with reason)
- [x] Status set to `approved` by the user *(2026-07-17)*
