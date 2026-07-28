"""pypi-publish deviation (2026-07-28): the sdist must never carry untracked
or locally-ignored content (NFR-2/AC-1.5).

hatchling's sdist only reads the committed .gitignore — it is blind to paths
ignored via global git excludes or a repo-local .git/info/exclude (e.g. this
machine's .claude/settings.local.json and .claude/worktrees/, which briefly
rode into a real sdist build before the [tool.hatch.build.targets.sdist]
allowlist in pyproject.toml was added). An allowlist is immune to *any*
future untracked/locally-ignored path by construction, but only if it stays
an allowlist — this test builds a real sdist and asserts the manifest is
exactly what's expected, so a future edit that widens it back to a blanket
include silently regresses this, not just the one path found this cycle.

Marked slow: invokes `uv build` as a subprocess.
"""

import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Top-level entries an sdist tarball may contain (after stripping the
# "aspark_graph-<version>/" prefix every member carries).
_ALLOWED_TOP_LEVEL = {"src", "tests", "README.md", "LICENSE", "pyproject.toml", "PKG-INFO", ".gitignore"}


@pytest.mark.slow
def test_sdist_manifest_carries_no_untracked_or_local_content(tmp_path):
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv not on PATH; run under 'uv run pytest -m slow'")
    out_dir = tmp_path / "dist"
    subprocess.run(
        [uv, "build", "--sdist", "--out-dir", str(out_dir)],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    sdists = list(out_dir.glob("*.tar.gz"))
    assert len(sdists) == 1, f"expected exactly one sdist, found {sdists}"

    with tarfile.open(sdists[0]) as tar:
        names = tar.getnames()

    assert names, "sdist is empty"
    prefix = names[0].split("/")[0] + "/"
    assert all(n.startswith(prefix) for n in names), "sdist has more than one top-level directory"

    top_level = {n[len(prefix):].split("/")[0] for n in names if n != prefix}
    top_level.discard("")
    unexpected = top_level - _ALLOWED_TOP_LEVEL
    assert not unexpected, f"sdist contains unexpected top-level entries: {sorted(unexpected)}"

    # The specific regression this test exists to catch, named explicitly.
    assert not any(".claude" in n for n in names), "sdist leaked .claude/ content"
    assert not any(".spark" in n and "tests/fixtures" not in n for n in names), (
        "sdist leaked the project's own .spark/ trail (tests/fixtures/sample_repo/.spark/ is expected and excluded from this check)"
    )
