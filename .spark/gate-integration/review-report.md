# Review Report: gate-integration

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | Untracked/modified files vs HEAD; `.spark/gate-integration/plan.md` |
| **Status** | `passed` |
| **Date** | 2026-07-17 |

## 1. Scope

Files reviewed (new or modified vs last commit):

- `docs/aspark-integration.md` (new) — the portable Reviewer + QA-Tester drop-in blocks and setup section
- `tests/test_integration_docs.py` (new) — 31-test falsifiability harness
- `CLAUDE.md` (modified) — Reviewer block dogfood witness + N/A QA note
- `README.md` (modified) — one pointer line
- `pyproject.toml` (modified) — version bump 0.3.0 → 0.3.1
- `uv.lock` (modified) — version string update only
- `.spark/gate-integration/spec.md` and `plan.md` — read as review baseline

Not reviewed: source files under `src/aspark_graph/` (unchanged — confirmed via git diff; NFR-5 verified). The plugin cache (`~/.claude/plugins/cache/`) is explicitly Out of Scope per spec §6/Q4 and was not examined.

## 2. Plan Conformance

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 — Reviewer block in `docs/aspark-integration.md` | ✅ | File exists; fenced block between explicit delimiters; `impact`, `story_trace`, `gate_health` present with AC-1.2 invocations |
| T2 — Graceful degradation baked into Reviewer block | ✅ | `staleness` pre-check (Step 0), grep/read fallback, accelerant framing, `{"found": false}` caveat, confidence-tier caveat all present |
| T3 — `tests/test_integration_docs.py` falsifiability harness | ✅ | CLI surface introspected from `_QUERY_ARGS`/`_QUERY_NAMES`; subcommand validity, flag validity, portability, and prose contract all tested; 31 tests, all green |
| T4 — QA-Tester block added; test extended | ✅ | Second fenced block present; `story_trace`+`gate_health`, staleness/fallback, non-replacement caveat, confidence tiers all present and tested |
| T5 — Setup section + README pointer | ✅ | Two prerequisites in order; staleness caveat; README links (not command copies); README has pointer line |
| T6 — CLAUDE.md dogfood witness | ✅ | Reviewer block with concrete values (`--feature aspark-graph`, `gate_health aspark-graph`) present; "QA-Tester half (`/demo-day`): N/A" explicit |
| T7 — Version bump 0.3.0 → 0.3.1 | ✅ | `pyproject.toml` and `uv.lock` updated; no code or pinned-dep change |

No deviations from the plan architecture decision were observed. The single-file layout, delimiter-based block extraction, and CLI-introspection approach all match the plan's architecture section.

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Minor | `CLAUDE.md:16` | Version reference `**Current shipped version: 0.3.0.**` was not updated when T7 bumped the version to 0.3.1. Creates a direct contradiction between the guidance document and `pyproject.toml`. | fixed |
| F2 | Nit | `CLAUDE.md` (Working here section) | Comment `# 103 tests; keep green` is stale: the suite has 134 tests after this increment's 31 additions. A developer following the comment's guidance would see 134 pass and think the count is wrong. | fixed |
| F3 | Nit | `tests/test_integration_docs.py:1` | Module docstring opens with `T12:` — no T12 exists in the plan (tasks are T1–T7; the test covers T3 through T6). Stale artifact from an earlier draft, creates confusion when tracing the test back to the plan. | fixed |
| F4 | Nit | `tests/test_integration_docs.py:291` | `test_qa_block_has_performance_caveat` is a misleading name. The test validates AC-3.2's "graph output scopes but never replaces performing steps" requirement — not a performance characteristic. | fixed |
| F5 | Nit | `tests/test_integration_docs.py:305` | `test_qa_block_is_portable` omits the `--feature aspark-graph` check that the parallel Reviewer portability test performs (`test_reviewer_block_is_portable`, line 234). The QA block correctly uses placeholder `<feature>` so no breach exists today, but the asymmetry means a future hardcoding would go undetected in the QA block. | fixed |
| F6 | Minor | `tests/test_integration_docs.py:423` | `test_claude_md_no_active_qa_tester_block` uses a logically weak assertion: `"demo-day" not in CLAUDE_MD or "N/A" in CLAUDE_MD`. Because "N/A" appears elsewhere in the file regardless of the QA block's presence, a developer could add an active `/demo-day` instruction to `CLAUDE.md` and this test would still pass. Fixed by the user after review: assertion replaced with `assert "## Using aspark-graph in /demo-day" not in CLAUDE_MD` — structural check that directly falsifies what it claims to guard. | fixed |

### Reviewer fixes applied (F1–F5)

