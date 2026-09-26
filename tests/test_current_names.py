"""current-artifact-names: the file names aSPARK Core writes today (qa.md,
review.md, release.md) and its current QA table header (`Spec ID`) reach the
graph exactly as the legacy names and the `AC` header do."""

import shutil
from pathlib import Path

import pytest

from aspark_graph import queries
from aspark_graph.artifacts import TemplateDriftError, _normalise_result, _split_row
from aspark_graph.build import build_graph
from aspark_graph.model import ac_id, feature_id, file_id, finding_id

CURRENT_REPO = Path(__file__).parent / "fixtures" / "current_names_repo"


def test_walking_skeleton_current_names_reach_the_graph():
    """T1 / AC-1.1, AC-1.2: a current-name trail with the real template header
    builds without drift, and the QA layer answers."""
    graph, _ = build_graph(CURRENT_REPO)

    trace = queries.story_trace(graph, "US-1", feature="demo")
    assert trace["found"] is True
    ac_1_1 = next(a for a in trace["acceptance_criteria"] if a["ac"] == "AC-1.1")
    assert ac_1_1["latest_result"] == "pass"

    assert queries.gate_health(graph, "demo")["unverified_acs"] == []


# --- T2: story coverage against the current-name fixture ---------------------

@pytest.fixture
def current_graph():
    graph, _ = build_graph(CURRENT_REPO)
    return graph


def _copy_repo(tmp_path) -> Path:
    """A writable copy of the fixture, without any build cache."""
    dest = tmp_path / "repo"
    shutil.copytree(CURRENT_REPO, dest, ignore=shutil.ignore_patterns(".aspark-graph"))
    return dest


def test_ac_1_3_failing_qa_row_leaves_ac_unverified(tmp_path):
    repo = _copy_repo(tmp_path)
    qa = repo / ".spark" / "demo" / "qa.md"
    qa.write_text(qa.read_text().replace(
        "| AC-1.1 | call main | a value | a value | ✅ pass |",
        "| AC-1.1 | call main | a value | nothing | ❌ fail |",
    ))
    graph, _ = build_graph(repo)
    unverified = {a["id"] for a in queries.gate_health(graph, "demo")["unverified_acs"]}
    assert ac_id("demo", "AC-1.1") in unverified
    assert ac_id("demo", "AC-1.2") not in unverified


def test_ac_1_4_feature_qa_status_from_qa_md(current_graph):
    assert current_graph.get_node(feature_id("demo"))["qa_status"] == "passed"


def test_ac_2_1_open_findings_from_review_md(current_graph):
    open_ids = [f["id"] for f in queries.gate_health(current_graph, "demo")["open_findings"]]
    assert open_ids == [finding_id("demo", "F1")]


def test_ac_2_2_finding_linked_to_its_file(current_graph):
    edges = {(e["source"], e["target"], e["type"]) for e in current_graph.edges()}
    assert (finding_id("demo", "F1"), file_id("src/demo/app.py"), "found_in") in edges


def test_ac_2_3_feature_review_status_from_review_md(current_graph):
    assert current_graph.get_node(feature_id("demo"))["review_status"] == "passed"


def test_ac_3_1_feature_release_status_from_release_md(current_graph):
    assert current_graph.get_node(feature_id("demo"))["release_status"] == "handed-off"


def test_ac_3_2_release_version_is_the_prose_cell_verbatim(current_graph):
    assert current_graph.get_node(feature_id("demo"))["version"] == "v0.12.0 (proposed, pr mode — no tag)"


def test_qa_nfr_rows_are_skipped(current_graph):
    checked = sorted(n["ac"] for n in current_graph.nodes() if n["type"] == "QACheck")
    assert checked == ["AC-1.1", "AC-1.2", "AC-2.1"]


# --- T3: one source per artifact when both names exist -----------------------

_LEGACY_QA_FAILING = """# QA Report: demo

| | |
|---|---|
| **Status** | `failed` |

## 2. Acceptance Criteria Verification

| AC | Steps performed | Expected | Observed | Result |
|---|---|---|---|---|
| AC-1.1 | call main | a value | nothing | ❌ fail |
"""

