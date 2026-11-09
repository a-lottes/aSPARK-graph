# Review Report: csharp-support

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | `git diff dd4b994..HEAD` (f4cf6ab, 8eebb96), `.spark/csharp-support/plan.md` |
| **Status** | `changes-requested` |
| **Round** | 1 |
| **Date** | 2026-11-09 |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Verdict:** Changes requested. The C# extractor is correct on every AC I probed, and the build crash I found (F1) is fixed in the working tree by the reviewer. Must AC-3.2 still fails as written (F2), which only a `/story-time` amendment or a user waiver can close.
- **Open:** `1 open` (Blockers: none; Majors: `F2`). Minors/Nits: see §3. F1/F3/F7 are reviewer fixes (`fixed`), awaiting confirmation in round 2.
- **Binding ruling:** §6 Verdict and the gate checklist below are the only binding location; there is no other round to point to.
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed; don't stop on it.

## 1. Scope

- **Reviewed:** `dd4b994..8eebb96`, 13 files. f4cf6ab (code, written before the spec and plan existed) was audited from scratch against spec ACs, not against the plan's account of it. 8eebb96 covers the tests, README and trail.
- **Mode:** live runs (full suite, slow suite, CLI builds, an old-vs-new round-trip, probes of the extractor). AC-3.4 was verified on a C# fixture by an in-process CLI-vs-MCP comparison; the MCP stdio transport could not be exercised in this sandbox (see F11).
- **Tooling:** `aspark-graph query staleness` reported no graph for this repo (CLAUDE.md Step 0), and no tool file was passed, so scoping was done by grep/Read.
- **Standard:** Anti-generosity standard applied (`/opt/aspark/standards/anti-generosity.md`, read in full before the verdict).
- **Re-derived, not cited:** I re-derived the T13 round-trip and the suite results under condition (b) (Must AC-3.3 / AC-3.5 verification) rather than citing the increment's account.
- **Not reviewed:** a real public .NET repo (plan §4 "recommended" check) was not built because this sandbox has no network. R1/R2 rest on synthetic probes only.

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ | `pyproject.toml:46` `==0.23.5`; `uv.lock:650` (wheel for macOS x86_64 present, unlike the old `cryptography` trap); `base.py:56`; `__init__.py:25`. |
| T2 | ✅ | `code_csharp.py:52-69`; tests pass. |
| T3 | ✅ | `code_csharp.py:120-152`; `Svc.Run.Helper` asserted. |
| T4 | ✅ | `_is_exported` matches the documented defaults. The exception was top-level-statement local functions, exported `True` against the docstring and the T4 DoD (F3, reviewer-fixed). |
| T5 | ✅ | Empty, usings-only, malformed and `Program.cs` tests present and green. |
| T6 | ✅ | All 3 forms asserted. Plan R1 says an alias with a generic target imports the alias `L`; a probe shows it imports the target `System.Collections.Generic.List<int>` (F8). |
| T7 | ✅ | `build.py:254-260, 312-335`. |
| T8 | ✅ | Tests for static-type, 3-file fan-out with double build, self-edge and edge integrity. |
| T9 | ✅ | `test_build.py:54`. |
| T10 | ✅ | `.js` file added; `javascript` asserted. |
| T11 | ✅ | `test_build.py:78` pins "no node". Wording mismatch routed as F2. |
| T12 | ✅ | README L272, L295-296, L315-318. The commit dropped the stale-count guard of current-artifact-names AC-6.1 (F7, reviewer-restored as a "five" guard). |
| T13 | ✅ | Re-derived (see §5). |
| T14 | ❌ | Default suite green. `-m slow`: 2 of 4 fail (transport is environmental and pre-existing, F11; bench see F10). Adapter diff is empty. |
| Process | ⚠️ | Code before spec/plan (R0). Documented in plan §1 Deviations, and the approved plan accepts it. Not a separate finding. |

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Major | `src/aspark_graph/extractors/code_csharp.py:143-152` | `_add_local_functions` recursed through **every** expression node of a method body. A valid `.cs` method with a ~1000-term `+` chain, a ~500-call fluent chain or a ~1000-branch `else if` raised `RecursionError`. `aspark-graph build` on `/tmp/rvrepo1` (1 such `.cs` + 1 `.py`) printed a full traceback, exited 1 and built **no graph for the whole repo**. That repo built cleanly under v0.7.3, which skipped `.cs`. This violates NFR-8 and the "clean errors, never tracebacks" rule; Java and TS extractors survive the same input. **Fix (applied by reviewer):** an iterative pre-order walk with an explicit stack, giving the same visit order. 26 probe extractions are unchanged and the C# fixture graph is unchanged apart from F3. Regression test `test_csharp_deeply_nested_method_body_does_not_crash` (3000-term concat + 1500-call chain). | fixed |
| F2 | Major | spec `AC-3.2`, spec §1 Problem; `README.md:273-274`; `extractors/base.py:43-44` | AC-3.2 (Must) says an unsupported extension "is still recorded as `unparsed: true`". Since v0.1.0, `build.py:132-133` skips any unlisted extension with **no node** (pinned by `test_build.py:78`). Spec §1's premise ("every `.cs` file is recorded as an unparsed `File` node") is equally false: pre-change `.cs` got no node. The README sentence (in the very paragraph this diff edited) and the `base.py` comment make the same false claim to users. The code is not at fault: emitting nodes for every unlisted file would change every repo's graph and void AC-3.3. **Why Major:** a Must AC fails as written and blocks the gate trace. The artifact-wording cap does not apply because it changes a Must AC verdict. **Fix:** `/story-time` amends AC-3.2 and §1 to "unlisted extensions are skipped, no node, build does not fail" (the `unparsed` path exists only for a registered language without an extractor, or files over 5 MB). Then correct README L273-274 and the `base.py:43-44` comment to match. | open |
| F3 | Minor | `code_csharp.py:72, 133-135` | A top-level-statement local function (`Program.cs`: `int Twice(...)`) was `exported=True`, contradicting the module docstring ("local function is False") and plan T4's DoD. It is never visible outside the file. **Fix (applied):** a local function is always `exported=False`; asserted in `test_csharp_top_level_statements_local_function`. | fixed |
| F4 | Minor | `build.py:319-322`; `code_csharp.py:56-59` | Every type in a file is indexed under the file's **first** namespace. With `namespace A {class X} namespace B {class Y}`, `Y` is keyed `A.Y`, a name that does not exist. With nested `namespace A { namespace B { class C } }`, `C` is keyed `A.C` and `using A.B;` never resolves. Mostly this fails toward absence (R3). However, a `using static A.Y;` that targets a real `A.Y` in a file sorting later gets a **wrong** edge, against constitution §1 ("honest absence beats a wrong link"). **Fix:** skip type indexing for files with more than one namespace declaration, or record the enclosing namespace per definition. | open |
| F5 | Minor | `code_csharp.py:75-84` | `using static Acme.Util.Helper<int>;` imports `Acme.Util.Helper<int>` and `using global::Acme.Util;` imports `global::Acme.Util`. Neither ever resolves (verified by probe). These are legal AC-2.2 shapes that silently lose their edge. **Fix:** strip a leading `global::` and drop a trailing type-argument list before appending the `Import`, and add a test for each. | open |
| F6 | Nit | `code_csharp.py:91-97, 112` | `file class F` (C# 11 file-local) reads as exported. A type nested in an interface (public by default in C#) reads as not exported. Namespace text keeps inner whitespace (`Acme . Util`). **Fix:** treat a `file` modifier as not exported; default nested-in-interface types to exported; join the name's identifiers instead of using raw text. | open |
| F7 | Minor | `tests/test_readme.py:68` | 8eebb96 deleted `test_current_names_ac_6_1_no_six_language_count` (current-artifact-names AC-6.1's stale-count guard) without a replacement, so a stale count could now linger in the README unnoticed. **Fix (applied):** `test_current_names_ac_6_1_no_stale_five_language_count` asserts no "five" remains. | fixed |
| F8 | Minor | `plan.md:16`, `plan.md:63-68`, `plan.md:143-144` (R0, R1) | The plan's Handoff says "7 tasks not done (T4, T5, T8, T10, T11, T13, T14)" and R0 says those are `todo`, but §3 marks all 14 `done`. §1 says "HEAD is f4cf6ab". R1's alias-generic claim is wrong (see T6). The body wins under the plan's own conflict rule. **Fix:** `/sprint-plan` updates Handoff `Open`, the R0/R1 rows and the §1 evidence note. | open |
| F9 | Minor | `CLAUDE.md:8, 81`; `.spark/constitution.md:35, 39` | These lines still say five grammars or list five languages. Line 81 and constitution L39 are the `==`-pin rule, which no longer names the C# pin. Ruling: not fixed here. By repo convention CLAUDE.md changes only in release commits (`git log -- CLAUDE.md`) and still says 0.7.3 is shipped, and the constitution is amended only via `/charter`. **Fix:** `/go-live` updates CLAUDE.md L8/L81 (plus the trail entry); `/charter` amends constitution §3. | open |
| F10 | Minor | `tests/test_incremental_bench.py:97` | NFR-6 bench: HEAD BENCH_HEAD_PLACEHOLDER; pre-change BENCH_OLD_PLACEHOLDER. | open |
| F11 | Minor | `tests/test_mcp_transport.py:103` | It fails with `No id=2 response within 10 s; server stderr: ''` on HEAD **and identically on dd4b994** (pre-change worktree, `uv sync --offline`), so it is environmental and pre-existing, not caused by this diff. The MCP stdio transport for C# is therefore not verified live here. **Fix:** rerun `-m slow` outside the sandbox before `/go-live`, and record the result in `qa.md`. | open |
| F12 | Minor | `src/aspark_graph/parse_cache.py:38-44` | The cache key names core plus the py/ts/java grammars only. The C# grammar joins Go/Rust as uncovered, and the docstring's "all four parse-affecting dependencies" is stale. A grammar bump without a package bump would reuse stale `.cs` extractions. Plan R5 accepts it for release builds. **Fix:** add the go/rust/c-sharp grammars to `_version_tag` (this changes the tag, a one-time full rescan), or record it in BACKLOG at `/go-live` as R5 says. | open |

## 4. Requirements Traceability

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | `base.py:56`, `__init__.py:25`, `build.py:168` | ✅ met (live fixture: `language=csharp`, no `unparsed`) |
| AC-1.2 | `code_csharp.py:56-59` | ✅ met (block + file-scoped tests) |
| AC-1.3 | `code_csharp.py:28-34, 100-118`; `build.py:230` | ✅ met (5 kinds + `record struct` probe) |
| AC-1.4 / AC-1.5 | `code_csharp.py:65-68, 115-117` | ✅ met |
| AC-1.6 | `code_csharp.py:120-152` | ✅ met (nested `L1.L2` probe too) |
| AC-1.7 | name field excludes type params | ✅ met (`Box`, `Box.Get` test) |
| AC-1.8 | `code_csharp.py:12-15, 91-97` | ✅ met after F3 fix |
| AC-1.9 | `code_csharp.py:38-42` | ✅ met (test) |
| AC-1.10 | canonical save | ✅ met (CLI double build of `/tmp/rvcs` `cmp`-identical; incremental also identical) |
| AC-2.1 / 2.3 / 2.4 / 2.5 | `build.py:312-335, 257-259` | ✅ met (tests + live: `Widget.cs→Helper.cs, Other.cs`; `System` gives no edge) |
| AC-2.2 | `code_csharp.py:75-84` | ✅ met for the spec's shapes; generic/`global::` variants are F5 |
| AC-3.1 | `test_extractor_java.py:50` | ✅ met (7 languages, `unparsed == set()`) |
| AC-3.2 | `build.py:132-133` | ❌ fails as written: no node is created (F2) |
| AC-3.3 | no-`.cs` code paths | ✅ met (re-derived, §5) |
| AC-3.4 | `cli.py`/`server.py` 0 diff lines | ✅ met (in-process CLI≡MCP on a C# fixture: `find_nodes`×3, `impact` equal) |
| AC-3.5 | suite | ✅ met (see §5) |
| AC-4.1 / AC-4.2 | `README.md:272, 295-296, 318` | ✅ met |
| NFR-1 | `pyproject.toml:46`, `uv.lock:650` | ✅ |
| NFR-2 / NFR-3 | `build.py:230-259` | ✅ (live: 0 dangling, confidences `{extracted}`) |
| NFR-4 | adapters untouched | ✅ |
| NFR-5 | `tests/test_extractor_csharp.py` (15 tests) | ✅ |
| NFR-6 | `build.py:135-145` precede dispatch | NFR6_PLACEHOLDER |
| NFR-7 | `test_fresh_install`, `test_packaging` | ✅ both PASSED (wheel boots `serve`, which imports `code_csharp` via the registry) |
| NFR-8 | `code_csharp.py:143-152` | ✅ after F1 fix (it was ❌: traceback) |
| NFR-9 | n/a | N/A per spec |

## 5. What Was Checked

- [x] Correctness: 26-case extractor probe (nested and multiple namespaces, records, expression bodies, lambdas, top-level statements, interfaces, partials, overloads, unicode, BOM, `#if`); live builds and resolution
- [x] Non-functional: `==` pin and lock. AC-3.3 round-trip: a `git worktree` at dd4b994 (= f4cf6ab^) vs HEAD, `--full`, built on two fixtures (`src`+`.spark/go-rust-support`: 230/41 entities; full `git archive HEAD` repo: 711/578). Both are `cmp`-identical (sha256 `72cbc485…`, `5a3a308c…`).
- [x] Error handling: malformed `.cs` tolerated; F1 crash found and fixed
- [x] Security: no new input surface; confinement and the size cap run before dispatch (`build.py:110, 135`)
- [x] Tests: before fixes, 401 passed and 4 deselected (EXIT 0). After fixes: SUITE_PLACEHOLDER
- [x] Readability: module docstring states every default

## 6. Verdict

VERDICT_PLACEHOLDER

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`. On
re-review, edit this same checklist in place — never duplicate it as a second gate.*

- [x] No open Blocker findings
- [ ] No open Major findings (F2 open; F1 reviewer-fixed, to be confirmed in round 2)
- [ ] Every Must AC traces to implementing code; no constitution non-negotiable violated (AC-3.2 ❌ as written)
- [ ] All plan deviations documented and accepted (F8 plan Handoff/R0/R1 stale)
- [ ] Test suite runs green (SLOWGATE_PLACEHOLDER)
- [x] Line budget respected: Ist LINES_PLACEHOLDER / Soll ~150 (excluding HTML comments)
- [ ] Status set to `passed`
