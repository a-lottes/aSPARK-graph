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


def commits_touching(root: str | Path, ids: set[str]) -> dict[str, list[str]]:
    """Map each id in ``ids`` to the sorted list of tracked files touched by a
    commit whose message references that id.

    Deterministic: no dates are read; the file set is a pure function of the
    reachable-from-HEAD commit DAG and the ids. Returns ``{}`` when git is
    unavailable or ``ids`` is empty.
    """
    if not ids or not is_git_repo(root):
        return {}
    # Format: RS <hash> FS <full message> FS  ; then --name-only appends the
    # file list. No date fields anywhere (determinism).
    fmt = f"{_RS}%H{_FS}%B{_FS}"
    code, out = _run(root, ["log", "--no-merges", "--name-only", f"--format={fmt}"])
    if code != 0 or not out:
        return {}

    id_pattern = re.compile(r"\b(" + "|".join(re.escape(i) for i in sorted(ids)) + r")\b")
    result: dict[str, set[str]] = {i: set() for i in ids}
    for record in out.split(_RS):
        if not record.strip():
            continue
        parts = record.split(_FS)
        if len(parts) < 3:
            continue
        message, files_blob = parts[1], parts[2]
        matched = set(id_pattern.findall(message))
        if not matched:
            continue
        files = [line.strip() for line in files_blob.splitlines() if line.strip()]
        for i in matched:
            result[i].update(files)
    return {i: sorted(fs) for i, fs in result.items() if fs}


def diff_files(root: str | Path, diff_range: str) -> tuple[list[str], str | None]:
    """Resolve a git range (e.g. ``HEAD~2..HEAD``) to the tracked files it
    touches. Returns (sorted files, error). On a bad/empty range or missing
    git, returns ([], message)."""
    if not diff_range or not diff_range.strip():
        return [], "empty diff range"
    if not is_git_repo(root):
        return [], "not a git repository"
    code, out = _run(root, ["diff", "--no-color", "--name-only", diff_range])
    if code != 0:
        return [], f"invalid diff range: {diff_range!r}"
    files = sorted({line.strip() for line in out.splitlines() if line.strip()})
    return files, None
