# Review: kotlin-support

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Status** | `in-review` |
| **Date** | 2026-11-11 |

## 1. Findings

No blocking findings. Full suite passes (396 tests); cli.py/server.py untouched. Known limit: a wildcard `import a.b.*` is indistinguishable in the grammar from `import a.b`, so the extractor reads the import text for the `*`.
