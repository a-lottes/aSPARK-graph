"""T7: impact — AC-3.1..AC-3.5 against the fixture trail."""

from aspark_graph import queries
from aspark_graph.model import ac_id, definition_id, story_id


def _confidences(items):
    return {i["id"]: i["confidence"] for i in items}


def test_ac_3_1_lists_code_entities_and_reachable_stories(sample_graph):
    graph, _ = sample_graph
    r = queries.impact(graph, ["src/demo/app.py"])
    assert r["found"] is True
    entry = next(f for f in r["files"] if f["path"] == "src/demo/app.py")
    assert definition_id("src/demo/app.py", "App") in entry["code_entities"]
    story_ids = {s["id"] for s in r["affected_stories"]}
    assert story_id("demo", "US-1") in story_ids
    ac_ids = {a["id"] for a in r["affected_acs"]}
    assert {ac_id("demo", "AC-1.1"), ac_id("demo", "AC-1.2")} <= ac_ids


def test_ac_3_2_declared_link_not_dropped_via_implements(sample_graph):
    graph, _ = sample_graph
    # app.py is directly implemented by T1 (declared) -> US-1 reached at declared.
    r = queries.impact(graph, ["src/demo/app.py"])
    conf = _confidences(r["affected_stories"])
    assert conf[story_id("demo", "US-1")] == "declared"


def test_ac_3_5_weakest_edge_confidence_via_import(sample_graph):
    graph, _ = sample_graph
    # util.py is reached to US-1 only through app.py's `imports` edge (extracted),
    # so the weakest edge on the path is extracted.
    r = queries.impact(graph, ["src/demo/util.py"])
    conf = _confidences(r["affected_stories"])
    assert conf[story_id("demo", "US-1")] == "extracted"


def test_ac_3_3_file_with_no_path_reports_explicitly(sample_graph, tmp_path):
    graph, _ = sample_graph
    # Add a standalone file with no artifact path by building a fresh repo.
    (tmp_path / "lonely.py").write_text("def x():\n    return 1\n")
    from aspark_graph.build import build_graph
    g2, _ = build_graph(tmp_path)
    r = queries.impact(g2, ["lonely.py"])
    entry = next(f for f in r["files"] if f["path"] == "lonely.py")
    assert entry["affected_stories"] == []
    assert entry["affected_acs"] == []
    assert "no affected" in entry["note"]


def test_ac_3_4_unknown_path_named_and_known_files_still_answered(sample_graph):
    graph, _ = sample_graph
    r = queries.impact(graph, ["does/not/exist.py", "src/demo/app.py"])
    assert "does/not/exist.py" in r["unknown_files"]
    # the known file is still answered
    assert any(f["path"] == "src/demo/app.py" for f in r["files"])
    assert any(s["id"] == story_id("demo", "US-1") for s in r["affected_stories"])
