"""T5: story_trace shows real code behind a story (US-2), with graceful absence."""

from aspark_graph import queries
from aspark_graph.build import build_graph
from aspark_graph.model import file_id, story_id, task_id


def test_ac_2_1_story_trace_code_section_nonempty(git_backed_repo):
    graph, _ = build_graph(git_backed_repo)
    r = queries.story_trace(graph, "US-1", feature="demo")
    t1 = next(t for t in r["tasks"] if t["task"] == "T1")
    # v0.1.0 returned an empty code list here; now it is non-empty via inference.
    assert t1["code"]
    assert t1["code"][0]["id"] == file_id("src/app.py")


def test_ac_2_2_inferred_code_link_tagged_distinctly(git_backed_repo):
    graph, _ = build_graph(git_backed_repo)
    r = queries.story_trace(graph, "US-1", feature="demo")
    t1 = next(t for t in r["tasks"] if t["task"] == "T1")
    assert t1["code"][0]["confidence"] == "inferred"


def test_ac_2_3_no_code_link_still_returns_full_declared_trail(sample_graph):
    # sample_repo is not a git repo -> no inference. US-2's task T2 has no files:
    # note, so its code section is empty, but the declared trail is intact.
    graph, _ = sample_graph
    r = queries.story_trace(graph, "US-2", feature="demo")
    assert r["found"] is True
    assert r["acceptance_criteria"]  # declared ACs still present
    t2 = next(t for t in r["tasks"] if t["task"] == "T2")
    assert t2["code"] == []  # empty, not an error


def test_ac_5_2_declared_files_note_still_wins(sample_graph):
    # sample_repo T1 carries a files: note -> declared, not inferred (no regression).
    graph, _ = sample_graph
    r = queries.story_trace(graph, "US-1", feature="demo")
    t1 = next(t for t in r["tasks"] if t["task"] == "T1")
    assert any(c["confidence"] == "declared" for c in t1["code"])
