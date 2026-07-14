# Spec: close-the-loop

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (`/story-time`), Designer (`/look-and-feel`) |
| **Status** | `approved` |
| **Date** | 2026-07-14 |

## 1. Problem & Goal

<!-- The PO's interrogation result. Not what the user asked for — what they actually need. -->

- **Problem:** v0.1.0 shipped a correct, tested graph and two headline tools
  (`impact`, `story_trace`) — but on real repositories those tools deliver
  **latent, not realised, value**. The evidence is the tool's own repo, which is
  the best possible case (a complete, gate-passed `.spark/` trail): the built
  graph has **zero `implements` (code→artifact) edges**, and `impact` on a
  central source file returns **no affected story or acceptance criterion**. The
  cause is a conscious v0.1.0 decision (spec A3/Q1): the task→code link only
  exists where a plan task happens to carry an inline `files:` note, and real
  aSPARK plans do not write those. So the one link that connects a *code change*
  to the *stories QA must re-verify* is almost never present, and the blast-radius
  question — the whole reason a reviewer would reach for this tool — comes back
  empty on exactly the repos it was built for. The pain is felt the moment anyone
  actually runs `impact` on a real change and gets nothing back: the tool looks
  broken even though every v0.1.0 AC passed.
- **Goal:** Make `impact` and `story_trace` return a **non-empty, correct**
  code→story result on a real repository that has a normal `.spark/` trail —
  *without* requiring every plan to have been hand-annotated with `files:` notes.
  Close the loop from a changed file back to the stories and acceptance criteria
  in its blast radius, and make the tool honest about how confident each such link
  is and whether the answer is stale.
- **Success signal (observable):** On a real repository with a full `.spark/`
  trail (the aspark-graph repo itself is the primary witness), after building the
  graph:
  1. `impact(<a real source file that implements a story>)` returns **at least one
     affected story and at least one affected acceptance criterion**, and a human
     confirms the reported story is genuinely the one that file helps implement.
     (This is the exact query that returns empty today.)
  2. The graph on that same repo contains **one or more `implements` (code→artifact)
     edges** where today it contains zero.
  3. Every reported code→story link carries a confidence tag that lets a consumer
     distinguish a link the artifacts *declared* from one the tool *inferred*, and
     an `impact`/`story_trace` result run against an out-of-date graph is either
     refreshed or flagged as stale rather than silently answering from stale data.
- **Why now:** The two headline tools are the entire justification for the tool
  existing (v0.1.0 spec §1). Right now their value is theoretical on real repos,
  and the tool has no consumers yet, so nobody has hit the empty result in anger.
  If we ship the tool "as is" to aSPARK agents, the first real `impact` call
  returns nothing and the tool is written off. Closing the loop now — before
  adoption — is what turns a passing test suite into a tool that earns its place.
  Honest caveat: if we never build this, aSPARK still works (agents keep the
  Grep/Glob fallback), and `story_trace` already returns the declared story→AC→QA
  trail correctly. This cycle is about making the *code linkage* real, not about
  rescuing a broken product.

## 2. Target Users

<!-- Concrete personas or roles. "Everyone" is not an answer. -->

- **Primary: the aSPARK reviewer / engineering-manager agent** running inside
  Claude Code on a repo too large to hold in one's head. It is the caller of
  `impact` before approving an increment ("what does QA have to re-verify?") and
  the one that today gets an empty answer.
- **Secondary: the developer supervising that agent**, who runs the CLI
  (`aspark-graph query impact ...`) to sanity-check a change's blast radius and who
  is the first human to notice the tool returns nothing useful.
- **Explicitly NOT a target this cycle:** any consumer that requires aspark-graph
  to be published to a package index (publishing is deferred — Q1), and any
  aSPARK-repo agent whose *own* prompt/template needs editing to call the tool
  (that is aSPARK-repo work — A7).
- **Not useful for:** repos with no `.spark/` artifacts, or repos small enough to
  read by hand — unchanged from v0.1.0.

## 3. Assumptions & Open Questions

<!-- Every assumption is a risk. Open questions block the gate until answered or explicitly accepted. -->

