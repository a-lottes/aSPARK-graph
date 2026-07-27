# Release Notes: security-posture (v0.6.0)

| | |
|---|---|
| **Phase** | Keep |
| **Owner** | Release Manager (`/go-live`) |
| **Input** | `review-report.md` (`passed`), QA gate (N/A — override recorded below) |
| **Status** | `preparing` |
| **Date** | 2026-07-27 |
| **Version** | 0.6.0 (proposed) |
| **Previous version** | 0.5.0 |
| **Bump level** | minor — new user-facing behaviour (confinement refusal + build bounds) and a new document, fully backwards-compatible from the documented install shape |

> **Prepare-only pass.** Everything below the "Release Actions" heading is
> **pending explicit user authorization**. No commit, no tag, no push, no PR,
> no GitHub Release has been created. The working tree still carries the
> feature as uncommitted changes against `HEAD` (`f04c81d`). The exact pending
> commands are listed; the one hard stop left in this loop is the human's
> go/no-go.

---

## 0. Gate Status

| Gate | Status | Notes |
|---|---|---|
| Review (`review-report.md`) | **passed** | 2026-07-27; zero Blockers/Majors/Minors, one Nit (F1, cosmetic build-summary double-count) accepted by the user as-is, no AC impact |
| QA (`qa.md`) | **override — N/A** | See the QA Gate Override Record below. There is no `qa.md` and there never will be one for this feature. |

### Review gate — the one Nit (accepted, quoted verbatim)

- **F1** (Nit, `build.py:104-110`, `build.py:53-65`): "A size-skipped file is
  appended to **both** `report.unparsed` and `report.size_skipped`, so
  `summary()` can read `"1 file(s) unparsed, 1 file(s) skipped (over size
  limit)"` for a single file — a reader may parse it as two files. Consistent
  with the existing 'no extractor' unparsed pattern and harms no AC (AC-3.2
  only requires the size-skipped count), so cosmetic." — **accepted by user
  (2026-07-27), cosmetic, no AC impact.** Recorded as a follow-up candidate in
  Learnings, not fixed on the release commit (the Release Manager fixes
  nothing).

No Blocker, Major or Minor findings. Every Must AC (AC-1.1–1.13, AC-2.1–2.10)
and the Should/Could ACs (AC-3.1–3.4, AC-4.1) trace to implementing code and a
passing test in the review report's traceability table. Verdict: "Passed."

### QA Gate Override Record

- **Authorizer:** the project's own `CLAUDE.md` (committed, reviewed by the
  project owner) — the same standing policy applied to every aspark-graph
  release since v0.2.0 (`close-the-loop` through `go-rust-support`; none of
  those releases has a `qa.md` either). First authorized by Andreas Lottes
  (andreas@lottes.dev) for v0.3.0 (2026-07-16) and carried forward with the
  same rationale and authorizer through v0.3.1, v0.4.0, v0.4.1 and v0.5.0.
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
- **What substituted for it (a gate substitution, not a skip):** the
  QA-equivalent was performed as the T13 regression sweep (`plan.md` §6) and
  independently re-verified by the Reviewer in `/peer-review`
  (`review-report.md` §5) — full suite 275 passed + 2 slow passed;
  `sample_repo` byte-identity verified against *actual pre-change code* via
  `git stash push -u` / `git stash pop` (not merely a double-build);
  clean-environment wheel install (`uv build` → fresh venv → wheel only, with
  `cryptography`/`joserfc` confirmed absent); `serve` JSON-RPC `initialize`
  handshake booting with all 9 tools registered; and a live confinement refusal
  from the packaged install. **Every one of these was independently re-run
  fresh at release time (see §1 Pre-Flight), not cited from an earlier
  report.** This is a gate substitution, not a silent skip.

---

## 1. Pre-Flight Checks

All checks run fresh on 2026-07-27, on the release working tree, on the exact
commit being prepared (`HEAD` = `f04c81d`). None copied from `review-report.md`
or `plan.md` §6.

