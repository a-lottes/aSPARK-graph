# Review Report: aspark-graph

| | |
|---|---|
| **Phase** | Review |
| **Owner** | Reviewer (`/peer-review`) |
| **Input** | Working tree of `aspark-graph` (new repo, no git history), `.spark/aspark-graph/plan.md` |
| **Status** | `passed` |
| **Date** | 2026-07-14 |

## 1. Scope

Reviewed the entire working tree (no git history exists, so there is no diff —
the whole tree is the change):

- `src/aspark_graph/`: `model.py`, `graph.py`, `build.py`, `artifacts.py`,
  `queries.py`, `cli.py`, `server.py`, `extractors/{base,__init__,code_py,code_ts,code_java}.py`
- `tests/` (57 tests) and fixtures under `tests/fixtures/`
- `README.md`, `pyproject.toml`, `LICENSE`, `.gitignore`

Verified by running: `uv run pytest` (57 passed), `uv run aspark-graph build .`
(238 code / 45 artifact entities), a byte-for-byte double-build determinism check
on the real repo, `story_trace`/`impact`/`gate_health` against the real dogfood
trail, and targeted probes of the confidence logic, QA-result normalisation, the
drift-failure path, and vendored-directory exclusion.

**Not reviewed:** the live-Claude-Code MCP handshake and the clean-`uvx` install
smoke — both are explicitly assigned to `/demo-day` by the plan's test strategy
and confirmed by D3. The in-memory FastMCP client path *is* exercised in tests, so
tool dispatch is covered; only the external session/install remain for QA.

## 2. Plan Conformance

The architecture (§1) and layout (§2) were followed faithfully: Python ≥3.11 / uv,
FastMCP stdio server, networkx `MultiDiGraph`, py-tree-sitter with all three grammar
packages, a single canonical `graph.json` under `.aspark-graph/`, and — the one
load-bearing convention — CLI and MCP as thin adapters that both call `queries.py`
/ `build.py` and contain no query logic of their own. AC-5.1 parity is structural
and asserted.

| Task | Implemented as planned? | Note |
|---|---|---|
| T1 | ✅ | Scaffold, entry point, uv-managed; `uv run pytest` green. |
| T2 | ✅ | `model.py` ids/enum + `graph.py` canonical sorted save; byte-stable round-trip tested. |
| T3 | ✅ | Python extractor + build + `get_node` + CLI/MCP wired; MCP exercised via in-memory client. |
| T4 | ✅ | Counts, no-`.spark/` code-only path, deterministic double-build all tested (AC-1.1/1.2/1.4). |
| T5 | ✅ | Version-pinned structural drift detection naming file+mismatch (AC-1.3); dogfood spec parses. |
| T6 | ✅ | `story_trace` covers AC-2.1..2.5, incl. best-effort `implements` absence handled as non-error. |
| T7 | ✅ | `impact` reachability + weakest-edge confidence (AC-3.1..3.5) verified against fixtures and by hand. |
| T8 | ✅ | CLI≡MCP parity asserted; build-first message clean, no trace (AC-5.2). |
| T9 | ✅ | TS/JS extractor incl. arrow-binding functions + relative import resolution. |
| T10 | ✅ | Java extractor (package/class/method/import); AC-4.2 unparsed path proven by un-registering an extractor. |
| T11 | ✅ | `find_nodes`/`get_neighbors`/`shortest_path` (AC-7.1/7.2). |
| T12 | ✅ | `gate_health` orphan tasks / unverified ACs / open findings (AC-6.1..6.3). |
| T13 | ✅ | README documents both surfaces and LICENSE added (D4). Grammar/dep exact-pin gap (F2) reconciled in fix-mode: the three grammars + tree-sitter core are now `==`-pinned; fastmcp/networkx floor + `uv.lock` documented as their determinism contract. |

