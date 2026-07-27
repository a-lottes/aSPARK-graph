# Review Report: security-posture

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | The working-tree diff vs `HEAD`, `.spark/security-posture/plan.md` + `spec.md` |
| **Status** | `passed` |
| **Date** | 2026-07-27 |

## 1. Scope

Reviewed the entire uncommitted working tree vs `HEAD`: new `src/aspark_graph/confinement.py`,
`SECURITY.md`, five new test files; modified `build.py`, `cli.py`, `queries.py`, `server.py`,
`conftest.py`, `test_build.py`, `test_cli_mcp_parity.py`, `README.md`, `CLAUDE.md`,
`docs/aspark-integration.md`. Read each in full plus the surrounding context needed to judge it
(`artifacts.extract_features`, `inference.py` F1, `graph.add_node` semantics).

**aspark-graph tool used as scoping input** (`staleness` → fresh; `impact` on `confinement.py`,
`build.py`, `queries.py` → all three `in_graph: true`, `unknown_files: []`; `story_trace US-1
--feature security-posture` → `found: true`). Every hit was `inferred`-tier, so it only told me
which files to open — I read the code behind each verdict directly and did not rest any finding
on graph output.

**Not verifiable from the repo:** AC-2.8 (GitHub "private vulnerability reporting" enabled) is a
GitHub UI setting; the plan records the maintainer confirmed it (T7). Flagged as an open item to
eyeball in the Security tab, not a code finding. The old-code-vs-new-code byte-identity stash run
(plan §6) I did not re-execute; I confirmed its two supporting facts instead (double-build test
green; `build.py` changes are inert for marker repos with no oversized file).

## 2. Plan Conformance

Verified independently — no deviations. R1 (fixtures *marked*, no bypass) is implemented exactly
as the plan's §1 decision states, not as the spec's accepted Q3/A11 bypass. The user accepted R1
at the plan gate (plan gate line, 2026-07-27), so this is conformant.

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ | `confinement.py` stdlib-only; three markers; OS errors folded into `OutsideConfinementError`; constants + basis in docstring. |
| T2 | ✅ | Autouse `conftest.py` fixture marks every `tmp_path` with empty `.spark/`; `test_no_spark_builds_code_only` relocated to a `.git`-marked subdir. |
| T3 | ✅ | `build_graph` calls `ensure_repo` first; both adapters render `RepoRefused`. |
| T4 | ✅ | `ensure_repo` in `load_graph`/`staleness`/`impact_diff`; `_open` renders it; table-driven 8-tool + registry test. |
| T5 | ✅ | Refusal rows added to the *existing* parity file; AC-1.8 default-`repo="."` regression present. |
| T6 | ✅ | AST-based adapter guard (not keyword-only), no-bypass surface guard, no-env-read, patched-read NFR-1 guard. |
| T7 | ⚠️ | User-owned GitHub setting; not verifiable from repo — see §1. |
| T8 | ✅ | Bounded collector raises before parsing; no partial graph; byte-identity preserved. |
| T9 | ✅ | `stat().st_size` checked before `read_bytes`; unparsed node carries no `hash` key; symlink-cycle characterised. |
| T10 | ✅ | `SECURITY.md` — six non-guarantees, asymmetric bound basis, honest prose (read below). |
| T11 | ✅ | README/CLAUDE.md prose fixed at source; both link `SECURITY.md`. |
| T12 | ✅ | Injection warning in both copied integration blocks with a `SECURITY.md` anchor link. |

## 3. Findings

No Blockers, no Majors, no Minors.

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Nit | `build.py:104-110`, `build.py:53-65` | A size-skipped file is appended to **both** `report.unparsed` and `report.size_skipped`, so `summary()` can read `"1 file(s) unparsed, 1 file(s) skipped (over size limit)"` for a single file — a reader may parse it as two files. Consistent with the existing "no extractor" unparsed pattern and harms no AC (AC-3.2 only requires the size-skipped count), so cosmetic. Fix (optional): exclude size-skipped nodes from `unparsed`, or word the summary so the two counts don't look additive. | accepted by user (2026-07-27) — cosmetic, no AC impact |

## 4. Requirements Traceability

