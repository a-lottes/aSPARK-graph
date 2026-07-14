"""F3: MCP query tools return a clean 'build first' dict, never a raw error.

Parity with the CLI's AC-5.2 behaviour (which prints a clean message and exits
1) — the MCP client must not receive a raised GraphNotBuiltError.
"""

import asyncio

from fastmcp import Client

from aspark_graph.server import mcp


def _call(tool, params):
    async def go():
        async with Client(mcp) as c:
            return (await c.call_tool(tool, params)).data
    return asyncio.run(go())


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
