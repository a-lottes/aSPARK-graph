# Release notes: close-the-loop (shipped in aspark-graph 0.3.0)

| | |
|---|---|
| **Phase** | Keep |
| **Status** | `preparing` (bundled into 0.3.0) |
| **Version** | v0.3.0 |
| **Date** | 2026-07-16 |

close-the-loop was planned as 0.2.0 but **never shipped on its own**. It is
released as part of **aspark-graph 0.3.0**, bundled with the distributable-install
feature. Its review gate is `passed` (see `review-report.md`).

## What close-the-loop delivers (user-facing)

- **`impact` and `story_trace` return real answers on ordinary repos.** Task→code
  links are now inferred from git history when your commits mention story/task ids,
  so the two headline queries stop coming back empty on repos that never
  hand-annotated the link.
- **`impact --diff <range>`** — scope impact from a commit/branch range instead of
  listing changed files by hand.
- **`staleness` detection** — the tool warns when the graph no longer matches the
  repo it was built from.
- **An `inferred` confidence tier** — weaker than `declared`/`extracted` — so a
  git-history-derived link is visibly distinguishable from a certain one.
- **Fixed: cross-feature id-collision (F1)** — a file is no longer mis-attributed to
  a same-numbered story in a different feature; results are scoped to the feature
  that owns the code.

## Full details

The complete 0.3.0 changelog, pre-flight results, rollback path, pending publish
commands, and learnings live in the release report for the feature carrying the
0.3.0 bump:

→ **`.spark/distributable-install/release-notes.md`**
