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


def _feature(root, name, task, story):
    d = root / ".spark" / name
    d.mkdir(parents=True)
    (d / "spec.md").write_text(
        f"# Spec: {name}\n\n| **Status** | `approved` |\n\n## 4. User Stories\n\n"
        f"### {story} (Must): S\n\n- [ ] {story}.1: y.\n"
    )
    (d / "plan.md").write_text(
        f"# Plan: {name}\n\n| **Status** | `approved` |\n\n## 3. Task Breakdown\n\n"
        "| # | Task | Story | Depends on | Status | Definition of Done |\n"
        "|---|---|---|---|---|---|\n"
        f"| {task} | Impl | {story} | – | `done` | x |\n"
    )


def test_f1_cross_feature_id_collision_disambiguated(tmp_path, git_tools):
    """Two features both have a task T1, but map it to DIFFERENT stories. A
    commit `T1 (US-1)` must attribute only to the feature whose T1→US-1 (F1)."""
    root = tmp_path
    git_tools["init"](root)
    # alpha: T1 -> US-1 ; beta: T1 -> US-2 (same task id, different story)
    _feature(root, "alpha", "T1", "US-1")
    _feature(root, "beta", "T1", "US-2")
    git_tools["commit"](root, "docs: trails")
    (root / "shared.py").write_text("def f():\n    return 1\n")
    # Commit names the (T1, US-1) pair -> only alpha's T1 is consistent.
    git_tools["commit"](root, "T1: implement shared (US-1)")

    graph, _ = build_graph(root)
    impl = [(e["source"], e["target"]) for e in graph.edges() if e["type"] == "implements"]
    assert (task_id("alpha", "T1"), file_id("shared.py")) in impl
    assert (task_id("beta", "T1"), file_id("shared.py")) not in impl  # US-2 != US-1

    # And impact reflects only alpha.
    r = queries.impact(graph, ["shared.py"])
    assert {s["id"] for s in r["affected_stories"]} == {story_id("alpha", "US-1")}


def test_t4_inference_is_deterministic(git_backed_repo):
    g1, _ = build_graph(git_backed_repo)
    g2, _ = build_graph(git_backed_repo)
    assert g1.to_dict() == g2.to_dict()
    # And the inferred edge survives a save/load round-trip byte-stably.
    p1 = g1.save(git_backed_repo / "out1" / "graph.json")
    p2 = g2.save(git_backed_repo / "out2" / "graph.json")
    assert p1.read_text() == p2.read_text()
