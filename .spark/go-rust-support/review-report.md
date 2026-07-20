# Review Report: go-rust-support

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | The uncommitted working-tree diff of `/increment`, `.spark/go-rust-support/plan.md` + `spec.md` |
| **Status** | `passed` |
| **Date** | 2026-07-20 |

## 1. Scope

Reviewed the working-tree diff for the go-rust-support feature only:

- **New:** `src/aspark_graph/extractors/code_go.py`, `src/aspark_graph/extractors/code_rust.py`,
  `tests/test_extractor_go.py`, `tests/test_extractor_rust.py`
- **Modified:** `src/aspark_graph/extractors/base.py` (2 `EXTENSION_LANGUAGE` entries),
  `src/aspark_graph/extractors/__init__.py` (registry), `src/aspark_graph/build.py`
  (Go/Rust import indexes + `_resolve_imports` dispatch), `pyproject.toml` / `uv.lock`
  (grammar pins), `tests/test_build.py` (six-language determinism test),
  `tests/test_extractor_java.py` (three→six language integration test).

**Not reviewed (out of scope, per task):** `README.md` and `docs/*.png` — pre-existing
unrelated working-tree changes from an earlier session, not part of this feature.

**Verification performed:** full suite (`uv run pytest` — 187 passed) and slow suite
(`uv run pytest -m slow` — 2 passed) run locally; wrote throwaway tree-sitter probes
against the *actual* pinned grammars (`tree-sitter-go==0.25.0`, `tree-sitter-rust==0.24.2`)
to verify node-shape assumptions (R1) rather than trusting the code's comments.

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ | Grammar deps pinned `==` in `pyproject.toml` + `uv.lock`; `.go`/`.rs` wired into `EXTENSION_LANGUAGE` and `_REGISTRY`; empty/bare files produce non-`unparsed` File nodes (build.py:117). |
| T2 | ✅ | Go two-pass extractor: `_declared_type_names` pre-pass, struct/interface folded into `Class`, same-file receiver methods nest, cross-file land as top-level `Function` (parent=None). Verified against real grouped `type (...)`, pointer/generic receivers. |
| T3 | ✅ | Rust two-pass extractor: struct/enum/trait → `Class`; multiple `impl` blocks (inherent, `impl Trait for Type`, generic) fold into the one same-file `Class`; foreign/cross-file impls land top-level. `impl Trait for Type` correctly reads the `type` field as the target. |
| T4 | ✅ | `_go_package_index` + `_resolve_go_import`: trailing-segment match with a leading-`/` boundary guard; ambiguity (>1 candidate) → no edge; fan-out to all files in a matched package dir; sorted for determinism. |
| T5 | ✅ | `_rust_module_index` + `_resolve_rust_import` + `_lookup_or_parent`: layout-only module index, `crate::`/`self::`/`super::` resolution, colliding module paths (`util.rs` + `util/mod.rs`) recorded as multi-candidate → no guess. |
| T6 | ✅ | Six-language integration test asserts none `unparsed`; six-language double-build determinism test; `cli.py`/`server.py` untouched (confirmed absent from diff — NFR-4 structurally held); slow suite green (NFR-6). |

No deviations from the plan. The architecture decision (§1: single-file-only
extraction, `_add_definitions` untouched, no cross-file type index, no new
`NodeType`) was followed exactly — `_add_definitions` (build.py:153) is byte-for-byte
unchanged and no `NodeType` value was added.

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Nit | `code_rust.py:51` `_is_pub` | Restricted visibility (`pub(crate)`, `pub(super)`) is marked `exported=True` because it detects any `visibility_modifier` node. This is consistent with AC-2.6's literal wording ("presence or absence of the `pub` keyword") and the Go binary-exported model, and `pub(crate)` genuinely contains `pub`, so it is defensible — but it slightly overstates "exported" for crate-restricted items. Suggested fix (optional, future refinement): treat a `visibility_modifier` with a restriction child as non-exported if a finer distinction is ever needed. No change required this cycle. | accepted by user (2026-07-20) |
| F2 | Nit | `build.py:263` `_resolve_rust_import` / `_lookup_or_parent` | A `use crate::X::…` whose intermediate segments match no repo module file walks all the way up to the crate root (`lib.rs`/`main.rs`) and links there. For *valid* Rust this is correct (the item must be an inline `mod` in the crate root), and it is spec-sanctioned best-effort (A3) — never a dangling edge. On malformed/incomplete source it can over-link to the root file. Acceptable under A3/A5; recorded for transparency, no fix needed. | accepted by user (2026-07-20) |
| F3 | Nit | `tests/test_build.py:47`, per-language determinism tests | The double-build determinism tests use single-file-per-language fixtures, so they exercise the extraction/nesting paths but not multi-file *import-resolution* determinism. Low risk — canonical sorted persistence (`graph.py`) and the sorted `_go_package_index` make import-edge ordering deterministic by construction — but a multi-file Go/Rust double-build fixture would close the last gap directly. Optional. | accepted by user (2026-07-20) |