_LEGACY_REVIEW_OPEN_F9 = """# Review Report: demo

| | |
|---|---|
| **Status** | `changes-requested` |

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F9 | Major | `src/demo/app.py:2` | stale legacy finding | open |
"""

_LEGACY_RELEASE_PREPARING = """# Release: demo

| | |
|---|---|
| **Status** | `preparing` |
| **Version** | v0.0.1 |
"""


def _graph_bytes(graph, tmp_path, name) -> bytes:
    return graph.save(tmp_path / name / "graph.json").read_bytes()


def test_ac_4_1_current_qa_wins_over_legacy(tmp_path):
    repo = _copy_repo(tmp_path)
    (repo / ".spark" / "demo" / "qa-report.md").write_text(_LEGACY_QA_FAILING)
    graph, _ = build_graph(repo)
    results = {n["result"] for n in graph.nodes() if n["type"] == "QACheck" and n["ac"] == "AC-1.1"}
    assert results == {"pass"}
    unverified = {a["id"] for a in queries.gate_health(graph, "demo")["unverified_acs"]}
    assert ac_id("demo", "AC-1.1") not in unverified


def test_ac_4_2_current_review_and_release_win_over_legacy(tmp_path):
    repo = _copy_repo(tmp_path)
    feature = repo / ".spark" / "demo"
    (feature / "review-report.md").write_text(_LEGACY_REVIEW_OPEN_F9)
    (feature / "release-notes.md").write_text(_LEGACY_RELEASE_PREPARING)
    graph, _ = build_graph(repo)
    assert graph.get_node(finding_id("demo", "F9")) is None
    node = graph.get_node(feature_id("demo"))
    assert node["review_status"] == "passed"
    assert node["release_status"] == "handed-off"
    assert node["version"] == "v0.12.0 (proposed, pr mode — no tag)"


def test_ac_4_3_resolution_is_per_artifact(tmp_path):
    repo = _copy_repo(tmp_path)
    feature = repo / ".spark" / "demo"
    (feature / "review.md").rename(feature / "review-report.md")
    graph, report = build_graph(repo)
    assert any(n["type"] == "QACheck" for n in graph.nodes())
    assert graph.get_node(finding_id("demo", "F1")) is not None
    assert report.shadowed == []


def test_ac_4_6_ignored_legacy_file_leaves_no_trace_in_the_graph(tmp_path):
    only_current = _copy_repo(tmp_path / "a")
    both = _copy_repo(tmp_path / "b")
    feature = both / ".spark" / "demo"
    (feature / "qa-report.md").write_text(_LEGACY_QA_FAILING)
    (feature / "review-report.md").write_text(_LEGACY_REVIEW_OPEN_F9)
    (feature / "release-notes.md").write_text(_LEGACY_RELEASE_PREPARING)
    g_current, _ = build_graph(only_current)
    g_both, report = build_graph(both)
    assert report.shadowed  # the legacy files were seen and ignored
    assert _graph_bytes(g_current, tmp_path, "current") == _graph_bytes(g_both, tmp_path, "both")


def test_nfr_1_shadowed_order_is_fixed_and_repeatable(tmp_path):
    repo = _copy_repo(tmp_path)
    spark = repo / ".spark"
    shutil.copytree(spark / "demo", spark / "alpha")
    for feature in ("demo", "alpha"):
        (spark / feature / "qa-report.md").write_text(_LEGACY_QA_FAILING)
        (spark / feature / "release-notes.md").write_text(_LEGACY_RELEASE_PREPARING)
    (spark / "demo" / "review-report.md").write_text(_LEGACY_REVIEW_OPEN_F9)
    g1, r1 = build_graph(repo)
    g2, r2 = build_graph(repo)
    assert r1.shadowed == [
        ".spark/alpha/qa-report.md",
        ".spark/alpha/release-notes.md",
        ".spark/demo/review-report.md",
        ".spark/demo/qa-report.md",
        ".spark/demo/release-notes.md",
    ]
    assert r2.shadowed == r1.shadowed
    assert _graph_bytes(g1, tmp_path, "run1") == _graph_bytes(g2, tmp_path, "run2")


