"""aSPARK ``.spark/`` artifact parser — the crown jewel.

Parses the five aSPARK templates (spec / plan / review / qa / release) into the
graph's artifact layer and links them with *declared* edges. It is pinned to a
supported template shape and **fails loudly on drift** (AC-1.3): a structurally
malformed artifact raises :class:`TemplateDriftError` naming the file and the
mismatch — it never silently skips or guesses.

Deterministic and offline. Feature directories and rows are processed in sorted
order so the artifact layer is byte-stable like the code layer (AC-1.2).
"""

from __future__ import annotations

import re
from pathlib import Path

from .graph import Graph
from .model import (
    Confidence,
    EdgeType,
    NodeType,
    ac_id,
    feature_id,
    file_id,
    finding_id,
    qacheck_id,
    story_id,
    task_id,
)

# The template shape this parser understands. There is no version string in the
# artifacts themselves, so drift is detected structurally against this pin.
SUPPORTED_TEMPLATE = "aspark/0.1.0"

_SPARK_DIRNAME = ".spark"

# Review, QA and release each exist under two names: the one aSPARK Core's
# ceremonies write today, and the legacy one its templates (and older trails) use.
# Resolved per artifact: the current name wins; a shadowed legacy file is
# reported by the build, never merged (current-artifact-names US-4).
_ARTIFACT_NAMES = (
    ("review", "review.md", "review-report.md"),
    ("qa", "qa.md", "qa-report.md"),
    ("release", "release.md", "release-notes.md"),
)
# For build output: which current name shadows a given legacy name.
CURRENT_NAME_FOR = {legacy: current for _, current, legacy in _ARTIFACT_NAMES}

_STORY_RE = re.compile(r"^###\s+(US-\d+)\s*\(([^)]*)\)\s*:\s*(.+?)\s*$")
_STORY_ANY_RE = re.compile(r"^###\s+US-", re.IGNORECASE)
_AC_RE = re.compile(r"^\s*-\s*\[[ xX]?\]\s*(AC-\d+\.\d+)\s*:\s*(.+?)\s*$")
_US_REF_RE = re.compile(r"(US-\d+)")
_FILES_NOTE_RE = re.compile(r"files:\s*([^|]+)", re.IGNORECASE)
_LOCATION_RE = re.compile(r"([\w./\-]+?\.[A-Za-z0-9]+)(?::(\d+))?")


class TemplateDriftError(Exception):
    """A ``.spark/`` artifact does not match the supported template (AC-1.3)."""

    def __init__(self, file: str, mismatch: str) -> None:
        self.file = file
        self.mismatch = mismatch
        super().__init__(f"template drift in {file}: {mismatch} (supported: {SUPPORTED_TEMPLATE})")


# --- public entry point ----------------------------------------------------

def extract_features(repo_root: Path, graph: Graph, shadowed: list[str] | None = None) -> int:
    """Parse every ``.spark/<feature>/`` trail into ``graph``. Returns node count.

    If ``shadowed`` is given, every legacy artifact file ignored because its
    current name exists is appended to it as ``.spark/<feature>/<name>``, in
    feature order and then review, qa, release — never written to the graph."""
    spark = Path(repo_root) / _SPARK_DIRNAME
    if not spark.is_dir():
        return 0
    added = 0
    for feature_dir in sorted(p for p in spark.iterdir() if p.is_dir()):
        added += _parse_feature(feature_dir, graph, shadowed)
    return added


def _resolve(feature_dir: Path, current: str, legacy: str, shadowed: list[str] | None) -> Path | None:
    """The file to read for one artifact kind: the current name if it exists
    (recording a legacy file it shadows), else the legacy name, else None.
    Paths are only ever ``feature_dir / <literal from _ARTIFACT_NAMES>``."""
    current_path = feature_dir / current
    legacy_path = feature_dir / legacy
    if current_path.exists():
        if legacy_path.exists() and shadowed is not None:
            shadowed.append(f"{_SPARK_DIRNAME}/{feature_dir.name}/{legacy}")
        return current_path
    return legacy_path if legacy_path.exists() else None


