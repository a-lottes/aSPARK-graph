"""qa.md with one verification table per story: all tables are read (#56)."""
from aspark_graph.artifacts import _parse_qa
from aspark_graph.graph import Graph

QA = """# QA

## Acceptance Criteria Verification

### US-1

| AC | Result |
|----|--------|
| AC-1.1 | ✅ pass |

### US-2

| AC | Result |
|----|--------|
| AC-2.1 | ❌ fail |
| AC-2.2 | ✅ pass |
"""


def test_all_story_tables_read(tmp_path):
    p = tmp_path / "qa.md"
    p.write_text(QA, encoding="utf-8")
    g = Graph()
    assert _parse_qa(p, "feat", g) == 3
    results = sorted(
        (d["ac"], d["result"]) for _, d in g.nx.nodes(data=True) if d.get("ac") and "result" in d
    )
    assert results == [("AC-1.1", "pass"), ("AC-2.1", "fail"), ("AC-2.2", "pass")]
