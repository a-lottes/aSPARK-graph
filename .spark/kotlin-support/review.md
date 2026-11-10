# Review Report: kotlin-support

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | The diff of `/increment` (`git diff dd4b994..HEAD`, HEAD `ffe5c4a`), `.spark/kotlin-support/plan.md` + `spec.md` |
| **Status** | `passed` |
| **Round** | 1 |
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
- **Verdict:** passed: every Must AC and NFR is met and re-verified; no Blocker or Major. 3 Minors and 2 Nits remain open as doc/backlog follow-ups.
- **Open:** `5 open` — Blockers: none; Majors: none (Minors/Nits: see §3)
- **Binding ruling:** §6 Verdict and the gate checklist below — the only binding location; there is no other round to point to
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Scope

Reviewed `dd4b994..ffe5c4a` (5cc459a, 9bc4679, ffe5c4a). New: `src/aspark_graph/extractors/code_kotlin.py`
and `tests/test_extractor_kotlin.py`. Changed: `extractors/base.py`, `extractors/__init__.py`,
`build.py` (Kotlin index and resolver), `parse_cache.py` (cache key), `pyproject.toml`/`uv.lock`, `README.md`,
`tests/test_build.py`, `tests/test_extractor_java.py` and `tests/test_readme.py`. No tool file was passed and graph
Step 0 was skipped, so scoping was done by hand from the diff (CLAUDE.md allows this fallback).
**Re-derived myself:** the Must-AC verifications, which are condition (b). I probed 20 Kotlin snippets
against the pinned grammar, covering one-line bodies, named companions, sealed/value/annotation/fun-interface
types, nullable, generic and qualified receivers, overloads, CRLF and BOM input, and backtick and star imports
with comments. I also ran 8 build-level import probes (owner fallback, enum entry, extension by name, top-level
`val`, Kotlin↔Java in both directions, ambiguous with fallback) and a parse-cache round-trip.
The T12 pre-change proof was re-run independently (see §2).
**Not reviewed:** a real Android repo. None was available offline, so the package-collision risk (R3) is
covered only by the synthetic test.

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ | `==1.1.0` pin plus lock, with wheels for every platform including macOS x86_64. `.kt`/`.kts` mapped, registry entry added, and no `kotlin` in `cli.py`/`server.py`. |
| T2 | ✅ | Kind folding, companion flattening (named companions too), `Recv.name` extensions and undescended bodies all hold on the real grammar. Only `private` is non-exported, as planned (see F9). |
| T3 | ✅ | Raw import capture (alias dropped, `pkg.*` kept), plus the index and `elif` branch. |
| T6 | ✅ | `build.py:307-334`: an exact match is tried first, then the owner fallback, and a link is made only when exactly one distinct file matches. An ambiguous exact match does not fall through to the owner. |
| T7 | ✅ | Build-level alias test present (`test_extractor_kotlin.py:159`). |
| T8 | ⚠️ | No-error and CLI-exit tests are fine. The edge-integrity test was tautological (F1, fixed by reviewer). |
| T4, T5, T9, T11 | ⚠️ | Implemented. T9 differs from the plan: an unknown extension like `.rb` is skipped, not marked unparsed. The plan documents this as a deviation, but spec AC-1.8 and README still state the false version (F3). |
| T10 | ✅ | Key extended. The test sits in `test_extractor_kotlin.py:222`, not `test_incremental.py` as the DoD says; harmless. |
| T12 | ⚠️ | Documented deviation: the commit used a five-language fixture without the `git archive` export of `dd4b994` and recorded no slow-suite result. **I re-derived it** under condition (b), AC-1.9 being a Must. I used the plan's fixture (`git archive dd4b994` plus `.py/.ts/.java/.go/.rs/.js`, git-initialised, 0 `.kt` files) and built with `--full` from a `git worktree` of `dd4b994` (confirmed it ran the old code: no `.kt` in `EXTENSION_LANGUAGE`) and from HEAD `ffe5c4a`. `cmp` exit 0, both sha256 `104c5016eb33e36ed2879f98dde789bc80855bd64158b896805c0a3ecef2a604` (600 867 B). Worktree removed. `git diff dd4b994 -- cli.py server.py` is empty. |

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Minor | `tests/test_extractor_kotlin.py:200` | `test_kotlin_no_dangling_edges` checked each endpoint against `graph.nodes()` ids. networkx `add_edge` creates a bare endpoint on its own, so the check could never fail; a mutant injecting a dangling `contains` passed it. That leaves NFR-2 unverified. Fix applied: assert each endpoint carries a `type` attribute and that more than 0 edges were checked. The same mutant now fails. | fixed |
| F2 | Minor | `src/aspark_graph/build.py:330` | The owner-fallback branch and the README limit "extension functions imported by name are not resolved" had no test, so a regression in either would go unseen. Fix applied: added `test_kotlin_nested_import_falls_back_to_owner_file` and `test_kotlin_extension_imported_by_name_makes_no_edge`. | fixed |
| F3 | Minor | `README.md:281` | "Files in other languages are recorded as unparsed `File` nodes" is false. Unmapped extensions are skipped (`build.py:132`), and every mapped language now has an extractor. The same wrong premise sits in `extractors/base.py:44`, spec §1 ("every `.kt` file is an `unparsed` File node" — before this change they were absent) and AC-1.8. The error predates this feature, but this feature repeats it and its acceptance criterion is built on it. Fix: README and the comment say "skipped, no node", and spec AC-1.8/§1 are reworded to match plan Deviation T9 (user to accept). | open |
| F4 | Minor | `README.md:277` | The known-limits list is incomplete. The index is Kotlin-only (`build.py:307`), so Kotlin↔Java imports never resolve in either direction. That covers most cross-file imports in a mixed Android repo, the primary target user. Imports of a top-level `val`/`const`/`typealias` also never resolve. Both were confirmed by probe; README only promises "best-effort". Fix: add one sentence naming both limits, or a BACKLOG item if interop is wanted. | open |
| F5 | Minor | `.spark/kotlin-support/plan.md:22` | The plan Handoff said "`7 tasks not done` (T6–T12)" while §3 marks all 12 `done`, a stale block. Fix applied: `Open: none`. | fixed |
| F6 | Minor | `CLAUDE.md:8` | CLAUDE.md lines 8, 28 and 81 and `constitution.md` §3 still say "five grammars" and list five languages. The constitution's off-limits pin rule therefore does not name the Kotlin pin (plan R6). Fix: update CLAUDE.md at `/go-live` and amend the constitution via `/charter`. | open |
| F7 | Nit | `src/aspark_graph/parse_cache.py:40` | The cache key now covers Kotlin, but `tree-sitter-go`/`-rust` were never in it (since v0.5.0). A Go/Rust pin bump under an unchanged tool version reuses stale extractions; only dev builds are affected. Not this diff's scope. Fix: add both, or log in `.spark/BACKLOG.md`. | open |
| F8 | Nit | `src/aspark_graph/extractors/code_kotlin.py:106` | The receiver is taken as raw text. `fun @receiver:Ann String.z()` gets qualname `@receiver:Ann String.z`, and `fun (() -> Unit).call()` gets `(() -> Unit).call`. Rare, with no dangling edge, but the names are unsearchable. Fix: take the `type_identifier`s of the `user_type` and ignore `type_modifiers`. | open |
| F9 | Nit | `src/aspark_graph/extractors/code_kotlin.py:57` | `internal`/`protected` members count as `exported=True`. This follows plan T2 and the Rust `pub(crate)` precedent (go-rust F1). Noted for transparency; no change required. | open |

