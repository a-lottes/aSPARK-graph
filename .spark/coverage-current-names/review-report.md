# Review Report: coverage-current-names

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | Working tree vs `1b62da0` (uncommitted), `.spark/coverage-current-names/plan.md`; PR #2 code (`dcf85f1`) |
| **Status** | `passed` |
| **Round** | 2 |
| **Date** | 2026-09-26 |

<!-- Handoff: read this block first, the numbered sections below by exception. Whoever
     writes to this report — including `/increment` in fix-mode, which is not this
     report's owner — updates it in the same edit that closes or re-rules a finding:
     overwrite in place, never append. The block holds one current state, never a
     per-round log; a stale block is a defect, not a cosmetic issue. -->

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Verdict:** Passed: the repair is correct and proven, F1–F5 are fixed, and the release notes honestly defer the pre-flight to T4; one new Minor (F11) is left open.
- **Open:** `1 open` — Blockers: none; Majors: none (Minor F11; F6–F9 accepted into BACKLOG G10, see §3)
- **Binding ruling:** §6 Verdict and the gate checklist below — the only binding location; there is no other round to point to
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Scope

Round 2 (re-review). Reviewed the fix-mode edits for F1–F5: `.spark/current-artifact-names/release-notes.md`, `.spark/coverage-current-names/plan.md` and `spec.md`, and the new `.spark/BACKLOG.md` G10. `src/` and `tests/` are unchanged since round 1 (only my F10 comment edit is in the diff), so I did not re-hunt the code; the round 1 code review of the repair and of PR #2 (`dcf85f1`) stands. No constitution, lenses or tool file.

Re-derived in round 2:
- `uv run --extra dev pytest`: 328 passed; `-m slow`: 3 passed. Re-derived because the gate needs a green suite.
- AC-3.2: this worktree's trail, now holding the edited `.spark/` files and this report, built `--full` by the fix and by `scratchpad/base_ad83` (`ad83eae`): `cmp` identical (524287 bytes). Condition (a): this round verifies the fixes to artifacts in that very trail.
- Local tag `v0.7.1` still points to `e57ce6d`; `origin` has no `v0.7.1` tag.