F1: Updated `CLAUDE.md` line 16: `0.3.0` → `0.3.1`.  
F2: Updated `CLAUDE.md` Working-here comment: `103` → `134`.  
F3: Updated `tests/test_integration_docs.py` module docstring: `T12:` → `T3/T4/T5/T6:`.  
F4: Renamed `test_qa_block_has_performance_caveat` → `test_qa_block_has_non_replacement_caveat`.  
F5: Added `assert "--feature aspark-graph" not in block` to `test_qa_block_is_portable`, mirroring the Reviewer block test.  

All 134 tests remain green after these edits.

## 4. Requirements Traceability

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1 | `docs/aspark-integration.md:14` (BEGIN delimiter) | ✅ met |
| AC-1.2 | `docs/aspark-integration.md:37–65` (Steps 1–3); `test_reviewer_block_has_required_tools`, `test_reviewer_block_has_impact_diff_flag` | ✅ met |
| AC-1.3 | `tests/test_integration_docs.py` — `test_reviewer_block_names_real_query_subcommands`, `test_reviewer_block_flags_are_valid`; all invocations verified against `_QUERY_ARGS` | ✅ met |
| AC-1.4 | `docs/aspark-integration.md` Reviewer block uses `<changed files>`, `<US-n>`, `<feature>` throughout; `test_reviewer_block_is_portable` | ✅ met |
| AC-1.5 | `docs/aspark-integration.md:71–77` (Interpreting results); `test_reviewer_block_has_confidence_tier_caveat` | ✅ met |
| AC-2.1 | `docs/aspark-integration.md:25–32` (Step 0); `test_reviewer_block_has_staleness_precheck` | ✅ met |
| AC-2.2 | `docs/aspark-integration.md:29–31`; `test_reviewer_block_has_grep_fallback` | ✅ met |
| AC-2.3 | `docs/aspark-integration.md:18–21`; `test_reviewer_block_has_accelerant_framing` | ✅ met |
| AC-2.4 | `docs/aspark-integration.md:78–81`; `test_reviewer_block_has_empty_result_caveat` | ✅ met |
| AC-3.1 | `docs/aspark-integration.md:108–116` (QA Step 1); `test_qa_block_has_required_tools` | ✅ met |
| AC-3.2 | `docs/aspark-integration.md:121–124`; `test_qa_block_has_non_replacement_caveat` (renamed by F4) | ✅ met |
| AC-3.3 | `docs/aspark-integration.md:96–104` (QA Step 0); `test_qa_block_has_staleness_precheck`, `test_qa_block_has_grep_fallback` | ✅ met |
| AC-3.4 | `tests/test_integration_docs.py` — `test_qa_block_names_real_query_subcommands`, `test_qa_block_flags_are_valid` | ✅ met |
| AC-4.1 | `docs/aspark-integration.md:139–151` (Setup steps 1 and 2, in order); `test_setup_section_mentions_mcp_server`, `test_setup_section_mentions_build` | ✅ met |
| AC-4.2 | `docs/aspark-integration.md:153–158` (Setup step 3); `test_setup_section_has_staleness_caveat` | ✅ met |
| AC-4.3 | `docs/aspark-integration.md:140–151` links to `../README.md#install` and `../README.md#build-the-graph`; no `git clone` or `uv sync`; `test_setup_section_references_readme`, `test_setup_section_does_not_duplicate_install_commands` | ✅ met |
| AC-4.4 | Setup sequence is followable; all commands (`aspark-graph build .`) work on any target project, not just this repo; README links resolve correctly to named sections | ✅ met |
| AC-5.1 | `CLAUDE.md:89–121`; `test_claude_md_has_reviewer_tool_references`, `test_claude_md_reviewer_tools_are_real` | ✅ met |
| AC-5.2 | `CLAUDE.md:80–82` ("missing or stale graph is no weaker…"); `test_claude_md_has_freshness_note` | ✅ met |
| AC-5.3 | `CLAUDE.md:84–87` ("QA-Tester half (`/demo-day`): N/A"); `test_claude_md_no_active_qa_tester_block` (weak assertion noted in F6 but content is correct) | ✅ met |
| NFR-1 | Every tool invocation cross-checked against `cli.py`'s `_QUERY_ARGS`/`_QUERY_NAMES`: `staleness`, `impact` (files + `--diff`), `story_trace` (`--feature`), `gate_health` (positional `feature`). Zero fictional tools, zero wrong flags. | ✅ met |
| NFR-2 | Freshness precondition and grep/read fallback are first-class in both blocks (Step 0 before Steps 1–3); AC-2.x all met | ✅ met |
| NFR-3 | Shipped blocks (Reviewer and QA) use only `<placeholders>`; `test_reviewer_block_is_portable` and `test_qa_block_is_portable` (F5 added symmetry) enforce this; CLAUDE.md copy correctly uses concrete values | ✅ met |
| NFR-4 | Setup section references README at two named anchor links; no duplicated install commands; `test_setup_section_references_readme`, `test_setup_section_does_not_duplicate_install_commands` | ✅ met |
| NFR-5 | `git diff HEAD -- src/aspark_graph/` is empty; `pyproject.toml` diff is version string only; `uv.lock` diff is version string only; all tree-sitter and mcp pins unchanged | ✅ met |

