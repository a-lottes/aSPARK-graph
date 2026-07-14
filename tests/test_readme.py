"""T11: README documents only install paths that work today (US-6, AC-6.1/6.3)."""

import re
from pathlib import Path

README = (Path(__file__).resolve().parents[1] / "README.md").read_text()


def _install_section() -> str:
    # From the "## Install" heading to the next "## " heading.
    m = re.search(r"## Install\b(.*?)(?=\n## )", README, re.DOTALL)
    assert m, "README has no Install section"
    return m.group(1)


def test_ac_6_1_no_fictional_package_index_command():
    section = _install_section()
    # No copy-pasteable uvx/pip/PyPI install command (the tool is unpublished).
    assert "uvx aspark-graph" not in section
    assert "pip install aspark-graph" not in section


def test_ac_6_1_from_source_path_is_documented():
    section = _install_section()
    assert "uv sync" in section
    assert "uv run aspark-graph build" in section
    normalized = " ".join(section.lower().split())  # collapse line wraps
    assert "not yet published" in normalized


def test_ac_6_3_mcp_add_uses_working_entry_point():
    section = _install_section()
    assert "claude mcp add" in section
    # The MCP-add command must use the working `uv run` form, not fictional uvx.
    mcp_line = next(line for line in section.splitlines() if "claude mcp add" in line)
    assert "uv run" in mcp_line
    assert "uvx" not in mcp_line
