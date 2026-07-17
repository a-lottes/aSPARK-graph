"""T3/T4/T5/T6: docs/aspark-integration.md is correct, portable, and coherent.

Doc-introspection testing (same technique as test_readme.py / test_link_conventions.py).
Every `aspark-graph` invocation in the shipped blocks is validated against the live
CLI surface introspected from cli.py — so a tool rename or removal that invalidates a
documented command turns a doc lie into a red test.

Vocabulary contract for prose assertions (US-2, AC-2.x):
  - staleness pre-check: the word "staleness" must appear in the block
  - grep/read fallback: "fallback" or "grep" must appear
  - accelerant framing: "accelerant" must appear
  - empty-result caveat: "found" and ("manually" or "fall back") must appear
  - confidence-tier caveat: "inferred" must appear (AC-1.5 / AC-3.x)
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = (ROOT / "docs" / "aspark-integration.md").read_text()
CLAUDE_MD = (ROOT / "CLAUDE.md").read_text()


# ---------------------------------------------------------------------------
# CLI surface (introspected, not hardcoded)
# ---------------------------------------------------------------------------

from aspark_graph.cli import _QUERY_ARGS, _QUERY_NAMES  # noqa: E402

_VALID_QUERY_NAMES: frozenset[str] = frozenset(_QUERY_NAMES)
_VALID_TOP_LEVEL: frozenset[str] = frozenset({"build", "serve", "query"})


def _valid_flags_per_query() -> dict[str, frozenset[str]]:
    """Returns {query_name: frozenset_of_valid_long_flags}."""
    result: dict[str, frozenset[str]] = {}
    for name in _QUERY_NAMES:
        p = argparse.ArgumentParser()
        _QUERY_ARGS[name](p)
        p.add_argument("--repo", default=".")
        result[name] = frozenset(
            opt
            for action in p._actions
            for opt in action.option_strings
            if opt.startswith("--")
        )
    return result


_FLAGS: dict[str, frozenset[str]] = _valid_flags_per_query()


# ---------------------------------------------------------------------------
# Block extraction helpers
# ---------------------------------------------------------------------------

def _reviewer_block() -> str:
    """Extract text between the Reviewer block delimiters in the docs file."""
    m = re.search(
        r"<!-- BEGIN: Reviewer block[^>]*-->(.*?)<!-- END: Reviewer block -->",
        DOCS,
        re.DOTALL,
    )
    assert m, "docs/aspark-integration.md missing <!-- BEGIN: Reviewer block --> delimiter"
    return m.group(1)


def _qa_block() -> str:
    """Extract text between the QA-Tester block delimiters in the docs file."""
    m = re.search(
        r"<!-- BEGIN: QA-Tester block[^>]*-->(.*?)<!-- END: QA-Tester block -->",
        DOCS,
        re.DOTALL,
    )
    assert m, "docs/aspark-integration.md missing <!-- BEGIN: QA-Tester block --> delimiter"
    return m.group(1)


def _setup_section() -> str:
    """Extract the Setup section from the docs file."""
    m = re.search(r"## Setup\b(.*?)$", DOCS, re.DOTALL)
    assert m, "docs/aspark-integration.md missing ## Setup section"
    return m.group(1)


def _extract_commands(text: str) -> list[tuple[str, str | None, list[str]]]:
    """Return [(verb, subcommand_or_None, [long_flags])] for aspark-graph lines.

    Only lines whose first non-space token is 'aspark-graph' are extracted
    (comment lines starting with '#' are skipped automatically).
    """
    results = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("aspark-graph"):
            continue
        parts = stripped.split()
        if len(parts) < 2:
            continue
        verb = parts[1]
        if verb == "query" and len(parts) >= 3:
            subcommand = parts[2]
            rest = " ".join(parts[3:])
            flags = re.findall(r"--[\w-]+", rest)
            results.append(("query", subcommand, flags))
        elif verb in ("build", "serve"):
            results.append((verb, None, []))
    return results


# ---------------------------------------------------------------------------
# T3: Reviewer block — correct tool names and flags (AC-1.2, AC-1.3)
# ---------------------------------------------------------------------------

def test_reviewer_block_exists():
    block = _reviewer_block()
    assert len(block.strip()) > 0


def test_reviewer_block_names_real_query_subcommands():
    """Every query in the Reviewer block must be a real CLI subcommand (AC-1.3)."""
    for verb, subcommand, _ in _extract_commands(_reviewer_block()):
        if verb == "query":
            assert subcommand in _VALID_QUERY_NAMES, (
                f"Reviewer block references fictional query subcommand: {subcommand!r}. "
                f"Valid: {sorted(_VALID_QUERY_NAMES)}"
            )


def test_reviewer_block_flags_are_valid():
    """Every long flag in the Reviewer block must exist on its subcommand's parser (AC-1.3)."""
    for verb, subcommand, flags in _extract_commands(_reviewer_block()):
        if verb != "query" or not subcommand:
            continue
        valid = _FLAGS.get(subcommand, frozenset())
        for flag in flags:
            assert flag in valid, (
                f"Flag {flag!r} not valid for `aspark-graph query {subcommand}`. "
                f"Valid flags: {sorted(valid)}"
            )


