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
    with pytest.raises(TemplateDriftError, match="Result"):
        build_graph(_repo(tmp_path, bad))


def test_subtable_without_id_column_is_drift(tmp_path):
    bad = SPLIT + "\n### US-2\n\n| Step | Result |\n|---|---|\n| x | ✅ pass |\n"
    with pytest.raises(TemplateDriftError, match="AC"):
        build_graph(_repo(tmp_path, bad))


def test_tables_outside_the_section_are_not_read(tmp_path):
    repo = _repo(tmp_path, HEAD + "| AC-1.1 | a | b | b | ✅ pass |\n")
    qa = repo / ".spark" / "demo" / "qa.md"
    qa.write_text(qa.read_text() + "\n## 6. Other\n\n| Foo | Bar |\n|---|---|\n| 1 | 2 |\n")
    graph, _ = build_graph(repo)
    assert queries.story_trace(graph, "US-1", feature="demo")["found"]
    assert graph.has_node(ac_id("demo", "AC-1.2"))
    unverified = {a["id"] for a in queries.gate_health(graph, "demo")["unverified_acs"]}
    assert ac_id("demo", "AC-1.2") in unverified


def test_single_table_unchanged_checks(tmp_path):
    g1, _ = build_graph(CURRENT_REPO)
    one = HEAD + "| AC-1.1 | call main | a value | a value | ✅ pass |\n| AC-1.2 | inspect run | uses helper | uses helper | ✅ pass |\n| AC-2.1 | trigger secondary | responds | responds | ✅ pass |\n| NFR-1 | build twice | identical output | identical output | ✅ pass |\n"
    g2, _ = build_graph(_repo(tmp_path, one))
    q = lambda g: sorted(n for n in g.nodes() if str(n).startswith("qacheck"))
    assert q(g1) == q(g2)
