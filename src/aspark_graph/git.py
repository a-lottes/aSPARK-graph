"""Offline git access via ``subprocess`` — no new dependency, no network.

Every helper reads only the local object store and **never raises** to its
caller: a missing ``git`` binary, a non-repo directory, a shallow/empty clone,
or a bad range all yield an empty/typed result. This keeps inference a pure
enhancement — its absence degrades the build to v0.1.0 behaviour (AC-1.6),
never a crash.

Determinism (A5/AC-1.5): commands are keyed on repo *state* only. No author or
committer dates are read; commit selection is a pure function of the commit DAG
reachable from ``HEAD`` and the (already-in-graph) task/story ids.
"""

from __future__ import annotations

import re
import subprocess
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


def log_records(root: str | Path) -> list[dict]:
    """Return one record per non-merge commit reachable from ``HEAD``, each
    ``{"message": str, "files": [str, ...]}``.

    Deterministic: no dates are read; the records are a pure function of the
    reachable-from-``HEAD`` commit DAG (git's fixed default order). Returns
    ``[]`` when git is unavailable. This is the primitive inference reads so it
    can attribute *per commit* (message ids AND touched paths together), rather
    than collapsing the commit boundary.
    """
    if not is_git_repo(root):
        return []
    # Format: RS <full message> FS ; then --name-only appends the file list.
    # No hash, no date fields anywhere (determinism).
    fmt = f"{_RS}%B{_FS}"
    code, out = _run(root, ["log", "--no-merges", "--name-only", f"--format={fmt}"])
    if code != 0 or not out:
        return []
    records = []
    for record in out.split(_RS):
        if not record.strip():
            continue
        parts = record.split(_FS)
        if len(parts) < 2:
            continue
        message, files_blob = parts[0], parts[1]
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
