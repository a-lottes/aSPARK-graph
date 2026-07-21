# Release Notes: robustness (v0.4.1)

| | |
|---|---|
| **Phase** | Release |
| **Owner** | Release Manager (`/go-live`) |
| **Status** | `released` |
| **Date** | 2026-07-18 |
| **Version** | 0.4.1 |
| **Previous version** | 0.4.0 |
| **Bump level** | patch — backwards-compatible correctness fix to an existing query |

---

## Post-Release Close-Out Note (added 2026-07-21)

This release was fully prepared and gated on 2026-07-18, but the local
release commit (`d3c5ff5`) and local tag `v0.4.1` were never pushed at the
time — this note's own status was left at `preparing` for three days while
a subsequent, unrelated feature (`go-rust-support`, v0.5.0) was built,
reviewed, and prepared on top of it.

It shipped on **2026-07-21**, bundled with `go-rust-support` v0.5.0 in a
single `git push origin main` (explicit user authorization) that carried
both `d3c5ff5` and `31b2a0d` in one fast-forward push, followed by
`git push origin v0.5.0`. **Note: the local `v0.4.1` tag itself was not
pushed in this ceremony** — only the `v0.5.0` tag push was explicitly
authorized; `git push origin v0.4.1` remains a pending, separately-
authorizable action (the commit `d3c5ff5` is on the remote `main` branch
regardless, since tags and branch history are independent — the code is
published, but there is no `v0.4.1` ref on the remote to point at it yet).
Both releases had independently passed their own gates and pre-flight
checks before the bundled push; bundling changed only the timing of
publication, not the gating. See `.spark/go-rust-support/release-notes.md` for the bundled
push's full record and the shared post-release smoke check (both releases
are verified live at the same post-push commit).

No content below this note was changed — the original pre-flight results,
changelog, and learnings from 2026-07-18 stand as written.

---

## Gate Status

| Gate | Status | Notes |
|---|---|---|
| Review (`review-report.md`) | passed | 2026-07-18; no Blockers, no Majors; all 3 Minors/Nits fixed pre-merge |
| QA (`qa.md`) | **override — N/A** | See gate override record below |

### QA Gate Override Record

- **Authorizer:** Project CLAUDE.md standing policy (committed to the repo, reviewed by the project owner).
- **Reason:** `aspark-graph` is a headless CLI/MCP tool with no visual or browser surface. The `/demo-day` ceremony is structurally inapplicable. The QA-equivalent — full test suite (165 passed, 2 deselected default; 2 passed slow), `serve` boot, byte-identical build, real-repo staleness and `find_nodes` queries — was performed in `/peer-review` and independently repeated at release time (see Pre-Flight Results below). This is not a skip; it is a gate substitution documented by the project's own CLAUDE.md. CLAUDE.md: "Overriding the QA gate at `/go-live` is legitimate here, but record the authorizer + reason in the release report — never a silent skip."

---

## Version Justification

Current: `0.4.0`. Proposed: `0.4.1` (semver patch).

Rationale: Both changes in this release are backwards-compatible.

- The `find_nodes("")` guard fixes a silent correctness defect (full-graph return on empty query → empty-result return). Callers that previously avoided empty queries are unaffected. Callers that accidentally passed an empty query now receive an honest empty result instead of a misleading full-graph match — this is a correction, not a breaking change.
- The MCP stdio transport smoke test (`tests/test_mcp_transport.py`) is a new test file only. No new CLI command, no new MCP tool, no public API change.

No minor version bump is warranted: no new user-facing capability was added. The patch bump is correct.

---

## Changelog

### Fixed

- Searching for nodes with an empty query string no longer silently returns every node in the graph. It now returns an empty result (`count: 0, nodes: []`), so dynamically constructed queries that accidentally produce an empty string are no longer indistinguishable from a valid full-match result.

### Added

- A transport-level smoke test now verifies that `aspark-graph serve` can start, accept a JSON-RPC request over stdin, and return a well-formed response — catching any MCP SDK wire-format regression before it reaches a live environment. The test runs under `uv run pytest -m slow` and does not slow down the default suite.

---

## Pre-Flight Results

All checks run fresh on the release working tree (commit pending; working tree = `61d6e88` + feature diff).

| Check | Command | Result |
|---|---|---|
| Working tree | `git status` | 3 modified files, 2 untracked (all feature files — expected) |
| Default suite | `uv run pytest -q` | **165 passed, 2 deselected** in 23.94 s |
| Slow suite | `uv run pytest -m slow -q` | **2 passed, 165 deselected** in 9.97 s |
| Build | `uv run aspark-graph build .` | Built: 402 code entities, 235 artifact entities, 68 inferred links; 4 re-parsed, 41 cached — no error |
| Staleness | `uv run aspark-graph query staleness --repo .` | `{"stale": false, "changed": [], "missing": [], "files_checked": 45, "advice": null}` |
| Empty-query fix | `uv run aspark-graph query find_nodes --repo . ""` | `{"count": 0, "nodes": [], "query": "", "type": null}` — guard confirmed live |

All six checks passed.

---

## Release Commit

### Files staged

