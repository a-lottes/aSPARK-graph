# Review Report: kotlin-support

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | `git diff dd4b994..c1625f8` (2bcdf98, c1625f8), `.spark/kotlin-support/plan.md` |
| **Status** | `passed` |
| **Round** | 1 |
| **Date** | 2026-11-10 |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Verdict:** Pass. Every Must AC traces to code and a test that fails when the code breaks. Pre-change determinism re-proven byte-identical. Four low-risk fixes applied by the reviewer. No Blocker or Major.
- **Open:** `6 open` — Blockers: none; Majors: none (Minors/Nits: F5–F10, see §3)
- **Binding ruling:** §6 Verdict and the gate checklist below — the only binding location; there is no other round to point to
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Scope

- **Reviewed:** the whole diff `dd4b994..c1625f8`: `extractors/code_kotlin.py` (new), `extractors/base.py`, `extractors/__init__.py`, `build.py` (Kotlin index and resolver), `parse_cache.py`, `pyproject.toml`/`uv.lock`, `README.md`, and the tests in `test_extractor_kotlin.py`, `test_extractor_java.py`, `test_build.py`, `test_incremental.py`, `test_cli_mcp_parity.py` and `test_readme.py`. Lens: `cli` (constitution §2).
- **Graph tool:** not used. I scoped by hand with grep and Read (CLAUDE.md fallback). The diff is small and touches only the extractor seam.
- **Hands-on evidence (re-derived, condition (b): Must-AC verification):**
  - **T12 pre-change determinism.** I built `tests/fixtures/sample_repo` (0 `.kt` files, `.git`-marked copy in `/tmp`) under a `dd4b994` worktree and under HEAD. Both `graph.json` files are 7169 B, sha256 `7a82e69c…2d2296`, and `cmp` finds them identical. I also built a full clone of this repo at c1625f8 with both code versions: sha256 `b36857a1…d561`, identical.
  - **Kotlin fixture through the CLI** (two packages, an extension import, an alias import, a stdlib import, a malformed `.kt` and a 6 MB `.kt`). `build` exits 0, the summary goes to stdout and stderr carries only the no-git note, with no traceback. The 6 MB file becomes `unparsed_reason="size"`. There is exactly one `imports` edge (`Screen.kt`→`Strings.kt`, `extracted`).
  - **Extractor edge cases probed:** ERROR nodes, a MISSING name, backtick identifiers, `fun interface`, `enum class` with entry bodies, local and anonymous functions, `value class`, `annotation class`, `sealed interface` with `data object`, nullable/generic/qualified receivers, CRLF, BOM, `.kts` scripts and one-line forms.
