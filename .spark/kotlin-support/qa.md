# QA Report: kotlin-support

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review (hands-on) |
| **Owner** | QA Tester (`/demo-day`) |
| **Input** | Running CLI/MCP tool (no URL), `.spark/kotlin-support/spec.md` (the acceptance criteria) |
| **Status** | `passed` |
| **Round** | 1 |
| **Date** | 2026-11-10 |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Verdict:** Yes, I would demo this now: every AC and NFR was exercised against the real tool, no Blocker/Major found.
- **Open:** `none` (Minors B1-B3: see §3)
- **Binding ruling:** §5 Verdict and the gate checklist below — the only binding location; there is no other round to point to
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/demo-day` and proceed — don't stop on it.

## 1. Test Environment

- **App URL:** N/A. Headless CLI/MCP tool. `.spark/constitution.md` §8 declares `Browser-observable surface: no` and a substitute method (full suite + slow tests, clean-env wheel install, `serve` boot, byte-identical double build, real-repo check); that method was performed. Browser, URL and viewports are N/A; steps 5/6 (console/network) have no analogue.
- **Mode (anti-generosity §3):** live runs of the real tool (`uv run aspark-graph ...`, in-process `aspark_graph.server`, stdio `serve` via slow test) at HEAD `218aa5f`, branch `factory/issue-25`. No code reading was used as evidence. Anti-generosity standard applied (`/opt/aspark/standards/anti-generosity.md`).
- **Test data:** scratch repos under `/tmp` each with a `.git` marker: `kt1` (Android-style: 4 packages, data/sealed/enum/interface/object/companion/named companion, member and top-level extension, `build.gradle.kts`, empty file, package-only file, malformed file, duplicate-package twins, `.rb`); `kt_i1..i7` (one import form each); `kt_m` (malformed, one-line, 6 MB `.kt`, `.rb`); `kt_o` (one-line companion, private class, backticks); `poly` (one file per language + `.rb`); `nokt`/`mig` (pre-change comparison built from a `dd4b994` worktree, since removed).

## 2. Acceptance Criteria Verification

| Spec ID | Steps performed | Expected | Observed | Result |
|---|---|---|---|---|
| AC-1.1 | `build /tmp/kt1`; inspect graph.json `File` nodes | `.kt` File, language kotlin, package set, no `unparsed` | `Models.kt`: `language=kotlin, package=com.example.model`, no `unparsed` key; same for all 9 Kotlin files | ✅ pass |
| AC-1.2 | `app/build.gradle.kts` with `fun greet()` + a call | kotlin File, Function via `contains` | `file:app/build.gradle.kts` kotlin, not unparsed; `def:...::greet` with `file -> def contains` | ✅ pass |
| AC-1.3 | `Models.kt` has data class, sealed class, enum class, interface, object, class | 6 `Class` nodes, file `contains`, `extracted` | `User, Result, Color, Repo, Registry, Host, Host2` all Class, each `file contains` edge `confidence=extracted` | ✅ pass |
| AC-1.4 | top-level `fun hidden()`, `fun greet()` | Function, file `contains` | `Helper.kt::hidden` and `greet` have `file contains def` edges, no class parent | ✅ pass |
| AC-1.5 | `Helper.help`; `sealed class Result { class Ok { fun value } }` | member nests under class; nested class under outer | edges `Helper contains Helper.help`, `Result contains Result.Ok`, `Result.Ok contains Result.Ok.value` | ✅ pass |
| AC-1.6 | `Host { companion object { make } }`; `Host2 { companion object Factory { build } }` | `Host.Companion` + `Host.Companion.make`; named uses its name | `Host.Companion`, `Host.Companion.make`, `Host2.Factory`, `Host2.Factory.build`; chained `contains` edges | ✅ pass |
| AC-1.7 | top-level `fun String.shout()`; member `fun String.ext()` in `Host2` | `String.shout` contains from own file, no dangling edge | `def:Helper.kt::String.shout` with `file:Helper.kt contains` it; member is `Host2.String.ext` under `Host2`; dangling-endpoint scan over all edges of `kt1` = `[]` | ✅ pass |
| AC-1.8 | `private fun hidden`, `private class Priv`, public others | `exported` false/true | `hidden: False`, `Priv: False`; `shout`, `Helper`, others `True` | ✅ pass |
| AC-1.9 | empty `Empty.kt`; `OnlyPkg.kt` (package + comment) | File, zero defs, not unparsed | `Empty.kt` kotlin File (hash of empty), no package, no defs; `OnlyPkg.kt` package `com.example.only`, no defs; neither unparsed | ✅ pass |
| AC-1.10 | `Bad.kt` (broken parens, `class ???`), `Mal.kt` (good class, `fun broken( {`, later decls) | no raise, no traceback, recognisable decls kept | exit 0, stderr empty, no traceback. `Mal.kt`: `Good`, `Good.a` kept; `later`/`After` after the break are lost (B1). `Bad.kt`: File node, no defs | ✅ pass |
| AC-1.11 | build `kt1` twice, then `--full`; `cmp` | byte-identical | `BYTE_IDENTICAL` and `FULL_IDENTICAL`; sha256 `5ed841ac3d2bcc3f5587ef36ff6d456bb34578672a48f4f65db1028e277b0b1f` | ✅ pass |
| AC-2.1 | `kt_i1`: `import com.example.util.Helper` vs `B.kt` declaring it; also top-level `fun` import (`kt_i7`) | extracted `imports` A -> B | `A.kt -> B.kt extracted` in both | ✅ pass |
| AC-2.2 | `kt_i3`: `import kotlinx.coroutines.launch`; `kt1` also imports `kotlin.collections.List` | no edge, no error | `imports: []`, exit 0, stderr empty | ✅ pass |
| AC-2.3 | `kt_i4`: `import com.example.util.*` | no edge | `imports: []`. Isolated, so not masked by another import | ✅ pass |
| AC-2.4 | `kt_i6`: two files declare `com.example.util.Helper` (+ `kt1` Dup1/Dup2 `Twin`) | no edge | `ambig imports: []`; `Main.kt` has no edge to Dup1/Dup2 | ✅ pass |
| AC-2.5 | `kt_i2`: `import com.example.util.Helper as H` | same edge as un-aliased | `A.kt -> B.kt extracted`. Nested `Helper.Inner` (`kt_i5`): no edge, as spec A5 says | ✅ pass |
| AC-3.1 | `poly`: py, ts, js, java, go, rs, kt (+ rb) | all language-tagged, defs, none unparsed | 7 File nodes: python, typescript, javascript, java, go, rust, kotlin; none unparsed; 15 defs; `.rb` absent | ✅ pass |
| AC-3.2 | `.rb` in `poly`, `kt1`, `kt_m` | no File node, build ok | `.rb` never appears; exit 0. A known language with no extractor path untouched (`Big.kt` over 5 MB is `unparsed` + counted as skipped: same cap as other files) | ✅ pass |
| AC-3.3 | `uv run pytest` | green | `414 passed, 4 deselected in 17.38s` | ✅ pass |
| AC-3.4 | `find_nodes Helper` and `impact <Helper.kt>` via CLI vs in-process `server.find_nodes`/`server.impact` on `kt1`; grep `cli.py`/`server.py`/`queries.py` | identical; no Kotlin branch | both parities `True`; `git diff dd4b994 HEAD` on those three files = 0 lines; no "kotlin" match. `server.find_nodes("")` returns the empty guard result | ✅ pass |
| AC-3.5 | build `mig` with pre-change code, then incremental with new code | no stale entry; other languages unchanged | cache rejected by tag (`tree-sitter-kotlin=1.1.0` added) -> full rescan; `G.kt` kotlin, not unparsed, defs `K`, `K.m`; changed non-Kotlin nodes `[]`; next run `0 re-parsed, 7 cached`; incremental graph equals `--full` (`INCR_EQ_FULL`). Old code skipped `.kt` entirely, so no unparsed entry existed to go stale | ✅ pass |
| AC-4.1 | read README | Kotlin (`.kt`, `.kts`) named in Supported languages and guarantees list; no numeric count | README:272-276 (languages), 304 (grammars), 326 (support list); `test_readme.py` included in the green suite | ✅ pass |
| AC-4.2 | read `pyproject.toml`, `uv.lock` | `==` pin, lock agrees | `pyproject.toml:46` `tree-sitter-kotlin==1.1.0`; `uv.lock:680-682` version `1.1.0` | ✅ pass |
| AC-4.3 | read README + reproduce limits | wildcard and one-line limits stated and true | README:276-279 states both. Wildcard behaviour reproduced (AC-2.3). One-line example `class A { companion object { fun c() {} } }` reproduced exactly as documented (`kt_o`: only top-level `c`, class dropped). The spec's own example `class A { fun m() {} }` parses fine (`kt_m/OneLine.kt` gives `Z`, `Z.m`); see B2 | ✅ pass |
| NFR-1 | Exact pin (AC-4.2); AC-1.11; no-Kotlin repo `nokt` built with `dd4b994` code then HEAD `--full`, `cmp` | identical | `NOKT_IDENTICAL_OLD_vs_NEW`, sha256 `a9273ec31cbacd966a98fde34367a1e158e13f2d978da928a3f844e83fa0e25c` | ✅ pass |
| NFR-2 | endpoint scan of every edge in `kt1`; ambiguous/wildcard cases | no dangling edges, absence for ambiguous | `dangling: []`; AC-2.3/2.4 give no edge | ✅ pass |
| NFR-3 | inspect `kt1` graph.json | all `contains`/`imports` `extracted` | every edge `confidence: extracted`; no new tier | ✅ pass |
| NFR-4 | AC-3.4 evidence | zero Kotlin code in adapters; parity | as AC-3.4 | ✅ pass |
| NFR-5 | `uv run pytest`; `tests/test_extractor_kotlin.py` exists (269 lines) | covers the listed topics | suite green, 414 passed; hands-on checks above independently confirm each topic | ✅ pass |
| NFR-6 | `uv run pytest -m slow -v` | bench passes unmodified | `4 passed`: `test_nfr1_incremental_at_least_50_percent_faster`, MCP stdio round trip, sdist manifest, unlocked fresh-install boot. Bench is flaky in this container per review F7; it passed in this run | ✅ pass |
| NFR-7 | 6 MB `.kt` in `kt_m`; slow packaging and fresh-install tests | cap applies; sdist allowlist holds; boots from unlocked wheel | `Big.kt` -> `unparsed`, "1 file(s) skipped (over size limit)", exit 0; `test_sdist_manifest...` and `test_unlocked_wheel_install_boots_mcp_server` PASSED | ✅ pass |
| NFR-8 | `build` on `kt_m` (malformed) with stdout/stderr split; `--help` hash; `git diff` of `cli.py` | no traceback, exit 0, no new flag | exit 0; stderr empty; stdout 2 lines as today; `cli.py` diff 0 lines, `--help` md5 `428da8d7e4142a8661cf4984b197705d` | ✅ pass |
| NFR-9 | inspect JSON from `find_nodes`/`get_node`/`impact` | only new `language` value | output keys identical to existing shape; only `"kotlin"` appears in `language` | ✅ pass |
| NFR-10 | N/A: no UI | N/A | N/A | N/A |

## 3. Exploratory Findings

| # | Severity | Steps to reproduce | Expected vs. observed | Status |
|---|---|---|---|---|
| B1 | Minor | `Mal.kt`: `class Good{fun a()}`, then `fun broken( {`, then `fun later()` and `class After`; `build` | Expected: recoverable decls kept. Observed: declarations after the syntax error (`later`, `After`) are dropped; those before it kept. Within AC-1.10 tolerance; extraction after an error is not guaranteed | open |
| B2 | Minor | Spec A8 example `class A { fun m() {} }`; build | Spec says it misparses; observed it parses correctly (`Z`, `Z.m`). README was already corrected to the companion-object example (review F2). Spec text is stale: artifact-wording only | open |
| B3 | Minor | `kt_o/P.kt`: ``class `My Class` {}``; build | Name kept with backticks: `` `My Class` ``. Same as review F5 | open |

Also exercised with no defect: `.kts` with top-level statements, 6 MB file, Kotlin next to `.rb`, empty/package-only files, alias, nested-class import, duplicate packages, repeat/incremental/`--full` builds.

## 4. Console & Network

N/A (no browser). Machinery watched instead: stderr on every `build` was empty except the expected one-time `Cache unusable (version mismatch ...)` notice on the first build after the grammar tag changed (`mig`, and dogfood `/workspace/repo`); no tracebacks anywhere. Dogfood `build /workspace/repo`: exit 0, `726 code entities, 589 artifact entities, 218 inferred link(s)`; `staleness` -> `stale: false`. `query gate_health kotlin-support` after rebuilding with this report: 0 unverified ACs, 0 orphan tasks, `healthy: false` only because review findings F5-F10 (Minors/Nits) are still open. Before this report existed it listed every AC as unverified. Stdio `serve` boot passed via `test_mcp_stdio_transport_round_trip`; no network used.

## 5. Verdict

I would demo this to a stakeholder now. Every Must AC (US-1, US-3, US-4) and the Should AC (US-2) was exercised against the real tool and passed, including byte-identical rebuilds, old-vs-new equality on a non-Kotlin repo, cache migration, CLI/MCP parity and the slow suite. Three Minors are open (B1-B3), none blocks a flow. Known environmental risk: the incremental benchmark is flaky in this container (review F7), passed here.

---

## ✅ QA GATE

- [x] Every Must-story acceptance criterion verified (by the §8 substitute method, not a browser) and passed
- [x] Every browser-observable NFR verified and passed (none browser-observable; all other NFRs verified by the declared method)
- [x] No open Blocker or Major bugs (Minor bugs listed; acceptance by the user is pending at `/go-live`)
- [x] Browser console free of errors on the tested flows (N/A, no browser; stderr clean)
- [x] Tested on all agreed viewports (N/A, no UI)
- [x] Line budget respected: Ist ~75 / Soll ~130 (excluding HTML comments) — self-reported
- [x] Status set to `passed`
