# QA Report: qa-multi-table

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review (hands-on) |
| **Owner** | QA Tester (`/demo-day`) |
| **Input** | Headless CLI/MCP tool (no running app), `.spark/qa-multi-table/spec.md` (the acceptance criteria) |
| **Status** | `passed` |
| **Round** | 1 |
| **Date** | 2026-11-12 |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Verdict:** Yes, I would demo this now. Every AC and both NFRs passed by performed steps; no bug found.
- **Open:** `none` — Blockers: none; Majors: none (Minors: none; review.md F4 Nit is not a QA finding)
- **Binding ruling:** §5 Verdict and the gate checklist below — the only binding location; there is no other round to point to
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/demo-day` and proceed — don't stop on it.

## 1. Test Environment

- **App URL:** N/A. Constitution §8 declares `Browser-observable surface: no` and names the substitute method, which I performed (steps in §2). Browser, viewports: N/A.
- **Mode:** live runs (suite, slow tier, CLI builds and queries, old-vs-new code builds). Not degraded: every row below rests on a command I ran. The earlier `qa.md` (written without this ceremony) was discarded and every row re-tested.
- **Anti-generosity standard applied** (`/opt/aspark/standards/anti-generosity.md`, read in full before the verdict). Binary results; no row is rounded up.
- **Test data:** scratch dir `/tmp/qa-scratch/<name>` (each with its own `.git` marker), copies of `tests/fixtures/current_names_repo` with only the `qa.md` verification section replaced: `multi` (3 tables: `### US-1`, `### US-2`, `### Bugs`), `nofirstid`, `nofirstresult`, `laternoresult`, `repeat`, `single`, `edge1`-`edge3`, and a clone of this repo at `63b922c` (`live`). Code under test: working tree `63b922c` (parser = `8a08bbf`). Old code: `git worktree` at `adeda0a`; `git diff v0.7.3 adeda0a -- src/aspark_graph/artifacts.py` is empty, so it is the v0.7.3 parser. Each build ran `--full` with `PYTHONPATH` pinned; the printed module path confirmed which code ran.
- **Graph tool** (`/opt/aspark/tools/aspark-graph.md`): `staleness` gave `stale: false`, 67 files. `impact --diff adeda0a..8a08bbf` pointed me to `artifacts.py` and `tests/test_qa_multi_table.py` (story `qa-multi-table` US-1 declared). It scoped where to probe only. No Result cell rests on it. The tool file says not to read `gate_health`/`story_trace` QA legs for a project's own QA evidence; here they are the product under test, run on my own scratch fixtures.

## 2. Acceptance Criteria Verification

<!-- Plan risk 1 / review §6: this trail's verification stays ONE table. -->

