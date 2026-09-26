# Review Report: current-artifact-names

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | Working tree vs `dc3a94c` (uncommitted), `.spark/current-artifact-names/plan.md` |
| **Status** | `passed` |
| **Round** | 2 |
| **Date** | 2026-09-25 |

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
- **Verdict:** Pass. The C14 fix (T5c) works, stays QA-only, and AC-5.1 was re-derived byte-identical against v0.7.0. The reviewer closed one closing-pipe edge case and two test gaps (F5, F6). No Blockers or Majors.
- **Open:** `2 open` — Blockers: none; Majors: none (Minors/Nits: see §3)
- **Binding ruling:** §6 Verdict and the gate checklist below — the only binding location; there is no other round to point to
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

<!-- Budget: ~150 lines. -->

## 1. Scope

- **Reviewed (round 2):** the T5c diff, meaning `_first_table`/`_split_row` (`artifacts.py:338-371`)
  and the `_parse_qa` call site (`:260`), plus the C14 tests (`test_current_names.py:298-339`). I also
  checked spec C14, plan Revision 3 and the T5c row and note, and the BACKLOG G7/G8 text.
  Round-1 findings were verified against their rows.
- **Incident check:** `tests/test_current_names.py` is complete. Diffed against the QA-clone copy
  (`scratchpad/qa/clone`, identical to `scratchpad/rc`), the only differences are the `_split_row`
  import and the C14 block. The F2 fix is present (`:177-197`: `demo` shadows `review-report.md`,
  expected before `qa-report.md`). The T1–T6/T5b tests are all there (314 + 3 = 317 before my additions).
- **Re-derived, not cited:** AC-5.1, under condition **a** (this round verifies a fix that touches
  the table splitter AC-5.1 depends on) and **b** (Must AC). I cloned `dc3a94c` fresh, applied the
  tracked diff and the untracked files (no symlink, no `.spark/.guard/`), then built with
  `uvx --offline --from aspark-graph==0.7.0 … --full` and with the working tree: `cmp` found them
  identical. I repeated this after my own fixes: identical (`bcc6ee31…`), with no stderr lines.
  **Core `e1a0005` / steamcore `bf1b3e0`** were rebuilt before and after my F5 fix and came out
  byte-identical. QACheck counts: Core pass 143 / unknown 11 / fail 11, steamcore pass 251 /
  unknown 10. These match the T5c note.
- **Mutation checks (scratch copy):** first, dropping the flag at `:260` fails the C14 end-to-end
  test. Second, `unescape_pipes=True` as the `_first_table` default **survived** the original
  suite, and so did `_parse_review` passing the flag (F6). Both mutants fail now, as does the
  pre-F5 closing strip.
