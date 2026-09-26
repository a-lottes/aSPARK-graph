# Spec: current-artifact-names

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (`/story-time`), Designer (`/look-and-feel`) |
| **Status** | `approved` |
| **Date** | 2026-09-24 |
| **Ticket** | none |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Summary:** aspark-graph reads only the legacy `qa-report.md`/`review-report.md`/`release-notes.md`, so on every current aSPARK project the QA and review layers are empty; read the current `qa.md`/`review.md`/`release.md` too (current wins, ignored legacy files named in build output), keep legacy byte-identical, fix language/artifact-name docs. Target v0.7.1.
- **Open:** `none` — Q1–Q5 resolved by the user 2026-09-24 (§3, §7 C1–C5)
- **Binding ruling:** §4 User Stories for the current stories; §7 Clarifications for what changed since the last round and why
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Problem & Goal

- **Problem:** The artifact parser looks for exactly three legacy file names per
  feature (`src/aspark_graph/artifacts.py:78-80`). aSPARK Core's ceremonies have
  since switched the files they *write* to `review.md`, `qa.md` and `release.md`
  (`/Users/andreaslottes/aSPARK/skills/demo-day/SKILL.md`, `go-live/SKILL.md`,
  `spark/SKILL.md:51-53`; Core's own `.spark/` holds 14 `qa.md`, 15 `review.md`,
  15 `release.md`). Core's *templates* still carry the legacy names, which is why
  the mismatch went unnoticed. The result is silent, not loud: on a clone of
  steamcore (13 features, full QA reports) the graph has 269 ACs but **0 QACheck and
  0 Finding nodes**; `gate_health` lists every AC as unverified and no open finding
  ever appears; `story_trace` can never answer "did its ACs pass QA?". The tool's
  headline question is answered wrongly — "unverified" — on exactly the projects it
  is meant for. `impact` is unaffected.
