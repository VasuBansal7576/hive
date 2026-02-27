"""Structure tests for modern RSS-to-Twitter template."""

from rss_twitter_agent.agent import default_agent


def test_graph_nodes_present() -> None:
    node_ids = {n.id for n in default_agent.nodes}
    assert {"fetch", "process", "generate", "approve", "post", "complete"}.issubset(node_ids)


def test_validation_passes() -> None:
    result = default_agent.validate()
    assert result["valid"] is True