- [x] `review-report.md` status is `passed` (2026-07-27)
- [x] QA gate: N/A override recorded above with authorizer, quoted policy, reason and substitution
- [x] All plan tasks confirmed `done` — T1 through T13 all marked `done` in `plan.md`
- [x] Full default suite green — `uv run pytest -q` → **275 passed, 2 deselected in 27.74s**
- [x] Slow suite green — `uv run pytest -m slow -q` → **2 passed, 275 deselected in 11.17s**
- [x] Byte-identical rebuild — `aspark-graph build . --full` run twice, `graph.json` diffed → **IDENTICAL**
- [x] Live confinement refusal (CLI) — `aspark-graph build /tmp` → `"/private/tmp: not a repository (no .git, .spark/, or .aspark-graph/graph.json found) — refusing to scan it"`, **exit 1**, one line, no traceback
- [x] Staleness on this repo — `{"stale": false, "changed": [], "missing": [], "files_checked": 106, "advice": null}`
- [x] Clean-env packaged install — `uv build --wheel` → fresh `uv venv` (Python 3.13) → `uv pip install` the wheel only; resolved cleanly; `cryptography`/`joserfc` **absent**
- [x] Confinement refusal from the packaged install — `aspark-graph build /tmp` → exit 1, clean one-line message
- [x] `serve` boots from the packaged install — JSON-RPC `initialize` + `tools/list` handshake completes and registers exactly **9 tools** (`build_graph`, `find_nodes`, `gate_health`, `get_neighbors`, `get_node`, `impact`, `shortest_path`, `staleness`, `story_trace`)
- [x] Lockfile self-version check (a learning from `go-rust-support`) — `uv.lock`'s own `aspark-graph` version is `0.5.0`, matching `pyproject.toml`; **no drift** (bump to `0.6.0` pending below)
- [x] No `v0.6.0` tag collision — `git tag -l v0.6.0` returned empty
- [x] Unpublished-release guard (a learning from `go-rust-support`) — no prior `.spark/*/release-notes.md` is stuck in `preparing`; `robustness` and `go-rust-support` are both `released`, and the v0.4.1 + v0.5.0 close-out was recorded on `main` (`18b8ec0`)
- [ ] Working tree clean on the release commit (PENDING — the uncommitted feature files *are* the release content; see §3 for the staged set)
- [ ] Release commit created (PENDING — awaiting user go)

### Note for the human — a stray untracked file

`git status` shows an untracked `.spark/BACKLOG.md` — a German-language
planning/architecture-review-response document (`Stand: 2026-07-25`), **not**
part of the `security-posture` feature. It is not in the staged set below and
is not part of this release. It should be triaged (committed on its own, moved,
or discarded) rather than left to accumulate in the working tree — see the
`go-rust-support` learnings, which flagged the same "stray working-tree file"
pattern for `README.md`/`docs/*.png`. Recorded as a numbered question, not
acted on.

---

## 2. Version Justification

Current: `0.5.0`. Proposed: **`0.6.0` (semver minor).**

This project states no explicit versioning policy in `pyproject.toml` or the
README, so it follows semver by convention, and its own release history sets
the precedent: a **new capability or new user-facing behaviour** is a minor
bump (`incremental-builds` 0.3.1→0.4.0 for the incremental cache + `--full`
flag + a new public module; `go-rust-support` 0.4.1→0.5.0 for two new
languages), while a **small backwards-compatible guard/bug fix with no
capability change** is a patch (`robustness` 0.4.0→0.4.1).

This release is the former, not the latter:

- **New user-facing behaviour.** A target that is not a repository is now
  refused immediately and legibly on every entry point (CLI: one stderr line +
  exit 1; MCP: `{"found": false, "reason": "outside_confinement"|"too_large",
  "message": …}`) where previously it walked silently or hung. That is a
  behaviour change for those inputs, not just an internal fix — it is the whole
  point of US-1/US-3.
- **New public module.** `src/aspark_graph/confinement.py` (`ensure_repo`,
  `RepoRefused`/`OutsideConfinementError`/`RepoTooLargeError`) widens the
  library's public surface — the same trigger that made `incremental-builds`'
  `parse_cache.py` a minor.
- **New document + prose contract.** `SECURITY.md` ships and is linked from
  README/CLAUDE.md; the README/CLAUDE.md MCP tool descriptions now state that
  `build_graph` writes.

It is **not a major bump** — nothing that works on v0.5.0 stops working
(NFR-4, verified in review and re-verified at pre-flight):

- No query name, argument name, CLI↔MCP name parity, JSON-on-stdout shape,
  exit-1-on-unbuilt-graph behaviour, or any existing success-response key
  changed. The `reason` field gains **two additive values**
  (`outside_confinement`, `too_large`); `found: false` is unchanged, which is
  what aSPARK Core branches on (spec A13).
- No new runtime dependency; `mcp>=1.12,<1.20` is untouched
  (`confinement.py` is stdlib-only).
