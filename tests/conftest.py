"""Shared fixtures. The sample_repo trail doubles as a realistic .spark/ fixture."""

from pathlib import Path

import pytest

from aspark_graph.build import build_graph

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_REPO = FIXTURES / "sample_repo"


@pytest.fixture
def sample_repo() -> Path:
    return SAMPLE_REPO


@pytest.fixture
def sample_graph():
    graph, report = build_graph(SAMPLE_REPO)
    return graph, report