- `src/aspark_graph/queries.py` — `find_nodes("")` empty-query guard (+2 lines)
- `tests/test_navigation.py` — 3 new unit tests (AC-1.1/1.2/1.5)
- `tests/test_cli_mcp_parity.py` — 1 new parity test (AC-1.3/1.4)
- `tests/test_mcp_transport.py` — new MCP stdio transport smoke test (US-2)
- `pyproject.toml` — version bumped from `0.4.0` to `0.4.1`
- `CLAUDE.md` — trail entry added, shipped version updated, test count updated
- `.spark/robustness/` — spec, plan, review report, release notes (all new)

### Commit message

```
feat(robustness): ship v0.4.1 — find_nodes guard + MCP transport smoke test

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

### Local tag

`v0.4.1` — created locally on the release commit; not yet pushed.

---

## Pending Outward-Facing Actions (awaiting explicit go)

The following commands will be run **only after explicit user authorization**:

```bash
# 1. Push the release commit to the remote
git push origin main

# 2. Push the local tag
git push origin v0.4.1
```

There is no PyPI publish step — the package is install-from-source only. The README contains no `uvx`/PyPI claims.

---

## Rollback Path

The release is install-from-source only (no PyPI publish to unwind).

To roll back after a push:

```bash
# Delete the remote tag
git push origin --delete v0.4.1

# Revert the release commit on the remote (creates a new revert commit — preserves history)
git revert HEAD --no-edit
git push origin main
```

To roll back before push (local only):

```bash
git tag -d v0.4.1
git reset --hard HEAD~1
```

---

## Learnings

### What went well

- The three-gate review caught three non-trivial test-hardening issues (F1/F2/F3) in the transport smoke test: missing stderr drain on timeout (hard to diagnose), potential 64 KB deadlock risk, and unclosed file handles. All fixed before the gate closed. The review process is working exactly as intended for this class of change.
- The QA gate override process is clean: the CLAUDE.md policy means the release manager never needs to make a judgment call — the rule is pre-approved and documented in the source tree itself. Zero ambiguity.
- The `find_nodes("")` guard is a textbook minimal fix: two lines, single-sourced at the query layer, zero adapter changes, parity preserved by construction. The correctness proof is cheap.
- Falsifiability probes in the review (commenting out the guard; changing `id==2` to `id==999`) confirmed both the correctness tests and the transport test are genuine, not tautologies. This is a pattern worth institutionalizing.

### What to do differently

- The R1 mitigation (surface stderr on transport test failure) was specified in the plan but not implemented in the initial delivery. It was caught by the reviewer, but it would have been better to check plan mitigations line-by-line before declaring a task complete. A pre-review self-check step ("re-read the plan's risk mitigations and confirm each is in the code") would prevent this class of omission.
- The transport test relied on the reviewer to catch the 64 KB deadlock risk (F3 — `stderr=PIPE` never drained while blocked on `stdout.readline()`). This is a subtle but well-known subprocess pitfall. Worth adding to the team's internal checklist for any test that opens `stderr=PIPE`.

### Patterns to persist (CLAUDE.md / memory candidates)

1. **Subprocess test checklist.** Any test using `subprocess.Popen` with `stderr=PIPE` must drain stderr concurrently (thread or `communicate()`), close both handles explicitly after `wait()`, and surface stderr content in assertion failure messages. The three F1/F2/F3 findings from this review are the canonical example.

2. **Plan-to-delivery self-check.** Before opening a review, re-read the plan's "Risks & Mitigations" section and confirm each mitigation is present in the code. A one-minute check prevents a round-trip.

3. **Falsifiability probes as a release-readiness signal.** If a reviewer cannot break a test by reverting the code it guards, the test is not load-bearing. The robustness cycle used two explicit probes (A and B) — this should be a required step in every `/peer-review` checklist entry for new tests.

---

## KEEP GATE

- [x] Both gates checked: review `passed`; QA gate override recorded with authorizer and reason
- [x] Pre-flight run fresh on the release working tree — not copied from an earlier report
- [x] Version `0.4.1` justified (patch: backwards-compatible correctness fix + tests only)
- [x] Changelog written in user-facing language — no commit hashes, no ticket IDs, no internal jargon
- [x] Release commit prepared with exact file list; local tag `v0.4.1` created
- [x] Rollback path written before any outward-facing action
- [x] Outward-facing actions executed (partial): `git push origin main` on 2026-07-21 carried `d3c5ff5` to the remote (verified: `git log` on origin/main shows it, `git ls-remote --tags origin` confirms `main` is at `31b2a0d` which has `d3c5ff5` as its parent). **`git push origin v0.4.1` (the tag itself) was NOT executed** — only `git push origin v0.5.0` was explicitly authorized in this ceremony; the local `v0.4.1` tag still needs its own explicit go to publish. Flagged as an open item below.
- [x] Learnings written: what went well, what to do differently, patterns to persist
- [x] Status updated to `released` — shipped 2026-07-21, bundled with go-rust-support v0.5.0 push
- [x] Post-release smoke confirmed — see `.spark/go-rust-support/release-notes.md` post-release smoke check (shared, same push, same commit)
