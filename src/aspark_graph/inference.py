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

import re
from pathlib import Path

from . import git
from .graph import Graph
from .model import Confidence, EdgeType, NodeType, file_id

# A touched path like ".spark/<feature>/..." tells us which feature a commit
# belongs to — used to disambiguate colliding task/story ids across features.
_SPARK_FEATURE_RE = re.compile(r"(?:^|/)\.spark/([^/]+)/")


def infer_implements(graph: Graph, repo_root: str | Path) -> int:
    """Add inferred ``implements`` edges from git history. Returns edges added.

    A file is linked to a task when a commit whose message references the task's
    id (or its mapped story's id) touched that file. To avoid cross-feature
    over-attribution when two features reuse the same ``T<n>``/``US<n>``
    numbering (F1), every commit is first resolved to the feature(s) it belongs
    to, and only tasks of those features can match:

    - a commit that touched a ``.spark/<feature>/`` tree belongs to that feature
      (co-touch is authoritative);
    - otherwise the commit's referenced ids must resolve to exactly **one**
      feature (e.g. via a ``T<n> (US<n>)`` pairing that is unique across
      features). If the ids are consistent with two or more features — the
      residual collision case, e.g. a story-only ``(US-1)`` commit that touches
      no ``.spark/`` tree while two features both map a task to ``US-1`` — the
      commit is genuinely ambiguous and contributes **no** edges. An honest
      absence beats an obviously-wrong cross-feature link (AC-1.4).
    """
    if not git.is_git_repo(repo_root):
        return 0

    # task node -> (feature, task_id, story_id); collect the ids to match.
    tasks: dict[str, tuple[str, str | None, str | None]] = {}
    all_ids: set[str] = set()
    for task in graph.nodes(NodeType.TASK):
        tid = task.get("task")
        feature = task.get("feature")
        story_ref = None
        for story_node_id, _ in graph.out_edges(task["id"], EdgeType.MAPS_TO):
            story_ref = graph.get_node(story_node_id).get("story")
        tasks[task["id"]] = (feature, tid, story_ref)
        if tid:
            all_ids.add(tid)
        if story_ref:
            all_ids.add(story_ref)

    records = git.log_records(repo_root)
    if not all_ids or not records:
        return 0
    id_pattern = re.compile(r"\b(" + "|".join(re.escape(i) for i in sorted(all_ids)) + r")\b")

    def _matches(tid_: str | None, story_: str | None, c_tasks: set[str], c_stories: set[str]) -> bool:
        # Semantic pairing: a commit naming BOTH a task id and a story id is
        # about that (task, story) pair, so a task must match on *both* —
        # otherwise the shared id numbering collides with another feature (e.g.
        # commit "T9 (US-3)" is close-the-loop's T9→US-3, not aspark-graph's
        # T9→US-4 nor its US-3-mapped T7). A task-only or story-only commit
        # matches on the id it does name.
        if c_tasks and c_stories:
            return tid_ in c_tasks and story_ in c_stories
        if c_tasks:
            return tid_ in c_tasks
        if c_stories:
            return story_ in c_stories
        return False

    # Pre-compute per commit: the ids it references, and the feature(s) it can
    # be resolved to. Co-touch (a touched .spark/<feature>/ tree) is
    # authoritative; otherwise the ids must resolve to exactly one feature, else
    # the commit is ambiguous and dropped (F1).
    parsed = []
    for rec in records:
        matched = set(id_pattern.findall(rec["message"]))
        if not matched:
            continue
        commit_tasks = {m for m in matched if m.startswith("T")}
        commit_stories = {m for m in matched if m.startswith("US")}
        commit_features = {m.group(1) for f in rec["files"] if (m := _SPARK_FEATURE_RE.search(f))}
        if commit_features:
            resolved = commit_features
        else:
            consistent = {feat for feat, tid_, story_ in tasks.values()
                          if _matches(tid_, story_, commit_tasks, commit_stories)}
            resolved = consistent if len(consistent) == 1 else set()
        if not resolved:
            continue
        parsed.append((commit_tasks, commit_stories, resolved, rec["files"]))

    added = 0
    for task_node_id in sorted(tasks):
        feature, tid, story_ref = tasks[task_node_id]
        files: set[str] = set()
        for commit_tasks, commit_stories, resolved, touched in parsed:
            if feature not in resolved:
                continue
            if not _matches(tid, story_ref, commit_tasks, commit_stories):
                continue
            files.update(touched)
        existing = {tgt for tgt, _ in graph.out_edges(task_node_id, EdgeType.IMPLEMENTS)}
        for rel in sorted(files):
            fid = file_id(rel)
            if graph.has_node(fid) and fid not in existing:
                graph.add_edge(task_node_id, fid, EdgeType.IMPLEMENTS, Confidence.INFERRED)
                added += 1
    return added
