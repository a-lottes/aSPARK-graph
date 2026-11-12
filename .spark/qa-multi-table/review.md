# Review Report: qa-multi-table

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | The diff of `/increment`, `.spark/qa-multi-table/plan.md` |
| **Status** | `passed` |
| **Round** | 1 |
| **Date** | 2026-11-12 |

<!-- Handoff: read this block first, the numbered sections below by exception. Whoever
     writes to this report — including `/increment` in fix-mode, which is not this
     report's owner — updates it in the same edit that closes or re-rules a finding:
     overwrite in place, never append. The block holds one current state, never a
     per-round log; a stale block is a defect, not a cosmetic issue.

     Re-review: bump `Round` yourself (only the owner bumps it, never `/increment`) at
     the start of the pass, then overwrite every section below in place — §1 Scope, §2
     Plan Conformance, §3 Findings, §4 Traceability, §6 Verdict and the gate checklist
     all hold exactly one current state, never a `## Round N` heading or a second gate.
     History lives in git, not in this file. -->

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Verdict:** Passed. Every AC and NFR verified by tests, an old-vs-new-code build diff, and a Core real-repo check. 1 open (Nit F4); reviewer added one test (F1).
- **Open:** `1 open` — Blockers: none; Majors: none (Minors/Nits: see §3)
- **Binding ruling:** §6 Verdict and the gate checklist below — the only binding location; there is no other round to point to
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Scope

- **Reviewed:** commit `8a08bbf` (parent `adeda0a`): `src/aspark_graph/artifacts.py` (`_parse_qa`, `_first_table`, new `_tables`/`_parse_run`), `tests/test_qa_multi_table.py`, `.spark/BACKLOG.md` (G6), `.spark/qa-multi-table/plan.md`. Context read: `_section`, `_col`, `_qa_id_column`, `_normalise_result`, `_parse_review`/`_parse_plan` (the other `_first_table` callers, `artifacts.py:211,252`).
- **Mode:** live runs (suite, slow tier, real builds, mutants), plus a static read of the diff. Nothing is degraded below what the ACs need.
- **Anti-generosity standard applied** (`/opt/aspark/standards/anti-generosity.md`, read in full before the verdict).
- **Graph tool** (`/opt/aspark/tools/aspark-graph.md`): `staleness` → `stale: false`, 67 files checked. `impact --diff adeda0a..8a08bbf` → `artifacts.py` reaches `current-artifact-names` US-1/US-4, `coverage-current-names` US-1 and `qa-multi-table` US-1. That pointed me at the other `_first_table` callers (`artifacts.py:211,252`), which I read. Their behaviour is unchanged (§4 AC-1.3). The suite covering those stories is green.
- **Observation, outside this diff:** `staleness` hashes only code `File` nodes (`queries.py:368`), so `.spark/` edits never make it stale. The graph reported `stale: false`, yet its `story_trace` still showed T1 `todo` from the pre-commit plan. I used the graph only for code scoping. This is a candidate BACKLOG item and not a finding against this feature.
- **Not reviewed:** lenses (none passed; `cli`/`library` were judged N/A because the diff changes no CLI surface or public API).

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ | `_tables` + `_parse_run` (documented split), `_first_table` delegates (`artifacts.py:370-373`), strict first run (`:285-292`), lenient later runs (`:300-301`), running index (`:295,303`). No new exception type. |
| T2 | ⚠️ | All seven DoD items are present. Two undocumented deviations exist (F4). Two behaviours were unpinned until the reviewer's added test (F1). |
| T3 | ✅ | The commit records only the cnr result (F2). The reviewer re-derived the evidence for both targets (§5). The plan's live-repo "two def nodes" deviation comes from stash changing the indexed source. With identical content the graphs are byte-identical. |
| T4 | ✅ | `.spark/BACKLOG.md:238`: one heading changed, German style, names `qa-multi-table`. |

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Minor | `tests/test_qa_multi_table.py:71` | AC-1.4's second half has a gap: a later table lacking *only* Result was untested, and so was plan §1.5 (skipped tables don't advance the index). Mutants that dropped the Result check (M1) or advanced the index on a skip (M4) passed all 6 tests. Fix applied: added `test_skipped_middle_tables_add_nothing_and_keep_index`, which kills both mutants. | fixed r1 |
| F2 | Minor | commit `8a08bbf` message; `plan.md:96` | The T3 DoD requires commands, the HEAD SHA and the diff result for both targets. The commit records only "current_names_repo byte-identical", with no commands, no SHA and no live-repo result. Fix applied: evidence re-derived and recorded in §5 (DoD allows "review evidence"). | fixed r1 |
| F3 | Minor | `.spark/qa-multi-table/plan.md:94-97` | `/increment` appended a `## Deviations` heading. The plan template has no such section, and the plan's own Handoff says revisions update §1/§3 in place, never as a new section. This adds structural drift to a parsed artifact. Fix: fold both bullets into §1 Consequences / the T3 row and drop the heading. | fixed |
| F4 | Nit | `tests/test_qa_multi_table.py:26,84` | Two undocumented deviations from the T2 DoD. (1) The fixture is confined by the copied `.spark/` marker, not the `.git` marker the DoD names. This is a valid marker and not a bypass. (2) The repeated AC sits in tables 1 and 2, not 1 and 3. Neither weakens any assertion. Fix: amend the T2 DoD wording. | open |

