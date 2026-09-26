# Plan: current-artifact-names

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Engineering Manager (`/sprint-plan`) |
| **Input** | `.spark/current-artifact-names/spec.md` (`approved`, 2026-09-24) |
| **Status** | `approved` |
| **Date** | 2026-09-24 |

> **Revision 1 (2026-09-24).** *Trigger:* spec C12. At the start of `/increment`, before any
> code was written, it turned out that A1 had materialised for QA. Core's current
> `templates/qa-report.md` and every current `qa.md` head the verification table
> `Spec ID | … | Result`, but `_parse_qa` requires an `AC` column. v0.7.0 on a steamcore `qa.md`
> renamed to `qa-report.md` → `template drift … missing an 'AC' column`. *What changed:*
> Decision 5 (header-based QA id column: `AC` or `Spec ID`; neither is drift). The T1 fixture
> now uses the real current header plus an NFR row. There are new tests in T2/T5, and T5's
> early check now covers steamcore as well. §1 Context, Alternatives and Consequences, §2, §4
> and R1 are updated, and R8/Q1 are new. Stories, task ids and every other decision are
> unchanged.

<!-- Handoff: read this block first, the numbered sections below by exception. Whoever
     writes to this plan updates it in the same edit that changes a task's status or
     the plan's own status: overwrite in place, never append. The block holds one
     current state, never a per-round log; a stale block is a defect, not a cosmetic
     issue. -->

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Summary:** One fixed `(kind, current, legacy)` name table in `artifacts.py`; each artifact resolves on its own, current name first. A shadowed legacy file goes onto `BuildReport.shadowed`, never into the graph; the CLI prints it to stderr, and MCP `build_graph` returns it as `ignored_legacy_files`. `_parse_qa` recognises the id column by header, either `AC` (the v0.7.0 path, unchanged) or `Spec ID` (the current template); a table with neither is drift. No new dependency. Target v0.7.1.
- **Open:** `2 tasks not done` (T7–T8, go-live; T5c done, re-review and re-QA pending) (see §3 Task Breakdown). One question for the user, Q1 (per-story QA sub-tables, R8), which would add a task and does not change this design. **Process constraint:** this feature's own review/QA/release files must use the **legacy** names (`review-report.md`, `qa-report.md`, `release-notes.md`). See R2.
- **Binding ruling:** §3 Task Breakdown for current task status; a plan revision after review/QA findings updates §1/§3 in place, never a new section
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

<!-- Budget: ~300 lines. -->

> **Revision 2026-09-25 (scope addition, user ruling in conversation — spec C13):** the early
> A1 check in T5 found `_normalise_result` reading `⚠️`/`❌` rows as `pass` when the cell also
> contains the word "pass". New task **T5b** fixes the precedence (❌ → fail, ⚠️ → unknown,
> ✅ → pass, then words) with tests on the five real rows. No other decision changes.

> **Revision 3 (2026-09-25, approved by the user 2026-09-25).** *Trigger:* QA bug B1 (spec C14): an
> escaped pipe inside a QA cell shifts the columns, so `✅ pass` rows read `unknown`. *What
> changed:* new task **T5c**; `_first_table`/`_split_row` get an opt-in `unescape_pipes` flag,
> set only by `_parse_qa`. Review, plan and other tables are untouched, so this repo's own
> trail stays byte-identical. QA B2 →
> G6 (accepted), B3–B6 → BACKLOG G8.
 Architecture Decision

- **Context:** `_parse_feature` (`src/aspark_graph/artifacts.py:76-99`) hard-codes
  `review-report.md`, `qa-report.md` and `release-notes.md`. Core now writes `review.md`,
  `qa.md` and `release.md`. **Review and release** have the same structure under the new
  name: the Findings table is `# | Severity | Location | Finding | Status`, and the Status and
  Version rows are unchanged. **QA does not** (C12). Core's current template
  (`aSPARK/templates/qa-report.md:50`), all 13 steamcore `qa.md`, all 13 Core `qa.md` and
  aspark-demo head the verification table `| Spec ID | Steps performed | Expected | Observed | Result |`.
  Their rows mix `AC-n.m` and `NFR-n`. `_parse_qa` (`artifacts.py:234-242`) demands a header
  that equals or starts with `ac` and reads the id via `_col(row, "ac")`. Our own legacy
  trail (`.spark/aspark-graph/qa-report.md:31`) and `tests/fixtures/sample_repo` use `| AC | …`.
  `extract_features` runs on every build, including incremental ones, because the parse
  cache covers only code (`build.py:141`), so artifacts have no cache to interact with.
  The binding rules are the CLAUDE.md non-negotiables: determinism (byte-identical builds),
  fail loudly on drift, thin adapters, CLI ≡ MCP parity, and errors through the existing
  exception→adapter seam. There is no constitution. Output channels today:
  `cli._cmd_build` prints the summary to stdout and notices to stderr (`cli.py:173-178`).
  `server.build_graph` returns a dict built from `BuildReport` (`server.py:29-36`).