No Blocker, Major, or Minor findings. Nothing was fixed by the reviewer — the diff
had no typos, dead code, or missing guards warranting a direct edit.

## 4. Requirements Traceability

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 (Go File node, package, no unparsed) | `code_go.py:32-34`, `build.py:117` | ✅ met |
| AC-1.2 (struct/interface → Class) | `code_go.py:70-81` (`_TYPE_KINDS`) | ✅ met |
| AC-1.3 (free func → top-level Function) | `code_go.py:84-91` | ✅ met |
| AC-1.4 (same-file receiver method nests) | `code_go.py:94-102`; test `test_build_go_same_file_method_nests_under_class` | ✅ met |
| AC-1.5 (cross-file method → top-level, no dangling) | `code_go.py:103-107`; test `test_build_go_cross_file_method_becomes_top_level_function` (asserts every edge endpoint exists) | ✅ met |
| AC-1.6 (exported via capitalization) | `code_go.py:51-52`; test `test_go_exported_follows_capitalization` | ✅ met |
| AC-1.7 (Go double-build byte-identical) | test `test_double_build_go_is_deterministic` | ✅ met |
| AC-1.8 (empty/bare Go file not unparsed) | `build.py:117`; test `test_go_empty_file_is_not_unparsed` | ✅ met |
| AC-2.1 (Rust File node, no unparsed) | `code_rust.py:29`, `build.py:117` | ✅ met |
| AC-2.2 (struct/enum/trait → Class) | `code_rust.py:23,66-73` | ✅ met |
| AC-2.3 (free fn → top-level Function) | `code_rust.py:76-84` | ✅ met |
| AC-2.4 (impl fns nest, incl. multiple impls) | `code_rust.py:87-112`; tests `test_rust_multiple_impl_blocks_fold_into_one_class`, `test_build_rust_same_file_impl_nests_under_class` | ✅ met |
| AC-2.5 (cross-file/foreign impl → top-level, no dangling) | `code_rust.py:102-106`; tests `test_build_rust_cross_file_impl_becomes_top_level_function`, `test_build_rust_impl_on_foreign_type_becomes_top_level_function` | ✅ met |
| AC-2.6 (exported via `pub`) | `code_rust.py:51-52`; test `test_rust_exported_follows_pub` | ✅ met (see F1 nit on `pub(crate)`) |
| AC-2.7 (Rust double-build byte-identical) | test `test_double_build_rust_is_deterministic` | ✅ met |
| AC-2.8 (item-less Rust file not unparsed) | `build.py:117`; test `test_rust_empty_file_is_not_unparsed` | ✅ met |
| AC-3.1 (Go in-repo import resolves) | `build.py:238-259`; test `test_build_resolves_go_import` | ✅ met |
| AC-3.2 (Go stdlib/third-party → no edge) | `_resolve_go_import` no-match; test `test_build_go_stdlib_import_yields_no_edge` | ✅ met |
| AC-3.3 (Go ambiguous import → no edge) | `build.py:257` (`len(candidates) != 1`); test `test_build_go_ambiguous_import_yields_no_edge` | ✅ met |
| AC-4.1 (Rust crate/self/super import resolves) | `build.py:262-290`; tests `test_build_resolves_rust_crate_import`, `test_build_resolves_rust_self_and_super_import` | ✅ met |
| AC-4.2 (Rust external crate → no edge) | `_resolve_rust_import` returns None for non-crate/self/super head; test `test_build_rust_external_crate_import_yields_no_edge` | ✅ met |
| AC-4.3 (Rust ambiguous module → no edge) | `_lookup_or_parent` returns None on multi-candidate key; test `test_build_rust_ambiguous_import_yields_no_edge` | ✅ met |
| AC-5.1 (six languages, none unparsed) | test `test_all_six_languages_in_one_build` (asserts `unparsed == set()`) | ✅ met |
| AC-5.2 (unknown extension still unparsed) | unchanged `build.py:111`; existing `test_ac_4_2_unsupported_language_becomes_unparsed_file_node` | ✅ met |
| AC-5.3 (full suite green, no regressions) | `uv run pytest` → 187 passed | ✅ met |
| AC-5.4 (CLI≡MCP parity) | `cli.py`/`server.py` absent from diff; dispatch data-driven; existing parity suite green | ✅ met |
| NFR-1 (exact grammar pins, determinism) | `pyproject.toml` + `uv.lock` `==0.25.0`/`==0.24.2`; double-build tests | ✅ met |
| NFR-2 (no dangling edges) | same-file/cross-file discipline in both extractors; cross-file tests assert every edge endpoint exists as a node | ✅ met |
| NFR-3 (all edges `EXTRACTED`) | `code_*`/`build.py` all emit `Confidence.EXTRACTED`; no new tier | ✅ met |
| NFR-4 (parity, no per-language adapter code) | `cli.py`/`server.py` untouched | ✅ met |
| NFR-5 (two extractor test files + six-lang test) | present, at `test_extractor_java.py` granularity | ✅ met |
| NFR-6 (slow benchmark still passes) | `uv run pytest -m slow` → 2 passed | ✅ met |
| NFR-9 (Go/Rust distinguishable via `language`) | `build.py:117` tags each File node | ✅ met |

