# Spec: shallow-clone-warning

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (`/story-time`), Designer (`/look-and-feel`) |
| **Status** | `approved` |
| **Date** | 2026-09-30 |
| **Ticket** | none |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Summary:** A build on a shallow clone or on a directory without git (e.g. a ZIP download) silently loses `inferred` implements links, so `impact`/`story_trace` give weaker answers with no hint why. Goal: when the graph has at least one plan task, the build names the condition in one approved stderr line and in two always-present MCP `build_graph` booleans (`shallow_history`, `no_git_history`), and names the remedy. Exit code, stdout and graph.json bytes stay as in v0.7.1. Target v0.7.2.
- **Open:** `none` — Q1–Q7, the notice wording and A7–A9 resolved by the user 2026-09-29/30 (§7 C1–C10)
- **Binding ruling:** §4 User Stories for the current stories; §7 Clarifications for what changed since the last round and why
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Problem & Goal

- **Problem:** `inferred` implements edges come from commit history reachable from
  `HEAD` (`src/aspark_graph/inference.py`, `git.py::log_records`). A shallow clone
  truncates that history, and a directory without git has none. `git.py` treats both
  cases as "return less, never raise" (module docstring line 4), and the build prints
  nothing about either. Evidence from 2026-09-29, aspark-graph 0.7.1 from PyPI on
  this repo: `impact src/aspark_graph/queries.py` gave **2 stories / 8 ACs** (only
  `declared`/`extracted`) on a `git clone --depth 1`, and **4 stories / 17 ACs**
  (including `inferred`) on a full clone. The weaker answer looks complete.
- **Goal:** Anyone who builds without full git history learns this during the build,
  from the tool itself, and learns the fix. Nothing else about the build changes.
- **Success signal (observable):**
  1. On a fresh `git clone --depth 1` of this repo, `aspark-graph build .` prints the
     shallow notice and MCP `build_graph` returns `shallow_history: true`.
  2. Following the notice (`git fetch --unshallow`, rebuild) removes it, and
     `impact src/aspark_graph/queries.py` then equals the full-clone answer at the same
     `HEAD`. Record the SHA and the counts as evidence.
  3. On a full clone the build output is the same as v0.7.1's except for the two new
     MCP keys, both `false`. graph.json is byte-identical to v0.7.1 in every fixture.