| Spec ID | Steps performed | Expected | Observed | Result |
|---|---|---|---|---|
| AC-1.1 | `aspark-graph build /tmp/qa-scratch/multi` (AC-1.1, AC-1.2 in table 1; AC-2.1 in table 2; a bug table). Read the QACheck nodes in `graph.json`. Built the same fixture under old code. | One QA check per AC row of every verification table, with its result. | New code: `qa:demo:AC-1.1#0` pass, `AC-1.2#1` fail, `AC-2.1#2` pass; the bug table added nothing. Old code: only `AC-1.1#0`, `AC-1.2#1` (artifact entities 12 vs 13), so the fixture reproduces the defect and the fix. | ✅ pass |
| AC-1.2 | `query gate_health demo` and `query story_trace US-1 / US-2 --feature demo` on `multi`. Also on `laternoresult`. | Second-table ACs show their recorded result, not unverified. | `story_trace US-2`: AC-2.1 `latest_result` `pass`, 1 check. `US-1`: AC-1.1 pass, AC-1.2 fail. `gate_health`: AC-2.1 absent from `unverified_acs`; AC-1.2 listed only because its result is `fail` (queries.py:410 counts "no pass" as unverified, pre-existing, unchanged). `laternoresult` correctly lists AC-1.2 (its row sits in a skipped table). | ✅ pass |
| AC-1.3 | Built `single` (one table), `tests/fixtures/current_names_repo` (same content) and a clone of this repo at `63b922c`, each `--full` under old (`adeda0a`) and new code; `cmp` on the graph.json pairs. | Byte-identical. | `single` identical, sha256 `07ee6b9ca8e8`, 6038 B. `live` identical, sha256 `45b7289e912b`, 673987 B (732 code, 582 artifact entities, 189 inferred). Re-run on the final working tree with this report included: identical, see §5. Re-derived myself: Must AC (condition b). | ✅ pass |
| AC-1.4 | `build` on `nofirstid` (first table `Step`, `Result`) and `nofirstresult` (`Spec ID`, `Observed`). Built `laternoresult` (later table `Spec ID`, `Notes` between two valid tables) and `multi` (later `Bug`, `Severity` table). Checked exit code, stderr line count, `Traceback`. | Drift error as before on the first table; later tables skipped silently. | `nofirstid`: exit 1, one stderr line `template drift in .../qa.md: QA table missing an 'AC' or 'Spec ID' column (found ['result', 'step'])`. `nofirstresult`: exit 1, one line `QA table missing a 'Result' column`. No traceback in either. `laternoresult`: exit 0, checks `AC-1.1#0`, `AC-2.1#1`, the Notes table added none and did not advance the index. `multi`: exit 0. | ✅ pass |
| AC-1.5 | Built `repeat` (AC-1.1 `❌ fail` in table 1, `✅ pass` in table 2). `story_trace US-1 --feature demo`. | Both checks kept in file order, later one is latest. | `qa_checks`: `order 0 fail`, `order 1 pass`; `latest_result` `pass`. Ids `qa:demo:AC-1.1#0` and `#1`, unique. | ✅ pass |
| NFR-1 | Built `multi` twice with `--full`; `cmp` of the two graph.json. Ran `uv run pytest` (incl. `test_double_build_byte_identical`) and `-m slow`. | Byte-identical double build; suites green. | Identical, sha256 `c91038d19242`. `uv run pytest`: 411 passed. `uv run pytest -m slow`: 4 passed (`test_unlocked_wheel_install_boots_mcp_server` = clean-env wheel install plus `serve` boot without the lock; `test_mcp_stdio_transport_round_trip`; `test_sdist_manifest...`; `test_nfr1_incremental...`). | ✅ pass |
| NFR-2 | Drove every failure path I could reach through the CLI: both drift cases above, plus `edge1` (escaped pipe, header-only table, `Criterion`-headed table, NFR and out-of-spec AC rows, `⚠` result), `edge2` (two tables with no blank line), `edge3` (no table, one lone pipe line). Checked exit code and `Traceback`. | No new traceback path; errors stay one-line domain errors. | Drift cases: exit 1, one line, no traceback. `edge1`-`edge3`: exit 0, no stderr beyond the "No git history" notice, no traceback. Row indexes follow old `enumerate` semantics (skipped non-AC rows advance the index, e.g. `AC-9.9#2`). `⚠ not-verified-live` reads `unknown`, not pass. | ✅ pass |

## 3. Exploratory Findings

<!-- None filed. Behaviours below were probed, are spec-accepted, and changed no result. -->

| # | Severity | Steps to reproduce | Expected vs. observed | Status |
|---|---|---|---|---|
| — | — | No bug found. Probed: `edge1` (later table headed `Criterion`/`Result` is skipped silently, spec A2/C1 and plan risk 2; its AC-1.2 stays unverified), `edge2` (adjacent tables with no blank line are one pipe run; the second header and separator count as skipped data rows, result unchanged). | Both match the spec and plan; no wrong result, crash or message. | n/a |

## 4. Console & Network

N/A (no browser, no network). The CLI's stderr was checked on every build: only the "No git history" notice for git-less scratch dirs, plus the intended one-line drift errors. No traceback anywhere.

## 5. Verdict

Yes, I would demo this now. Anti-generosity standard applied. All five ACs and both NFRs passed by commands I ran; each passes on its own observable, none is partial. The defect is reproduced under v0.7.3 code (AC-2.1 missing) and gone under the new code. Single-table output is byte-identical on the fixture and on a clone of the live repo. No open Blocker, Major or Minor. review.md's F4 is a Nit about test-DoD wording, not a QA finding. One wording note in review.md: its Handoff says "2 open" and its §6 calls F3 open while §3 marks F3 `fixed`; artifact wording, capped at Minor, changes no gate.

Final live-repo byte-identity check on the final working tree (this report included, one table): old and new code give identical graph.json (732 code, 582 artifact entities), sha256 `5f11209c616d`.

---

## ✅ QA GATE

*All boxes checked → `/go-live` may start. Any box open → back to `/increment`, then re-run
`/demo-day`. On re-test, edit this same checklist in place — never duplicate it as a second gate.*

- [x] Every Must-story acceptance criterion verified (by the §8 substitute method) and passed
- [x] Every browser-observable NFR verified and passed (NFR-1, NFR-2 by the §8 method; no browser NFRs exist)
- [x] No open Blocker or Major bugs (Minor bugs listed and accepted by the user): none filed
- [x] Browser console free of errors on the tested flows: N/A per §8; CLI stderr clean (§4)
- [x] Tested on all agreed viewports: N/A per §8 (no UI, no viewports agreed)
- [x] Line budget respected: Ist 71 / Soll ~130 (excluding HTML comments) — self-reported, no linter checks this
- [x] Status set to `passed`
