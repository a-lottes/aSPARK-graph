"""T1 smoke test: the package imports and exposes its version."""

import aspark_graph


def test_package_imports():
    assert aspark_graph.__version__ == "0.1.0"