def test_reviewer_block_has_required_tools(  ):
    """Reviewer block must direct the use of impact, story_trace, and gate_health (AC-1.2)."""
    block = _reviewer_block()
    invoked = {sc for _, sc, _ in _extract_commands(block) if sc}
    assert "impact" in invoked, "Reviewer block missing impact invocation (AC-1.2)"
    assert "story_trace" in invoked, "Reviewer block missing story_trace invocation (AC-1.2)"
    assert "gate_health" in invoked, "Reviewer block missing gate_health invocation (AC-1.2)"


def test_reviewer_block_has_impact_diff_flag():
    """Reviewer block must show impact --diff <range> variant (AC-1.2)."""
    block = _reviewer_block()
    diff_invocations = [
        (sc, flags) for _, sc, flags in _extract_commands(block)
        if sc == "impact" and "--diff" in flags
    ]
    assert diff_invocations, "Reviewer block missing `impact --diff <range>` variant (AC-1.2)"


# ---------------------------------------------------------------------------
# T3: Reviewer block — graceful degradation required elements (US-2 / AC-2.x)
# ---------------------------------------------------------------------------

def test_reviewer_block_has_staleness_precheck():
    """Reviewer block must instruct staleness check before trusting results (AC-2.1)."""
    assert "staleness" in _reviewer_block(), (
        "Reviewer block missing staleness pre-check (AC-2.1)"
    )


def test_reviewer_block_has_grep_fallback():
    """Reviewer block must explicitly state grep/read fallback (AC-2.2)."""
    block = _reviewer_block().lower()
    assert "fallback" in block or "grep" in block, (
        "Reviewer block missing grep/read fallback instruction (AC-2.2)"
    )


def test_reviewer_block_has_accelerant_framing():
    """Reviewer block must frame tools as accelerant, not hard dependency (AC-2.3)."""
    assert "accelerant" in _reviewer_block(), (
        "Reviewer block missing 'accelerant, not a hard dependency' framing (AC-2.3)"
    )


def test_reviewer_block_has_empty_result_caveat():
    """Reviewer block must say empty result → fall back / confirm manually (AC-2.4)."""
    block = _reviewer_block().lower()
    has_found = "found" in block
    has_action = "manually" in block or "fall back" in block
    assert has_found and has_action, (
        "Reviewer block missing empty-result 'confirm manually' caveat (AC-2.4)"
    )


def test_reviewer_block_has_confidence_tier_caveat():
    """Reviewer block must reference inferred confidence tier (AC-1.5)."""
    assert "inferred" in _reviewer_block(), (
        "Reviewer block missing confidence-tier caveat (AC-1.5)"
    )


# ---------------------------------------------------------------------------
# T3: Reviewer block — portability (AC-1.4, NFR-3)
# ---------------------------------------------------------------------------

_THIS_REPO_SPARK_FEATURES = [
    "gate-integration",
    "distributable-install",
    "close-the-loop",
    "aspark-graph",  # only as a feature name in --feature context
]
_THIS_REPO_PATHS = ["src/aspark_graph/", ".spark/gate-integration", ".spark/aspark-graph"]


