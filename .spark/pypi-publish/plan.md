# Plan: pypi-publish

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Engineering Manager (`/sprint-plan`) |
| **Input** | `.spark/pypi-publish/spec.md` (`approved`, 2026-07-27) |
| **Status** | `approved` |
| **Date** | 2026-07-27 |

## 1. Architecture Decision

- **Context:** This is a **packaging + docs** cycle — no `src/` code, no grammar,
  no query changes (spec §6). The tool is already a pure-Python `py3-none-any`
  wheel proven installable in a clean env (`distributable-install`, v0.3.0). What
  remains is the one irreversible outward step that cycle deferred: build the
  distribution, prove it works *before* upload, upload to public PyPI, and make
  the README honest about the now-working path — without ever letting a
  published-path claim enter public git history before the package is live
  (A5/NFR-3), and without any agent holding a PyPI credential (A3/NFR-5). The repo
  has **zero CI** and every release check to date is hand-run; the user settled on
  manual upload, no trusted-publishing (Q1/C5).

- **Decision:** Publish with **`uv publish`** (upload) over artifacts from
  **`uv build`** (wheel + sdist into `dist/`) — the toolchain already used
  everywhere in this repo (`uv sync`/`uv build`/`uv run`), so **no new
  dependency**. The credential is a PyPI **API token** the maintainer holds in
  their own shell as `UV_PUBLISH_TOKEN`, entered in an isolated **user-owned**
  task (T6) — never typed, stored, or read by an agent. The go-live sequence is
  strictly ordered so the **live upload precedes the published-README commit**:
  build → dual fresh-venv smoke of *both* artifacts (AC-1.7) → user sets token →
  `uv publish` → re-verify from `pypi.org/pypi/aspark-graph/json` → *only then*
  create/push the release commit carrying the published-state README + inverted
  tests → tag/push → `gh release`. Every step that follows an upload
  independently re-verifies actual per-artifact state from PyPI/GitHub before the
  next outward action (AC-1.8), reusing `security-posture` §7's "never resume from
  trust alone" pattern. All README prose (US-2/US-3/US-5) lands in **one** edit;
  the three `test_readme.py` functions are inverted in the same logical change.

- **Alternatives considered:**
  | Alternative | Why rejected |
  |---|---|
  | **`twine upload`** for the upload step | Adds a dev dependency (every dependency is a liability) to do what `uv publish` — already in the toolchain — does natively for wheel+sdist with `UV_PUBLISH_TOKEN`. No benefit to justify the new package. |
  | **GitHub Actions / OIDC trusted publishing** | Explicitly settled Out of Scope (Q1/C5): stands up CI apparatus this repo has never had. A separate feature. |
  | **Commit the published-README first, upload second** | Puts a commit claiming "pip install aspark-graph" into **public** git history before it is true — violates A5/NFR-3 and the `distributable-install` A5 honesty rule. Inverted: upload first, commit second. |
  | **Version-parity as an automated test** | The `pypi.org` leg can't be asserted pre-release and the wheel-metadata leg is a build artifact, not a source property. Handled as a mechanical go-live pre-flight item (T7/T8), matching `security-posture`'s "Lockfile self-version check" precedent. |
  | **TestPyPI/RC staging first** | Out of Scope (A1) — user chose a full public release now. |

- **Consequences:**
  - *Easier:* the artifact is de-risked locally before the irreversible upload
    (T1); the honesty rule is satisfied by **ordering**, not by a fragile split of
    the README into "safe" and "unsafe" halves — the whole README change is
    prepared in the working tree during `/increment` (reviewable) and only
    *committed/pushed* at go-live, after the package is live.
  - *Harder / accepted cost:* this feature is **back-loaded** — most Must ACs
    (AC-1.1–1.3, 1.5, 1.6, 1.8) are provable **only at `/go-live`**, human-run,
    not at a Review gate. `/peer-review` proves doc content, test-inversion
    correctness, the local dual-venv artifact smoke, and rollback completeness;
    the live upload and the 404→version flip are release-only (C2). The plan marks
    the boundary at every task. A burned version number is permanent — mitigated
    by T1/T7's pre-upload smoke and T5's yank path.

