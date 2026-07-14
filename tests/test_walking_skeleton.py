"""T3: the walking skeleton — Python extraction, build, get_node, CLI and MCP.

The MCP path is exercised via FastMCP's in-memory client, which performs the
real protocol handshake and tool dispatch. The live-Claude-Code check is a
/demo-day item (see the plan's test strategy).
"""

import asyncio
import json

import pytest

from aspark_graph.build import build_graph
from aspark_graph.extractors import code_py
from aspark_graph.model import definition_id, file_id
from aspark_graph import cli, queries


def _write_repo(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "mod.py").write_text(
        "def top():\n    return 1\n\n"
        "class C:\n    def m(self):\n        return top()\n"
    )
    (tmp_path / "pkg" / "user.py").write_text(
        "from pkg.mod import C\n\n"
        "def use():\n    return C()\n"
    )
    return tmp_path


# --- extractor unit test ---------------------------------------------------

def test_python_extractor_finds_defs_and_imports():
    source = b"import os\nfrom a.b import c\n\nclass Foo:\n    def bar(self):\n        pass\n\ndef top():\n    pass\n"
    result = code_py.extract("x.py", source)
    quals = {(d.qualname, d.kind, d.parent) for d in result.definitions}
    assert ("Foo", "Class", None) in quals
    assert ("Foo.bar", "Function", "Foo") in quals
    assert ("top", "Function", None) in quals
    modules = {imp.module for imp in result.imports}
    assert "os" in modules
    assert "a.b" in modules


# --- build + get_node ------------------------------------------------------

def test_build_produces_file_and_def_nodes(tmp_path):
    repo = _write_repo(tmp_path)
    graph, report = build_graph(repo)
    assert graph.has_node(file_id("pkg/mod.py"))
    assert graph.has_node(definition_id("pkg/mod.py", "C"))
    assert graph.has_node(definition_id("pkg/mod.py", "C.m"))
    assert graph.has_node(definition_id("pkg/mod.py", "top"))
    assert report.code_entities >= 4

    result = queries.get_node(graph, file_id("pkg/mod.py"))
    assert result["found"] is True
    assert result["node"]["language"] == "python"


def test_build_resolves_cross_file_import(tmp_path):
    repo = _write_repo(tmp_path)
    graph, _ = build_graph(repo)
    edges = {(e["source"], e["target"], e["type"]) for e in graph.edges()}
    assert (file_id("pkg/user.py"), file_id("pkg/mod.py"), "imports") in edges


def test_get_node_missing_returns_not_found(tmp_path):
    graph, _ = build_graph(_write_repo(tmp_path))
    assert queries.get_node(graph, "file:nope.py") == {"found": False, "id": "file:nope.py"}


# --- CLI and MCP return the same answer (seeds AC-5.1) ---------------------

def test_cli_and_mcp_get_node_agree(tmp_path, capsys):
    from fastmcp import Client
    from aspark_graph.server import mcp

    repo = _write_repo(tmp_path)
    graph, _ = build_graph(repo)
    graph.save(queries.default_graph_path(repo))
    node_id = file_id("pkg/mod.py")

    # CLI
    rc = cli.main(["query", "get_node", "--repo", str(repo), node_id])
    assert rc == 0
    cli_out = json.loads(capsys.readouterr().out)

    # MCP (in-memory transport = real handshake + dispatch)
    async def call():
        async with Client(mcp) as c:
            res = await c.call_tool("get_node", {"id": node_id, "repo": str(repo)})
            return res.data

    mcp_out = asyncio.run(call())
    assert cli_out == mcp_out
    assert cli_out["found"] is True