def test_reviewer_block_is_portable():
    """Shipped Reviewer block must not contain this-repo-specific feature names or paths."""
    block = _reviewer_block()
    for literal in _THIS_REPO_PATHS:
        assert literal not in block, (
            f"Portability breach in Reviewer block: {literal!r} (AC-1.4, NFR-3)"
        )
    # gate-integration is a this-repo feature name; must not appear as a value
    assert "gate-integration" not in block, (
        "Portability breach: 'gate-integration' feature name in shipped Reviewer block (AC-1.4)"
    )
    # --feature aspark-graph would be a hardcoded value; check for --feature with concrete value
    # (placeholder <feature> is fine; 'aspark-graph' as the resolved value is not)
    assert "--feature aspark-graph" not in block, (
        "Portability breach: '--feature aspark-graph' (hardcoded repo value) in shipped block (AC-1.4)"
    )


# ---------------------------------------------------------------------------
# T4: QA-Tester block — correct tools and graceful degradation (AC-3.x)
# ---------------------------------------------------------------------------

def test_qa_block_exists():
    block = _qa_block()
    assert len(block.strip()) > 0


def test_qa_block_names_real_query_subcommands():
    """Every query in the QA block must be a real CLI subcommand (AC-3.4)."""
    for verb, subcommand, _ in _extract_commands(_qa_block()):
        if verb == "query":
            assert subcommand in _VALID_QUERY_NAMES, (
                f"QA-Tester block references fictional query subcommand: {subcommand!r}"
            )


def test_qa_block_flags_are_valid():
    """Every long flag in the QA block must exist on its subcommand's parser (AC-3.4)."""
    for verb, subcommand, flags in _extract_commands(_qa_block()):
        if verb != "query" or not subcommand:
            continue
        valid = _FLAGS.get(subcommand, frozenset())
        for flag in flags:
            assert flag in valid, (
                f"Flag {flag!r} not valid for `aspark-graph query {subcommand}` in QA block. "
                f"Valid: {sorted(valid)}"
            )


def test_qa_block_has_required_tools():
    """QA block must direct the use of story_trace and gate_health (AC-3.1)."""
    block = _qa_block()
    invoked = {sc for _, sc, _ in _extract_commands(block) if sc}
    assert "story_trace" in invoked, "QA block missing story_trace invocation (AC-3.1)"
    assert "gate_health" in invoked, "QA block missing gate_health invocation (AC-3.1)"


def test_qa_block_has_staleness_precheck():
    """QA block must have staleness check before trusting results (AC-3.3)."""
    assert "staleness" in _qa_block(), "QA block missing staleness pre-check (AC-3.3)"


def test_qa_block_has_grep_fallback():
    """QA block must state fallback to reading the spec directly (AC-3.3)."""
    block = _qa_block().lower()
    assert "fallback" in block or "directly" in block or "spec" in block, (
        "QA block missing fallback instruction (AC-3.3)"
    )


def test_qa_block_has_non_replacement_caveat():
    """QA block must state graph scopes plan but never replaces performing steps (AC-3.2)."""
    block = _qa_block().lower()
    # "if you didn't see it, it didn't happen" or similar
    assert "see it" in block or "didn't happen" in block or "replaces" in block, (
        "QA block missing 'graph scopes but never replaces performing' caveat (AC-3.2)"
    )


def test_qa_block_has_confidence_tier_caveat():
    """QA block must reference inferred tier (AC-3.x / consistency with Reviewer)."""
    assert "inferred" in _qa_block(), "QA block missing confidence-tier caveat"


def test_qa_block_is_portable():
    """Shipped QA block must not contain this-repo-specific feature names or paths."""
    block = _qa_block()
    for literal in _THIS_REPO_PATHS:
        assert literal not in block, (
            f"Portability breach in QA block: {literal!r} (NFR-3)"
        )
    assert "gate-integration" not in block, (
        "Portability breach: 'gate-integration' feature name in shipped QA block"
    )
    assert "--feature aspark-graph" not in block, (
        "Portability breach: '--feature aspark-graph' (hardcoded repo value) in shipped QA block (AC-1.4)"
    )


# ---------------------------------------------------------------------------
# T5: Setup section — honest prerequisites and README references (US-4 / AC-4.x)
# ---------------------------------------------------------------------------

def test_setup_section_exists():
    section = _setup_section()
    assert len(section.strip()) > 0