- **Decision:**
  1. **Name table + resolver.** Add a module-level table to `artifacts.py`:
     `_ARTIFACT_NAMES = (("review", "review.md", "review-report.md"), ("qa", "qa.md",
     "qa-report.md"), ("release", "release.md", "release-notes.md"))`. A helper,
     `_resolve(feature_dir, current, legacy, shadowed) -> Path | None`, returns the current
     file if it `exists()`. If the legacy file also exists, it appends the repo-relative POSIX
     path `.spark/<feature>/<legacy>` to `shadowed`. Otherwise it returns the legacy file if
     that exists, or `None`. `_parse_feature` uses it for these three kinds. `spec.md` and
     `plan.md` are not touched. Resolution is per artifact (A2): a folder with `qa.md` and
     `review-report.md` reads both.
  2. **The notice lives only in the build report.** `extract_features(repo_root, graph,
     shadowed: list[str] | None = None) -> int` gets an optional out-parameter. The return
     type and every existing caller and test stay the same. `BuildReport` gets
     `shadowed: list[str]` (default empty), which `build.py` passes through. The order is
     fixed: feature dirs are already sorted (`artifacts.py:63`), and within a feature the
     order is review, qa, release. It never depends on directory listing order (NFR-1).
  3. **Adapters render the list and add no logic.** The CLI prints one stderr line per path,
     `Ignored .spark/<f>/qa-report.md (qa.md takes precedence)`, and exits 0. MCP
     `build_graph` adds `"ignored_legacy_files": report.shadowed`, always present like
     `unparsed`. Neither adapter computes anything, so parity is by construction (AC-4.5,
     NFR-3). Nothing is written to `graph.json` (AC-4.6).
  4. **Drift reuses the parsers.** A resolved `qa.md`/`review.md` goes through the same
     parser, which raises `TemplateDriftError(str(path), …)`. The error therefore names the
     current-name path (AC-5.2).
  5. **QA id column is recognised by header, never by file name.** A new helper,
     `_qa_id_column(header) -> str | None`, is checked in this fixed order on the lower-cased,
     stripped header cells:
     (a) a cell exactly `ac` → `"ac"`;
     (b) a cell exactly `spec id` → `"spec id"`;
     (c) a cell starting with `ac` → `"ac"` (today's looser legacy rule, kept verbatim);
     (d) none of these → `TemplateDriftError(path, "QA table missing an 'AC' or 'Spec ID'
     column (found [...])")`.
     The row loop is unchanged apart from `_col(row, id_col)` replacing `_col(row, "ac")`.
     `re.search(r"AC-\d+\.\d+")` on the id cell still skips `NFR-n` and any other non-AC row,
     `index` still counts every data row, and the `Result` check is unchanged. No node
     attribute records which header was used, so the same rows under either header give
     identical nodes.
     **What still counts as drift:** a missing verification section, a table without a
     `Result` column, and a table whose id column is neither `AC` nor `Spec ID` (for example
     `ID`, `Criterion`, `Spec-ID`). Drift is raised under either file name.
     **Byte-identity:** a v0.7.0-parsable table without a `spec id` cell hits (a) or (c),
     which is the v0.7.0 path. Our repo's `| AC |` table hits (a). The only observable change
     for legacy files is the wording of the drift message, which is error text and not graph
     content. (b) comes before (c) so that a current table with a column like `Actual …` can't
     capture the id column.
- **Alternatives considered:**
  | Alternative | Why rejected |
  |---|---|
  | **Read both files and merge their nodes** | A3/§6 rule this out. Stale legacy rows would double or contradict the QA picture, which is what US-4 exists to prevent. |
  | **Resolve per feature** ("current layout if any current file exists") | Contradicts A2/AC-4.3. A half-migrated folder would lose a real artifact. |
  | **Put the notice in the graph** (`shadowed` attr on the Feature node) | Breaks AC-4.6/AC-5.3 byte-identity and turns a build diagnostic into query data. |
  | **Emit it through `logging`/`warnings`** | Parity would depend on each adapter's handler setup. A plain list on `BuildReport` follows the `unparsed`/`fallback_reason` precedent. |
  | **Glob-based file matching** (`*qa*.md`) | §6 puts other names out of scope. It risks non-deterministic ties and would silently read files like `qa-notes.md`. |
  | **`extract_features` returns `(int, list)`** | Breaks the four direct callers in `tests/test_artifacts.py`, which violates NFR-2 (zero modified expectations). |
  | **Print the notice to stdout** | stdout carries the build result. Notices already go to stderr (`cli.py:174`). |
  | **QA id column chosen by file name** (`qa.md` → `Spec ID`, `qa-report.md` → `AC`) | File name and template generation are independent: the C12 repro was a `Spec ID` table in a `qa-report.md`. It would also break AC-5.3, because renaming a current trail to legacy names would turn it into drift. |
  | **Loose id match** (any header containing `id`, or sniffing cells for `AC-n.m`) | It would silently accept `Bug ID`/`#` columns or guess. That contradicts "fail loudly on drift" and makes the pin unfalsifiable. |
  | **Switch the pin to `Spec ID` only** | Legacy `AC` tables (this repo, `sample_repo`, older adopters) would drift, which breaks AC-5.1/NFR-2. |
  | **Warn and skip a QA table with an unknown header** | Ruled out by C2 and §6 (no warn-and-skip mode). |
- **Consequences:** *Easier:* another file name means one more row in the table, and another
  QA id header means one more branch in `_qa_id_column`. `gate_health` and `story_trace`
  become correct on current projects with no change to query code. Core's tool doc
  (`aSPARK/tools/aspark-graph.md`, "Not wired") can reopen `gate_health` once v0.7.1 ships;
  that is a Core follow-up. *Harder:* current projects now get their QA and review files
  parsed, so a project whose files drift in other ways will see its build go **red** where it
  used to pass by accident (C2, accepted). The QA pin is now two headers wide, and the helper
  owns that knowledge. The MCP result gains one key (additive). *Not solved here:* the
  per-story sub-tables in the QA section (R8/Q1).

## 2. Affected Components

**New dependencies, services, patterns: none.** stdlib `pathlib` only. The only new
pattern is the name table plus the QA header helper, both justified above.

| Component | Change |
|---|---|
| `src/aspark_graph/artifacts.py` | `_ARTIFACT_NAMES`, `_resolve`, `_qa_id_column` + the one-line `_col` switch and drift message in `_parse_qa`, optional `shadowed` param on `extract_features`, `_parse_feature` uses the resolver (T1, T3). `_parse_review`, `_parse_spec`, `_parse_plan`, `_status` and `_release_version` are unchanged |
| `src/aspark_graph/build.py` | `BuildReport.shadowed` field; pass-through to `extract_features` (T3). `summary()` unchanged |
| `src/aspark_graph/cli.py` | `_cmd_build`: one stderr line per shadowed path (T4) |
| `src/aspark_graph/server.py` | `build_graph`: `ignored_legacy_files` key (T4) |
| `tests/fixtures/current_names_repo/` (**new**) | Committed fixture with current names: `.spark/demo/{spec,plan,qa,review,release}.md` + `src/demo/app.py`. `qa.md` copies Core's header line verbatim and has an `NFR-1` row. Rows use Core's phrasing (`✅ pass`, prose Version cell) |
| `tests/test_current_names.py` (**new**) | US-1–US-5 behaviour, QA header handling, byte-identity, double build |
| `tests/test_artifacts.py`, `tests/test_cli_mcp_parity.py`, `tests/test_readme.py` | New tests **added**. No existing assertion edited (NFR-2) |
| `README.md`, `CLAUDE.md` | Five languages (the uncommitted README change is folded in), artifact-name statement, the release bump |
| `pyproject.toml`, `uv.lock` | 0.7.0 → 0.7.1 (go-live) |

**Queries untouched:** `queries.py` is not touched (§6).

**Blast radius: graph-verified, then read by hand.** The caller ran both queries on 2026-09-24.
Revision 1 adds no new existing path to the union of `files:` notes (`artifacts.py` and
`test_artifacts.py` were already in it), and no code has changed since, so that result stands
and no re-query was requested.

- **`staleness`:** `stale: false`, `files_checked: 107`.
- **`impact`** on the ten existing paths: `found: true`, 7 files in the graph, 10 stories,
  49 ACs. `unknown_files` = `CLAUDE.md`, `README.md`, `pyproject.toml` (not indexed as code,
  as expected). New files were not queried because they don't exist yet.

**Declared links and what they mean here:**
- **`pypi-publish:US-2`** (`tests/test_readme.py` Install tests). T6 only *adds* tests.
- **`security-posture:US-1`** (confinement parity rows in `tests/test_cli_mcp_parity.py`). T4 must not edit `_confinement_rows` or its parametrised test.
- **`security-posture:US-3`** (build bounds in `build.py`). T3 touches only `BuildReport` fields and the `extract_features` call.

**Inferred links (git history, weakest tier).** `close-the-loop` and `distributable-install`
are co-change hints, covered by NFR-2 (the existing suite passes unedited).

**Not in the result:**
- **The base `aspark-graph` feature** (its drift non-negotiable, AC-1.3). Its plan has no
  `files:` notes, so its absence is empty by construction and *not* evidence of no risk.
  Revision 1 touches its drift code directly (`_parse_qa`). It is covered by T5's new
  neither-header drift tests plus the unedited `test_artifacts.py` drift tests.
- **No test asserts the full success dict of `build_graph`.** Found by reading `cli.py:164-179`,
  `server.py:21-36`, `build.py:40-152` and grepping `tests/`. The only whole-dict equalities
  are refusal dicts (`test_confinement_cli_mcp.py:65,124`). No existing test asserts the QA
  drift message text either (grep of `tests/`), so the widened wording edits no test.

## 3. Task Breakdown

**Walking skeleton = T1:** a current-name trail **with Core's real QA header** builds end to
end, and `gate_health` answers correctly. That proves the path resolver → parser → graph →
query before any shadowing or adapter work. **T1–T6 run in `/increment`** and are checked at
Review. **T7–T8 run at `/go-live`**, by a human.

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | **Walking skeleton.** Add `_ARTIFACT_NAMES` + `_resolve` (current first, legacy fallback, per artifact) and switch `_parse_feature` to them. Add `_qa_id_column` (Decision 5, order a→d) and use it in `_parse_qa`. Commit `tests/fixtures/current_names_repo/`: feature `demo`, 2 stories. `qa.md` has the header line copied verbatim from `aSPARK/templates/qa-report.md:50`, every AC `✅ pass`, plus one `NFR-1` row. `review.md` has F1 `open` and F2 `fixed`, F1's location `src/demo/app.py:1`. `release.md` has status `handed-off` and Version `v0.12.0 (proposed, pr mode — no tag)`. qa/review status `passed`. One end-to-end test: build the fixture; `story_trace` US-1 shows AC-1.1 with `latest_result == "pass"`, and `gate_health("demo")["unverified_acs"] == []` | US-1 | AC-1.1, AC-1.2, NFR-5 | – | `done` | The new test passes on the real-header fixture with no drift. `_resolve` builds paths only as `feature_dir / <table literal>`: no glob, no user input (NFR-5, yes/no by reading). In the `_parse_qa` diff, the only changes are the header check, the drift message and `_col(row, id_col)`; the row loop is otherwise untouched (yes/no by reading). Full `uv run pytest` is green — files: src/aspark_graph/artifacts.py, tests/fixtures/current_names_repo/.spark/demo/spec.md, tests/fixtures/current_names_repo/.spark/demo/plan.md, tests/fixtures/current_names_repo/.spark/demo/qa.md, tests/fixtures/current_names_repo/.spark/demo/review.md, tests/fixtures/current_names_repo/.spark/demo/release.md, tests/fixtures/current_names_repo/src/demo/app.py, tests/test_current_names.py |
| T2 | **Story coverage against the fixture.** Tests, each on a tmp copy or the fixture itself: a tmp copy whose `qa.md` fails AC-1.1 puts AC-1.1 in `unverified_acs` (AC-1.3). `get_node(feature:demo)` shows `qa_status == "passed"` and `review_status == "passed"` (AC-1.4, AC-2.3). `open_findings` lists exactly F1 (AC-2.1). A `found_in` edge runs F1 → `file:src/demo/app.py` (AC-2.2). `release_status == "handed-off"` (AC-3.1). `version` equals the prose cell verbatim (AC-3.2). **NFR-row skip:** the fixture's QACheck nodes are exactly its AC rows, and none carries `NFR-1` | US-1, US-2, US-3 | AC-1.1, AC-1.3, AC-1.4, AC-2.1, AC-2.2, AC-2.3, AC-3.1, AC-3.2 | T1 | `done` | One test per AC, each named after its AC id, plus `test_qa_nfr_rows_are_skipped`. All pass. No `src/` change beyond T1 — files: tests/test_current_names.py |
| T3 | **Shadowing.** `_resolve` records the shadowed legacy path. Add the optional `shadowed` param on `extract_features`, `BuildReport.shadowed`, and the pass-through in `build.py` (bounds and `_iter_source_files` untouched). Tests on tmp copies of the fixture: `qa.md` with AC-1.1 passing + `qa-report.md` with AC-1.1 failing → no failing QACheck, AC-1.1 not unverified (AC-4.1). The same for review (legacy F9 `open` absent) and release (legacy status absent) (AC-4.2). `qa.md` + `review-report.md` → QA checks **and** findings, `shadowed == []` (AC-4.3). Both names vs only current names → identical `graph.json` bytes (AC-4.6). Two features, each shadowing two kinds → `report.shadowed` in exact order (feature, then review, qa, release); two builds give equal lists and identical bytes (NFR-1) | US-4 | AC-4.1, AC-4.2, AC-4.3, AC-4.6, NFR-1 | T1 | `done` | The listed tests pass. `extract_features(root, graph)` without a third argument behaves as before, and the existing `test_artifacts.py` passes unedited — files: src/aspark_graph/artifacts.py, src/aspark_graph/build.py, tests/test_current_names.py |
| T4 | **Adapters + parity.** `_cmd_build` prints one stderr line per `report.shadowed` entry and keeps exit 0. `server.build_graph` returns `ignored_legacy_files`. Parity test on a mixed trail (tmp copies A and B of the fixture, each with `qa-report.md` + `release-notes.md` added): `cli.main(["build", A])` and `server.build_graph(path=B)` both succeed, the stderr paths equal the MCP list in the same order, and the two `graph.json` files are byte-identical | US-4 | AC-4.4, AC-4.5, NFR-3, NFR-7 | T3 | `done` | The parity test passes. The CLI names `.spark/demo/qa-report.md` and `.spark/demo/release-notes.md`, one line each, rc 0. A legacy-only build prints no `Ignored` line, and MCP returns `ignored_legacy_files: []`. Neither adapter contains resolution logic (yes/no by reading the diff). The confinement parity rows are unchanged — files: src/aspark_graph/cli.py, src/aspark_graph/server.py, tests/test_cli_mcp_parity.py |
| T5 | **Legacy safety, drift, QA header.** (i) A `qa.md` without the verification section and a `review.md` without Findings each raise `TemplateDriftError`, and `exc.file` ends with `qa.md`/`review.md` (AC-5.2). (ii) **Neither header:** a verification table headed `\| ID \| Steps performed \| Result \|` raises drift both as `qa.md` and as `qa-report.md`. The message contains `'AC' or 'Spec ID'` and `exc.file` names that path. (iii) **Header-independence:** the fixture and a copy whose header cell `Spec ID` is replaced by `AC` build to byte-identical `graph.json`. (iv) **Precedence:** a table `\| Spec ID \| Actual \| Result \|` yields QAChecks from the `Spec ID` column. (v) Rename test: the fixture and a copy with the three files renamed to legacy names → byte-identical `graph.json` (AC-5.3). (vi) Early A1 check: build **scratch clones** (`git clone` into the scratchpad, never the live checkouts) of Core (`/Users/andreaslottes/aSPARK`) and steamcore (`/Users/andreaslottes/steamcore`) with the working tree. Record the SHAs, drift yes/no, QACheck/Finding counts, and, for Core's `graph-gates`, `lean-artifacts`, `project-kickoff` and `tracker-handoff`, QACheck count vs AC rows in the section (R8/Q1 evidence) | US-5 | AC-5.2, AC-5.3, AC-5.4, NFR-2 | T3 | `done` | Tests (i)–(v) pass. `git diff` on existing test files shows additions only (NFR-2). Full `uv run pytest` is green. The scratch builds are recorded in the task notes. Drift in either → stop and raise a finding (C10) — files: tests/test_current_names.py |
| T5b | **Result markers before words (C13).** `_normalise_result` checks explicit markers first — `❌` → `fail`, `⚠` → `unknown`, `✅` → `pass` — and only then the word patterns. Tests: the five real result cells from C13 (verbatim) normalise to `unknown`/`fail`; plain `pass`, `✅ pass`, `❌ fail` unchanged; a fixture copy whose AC-1.1 row is `⚠️ not capturable — never claimed as passed` leaves AC-1.1 in `unverified_acs` | US-1 | AC-1.1, AC-1.3, AC-5.1 | T5 | `done` | Tests pass. This repo's own legacy `.spark/` normalises every QA cell exactly as before (checked by diffing old vs new normaliser over its cells; T8a `cmp` is the binding proof) — files: src/aspark_graph/artifacts.py, tests/test_current_names.py |
| T6 | **Docs.** Keep the uncommitted README change (five languages, "six" removed). Add a short `## Artifacts read` section after `## Supported languages`. It names `spec.md`, `plan.md`, `review.md`/`review-report.md`, `qa.md`/`qa-report.md`, `release.md`/`release-notes.md`, and states that the current name wins, the ignored file is named in build output, and the graph is unaffected. Change `CLAUDE.md:8` to Python, TypeScript/JavaScript, Java, Go, Rust. Add `test_readme.py` checks: no `\bsix\b` (case-insensitive), the five-language sentence is present, and all eight file names appear in the Artifacts section | US-6 | AC-6.1, AC-6.2, AC-6.3 | T4 | `done` | New README tests pass. `CLAUDE.md` lines 8 and 28 name exactly the five languages (line 28 per spec C11; checked by reading, since CLAUDE.md is not in the sdist). Existing README tests, including the three Install tests, pass unedited — files: README.md, CLAUDE.md, tests/test_readme.py |
| T5c | **Escaped pipes in QA cells (C14).** `_split_row(line, unescape_pipes=False)`: with the flag, `\|` is literal `|` inside the cell and only unescaped `\|` separates cells. `_first_table` passes the flag through; only `_parse_qa` sets it. Tests: (i) the QA repro row `\| AC-1.1 \| grep for `a\\|b` \| none \| `x\\|y` returns nothing \| ✅ pass \|` yields QACheck `pass` and AC-1.1 verified; (ii) a row without escaped pipes is unchanged; (iii) a review-report table cell with `\\|` splits exactly as before (scope guard); (iv) fixture copy with the escaped-pipe row builds and `gate_health` lists no unverified AC | US-1 | AC-1.1, AC-1.3, AC-5.1 | T5b | `done` | Tests pass; full suite green; AC-5.1 re-checked byte-identical (this repo's plan/review tables contain `\\|`, which is why the flag is QA-only); Core/steamcore scratch rebuild: the 13 rows now `pass`, counts recorded in the task notes; then re-review and re-QA — files: src/aspark_graph/artifacts.py, tests/test_current_names.py |
| T7 | **(Go-live.) Version bump.** `pyproject.toml` 0.7.0 → 0.7.1, then `uv lock`. CLAUDE.md: "Current shipped version: 0.7.1" plus a `current-artifact-names/` (v0.7.1) trail entry. This is a patch: a bug fix whose only output-shape change is one additive MCP key | US-5 | AC-5.1 | T1–T6 | `todo` | `pyproject.toml` == `uv.lock` self-version == intended tag `v0.7.1`. CLAUDE.md updated. The release commit adds explicit paths (no `git add -A`), so the untracked `aSPARK-graph` symlink stays out — files: pyproject.toml, uv.lock, CLAUDE.md |
| T8 | **(Go-live.) Release evidence, by hand.** (a) AC-5.1: in a **fresh clone of the RC commit**, run `uvx --from aspark-graph==0.7.0 aspark-graph build . --full`, copy `graph.json` aside, run `uv run --directory <checkout> aspark-graph build <clone> --full`, then `cmp`. (b) AC-5.4: build scratch clones of Core and of `github.com/a-lottes/steamcore` (record both SHAs) with the RC. Check for no drift error, count QACheck/Finding nodes from `graph.json` (both > 0), and on steamcore run `gate_health` on one feature whose QA passed everywhere → `unverified_acs: []`. (c) `uv run pytest -m slow` is green (NFR-4). (d) No `review.md`/`qa.md`/`release.md` exists under this repo's `.spark/` | US-5 | AC-5.1, AC-5.4, NFR-4 | T7 | `todo` | `cmp` reports no difference. Core and steamcore both exit 0 with QACheck > 0 and Finding > 0. The slow suite is green, and the glob in (d) is empty. Commands, SHAs and counts are recorded in the release report. Any drift **blocks** the release (C10) — files: .spark/current-artifact-names/release-notes.md |

Every Must AC (US-1, US-2, US-4, US-5) and every Should AC (US-3, US-6) has a task. NFR-1–5 and
NFR-7 are covered, and NFR-6 is N/A (headless). No task is an orphan. AC-5.4 is checked early in
T5(vi) and bindingly in T8(b).

### Task notes (from /increment)

- **T5 (vi), early A1 check, 2026-09-25**, working tree on scratch clones
  (`/private/tmp/claude-501/a1check/`). Core `e1a0005`: no drift; 165 QACheck, 170 Finding.
  steamcore `bf1b3e0`: no drift; 261 QACheck (v0.7.0: 0), 138 Finding (v0.7.0: 0).
  R8/Q1: in 4 of 13 Core `qa.md` the section has `### US-n` sub-tables, and only the first
  table is read → backlog G6 (user ruling, revision 1).
- **T5b (C13), 2026-09-25.** I diffed the old and new `_normalise_result` over every QA result
  cell. This repo: 27 cells, 0 changed. Core: 519 cells, 6 changed (the four C13 rows, plus
  `graph-gates` AC-3.3 `⚠ partial …`, which used to read as `fail` because of the word
  "failure" and is now `unknown`, per the ⚠ rule). steamcore: 491 cells, 1 changed
  (`highscore-system` AC-1.5). After the fix: Core pass 135 / unknown 21 / fail 9,
  steamcore pass 250 / unknown 11. AC-5.1 spot check: a clean clone of `dc3a94c` builds
  byte-identical under v0.7.0 and the working tree (`f7aba174…`). T8a stays the binding proof.
- **T6, 2026-09-25.** README `## Artifacts read` (after Supported languages), CLAUDE.md lines 8 and 28 (five languages, read), 3 new README tests.
- **T5 test placement (review F3).** The planned `tests/test_artifacts.py` additions went into `tests/test_current_names.py`; T5's `files:` note corrected so the graph shows no false link.
- **T5c (C14), 2026-09-25.** `_split_row(line, unescape_pipes=False)`; only `_parse_qa` passes the flag. 3 new tests; the end-to-end test fails when the flag is removed (mutation-checked). AC-5.1 re-checked on a clean clone of HEAD: v0.7.0 and the working tree build byte-identical. Scratch rebuilds: Core pass 135→143, unknown 21→11, fail 9→11 (the 2 new fails are real `❌ fail` rows that the column shift had hidden: situational-lenses AC-5.2, AC-6.1; corrected by review r2); steamcore pass 250→251, unknown 11→10 (`analog-joystick-input` AC-1.5). Incident: while tidying the test file I truncated it; restored from the QA clone copy (identical to the pre-edit state, 314 tests), then re-added the 3 tests.
- **Suite:** `uv run pytest`: 317 passed, `-m slow` 3 passed (was 314 before T5c). `-m slow`: 3 passed. The diff on existing test files is additions only.

## 4. Test Strategy

`/demo-day` does not apply to this headless tool (CLAUDE.md). The equivalent QA runs in
`/peer-review` and the `/go-live` pre-flight.

- **Unit (`test_artifacts.py`, `test_current_names.py`):**
  - resolver precedence per artifact and per mixed folder (AC-4.1–4.3);
  - the drift path for current names (AC-5.2);
  - prose version verbatim (AC-3.2);
  - **QA header recognition:** a `Spec ID` table parses (T1 fixture), a table with neither
    header drifts under both file names (T5 ii), `Spec ID` wins over a prefix-`ac` column
    (T5 iv), and NFR rows are skipped (T2).
- **Integration (build → query, same fixture):** US-1/2/3 through `build_graph` +
  `queries.gate_health` / `story_trace` / `get_node`, the functions the adapters call. No mocks:
  a real build on a committed fixture whose QA header is Core's real one, not a hand-written
  approximation.
- **Byte-identity, proven three ways:**
  1. *Self-consistency (automated):* double build of the fixture, equal `graph.save()` bytes
     (NFR-1).
  2. *Name- and header-independence (automated):* current vs legacy names (AC-5.3), both names
     vs current only (AC-4.6), and `Spec ID` vs `AC` header (T5 iii). Each runs in its own
     `tmp_path` copy with no git, so inference contributes nothing. Compare bytes, not dicts.
  3. *Against real v0.7.0 code (manual, T8a):* per CLAUDE.md, "prove determinism against actual
     pre-change code". The 0.7.0 wheel and the RC build the same clean clone with `--full`,
     then `cmp`. This repo's `| AC |` table takes branch (a) of Decision 5, so T8a directly
     tests the claim that the legacy path is unchanged.
- **CLI ≡ MCP parity (T4):** the existing in-process pattern. Same ignored list in the same
  order, both clean, identical `graph.json` bytes on a mixed trail.
- **Regression (NFR-2):** full `uv run pytest` (275 tests) is green, and the existing test files
  diff shows additions only. `uv run pytest -m slow` (NFR-4) runs at T8.
- **Doc introspection (T6):** `test_readme.py` additions for AC-6.1/6.3. AC-6.2 is checked by
  reading.
- **Manual on purpose:** Core/steamcore evidence (AC-5.4: early in T5 vi, binding in T8b) and
  AC-5.1. Both need external repos or the published old version, which the suite must not
  depend on (Q5).

## 5. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| **R1: A1 drift. Resolved by design for the known case, residual for unknown ones.** The QA header gap (C12) is handled by Decision 5. Review tables and Status/Version rows were checked and match. Residual: another structural difference not yet seen in some current file | Release blocked (C10); a red build for those users | T5(vi) builds scratch clones of **both** Core and steamcore during `/increment`, and T8b is the binding check (AC-5.4). No warn-and-skip (C2). New drift goes back to the PO as a finding |
| **R2: This feature's own trail written under current names.** Core ceremonies now write `review.md`/`qa.md`/`release.md` | v0.7.1 would read what v0.7.0 doesn't → AC-5.1 fails; A4/§6 broken | Per the orchestrator's standing instruction, every later ceremony for this feature (`/peer-review`, `/demo-day`, `/go-live`) writes `review-report.md`/`qa-report.md`/`release-notes.md`. T8(d) globs for current names before the AC-5.1 run |
| **R3: Untracked self-symlink `aSPARK-graph -> /Users/andreaslottes/aSPARK-graph`** in the repo root | Pytest is unaffected. A repo-root build walks `rglob("*")`, and whether it follows the symlink depends on the Python version, so the entry-count bound may refuse or skew the build. Sdist is safe | Leave the file alone. AC-5.1 runs in a **fresh clone** (the symlink is absent there). The release commit uses explicit paths (T7) |
| **R4: MCP `build_graph` does not catch `TemplateDriftError`** (`server.py:25-28` catches only `RepoRefused`). Pre-existing | More projects can now hit drift over MCP, and it surfaces as a tool error rather than a structured dict | Out of scope: AC-5.2 asks for "the same error legacy files get". Candidate BACKLOG item for the PO, not planned silently → recorded as BACKLOG G7 (review F1, 2026-09-25) |
| **R5: Hidden legacy-path perturbation.** The `_parse_feature`/`_parse_qa` edits change legacy output | Byte-identity lost (NFR-2/AC-5.1) | Only the path choice and the id-column choice change. For every v0.7.0-parsable table without a `spec id` cell, the id column is `"ac"` as before. `Graph.save` is canonical. Existing tests pass unedited. T5(iii) and T8a check it |
| **R6: The steamcore clone is not reproducible** | The evidence can't be re-derived | Record the Core and steamcore SHAs next to the counts (T5 vi, T8) |
| **R7: Inherited A3/A5.** A future Core wants merging, a third name, or a third QA header | Scope creep | One table row or one `_qa_id_column` branch each. Merging stays out (A3) |
| **R8: Per-story QA sub-tables (found during this revision).** 4 of Core's 13 `qa.md` (`graph-gates`, `lean-artifacts`, `project-kickoff`, `tracker-handoff`) split §2 into `### US-n` sub-tables. `_first_table` reads only the first one; this is v0.7.0 behaviour, legacy included. All 13 steamcore `qa.md` use one table | No drift and AC-5.4 still passes, but ACs in later sub-tables show as `unverified` in those Core features. The spec's success signal 1 ("one QACheck per AC row in each table") is not fully met on Core | **Not planned silently: raised as Q1 to the user.** T5(vi) records the gap per feature so the decision rests on numbers. If the user accepts it into scope, it becomes one new task (read every table in the section). This repo's legacy `qa-report.md` has one table, so AC-5.1 is unaffected |

---

## ✅ PLAN GATE

*All boxes checked → `/increment` may start. Any box open → back to `/sprint-plan`.*

- [x] Spec status is `approved` (never plan against a draft): 2026-09-24, including C11/C12
- [x] Architecture decision includes rejected alternatives (eleven: merge, per-feature, notice-in-graph, logging, glob, tuple return, stdout, id-by-file-name, loose id match, Spec-ID-only pin, warn-and-skip)
- [x] Architecture respects the constitution's technical constraints: no constitution. The CLAUDE.md non-negotiables hold (determinism, drift loud, thin adapters, parity, no new dependency)
- [x] Every task maps to a user story: no orphan tasks, no story without tasks
- [x] Every Must AC and every applicable NFR is covered by at least one task (NFR-6 N/A)
- [x] Every task has a checkable definition of done
- [x] Task order respects dependencies: skeleton T1 → T2/T3 → T4 → T5/T6 → go-live T7 → T8
- [x] Test strategy covers every Must story
- [x] Line budget respected: Ist 252 / Soll ~300 (258 lines minus 6 HTML-comment lines)
- [x] Status set to `approved` by the user *(revised plan approved 2026-09-24; Q1 multi-table QA → backlog G6. Revision 2 — T5b, spec C13 — approved by the user's ruling "In v0.7.1 mit beheben", 2026-09-25)*
