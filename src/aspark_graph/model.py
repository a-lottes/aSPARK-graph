"""Typed node/edge vocabulary, id schemes and the confidence enum.

The graph is a read model: every node has a stable, deterministic id derived
only from its content and location, so two builds of an unchanged repo produce
identical ids (AC-1.2). Nothing here touches the filesystem or the network.
"""

from __future__ import annotations

from enum import Enum


class NodeType(str, Enum):
    # Code layer (extracted by tree-sitter)
    FILE = "File"
    CLASS = "Class"
    FUNCTION = "Function"
    # Artifact layer (parsed from .spark/ templates)
    FEATURE = "Feature"
    STORY = "Story"
    ACCEPTANCE_CRITERION = "AcceptanceCriterion"
    TASK = "Task"
    FINDING = "Finding"
    QA_CHECK = "QACheck"


class EdgeType(str, Enum):
    # Code edges (extracted)
    CONTAINS = "contains"      # File -> Class/Function
    IMPORTS = "imports"        # File -> File
    CALLS = "calls"            # Function -> Function (best-effort, may be absent)
    # Artifact edges (declared)
    HAS_STORY = "has_story"    # Feature -> Story
    HAS_AC = "has_ac"          # Story -> AcceptanceCriterion
    HAS_TASK = "has_task"      # Feature -> Task
    MAPS_TO = "maps_to"        # Task -> Story
    IMPLEMENTS = "implements"  # Task -> File/Function (best-effort)
    VERIFIES = "verifies"      # QACheck -> AcceptanceCriterion
    FOUND_IN = "found_in"      # Finding -> File


class Confidence(str, Enum):
    """Where an edge came from."""

    INFERRED = "inferred"    # self-derived (e.g. from git history) — weakest
    EXTRACTED = "extracted"  # deterministic, from tree-sitter
    DECLARED = "declared"    # from an aSPARK artifact

    def rank(self) -> int:
        """Higher = stronger. Used to pick the *weakest* edge on a path."""
        return {Confidence.INFERRED: 0, Confidence.EXTRACTED: 1, Confidence.DECLARED: 2}[self]


# --- Id schemes ------------------------------------------------------------
# Ids are prefixed by kind so lookups and `find_nodes` can filter cheaply, and
# so ids never collide across layers.


def file_id(relpath: str) -> str:
    return f"file:{relpath}"


def definition_id(relpath: str, qualname: str) -> str:
    """A class/function/method, qualified within its file (e.g. ``Foo.bar``)."""
    return f"def:{relpath}::{qualname}"


def feature_id(name: str) -> str:
    return f"feature:{name}"


def story_id(feature: str, story: str) -> str:
    return f"story:{feature}:{story}"


def ac_id(feature: str, ac: str) -> str:
    return f"ac:{feature}:{ac}"


def task_id(feature: str, task: str) -> str:
    return f"task:{feature}:{task}"


def finding_id(feature: str, finding: str) -> str:
    return f"finding:{feature}:{finding}"


def qacheck_id(feature: str, ac: str, index: int) -> str:
    return f"qa:{feature}:{ac}#{index}"
