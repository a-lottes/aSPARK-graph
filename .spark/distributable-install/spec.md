# Spec: distributable-install

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (`/story-time`), Designer (`/look-and-feel`) |
| **Status** | `approved` |
| **Date** | 2026-07-16 |

## 1. Problem & Goal

<!-- The PO's interrogation result. Not what the user asked for — what they actually need. -->

- **Problem:** aspark-graph cannot be installed cleanly by anyone who is not the
  author on an Apple-Silicon machine. Two things stack up:
  1. **A hard install failure on Intel macOS.** The MCP dependency drags in a
     transitive native dependency (`cryptography==49.0.0`) that has **no prebuilt
     wheel for macOS x86_64** and requires a Rust/OpenSSL toolchain to build from
     sdist. On the author's own Intel host (macOS 13.7, no toolchain) `uv sync`
     **fails outright**, which blocked both the test suite and installing the MCP
     server. The workaround in the repo today is a second `.venv-test` without
     fastmcp — i.e. the MCP server, the tool's whole reason for the dependency,
     cannot be installed at all on that machine. And this dependency is **dead
     weight**: `cryptography` is not imported anywhere in `src/` (verified by grep);
     it exists only to satisfy an MCP server auth extra the tool does not use.
  2. **No distribution path.** The README documents **clone + `uv sync` only**
     ("not yet published to a package index"). Every prospective consumer must
     clone the repo. There is no `uvx`/`pipx` one-command install — a real
     adoption tax for a tool whose primary consumer is an agent that would `uvx`
     an MCP server.

  Who feels it: the *next* person (or agent) who tries to install the tool on a
  platform without a `cryptography` wheel/toolchain — starting with the author on
  Intel macOS, where it is a total block, not a nuisance.
- **Goal:** aspark-graph installs cleanly and runs on all supported platforms
  **without** dragging in a native dependency that serves functionality the tool
  does not use — and a built distributable can be installed into a fresh, isolated
  environment where both the CLI and the MCP server work. In short: make "install
  it and run it anywhere" true and *proven*, and make it distributable rather than
  clone-only.
- **Success signal (observable):**
  1. On a platform that has **no** prebuilt wheel for the previously-transitive
     native dependency and **no** build toolchain (the author's Intel macOS host is
     the primary witness), a clean install of aspark-graph **completes** and
     `aspark-graph serve` starts — where today `uv sync` fails building that
     dependency from source.
  2. The installed dependency tree contains **no** dependency that exists solely to
     serve unused (auth) functionality — `cryptography` is gone.
  3. A distributable built from the repo installs into a **fresh, isolated
     environment** (no checkout, no dev deps) and both `aspark-graph <query>` and
     `aspark-graph serve` run end-to-end.
  4. The graph still rebuilds **byte-for-byte identically** on an unchanged repo
     (the determinism non-negotiable is not broken by the dependency change).
