# Spec: shallow-clone-warning

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (`/story-time`), Designer (`/look-and-feel`) |
| **Status** | `approved` |
| **Date** | 2026-10-03 |
| **Ticket** | none |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Summary:** A build on a shallow clone or on a directory without git (e.g. a ZIP download) silently degrades `inferred` implements links, so `impact`/`story_trace` give wrong answers with no hint why. Worse, on a shallow clone with a non-merge tip the grafted boundary commit links *every* tracked file (review F1: 40 stories / 181 ACs instead of 4 / 17). Goal: (1) in a shallow repo, grafted boundary commits contribute no inferred links, so truncated history only ever loses links (US-5, C11); (2) when the graph has at least one plan task, the build names the condition in one approved stderr line and in two always-present MCP `build_graph` booleans (`shallow_history`, `no_git_history`), and names the remedy. Exit code and stdout format stay as in v0.7.1; graph.json is byte-identical to v0.7.1 for every non-shallow build. Target v0.7.2.
- **Open:** `none` — Q1–Q7, the notice wording and A7–A9 resolved 2026-09-29/30 (C1–C10); review F1 resolved by the user 2026-10-03 (C11); A10 and the undeterminable-boundary case confirmed by the user 2026-10-03 (C12).
- **Binding ruling:** §4 User Stories for the current stories; §7 Clarifications for what changed since the last round and why (round 2: C11, US-5, AC-1.2, NFR-1, NFR-4)
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Problem & Goal

- **Problem:** `inferred` implements edges come from commit history reachable from
  `HEAD` (`src/aspark_graph/inference.py`, `git.py::log_records`). A shallow clone
  truncates that history, and a directory without git has none. `git.py` treats both
  cases as "return less, never raise" (module docstring line 4), and v0.7.1 prints
  nothing about either. Truncation does not only lose links, it also invents them:
  a grafted boundary commit has no parent, so `git log --name-only` lists every
  tracked file as touched, and inference links all of them to the task ids in that
  commit's message. Evidence from review F1 (2026-10-03), this repo at `19a5bef`
  (non-merge tip): a `--depth 1` build made **4716** inferred edges against **132** on
  a full clone, and `impact src/aspark_graph/queries.py` gave **40 stories / 181 ACs**
  against **4 / 17**. v0.7.1 behaves the same, so the bug is pre-existing. The
  earlier evidence (2026-09-29: 2 stories / 8 ACs on `--depth 1`) held only because
  the tip then was a merge commit, which `--no-merges` skips. Either way the wrong
  answer looks complete.
- **Goal:** Truncated history only ever loses inferred links and never invents them.
  Anyone who builds without full git history learns this during the build, from the
  tool itself, and learns the fix. A non-shallow build is otherwise unchanged.
- **Success signal (observable):**
  1. On a fresh `git clone --depth 1` of this repo at a non-merge tip,
     `aspark-graph build .` prints the shallow notice, MCP `build_graph` returns
     `shallow_history: true`, and `impact src/aspark_graph/queries.py` is a subset of
     the full-clone answer at the same `HEAD`. Record the SHA and the counts.
  2. Following the notice (`git fetch --unshallow`, rebuild) removes it, and
     `impact src/aspark_graph/queries.py` then equals the full-clone answer.
  3. On every non-shallow build the output is the same as v0.7.1's except for the two
     new MCP keys, both `false`, and graph.json is byte-identical to v0.7.1.
