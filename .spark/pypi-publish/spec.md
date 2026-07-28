# Spec: pypi-publish

| | |
|---|---|
| **Phase** | Specify |
| **Owner** | Product Owner (`/story-time`), Designer (`/look-and-feel`) |
| **Status** | `approved` |
| **Date** | 2026-07-27 |

## 1. Problem & Goal

- **Problem:** aspark-graph is a mature, shipped product (v0.6.0: six languages,
  a hardened MCP server, a `SECURITY.md`) that **cannot be installed the way its
  primary consumer installs things.** Its README states "not yet published to a
  package index" and the only supported path is `git clone` → `uv sync`. For an
  MCP-server tool whose intended consumer is an agent that `uvx`-launches a
  server, clone-from-source is the single largest adoption blocker — and it is
  about to bite: aSPARK Core is starting to point users at this repo. The
  publish was *consciously* deferred in `distributable-install` (v0.3.0) — that
  cycle proved a clean-env install works but left "not yet published" true. The
  gap it deferred is now the thing standing between a finished product and its
  users.
- **Goal:** aspark-graph is installable in **one command from the public PyPI
  index** (`uvx aspark-graph …` / `pip install aspark-graph`), the README and
  `claude mcp add` instructions describe that working path (and only paths that
  work), and the deferral notes in `CLAUDE.md` and the README are resolved. The
  live publish is a human-executed release action — no agent in the SPARK loop
  holds or types a PyPI credential.
- **Success signal (observable):** on a clean machine with no checkout, `uvx
  aspark-graph query …` and `aspark-graph serve` both run end-to-end from the
  published package; `GET https://pypi.org/pypi/aspark-graph/json` returns the
  released version (not 404); the README's documented install command is that
  command, verbatim.
- **Why now:** the product is done enough that "install from a checkout" is the
  binding constraint on anyone but the author using it, and an external repo
  (Core) is about to send users here. `distributable-install` did the hard
  de-risking (dropped the native `cryptography` dep, proved clean-env install);
  what remains is the one irreversible outward-facing step it deliberately left
  for later. If we never build this, the tool stays effectively author-only.

## 2. Target Users

- **Primary: the agent or developer adopting the tool** who expects `uvx
  aspark-graph serve` / `pip install aspark-graph` and today must instead clone,
  `uv sync`, and wire `uv run --directory /path/...`. They are the acute pain.
- **Secondary: aSPARK Core's integration docs and the users they route here** —
  Core is adding a pointer to this repo; a published install is what that
  pointer should resolve to.
- **Tertiary: the maintainer (Andreas Lottes, maintainer of record)** who must
  execute the publish safely, once, with a rollback plan, and never ship a
  broken or mislabeled artifact to an index where a version number, once used,
  is burned forever.
- **Explicitly NOT a target this cycle:** anyone wanting a hands-off CI/trusted-
  publishing release pipeline (Out of Scope), or a TestPyPI/RC staging lane (the
  user chose a full public release now — A1).

## 3. Assumptions & Open Questions