- **Why now:** close-the-loop (v0.2.0) is making the two headline tools return real
  value; that is worthless to anyone who cannot install the tool. Publishing was
  consciously deferred in close-the-loop (Q1 → Won't/US-7). This cycle reopens it —
  but the *urgent* driver is not the convenience of `uvx`; it is that install is
  **broken** on a whole platform class today. If we never build this, the tool
  stays effectively single-machine (author, arm64), the MCP server is uninstallable
  on Intel macOS, and adoption cannot start. Honest caveat: the author on Apple
  Silicon is unblocked today, so this is not an emergency for *them* — it is the
  gate on anyone else using the tool at all.

## 2. Target Users

<!-- Concrete personas or roles. "Everyone" is not an answer. -->

- **Primary: the prospective installer on a platform without a `cryptography`
  wheel/toolchain** — concretely the author on Intel x86_64 macOS 13.7, and by
  extension anyone on a platform where a native-build dependency is a wall rather
  than a wheel. They cannot install the tool today; they are the acute pain.
- **Secondary: an agent or developer who wants a one-command install** of the MCP
  server (`uvx`/`pipx`) instead of cloning the repo and running `uv sync` — the
  natural way an MCP consumer adopts a server.
- **Tertiary: the maintainer (author)** who needs a repeatable, proven build →
  clean-env-install → run path before ever pushing to a public index, so a broken
  package is never published.
- **Explicitly NOT a target this cycle:** anyone needing authenticated/remote MCP
  transport (the local stdio server is the only supported surface; the dropped
  dependency served an auth path the tool does not offer — see Q4), and anyone on
  an OS not confirmed as supported (Windows status is Q3).

## 3. Assumptions & Open Questions

<!-- Every assumption is a risk. Open questions block the gate until answered or explicitly accepted. -->

| # | Assumption / Question | Resolution |
|---|---|---|
| A1 | The idea arrived partly as **solutions** ("drop the transitive cryptography dependency", "use fastmcp WITHOUT its `[server]` auth extra / pin a lean fastmcp", "publish to PyPI so users get uvx/pipx"). This spec records the underlying *needs* — a clean cross-platform install with no unused native dependency, and a proven distributable install — and leaves **how** to trim the dependency (drop an extra, pin a version, or otherwise) entirely to `/sprint-plan`. Original phrasing kept here as the assumption. | Accepted as assumption |
| A2 | The install failure and the dead-weight dependency are **facts**: `cryptography==49.0.0` is transitive via the MCP dependency's server-auth extra, is imported nowhere in `src/`, has no macOS x86_64 wheel, and its sdist build fails on the author's Intel host with no toolchain. Verified in the repo/grounding. | Accepted as fact (motivating this spec) |
| A3 | Trimming the dependency must **not** regress any capability the tool actually ships: all CLI queries, the MCP server (`aspark_graph.server:run`), and the CLI/MCP parity contract must still hold. | Accepted as assumption (binding guardrail — AC-1.3) |
| A4 | The dependency change must **preserve determinism** (project non-negotiable / v0.1.0 AC-1.2): parse-affecting deps (tree-sitter core + three grammars) stay pinned `==`; the byte-identical double-build test stays green. fastmcp/networkx do not affect the serialised graph, so a floor + committed lock remains their determinism contract. | Accepted as assumption (binding guardrail — AC-1.4) |
| A5 | **Install honesty is a hard rule** (inherited from close-the-loop F4/US-6): the README must document only install paths that work *today*. If the package is not actually published on an index by the end of this cycle, the docs must claim no `uvx`/PyPI path (US-3). | Accepted as assumption |
| Q1 | **Versioning.** close-the-loop is v0.2.0 and in review. Does this work ship *inside* 0.2.0, or as a new version (e.g. 0.3.0)? This changes the version string in the package metadata and the release trail. | **RESOLVED (2026-07-16): new `0.3.0`.** Kept separate from in-review 0.2.0 so the two release trails don't mix. |
| Q2 | **Publish go/no-go and target, and where the "publish" line sits.** The idea says "publish to PyPI". But a *live* push to a public index requires owning the `aspark-graph` name and is a release-time action provable only at release/Keep — not something a Review gate can verify. Is the actual live publish part of **this cycle's** definition of done, or is the cycle's DoD "**publish-ready and proven in a clean env**" (US-2) with the live push deferred to the release phase? close-the-loop Q1 deferred publishing; this reopens it. | **RESOLVED (2026-07-16): publish-ready + clean-env proof (US-2) is the DoD; the live PyPI push is deferred to the release/Keep phase.** US-4 (live index install) → Out of Scope this cycle; README stays honest (US-3, no `uvx`). |
| Q3 | **Windows support.** Is Windows a supported install target (Must/Should) or best-effort (Could/Won't) this cycle? There is no Windows host available here to prove a clean install, so "runs anywhere" can be *asserted* for Windows but not *demonstrated* this cycle. | **RESOLVED (2026-07-16): best-effort / Could — asserted from wheel availability, not demonstrated (no host).** No platform-specific deps remain (pure-Python `mcp` + networkx + tree-sitter grammars ship wheels), so Windows should work; not a Must this cycle. |
| Q4 | **Is any near-term feature going to need the dropped server-auth capability?** The MCP server is local/offline/stdio today and offers no auth. Dropping the auth extra is safe *only if* no planned story needs authenticated/remote MCP transport soon (which would re-pull the same dependency class). | **RESOLVED (2026-07-16): "no" — the tool is offline/local/stdio by design.** Trimming the auth dependency removes no offered capability; re-introducing auth is a separate future spec. |
| Q5 | **What is the accepted proof of "runs anywhere" this cycle?** A one-time clean-environment install + run on the available platform(s), or an automated multi-OS install matrix (CI) that re-proves it on every change? The latter is materially larger scope. | **RESOLVED (2026-07-16): a one-time clean-env install + run is the accepted proof.** US-5 (automated multi-OS CI matrix) → Out of Scope this cycle. |

## 4. User Stories

<!-- MoSCoW priority: Must / Should / Could / Won't. Every story needs testable acceptance criteria.
     Story and AC IDs (US-n, AC-n.m) are stable — never renumber; add new at the end. -->

### US-1 (Must): Clean cross-platform install with no unused native dependency

> As a prospective user on a platform without a prebuilt wheel or build toolchain
> for the previously-transitive native dependency, I want to install aspark-graph
> without it pulling in a dependency that serves functionality the tool does not
> use, so that install succeeds where it fails today.

<!-- The acute pain: install is a total block on Intel macOS. State the OUTCOME
     (clean install, no unused native dependency), not the mechanism (drop an
     extra / pin a version) — that is /sprint-plan's call (A1). -->

**Acceptance criteria:**

- [ ] AC-1.1: Given a clean environment on a platform where the previously-transitive
  native dependency (`cryptography`) has **no** prebuilt wheel and **no** build
  toolchain is present (the author's Intel macOS x86_64 host is the witness), when I
  install aspark-graph, then the install **completes successfully** without
  attempting to compile that dependency from source — where the same install fails
  today.
- [ ] AC-1.2: Given a completed install, when I inspect the installed dependency
  tree, then `cryptography` — and any dependency present *solely* to satisfy the MCP
  server's unused auth extra — is **absent**. No dependency exists only to serve
  functionality aspark-graph does not use.
- [ ] AC-1.3: Given the leaner dependency set, when I run every CLI query, the MCP
  server (`aspark-graph serve` / `aspark_graph.server:run`), and the CLI↔MCP parity
  test, then **all existing v0.1.0/v0.2.0 functionality still works** — no capability
  is regressed by trimming the dependency, and CLI and MCP still return identical
  answers (A3).
- [ ] AC-1.4: Given the dependency change, when I build the graph **twice** on an
  unchanged repo, then the two `graph.json` outputs are **byte-identical**, the
  parse-affecting deps remain pinned `==`, and the existing double-build determinism
  test stays green (A4; v0.1.0 AC-1.2).
- [ ] AC-1.5: Given a completed install on a supported platform, when I run
  `aspark-graph serve`, then the MCP server **starts and registers its tools**
  (`build_graph`, `story_trace`, `impact`, `gate_health`, `staleness`, `get_node`,
  `find_nodes`, `get_neighbors`, `shortest_path`) without error — the server that is
  uninstallable today is installable and runnable.

### US-2 (Must): A built distributable installs into a clean env and both entry points work

> As the maintainer preparing to distribute the tool, I want a built distributable
> to install into a fresh, isolated environment and expose a working CLI **and** MCP
> server, so that "runs anywhere" is proven before any publish and a broken package
> is never shipped.

<!-- This is the headline, provable-in-Review success signal. It stands independent
     of whether we push to a live index (Q2): a clean-env install of a locally-built
     distributable proves the package is self-contained and correct. -->

**Acceptance criteria:**

- [ ] AC-2.1: Given a distributable (wheel and/or sdist) built from the repo, when I
  install it into a **fresh isolated environment** (no repo checkout, no dev
  dependencies), then the install **succeeds** and the `aspark-graph` console command
  is available on PATH.
- [ ] AC-2.2: Given that clean-env install, when I run `aspark-graph build .` on a
  repo with a `.spark/` trail and then at least one query (e.g. `story_trace`), then
  both run **end-to-end and return the expected result** — not an import error, a
  missing-package-data error, or a missing-entry-point error.
- [ ] AC-2.3: Given that clean-env install, when I run `aspark-graph serve`, then the
  MCP server starts and registers its tools without error (US-1's AC-1.5 holds from a
  *packaged* install, not just an editable checkout).
- [ ] AC-2.4: Given the built distributable, when I inspect its metadata, then the
  package name, version, entry points (`aspark-graph` console script and the MCP
  `run` entry), description and required package data are **correct and complete** —
  nothing needed at runtime is missing from the built artifact.

### US-3 (Should): Install docs describe only paths that work today

> As a new user following the README, I want the install instructions to describe
> only paths that actually work right now, so that I never hit a dead end trying to
> install the tool.

<!-- Inherits the F4/US-6 honesty rule (A5). Which commands are "true" depends on
     Q2's publish decision: if we do NOT publish live this cycle, the README must
     claim no uvx/PyPI path; if we DO, it documents the working uvx/pipx command. -->

**Acceptance criteria:**

- [ ] AC-3.1: Given the tool's actual publish status at the end of this cycle, when I
  read the README install section, then **every documented command corresponds to a
  path that works today** — no `uvx`/`pipx`/PyPI command appears unless the package
  is genuinely installable that way at that moment.
- [ ] AC-3.2: Given a fresh environment with only the prerequisites the README
  states, when I follow the documented install exactly, then I reach a **working
  install with no dead end** and can run `build` followed by at least one `query`
  end-to-end.
- [ ] AC-3.3: Given the README's "add to Claude Code as an MCP server" instructions,
  when I follow them, then the documented command uses only a **working entry
  point** — the fictional path is never documented.

### US-4 (Could): Distributed via a package index for one-command install

> As an agent or developer, I want to install aspark-graph with a single `uvx`/`pipx`
> command from a package index, so that I do not have to clone the repo and run a
> sync to use the tool.

<!-- The distribution convenience half of the idea. Priority and even inclusion are
     GATED on Q2 (publish go/no-go) and Q1 (version). A LIVE publish is provable only
     at release/Keep, not by a Review gate — so if kept, its DoD is "installable from
     the index and both entry points run", verified at release. If the user defers
     publishing, this story moves to Out of Scope (as in close-the-loop US-7) and the
     honesty rule (US-3) keeps the README truthful in the meantime. -->

**Acceptance criteria (only if Q2 resolves to publish this cycle):**

- [ ] AC-4.1: Given the package is published to the agreed index, when I run the
  documented one-command install (`uvx aspark-graph ...` / `pipx install
  aspark-graph`) in a clean environment, then it installs and the `aspark-graph`
  command and `aspark-graph serve` both run — with no unused native dependency
  pulled (US-1 holds from the published artifact).
- [ ] AC-4.2: Given the package is published, when the README is updated to document
  the index install, then those commands satisfy US-3 (they are true because the
  package now exists on that index).

### US-5 (Could): Cross-platform install is re-proven automatically

> As the maintainer, I want a clean install + run to be verified automatically across
> the supported platforms, so that a future dependency change cannot silently
> re-break install on a platform I do not develop on.

<!-- GATED on Q5. A one-time clean-env check (US-1/US-2) is the minimum proof; an
     automated multi-OS matrix is a larger, ongoing investment. Could, not Must —
     the core value (unbreak + proven distributable) does not require CI. -->

**Acceptance criteria (only if Q5 resolves to include CI):**

- [ ] AC-5.1: Given the agreed supported-platform matrix, when the automated check
  runs, then it performs a clean-environment install of the built distributable and
  runs `build` + one query on each platform, and **fails the check** if any platform
  cannot install or run.

### US-6 (Won't, this version): Everything on the Out-of-Scope list

> Recorded so the "no" is documented. See section 6. Includes any authenticated/remote
> MCP transport, and — pending Q2 — possibly the live publish itself.

## 5. Non-Functional Requirements

<!-- Each NFR is falsifiable and downstream-traceable. Inherits the project's
     determinism and clean-error non-negotiables rather than restating them. -->

| # | Category | Requirement (measurable) | How it's verified |
|---|---|---|---|
| NFR-1 | Cross-platform install (first-class) | A clean install with no build toolchain present **succeeds** on: Intel macOS x86_64 (the witness that fails today), Apple Silicon macOS arm64, and Linux x86_64 (manylinux). Windows is per Q3 (asserted, not demonstrated, unless a host is provided). No dependency requires compiling from sdist on any of these. | Clean-env install on each available target (/demo-day); Q3 sets the Windows row |
| NFR-2 | Determinism (non-negotiable) | The graph rebuilds **byte-for-byte identically** on an unchanged repo after the dependency change; parse-affecting deps stay pinned `==`; the double-build test stays green. | Existing double-build test + /peer-review of the dependency diff |
| NFR-3 | Dependency hygiene / supply chain | The installed runtime dependency tree contains **no** package present solely to serve unused functionality; the committed lock resolves the same trimmed set; the runtime dependency count does not increase. | /peer-review of the resolved dependency tree + lock diff |
| NFR-4 | Reliability / no regression | The full existing test suite (65 tests) is **green** on a platform where it can now run — including the MCP-dependent tests that the `.venv-test` workaround had to skip — and the CLI↔MCP parity test passes from a packaged install. | `uv run pytest` + clean-env parity check (/demo-day) |
| NFR-5 | Observability / clean errors (non-negotiable) | Domain errors continue to surface as one-line messages / structured dicts, never tracebacks, from the packaged install. (Installer-tool failures themselves are the packaging tool's domain, not aspark-graph's — out of scope for this NFR.) | /peer-review + clean-env smoke run |
| NFR-6 | Security & privacy | N/A — dropping the auth dependency removes **no** capability the tool offers: aspark-graph is local, offline, no-network, no-auth by design; the dependency served an MCP auth path the tool does not expose (confirm via Q4). | /peer-review; Q4 confirmation |
| NFR-7 | Accessibility | N/A — no graphical/human-visual interface; surfaces are a JSON CLI and an agent-facing MCP API (unchanged from v0.1.0). | N/A |

## 6. Out of Scope

<!-- Explicitly cut. Prevents scope creep in /increment. -->

Consciously cut this cycle:

- **Authenticated / remote MCP transport.** The tool ships a local, offline, stdio
  MCP server. Dropping the unused server-auth dependency is *because* that transport
  is not offered. Re-introducing auth/remote transport (which would re-pull the same
  native dependency class) is a separate, future decision — not this cycle (Q4).
- **A live publish to a public index — PENDING Q2.** If the user defers publishing
  (as close-the-loop did in its Q1), the actual push to PyPI and the `uvx`/`pipx`
  docs (US-4) are Out of Scope this cycle, and US-3 keeps the README honest in the
  meantime. If the user opts to publish, US-4 comes into scope but its *live-index*
  proof is a **release/Keep-phase action**, not a Review-gate check — the Review-gate
  proof is US-2 (clean-env install of the built distributable).
- **An automated multi-OS CI install matrix — PENDING Q5.** The minimum accepted
  proof of "runs anywhere" is a one-time clean-env install + run (US-1/US-2). A
  standing CI matrix (US-5) is a larger, ongoing investment; in scope only if the
  user asks for it this cycle.
- **Windows demonstration — PENDING Q3.** With no Windows host available, a Windows
  clean install can be *asserted* from wheel availability but not *demonstrated* this
  cycle. Whether Windows is a supported target at all is Q3.
- **Bumping or re-pinning parse-affecting dependencies for any reason other than the
  install fix.** The tree-sitter core + grammars stay exactly pinned; this cycle does
  not touch them (they are the determinism contract). Any grammar bump is a separate
  spec.
- **Everything already Out of Scope in v0.1.0/v0.2.0** — more languages, LLM/NL layer,
  call-graph precision, incremental builds, visualization, exports, HTTP/team mode.
  Unchanged.

## 7. Clarifications

<!-- The record of the Specify-phase Clarify pass. Each resolution sharpens a
     story/NFR above or lands in Out of Scope. Unresolved → §3 and gate stays closed. -->

| # | Date | Question | Resolution |
|---|---|---|---|
| C1 | 2026-07-16 | Does the spec prescribe *how* to drop `cryptography` (no `[server]` extra vs. pin a lean fastmcp)? | No — that is a solution. The spec states the outcome (clean install, no unused native dependency: AC-1.1/AC-1.2) and leaves mechanism to `/sprint-plan` (A1). |
| C2 | 2026-07-16 | What does "publishable" mean as a Review-provable acceptance signal without owning the PyPI name? | The Review-provable signal is US-2: a locally-built distributable installs into a fresh isolated env and both entry points run. A live-index push is a release/Keep action (Q2), not a Review-gate check. |
| C3 | 2026-07-16 | (raised to §3) Version (0.2.0 vs 0.3.0), publish go/no-go, Windows scope, safety of dropping auth, and CI matrix scope. | **RESOLVED** — see Q1–Q5 in §3. Version `0.3.0`; DoD = publish-ready + clean-env proof (live push deferred); Windows best-effort/Could; auth-drop safe; no CI matrix this cycle. |
| C4 | 2026-07-16 | With US-4 (live publish) and US-5 (CI matrix) deferred, does the cycle still deliver value? | Yes — US-1 (unbreak install, drop the unused native dependency) + US-2 (proven clean-env distributable) are the value; US-4/US-5 are convenience layered on top. Both moved to Out of Scope §6. |

## 8. Design Review

<!-- Filled by /look-and-feel. Empty design review = gate stays red for UI-facing features. -->

**N/A — with reason.** Like v0.1.0 and close-the-loop, this cycle adds no graphical
or human-visual interface. It changes packaging, the dependency footprint, and README
prose. The only human-facing text — README install instructions and clean CLI/MCP
error messages — is captured as falsifiable acceptance criteria (AC-3.1..3.3, NFR-5).
There is no layout, visual hierarchy, or accessibility surface to review.

- **Overall impression:** N/A (no visual UI)
- **Heuristics findings:** N/A — install-doc honesty and clean-error heuristics covered via ACs (AC-3.1, NFR-5)
- **Accessibility notes:** N/A (no visual UI)
- **Design risks & required changes:** None for a non-UI packaging change

---

## ✅ SPEC GATE

*All boxes checked → `/sprint-plan` may start. Any box open → back to `/story-time` or `/look-and-feel`.*

- [x] Problem, goal and success signal are concrete (no buzzwords, no "everyone")
- [x] Every story has testable Given/When/Then acceptance criteria
- [x] Stories are prioritized (MoSCoW) and at least one is a Must
- [x] Non-functional requirements are stated and measurable (or marked N/A with reason)
- [x] Clarify pass done: no ambiguity left unresolved or unparked
- [x] Open questions are resolved or explicitly accepted as risk *(Q1–Q5 all RESOLVED 2026-07-16 — see §3)*
- [x] Out-of-scope section is filled (something was consciously cut)
- [x] Constitution (`.spark/constitution.md`) respected — N/A, no constitution exists
- [x] Design review done for UI-facing features (or marked N/A with reason)
- [x] Status set to `approved` by the user *(2026-07-16)*
