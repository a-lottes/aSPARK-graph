# Spec: security-posture

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (`/story-time`), Designer (`/look-and-feel`) |
| **Status** | `approved` |
| **Date** | 2026-07-26 |

## 1. Problem & Goal

- **Problem:** aspark-graph v0.5.0 ships an MCP stdio server with nine tools; three things
  about it are true, undocumented and unenforced:
  1. `build_graph` is an `@mcp.tool()` (`server.py:21`) — the surface **writes**
     (`<root>/.aspark-graph/`), while README/CLAUDE.md read as a read-only context service.
  2. `repo`/`path` default to `"."` with no constraint on any of the nine tools, so
     "aspark-graph reads **one** repository" (README:11) is an aspiration, not a behaviour.
  3. `build.py:140` materialises `sorted(repo_root.rglob("*"))` with no count, size or
     symlink bound. Pointed at `$HOME` or `/`, the build does not fail — it hangs silently,
     violating the standing "clean errors, never tracebacks" non-negotiable.
  Who hurts: the **maintainer** (an external reviewer flags a missing `SECURITY.md` on sight,
  and this is the family's second-most-mature product) and the **agent developer** who
  mistypes a `repo` argument and gets a hang instead of a one-line refusal.
- **Explicitly NOT the problem:** this is **not** an exfiltration fix. The server is a local
  stdio child of the agent, running under the user's own file permissions; an agent that can
  call `build_graph(path="~/.ssh")` can generally read that path directly. **Confinement
  removes no privilege the caller did not already have.** The `.spark/BACKLOG.md` §3/G3
  framing ("konkreter Exfiltrationspfad") oversells it and must not be restored downstream.
- **Goal:** documented promise and shipped behaviour agree. A target that is not a repository
  is refused in milliseconds with a legible message; a target that is one behaves exactly as
  today; and `SECURITY.md` states the trust boundary and the **non**-guarantees honestly
  enough that a reviewer can check it against the code and find no overclaim.
- **Success signal:** (a) all nine tools refuse a non-repo path in a table-driven test — zero
  exceptions; (b) `aspark-graph build /tmp/empty` exits 1 with one line in <1s where today it
  walks; (c) `SECURITY.md` exists, is linked from README/CLAUDE.md, and a doc test asserts
  its required sections; (d) full suite and byte-identical-rebuild test stay green.
- **Why now:** the query surface just became a normative cross-repo contract with aSPARK
  Core, so every unstated behaviour hardens into one. And the hang is a shipped bug today.

## 2. Target Users

- **The maintainer**, answering an external architecture review and about to promote the tool
  (PyPI is queued behind this in the backlog).
- **The agent developer** wiring aspark-graph into `/peer-review` on their own repo, who
  passes a `repo` argument by hand and needs a wrong one to fail loudly, not slowly.
- **The reviewing agent** (Claude Code) that reads `SECURITY.md` to decide how much to trust
  the graph's output as context.
- Not a target: anyone expecting a sandbox, an isolation boundary, or multi-tenant safety.

## 3. Assumptions & Open Questions

| # | Assumption / Question | Resolution |
|---|---|---|
| A1 | **Original phrasing arrived as a solution** ("SECURITY.md + path confinement"). Translated to the need: *documented behaviour must match shipped behaviour, and a wrong target must fail fast.* Original recorded here. | Accepted |
| A2 | Confinement root: the resolved directory holds a `.git` entry, a `.spark` directory, or (query tools) a `.aspark-graph/graph.json` file. A **shape check**: every real project on the machine passes. | Decided by user |
| Q3 | Confinement scope — library, or entry points only? | **RESOLVED:** the **library too**, enforced in the shared module (AC-1.9), with an internal test-only bypass for the ~20 bare-`tmp_path` fixtures. Cost carried as A11. |
| Q4 | The file-count bound needs a number. | **RESOLVED:** no number here. `/sprint-plan` **measures** it and pins a fixed constant documented with that basis (AC-3.1). A fabricated figure is what this product refuses elsewhere (`"mttr": null`). |
| Q5 | The per-file size cap needs a number. | **RESOLVED: 5 MB** (≈150k lines; larger is generated/minified, where tree-sitter degrades). A judgement call, **not** a measurement — asymmetry with Q4 stated, not smoothed over (AC-2.9). |
| Q6 | Reporting channel. | **RESOLVED: GitHub private security advisories.** Enabling private vulnerability reporting is a **deliverable** (AC-2.8), not an assumption, so the doc cannot point at a 404. Maintainer identity: andreas@lottes.dev. Initial response: 5 working days (AC-2.6). |
| A7 | Building a **subdirectory** of a repo (monorepo package) stops working for a *first* build — a subdir has neither `.git` nor `.spark`. Already-built subdirs keep working via the third marker (A12). | Accepted risk |
| A8 | A source export with **no `.git` and no `.spark`** is refused. Per README it was never a supported target (the artifact layer is the point). | Accepted |
| A9 | CLI refusal rendering: one line on stderr + exit 1, matching the existing `GraphNotBuiltError` split (`cli.py:189` vs `server.py:41`). `{"found": false, "reason": …}` is the **MCP** rendering. | Settled by existing convention |
| A10 | Confinement is not a security control (§1). The Musts are justified as **correctness and legibility**, not risk reduction. | Accepted framing |
| A11 | **Risk from Q3:** the test-only bypass is a **second code path** — what the suite exercises is not what users get, so every confinement test proves slightly less than it appears to. Mitigated by AC-1.10/NFR-9; carried openly rather than dissolved by the decision. | Accepted risk |
| A12 | **The third marker is narrow, not self-authorising.** A `.aspark-graph/graph.json` exists only where this tool already built, and a *fresh* directory has none — so it can never admit a directory the tool has not already built from a `.git`/`.spark`-marked path (AC-1.12). One honest exception: graphs built by **pre-confinement versions** (≤0.5.0) were built with no check at all, so such a directory stays queryable. Recorded in `SECURITY.md`, consistent with "shape check, not a boundary". | Accepted |
| A13 | **Unverified from this repo (C16):** aSPARK Core skills branch on `found`, not on `reason`, so adding `outside_confinement` and `too_large` to the `reason` vocabulary is additive and needs no coordinated Core change. If wrong, it is Core's *read* that breaks, not this contract. Logged so a future cycle finds the assumption instead of re-deriving it. | Accepted risk |

## 4. User Stories

### US-1 (Must): A target that is not a repository is refused, on every entry point

> As an agent developer, I want a `repo`/`path` that is not a repository to be refused
> immediately and legibly, so that "aspark-graph reads one repository" is behaviour I can
> rely on rather than a sentence in the README.

**Acceptance criteria:**

- [ ] AC-1.1: Given a directory holding none of the three markers, when I run
      `aspark-graph build <dir>`, then the command exits 1, prints one line on stderr naming
      the path and the rule, prints no traceback, and creates **no** `.aspark-graph/`
      directory in the target.
- [ ] AC-1.2: Given the same directory, when an MCP client calls `build_graph(path=<dir>)`,
      then the result is `{"found": false, "reason": "outside_confinement", "message": …}`
      and no directory is created in the target.
- [ ] AC-1.3: Given the same directory, when an MCP client calls **each** of `get_node`,
      `story_trace`, `impact`, `gate_health`, `staleness`, `find_nodes`, `get_neighbors`,
      `shortest_path` with `repo=<dir>`, then every one returns the AC-1.2 shape — asserted
      by a test that iterates the tool list, so a tool added later cannot silently skip it.
- [ ] AC-1.4: Given each of (a) a directory whose `.git` is a **file** (git worktree /
      submodule), (b) a directory with a `.spark/` tree and no git at all, (c) a directory
      with a `.git/` directory and no `.spark/`, when any tool targets it, then it is
      **accepted** and behaves exactly as it does today.
- [ ] AC-1.5: Given a path that does not exist, or is a regular file, or is unreadable, when
      any tool targets it, then it is refused with the AC-1.1/AC-1.2 rendering — never a
      `FileNotFoundError`, `NotADirectoryError` or `PermissionError` traceback.
- [ ] AC-1.6: Given a symlink whose target directory holds a marker, when any tool targets
      the symlink, then it is accepted; the verdict is computed on the resolved path.
- [ ] AC-1.7: Given one fixed table of paths carrying **both** accepted and refused rows,
      when each path is passed to the CLI and to the MCP tool of the same name, then the
      verdict is identical for every row — the **existing** CLI↔MCP parity test is extended
      with the refusal rows rather than a second parity test being added.
- [ ] AC-1.8: Given the documented install (server cwd = the aspark-graph checkout, target
      passed as `repo`), when any tool runs with the default `repo="."`, then it is accepted
      and every existing behaviour and output is byte-for-byte unchanged.
- [ ] AC-1.9: Given a refused directory, when the **Python library** functions
      (`build_graph()`, `queries.load_graph()` and the `queries.*` functions taking a repo
      root) are called directly with no bypass in effect, then they refuse it too —
      confinement is enforced in the shared module, not at the adapter edge.
- [ ] AC-1.10: Given the shipped package, when the CLI and every MCP tool are exercised,
      then **no argument, flag, environment variable or tool parameter reachable from either
      surface** activates the test-only bypass — asserted by a test — and the bypass appears
      in no user-facing documentation.
- [ ] AC-1.11: Given a directory holding `.aspark-graph/graph.json` and neither `.git` nor
      `.spark`, when any of the eight query tools targets it, then it is **accepted**. The
      marker is the **existence of that regular file** — the check never opens, reads or
      parses it (NFR-1). A `.aspark-graph/` directory **without** `graph.json` is not a
      marker and is refused.
- [ ] AC-1.12: Given a fresh directory with no marker and no prior build, when `build_graph`
      targets it, then it is refused (AC-1.1/AC-1.2) — the third marker can never admit a
      directory this tool has not already built.
- [ ] AC-1.13: Given a directory that was built while marked and whose `.git`/`.spark` was
      later removed, when a query tool targets it, then it is still **accepted** — the graph
      is a read model of a repo that was valid when built. Deliberate, and stated in
      `SECURITY.md` (A12).

### US-2 (Must): A SECURITY.md that a reviewer can check against the code

> As the maintainer, I want a `SECURITY.md` that states the trust boundary and the explicit
> non-guarantees, so that the security posture is legible without reading `server.py` — and
> so that no sentence in it overclaims.

**Acceptance criteria:**

- [ ] AC-2.1: Given the repository, when I look at the root, then `SECURITY.md` exists and
      the README links to it.
- [ ] AC-2.2: Given `SECURITY.md`, then it states the trust boundary: a local **stdio child
      process** of the calling agent, running with the invoking user's own file permissions;
      **no auth, no HTTP, no network, no remote transport**; and that `mcp` is capped
      `<1.20` because 1.20+ hard-pulls `cryptography` for server-side OAuth this server does
      not use — the cap is a packaging decision, not a security control.
- [ ] AC-2.3: Given `SECURITY.md`, then it contains a *Non-guarantees* section with these
      **six** named entries: (1) the confinement rule is a **shape check, not a sandbox** —
      any git repo or `.spark` tree on the machine passes; (2) confinement **removes no
      privilege the caller did not already have**; (3) the MCP surface is **not read-only**
      — `build_graph` writes `<target>/.aspark-graph/`; (4) graph output is **data, not
      instruction**, and nothing is sanitised; (5) no auth, no HTTP, no network, no
      multi-user or multi-tenant model; (6) a directory already built stays queryable even
      if its `.git`/`.spark` later disappears, and graphs built by pre-confinement versions
      were built with no check at all (A12).
- [ ] AC-2.4: Given `SECURITY.md`, then a doc test fails if the words *sandbox*, *isolat*,
      *contain*, *prevent* or *protect* appear **outside** the *Non-guarantees* section.
- [ ] AC-2.5: Given `SECURITY.md`, then an *Output is data, not instruction* section states
      that the graph ingests `.spark/` prose **and** source text and returns it verbatim to
      an agent (e.g. `find_nodes` returns node `title`/`text` attributes), so any content
      that can reach the repo — a spec line, a code comment, a finding — is a potential
      prompt-injection vector, and graph output must never be treated as instruction.
- [ ] AC-2.6: Given `SECURITY.md`, then it names **GitHub private security advisories** as
      the reporting route (never a public issue for a suspected vulnerability), states an
      initial response within **5 working days**, and says what is in scope for a report.
- [ ] AC-2.7: Given the test suite, when it runs, then a doc test asserts `SECURITY.md`
      exists, is linked from README and CLAUDE.md, and contains the sections and the six
      named entries required by AC-2.2–AC-2.6 and AC-2.9 — so the document cannot rot
      silently (v0.3.1 doc-introspection harness).
- [ ] AC-2.8: Given the GitHub repository, when a would-be reporter opens the Security tab,
      then **private vulnerability reporting is enabled** and the advisory form is reachable
      — the channel exists before `SECURITY.md` names it.
- [ ] AC-2.9: Given `SECURITY.md`'s statement of the build limits, then it distinguishes
      their basis: the file-count bound is a **measured** constant (naming the measurement),
      the 5 MB per-file cap is a **judgement call**. It must not imply both were derived the
      same way.
- [ ] AC-2.10: Given `README.md` and `CLAUDE.md`, then (a) the MCP tool list states that
      `build_graph` **writes** `<target>/.aspark-graph/` while the other eight only read;
      (b) the "disposable read model" phrasing (README *Design guarantees*, CLAUDE.md *What
      this is*) is qualified so it describes the **graph artifact**, not the server surface;
      (c) both link to `SECURITY.md`. No sentence in either file states or implies that the
      MCP surface is read-only.

### US-3 (Should): A build that cannot terminate becomes a build that refuses

> As an agent developer, I want an oversized or cyclic target to produce a clean refusal
> instead of a hang, so that a mistake costs me a message rather than a killed process.

**Acceptance criteria:**

- [ ] AC-3.1: Given an accepted target whose walk exceeds the entry-count bound, when I build
      it, then the build stops before parsing, exits 1 (MCP: the AC-1.2 shape with
      `"reason": "too_large"`), names the observed count and the limit, and writes **no**
      partial graph. The bound is a **fixed constant** whose value `/sprint-plan` derives
      from a stated measurement and records with that basis — no number is invented here.
- [ ] AC-3.2: Given an accepted target containing a source file larger than **5 MB**, when I
      build it, then the file is recorded as an **unparsed** `File` node with a stated
      reason, its contents are never read into memory, the build exits 0, and the build
      summary reports the count of size-skipped files.
- [ ] AC-3.3: Given an accepted target containing a symlink to one of its own ancestor
      directories, when I build it, then the build terminates (no infinite descent) and
      reports a result.
- [ ] AC-3.4: Given any repo below both bounds — including the `sample_repo` fixture and
      this repo itself — when I build it twice, then `graph.json` is byte-identical to a
      pre-change build of the same state: the bounds change no accepted repo's graph.

### US-4 (Could): The injection warning reaches the integration doc

> As an agent operator wiring aspark-graph into a gate, I want the "output is data, not
> instruction" rule where I copy the gate blocks from, so I read it at the point of use.

**Acceptance criteria:**

- [ ] AC-4.1: Given `docs/aspark-integration.md`, then it carries a short paragraph stating
      that graph output is data and never instruction, linking to `SECURITY.md`.

## 5. Non-Functional Requirements

| # | Category | Requirement (measurable) | How it's verified |
|---|---|---|---|
| NFR-1 | Performance | A verdict for any path is reached in <100 ms and reads **no** file contents — it inspects at most the three marker entries and never opens `graph.json` (AC-1.11). | /peer-review (timed test) |
| NFR-2 | Determinism | The byte-identical double-build test (base AC-1.2) stays green; `graph.json` for `sample_repo` and this repo is unchanged from v0.5.0. All bounds are fixed constants — no machine-dependent thresholds. | /peer-review |
| NFR-3 | Clean errors | No confinement or bound path surfaces a traceback: CLI → one line on stderr + exit 1; MCP → `{"found": false, "reason": …}`. Asserted for every refusal case in AC-1.1–1.5, 1.12, 3.1. | /peer-review |
| NFR-4 | Contract stability | Zero changes to query names, argument names, CLI↔MCP name parity, JSON-on-stdout, exit 1 on unbuilt graph, or any existing success-response key. `reason` gains two additive values (A13). No new runtime dependency; `mcp>=1.12,<1.20` unchanged. **Nothing that works on v0.5.0 stops working.** | /peer-review |
| NFR-5 | Documentation honesty | AC-2.3 (six named non-guarantees) + AC-2.4 (keyword denylist) are automated. **Both are defeatable by rephrasing** — they catch regression, not adversarial authorship — so the honesty guarantee still rests partly on a human `/peer-review` reading every guarantee sentence against the code. | /peer-review + doc test |
| NFR-6 | Reliability | A symlink cycle, a non-existent path, a regular file and an unreadable directory each produce a result rather than a hang or a crash (AC-1.5, AC-3.3). | /peer-review |
| NFR-7 | Architecture | The confinement rule is defined **once** in a shared module and enforced there; `cli.py` and `server.py` call it and contain no rule logic — the thin-adapter non-negotiable holds. | /peer-review |
| NFR-8 | Accessibility | N/A — headless CLI + MCP stdio, no UI. | N/A |
| NFR-9 | Second-code-path containment (A11) | The test-only bypass is unreachable from the CLI and MCP surfaces (AC-1.10) and undocumented; on an accepted path, bypassed and non-bypassed execution produce identical results. | /peer-review |

## 6. Out of Scope

- **A full STRIDE table.** A sketch of the actual boundary beats a matrix on a one-process
  local tool. Revisit if a remote transport ever ships.
- **Making `build_graph` read-only-by-default** (or splitting read/write servers) — a
  behaviour change to a contracted tool, needing a coordinated decision with aSPARK Core.
  This cycle only *documents* the write (AC-2.4/AC-2.10).
- **A README "Limits" section** carrying the count and size bounds. Deliberately chosen
  against (C17): the numbers live in `SECURITY.md` only and the README links across.
  Recorded so a later cycle reads this as a decision, not an oversight.
- **Recursion-depth limits**, per-build wall-clock timeouts, and memory caps.
- **Remote or authenticated MCP transport**, and lifting the `mcp<1.20` cap.
- **A configurable allowlist, an `--allow-any-path` flag, or a documented escape hatch.** The
  Q3 bypass is internal and test-only (AC-1.10); promoting it is a separate decision.
- **First builds of a repo subdirectory** (A7) and **sandboxing/process isolation** (A10).
- **Hardening the load path against a malformed `graph.json`.** The marker check never parses
  it (AC-1.11), so this feature neither creates nor fixes that pre-existing behaviour.
- **Sanitising or escaping graph output** to defuse injection. The mitigation is a documented
  contract (AC-2.5); filtering would imply a guarantee we cannot make.
- **Auditing/logging of tool calls.**

## 7. Clarifications

| # | Date | Question | Resolution |
|---|---|---|---|
| C1 | 2026-07-26 | Confinement on the CLI too, or only MCP? | **Both.** The parity test asserts CLI and MCP answer identically; confining one breaks that. The refused set is already outside the README's supported use. AC-1.7. |
| C2 | 2026-07-26 | Which of the nine tools actually walk the filesystem? | Only `build_graph`. The eight query tools resolve `repo` to `<repo>/.aspark-graph/graph.json`, and a graph-less directory already refuses today. **Confinement on the query tools buys consistency, not protection** — stated so the Musts are not oversold. It does bound `staleness`/`impact --diff`, which touch disk/git under `repo`. |
| C3 | 2026-07-26 | Does confinement close the unbounded-walk finding by itself? | Partly — hence Must. `/`, `/tmp` and most `$HOME`s hold no marker, so the common accidental target is refused before the walk. A `$HOME` that *is* a dotfiles git repo passes — hence US-3. Complementary, not redundant. |
| C4 | 2026-07-26 | Would `SECURITY.md` alone capture most of the value? | It captures the reviewer-facing value but none of the hang fix, and would have to document `repo`/`path` as unconstrained — a worse artifact. Roughly half the value; both Musts stay. |
| C5 | 2026-07-26 | Hard error or truncate on an oversized walk? | **Hard error** (AC-3.1) — a truncated graph is a silently wrong answer, which "fails loudly" forbids. A size-skipped *individual file* is different: an unparsed node (AC-3.2), which the model already supports. |
| C6 | 2026-07-26 | Which marker shapes count? | `.git` as **file or directory** (worktrees/submodules use a file), `.spark` as a directory, plus the third marker from C13. A **bare** repo has no `.git` entry and no worktree — correctly refused. AC-1.4. |
| C7 | 2026-07-26 | Does the default `repo="."` still work under the documented install? | Yes — the server's cwd is the aspark-graph checkout, which is marked. Regression test AC-1.8. |
| C8 | 2026-07-26 | Confinement scope: entry points or the library? (Q3) | **Library too** (AC-1.9), with an internal test-only bypass, constrained by AC-1.10/NFR-9. Second-code-path cost carried as A11. |
| C9 | 2026-07-26 | Where does the file-count bound's number come from? (Q4) | **Measured in `/sprint-plan`**, then pinned and documented with that basis (AC-3.1). No figure invented here. |
| C10 | 2026-07-26 | Per-file size cap. (Q5) | **5 MB** now (AC-3.2), explicitly a judgement call; AC-2.9 forbids `SECURITY.md` presenting it as derived like the measured bound. |
| C11 | 2026-07-26 | Reporting channel. (Q6) | **GitHub private security advisories**, 5-working-day initial response (AC-2.6); enabling it is a deliverable (AC-2.8). |
| C12 | 2026-07-26 | How does a CLI refusal render? (A9) | One line on stderr + exit 1, matching the existing `GraphNotBuiltError` split. Settled by convention; no user decision needed. |
| C13 | 2026-07-26 | A directory with a pre-existing `graph.json` but no `.git`/`.spark` — refuse, or treat the graph as a marker? | **Third marker (existence of `.aspark-graph/graph.json`)**, so nothing working today breaks and NFR-4 holds with no caveat. Narrow, not self-authorising: a fresh directory has no `graph.json`, so it only ever admits the **query** tools to a directory this tool already built (AC-1.11/1.12, A12). Marker = **file exists**, never parsed — cheaper, and keeps NFR-1's "reads no file contents"; a `.aspark-graph/` without `graph.json` is not a marker. A directory whose `.git` later vanished stays queryable — deliberate (AC-1.13). |
| C14 | 2026-07-26 | Does the existing parity test still prove AC-1.7 with the rule below the adapters? | **Extend it** — one path table, refusal rows alongside successful ones, no second test (AC-1.7). |
| C15 | 2026-07-26 | How is the anti-overclaim requirement actually checked? | **Both**: six named *Non-guarantees* entries (AC-2.3) plus a keyword denylist outside that section (AC-2.4), via the doc harness. N and the entries are fixed, so the check is falsifiable. NFR-5 records that both are defeatable by rephrasing — regression cover, not adversarial cover. |
| C16 | 2026-07-26 | Are `outside_confinement` / `too_large` a change to the Core contract? | **Additive, no coordination.** Rests on the unverified belief that Core branches on `found`, not `reason` — logged as A13 so a future cycle finds it. |
| C17 | 2026-07-26 | Does README/CLAUDE.md prose change, or only gain a link? | **Prose is fixed at the source** (AC-2.10): the MCP tool list marks `build_graph` as writing, and "disposable read model" is qualified to describe the artifact, not the surface. A README "Limits" section with the bound numbers is explicitly **not** included — Out of Scope. |

## 8. Design Review

<!-- Filled by /look-and-feel. Empty design review = gate stays red for UI-facing features. -->

- **Overall impression:** N/A — no UI. Headless CLI + MCP stdio server; the only "surface" is
  JSON output and one-line error text, covered by AC-1.1–1.5 and NFR-3.
- **Heuristics findings:**
- **Accessibility notes:**
- **Design risks & required changes:**

---

## ✅ SPEC GATE

*All boxes checked → `/sprint-plan` may start. Any box open → back to `/story-time` or `/look-and-feel`.*
*Evidence noted per line; the boxes are the user's to tick.*

- [x] Problem, goal and success signal are concrete — §1 names two personas and four observable signals
- [x] Every story has testable Given/When/Then acceptance criteria — 13 + 10 + 4 + 1
- [x] Stories are prioritized (MoSCoW) and at least one is a Must — two Musts, one Should, one Could
- [x] Non-functional requirements stated and measurable (or N/A with reason) — NFR-1…9; NFR-8 N/A (headless)
- [x] Clarify pass done: no ambiguity left unresolved or unparked — two passes, C1–C17, all resolved
- [x] Open questions resolved or explicitly accepted as risk — Q3–Q6 resolved; A7/A8/A10/A11/A12/A13 accepted
- [x] Out-of-scope section filled — ten items, two of them chosen against by the user
- [x] Constitution respected, or conflicts recorded — none exists; CLAUDE.md non-negotiables binding via NFR-2/3/4/7; no conflict found
- [x] Design review done for UI-facing features (or N/A with reason) — N/A, headless
- [x] Status set to `approved` by the user — 2026-07-26, explicit approval at the `/spark` spec gate
