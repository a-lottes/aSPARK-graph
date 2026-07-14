"""Shared fixtures. The sample_repo trail doubles as a realistic .spark/ fixture."""

import os
import subprocess
from pathlib import Path

import pytest

from aspark_graph.build import build_graph

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_REPO = FIXTURES / "sample_repo"

_FIXED_DATE = "2026-01-01T00:00:00"


@pytest.fixture
def sample_repo() -> Path:
    return SAMPLE_REPO


@pytest.fixture
def sample_graph():
    graph, report = build_graph(SAMPLE_REPO)
    return graph, report


# --- git-backed fixture (for inference / staleness / --diff tests) ---------

def _git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def git_commit(root, message):
    """Commit all changes with a fixed date, so history is reproducible."""
    _git(root, "add", "-A")
    env = {
        "GIT_AUTHOR_DATE": _FIXED_DATE, "GIT_COMMITTER_DATE": _FIXED_DATE,
        "PATH": os.environ["PATH"], "HOME": str(root),
    }
    subprocess.run(
        ["git", "-C", str(root), "commit", "-q", "-m", message],
        check=True, capture_output=True, text=True, env=env,
    )


def init_git_repo(root):
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "Test")
    _git(root, "config", "commit.gpgsign", "false")


@pytest.fixture
def git_backed_repo(tmp_path):
    """A git repo with a .spark trail and an id-referencing commit that links
    code to a task (the realistic history inference reads)."""
    root = tmp_path
    init_git_repo(root)

    spark = root / ".spark" / "demo"
    spark.mkdir(parents=True)
    (spark / "spec.md").write_text(
        "# Spec: demo\n\n| **Status** | `approved` |\n\n## 4. User Stories\n\n"
        "### US-1 (Must): Run the app\n\n"
        "**Acceptance criteria:**\n\n"
        "- [ ] AC-1.1: Given the app, when I run it, then it returns a value.\n"
    )
    (spark / "plan.md").write_text(
        "# Plan: demo\n\n| **Status** | `approved` |\n\n## 3. Task Breakdown\n\n"
        "| # | Task | Story | Depends on | Status | Definition of Done |\n"
        "|---|---|---|---|---|---|\n"
        "| T1 | Implement app | US-1 | – | `done` | app returns a value |\n"
    )
    git_commit(root, "docs: add spark trail")

    src = root / "src"
    src.mkdir()
    (src / "app.py").write_text("def run():\n    return 1\n")
    git_commit(root, "T1: implement app (US-1)")

    return root
