# Release: pypi-publish

| | |
|---|---|
| **Phase** | Keep |
| **Owner** | Release Manager (`/go-live`) |
| **Input** | `review-report.md` (`passed` + re-review `passed`, 2026-07-28), `plan.md` T1–T5 (`done`) + Deviations, T6–T10 (release procedure) |
| **Status** | `preparing` — T7 pre-flight re-verified clean on the corrected artifacts. T8's `uv publish` is prepared for the maintainer to run themselves; T9/T10 are prepared, pending (a) the maintainer's confirmation that T8 succeeded and (b) the coordinator's go. |
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

## 4. Release Actions — PREPARED, NOT YET EXECUTED

**No outward-facing action has been taken. Nothing was published, committed,
tagged, or pushed.** `dist/` holds the clean, corrected, independently
re-verified 0.7.0 wheel + sdist. The steps below are prepared and handed off.

### T6 — Maintainer credential checklist (user-owned; no agent touches the token)

Hand this to the maintainer (Andreas Lottes). No agent reads, stores, echoes,
or types the token (A3/NFR-5).

- [ ] **2FA enabled** on the PyPI account — pypi.org → *Account settings* →
  *Two factor authentication* (A6).
- [ ] **API token created.** The project `aspark-graph` does not exist on PyPI
  yet (404), so a *project-scoped* token can't be minted for the **first**
  upload — create a token scoped to *Entire account* for the initial publish,
  then (after 0.7.0 is live) rotate to a project-scoped token for future
  releases.
- [ ] **Token exported in your own shell**, never pasted into a file, commit,
  PR, or agent message:
  `export UV_PUBLISH_TOKEN='pypi-…'` (uv uses `__token__` as the username
  automatically when `UV_PUBLISH_TOKEN` is set).
- [ ] **Confirm back to the coordinator** that 2FA is on and the token is set in
  your environment — *without revealing the token value* — before T8.

### T8 — Publish (OUTWARD-FACING, maintainer-run in their own terminal)

**You (maintainer) run this — no agent executes `uv publish`.**

```bash
cd /Users/andreaslottes/aSPARK-graph

# 0. Sanity: confirm you are publishing the intended, CLEAN artifacts.
#    dist/ currently holds the corrected build (sdist manifest fix applied
#    and independently re-verified by the Release Manager). If you rebuild,
#    re-check the manifest before publishing:
uv build
tar tzf dist/aspark_graph-0.7.0.tar.gz | grep -E '\.claude/|worktrees/' \
  && { echo 'ABORT: sdist still contains local cruft'; exit 1; } \
  || echo 'sdist manifest clean'
ls dist/   # expect exactly: aspark_graph-0.7.0-py3-none-any.whl  aspark_graph-0.7.0.tar.gz

# 1. Publish BOTH the wheel and the sdist (UV_PUBLISH_TOKEN already set — T6).
uv publish
```

Then **independently re-verify from PyPI's public API** (an agent may run this
read — no credential needed) before any further step (AC-1.8):

```bash
curl -s https://pypi.org/pypi/aspark-graph/json \
  | python3 -c 'import sys,json;d=json.load(sys.stdin);\
v=d["info"]["version"];fs=sorted(f["packagetype"] for f in d["releases"].get(v,[]));\
print("version:",v,"files:",fs)'
# Expect: version: 0.7.0  files: ['bdist_wheel', 'sdist']
```

Apply AC-1.8: if only one file type landed, upload the missing one to the
**same** 0.7.0 (`uv publish dist/<missing-file>`); a genuinely broken upload
follows §0's yank path. Never assume success from intent — read PyPI directly.
Record the human authorizer + "no agent held the credential" here once done.

### T9 — Release commit, tag, push, GitHub Release (OUTWARD-FACING — agent-run, **only after** T8 confirms live)

Load-bearing order (A5/NFR-3): the published-path README claim must not enter
public git history until PyPI confirms 0.7.0 is live. Once T8's PyPI JSON shows
0.7.0 with both file types, the coordinator relays the go, and these run (each
step re-verified before the next — AC-1.8):

```bash
# Release file set: pyproject.toml, uv.lock, README.md, tests/test_readme.py,
# tests/test_packaging.py (new), CLAUDE.md, .spark/pypi-publish/*
# (NOT .spark/BACKLOG.md — pre-existing, out of scope)
git add pyproject.toml uv.lock README.md tests/test_readme.py \
        tests/test_packaging.py CLAUDE.md .spark/pypi-publish/
git commit -m "feat(pypi-publish): ship v0.7.0 — publish aspark-graph to PyPI

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
git tag -a v0.7.0 -m "aspark-graph v0.7.0 — first public PyPI release"
git push origin main          # re-verify: git ls-remote origin main
git push origin v0.7.0        # re-verify: git ls-remote --tags origin | grep v0.7.0
gh release create v0.7.0 --title "v0.7.0 — aspark-graph on PyPI" --notes "<changelog §3>"
# if a long --notes heredoc is sandbox-blocked: minimal create, then
# gh release edit v0.7.0 --notes-file <file>  (security-posture §7 learning)
```

Note: `plan.md`'s Deviations section is part of `.spark/pypi-publish/` and is
carried in the same commit — the sdist fix's own trail ships with the release
it fixed, not as a separate follow-up.

### T10 — Post-publish clean-machine verification (agent-run, after T9)

From a fresh venv with no checkout: `uvx aspark-graph …` / `pip install
aspark-graph` from **live** PyPI → `build` + a query + `serve` (9 tools);
`cryptography` absent; `GET pypi.org/pypi/aspark-graph/json` returns 0.7.0;
open the pypi.org project page and confirm the README renders (logo + links
resolve — AC-2.6 live leg; the absolute URLs, verified static at review).

### Working-tree state left by this pass

`git status`: `pyproject.toml` (→0.7.0 + sdist allowlist) and `uv.lock`
(→0.7.0) modified; `README.md` / `CLAUDE.md` / `tests/test_readme.py` from the
T2–T4 review; new `tests/test_packaging.py`; untracked `.spark/pypi-publish/`.
`dist/` holds the corrected, independently re-verified 0.7.0 wheel + sdist.
`.spark/BACKLOG.md` remains pre-existing and untracked, untouched. No commit,
tag, push, or publish has occurred.

---

## 5. Learnings (Keep!) — preliminary (finalize at the successful release)

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

---

## ✅ KEEP GATE

*All boxes checked → the loop is closed. The feature is done-done.*

- [x] All pre-flight checks passed at release time — re-verified fresh,
  independently, on the corrected artifacts (§1); wheel byte-identical to the
  pre-fix build, sdist manifest read and confirmed clean by the Release
  Manager itself, both suites green, both artifacts smoke-tested in fresh
  venvs
- [x] Changelog written in user-facing language — no commit hashes / ticket IDs / jargon
- [ ] Release actions executed and verified — **not yet.** Prepared, not
  executed. T8 (`uv publish`) awaits the maintainer running it themselves;
  T9/T10 await T8's confirmation + the coordinator's go. This is the one hard
  stop left in the loop, by design — not a gap.
- [x] Learnings recorded — preliminary (to be finalized at the successful release)
- [ ] Status set to `released` — pending T8 (maintainer) → T9/T10 (agent, on go)

### QA-equivalent (this headless tool)

- [x] QA gate override recorded with authorizer, quoted policy, reason, substitution
- [x] Wheel **and** sdist packaged-install QA-equivalent re-run fresh at
  prepare time on the corrected artifacts (9 tools each, build, query, crypto
  absent from each)
- [ ] Live-index QA-equivalent (T8/T10) — pending the maintainer's publish
