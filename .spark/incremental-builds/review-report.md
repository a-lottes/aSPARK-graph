# Review Report: incremental-builds

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | Working-tree diff of `/increment`, `.spark/incremental-builds/plan.md` |
| **Status** | `passed` |
| **Date** | 2026-07-17 |

## 1. Scope

Reviewed the uncommitted `/increment` output for the `incremental-builds` feature
against the approved spec and plan.

**Reviewed:**
- `src/aspark_graph/parse_cache.py` (new module) — full read
- `src/aspark_graph/build.py` (refactored extraction seam + `BuildReport`) — full read
- `src/aspark_graph/cli.py` (`--full` flag + fallback notice) — full read
- `pyproject.toml` (`slow` marker + `addopts`) — diff read; dependencies verified unchanged
- `tests/test_incremental.py` (26 tests, T1–T7/T9) — full read
- `tests/test_incremental_bench.py` (T8, `@pytest.mark.slow`) — full read

**Not reviewed (confirmed untouched / not in diff):** `server.py`, `inference.py`,
`git.py`, `artifacts.py`, `model.py`, `graph.py`, the extractor modules, and all
existing test files (`git status` shows only the three modified source files plus
the two new test files as changes). Existing `test_build.py` determinism tests are
unmodified and were run as part of the suite.

**Verification performed:** ran the default suite (160 passed, 1 deselected), ran
the slow benchmark (`-m slow`, 1 passed), and executed two falsifiability probes
(below).

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 Walking skeleton (`parse_cache.py`, extraction seam, cache write every build) | ✅ | Single cache-or-parse seam at `build.py:99–120`; graph assembled from identical `FileExtraction` objects regardless of origin — byte-identity is structural, as the ADR requires. Round-trip test present. |
| T2 Change detection + reuse accounting | ✅ | `reparsed`/`cached` counted at the seam; digest recomputed from disk every build (`build.py:97`) so changed-file hashes always land in `graph.json`. |
| T3 Add / delete / rename | ✅ | Whole-walk rebuild + wholesale cache rewrite; rename test asserts byte-identity vs full rescan. |
| T4 `graph.json` anchor + first build | ✅ | Anchor guard at `build.py:79` — the cache load is not even attempted without `graph.json`, so a first build emits no "missing cache" notice (AC-3.1). |
| T5 Corrupt-cache fallback + one-line stderr | ✅ | `load()` raises `CacheUnusable`; caught in `build.py:82–83`; CLI prints the single notice at the edge (`cli.py:170–171`). |
| T6 Version-tag invalidation | ✅ | `_version_tag()` keys on installed metadata for the tool + 4 parse-affecting deps, never `__init__.__version__`. |
| T7 `--full` flag | ✅ | `store_true` on the `build` subparser; passed through; cache unconditionally rewritten so `--full` replaces stale state (AC-4.2). |
| T8 NFR-1 benchmark | ✅ | 100-line files, 220 files, 8% changed, median-of-3; measured **71.5% speedup** (target ≥50%). Correctly `@pytest.mark.slow` and excluded by `addopts`. |
| T9 Summary extension | ✅ | `summary()` appends `; incremental: M re-parsed, N cached` on the incremental path and `; full rescan` otherwise. |

Both documented deviations in `plan.md` (§Deviations) are accurate and accepted:
the benchmark file-size change (8-line → 100-line files to make parse dominate)
and the `test_first_build_no_cache_no_error` assertion adjustment (`build_graph`
does not save `graph.json` — the CLI does). Both match the code as reviewed.

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Minor | `parse_cache.py:107–112` | `lookup()` deserialized entry bodies outside any guard, so a valid-JSON + valid-version cache with a malformed entry body raised an uncaught `KeyError`/`TypeError` — a traceback, not a graceful fallback (NFR-3 gap). **Fixed (post-review, user decision):** wrapped `_deserialize_extraction()` call in `lookup()` with `try/except (KeyError, TypeError, ValueError): return None`, degrading a malformed entry to a per-file cache miss. A new test `test_malformed_entry_body_degrades_to_cache_miss` confirms the fix. | fixed |
| F2 | Nit | `build.py:110` | Comment `# Known language, no extractor (unsupported): AC-4.2.` referenced `AC-4.2` from this feature's spec (the `--full`-replaces-cache criterion), not the original unparsed-file spec AC. **Fixed (post-review, user decision):** updated to `# Known language, no extractor registered yet (unsupported extension).` — no bare AC reference. | fixed |

Both findings fixed by the user at `/peer-review` close time. Suite: 161 passed / 1 deselected.

## 4. Requirements Traceability

