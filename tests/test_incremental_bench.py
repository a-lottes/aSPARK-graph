"""NFR-1 performance benchmark: incremental build must be ≥50% faster than full
rescan when ≤10% of files changed on a repo with 200+ source files.

Marked @pytest.mark.slow — excluded from the default `uv run pytest` run.
Run explicitly during /peer-review:

    uv run pytest -m slow -q

This test validates assumption A2 (parse cost dominates). If it fails, surface
before committing rather than shipping a miss.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from aspark_graph.build import build_graph
from aspark_graph.graph import default_graph_path


def _populate_repo(root: Path, n_files: int) -> list[Path]:
    """Write n_files realistic-size Python source files (100+ lines each).

    Files need to be large enough that tree-sitter parse time dominates over
    the cache I/O + SHA-256 hashing overhead (assumption A2 in the spec).
    Tiny files make parse time negligible, which is not the target workload.
    """
    files = []
    for i in range(n_files):
        subdir = root / f"pkg_{i // 50}"
        subdir.mkdir(exist_ok=True)
        p = subdir / f"mod_{i}.py"
        # 10 classes × 8 methods each ≈ 100+ lines — realistic module size.
        lines = [f"# module {i}\nfrom typing import Optional, List\n\n"]
        for c in range(10):
            lines.append(f"class Class{i}_{c}:\n")
            lines.append(f"    \"\"\"Docstring for Class{i}_{c}.\"\"\"\n\n")
            lines.append(f"    def __init__(self, x: int = {i}):\n")
            lines.append(f"        self.x = x\n")
            lines.append(f"        self.y: Optional[int] = None\n\n")
            for m in range(7):
                lines.append(f"    def method_{c}_{m}(self, value: int) -> int:\n")
                lines.append(f"        return self.x + value + {m}\n\n")
        p.write_text("".join(lines))
        files.append(p)
    return files


@pytest.mark.slow
def test_nfr1_incremental_at_least_50_percent_faster(tmp_path):
    """NFR-1: incremental build ≥50% faster than full rescan at ≤10% changed.

    Takes the median of 3 trial pairs to reduce wall-clock measurement noise.
    The benchmark is inherently machine-sensitive; /peer-review is the gate.
    """
    N = 220  # >200 files per spec
    changed_count = int(N * 0.08)  # 8% — well within the ≤10% scenario

    files = _populate_repo(tmp_path, N)

    # Warm: full build to populate cache and graph.json.
    g, _ = build_graph(tmp_path, full=True)
    g.save(default_graph_path(tmp_path))

    # Mutate ≤10% of files.
    for i in range(changed_count):
        files[i].write_text(
            f"# mutated module {i}\n\n"
            f"def mutated_{i}():\n"
            f"    return {i * 2}\n"
        )

    trials_inc = []
    trials_full = []
    for _ in range(3):
        t0 = time.perf_counter()
        build_graph(tmp_path)
        trials_inc.append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        build_graph(tmp_path, full=True)
        trials_full.append(time.perf_counter() - t0)

    trials_inc.sort()
    trials_full.sort()
    incremental_wall = trials_inc[1]   # median
    full_wall = trials_full[1]

    speedup_pct = (full_wall - incremental_wall) / full_wall * 100
    print(
        f"\nNFR-1 result (median of 3): incremental={incremental_wall:.3f}s  "
        f"full={full_wall:.3f}s  speedup={speedup_pct:.1f}%  (target ≥50%)"
    )
    assert speedup_pct >= 50, (
        f"Incremental build is only {speedup_pct:.1f}% faster than full rescan "
        f"({incremental_wall:.3f}s vs {full_wall:.3f}s). "
        f"If git inference (not yet cached) dominates, see A2 escape valve in plan."
    )