## 5. What Was Checked

- [x] **Correctness:** Every AC traced to implementing text in `docs/aspark-integration.md` and/or `CLAUDE.md`; every tool name and flag in both files verified against `cli.py`'s `_QUERY_ARGS` and `_QUERY_NAMES`; portability of shipped blocks confirmed (no this-repo literals)
- [x] **Non-functional:** NFR-1 (honesty), NFR-2 (graceful degradation), NFR-3 (portability), NFR-4 (no doc drift), NFR-5 (no code/dep change) all verified
- [x] **Error handling:** N/A — no new runtime code path; domain errors remain handled as before
- [x] **Security:** No new data path, no network, no auth surface; NFR-6 N/A
- [x] **Tests:** `uv run pytest` run twice (pre-fix and post-fix): 134/134 passed both times; test soundness probed — fictional subcommand detection, hardcoded feature name detection, and staleness-removal detection all confirmed falsifiable
- [x] **Readability:** Block prose is clear, steps are numbered, placeholders are angle-bracketed and consistent; test file structure mirrors `test_readme.py` convention; reviewer-judged prose is honest and plain

### Falsifiability spot-checks performed

- Would `blast_radius` in the Reviewer block make a test red? Yes — `test_reviewer_block_names_real_query_subcommands` asserts against `_VALID_QUERY_NAMES`, which does not contain `blast_radius`.
- Would `--feature gate-integration` in the shipped Reviewer block make a test red? Yes — `test_reviewer_block_is_portable` explicitly asserts `"gate-integration" not in block`.
- Would removing `staleness` from the Reviewer block make a test red? Yes — `test_reviewer_block_has_staleness_precheck` asserts `"staleness" in _reviewer_block()`.
- Would `--feature aspark-graph` appear in the shipped QA block and pass? No — after F5 fix, `test_qa_block_is_portable` now asserts against it symmetrically.

### CLI surface audit (NFR-1)

Each documented invocation cross-checked against `cli.py`:

| Invocation | Arg/flag source | Result |
|---|---|---|
| `aspark-graph query staleness` | `_args_staleness` (no additional args) | ✅ |
| `aspark-graph query impact <files>` | `_args_impact`: `files nargs="*"` | ✅ |
| `aspark-graph query impact --diff <range>` | `_args_impact`: `--diff` defined | ✅ |
| `aspark-graph query story_trace <US-n> --feature <feature>` | `_args_story_trace`: `story` positional + `--feature` | ✅ |
| `aspark-graph query gate_health <feature>` | `_args_gate_health`: `feature` positional | ✅ |
| `aspark-graph build .` | top-level `build` subparser with `path nargs="?"` | ✅ |

### No code changes (NFR-5)

`git diff HEAD -- src/` produces no output. `pyproject.toml` diff is the single `version =` line; `uv.lock` diff is the package entry version string. All tree-sitter grammar pins and the `mcp>=1.12,<1.20` cap are unchanged. The byte-identical double-build contract is untouched.

## 6. Verdict

This is a clean, well-scoped docs/prompt increment. The deliverable — a portable integration block, an honest setup section, a dogfood witness in CLAUDE.md, and a 31-test falsifiability harness — exactly matches the plan and satisfies every Must and Should AC. The test design is sound: CLI surface introspection from `cli.py` rather than a hardcoded list is the right call, and the three spot-checks above confirm the harness would catch the canonical failure modes (fictional tool, hardcoded feature name, missing staleness pre-check). The reviewer applied five direct fixes (F1–F5) — all obvious, low-risk, and tests-green — addressing stale version references, a stale test count, a wrong docstring task reference, a misleading test name, and an asymmetric portability assertion. One open Minor (F6) records a logically weak assertion in `test_claude_md_no_active_qa_tester_block` that does not falsify what it claims; the content it guards is correct today, but the assertion would not catch a future active demo-day block alongside any "N/A" elsewhere in the file. This is the only open finding and it does not block the gate — the actual content is correct and the intent (AC-5.3) is met. The increment passes.

---

## REVIEW GATE

- [x] Plan fully implemented (all 7 tasks `done`, nothing missing)
- [x] No open Blockers
- [x] No open Majors (or each waived with recorded reason)
- [x] All Must ACs verified (AC-1.x, AC-2.x, AC-4.x, AC-5.x)
- [x] Should ACs verified or explicitly accepted (AC-3.x — all four met)
- [x] No regression in the 103 prior tests (134 total green; 103 pre-existing all still pass)
- [x] NFR-1 (honesty), NFR-3 (portability), NFR-4 (no doc drift), NFR-5 (no code/dep change) all pass
- [x] Status set to `passed`
