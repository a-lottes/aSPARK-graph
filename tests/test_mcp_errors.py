"""F3: MCP query tools return a clean 'build first' dict, never a raw error.

Parity with the CLI's AC-5.2 behaviour (which prints a clean message and exits
1) — the MCP client must not receive a raised GraphNotBuiltError.
"""

import shutil
from pathlib import Path

from aspark_graph import server

SAMPLE_REPO = Path(__file__).parent / "fixtures" / "sample_repo"


def _call(tool, params):
    # @mcp.tool() leaves the function directly callable; it returns the same
    # dict the MCP surface serialises (a clean 'build first' dict on error).
    return getattr(server, tool)(**params)


def test_query_before_build_returns_clean_error(tmp_path):
    # No graph built in tmp_path.
    for tool, params in [
        ("get_node", {"id": "file:x.py", "repo": str(tmp_path)}),
        ("story_trace", {"story": "US-1", "repo": str(tmp_path)}),
        ("impact", {"files": ["x.py"], "repo": str(tmp_path)}),
        ("staleness", {"repo": str(tmp_path)}),
        ("gate_health", {"feature": "demo", "repo": str(tmp_path)}),
    ]:
        data = _call(tool, params)
        assert data["found"] is False
        assert "build" in data["error"].lower()


# --- template drift (issue #42 / BACKLOG G7) --------------------------------

import pytest

from aspark_graph import artifacts, build

DRIFT_KEYS = {"built", "reason", "file", "message"}
SUCCESS_KEYS = {
    "code_entities", "artifact_entities", "inferred_edges", "unparsed",
    "ignored_legacy_files", "graph_path", "shallow_history", "no_git_history",
}


def _drift_repo(tmp_path, name, body):
    repo = tmp_path / "r"
    feat = repo / ".spark" / "demo"
    feat.mkdir(parents=True)
    (repo / ".git").mkdir()
    (feat / name).write_text(body)
    return repo


QA_DRIFT = ("qa.md", "# QA\n\nno verification section\n")
REVIEW_DRIFT = (
    "review.md",
    "# Review\n\n## 3. Findings\n\n| # | Note |\n|---|---|\n| F1 | x |\n",
)


@pytest.mark.parametrize("name,body", [QA_DRIFT, REVIEW_DRIFT], ids=["qa", "review"])
def test_build_graph_template_drift_returns_structured_result(tmp_path, name, body):
    repo = _drift_repo(tmp_path, name, body)
    with pytest.raises(artifacts.TemplateDriftError) as caught:
        build.build_graph(str(repo))
    exc = caught.value
    gpath = repo / ".aspark-graph" / "graph.json"

    data = server.build_graph(str(repo))
    assert set(data) == DRIFT_KEYS
    assert data["built"] is False
    assert data["reason"] == "template_drift"
    assert data["file"] == exc.file and data["file"].endswith(name)
    assert data["message"] == str(exc) and data["file"] in data["message"]
    assert not gpath.exists()

    # A prior (real) graph stays byte-identical across a failed build.
    clean = tmp_path / "clean"
    shutil.copytree(repo, clean)
    (clean / ".spark" / "demo" / name).unlink()
    good = server.build_graph(str(clean))
    assert "graph_path" in good
    shutil.copytree(clean / ".aspark-graph", repo / ".aspark-graph")
    before = gpath.read_bytes()
    assert server.build_graph(str(repo)) == data
    assert gpath.read_bytes() == before


def test_build_graph_success_keys_unchanged(tmp_path):
    repo = tmp_path / "s"
    shutil.copytree(SAMPLE_REPO, repo)
    (repo / ".git").mkdir(exist_ok=True)
    data = server.build_graph(str(repo))
    assert set(data) == SUCCESS_KEYS
