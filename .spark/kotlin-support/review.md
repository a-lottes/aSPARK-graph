# Review Report: kotlin-support

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | The diff of `/increment` (`64a081b^..a1d58d5`), `.spark/kotlin-support/plan.md` |
| **Status** | `changes-requested` |
| **Round** | 1 |
| **Date** | 2026-11-11 |

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
- **Verdict:** Changes requested. The `ERROR` recovery emits wrong nesting on valid Kotlin, including a real OkHttp file (AC-1.3 fails), and `qa.md` records unperformed passes.
- **Open:** `0 open`. Blockers: none. Majors: none (Minors/Nits: see §3)
- **Binding ruling:** §6 Verdict and the gate checklist below — the only binding location; there is no other round to point to
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

<!-- Budget: ~150 lines. Findings are rows, not essays: location, what's wrong, why it matters, in a
     cell. The report is read back at the gate, again in fix-mode, and once more at re-review — a
     finding that takes three paragraphs to state is a finding nobody rereads. §6 Verdict is the one
     place prose is worth it. -->

## 1. Scope

- **Reviewed:** `git diff 64a081b^..HEAD` (64a081b, 71ea228, a1d58d5; 16 files). I read in full `extractors/code_kotlin.py`, `build.py` (`_kotlin_indexes`, `_resolve_kotlin_import` and the Kotlin branch of `_resolve_imports`), `tests/test_extractor_kotlin.py`, and the hunks in `base.py`, `__init__.py`, `test_build.py`, `test_extractor_java.py`, `test_readme.py`, `README.md`, `CLAUDE.md`, `pyproject.toml` and `uv.lock`.
- **Graph (aspark-graph, MCP):** `staleness` returned fresh (65 files). `impact --diff 64a081b^..HEAD` returned 8 code files in the graph and 22 stories, 11 of them `declared`. `unknown_files` held the `.spark/` files, `CLAUDE.md`, `README.md`, `pyproject.toml` and `uv.lock`, so I read those by hand. `story_trace` US-1 and US-3 returned T1–T4, T7 and T9 → `code_kotlin.py`, `extractors/__init__.py`, `base.py` and the three test files, which I then read. Graph hits outside Kotlin come in through `build.py`; reading it showed the change is confined to the Kotlin functions and one new branch (`build.py:254-258`). I did not read story_trace's QA leg, per the tool guide.
- **Not reviewed:** the parse-cache interaction beyond one incremental rebuild. `gate_health` was not called (tool guide: false-zero `open_findings`).
- **Mode:** live runs. Full suite, slow suite, T8 round-trip, okhttp double build and okhttp sweep (`/tmp/scratch/okhttp` @ `4162e9da`), plus targeted probes of the extractor (scripts in `/tmp/rvprobe/`).
- **Standard:** Anti-generosity standard applied (`/opt/aspark/standards/anti-generosity.md`). **Active lens:** `cli`.

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ | `pyproject.toml:46` `tree-sitter-kotlin==1.1.0`; `uv.lock` locks 1.1.0 with abi3 wheels incl. macOS x86_64; `base.py:56-57`; `__init__.py:25` |
| T2 | ✅ | `test_all_languages_in_one_build` asserts `kotlin` language + `definition_id("f.kt","k")` |
| T3 | ✅ | Class kinds + single-line `ERROR` shape tested (`test_extractor_kotlin.py:54-60,91-94`) |
| T4 | ❌ | Canonical shapes tested and pass; real-file nesting is wrong (F1, F2) |
| T5 | ✅ | `build.py:337-354`; `test_build_resolves_kotlin_imports` |
| T6 | ✅ | `build.py:351` `return hit if len(hit) == 1 else []`, no further stripping; both T6 tests present |
| T7 | ⚠️ | (b) asserted only 4 of the 5 class kinds for `contains`; I added the plain-class assertion (F7) |
| T8 | ✅ | Re-derived (condition b, Must AC-3.1): `git archive 64a081b^` built by `/tmp/rv-base` (64a081b^) and by HEAD → 597391 B each, `cmp` 0; `tests/fixtures/sample_repo` → 7169 B each, `cmp` 0 |
| T9 | ✅ | README §Supported languages/§Design guarantees/§Out of scope; `test_readme.py:74` |
| T10 | ❌ | `CLAUDE.md:8` still lists five languages (F4) |
| T11 | ❌ | DoD "every mis-nesting found becomes a test plus a fix, or a named known limit" is not met: `Http2Stream.kt` mis-nests (F1). The deviation note's "No wrong nesting was seen" is false |
| Deviation | ⚠️ | Constitution §3 still says "five grammars". The plan §5 records this as a `/charter` matter, which is acceptable as a documented deviation; the user has not yet amended it |

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Major | `code_kotlin.py:47-83` (`_walk`: an `ERROR` sibling after a body-less class is walked with `parent`, not the class) | Real file: okhttp `Http2Stream.kt` (in T11's own sample). The class header ends early at :40 and the body becomes an `ERROR` at :48, so 12 members (`takeHeaders`, `close`, `cancel`, …) are emitted as **top-level** functions (parent `None`) and indexed as `okhttp3.internal.http2.<name>` symbols by `_kotlin_indexes`. This puts wrong `contains` edges and FQNs in the graph tagged `extracted`, which violates constitution §1 and contradicts README:278 "missing rather than wrong". Fix: when the previous sibling is a body-less class, walk an immediately following `ERROR` with that class as parent (or emit nothing for it); add a regression test of this shape; correct the plan's T11 note. | fixed |
| F2 | Major | `code_kotlin.py:51-56` (orphan rule) | The orphan rule mis-attributes members on valid code. `data class P(val x: Int)` followed by `@Ann(X::class)\n@B\nclass A {\n fun m() {}\n class N { fun n() {} }\n}` yields `P.m`, `P.N`, `P.N.n`, and `A` is lost. In `.kts`, `class Marker` + `run { class A { fun m() {} } }` yields `Marker.A`. The rule never fires on any of okhttp's 619 files (instrumented), including `Android17SocketAdapter.kt`, the file it was written for (that file misparses as an `infix_expression`). So it adds wrong-link risk and recovers nothing in the sweep. Fix: restrict it to the shape it targets (sibling text starts with an annotation + `constructor`), or remove it and its synthetic test, and add a negative test for the `P`/`A` case. | fixed |
| F3 | Major | `.spark/kotlin-support/qa.md` §2 | Written before review: all 5 ACs show `✅ pass` with Observed "tests green", and no performed step per constitution §8. `story_trace` serves these as `latest_result: "pass"`, so this repo's own graph reports AC-1.3 as passed while F1 shows it failing. Plan §4 itself says these rows must be redone. Fix: set each Result to `⚠ not-verified-live` (or remove the file) until `/demo-day` performs the §8 method. | fixed |
| F4 | Minor | `CLAUDE.md:8` | Still "tree-sitter: Python, TypeScript/JavaScript, Java, Go, Rust". The T10 DoD names line 8 explicitly. Fix: add Kotlin. Not fixed by the reviewer, because agent edits to CLAUDE.md are off-limits. | fixed |
| F5 | Minor | `README.md:275-279` | The known-limit text undercounts. Losses also happen in **ERROR-free** parses: a multi-annotation, body-less class with arguments (`@A(X::class)\n@B\nclass T`) parses as an expression, and the following class (`class U { fun u() {} }`) is lost too. On okhttp, 5 clean-parse files lose 9 top-level classes (`StartStop.kt`, `GraalSvm.kt` ×5, `ConnectionListenerTest.kt` incl. its 12 members, `Flaky.kt`, `OkHttpInternalApi.kt`). "8 files parsed with errors" reads as the affected-file count; it isn't. Fix: reword so it doesn't tie the loss to ERROR files, and pin the shape with a test that asserts the known absence. | fixed |
| F6 | Minor | `build.py:310-331`; README | Top-level `val`/`const val` and lost annotation classes are not indexed. On okhttp, 184 in-repo imports resolve to nothing (e.g. `okhttp3.internal.USER_AGENT`, `mockwebserver3.junit5.StartStop` ×52). This is within AC-2.1's wording (class or top-level fun) but undocumented. Fix: name it as a known limit, or index top-level properties. | fixed |
| F7 | Minor | `tests/test_extractor_kotlin.py:121-122` | T7b asked for a `contains` edge for all 5 class kinds; a plain `class` was never asserted. Reviewer added the assertion; the Kotlin tests and the full suite are green. | fixed |
| F8 | Minor | `.spark/kotlin-support/plan.md:16` | The Handoff says "Open: 5 tasks not done (T6, T7, T8, T10, T11)", but §3 marks all of them `done`. Fix: update the Handoff (EM-owned). | fixed |

## 4. Requirements Traceability

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | `base.py:56-57`, `__init__.py:25`, `code_kotlin.py:32-37` | ✅ met — tests + okhttp build: 619 `kotlin` Files, 0 `unparsed` |
| AC-1.2 | `code_kotlin.py:26,175-185` | ✅ met — all 5 kinds tested incl. `contains` (F7); okhttp 558/567 top-level classes found, losses are absences (F5) |
| AC-1.3 | `code_kotlin.py:188-210`, `_walk_error`/orphan rule | ❌ missing — canonical shapes pass, but member functions are emitted with the wrong parent/qualname on valid input (F1 real file, F2) |
| AC-2.1 (Should) | `build.py:254-258,310-354`, `code_kotlin.py:213-220` | ✅ met — class, top-level fun, wildcard, stdlib-no-edge and ambiguity tests live; okhttp: 2353 resolved, 39 refused as ambiguous |
| AC-3.1 | `pyproject.toml:46`, README:272, `test_build.py:53-63` | ✅ met — pin `==1.1.0`; okhttp double `--full` build + incremental rebuild byte-identical (5361465 B, `cmp` 0); T8 round-trip byte-identical |
| Constitution §1 | `code_kotlin.py` | ❌ wrong links tagged `extracted` (F1, F2) |
| Constitution §6 non-negotiables | — | ✅ none violated: determinism held; `cli.py`/`server.py`/`queries.py`/`model.py`/`artifacts.py` unchanged (`git diff --quiet` 0), no per-language logic in adapters |

## 5. What Was Checked

- [x] Correctness: logic does what the acceptance criteria demand — checked; AC-1.3 fails (F1, F2)
- [x] Non-functional: applicable NFRs and constitution quality bars hold — spec has no NFRs; pin, determinism and the T8 round-trip hold; §1 fails (F1/F2)
- [x] Error handling: failures are handled, not swallowed — tree-sitter never raises; `_text` decodes with `replace`; the 5 MB cap and confinement are unchanged
- [x] Security: no injected input trusted, no secrets in code — the import text is only string-matched; no new I/O or network
- [x] Tests: exist, are meaningful, and pass — 402 passed. Slow suite: 3 passed, 1 failed (`test_nfr1…` 33.4% vs ≥50%). That failure is environmental: on 64a081b^ code it also failed (49.3%) in 1 of 2 runs, and HEAD passed 2/2 in isolation. The rest of the slow suite (fresh install, transport, sdist) passed. Gaps: F1/F2 shapes untested
- [x] Readability: the next developer will understand this — the three walkers (`_walk`/`_walk_single`/`_walk_error`) duplicate dispatch; acceptable
- [x] `cli` lens: the diff adds no flag, stream, exit code or help text; build stderr/stdout unchanged. No lens check applies to the diff

## 6. Verdict

Changes requested. Determinism, the pin, the adapter rule and import resolution hold, and I verified each live. Two `ERROR`-recovery paths, though, put wrong links into the graph under `extracted`. F1 does it on a real OkHttp file that was in the plan's own T11 sample: 12 members of `Http2Stream` become top-level functions. F2's orphan rule does it on valid Kotlin and fires on none of okhttp's 619 files. Together they break AC-1.3 and constitution §1, and they contradict the README's "missing rather than wrong" and the plan's "no wrong nesting was seen". F3: `qa.md` records five passes that rest on no performed step, and the graph already serves them as `pass`. Open: Majors F1, F2, F3; Minors F4, F5, F6, F8. F7 was fixed by the reviewer. Anti-generosity standard applied.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`. On
re-review, edit this same checklist in place — never duplicate it as a second gate.*

- [x] No open Blocker findings
- [ ] No open Major findings (or explicitly waived by the user, with reason recorded here) — F1, F2, F3 open
- [ ] Every Must AC traces to implementing code; no constitution non-negotiable violated — AC-1.3 ❌ (F1/F2); §6 non-negotiables intact
- [ ] All plan deviations documented and accepted — T10, T11 DoD unmet; §3 "five grammars" awaits `/charter`
- [x] Test suite runs green — 402 passed; slow NFR-1 bench flaky on pre-change code too (§5)
- [x] Line budget respected: Ist 102 / Soll ~150 (excluding HTML comments) — self-reported, no linter checks this; an overage is recorded here with a reason or explicitly waived by the user
- [ ] Status set to `passed`
