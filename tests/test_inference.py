"""T3/T4: git-history inference of implements edges (US-1, the core problem)."""

from aspark_graph import queries
from aspark_graph.build import build_graph
from aspark_graph.model import ac_id, file_id, story_id, task_id


def test_t3_inference_creates_implements_edge_and_nonempty_impact(git_backed_repo):
    graph, report = build_graph(git_backed_repo)
    # An inferred implements edge exists (0 in v0.1.0).
    implements = [e for e in graph.edges() if e["type"] == "implements"]
    assert len(implements) >= 1
    assert report.inferred_edges >= 1
    edge = next(e for e in implements if e["target"] == file_id("src/app.py"))
    assert edge["source"] == task_id("demo", "T1")
    assert edge["confidence"] == "inferred"

    # impact on the real file is now NON-EMPTY (the query empty in v0.1.0).
    r = queries.impact(graph, ["src/app.py"])
    story_ids = {s["id"] for s in r["affected_stories"]}
    assert story_id("demo", "US-1") in story_ids
    ac_ids = {a["id"] for a in r["affected_acs"]}
    assert ac_id("demo", "AC-1.1") in ac_ids


def test_t3_impact_confidence_is_inferred(git_backed_repo):
    graph, _ = build_graph(git_backed_repo)
    r = queries.impact(graph, ["src/app.py"])
    conf = {s["id"]: s["confidence"] for s in r["affected_stories"]}
    # The only path runs through the inferred implements edge -> weakest tier.
    assert conf[story_id("demo", "US-1")] == "inferred"


def test_t3_non_git_repo_yields_zero_inferred(tmp_path):
    # Same content, but no git history -> no inference, build still succeeds (AC-1.6).
    (tmp_path / ".spark" / "demo").mkdir(parents=True)
    (tmp_path / ".spark" / "demo" / "spec.md").write_text(
        "# Spec: demo\n\n| **Status** | `approved` |\n\n## 4. User Stories\n\n"
        "### US-1 (Must): X\n\n- [ ] AC-1.1: y.\n"
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("def run():\n    return 1\n")
    graph, report = build_graph(tmp_path)
    assert report.inferred_edges == 0
    assert [e for e in graph.edges() if e["type"] == "implements"] == []
    # impact still answers cleanly (empty, not a crash).
    r = queries.impact(graph, ["src/app.py"])
    entry = next(f for f in r["files"] if f["path"] == "src/app.py")
    assert entry["affected_stories"] == []


def test_t4_inference_is_deterministic(git_backed_repo):
    g1, _ = build_graph(git_backed_repo)
    g2, _ = build_graph(git_backed_repo)
    assert g1.to_dict() == g2.to_dict()
    # And the inferred edge survives a save/load round-trip byte-stably.
    p1 = g1.save(git_backed_repo / "out1" / "graph.json")
    p2 = g2.save(git_backed_repo / "out2" / "graph.json")
    assert p1.read_text() == p2.read_text()