def test_setup_section_mentions_mcp_server():
    """Setup must state MCP server as a prerequisite (AC-4.1)."""
    section = _setup_section().lower()
    assert "mcp" in section, "Setup section missing MCP server prerequisite (AC-4.1)"


def test_setup_section_mentions_build():
    """Setup must state 'aspark-graph build .' as a prerequisite (AC-4.1)."""
    section = _setup_section()
    assert "aspark-graph build" in section, (
        "Setup section missing 'aspark-graph build' prerequisite (AC-4.1)"
    )


def test_setup_section_has_staleness_caveat():
    """Setup must state the staleness caveat (AC-4.2)."""
    section = _setup_section().lower()
    assert "stale" in section or "staleness" in section, (
        "Setup section missing staleness caveat (AC-4.2)"
    )


def test_setup_section_references_readme():
    """Setup must reference/link to the README instead of duplicating install commands (AC-4.3)."""
    section = _setup_section()
    assert "README" in section or "readme" in section.lower(), (
        "Setup section missing README reference (AC-4.3, NFR-4)"
    )


def test_setup_section_does_not_duplicate_install_commands():
    """Setup must not restate git clone or uv sync commands (AC-4.3, NFR-4)."""
    section = _setup_section()
    assert "git clone" not in section, (
        "Setup section duplicates 'git clone' (should reference README, not copy it) (AC-4.3)"
    )
    assert "uv sync" not in section, (
        "Setup section duplicates 'uv sync' (should reference README, not copy it) (AC-4.3)"
    )


# ---------------------------------------------------------------------------
# T5: README has a pointer to docs/aspark-integration.md
# ---------------------------------------------------------------------------

def test_readme_has_integration_docs_pointer():
    """README must have a pointer to docs/aspark-integration.md (discoverability)."""
    readme = (ROOT / "README.md").read_text()
    assert "aspark-integration" in readme, (
        "README missing pointer to docs/aspark-integration.md"
    )


# ---------------------------------------------------------------------------
# T6: CLAUDE.md dogfood witness (AC-5.1, AC-5.2, AC-5.3)
# ---------------------------------------------------------------------------

def test_claude_md_has_reviewer_tool_references():
    """CLAUDE.md must reference the core reviewer tools (AC-5.1)."""
    assert "impact" in CLAUDE_MD, "CLAUDE.md missing impact reference (AC-5.1)"
    assert "story_trace" in CLAUDE_MD, "CLAUDE.md missing story_trace reference (AC-5.1)"
    assert "gate_health" in CLAUDE_MD, "CLAUDE.md missing gate_health reference (AC-5.1)"


def test_claude_md_reviewer_tools_are_real():
    """Tool invocations in CLAUDE.md must reference real CLI subcommands (AC-5.1)."""
    for verb, subcommand, flags in _extract_commands(CLAUDE_MD):
        if verb != "query" or not subcommand:
            continue
        assert subcommand in _VALID_QUERY_NAMES, (
            f"CLAUDE.md references fictional query subcommand: {subcommand!r} (AC-5.1)"
        )
        valid = _FLAGS.get(subcommand, frozenset())
        for flag in flags:
            assert flag in valid, (
                f"Flag {flag!r} not valid for `aspark-graph query {subcommand}` in CLAUDE.md "
                f"(AC-5.1). Valid: {sorted(valid)}"
            )


def test_claude_md_has_freshness_note():
    """CLAUDE.md reviewer section must note graph freshness requirement (AC-5.2)."""
    lower = CLAUDE_MD.lower()
    assert "fresh" in lower or "stale" in lower or "staleness" in lower, (
        "CLAUDE.md missing graph-freshness note for reviewer (AC-5.2)"
    )


def test_claude_md_no_active_qa_tester_block():
    """CLAUDE.md must not contain an active QA-Tester / demo-day instruction (AC-5.3).

    The QA block is absent or explicitly N/A (aspark-graph is headless).
    The exact heading '## Using aspark-graph in /demo-day' would be an active QA block;
    its presence is a violation regardless of what else appears in the file.
    """
    assert "## Using aspark-graph in /demo-day" not in CLAUDE_MD, (
        "CLAUDE.md contains an active /demo-day QA-Tester block (AC-5.3); "
        "aspark-graph is headless — only the Reviewer block is dogfooded here"
    )