Cited from round 1, not re-run: new tests fail without the fix; legacy-only repo `cmp`; v0.7.0 identity minus `coverage`; incremental stability; CLI≡MCP. No code changed that would affect them.

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ r2 | Code follows C4; plan §1 now says the same (F4 fixed). |
| T2 | ✅ | 5 tests, fail on `1b62da0`, pass now (re-derived). |
| T3 | ✅ | Byte-identity re-derived on both repos (§1). |
| T4 | ✅ r2 | `todo`, correctly. The DoD now requires the pre-flight re-run on the repair commit before the KEEP GATE box is ticked. Release notes: F11 is left for T4. |

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Major | `.spark/current-artifact-names/release-notes.md:21-35, 90, 98` | §1 Pre-flight is "run fresh on the release commit" but still states the old one: 319 tests, base `dc3a94c == origin/main`, and T8(a) "`cmp` no difference vs 0.7.0" — contradicted by line 49 of the same file (coverage changes every Feature node). Learnings line 90 repeats "byte-identical proof against v0.7.0 valid". KEEP GATE line 98 `[x] All pre-flight checks passed` is therefore untrue for the commit that will ship. Why: the publish hard stop rests on this record. Fix: re-run pre-flight on the repair commit in T4 (328 + 3 slow, base `1b62da0`, T8(a) against `ad83eae` plus v0.7.0 minus `coverage`), rewrite line 90, uncheck line 98 until then; add "re-run pre-flight" to the T4 DoD. | fixed r2 |
| F2 | Minor | `.spark/current-artifact-names/release-notes.md:79` | Pending command 3 still pushes `feat/current-artifact-names` and opens a PR from it; PR #3 is merged. Fix: `fix/coverage-current-names`. | fixed r2 |
| F3 | Minor | `.spark/current-artifact-names/release-notes.md:9` | Version rationale names one additive key (`ignored_legacy_files`); 0.7.1 now also adds the `coverage` node attribute and `gate_health` keys `coverage`, `coverage_note`. Fix: list them; the user may want to rule patch vs minor (open question 1). | fixed r2 |
| F4 | Minor | `.spark/coverage-current-names/plan.md` §1, bullet `recognized` | Architecture decision says `recognized` = "names of the files that exist"; code and C4 use the legacy spelling per kind. Fix: reword the bullet to match C4. | fixed r2 |
| F5 | Minor | `.spark/coverage-current-names/spec.md` C2 | "A later cleanup can switch to current names (BACKLOG G8)" — G8 (`BACKLOG.md:273-293`) has no such item, so the follow-up is lost. Fix: add a G8 bullet or drop the reference. | fixed r2 |
| F6 | Minor | `src/aspark_graph/artifacts.py:145-147` (PR #2) | Near-miss is a raw substring test, so `explanation.md` ("plan"), `perspective.md`/`inspection.md` ("spec") are flagged. Reproduced: `explanation.md` in `near_misses`. Noise only — `coverage_note` ignores near-misses. Fix: split the stem on `-`/`.` and match tokens (or edit distance against `known`); add a negative test. | accepted |
| F7 | Minor | `src/aspark_graph/artifacts.py:142-147` (PR #2) | Case and non-files: on macOS (case-insensitive FS) `QA.md` is read as QA (`qa_status` set, `qa-report.md` recognized) and also listed as near-miss; on Linux the same trail yields `qa-report.md` skipped — graph depends on OS. `glob("*.md")` also returns dotfiles (`._qa.md`) and directories. Fix: skip names in `known` case-insensitively, filter `is_file()` and leading dots; pair with G8 B3. | accepted |
| F8 | Minor | `src/aspark_graph/queries.py:308-321` (PR #2) | A graph built before PR #2 (no `coverage` on the node) returns `coverage: {}` and `coverage_note: null`, which reads as full coverage — the opposite of #61's intent — until the user rebuilds after upgrading. Fix: when the key is absent, set a note such as "coverage unknown; rebuild". | accepted |
| F9 | Minor | `tests/test_cli_mcp_parity.py` | No `gate_health` parity test, so the new `coverage`/`coverage_note` fields have no CLI≡MCP assertion. Parity holds by construction (both call `queries.gate_health`) and I confirmed it by hand. Fix: add a `gate_health` row. | accepted |
| F10 | Nit | `src/aspark_graph/artifacts.py:136` | Comment cited only C2 for a rule that C4 made. | fixed r1 |
| F11 | Minor | `.spark/current-artifact-names/release-notes.md:14, 73, 78-81` | Three leftover inconsistencies. (1) Handoff says "nothing pushed", but PR #3 was pushed and merged. (2) Pending commands are listed "in order", yet command 1 (publish) needs the merge that command 3 performs. (3) The Version row says the `e57ce6d` tag "is dropped", but the local `v0.7.1` still points there. Why: the publish hard stop reads this list top-down. Fix in T4: move command 3 first, reword the Handoff ("PR #3 merged; nothing published or tagged remotely"), and write "to be dropped" until `git tag -d` runs. | fixed r2 (orchestrator, T4 text) |

## 4. Requirements Traceability

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | whole suite; PR #2/#3 tests unedited (`git diff` touches no existing test) | ✅ met |
| AC-1.2 | `artifacts.py:133-139` (`None` never dereferenced); `test_ac_1_2_and_2_2…` | ✅ met |
| AC-2.1 | `artifacts.py:137-140`, `queries.py:317-321`; `test_ac_2_1…` | ✅ met |
| AC-2.2 | `artifacts.py:139`; `test_ac_1_2_and_2_2…` | ✅ met |
| AC-2.3 | `artifacts.py:140-143` (`known` holds current and legacy); `test_ac_2_3…` | ✅ met |
| AC-2.4 | `artifacts.py:145-147`; `test_ac_2_4…` | ✅ met (see F6 for false positives) |
| AC-3.1 | byte-identity re-derived, §1 | ✅ met |
| AC-3.2 | byte-identity re-derived, §1 | ✅ met |
| NFR-1 | `sorted()` at `artifacts.py:156-158`; `sort_keys=True` in `graph.py:128` | ✅ (OS dependence: F7) |
| NFR-2 | no existing test edited | ✅ |
| NFR-3 | `legacy_name`, `known` derived from `_ARTIFACT_NAMES` | ✅ |

## 5. What Was Checked

- [x] Correctness: logic does what the acceptance criteria demand
- [x] Non-functional: applicable NFRs and constitution quality bars hold (no constitution; spec NFRs hold)
- [x] Error handling: failures are handled, not swallowed (no new try/except; the crash is gone)
- [x] Security: no injected input trusted, no secrets in code (paths only from literals and `glob` inside the feature dir)
- [x] Tests: exist, are meaningful, and pass (fail without the fix; AC-2.3 also fails a None-guard-only fix)
- [x] Readability: the next developer will understand this

**User rulings (2026-09-26), replacing round 1's open questions**
1. The version stays 0.7.1 (patch); recorded at release-notes line 9.
2. `coverage_note` on in-progress features stays as PR #2 intends; recorded in BACKLOG G10.
3. F6–F9 are accepted for this release and moved to BACKLOG G10 (`coverage-hardening`). I checked that G10 carries all four accurately, plus the C2/C4 follow-up.

## 6. Verdict

Passed. The code repair was already correct in round 1 and is unchanged: the crash is gone, coverage is built from `_resolve` with names from `_ARTIFACT_NAMES`, and the graph stays byte-identical to `ad83eae` on this trail. I re-checked that identity this round with the edited artifacts and this report in the trail, and the suite is still 328 + 3 green. F1 is fixed honestly. The old pre-flight is now labelled as having run on `e57ce6d`, it explicitly does not certify the release, and it names `ad83eae` as the baseline. The KEEP GATE box is unchecked, and the T4 DoD makes the re-run on the repair commit a precondition for ticking it. Nothing in the notes now claims evidence that does not exist; the actual re-run stays T4's job at release time, which is where it belongs. F2–F5 are fixed as asked. F6–F9 are Minor weaknesses in PR #2's code; the user accepted them for this release and they are tracked in G10. One new Minor (F11): the release notes' command order, Handoff summary and tag wording are out of step with each other. It does not block this gate, but T4 must fix it before the publish stop, because that list is read and executed top-down.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`. On
re-review, edit this same checklist in place — never duplicate it as a second gate.*

- [x] No open Blocker findings
- [x] No open Major findings (F1 fixed r2)
- [x] Every Must AC traces to implementing code; no constitution non-negotiable violated
- [x] All plan deviations documented and accepted (T1/C4 ruled by the user; plan §1 aligned r2)
- [x] Test suite runs green (328 passed, `-m slow` 3 passed)
- [x] Line budget respected: Ist 104 / Soll ~150 (excluding HTML comments)
- [x] Status set to `passed`