## 4. Requirements Traceability

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | `base.py:56-57`, `code_kotlin.py:30-42`; tests at `:112`, `:215`, `:107` | ✅ met |
| AC-1.2 | `code_kotlin.py:26,87-97`; test `:63`; probe: sealed/value/annotation/fun interface | ✅ met |
| AC-1.3 | `code_kotlin.py:111-124`, `:100-108`; test `:88` | ✅ met (F8 nit) |
| AC-1.4 | `code_kotlin.py:70-84` (companion transparent, bodies not descended); tests `:81`, `:94` | ✅ met |
| AC-1.5 | `code_kotlin.py:60-67`, `build.py:307-334`; tests `:134`, `:159`, `:228` | ✅ met |
| AC-1.6 | `build.py:326,332`; tests `:146`, `:169`, `:236`, star import in `:134` | ✅ met |
| AC-1.7 | probe: `A` kept, `f` dropped, no error; test `:186`; README `:277` | ✅ met |
| AC-1.8 | `tests/test_extractor_java.py:50`, all seven languages, no unparsed | ⚠️ partial: `.rb` is skipped, not `unparsed` (F3) |
| AC-1.9 | `test_build.py:53`, test `:152`; pre-change proof re-run (§2 T12) | ✅ met |
| AC-1.10 | `README.md:272,303,326`; `test_readme.py:72,120` | ✅ met (F4 doc gap) |
| NFR-1 | `pyproject.toml:46`, `uv.lock:681`, `parse_cache.py:44`; byte-identity re-run | ✅ met |
| NFR-2 | ambiguous → no edge; `test_extractor_kotlin.py:200` (after F1) | ✅ met |
| NFR-3 | `cli.py`/`server.py` diff empty; parity suite green | ✅ met |
| NFR-4 | `uv run pytest` 409 passed; `-m slow` 4 passed | ✅ met |
| NFR-7 | test `:186` (garbage bytes and invalid UTF-8, CLI rc 0, no traceback) | ✅ met |

