# Review Report: pypi-publish

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | Working-tree diff vs `HEAD` (2d5c089), `.spark/pypi-publish/plan.md` |
| **Status** | `passed` |
| **Date** | 2026-07-28 |

## 1. Scope

Reviewed the uncommitted working-tree diff vs `HEAD` (2d5c089): `README.md`,
`CLAUDE.md`, `tests/test_readme.py`, and new `.spark/pypi-publish/`
(spec.md, plan.md, release-notes.md). **Review scope is T1–T5 only** — the
`/increment`, Review-provable half. T6–T10 are `/go-live`, human-executed, and
correctly still `todo` by the plan's own §1 architecture decision (upload before
published-README commit); not a gap. `.spark/BACKLOG.md` is a pre-existing
untracked file, out of scope. No `src/` code changed, so structural blast radius
is empty by construction (plan §2 graph query re-confirmed: docs are
`unknown_files`, `test_readme.py` has exactly 4 code entities). Not
Review-provable and correctly deferred: the live upload / 404→version flip
(AC-1.1–1.3, 1.5, 1.6, 1.8), live PyPI-page render (AC-2.6 live leg).

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ | Marked `done` (manual dual-venv smoke). Independently spot-checked: `uv build` succeeds → `py3-none-any` wheel; metadata name/version/entry-point/license correct; `mcp<1.20,>=1.12` cap honored; five grammar pins + core all `==`; no `cryptography`/`joserfc` in direct deps. Full resolved-tree + serve smoke is T1's manual/T10 leg. |
| T2 | ✅ | Install leads with `uvx`/`pip install`; "not yet published" gone; `claude mcp add` uses `uvx`; from-source relocated to `## Development`; determinism-boundary prose added; logo + internal links switched to absolute GitHub URLs. |
| T3 | ✅ | Three named functions inverted correctly; `_install_section` helper unchanged; `test_link_conventions.py` byte-identical (zero diff). Full suite green. |
| T4 | ✅ | CLAUDE.md deferral note resolved; no version number asserted; no contradiction with "Current shipped version: 0.6.0". |
| T5 | ✅ | Rollback path complete: yank / version-burn / yank≠delete / maintainer-only / AC-1.8 cross-ref kept distinct. One factual inaccuracy fixed (F1). |
| T6–T10 | — | Correctly `todo` by design (go-live, human-executed). Not reviewed, not a gap. |

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Minor | `.spark/pypi-publish/release-notes.md:29` | Rollback step 1 said yank could be done via "`twine`/`uv`'s equivalent" — neither tool has a yank command; yank is a PyPI web-UI/API action. At the moment the rollback is needed (under pressure, version already burned) this sends the maintainer hunting for a command that doesn't exist. Fixed: named the web-UI path (Options→Yank) explicitly and stated it is not a `twine`/`uv publish` operation. | fixed |
| F2 | Nit | `README.md` / `CLAUDE.md` (working tree) | Both now assert present-tense "published on PyPI" while PyPI returns 404. This is **not** a finding against the code — it is the plan's deliberate design (§1, R2): the claim is confined to the **uncommitted** working tree and only lands in public history at T9, after T8's live upload. Recorded here so the honesty question is answered explicitly, not assumed. | open (by design) |

