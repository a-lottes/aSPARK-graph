# Plan: gate-integration

| | |
|---|---|
| **Phase** | Plan |
| **Input** | `.spark/gate-integration/spec.md` (status `approved`) |
| **Owner** | Engineering Manager (`/sprint-plan`) |
| **Status** | `approved` |
| **Date** | 2026-07-17 |
| **Target version** | `0.3.1` (patch — docs/prompt-only, no code/API change; spec Q2) |

## 1. Architecture Decision

<!-- Mini-ADR. The EM decides — but shows the alternatives that were rejected and why. -->

- **Context:** The deliverable is **prose/prompt material only** — no product
  code, no change to the tools, the graph model, or dependencies (NFR-5/6/7 all
  N/A). It ships three things: a portable Reviewer drop-in block (US-1/US-2), a
  portable QA-Tester drop-in block (US-3), and honest setup docs (US-4); plus one
  witness copy of the Reviewer block in this repo's own `CLAUDE.md` (US-5). The
  spec's whole falsifiable DoD is "the block names only real tools with correct
  syntax, is portable, and carries the freshness/fallback + setup guidance" (C1,
  A5, Q5) — there is no runtime path to unit-test, so the central engineering
  problem is **how to make a documentation artifact green/red in CI**, not how to
  write the prose. The repo already has the pattern: `tests/test_readme.py` and
  `tests/test_link_conventions.py` parse Markdown and assert honesty facts.

