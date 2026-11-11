# Plan: mcp-drift-result

<!-- aspark-template: aspark/0.1.0 -->

| | |
|---|---|
| **Phase** | Plan |
| **Owner** | Engineering Manager (`/sprint-plan`) |
| **Input** | `.spark/mcp-drift-result/spec.md` (must be `approved`) |
| **Status** | `approved` |
| **Date** | 2026-11-11 |

**Handoff**
- **Status:** mirrors the header table above (authoritative for `Status`).
- **Summary:** Keep commit `0c8d960`'s design: `TemplateDriftError` carries `reason = "template_drift"` in `artifacts.py`, and `server.build_graph` catches it once and renders `{"built", "reason", "file", "message"}`. `cli.py` keeps its existing catch. The open work is proof (tighter MCP tests, a `review.md` case, CLI↔MCP parity, a pre-change round-trip) and docs (README principle, CLAUDE.md, G7).
- **Open:** `none` — all tasks done.
- **Binding ruling:** §3 Task Breakdown for current task status; a plan revision after review/QA findings updates §1/§3 in place, never a new section
- **On conflict:** the numbered body below wins for everything except `Status`; log the mismatch as a finding at the next `/peer-review` and proceed — don't stop on it.

## 1. Architecture Decision

- **Context:** `artifacts.py` raises `TemplateDriftError(file, mismatch)` at 12 sites while `extract_features` runs. In `build.build_graph` that call (`build.py:176`) comes before `parse_cache.save` (`:192`), and both adapters call `Graph.save` only after `build_graph` returns. So a drifted build writes neither `graph.json` nor the parse-cache sidecar, and A2/C4 hold structurally. Before `0c8d960`, `cli.py:170` already caught drift (one stderr line, exit 1). `server.build_graph` caught only `confinement.RepoRefused`, so drift reached the MCP client as a tool error. The constitution (§3 Patterns, §6) and CLAUDE.md ("a new refusal reuses the existing exception→adapter seam") prescribe the shape: raise in the shared module, then catch and render once per adapter. Code at HEAD checked: `artifacts.py:58-69` has `reason`, `server.py:29-31` has the catch, and `cli.py` is unchanged by the commit.
- **Decision:** Keep the committed seam. `TemplateDriftError.reason` is a class attribute, like `RepoRefused.reason`. `server.build_graph` adds one `except artifacts.TemplateDriftError` that returns exactly `built: False`, `reason: exc.reason`, `file: exc.file` and `message: str(exc)`. The library contract (`build.build_graph` raises) and the CLI do not change. The increment adds only tests, a recorded pre-change comparison and docs. No production code changes are planned.
- **Alternatives considered:**
  | Alternative | Why rejected |
  |---|---|
  | Have `build.build_graph` (or a `queries.py` wrapper) catch drift and return a result object | Changes the library contract. `test_current_names.py` and `test_artifacts.py` rely on `build_graph` raising, and so does the CLI's catch. It would also move rendering into the shared module, and the adapter seam exists to avoid exactly that |
  | Catch-all `except Exception` in `server.build_graph` | Disguises real crashes as results. Structured results for other errors (G8 B3) are out of scope (spec §6) |
  | Reuse the refusal shape `{"found": false, …}` | Rejected by spec C1: `found` is wrong for a write. Unifying the shapes is out of scope |
  | A shared `render_drift(exc)` helper in `queries.py`, used by both adapters | The adapters render differently (stderr line vs dict), so the only shared part would be `str(exc)`. A helper adds an indirection with nothing to share. NFR-5 already holds because `reason` comes from the exception |
  | Literal `"template_drift"` in `server.py` | Duplicates the key in the adapter, which violates NFR-5. The `exc.reason` attribute mirrors `RepoRefused` |
- **Consequences:** Easier: the next refusal kind follows the same pattern, and agents can branch on `reason`. Harder: MCP `build_graph` now has three result shapes (success, `found: false`, `built: false`), and clients must check for both failure keys (documented, T8). No new dependency, service or pattern.

## 2. Affected Components

