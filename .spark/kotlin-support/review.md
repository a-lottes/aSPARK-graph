# Review: kotlin-support

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Status** | `passed` |

Plan conformance checked against AC-1.1 to AC-2.1; full suite green (391 passed).
Known limit: the grammar mis-parses some one-line `object X { fun f() {} }` bodies; multi-line bodies parse fully.

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Nit | `code_kotlin.py` | Grammar mis-parses some one-line object bodies; documented, not fixable here. | accepted |
