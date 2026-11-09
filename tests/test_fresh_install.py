"""v0.7.3 hotfix: a fresh, UNLOCKED install must boot the MCP server.

The rest of the suite runs against uv.lock, so it only ever sees the locked
dependency set. A real user's `pip install aspark-graph` / `uvx aspark-graph
serve` resolves the newest versions our ranges allow — and when pydantic 2.14
removed a private helper that mcp 1.19 imports, `serve` crashed on start for
every new install while this suite stayed green.

This test builds the wheel, installs it into a fresh venv with a normal
resolve (no lockfile, no constraints), starts `aspark-graph serve` over stdio
and lists its tools via the mcp client. It needs network access to the
package index, like `uv build` in test_packaging.py.

Marked slow: builds a wheel and resolves a full environment.
"""

import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

_EXPECTED_TOOLS = [
    "build_graph",
    "find_nodes",
    "gate_health",
    "get_neighbors",
    "get_node",
    "impact",
    "shortest_path",
    "staleness",
    "story_trace",
]

_CLIENT = textwrap.dedent(
    """
    import asyncio, sys
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def main():
        params = StdioServerParameters(command=sys.argv[1], args=["serve"])
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                tools = await s.list_tools()
                print(",".join(sorted(t.name for t in tools.tools)))

    asyncio.run(asyncio.wait_for(main(), timeout=60))
    """
)


@pytest.mark.slow
def test_unlocked_wheel_install_boots_mcp_server(tmp_path):
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv not on PATH; run under 'uv run pytest -m slow'")

    dist = tmp_path / "dist"
    subprocess.run(
        [uv, "build", "--wheel", "--out-dir", str(dist)],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    wheels = list(dist.glob("*.whl"))
    assert len(wheels) == 1, f"expected exactly one wheel, found {wheels}"

    venv = tmp_path / "venv"
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    subprocess.run(
        [uv, "venv", "--python", py_version, str(venv)],
        check=True, capture_output=True, text=True,
    )
    py = venv / "bin" / "python"
    exe = venv / "bin" / "aspark-graph"
    # A plain resolve, deliberately run outside the repo so no uv.lock or
    # project config can influence it — exactly what a new user gets.
    subprocess.run(
        [uv, "pip", "install", "--python", str(py), "--refresh", str(wheels[0])],
        cwd=tmp_path, check=True, capture_output=True, text=True,
    )

    client = tmp_path / "client.py"
    client.write_text(_CLIENT)
    result = subprocess.run(
        [str(py), str(client), str(exe)],
        cwd=tmp_path, capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, (
        "aspark-graph serve did not boot in a fresh unlocked install:\n"
        + result.stderr[-2000:]
    )
    assert result.stdout.strip().split(",") == _EXPECTED_TOOLS
