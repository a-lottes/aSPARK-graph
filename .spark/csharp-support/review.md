# Review Report: csharp-support

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | The diff of `/increment` (`dd4b994..bb7d1fd`), `.spark/csharp-support/plan.md` |
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
- **Verdict:** Pass. One Major (C# `#if` blocks silently dropped declarations) was found and fixed by the reviewer, with tests that fail without the fix. All Must ACs trace to code and live checks.
- **Open:** `7 open`. Blockers: none. Majors: none. Minors/Nits: F5–F11 (see §3)
- **Binding ruling:** §6 Verdict and the gate checklist below — the only binding location; there is no other round to point to
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Scope

- **Reviewed:** `git diff dd4b994..HEAD` (HEAD `bb7d1fd`, 15 files): `code_csharp.py` (new), `build.py`, `extractors/{__init__,base}.py`, `pyproject.toml`/`uv.lock`, README, and the tests `test_extractor_csharp.py`, `test_extractor_java.py`, `test_build.py`, `test_incremental.py`, `test_cli_mcp_parity.py` and `test_readme.py`. Spec and plan were read in full.
- **Standards:** constitution §1–§3. `cli` lens: the diff touches no flags, streams, exit codes or help (`cli.py`/`server.py`/`queries.py`/`model.py` diff is empty), so it has nothing to check. **Anti-generosity standard applied.**
- **Tooling:** aspark-graph was run on the live repo (`staleness` fresh, `impact --diff dd4b994..HEAD`). It mapped all 10 changed `src/`/`tests/` files in-graph and listed csharp-support US-1..3 as `declared`. Every one of those files was then read directly. `.aspark-graph/` was deleted afterwards.
- **Mode:** live runs plus tests plus a static read. Nothing was degraded.
- **Not reviewed:** `uv.lock` beyond the c-sharp entries. Real third-party .NET repos were not checked: there is no network clone here, so a hand-built fixture stood in (§5).

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ | Pin `pyproject.toml:46`, `base.py:56`, `extractors/__init__.py:25` |
| T2 | ✅ | Extractor as planned. It missed preprocessor blocks (F1, fixed) |
| T3 | ✅ | `build.py:312-343`; dedup gap F2 (fixed) |
| T4 | ✅ | README/test_readme. A stale "five" count stayed in the README (F3, fixed) |
| T5 | ✅ | `test_extractor_csharp.py:105-138`. The top-level type case asserts `package is None` (A6 verified, see §5) |
| T6 | ✅ | `test_extractor_csharp.py:154-169` |
| T7 | ✅ | `test_build.py` byte-compares the saved JSON; `test_incremental.py:495` |
| T8 | ✅ | `test_extractor_java.py:50` asserts seven languages |
| T9 | ❌ | Marked `done`, but the DoD `.rb` test existed nowhere (F4, test now added). No PO ruling row in spec §7 (F5) |
| T10 | ✅ | Re-derived by the reviewer, §5 (condition b: Must AC-3.5) |
| T11 | ✅ | Adapter diff empty (re-run); parity test `test_cli_mcp_parity.py:301` |
| T12 | ✅ | Re-run by the reviewer, §5 |

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Major | `extractors/code_csharp.py:28,63,101` | Declarations inside `#if/#elif/#else` were dropped silently. tree-sitter-c-sharp 0.23.5 nests them under `preproc_if`, and the walkers never descended into it. A type, a member (e.g. `#if NET6_0_OR_GREATER` multi-targeting), a `using`, or a whole file wrapped in `#if` gave no nodes, which breaks AC-1.2/1.3 on common real code. **Fix applied:** walk every branch (no symbols are defined at build time) via `_PREPROC` plus `_add_members`. Tests at `test_extractor_csharp.py:174,206` fail without the fix. | fixed r1 |
| F2 | Minor | `build.py:326-328` | Follows from F1: the same type declared in both `#if` and `#else` put the file into the type index twice, so `len==2` read it as ambiguous and no `using` edge was made. **Fix applied:** dedupe relpaths per type. | fixed r1 |
| F3 | Minor | `README.md:299,319` | The diff left "The five tree-sitter grammars (…six names…)" and "Languages beyond the five currently supported". Both are factually wrong. **Fix applied:** reworded to "The tree-sitter grammars" and "beyond those currently supported" (the word "six" is banned by `test_readme.py:68`). | fixed r1 |
| F4 | Minor | `tests/test_extractor_csharp.py:213` | T9's DoD required a `.rb` test, but none existed in `tests/`, so the reworded AC-3.1 clause was untested. **Fix applied:** a test now asserts `language_for("x.rb") is None`, no node, and not in `report.unparsed`. | fixed r1 |
| F5 | Minor | `.spark/csharp-support/spec.md:16,84` §7 | `/increment` reworded AC-3.1 and the Summary of an `approved` spec, with no §7 Clarification row and no PO ruling (T9 DoD). The new AC-3.1 wording is also weaker than the EM proposal ("no File node"). Fix: the PO adds row C7 recording the ruling. | open |
| F6 | Minor | `README.md:277`, `extractors/base.py:44` | "Files in other languages are recorded as unparsed `File` nodes" is false: `build.py:132` skips them, and the `.rb` test proves it. This predates the feature and diverges from v0.1.0 AC-4.2 (`.spark/aspark-graph/spec.md:173`). Changing the code would break AC-3.5, so it is a PO call: fix the docs, or ship the behaviour in a later feature. | open |
| F7 | Minor | `extractors/code_csharp.py:51-53` | Nested block namespaces `namespace A { namespace B { class X{} } }` record `A`, so X is indexed as `A.X`. A `using A.B;` then gives no edge. That is honest absence, never a wrong edge for valid C#. Fix: compose nested names (`A.B`) or list the case as a known limit under A4. | open |
| F8 | Minor | `extractors/code_csharp.py:71-73` | An alias to a generic gives the module `N.Box<int>` (never resolves). `using L = Box<int>;` picks the alias `L` as the target, because `generic_name` is filtered out. Both cause missed edges, and a wrong edge is possible only if a namespace is literally named after the alias. Fix: exclude the `name` field child and strip type arguments. | open |
| F9 | Minor | `parse_cache.py:38-44` | The cache version tag omits `tree-sitter-c-sharp` (and go/rust), so a future grammar bump reuses stale C# extractions. Plan R4 rules it out of scope. Fix: propose a `.spark/BACKLOG.md` entry to add all grammars to the tag. | open |
| F10 | Minor | `.spark/constitution.md:35,39`; `CLAUDE.md:8,28,81` | These still say five languages/grammars. Constitution §3 off-limits "the five grammars" does not literally protect the new `==` pin. Confirmed as release-time docs: `CLAUDE.md` is updated at `/go-live` (`.spark/go-rust-support/release.md:161`, commit `19d1a7d`). The constitution needs `/charter`. Route both, do not edit here. | open |
| F11 | Nit | `.spark/csharp-support/plan.md:16,127` | The plan Handoff still says "8 tasks not done … T9 blocked", but all 12 tasks are `done`. The PLAN GATE box "Status set to approved by the user" is unchecked while the Status is `approved`. Fix: the EM updates both. | open |

## 4. Requirements Traceability

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | `code_csharp.py:51-53`, `base.py:56`; tests `:34,:59,:116` | ✅ |
| AC-1.2 | `code_csharp.py:20-23,76-87` (+F1 fix); tests `:36,:121,:174` | ✅ |
| AC-1.3 | `code_csharp.py:89-100`; tests `:38` | ✅ |
| AC-1.4 | `code_csharp.py:105-117`; tests `:62` | ✅ |
| AC-1.5 | name field excludes type params; test `:105` | ✅ |
| AC-1.6 | test `:112` | ✅ |
| AC-1.7 | `test_build.py` saved-JSON byte compare; reviewer CLI double build `cmp` identical | ✅ |
| AC-2.1–2.3 | `build.py:254-260,332-343`; test `:154` (5 forms) | ✅ |
| AC-2.4 | test `:165` | ✅ |
| AC-2.5 | `build.py:341`; test `:95` | ✅ |
| AC-3.1 | `base.py:56`; tests `:74,:213` | ✅ |
| AC-3.2 | `test_extractor_java.py:50` (7 languages, none unparsed) | ✅ |
| AC-3.3 | `pyproject.toml:46` `==0.23.5`, `uv.lock:62` | ✅ |
| AC-3.4 | `README.md:272-276`; `test_readme.py:72` | ✅ |
| AC-3.5 | Reviewer round-trip, §5 | ✅ |
| AC-3.6 | Adapter diff empty; `test_cli_mcp_parity.py:301` | ✅ |
| NFR-1 | AC-1.7/3.3/3.5 above | ✅ |
| NFR-2 | Fixture: 0 dangling edges; broken source test `:128` | ✅ |
| NFR-3 | All C# `imports` edges `extracted` (fixture JSON, test `:162`) | ✅ |
| NFR-4 | = AC-3.6 | ✅ |
| NFR-5 | 16 C# tests, suite green | ✅ |
| NFR-6 | `pytest -m slow` bench passed this run (2 runs, both green) | ✅ |
| NFR-7/8 | N/A per spec | N/A |

## 5. What Was Checked

- [x] Correctness: probed 16 C# shapes against the real parser. Found: BOM, CRLF, `#region`, record struct, generics, interface default methods and attributes all OK; `#if` lost declarations (F1); nested namespace (F7); generic alias (F8); delegates, destructors and properties not modelled (out of scope per spec §6).
- [x] Spec claim A6 verified: a top-level type outside any namespace is captured as `Class` with `parent=None`. A namespace-less file has `package=None` and is skipped by `_csharp_indexes` (`build.py:319`), so no `using` resolves to it.
- [x] Non-functional: AC-3.5 re-derived (condition b). `git archive dd4b994 src` vs the working-tree `src` (incl. reviewer fixes), each `build --full` on a copy of this repo (145 tracked files + `x.rb`, no `.cs`): `cmp` identical, 666886 bytes each, sha256 `9e4d072d…a320b0`. C# fixture (4 files, BOM/CRLF/`#if`/`#region`/partial/static using): double build identical; incremental == full; 3 correct `imports` edges; 0 dangling.
- [x] Error handling: malformed source builds without an exception (test `:128`). No new error paths.
- [x] Security: no new input surface. Confinement and the 5 MB cap apply unchanged (same `build.py` walk).
- [x] Tests: `uv run pytest` 405 passed (402 + 3 reviewer). `-m slow` 4/4 passed: fresh unlocked install boots `serve` (`server.py:16` → `build` → `code_csharp` imports the grammar at boot), MCP transport, sdist manifest, NFR-1 bench. New tests were confirmed failing against the unfixed `src/`.
- [x] Readability: the extractor mirrors the Java/Go pattern and is about 120 lines.

## 6. Verdict

Pass. The C# extractor, registry and `using` resolver implement every Must AC of US-1 and US-3 and every Should AC of US-2. The adapters are untouched, and the non-C# graph is byte-identical to `dd4b994` (re-derived, sha256 above). The diff as delivered had one Major: any declaration inside `#if/#elif/#else` (types, members, usings, or a whole file) was dropped silently. Multi-targeting .NET code does this routinely. The reviewer fixed it in `code_csharp.py` (walk every branch) and `build.py` (index dedup), with tests that fail without the fix, and also fixed the README count and the missing T9 `.rb` test. Fixed code is new code, so `/increment` should read F1/F2 before release. Seven Minor/Nit findings stay open: F5, F11 and F10 are artifact or doc routing (PO, EM, `/go-live`/`/charter`); F6 is a pre-existing doc-vs-AC-4.2 divergence for the PO; F7 and F8 are honest-absence resolver gaps; F9 is a backlog proposal. None blocks QA-equivalent sign-off. The PO should still record the AC-3.1 ruling (F5) before `/go-live`.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`. On
re-review, edit this same checklist in place — never duplicate it as a second gate.*

- [x] No open Blocker findings
- [x] No open Major findings (F1 fixed r1 by the reviewer)
- [x] Every Must AC traces to implementing code; no constitution non-negotiable violated
- [x] All plan deviations documented and accepted (T9 deviation recorded as F4 fixed / F5 open Minor)
- [x] Test suite runs green (405 passed; slow 4/4)
- [x] Line budget respected: Ist ~120 / Soll ~150 (excluding HTML comments)
- [x] Status set to `passed`
