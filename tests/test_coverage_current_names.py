"""coverage-current-names: the coverage statement (PR #2) on current-name trails (PR #3).

Coverage names each artifact kind by its legacy spelling, whichever file was
read (spec C2/C4), so current and legacy trails produce the same graph.
"""

import shutil
from pathlib import Path

from aspark_graph.build import build_graph
from aspark_graph.model import feature_id
from aspark_graph.queries import gate_health

CURRENT_REPO = Path(__file__).parent / "fixtures" / "current_names_repo"
FIVE_KINDS = ["plan.md", "qa-report.md", "release-notes.md", "review-report.md", "spec.md"]


def _copy_repo(tmp_path) -> Path:
    dest = tmp_path / "repo"
    shutil.copytree(CURRENT_REPO, dest, ignore=shutil.ignore_patterns(".aspark-graph"))
    return dest


def _coverage(repo: Path) -> dict:
    graph, _ = build_graph(repo)
    return graph.get_node(feature_id("demo"))["coverage"], graph


def test_ac_2_1_full_current_name_trail_is_fully_covered(tmp_path):
    cov, graph = _coverage(_copy_repo(tmp_path))
    assert cov == {"recognized": FIVE_KINDS, "skipped": [], "near_misses": []}
    assert gate_health(graph, "demo")["coverage_note"] is None


def test_ac_1_2_and_2_2_missing_kinds_are_skipped_not_a_crash(tmp_path):
    repo = _copy_repo(tmp_path)
    feature = repo / ".spark" / "demo"
    (feature / "review.md").unlink()
    (feature / "release.md").unlink()
    cov, graph = _coverage(repo)
    assert cov["recognized"] == ["plan.md", "qa-report.md", "spec.md"]
    assert cov["skipped"] == ["release-notes.md", "review-report.md"]
    assert cov["near_misses"] == []
    assert gate_health(graph, "demo")["coverage_note"] == "verdict is over recognized artifacts only"


def test_ac_2_3_shadowed_legacy_file_is_not_a_near_miss(tmp_path):
    repo = _copy_repo(tmp_path)
    feature = repo / ".spark" / "demo"
    shutil.copy(feature / "qa.md", feature / "qa-report.md")
    cov, _ = _coverage(repo)
    assert cov["recognized"] == FIVE_KINDS
    assert cov["near_misses"] == []


def test_ac_2_4_unknown_artifact_like_name_is_still_a_near_miss(tmp_path):
    repo = _copy_repo(tmp_path)
    (repo / ".spark" / "demo" / "reviews.md").write_text("# notes\n")
    cov, _ = _coverage(repo)
    assert cov["near_misses"] == ["reviews.md"]


def test_c4_current_and_legacy_trails_record_the_same_coverage(tmp_path):
    current, _ = _coverage(_copy_repo(tmp_path / "a"))
    repo = _copy_repo(tmp_path / "b")
    feature = repo / ".spark" / "demo"
    for current_name, legacy in (("review.md", "review-report.md"), ("qa.md", "qa-report.md"),
                                 ("release.md", "release-notes.md")):
        (feature / current_name).rename(feature / legacy)
    legacy_cov, _ = _coverage(repo)
    assert current == legacy_cov