| # | Assumption / Question | Resolution |
|---|---|---|
| A1 | **Settled by the user, not re-opened here:** (a) a full **public PyPI** package now, not a TestPyPI/RC slice; (b) Andreas Lottes is the **maintainer of record**; (c) the name `aspark-graph` is **confirmed available** (`GET /pypi/aspark-graph/json` → 404, unclaimed 2026-07-27). | Accepted as settled |
| A2 | The idea arrived partly as **solution/mechanism** ("build `dist/` fresh", "move the grammar-pin rationale into the README"). The spec records the *outcome* (a working published install; an honest, complete install doc) and leaves the exact build/upload commands to `/sprint-plan` and `/go-live`. Original phrasing kept here. | Accepted as assumption |
| A3 | **No agent holds a PyPI credential.** Uploading to PyPI is an outward-facing action requiring a token or OIDC config; per this project's own operating norms (outward-facing actions are human-executed with authorization relayed by the caller — the exact pattern used for `git push` and the `security-posture` AC-2.8 GitHub-setting confirmation), the actual publish is a **user-owned release-phase task**, provable only at `/go-live`, not by a Review gate. | Accepted as binding guardrail (US-1, NFR-5) |
| A4 | aspark-graph's **own** distribution is a **pure-Python wheel** (`py3-none-any`; no compiled extension lives in `src/aspark_graph`). Its tree-sitter grammar dependencies ship their own wheels, resolved at install. So the published artifact is platform-independent and its build environment (OS/Python) does not change its bytes — build-reproducibility risk is low. | Accepted as fact |
| A5 | **Install honesty is a hard rule** (inherited from `distributable-install` A5/US-3): the README must document only paths that work at the moment it is read. No `uvx`/`pip install aspark-graph`/PyPI command may appear until the package is genuinely live on PyPI. | Accepted as binding guardrail (NFR-3) |
| A6 | PyPI requires 2FA on the maintainer's account and an API token (or trusted-publisher config) to upload; a username/password upload is no longer accepted. This is an operational precondition for the human-executed upload (A3), not something this spec builds — the maintainer is assumed to already have, or will set up, 2FA before `/go-live`. | Accepted as assumption |
| Q1 | **Publish mechanism.** Manual `uv build` + upload from the maintainer's machine (API token), or GitHub Actions **trusted publishing** (OIDC, no stored secret)? Trusted publishing means creating a CI apparatus this repo **does not have today** (`.github/` is absent; every release smoke check to date is hand-run). | **RESOLVED 2026-07-27 — settled by user:** manual `uv build` + upload from the maintainer's machine, matching the repo's zero-CI, all-manual ethos. No GitHub Actions/OIDC trusted publishing this cycle — confirmed as a genuine decision, not a default holding by omission. Stays Out of Scope (§6). |
| Q2 | **Version to publish.** Publish the current `0.6.0` code as-is, or does the act of publishing (which changes README + `pyproject.toml` + `CLAUDE.md`, all user-facing) warrant a fresh bump? The backlog's "publish 0.5.x" is **stale** (0.6.0 is current). | **RESOLVED 2026-07-27 — settled by user:** a **fresh version bump accompanies the publish** (user-facing doc/metadata changes ship as their own version, per every prior feature's precedent). The exact number is decided at `/go-live` per this project's usual convention (see `go-rust-support`/`security-posture` release-notes for the semver-minor-vs-patch reasoning pattern to reuse). |
| Q3 | **Fate of the from-source install path.** Remove it in favor of the published path, or retain it as a documented contributor/development install? | **RESOLVED 2026-07-27 — settled by user:** **kept**, relocated to the existing `## Development` section (README already has one) rather than removed. |
| Q4 | **Name-conflict depth.** The 404 confirms the exact string is unclaimed, but does not rule out typosquat-adjacent names, a similarly-named package, or a reservation. | **Accepted as risk, not solved this cycle.** Named here so the 404 is not silently treated as the whole story. |

## 4. User Stories

### US-1 (Must): One-command install from the public PyPI index

> As an agent or developer adopting aspark-graph, I want to install it with a
> single `uvx`/`pip` command from PyPI, so that I never have to clone the repo
> and run a sync to use the tool.

<!-- The core value. State the outcome (installable + both entry points run from
     the published artifact); the live upload itself is human-executed (A3) and
     provable only at /go-live. -->

**Acceptance criteria:**

