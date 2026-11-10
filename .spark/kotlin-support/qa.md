# QA Report: kotlin-support

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review (hands-on) |
| **Owner** | QA Tester (`/demo-day`) |
| **Input** | Branch `factory/issue-13` (clean tree), `.spark/kotlin-support/spec.md` (approved) |
| **Status** | `passed` |
| **Round** | 1 |
| **Date** | 2026-11-10 |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Verdict:** Yes. Kotlin structure and in-repo imports appear through the real CLI; builds are byte-identical; non-Kotlin graphs are unchanged. Two Minors, no Blocker or Major.
- **Open:** `2 open` — Blockers: none; Majors: none (Minors: see §3)
- **Binding ruling:** §5 Verdict and the gate checklist below — the only binding location; there is no other round to point to
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/demo-day` and proceed — don't stop on it.

## 1. Test Environment

- **App URL:** N/A. No browser surface; substitute method per `.spark/constitution.md` §8, performed here.
- **Browser / viewport(s):** N/A (headless CLI/MCP tool).
- **Test data / accounts used:** scratch git repo `/tmp/ktqa.*` (Android-style `app/src/main/java/com/ex/{data,ui}`: data class with companion and nested class, enum, interface, object, extension fun, local fun, aliased/star/stdlib/missing imports, `build.gradle.kts`, `scripts/s.kts`, empty `.kt`, invalid-UTF-8 `.kt`, duplicate `Screen` in two files, one-line class bodies, `.rb` file); `/tmp/ktamb.*` (two files same package+class); `/tmp/ktreg.*` (Python+Go only). Driven via `uv run aspark-graph build/query`.

## 2. Acceptance Criteria Verification

| Spec ID | Steps performed | Expected | Observed | Result |
|---|---|---|---|---|
| AC-1.1 | `build . --full` on scratch repo; read graph.json | `.kt`/`.kts` are File nodes `language=kotlin`, no `unparsed`; empty file has no defs | All 7 Kotlin files (incl. `s.kts`, `build.gradle.kts`, `Empty.kt`) tagged `kotlin`, none unparsed; `Empty.kt` has zero defs | ✅ pass |
| AC-1.2 | Inspect nodes/edges for class, data class, object, interface, enum class | Each a `Class` with extracted `contains` from File | `User`, `Role`, `Repo`, `Registry` Class nodes present; File→def `contains` edges `extracted` | ✅ pass |
| AC-1.3 | `query find_nodes shout`, `get_node` | Top-level and extension fun are Function nodes | `String.shout` and `outer` Function nodes in `User.kt` | ✅ pass |
| AC-1.4 | Inspect `User.kt` defs | Members and companion members nest under class; local fun yields no node | `User.greet`, `User.anon` (companion), `User.Inner.deep`, `Registry.all` present; `local` absent | ✅ pass |
| AC-1.5 | Inspect imports edges; `query impact User.kt` | `Main.kt` and `s.kts` link to `User.kt`; alias resolves by original path | Edges `Main.kt`→`User.kt` and `s.kts`→`User.kt`, extracted; `impact` lists `User.kt` entities | ✅ pass |
| AC-1.6 | Main.kt imports `kotlin.collections.List`, `com.ex.data.*`, `com.ex.data.Missing`; `/tmp/ktamb` imports `com.x.S` defined in two files | No edge, no error | Only the 2 expected edges; ambiguous repo: 0 imports edges; rc=0 | ✅ pass |
| AC-1.7 | Build `class A { fun f() {} }` | Build succeeds; limit documented | Builds rc=0, `A` kept, `A.f` missing; README line 277 documents it (but see B1) | ⚠️ pass with caveat (B1) |
| AC-1.8 | Scratch repo with `.rb`; `test_build` multi-language test in suite | All supported files tagged; `.rb` skipped | `r.rb` has no node; suite multi-language test green | ✅ pass |
| AC-1.9 | `build --full` twice, `cmp`; non-Kotlin repo (py+go) built with branch code vs `main` worktree code, `cmp` | Byte-identical | Both `cmp` identical | ✅ pass |
| AC-1.10 | Ran suite incl. `tests/test_readme.py`; read README | Kotlin listed, language-count test passes | 409 passed; README lists Kotlin and its known limits | ✅ pass |
| NFR-1 | `grep kotlin pyproject.toml`; AC-1.9 stash-equivalent (main worktree) round trip | Pinned `==1.1.0`, determinism proven vs pre-change | `tree-sitter-kotlin==1.1.0`; identical to `main` output | ✅ pass |
| NFR-2 | Check every edge endpoint exists in scratch graph | No dangling edges | `dangling []`; unresolved/ambiguous imports give no edge | ✅ pass |
| NFR-3 | `git diff main --stat` | No Kotlin code in `cli.py`/`server.py`; parity test green | Neither adapter changed; suite green | ✅ pass |
| NFR-4 | `uv run pytest`; `uv run pytest -m slow` (fresh-install `serve` boot, sdist manifest) | All green | Fast: 409 passed. Slow: fresh-install and sdist pass; `test_incremental_bench` failed 2 of 4 runs (49.8%, 27.4% vs target 50%), passed 2 (timing on a shared sandbox, see B2) | ⚠️ pass with caveat (B2) |
| NFR-7 | Invalid-UTF-8 `.kt`, empty file, malformed `fun f(` | One-line errors only, no traceback | Build rc=0, no traceback; `Bad.kt` yields File node (see B3) | ✅ pass |

## 3. Exploratory Findings

| # | Severity | Steps to reproduce | Expected vs. observed | Status |
|---|---|---|---|---|
| B1 | Minor | Extract `package p\nfun a(){}\nclass S { fun s() {} }\nclass A { fun f() {} }\nfun z(){}` (two consecutive one-line class bodies) | README says one-line bodies "may lose or misplace members". Observed: both classes and every later top-level def (`z`) vanish; only `a` survives. Limit is wider than documented | fixed |
| B2 | Minor | `uv run pytest -m slow tests/test_incremental_bench.py` x4 on this sandbox | Expected speedup >=50%; observed 49.8% and 27.4% on two runs, pass on two. Run-to-run timing noise, not Kotlin-specific; confirmed pre-existing: also fails 2 of 3 runs at dd4b994 (orchestrator re-run) | open |
| B3 | Minor | Create `.kt` with `class \xff\xfe Bad { fun f( }`, build | Expected no definition from garbage; observed a `Class` node with empty name (`def:...Bad.kt::`) | fixed |

Also checked, no defect: duplicate `Screen` in two files (distinct nodes, no collision); nested class; `build.gradle.kts` parsed; incremental rebuild re-parsed only changed files.

## 4. Console & Network

N/A (no browser). CLI stderr/stdout clean on all builds and queries: no tracebacks, no warnings.

## 5. Verdict

Would I demo this? Yes. Every AC and QA-owned NFR passes by the declared method on a realistic Android-style layout through the CLI; determinism and non-Kotlin regression are proven against `main`. Minors: the one-line-body limit is broader than the README says (B1), the incremental benchmark is timing-flaky here (B2), garbage input gives an empty-named Class (B3).

---

## ✅ QA GATE

- [x] Every Must-story acceptance criterion verified (by §8 substitute method) and passed
- [x] Every QA-owned NFR verified and passed
- [x] No open Blocker or Major bugs (Minor bugs listed; acceptance by the user pending)
- [x] Console/CLI output free of errors on the tested flows
- [x] Tested on all agreed viewports (N/A, headless)
- [x] Line budget respected: Ist ~62 / Soll ~130 (excluding HTML comments)
- [x] Status set to `passed`
