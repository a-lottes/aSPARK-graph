"""`impact --brief` (issue #46): a bounded answer an agent can read in one go.

The full form is the reference; the brief form is a regrouping of the same hits,
so every test here compares against it or against the fixture trail.
"""

import json
import shutil

import pytest

from aspark_graph import cli, queries, server
from aspark_graph.build import build_graph
from aspark_graph.model import ac_id, story_id

FILES = ["src/demo/app.py", "src/demo/util.py"]


@pytest.fixture
def two_features(tmp_path, sample_repo):
    """The sample repo with its trail under two feature names: both reach the same code."""
    root = tmp_path / "repo"
    shutil.copytree(sample_repo, root, ignore=shutil.ignore_patterns(".aspark-graph"))
    shutil.copytree(root / ".spark" / "demo", root / ".spark" / "second")
    (root / ".git").mkdir()
    graph, _ = build_graph(root)
    return graph, root


def _stories(groups):
    return {(g["feature"], s["story"]) for g in groups for s in g["stories"]}


def test_brief_names_the_same_stories_and_acs_as_the_full_form(sample_graph):
    graph, _ = sample_graph
    full = queries.impact(graph, FILES)
    brief = queries.impact(graph, FILES, brief=True)

    assert brief["found"] is True and brief["brief"] is True
    assert brief["truncated"] is False
    assert {story_id(f, s) for f, s in _stories(brief["affected"])} >= {s["id"] for s in full["affected_stories"]}
    acs = {
        ac_id(g["feature"], ac)
        for g in brief["affected"]
        for s in g["stories"]
        for tier in s["acs"].values()
        for ac in tier
    }
    assert acs == {a["id"] for a in full["affected_acs"]}
    assert brief["totals"]["acs"] == len(full["affected_acs"])


def test_brief_has_one_entry_per_story(sample_graph):
    graph, _ = sample_graph
    brief = queries.impact(graph, FILES, brief=True)
    names = [(g["feature"], s["story"]) for g in brief["affected"] for s in g["stories"]]
    assert len(names) == len(set(names))
    assert all(":" not in story for _, story in names)
    assert brief["totals"]["stories"] == len(names)


def test_brief_keeps_confidence_and_says_which_files_reach_a_story(sample_graph):
    graph, _ = sample_graph
    brief = queries.impact(graph, ["src/demo/util.py"], brief=True)
    story = next(s for g in brief["affected"] for s in g["stories"] if s["story"] == "US-1")
    # util.py reaches US-1 only through app.py's import edge (test_impact AC-3.5).
    assert story["confidence"] == "extracted"
    assert story["via"] == ["src/demo/util.py"]
    assert set(story["acs"]) <= {"declared", "extracted", "inferred"}


def test_brief_files_carry_counts_not_lists(sample_graph):
    graph, _ = sample_graph
    full = queries.impact(graph, [*FILES, "does/not/exist.py"])
    brief = queries.impact(graph, [*FILES, "does/not/exist.py"], brief=True)
    assert brief["unknown_files"] == ["does/not/exist.py"]
    for f, b in zip(full["files"], brief["files"], strict=True):
        assert b == {
            "path": f["path"],
            "in_graph": True,
            "code_entities": len(f["code_entities"]),
            "stories": len(f["affected_stories"]),
            "acs": len(f["affected_acs"]),
        }


def test_feature_puts_other_features_first_and_apart(two_features):
    graph, _ = two_features
    brief = queries.impact(graph, FILES, brief=True, feature="demo")
    assert "affected" not in brief
    assert brief["feature"] == "demo"
    assert [g["feature"] for g in brief["other_features"]] == ["second"]
    assert brief["this_feature"] and all("feature" not in s for s in brief["this_feature"])
    assert brief["totals"]["features"] == 2
    # The node-id spelling of a feature is accepted too.
    assert queries.impact(graph, FILES, brief=True, feature="feature:demo") == brief
    # Key order in the answer: the other features come before the own one.
    keys = list(brief)
    assert keys.index("other_features") < keys.index("this_feature")


def test_feature_without_hits_reports_an_empty_own_group(two_features):
    graph, _ = two_features
    brief = queries.impact(graph, FILES, brief=True, feature="not-there")
    assert brief["this_feature"] == []
    assert [g["feature"] for g in brief["other_features"]] == ["demo", "second"]


def test_truncation_is_marked_and_totals_stay_complete(two_features, monkeypatch):
    graph, _ = two_features
    whole = queries.impact(graph, FILES, brief=True)
    monkeypatch.setattr(queries, "BRIEF_MAX_STORIES", 1)
    monkeypatch.setattr(queries, "BRIEF_MAX_ACS", 1)
    monkeypatch.setattr(queries, "BRIEF_MAX_VIA", 1)
    cut = queries.impact(graph, FILES, brief=True)

    assert cut["truncated"] is True
    assert cut["totals"] == whole["totals"]
    shown = [s for g in cut["affected"] for s in g["stories"]]
    assert len(shown) == 1
    assert sum(len(tier) for tier in shown[0]["acs"].values()) == 1
    assert shown[0]["acs_total"] > 1
    assert len(shown[0]["via"]) == 1 and shown[0]["via_total"] == 2


def test_truncation_drops_the_own_feature_before_other_features(two_features, monkeypatch):
    graph, _ = two_features
    monkeypatch.setattr(queries, "BRIEF_MAX_STORIES", 1)
    cut = queries.impact(graph, FILES, brief=True, feature="demo")
    assert cut["truncated"] is True
    assert [g["feature"] for g in cut["other_features"]] == ["second"]
    assert cut["this_feature"] == []


def test_brief_is_deterministic_and_order_independent(two_features):
    graph, _ = two_features
    a = json.dumps(queries.impact(graph, FILES, brief=True, feature="demo"))
    b = json.dumps(queries.impact(graph, list(reversed(FILES)), brief=True, feature="demo"))
    assert a == b


def test_natural_order_of_stories_and_acs():
    assert sorted(["US-10", "US-2", "US-1"], key=queries._natural) == ["US-1", "US-2", "US-10"]
    assert sorted(["AC-1.10", "AC-1.2"], key=queries._natural) == ["AC-1.2", "AC-1.10"]


def test_full_form_is_unchanged_by_the_new_arguments(sample_graph):
    graph, _ = sample_graph
    full = queries.impact(graph, FILES)
    assert set(full) == {"found", "files", "unknown_files", "affected_stories", "affected_acs"}
    # `feature` alone does nothing: it only orders the brief form.
    assert queries.impact(graph, FILES, feature="demo") == full


def test_brief_diff_equals_brief_files(git_backed_repo):
    graph, _ = build_graph(git_backed_repo)
    by_diff = queries.impact_diff(graph, git_backed_repo, "HEAD~1..HEAD", brief=True)
    by_files = queries.impact(graph, ["src/app.py"], brief=True)
    assert by_diff.pop("range") == "HEAD~1..HEAD"
    assert by_diff == by_files


def test_brief_cli_equals_mcp(two_features, capsys):
    graph, root = two_features
    graph.save(queries.default_graph_path(root))
    repo = str(root)
    assert cli.main(["query", "impact", "--repo", repo, "--brief", "--feature", "demo", *FILES]) == 0
    cli_out = json.loads(capsys.readouterr().out)
    mcp_out = server.impact(files=FILES, repo=repo, brief=True, feature="demo")
    assert cli_out == mcp_out
    assert cli_out["brief"] is True