- From the documented install shape (server cwd = the aspark-graph checkout,
  target passed as `repo`, which is a marked directory), every existing
  behaviour and output is byte-for-byte unchanged (AC-1.8, and the
  byte-identical rebuild above).

It is **not a patch** — `robustness` (patch) added a single empty-query guard
with no capability or behaviour change; this release adds a new module, a new
document, and a new user-visible refusal behaviour across all nine tools.

**Minor is the correct bump: new behaviour and new surface, zero breaking
change from the documented install.**

---

## 3. Changelog

User-facing language. No commit hashes, ticket IDs or internal jargon.

### Added

- **A `SECURITY.md` you can check against the code.** aspark-graph now ships a
  security document that states plainly what it is — a local, offline stdio
  helper that runs with your own file permissions, with no network, no auth and
  no remote access — and, just as plainly, what it is **not**: it is not a
  sandbox, it grants no privilege you did not already have, and its graph output
  is data, never instructions to follow. If a spec line, a code comment or a
  review note lives in a repo you graph, treat anything the graph hands back as
  untrusted text, never as a command. The document names how to report a
  suspected vulnerability privately (GitHub private security advisories, initial
  response within 5 working days) and is linked from the README and CLAUDE.md.

- **A note where you wire it in.** The integration guide
  (`docs/aspark-integration.md`) now carries the same "graph output is data, not
  instruction" reminder at the point where you copy the gate blocks, with a link
  to `SECURITY.md`.

### Changed

- **Pointing a tool at something that isn't a repository now fails fast and
  clearly, instead of hanging or quietly wandering off.** Every one of the nine
  tools (build and the eight queries) now checks that the target is actually a
  repository — it holds a `.git`, a `.spark/`, or an aspark-graph you already
  built there — before doing any work. If it isn't, the CLI prints one line
  naming the path and the rule and exits non-zero, and the MCP tool returns a
  clean `{"found": false, "reason": "outside_confinement", …}` result. Nothing
  is written into a directory that gets refused. Real repositories — including
  git worktrees and submodules (where `.git` is a file), `.spark/`-only trees,
  and directories reached through a symlink — behave exactly as before. If you
  run aspark-graph the documented way (from its own checkout, passing your
  target as `repo`), nothing you do today changes.

- **The MCP `reason` field can now say `outside_confinement` or `too_large`.**
  These are additive; existing consumers that branch on `found` are unaffected.

- **The README and CLAUDE.md are now honest about writes.** They state that
  `build_graph` **writes** `<target>/.aspark-graph/` while the other eight tools
  only read, and the "disposable read model" phrasing is qualified so it clearly
  describes the graph artifact, not the server surface. Both link to
  `SECURITY.md`.

### Fixed

- **A build could hang forever on the wrong target.** Aimed at your home
  directory or the filesystem root, a build used to try to walk everything and
  silently stall. Now an oversized target is refused before any parsing begins,
  with a message naming the limit and the count it stopped at, and no partial
  graph is written — a mistake costs you a one-line message instead of a killed
  process.

- **A single huge file no longer stalls a build.** A source file larger than
  5 MB (typically generated or minified code) is recorded as an unrecognized
  file and skipped without ever being read into memory; the build finishes
  normally and its summary reports how many files were skipped for size.

- **A self-referential symlink no longer sends a build into an infinite loop.**
  A directory that links back to one of its own ancestors now builds to
  completion and returns a result.

---

## 4. Release Actions

**All outward-facing actions are PENDING — awaiting the user's explicit go.**
Nothing below has been executed. Consistent with the `incremental-builds`
prepare precedent (commit and tag both deferred until the go), **no commit and
no tag have been created** during this prepare pass — a local tag is cheap to
delete but is created here only after authorization, alongside the commit it
names.

### Pending commands (execute in order, after the user's go)

| # | Action | Outward-facing? |
|---|---|---|
| 1 | Bump `pyproject.toml` version `0.5.0` → `0.6.0` | no (local) |
| 2 | Regenerate `uv.lock` | no (local) |
| 3 | Update `CLAUDE.md` — add the `security-posture/` trail entry and set "Current shipped version: 0.6.0" | no (local) |
| 4 | Stage the feature files + version bump + `uv.lock` + `CLAUDE.md` + `.spark/security-posture/` | no (local) |
| 5 | Create the release commit | no (local) |
| 6 | Create the local tag `v0.6.0` | no (local) |
| 7 | Push `main` to `origin` | **YES** |
| 8 | Push tag `v0.6.0` to `origin` | **YES** |
| 9 | Create the GitHub Release | **YES** |

