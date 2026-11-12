from pathlib import Path

from aspark_graph.artifacts import _parse_qa
from aspark_graph.graph import Graph


def test_per_story_qa_tables_all_read(tmp_path: Path):
    qa = tmp_path / "qa.md"
    qa.write_text(
        "# QA\n\n## Acceptance Criteria Verification\n\n### US-1\n\n"
        "| AC | Result |\n|---|---|\n| AC-1.1 | ✅ pass |\n\n"
        "### US-2\n\n| AC | Result |\n|---|---|\n| AC-2.1 | ❌ fail |\n| AC-2.2 | ✅ pass |\n"
    )
    g = Graph()
    assert _parse_qa(qa, "f", g) == 3