def _parse_feature(feature_dir: Path, graph: Graph, shadowed: list[str] | None = None) -> int:
    feature = feature_dir.name
    fid = feature_id(feature)
    added = 0

    statuses: dict[str, str | None] = {}
    version: str | None = None

    spec = feature_dir / "spec.md"
    plan = feature_dir / "plan.md"
    review, qa, release = (
        _resolve(feature_dir, current, legacy, shadowed) for _, current, legacy in _ARTIFACT_NAMES
    )

    graph.add_node(fid, NodeType.FEATURE, name=feature)
    added += 1

    if spec.exists():
        statuses["spec"] = _status(spec)
        added += _parse_spec(spec, feature, fid, graph)
    if plan.exists():
        statuses["plan"] = _status(plan)
        added += _parse_plan(plan, feature, fid, graph)
    if review is not None:
        statuses["review"] = _status(review)
        added += _parse_review(review, feature, graph)
    if qa is not None:
        statuses["qa"] = _status(qa)
        added += _parse_qa(qa, feature, graph)
    if release is not None:
        statuses["release"] = _status(release)
        version = _release_version(release)

    # Coverage statement (issue #61): a verdict is only honest over the files
    # that actually parsed. Record what was seen, what was skipped, and what
    # looked like an artifact but wasn't recognized (near-miss filenames).
    recognized = [p.name for p in (spec, plan, review, qa, release) if p.exists()]
    near_misses: list[str] = []
    expected = {"spec.md", "plan.md", "review-report.md", "qa-report.md", "release-notes.md"}
    for other in feature_dir.glob("*.md"):
        if other.name in expected:
            continue
        stem = other.name.rsplit(".", 1)[0].lower().replace("_", "-")
        if any(k in stem for k in ("spec", "plan", "review", "qa", "release")):
            near_misses.append(other.name)

    # Stamp phase statuses onto the Feature node (feeds gate_health / a board).
    graph.add_node(
        fid, NodeType.FEATURE, name=feature,
        spec_status=statuses.get("spec"), plan_status=statuses.get("plan"),
        review_status=statuses.get("review"), qa_status=statuses.get("qa"),
        release_status=statuses.get("release"), version=version,
        coverage={
            "recognized": sorted(recognized),
            "skipped": sorted(expected - set(recognized)),
            "near_misses": sorted(near_misses),
        },
    )
    return added


# --- per-artifact parsers --------------------------------------------------

def _parse_spec(path: Path, feature: str, fid: str, graph: Graph) -> int:
    lines = _read(path).splitlines()
    section = _section(lines, "user stories")
    if section is None:
        raise TemplateDriftError(str(path), "missing a '## … User Stories' section")

    added = 0
    current_story: str | None = None
    saw_story = False
    for line in section:
        if _STORY_ANY_RE.match(line):
            m = _STORY_RE.match(line)
            if not m:
                raise TemplateDriftError(
                    str(path),
                    f"user-story heading not in 'US-n (MoSCoW): title' form: {line.strip()!r}",
                )
            us, moscow, title = m.group(1), m.group(2).strip(), m.group(3).strip()
            current_story = story_id(feature, us)
            graph.add_node(
                current_story, NodeType.STORY,
                story=us, title=title, moscow=_moscow(moscow), feature=feature,
            )
            graph.add_edge(fid, current_story, EdgeType.HAS_STORY, Confidence.DECLARED)
            added += 1
            saw_story = True
            continue
        m = _AC_RE.match(line)
        if m and current_story is not None:
            ac, text = m.group(1), m.group(2).strip()
            aid = ac_id(feature, ac)
            graph.add_node(aid, NodeType.ACCEPTANCE_CRITERION, ac=ac, text=text, feature=feature, story=current_story)
            graph.add_edge(current_story, aid, EdgeType.HAS_AC, Confidence.DECLARED)
            added += 1

    if not saw_story:
        raise TemplateDriftError(str(path), "no user stories (US-n) found in the User Stories section")
    return added