```bash
export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"

# 1. Bump the version
sed -i '' 's/^version = "0.5.0"/version = "0.6.0"/' pyproject.toml

# 2. Relock (keeps uv.lock's own aspark-graph version in step — the go-rust learning)
uv lock

# 3. Update CLAUDE.md — two edits:
#    a) append after the go-rust-support trail line:
#       `security-posture/` (v0.6.0 — repo-confinement rule (all 9 tools refuse a
#       non-repo target), build bounds (entry-count + 5 MB per-file cap + symlink-cycle
#       termination), SECURITY.md documenting the trust boundary and six non-guarantees).
#    b) change "Current shipped version: 0.5.0." → "Current shipped version: 0.6.0."

# 4. Stage exactly the release content (NOT .spark/BACKLOG.md — see §1 note)
git add \
  pyproject.toml uv.lock CLAUDE.md README.md docs/aspark-integration.md \
  SECURITY.md \
  src/aspark_graph/confinement.py \
  src/aspark_graph/build.py \
  src/aspark_graph/cli.py \
  src/aspark_graph/queries.py \
  src/aspark_graph/server.py \
  tests/conftest.py \
  tests/test_build.py \
  tests/test_cli_mcp_parity.py \
  tests/test_build_bounds.py \
  tests/test_confinement.py \
  tests/test_confinement_cli_mcp.py \
  tests/test_confinement_guards.py \
  tests/test_security_doc.py \
  .spark/security-posture/

# 5. Verify the staged set before committing
git status

# 6. Release commit
git commit -m "$(cat <<'EOF'
feat(security-posture): ship v0.6.0 — repo confinement, build bounds, SECURITY.md

Every one of the nine tools now refuses a target that is not a repository
(.git / .spark/ / a prior .aspark-graph/graph.json) before doing any work:
CLI one-line + exit 1, MCP {"found": false, "reason": "outside_confinement"}.
The unbounded-walk hang is fixed by an entry-count bound (refuses oversized
targets before parsing) and a 5 MB per-file cap (oversized files recorded
unparsed, never read); symlink cycles terminate. SECURITY.md states the trust
boundary and six honest non-guarantees, checked by a doc harness. Additive
only: reason gains two values, found:false unchanged; mcp>=1.12,<1.20 and all
deps untouched; accepted repos build byte-identically to v0.5.0. 275 + 2 slow
green.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

# 7. Local tag
git tag -a v0.6.0 -m "aspark-graph 0.6.0 — repo confinement, build bounds, SECURITY.md"

# 8. Push main   [OUTWARD-FACING — requires user go]
git push origin main

# 9. Push tag    [OUTWARD-FACING — requires user go]
git push origin v0.6.0

# 10. GitHub Release   [OUTWARD-FACING — requires user go]
gh release create v0.6.0 \
  --title "aspark-graph 0.6.0 — repo confinement, build bounds, SECURITY.md" \
  --notes "See .spark/security-posture/release-notes.md for the full changelog."
```

There is **no PyPI publish step** — the package remains install-from-source
only; the README carries no `uvx`/PyPI claims (still Out of Scope).

### Post-release smoke check (run after push + Release creation)

To be run against the **published** state (remote `main` HEAD + the `v0.6.0`
tag), not the local pre-push tree — following the `go-rust-support` precedent:

```bash
export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"
git ls-remote --tags origin v0.6.0            # tag is on the remote, matches HEAD
gh release view v0.6.0                          # Release visible with the right title
git log --oneline -1                            # main at the release commit
# fresh clone of the tag → clean venv → wheel install → confirm no cryptography/joserfc
git clone --branch v0.6.0 <remote-url> /tmp/aspark-smoke && cd /tmp/aspark-smoke
uv sync --extra dev
uv run pytest -q                                # must still be 275 passed + 2 deselected
uv run aspark-graph build .                     # builds this repo (a marked dir)
uv run aspark-graph build /tmp                  # MUST refuse: exit 1, one clean line
uv run aspark-graph query staleness --repo .    # graph current
uv run aspark-graph query find_nodes --repo . confinement   # the shipped feature's own code is live
# then: rm -rf /tmp/aspark-smoke
```

The core flow to confirm alive: the CLI responds, a real repo still builds and
answers, and the released feature — a non-repo target being refused cleanly —
works end-to-end from a freshly cloned, freshly installed copy of the exact
published commit.

---

## 5. Rollback Path