## 2. Affected Components

**New dependencies: none.** `uv publish`/`uv build` are the existing toolchain;
`mcp>=1.12,<1.20` and the pinned grammars are untouched (§6 — no code/grammar
change rides along).

- **`README.md`** — Install section rewritten to lead with the published command;
  from-source relocated to `## Development`; determinism-boundary prose added;
  logo `<picture>` srcset/src and internal links (`SECURITY.md`,
  `docs/aspark-integration.md`) → **absolute** `raw.githubusercontent.com` /
  `github.com/blob/main` URLs so the file renders as the PyPI project page
  (`readme = "README.md"`).
- **`tests/test_readme.py`** — the three Install-section functions inverted to
  assert the published state (AC-2.3).
- **`CLAUDE.md`** — the "live PyPI publish (deferred…)" Out-of-scope note resolved.
- **`pyproject.toml` + `uv.lock`** — version bump (go-live; exact number per
  convention, likely minor — new distribution capability, following
  `go-rust-support`/`security-posture` reasoning; decided by `/go-live` per C6).
- **`.spark/pypi-publish/release-notes.md`** — carries the PyPI yank rollback path
  (US-4), drafted before any upload.

**Explicitly untouched:** `tests/test_link_conventions.py` (C8 — it tests the
`declared`/`inferred` link-convention prose, a different README section, not the
Install path); all `src/`; grammar pins.