## 4. Requirements Traceability

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-2.1 | `README.md` Install section | ✅ leads with `uvx`/`pip install`; "not yet published" removed |
| AC-2.2 | `README.md` Install `claude mcp add` | ✅ `uvx aspark-graph serve`, not `uv run --directory` |
| AC-2.3 | `tests/test_readme.py` 3 fns | ✅ present-commands + "not yet published" absent (whole README) + from-source under Development + `uvx` in mcp line; `test_link_conventions.py` untouched; green |
| AC-2.4 | git state | ✅ published claims uncommitted; committed HEAD README still honest; PyPI 404 |
| AC-2.5 | `README.md` `## Development` | ✅ `git clone`→`uv sync`→`uv run build` relocated |
| AC-2.6 (static) | logo `<picture>` + `SECURITY.md`/`docs/*` links | ✅ absolute `raw.githubusercontent.com`/`github.com/blob/main` URLs, owner `a-lottes/aSPARK-graph` matches remote, target files exist; no other relative links remain |
| AC-3.1 | `README.md` Design guarantees | ✅ pin rationale + `uv.lock` stated in user language |
| AC-3.2 | same | ✅ boundary stated: fixed grammar set; bump = deliberate, changelog-documented, version-bumped |
| AC-3.3 | vs `pyproject.toml` | ✅ "five grammars (Python, TypeScript, Java, Go, Rust) + core" matches the 5 grammar pins + `tree-sitter==` exactly — falsifiable and true |
| AC-4.1/4.2/4.3 | `release-notes.md` §0 | ✅ yank/burn/≠delete, maintainer-only, AC-1.8 kept distinct (post-F1 fix) |
| AC-5.1 | `CLAUDE.md` Out of scope | ✅ deferral note resolved (prepared for go-live) |
| AC-5.2 | `README.md` | ✅ no remaining unpublished/from-source-only claim |
| NFR-1/2 | wheel metadata + pins | ✅ `py3-none-any`, `==` pins intact, double-build test green, direct deps clean (crypto absent) |
| NFR-3 | git state | ✅ no published claim in public history; 404-honest |
| NFR-4 | full suite | ✅ 275 passed, 2 deselected |
| NFR-5 | `release-notes.md` / task split | ✅ upload is user-owned (T6/T8); no credential in any file/agent path |
| NFR-7 | (unchanged code) | ✅ no code touched; clean-error behavior unchanged |

Release-only (correctly deferred, not certifiable here): AC-1.1–1.3, 1.5, 1.6,
1.8, AC-2.6 live leg.

## 5. What Was Checked

- [x] Correctness: doc content, test inversions, rollback path match the ACs
- [x] Non-functional: honesty ordering, determinism pins, mcp cap, no-credential guardrail
- [x] Error handling: N/A — no code changed
- [x] Security: no secret/credential in any file; upload is human-owned
- [x] Tests: 3 inversions assert specific substrings (not tautologies), green; `test_link_conventions.py` untouched; full suite 275 passed
- [x] Readability: prose is clear; URLs resolvable and correct

## 6. Verdict

