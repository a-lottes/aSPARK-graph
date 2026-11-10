# QA Report: kotlin-support

| | |
|---|---|
| **Phase** | Review (hands-on) |
| **Owner** | QA Tester (`/demo-day`) |
| **Input** | Branch `factory/issue-34` at `fc91736` (working tree: only `.spark/kotlin-support/*.md` modified), `.spark/kotlin-support/spec.md` (approved) |
| **Status** | `passed` |
| **Round** | 1 |
| **Date** | 2026-11-10 |

<!-- Handoff: read this block first, the numbered sections below by exception. Whoever
     writes to this report updates it in the same edit that closes or re-rules a bug:
     overwrite in place, never append. The block holds one current state, never a
     per-round log; a stale block is a defect, not a cosmetic issue.

     Re-test: bump `Round` yourself (only the owner bumps it) at the start of the pass,
     then overwrite every section below in place — §1 Test Environment, §2 AC
     Verification, §3 Exploratory Findings, §4 Console & Network, §5 Verdict and the
     gate checklist all hold exactly one current state, never a `## Round N` heading or
     a second gate. History lives in git, not in this file. -->

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Verdict:** Yes. Every AC and every QA-owned NFR passes hands-on through the real CLI and a live MCP stdio server on scratch Kotlin repos; non-Kotlin repos build byte-identical to pre-change code.
- **Open:** `1 open` — Blockers: none; Majors: none (Minor B1, the documented one-line-class-body grammar limit, accepted at spec A7)
- **Binding ruling:** §5 Verdict and the gate checklist below — the only binding location; there is no other round to point to
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/demo-day` and proceed — don't stop on it.

## 1. Test Environment

- **App URL / browser / viewports:** N/A. `aspark-graph` is a headless Python CLI plus an MCP stdio server. `.spark/constitution.md` §8 declares `Browser-observable surface: no` with a substitute method; this pass performed it. **Override:** browser check skipped, authorizer `CLAUDE.md project rule (headless tool)`, reason: no UI exists, so a browser check is structurally N/A ("QA gate for this headless tool"). Nothing was tested by reading source.
- **Under test:** `/tmp/venv/bin/aspark-graph` (editable install of this checkout, Python 3.13, `tree-sitter-kotlin` 1.1.0) at `fc91736`; Linux.
- **MCP:** a real `aspark-graph serve` subprocess driven by the `mcp` stdio client (9 tools listed).
- **Test data (all scratch, each its own `git init` dir):** `/tmp/kt-qa` (classes, data class, object, interface, enum, companion, extension fun, local fn, private/internal, wildcard/explicit/member/extension/stdlib imports, `.kts`, comment-only and package-only files, a `.rb`), `/tmp/kt-qa2` (isolated one-import-per-file resolution cases plus a malformed `.kt`), `/tmp/kt-qa3` (seven-language mix), `/tmp/kt-qa4` (copy of this feature's `.spark/` trail with a plan task `files:` retargeted to a `.kt` file), `/tmp/nk` (no Kotlin), `/tmp/kt5` (one-line class bodies, 3 MB random `.kt`).
- **aspark-graph tool file:** none passed; scoped by hand from the spec.

## 2. Acceptance Criteria Verification

| Spec ID | Steps performed | Expected | Observed | Result |
|---|---|---|---|---|
| AC-1.1 | `build .` on `/tmp/kt-qa`; read graph.json | `.kt` and `.kts` are `File` nodes, `language=kotlin`, no `unparsed` | 9 File nodes incl. `build.gradle.kts`, `settings.gradle.kts`; all `language: kotlin`, no `unparsed` key | ✅ pass |
| AC-1.2 | Same; `Plain`, `Point` (data), `Registry` (object), `Greeter` (interface), `Color` (enum), `Owner` | `Class` node per kind, `contains` from File, `extracted` | all 6 kinds are `Class` nodes with a `file:` → `def:` `contains` edge, confidence `extracted` | ✅ pass |
| AC-1.3 | Top-level `topLevel`, `topLevelFn`, `internalFn`, `main` | `Function` node, `contains` from File | all present, edge from their File only | ✅ pass |
| AC-1.4 | `Plain.hello`, `Point.norm`, `Registry.register`, `Greeter.greet`, `Owner.member` | nested under owning `Class` via `contains` | each has `def:…::Class` → `def:…::Class.fn` `contains` edge | ✅ pass |
| AC-1.5 | `Owner` with `companion object { fun create() }` | no companion node; `create` under `Owner` | no `Companion` node; `Owner.create` with edge from `Owner` | ✅ pass |
| AC-1.6 | `fun String.shout()` in two files | node `String.shout`, edge from own File, no dangling edge | `def:src/a/b/Types.kt::String.shout` and `def:src/ext/Ext.kt::String.shout`, each with `contains` from its own File; dangling-edge scan on 2 graphs: 0 | ✅ pass |
| AC-1.7 | `Point.norm` contains `fun localHelper()` | no node for it | no `localHelper` node in graph | ✅ pass |
| AC-1.8 | `private class Hidden`, `internal fun internalFn`, public others | `exported` false / true | `Hidden` and `internalFn` `exported: false`; all others `true` | ✅ pass |
| AC-1.9 | `Only.kt` (`package only.pkg`), `Empty.kt` (comment only), `build.gradle.kts` (comment only) | File node, zero definitions, no `unparsed` | 3 File nodes, 0 `contains` edges, no `unparsed`; `Only.kt` carries `package: only.pkg` | ✅ pass |
| AC-1.10 | `build .` then `build . --full`; `cmp` graph.json | byte-identical | `cmp` equal (31 code entities both) | ✅ pass |
| AC-2.1 | `/tmp/kt-qa2`: `U1.kt` `import a.b.C`; `p/C.kt`, `p/D.kt` in `package a.b` | `imports` edge, `extracted` | `U1.kt → p/C.kt extracted` | ✅ pass |
| AC-2.2 | `U4.kt` `import a.b.*` | edge to each file of `a.b` | `U4 → C.kt` and `U4 → D.kt` | ✅ pass |
| AC-2.3 | `U2.kt` `import a.b.D.member` and `import a.b.topFn`; in `/tmp/kt-qa` `import a.b.Owner.Companion.create`, `import ext.shout` | trailing segments stripped to a repo file | `U2 → D.kt`; `Main.kt` edges to `Types.kt` (Owner), `Extra.kt` (topLevelFn), `Ext.kt` (extension by bare name) | ✅ pass |
| AC-2.4 | `U3.kt`: `kotlin.collections.List`, `androidx.core.app.X`; `Main.kt` same | no edge, build succeeds | no `imports` edge from `U3.kt`; rc 0 | ✅ pass |
| AC-2.5 | `U3.kt`: `nope.pkg.Missing`, `a.zzz.Q` | no edge, no guess | none; the only 4 edges in the graph are the resolvable ones above | ✅ pass |
| AC-3.1 | Inspect `pyproject.toml:46`, `uv.lock` | `tree-sitter-kotlin==1.1.0` pinned, locked | `"tree-sitter-kotlin==1.1.0"`; `uv.lock` has the package and `specifier = "==1.1.0"`; installed module imports | ✅ pass |
| AC-3.2 | List `tests/`; run suite | file exists, covers the listed cases | `tests/test_extractor_kotlin.py` exists (15 tests); full suite green (see AC-3.7) | ✅ pass |
| AC-3.3 | `/tmp/kt-qa3`: `.py .ts .js .java .go .rs .kt .kts` plus `.rb`; `build`, read File nodes | every file tagged, has definitions, none `unparsed`; `.rb` skipped | 8 File nodes (each language-tagged, 1+ `contains` edge, no `unparsed`), no `.rb` node. Note: the suite's `test_double_build_six_language_repo_is_deterministic` has Kotlin but no JS; my run covers JS | ✅ pass |
| AC-3.4 | In-process `_REGISTRY.pop("kotlin")` then `build_graph(full=True)` on `/tmp/kt-qa3` (not an edit of the code) | `.kt`/`.kts` → `unparsed: true`, build ok; `.rb` skipped | `F.kt`, `g.kts` `unparsed: True`, rc ok; no `.rb` node. (A first attempt without `full=True` hit the parse cache and showed parsed nodes; expected cache behaviour, not a bug) | ✅ pass |
| AC-3.5 | Read `README.md` | Kotlin in "Supported languages" and guarantees; one-line-body limit stated | `README.md:272` lists Kotlin, `:273` states the one-line class body caveat, `:298` and `:320` list Kotlin | ✅ pass |
| AC-3.6 | `grep -i kotlin` in `cli.py`, `server.py`, `queries.py`; `/tmp/kt-qa4`: `find_nodes Owner`, `impact Types.kt`, `story_trace US-1` via CLI and MCP | 0 hits; results identical | 0 hits; MCP JSON equals CLI JSON for all 3 (`True`/`True`/`True`); `impact` on the `.kt` file returns US-3 and its ACs at `declared` | ✅ pass |
| AC-3.7 | `pytest -q` and `pytest -q -m slow` | zero regressions | 402 passed; slow 4 passed | ✅ pass |
| NFR-1 | Double build (AC-1.10); worktree of pre-change `dd4b994` vs current on a repo with py/ts/js/java/go/rs and no Kotlin | byte-identical | `cmp` equal (`NOKOTLIN_IDENTICAL`); pin is `==` (AC-3.1) | ✅ pass |
| NFR-2 | Scripted dangling-edge scan on `/tmp/kt-qa`, `/tmp/kt-qa2`; unresolved imports | 0 dangling, 0 guessed edges | 0 and 0 | ✅ pass |
| NFR-3 | Read confidence of every `contains`/`imports` edge in graph.json | all `extracted` | every edge `extracted`; no new tier | ✅ pass |
| NFR-4 | Grep adapters (AC-3.6); build malformed `q/Bad.kt` and a 3 MB random-byte `.kt` | no Kotlin branching; no traceback | 0 grep hits; both builds rc 0, no traceback | ✅ pass |
| NFR-5 | `pytest -m slow` incl. incremental benchmark | passes unmodified | 4 passed | ✅ pass |
| NFR-6 | Same slow run (`test_fresh_install.py` unlocked wheel boots `serve`, `test_packaging.py` sdist manifest); live `serve` boot over stdio | boots; manifest test green | 4 passed; MCP server initialised and answered 3 queries | ✅ pass |
| NFR-7 | N/A per spec | N/A | N/A | N/A |
| NFR-8 | N/A per spec; `language` field visible in graph.json | N/A | N/A (field observed: `kotlin`) | N/A |

## 3. Exploratory Findings

| # | Severity | Steps to reproduce | Expected vs. observed | Status |
|---|---|---|---|---|
| B1 | Minor | `printf 'class A { fun m() {} val x = 1 }\nclass Ünï { fun é() {} }\n' > O.kt` in a `git init` dir; `aspark-graph build .`; read graph.json | Expected `A`, `A.m`, `Ünï`, `Ünï.é`. Observed only `def:O.kt::m` (parentless); classes `A` and `Ünï` and `é` missing. This is the grammar limit the spec accepts (A7, C4) and the README documents (AC-3.5); no crash | open |

Probed, no bug: malformed `.kt` (unbalanced braces, bare `fun`, `import ???`) builds, rc 0, File node kept; 3 MB random bytes `.kt` builds rc 0; incremental then `--full` rebuild equal; Unicode identifiers in a well-formed multi-line class not probed beyond B1; `.rb` file skipped as before; empty-string `find_nodes ""` still returns the guarded empty result.

## 4. Console & Network

No browser, console or network surface. Equivalent: stderr, exit codes, MCP results. Every build exited 0; no traceback anywhere. The MCP server logged only `Processing request` lines. No `isError` result. No network used.

## 5. Verdict

Would I demo this to a stakeholder right now? **Yes.** A scratch Kotlin repo with classes, a data class, object, interface, enum, companion, extension functions, `.kts` files and five import styles builds into exactly the graph the spec describes: extension functions are parentless with no dangling edge, unresolved and stdlib imports add no edge, `impact` on a `.kt` file reaches its story and ACs, and CLI and MCP answers are identical. Double builds are byte-identical and a Kotlin-free repo builds byte-equal to pre-change code. B1 is the documented grammar limit. Not tested: Windows/macOS, Kotlin Multiplatform sources, `.kt` files with `expect`/`actual`.

---

## ✅ QA GATE

*All boxes checked → `/go-live` may start. Any box open → back to `/increment`, then re-run
`/demo-day`. On re-test, edit this same checklist in place — never duplicate it as a second gate.*

- [x] Every Must-story acceptance criterion verified hands-on (CLI and live MCP; substitute for the browser per constitution §8 and the CLAUDE.md headless rule, §1) and passed
- [x] Every QA-relevant NFR verified and passed (NFR-1–6; NFR-7/8 N/A per spec)
- [x] No open Blocker or Major bugs. Minor B1 is the accepted, documented grammar limit (A7)
- [x] Tool output free of unexpected errors on the tested flows (no traceback)
- [x] Tested on all agreed surfaces (CLI, MCP stdio; no viewports apply)
- [x] Line budget respected: Ist 78 / Soll ~130 (excluding HTML comments)
- [x] Status set to `passed`