- **Goal:** A current aSPARK project gets a complete artifact layer — QA checks,
  review findings, review/QA/release statuses — without renaming any file, while
  legacy-named trails (including this repo's own) build exactly as before.
- **Success signal (observable):**
  1. Building a current-name trail yields one `QACheck` per AC row in each `qa.md`
     verification table and one `Finding` per `F<n>` row in each `review.md`
     findings table — checked on Core's own `.spark/` (13 features with `qa.md`) and,
     as manual release evidence, on a steamcore clone (QACheck and Finding counts > 0
     where today 0).
  2. `gate_health` on a steamcore feature whose `qa.md` marks all ACs passed reports
     `unverified_acs: []`.
  3. A legacy-only trail (this repo's `.spark/`) builds a `graph.json` byte-identical
     to v0.7.0's.
- **Why now:** Every project on current Core gets wrong gate answers today, and
  Core's gate skills consult the graph (`/peer-review`, `/demo-day`). The tool is
  published on PyPI, so every new adopter hits this on first use.

## 2. Target Users

- **Primary:** a developer or agent in a project run on current aSPARK Core who asks
  `gate_health` / `story_trace` whether a feature's ACs passed QA and whether review
  findings are still open — and today gets "unverified, no findings" for everything.
- **Secondary:** the aspark-graph maintainer, whose own trail and older adopters'
  trails use legacy names and must not regress.
- **Not a target:** projects whose artifacts use any other naming (hand-rolled trails,
  case variants like `QA.md`), and anyone wanting Release as a first-class node (G1).

## 3. Assumptions & Open Questions

| # | Assumption / Question | Resolution |
|---|---|---|
| A1 | Current-name files have the same structure as legacy ones; only the name changed. Verified on Core's `ticket-import` and Core's templates; not yet on all 13 steamcore features. | Accepted as risk; mitigated by the pre-release check (Q2, AC-5.4). A drift found there blocks the release and returns as a finding — it is not waved through. |
| A2 | Name resolution is per artifact, not per feature: a folder with `qa.md` and `review-report.md` reads both. | Accepted — AC-4.3 |
| A3 | Merging a legacy and a current file of the same kind is never wanted; one of the two is read. | Accepted — per the user's "current name wins" |
| A4 | This repo's own `.spark/` stays on legacy names; it is the legacy regression fixture. | Accepted — see §6 |
| A5 | Original phrasing was a solution ("read these file names, current wins"); the underlying need is "gate answers on current projects are correct". The file names are the observable contract with Core, so they stay in the stories. | Recorded |
| Q1 | Shadowing visibility when both names exist. | **RESOLVED 2026-09-24: (b)** — build succeeds; its output names each ignored legacy file. → AC-4.4, AC-4.5, NFR-7 |
| Q2 | Drift in newly-read files. | **RESOLVED 2026-09-24: (a)** — fail loudly with the same named drift error as legacy files; Core and steamcore must build cleanly before release. → AC-5.2, AC-5.4 |
| Q3 | Release version text. | **RESOLVED 2026-09-24: (a)** — Version cell verbatim, same treatment as legacy files; cleanup stays with G1 `release-nodes`. → AC-3.2 |
| Q4 | Docs scope. | **RESOLVED 2026-09-24: (b)+(c)** — also correct `CLAUDE.md:8`; README states which artifact file names are read (current and legacy). → AC-6.2, AC-6.3 |
| Q5 | Steamcore evidence. | **RESOLVED 2026-09-24: (a)** — manual steamcore-clone run is release evidence; automated tests use a committed current-name fixture. → AC-5.4, NFR-1 |

## 4. User Stories

### US-1 (Must): QA results from `qa.md` reach the graph

> As a developer or agent on a current aSPARK project, I want the ACs verified in a feature's `qa.md` to show as verified in the graph, so that `gate_health` and `story_trace` tell me which ACs actually passed QA.

**Acceptance criteria:**

- [ ] AC-1.1: Given a feature folder with `spec.md` and `qa.md` (no `qa-report.md`) whose verification table marks AC-1.1 `✅ pass`, when the repo is built, then `story_trace` for that story shows AC-1.1 with a passing QA check.
- [ ] AC-1.2: Given that same feature where every AC row passes, when `gate_health` is queried, then `unverified_acs` is empty.
- [ ] AC-1.3: Given a `qa.md` with a failing AC row, when built and `gate_health` is queried, then that AC appears in `unverified_acs`.
- [ ] AC-1.4: Given a `qa.md` with status `passed`, when the feature node is inspected via `get_node`, then its QA status reads `passed`.

### US-2 (Must): Review findings from `review.md` reach the graph

> As a developer or agent on a current aSPARK project, I want the findings recorded in a feature's `review.md` to be in the graph, so that `gate_health` shows which findings are still open.

**Acceptance criteria:**

- [ ] AC-2.1: Given a `review.md` whose findings table has F1 with status `open` and F2 with status `fixed`, when built and `gate_health` is queried, then `open_findings` lists F1 and not F2.
- [ ] AC-2.2: Given a finding whose location names a file present in the repo, when built, then that finding is linked to that file exactly as a legacy `review-report.md` finding would be.
- [ ] AC-2.3: Given a `review.md` with status `passed`, when the feature node is inspected via `get_node`, then its review status reads `passed`.

### US-3 (Should): Release status from `release.md` reaches the graph

> As a developer or agent, I want a feature's `release.md` status and version on the feature node, so that I can see from the graph whether and as what a feature shipped.

**Acceptance criteria:**

- [ ] AC-3.1: Given a `release.md` with status `handed-off`, when built, then the feature node's release status reads `handed-off`.
- [ ] AC-3.2: Given a `release.md` whose Version cell is prose (e.g. `v0.12.0 (proposed, pr mode — no tag …)`), when built, then the feature node's version is exactly what the same cell yields in a `release-notes.md` today — no extraction or normalisation.

### US-4 (Must): One source per artifact when both names exist

> As a developer or agent, I want exactly one file read per artifact kind, with the current name preferred and any ignored file named, so that a leftover legacy file never doubles or contradicts the QA and review picture without me knowing.

**Acceptance criteria:**

- [ ] AC-4.1: Given a feature with `qa.md` (AC-1.1 passes) and `qa-report.md` (AC-1.1 fails), when built, then only `qa.md`'s result is in the graph — AC-1.1 is not in `unverified_acs` and has no failing QA check.
- [ ] AC-4.2: The same holds for `review.md` over `review-report.md` and `release.md` over `release-notes.md`: no finding or status from the shadowed legacy file appears in the graph.
- [ ] AC-4.3: Given a feature with `qa.md` and `review-report.md` (no `review.md`), when built, then both QA checks and findings are present and nothing is reported as ignored.
- [ ] AC-4.4: Given a feature with both `qa.md` and `qa-report.md`, when built via the CLI, then the build succeeds (exit 0) and its output names `.spark/<feature>/qa-report.md` as ignored; every shadowed legacy file in the repo is named, one per file, in the same order on every run.
- [ ] AC-4.5: Given the same repo, when built via the `build_graph` MCP tool, then its result names the same ignored files as the CLI (inherited CLI ≡ MCP parity).
- [ ] AC-4.6: Given a feature that has both names and the same feature with only the current name, when each is built, then the two `graph.json` files are byte-identical — the notice is build output, never graph content.

### US-5 (Must): Legacy-named trails keep working unchanged

> As the aspark-graph maintainer, I want trails that use only the legacy names to build exactly as in v0.7.0, so that this fix regresses nobody.

**Acceptance criteria:**

- [ ] AC-5.1: Given this repo at the commit that ships v0.7.1 with its legacy-only `.spark/`, when built with v0.7.0 and with v0.7.1, then the two `graph.json` files are byte-identical.
- [ ] AC-5.2: Given a structurally broken `qa.md` or `review.md` (e.g. no verification / findings section), when built, then the build fails with the same named template-drift error legacy files get, naming the `qa.md`/`review.md` path.
- [ ] AC-5.3: Given a trail using current names and the same trail with the files renamed to legacy names, when each is built, then the two `graph.json` files are byte-identical.
- [ ] AC-5.4: Given Core's own `.spark/` and a steamcore clone, when each is built with the release candidate before v0.7.1 ships, then neither build raises a drift error and both report QACheck and Finding counts > 0; the commands and counts are recorded as release evidence.

### US-6 (Should): Docs state languages and artifact names consistently

> As a prospective user reading the README, I want one consistent statement of which languages are supported and which artifact files are read, so that I can tell whether my repo is covered.

**Acceptance criteria:**

- [ ] AC-6.1: Given the released README, when searched, then every statement of the supported-language set names the same five: Python, TypeScript/JavaScript, Java, Go, Rust — and no "six" count remains.
- [ ] AC-6.2: Given the released `CLAUDE.md`, when line 8's language list is read, then it names the same five languages.
- [ ] AC-6.3: Given the released README, when read, then it names the artifact files parsed per feature — `spec.md`, `plan.md`, `review.md`/`review-report.md`, `qa.md`/`qa-report.md`, `release.md`/`release-notes.md` — and states that the current name wins when both exist.

## 5. Non-Functional Requirements

| # | Category | Requirement (measurable) | How it's verified |
|---|---|---|---|
| NFR-1 | Determinism (inherited non-negotiable) | A double build of an unchanged repo with current-name files yields byte-identical `graph.json`; which file wins, and the order of ignored-file notices, never depends on directory listing order. | /peer-review: double-build test on a committed current-name fixture |
| NFR-2 | Backward compatibility | Legacy-only trail graph is byte-identical to v0.7.0's (AC-5.1); existing test suite passes with zero modified expectations. | /peer-review: `uv run pytest` |
| NFR-3 | CLI ≡ MCP parity (inherited) | CLI build and `build_graph` produce byte-identical graphs and the same ignored-file list on a trail mixing both naming schemes. | /peer-review: parity test |
| NFR-4 | Performance | No new target; the existing `slow`-marked build benchmark passes unmodified. | /peer-review: `uv run pytest -m slow` |
| NFR-5 | Security & privacy | No new read surface: only files inside an already-scanned `.spark/<feature>/` folder are read; path confinement unchanged. | /peer-review |
| NFR-6 | Accessibility | N/A — headless CLI/MCP tool, no UI. | N/A |
| NFR-7 | Observability | Every shadowed legacy file is named in build output (AC-4.4); the artifact-entity count in the build summary rises on a current-name trail. | /demo-day |

## 6. Out of Scope

- **Renaming this repo's own `.spark/` files** to current names — they stay legacy as the regression fixture (A4).
- **Renaming Core's templates** (`qa-report.md` etc.) — a Core concern; aspark-graph only reads outputs.
- **Normalising the Version cell** into a clean semver, and Release/Commit nodes — G1 `release-nodes` (Q3).
- **Parsing QA "Exploratory Findings" as `Finding` nodes** — not parsed today under the legacy name either.
- **Any other file names:** case variants (`QA.md`), `evidence.md`, user-configurable names.
- **Template-version markers / drift-as-version-conflict** — G5 `template-version-guard`.
- **Changes to `gate_health`/`story_trace` semantics or output shape** — the query contract is normative (BACKLOG §2).
- **Merging legacy and current files** of the same kind (A3); **a warn-and-skip mode** for drifted files (Q2).
- **Automating the steamcore check** in the test suite — it stays a manual release step (Q5).

## 7. Clarifications

| # | Date | Question | Resolution |
|---|---|---|---|
| C1 | 2026-09-24 | (Edge cases) What does the user see when both names exist? | User: build succeeds, output names each ignored legacy file → AC-4.4–4.6, NFR-7 |
| C2 | 2026-09-24 | (Error behavior) May newly-read files turn a green build red? | User: yes, fail loudly as legacy; Core + steamcore verified clean before release → AC-5.2, AC-5.4 |
| C3 | 2026-09-24 | (Data) What goes into the version field from a prose Version cell? | User: verbatim, as legacy; cleanup in G1 → AC-3.2, §6 |
| C4 | 2026-09-24 | (Scope) Which docs are corrected alongside the README? | User: also `CLAUDE.md:8`; README names artifact files read → AC-6.2, AC-6.3 |
| C5 | 2026-09-24 | (Integrations) Is steamcore evidence required for release? | User: manual clone run as evidence; committed current-name fixture for tests → AC-5.4, NFR-1, §6 |
| C6 | 2026-09-24 | (Data) Per-artifact or per-feature name resolution? | Per artifact (A2, AC-4.3) |
| C7 | 2026-09-24 | (Roles) Any permission concept? | N/A — local tool, no roles |
| C8 | 2026-09-24 | (UX states) UI states? | N/A — headless; output is the existing build summary and query JSON |
| C9 | 2026-09-24 | (Integrations) Does the ignored-file notice appear via MCP too, and can it touch `graph.json`? | Derived from inherited CLI ≡ MCP parity and determinism: both surfaces name it; never in `graph.json` → AC-4.5, AC-4.6 |
| C10 | 2026-09-24 | (Error behavior) What if the pre-release check finds drift in steamcore? | Release blocked; returns as a finding (A1). No warn-and-skip escape (C2). |
| C11 | 2026-09-24 | (Scope, raised at the plan gate) `CLAUDE.md:28` says "six languages supported" in the v0.5.0 history entry — correct it too? | Yes, by the user at the plan gate: extends AC-6.2 to line 28 (five languages). Recorded here, not reworded into the AC; tracked in plan T6. |
| C12 | 2026-09-24 | (Risk A1 materialised, found at the start of /increment) Do current-template QA reports have the structure the QA parser expects? | No. Core's current `templates/qa-report.md` and every current `qa.md` (steamcore, aspark-demo, Core) head the verification table `Spec ID | Steps performed | Expected | Observed | Result`; the parser requires an `AC` column. Reproduced: v0.7.0 on a steamcore `qa.md` renamed to `qa-report.md` → `template drift … QA table missing an 'AC' column`. Review tables match. The user ruled: plan revision so current-template QA tables are read without drift; stories unchanged, AC-5.4 is the acceptance evidence. |
| C13 | 2026-09-25 | (Found during /increment T5, early A1 check) Does a newly read QA row keep its meaning? | No. `_normalise_result` matches the word "pass" anywhere before looking at markers: 5 real rows read as `pass` — steamcore `highscore-system` AC-1.5 (`⚠️ not capturable — never claimed as passed`), Core `metrics-script-removal` AC-1.2/AC-4.1 and `project-kickoff` AC-5.1 (`⚠️ …`), Core `situational-lenses` AC-6.1 (`❌ not-verified-live … pass-worthy`). The user ruled: fix in v0.7.1 — explicit markers first (❌ → fail, ⚠️ → unknown, ✅ → pass), words only without a marker. This repo's legacy trail must stay byte-identical (AC-5.1). |
| C14 | 2026-09-25 | (Found in /demo-day, QA bug B1, Major) Does a QA row with a GFM escaped pipe (`\|`) inside a cell keep its columns? | No. `_split_row` splits on every `\|`, so the columns shift and a `✅ pass` row reads `unknown` (steamcore `analog-joystick-input` AC-1.5; 13 pass-marked rows in 7 Core/steamcore features). Pre-existing in v0.7.0, but it now hits every current trail. The user ruled: fix in v0.7.1, **for the QA verification table only** — an escaped `\|` is part of its cell (stored as a plain `|`), an unescaped `\|` still separates cells. Review/plan/other tables keep their current splitting (AC-5.1 byte-identity, scope) and go to BACKLOG G8. B2 stays deferred to G6 (user acceptance); B3–B6 → G8. |

## 8. Design Review

**N/A — with reason (confirmed by orchestrator 2026-09-24, no `/look-and-feel` run).** Headless CLI/MCP tool with no UI; the only user-facing change is a line in existing build output and README/`CLAUDE.md` text.

- **Overall impression:** N/A (no visual UI)
- **Heuristics findings:** N/A
- **Accessibility notes:** N/A (no visual UI)
- **Design risks & required changes:** None

---

## ✅ SPEC GATE

*All boxes checked → `/sprint-plan` may start. Any box open → back to `/story-time` or `/look-and-feel`.*

- [x] Problem, goal and success signal are concrete (no buzzwords, no "everyone")
- [x] Every story has testable Given/When/Then acceptance criteria
- [x] Stories are prioritized (MoSCoW) and at least one is a Must
- [x] Non-functional requirements are stated and measurable (or marked N/A with reason)
- [x] Clarify pass done: no ambiguity left unresolved or unparked *(second pass 2026-09-24; C9/C10 resolved by derivation)*
- [x] Open questions are resolved or explicitly accepted as risk *(Q1–Q5 resolved by user; A1 accepted as risk)*
- [x] Out-of-scope section is filled (something was consciously cut)
- [x] Constitution (`.spark/constitution.md`) respected — N/A, no constitution in this repo
- [x] Design review done for UI-facing features (or marked N/A with reason)
- [x] Line budget respected: Ist 204 / Soll ~250 (excluding HTML comments)
- [x] Status set to `approved` by the user *(2026-09-24, in conversation)*
