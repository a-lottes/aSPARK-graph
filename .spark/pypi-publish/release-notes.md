# Release: pypi-publish

| | |
|---|---|
| **Phase** | Keep |
| **Owner** | Release Manager (`/go-live`) |
| **Input** | `review-report.md` (`passed` + re-review `passed`, 2026-07-28), `plan.md` T1–T5 (`done`) + Deviations, T6–T10 (release procedure) |
| **Status** | `released` |
| **Version** | 0.7.0 (proposed — see Version Justification) |
| **Previous version** | 0.6.0 |
| **Date** | 2026-07-28 |

> **Prepare-only pass.** T7 (version bump, lock, build, dual-artifact smoke,
> version-parity) executed for real, twice: once at the original T7 pass (which
> correctly caught the sdist packaging gap below and halted the release), and
> again here, independently, on the corrected artifacts after the fix was
> re-reviewed. T6 is user-owned. T8's `uv publish` is handed to the maintainer
> to run in their own shell (no agent holds a PyPI credential — A3/NFR-5). T9/T10
> are prepared as pending commands awaiting a maintainer "T8 succeeded"
> confirmation **and** the coordinator's go.

## 0. PyPI Rollback Path (drafted before any upload — US-4)

This is **distinct** from this project's existing git-tag rollback path (see
`security-posture/release-notes.md` for that precedent): a PyPI version
number, once uploaded, is burned forever — even a yanked version can never be
reused for a different, fixed release. Git rollback (revert/reset/re-tag) has
no equivalent power here.

**If a published version turns out broken or wrong (AC-4.1/4.2):**

1. **Yank it.** From the PyPI project page
   (`https://pypi.org/manage/project/aspark-graph/releases/` → the release's
   *Options* → *Yank*), mark the specific version as **yanked**, with a short
   reason. Yanking is a maintainer action taken through the PyPI web UI (or the
   PyPI API) with the maintainer's own credentials — it is **not** a `twine`/
   `uv publish` operation, so don't expect an `uv`/`twine` yank command; no
   agent performs this; no agent holds the credential that could (A3/NFR-5).
2. **A yank hides, it does not delete.** The yanked version stays resolvable
   by an exact pin (`pip install aspark-graph==X.Y.Z`) for anyone who already
   depends on it, but is excluded from `pip install aspark-graph`'s normal
   "latest" resolution going forward. The file bytes and the version number
   remain permanently reserved on PyPI.
3. **The fix ships as a new version.** There is no "re-publish 0.7.0 with the
   bug fixed" — the next attempt is `0.7.1` (or whatever the next number is).
   Plan for this before uploading, not after: T1/T7's pre-upload dual-venv
   smoke test exists specifically to make reaching this path unlikely, not to
   make it survivable after the fact.
4. **Update the README/CLAUDE.md if the yanked version was the one they
   pointed at.** A yank is a PyPI-side action; it does not retroactively fix
   documentation that named the bad version number explicitly (this project's
   docs do not name specific versions in install commands, so this is
   expected to be a non-issue in practice — recorded here so it isn't missed
   if that ever changes).

