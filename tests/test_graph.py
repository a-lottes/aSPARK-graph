"""T2: graph core round-trip and byte-stable persistence (seeds AC-1.2)."""

from aspark_graph.graph import Graph
from aspark_graph.model import (
    Confidence,
    EdgeType,
    NodeType,
    ac_id,
    definition_id,
    file_id,
    story_id,
)


def _sample_graph() -> Graph:
    g = Graph()
    f = g.add_node(file_id("src/foo.py"), NodeType.FILE, language="python", hash="abc")
    fn = g.add_node(definition_id("src/foo.py", "bar"), NodeType.FUNCTION, name="bar", line=3)
    s = g.add_node(story_id("feat", "US-1"), NodeType.STORY, title="A story", moscow="Must")
    a = g.add_node(ac_id("feat", "AC-1.1"), NodeType.ACCEPTANCE_CRITERION, text="given/when/then")
    g.add_edge(f, fn, EdgeType.CONTAINS, Confidence.EXTRACTED)
    g.add_edge(s, a, EdgeType.HAS_AC, Confidence.DECLARED)
    return g


def test_add_and_get_node():
    g = _sample_graph()
    node = g.get_node(file_id("src/foo.py"))
    assert node is not None
    assert node["type"] == "File"
    assert node["language"] == "python"
    assert g.get_node("nope") is None


def test_counts_split_layers():
    counts = _sample_graph().counts()
    assert counts["code"] == 2  # File + Function
    assert counts["artifact"] == 2  # Story + AC
    assert counts["edges"] == 2


def test_roundtrip_preserves_nodes_and_edges(tmp_path):
    g = _sample_graph()
    path = g.save(tmp_path / ".aspark-graph" / "graph.json")
    loaded = Graph.load(path)
    assert {n["id"] for n in loaded.nodes()} == {n["id"] for n in g.nodes()}
    assert loaded.edges() == g.edges()


def test_save_is_byte_stable_regardless_of_insertion_order(tmp_path):
    # Build the same logical graph twice, inserting in different orders.
    g1 = _sample_graph()

    g2 = Graph()
    g2.add_node(ac_id("feat", "AC-1.1"), NodeType.ACCEPTANCE_CRITERION, text="given/when/then")
    g2.add_node(story_id("feat", "US-1"), NodeType.STORY, title="A story", moscow="Must")
    g2.add_node(definition_id("src/foo.py", "bar"), NodeType.FUNCTION, name="bar", line=3)
    g2.add_node(file_id("src/foo.py"), NodeType.FILE, language="python", hash="abc")
    g2.add_edge(story_id("feat", "US-1"), ac_id("feat", "AC-1.1"), EdgeType.HAS_AC, Confidence.DECLARED)
    g2.add_edge(file_id("src/foo.py"), definition_id("src/foo.py", "bar"), EdgeType.CONTAINS, Confidence.EXTRACTED)

    p1 = g1.save(tmp_path / "a" / "graph.json")
    p2 = g2.save(tmp_path / "b" / "graph.json")
    assert p1.read_text() == p2.read_text()


def test_confidence_rank_orders_weakest_first():
    assert Confidence.EXTRACTED.rank() < Confidence.DECLARED.rank()