- **Graph tool:** stale, treated as absent (caller). Not reviewed: T7/T8 (go-live).

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ | `_ARTIFACT_NAMES`/`_resolve` (`artifacts.py:42,84`), `_qa_id_column` order a→d (`:290`). The `_parse_qa` diff is limited to the header check, the message and `_col(row, id_col)` (`:264-272`). The fixture header is verbatim from Core `templates/qa-report.md:50` |
| T2 | ✅ | One test per AC, plus `test_qa_nfr_rows_are_skipped` |
| T3 | ✅ | `BuildReport.shadowed` (`build.py:54`), pass-through `:144`, bounds untouched. The order test lacked a review shadow; fixed (F2) |
| T4 | ✅ | stderr line per path (`cli.py:175-177`) and `ignored_legacy_files` (`server.py:35`). No resolution logic in either adapter. The public `CURRENT_NAME_FOR` helper is accepted (F4) |
| T5 | ✅ r2 | The test placement is now recorded in the task note (`plan.md:222`) and the `files:` note is corrected (F3) |
| T5b | ✅ | `_normalise_result` checks ❌ → ⚠ → ✅ before any word. The 5 C13 cells are tested verbatim |
| T5c | ✅ | The flag is opt-in and only `_parse_qa` sets it (`:260`); the default path of `_split_row` is unchanged (`:364-366`). Tests (i)–(iv) existed only in weaker form; the reviewer completed them (F6). The task note named the wrong feature for the 2 new fails; corrected (F8) |
| T6 | ✅ | README `## Artifacts read` and five languages; `CLAUDE.md:8` and `:28` read five; 3 README tests |

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Minor | `src/aspark_graph/server.py:25-28` | Plan R4's promised backlog item for uncaught MCP `TemplateDriftError` was missing. *Fix:* BACKLOG G7 | fixed r2 (G7 present in `.spark/BACKLOG.md`) |
| F2 | Minor | `tests/test_current_names.py:177-197` | The NFR-1 order test never asserted review before qa. *Fixed by the reviewer* in r1; confirmed present after the file-restore incident | fixed r1 |
| F3 | Minor | `.spark/current-artifact-names/plan.md:190` | T5's `files:` note declared `tests/test_artifacts.py`, which the diff never touched. *Fix:* note corrected, move recorded (`plan.md:222`) | fixed r2 |
| F4 | Nit | `src/aspark_graph/cli.py:176` | The CLI recovers the current name by splitting the path string (`CURRENT_NAME_FOR`) | accepted (user, 2026-09-25) |
| F5 | Minor | `src/aspark_graph/artifacts.py:369` | With the flag set, `strip` of the border also ate an escaped pipe placed directly before the closing pipe (no space between them), so the cell came out as `b` plus a stray backslash instead of `b` plus a pipe. No column shift, and no Core/steamcore row is affected. *Fixed by the reviewer:* in the flag path only, a trailing pipe run is stripped only when it is not escaped. The default path is untouched; test at `test_current_names.py:314` | fixed r2 |
| F6 | Minor | `tests/test_current_names.py:303,319` | Plan T5c (iii) asks for a review-table scope guard. The C14 tests checked only `_split_row`'s default, so flipping the `_first_table` default, or having `_parse_review` pass the flag, left the suite green, and only the manual T8a would have caught it. Test (i)/(iv) asserted "AC-1.1 not unverified" instead of `pass` and an empty `unverified_acs`. *Fixed by the reviewer:* added a graph-level review.md guard (`:319`) and strengthened `:303`; all three mutants now fail | fixed r2 |
| F7 | Nit | `src/aspark_graph/artifacts.py:371` | The lookbehind treats an escaped backslash followed by a pipe as an escaped pipe. GFM treats it as a backslash plus a cell border, so such a row merges two cells. There are 0 occurrences in this repo, Core or steamcore. An unescaped pipe inside backticks still splits, which matches GFM (GFM requires the escape there too). Core `situational-lenses` AC-3.3 has such an unescaped pipe and reads `unknown` (its author wrote ❌), exactly as in v0.7.0. *Fix:* add both to BACKLOG G8; tokenising backslash escapes pairwise would handle the first | open |
| F8 | Minor | `.spark/current-artifact-names/plan.md:223` | The T5c note attributed the 2 new `fail` rows to `graph-gates` AC-3.3/AC-5.2. A per-row probe shows they are `situational-lenses` AC-5.2 and AC-6.1. The DoD's "the 13 rows now pass" also overstates it: all 10 ✅-marked escaped-pipe rows read `pass` (9 of them newly); the rest are ⚠, ❌ or malformed. The counts are correct. *Fixed by the reviewer:* feature/AC names in the note | fixed r2 |
| F9 | Minor | `.spark/current-artifact-names/qa-report.md` (verification table) | AC-5.1 holds only because this repo's own QA verification tables contain no escaped pipe (the B1 repro sits in the bugs table, `qa-report.md:66`, which is not parsed). If re-QA puts the B1 repro row, with its escaped pipes, into the verification table, v0.7.0 and v0.7.1 read that row differently, so T8a's `cmp` fails and blocks the release (C10). *Fix:* re-QA keeps escaped pipes out of the first verification table, or rephrases the cell without them. T8a stays binding | open |