**This is the *completed-but-wrong* case (AC-4.1/4.2).** A release that fails
**partway through** the upload sequence — wheel uploads but the sdist doesn't,
or the upload succeeds but the tag/push/GitHub-Release step never runs — is a
**different** case, covered by the plan's AC-1.8 (T8/T9): independently
re-verify the actual live state from PyPI/GitHub before any further step, and
reconcile a partial-but-live version by uploading the missing artifact to the
**same** version rather than treating it as broken. **Do not conflate the
two** (AC-4.3): a partial upload is repaired in place; a genuinely broken or
wrong upload is yanked and superseded by a new version. Which path applies is
determined by what is actually live on `pypi.org`, checked directly — never
assumed from the last known intent (the `security-posture` "never resume from
trust alone" lesson, `CLAUDE.md`).

**All of the above references only actions the maintainer can take directly
on PyPI's own UI/API (AC-4.2)** — no step assumes an agent-held credential or
an agent-executed upload.

**Rollback-path accuracy confirmed for the proposed version (2026-07-28,
re-confirmed after the sdist fix):** T5 drafted this section assuming `0.7.0`;
the version proposal is still `0.7.0` after the sdist packaging fix (only the
artifact *contents* changed, not the version), so the "next attempt is `0.7.1`"
wording is still correct as written. No change needed.

---

## Gate Status

| Gate | Status | Notes |
|---|---|---|
| Review (`review-report.md`) | **passed** | 2026-07-28, T1–T5, zero Blockers/Majors, one Minor fixed (F1), one by-design honesty Nit (F2). **Re-reviewed 2026-07-28** after the sdist packaging fix (see below) — **still passed**, no new findings. |
| QA (`qa.md`) | **override — N/A** | See the QA Gate Override Record below. There is no `qa.md` and there never will be one for this feature. |

### Re-review — sdist packaging fix (routed back through `/increment` → `/peer-review`, 2026-07-28)

**What triggered it.** This ceremony's own T7 pre-flight (first pass) built a
real sdist at the 0.7.0 version bump and found it carried
`.claude/settings.local.json` and a ~50 MB `.claude/worktrees/` agent-worktree
tree — both untracked, both invisible to hatchling's sdist builder because
they're ignored only via the maintainer's global git excludes and this repo's
local `.git/info/exclude`, neither of which hatchling reads (it reads only the
committed `.gitignore`). The wheel was unaffected — `packages = [...]` already
scoped it correctly; this was an sdist-only gap. Per this role's hard rule
(fix nothing on the release commit), the release was halted and routed back
through `/increment`, then `/peer-review`, before returning here — exactly the
path this ceremony's own rules require for a pre-flight failure.

**Fix applied (recorded as a Deviation in `plan.md`, not a scope/architecture
change):** an explicit `[tool.hatch.build.targets.sdist]` **include allowlist**
in `pyproject.toml` (`/src`, `/tests`, `/README.md`, `/LICENSE`,
`/pyproject.toml`) — an allowlist rather than an exclude list, so it is immune
to any *future* untracked or locally-ignored path, not just this one. A new
regression test, `tests/test_packaging.py` (slow-marked, builds a real sdist
and inspects the actual tarball manifest, explicitly naming `.claude`/`.spark`
as forbidden top-level entries), locks the fix in.

**Re-review verdict (quoted): "Still passed — the fix is sound and
complete."** The reviewer did a genuine re-review, not a rubber stamp: rebuilt
both artifacts itself under the exact untracked-`.claude/` conditions that
caused the original bug, confirmed the resulting sdist manifest carries only
the allowlisted entries (no `.claude/`, no top-level `.spark/`), confirmed the
wheel manifest unaffected, and **proved the new test has teeth** by temporarily
reverting the allowlist and confirming `test_packaging.py` fails, naming
`.claude`/`.spark`/`docs`/`CLAUDE.md`/`SECURITY.md`/`uv.lock` explicitly,
before restoring the fix. No new findings. No scope creep (`git diff` since
the first review pass is exactly `pyproject.toml`, `uv.lock`, the new test,
and `plan.md`'s Deviations note — zero `src/` drift). See
`review-report.md`'s "Re-Review — sdist packaging fix" section for the full
record.

**Independently re-confirmed by the Release Manager, right now, not taken on
the reviewer's word alone (§1 below):** rebuilt `dist/` fresh myself, read the
actual tarball manifest myself, re-ran both suites myself, and re-smoke-tested
**both** the wheel and the sdist in fresh venvs myself. See §1.

### QA Gate Override Record

- **Authorizer:** the project's own `CLAUDE.md` (committed, reviewed by the
  project owner) — the same standing policy applied to every aspark-graph
  release since v0.2.0 (`close-the-loop` through `security-posture`; none of
  those releases has a `qa.md` either). First authorized by Andreas Lottes
  (andreas@lottes.dev) for v0.3.0 (2026-07-16) and carried forward with the
  same rationale and authorizer through v0.3.1, v0.4.0, v0.4.1, v0.5.0 and
  v0.6.0.
- **Quoted policy — CLAUDE.md, "Using aspark-graph in /peer-review":** *"QA-Tester
  half (`/demo-day`): N/A. aspark-graph is headless (no UI); the QA-equivalent
  is done hands-on in `/peer-review` (full suite, clean-env install, `serve`
  boot, byte-identical build, real-repo impact check). No active demo-day block
  applies here."*
- **Quoted policy — CLAUDE.md, "Working here":** *"There is no UI, so
  `/demo-day` (browser QA) is structurally N/A — the QA-equivalent (full suite,
  clean-env packaged install, `serve` boot, byte-identical build, a real-repo
  `impact` check) is done in `/peer-review`. Overriding the QA gate at
  `/go-live` is legitimate here, but record the authorizer + reason in the
  release report — never a silent skip."*
- **Reason:** aspark-graph is a headless CLI/MCP stdio tool with no browser or
  visual surface, so `/demo-day` is **structurally inapplicable**, not skipped.
  The one visual artifact this cycle introduces — the README as rendered on the
  **PyPI project page** — is captured as a falsifiable acceptance criterion
  (AC-2.6), verified statically at review (absolute GitHub URLs) and to be
  verified live at T10; it does not constitute a UI QA surface.
- **What substituted for it (a gate substitution, not a skip):** the
  QA-equivalent was performed hands-on at `/peer-review` (both passes — the
  original T1–T5 review and the sdist-fix re-review) **and** is re-performed
  fresh here at release-prepare time (§1): full + slow suites re-run, **both**
  wheel and sdist independently reinstalled into fresh venvs with all 9 tools
  registered, `build` + a real query run end-to-end, `cryptography` absent from
  each. This is a gate substitution, not a silent skip. The live-index legs
  (AC-1.1–1.3, 1.5, 1.6, 1.8, AC-2.6 live) remain the release-only
  QA-equivalent (T8/T10), not yet executable (no agent-held credential).

---

## 1. Pre-Flight Checks (prepare pass, 2026-07-28 — re-verified on corrected artifacts)

All checks below were run **fresh, independently, by the Release Manager**, on
the corrected working tree, right now — not copied from `review-report.md`'s
re-review section or from the coordinator's summary of it.

- [x] `review-report.md` status is `passed` (original T1–T5 pass **and** the
  sdist-fix re-review, both 2026-07-28) — read in full, confirmed genuine
  (rebuild-under-bug-conditions + proof-of-teeth test revert, not a rubber stamp)
- [x] `plan.md` Deviations section documents the sdist fix as a small, obvious
  correction (not a scope/architecture change) — read in full, matches the
  actual `pyproject.toml` diff
- [x] QA gate: N/A override recorded above with authorizer, quoted policy, reason, substitution
- [x] Unpublished-release guard — every other `.spark/*/release-notes.md` is
  `released` except `close-the-loop` (annotated `preparing (bundled into
  0.3.0)`, a known/documented bundled state, not a surprise)
- [x] PyPI name still available / honesty intact — `GET
  https://pypi.org/pypi/aspark-graph/json` → **HTTP 404** (re-checked just now;
  name unclaimed, committed HEAD README's "not yet published" remains true)
- [x] No `v0.7.0` tag collision — absent locally and on `origin` (re-checked)
- [x] Version fields — `pyproject.toml` `version = "0.7.0"`; `uv.lock`'s own
  `aspark-graph` self-entry `0.7.0` — unchanged from the original T7 pass, no
  drift introduced by the sdist fix
- [x] `pyproject.toml`'s new `[tool.hatch.build.targets.sdist]` block read
  directly — `include = ["/src", "/tests", "/README.md", "/LICENSE",
  "/pyproject.toml"]`, with an explanatory comment on *why* an allowlist (not
  an exclude list) was chosen
- [x] **Rebuilt `dist/` fresh, myself, right now** (`rm -rf dist && uv build`)
  — `aspark_graph-0.7.0-py3-none-any.whl` (49,754 bytes — **byte-identical**
  to the pre-fix wheel build, confirming the wheel was genuinely untouched by
  the sdist-only fix) + `aspark_graph-0.7.0.tar.gz` (79,487 bytes — down from
  the original defective 3.0 MB build, matching the reviewer's reported ~78 KB)
- [x] **Read the sdist tarball's actual manifest myself** (`tar tzf`, not the
  reviewer's or coordinator's description) — top-level entries are exactly
  `.gitignore, LICENSE, PKG-INFO, README.md, pyproject.toml, src, tests`. An
  explicit grep for `.claude|.spark|worktree|settings.local` across the full
  manifest returns only `tests/fixtures/sample_repo/.spark/demo/*.md` — the
  **tracked test fixture** under `/tests` (legitimate, part of the allowlist,
  not the top-level SPARK trail) — confirmed clean
- [x] Full default suite green — `uv run pytest -q` → **275 passed, 3
  deselected** (one more deselected than the original pass — the new
  slow-marked `test_packaging.py` test)
- [x] Slow suite green — `uv run pytest -m slow -q` → **3 passed** (the NFR-1
  bench, the MCP transport smoke, and the new
  `test_sdist_manifest_carries_no_untracked_or_local_content`)
- [x] **Wheel** fresh-venv packaged-install smoke, re-run on the freshly-built
  0.7.0 wheel — separate `uv venv`, wheel-only install: console script on
  PATH; `aspark-graph build <scratch repo>` succeeds; `find_nodes hello` →
  the `Function` node; `serve` registers **exactly 9 tools**;
  `cryptography`/`joserfc` absent from the resolved tree
- [x] **Sdist** fresh-venv packaged-install smoke, re-run on the freshly-built
  0.7.0 sdist (the corrected artifact — this is the leg that failed before the
  fix) — separate `uv venv`, sdist-only install: `aspark-graph build <scratch
  repo>` succeeds; `find_nodes hello` → the `Function` node; `serve` registers
  **exactly 9 tools**; `cryptography`/`joserfc` absent from the resolved tree
- [x] Wheel metadata re-spot-checked — `Name: aspark-graph`, `Version: 0.7.0`,
  `License: MIT`, `Requires-Python: >=3.11` — unchanged from the original pass
- [x] Version parity (mechanical) — `pyproject.toml` (0.7.0) == `uv.lock`
  self-version (0.7.0) == wheel `METADATA` version (0.7.0) == intended tag
  `v0.7.0`. The `pypi.org` leg cannot be asserted pre-upload (deferred to
  T8/T10).

**No blocker this pass.** Every check that failed the first time (the sdist
manifest) is independently confirmed clean on a rebuild I ran myself, not
merely reported as fixed. `dist/` currently holds the clean, correct 0.7.0
wheel + sdist, ready for the maintainer's T8.

### Not run this pass (correctly deferred to release-only steps)

- Byte-identical rebuild (double-`build --full` diff) — out of scope for a
  packaging-only pre-flight; NFR-1 is unaffected by a docs/packaging cycle and
  was already covered by the T1–T5 review pass and the `security-posture`
  precedent.
- Live-index checks (AC-1.1–1.3, 1.5, 1.6, 1.8), live PyPI-page render
  (AC-2.6 live) — all downstream of the actual `uv publish`; pending T8.

---

## 2. Version Justification

Shipped: `0.6.0` → **`0.7.0` (semver minor)**.

This project states no explicit versioning policy, so it follows semver by
convention, and its own history sets the precedent: a **new user-facing
capability** is a minor bump (`incremental-builds` 0.3.1→0.4.0; `go-rust-support`
0.4.1→0.5.0; `security-posture` 0.5.0→0.6.0), while a **small
backwards-compatible guard/fix with no capability change** is a patch
(`robustness` 0.4.0→0.4.1).

This release is the former:

- **A genuinely new distribution capability.** For the first time, the tool is
  installable in one command from public PyPI (`uvx aspark-graph …` /
  `pip install aspark-graph`) — the exact install path its primary consumer (an
  agent that `uvx`-launches an MCP server) expects, and the single largest
  adoption blocker to date (spec US-1, a Must). "Can install it the normal way"
  is new user-facing capability even though no `src/` byte changed.
- **User-facing surface changes ship with it.** The README leads with the
  published command, relocates from-source to `## Development`, adds the
  determinism-promise-and-boundary prose; CLAUDE.md's deferral note is resolved.
  Per this project's rule that user-facing doc/metadata changes ship as their
  own version (Q2/C6), this is a version-worthy change, not an unversioned edit.

It is **not a patch:** the `robustness` patch precedent was a single guard with
no capability change; this opens an entirely new install path. It is **not a
major:** nothing that worked stops working — the from-source path is retained
(under Development), and no query name, argument, output shape, exit code, graph
schema, or grammar pin changes (this is packaging + docs; NFR-4). The published
**wheel** is `py3-none-any` and behaviourally identical to the 0.6.0 code.

**A fresh `0.7.0` (not publishing the existing `0.6.0` code) is also the honest
provenance choice:** the `v0.6.0` git tag's tree says "not yet published to a
package index." Publishing 0.6.0's code to PyPI would create a package whose
corresponding tag denies it exists. `0.7.0` gets its own commit + tag whose
tree truthfully documents the published state — pypi 0.7.0 == git `v0.7.0` ==
the commit that says "published."

**The mid-cycle sdist packaging fix does not change this justification.** It
corrects the *contents* of the sdist artifact at the already-decided 0.7.0
version — it is not itself a second version-worthy change (no code, no new
capability, no user-facing behaviour); "0.7.0" still names one coherent
release: PyPI availability, published-state docs, and (as of the fix) a sdist
that only ships what it should.

---

## 3. Changelog

User-facing language. No commit hashes, ticket IDs or internal jargon.
*(Describes what 0.7.0 delivers once live; it enters the README/public history
only at T9, after the package is confirmed on PyPI — A5/NFR-3.)*

### Added

- **Install aspark-graph in one command, straight from PyPI.** You no longer
  have to clone the repository and run a sync to use the tool. `pip install
  aspark-graph` puts the `aspark-graph` command on your PATH, and `uvx
  aspark-graph serve` launches the MCP server with no checkout at all — which is
  exactly how an agent is meant to start it. Both the command-line queries and
  the MCP server run from the published package.
- **The README now explains the determinism promise — and its limits.** It says
  plainly why the language grammars are pinned to exact versions and that the
  lockfile is part of the deal, so a graph you build rebuilds byte-for-byte on
  an unchanged repository. It is equally plain about the boundary: that promise
  holds for a fixed set of grammars, and upgrading a grammar can change what
  gets extracted — so a grammar upgrade is always a deliberate, changelog-noted,
  version-bumped event, never a silent shift under your feet.

### Changed

- **The install instructions describe the working published path — and only
  that.** The README leads with the one-command PyPI install; the "add as an MCP
  server" instructions use `uvx aspark-graph serve` instead of pointing at a
  local checkout. The from-source route (clone → sync → build) is kept for
  contributors under a **Development** heading. The old "not yet published to a
  package index" note is gone, and nothing in the README or CLAUDE.md still
  claims the tool is install-from-source only.
- **The package page renders cleanly on PyPI.** The logo and the in-README links
  (to the security policy and the integration guide) now use absolute addresses,
  so the project page on pypi.org shows the same images and working links you
  see on GitHub rather than broken thumbnails and dead links.

### Fixed

- N/A user-facing — this release changes no tool behaviour. Every query,
  argument, output shape and exit code is identical to 0.6.0; this cycle is
  distribution and documentation only. (A packaging-hygiene issue was found
  and fixed *during* this release's own preparation, before anything was
  published — see the Re-review note above; it never reached a user and is not
  a user-facing "fix.")

---

## 4. Release Actions — EXECUTED, ALL VERIFIED

**Every outward-facing action below actually happened and was independently
re-verified after the fact — none taken on trust from a tool's exit code
alone.**

### T6 — Maintainer credential checklist ✅ done by the maintainer

2FA confirmed on, an account-scoped API token created (the `aspark-graph`
project didn't exist on PyPI yet, so a project-scoped token wasn't mintable
for the first upload), `UV_PUBLISH_TOKEN` exported in the maintainer's own
shell. No agent read, stored, echoed, or typed the token at any point
(A3/NFR-5 held throughout).

**One real hiccup, resolved without any agent touching the credential:** the
first `uv publish` attempt returned `403 Username/Password authentication is
no longer supported` — PyPI's response when it doesn't see a recognized
token, not a rejected-token error. Diagnosed via credential-free checks only
(confirmed no `~/.pypirc` existed to interfere; confirmed the coordinator's
own shell had no stray `UV_PUBLISH_TOKEN`, which was expected and correct).
Root cause was almost certainly the export not surviving into the exact shell
`uv publish` ran in — a maintainer-side shell-session issue, not a tool or
process defect. The maintainer re-exported the token in the same terminal as
the publish command and it succeeded on retry.

**A scope question surfaced and correctly declined mid-release:** the
maintainer asked about switching to GitHub Actions trusted publishing (OIDC)
after hitting the 403. The coordinator flagged that this reverses the spec's
explicit Q1/C5 decision and would require standing up this repo's first-ever
CI workflow — real new scope, not a quick fix — and asked the maintainer to
choose explicitly rather than sliding into it. The maintainer chose to keep
debugging the approved manual-token path, which then worked. Recorded here
because it's a real instance of the loop's own discipline (no architecture
drift without an explicit decision) holding under actual release pressure.

### T8 — Publish ✅ executed by the maintainer, confirmed live by the coordinator

The maintainer ran `uv build && uv publish` in their own terminal — no agent
executed or witnessed the token. The coordinator then independently verified
success by reading PyPI's public JSON API directly (no credential needed):

```
GET https://pypi.org/pypi/aspark-graph/json
→ version: 0.7.0
→ files: ['bdist_wheel', 'sdist']
→ aspark_graph-0.7.0-py3-none-any.whl  49754 bytes
→ aspark_graph-0.7.0.tar.gz            79487 bytes
```

Both byte counts match the locally-built, independently re-verified artifacts
exactly — confirming what's live on PyPI is genuinely the corrected,
re-reviewed build, not some other or stale one. Both file types present;
AC-1.8's partial-upload reconciliation path was not needed.

### T9 — Release commit, tag, push, GitHub Release ✅ executed by the coordinator, each step re-verified

Executed only after T8's live confirmation, exactly as the honesty-rule
ordering (A5/NFR-3) required — the published-path README claim entered public
git history strictly after PyPI confirmed 0.7.0 was live, never before.

| Step | Result | Independently re-verified |
|---|---|---|
| Stage release file set | `pyproject.toml`, `uv.lock`, `README.md`, `tests/test_readme.py`, `tests/test_packaging.py`, `CLAUDE.md`, `.spark/pypi-publish/*` — **not** `.spark/BACKLOG.md` | `git status --short` confirmed the exact intended set, nothing extra |
| Commit | `18ca494` — "feat(pypi-publish): ship v0.7.0 — publish aspark-graph to PyPI" | 10 files changed, 1358 insertions(+), 45 deletions(-) |
| Tag | `v0.7.0` (annotated) | `git tag --list \| grep v0.7.0` confirmed locally before push |
| Push `main` | `2d5c089..18ca494` | `git ls-remote origin main` → `18ca494...`, matches `git rev-parse HEAD` exactly |
| Push tag | `v0.7.0 -> v0.7.0` | `git ls-remote --tags origin` → tag dereferences (`^{}`) to `18ca494`, the exact commit pushed |
| GitHub Release | Created (minimal `--notes` first, then `gh release edit --notes-file` with the full changelog — the long-heredoc sandbox-block fallback from `security-posture` §7, needed again here) | `gh release view v0.7.0 --json isDraft,publishedAt,tagName` → `isDraft: false`, published, correct tag |

### T10 — Post-publish clean-machine verification ✅ executed by the coordinator

From a completely fresh `uv venv` with **no checkout of this repo present**:

- `pip install aspark-graph` resolved from live PyPI, version confirmed `0.7.0`
  via `importlib.metadata`.
- `cryptography` and `joserfc` absent from the installed tree.
- `aspark-graph build .` on a fresh scratch repo → succeeded; `find_nodes`
  returned the expected `Function` node.
- `aspark-graph serve` completed the JSON-RPC `initialize` handshake and
  registered exactly the 9 expected tools.
- **The live pypi.org project page rendered correctly** (AC-2.6's live leg,
  the one thing only verifiable post-publish): the logo `<picture>` loaded
  fully (2172×724, via PyPI's camo image proxy decoding the
  `raw.githubusercontent.com` URL — `complete: true`, not broken), and both
  `SECURITY.md`/`docs/aspark-integration.md` links resolved to the correct
  absolute `github.com/a-lottes/aSPARK-graph/blob/main/...` URLs — checked
  directly against the rendered DOM, not assumed from the source markup.

### Final working-tree state

`git status --short` → only `.spark/BACKLOG.md` (pre-existing, untracked,
untouched throughout this entire feature, exactly as instructed). Local
`HEAD` == `origin/main` == `18ca494`. `v0.7.0` tag on origin dereferences to
the same commit. Temp venvs and scratch directories cleaned up.

---

## 5. Learnings (Keep!)

### What went well

- **The pre-flight-failure → `/increment` → `/peer-review` → `/go-live` loop
  worked exactly as designed, on its first real test in this project's
  history for a *release-manager-discovered* defect.** T7 caught a real,
  irreversible-if-shipped defect (local machine config + a 50 MB agent
  worktree in a public sdist); the Release Manager fixed nothing itself,
  routed it back through the correct gates, and only resumed once an
  independent re-review — not a self-report — certified the fix.
- **The re-review was genuinely adversarial, not a rubber stamp.** The
  reviewer rebuilt both artifacts under the exact conditions that produced the
  bug and proved the new regression test would have caught it, by reverting
  the fix and watching the test fail by name. That is the standard this
  project's whole review discipline aims for.
- **Independent re-verification, not trust in a report, closed the loop
  here too.** Rather than accepting the coordinator's description of the fix
  and re-review as sufficient, the Release Manager re-ran `uv build`, read the
  raw tarball manifest, re-ran both suites, and re-smoke-tested both artifacts
  in fresh venvs itself before resuming — "trust nothing you didn't verify at
  release time," applied to a *retry after a fix*, not just after an
  interruption (extending the `security-posture` §7 pattern to a new trigger).
- **The honesty ordering held under a real stop-and-resume.** Because the
  published-path README claim lives only in the uncommitted working tree and
  PyPI is still 404, halting and later resuming the release left public git
  history honest throughout — no false claim was ever at risk of being pushed.
- **The blocker was caught before a version was burned.** Had the defective
  sdist been published, 0.7.0 would be permanently spent and the leak
  permanent. Catching it at prepare, before any upload, cost nothing but a
  rebuild and one extra review pass.
- **The credential boundary held under real friction, not just in the
  abstract.** The maintainer hit a genuine `uv publish` 403 and, separately,
  a live temptation to switch to GitHub Actions trusted publishing to route
  around it. Neither pressure caused the boundary to bend: no agent ever
  touched the token (diagnosis stayed credential-free — variable *names*
  only, never values, and `~/.pypirc` was checked for existence, never read),
  and the scope question was surfaced explicitly and declined by the
  maintainer rather than silently adopted mid-release.
- **Confirmed live before declaring anything done — for both the upload and
  the release commit's contents.** The wheel/sdist byte sizes read back from
  PyPI's public JSON matched the locally-built artifacts exactly, closing the
  loop that "the maintainer said it worked" alone would have left open. Same
  discipline applied to `git push`/`gh release create`: each was re-read from
  the remote, not assumed from a zero exit code.

### What we'd do differently

- **Inspect the sdist *manifest*, not just that it installs — now codified.**
  The original T1/AC-1.7 "installs and runs" smoke passed on the defective
  sdist because the leaked files were inert; only reading the actual tarball
  listing surfaced the leak. This is now enforced by
  `tests/test_packaging.py`, not just a manual pre-flight step — the right
  place for it to live going forward.
- **Sdist hygiene should not depend on the *global* gitignore.** hatchling's
  sdist reads the repo's committed `.gitignore` only. The fix (an explicit
  allowlist) is the right general answer: it is immune to *any* future
  untracked or locally-ignored path, not just the one that triggered this.
- **A first-time PyPI token setup deserves a pre-flight sanity check of its
  own.** The 403 cost real back-and-forth that a one-line check — export the
  token, then immediately verify `[ -n "$UV_PUBLISH_TOKEN" ]` and a
  prefix/whitespace check, *in the same shell about to run `uv publish`* —
  would have caught before the first failed attempt. Worth adding to T6's
  checklist for the next maintainer-token setup this project does.

### Patterns worth reusing (CLAUDE.md / memory candidates)

1. **Sdist manifest gate, now a real regression test.**
   `tests/test_packaging.py` builds a real sdist and asserts the actual
   tarball manifest against an allowlist, naming forbidden paths explicitly.
   Any future packaging-adjacent project should default to this shape rather
   than a manual pre-flight check alone.
2. **Prefer an explicit build-target allowlist over gitignore subtraction**
   for any package that promises provenance: a deliberate
   `[tool.hatch.build.targets.sdist]` `include` beats relying on what happens
   not to be gitignored, and is immune to drift by construction.
3. **A re-review after a mid-cycle fix should re-derive the evidence, not
   re-read the fix.** Rebuilding under the exact bug-triggering conditions and
   proving the new test fails on the pre-fix state (then restoring) is a
   stronger bar than "the diff looks right" — worth naming as the standard for
   any fix routed back through `/peer-review` mid-release.
4. **Independent re-verification applies to "the coordinator reports a fix was
   made and re-reviewed," not only to "a session was interrupted."** The
   `security-posture` learning ("never resume a possibly-interrupted release
   from trust alone") generalizes: any report of state you did not personally
   observe — including a fix-and-re-review your own gate demanded — gets
   independently re-derived before the release resumes.
5. **Diagnose credential problems without ever touching the credential.**
   Faced with an auth 403, every diagnostic step stayed read-only and
   value-free: variable *names* only (`env | grep '^UV_PUBLISH' | cut -d= -f1`),
   file *existence* only (`test -f ~/.pypirc`), never asking the user to paste
   a token or even a fragment of one into chat. A reusable shape for any
   future credential-adjacent debugging in this project.
6. **When a maintainer proposes a scope-changing workaround mid-release
   (e.g. "let's just use trusted publishing instead"), name the reversed
   decision and its real cost explicitly, then let them choose — don't
   silently follow the path of least resistance.** Publishing to PyPI
   is a bigger investment than debugging one env var, but it took explicit
   friction (a 403) to reveal that no CI existed to make trusted publishing
   a one-click fix. Worth the same discipline the next time a "quicker" path
   surfaces mid-release.

---

## ✅ KEEP GATE

*All boxes checked → the loop is closed. The feature is done-done.*

- [x] All pre-flight checks passed at release time — re-verified fresh,
  independently, on the corrected artifacts (§1); wheel byte-identical to the
  pre-fix build, sdist manifest read and confirmed clean by the Release
  Manager itself, both suites green, both artifacts smoke-tested in fresh
  venvs
- [x] Changelog written in user-facing language — no commit hashes / ticket IDs / jargon
- [x] Release actions executed and verified — T8 published by the maintainer
  (one 403 detour, diagnosed and resolved credential-free, resolved on
  retry), independently confirmed live via PyPI's public JSON API (byte
  sizes matching the reviewed build exactly); T9's commit/tag/push/GitHub
  Release each independently re-verified against the remote; T10's
  clean-machine install and live PyPI-page render both confirmed (§4)
- [x] Learnings recorded — finalized, including what the real publish attempt
  surfaced (§5)
- [x] Status set to `released`

### QA-equivalent (this headless tool)

- [x] QA gate override recorded with authorizer, quoted policy, reason, substitution
- [x] Wheel **and** sdist packaged-install QA-equivalent re-run fresh at
  prepare time on the corrected artifacts (9 tools each, build, query, crypto
  absent from each)
- [x] Live-index QA-equivalent (T8/T10) — executed: live install from public
  PyPI in a fresh venv with no checkout, `build`/query/`serve` (9 tools) all
  correct, `cryptography` absent, and the live pypi.org project page
  confirmed rendering (logo loaded, `SECURITY.md`/integration-doc links
  resolving to the correct absolute URLs)