**Deviations D1–D4 (plan §6):** all verified as described, none silent.
- **D1** — best-effort `implements` via an inline `files:` note in a task-row DoD,
  resolved to a `File` node only when it exists (`artifacts._parse_plan`,
  `_files_note`). Matches the A3/Q1 "explicit note happens to exist" path; absent
  note → no link, no error. Confirmed by `story_trace` on the demo fixture (T1 links,
  T2 does not).
- **D2** — all three extractors shipped; the AC-4.2 unparsed path is still proven by
  test (`test_ac_4_2_...` un-registers Java). Confirmed.
- **D3** — `requires-python = ">=3.11"`; runtime provisioned newer, floor holds.
  Clean-install verification is a `/demo-day` item.
- **D4** — MIT `LICENSE` present. Confirmed.

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Minor | `cli.py:143` (`_cmd_build`) | On template drift the CLI build let `TemplateDriftError` propagate, dumping a full Python traceback to the user. AC-1.3's *content* (file + mismatch) was present and exit code was 1, but a raw traceback violates the same CLI-UX contract the spec sets for AC-5.2 ("not a stack trace"). Why it matters: drift is the expected, user-facing failure mode of the crown-jewel parser; it should read as a clean error, not a crash. Fix: catch `TemplateDriftError`, print `str(exc)` to stderr, return 1 — mirroring the existing `GraphNotBuiltError` handling. **Fixed** by the reviewer; re-ran `uv run pytest` → 57 passed, and `aspark-graph build <drifted>` now prints one clean line and exits 1. | fixed |
| F2 | Minor | `pyproject.toml:12-17` | Dependencies (incl. the three tree-sitter grammars) are pinned with `>=`, but plan §2 ("pin **exact** versions for determinism (AC-1.2)") and §5's packaging risk both call for exact pins. Why it matters: a future resolver run could pull a grammar version whose parse tree differs, silently changing extracted nodes/edges and breaking AC-1.2 for a fresh environment. Mitigating fact: this is a uv-managed project with a committed `uv.lock` that pins exact resolved versions, and the byte-stable double-build test passes — so determinism holds *today*. Fix: either tighten to `==`/`~=` compatible-release pins for the grammar packages, or (cheaper) document that `uv.lock` is the determinism contract and must ship. Left open as a documented plan deviation for `/increment` to reconcile — not a correctness defect at HEAD. **Fixed** (fix-mode): the three tree-sitter grammar packages + core are now pinned `==` exactly (they alone affect parse output → the graph bytes); a code comment documents that fastmcp/networkx are covered by a floor + `uv.lock`, since they don't affect the canonicalised serialisation. Re-ran `uv sync` + `uv run pytest` → green; byte-stable rebuild re-confirmed with `diff`. | fixed |
| F3 | Minor | `artifacts.py:342` (`_normalise_result`) | `\bpass\b` / `\bfail\b` do not match the words "passed" / "failed" (they map to `"unknown"`). Why it matters: a QA author who writes "Passed" instead of the template's `✅ pass` would have their AC silently read as unverified, quietly weakening `story_trace` (AC-2.3) and `gate_health` (AC-6.2). Not a conformance defect: the pinned QA template (`qa-report.md`) prescribes the `✅ pass / ❌ fail` form, which the parser handles correctly (verified). Fix: broaden to `pass(ed)?` / `fail(ed)?` so common phrasings are robust. **Fixed** (fix-mode): broadened to `pass(ed|es|ing)?` / `fail(ed|s|ing|ure)?`, with a parametrised test covering `passed`/`Failed`/`PASSES`/`failure` and the `✅/❌` forms. Suite green. | fixed |
| F4 | Nit | `queries.py:269` (`find_nodes`); `build.py:79` (`_iter_source_files`) | Two harmless roughnesses: (a) `find_nodes("")` matches every node (empty substring is in everything); (b) `rglob("*")` enumerates files inside skip-dirs before filtering, so a repo with a large `node_modules`/`.venv` is stat-walked in full each build. Why it matters: (a) is a mildly surprising API for a null query; (b) is an unbounded-ish walk, though A6 accepts full-rescan cost and skip-dirs are correctly excluded from the graph (verified: zero vendored files leaked). Fix: guard `find_nodes` against an empty query; prune skip-dirs during traversal. Neither affects any AC. **Accepted** by the user (2026-07-14): no change — (a) is a harmless null-query convenience, (b) is bounded by A6's accepted full-rescan cost and skip-dirs are correctly excluded from the graph. Candidate for a Tier-1 cleanup. | accepted |