| Spec ID | Implemented at | Test | Verdict |
|---|---|---|---|
| AC-1.1 | `build.py:99–120` (cache-or-parse seam) | `test_one_changed_file_reparsed_exactly_one` | ✅ met |
| AC-1.2 | incremental path (whole feature) | `test_incremental_bench.py` — 71.5% speedup | ✅ met |
| AC-1.3 | `build.py:102–106` | `test_unchanged_repo_reparsed_zero` | ✅ met |
| AC-1.4 | `build.py:97,117` (fresh digest every build, incl. cache hits) | `test_changed_file_hash_updated_in_graph` | ✅ met |
| AC-2.1 | canonical serialization + structural reuse | `test_build.py::test_double_build_is_deterministic` (unmodified, green) | ✅ met |
| AC-2.2 | identical `FileExtraction` objects cached vs fresh | `test_full_then_incremental_parity` | ✅ met |
| AC-2.3 | seam feeds identical objects into steps 2–4 | `test_incremental_build_queries_correct` | ✅ met |
| AC-2.4 | `parse_cache.py:25–44,125–130` | `test_version_mismatch_triggers_fallback`, `test_stale_version_results_not_served` | ✅ met |
| AC-3.1 | `build.py:79` anchor guard (no load on first build) | `test_first_build_no_cache_no_error` | ✅ met |
| AC-3.2 | `parse_cache.py:118–123` + `cli.py:170–171` | `test_corrupt_cache_*`, `test_truncated_cache_falls_back` | ✅ met (see F1 for the narrow uncovered class) |
| AC-3.3 | `parse_cache.py:125–130` | `test_version_mismatch_triggers_fallback` | ✅ met |
| AC-3.4 | whole-walk rebuild + wholesale cache rewrite | `test_new_file_added_*`, `test_deleted_file_nodes_gone_*`, `test_rename_is_delete_plus_add` | ✅ met |
| AC-3.5 | `build.py:79` (`default_graph_path(...).exists()`) | `test_first_build_without_graph_json_skips_cache` | ✅ met |
| AC-4.1 | `build.py:65,79` (`full` short-circuits the load) | `test_full_flag_ignores_cache`, `test_full_flag_via_cli` | ✅ met |
| AC-4.2 | `build.py:134` (unconditional `save`) | `test_full_flag_replaces_cache` | ✅ met |
| AC-4.3 | `build.py:79` (no graph.json → full anyway) | `test_full_flag_no_prior_state` | ✅ met |
| AC-5.1 | `build.py:58–59` | `test_summary_incremental_reports_counts` | ✅ met |
| AC-5.2 | `build.py:60–61` | `test_summary_full_rescan_says_full`, `test_summary_fallback_not_labeled_incremental` | ✅ met |
| NFR-1 | incremental path | benchmark 71.5% ≥ 50% | ✅ met |
| NFR-2 | structural reuse of `FileExtraction` | double-build + parity tests green | ✅ met |
| NFR-3 | `CacheUnusable` + `fallback_reason` + CLI notice | fallback matrix green | ✅ met (F1 = a narrow, low-probability residual) |
| NFR-4 | `summary()` + stderr notice | summary + stderr tests | ✅ met |
| NFR-7 | `server.py` untouched; build is CLI-only | existing parity suite green | ✅ met |
| NFR-8 | stdlib `json` + `importlib.metadata` only | `pyproject.toml` deps unchanged (verified: `mcp>=1.12,<1.20`, grammar pins intact) | ✅ met |

## 5. What Was Checked

- [x] Correctness: logic does what the acceptance criteria demand — every Must AC traced to code + a falsifiable test.
- [x] Non-functional: NFR-1 (71.5% > 50%), determinism, no-new-dep, and thin-adapter non-negotiables verified against the code, not assumed.
- [x] Error handling: `CacheUnusable` is a named exception; `load()` catches JSON/OS/Value errors and version mismatch; CLI edge prints one line, exit 0. One narrow uncovered corruption class recorded as F1 (Minor).
- [x] Security: cache stores only local parse results; no network, no secrets, no deserialization of executable objects (JSON, not pickle — the ADR's stated reason). NFR-5 N/A holds.
- [x] Tests: 160 passed / 1 deselected; slow benchmark passes at 71.5%. Falsifiability confirmed — neutering `cache.lookup()` reddens `test_unchanged_repo_reparsed_zero`; changing the `"version mismatch"` string reddens `test_version_mismatch_triggers_fallback`.
- [x] Readability: the single extraction seam and the anchor guard are well-commented and boring; `parse_cache.py` serializers cover every `FileExtraction`/`Definition`/`Import` field.

**Non-negotiable checks (all verified against the diff, not assumed):**
- Determinism: byte-identical double-build and full-then-incremental parity tests green; reuse is structural.
- No new dependency: `pyproject.toml` `dependencies` unchanged; `parse_cache.py` imports only `json` + `importlib.metadata`.
- `mcp>=1.12,<1.20` cap and the four `==` grammar pins unchanged.
- `server.py` not in the diff — build stays CLI-only (NFR-7).
- Cache written to `.aspark-graph/parse-cache.json`; `graph.json` untouched as canonical output.
- Fallback notice emitted from `report.fallback_reason` at the CLI edge (`cli.py:170`), not inside `build.py` — thin-adapter convention respected.

## 6. Verdict

This is a clean, correctly-scoped implementation that earns a pass. Every Must
acceptance criterion traces to implementing code and to a test that genuinely
fails when the code is broken, both non-negotiables I probed directly hold
(byte-identical determinism is structural, not luck; no dependency crept in), and
the NFR-1 benchmark clears its 50% bar with room to spare at 71.5%. The
`graph.json`-anchor rule is the quiet star of the design: by refusing to even load
the cache without an anchor, it makes the first-build, no-cache, and missing-graph
paths collapse into the proven full-rescan behaviour with no special-casing. The
one substantive finding, F1, is a Minor: the cache's integrity check guards the
top level but not entry bodies, so a valid-JSON-but-malformed-entry cache with a
matching version tag would raise a traceback mid-build instead of falling back —
a real but low-probability gap against NFR-3's "never a traceback," worth closing
opportunistically but not a gate blocker. F2 is a cosmetic cross-spec comment
ambiguity. No Blockers, no Majors, no undocumented deviations.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`.*

- [x] No open Blocker findings
- [x] No open Major findings (or explicitly waived by the user, with reason recorded here)
- [x] Every Must AC traces to implementing code; no constitution non-negotiable violated
- [x] All plan deviations documented and accepted
- [x] Test suite runs green (161 passed, 1 deselected after F1+F2 fixes; slow benchmark passes at 71.5%)
- [x] Status set to `passed`
