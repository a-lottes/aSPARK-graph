# QA Report: coverage-current-names

| | |
|---|---|
| **Phase** | Review (hands-on) |
| **Owner** | QA Tester (`/demo-day`) |
| **Input** | Release candidate for v0.7.1 (branch `fix/coverage-current-names` from `1b62da0`, uncommitted tree), `.spark/coverage-current-names/spec.md` |
| **Status** | `passed` |
| **Round** | 1 |
| **Date** | 2026-09-26 |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Verdict:** Yes. Every Must AC and all three NFRs pass hands-on on the installed RC wheel over CLI and live MCP. Byte-identity to `ad83eae` holds on 7 legacy-only trails and on this repo's own trail. The v0.7.1 regression set, Core and steamcore are unchanged.
- **Open:** `none`. Blockers: none. Majors: none. No new bugs this round; B2 and B3 from `current-artifact-names` stay as ruled there (G6, G8), and review F6/F7 (G10) were seen again (see §3).
- **Binding ruling:** §5 Verdict and the gate checklist below
- **On conflict:** the numbered body below wins for everything except `Status`.

## 1. Test Environment

- **Browser:** does not apply. `aspark-graph` is a CLI plus an MCP stdio server with no UI. There is no constitution, so no §8 QA method is declared. The user approved hands-on CLI/MCP QA of the installed RC in its place, following the pattern of `.spark/current-artifact-names/qa-report.md` §1. Nothing was tested by reading source.
- **Artifact under test:** `uv build` of the worktree into scratch (`aspark_graph-0.7.1-py3-none-any.whl` plus sdist), installed into a fresh Python 3.11 venv, and also run via `uvx --from <wheel>`. Its `Requires-Dist` equals `1b62da0`'s `pyproject.toml`, which is unchanged.
- **MCP:** a real `aspark-graph serve` subprocess driven by the `mcp` stdio client, with 9 tools listed. Each scenario was built via the CLI and via `build_graph`; `gate_health` and `get_node` were called both ways.
- **Baselines:** `ad83eae` (clone `scratchpad/base_ad83`, via `uv run --project`) and merged main `1b62da0` (scratch clone, to confirm the crash).
- **Test data (scratch):** 45 generated repos from the v0.7.1 QA generator, pointed at this worktree's fixture. That includes 10 new coverage scenarios: full current, full legacy, only qa.md, none, both qa names, all six names, `reviews.md`, a mix of near-misses, no spec, 4 `AC`-header legacy-only trails (partial, near-miss, 4 features, no spec) and an edge repo (empty feature, evidence-only feature, directory named `qa-notes.md`). Also fresh copies of Core (`e1a0005`) and steamcore (`bf1b3e0`), and an rsync copy of this worktree without `.git`, `.venv`, `.aspark-graph` and `.spark/.guard/`.

## 2. Acceptance Criteria Verification

