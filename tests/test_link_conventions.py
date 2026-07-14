"""T10: the documented code→story link conventions (US-5) — AC-5.1..5.3."""

from pathlib import Path

from aspark_graph.build import build_graph
from aspark_graph.model import file_id, task_id

README = Path(__file__).resolve().parents[1] / "README.md"


def _plan_with_files_note(root, dod_note):
    spark = root / ".spark" / "demo"
    spark.mkdir(parents=True)
    (spark / "spec.md").write_text(
        "# Spec: demo\n\n| **Status** | `approved` |\n\n## 4. User Stories\n\n"
        "### US-1 (Must): X\n\n- [ ] AC-1.1: y.\n"
    )
    (spark / "plan.md").write_text(
        "# Plan: demo\n\n| **Status** | `approved` |\n\n## 3. Task Breakdown\n\n"
        "| # | Task | Story | Depends on | Status | Definition of Done |\n"
        "|---|---|---|---|---|---|\n"
        f"| T1 | Impl | US-1 | – | `done` | {dod_note} |\n"
    )
    (root / "real.py").write_text("def f():\n    return 1\n")
    return root


def test_ac_5_2_valid_files_note_is_declared(tmp_path):
    repo = _plan_with_files_note(tmp_path, "does it; files: real.py")
    graph, _ = build_graph(repo)
    edges = [e for e in graph.edges() if e["type"] == "implements"]
    assert len(edges) == 1
    assert edges[0]["source"] == task_id("demo", "T1")
    assert edges[0]["target"] == file_id("real.py")
    assert edges[0]["confidence"] == "declared"


def test_ac_5_3_dangling_files_note_is_safe(tmp_path):
    repo = _plan_with_files_note(tmp_path, "does it; files: nope/missing.py")
    graph, _ = build_graph(repo)  # must not raise
    edges = [e for e in graph.edges() if e["type"] == "implements"]
    assert edges == []  # no fabricated edge to a non-existent file


def test_ac_5_1_readme_documents_both_paths(tmp_path):
    text = README.read_text()
    assert "files:" in text
    assert "Refs:" in text or "commit message" in text.lower()
    assert "declared" in text and "inferred" in text
