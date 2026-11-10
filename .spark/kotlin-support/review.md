# Review Report: kotlin-support

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | The diff of `/increment` (`dd4b994..HEAD`: 215a915, 4c429a1, fix commit fc91736), `.spark/kotlin-support/plan.md` |
| **Status** | `passed` |
| **Round** | 2 |
| **Date** | 2026-11-10 |

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
- **Verdict:** Passed. F1 (Major) is confirmed fixed r2: on okio, extension-function import misses dropped from 421 to 0. No Blocker or Major remains.
- **Open:** `5 open` — Blockers: none; Majors: none (Minors/Nits: see §3 — F2, F3, F4, F10, F11)
- **Binding ruling:** §6 Verdict and the gate checklist below. This is the only binding location; there is no other round to point to.
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Scope

- **Reviewed (r2):** fix commit fc91736. It changes `build.py:290-293` (bare-name index), `code_kotlin.py:128-130` (last receiver segment) and two new tests (`test_extractor_kotlin.py:178-188`). I also re-ran the full QA-equivalent sweep. Rows F1, F3 and F5–F9 were re-verified because this round verifies fixes to them. The other rows were re-checked only by the full suite.
- **Graph (accelerant):** in r1, `impact --diff dd4b994..HEAD` scoped my reading to `build.py::build_graph`/`_resolve_imports`. In r2 the fix touched only the two hunks above, so I read those by hand. No verdict rests on a graph answer.
- **Mode:** live. I ran the full suite and the slow suite, built through the CLI, ran the probes in `/tmp/rvprobe/`, and checked a real repo (square/okio @ `f0e3f479`, 327 `.kt` files). I ran a mutation check: with the F1 fix reverted, the new F1 test fails.
- **Standard:** Anti-generosity standard applied (`/opt/aspark/standards/anti-generosity.md`). No lens files or tool file were passed.
- **Not reviewed:** KMP, annotations and Gradle resolution (spec §6). One-line class bodies are not checked exhaustively (A7 is an accepted risk).

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ | `==1.1.0` pin (`pyproject.toml:46`, `uv.lock:64`); registry and extension map present; adapters are unchanged against dd4b994 |
| T2 | ✅ | Matches plan §1; `ERROR` is walked as a body (`code_kotlin.py:27`) |
| T3 | ✅ r2 | The index now also keys extension functions by their bare name (`build.py:290-293`); F1 fixed r2. This is a documented deviation from plan §1's index description, and it is needed for AC-2.3 |
| T4 | ✅ | All-languages build, six-language double build and Kotlin double build |
| T5 | ✅ | README language list and pin list; `test_readme.py` pins the phrase |
| T6 | ✅ | (a)–(e) present and re-run; the `.rb` skip is tested (F7) |

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Major | `build.py:288-293` | `_kotlin_indexes` keyed an extension function only as `pkg.Recv.name`, but Kotlin imports it as `pkg.name`, so no edge was created. On okio @f0e3f479, 421 imports were unresolved against 434 resolved, which failed AC-2.3. **Fix:** also index `prefix + bare name`. r2: done. okio now resolves 855 imports with 0 extension-function misses. The test `test_build_resolves_extension_function_import_by_bare_name` fails with the fix reverted (mutation check). | fixed r2 |
| F2 | Minor | `build.py:302-303` | A wildcard on a class or object (`import a.b.Reg.*`) only looks in `packages`, so it creates no edge even when `a.b.Reg` is indexed (probe). The edge is absent, never wrong. **Fix:** when `packages` misses, fall back to `index.get(module[:-2])`. The coordinator proposed deferring it (the result is honest absence, not a wrong edge). User acceptance is pending. | open |
| F3 | Minor | `code_kotlin.py:121-133` | The receiver qualname was the first identifier, so `fun kotlin.String.q()` became `kotlin.q`. r2: that part is fixed, and the probe plus a test now give `String.q`. Still open: a function-type receiver gives the raw text `(() -> Unit).run2` (probe r2). **Fix:** use a stable placeholder for non-`user_type` receivers. | open |
| F4 | Minor | `parse_cache.py:37-43` | The cache version tag omits the go, rust and kotlin grammars. A grammar bump in a checkout with an unchanged package version reuses stale extractions. Releases are safe because they bump the version, and the gap is inherited from go/rust. **Fix:** add the three grammars to `_version_tag`. The coordinator proposed deferring it. User acceptance is pending. | open |
| F5 | Minor | `build.py:305-308` | The comment claimed stripping never goes below the package-qualified name, which is false. The comment is corrected, and the behaviour follows the spec's A5 rule. | fixed r2 |
| F6 | Minor | `README.md:275`, `base.py:43-45` | Both said "other languages are recorded as unparsed". They are skipped with no node. Both are corrected. | fixed r2 |
| F7 | Minor | `test_extractor_kotlin.py:121,155,169` | The AC-2.4 assertion was near-tautological, AC-1.9 had no zero-definition check, and the `.rb` half of AC-3.4 was untested. All three are tightened and pass. | fixed r2 |
| F8 | Minor | `CLAUDE.md:8,81` | The language list and the "five grammars" pin rule were stale. Both now say six. | fixed r2 |
| F9 | Minor | `plan.md:22,130-131,144`, `spec.md:33` | Artifact drift: the Handoff said "1 task not done", R4 still said "unsatisfiable", R5 still said "todo", and spec §1 claimed `.kt` files were previously unparsed. r2: the reviewer overwrote all of these in place. The dogfood build still parses both files. | fixed r2 |
| F10 | Minor | `constitution.md:35,39` | The constitution still lists five grammars. Kotlin is pinned `==`, so no non-negotiable is violated. The amendment is deferred to the user (plan §1); I did not edit it. Not blocking. | open |
| F11 | Minor | `build.py:288-293` | New in r2. A *member* extension function (`class A { fun String.dp() }`) also has `parent=None`, so the F1 index treats it as importable `pkg.dp`. Probe: `import lib.dp`, where `dp` is really a `const val` in another file, links to `A.kt`, which is a wrong edge. On okio there are 47 member extensions and 0 imports resolved through one. **Fix:** have the extractor mark top-level-ness (e.g. a `Definition` flag or a parent sentinel) and bare-index only top-level extension functions. | open |

