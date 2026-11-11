# QA Report: kotlin-support

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review (hands-on) |
| **Owner** | QA Tester (`/demo-day`) |
| **Input** | Headless tool: substitute method per `.spark/constitution.md` §8; `.spark/kotlin-support/spec.md` (the acceptance criteria) |
| **Status** | `passed` |
| **Round** | 1 |
| **Date** | 2026-11-11 |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Verdict:** Yes, I would demo this now; one Minor (B1, undocumented loss of declarations after one Kotlin shape) is open.
- **Open:** `1 open` — Blockers: none; Majors: none (Minors: see §3)
- **Binding ruling:** §5 Verdict and the gate checklist below — the only binding location; there is no other round to point to
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/demo-day` and proceed — don't stop on it.

## 1. Test Environment

- **App URL:** N/A. The constitution §8 declares `Browser-observable surface: no` and names the substitute method (suite + slow tests, clean-env wheel install and `serve` boot, byte-identical build, real-repo check). I performed each step and record it below.
- **Browser / viewport(s):** N/A (headless CLI/MCP tool).
- **Test data / accounts used:** `/workspace/repo` at HEAD 8c24235 (branch factory/issue-36). A COPY of okhttp at `/tmp/qa_work/okhttp` (source clone `/tmp/scratch/okhttp`, SHA 4162e9da32f636442bc789a7576144fe5972d0a5, untouched; 575 `.kt` + 44 `.kts`). A hand-made fixture repo `/tmp/qa_work/fx`. Mode: live runs of the real CLI, MCP tool functions and test suites; no item was verified by reading alone.
- **Standard applied:** `/opt/aspark/standards/anti-generosity.md` (anti-generosity standard applied; binary results, no partial passes, no banned phrases).
- **Graph calls used (scoping only, no Result rests on them):** `staleness` (fresh), `story_trace` for US-1 and US-3 (every AC read `unknown`, tasks T1-T4, T7, T9 mapped to Kotlin files).

## 2. Acceptance Criteria Verification

| Spec ID | Steps performed | Expected | Observed | Result |
|---|---|---|---|---|
| AC-1.1 | Built fixture `fx` (`src/**/*.kt`, root `build.gradle.kts`, an empty `Empty.kt`, a binary-garbage `Bin.kt`). Built the okhttp copy. Read `graph.json` | Every `.kt`/`.kts` is a `File` with `language="kotlin"`, none flagged unparsed | okhttp: 619 Kotlin `File` nodes = 575 + 44, all `language=kotlin`, 0 carry an unparsed flag, build line has no "unparsed" note. Fixture: `.kts`, empty and garbage files all `File` nodes, no crash | ✅ pass |
| AC-1.2 | Extracted a normally formatted file (`/tmp/qa_work/n.kt`) with class, data class, object, interface, enum class. Counted okhttp node types | One `Class` node each, `contains` edge from the `File` | Classes `Plain`, `D`, `Single`, `I`, `Color` all found. okhttp: 853 `Class` nodes, 829 `contains` edges from Kotlin Files. See B1 for a shape that loses later classes | ✅ pass |
| AC-1.3 | Same file, plus okhttp `find_nodes Dispatcher` | Top-level, member, extension and companion members are `Function` nodes; companion nests under the class, extension is `Receiver.name` | `top`, `Plain.m`, `Plain.make` (companion nested under `Plain`), `Single.s`, `I.i`, `Color.hex`, `String.shout` (extension). okhttp: `Dispatcher.wrap` (extension, `DeprecationBridge.kt:26`), `Dispatcher.dispatch`, 6317 `Function` nodes | ✅ pass |
| AC-2.1 | Fixture: `Use.kt` imports `com.a.Plain`, `com.a.helper`, `kotlin.collections.List`, `okhttp3.Foo`; `Wild.kt` imports `com.a.*`; `Amb.kt` imports `com.amb.Dup` defined in two files. okhttp: counted `imports` edges, read samples | Class and top-level-fun imports link files; wildcard links the package's files; stdlib/third-party none | `Use.kt` -> `Models.kt`, `Util.kt` only (stdlib and third-party: no edge). `Wild.kt` -> `Models.kt` and `Util.kt`. `Amb.kt`: no edge (ambiguous FQN). okhttp: 1785 `imports` edges, e.g. `MainActivity.kt` -> `AndroidPlatform.kt`, all `extracted` | ✅ pass |
| AC-3.1 | `grep` `pyproject.toml` and README. Built fixture twice (incremental then `--full`) and `cmp`. Built okhttp copy three times (cached, `--full`, cache deleted) and `cmp`. Suite, slow tests | Grammar pinned `==`, byte-identical double build, README lists Kotlin | `pyproject.toml:46` `tree-sitter-kotlin==1.1.0`. README:272 lists Kotlin. fixture `IDENT`; okhttp `IDENTICAL` and `IDENT_FRESH` (8170 entities). `uv run pytest -q` 407 passed, 4 deselected. `uv run pytest -m slow` 4 passed: fresh-install, NFR-1 bench, MCP stdio transport, sdist manifest | ✅ pass |
| NFR-1 (CLAUDE.md incremental bench) | `uv run pytest -m slow -k bench` rerun alone | Incremental at least 50% faster | Passed in the full slow run and again alone (1 passed, 9.56s); no flake seen this time | ✅ pass |
| Fresh install | `tests/test_fresh_install.py` (in slow set): builds wheel, installs into a venv without the lock, boots `serve` | Wheel installs and MCP server boots | PASSED (network was reachable in this container; nothing skipped, `-rs` shows no skips) | ✅ pass |
| CLI/MCP parity | `server.find_nodes('Dispatcher', repo=okhttp copy)` vs `aspark-graph query find_nodes Dispatcher`; `uv run pytest -q tests/test_cli_mcp_parity.py` | Identical answers | Dicts equal, both `count` 101 with Kotlin `File`/`Class`/`Function` nodes. `impact` via CLI and MCP both returned `HttpUrl.kt` -> `def:...HttpUrl.kt::HttpUrl`, `in_graph: true`. Parity tests 28 passed | ✅ pass |

## 3. Exploratory Findings

| # | Severity | Steps to reproduce | Expected vs. observed | Status |
|---|---|---|---|---|
| B1 | Minor | Make `a.kt`: `package a` / `class P {` / ` companion object { fun make() = 1 } }` / `fun top() {}`. Run `extract` (or build and `find_nodes top`) | Expected `P`, `P.make`, `top`. Observed `P`, `P.make` only: `top` (and in a longer fixture also `D`, `Single`, `I`, `Color`, `String.shout`) are silently dropped; the grammar puts the rest of the file into one `ERROR` node and `_walk` skips it. No wrong parent, so the "missing, never misplaced" rule holds, but README:272-281 does not name this trigger (a one-line companion whose closing `}` shares its line with the class's `}`). Normal formatting (`companion object {` on its own lines) extracts everything | open |
| B2 | Info | Broken file `class Broken { fun ( {{{ ` / ` fun ok() {}` | `Broken` extracted, `ok` absent, no crash. Matches the stated honest-absence behavior, no defect | n/a |

Other probes, all as expected: `.kts` file yields `File` plus `conf`; empty `.kt` yields a `File` node and no definitions; binary garbage in `.kt` does not crash the build; ambiguous FQN gives no edge; wildcard import links both package files.

## 4. Console & Network

N/A, no browser. Build output was clean on every run (no traceback, no stderr warnings beyond the normal "Built graph" lines). The okhttp scratch clone already carried an `.aspark-graph/` before my copy; I removed it only in my copy and never wrote to the clone or to `/workspace/repo` outside this file.

## 5. Verdict

Would I demo this to a stakeholder right now? Yes. Every AC (AC-1.1, AC-1.2, AC-1.3, AC-2.1, AC-3.1) was performed and passed with the observables above, the full suite (407) and slow set (4) pass, builds are byte-identical on a 619-file real Kotlin repo, and CLI and MCP agree. One Minor is open (B1); I did not waive it and cannot accept it, only the user can.

---

## ✅ QA GATE

*All boxes checked → `/go-live` may start. Any box open → back to `/increment`, then re-run
`/demo-day`. On re-test, edit this same checklist in place — never duplicate it as a second gate.*

- [x] Every Must-story acceptance criterion verified by the §8 substitute method and passed (AC-1.1, AC-1.2, AC-1.3, AC-3.1; Should AC-2.1 also passed)
- [x] Every browser-observable NFR verified and passed (none browser-observable; NFR-1 bench and fresh install passed)
- [x] No open Blocker or Major bugs (Minor B1 listed; not yet accepted by the user)
- [x] Browser console free of errors on the tested flows (N/A, headless; build output clean)
- [x] Tested on all agreed viewports (N/A, headless)
- [x] Line budget respected: Ist 71 / Soll ~130 (excluding HTML comments) — self-reported, no linter checks this
- [x] Status set to `passed`