- Production code (done in `0c8d960`, no further edits planned): `src/aspark_graph/artifacts.py` (`TemplateDriftError.reason`) and `src/aspark_graph/server.py` (`build_graph` catch). `src/aspark_graph/cli.py` is read-only for this increment. Its existing catch (`:170`) is the parity reference.
- Tests: `tests/test_mcp_errors.py` (MCP drift cases), `tests/test_cli_mcp_parity.py` (CLI↔MCP drift parity). The existing `tests/test_confinement_cli_mcp.py` and `tests/test_confinement_guards.py` must stay green unedited (AC-2.2, NFR-2).
- Docs: `README.md` (§MCP paragraph done; "Clean errors" principle open), `CLAUDE.md` (trail list, test count), `.spark/BACKLOG.md` (G7).
- Constitution §9 used for module structure (adapters over a shared surface) and test practice. Source was re-read anyway for `server.py`, `artifacts.py`, `cli.py:164-185` and `build.py:103-192`, because the feature touches that area (§9 rule (a)).
- **Blast radius (graph `impact`, rebuilt fresh this session):** for `artifacts.py`, `server.py`, `cli.py` and `tests/test_mcp_errors.py`, `impact` returns declared links into `security-posture` US-1 (AC-1.1-1.13, the refusal seam), `current-artifact-names` US-1/US-4, `coverage-current-names` US-1 and `shallow-clone-warning` US-1 (`build_graph` booleans, AC-2.1's keys). It also returns inferred links into `close-the-loop` US-4, `distributable-install` US-1/2 and `shallow-clone-warning` US-2-4. `README.md` is an unknown file to the graph, so I scoped it by hand. `story_trace security-posture US-1` confirms its refusal tests live in `test_confinement_cli_mcp.py`/`test_cli_mcp_parity.py`. Those are the regressions T6/T10 guard.
- **Trail-name rule (CLAUDE.md v0.7.1):** N/A. This feature does not change which files the tool reads, so later ceremonies use the current names (`review.md`/`qa.md`/`release.md`).

## 3. Task Breakdown

| # | Task | Story | Covers (AC / NFR) | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|---|
| T1 | Shared-module reason and MCP adapter catch (walking skeleton) | US-1, US-4 | AC-1.1, AC-4.1, NFR-5 | – | `done` | `TemplateDriftError.reason == "template_drift"` is a class attribute. `server.build_graph` has exactly one `except artifacts.TemplateDriftError` returning `built`/`reason`/`file`/`message` from the exception (no literal reason). `cli.py` is unchanged by the commit. Verified at HEAD `0c8d960` — files: src/aspark_graph/artifacts.py, src/aspark_graph/server.py |
| T2 | README §MCP paragraph states the drift result shape | US-4 | AC-4.2 | T1 | `done` | README §MCP names `{"built": false, "reason": "template_drift", "file", "message"}`, no write, and the CLI's one line with non-zero exit (README.md:222-227) — files: README.md |
| T3 | Tighten the MCP qa.md drift test to the spec's exact contract. The committed test checks only `endswith`/substring and uses `"old"` as the prior graph | US-1 | AC-1.1, AC-1.2, AC-1.4, NFR-4 | T1 | `done` | One test on a `.git`-marked fixture with a `qa.md` lacking the verification section asserts: (a) `set(data) == {"built","reason","file","message"}`, `built is False`, `reason == "template_drift"`. (b) `message == str(e)` where `e` is the `TemplateDriftError` raised by `build.build_graph` on the same fixture, `file == e.file`, `file in message`. (c) No `graph.json` afterwards when none existed. (d) After a **valid** prior build (build first, then inject the drift), `graph.json` bytes are unchanged. (e) Two calls return equal dicts. `uv run pytest tests/test_mcp_errors.py` green — files: tests/test_mcp_errors.py |
| T4 | MCP drift on `review.md` (findings table missing a required column) | US-1 | AC-1.3 | T3 | `done` | Test: a `review.md` with a `## … Findings` section whose table lacks a required column makes `server.build_graph` return the same four keys, `file.endswith("review.md")`, with the "findings table missing" mismatch in `message`, and no raise — files: tests/test_mcp_errors.py |
| T5 | CLI drift contract and CLI↔MCP parity on the same fixture | US-3 | AC-3.1, NFR-6 | T3 | `done` | Test: `cli.main(["build", repo])` on the T3 fixture returns 1. stdout is `""`. stderr is exactly one non-empty line, equals the MCP result's `message`, and contains its `file`. No `Traceback`. `graph.json` is absent, or byte-identical when one existed before. Same assertions for the T4 `review.md` fixture — files: tests/test_cli_mcp_parity.py |
| T6 | Success and refusal results pinned in-suite | US-2 | AC-2.1, AC-2.2 | T1 | `done` | Test: `server.build_graph` on a valid marked sample-repo copy returns exactly the key set `{code_entities, artifact_entities, inferred_edges, unparsed, ignored_legacy_files, graph_path, shallow_history, no_git_history}`, with no `built`/`reason`. Existing refusal tests in `test_confinement_cli_mcp.py` pass **unedited** (`found: false` shape, AC-2.2) — files: tests/test_mcp_errors.py |
| T7 | Pre-change round-trip (CLAUDE.md "prove against actual pre-change code") | US-2, US-3 | AC-2.1, AC-3.1, NFR-4 | T5, T6 | `done` | A `git worktree` at `dd4b994` (parent of `0c8d960`; the change is already committed, so a worktree replaces `git stash`) and HEAD each build the same fixed targets: a marked copy of `tests/fixtures/sample_repo` and a HEAD-tree export of this repo. Same absolute target path for both, so `graph_path` matches. Result: (i) `graph.json` byte-identical, `cmp` exit 0; (ii) MCP success dicts equal; (iii) CLI on the T3 drift fixture has identical rc/stdout/stderr under both. Commands, SHAs and outputs are recorded in this feature's `review.md` evidence |
| T8 | README "Clean errors" principle states the drift shape and the CLI exit | US-4 | AC-4.2 | T2 | `done` | `## Principles` "Clean errors" bullet names `built`/`reason`/`file`/`message` for MCP `build_graph` drift and the non-zero CLI exit. `tests/test_readme.py`, `tests/test_security_doc.py` and `tests/test_integration_docs.py` green — files: README.md |
| T9 | CLAUDE.md trail entry and BACKLOG G7 note | US-4 | AC-4.3 | T3, T4, T5, T6 | `done` | CLAUDE.md trail list gains `mcp-drift-result/` (one line: MCP drift as a `built: false` result, CLI unchanged) and its `uv run pytest` count matches the new total. The G7 done-note cites `.spark/mcp-drift-result/` and reads "version: set at /go-live". The version itself is filled in at `/go-live` (spec C5) — files: CLAUDE.md, .spark/BACKLOG.md |
| T10 | Full regression gate | US-2 | NFR-1, NFR-2, NFR-4 | T3-T9 | `done` | `uv run pytest` green (319 + new tests). `uv run pytest -m slow` green (NFR-1 bench, transport smoke, sdist manifest, fresh install). `test_confinement_guards.py` unedited and green. `uv run aspark-graph build .` succeeds on this repo, with this trail parsing without drift |

## 4. Test Strategy

- **US-1 (Must):** in-process unit/integration via the directly-callable `server.build_graph` (the existing `test_mcp_errors.py` harness pattern). Two drift fixtures, built as `.git`-marked tmp subdirectories and never through a confinement bypass: `qa.md` without a verification section (T3), and `review.md` with a findings table missing a column (T4). Exact-key, exact-message, no-write and byte-identity assertions. `message` is compared to `str()` of the exception that `build.build_graph` raises on the same fixture, so the test holds without hard-coding text.
- **US-2 (Must):** the success key set is pinned in-suite (T6). Refusal is covered by the existing unedited `test_confinement_cli_mcp.py`. Byte-identity and value-identity against pre-change code come from the T7 worktree round-trip. A double-build alone is not accepted as proof (constitution §4).
- **US-3 (Must):** CLI via `cli.main` plus `capsys` (T5), in the parity file, because the drift parity row belongs with the existing CLI≡MCP assertions. Old vs new CLI output identity comes from T7 (iii).
- **US-4 (Should):** a doc read at `/peer-review`, plus the existing README/SECURITY/integration-doc tests staying green (T8).
- **Transport:** not re-tested for drift. Spec NFR-4's "no MCP tool error" holds by construction because the tool returns a dict, which `test_mcp_transport.py` (slow) already proves serialises. `/demo-day` is N/A (headless); the QA-equivalent happens in `/peer-review` per constitution §8.

## 5. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| R1: The code was committed before spec and plan, so the plan could rubber-stamp it | Gaps hide behind "done" | T1/T2 were marked `done` only after reading HEAD. Every AC gap found (exact keys, valid prior graph, `review.md`, CLI parity, README principle, CLAUDE.md, G7) is an open task |
| R2: The class attribute `reason` on `TemplateDriftError` perturbs graph output (an extractor change, or this repo's own graph) | Byte-identity lost (AC-2.1) | Attributes are not `def:` nodes. T7 proves it on fixed targets against `dd4b994`, not by a double build |
| R3: A partially written `graph.json` or parse cache on drift | Corrupt read model (AC-1.2) | Structurally impossible today (`build.py:176` raises before `:192` and before `Graph.save`). T3(c)(d) pins it, so a future reorder fails a test |
| R4: `file` is an absolute path, so the result shows the machine's layout | Mild leakage, NFR-2 | Same string the CLI already prints (spec A3/C2), so no new content. Output is untrusted data per SECURITY.md |
| R5: Version unknown, so AC-4.3 cannot be fully met before `/go-live` | AC-4.3 stays partially open | T9 writes the trail and the "set at /go-live" note. The release step fills in the version. Recorded, not hidden |
| R6: The G7 note in `0c8d960` is German, while constitution §5 says English | Convention drift | T9 writes the done-note in English and leaves the historical German body untouched (BACKLOG predates the constitution) |
| R7: This plan/trail itself fails to parse (task table columns) | `aspark-graph build .` drifts on its own trail | Template columns kept verbatim. T10 builds this repo |

---

## ✅ PLAN GATE

*All boxes checked → `/increment` may start. Any box open → back to `/sprint-plan`.*

- [x] Spec status is `approved` (never plan against a draft)
- [x] Architecture decision includes rejected alternatives (a decision without alternatives is a guess)
- [x] Architecture respects the constitution's technical constraints (or a conflict is recorded): §3 adapter seam, §4 pre-change proof (T7), §6 drift stays loud; R6 records the BACKLOG language point
- [x] Every task maps to a user story — no orphan tasks, no story without tasks
- [x] Every Must AC and every applicable NFR is covered by at least one task (AC-1.1-1.4, 2.1-2.2, 3.1, 4.1-4.3; NFR-1, 2, 4, 5, 6; NFR-3 N/A)
- [x] Every task has a checkable definition of done
- [x] Task order respects dependencies
- [x] Test strategy covers every Must story
- [x] Line budget respected: Ist ~95 / Soll ~300 (excluding HTML comments)
- [x] Status set to `approved` by the user