# --- T5: legacy safety, drift under current names, header independence -------

def test_ac_5_2_qa_md_without_verification_section_is_drift(tmp_path):
    repo = _copy_repo(tmp_path)
    (repo / ".spark" / "demo" / "qa.md").write_text("# QA Report: demo\n\n| **Status** | `passed` |\n\n## 5. Verdict\n\nFine.\n")
    with pytest.raises(TemplateDriftError) as exc:
        build_graph(repo)
    assert exc.value.file.endswith("qa.md")


def test_ac_5_2_review_md_without_findings_section_is_drift(tmp_path):
    repo = _copy_repo(tmp_path)
    (repo / ".spark" / "demo" / "review.md").write_text("# Review Report: demo\n\n| **Status** | `passed` |\n\n## 1. Summary\n\nFine.\n")
    with pytest.raises(TemplateDriftError) as exc:
        build_graph(repo)
    assert exc.value.file.endswith("review.md")


@pytest.mark.parametrize("name", ["qa.md", "qa-report.md"])
def test_qa_table_with_neither_ac_nor_spec_id_is_drift(tmp_path, name):
    repo = _copy_repo(tmp_path)
    feature = repo / ".spark" / "demo"
    (feature / "qa.md").unlink()
    (feature / name).write_text(
        "# QA Report: demo\n\n| **Status** | `passed` |\n\n## 2. Acceptance Criteria Verification\n\n"
        "| ID | Steps performed | Result |\n|---|---|---|\n| AC-1.1 | call main | ✅ pass |\n"
    )
    with pytest.raises(TemplateDriftError) as exc:
        build_graph(repo)
    assert exc.value.file.endswith(name)
    assert "'AC' or 'Spec ID'" in exc.value.mismatch


def test_spec_id_and_ac_headers_build_byte_identical_graphs(tmp_path):
    spec_id = _copy_repo(tmp_path / "spec_id")
    ac = _copy_repo(tmp_path / "ac")
    qa = ac / ".spark" / "demo" / "qa.md"
    qa.write_text(qa.read_text().replace("| Spec ID |", "| AC |"))
    g1, _ = build_graph(spec_id)
    g2, _ = build_graph(ac)
    assert _graph_bytes(g1, tmp_path, "g1") == _graph_bytes(g2, tmp_path, "g2")


def test_spec_id_wins_over_a_column_starting_with_ac(tmp_path):
    repo = _copy_repo(tmp_path)
    (repo / ".spark" / "demo" / "qa.md").write_text(
        "# QA Report: demo\n\n| **Status** | `passed` |\n\n## 2. Acceptance Criteria Verification\n\n"
        "| Spec ID | Actual | Result |\n|---|---|---|\n| AC-1.1 | a value | ✅ pass |\n"
    )
    graph, _ = build_graph(repo)
    assert [n["ac"] for n in graph.nodes() if n["type"] == "QACheck"] == ["AC-1.1"]


def test_ac_5_3_current_and_legacy_names_build_byte_identical_graphs(tmp_path):
    current = _copy_repo(tmp_path / "current")
    legacy = _copy_repo(tmp_path / "legacy")
    feature = legacy / ".spark" / "demo"
    (feature / "qa.md").rename(feature / "qa-report.md")
    (feature / "review.md").rename(feature / "review-report.md")
    (feature / "release.md").rename(feature / "release-notes.md")
    g1, _ = build_graph(current)
    g2, _ = build_graph(legacy)
    assert _graph_bytes(g1, tmp_path, "g1") == _graph_bytes(g2, tmp_path, "g2")


# --- C13: an explicit result marker is the verdict, words only explain it ---

