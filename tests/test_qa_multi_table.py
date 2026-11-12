"""qa-multi-table: every table in the QA verification section is read (issue #72)."""
import shutil
from pathlib import Path

import pytest

from aspark_graph import queries
from aspark_graph.artifacts import TemplateDriftError, _first_table, _tables
from aspark_graph.build import build_graph
from aspark_graph.model import NodeType, ac_id

CURRENT_REPO = Path(__file__).parent / "fixtures" / "current_names_repo"

HEAD = "# QA Report: demo\n\n| **Status** | `passed` |\n\n## 2. Acceptance Criteria Verification\n\n"
T1 = "### US-1\n\n| Spec ID | Result |\n|---|---|\n| AC-1.1 | ✅ pass |\n| AC-1.2 | ✅ pass |\n\n"
T2 = "### US-2\n\n| Spec ID | Result |\n|---|---|\n| AC-2.1 | ❌ fail |\n\n"


def _repo(tmp_path, body) -> Path:
    dest = tmp_path / "repo"
    shutil.copytree(CURRENT_REPO, dest, ignore=shutil.ignore_patterns(".aspark-graph"))
    (dest / ".spark" / "demo" / "qa.md").write_text(HEAD + body)
    return dest


def _checks(graph):
    return sorted(graph.nodes(NodeType.QA_CHECK), key=lambda n: n["order"])


def test_tables_yields_every_run_and_none_for_malformed():
    block = ["| a | b |", "|---|---|", "| 1 | 2 |", "", "| x | y |", "| 3 | 4 |", "", "| h |", "|---|", "| v |"]
    tables = list(_tables(block))
    assert [t is None for t in tables] == [False, True, False]
    assert _first_table(["| x | y |", "| 3 | 4 |", "", "| h |", "|---|", "| v |"]) is None


def test_every_table_row_becomes_a_check_with_unique_ordered_ids(tmp_path):
    graph, _ = build_graph(_repo(tmp_path, T1 + T2))
    checks = _checks(graph)
    assert [c["ac"] for c in checks] == ["AC-1.1", "AC-1.2", "AC-2.1"]
    assert [c["order"] for c in checks] == [0, 1, 2]
    assert len({c["id"] for c in checks}) == 3
    for c in checks:
        assert graph.out_edges(c["id"])  # verifies edge to its AC


def test_ac_in_two_tables_keeps_both_checks_in_order(tmp_path):
    t = "### US-3\n\n| Spec ID | Result |\n|---|---|\n| AC-1.1 | ❌ fail |\n\n"
    graph, _ = build_graph(_repo(tmp_path, T1 + t))
    checks = [c for c in _checks(graph) if c["ac"] == "AC-1.1"]
    assert [c["result"] for c in checks] == ["pass", "fail"]


def test_later_table_verdicts_reach_queries(tmp_path):
    first = "### US-1\n\n| Spec ID | Result |\n|---|---|\n| AC-1.1 | ✅ pass |\n\n"
    later = "### More\n\n| Spec ID | Result |\n|---|---|\n| AC-1.2 | ✅ pass |\n| AC-2.1 | ❌ fail |\n\n"
    graph, _ = build_graph(_repo(tmp_path, first + later))
    unverified = {a["id"] for a in queries.gate_health(graph, "demo")["unverified_acs"]}
    assert ac_id("demo", "AC-1.2") not in unverified  # pass read from a later table
    assert ac_id("demo", "AC-2.1") in unverified  # fail verdict, not a pass
    trace = queries.story_trace(graph, "US-2", feature="demo")
    [ac] = [a for a in trace["acceptance_criteria"] if a["ac"] == "AC-2.1"]
    assert ac["latest_result"] == "fail"


def test_malformed_first_run_then_valid_table_produces_checks(tmp_path):
    # R2: a malformed first pipe run no longer hides a valid later table.
    graph, _ = build_graph(_repo(tmp_path, "| Spec ID | Result |\n\n" + T2))
    assert [(c["ac"], c["order"]) for c in _checks(graph)] == [("AC-2.1", 0)]


def test_notes_table_without_id_column_is_skipped(tmp_path):
    notes = "| Item | Note |\n|---|---|\n| a | b |\n\n"
    graph, _ = build_graph(_repo(tmp_path, T1 + notes + T2))
    assert [c["ac"] for c in _checks(graph)] == ["AC-1.1", "AC-1.2", "AC-2.1"]


def test_later_table_with_id_but_no_result_is_drift(tmp_path):
    bad = "| Spec ID | Notes |\n|---|---|\n| AC-2.1 | x |\n"
    with pytest.raises(TemplateDriftError) as exc:
        build_graph(_repo(tmp_path, T1 + bad))
    assert exc.value.file.endswith("qa.md")
    assert "Result" in exc.value.mismatch


def test_first_table_without_result_is_still_drift(tmp_path):
    with pytest.raises(TemplateDriftError):
        build_graph(_repo(tmp_path, "| Spec ID | Notes |\n|---|---|\n| AC-1.1 | x |\n"))


def test_notes_table_with_loose_ac_prefix_header_is_skipped(tmp_path):
    notes = "| Item | Action |\n|---|---|\n| a | b |\n\n"
    graph, _ = build_graph(_repo(tmp_path, T1 + notes + T2))
    assert [c["ac"] for c in _checks(graph)] == ["AC-1.1", "AC-1.2", "AC-2.1"]


def test_later_notes_table_mentioning_an_ac_id_is_not_a_verification_table(tmp_path):
    notes = "| # | Action | Owner |\n|---|---|---|\n| 1 | Re-verify AC-1.2 live | me |\n\n"
    notes2 = "| Action | Result |\n|---|---|\n| Re-ran AC-1.2 | ✅ done |\n\n"
    graph, _ = build_graph(_repo(tmp_path, T1 + notes + notes2 + T2))
    assert [c["ac"] for c in _checks(graph)] == ["AC-1.1", "AC-1.2", "AC-2.1"]