| Spec ID | Implemented at | Verdict |
|---|---|---|
| AC-1.1/1.2 | `build.py:75`, `cli.py:167`, `server.py:24-27` | ✅ CLI 1-line+exit 1, MCP dict; no `.aspark-graph/` created (verified live on `/tmp`, <1s). |
| AC-1.3 | `test_confinement_cli_mcp.py:118` + registry test | ✅ Iterates `_QUERY_NAMES`; a 9th tool without a row fails first. |
| AC-1.4/1.6/1.11 | `confinement.py:105-116` | ✅ `.git` file/dir, `.spark/`, `graph.json`-file each accepted; symlink resolved; `.aspark-graph/` w/o `graph.json` refused. |
| AC-1.5 | `confinement.py:78-88,114` | ✅ `OSError`/`resolve` failures folded to `OutsideConfinementError` (T1 chmod-000 test). |
| AC-1.7 | `test_cli_mcp_parity.py:_confinement_rows` | ✅ One table, accept+refuse rows, CLI==MCP; in the existing file. |
| AC-1.8 | `queries.py:30-31` | ✅ `ensure_repo` return discarded; `default_graph_path(repo_root)` uses the original arg — relative message byte-identical (test asserts exact string). |
| AC-1.9 | `build.py:75`, `queries.py:30,212,247` | ✅ All four library entry points call `ensure_repo`; direct-call tests raise `RepoRefused`. |
| AC-1.10/NFR-9 | `test_confinement_guards.py` | ✅ No bypass name on the public surface, no env read, `ensure_repo` arity 1, no CLI flag / MCP param matches. Marking means there is no second path to be reachable. |
| AC-1.12/1.13 | `test_confinement_cli_mcp.py:74,93,182` | ✅ Fresh unmarked dir refused after a prior build elsewhere; graph-only dir (marker deleted post-build) accepted by all eight. |
| AC-2.1–2.7,2.9 | `SECURITY.md`, `test_security_doc.py` | ✅ Trust boundary, six non-guarantees, denylist, output-is-data, reporting, asymmetric bound basis — all present and read honestly (§6). |
| AC-2.8 | GitHub setting (T7) | ⚠️ Not verifiable from repo — confirm in Security tab. |
| AC-2.10 | README `### MCP`, CLAUDE.md | ✅ `build_graph` marked as writing; "disposable read model" qualified to the artifact; both link `SECURITY.md`; no read-only-surface claim. |
| AC-3.1 | `build.py:155-170`, `confinement.py:91-102` | ✅ Generator exhausts the bounded `rglob` collection on first advance, before any `read_bytes` — bound raises pre-parse; no partial graph. |
| AC-3.2 | `build.py:100-110` | ✅ `stat().st_size` before `read_bytes`; node has **no** `hash` key (verified: `"hash" not in node`), `unparsed_reason="size"`, `size_bytes` set; exit 0. |
| AC-3.3 | `test_build_bounds.py:162` | ✅ Ancestor-symlink build terminates (rglob does not recurse symlinks; entry bound is a backstop). |
| AC-3.4/NFR-2 | `test_build_bounds.py:88,153` + suite | ✅ Double-build byte-identical; `sample_repo`/this repo unaffected (no oversized file, marker present). |
| AC-4.1 | `docs/aspark-integration.md` (both blocks) | ✅ Data-not-instruction paragraph + `SECURITY.md` anchor in each copied block. |
| NFR-1 | `confinement.py:105-116` | ✅ Only `resolve`/`is_file`/`is_dir` — no content read; guard patches `open`/`read_bytes`/`read_text` (and `Path` uses nothing else, so the patch set is complete); 1000 verdicts <100ms each. |
| NFR-3/6 | adapters + `confinement.py` | ✅ Every refusal path renders 1 line / dict; no traceback (verified live + tests). |
| NFR-4 | tool names/args unchanged; `pyproject` deps untouched | ✅ Only additive `reason` values; `mcp>=1.12,<1.20` intact. |
| NFR-7 | `test_confinement_guards.py:80-96` | ✅ AST guard proves adapters touch only `confinement.RepoRefused`; no marker string/constant in either. |
| NFR-5 | human read (§6) | ✅ Read every guarantee sentence against the code; no overclaim found. |

**R1 verified independently:** (a) no bypass mechanism is reachable — the guard tests are
introspection/AST-based, not tautological keyword checks, and there simply is no second code path
to reach; (b) the "empty `.spark/` is graph-neutral" claim holds — `artifacts.extract_features`
(`artifacts.py:57-65`) iterates `.spark/` *sub-directories* and returns 0 when there are none, so
the autouse marker adds no node. **F1/close-the-loop:T9 edge loss verified:** `inference.py:71-103`
— a history commit whose message names only `T9` (task-only, no story) now matches this feature's
own `T9` *and* `close-the-loop:T9`, so `resolved` has two features → dropped. Exactly the F1
non-negotiable behaving correctly; not a regression. **Scope discipline:** no README "Limits"
section and no `200,000`/`5 MB` numbers in README/CLAUDE.md (grep clean); no read-only `build_graph`.

## 5. What Was Checked

- [x] Correctness: all Must ACs trace to code; US-3/US-4 too; traced independently, not via the graph
- [x] Non-functional: NFR-1/2/3/4/5/6/7/9 hold; thin-adapter and determinism non-negotiables intact
- [x] Error handling: every refusal renders cleanly; OS errors folded; no swallowed failures
- [x] Security: `SECURITY.md` read as a human — honest, non-overclaiming; denylist holds; no secrets
- [x] Tests: 275 pass + 2 slow pass; guards are meaningful (AST/patched-read), not decorative
- [x] Readability: `confinement.py` is small, documented, boring in the good way

## 6. Verdict

This is a clean, honest implementation that does exactly what the spec and plan promised, and the
plan's most contested decision — R1, marking fixtures instead of shipping a test-only bypass — is
not just defensible but stronger than the alternative: I confirmed for myself that no second code
path exists to be reached, so AC-1.10/NFR-9 are satisfied by construction rather than by policing.
The confinement rule reads no file contents, refuses in milliseconds, and folds every OS error into
one legible message; the build bounds raise before parsing and leave accepted repos byte-identical;
and `SECURITY.md` reads as a document that wants to be checked against the code rather than to
impress — every non-guarantee is true, the injection warning is real, and the two bounds are
presented with honestly different provenance. The full suite (275 + 2 slow) is green, the live CLI
refuses a non-repo in under a second with one line, and this repo still builds and answers. The
single finding is a cosmetic double-count in the build summary (F1, Nit) that harms no acceptance
criterion. Two things stay outside my reach and are logged, not waved through: AC-2.8 (the GitHub
private-advisory setting) is a maintainer UI action I cannot see, and the old-vs-new stash
byte-identity run I corroborated indirectly rather than re-executing. **Passed.**

---

## ✅ REVIEW GATE

- [x] No open Blocker findings
- [x] No open Major findings
- [x] Every Must AC traces to implementing code; no constitution non-negotiable violated
- [x] All plan deviations documented and accepted — none found (R1 is plan-conformant and user-accepted)
- [x] Test suite runs green — 275 passed + 2 slow passed
- [x] Status set to `passed`