@pytest.mark.parametrize("cell, expected", [
    # the real cells that read as "pass" before (Core, steamcore), verbatim openings
    ("⚠️ not capturable — never claimed as passed, matches plan.md T15's anticipated gap", "unknown"),
    ("⚠️ pass on intent — literal clause `refuted-with-finding` (already ruled: F8, Minor)", "unknown"),
    ("⚠️ first clause pass; constitution clause `refuted-with-finding` — user-ruled D1", "unknown"),
    ("⚠️ pass (structural only) — dynamic trigger not-verified-live, same root cause as AC-5.2", "unknown"),
    ("❌ not-verified-live — negative half independently pass-worthy on its own", "fail"),
    # unchanged cells
    ("✅ pass", "pass"),
    ("pass", "pass"),
    ("PASSED", "pass"),
    ("❌ fail", "fail"),
    ("failed", "fail"),
    ("", "unknown"),
    ("not run", "unknown"),
])
def test_result_marker_decides_before_words(cell, expected):
    assert _normalise_result(cell) == expected


def test_warning_row_that_mentions_passed_leaves_ac_unverified(tmp_path):
    repo = _copy_repo(tmp_path)
    qa = repo / ".spark" / "demo" / "qa.md"
    qa.write_text(qa.read_text().replace(
        "| AC-1.1 | call main | a value | a value | ✅ pass |",
        "| AC-1.1 | call main | a value | n/a | ⚠️ not capturable — never claimed as passed |",
    ))
    graph, _ = build_graph(repo)
    unverified = {a["id"] for a in queries.gate_health(graph, "demo")["unverified_acs"]}
    assert ac_id("demo", "AC-1.1") in unverified
    assert ac_id("demo", "AC-1.2") not in unverified


# --- C14: an escaped pipe in a QA cell belongs to that cell ---

ESCAPED_ROW = "| AC-1.1 | grep for `a\\|b` | none | `x\\|y` returns nothing | ✅ pass |"


def test_c14_escaped_pipe_row_reads_pass_and_verifies_the_ac(tmp_path):
    repo = _copy_repo(tmp_path)
    qa = repo / ".spark" / "demo" / "qa.md"
    qa.write_text(qa.read_text().replace(
        "| AC-1.1 | call main | a value | a value | ✅ pass |", ESCAPED_ROW))
    graph, _ = build_graph(repo)
    [check] = [n for n in graph.nodes() if n["type"] == "QACheck" and n["ac"] == "AC-1.1"]
    assert check["result"] == "pass"
    assert queries.gate_health(graph, "demo")["unverified_acs"] == []


def test_c14_escaped_pipe_before_the_closing_pipe_stays_in_the_cell():
    assert _split_row("| a | b\\||", True) == ["a", "b|"]
    assert _split_row("| a | b ||", True) == _split_row("| a | b ||") == ["a", "b"]


def test_c14_review_tables_keep_the_v070_split(tmp_path):
    # scope guard (C14): only the QA table unescapes; a review cell with "\|" still
    # shifts its columns exactly as in v0.7.0 (AC-5.1; the review fix is BACKLOG G8)
    repo = _copy_repo(tmp_path)
    review = repo / ".spark" / "demo" / "review.md"
    review.write_text(review.read_text().replace(
        "| run() could log its result | open |", "| log a\\|b | open |"))
    graph, _ = build_graph(repo)
    assert graph.get_node(finding_id("demo", "F1"))["status"] == "b"


def test_c14_row_without_escaped_pipes_is_unchanged():
    row = "| AC-1.1 | call main | a value | a value | ✅ pass |"
    assert _split_row(row, True) == _split_row(row) == [
        "AC-1.1", "call main", "a value", "a value", "✅ pass"]


def test_c14_default_split_still_separates_on_every_pipe():
    # scope guard: review/plan tables keep their current splitting (AC-5.1)
    assert _split_row("| a | b\\|c | d |") == ["a", "b\\", "c", "d"]
    assert _split_row("| a | b\\|c | d |", True) == ["a", "b|c", "d"]
