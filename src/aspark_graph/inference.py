"""Derive best-effort ``implements`` (task→code) edges from git history.

This is what makes `impact`/`story_trace` non-empty on real repos that never
hand-annotated a ``files:`` note. It reads commit history through :mod:`git`
(offline, deterministic) and links a Task to a File when a commit whose message
references the task's id (``T<n>``) or its mapped story's id (``US-<n>``) touched
that file.

Every edge is tagged :data:`Confidence.INFERRED` (the weakest tier) so a
consumer never mistakes it for a declared link. Declared ``implements`` edges
(from ``files:`` notes, added earlier in the build) always win — inference never
overwrites an existing edge. If git is unavailable, this is a no-op (AC-1.6).
"""

from __future__ import annotations

from pathlib import Path

from . import git
from .graph import Graph
from .model import Confidence, EdgeType, NodeType, file_id


def infer_implements(graph: Graph, repo_root: str | Path) -> int:
    """Add inferred ``implements`` edges. Returns the number of edges added."""
    if not git.is_git_repo(repo_root):
        return 0

    # Collect each task's id and its mapped story id; query git in one pass.
    task_ids: dict[str, tuple[str | None, str | None]] = {}
    all_ids: set[str] = set()
    for task in graph.nodes(NodeType.TASK):
        tid = task.get("task")
        story_ref = None
        for story_node_id, _ in graph.out_edges(task["id"], EdgeType.MAPS_TO):
            story_ref = graph.get_node(story_node_id).get("story")
        task_ids[task["id"]] = (tid, story_ref)
        if tid:
            all_ids.add(tid)
        if story_ref:
            all_ids.add(story_ref)

    if not all_ids:
        return 0

    touched = git.commits_touching(repo_root, all_ids)
    if not touched:
        return 0

    added = 0
    for task_node_id in sorted(task_ids):
        tid, story_ref = task_ids[task_node_id]
        files: set[str] = set()
        if tid:
            files.update(touched.get(tid, []))
        if story_ref:
            files.update(touched.get(story_ref, []))
        existing = {tgt for tgt, _ in graph.out_edges(task_node_id, EdgeType.IMPLEMENTS)}
        for rel in sorted(files):
            fid = file_id(rel)
            if graph.has_node(fid) and fid not in existing:
                graph.add_edge(task_node_id, fid, EdgeType.IMPLEMENTS, Confidence.INFERRED)
                added += 1
    return added
