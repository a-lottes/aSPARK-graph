# Review Report: kotlin-support

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Status** | `passed` |
| **Date** | 2026-11-10 |

## 1. Scope
Working-tree diff for issue #29: `code_kotlin.py`, `base.py`, `extractors/__init__.py`, `build.py`, `pyproject.toml`/`uv.lock`, README, tests.

## 2. Verification
- Full suite: 401 passed (`uv run pytest`). Slow: packaging + MCP transport pass; `test_fresh_install` not run (no network). `test_nfr1_incremental...` fails at 35-49% speedup, **identically on the unchanged baseline (49.2%)** — container timing noise, not caused by this diff.
- Determinism (AC-3.2): double-build test for Kotlin; the only graph differences when building this repo with old vs new code are the new `build.py` functions themselves.
- Probed the pinned grammar for node shapes (package/import/class/companion/enum/extension); grammars 1.0.0/1.0.1 also probed.

## 3. Findings
- **Minor (documented, R1):** single-line `class A { fun m() {} }` parses with an ERROR node in grammar 1.1.0; the function is recovered but may not nest. Not fixable here without changing the grammar.
- **Minor:** `.kts` scripts have no package, so imports into them are unaffected; resolved imports out of them work.
- No Critical/Major findings.