This release is additive and backwards-compatible from the documented install,
so rollback risk is low. There is no schema change to `graph.json`, no
migration, and no external service. The one behaviour that reverts on rollback:
a non-repo target would once again walk/hang instead of refusing, and the build
bounds would be gone — i.e. rollback re-opens the very bug US-3 fixes, which is
worth stating before going forward.

**Before push (local only — if the go is withdrawn after the commit/tag):**

```bash
git tag -d v0.6.0
git reset --mixed HEAD~1   # NOT --hard — the working tree also carries the
                            # untracked .spark/BACKLOG.md (out of scope, §1).
                            # --mixed unwinds only the release commit and
                            # re-stages nothing; untracked files are untouched.
```

**After push (if v0.6.0 has gone out and must come back):**

```bash
# Delete the remote tag
git push origin --delete v0.6.0

# Revert the release commit on the remote (new revert commit — preserves history)
git revert HEAD --no-edit
git push origin main

# Remove the GitHub Release
gh release delete v0.6.0 --yes

# Callers who pinned aspark-graph>=0.6.0 for the confinement behaviour would
# pin back to 0.5.0 — install-from-source, so this means checking out the
# v0.5.0 tag/commit. There is no published package to unpublish.
```

Because the change is additive, a rollback loses only the confinement refusal,
the build bounds and `SECURITY.md` — it cannot corrupt or regress
`story_trace`/`impact` results for accepted repos, whose graphs are
byte-identical to v0.5.0 (AC-3.4/NFR-2, verified above).

---

## 6. Learnings (Keep!)

### What went well

- **Marking the test fixtures instead of shipping a test-only bypass (plan R1)
  is the standout.** The spec *accepted* an internal bypass (Q3/A11); the plan
  reversed that at the gate and instead made every `tmp_path` a marked repo (an
  empty, graph-neutral `.spark/`), so the whole suite exercises the shipped
  code path. This retired A11 entirely: there is no second code path to police,
  so AC-1.10/NFR-9 are true **by construction** rather than by a guard test
  chasing an escape hatch. Reversing a user-resolved decision is expensive to do
  right; raising it explicitly at the plan gate (R1) and recording it as the
  first rejected alternative made it a decision the next reader can see, not an
  oversight.

- **Reusing the existing `GraphNotBuiltError` exception→adapter seam made
  CLI↔MCP refusal parity free.** Confinement is "the same problem again" as the
  already-solved unbuilt-graph error, so it got the same shape: raise once in
  the shared module, render one stderr line in `cli.py` and one dict in
  `server.py`. The parity test only needed new rows, not a new test — parity is
  structural, not policed.