- **Decision:** Ship the portable material as a **single repo-owned file,
  `docs/aspark-integration.md`**, containing two fenced, copy-paste, placeholder-only
  drop-in blocks (Reviewer, then QA-Tester) plus a short setup section that
  **references** the README's existing Install / MCP-add / Build steps rather than
  restating them. Dogfood the **Reviewer** block into this repo's `CLAUDE.md` as a
  live witness (placeholders resolved to this repo's values, per C9), and mark the
  QA half explicitly N/A here (AC-5.3). Make the artifact falsifiable with one new
  test, `tests/test_integration_docs.py`, that **extracts every `aspark-graph`
  invocation from the shipped block(s) and validates each against the live CLI
  surface introspected from `cli.py`** (not a hardcoded list), and asserts the
  required prose elements (staleness pre-check, grep/read fallback, "accelerant not
  a hard dependency", confidence-tier caveat, README-referencing setup, portability,
  the CLAUDE.md witness, QA-absent-here). Version bumps to `0.3.1`.

- **Alternatives considered:**
  | Alternative | Why rejected |
  |---|---|
  | **Put the blocks directly in `README.md`** | The README is the human on-ramp and is already long; drop-in *agent* prompt blocks bloat it, and it creates a circular reference (setup docs are meant to *point at* the README's install steps per AC-4.3/NFR-4, not live inside it). Keeps the shipped agent material separable and independently testable. |
  | **A `docs/integration/` directory with one file per block (`reviewer.md`, `qa-tester.md`, `setup.md`)** | Over-structured for three short sections; more paths to keep coherent and more surface for drift; the single-file layout lets one test target one artifact and keeps the "copy this block" story obvious. YAGNI — split it only if the material outgrows a page. |
  | **Assert doc correctness by re-listing the tools inside the test as a fixed expected set** | A frozen copy of the tool names *in the test* is a second source of truth that silently drifts from `cli.py`. Rejected in favour of **introspecting `cli.py`'s query registry at test time**, so the test fails the moment the block names a subcommand the CLI no longer ships — the check tracks the real surface, matching this repo's CLI≡MCP parity philosophy. |
  | **Manual review only ("a reviewer checks each line")** | The spec explicitly wants each "the block is correct" AC to be a checkable yes/no (C1); leaving NFR-1/AC-1.3/AC-3.4/AC-5.1 to human vigilance is exactly the "grep tax" this product exists to kill. A test makes correctness regression-proof. |

- **Consequences:**
  - *Easier:* Correctness (NFR-1) and portability (NFR-3) become CI-enforced; a
    future tool-surface change that invalidates a documented invocation breaks a
    test instead of silently shipping a lie. One file is trivial to find, copy, and
    review.
  - *Harder:* The test necessarily asserts on some **prose tokens** (e.g. the
    fallback/accelerant phrasing) — a legitimate reword can trip it, so the block
    and test share a small documented vocabulary contract (Risk R1). The prose
    itself is still human-judged for clarity; the test proves it is *correct and
    complete*, not that it is *well-written*.
  - *Accepted ceiling:* No test can prove a real *other* project's gate actually
    called the tools cross-session (A5/Q5) — that stays asserted-not-demonstrated;
    the CLAUDE.md witness (US-5) is the one live adoption proof this cycle carries.

## 2. Affected Components

**New files**
- `docs/aspark-integration.md` — the shipped, repo-owned material: portable
  Reviewer block, portable QA-Tester block, and a setup section that references the
  README. Placeholder-only (NFR-3).
- `tests/test_integration_docs.py` — the falsifiability harness (mirrors
  `tests/test_readme.py` / `tests/test_link_conventions.py`).

**Edited files**
- `CLAUDE.md` — add the Reviewer block as a live witness (US-5), placeholders
  resolved to this repo's values (C9); QA half marked N/A (AC-5.3).
- `README.md` — one pointer line to `docs/aspark-integration.md` for discoverability
  (bidirectional with the setup section's back-reference); no new install prose.
- `pyproject.toml` — version `0.3.0` → `0.3.1` (spec Q2).

**Dependencies:** none added. The test uses only the stdlib (`re`, `pathlib`) plus
an in-process import of `aspark_graph.cli` to introspect the query registry — the
same "import and drive the adapter" approach `tests/test_cli_mcp_parity.py` already
uses. A new package would have to beat "zero lines of new dependency"; it does not.

**Ground-truth CLI surface (verified against `src/aspark_graph/cli.py`)** — the
blocks pin exactly these shapes:
- `aspark-graph query impact <file> [<file> ...]` and `aspark-graph query impact --diff <range>` (mutually exclusive; both-or-neither guarded in the handler)
- `aspark-graph query story_trace <US-n> [--feature <feature>]`
- `aspark-graph query gate_health <feature>`
- `aspark-graph query staleness` (only the shared `--repo`)
- setup: `aspark-graph build <path>`, `aspark-graph serve`
- every `query` subcommand also accepts `--repo` (default `.`)
- MCP tool names (identical answers): `build_graph`, `story_trace`, `impact`, `gate_health`, `staleness`, `get_node`, `find_nodes`, `get_neighbors`, `shortest_path`
- confidence tiers in results: `inferred` < `extracted` < `declared`

## 3. Task Breakdown

<!-- Ordered. Walking skeleton first: the Reviewer block + its falsifiability test
     land and go green before the QA block, per the brief. -->

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | Create `docs/aspark-integration.md` with the portable **Reviewer** drop-in block: one fenced, copy-paste-able block that directs the Reviewer to run `impact <changed files>` / `impact --diff <range>` on the diff, `story_trace <US-n>` per Must-story, and `gate_health <feature>` to scope the correctness pass. Placeholders only. | US-1 | AC-1.1, AC-1.2 | – | `done` | File exists; contains exactly one fenced Reviewer block; the block text names the three tools with the AC-1.2 invocations and maps them to `reviewer.md`'s "trace each Must-story AC" + "get the diff" steps. |
| T2 | Bake **graceful degradation + result-interpretation** into the Reviewer block: a `staleness`/graph-built pre-check *before* trusting any result; an explicit grep/read fallback when the graph is absent/stale; the "accelerant, never a hard dependency — a run with no graph is no weaker than manual" statement; empty/`{"found": false}` framed as "confirm manually, not nothing"; and the "graph hit is scoping input, not a verdict" + confidence-tier (`inferred` < `extracted` < `declared`) caveat. | US-1, US-2 | AC-1.5, AC-2.1, AC-2.2, AC-2.3, AC-2.4, NFR-2 | T1 | `done` | The Reviewer block contains, as identifiable lines: a staleness/build pre-check; a grep/read fallback marked still-valid; the accelerant-not-a-dependency sentence; the empty-result caveat; and the confidence-tier caveat naming `inferred`. |
| T3 | Write `tests/test_integration_docs.py` — the **falsifiability harness** for the shipped block. Extract every `aspark-graph query <name> …` / `aspark-graph <build\|serve>` invocation from the fenced block(s) and assert each `<name>` is a real subcommand (introspected from `cli.py`'s query registry ∪ {`build`,`serve`}) and each long flag exists on that subcommand's argparse parser. Assert portability (no this-repo feature name / `src/aspark_graph` path literals in the shipped block) and the US-2 required-element lines from T2. | US-1, US-2 | AC-1.3, AC-1.4, NFR-1, NFR-2, NFR-3 | T2 | `done` | `uv run pytest tests/test_integration_docs.py` is green; a deliberately-broken invocation (e.g. a fictional `blast_radius` subcommand or a hardcoded `gate-integration` feature name in the shipped block) makes it red; suite still 66+ tests, all green. |
| T4 | Add the portable **QA-Tester** drop-in block to `docs/aspark-integration.md`: a second fenced block directing `/demo-day` to use `story_trace <US-n>` + `gate_health <feature>` to enumerate ACs and their QA/pass state; explicit that graph output *scopes* the test plan but never replaces performing the steps ("if you didn't see it, it didn't happen"); same staleness-check-and-fallback rule as US-2. Extend `test_integration_docs.py` to validate the QA block's tool syntax and required lines. | US-3 | AC-3.1, AC-3.2, AC-3.3, AC-3.4 | T3 | `done` | Second fenced block present; test extends its invocation/portability/fallback assertions over the QA block and stays green; the QA block names only `story_trace`/`gate_health` with correct syntax. |
| T5 | Add the **setup & adoption** section to `docs/aspark-integration.md`: the two ordered prerequisites (MCP server connected, then `aspark-graph build .` first) and the staleness caveat (rebuildable read model; `staleness` reports drift; rebuild or fall back). It **references** the README's Install / "Add to Claude Code as an MCP server" / "Build the graph" sections instead of restating the commands. Add the README pointer line. Extend the test to assert the setup section references the README and does not duplicate the install command block. | US-4 | AC-4.1, AC-4.2, AC-4.3, AC-4.4, NFR-4 | T4 | `done` | Setup section lists the two prerequisites in order + the staleness caveat; it links to the README rather than copying `git clone`/`uv sync`/`claude mcp add`; the test asserts the reference exists and no duplicated install command is present; README has a pointer to the doc. |
| T6 | **Dogfood** the Reviewer block into this repo's `CLAUDE.md` as a live witness: paste the Reviewer block (placeholders resolved to this repo's values per C9), honest that a `/peer-review` here needs a built, fresh graph and otherwise falls back (US-2); mark the QA half explicitly N/A (headless). Extend the test to assert `CLAUDE.md` contains the Reviewer block's tool references (valid against the live surface) **and** contains no active QA-Tester instruction. | US-5 | AC-5.1, AC-5.2, AC-5.3 | T5 | `done` | `CLAUDE.md` contains the Reviewer witness block with correct tool syntax + a graph-freshness/fallback note; the test asserts the block's invocations validate against the CLI surface and that no dead QA instruction is present (absent or explicitly N/A); the portability check for the *shipped* block still targets only `docs/` (not `CLAUDE.md`). |
| T7 | Bump `pyproject.toml` version `0.3.0` → `0.3.1` and record the docs-only change in the release trail (spec Q2). No code, dependency, or graph-behaviour change. | US-4 | Q2 (versioning) | T6 | `done` | `pyproject.toml` reads `version = "0.3.1"`; the change is documented as docs/prompt-only; the determinism/double-build contract (NFR-5) is demonstrably untouched — no code or pinned-dep diff. |

## 4. Test Strategy

There is no runtime product code this cycle, so the honest phrase is not "manual
testing only" — it is **doc-introspection testing**, the same technique the repo
already trusts in `tests/test_readme.py` (README honesty) and
`tests/test_link_conventions.py` (link conventions). Every Must story is covered:

- **US-1 (Reviewer block correctness) & US-3 (QA block correctness) — automated.**
  `tests/test_integration_docs.py` parses the fenced block(s) in
  `docs/aspark-integration.md`, extracts each `aspark-graph query <name> …` and
  `aspark-graph <build|serve>` command, and asserts:
  - `<name>` ∈ the **live** subcommand set introspected from `aspark_graph.cli`'s
    query registry (`_QUERY_NAMES`) ∪ `{build, serve}` — so a fictional or renamed
    tool fails the test (AC-1.3, AC-3.4, NFR-1);
  - each long flag used (`--diff`, `--feature`, `--repo`) exists on that
    subcommand's argparse parser (correct syntax, not just a real name);
  - the shipped block contains **no** this-repo literal (feature name
    `gate-integration`, `src/aspark_graph` paths) — placeholder-only (AC-1.4, NFR-3).
- **US-2 (graceful degradation) — automated on prose contract.** The test asserts
  the Reviewer (and QA) block carries the load-bearing lines: a `staleness`/build
  pre-check, an explicit still-valid grep/read fallback, the "accelerant, not a
  hard dependency" statement, the empty-result "confirm manually" caveat, and the
  `inferred`-confidence caveat (AC-1.5, AC-2.1–2.4, NFR-2). These assert on a small,
  documented vocabulary (see Risk R1), not on freeform wording.
- **US-4 (honest setup) — automated.** The test asserts the setup section
  references the README's install/MCP-add/build steps and does **not** duplicate the
  install command block (AC-4.3, NFR-4), and that the two prerequisites + staleness
  caveat are present (AC-4.1, AC-4.2). AC-4.4 ("followable to a working state with
  no this-repo-only step") is partly structural (the referenced README steps are
  already test-covered by `test_readme.py`) and partly reviewer-judged.
- **US-5 (dogfood witness) — automated.** The test asserts `CLAUDE.md` contains the
  Reviewer block's invocations (valid against the live surface, AC-5.1) and that no
  active QA-Tester instruction is present (AC-5.3). AC-5.2's honesty note is
  reviewer-judged prose backed by the presence check.
- **Left to `/demo-day` in a browser: nothing — N/A with reason.** aspark-graph is
  headless; there is no UI (matches v0.1.0–v0.3.0). The one thing no in-repo test
  can prove — a real *other* project's `/peer-review`/`/demo-day` observably calling
  the tools cross-session — is **asserted-not-demonstrated** by explicit spec
  decision (A5, Q5) and is deliberately **not** faked with a test.
- **Regression guard:** the existing 65 tests stay green (this cycle touches no code
  they cover); NFR-5's byte-identical double-build contract is untouched because no
  code or pinned dependency changes.

## 5. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| **R1 — Prose-token assertions are brittle.** The US-2 required-element checks must match against wording; an innocent reword could break the test, or a shallow keyword match could pass on hollow prose. | Med | Assert on a **small, documented vocabulary contract** (e.g. the literal `staleness`, an "accelerant" / "not a hard dependency" phrase, `inferred`) recorded next to the test; the *strong* checks (tool names/flags) are introspected, not string-matched, so correctness never rests on wording alone. |
| **R2 — Portability check false-positive/negative.** The tool name `aspark-graph` legitimately appears in the shipped block; only a *repo-specific* literal (feature name, source path) is a breach. A naive grep could flag the tool name or miss a real leak. | Med | The portability assertion greps for **specific this-repo literals** (`gate-integration`, `src/aspark_graph/…`), never the tool name; and it targets **only `docs/`**, so the US-5 witness copy in `CLAUDE.md` (which *should* carry concrete values, C9) is exempt by construction. |
| **R3 — Tool surface drifts from the shipped block later.** A future tool rename/removal would leave the block naming a dead command. | Low | The test **introspects `cli.py` at run time** rather than hardcoding the tool list — the block naming a subcommand the CLI no longer ships turns a doc lie into a red test the next time the suite runs. |
| **R4 — Setup docs drift from the README (double source of truth).** Restating install commands would let the two copies diverge. | Med | AC-4.3/NFR-4 mandate **reference, not restate**; the test asserts the setup section links to the README and contains no duplicated install command block. |
| **R5 — The real end-to-end proof is out of reach.** "An agent actually called `impact` during a gate" cannot be shown in this headless repo (A5/Q5). | Low (accepted) | Accepted ceiling, recorded in the spec (Q5). The CLAUDE.md dogfood (US-5) is the single live adoption witness; broader cross-session proof is explicitly deferred, not silently claimed. |
| **R6 — Scope creep toward editing the tool or the plugin cache.** Temptation to "just add a gate mode" or tweak `reviewer.md` in the cache. | Low | Firm Out-of-Scope boundary (spec §6, Q4): repo-owned material only, existing v0.3.0 surface only. Any tool change is a separate spec. |

---

## ✅ PLAN GATE

*All boxes checked → `/increment` may start. Any box open → back to `/sprint-plan`.*

- [x] Spec status is `approved` (never plan against a draft)
- [x] Architecture decision includes rejected alternatives (a decision without alternatives is a guess)
- [x] Architecture respects the constitution's technical constraints (or a conflict is recorded) — *N/A: no `.spark/constitution.md` exists; project non-negotiables (honesty, no code/dep change) are honored*
- [x] Every task maps to a user story — no orphan tasks, no story without tasks
- [x] Every Must AC and every applicable NFR is covered by at least one task *(AC-1.x, AC-2.x, AC-4.x, AC-5.x + AC-3.x; NFR-1..4 mapped; NFR-5/6/7 N/A by spec)*
- [x] Every task has a checkable definition of done
- [x] Task order respects dependencies (walking skeleton: Reviewer block + its test before the QA block)
- [x] Test strategy covers every Must story
- [x] Status set to `approved` by the user *(2026-07-17)*
