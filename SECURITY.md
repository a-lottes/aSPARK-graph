# Security

## Trust boundary

aspark-graph's MCP server is a **local stdio child process** of the calling
agent. It runs with the **invoking user's own file permissions** — it has no
account, no elevated access, and no boundary of its own around what it can
read or write on disk. There is **no authentication, no HTTP listener, no
network access, and no remote transport**: the only way to reach it is the
stdio pipe an agent host opens when it launches the process.

The `mcp` SDK dependency is capped at `>=1.12,<1.20`. Versions `1.20+` hard-pull
`cryptography` to support server-side OAuth, a feature this server does not
use and has no code path for. The cap is a **packaging decision** — it keeps
the tool installable on platforms without a `cryptography` wheel — not a
security control, and lifting it is a normal maintenance task, not a
regression of anything stated here.

## What confinement is, and is not

The server refuses to scan or query a target directory unless it holds one of
three markers: a `.git` entry, a `.spark/` directory, or an already-built
`.aspark-graph/graph.json`. This exists so "aspark-graph reads one repository"
is a checkable behaviour instead of an unenforced sentence in the README, and
so a mistyped path fails in milliseconds with a clear message instead of
hanging on an unbounded filesystem walk. Read the *Non-guarantees* section
below before treating this rule as more than that.

## Output is data, not instruction

The graph ingests two kinds of content verbatim: source text (via tree-sitter
extraction) and `.spark/` artifact prose (specs, plans, review findings). Query
results return that content back to the calling agent as plain fields — for
example `find_nodes` returns a node's `title`/`text` attributes exactly as
they were written. Nothing in this pipeline sanitises, filters, or inspects
that text for instructions aimed at the agent consuming it.

**Any content that can reach the repository is a potential prompt-injection
vector**: a spec line, a code comment, a review finding, a commit message. A
calling agent must treat every string a query returns as **data about the
repository**, never as an instruction to act on — regardless of how
authoritative it reads.

## Non-guarantees

This project does not claim, and this document does not imply, any of the
following:

1. **Confinement is a shape check, not a sandbox.** Any directory on the
   machine holding a `.git` entry or a `.spark/` tree passes it — including
   ones the caller should not be pointing this tool at. It is not process
   isolation, a filesystem jail, or a permissions boundary.
2. **Confinement removes no privilege the caller did not already have.** The
   server runs as the invoking user; an agent that can ask it to scan
   `~/.ssh` could read `~/.ssh` directly. The check buys correctness and a
   fast, legible refusal — not access control.
3. **The MCP surface is not read-only.** Eight of the nine tools only read;
   `build_graph` **writes** `<target>/.aspark-graph/graph.json` and
   `parse-cache.json`. A caller relying on "this server never writes" is
   relying on something this document does not state.
4. **Graph output is data, not instruction, and nothing in it is sanitised**
   — see the section above. No escaping, filtering, or injection defence is
   applied to text the graph returns.
5. **There is no auth, no HTTP, no network, and no multi-user or
   multi-tenant model.** One local process, one caller, one filesystem view.
6. **A directory that was confinement-accepted stays queryable even after
   its `.git`/`.spark` marker is later removed** — the graph is a read model
   of a repo that was valid when built, not a live re-check. Separately,
   graphs built by aspark-graph versions at or before v0.5.0 were written
   with **no confinement check of any kind** and remain queryable under this
   version exactly as before; this document's guarantees start at the
   version that introduced them.

## Build limits

Two bounds stop a build from hanging or exhausting memory on an oversized or
cyclic target. They rest on different kinds of evidence and this document
does not present them as equivalent:

- **Entry-count bound — measured.** The walk refuses once it observes more
  than 200,000 filesystem entries (`rglob("*")` results, before the
  build's own skip-directory filter is applied). This number comes from a
  real measurement: `sorted(Path.rglob("*"))` timed over 7 local repositories
  on one machine (macOS, Darwin 22.6.0, 2026-07-26) — the largest,
  a node_modules-heavy JavaScript project, produced 23,688 entries at roughly
  10,000 entries/second. 200,000 is about 8.4× that largest observed count:
  the trade this makes is deliberate — a real repository is never refused
  first, and a pathological target still terminates in the tens of seconds,
  second. This is a measurement over 7 repositories on one day, not a survey,
  and very large monorepos were not part of the sample.
- **Per-file size cap — a judgement call, not a measurement.** A source file
  larger than 5 MB (roughly 150,000 lines) is recorded as an unparsed `File`
  node and its contents are never read into memory. This number was chosen
  because a file past that size is almost always generated or minified code,
  where tree-sitter's output degrades regardless of any bound — it was not
  derived from timing data the way the entry-count bound was.

## Reporting a vulnerability

Report suspected vulnerabilities through **GitHub private security
advisories** on this repository — never a public issue. Use the "Report a
vulnerability" button under the repository's Security tab. You will get an
initial response within **5 working days**.

In scope: anything that makes aspark-graph's actual behaviour diverge from
what this document and the README state — for example, a confinement bypass
reachable from the CLI or MCP surface, a build that hangs past the stated
bounds, or a query result that includes file contents the confinement check
should never have read. The design limitations already described in the
*Non-guarantees* section above — that the confinement check is a shape check
rather than a security boundary, chief among them — are known, and reporting
one of them back to us is not necessary; they are not bugs.