def _parse_plan(path: Path, feature: str, fid: str, graph: Graph) -> int:
    lines = _read(path).splitlines()
    section = _section(lines, "task breakdown")
    if section is None:
        raise TemplateDriftError(str(path), "missing a '## … Task Breakdown' section")
    table = _first_table(section)
    if table is None:
        raise TemplateDriftError(str(path), "Task Breakdown section has no task table")
    header = {k.lower() for k in table["header"]}
    for required in ("task", "story", "status"):
        if not any(required in h for h in header):
            raise TemplateDriftError(str(path), f"task table missing a '{required}' column (found {sorted(header)})")

    added = 0
    for row in table["rows"]:
        tid_raw = _col(row, "#")
        if not tid_raw or not re.match(r"^T\d+$", tid_raw):
            continue  # placeholder / non-task row
        node_id = task_id(feature, tid_raw)
        story_cell = _col(row, "story")
        status = _strip_ticks(_col(row, "status"))
        dod = _col(row, "definition of done") or _col(row, "definition")
        graph.add_node(
            node_id, NodeType.TASK,
            task=tid_raw, status=status, dod=dod, feature=feature, story_ref=story_cell,
        )
        graph.add_edge(fid, node_id, EdgeType.HAS_TASK, Confidence.DECLARED)
        added += 1
        m = _US_REF_RE.search(story_cell or "")
        if m:
            target = story_id(feature, m.group(1))
            if graph.has_node(target):
                graph.add_edge(node_id, target, EdgeType.MAPS_TO, Confidence.DECLARED)
        # Best-effort implements (Q1): only where an explicit `files:` note exists
        # in the task row and resolves to a real File node. No template change.
        for rel in _files_note(dod):
            if graph.has_node(file_id(rel)):
                graph.add_edge(node_id, file_id(rel), EdgeType.IMPLEMENTS, Confidence.DECLARED)
    return added


def _parse_review(path: Path, feature: str, graph: Graph) -> int:
    lines = _read(path).splitlines()
    section = _section(lines, "findings")
    if section is None:
        raise TemplateDriftError(str(path), "missing a '## … Findings' section")
    table = _first_table(section)
    if table is None:
        return 0  # a review with no findings table logged is not drift
    header = {k.lower() for k in table["header"]}
    for required in ("severity", "location", "status"):
        if not any(required in h for h in header):
            raise TemplateDriftError(str(path), f"findings table missing a '{required}' column (found {sorted(header)})")

    added = 0
    for row in table["rows"]:
        fid_raw = _col(row, "#")
        if not fid_raw or not re.match(r"^F\d+$", fid_raw):
            continue
        node_id = finding_id(feature, fid_raw)
        location = _strip_ticks(_col(row, "location"))
        graph.add_node(
            node_id, NodeType.FINDING,
            finding=fid_raw, severity=_col(row, "severity"),
            location=location, status=_strip_ticks(_col(row, "status")), feature=feature,
        )
        added += 1
        rel = _location_file(location)
        if rel and graph.has_node(file_id(rel)):
            graph.add_edge(node_id, file_id(rel), EdgeType.FOUND_IN, Confidence.DECLARED)
    return added


def _parse_qa(path: Path, feature: str, graph: Graph) -> int:
    lines = _read(path).splitlines()
    section = _section(lines, "acceptance criteria verification")
    if section is None:
        raise TemplateDriftError(str(path), "missing a '## … Acceptance Criteria Verification' section")
    table = _first_table(section, unescape_pipes=True)
    if table is None:
        return 0
    header = {k.lower() for k in table["header"]}
    id_col = _qa_id_column(table["header"])
    if id_col is None:
        raise TemplateDriftError(str(path), f"QA table missing an 'AC' or 'Spec ID' column (found {sorted(header)})")
    if not any("result" in h for h in header):
        raise TemplateDriftError(str(path), f"QA table missing a 'Result' column (found {sorted(header)})")

    added = 0
    for index, row in enumerate(table["rows"]):
        ac_cell = _col(row, id_col)
        m = re.search(r"(AC-\d+\.\d+)", ac_cell or "")
        if not m:
            continue
        ac = m.group(1)
        result = _normalise_result(_col(row, "result"))
        node_id = qacheck_id(feature, ac, index)
        graph.add_node(
            node_id, NodeType.QA_CHECK,
            ac=ac, result=result, date=_col(row, "date"), feature=feature, order=index,
        )
        target = ac_id(feature, ac)
        if graph.has_node(target):
            graph.add_edge(node_id, target, EdgeType.VERIFIES, Confidence.DECLARED)
        added += 1
    return added


