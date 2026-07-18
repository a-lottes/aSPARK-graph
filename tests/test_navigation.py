"""T11: general graph navigation — AC-7.1 (lookup/search) and AC-7.2 (paths)."""

from aspark_graph import queries
from aspark_graph.model import ac_id, file_id, story_id, task_id


def test_ac_7_1_find_nodes_by_name_and_type(sample_graph):
    graph, _ = sample_graph
    r = queries.find_nodes(graph, "App")
    ids = {n["id"] for n in r["nodes"]}
    assert file_id("src/demo/app.py") in ids or any("App" in i for i in ids)

    typed = queries.find_nodes(graph, "US-1", type="Story")
    assert typed["count"] == 1
    assert typed["nodes"][0]["id"] == story_id("demo", "US-1")


def test_ac_7_1_get_node_returns_attributes(sample_graph):
    graph, _ = sample_graph
    r = queries.get_node(graph, story_id("demo", "US-1"))
    assert r["found"] is True
    assert r["node"]["moscow"] == "Must"


def test_ac_7_2_connected_nodes_return_ordered_path(sample_graph):
    graph, _ = sample_graph
    r = queries.shortest_path(graph, task_id("demo", "T1"), ac_id("demo", "AC-1.1"))
    assert r["found"] is True
    assert r["nodes"][0] == task_id("demo", "T1")
    assert r["nodes"][-1] == ac_id("demo", "AC-1.1")
    assert all("edge" in s for s in r["steps"])


def test_ac_7_2_unconnected_nodes_return_no_path(sample_graph, tmp_path):
    from aspark_graph.build import build_graph
    (tmp_path / "island.py").write_text("def alone():\n    return 1\n")
    (tmp_path / "other.py").write_text("def separate():\n    return 2\n")
    g, _ = build_graph(tmp_path)
    from aspark_graph.model import definition_id
    r = queries.shortest_path(g, definition_id("island.py", "alone"), definition_id("other.py", "separate"))
    assert r["found"] is False
    assert r["reason"] == "no_path"


def test_shortest_path_missing_node_is_explicit(sample_graph):
    graph, _ = sample_graph
    r = queries.shortest_path(graph, "nope:1", story_id("demo", "US-1"))
    assert r["found"] is False
    assert r["reason"] == "not_found"
    assert r["missing"] == "nope:1"


def test_get_neighbors_depth_and_direction(sample_graph):
    graph, _ = sample_graph
    r = queries.get_neighbors(graph, story_id("demo", "US-1"), edge_types=["has_ac"], depth=1)
    assert r["found"] is True
    neighbor_ids = {n["id"] for n in r["neighbors"]}
    assert ac_id("demo", "AC-1.1") in neighbor_ids
    assert all(n["edge"] == "has_ac" for n in r["neighbors"])


def test_find_nodes_empty_query_returns_empty_result(sample_graph):
    """AC-1.1: find_nodes("") returns count 0 and no nodes, not the whole graph."""
    graph, _ = sample_graph
    r = queries.find_nodes(graph, "")
    assert r == {"query": "", "type": None, "count": 0, "nodes": []}


def test_find_nodes_empty_query_with_type_filter_returns_empty(sample_graph):
    """AC-1.2: type filter does not bypass the empty-query guard."""
    graph, _ = sample_graph
    r = queries.find_nodes(graph, "", type="Story")
    assert r == {"query": "", "type": "Story", "count": 0, "nodes": []}


def test_find_nodes_nonempty_query_unaffected(sample_graph):
    """AC-1.5: non-empty queries are not affected by the empty-query guard."""
    graph, _ = sample_graph
    r = queries.find_nodes(graph, "US-1", type="Story")
    assert r["count"] == 1
    assert r["nodes"][0]["id"] == story_id("demo", "US-1")