- **Why now:** A public Show HN demo is planned. Readers who clone with `--depth 1`
  (a common habit, and the default of CI checkouts such as `actions/checkout`) or
  download a ZIP will see the headline `inferred` tier fail, today often by a factor
  of ten in the wrong direction. The README (PR #7) only reaches readers who read
  that line. Size: S→M (US-5 touches inference).

## 2. Target Users

- **Show HN / first-time evaluator:** clones the repo shallowly or downloads a ZIP,
  runs `build` then `impact`, and judges the tool on the result.
- **Agent using the MCP server:** calls `build_graph` and never sees stderr. It needs
  the condition in the response (parity precedent: `ignored_legacy_files`, v0.7.1).
- **CI user:** builds in a pipeline whose checkout is shallow by default. This user
  is assumed, not observed (A3).

## 3. Assumptions & Open Questions

| # | Assumption / Question | Resolution |
|---|---|---|
| A1 | Original phrasing (translated from German): "Show a warning when the build runs on a shallow clone." The underlying need is honesty about a degraded answer. | recorded |
| A2 | Both notices are build *output*, never graph *content*, the same way `ignored_legacy_files` is handled. | accepted (C4) |
| A3 | CI checkouts are shallow by default. We don't know that anyone runs aspark-graph in CI today. | accepted as risk, low impact |
| A4 | A shallow clone of *any* depth gets the notice, even a deep one that misses nothing relevant. The tool cannot know which commits are missing, so the wording says "may be missing". With US-5 that wording is accurate. | accepted (C11) |
| A5 | A detached `HEAD`, a `--single-branch` clone and a `--filter=blob:none` partial clone keep the full history reachable from `HEAD`, so they get no notice. | accepted; blob-filter case verified in review round 1 |
| A6 | A `--filter=tree:0` partial clone may make `git log --name-only` fetch trees from the remote, which would be network access. Unverified. | accepted as risk, out of scope → BACKLOG |
| A7 | "Git history" means the build path lies inside a git work tree. A subdirectory of a git repo counts as having git; its shallowness is the enclosing repo's. A corrupt `.git` counts as no git. | accepted (C10) |
| A8 | A missing `git` binary is not detected on its own. It looks the same as "not a git repo", so it gets the no-history notice and `no_git_history: true`. The notice wording stays true in that case. | accepted (C10) |
| A9 | Each MCP key is `true` exactly when the CLI prints the matching notice. A shallow or no-git repo with no plan task therefore reports `false` in both keys. | accepted (C10) |
| A10 | NFR-1's budget (one extra local git call, < 5% median rise) covers detection *and* the US-5 fix together, so the fix may not add a second git process. Review round 1 measured +3.2% for detection alone. | Confirmed by the user 2026-10-03 (C12) |
| Q7 | What does MCP report when there is no git history? | resolved: a second key, `no_git_history` (C8) |

## 4. User Stories

### US-1 (Must): CLI build names truncated history

> As an evaluator building on a shallow clone, I want the build to tell me that git history is truncated and how to fix it, so that I don't mistake a weaker `impact` answer for the full one.

Fixture: a git repo with ≥2 commits and ≥1 plan task whose id appears in a commit message, cloned with `git clone --depth 1 file://…`.

**Acceptance criteria:**

- [ ] AC-1.1: Given the shallow fixture, when `aspark-graph build .` runs, then stderr contains exactly this line, once:
  `Shallow git history: inferred links may be missing (run 'git fetch --unshallow', then rebuild).`
- [ ] AC-1.2: Given the same fixture, when the build runs, then the exit code is 0 and the stdout lines (`Built graph: …`, `Saved to …`) have v0.7.1's format, with counts that differ from v0.7.1's only by the inferred edges US-5 drops. *(amended by C11)*
- [ ] AC-1.3: Given a full clone of the same repo, when the build runs, then stderr equals v0.7.1's (no notice).
- [ ] AC-1.4: Given the shallow fixture, when the build runs with `--full` and again incrementally (graph already present), then the notice appears on each run.
- [ ] AC-1.5: Given a `--depth 1` clone of this repo, when the user runs `git fetch --unshallow` and rebuilds, then the notice is gone and `impact src/aspark_graph/queries.py` equals the full-clone result at the same `HEAD` (stories, ACs, confidence tiers).
- [ ] AC-1.6: Given a detached `HEAD`, or a `--single-branch` clone at full depth, when the build runs, then no notice appears.
- [ ] AC-1.7: Given a shallow repo whose graph has no plan Task node, when the build runs, then no notice appears.

### US-2 (Must): MCP `build_graph` reports the same condition

> As an agent calling `build_graph`, I want the response to state whether git history was truncated or absent, so that I can explain a thin answer without seeing stderr.

**Acceptance criteria:**

- [ ] AC-2.1: Given the shallow fixture, when `build_graph` is called, then the response contains `"shallow_history": true` and `"no_git_history": false`.
- [ ] AC-2.2: Given a full clone, when `build_graph` is called, then the response contains `"shallow_history": false` and `"no_git_history": false`, and every v0.7.1 key and value is unchanged.
- [ ] AC-2.3: Given the fixture from AC-1.7 (shallow, no plan task), when `build_graph` is called, then both keys are `false` (A9).
- [ ] AC-2.4: Given every fixture in US-1, US-4 and US-5, when built through the CLI and through MCP, then the CLI prints the shallow notice exactly when `shallow_history` is `true`, and prints the no-history notice exactly when `no_git_history` is `true`. The two keys are never both `true`, and graph.json bytes are identical between the two surfaces.

### US-3 (Should): README documents the notices

> As a reader of the README, I want the notice text and the remedy documented next to the full-clone advice, so that I recognise the message and know it is expected.

**Acceptance criteria:**

- [ ] AC-3.1: Given the README, when a reviewer compares it with real CLI stderr from the shallow and the no-git fixtures, then both notices are quoted character for character. The README also names `shallow_history`, `no_git_history` and `git fetch --unshallow`.

### US-4 (Should): No git history is named too

> As an evaluator who downloaded a ZIP, I want the build to say that no git history was available, so that the absence of `inferred` links is explained.

Fixture: a `.spark/`-marked directory that is not inside a git work tree and has ≥1 plan task.

**Acceptance criteria:**

- [ ] AC-4.1: Given the no-git fixture, when `aspark-graph build .` runs, then stderr contains exactly this line, once, and the exit code is 0:
  `No git history: inferred links are missing (build from a full git clone to get them).`
- [ ] AC-4.2: Given the no-git fixture, when `build_graph` is called, then the response contains `"no_git_history": true` and `"shallow_history": false`, and graph.json is byte-identical to the CLI build.
- [ ] AC-4.3: Given the no-git fixture with no plan Task node, when the build runs, then no notice appears and MCP reports `"no_git_history": false`.
- [ ] AC-4.4: Given a build path that is a subdirectory of a full git clone, when the build runs, then no notice appears and both MCP keys are `false` (A7).

### US-5 (Must): Truncated history never invents inferred links

> As an evaluator building on a shallow clone, I want the build to drop what it cannot know rather than guess, so that a shallow `impact` answer is at worst incomplete, never inflated.

Fixture: a git repo with ≥5 commits and ≥3 tracked files. Its tip is a non-merge commit whose message names plan task `T1` and that touches one file; no other commit names `T1`. "Boundary commit" means a commit whose parents a shallow repository lacks.

**Acceptance criteria:**

- [ ] AC-5.1: Given a `--depth 1` clone of the fixture, when the build runs (with `--full` and again incrementally), then graph.json contains no `inferred` implements edge from `T1`.
- [ ] AC-5.2: Given a `--depth 1` and a full clone of the fixture at the same `HEAD`, when both are built, then every `inferred` edge (task, file) of the shallow build is also in the full build, and the non-`inferred` edges of the two builds are equal.
- [ ] AC-5.3: Given a `--depth 3` clone of the fixture where the oldest kept commit is a non-merge commit naming task `T2`, when the build runs, then that commit contributes no `inferred` edge, the two newer kept commits contribute exactly the edges they contribute on the full clone, and AC-5.2's subset rule holds.
- [ ] AC-5.4: Given every non-shallow fixture of US-1, US-4 and US-5 (full clone, detached `HEAD`, `--single-branch`, subdirectory, no-git), when the build runs, then graph.json is byte-identical to v0.7.1's.
- [ ] AC-5.5: Given a full, non-shallow repo whose root commit names a task id and adds files, when the build runs, then the root commit's `inferred` edges are present and graph.json is byte-identical to v0.7.1's.
- [ ] AC-5.6: Given this repo cloned with `--depth 1` at a non-merge tip, when `impact src/aspark_graph/queries.py` runs, then its stories and ACs are a subset of the full-clone answer at the same `HEAD`. Record SHA and counts.

## 5. Non-Functional Requirements

| # | Category | Requirement (measurable) | How it's verified |
|---|---|---|---|
| NFR-1 | Performance | Detection and the US-5 fix together add at most one local git call per build, run once and not per commit (A10). Median build time on this repo over 5 runs rises by < 5% compared with v0.7.1. | /peer-review timing |
| NFR-2 | Security & privacy | Notices and MCP keys contain no remote URL (URLs can embed credentials) and no path. Detection and the US-5 fix make no network access: the build passes with the network disabled on the shallow fixtures. | /peer-review |
| NFR-3 | Accessibility | N/A: headless tool. Notices are plain text with no ANSI colour, like the existing `Ignored …` line. | /peer-review |
| NFR-4 | Reliability / determinism | graph.json is byte-identical to v0.7.1 on every non-shallow build (full, detached, single-branch, subdirectory, no-git). A shallow build differs from v0.7.1 only by lacking the `inferred` edges that boundary commits alone contributed; no edge is added or re-tiered. Both are proven against pre-change code, not only a double build. A shallow build is deterministic across two runs. No fixture produces a traceback; the fix never raises. *(amended by C11)* | tests + /peer-review |
| NFR-5 | Observability / ops | At most one notice per build. The exact texts in AC-1.1 and AC-4.1 are a stable, user-approved contract, printed to stderr only, so stdout parsers are unaffected. | tests |
| NFR-6 | CLI≡MCP parity | The condition and the boundary exclusion are decided in the shared build layer and each adapter only renders the result (thin adapters). A parity test covers every fixture in AC-2.4. | /peer-review + parity test |

## 6. Out of Scope

- Storing any history flag in graph.json, or adding it to `impact`/`story_trace` answers (C4: Won't).
- Unshallowing automatically, or fetching anything, including a boundary commit's real diff. The tool stays offline and read-only on git.
- Changing either notice text (C9 stands; C11 makes it accurate).
- A dedicated notice for a missing `git` binary (C3 → BACKLOG). It gets the no-history notice (A8).
- A notice for a git repo with zero commits (C3 → BACKLOG).
- A strict flag or a non-zero exit (C1).
- Counting or naming the missing commits, or estimating how many links were lost.
- A shallow-aware `impact --diff`. A range deeper than the clone still fails with today's "invalid diff range" message.
- Guarding against network fetches in `--filter=tree:0` partial clones (A6 → BACKLOG).
- Other sources of over-broad inferred links in full repos, e.g. a genuine root or bulk-import commit that touches many files. It keeps v0.7.1 behaviour (AC-5.5).
- Notices for other causes of thin inference: commits without ids, ambiguous id-only commits (F1 of aspark-graph), squash merges.

## 7. Clarifications

| # | Date | Question | Resolution |
|---|---|---|---|
| C1 | 2026-09-29 | Exit code on a shallow build? | Always 0; the notice is information only (AC-1.2, AC-4.1). |
| C2 | 2026-09-29 | Shape of the MCP field? | Boolean `shallow_history`, always present, name given by the user (US-2). |
| C3 | 2026-09-29 | Other no-history cases? | Option (c): also "not a git repo / ZIP", with one no-history notice. US-4 becomes Should. Missing binary and zero commits → §6 / BACKLOG. |
| C4 | 2026-09-29 | Flag on query answers? | Won't. Nothing is stored; graph.json stays byte-identical to v0.7.1 (narrowed by C11 to non-shallow builds). |
| C5 | 2026-09-29 | When to warn? | Only when the graph has ≥1 plan task (AC-1.7, AC-4.3). |
| C6 | 2026-09-29 | Version? | Patch, 0.7.2. |
| C7 | 2026-09-29 | Clarify pass round 2: PO proposals A7–A9 and the two notice texts. | Resolved by C9 and C10. |
| C8 | 2026-09-30 | Q7: what does MCP report when there is no git history? | Option (a): `shallow_history` stays shallow-only, and a second always-present boolean `no_git_history` is added. AC-2.1–2.4 and AC-4.2–4.4 updated. |
| C9 | 2026-09-30 | Notice wording? | Both texts in AC-1.1 and AC-4.1 approved by the user exactly as written. |
| C10 | 2026-09-30 | A7 (subdirectory / corrupt `.git`), A8 (missing binary gets the no-history notice), A9 (each key is true exactly when the matching notice prints)? | A9 approved by the user. A7 and A8 stand; the user did not overrule them. |
| C11 | 2026-10-03 | Review F1: on a shallow clone with a non-merge tip, the grafted boundary commit links every tracked file, so "may be missing" names the wrong direction. Amend the wording, fix inference, or waive? | Option (b), user decision: in a shallow repo, grafted boundary commits contribute no inferred links, so truncated history only loses links. New US-5 (Must). NFR-4 and C4 narrowed: graph.json unchanged vs v0.7.1 for every non-shallow build; shallow builds change only by dropping the boundary commits' inferred edges. AC-1.2 and NFR-1 amended to match. Notice texts (C9) unchanged, now accurate. How to identify boundary commits is the EM's call. |
| C12 | 2026-10-03 | A10 and the PO's open point: how much may the US-5 fix cost, and what if the boundary commits cannot be determined (e.g. a corrupt shallow marker)? | User decision: (1) A10 confirmed. Detection and the fix share one local git call per build, and the median rise stays < 5% (NFR-1 unchanged). (2) If a shallow repo's boundary commits cannot be determined, inference contributes no inferred edges for that build. It errs toward losing links, never inventing them (US-5), and never raises. |

## 8. Design Review

- **Overall impression:** N/A. The tool has no UI. The user reviewed and approved the two notice texts at the spec gate instead (C9).
- **Heuristics findings:** N/A
- **Accessibility notes:** N/A (see NFR-3)
- **Design risks & required changes:** none

---

## ✅ SPEC GATE

*All boxes checked → `/sprint-plan` may start. Any box open → back to `/story-time` or `/look-and-feel`.*

- [x] Problem, goal and success signal are concrete (no buzzwords, no "everyone")
- [x] Every story has testable Given/When/Then acceptance criteria
- [x] Stories are prioritized (MoSCoW) and at least one is a Must
- [x] Non-functional requirements are stated and measurable (or marked N/A with reason)
- [x] Clarify pass done: no ambiguity left unresolved or unparked
- [x] Open questions are resolved or explicitly accepted as risk (A3, A6 accepted as risk; A10 confirmed by the user, C12)
- [x] Out-of-scope section is filled (something was consciously cut)
- [x] Constitution (`.spark/constitution.md`) respected, or conflicts recorded as open questions (no constitution; CLAUDE.md non-negotiables applied: determinism, thin adapters, parity)
- [x] Design review done for UI-facing features (or marked N/A with reason). N/A: no UI; the notice wording was approved at the spec gate (C9).
- [x] Line budget respected: Ist ~208 / Soll ~250 (excluding HTML comments)
- [x] Status set to `approved` by the user (2026-10-03, re-approval after review F1)
