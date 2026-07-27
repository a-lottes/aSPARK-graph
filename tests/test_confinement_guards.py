"""T6: introspection guards for the confinement architecture (security-posture).

Covers AC-1.10 (no bypass exists, anywhere, under any name), NFR-7 (the
adapters render RepoRefused but hold no rule logic of their own) and NFR-1
(a verdict reads no file contents and is fast). These are the cheapest
defence against the design silently eroding later — R1 in the plan rejected
a test-only bypass entirely, so this file asserts the *absence* of one
rather than merely constraining a bypass's reach.
"""

from __future__ import annotations

import ast
import inspect
import re
import time
from pathlib import Path

import pytest

from aspark_graph import cli, confinement, server

SRC = Path(__file__).resolve().parents[1] / "src" / "aspark_graph"

_SUSPICIOUS_NAME_RE = re.compile(
    r"bypass|allow.?any|allow.?all|skip.?confin|disable.?confin|unsafe|no.?confin|force.?repo",
    re.IGNORECASE,
)


# --- AC-1.10: no bypass exists, under any name ------------------------------


def test_confinement_public_surface_has_no_bypass_hook():
    public_names = [n for n in dir(confinement) if not n.startswith("_")]
    offenders = [n for n in public_names if _SUSPICIOUS_NAME_RE.search(n)]
    assert offenders == [], f"confinement.py exposes a suspiciously bypass-shaped name: {offenders}"


def test_confinement_reads_no_environment_variable():
    source = (SRC / "confinement.py").read_text()
    assert "environ" not in source
    assert "getenv" not in source


def test_ensure_repo_takes_exactly_one_parameter():
    params = inspect.signature(confinement.ensure_repo).parameters
    assert list(params) == ["path"]


def test_no_cli_flag_matches_a_bypass_name():
    cli_source = (SRC / "cli.py").read_text()
    flags = re.findall(r'add_argument\(\s*"(-[-\w]+)"', cli_source)
    offenders = [f for f in flags if _SUSPICIOUS_NAME_RE.search(f)]
    assert offenders == [], f"a CLI flag looks like a confinement bypass: {offenders}"


def test_no_mcp_tool_parameter_matches_a_bypass_name():
    tool_names = set(cli._QUERY_NAMES) | {"build_graph"}
    offenders = []
    for name in tool_names:
        for param in inspect.signature(getattr(server, name)).parameters:
            if _SUSPICIOUS_NAME_RE.search(param):
                offenders.append((name, param))
    assert offenders == [], f"an MCP tool parameter looks like a confinement bypass: {offenders}"


# --- NFR-7: the adapters hold no rule logic ---------------------------------


def _confinement_attrs_used(source: str) -> set[str]:
    tree = ast.parse(source)
    attrs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "confinement":
            attrs.add(node.attr)
    return attrs


@pytest.mark.parametrize("filename", ["cli.py", "server.py"])
def test_adapter_only_ever_catches_repo_refused(filename):
    # The adapters render RepoRefused; they must never reach into confinement
    # for the rule itself (ensure_repo, the marker constants, the bounds).
    source = (SRC / filename).read_text()
    used = _confinement_attrs_used(source)
    assert used == {"RepoRefused"}, (
        f"{filename} touches confinement.{used - {'RepoRefused'}} — "
        "the rule must stay in confinement.py, not leak into the adapter"
    )


@pytest.mark.parametrize("filename", ["cli.py", "server.py"])
def test_adapter_source_has_no_rule_constants_or_markers(filename):
    source = (SRC / filename).read_text()
    for needle in ("MAX_ENTRIES", "MAX_FILE_BYTES", "GRAPH_DIRNAME", "GRAPH_FILENAME", "outside_confinement", "too_large"):
        assert needle not in source, f"{filename} hardcodes {needle!r} — that belongs in confinement.py alone"


# --- NFR-1: reads no file contents, and is fast -----------------------------


def test_ensure_repo_reads_no_file_contents(tmp_path, monkeypatch):
    marked = tmp_path / "marked"
    marked.mkdir()
    (marked / ".aspark-graph").mkdir()
    (marked / ".aspark-graph" / "graph.json").write_text('{"nodes": [], "edges": []}')

    def _boom(*a, **kw):
        raise AssertionError("ensure_repo must not read file contents")

    monkeypatch.setattr("builtins.open", _boom)
    monkeypatch.setattr("pathlib.Path.read_bytes", _boom)
    monkeypatch.setattr("pathlib.Path.read_text", _boom)
    assert confinement.ensure_repo(marked) == marked.resolve()


def test_1000_verdicts_complete_well_under_100ms_each(tmp_path):
    marked = tmp_path / "marked"
    marked.mkdir()
    (marked / ".git").mkdir()

    start = time.monotonic()
    for _ in range(1000):
        confinement.ensure_repo(marked)
    elapsed = time.monotonic() - start

    assert elapsed / 1000 < 0.1  # NFR-1: <100ms per verdict