| AC | Steps performed | Expected | Observed | Result |
|---|---|---|---|---|
| AC-1.1 | Rsync clone of the worktree; `uv run --extra dev pytest`; `git diff --numstat 1b62da0 -- tests/` | all green; PR #2 tests unedited | 328 passed; no tracked test file differs, only the new `test_coverage_current_names.py` is added | ✅ pass |
| AC-1.2 | Built only-qa.md, none, no-spec, only-release, empty and evidence-only feature folders via CLI, MCP and uvx; the same only-qa.md repo on merged main `1b62da0` | no exception; missing kinds in `skipped` | RC: exit 0 everywhere, missing kinds listed in `skipped`. `1b62da0`: `AttributeError: 'NoneType' object has no attribute 'exists'`, so the repair is what fixes it | ✅ pass |
| AC-2.1 | `cov_full_current` (spec, plan, review.md, qa.md, release.md); CLI and MCP `gate_health demo`, `get_node feature:demo` | five kinds recognized (legacy spelling), skipped and near_misses empty, note null | recognized `plan.md, qa-report.md, release-notes.md, review-report.md, spec.md`; `skipped: []`; `near_misses: []`; `coverage_note: null`; the node carries the same coverage | ✅ pass |
| AC-2.2 | `cov_only_qa` (spec, plan, qa.md); CLI, MCP and uvx | QA kind recognized as `qa-report.md`; review and release skipped in legacy spelling | recognized `plan.md, qa-report.md, spec.md`; skipped `release-notes.md, review-report.md`; note `verdict is over recognized artifacts only`; `qa_status: passed` | ✅ pass |
| AC-2.3 | `cov_both_qa` (qa.md and qa-report.md); also all six names | QA kind once, shadowed legacy not a near-miss | recognized lists `qa-report.md` once, `near_misses: []`; the `Ignored .spark/demo/qa-report.md (qa.md takes precedence)` notice is on stderr and in MCP `ignored_legacy_files`; all six names give no near-miss | ✅ pass |
| AC-2.4 | `cov_reviews` (full trail plus `reviews.md`); a mix with `QA-notes.md`, `release_notes.md`, `spec-old.md`, `notes.md` | `reviews.md` still a near-miss | `near_misses: [reviews.md]`, note null; the mix lists the four look-alikes, not `notes.md` | ✅ pass |
| AC-3.1 | Legacy-only trails with `AC` header (`legacy`, `only_release_legacy`, `cov_none`, `L_only_qa`, `L_near`, `L_multi` 4 features, `L_no_spec`); `build . --full` with `ad83eae` and with the RC; `cmp` | byte-identical | all 7 identical (2.9 to 14.1 KB), both exit 0, stderr empty. Legacy names with a `Spec ID` header drift on `ad83eae` (PR #3 added that header), so they are no baseline | ✅ pass |
| AC-3.2 | Rsync copy of this worktree (without `.git`, `.venv`, `.aspark-graph`, `.spark/.guard/`); build with `ad83eae` and the RC; `cmp`; re-run with this report in place (see §5) | byte-identical | identical (513206 bytes before the report), both stderr empty; identical again with this report in the trail | ✅ pass |
| NFR-1 | Three `--full` builds of `L_multi`; a reverse-created copy of `L_near`; incremental vs `--full` after deleting release.md, adding and removing `reviews.md` and renaming qa.md; Wheel `Requires-Dist` vs `1b62da0` | same bytes; sorted lists; no new dependency | same sha on all 3 builds; the reversed copy is identical; incremental equals `--full` after each of the 4 edits, and coverage follows them; lists sorted; dependencies unchanged | ✅ pass |
| NFR-2 | `git status` and `git diff --numstat 1b62da0 -- tests/` in the worktree | tests only added | 0 lines changed in existing tests; one new untracked test file | ✅ pass |
| NFR-3 | Runtime probe on the installed package: set `_ARTIFACT_NAMES` QA current name to `qa-v2.md` (no file edit), built a repo holding `qa-v2.md` | coverage follows the single list | patched: `qa-report.md` recognized, `qa-v2.md` read (`qa_status: passed`), no near-miss. Unpatched: `qa-v2.md` is a near-miss and QA is skipped | ✅ pass |
| CLI≡MCP | Every building scenario (35 generated repos, Core, steamcore): graph bytes, `ignored_legacy_files`, `gate_health`, `get_node` | equal | equal on every repo; `gate_health` equal on all 14 Core and 13 steamcore features | ✅ pass |

**Regression of `current-artifact-names` (v0.7.1) with the RC:** current names are read, and current wins: `both` shows only F1 open, release `handed-off`/`v0.12.0`, and no `fail` QACheck. The `Ignored` notices are one per shadowed file in a stable order, and equal to MCP. Drift on malformed qa.md, review.md, an empty file or a `Criterion` header is a one-line error, exit 1, `isError` over MCP, for current and legacy names alike. Results are marker-first: a warning-sign cell reads `unknown`, a cross-mark cell containing "pass-worthy" reads `fail`, `plain pass` reads `pass`, and `pass (was fail)` reads `fail` (B4). A QA row with an escaped pipe in a code span and in the Observed cell reads `pass` on all rows. The current-name and legacy renamed trail, CRLF and mixed repos all give sha `c00d873d1d`. Core: 818 artifact entities, QACheck pass 143 / unknown 11 / fail 11, Finding 170, 14 features, exit 0. steamcore: 893 entities, pass 251 / unknown 10, Finding 138, 13 features, exit 0. Incremental equals `--full` on both. Those counts are re-derived, not cited (condition b: Must AC of the release).

## 3. Exploratory Findings

No new bugs. Seen again, already ruled, not re-filed:
- **Core coverage:** `lean-rounds` has no QA file, so it gets `skipped: [qa-report.md]` with the note set. That is correct, but on a current-name trail it names the legacy spelling (C2/C4, follow-up in G10). `graph-gates` has near-miss `PATCH-PLAN.md`, a genuine look-alike. steamcore has no skips and no near-misses. That makes 0 false near-misses from current names on 27 real features.
- **Review F6 (G10):** `explanation.md` is a near-miss (substring "plan").
- **Review F7 (G10):** a directory named `qa-notes.md` is a near-miss.
- **B3 (G8):** a directory named `qa.md` or `qa-report.md` still raises a traceback, the same as `ad83eae`, not caused by the repair.
- **Other probes, no bug:** an empty feature folder and an evidence-only folder list all five kinds as skipped. A broken `qa.md` symlink falls back to `qa-report.md`. A feature without `spec.md` lists `spec.md` in `skipped`.

## 4. Console & Network

There is no browser, console or network (offline tool). The equivalent surface is stderr and exit codes: on building repos, stderr carries only the `Ignored …` notices. Drift is a clean line, exit 1. Tracebacks appear only for B3 (deferred). The MCP server's stderr carries only the pydantic-settings warning and `Processing request` lines.

## 5. Verdict

Would I demo this to a stakeholder right now? **Yes.** The merged main crash is real: `1b62da0` raises `AttributeError` on a qa.md-only feature. The RC builds every scenario, including Core and steamcore. Coverage now speaks the trail's actual names. A full current-name trail is fully recognized with a null note. A lone `qa.md` counts as QA. A shadowed legacy file is neither a near-miss nor double-counted. `reviews.md` is still flagged. CLI and MCP agree byte for byte. Legacy trails are byte-identical to `ad83eae` on 7 repos and on this repo's own trail, and that was re-checked with this report in place. The v0.7.1 feature behaves as its round-2 QA recorded. Caveats for the release notes are unchanged: B2 (only the first QA table is read, G6), and `skipped` naming missing kinds by their legacy spelling (C2, G10). Not tested: Linux and Windows (F7 means the macOS case-insensitive results may differ there), PyPI upload, and the T4 pre-flight on the repair commit, which is still `todo`.

---

## ✅ QA GATE

- [x] Every Must-story acceptance criterion verified by running the installed RC (CLI, live MCP, uvx) and passed
- [x] Every relevant NFR verified and passed (NFR-1 to NFR-3; suite 328 and `-m slow` 3 passed)
- [x] No open Blocker or Major bugs (none new; B2 accepted G6, Minors deferred G8/G10)
- [x] Tool output free of unexpected errors on the tested flows (B3 only, Minor, deferred)
- [x] Tested on all agreed surfaces (CLI, MCP stdio, wheel venv, `uvx`; no viewports apply)
- [x] Line budget respected: Ist 73 / Soll ~130
- [x] Status set to `passed`