## 4. Requirements Traceability

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | `artifacts.py:84,107,260,290,363-371`; `test_current_names.py:18,303` | ✅ met |
| AC-1.2 | same; `test_current_names.py:28` | ✅ met |
| AC-1.3 | `_normalise_result`; C14 split (`:260`); `test_current_names.py:46,281,303` | ✅ met |
| AC-1.4 | `artifacts.py:123-125`; `test_current_names.py:59` | ✅ met |
| AC-2.1 | `_parse_review` + `queries.py:302` (unchanged); `test_current_names.py:63` | ✅ met |
| AC-2.2 | `artifacts.py:251`; `test_current_names.py:68` | ✅ met |
| AC-2.3 | `artifacts.py:120-122`; `test_current_names.py:73` | ✅ met |
| AC-3.1 / AC-3.2 | `artifacts.py:126-128`; `test_current_names.py:77,81` | ✅ met |
| AC-4.1 / 4.2 / 4.3 | `artifacts.py:84-94`; `test_current_names.py:131,141,154` | ✅ met |
| AC-4.4 | `cli.py:175-177`; `test_cli_mcp_parity.py:174` | ✅ met |
| AC-4.5 | `server.py:35`; `test_cli_mcp_parity.py:174,191` | ✅ met |
| AC-4.6 | `build.py:54` (report only); `test_current_names.py:164` | ✅ met |
| AC-5.1 | re-derived r2: `cmp` v0.7.0 vs working tree, identical (§1); scope guard `test_current_names.py:319` | ✅ met (binding: T8a; see F9) |
| AC-5.2 | reused parsers; `test_current_names.py:200,208,217` | ✅ met |
| AC-5.3 | `test_current_names.py:251` | ✅ met |
| AC-5.4 | Core/steamcore rebuilt r2 (§1), no drift | ✅ early; binding T8b (incl. steamcore `gate_health`) |
| AC-6.1 / 6.2 / 6.3 | `README.md:233,237-251,276`; `CLAUDE.md:8,28`; `test_readme.py:68-82` | ✅ met |
| NFR-1 | `artifacts.py:79` (sorted dirs) + table order; `test_current_names.py:177` | ✅ |
| NFR-2 | existing test diffs are additions only; 319 passed | ✅ |
| NFR-3 | `test_cli_mcp_parity.py:174` (paths + graph bytes) | ✅ |
| NFR-4 | `uv run pytest -m slow`: 3 passed | ✅ |
| NFR-5 | `_resolve` joins only table literals; the new regex is linear, no input-driven paths | ✅ |
| NFR-6 | N/A (headless) | N/A |
| NFR-7 | `cli.py:175-177`; Core builds 818 artifact entities (was spec/plan only) | ✅ |

## 5. What Was Checked

- [x] Correctness: C14 behaviour, traced per row on Core/steamcore. All ✅-marked escaped-pipe rows read `pass`; the ❌ rows the shift had hidden now read `fail`
- [x] Edge cases probed: an escaped backslash before a pipe (F7), a trailing escaped pipe (F5, fixed), a row without a closing pipe, `||`, pipes in backticks (GFM-consistent)
- [x] Non-functional: NFR-1–5 and 7 hold; the default split path is byte-for-byte the old code
- [x] Error handling: unchanged by T5c; drift paths as in round 1
- [x] Security: the regex is a fixed pattern with no backtracking blow-up; no new read surface
- [x] Tests: 319 passed, `-m slow` 3 passed; mutation-checked (§1)
- [x] Readability: the flag and its comment are small and local

## 6. Verdict

Pass. T5c does what C14 asks. With the opt-in flag, an escaped pipe in the QA verification
table stays in its cell, so the real steamcore/Core rows that shifted into `unknown` now read
what their markers say. That is 9 new passes, plus 2 honest fails that the shift had hidden.
Every other table goes through the unchanged default path. I re-derived AC-5.1 myself on a
fresh clone, before and after my own edits: v0.7.0 and the working tree build byte-identical.
The file-restore incident left nothing missing; the F2 fix and all earlier tests are present.
Three things were wrong, and I fixed each one myself:
- F5: an escaped pipe directly before the closing pipe was swallowed by the border strip.
- F6: the planned scope guard existed only as a unit test on the default argument, so a
  mutant enabling the flag for review tables passed the suite.
- F8: the T5c note named the wrong Core feature.
Two items remain, and neither blocks. F7 is a documented GFM divergence with zero real
occurrences, a candidate for G8. F9 is a release-process risk: re-QA must keep escaped pipes
out of this feature's own verification table, or T8a's `cmp` will fail. F1 and F3 are
confirmed fixed, and F4 is accepted.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`. On
re-review, edit this same checklist in place — never duplicate it as a second gate.*

- [x] No open Blocker findings
- [x] No open Major findings (or explicitly waived by the user, with reason recorded here)
- [x] Every Must AC traces to implementing code; no constitution non-negotiable violated (no constitution; the CLAUDE.md non-negotiables hold)
- [x] All plan deviations documented and accepted. The T5c test weakening (F6) and the note error (F8) were fixed by the reviewer; F4 was accepted by the user; B2/G6 was accepted by the user
- [x] Test suite runs green (319 passed; `-m slow` 3 passed)
- [x] Line budget respected: Ist 144 / Soll ~150 (excluding HTML comments)
- [x] Status set to `passed`
