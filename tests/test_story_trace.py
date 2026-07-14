"""T6: story_trace — AC-2.1..AC-2.5 against the fixture trail."""

from aspark_graph import queries
from aspark_graph.model import ac_id, file_id, story_id, task_id


def test_ac_2_1_title_and_all_acs(sample_graph):
    graph, _ = sample_graph
    r = queries.story_trace(graph, "US-1", feature="demo")
    assert r["found"] is True
    assert r["story"]["title"] == "Run the app"
    ac_ids = {a["ac"] for a in r["acceptance_criteria"]}
    assert ac_ids == {"AC-1.1", "AC-1.2"}


def test_ac_2_2_mapped_tasks_with_status(sample_graph):
    graph, _ = sample_graph
    r = queries.story_trace(graph, "US-1", feature="demo")
    tasks = {t["task"]: t["status"] for t in r["tasks"]}
    assert tasks == {"T1": "done"}  # only T1 maps to US-1


def test_ac_2_3_each_ac_carries_latest_qa_result(sample_graph):
    graph, _ = sample_graph
    r = queries.story_trace(graph, "US-2", feature="demo")
    ac21 = next(a for a in r["acceptance_criteria"] if a["ac"] == "AC-2.1")
    assert ac21["latest_result"] == "fail"
    # AC-1.1 passed
    r1 = queries.story_trace(graph, "US-1", feature="demo")
    ac11 = next(a for a in r1["acceptance_criteria"] if a["ac"] == "AC-1.1")
    assert ac11["latest_result"] == "pass"


def test_ac_2_4_explicit_ref_declared_and_absent_ref_is_not_error(sample_graph):
    graph, _ = sample_graph
    r = queries.story_trace(graph, "US-1", feature="demo")
    t1 = next(t for t in r["tasks"] if t["task"] == "T1")
    # T1 has an explicit `files:` note -> a declared implements link to app.py
    assert any(c["id"] == file_id("src/demo/app.py") and c["confidence"] == "declared" for c in t1["code"])

    # US-2's task T2 has no files: note -> no code link, and that is not an error
    r2 = queries.story_trace(graph, "US-2", feature="demo")
    t2 = next(t for t in r2["tasks"] if t["task"] == "T2")
    assert t2["code"] == []
    assert r2["found"] is True


def test_ac_2_5_unknown_story_is_explicit_not_found(sample_graph):
    graph, _ = sample_graph
    r = queries.story_trace(graph, "US-99", feature="demo")
    assert r["found"] is False
    assert r["reason"] == "not_found"
    assert r["story"] == "US-99"


def test_full_node_id_also_resolves(sample_graph):
    graph, _ = sample_graph
    r = queries.story_trace(graph, story_id("demo", "US-1"))
    assert r["found"] is True
    assert r["story"]["story"] == "US-1"