## 4. Requirements Traceability

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | `artifacts.py:296-318`; `test_every_table_yields_checks_with_continuous_index` | ✅ PASS. Core real-repo check: QA checks rise from 5→30 (graph-gates), 8→15 (lean-artifacts), 6→26 (project-kickoff) and 5→21 (tracker-handoff). The other 29 `qa.md` files are unchanged. |
| AC-1.2 | `queries.py` unchanged; `test_later_table_acs_not_unverified` | ✅ PASS. `gate_health.unverified_acs == []` and AC-2.1 `latest_result == "pass"`. The test fails under pre-change code. |
| AC-1.3 | `artifacts.py:370-373` (`runs[0]` = old first-run semantics) | ✅ PASS. Re-derived because this is a Must AC (condition b): byte-identical graph.json under old and new code, §5. |
| AC-1.4 | `artifacts.py:289-292` (strict), `:300-301` (lenient) | ✅ PASS. `test_first_table_missing_columns_is_drift`, `test_later_non_verification_table_is_skipped`, plus the F1 test. |
| AC-1.5 | `artifacts.py:303,313` (`order=i` continuous) | ✅ PASS. `test_same_ac_in_two_tables_latest_wins`: orders (0 fail),(1 pass), and `latest_result == "pass"`. |
| NFR-1 | `test_double_build_byte_identical` | ✅ PASS |
| NFR-2 | raises only at `artifacts.py:283,290,292` (messages unchanged) | ✅ PASS. `_col(row, None)` is unreachable: a `None` id column on table 0 raises first, and on later tables it is skipped. Across 33 Core `qa.md` files, old and new code produce the identical error set (9 pre-existing section-drift errors, no new types). |

## 5. What Was Checked

- [x] Correctness: logic does what the acceptance criteria demand
- [x] Non-functional: applicable NFRs and constitution quality bars hold
- [x] Error handling: failures are handled, not swallowed
- [x] Security: no injected input trusted, no secrets in code
- [x] Tests: exist, are meaningful, and pass
- [x] Readability: the next developer will understand this

Evidence (re-derived, F2):
- **Suite:** `uv run pytest`: 411 passed (410 before the F1 test). `uv run pytest -m slow`: 4 passed.
- **AC-1.3 method:** the old code is a `git worktree` at `adeda0a`. `src/aspark_graph/artifacts.py` is identical to `v0.7.3` (`git diff v0.7.3 adeda0a` is empty). The new code is `8a08bbf`. Each target was built `--full` under both codes, with `PYTHONPATH` pinned (module path printed). Swapping only the tool code isolates the parser; stash would also change the indexed source.
- **AC-1.3 result:** `tests/fixtures/current_names_repo` gives sha256 `07ee6b9c…f5aa` under both codes, and a clone of the live repo at `8a08bbf` gives `26f5e148…0842` under both. `cmp` reports identical in each case.
- **Core:** `/opt/aspark/.spark` snapshot (no git, so no SHA; copied and `git init`). The full Core build fails under both codes on a pre-existing `adversarial-gates-standard/spec.md` drift, so `_parse_qa` was run directly per file. All 21 accepted tables in the 4 G6 files have the header `Spec ID | Steps performed | Expected | Observed | Result`, and no table was skipped. The new `fail`s (e.g. graph-gates AC-2.4–2.6, AC-3.1) are authored `❌ not-verified-live` cells.
- **Mutants:** new tests vs pre-change code: 4/6 fail. Per-table index reset: caught. M1/M4: caught only after F1.

## 6. Verdict

Passed. The change does what US-1 asks. `_parse_qa` reads every pipe-table in the verification section and keeps the first table strict and later non-verification tables lenient. The running index leaves single-table output unchanged. I proved this with byte-identical graph.json under pre-change (= v0.7.3 parser) and new code, on the fixture and on the live repo. On the real Core trail, exactly the four G6 files gain their missing checks and nothing else moves. There are no Blockers or Majors. I fixed F1 (an untested half of AC-1.4 and the skip-doesn't-advance-index rule, both shown by surviving mutants) by adding one test. I fixed F2 by recording the T3 evidence here. F3 (a non-template `## Deviations` heading in plan.md) was fixed afterwards by folding it into §1; F4 (T2 DoD wording drift) remains open. Neither affects behaviour. Binding for later phases (plan risk 1): any QA artifact for this trail must keep its Acceptance Criteria Verification as **one** table. Otherwise the shipped tool reads it differently from v0.7.3, and the live-repo byte-identity proof is void.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`. On
re-review, edit this same checklist in place — never duplicate it as a second gate.*

- [x] No open Blocker findings
- [x] No open Major findings (or explicitly waived by the user, with reason recorded here)
- [x] Every Must AC traces to implementing code; no constitution non-negotiable violated
- [x] All plan deviations documented and accepted (`_parse_run` split and the T3 live-repo note are documented and explained in §2. F4's undocumented test deviations are Nits that change no assertion and are recorded here.)
- [x] Test suite runs green (411 + 4 slow)
- [x] Line budget respected: Ist 95 / Soll ~150 (excluding HTML comments)
- [x] Status set to `passed`
