"""T6a: the headline hard proof — impact on a real file returns the RIGHT story.

This is the automated, deterministic witness for AC-1.1/AC-1.2 (the exact query
that returns empty in v0.1.0). It uses a git-backed fixture with a realistic,
multi-task id-referencing history and asserts not just non-emptiness but correct
attribution (the file's own story, not another). The real-repo run is a
/demo-day item (T6b), kept out of CI to stay hermetic.
"""

from aspark_graph import queries
from aspark_graph.build import build_graph
from aspark_graph.model import story_id


def _multi_story_repo(root, git_tools):
    git_tools["init"](root)
    spark = root / ".spark" / "shop"
    spark.mkdir(parents=True)
    (spark / "spec.md").write_text(
        "# Spec: shop\n\n| **Status** | `approved` |\n\n## 4. User Stories\n\n"
        "### US-1 (Must): Cart total\n\n"
        "**Acceptance criteria:**\n\n- [ ] AC-1.1: totals correctly.\n\n"
        "### US-2 (Must): Checkout\n\n"
        "**Acceptance criteria:**\n\n- [ ] AC-2.1: checks out.\n"
    )
    (spark / "plan.md").write_text(
        "# Plan: shop\n\n| **Status** | `approved` |\n\n## 3. Task Breakdown\n\n"
        "| # | Task | Story | Depends on | Status | Definition of Done |\n"
        "|---|---|---|---|---|---|\n"
        "| T1 | Cart | US-1 | – | `done` | totals |\n"
        "| T2 | Checkout | US-2 | T1 | `done` | checks out |\n"
    )
    git_tools["commit"](root, "docs: shop trail")
    src = root / "src"
    src.mkdir()
    (src / "cart.py").write_text("def total():\n    return 0\n")
    git_tools["commit"](root, "T1: implement cart (US-1)")
    (src / "checkout.py").write_text("def checkout():\n    return True\n")
    git_tools["commit"](root, "T2: implement checkout (US-2)")
    return root


def test_headline_impact_returns_the_correct_story(tmp_path, git_tools):
    repo = _multi_story_repo(tmp_path, git_tools)
    graph, report = build_graph(repo)

    # AC-1.2: the graph now has implements edges (zero in v0.1.0).
    assert report.inferred_edges >= 2

    # AC-1.1 + attribution: cart.py maps to US-1 only, checkout.py to US-2 only.
    cart = queries.impact(graph, ["src/cart.py"])
    cart_stories = {s["id"] for s in cart["affected_stories"]}
    assert story_id("shop", "US-1") in cart_stories
    assert story_id("shop", "US-2") not in cart_stories

    checkout = queries.impact(graph, ["src/checkout.py"])
    checkout_stories = {s["id"] for s in checkout["affected_stories"]}
    assert story_id("shop", "US-2") in checkout_stories
    assert story_id("shop", "US-1") not in checkout_stories

    # Every affected story here is reached via the inferred tier.
    assert all(s["confidence"] == "inferred" for s in cart["affected_stories"])
