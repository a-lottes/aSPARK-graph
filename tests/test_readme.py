"""T11/pypi-publish T3: README documents only install paths that work today
(US-6, AC-6.1/6.3; inverted for pypi-publish AC-2.3 once the package is
published — see .spark/pypi-publish/spec.md).
"""

import re
from pathlib import Path

README = (Path(__file__).resolve().parents[1] / "README.md").read_text()


def _install_section() -> str:
    # From the "## Install" heading to the next "## " heading.
    m = re.search(r"## Install\b(.*?)(?=\n## )", README, re.DOTALL)
    assert m, "README has no Install section"
    return m.group(1)


def _development_section() -> str:
    # From the "## Development" heading to the next "## " heading (or EOF).
    m = re.search(r"## Development\b(.*?)(?=\n## |\Z)", README, re.DOTALL)
    assert m, "README has no Development section"
    return m.group(1)


def test_ac_6_1_no_fictional_package_index_command():
    # pypi-publish AC-2.1/2.3: the package is live, so the published install
    # commands must be present, not fictional.
    section = _install_section()
    assert "uvx aspark-graph" in section
    assert "pip install aspark-graph" in section


def test_ac_6_1_from_source_path_is_documented():
    # pypi-publish AC-2.3/2.5: "not yet published" is gone from the whole
    # README, and the from-source path lives under Development, not Install.
    normalized = " ".join(README.lower().split())  # collapse line wraps
    assert "not yet published" not in normalized

    dev_section = _development_section()
    assert "uv sync" in dev_section
    assert "uv run aspark-graph build" in dev_section

    install_section = _install_section()
    assert "uv sync" not in install_section
    assert "git clone" not in install_section


def test_ac_6_3_mcp_add_uses_working_entry_point():
    # pypi-publish AC-2.2/2.3: the Install section's `claude mcp add` line
    # uses the published `uvx` entry point, not the from-source `uv run
    # --directory` form (which still lives, correctly, under Development).
    section = _install_section()
    assert "claude mcp add" in section
    mcp_line = next(line for line in section.splitlines() if "claude mcp add" in line)
    assert "uvx" in mcp_line
    assert "uv run --directory" not in mcp_line