def _qa_id_column(header: list[str]) -> str | None:
    """The QA table's id column, chosen by header in a fixed order: ``AC`` (legacy
    template), ``Spec ID`` (Core's current template), then v0.7.0's looser
    ``AC…`` prefix rule. ``Spec ID`` is checked before the prefix rule so a column
    such as ``Actual`` can never capture the id. None means template drift."""
    cells = [h.strip().lower() for h in header]
    if "ac" in cells:
        return "ac"
    if "spec id" in cells:
        return "spec id"
    if any(h.startswith("ac") for h in cells):
        return "ac"
    return None


# --- markdown helpers ------------------------------------------------------

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _status(path: Path) -> str | None:
    m = re.search(r"\|\s*\*\*Status\*\*\s*\|\s*([^|]+?)\s*\|", _read(path))
    return _strip_ticks(m.group(1)) if m else None


def _release_version(path: Path) -> str | None:
    m = re.search(r"\|\s*\*\*Version\*\*\s*\|\s*([^|]+?)\s*\|", _read(path))
    return _strip_ticks(m.group(1)) if m else None


def _section(lines: list[str], keyword: str) -> list[str] | None:
    """Lines under a ``##`` heading containing ``keyword`` until the next ``#``/``##``."""
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^##\s", line) and keyword.lower() in line.lower():
            start = i + 1
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start, len(lines)):
        if re.match(r"^#{1,2}\s", lines[j]):
            end = j
            break
    return lines[start:end]


def _first_table(block: list[str], unescape_pipes: bool = False) -> dict | None:
    """First markdown pipe-table in ``block`` as {header: [...], rows: [{col: val}]}."""
    rows: list[list[str]] = []
    in_table = False
    for line in block:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            rows.append(_split_row(stripped, unescape_pipes))
            in_table = True
        elif in_table:
            break  # table ended
    if len(rows) < 2:
        return None
    header = rows[0]
    # rows[1] is the |---|---| separator
    if not all(set(cell) <= set("-: ") for cell in rows[1]):
        # No separator row → not a real table shape
        return None
    data = []
    for raw in rows[2:]:
        cells = raw + [""] * (len(header) - len(raw))
        data.append({header[i].lower(): cells[i] for i in range(len(header))})
    return {"header": header, "rows": data}


def _split_row(line: str, unescape_pipes: bool = False) -> list[str]:
    if not unescape_pipes:
        inner = line.strip().strip("|")
        return [c.strip() for c in inner.split("|")]
    # GFM: an escaped pipe belongs to its cell and is stored as a plain "|".
    # An escaped pipe right before the closing one is cell content, not border.
    inner = re.sub(r"(?<!\\)\|+$", "", line.strip().lstrip("|"))
    return [c.replace("\\|", "|").strip() for c in re.split(r"(?<!\\)\|", inner)]


def _col(row: dict, name: str) -> str:
    name = name.lower()
    if name in row:
        return row[name]
    for k, v in row.items():
        if name in k:
            return v
    return ""


def _strip_ticks(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip().strip("`").strip()


def _moscow(value: str) -> str:
    return value.strip().split()[0].rstrip(",") if value.strip() else ""


def _normalise_result(cell: str) -> str:
    # An explicit marker is the verdict; the words after it only explain it
    # ("⚠️ not capturable — never claimed as passed" is not a pass).
    cell = cell or ""
    if "❌" in cell:
        return "fail"
    if "⚠" in cell:
        return "unknown"
    if "✅" in cell:
        return "pass"
    low = cell.lower()
    if re.search(r"\bpass(ed|es|ing)?\b", low):
        return "pass"
    if re.search(r"\bfail(ed|s|ing|ure)?\b", low):
        return "fail"
    return "unknown"


def _files_note(dod: str | None) -> list[str]:
    """Extract paths from an optional inline ``files: a.py, b.py`` note (Q1)."""
    if not dod:
        return []
    m = _FILES_NOTE_RE.search(dod)
    if not m:
        return []
    return [tok.strip().strip("`") for tok in re.split(r"[,\s]+", m.group(1)) if tok.strip()]


def _location_file(location: str | None) -> str | None:
    if not location:
        return None
    m = _LOCATION_RE.search(location)
    return m.group(1) if m else None