| # | Assumption / Question | Resolution |
|---|---|---|
| A1 | The idea arrived partly as solutions (git-blame inference, a new `inferred` confidence tier, file-hash staleness, `impact --diff <range>`, a `feature_overview` tool, PyPI/GitHub publish). This spec records the underlying *needs* — a non-empty impact result on real repos, honesty about link confidence and staleness, and a change-range entry point — and leaves all mechanism (how inference works, how the tier is computed, how a diff is resolved) to `/sprint-plan`. Original phrasing kept here as the assumption. | Accepted as assumption |
| A2 | The empirical finding is real and is the mandate for this cycle: on the aspark-graph repo, the v0.1.0 graph has 0 `implements` edges and `impact` on a central file returns no affected story. Verified against the shipped `_files_note`/best-effort-`implements` behaviour (v0.1.0 A3/Q1). | Accepted as fact (motivating this spec) |
| A3 | v0.1.0 deliberately kept `implements` best-effort and treated its absence as expected, on the sole declared source of an inline `files:` note that real plans do not write. **This cycle overturns that** for the code→artifact link specifically: an empty `impact` on a real trail is now treated as the defect to fix, not as expected behaviour. | Accepted as assumption (supersedes v0.1.0 A3/Q1 for `implements`) |
| A4 | A code→artifact link the tool derives itself (e.g. from repository history rather than a declared note) is **necessarily lower-confidence than a declared or extracted link** and must be surfaced as such, so consumers never mistake an inferred blast-radius hit for a declared one. The exact tiering label and computation are the EM's call. | **Accepted as assumption — now a binding guardrail on the confirmed inference path (see Q2).** |
| A5 | Inference from repository history must remain **deterministic and offline** to honour the tool's core contract (v0.1.0 §1, AC-1.2): the same repository state must always produce the same graph. If any inference source cannot be made deterministic, it is out of scope rather than allowed to break determinism. | **Accepted as assumption — now a binding guardrail on the confirmed inference path (see Q2).** |
| A6 | The graph already stores file hashes (v0.1.0 T2/model), so detecting that the graph no longer matches the repository it was built from is cheap and needs no new data — only a decision on what to do when they diverge. | Accepted as assumption |
| A7 | **Wiring aSPARK's own agents to call the graph, and changing the aSPARK plan template to emit a `files:` convention, are deliverables in the *aSPARK* repository, not in aspark-graph.** v0.1.0 put "modifying aSPARK itself" Out of Scope; this spec keeps that boundary. aspark-graph may *document and harden the convention it reads*, but it does not ship the aSPARK-side change. | Accepted as assumption (split-out — see Out of Scope) |
| Q1 | **Publish target and go/no-go.** *Where* (PyPI, a GitHub release, both, or neither yet) and *whether* to publish v0.2.0 is a user/product decision, not something the team can assume. | **RESOLVED (user, 2026-07-14): do NOT publish this cycle.** Publishing is a deferred product decision, not a v0.2.0 build task. The publish-gated "working install path" story is therefore **withdrawn to Won't (US-7).** The separate, real gap — the README today advertises a *fictional* `uvx`/PyPI install path (the package is on neither PyPI nor GitHub) — is corrected by a small honesty story, **US-6 (Should)**: the README must describe only install paths that work today (from-source via `uv`; optionally a local wheel) and must claim no `uvx`/PyPI path while unpublished. |
| Q2 | **Is a repository-history inference fallback acceptable at all**, given it produces links no artifact declared? The alternative is to rely solely on the declared `files:` convention (and thus depend on the aSPARK-side change in A7 before `impact` is ever non-empty on real repos). | **RESOLVED (user, 2026-07-14): YES — the git-history inference fallback is confirmed.** `implements` edges may be derived from commit history (e.g. commits that touch files while a task was `doing`/`done`; the exact mechanic is `/sprint-plan`'s call). US-1 stands as designed and **does not depend** on the aSPARK-template PR. Hard guardrails: **A4** (inferred is a distinct, weaker confidence tier) and **A5** (must stay deterministic/offline; must not break the AC-1.2 / AC-1.5 determinism contract) are binding. |

## 4. User Stories

<!-- MoSCoW priority: Must / Should / Could / Won't. Every story needs testable acceptance criteria. -->

### US-1 (Must): A code change yields its real story blast radius

> As the reviewer agent, I want `impact` on a real changed file to return the
> stories and acceptance criteria that actually depend on it — even when no plan
> task was hand-annotated — so that the tool answers the one question it exists to
> answer instead of coming back empty.

<!-- This is the core problem. The success signal above is this story. Q2 confirmed
     the git-history inference fallback: implements edges may be derived from commit
     history. Mechanism is the EM's call in /sprint-plan; the ACs fix only the
     observable outcome and the A4/A5 honesty+determinism guardrails. US-1 does NOT
     depend on the aSPARK-template PR (A7). -->

**Acceptance criteria:**

- [ ] AC-1.1: Given the aspark-graph repository (a real, complete `.spark/` trail)
  built into a graph, when I call `impact` on a source file that genuinely
  contributes to a shipped user story, then the result includes **at least one
  affected user story and at least one affected acceptance criterion** — i.e. it is
  **not** the empty result v0.1.0 returns today for the same input.
- [ ] AC-1.2: Given the same built graph, when I inspect the graph's edges, then it
  contains **one or more `implements` (code→artifact) edges**, where the v0.1.0
  graph on the same repo contains zero.
- [ ] AC-1.3: Given an `impact` result that includes a story/AC reached through a
  code→artifact link the tool **inferred** (e.g. from commit history) rather than
  one the artifacts declared, when I inspect that link, then it is tagged with a
  confidence level that is **distinguishable from and weaker than** a `declared` or
  `extracted` link (A4), so a consumer can tell an inferred blast-radius hit from a
  declared one.
- [ ] AC-1.4: Given the human-confirmation step of the success signal, when a
  reviewer inspects the story returned by AC-1.1, then they confirm it is a story
  that source file genuinely helps implement (no fabricated or obviously wrong
  link presented at a confidence tag implying certainty).
- [ ] AC-1.5: Given the same repository state built twice, when I compare the two
  graphs, then the code→artifact links (and their confidence tags) are **identical**
  across both builds — deriving links from commit history must not break the
  determinism contract (A5; v0.1.0 AC-1.2).
- [ ] AC-1.6: Given a repository with a `.spark/` trail but where the tool can
  derive **no** code→artifact link for a queried file, when I call `impact` on it,
  then the result still reports "no affected stories/ACs" cleanly (v0.1.0 AC-3.3
  behaviour preserved) rather than erroring — inference improves coverage but its
  absence is never a crash.

### US-2 (Must): `story_trace` shows the real code behind a story

> As the reviewer agent, I want `story_trace(US-n)` on a real repo to list the
> code entities that implement the story — not an empty code section — so that I
> can see what a story is actually made of before reading files.

<!-- The read-direction counterpart of US-1: the same closed loop, viewed from the
     story rather than the file. Shares the code→artifact link with US-1. -->

**Acceptance criteria:**

- [ ] AC-2.1: Given the aspark-graph repository built into a graph, when I call
  `story_trace(US-n)` for a story that has shipped code, then the result's code
  section is **non-empty** — it lists at least one code entity linked to that
  story — where v0.1.0 returns an empty code section for the same story.
- [ ] AC-2.2: Given a `story_trace` result, when a listed code entity is linked
  through an inferred rather than declared/extracted link, then it carries the same
  distinguishable, weaker confidence tag defined in AC-1.3, so the reviewer is not
  misled about how the link was established.
- [ ] AC-2.3: Given a story for which the tool can establish no code link at all,
  when I call `story_trace(US-n)`, then the declared story→AC→task→QA trail is still
  returned in full and the code section is an explicit empty (non-error) result —
  the v0.1.0 declared-trail correctness (AC-2.1..2.5) is not regressed.

### US-3 (Should): Impact from a change range, not a hand-typed file list

> As the reviewer agent, I want to ask for the impact of a range of changes rather
> than typing out every changed file, so that I can scope a review directly from
> "what changed in this branch/commit" without an intermediate manual step.

<!-- V5. A convenience entry point onto the US-1 engine. Not the core problem, but
     it is how a reviewer naturally arrives at impact; keeps the tool in the real
     workflow. Deliberately a Should, not a Must — the core value is US-1. -->

**Acceptance criteria:**

- [ ] AC-3.1: Given a built graph and a repository with more than one recorded
  change, when I ask `impact` for a change range instead of an explicit file list,
  then the result is the same set of affected stories/ACs I would get by passing
  the files in that range explicitly to the existing `impact`.
- [ ] AC-3.2: Given a change range that touches files not present in the graph, when
  I run the range-based impact, then unknown paths are named and the known files in
  the range are still answered in the same call (v0.1.0 AC-3.4 behaviour, preserved
  for the range entry point).
- [ ] AC-3.3: Given an empty or invalid change range, when I run the range-based
  impact, then I get a clear message stating the range was empty/invalid — not a
  stack trace and not a silently empty success.

### US-4 (Should): Don't answer from a stale graph without saying so

> As the developer or agent, I want the tool to tell me when the graph no longer
> matches the repository it was built from, so that I never act on an `impact` or
> `story_trace` answer that is quietly out of date.

<!-- V2. File hashes are already in the graph (A6), so this is cheap honesty that
     directly protects the trust in US-1/US-2. Should, not Must: the answer is still
     correct for the state the graph was built from; the risk is the user not
     knowing that state is old. -->

**Acceptance criteria:**

- [ ] AC-4.1: Given a graph built from a repository, and then one or more of that
  repository's tracked source files change on disk, when I run a query, then the
  result **indicates the graph is stale** (or the query refreshes it) rather than
  answering silently from the outdated graph.
- [ ] AC-4.2: Given a graph whose files are unchanged since the build, when I run a
  query, then it reports the graph as current and answers normally with no staleness
  warning — no false positives.
- [ ] AC-4.3: Given a stale graph, when I follow the tool's own guidance to refresh
  it, then a subsequent query on the up-to-date graph reports current and answers
  from the new state.

### US-5 (Should): The convention the tool reads is documented and dependable

> As a developer setting up an aSPARK repo to get the most out of the graph, I want
> the code→artifact linking convention that aspark-graph reads to be clearly
> documented, so that a repo can *opt into* declared (highest-confidence) links
> rather than relying only on inference.

<!-- The aspark-graph-owned half of V1a: document/harden the `files:` note the tool
     already parses. The aSPARK-side change that makes aSPARK plans EMIT the note is
     split out to the aSPARK repo (A7). This story is purely about aspark-graph's own
     documentation and robustness of what it reads. -->

**Acceptance criteria:**

- [ ] AC-5.1: Given the aspark-graph documentation, when a developer reads it, then
  the exact convention aspark-graph recognises for declaring a task→code link is
  described precisely enough to reproduce (what to write, and where), with an
  example that the tool then links at `declared` confidence.
- [ ] AC-5.2: Given a plan whose task follows the documented convention, when I
  build and run `story_trace`/`impact`, then the resulting code→artifact link is
  tagged `declared` (highest confidence), distinct from an inferred link.
- [ ] AC-5.3: Given a plan whose task follows the documented convention but names a
  file that does not exist in the repo, when I build, then the tool does not
  fabricate a link and does not crash — it either omits the link or reports the
  dangling reference clearly (no silent wrong edge).

### US-6 (Should): The README documents only install paths that work today

> As a new user following the README, I want the getting-started instructions to
> describe only install paths that actually work right now, so that I do not hit a
> dead end trying to install a package that has not been published.

<!-- Q1 resolved: NOT publishing this cycle. The README today advertises a fictional
     `uvx`/PyPI install path — the package is on neither PyPI nor GitHub — which is a
     real, present dead end for any reader. This story fixes that honesty gap WITHOUT
     publishing: describe only the from-source (uv) path that works today, and drop
     any uvx/PyPI claim until the tool is actually published. The publish-gated
     "install from a package index" work is withdrawn to US-7 (Won't). -->

**Acceptance criteria:**

- [ ] AC-6.1: Given the tool is not published to any package index this cycle, when
  I read the README's install section, then it makes **no** claim of a `uvx`/PyPI
  (or other package-index) install path — every documented command corresponds to a
  source that actually exists today.
- [ ] AC-6.2: Given a fresh environment with only the prerequisites the README
  states, when I follow the README's install/run instructions exactly (from source
  via `uv`, or a documented local wheel), then I reach a working install with **no
  dead end**, and `build` followed by at least one `query` runs successfully
  end-to-end.
- [ ] AC-6.3: Given the README, when I read how to add the tool to Claude Code as an
  MCP server, then the documented command uses only a working (non-published) entry
  point (e.g. the from-source/`uv run` form), not the fictional `uvx` form.

### US-7 (Won't, this version): Everything on the Out-of-Scope list

> Recorded so the "no" is documented. See section 5. Includes the deferred
> **publish** work (Q1) and the aSPARK-repo split-outs (A7).

## 5. Out of Scope

<!-- Explicitly cut. Prevents scope creep in /increment. -->

Consciously cut this cycle (each is a real candidate from the evaluation — the
answer is "not now" or "not here"):

- **Publishing v0.2.0 to any package index (PyPI / GitHub release) — deferred
  product decision (Q1).** The user decided **not** to publish this cycle, so the
  publish work and any "install from a package index" story are Won't for v0.2.0.
  The *honesty* consequence — the README must stop advertising a fictional `uvx`/PyPI
  path — is handled in-scope by US-6. When publishing is later decided, a fresh
  story defines the working published install path and its testable ACs.
- **Split-out to the aSPARK repo (not aspark-graph's scope at all):**
  - **Wiring aSPARK's own EM/reviewer agents to query the graph ("graph-first"
    agent behaviour).** This edits aSPARK agent prompts, not aspark-graph. It is the
    consumer side and belongs in the aSPARK repo (A7; v0.1.0 Out-of-Scope
    "modifying aSPARK itself"). aspark-graph must simply *be callable*; making
    aSPARK call it is a separate deliverable there.
  - **Changing the aSPARK plan template to emit the `files:` convention.** The
    template lives in aSPARK. aspark-graph documents and reads the convention (US-5);
    aSPARK adopting it is the aSPARK repo's PR. Without that PR, `impact` on real
    repos stays non-empty *only* via the inference path (US-1) — which is exactly
    why US-1 (Q2-confirmed) does not depend on the aSPARK-side change.
- **Cut from this cycle (in aspark-graph's scope, but not now):**
  - **A `board` / `feature_overview` tool (V6).** A new reporting surface that does
    not move the needle on the empty-impact core problem. Scope creep this cycle;
    revisit once the loop is genuinely closed and there are real consumers asking
    for it.
  - **Incremental / sub-second rebuild (V8).** v0.1.0 accepted full rescan per
    build (A6); still accepted. Staleness detection (US-4) gives the honesty benefit
    without the incremental-update machinery. Tier-1 candidate.
  - **The F4 review nits (V7): `find_nodes("")` guard and skip-dir pruning.** The
    user already accepted these as "no change" at review (review-report F4). They do
    not touch the core problem and are explicitly not reopened here. Tier-1 cleanup.
  - **Any non-deterministic inference source.** If a repository-history signal
    cannot be made reproducible for a fixed repo state (A5), it is out — determinism
    is not negotiable, even for the confirmed git-history fallback.
  - **Broader `calls`/call-graph precision, more languages, LLM/NL layer,
    visualization, exports, HTTP/team mode.** All remain out of scope exactly as in
    v0.1.0 §5.

## 6. Design Review

<!-- Filled by /look-and-feel. Empty design review = gate stays red for UI-facing features. -->

**N/A — with reason.** Like v0.1.0, close-the-loop adds no graphical or human-facing
visual interface. Its surfaces are the same two non-visual ones: an MCP tool API
consumed by agents and a text CLI whose output is JSON. Everything this cycle adds —
a richer `impact`/`story_trace` result, a change-range input, staleness reporting,
clear error/guidance messages, and README prose — is textual and is captured as
falsifiable acceptance criteria (AC-1.3, AC-3.3, AC-4.1, AC-5.1, AC-6.1). There is no
layout, visual hierarchy, or accessibility surface (contrast/focus/keyboard) to
review. If a visualization surface is ever brought in scope, this section must be
reopened.

- **Overall impression:** N/A (no visual UI)
- **Heuristics findings:** N/A — CLI error-handling/honesty heuristics covered via ACs (AC-3.3, AC-4.1, AC-5.3, AC-6.1)
- **Accessibility notes:** N/A (no visual UI)
- **Design risks & required changes:** None for a non-UI tool

---

## ✅ SPEC GATE

*All boxes checked → `/sprint-plan` may start. Any box open → back to `/story-time` or `/look-and-feel`.*

- [x] Problem, goal and success signal are concrete (no buzzwords, no "everyone")
- [x] Every story has testable Given/When/Then acceptance criteria
- [x] Stories are prioritized (MoSCoW) and at least one is a Must
- [x] Open questions are resolved or explicitly accepted as risk *(Q1 resolved: no publish this cycle → US-6 honesty story, publish withdrawn to US-7. Q2 resolved: git-history inference confirmed, A4/A5 binding guardrails.)*
- [x] Out-of-scope section is filled (something was consciously cut)
- [x] Design review done for UI-facing features (or marked N/A with reason)
- [x] Status set to `approved` by the user
