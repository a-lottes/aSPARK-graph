"""T10/T11: SECURITY.md says what it means and means what it says.

Doc-introspection testing (same technique as test_readme.py /
test_link_conventions.py / test_integration_docs.py): section extraction +
substring/count assertions, so the document cannot rot silently (AC-2.7).

T10 covers the document's own content (AC-2.1..2.6, AC-2.9, NFR-5). T11 adds
the README/CLAUDE.md link and prose assertions (AC-2.1, AC-2.7, AC-2.10).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECURITY_PATH = ROOT / "SECURITY.md"
README_PATH = ROOT / "README.md"
CLAUDE_MD_PATH = ROOT / "CLAUDE.md"
INTEGRATION_DOC_PATH = ROOT / "docs" / "aspark-integration.md"

_DENYLIST = ("sandbox", "isolat", "contain", "prevent", "protect")


def _security_text() -> str:
    assert SECURITY_PATH.exists(), "SECURITY.md does not exist at the repo root"
    return SECURITY_PATH.read_text()


def _section(text: str, heading: str) -> str:
    """Text from `## <heading>` to the next `## ` heading (or EOF)."""
    m = re.search(rf"^## {re.escape(heading)}\b(.*?)(?=\n## |\Z)", text, re.DOTALL | re.MULTILINE)
    assert m, f"SECURITY.md missing '## {heading}' section"
    return m.group(1)


# --- AC-2.1: the file exists -------------------------------------------------


def test_ac_2_1_security_md_exists():
    assert SECURITY_PATH.exists()


# --- AC-2.2: trust boundary ---------------------------------------------------


def test_ac_2_2_trust_boundary_stated():
    section = _section(_security_text(), "Trust boundary")
    lowered = section.lower()
    assert "stdio" in lowered
    assert "no authentication" in lowered or "no auth" in lowered
    assert "no http" in lowered
    assert "no network" in lowered or "network access" in lowered
    assert "remote transport" in lowered
    assert "1.20" in section and "cryptography" in section
    assert "packaging decision" in lowered
    assert "not a" in lowered and "security control" in lowered


# --- AC-2.3: exactly six named non-guarantees --------------------------------

_NON_GUARANTEE_MARKERS = [
    "shape check",         # 1: not a sandbox
    "no privilege",        # 2: removes no privilege the caller didn't have
    "not read-only",       # 3: MCP surface writes
    "nothing in it is sanitised",  # 4: graph output is data, nothing sanitised
    "multi-tenant",        # 5: no auth/HTTP/network/multi-user
    "no confinement check",  # 6: pre-confinement graphs stayed unchecked
]


def test_ac_2_3_six_non_guarantees_present():
    section = _section(_security_text(), "Non-guarantees")
    # Numbered list items 1..6, and no 7th.
    items = re.findall(r"^\d+\.\s", section, re.MULTILINE)
    assert len(items) == 6, f"expected exactly six numbered non-guarantees, found {len(items)}"
    lowered = section.lower()
    for marker in _NON_GUARANTEE_MARKERS:
        assert marker in lowered, f"non-guarantee marker {marker!r} not found in the section"


# --- AC-2.4: the keyword denylist, outside Non-guarantees only --------------


def test_ac_2_4_denylist_words_appear_only_in_non_guarantees():
    text = _security_text()
    non_guarantees = _section(text, "Non-guarantees")
    rest = text.replace(non_guarantees, "")  # every other section, concatenated
    for word in _DENYLIST:
        offenders = [
            line for line in rest.splitlines() if re.search(word, line, re.IGNORECASE)
        ]
        assert offenders == [], f"{word!r} appears outside Non-guarantees: {offenders}"


# --- AC-2.5: output is data, not instruction --------------------------------


def test_ac_2_5_output_is_data_not_instruction_section():
    section = _section(_security_text(), "Output is data, not instruction")
    lowered = section.lower()
    assert "prompt-injection" in lowered or "prompt injection" in lowered
    assert "find_nodes" in section
    assert "spark" in lowered  # .spark/ artifact prose is named as ingested
    assert "never" in lowered and "instruction" in lowered


# --- AC-2.6: reporting channel + scope --------------------------------------


def test_ac_2_6_reporting_channel_and_response_window():
    section = _section(_security_text(), "Reporting a vulnerability")
    lowered = section.lower()
    assert "private security advisor" in lowered or "private vulnerability" in lowered or "private security" in lowered
    assert "never a public issue" in lowered or "not a public issue" in lowered
    assert "5 working days" in section
    assert "in scope" in lowered


# --- AC-2.9: the two bounds' bases are stated as different in kind ----------


def test_ac_2_9_entry_bound_is_measured_size_cap_is_judgement():
    section = _section(_security_text(), "Build limits")
    lowered = section.lower()
    assert "measured" in lowered
    assert "judgement call" in lowered or "judgment call" in lowered
    assert "not a measurement" in lowered
    # The measurement basis is actually named, not just asserted.
    assert "7 local repositories" in section or "7 repositories" in section
    assert "2026-07-26" in section
    assert "200,000" in section or "200000" in section
    assert "5 mb" in lowered


# --- T11: AC-2.1/AC-2.7 — both files link SECURITY.md -----------------------


def test_ac_2_1_readme_and_claude_md_link_security_doc():
    assert "SECURITY.md" in README_PATH.read_text()
    assert "SECURITY.md" in CLAUDE_MD_PATH.read_text()


# --- T11: AC-2.10(a) — README's MCP tool list marks build_graph as writing -


def test_ac_2_10a_readme_mcp_tool_list_marks_build_graph_as_writing():
    readme = README_PATH.read_text()
    m = re.search(r"### MCP\b(.*?)(?=\n## |\Z)", readme, re.DOTALL)
    assert m, "README.md missing '### MCP' section"
    section = m.group(1)
    lowered = section.lower()
    assert "build_graph" in section
    assert "read-only" in lowered
    assert "writes" in lowered or "write" in lowered


# --- T11: AC-2.10(b) — "disposable read model" describes the artifact ------


def test_ac_2_10b_disposable_read_model_phrasing_names_the_graph_artifact():
    found_any = False
    for path in (README_PATH, CLAUDE_MD_PATH):
        text = path.read_text()
        for m in re.finditer(r"disposable\s+read\s+model", text, re.IGNORECASE):
            found_any = True
            # The surrounding ~300 chars must name the graph artifact, not
            # just the tool/server in general.
            window = text[max(0, m.start() - 300): m.end() + 100]
            assert "graph" in window.lower(), (
                f"{path.name}: 'disposable read model' near {window!r} "
                "doesn't name the graph artifact"
            )
    assert found_any, "expected 'disposable read model' to appear at least once"


# --- T11: AC-2.10(c) — no sentence states or implies the MCP surface is
# read-only -------------------------------------------------------------


def test_ac_2_10c_neither_file_claims_the_mcp_surface_is_read_only():
    banned = (
        "read-only mcp",
        "mcp surface is read-only",
        "mcp server is read-only",
        "read-only server",
    )
    for path in (README_PATH, CLAUDE_MD_PATH):
        lowered = path.read_text().lower()
        for phrase in banned:
            assert phrase not in lowered, f"{path.name} contains {phrase!r}"


# --- T12: AC-4.1 — the injection warning travels with each copied block ----


def _delimited_block(text: str, name: str) -> str:
    m = re.search(
        rf"<!-- BEGIN: {re.escape(name)} block[^>]*-->(.*?)<!-- END: {re.escape(name)} block -->",
        text,
        re.DOTALL,
    )
    assert m, f"docs/aspark-integration.md missing the {name} block delimiters"
    return m.group(1)


def test_ac_4_1_injection_warning_present_in_both_copied_blocks():
    text = INTEGRATION_DOC_PATH.read_text()
    for block_name in ("Reviewer", "QA-Tester"):
        block = _delimited_block(text, block_name)
        lowered = block.lower()
        assert "data" in lowered and "instruction" in lowered, (
            f"{block_name} block has no 'data, not instruction' warning — "
            "it would not travel with a copied block"
        )
        assert "SECURITY.md" in block
