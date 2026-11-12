from aspark_graph.artifacts import _all_tables


def test_all_tables_reads_every_table():
    block = [
        "### US-1", "| AC | Result |", "|---|---|", "| AC-1.1 | ✅ |", "",
        "### US-2", "| AC | Result |", "|---|---|", "| AC-2.1 | ✅ |",
    ]
    tables = _all_tables(block)
    assert [t["rows"][0]["ac"] for t in tables] == ["AC-1.1", "AC-2.1"]
