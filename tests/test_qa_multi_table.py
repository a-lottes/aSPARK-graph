"""qa-multi-table (BACKLOG G6): every table of the QA verification section is read."""

import shutil
from pathlib import Path

import pytest

from aspark_graph import queries
from aspark_graph.artifacts import TemplateDriftError
from aspark_graph.build import build_graph
from aspark_graph.model import ac_id

CURRENT_REPO = Path(__file__).parent / "fixtures" / "current_names_repo"
HEAD = "| Spec ID | Steps performed | Expected | Observed | Result |\n|---|---|---|---|---|\n"


def _repo(tmp_path, section: str) -> Path:
    dest = tmp_path / "repo"
    shutil.copytree(CURRENT_REPO, dest, ignore=shutil.ignore_patterns(".aspark-graph"))
    qa = dest / ".spark" / "demo" / "qa.md"
    text = qa.read_text()
    start = text.index("## 2.")
    end = text.index("## 5.")
    qa.write_text(text[:start] + "## 2. Acceptance Criteria Verification\n\n" + section + "\n" + text[end:])
    return dest


SPLIT = (
    "### US-1\n\n" + HEAD + "| AC-1.1 | a | b | b | ✅ pass |\n\n"
    "### US-1 more\n\n" + HEAD + "| AC-1.2 | a | b | b | ✅ pass |\n| AC-2.1 | a | b | b | ✅ pass |\n"
)


def test_every_subtable_is_read(tmp_path):
    graph, _ = build_graph(_repo(tmp_path, SPLIT))
    assert queries.gate_health(graph, "demo")["unverified_acs"] == []
    trace = queries.story_trace(graph, "US-1", feature="demo")
    assert {a["ac"]: a["latest_result"] for a in trace["acceptance_criteria"]} == {
        "AC-1.1": "pass", "AC-1.2": "pass"}


def test_subtable_without_result_column_is_drift(tmp_path):
    bad = SPLIT + "\n### US-2\n\n| Spec ID | Notes |\n|---|---|\n| AC-2.1 | x |\n"
    with pytest.raises(TemplateDriftError, match="Result") as exc:
        build_graph(_repo(tmp_path, bad))
    assert exc.value.file.endswith(".spark/demo/qa.md")


def test_subtable_without_id_column_is_drift(tmp_path):
    bad = SPLIT + "\n### US-2\n\n| Step | Result |\n|---|---|\n| x | ✅ pass |\n"
    with pytest.raises(TemplateDriftError, match="AC") as exc:
        build_graph(_repo(tmp_path, bad))
    assert exc.value.file.endswith(".spark/demo/qa.md")


def test_tables_outside_the_section_are_not_read(tmp_path):
    repo = _repo(tmp_path, HEAD + "| AC-1.1 | a | b | b | ✅ pass |\n")
    qa = repo / ".spark" / "demo" / "qa.md"
    # AC-shaped on purpose: if this table were read, AC-1.2 would turn verified.
    qa.write_text(qa.read_text() + "\n## 6. Other\n\n| Spec ID | Result |\n|---|---|\n| AC-1.2 | ✅ pass |\n")
    graph, _ = build_graph(repo)
    assert queries.story_trace(graph, "US-1", feature="demo")["found"]
    assert graph.has_node(ac_id("demo", "AC-1.2"))
    unverified = {a["id"] for a in queries.gate_health(graph, "demo")["unverified_acs"]}
    assert ac_id("demo", "AC-1.2") in unverified


def test_single_table_unchanged_checks(tmp_path):
    g1, _ = build_graph(CURRENT_REPO)
    one = HEAD + "| AC-1.1 | call main | a value | a value | ✅ pass |\n| AC-1.2 | inspect run | uses helper | uses helper | ✅ pass |\n| AC-2.1 | trigger secondary | responds | responds | ✅ pass |\n| NFR-1 | build twice | identical output | identical output | ✅ pass |\n"
    g2, _ = build_graph(_repo(tmp_path, one))
    q = lambda g: sorted(n["id"] for n in g.nodes() if n["id"].startswith("qa:"))
    assert q(g1) == q(g2)


def test_running_index_keeps_same_ac_in_two_tables_distinct(tmp_path):
    """NFR-2: the same AC in row 0 of two tables gets two ids; the later result wins."""
    two = (
        "### a\n\n" + HEAD + "| AC-1.1 | a | b | b | ❌ fail |\n\n"
        "### b\n\n" + HEAD + "| AC-1.1 | a | b | b | ✅ pass |\n"
    )
    graph, _ = build_graph(_repo(tmp_path, two))
    checks = sorted(n["id"] for n in graph.nodes() if n["id"].startswith("qa:demo:AC-1.1#"))
    assert len(checks) == 2
    trace = queries.story_trace(graph, "US-1", feature="demo")
    ac = next(a for a in trace["acceptance_criteria"] if a["ac"] == "AC-1.1")
    assert ac["latest_result"] == "pass"


def test_row_index_advances_on_non_ac_rows(tmp_path):
    """NFR-2: non-AC rows (e.g. NFR-1) still consume an index, as in the old single-table code."""
    t = (
        "### a\n\n" + HEAD + "| NFR-1 | a | b | b | ✅ pass |\n\n"
        "### b\n\n" + HEAD + "| AC-1.1 | a | b | b | ✅ pass |\n"
    )
    graph, _ = build_graph(_repo(tmp_path, t))
    ids = [n["id"] for n in graph.nodes() if n["id"].startswith("qa:demo:AC-1.1#")]
    assert ids == ["qa:demo:AC-1.1#1"]