## 5. What Was Checked

- [x] Correctness: each Must AC was traced to code and re-verified on the pinned grammar with 28 probes.
- [x] Non-functional: the `==` pin, byte-identity against `dd4b994`, thin adapters untouched, the slow suite and the cache round-trip all hold.
- [x] Error handling: the tolerant parse means a one-line body, garbage, invalid UTF-8, CRLF or a BOM never raises; a resolver miss returns `None`.
- [x] Security: no new I/O or network surface; confinement unchanged. Kotlin text is used only as dict keys and qualnames.
- [x] Tests: they exist and pass. One tautology was found and fixed (F1), and two coverage gaps were closed (F2).
- [x] Readability: the extractor is 124 lines and mirrors the Java/Go precedents; the docstrings state the limits.

## 6. Verdict

**Passed.** The Kotlin extractor and resolver do what the approved spec and plan ask, and every Must
AC holds when re-checked against the real pinned grammar rather than the code's comments. Kind folding,
companion flattening, receiver-qualified extensions, undescended bodies, alias-by-original-path, star → no
edge, and exactly-one-file resolution (T6, without falling through to the owner on ambiguity) are all
confirmed. The one-line-body limit loses the member without an error, as documented. I re-ran the
pre-change byte-identity proof myself on the plan's specified fixture, because the commit used a narrower
one; the `dd4b994` and HEAD graphs are byte-identical. The full suite (409) and the slow suite (4) are
green. I fixed one real test defect: the dangling-edge test could never fail (F1). I also closed two
coverage gaps (F2) and the stale plan Handoff (F5). What remains is honest-documentation work. The README
"unparsed" claim and spec AC-1.8 describe behaviour the tool does not have (F3). README does not say that
Kotlin↔Java and top-level-property imports never resolve, which matters most in the Android repos this
feature targets (F4). CLAUDE.md and the constitution still say five grammars (F6). None of these is a wrong
edge or a broken guarantee, so none blocks. F3 and F4 should land before `/go-live`, F6 at `/go-live` and
`/charter`. The reviewer's test and plan edits are uncommitted.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`. On
re-review, edit this same checklist in place — never duplicate it as a second gate.*

- [x] No open Blocker findings
- [x] No open Major findings (or explicitly waived by the user, with reason recorded here)
- [x] Every Must AC traces to implementing code; no constitution non-negotiable violated
- [x] All plan deviations documented and accepted. T9 and T12 are documented in the plan. The T12 evidence was re-derived independently. The T9 wording conflict with spec AC-1.8 is tracked as F3 (Minor).
- [x] Test suite runs green: 409 passed, 4 slow passed
- [x] Line budget respected: Ist 126 / Soll ~150 (excluding HTML comments) — self-reported, no linter checks this; an overage is recorded here with a reason or explicitly waived by the user
- [x] Status set to `passed`
