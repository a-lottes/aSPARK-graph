"""Offline git access via ``subprocess`` — no new dependency, no network.

Every helper reads only the local object store and **never raises** to its
caller: a missing ``git`` binary, a non-repo directory, a shallow/empty clone,
or a bad range all yield an empty/typed result (``history_state`` included).
This keeps inference a pure enhancement — its absence degrades the build to
v0.1.0 behaviour (AC-1.6), never a crash.

Determinism (A5/AC-1.5): commands are keyed on repo *state* only. No author or
committer dates are read; commit selection is a pure function of the commit DAG
reachable from ``HEAD`` and the (already-in-graph) task/story ids.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

# Record/field separators unlikely to appear in commit messages or paths.
_RS = "\x1e"
_FS = "\x1f"


def _run(root: str | Path, args: list[str]) -> tuple[int, str]:
    """Run ``git -C <root> <args>``. Returns (returncode, stdout). Never raises."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True, text=True, check=False,
        )
    except (OSError, ValueError):
        return 1, ""  # git binary missing / bad invocation
    return proc.returncode, proc.stdout


def is_git_repo(root: str | Path) -> bool:
    code, out = _run(root, ["rev-parse", "--is-inside-work-tree"])
    return code == 0 and out.strip() == "true"


_SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


@dataclass(frozen=True)
class GitHistory:
    """How much history inference can read, from one ``git rev-parse`` call.

    ``state`` is ``"full"``, ``"shallow"`` or ``"none"`` (see
    :func:`history_state`). ``boundary`` is the set of grafted commits of a
    shallow repo — commits whose parents the clone lacks, so ``git log``
    shows them as adding every file. It is empty when the repo is not
    shallow, and ``None`` when it is shallow but the set cannot be read
    (spec C12: inference then adds no inferred edges at all).
    """

    state: str
    boundary: frozenset[str] | None = frozenset()


def read_history(root: str | Path) -> GitHistory:
    """One local ``git rev-parse`` call, no network, never raises.

    ``--git-path shallow`` names git's own list of grafted commits; it is read
    only when the repo is shallow. ``none`` uses the same test as
    :func:`is_git_repo`, so it holds exactly when inference is skipped. git <
    2.15 echoes ``--is-shallow-repository`` back instead of answering; the
    strict ``== "true"`` comparison then reads ``"full"`` (v0.7.1 behaviour).
    """
    code, out = _run(root, [
        "rev-parse", "--is-inside-work-tree", "--is-shallow-repository",
        "--git-path", "shallow",
    ])
    lines = out.splitlines()
    if code != 0 or not lines or lines[0].strip() != "true":
        return GitHistory("none")
    if len(lines) < 2 or lines[1].strip() != "true":
        return GitHistory("full")
    if len(lines) < 3 or not lines[2].strip():
        return GitHistory("shallow", None)
    try:
        text = (Path(root) / lines[2].strip()).read_text()
    except (OSError, ValueError):
        return GitHistory("shallow", None)
    shas = [line.strip() for line in text.splitlines() if line.strip()]
    if not shas or not all(_SHA_RE.match(sha) for sha in shas):
        return GitHistory("shallow", None)
    return GitHistory("shallow", frozenset(shas))


def history_state(root: str | Path) -> str:
    """``"full"``, ``"shallow"`` or ``"none"`` — :func:`read_history`'s state.

    A subdirectory of a clone, a detached ``HEAD``, a ``--single-branch`` clone
    and a repo with no commits all read ``"full"``.
    """
    return read_history(root).state


def log_records(root: str | Path, *, skip: frozenset[str] = frozenset()) -> list[dict]:
    """Return one record per non-merge commit reachable from ``HEAD``, each
    ``{"message": str, "files": [str, ...]}``.

    Deterministic: no dates are read; the records are a pure function of the
    reachable-from-``HEAD`` commit DAG (git's fixed default order). Returns
    ``[]`` when git is unavailable. This is the primitive inference reads so it
    can attribute *per commit* (message ids AND touched paths together), rather
    than collapsing the commit boundary.

    Commits whose full hash is in ``skip`` are dropped (shallow-clone-warning
    US-5: a shallow clone's grafted boundary commits). The hash is read only to
    filter and never leaves this function, so records keep their shape.
    """
    if not is_git_repo(root):
        return []
    # Format: RS <hash> FS <full message> FS ; then --name-only appends the file
    # list. The hash is content-derived (filter only); no date fields (determinism).
    fmt = f"{_RS}%H{_FS}%B{_FS}"
    code, out = _run(root, ["log", "--no-merges", "--name-only", f"--format={fmt}"])
    if code != 0 or not out:
        return []
    records = []
    for record in out.split(_RS):
        if not record.strip():
            continue
        parts = record.split(_FS)
        if len(parts) < 3:
            continue
        sha, message, files_blob = parts[0].strip(), parts[1], parts[2]
        if sha in skip:
            continue
        files = [line.strip() for line in files_blob.splitlines() if line.strip()]
        records.append({"message": message, "files": files})
    return records


def commits_touching(root: str | Path, ids: set[str]) -> dict[str, list[str]]:
    """Map each id in ``ids`` to the sorted list of tracked files touched by a
    commit whose message references that id. Thin id-only view over
    :func:`log_records` (kept for callers that don't need per-commit context)."""
    if not ids:
        return {}
    id_pattern = re.compile(r"\b(" + "|".join(re.escape(i) for i in sorted(ids)) + r")\b")
    result: dict[str, set[str]] = {i: set() for i in ids}
    for rec in log_records(root):
        matched = set(id_pattern.findall(rec["message"]))
        for i in matched:
            result[i].update(rec["files"])
    return {i: sorted(fs) for i, fs in result.items() if fs}


def diff_files(root: str | Path, diff_range: str) -> tuple[list[str], str | None]:
    """Resolve a git range (e.g. ``HEAD~2..HEAD``) to the tracked files it
    touches. Returns (sorted files, error). On a bad/empty range or missing
    git, returns ([], message)."""
    if not diff_range or not diff_range.strip():
        return [], "empty diff range"
    if not is_git_repo(root):
        return [], "not a git repository"
    # The trailing `--` forces <diff_range> to be parsed as a revision range,
    # so a bare filename is not silently treated as a pathspec (F2) — it fails
    # to resolve and we report it as an invalid range.
    code, out = _run(root, ["diff", "--no-color", "--name-only", diff_range, "--"])
    if code != 0:
        return [], f"invalid diff range: {diff_range!r}"
    files = sorted({line.strip() for line in out.splitlines() if line.strip()})
    return files, None