- **Not reviewed:** a real third-party Kotlin/Android repo. There is no network, so I used a synthetic multi-package fixture instead.

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ | `tree-sitter-kotlin==1.1.0` in `pyproject.toml:46`, and `uv.lock` agrees. `.kt`/`.kts` are mapped in `base.py:56-57` and the extractor is registered in `__init__.py:25` |
| T2 | ✅ | `code_kotlin.py:57-104`. Class kinds, member/nested, companion and extension handling all work as specified |
| T3 | ✅ | Wildcard marked `.*` (`code_kotlin.py:122`). The double-build test includes `f.kt` |
| T4 | ✅ | `build.py:307-337` uses an exact key and `len(files) != 1` → None. The nested-class test was flipped to expect no edge |
| T5 | ✅ | The alias needed no code change because `qualified_identifier` excludes `as H`. Tests exist at the extractor and build level |
| T6 | ✅ | Empty, package-only and malformed cases, plus the CLI exit code and no-traceback check (`test_extractor_kotlin.py:189-209`) |
| T7 | ✅ | Sealed class, named companion, member extension, and an `EXTRACTED` + endpoint integrity loop |
| T8 | ✅ | `parse_cache.py:44`. The incremental unregistered→registered test checks `reparsed==1`, `cached==1` and that the `.py` node is equal |
| T9 | ✅ | Seven languages including `.js`. The function name was changed from `six` to `seven`. This is a test rename, not a deviation |
| T10 | ✅ | Parity for `find_nodes`/`impact`/`story_trace`, plus an assertion that `cli.py`/`server.py` have no `kotlin` branch |
| T11 | ⚠️ | The README states the limits, but its one-line example was wrong. Fixed (F2) |
| T12 | ✅ | Evidence re-derived by me (see §1). The slow suite: 3 of 4 tests pass deterministically. The NFR-1 bench is flaky on both the old and the new code (F7) |
| T13 | ✅ | `test_unknown_extension_is_handled_as_before`. README line corrected (C9) |

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Minor | `extractors/code_kotlin.py:41-47` | `_name` accepted a tree-sitter MISSING (zero-width) identifier. Malformed input such as invalid UTF-8 after `class` produced a `Class` with qualname `""` (`def:x.kt::`), and its members got `parent=""`. That is a junk node under AC-1.10's "what the parser can still recognise". Fix: return None when the name node `is_missing` or is empty. Regression test `test_missing_name_from_error_recovery_yields_no_definition` fails on the old code. | fixed |
| F2 | Minor | `README.md:277-279` | The known-limit example `class A { fun m() {} }` parses **correctly** with grammar 1.1.0 (probed), so the documented limit cited a non-example. A real misparse is `class A { companion object { fun c() {} } }`: `A` is dropped and `c` becomes a top-level `Function`. That is a misplaced node, not only a missing one. README corrected. Spec A8 and plan T11 cite the same wrong example; that is artifact wording, left for the owners. | fixed |
| F3 | Nit | `extractors/code_kotlin.py:127` | The wildcard check had a redundant text fallback (`b".*" in node.text…`). The grammar always emits an anonymous `*` token, including for `a.b. *`. Fallback removed; `test_wildcard_with_space_before_star_is_still_wildcard` guards the token path. | fixed |
| F4 | Nit | `code_kotlin.py:27,53`; `test_extractor_kotlin.py:107` | The `_PRIVATE` constant was dead because `_exported` repeated the literal; it is now used. The import test asserted the same `Fns.kt` edge twice while its comment claimed a nested-import check. The second assert now checks that there is no edge to `Helper.kt`. | fixed |
| F5 | Minor | `extractors/code_kotlin.py:41-47`, `build.py:322` | Backtick identifiers keep their backticks in the qualname (`` `My Class` ``). Kotlin treats `` `Foo` `` and `Foo` as the same name, so `import p.Foo` misses a file that declares `` class `Foo` ``. The low recall stays honest because no wrong edge is created. Fix: strip enclosing backticks from names and import segments, and decide whether backticked test-function names (with spaces) should keep them. This is a design call, so it is left to the developer. | open |
| F6 | Nit | `extractors/code_kotlin.py:92-96` | A top-level `fun Foo.ext()` and a member `Foo.ext` in the same file share qualname `Foo.ext` and therefore one node id with two `contains` parents. This follows from spec A3 naming. It is rare because Kotlin shadows such an extension. Fix if it ever matters: name extensions `ext` with the receiver held in an attribute. | open |
| F7 | Minor | `tests/test_incremental_bench.py:97` | The NFR-1 bench (≥50% speedup) is flaky in this container. It failed 2 of 4 runs on HEAD (46.1%, 48.9%) and 2 of 4 runs on pre-change `dd4b994` (46.1%, 50.0%). This is not a Kotlin regression, but NFR-6 ("passes unmodified") is only intermittently true. Suggest a BACKLOG item: a more robust bench (larger fixture or a relative margin). | open |
| F8 | Minor | `parse_cache.py:39-45` | Pre-existing since v0.5.0 (plan R6): `_version_tag` omits `tree-sitter-go` and `tree-sitter-rust`, so a bump of either grammar alone would serve stale cached extractions. Out of this spec's scope. Suggest a BACKLOG item; not fixed here. | open |
| F9 | Minor | `.spark/constitution.md:39`; `CLAUDE.md` (intro, layout, "five languages", test count 319) | The docs still say "five grammars" / five languages. The constitution belongs to the user, via `/charter`. CLAUDE.md should be updated at `/go-live` along with the trail entry. Artifact wording, so capped at Minor. | open |
| F10 | Minor | process, issue tracker | Duplicate tickets #13 and #23 exist for this same feature (the spec is #25). Close them as duplicates of #25 at `/go-live` so the backlog doesn't double-count. | open |

