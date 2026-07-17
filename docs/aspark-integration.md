# aspark-graph integration

Drop-in blocks for wiring aspark-graph into an aSPARK project's `/peer-review`
(Reviewer) and `/demo-day` (QA-Tester) gates.

**How to use:** copy the relevant block into your project's `CLAUDE.md`, then
follow the [Setup](#setup) steps. Both blocks use `<placeholders>` — fill in
your project's actual feature name and file paths before use.

See the [aspark-graph README](../README.md) for what the tool does and why.

---

<!-- BEGIN: Reviewer block — copy this section into your CLAUDE.md -->

## Using aspark-graph in /peer-review

**aspark-graph is an accelerant, not a hard dependency.** A gate run with a
missing or stale graph is no weaker than the manual ceremony — the existing
grep/read approach remains fully valid. Do not block the gate on graph
availability.

### Step 0 — confirm the graph is fresh (do this before every run)

```bash
aspark-graph query staleness
```

- If the graph is **absent or stale**: fall back to the ceremony's existing
  grep/read method for this run. State that you did so. The manual fallback
  is valid; proceed without the tools.
- If the graph is **fresh**: proceed with the steps below.

### Step 1 — scope the blast radius of the diff

```bash
aspark-graph query impact <changed files>
```

Or from a git range:

```bash
aspark-graph query impact --diff <range>
```

This tells you which stories and acceptance criteria are in the blast radius —
where to focus the correctness pass. Maps onto the Reviewer's "get the diff"
step in `reviewer.md`.

### Step 2 — trace each Must-story to the code

For each Must-story in scope:

```bash
aspark-graph query story_trace <US-n> --feature <feature>
```

Traces story → ACs → plan tasks → code. Maps onto `reviewer.md`'s "trace each
Must-story AC-n.m to the code that implements it."

### Step 3 — check AC coverage and pass state

```bash
aspark-graph query gate_health <feature>
```

Reports which ACs have code links and QA checks, and their current pass state.

### Interpreting results

- **A graph hit is scoping input, not a verdict.** The graph tells you where to
  look; you still trace and judge the code yourself. Never skip a code read
  because the graph pointed at it — the graph is a map, not a certificate.
- **Confidence tiers in results:** `inferred` < `extracted` < `declared`. An
  `inferred` hit came from git-history inference — treat it as a hint to
  confirm, not an established fact. A `declared` hit rests on an author-written
  link.
- **An empty or `{"found": false}` result means: fall back and confirm
  manually.** An absent result never narrows the review — if the tools return
  nothing, that means the graph does not know, not that there is nothing to
  review. Treat it the same as a stale graph: revert to grep/read.

<!-- END: Reviewer block -->

---

<!-- BEGIN: QA-Tester block — copy this section into your CLAUDE.md -->

## Using aspark-graph in /demo-day

**aspark-graph is an accelerant, not a hard dependency.** A gate run with a
missing or stale graph is no weaker than the manual ceremony — the existing
approach (reading the spec's ACs directly) remains fully valid. Do not block
the gate on graph availability.

### Step 0 — confirm the graph is fresh (do this before every run)

```bash
aspark-graph query staleness
```

- If the graph is **absent or stale**: fall back to reading the feature's spec
  directly for the AC list. State that you did so. The manual fallback is valid;
  proceed without the tools.
- If the graph is **fresh**: proceed with the steps below.

### Step 1 — enumerate ACs and their state

```bash
aspark-graph query story_trace <US-n> --feature <feature>
aspark-graph query gate_health <feature>
```

`story_trace` traces a story → its ACs → plan tasks → code → QA checks.
`gate_health` reports AC coverage and QA pass state across the whole feature.
Use both to scope qa-tester.md's test plan: which ACs exist, which have QA
checks, and whether those checks passed.

### Interpreting results

- **Graph output scopes the test plan; it never replaces performing the steps.**
  An AC is `pass` only after you have observed the actual steps. "The graph
  shows a QA check passed" is not a substitute for seeing it yourself — if you
  didn't see it, it didn't happen.
- **An empty or `{"found": false}` result means: fall back and confirm
  manually.** An absent result never narrows the test plan. Treat it the same
  as a stale graph: read the spec's ACs directly.
- **Confidence tiers:** `inferred` < `extracted` < `declared`. An `inferred`
  result is a hint to investigate, not a confirmed coverage claim.

<!-- END: QA-Tester block -->

---

## Setup

Follow these steps once per target project, in order.

**1. Install aspark-graph and connect the MCP server.**

Follow the README's [Install](../README.md#install) section for the full
prerequisites and installation steps, then the "Add to Claude Code as an MCP
server" step in the same section.

**2. Build the graph in your target project.**

```bash
aspark-graph build .
```

See the README's [Build the graph](../README.md#build-the-graph) section.

**3. Staleness caveat — keep the graph fresh.**

The graph is a rebuildable read model: it can go stale when code or `.spark/`
files change. Run `aspark-graph query staleness` to check whether it still
matches the repo on disk. If it reports drift, rebuild (`aspark-graph build .`)
or rely on the blocks' fallback instructions until you do.