- **A `SECURITY.md` written to be *checked*, not to *impress*.** The spec's
  refusal to oversell (confinement is a "shape check, not a sandbox"; it "removes
  no privilege the caller did not already have") plus the anti-overclaim doc
  harness — six named non-guarantees *and* a keyword denylist outside that
  section — turned honesty into an automated, falsifiable property. NFR-5 is
  candid that both checks are defeatable by rephrasing, so the human read in
  `/peer-review` still carried the final weight; the harness catches regression,
  not adversarial authorship, and says so.

- **The `close-the-loop:T9` inferred-edge loss was diagnosed as *correct* before
  review had to.** The increment sweep noticed four `inferred implements` edges
  vanish and traced it to `inference.py`'s F1 disambiguation reacting correctly
  to this feature also having a `T9` — honest absence over a wrong cross-feature
  link, exactly as the CLAUDE.md non-negotiable specifies. Documented in plan §6
  so review confirmed rather than re-derived it. Pre-explaining a surprising
  diff is cheaper than having each downstream reader rediscover it.

- **Two prior-cycle learnings actually fired this time.** The lockfile
  self-version check and the unpublished-release guard (both raised as
  CLAUDE.md candidates in `go-rust-support`) were run at pre-flight: `uv.lock`
  was in step with `pyproject.toml`, and no earlier release was stuck in
  `preparing`. Learnings that get re-applied are learnings that stuck.

### What we'd do differently

- **AC-2.8 (GitHub private vulnerability reporting enabled) is verifiable by no
  agent and no test — only by a human in the Security tab.** T7 handled it as a
  user-owned task and the plan records the maintainer confirmed it, which is the
  right shape, but it remains the one gate item with zero automated or
  agent-visible evidence. Any future external-side deliverable (a GitHub
  setting, a DNS record, an enabled integration) should be closed the same way:
  a user-owned task whose done-ness is recorded as an explicit human statement,
  never inferred. Flagged as an open item to eyeball, below.

- **The F1 Nit (build-summary double-count) was accepted as-is.** A size-skipped
  file lands in both `report.unparsed` and `report.size_skipped`, so the summary
  can look like it names two files when it means one. Harmless to every AC, so
  correctly not fixed on the release commit — but a genuine one-line follow-up
  (exclude size-skipped nodes from `unparsed`, or reword the summary) rather
  than permanent cosmetic debt.

- **A stray, untracked `.spark/BACKLOG.md` is sitting in the working tree** —
  the same "stray working-tree file" pattern `go-rust-support` flagged for
  `README.md`/`docs/*.png`. It is out of scope for this release and is not
  staged, but it should be triaged rather than left to accrete across cycles.

### Patterns worth reusing (CLAUDE.md / memory candidates)

1. **Mark the environment, don't bypass the guard.** When a cross-cutting rule
   must hold for the whole test suite, prefer making the test environment
   *satisfy* the rule (here: a graph-neutral `.spark/` marker on every
   `tmp_path`) over adding a test-only escape hatch. It removes the
   second-code-path risk instead of policing it, and every existing test then
   becomes evidence for the new rule. Candidate under "Testing patterns."

2. **Reuse an existing exception→adapter rendering seam for any new refusal.**
   A new domain refusal that raises in the shared module and is rendered once
   per adapter inherits CLI↔MCP parity for free — the parity test only needs new
   rows. Candidate under "Architecture patterns" (it reinforces the existing
   thin-adapter non-negotiable).

3. **The anti-overclaim doc harness: N named entries + a keyword denylist
   outside a section.** For any trust/security document, assert a fixed set of
   named claims are present *and* that overclaiming words (sandbox, isolat,
   prevent, protect, contain) appear nowhere outside the explicit
   non-guarantees section — falsifiable regression cover that keeps the document
   honest as it is edited. Candidate under "Documentation patterns."

4. **Prove determinism against actual pre-change code, not just a double-build.**
   The `git stash push -u` / build / `git stash pop` / rebuild comparison (plan
   §6) is the strongest available AC-3.4/NFR-2 evidence — old code vs. new code
   on a fixed fixture, not new code vs. itself. Candidate under "Testing
   patterns."

5. **(Re-affirm, from `go-rust-support`.)** The lockfile self-version check and
   the unpublished-release guard both earned their keep again — they belong in a
   written release pre-flight checklist in CLAUDE.md if they are not there yet.

---

## ✅ KEEP GATE

*Prepare-only pass: publish, smoke and status remain open until the human's go.*

- [x] Both gates checked: review `passed`; QA gate override recorded with authorizer, quoted policy, reason and substitution
- [x] Pre-flight run fresh on the release working tree — not copied from an earlier report (275 + 2 slow green; byte-identical rebuild; live refusal; clean-env wheel install; 9-tool `serve` boot; no lockfile drift; no tag collision; no stale `preparing` release)
- [x] Version `0.6.0` justified (minor: new behaviour + new public module + new document, zero breaking change)
- [x] Changelog written in user-facing language — no commit hashes, ticket IDs or internal jargon
- [x] Rollback path written before any outward-facing action
- [x] Learnings written: what went well, what to do differently, patterns to persist
- [ ] Release commit + local tag created (PENDING — deferred to after the go, per the prepare-only precedent; exact commands in §4)
- [ ] Outward-facing actions executed with explicit user authorization (PENDING — push main, push tag `v0.6.0`, create GitHub Release; all listed in §4)
- [ ] Post-release smoke confirmed (PENDING — commands in §4, run against the published state)
- [ ] Status set to `released` (PENDING — currently `preparing`)

### What I need back (the go/no-go, and two smaller items)

1. **Go / no-go to publish v0.6.0.** If go: I will run steps 1–10 in §4 in
   order (version bump → relock → CLAUDE.md → commit → local tag → push main →
   push tag → GitHub Release), then the post-release smoke check, then set the
   status to `released`.
2. **Confirm AC-2.8 by eye.** Private vulnerability reporting on the GitHub repo
   (Settings → Security → "Private vulnerability reporting") is the one gate
   item no agent can verify. The plan records the maintainer enabled it (T7);
   please confirm the Security tab shows a reachable "Report a vulnerability"
   form before or at the go, since `SECURITY.md` names that channel.
3. **Triage the stray `.spark/BACKLOG.md`.** It is untracked, out of scope for
   this feature, and deliberately not in the staged set. Commit it on its own,
   move it, or discard it — but it should not keep riding along in the working
   tree across cycles.
