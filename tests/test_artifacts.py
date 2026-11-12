"""T5: artifact parser + the crown-jewel drift-failure test (AC-1.3)."""

import pytest

from aspark_graph.artifacts import TemplateDriftError, _normalise_result, extract_features
from aspark_graph.graph import Graph
from aspark_graph.model import (
    ac_id,
    feature_id,
    file_id,
    finding_id,
    story_id,
    task_id,
)


# --- parsing the valid fixture trail ---------------------------------------

def test_parses_stories_and_acs(sample_graph):
    graph, _ = sample_graph
    assert graph.has_node(story_id("demo", "US-1"))
    assert graph.get_node(story_id("demo", "US-1"))["moscow"] == "Must"
    assert graph.has_node(ac_id("demo", "AC-1.1"))
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    assert (feature_id("demo"), story_id("demo", "US-1"), "has_story") in edges
    assert (story_id("demo", "US-1"), ac_id("demo", "AC-1.1"), "has_ac") in edges


def test_parses_tasks_and_maps_to(sample_graph):
    graph, _ = sample_graph
    t1 = graph.get_node(task_id("demo", "T1"))
    assert t1["status"] == "done"
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    assert (feature_id("demo"), task_id("demo", "T1"), "has_task") in edges
    assert (task_id("demo", "T1"), story_id("demo", "US-1"), "maps_to") in edges
    # T3 is intentionally orphaned (no story) -> no maps_to edge.
    assert not any(
        e[0] == task_id("demo", "T3") and e[2] == "maps_to" for e in edges
    )


def test_parses_qa_verifies(sample_graph):
    graph, _ = sample_graph
    verifies = [e for e in graph.edges() if e["type"] == "verifies"]
    targets = {e["target"] for e in verifies}
    assert ac_id("demo", "AC-1.1") in targets
    # AC-2.1 QA result is a fail
    qa_nodes = [n for n in graph.nodes() if n["type"] == "QACheck" and n["ac"] == "AC-2.1"]
    assert qa_nodes and qa_nodes[0]["result"] == "fail"


def test_parses_findings_found_in(sample_graph):
    graph, _ = sample_graph
    f1 = graph.get_node(finding_id("demo", "F1"))
    assert f1["severity"] == "Major"
    assert f1["status"] == "open"
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    assert (finding_id("demo", "F1"), file_id("src/demo/app.py"), "found_in") in edges


def test_feature_statuses_stamped(sample_graph):
    graph, _ = sample_graph
    feat = graph.get_node(feature_id("demo"))
    assert feat["spec_status"] == "approved"
    assert feat["qa_status"] == "failed"
    assert feat["version"] == "v0.1.0"


# --- the crown jewel: drift fails loudly, naming file + mismatch (AC-1.3) ---

def test_drift_missing_user_stories_section(tmp_path):
    feature = tmp_path / ".spark" / "broken"
    feature.mkdir(parents=True)
    (feature / "spec.md").write_text("# Spec: broken\n\n| **Status** | draft |\n\n## 1. Problem\n\nNo stories here.\n")
    with pytest.raises(TemplateDriftError) as exc:
        extract_features(tmp_path, Graph())
    assert exc.value.file.endswith("spec.md")
    assert "User Stories" in exc.value.mismatch


def test_drift_malformed_story_heading_names_the_line(tmp_path):
    feature = tmp_path / ".spark" / "broken"
    feature.mkdir(parents=True)
    (feature / "spec.md").write_text(
        "# Spec: broken\n\n| **Status** | draft |\n\n## 4. User Stories\n\n"
        "### US-1 the colon and moscow are missing\n\n- [ ] AC-1.1: x\n"
    )
    with pytest.raises(TemplateDriftError) as exc:
        extract_features(tmp_path, Graph())
    assert exc.value.file.endswith("spec.md")
    assert "US-1" in exc.value.mismatch


def test_drift_plan_missing_status_column(tmp_path):
    feature = tmp_path / ".spark" / "broken"
    feature.mkdir(parents=True)
    (feature / "spec.md").write_text(
        "# Spec: broken\n\n| **Status** | draft |\n\n## 4. User Stories\n\n### US-1 (Must): x\n\n- [ ] AC-1.1: y\n"
    )
    (feature / "plan.md").write_text(
        "# Plan: broken\n\n| **Status** | draft |\n\n## 3. Task Breakdown\n\n"
        "| # | Task | Story | Notes |\n|---|---|---|---|\n| T1 | do it | US-1 | none |\n"
    )
    with pytest.raises(TemplateDriftError) as exc:
        extract_features(tmp_path, Graph())
    assert exc.value.file.endswith("plan.md")
    assert "status" in exc.value.mismatch.lower()


@pytest.mark.parametrize(
    "cell,expected",
    [
        ("✅ pass", "pass"), ("❌ fail", "fail"),
        ("passed", "pass"), ("Failed", "fail"),
        ("PASSES", "pass"), ("failure", "fail"),
        ("in-testing", "unknown"), ("", "unknown"),
    ],
)
def test_f3_qa_result_normalisation_handles_common_phrasing(cell, expected):
    assert _normalise_result(cell) == expected


def test_valid_dogfood_spec_parses_without_drift():
    """The project's own spec.md must parse cleanly (dogfooding)."""
    repo_root = __import__("pathlib").Path(__file__).resolve().parents[1]
    graph = Graph()
    added = extract_features(repo_root, graph)
    assert added > 0
    assert graph.has_node(story_id("aspark-graph", "US-1"))


def test_release_node_and_released_as_edge(tmp_path):
    import subprocess
    from aspark_graph.build import build_graph

    def sh(*a):
        subprocess.run(a, cwd=tmp_path, check=True, capture_output=True)

    sh("git", "init", "-q")
    f = tmp_path / ".spark" / "f"
    f.mkdir(parents=True)
    (f / "release.md").write_text(
        "| **Status** | done |\n| **Version** | `v0.7.1` (hotfix) |\n| **Date** | 2026-01-02 |\n"
    )
    (tmp_path / "a").write_text("x")
    sh("git", "add", ".")
    sh("git", "-c", "user.name=a", "-c", "user.email=a@b", "commit", "-qm", "m")
    g, _ = build_graph(tmp_path)
    assert g.get_node("release:f:v0.7.1").get("commit") is None  # no tag: never guessed
    sh("git", "tag", "v0.7.1")
    g, _ = build_graph(tmp_path)
    n = g.get_node("release:f:v0.7.1")
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True).stdout.strip()
    assert (n["version"], n["status"], n["date"], n["commit"]) == ("v0.7.1", "done", "2026-01-02", sha)
    assert g.get_node("feature:f")["release_status"] == "done"