**Blast radius — graph-verified** (caller ran `aspark-graph query impact
README.md CLAUDE.md pyproject.toml tests/test_readme.py --repo .`, graph fresh).
`README.md`, `CLAUDE.md` and `pyproject.toml` return in `unknown_files` (not code
nodes) — as `security-posture` §2 also found. `tests/test_readme.py` is
`in_graph: true` with **exactly four** code entities: the shared `_install_section`
helper plus the three Install-section test functions T3 names
(`test_ac_6_1_no_fictional_package_index_command`,
`test_ac_6_1_from_source_path_is_documented`,
`test_ac_6_3_mcp_add_uses_working_entry_point`) — independent confirmation that
**no fourth Install-section test was missed** and that T3's scope is complete.
Since this cycle changes **no** `src/` code, the structural code-graph radius is
empty by construction; the risk here is release-mechanical, not code-structural.
The query also surfaced `story:close-the-loop:US-6`/AC-6.1–6.3 linked to
`test_readme.py` at `inferred` confidence — a historical git-inference artifact
(a past commit referencing `close-the-loop`'s own numbering), the same category
as the `close-the-loop:T9` collision in `security-posture` §6. Not this feature's
scope; noted so it isn't re-derived as a finding.

## 3. Task Breakdown

**Walking skeleton = T1:** build the wheel + sdist from the working tree and prove
**both** install-and-run in fresh isolated venvs *before* any doc churn or upload.
That kills the only pre-release integration risk (does the artifact that will be
uploaded actually work?) first — the pure-Python analogue of `security-posture`'s
T13 clean-env proof. **T1–T5 are `/increment` (Review-provable).** **T6–T10 are
`/go-live` (human-executed, release-only)** — the boundary is marked per task.

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | **Walking skeleton: dual fresh-venv artifact proof (pre-upload).** `uv build` → wheel + sdist in `dist/`; install **each** independently into a **separate** fresh `uv venv`; from each, run `aspark-graph build .` + one query + `serve` (registers 9 tools). Reuses `security-posture` T13's technique. | US-1 | AC-1.4, AC-1.7, NFR-1, NFR-2 | – | `done` | From the **wheel-only** venv and, separately, the **sdist-only** venv: the `aspark-graph` console script is on PATH; `build` + a query return expected results; `serve` registers exactly 9 tools; `cryptography`/`joserfc` are absent from each resolved tree and nothing built from an sdist-that-needs-compiling; no checkout on PATH — all verified before any upload |
| T2 | **README: all prose in one edit.** Install leads with `uvx aspark-graph …` / `pip install aspark-graph` and drops "not yet published" (AC-2.1); `claude mcp add` uses `uvx aspark-graph serve` (AC-2.2); from-source (`git clone`→`uv sync`→`uv run aspark-graph build`) relocated under `## Development` (AC-2.5); determinism-boundary prose in Design guarantees — why grammars are pinned `==` + `uv.lock` is part of the contract (AC-3.1), and the boundary: byte-identity holds on a **fixed** grammar set; a grammar bump is a deliberate, changelog-documented, version-bumped event (AC-3.2), pins named matching `pyproject.toml` (AC-3.3); no remaining "unpublished / from-source-only" sentence (AC-5.2); logo `<picture>` srcset/src + `SECURITY.md`/`docs/*` links switched to absolute GitHub URLs for the PyPI page (AC-2.6, static leg). | US-2, US-3, US-5 | AC-2.1, AC-2.2, AC-2.5, AC-2.6, AC-3.1, AC-3.2, AC-3.3, AC-5.2, NFR-3 | – | `done` | Install section leads with both published commands and contains no "not yet published"/from-source steps; `## Development` holds the from-source path; `claude mcp add` line uses `uvx`, not `uv run --directory`; Design-guarantees section states the grammar-pin rationale and the byte-identity **boundary** with pins matching `pyproject.toml`; the `<picture>` and internal links use absolute `raw.githubusercontent.com`/`github.com/blob/main` URLs — files: README.md |
| T3 | **Invert the three `test_readme.py` Install tests (co-commit with T2).** The shared `_install_section` helper stays; its three callers are rewritten. `test_ac_6_1_no_fictional_package_index_command` (now assert `uvx aspark-graph` **and** `pip install aspark-graph` **present** in Install), `test_ac_6_1_from_source_path_is_documented` (assert "not yet published" **absent** from the README; from-source now asserted under the **Development** section, not Install), `test_ac_6_3_mcp_add_uses_working_entry_point` (assert `uvx` in the `mcp add` line, `uv run --directory` absent). `tests/test_link_conventions.py` untouched (C8). | US-2 | AC-2.3, NFR-4 | T2 | `done` | The three named functions are rewritten to the published assertions above and are **green** against T2's README; the `_install_section` helper is unchanged (three callers rewritten, no fourth Install-section test exists — graph-confirmed, §2); `uv run pytest` passes with zero other regressions; `test_link_conventions.py` unchanged and green — files: tests/test_readme.py |
| T4 | **Resolve the CLAUDE.md deferral note.** Rewrite the "live PyPI publish (deferred; … keep the README free of `uvx`/PyPI claims until it's actually published)" Out-of-scope note to state the package is now published (or remove it). | US-5 | AC-5.1 | – | `done` | `CLAUDE.md`'s Out-of-scope section no longer defers the PyPI publish and contains no sentence claiming the package is install-from-source-only — files: CLAUDE.md |
| T5 | **Draft the PyPI yank rollback path (before any upload).** In the feature's release-notes, write a **PyPI-specific** rollback distinct from the existing `git tag -d`/`git revert` path: how to `yank` a bad release via the project page/API, that a version number is **burned** (the next fix must be a new version), that yank hides but does not delete (AC-4.1); reference **only** maintainer-executable actions, no agent-held credential (AC-4.2); and keep the **completed-but-wrong** (yank) case explicitly distinct from the **incomplete/partway** case, which is AC-1.8's re-verify path (AC-4.3). | US-4 | AC-4.1, AC-4.2, AC-4.3 | – | `done` | A "PyPI rollback" section exists in the feature trail, is reviewable before go-live, names yank-via-project-page/API + version-burn + yank≠delete, references only maintainer actions, and cross-references AC-1.8 for the incomplete-upload case without conflating the two — files: .spark/pypi-publish/release-notes.md |
| T6 | **(User-owned — not code.) Maintainer holds the PyPI credential.** The maintainer ensures 2FA is enabled (A6) and sets the PyPI **API token** as `UV_PUBLISH_TOKEN` in their **own** shell for the upload. No agent reads, stores, echoes, or types the token. | US-1 | AC-1.6, NFR-5 | – | `todo` | The maintainer confirms in this plan's status that 2FA is on and the token is set in their own environment, before T8 runs; no token value appears in any file, log, commit, or agent message |
| T7 | **(Go-live.) Version bump + metadata-parity pre-flight, then re-smoke the bumped artifacts.** Bump `pyproject.toml`, `uv lock`, `uv build` the wheel+sdist at the new version, and re-run T1's dual fresh-venv smoke on the bumped artifacts. Mechanically check version parity: `pyproject.toml` == wheel metadata == intended git tag (NFR-2). | US-1 | AC-1.5, AC-1.7, NFR-1, NFR-2 | T1, T2, T3, T4, T5 | `todo` | The bumped wheel + sdist each install and smoke-test (build/query/serve) in a fresh venv; wheel metadata (name, version, entry point `aspark-graph`, description, license, README long-description, package data) is correct and complete; `pyproject.toml` version == wheel metadata version == the tag to be pushed — files: pyproject.toml, uv.lock |
| T8 | **(Go-live — OUTWARD-FACING, human-authorized.) `uv publish` + re-verify from PyPI.** With the maintainer's `UV_PUBLISH_TOKEN` set (T6), `uv publish` uploads the wheel **and** sdist. Then independently re-verify from `GET https://pypi.org/pypi/aspark-graph/json`: the new version is live (not 404) and **both** file types are present. Apply AC-1.8: never assume success from the last intent — if only one file type landed, upload the missing one to the **same** version; a genuinely broken upload follows T5's yank path. Record authorizer + reason in the release trail (NFR-5). | US-1 | AC-1.5, AC-1.6, AC-1.8, NFR-2 | T6, T7 | `todo` | `pypi.org/pypi/aspark-graph/json` returns the released version with both wheel and sdist present, independently re-verified after upload; the release trail records the human authorizer and that no agent held the credential; any partial-upload state was re-verified from PyPI and reconciled to the same version (or yanked), never assumed |
| T9 | **(Go-live — OUTWARD-FACING.) Honesty-ordered release commit, tag, push, GitHub Release.** **Only after T8 confirms the package is live**, create the release commit bundling the version bump + published-state README + inverted tests + CLAUDE.md + spark trail; annotated tag `vX.Y.Z`; `git push origin main`; `git push origin vX.Y.Z`; `gh release create`. Re-verify actual remote/tag/release state between each outward step (AC-1.8). This is the first moment a published-path claim enters public history — and by then it is true. | US-2, US-1 | AC-2.4, AC-1.8, NFR-3 | T8 | `todo` | The commit carrying `uvx`/`pip install` README claims is created and pushed strictly **after** the live-on-PyPI confirmation; `main`, the `vX.Y.Z` tag, and the GitHub Release are each independently verified live; no published-path commit exists in pushed history dated before the upload |
| T10 | **(Go-live.) Post-publish clean-machine verification.** On a clean machine/fresh venv with no checkout: `uvx aspark-graph …` / `pip install aspark-graph` from **live** PyPI; run `build` + a query + `serve` (9 tools); confirm `cryptography` absent; confirm the `pypi.org` JSON returns the version; view the **pypi.org project page** to confirm the README renders (logo + links resolve — AC-2.6 live leg). | US-1, US-2 | AC-1.1, AC-1.2, AC-1.3, AC-1.4, AC-1.5, AC-2.6, NFR-1, NFR-3, NFR-7 | T8, T9 | `todo` | From a no-checkout clean env the documented one-command install resolves from public PyPI, the console script is on PATH, `build`+query+`serve` (9 tools) run end-to-end with no import/entry-point error and `cryptography` absent; the pypi.org page shows the rendered README with the logo and links resolving; domain errors still surface as clean one-line/dict messages, never tracebacks |

## 4. Test Strategy

Headless tool: `/demo-day` is structurally N/A (CLAUDE.md); the QA-equivalent runs
in `/peer-review` and at `/go-live`'s pre-flight. NFR-6 (accessibility) is N/A —
the one rendered surface (the PyPI page) is covered by AC-2.6, not a UI review.

- **Doc-introspection (automated, T3):** the three inverted `test_readme.py`
  functions — the *only* automated net on the Install-doc honesty. They assert
  presence of the published commands, absence of "not yet published", from-source
  under Development, and `uvx` in the `mcp add` line. `test_link_conventions.py` is
  out of scope (C8) and must stay green untouched.
- **Regression (automated, T3):** full `uv run pytest` green — this is docs +
  packaging, so no query name/argument/output/exit-code changes (NFR-4).
- **Local artifact integration (manual, pre-upload — T1, re-run T7):** `uv build`
  → install wheel-only and sdist-only into **separate** fresh venvs → build +
  query + `serve` from each, `cryptography` absent. This is the Review-provable
  proof that the artifact-to-be-uploaded works (AC-1.7/NFR-1/NFR-2), and the
  strongest pre-release signal (matching `distributable-install`/`security-posture`
  clean-env precedent).
- **Provenance (manual mechanical pre-flight, T7/T8):** version parity
  `pyproject.toml` == wheel metadata == git tag == `pypi.org` JSON — a checklist
  item, not a test (the pypi.org leg can't be asserted before release).
- **Release-only, human-executed at `/go-live` (T8–T10):** the live `uv publish`,
  the 404→version flip, the partial-failure re-verification (AC-1.8), the
  clean-machine install from live PyPI (AC-1.1–1.3), and the live pypi.org page
  render (AC-2.6). These **cannot** be proven at `/peer-review` — the plan says so
  explicitly so the Review gate is not asked to certify what only release can.
- **Deliberately manual, no test:** AC-1.6/NFR-5 (no agent-held credential) — a
  human-owned fact recorded in the release trail, the `security-posture` AC-2.8
  precedent; faking a test for it would be worse than naming it.

## 5. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| **R1 — Burned version number.** A broken/mislabeled upload permanently consumes the version; PyPI never lets it be reused. | High, irreversible | T1 **and** T7 smoke both artifacts in fresh venvs **before** the upload; T5's yank path is written before the irreversible action; AC-1.8 (T8) reconciles a partial upload to the same version rather than burning a new one. |
| **R2 — Honesty-rule ordering (AC-2.4/NFR-3).** A pushed commit claiming "pip install aspark-graph" before the package is live would put a false claim in **public** git history — the exact `distributable-install` A5 rule. | Breaks the project's own honesty guarantee | T9 is sequenced strictly after T8's live-on-PyPI confirmation; all README/test work is prepared in the working tree during `/increment` (reviewable, unpushed) and only committed/pushed at go-live. The wheel embeds the published README legitimately — the artifact describes the state its own upload creates and is unreadable until live. |
| **R3 — Most Must ACs are release-only.** AC-1.1–1.3, 1.5, 1.6, 1.8 can't be proven at `/peer-review`. | Review could over- or under-claim | The plan marks the increment/go-live boundary on every task; T1 de-risks the artifact locally; go-live pre-flight (T7/T8/T10) is the real gate, consistent with this repo's headless QA-at-release norm. `/peer-review` certifies only T1–T5. |
| **R4 — PyPI-page rendering (AC-2.6).** Relative logo/link paths that work on GitHub break on pypi.org. | A broken-looking first impression on the package page | T2 switches the `<picture>` and internal links to absolute GitHub URLs (static leg, review-provable); T10 confirms the live rendered page (release leg). Residual: full render only confirmable post-publish — accepted, named. |
| **R5 — Upload precondition (A6/NFR-5).** No 2FA/token, or an agent inadvertently handling the credential. | Upload fails, or a credential-handling violation | T6 is an isolated **user-owned** task (the `security-posture` T7 pattern); no token appears in any file/log/agent message; T6 must confirm before T8. |
| **R6 — Interrupted release resumed on trust.** The build→upload→tag→push→release sequence fails partway and a retry assumes prior success. | Double-upload, wrong tag, or a silent gap (AC-1.8) | T8/T9 independently re-verify actual per-artifact state from `pypi.org` JSON / `gh`/`git ls-remote` before each next outward step — never from the last known intent — reusing `security-posture` §7's "never resume from trust alone" learning. |
| **R7 — Name safety (Q4).** The 404 confirms only the exact string is unclaimed; typosquat/adjacent names are not ruled out. | Accepted risk, not solved this cycle | Named in spec §6/Out of Scope; the maintainer visually confirms the project URL/owner on the pypi.org page at T10. |

## Deviations

- **2026-07-28 — sdist packaging gap found at `/go-live`'s T7 pre-flight, fixed
  before re-review.** `uv build`'s sdist (at the T7 version bump to 0.7.0)
  included `.claude/settings.local.json` and a 50 MB `.claude/worktrees/`
  agent-worktree directory — both untracked, both invisible to hatchling's
  sdist builder because they're ignored via the maintainer's *global* git
  excludes and this repo's local, uncommitted `.git/info/exclude`, neither of
  which hatchling reads (only the committed `.gitignore`). The wheel was
  unaffected (`[tool.hatch.build.targets.wheel] packages = [...]` already
  scopes it correctly) — this was an sdist-only gap. No task in T1–T5
  anticipated it because none of them build the sdist under conditions where
  an agent worktree exists; T7 (go-live pre-flight) was the first real build
  against the actual working tree.
  **Fix:** added `[tool.hatch.build.targets.sdist]` with an explicit
  `include` allowlist (`/src`, `/tests`, `/README.md`, `/LICENSE`,
  `/pyproject.toml`) in `pyproject.toml` — an allowlist rather than an
  exclude list, so it is immune to *any* future untracked or locally-ignored
  path, not just this one. Verified: sdist manifest confirmed clean
  (`tar tzf`), size dropped 3.0 MB → 78 KB, full suite re-run green, both
  wheel and sdist re-proven independently in fresh venvs (build/query/serve,
  9 tools, `cryptography` absent) — the same T1 technique, re-run post-fix.
  **New regression test added:** `tests/test_packaging.py` (slow-marked —
  invokes a real `uv build`), asserting the sdist's actual tarball manifest
  contains only the allowlisted top-level entries and explicitly names
  `.claude/` and the top-level `.spark/` trail as forbidden, so a future
  widening of the allowlist regresses loudly instead of silently. Full suite
  + slow suite green together (275 + 3, the new test included). This is a
  small, obvious correction serving NFR-2/AC-1.5 as already specified — no
  architecture, scope, or story change; not routed
  back through `/story-time`/`/sprint-plan`.

---

## ✅ PLAN GATE

*All boxes checked → `/increment` may start. Any box open → back to `/sprint-plan`.*

- [x] Spec status is `approved` (never plan against a draft) — 2026-07-27
- [x] Architecture decision includes rejected alternatives (five: twine, CI/OIDC, commit-before-upload, parity-as-test, TestPyPI)
- [x] Architecture respects the constitution's technical constraints — no constitution; CLAUDE.md non-negotiables honoured (determinism/grammar pins untouched, no new dependency, `mcp` cap untouched, install honesty, no agent-held credential, never-resume-on-trust)
- [x] Every task maps to a user story — no orphan tasks, no story without tasks
- [x] Every Must AC and every applicable NFR is covered by at least one task — NFR-6 N/A (headless)
- [x] Every task has a checkable definition of done
- [x] Task order respects dependencies — increment (T1–T5) before go-live (T6–T10); upload (T8) before published-README commit (T9)
- [x] Test strategy covers every Must story
- [x] Status set to `approved` by the user — 2026-07-28, explicit approval at the `/spark` plan gate