## 4. Requirements Traceability

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | `base.py:57-58`, `build.py:166` | ✅ CLI build: `.kt`/`.kts` are `language=kotlin` and not unparsed |
| AC-1.2 | `code_kotlin.py:26,79-89` | ✅ unit test plus probe; `contains`/`extracted` |
| AC-1.3 | `code_kotlin.py:105-106` | ✅ |
| AC-1.4 | `code_kotlin.py:103-104` | ✅ |
| AC-1.5 | `code_kotlin.py:90-91` | ✅ named and unnamed companion |
| AC-1.6 | `code_kotlin.py:101-102,114-133` | ✅ parentless; 0 dangling edges (fixture, okio r2) |
| AC-1.7 | `code_kotlin.py:76-93` | ✅ |
| AC-1.8 | `code_kotlin.py:62-66` | ✅ |
| AC-1.9 | `build.py:166` | ✅ |
| AC-1.10 | canonical `graph.py` | ✅ CLI builds are `cmp`-identical: Kotlin fixture ×3 (r1) and okio incremental vs `--full` (r2) |
| AC-2.1 | `build.py:254-258,299-313` | ✅ |
| AC-2.2 | `build.py:302-303` | ✅ package wildcard; object wildcard is F2 |
| AC-2.3 | `build.py:288-293,309-313` | ✅ r2 (F1 fixed; residual F11) |
| AC-2.4 | `build.py:309-313` | ✅ |
| AC-2.5 | `build.py:309-313` | ✅ per the spec rule; residual F5 (documented) and F11 |
| AC-3.1 | `pyproject.toml:46`, `uv.lock:64` | ✅ |
| AC-3.2 | `tests/test_extractor_kotlin.py` | ✅ |
| AC-3.3 | `tests/test_extractor_java.py:50-67` | ✅ |
| AC-3.4 | `build.py:131-133,159-163` | ✅ |
| AC-3.5 | `README.md:272-276` | ✅ |
| AC-3.6 | adapters unchanged | ✅ `find_nodes` ×2, `impact`, `story_trace` and `get_node` give CLI == MCP on a Kotlin repo; the adapters contain no Kotlin |
| AC-3.7 | full suite | ✅ 402 passed (r2) |
| NFR-1 | pin + double build | ✅ r2 round-trip: the dd4b994 tree (no `.kt`) built with dd4b994 code vs HEAD code gives an identical 723,794-byte `graph.json` |
| NFR-2 | `build.py:256` | ✅ 0 dangling edges; F11 is a wrong edge, not a dangling one |
| NFR-3 | `build.py:258` | ✅ only `extracted` |
| NFR-4 | tolerant parse | ✅ malformed `.kt` builds through the CLI with rc 0 and no traceback |
| NFR-5 | slow bench | ✅ no regression: HEAD passed 5 of 10 runs, dd4b994 passed 5 of 9 (failures at 40–49.4% vs the 50% bar). The bench flakes on the baseline too, so this is not a Kotlin finding |
| NFR-6 | `test_fresh_install.py`, `test_packaging.py` | ✅ both passed in the r2 slow run |

## 5. What Was Checked

- [x] Correctness: logic does what the acceptance criteria demand
- [x] Non-functional: applicable NFRs and constitution quality bars hold
- [x] Error handling: failures are handled, not swallowed
- [x] Security: no injected input trusted, no secrets in code
- [x] Tests: exist, are meaningful (F1 test mutation-checked), and pass
- [x] Readability: the next developer will understand this

## 6. Verdict

Passed. The Major F1 is confirmed fixed in r2. Re-derived because this round verifies that fix: on okio @f0e3f479, in-repo Kotlin imports now resolve 855 against 434 before, with 0 extension-function misses, and the new regression test fails when the fix is reverted. The F3 change gives `String.q` for a qualified receiver, but the function-type receiver qualname remains, so F3 stays open as a Minor. Every Must AC of US-1 and US-3 and every US-2 AC traces to code and was verified live. The suite is green (402), and the no-Kotlin round-trip against dd4b994 is byte-identical. F11 is new and Minor: member extension functions can attract a wrong bare-name import edge, which happened in a probe and 0 times on okio. F2, F3, F4, F10 and F11 remain open Minors. None blocks the gate. The coordinator proposed deferring F2 and F4, and F10 is the user's call, but no user acceptance is recorded, so they stay `open` and not `accepted`. F9 (plan/spec drift) was fixed by the reviewer this round in `plan.md` and `spec.md`. Those edits are uncommitted.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`. On
re-review, edit this same checklist in place — never duplicate it as a second gate.*

- [x] No open Blocker findings
- [x] No open Major findings (F1 fixed r2)
- [x] Every Must AC traces to implementing code; no constitution non-negotiable violated
- [x] All plan deviations documented and accepted (T3 bare-name index recorded in §2; F9 drift fixed r2)
- [x] Test suite runs green (402 passed; slow: NFR-1 bench flaky on baseline too, see NFR-5)
- [x] Line budget respected: Ist 110 / Soll ~150 (excluding HTML comments) — self-reported
- [x] Status set to `passed`
