"""Repo confinement: refuse a target that doesn't look like a repo.

A **shape check, not a sandbox** (SECURITY.md Non-guarantees #1) — it removes
no privilege the caller did not already have. It exists so "aspark-graph reads
one repository" is behaviour, and so a mistyped path fails in milliseconds
instead of hanging on an unbounded walk.

Enforced once, here, below the CLI/MCP adapters (NFR-7): ``build.build_graph``
and ``queries.load_graph``/``staleness``/``impact_diff`` all call
:func:`ensure_repo` before touching the filesystem further. ``cli.py`` and
``server.py`` only catch :class:`RepoRefused` and render it — no marker
string or constant appears in either adapter.

A resolved directory is accepted iff it holds any of three markers:

- ``.git``, as a file (worktree/submodule) or a directory
- ``.spark/``, as a directory
- ``.aspark-graph/graph.json``, as an **existing regular file** — its
  existence is checked, it is never opened or parsed (NFR-1). This marker is
  narrow, not self-authorising: a fresh, never-built directory has no
  ``graph.json``, so it can only ever admit a directory this tool already
  built from a ``.git``/``.spark``-marked path (A12).

The verdict is computed on the *resolved* path, so a symlink to a marked
directory is accepted (AC-1.6). No OS-level failure to resolve or inspect a
path (missing, not a directory, unreadable) ever escapes as a raw
``FileNotFoundError``/``NotADirectoryError``/``PermissionError`` — it is
folded into :class:`OutsideConfinementError` (AC-1.5).
"""

from __future__ import annotations

from pathlib import Path

GRAPH_DIRNAME = ".aspark-graph"
GRAPH_FILENAME = "graph.json"

# Measured 2026-07-26, macOS (Darwin 22.6.0): sorted(Path.rglob("*")) over 7
# local repos — aSPARK (308 entries), aSPARK-policy (1,205), this repo
# (7,228), ~/.nvm (11,785), lottes.dev (23,688, the largest measured,
# node_modules-heavy) — at ~10,000 entries/s. 200,000 is ~8.4x headroom over
# the largest measured repo: the trade is deliberate — never refuse a real
# repo first, terminate in the tens of seconds second. This is a measurement
# over 7 repos on one machine, one day — not a survey.
MAX_ENTRIES = 200_000

# A judgement call, not a measurement (contrast MAX_ENTRIES above): ~150k
# lines; a source file larger than this is generated or minified, where
# tree-sitter degrades regardless of the bound.
MAX_FILE_BYTES = 5 * 1024 * 1024


class RepoRefused(Exception):
    """A repo root was refused. ``.reason`` is the MCP-rendering reason string."""

    reason = "outside_confinement"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class OutsideConfinementError(RepoRefused):
    """The resolved path holds none of the three markers (AC-1.1/1.2/1.5)."""

    reason = "outside_confinement"


class RepoTooLargeError(RepoRefused):
    """The walk exceeded MAX_ENTRIES before parsing began (AC-3.1)."""

    reason = "too_large"


def ensure_repo(path: str | Path) -> Path:
    """Resolve ``path`` and return it if it looks like a repo; else raise
    :class:`OutsideConfinementError`. Reads no file contents (NFR-1)."""
    try:
        resolved = Path(path).resolve()
    except OSError as exc:
        raise OutsideConfinementError(f"{path}: cannot resolve path ({exc})") from exc

    if _is_marked(resolved):
        return resolved
    raise OutsideConfinementError(
        f"{resolved}: not a repository (no .git, .spark/, or "
        f"{GRAPH_DIRNAME}/{GRAPH_FILENAME} found) — refusing to scan it"
    )


def check_entry_count(count: int, repo_root: str | Path) -> None:
    """Raise :class:`RepoTooLargeError` once a walk has observed more than
    ``MAX_ENTRIES`` entries. The caller stops counting the instant it exceeds
    the bound (AC-3.1) — the message names that count and the limit, not the
    tree's true total, which would require completing the walk this bound
    exists to avoid."""
    if count > MAX_ENTRIES:
        raise RepoTooLargeError(
            f"{repo_root}: more than {MAX_ENTRIES} entries found while walking "
            f"(stopped counting at {count}) — refusing before parsing. "
            f"Limit is a measured, documented bound (see SECURITY.md)."
        )


def _is_marked(resolved: Path) -> bool:
    try:
        git = resolved / ".git"
        if git.is_file() or git.is_dir():
            return True
        if (resolved / ".spark").is_dir():
            return True
        if (resolved / GRAPH_DIRNAME / GRAPH_FILENAME).is_file():
            return True
    except OSError:
        return False
    return False