## 4. Requirements Traceability

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | `code_kotlin.py:60-63`; `test_build_level_file_node_and_kts_contains` | ✅ met |
| AC-1.2 | `code_kotlin.py:72-75` (`script`/`statements`); same test, plus `test_kotlin_script_file_extracted` | ✅ met |
| AC-1.3 | `code_kotlin.py:26,66`; `test_kotlin_extractor_finds_package_classes_functions`, `test_sealed_…` | ✅ met |
| AC-1.4 | `code_kotlin.py:98-102`; `("top","Function",None)` asserted | ✅ met |
| AC-1.5 | `code_kotlin.py:78-86`; `Widget.render`, `Widget.Nested`; `test_build_contains_edges_for_kotlin` | ✅ met |
| AC-1.6 | `code_kotlin.py:68-69`; plain and named companion tests | ✅ met |
| AC-1.7 | `code_kotlin.py:92-93`; the endpoint-integrity loop | ✅ met |
| AC-1.8 | `code_kotlin.py:50-54`; `test_kotlin_private_is_not_exported` (class level probed too) | ✅ met |
| AC-1.9 | `test_empty_and_package_only_kotlin_files_are_parsed_files` | ✅ met |
| AC-1.10 | `ERROR` walked at `code_kotlin.py:72`; malformed test and CLI exit 0; F1 fixed | ✅ met |
| AC-1.11 | `test_double_build_six_language_repo_is_deterministic` (includes `.kt`) | ✅ met |
| AC-2.1–2.5 | `build.py:307-337`; the class/object/interface/fun, extension, ambiguous, nested and alias tests | ✅ met (Should) |
| AC-3.1 | `test_all_seven_languages_in_one_build` | ✅ met |
| AC-3.2 | `test_unknown_extension_is_handled_as_before` (spec C9) | ✅ met |
| AC-3.3 | `uv run pytest`: 414 passed (412 before the reviewer's tests) | ✅ met |
| AC-3.4 | `test_kotlin_queries_cli_equals_mcp`; `cli.py`/`server.py` untouched by the diff | ✅ met |
| AC-3.5 | `test_kotlin_registered_after_unregistered_build_is_parsed_once` | ✅ met |
| AC-4.1 / 4.3 | `README.md:272-282,303`; `test_kotlin_support_ac_4_1_4_3_…` | ✅ met (example fixed, F2) |
| AC-4.2 | `pyproject.toml:46`; the `uv.lock` entry for `tree-sitter-kotlin` 1.1.0 | ✅ met |
| NFR-1 | Pin, double build, and the stash/worktree round-trip identical (§1) | ✅ |
| NFR-2 / NFR-3 | Endpoint and `extracted` loop test; CLI fixture shows a single `extracted` import edge | ✅ |
| NFR-4 | Parity test, plus the no-`kotlin` grep in the adapters | ✅ |
| NFR-5 | 22 Kotlin tests at Java-test granularity or finer | ✅ |
| NFR-6 | The bench passes intermittently on both the old and the new code (F7) | ⚠️ |
| NFR-7 | Offline parse only. Confinement is generic. 6 MB `.kt` → `size`. `test_packaging` and `test_fresh_install` pass (slow) | ✅ |
| NFR-8 / NFR-9 (cli lens) | No new flag or exit code. stdout/stderr discipline holds and a malformed `.kt` exits 0. The only addition is the `language` value `"kotlin"` | ✅ |

## 5. What Was Checked

- [x] Correctness: logic does what the acceptance criteria demand
- [x] Non-functional: applicable NFRs and constitution quality bars hold (NFR-6 flaky on both sides, F7)
- [x] Error handling: failures are handled, not swallowed (malformed input is tolerated, no new error class)
- [x] Security: no injected input trusted, no secrets in code (offline parse, size cap, confinement)
- [x] Tests: exist, are meaningful, and pass (the F1 test was shown to fail on the pre-fix code)
- [x] Readability: the next developer will understand this

## 6. Verdict

The Kotlin extractor is a clean, data-driven addition that follows the Go/Rust pattern: no adapter code, an exact `==` pin, and an import index that gives honest absence for wildcard, nested, ambiguous and stdlib imports. I re-derived the Must evidence myself rather than taking it from the plan. Building a non-Kotlin fixture and this repo's own clone under `dd4b994` and under HEAD gave byte-identical `graph.json` files. The full suite is green (414 passed). The slow suite passes except for a timing bench that is equally flaky on the pre-change code. Probing the extractor turned up one real defect, F1: a MISSING identifier became an empty-named `Class`. I fixed it with a regression test that fails on the old code. I also found that the README's one-line-limit example was false (F2, fixed). Two nits are fixed as well (F3, F4). What remains open is Minor or Nit and does not block: backtick-identifier recall (F5), the extension/member id collision (F6), bench flakiness (F7), the pre-existing Go/Rust cache-tag gap (F8, BACKLOG), stale "five" wording in the constitution and CLAUDE.md (F9), and duplicate tickets #13/#23 (F10). No Blocker or Major remains, so the gate passes. Anti-generosity standard: not passed to this run, so not applied by name. Severities were set on observed behaviour only.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`. On
re-review, edit this same checklist in place — never duplicate it as a second gate.*

- [x] No open Blocker findings
- [x] No open Major findings (or explicitly waived by the user, with reason recorded here)
- [x] Every Must AC traces to implementing code; no constitution non-negotiable violated
- [x] All plan deviations documented and accepted (T11 example corrected, F2)
- [x] Test suite runs green (414 passed; slow: 3/4 green, NFR-1 bench flaky pre- and post-change, F7)
- [x] Line budget respected: Ist ~120 / Soll ~150 (excluding HTML comments), self-reported
- [x] Status set to `passed`