- **Why now:** A public Show HN demo is planned. Readers who clone with `--depth 1`
  (a common habit, and the default of CI checkouts such as `actions/checkout`) or
  download a ZIP will see the headline `inferred` tier fail and not know why. The
  README (PR #7) only reaches readers who read that line. Size: S.

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
| A4 | A shallow clone of *any* depth gets the notice, even a deep one that misses nothing relevant. The tool cannot know which commits are missing, so the wording says "may be missing". | accepted |
| A5 | A detached `HEAD`, a `--single-branch` clone and a `--filter=blob:none` partial clone keep the full history reachable from `HEAD`, so they get no notice. | accepted. Blob-filter case to be checked hands-on in /peer-review |
| A6 | A `--filter=tree:0` partial clone may make `git log --name-only` fetch trees from the remote, which would be network access. Unverified. | accepted as risk, out of scope → BACKLOG |
| A7 | "Git history" means the build path lies inside a git work tree. A subdirectory of a git repo counts as having git; its shallowness is the enclosing repo's. A corrupt `.git` counts as no git. | accepted (C10) |
| A8 | A missing `git` binary is not detected on its own. It looks the same as "not a git repo", so it gets the no-history notice and `no_git_history: true`. The notice wording stays true in that case. | accepted (C10) |
| A9 | Each MCP key is `true` exactly when the CLI prints the matching notice. A shallow or no-git repo with no plan task therefore reports `false` in both keys. | accepted (C10) |
| Q7 | What does MCP report when there is no git history? | resolved: a second key, `no_git_history` (C8) |

## 4. User Stories

### US-1 (Must): CLI build names truncated history

> As an evaluator building on a shallow clone, I want the build to tell me that git history is truncated and how to fix it, so that I don't mistake a weaker `impact` answer for the full one.

Fixture: a git repo with ≥2 commits and ≥1 plan task whose id appears in a commit message, cloned with `git clone --depth 1 file://…`.

**Acceptance criteria:**

- [ ] AC-1.1: Given the shallow fixture, when `aspark-graph build .` runs, then stderr contains exactly this line, once:
  `Shallow git history: inferred links may be missing (run 'git fetch --unshallow', then rebuild).`
- [ ] AC-1.2: Given the same fixture, when the build runs, then the exit code is 0 and the stdout lines (`Built graph: …`, `Saved to …`) are the same as v0.7.1 prints for that fixture.
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
- [ ] AC-2.4: Given every fixture in US-1 and US-4, when built through the CLI and through MCP, then the CLI prints the shallow notice exactly when `shallow_history` is `true`, and prints the no-history notice exactly when `no_git_history` is `true`. The two keys are never both `true`, and graph.json bytes are identical between the two surfaces.

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

## 5. Non-Functional Requirements

| # | Category | Requirement (measurable) | How it's verified |
|---|---|---|---|
| NFR-1 | Performance | Detection adds at most one local git call per build, run once and not per commit. Median build time on this repo over 5 runs rises by < 5% compared with v0.7.1. | /peer-review timing |
| NFR-2 | Security & privacy | Notices and MCP keys contain no remote URL (URLs can embed credentials) and no path. Detection makes no network access: the build passes with the network disabled on the shallow fixture. | /peer-review |
| NFR-3 | Accessibility | N/A: headless tool. Notices are plain text with no ANSI colour, like the existing `Ignored …` line. | /peer-review |
| NFR-4 | Reliability / determinism | graph.json is byte-identical to v0.7.1 on the shallow, full, no-git and subdirectory fixtures, proven by a `git stash` round-trip against pre-change code (not only a double build). No fixture produces a traceback. | tests + /peer-review |
| NFR-5 | Observability / ops | At most one notice per build. The exact texts in AC-1.1 and AC-4.1 are a stable, user-approved contract, printed to stderr only, so stdout parsers are unaffected. | tests |
| NFR-6 | CLI≡MCP parity | The condition is decided in the shared build layer and each adapter only renders it (thin adapters). A parity test covers every fixture in AC-2.4. | /peer-review + parity test |

## 6. Out of Scope

- Storing any history flag in graph.json, or adding it to `impact`/`story_trace` answers (C4: Won't).
- Unshallowing automatically, or fetching anything. The tool stays offline and read-only on git.
- A dedicated notice for a missing `git` binary (C3 → BACKLOG). It gets the no-history notice (A8).
- A notice for a git repo with zero commits (C3 → BACKLOG).
- A strict flag or a non-zero exit (C1).
- Counting or naming the missing commits, or estimating how many links were lost.
- A shallow-aware `impact --diff`. A range deeper than the clone still fails with today's "invalid diff range" message.
- Guarding against network fetches in `--filter=tree:0` partial clones (A6 → BACKLOG).
- Notices for other causes of thin inference: commits without ids, ambiguous id-only commits (F1), squash merges.

## 7. Clarifications

| # | Date | Question | Resolution |
|---|---|---|---|
| C1 | 2026-09-29 | Exit code on a shallow build? | Always 0; the notice is information only (AC-1.2, AC-4.1). |
| C2 | 2026-09-29 | Shape of the MCP field? | Boolean `shallow_history`, always present, name given by the user (US-2). |
| C3 | 2026-09-29 | Other no-history cases? | Option (c): also "not a git repo / ZIP", with one no-history notice. US-4 becomes Should. Missing binary and zero commits → §6 / BACKLOG. |
| C4 | 2026-09-29 | Flag on query answers? | Won't. Nothing is stored; graph.json stays byte-identical to v0.7.1. |
| C5 | 2026-09-29 | When to warn? | Only when the graph has ≥1 plan task (AC-1.7, AC-4.3). |
| C6 | 2026-09-29 | Version? | Patch, 0.7.2. |
| C7 | 2026-09-29 | Clarify pass round 2: PO proposals A7–A9 and the two notice texts. | Resolved by C9 and C10. |
| C8 | 2026-09-30 | Q7: what does MCP report when there is no git history? | Option (a): `shallow_history` stays shallow-only, and a second always-present boolean `no_git_history` is added. AC-2.1–2.4 and AC-4.2–4.4 updated. |
| C9 | 2026-09-30 | Notice wording? | Both texts in AC-1.1 and AC-4.1 approved by the user exactly as written. |
| C10 | 2026-09-30 | A7 (subdirectory / corrupt `.git`), A8 (missing binary gets the no-history notice), A9 (each key is true exactly when the matching notice prints)? | A9 approved by the user. A7 and A8 stand; the user did not overrule them. |

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
- [x] Open questions are resolved or explicitly accepted as risk (A3, A6 accepted as risk)
- [x] Out-of-scope section is filled (something was consciously cut)
- [x] Constitution (`.spark/constitution.md`) respected, or conflicts recorded as open questions (no constitution; CLAUDE.md non-negotiables applied: determinism, thin adapters, parity)
- [x] Design review done for UI-facing features (or marked N/A with reason). N/A: no UI; the notice wording was approved at the spec gate (C9).
- [x] Line budget respected: Ist ~180 / Soll ~250 (excluding HTML comments)
- [x] Status set to `approved` by the user (2026-10-03)
