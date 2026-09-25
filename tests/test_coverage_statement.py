"""Coverage statement (aSPARK issue #61): verdicts must disclose what parsed.

A clean gate_health over a partial parse is not clean - it is a confident
answer on incomplete data. These tests pin: recognized/skipped/near_misses on
the feature node, coverage echoed by gate_health, near-miss filenames flagged
instead of silently dropped, and no noise for complete trails.
"""

from pathlib import Path

from aspark_graph.artifacts import extract_features, feature_id
from aspark_graph.graph import Graph
from aspark_graph.queries import gate_health


def _make_feature(root: Path, name: str, files: dict) -> Path:
    d = root / ".spark" / name
    d.mkdir(parents=True)
    for fname, body in files.items():
        (d / fname).write_text(body)
    return d


SPEC = """# Spec: cov-demo

| | |
|---|---|
| **Phase** | Specify |
| **Status** | `approved` |
| **Date** | 2026-09-24 |

## 4. User Stories

### US-1 (Must): Coverage works

> As a maintainer, I want parse coverage disclosed.

**Acceptance criteria:**

- [ ] AC-1.1: Given a feature trail, when parsed, then coverage is recorded.

## 5. Out of Scope

Everything else.
"""

PLAN = """# Plan: cov-demo

| | |
|---|---|
| **Phase** | Plan |
| **Status** | `approved` |
| **Date** | 2026-09-24 |

## 3. Task Breakdown

| # | Task | Story | Depends on | Status | Definition of Done |
|---|---|---|---|---|---|
| T1 | Do the thing | US-1 | - | `done` | coverage recorded; files: src/x.py |
"""


def test_full_parse_lists_missing_as_skipped(tmp_path):
    _make_feature(tmp_path, "cov-demo", {"spec.md": SPEC, "plan.md": PLAN})
    g = Graph()
    extract_features(tmp_path, g)
    fid = feature_id("cov-demo")
    cov = g.get_node(fid)["coverage"]
    assert cov["recognized"] == ["plan.md", "spec.md"]
    assert cov["skipped"] == ["qa-report.md", "release-notes.md", "review-report.md"]
    assert cov["near_misses"] == []


def test_near_miss_filename_is_flagged_not_silent(tmp_path):
    _make_feature(tmp_path, "cov-demo",
                  {"spec.md": SPEC, "plan.md": PLAN, "reviews.md": "# x\n"})
    g = Graph()
    extract_features(tmp_path, g)
    fid = feature_id("cov-demo")
    assert g.get_node(fid)["coverage"]["near_misses"] == ["reviews.md"]


def test_gate_health_echoes_coverage_and_note(tmp_path):
    _make_feature(tmp_path, "cov-demo", {"spec.md": SPEC, "plan.md": PLAN})
    g = Graph()
    extract_features(tmp_path, g)
    res = gate_health(g, "cov-demo")
    assert res["found"] is True
    assert res["coverage"]["recognized"] == ["plan.md", "spec.md"]
    assert res["coverage_note"] == "verdict is over recognized artifacts only"


REVIEW = """# Review Report: cov-demo

| | |
|---|---|
| **Phase** | Review |
| **Status** | `passed` |
| **Date** | 2026-09-24 |

## 3. Findings

| # | Severity | Location | Finding | Status |
|---|---|---|---|---|
| F1 | Nit | `src/x.py:1` | could be typed | fixed |
"""

QA = """# QA Report: cov-demo

| | |
|---|---|
| **Phase** | Review (hands-on) |
| **Status** | `passed` |
| **Date** | 2026-09-24 |

## 2. Acceptance Criteria Verification

| AC | Steps performed | Expected | Observed | Result |
|---|---|---|---|---|
| AC-1.1 | check coverage | recorded | recorded | ✅ pass |

## 5. Verdict

Fine.
"""

RELEASE = """# Release: cov-demo

| | |
|---|---|
| **Phase** | Keep |
| **Status** | `released` |
| **Date** | 2026-09-24 |
"""


def test_gate_health_full_parse_has_no_note(tmp_path):
    files = {"spec.md": SPEC, "plan.md": PLAN, "review-report.md": REVIEW,
             "qa-report.md": QA, "release-notes.md": RELEASE}
    _make_feature(tmp_path, "cov-demo", files)
    g = Graph()
    extract_features(tmp_path, g)
    res = gate_health(g, "cov-demo")
    assert res["coverage"]["skipped"] == []
    assert res["coverage_note"] is None