No Blocker or Major findings. No security issues found: no `eval`/`exec` of parsed
content (tree-sitter parses, never executes); user-supplied paths are only used for
lookup/normalisation, never for arbitrary filesystem writes outside `.aspark-graph/`;
no secrets in code or logs; file contents are trusted only as far as parsing.

## 4. What Was Checked

- [x] Correctness: logic does what the acceptance criteria demand
- [x] Error handling: failures are handled, not swallowed
- [x] Security: no injected input trusted, no secrets in code
- [x] Tests: exist, are meaningful, and pass
- [x] Readability: the next developer will understand this

Notes on the crown jewels, verified by hand as well as by test:
- **`story_trace`** returns title + all ACs (AC-2.1), exactly the mapped tasks with
  status (AC-2.2), each AC's most-recent QA verdict (AC-2.3), `declared`-tagged code
  links where a `files:` note exists and an empty (non-error) `code` list where it
  does not (AC-2.4), and an explicit `not_found` naming the id — plus a graceful
  `ambiguous` result for bare ids spanning features (AC-2.5).
- **`impact`** widest-path (max-bottleneck) reachability tags each story/AC with the
  **weakest** edge confidence on its strongest path: `app.py` reaches US-1 at
  `declared` (via the declared `implements`→`maps_to` chain) while `util.py` reaches
  it at `extracted` (its path runs through an `imports` edge) — AC-3.5 confirmed
  live. Unknown paths are named while known files are still answered (AC-3.4);
  a file with no artifact path reports an explicit note (AC-3.3).
- **Determinism (AC-1.2):** canonical sorted, `sort_keys` JSON; two builds of the
  real repo produced byte-identical `graph.json` (checked with `diff`).
- **Drift (AC-1.3):** all four parsed artifact types fail loudly naming file +
  mismatch; F1's fix makes the CLI presentation clean.

Tests are meaningful, not tautological: they assert concrete node/edge presence,
specific confidence tags, exact status/QA values, and negative cases (orphan task,
failing AC, unknown id, no-path). The dogfood test parses the tool's own real
`spec.md`. Coverage maps to every Must AC (US-1 → build/artifacts tests, US-2 →
story_trace, US-3 → impact, US-4 → both extractor suites incl. the three-language
single-build and the unparsed path).

## 5. Verdict

This is a boring diff in the best sense: the architecture the plan promised is the
architecture that shipped, the thin-adapter convention makes CLI≡MCP parity true by
construction rather than by hope, and the two crown-jewel tools are correct against
both fixtures and hand probes — the weakest-edge confidence tagging, which is the
easiest thing in this spec to get subtly wrong, is right. All four documented
deviations are real, in-scope, and match their D1–D4 descriptions; nothing drifted
silently. I found no Blocker or Major issues; the four findings are a traceback that
should have been a clean error (which I fixed and re-verified green), a plan-vs-code
gap on exact dependency pins that the committed lockfile currently compensates for,
and two low-risk robustness nits — none of which touch a Must acceptance criterion.
The suite is 57 green after my fix. This increment passes review and is ready for
`/demo-day`, whose remaining job is the live-session MCP check and the clean `uvx`
install that only a real environment can confirm.

---

## ✅ REVIEW GATE

*All boxes checked → `/demo-day` may start. Any box open → back to `/increment`.*

- [x] No open Blocker findings
- [x] No open Major findings (or explicitly waived by the user, with reason recorded here)
- [x] All plan deviations documented and accepted
- [x] Test suite runs green
- [x] Status set to `passed`
