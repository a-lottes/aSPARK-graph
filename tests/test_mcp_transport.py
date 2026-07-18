"""US-2: stdio MCP transport smoke test (AC-2.1/2.2/2.3/2.4).

Wire format: newline-delimited JSON (one compact JSON object + "\n" per message).
Verified against mcp 1.19.0 (mcp/server/stdio.py, mcp/server/session.py, mcp/types.py).
Handshake: initialize (id:1) → notifications/initialized → tools/call (id:2).
Match responses by "id" — the server emits the initialize response before the tool result.
"""

import json
import shutil
import subprocess
import threading

import pytest

from aspark_graph.build import build_graph
from aspark_graph.graph import default_graph_path


@pytest.mark.slow
def test_mcp_stdio_transport_round_trip(tmp_path):
    """AC-2.1/2.2/2.3: initialize + tools/call over newline-delimited JSON-RPC."""
    if shutil.which("aspark-graph") is None:  # AC-2.3
        pytest.skip("aspark-graph not on PATH; run under 'uv run pytest -m slow'")

    # Inline fixture: a minimal built graph so staleness has something to query (A3).
    (tmp_path / "hello.py").write_text("def greet():\n    return 'hello'\n")
    graph, _ = build_graph(tmp_path)
    graph.save(default_graph_path(tmp_path))

    proc = subprocess.Popen(
        ["aspark-graph", "serve"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Drain stderr concurrently to prevent pipe-buffer deadlock (F3) and to
    # capture diagnostic content for timeout failures (F1).
    stderr_buf: list[bytes] = []
    stderr_drain = threading.Thread(
        target=lambda: stderr_buf.append(proc.stderr.read()),
        daemon=True,
    )
    stderr_drain.start()

    # Watchdog: kill the process if the read loop deadlocks (R1).
    watchdog = threading.Timer(10.0, proc.kill)
    watchdog.start()
    tool_response = None
    try:
        for msg in [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "smoke", "version": "0"},
                },
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "staleness", "arguments": {"repo": str(tmp_path)}},
            },
        ]:
            proc.stdin.write((json.dumps(msg, separators=(",", ":")) + "\n").encode())
        proc.stdin.flush()

        # Read stdout lines; match by id==2 — initialize response arrives first (R3).
        while True:
            raw = proc.stdout.readline()
            if not raw:
                break
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if data.get("id") == 2:
                tool_response = data
                break
    finally:
        watchdog.cancel()

    # On timeout, kill first so the stderr drain thread can reach EOF (F1).
    if tool_response is None:
        proc.kill()

    # AC-2.2: close stdin to signal the server to exit on the success path.
    proc.stdin.close()
    proc.wait(timeout=5)
    stderr_drain.join(timeout=2)
    proc.stdout.close()  # F2: close handles after process has exited
    proc.stderr.close()

    stderr_out = (stderr_buf[0] if stderr_buf else b"").decode(errors="replace")

    # AC-2.1: valid JSON, no top-level error key, received within 10 s.
    assert tool_response is not None, (
        f"No id=2 response within 10 s; server stderr: {stderr_out!r}"
    )
    assert "error" not in tool_response, f"Unexpected transport error: {tool_response}"

    # AC-2.2: subprocess exits 0 after stdin close.
    assert proc.returncode == 0, f"Server exited with code {proc.returncode}"
