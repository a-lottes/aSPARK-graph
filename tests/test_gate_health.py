"""T12: gate_health — AC-6.1 (orphan tasks), AC-6.2 (unverified ACs), AC-6.3 (open findings)."""

from aspark_graph import queries
from aspark_graph.model import ac_id, finding_id, task_id


def test_ac_6_1_orphan_task_listed(sample_graph):
    graph, _ = sample_graph
    r = queries.gate_health(graph, "demo")
    assert r["found"] is True
    orphan_ids = {t["id"] for t in r["orphan_tasks"]}
    assert task_id("demo", "T3") in orphan_ids  # T3 maps to no story
    # T1 and T2 map to stories -> not orphans
    assert task_id("demo", "T1") not in orphan_ids
    assert task_id("demo", "T2") not in orphan_ids


def test_ac_6_2_unverified_ac_listed(sample_graph):
    graph, _ = sample_graph
    r = queries.gate_health(graph, "demo")
    unverified = {a["id"] for a in r["unverified_acs"]}
    # AC-2.1 only has a failing QA record -> unverified
    assert ac_id("demo", "AC-2.1") in unverified
    # AC-1.1 passed QA -> verified
    assert ac_id("demo", "AC-1.1") not in unverified


def test_ac_6_3_open_finding_listed(sample_graph):
    graph, _ = sample_graph
    r = queries.gate_health(graph, "demo")
    open_ids = {f["id"] for f in r["open_findings"]}
    assert finding_id("demo", "F1") in open_ids  # status open
    assert finding_id("demo", "F2") not in open_ids  # status fixed


def test_healthy_flag_and_unknown_feature(sample_graph):
    graph, _ = sample_graph
    r = queries.gate_health(graph, "demo")
    assert r["healthy"] is False  # demo has orphans/unverified/open findings

    missing = queries.gate_health(graph, "does-not-exist")
    assert missing["found"] is False
    assert missing["reason"] == "not_found"
