"""Shared fixtures. The sample_repo trail doubles as a realistic .spark/ fixture."""

import os
import subprocess
from pathlib import Path

import pytest

from aspark_graph.build import build_graph

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_REPO = FIXTURES / "sample_repo"

_FIXED_DATE = "2026-01-01T00:00:00"


@pytest.fixture(autouse=True)
def _tmp_path_is_confined(tmp_path):
    """security-posture US-1: every `tmp_path` marks itself as a repo, so the
    confinement rule in confinement.py stays enforced (no test-only bypass —
    see the plan's R1) rather than the whole suite running through a hole in
    it. An empty `.spark/` is graph-neutral (verified: yields a byte-identical
    graph to none at all — artifacts.extract_features returns 0 for it), so no
    existing test's counts or assertions change. A test that genuinely needs
    an *unmarked* directory builds its own subdirectory under `tmp_path`."""
    (tmp_path / ".spark").mkdir(exist_ok=True)


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
def git_tools():
    """Expose the git fixture helpers to tests that build their own repo."""
    return {"init": init_git_repo, "commit": git_commit}


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


# --- shallow-clone-warning fixtures ---------------------------------------

def make_trail(root, *, with_task=True, tasks=("T1",)):
    """A minimal .spark/ trail: an approved spec with one AC and, unless
    ``with_task`` is False, a plan with ``tasks`` (default one task T1, all
    mapped to US-1; the C5 gate needs >=1 plan Task node)."""
    spark = Path(root) / ".spark" / "demo"
    spark.mkdir(parents=True, exist_ok=True)
    (spark / "spec.md").write_text(
        "# Spec: demo\n\n| **Status** | `approved` |\n\n## 4. User Stories\n\n"
        "### US-1 (Must): Run the app\n\n"
        "**Acceptance criteria:**\n\n"
        "- [ ] AC-1.1: Given the app, when I run it, then it returns a value.\n"
    )
    if with_task:
        (spark / "plan.md").write_text(
            "# Plan: demo\n\n| **Status** | `approved` |\n\n## 3. Task Breakdown\n\n"
            "| # | Task | Story | Depends on | Status | Definition of Done |\n"
            "|---|---|---|---|---|---|\n"
            + "".join(f"| {t} | Implement {t} | US-1 | – | `done` | {t} is done |\n" for t in tasks)
        )


def make_origin(root, *, with_task=True):
    """A >=2-commit repo whose second commit message names T1, so inference
    has history to read (the spec's US-1 fixture source)."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    init_git_repo(root)
    make_trail(root, with_task=with_task)
    git_commit(root, "docs: add spark trail")
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("def run():\n    return 1\n")
    git_commit(root, "T1: implement app (US-1)")
    return root


def shallow_clone(src, dst, *extra):
    """``git clone --depth 1`` via a file:// URI: with a plain path git ignores
    ``--depth`` and silently makes a full clone (plan R4)."""
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", *extra, Path(src).as_uri(), str(dst)],
        check=True, capture_output=True, text=True,
    )
    return Path(dst)


def full_clone(src, dst, *extra):
    subprocess.run(
        ["git", "clone", "-q", *extra, Path(src).as_uri(), str(dst)],
        check=True, capture_output=True, text=True,
    )
    return Path(dst)


def make_boundary_origin(root):
    """Spec US-5 fixture: 5 commits, a non-merge tip naming T1 that touches one
    file. On a full clone inference yields T2->b.py (c3), T2->c.py (c4) and
    T1->a.py (c5). A ``--depth 3`` clone grafts c3, so only c4 and c5 count; a
    ``--depth 1`` clone grafts c5 and yields no inferred edge at all."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    init_git_repo(root)
    make_trail(root, tasks=("T1", "T2"))
    git_commit(root, "docs: add spark trail")                      # c1
    (root / "src").mkdir()
    (root / "src" / "b.py").write_text("B = 1\n")
    git_commit(root, "chore: add b")                               # c2
    (root / "src" / "b.py").write_text("B = 2\n")
    git_commit(root, "T2: change b (US-1)")                        # c3
    (root / "src" / "c.py").write_text("C = 1\n")
    git_commit(root, "T2: add c (US-1)")                           # c4
    (root / "src" / "a.py").write_text("A = 1\n")
    git_commit(root, "T1: add a (US-1)")                           # c5, the tip
    return root