**Passed.** T1–T5 are complete and correct, and — the thing that matters most in
a doc-honesty cycle — the install-honesty rule is genuinely honored, not merely
asserted. The committed HEAD README still says "not yet published"; PyPI returns
404; every `uvx`/`pip install` claim lives only in the uncommitted working tree
and will enter public history only at T9, after T8's live upload. The three
`test_readme.py` inversions assert the specific published-state facts AC-2.3
demands and fail if the README regresses; `test_link_conventions.py` is
byte-identical. The determinism-boundary prose names five grammars + core that
match `pyproject.toml` exactly (the earlier "three→five" self-correction is
confirmed independently). All relative image/link paths are now resolvable
absolute GitHub URLs against the real `a-lottes/aSPARK-graph` remote. The T5
rollback path is complete, maintainer-only, and keeps the completed-but-wrong
(yank) case distinct from the incomplete-upload (AC-1.8) case — its one factual
slip (a non-existent `twine`/`uv` yank command) is fixed. Scope discipline holds:
no `src/`, no `.github/`, no premature version bump. No Blockers, no Majors; one
Minor fixed directly, one by-design honesty note recorded for transparency. The
increment leaves nothing that makes T6–T10 unsafe or ambiguous to execute later.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`.*

- [x] No open Blocker findings
- [x] No open Major findings (or explicitly waived by the user, with reason recorded here)
- [x] Every Must AC traces to implementing code; no constitution non-negotiable violated *(release-only Must ACs correctly deferred to /go-live per plan §1)*
- [x] All plan deviations documented and accepted *(none; T6–T10 deferred by design)*
- [x] Test suite runs green *(275 passed, 2 deselected)*
- [x] Status set to `passed`

---

## Re-Review — sdist packaging fix (2026-07-28)

**Trigger.** After this report passed, `/go-live`'s T7 pre-flight built a real
sdist at the 0.7.0 bump and found it carried `.claude/settings.local.json` +
a 50 MB `.claude/worktrees/` tree — untracked, ignored only via the maintainer's
global git excludes and `.git/info/exclude`, neither of which hatchling reads.
The Release Manager routed it back through `/increment`. Fix (recorded as a
Deviation in `plan.md`): a `[tool.hatch.build.targets.sdist]` `include` allowlist
in `pyproject.toml` + a new slow-marked regression test `tests/test_packaging.py`.
This section verifies that fix independently; it does not disturb the T1–T5 verdict.

### What was independently verified (not merely re-read)

- **Rebuilt both artifacts myself** (`uv build`). The `.claude/` tree still
  physically exists in the working copy and is still ignored only via global
  excludes / `.git/info/exclude` (confirmed: `git check-ignore .claude/…`,
  `.gitignore` has no `.claude`), so the build ran under the *exact* conditions
  that produced the bug. The resulting sdist manifest (`tar tzf`) contains **no
  `.claude/` anywhere, no top-level `.spark/`, no `docs/`, `CLAUDE.md`,
  `SECURITY.md`, `uv.lock` or `.python-version`** — only `/src`, `/tests` (incl.
  `tests/fixtures/sample_repo/…`, needed by the suite), `README.md`, `LICENSE`,
  `pyproject.toml`, plus hatchling's auto `PKG-INFO` + `.gitignore`.
- **Wheel re-verified, not assumed.** Wheel manifest holds only
  `aspark_graph/**` modules + `.dist-info` (name/version/entry-point/license
  intact); no `.claude`, no tests. The wheel-scoping claim (`packages=[...]`)
  is confirmed true, not taken on faith.
- **Allowlist shape is correct and complete.** An allowlist (not exclude list)
  is the right call — immune to any future untracked/locally-ignored path. It
  excludes nothing a from-sdist consumer needs: `/src` + `pyproject.toml`
  (with the `[dev]` extra) build and test; `tests/fixtures/` is reachable under
  `/tests`, so fixture-dependent tests run. `uv.lock` absence is standard and
  correct for an sdist (ranges, not the lockfile, govern a downstream build).
- **The test is a real integration test, and it catches the original bug.** It
  shells out to `uv build --sdist`, opens the real tarball, and checks actual
  members (not config text — non-tautological). Proof of teeth: I temporarily
  removed the allowlist block and re-ran it — it **failed**, naming
  `['.claude', '.python-version', '.spark', 'CLAUDE.md', 'SECURITY.md', 'docs',
  'uv.lock']` and tripping the explicit `.claude`/`.spark` guards. Restored the
  block; green again.
- **Suites green fresh.** `uv run pytest` → 275 passed, 3 deselected;
  `uv run pytest -m slow` → 3 passed (bench + MCP transport + new packaging test).
- **No scope creep.** `git diff HEAD` since the last review is exactly:
  `pyproject.toml` (version 0.6.0→0.7.0 + sdist block), `uv.lock` (version),
  new `tests/test_packaging.py`, and `plan.md` Deviations. **No `src/` change.**
- **Version/honesty sanity.** `0.7.0` lives only in `pyproject.toml`/`uv.lock`;
  it does not leak into `README.md`/`CLAUDE.md`. Committed HEAD README is still
  404-honest ("Until aspark-graph is published … the from-source path … is the
  supported install"); the `uvx`/`pip install` claims remain uncommitted
  working-tree only. The honesty ordering from the first pass is intact.

### Re-review findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| — | — | — | No new findings. Fix is sound, complete, and covered by a test that provably fails on the pre-fix config. | — |

### Re-review verdict

**Still passed — the fix is sound and complete.** The sdist packaging gap is
genuinely closed: a real rebuild under the same untracked-`.claude/` conditions
that caused the bug now produces a clean manifest carrying only the allowlisted
source, tests, and metadata — no `.claude/`, no top-level `.spark/`, wheel
unaffected. The allowlist is the correct shape (immune to future stray paths by
construction) and excludes nothing a downstream sdist build legitimately needs.
The new `tests/test_packaging.py` is a true build-and-inspect regression test,
not a config re-read, and I proved it fails on the pre-fix `pyproject.toml` —
naming `.claude` and `.spark` explicitly — so this cannot silently regress. Full
and slow suites are green (275 + 3), the change is confined to `pyproject.toml`,
`uv.lock`, the new test, and the plan's Deviations note with zero `src/` drift,
and the install-honesty ordering the first pass certified is untouched. No
Blockers, no Majors, no new findings. The increment is ready to return to
`/go-live`.