- [ ] AC-1.1: Given a clean machine with **no checkout** and only Python ≥ 3.11 + uv/pip, when I run the documented one-command install (`uvx aspark-graph …` / `pip install aspark-graph`), then it resolves and installs from **public PyPI** and the `aspark-graph` console command is on PATH.
- [ ] AC-1.2: Given that published install, when I run `aspark-graph build .` on a repo with a `.spark/` trail and then at least one query, then both run **end-to-end and return the expected result** — no import, package-data, or entry-point error.
- [ ] AC-1.3: Given that published install, when I run `aspark-graph serve`, then the MCP server **starts and registers all nine tools** from the *packaged* install (not an editable checkout).
- [ ] AC-1.4: Given the published wheel's resolved dependency tree, when I inspect it, then **`cryptography` and any dependency serving only the unused MCP auth path are absent** (the `distributable-install` guarantee holds from the published artifact), and no dependency requires compiling from sdist.
- [ ] AC-1.5: Given the published package metadata, when I inspect it, then the **name, version, entry points, description, license and required package data are correct and complete**, and `GET https://pypi.org/pypi/aspark-graph/json` returns the released version rather than 404.
- [ ] AC-1.6: Given the SPARK delivery loop, when the publish is performed, then it is executed by the **human maintainer** with authorization recorded in the release trail — **no agent held or typed a PyPI credential** (A3, NFR-5).
- [ ] AC-1.7 *(closes the "published ≠ published-and-working" gap)*: Given **both** the wheel and the sdist built locally, **before any upload to PyPI**, when each is installed independently into a fresh isolated environment, then `aspark-graph build`/`query` and `aspark-graph serve` both smoke-test successfully from **each** artifact — matching the `distributable-install` clean-env-install precedent. This local proof happens *before* the irreversible upload, not only after (AC-1.1-1.3 verify the live index; this verifies the artifact that will be uploaded, first).
- [ ] AC-1.8 *(the partial-publish state, distinct from AC-4.1's rollback of a completed-but-bad release)*: Given the manual upload sequence (build wheel + sdist → upload both to PyPI → git tag/push → GitHub Release), when any step fails partway (e.g. the wheel uploads but the sdist does not, or the PyPI upload succeeds but the following git tag/push/GitHub-Release step does not run), then the release process **does not silently continue as if it succeeded**: the actual per-artifact state (what is/isn't live on PyPI, what is/isn't tagged/pushed) is independently re-verified from PyPI/GitHub directly — never assumed from the last known intent — before any further outward-facing action, reusing this project's existing "never resume a possibly-interrupted release from trust alone" pattern (`security-posture` release-notes §7). If PyPI is left with an incomplete-but-live version (e.g. wheel-only, no sdist), the missing artifact is uploaded to **the same version** (PyPI allows adding a missing file type to an existing release) rather than treated as broken; a genuinely broken/wrong upload instead follows AC-4.1's yank path.

### US-2 (Must): Install docs describe the published path — precisely, and only if it works

> As a new user following the README, I want the install instructions to
> describe the working published path and nothing fictional, so that I reach a
> working install with no dead end.

<!-- Correction from the original grounding: only tests/test_readme.py's Install-
     section assertions need inverting. tests/test_link_conventions.py (read in
     full) tests the "declared"/"inferred" implements-link-convention prose
     (files:/Refs:/declared/inferred), a different README section entirely —
     it is UNAFFECTED by this feature and needs no change. Recorded as C8 below
     so /sprint-plan does not go looking for install-path assertions in it. -->

**Acceptance criteria:**

- [ ] AC-2.1: Given the package is live on PyPI, when I read the README `## Install` section, then it leads with the **one-command published install** (`uvx aspark-graph …` / `pip install aspark-graph`) and the "not yet published to a package index" sentence is **gone**.
- [ ] AC-2.2: Given the README's "add to Claude Code as an MCP server" instructions, when I read them, then the `claude mcp add` command uses the **published entry point** (e.g. `uvx aspark-graph serve`), not `uv run --directory /path/to/aspark-graph`.
- [ ] AC-2.3: Given `tests/test_readme.py` (the **only** doc-introspection test covering the `## Install` section — its three functions `test_ac_6_1_no_fictional_package_index_command`, `test_ac_6_1_from_source_path_is_documented`, `test_ac_6_3_mcp_add_uses_working_entry_point`), when the suite runs after this change, then all three are **rewritten to assert the published state**: presence of `uvx aspark-graph`/`pip install aspark-graph`, absence of "not yet published", and the `claude mcp add` line using `uvx` (not `uv run --directory`) — and are **green**. `tests/test_link_conventions.py` is **untouched** (out of this story's scope — see the note above, corrected against the original grounding). The rewritten tests ship in the **same commit** as the doc change, never after.
- [ ] AC-2.4: Given the honesty rule (A5), when the README is inspected at any point in this cycle, then **no published-path command appears before the package is actually live** on PyPI — if the live upload slips, the README does not claim it.
- [ ] AC-2.5: Given Q3's resolution (kept, relocated), when I read the README, then the from-source install steps (`git clone` → `uv sync` → `uv run aspark-graph build .`) appear under the existing **`## Development`** section as the documented contributor/dev path, not under `## Install`.
- [ ] AC-2.6 *(closes a rendering gap the original draft missed)*: Given the README is also rendered as the **PyPI project page** (`readme = "README.md"` in `pyproject.toml`, uploaded as-is), when I view that page on pypi.org, then it **does not silently show broken images or dead links**: the logo `<picture>` block's relative image paths (`docs/aSPARK-graph-logo-*.png`) and any repo-relative links (`SECURITY.md`, `docs/aspark-integration.md`, etc.) either resolve via **absolute GitHub URLs** or are acceptably omitted from what's shown on PyPI — checked as part of the pre-upload local review (extending AC-1.7's spirit to the rendered page, verified via a rendered-markdown preview or a fresh look at the live page post-publish).

### US-3 (Should): The determinism promise is public — with its stated boundary

> As a user installing a pinned, published package, I want the README to explain
> why the grammars are pinned and what the byte-identical-rebuild guarantee does
> and does **not** cover, so that I understand what I am relying on and am not
> surprised when a grammar bump changes output.

<!-- Publishing turns a contributor-facing code comment (the grammar-pin
     rationale in pyproject.toml) into a promise users install against. Stating
     the guarantee WITHOUT its boundary would create an implied promise the
     maintainer can't keep: a grammar version bump changes extracted node types
     by definition, breaking byte-identity across the bump. The boundary is the
     deliverable. -->

**Acceptance criteria:**

- [ ] AC-3.1: Given the README, when I read the install/guarantees section, then it states **why** parse-affecting deps (tree-sitter core + the six grammars) are pinned `==` and that `uv.lock` is part of the determinism contract, in user-facing language.
- [ ] AC-3.2: Given the same section, when I read it, then it states the **boundary explicitly**: byte-identical rebuild holds for an unchanged repo **on a fixed grammar set**, and a grammar version bump can change extracted nodes and is therefore a **deliberate, changelog-documented, version-bumped event** — not a silent change.
- [ ] AC-3.3: Given a QA/reviewer reading AC-3.1/3.2 against the code, when they check, then the stated policy is **falsifiable and true** (the pins named in the README match `pyproject.toml`; no over-claim of cross-version determinism).

### US-4 (Should): A PyPI-specific rollback/yank path is written before the publish

> As the maintainer, I want a documented rollback path for the published
> package, distinct from the git-tag rollback this project already documents, so
> that a broken published version has a defined recovery — knowing a PyPI version
> number, once used, can be yanked but never reused.

<!-- Every release-notes.md here already carries a git-tag Rollback Path. PyPI
     adds an irreversibility the git path doesn't cover (a burned version number).
     This story forces the PyPI-specific path to exist BEFORE the irreversible
     action, matching the "rollback written before any outward-facing action"
     KEEP-gate precedent. -->

**Acceptance criteria:**

- [ ] AC-4.1: Given the release trail for this feature, before any upload, then it documents a **PyPI-specific rollback**: how to `yank` a bad release, that the version number cannot be reused (the next fix must be a **new** version), and that yanking does not delete — distinct from the existing `git tag -d` / `git revert` path.
- [ ] AC-4.2: Given a hypothetical broken publish, when the rollback path is followed as written, then it references **only actions the maintainer can actually take** on PyPI (yank via the project page / API), with no step that assumes an agent-held credential.
- [ ] AC-4.3 *(cross-reference, no new content)*: AC-4.1/4.2 cover a **completed but wrong** release (yank). A release that is **incomplete** (partway through the upload sequence) is a distinct case, covered by AC-1.8 — the two paths are not to be conflated in the release-notes rollback section.

### US-5 (Should): The deferral notes are resolved

> As a contributor reading `CLAUDE.md`/README, I want the "PyPI publish deferred /
> install-from-source only" notes updated to reflect reality, so that the docs do
> not contradict the shipped state.

**Acceptance criteria:**

- [ ] AC-5.1: Given the publish is live, when I read `CLAUDE.md`'s "Out of scope" section, then the "live PyPI publish (deferred; ... keep the README free of `uvx`/PyPI claims until it's actually published)" note is **resolved** — either removed or rewritten to state the package is now published.
- [ ] AC-5.2: Given the README's own "Out of scope"/install prose, when I read it, then no remaining sentence claims the package is unpublished or install-from-source-only.

### US-6 (Won't, this version): Everything on the Out-of-Scope list

> Recorded so the "no" is documented. See section 6 — trusted-publishing CI,
> TestPyPI/RC staging, automated release matrices, and more.

## 5. Non-Functional Requirements

| # | Category | Requirement (measurable) | How it's verified |
|---|---|---|---|
| NFR-1 | Determinism (non-negotiable, inherited) | The **published** wheel builds the graph byte-for-byte identically on an unchanged repo; parse-affecting deps stay pinned `==`; the double-build test stays green. The wheel is `py3-none-any` (A4). | Existing double-build test + clean-env install from the published index (/peer-review) |
| NFR-2 | Supply chain / provenance | The published artifact's contents correspond to the **tagged release commit**; wheel metadata version == `pyproject.toml` == git tag == the version on `pypi.org`; the resolved runtime dep tree contains no package serving only unused functionality (`cryptography` absent). Both wheel and sdist are built and verified locally before upload (AC-1.7). | /peer-review of metadata + lock; clean-env `pip install` provenance check |
| NFR-3 | Install honesty (hard rule, inherited) | No `uvx`/`pip install aspark-graph`/PyPI command appears in the README until the package is genuinely live; the documented command matches the actual published state at read time. | /peer-review of README against `pypi.org` state |
| NFR-4 | Reliability / no regression | The full existing suite is green **including the rewritten `tests/test_readme.py`** (AC-2.3); CLI↔MCP parity holds from the **published** install; no query name, argument, output shape, or exit-code behaviour changes (this is packaging + docs, not code capability). | `uv run pytest` + clean-env parity check |
| NFR-5 | Security & credentials | **No agent holds or types a PyPI credential.** The upload is a human-executed outward-facing action, recorded in the release trail with authorizer + reason (the `security-posture` AC-2.8 precedent). Maintainer 2FA/API-token precondition assumed (A6). | /peer-review + release-notes authorization record |
| NFR-6 | Accessibility | N/A — no graphical/human-visual interface; surfaces are a JSON CLI and an agent-facing MCP API (unchanged). | N/A |
| NFR-7 | Observability / clean errors (inherited) | Domain errors continue to surface as one-line messages / structured dicts, never tracebacks, from the published install. | /peer-review + clean-env smoke run |

## 6. Out of Scope

Consciously cut this cycle:

- **GitHub Actions trusted publishing / any CI release pipeline (settled — Q1).**
  This repo has **zero CI** today (`.github/` is absent; every release smoke
  check is hand-run). Standing up an OIDC trusted-publishing workflow is a new
  apparatus and a separate feature. The user confirmed manual, human-run upload
  for this cycle; CI is deferred, not defaulted-into.
- **TestPyPI / release-candidate staging.** The user chose a full public release
  now (A1). A staging lane is not built.
- **An automated multi-OS install matrix.** `distributable-install` already
  deferred this (its US-5); a one-time clean-env install from the published index
  remains the accepted proof.
- **Artifact signing / attestation (Sigstore, etc.) beyond what PyPI provides by
  default**, and publishing to any index other than PyPI (conda, etc.).
- **Typosquat / adjacent-name defense beyond the 404 check (Q4)** — named as an
  accepted risk, not solved.
- **Any code capability change** — no new query, language, node type, or grammar
  bump rides along. The grammars stay exactly pinned; this cycle only makes their
  pinning a *documented public promise*, it does not change them.
- **Everything already Out of Scope through v0.6.0** — LLM/NL layer, call-graph
  precision, visualization, exports, HTTP/team mode, authenticated/remote MCP
  transport. Unchanged.

## 7. Clarifications

| # | Date | Question | Resolution |
|---|---|---|---|
| C1 | 2026-07-27 | Does the spec prescribe *how* to build/upload (twine vs uv publish vs CI)? | No — that is mechanism (A2), left to `/sprint-plan`/`/go-live`. The spec fixes the outcome (a working published install; honest, complete docs) and the guardrail that no agent holds the credential (A3). |
| C2 | 2026-07-27 | What is the Review-provable signal vs. the release-only signal? | Review-provable: the doc inversion + tests green + determinism-boundary prose + rollback path written (US-2/US-3/US-4). Release-only (`/go-live`, human-executed): the live upload and the `pypi.org` 404→version flip (US-1, AC-1.5/1.6). |
| C3 | 2026-07-27 | Publish mechanism (Q1), version (Q2), from-source fate (Q3) — three PO defaults proposed in the draft. | **Superseded by C5–C7** — the user confirmed all three explicitly, not by omission. See below. |
| C4 | 2026-07-27 | Is the 404 the whole name-safety story? | No (Q4) — it confirms the exact string is unclaimed only. Typosquat/adjacent-name risk is accepted, not solved, and recorded in Out of Scope. |
| C5 | 2026-07-27 | Publish mechanism: manual upload vs. GitHub Actions/OIDC trusted publishing? | **Settled by user:** manual `uv build` + upload from the maintainer's machine. No trusted-publishing CI this cycle — an explicit decision, confirmed rather than left as an unchallenged default. Folded into Q1/§6. |
| C6 | 2026-07-27 | Version to publish: `0.6.0` as-is, or a fresh bump? | **Settled by user:** a fresh version bump accompanies the publish; exact number decided at `/go-live` per this project's usual convention. Folded into Q2. |
| C7 | 2026-07-27 | From-source install path: removed or retained? | **Settled by user:** retained, relocated to the existing `## Development` section (not removed). Folded into Q3/AC-2.5. |
| C8 | 2026-07-27 | Does `tests/test_link_conventions.py` also need inverting, as the original grounding note implied ("`tests/test_readme.py` and `tests/test_link_conventions.py` doc-introspection-test this section")? | **No — that premise was incorrect.** On reading the file in full, `test_link_conventions.py` tests the *"declared"/"inferred" implements-link-convention* prose (`files:`, `Refs:` trailers), a wholly different README section unrelated to the Install path. Only `test_readme.py`'s three Install-section tests need inversion (AC-2.3). Corrected in the story so `/sprint-plan` does not go hunting for install assertions in the wrong file. |
| C9 | 2026-07-27 | What happens if the manual upload sequence fails partway (wheel uploads, sdist doesn't; or PyPI succeeds but the git tag/push/GitHub Release doesn't follow)? | **Resolved directly in the spec (AC-1.8):** no silent continuation — actual per-artifact state is independently re-verified from PyPI/GitHub before any further step, reusing this project's existing "never resume a possibly-interrupted release from trust alone" pattern. A missing file-type on an otherwise-live version is added to the same version; a genuinely broken/wrong release instead follows the yank path (AC-4.1), kept distinct (AC-4.3). |
| C10 | 2026-07-27 | Is there an explicit step proving the built artifact actually works *before* the irreversible upload — so "published something" and "published something that works" aren't conflated? | **Resolved directly in the spec (AC-1.7):** wheel and sdist are each installed into a fresh isolated environment and smoke-tested (build + query + serve) locally, before any upload — mirroring the `distributable-install` clean-env-install precedent. |
| C11 | 2026-07-27 | Does the README's relative image/link paths (the logo `<picture>` block, links to `SECURITY.md`/`docs/*`) render correctly once the same file becomes the **PyPI project page** long description? | **New gap, resolved directly in the spec (AC-2.6):** not previously addressed. Relative paths that work on GitHub do not generally resolve on PyPI's rendered page. Requirement added: absolute GitHub URLs for anything shown on the PyPI page, or acceptable omission — checked before/at publish, not assumed to "just work" because it works on GitHub. |

## 8. Design Review

**N/A — with reason.** Like every prior aspark-graph cycle, this adds no
graphical or human-visual interface. It changes packaging, distribution, and
README/CLAUDE.md prose. The one genuinely visual artifact this cycle touches —
the README as rendered on the **PyPI project page** — is captured as a
falsifiable acceptance criterion (AC-2.6) rather than requiring a UI heuristics
review; there is no new layout, interaction, or accessibility surface beyond
that single rendering check.

- **Overall impression:** N/A (no interactive UI; one static rendered-page check, see AC-2.6)
- **Heuristics findings:** N/A — install-doc honesty covered via ACs (AC-2.4, NFR-3)
- **Accessibility notes:** N/A (no visual UI)
- **Design risks & required changes:** None for a packaging/docs change

---

## ✅ SPEC GATE

*All boxes checked → `/sprint-plan` may start. Any box open → back to `/story-time` or `/look-and-feel`.*

- [x] Problem, goal and success signal are concrete (no buzzwords, no "everyone")
- [x] Every story has testable Given/When/Then acceptance criteria
- [x] Stories are prioritized (MoSCoW) and at least one is a Must
- [x] Non-functional requirements are stated and measurable (or marked N/A with reason)
- [x] Clarify pass done: full taxonomy sweep complete (§3 Q1–Q4 settled/accepted; C8–C11 new findings folded into ACs directly — see §7)
- [x] Open questions are resolved or explicitly accepted as risk *(Q1–Q3 settled by user 2026-07-27; Q4 accepted as risk)*
- [x] Out-of-scope section is filled (something was consciously cut)
- [x] Constitution (`.spark/constitution.md`) respected — N/A, no constitution exists
- [x] Design review done for UI-facing features (marked N/A with reason; AC-2.6 covers the one rendered-page surface)
- [x] Status set to `approved` by the user — 2026-07-27, explicit approval at the `/spark` spec gate
