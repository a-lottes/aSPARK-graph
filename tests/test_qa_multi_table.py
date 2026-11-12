"""qa-multi-table: every verification table under the QA section is read."""

import shutil
from pathlib import Path

import pytest

from aspark_graph import queries
from aspark_graph.artifacts import TemplateDriftError
from aspark_graph.build import build_graph
from aspark_graph.model import ac_id

CURRENT_REPO = Path(__file__).parent / "fixtures" / "current_names_repo"

HEAD = "| Spec ID | Steps performed | Expected | Observed | Result |\n|---|---|---|---|---|\n"
MULTI = (
    "### US-1\n\n" + HEAD
    + "| AC-1.1 | a | b | b | ✅ pass |\n| AC-1.2 | a | b | b | ✅ pass |\n\n"
    "### US-2\n\n" + HEAD + "| AC-2.1 | a | b | c | ❌ fail |\n\n"
    "### Bugs\n\n| Bug | Severity |\n|---|---|\n| B1 | minor |\n"
)


def _repo(tmp_path, section: str) -> Path:
    dest = tmp_path / "repo"
    shutil.copytree(CURRENT_REPO, dest, ignore=shutil.ignore_patterns(".aspark-graph"))
    qa = dest / ".spark" / "demo" / "qa.md"
    text = qa.read_text()
    start = text.index("## 2.")
    end = text.index("## 5.")
    qa.write_text(text[:start] + "## 2. Acceptance Criteria Verification\n\n" + section + "\n" + text[end:])
    return dest


def _checks(graph):
    return sorted(
        (n["order"], n["ac"], n["result"], n["id"]) for n in graph.nodes("QACheck")
    )


def test_every_table_yields_checks_with_continuous_index(tmp_path):
    graph, _ = build_graph(_repo(tmp_path, MULTI))
    checks = _checks(graph)
    assert [(c[1], c[2]) for c in checks] == [("AC-1.1", "pass"), ("AC-1.2", "pass"), ("AC-2.1", "fail")]
    assert [c[0] for c in checks] == [0, 1, 2]
    assert len({c[3] for c in checks}) == 3


def test_later_table_acs_not_unverified(tmp_path):
    graph, _ = build_graph(_repo(tmp_path, MULTI.replace("❌ fail", "✅ pass")))
    assert queries.gate_health(graph, "demo")["unverified_acs"] == []
    trace = queries.story_trace(graph, "US-2", feature="demo")
    ac = next(a for a in trace["acceptance_criteria"] if a["ac"] == "AC-2.1")
    assert ac["latest_result"] == "pass"


def test_first_table_missing_columns_is_drift(tmp_path):
    no_id = "| Step | Result |\n|---|---|\n| x | ✅ pass |\n"
    with pytest.raises(TemplateDriftError):
        build_graph(_repo(tmp_path, no_id))
    no_result = "| Spec ID | Observed |\n|---|---|\n| AC-1.1 | ok |\n"
    with pytest.raises(TemplateDriftError):
        build_graph(_repo(tmp_path / "b", no_result))


def test_later_non_verification_table_is_skipped(tmp_path):
    graph, _ = build_graph(_repo(tmp_path, MULTI))
    assert len(_checks(graph)) == 3  # the bug table adds nothing


def test_skipped_middle_tables_add_nothing_and_keep_index(tmp_path):
    # AC-1.4 second half: a later table lacking only the Result column is skipped too,
    # and skipped tables do not advance the running index (plan §1 decision 5).
    section = (
        HEAD + "| AC-1.1 | a | b | b | ✅ pass |\n\n"
        "| Spec ID | Notes |\n|---|---|\n| AC-1.2 | not a verification row |\n\n"
        "| Bug | Severity |\n|---|---|\n| B1 | minor |\n\n"
        + HEAD + "| AC-2.1 | a | b | b | ✅ pass |\n"
    )
    graph, _ = build_graph(_repo(tmp_path, section))
    assert [(c[0], c[1]) for c in _checks(graph)] == [(0, "AC-1.1"), (1, "AC-2.1")]


def test_same_ac_in_two_tables_latest_wins(tmp_path):
    section = HEAD + "| AC-1.1 | a | b | b | ❌ fail |\n\n" + HEAD + "| AC-1.1 | a | b | b | ✅ pass |\n"
    graph, _ = build_graph(_repo(tmp_path, section))
    assert [(c[0], c[2]) for c in _checks(graph)] == [(0, "fail"), (1, "pass")]
    trace = queries.story_trace(graph, "US-1", feature="demo")
    ac = next(a for a in trace["acceptance_criteria"] if a["ac"] == "AC-1.1")
    assert ac["latest_result"] == "pass"
    assert ac_id("demo", "AC-1.1") in {n["id"] for n in graph.nodes()}


def test_double_build_byte_identical(tmp_path):
    repo = _repo(tmp_path, MULTI)
    g1, _ = build_graph(repo, full=True)
    g2, _ = build_graph(repo, full=True)
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    g1.save(a)
    g2.save(b)
    assert a.read_bytes() == b.read_bytes()