## 5. What Was Checked

- [x] Correctness: logic does what the acceptance criteria demand — traced every Must AC to code and a test; verified node shapes against the real pinned grammars.
- [x] Non-functional: NFR-1/2/3/4/5/6/9 all hold; CLAUDE.md non-negotiables (exact pins, no dangling edges, `EXTRACTED` tier, thin-adapter/data-driven dispatch, `_add_definitions` untouched, no new `NodeType`) all respected.
- [x] Error handling: tolerant tree-sitter parse (A5); best-effort import resolution refuses to guess on ambiguity (A7) — verified empty/malformed/ambiguous paths.
- [x] Security: N/A — offline, local, no new network/credential/execution surface (NFR-7).
- [x] Tests: exist, assert real structure (qualname/kind/parent tuples, edge-endpoint existence), and pass (187 + 2 slow).
- [x] Readability: extractors are small, single-file, mirror the Java precedent; comments explain the same-file/cross-file cut and the ambiguity discipline.

## 6. Verdict

**Pass.** This is careful, correct parser code that does exactly what the approved
spec and plan asked and no more. The two extractors follow the established single-file
pattern, fold Go/Rust types into `Class` per the Java precedent, and implement the
same-file-nests / cross-file-top-level cut (A2) entirely inside each extractor so
`build.py`'s `_add_definitions` never sees a parent id it can't resolve — I confirmed
the NFR-2 "no dangling edge" invariant both by reading the logic and via the tests'
explicit every-endpoint-exists assertions. I did not take the code's grammar comments
on trust: I parsed non-trivial Go/Rust snippets (grouped `type (...)`, pointer/generic
receivers, `impl Trait for Type`, multiple impls, wildcard/aliased/grouped `use`) with
the actual pinned grammars and the extractor output matched. Import resolution correctly
refuses to guess on ambiguity, and the Go trailing-segment match uses a leading-`/`
boundary so it cannot match a partial path segment (the `foo/mywidget` vs `widget`
concern does not occur). Determinism is doubly guaranteed — exact `==` grammar pins plus
canonical sorted persistence — and the double-build tests confirm byte-identical output.
The only observations are three Nits (restricted-visibility `exported` semantics,
best-effort crate-root fallback linking, and single-file-only determinism fixtures), all
spec-sanctioned best-effort behavior, none requiring a change this cycle. Full and slow
suites are green with zero regressions. Ship it.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`.*

- [x] No open Blocker findings
- [x] No open Major findings (or explicitly waived by the user, with reason recorded here)
- [x] Every Must AC traces to implementing code; no constitution non-negotiable violated
- [x] All plan deviations documented and accepted — none; plan followed exactly
- [x] Test suite runs green — 187 passed, 2 slow passed
- [x] Status set to `passed`
