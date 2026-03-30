"""
Structure validation tests for SDR LinkedIn Monitor Agent (Use Case #58).

These tests validate the agent's graph structure, node/edge integrity, and
package imports without requiring any API keys (MOCK_MODE=1).
"""

import json
import os
import pytest

# ---------------------------------------------------------------------------
# Module-level skip for real-credential tests — structure tests skip in CI
# ---------------------------------------------------------------------------
pytestmark = pytest.mark.skipif(
    os.environ.get("MOCK_MODE") != "1" and not os.environ.get("ANTHROPIC_API_KEY"),
    reason=(
        "Set ANTHROPIC_API_KEY for live tests or MOCK_MODE=1 for structure validation."
    ),
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def agent():
    """Return the default agent instance."""
    from sdr_linkedin_monitor import default_agent

    return default_agent


@pytest.fixture(scope="module")
def agent_module():
    """Return the full agent module for graph inspection."""
    import sdr_linkedin_monitor.agent as agent_mod

    return agent_mod


# ---------------------------------------------------------------------------
# Import & instantiation
# ---------------------------------------------------------------------------


def test_package_imports():
    """Agent package can be imported without errors."""
    from sdr_linkedin_monitor import (
        SdrLinkedinMonitorAgent,
        default_agent,
        goal,
        nodes,
        edges,
        metadata,
    )

    assert SdrLinkedinMonitorAgent is not None
    assert default_agent is not None
    assert goal is not None
    assert nodes is not None
    assert edges is not None
    assert metadata is not None


def test_default_agent_instantiates():
    """default_agent is a SdrLinkedinMonitorAgent instance."""
    from sdr_linkedin_monitor import default_agent, SdrLinkedinMonitorAgent

    assert isinstance(default_agent, SdrLinkedinMonitorAgent)


# ---------------------------------------------------------------------------
# Graph validation
# ---------------------------------------------------------------------------


def test_agent_validates(agent):
    """validate() reports no structural errors."""
    result = agent.validate()
    assert result["valid"] is True, f"Agent validation failed: {result['errors']}"


def test_node_count(agent):
    """Agent has exactly 5 nodes."""
    assert len(agent.nodes) == 5


def test_edge_count(agent):
    """Agent has exactly 4 edges (linear pipeline)."""
    assert len(agent.edges) == 4


def test_node_ids(agent):
    """All expected node IDs are present."""
    node_ids = {n.id for n in agent.nodes}
    expected = {
        "intake",
        "linkedin-monitor",
        "email-lookup",
        "email-drafter",
        "queue-review",
    }
    assert node_ids == expected, f"Node ID mismatch: {node_ids}"


def test_entry_node(agent):
    """Entry node is 'intake'."""
    assert agent.entry_node == "intake"


def test_entry_points_format(agent):
    """entry_points follows the required {start: node-id} format."""
    assert agent.entry_points == {"start": "intake"}


def test_terminal_node(agent):
    """Terminal node is 'queue-review'."""
    assert agent.terminal_nodes == ["queue-review"]


def test_all_edges_reference_valid_nodes(agent):
    """Every edge source and target references a known node ID."""
    node_ids = {n.id for n in agent.nodes}
    for edge in agent.edges:
        assert edge.source in node_ids, (
            f"Edge {edge.id}: source '{edge.source}' not in nodes"
        )
        assert edge.target in node_ids, (
            f"Edge {edge.id}: target '{edge.target}' not in nodes"
        )


# ---------------------------------------------------------------------------
# Client-facing node checks
# ---------------------------------------------------------------------------


def test_client_facing_nodes(agent):
    """Exactly intake and queue-review are client-facing."""
    cf_ids = {n.id for n in agent.nodes if n.client_facing}
    assert cf_ids == {"intake", "queue-review"}, (
        f"Unexpected client-facing nodes: {cf_ids}"
    )


def test_autonomous_nodes_not_client_facing(agent):
    """linkedin-monitor, email-lookup, and email-drafter are not client-facing."""
    autonomous = {"linkedin-monitor", "email-lookup", "email-drafter"}
    for node in agent.nodes:
        if node.id in autonomous:
            assert not node.client_facing, (
                f"Node '{node.id}' should not be client-facing"
            )


# ---------------------------------------------------------------------------
# Tool references
# ---------------------------------------------------------------------------


def test_linkedin_monitor_uses_exa_tools(agent):
    """linkedin-monitor node uses exa_search and exa_get_contents."""
    monitor = next(n for n in agent.nodes if n.id == "linkedin-monitor")
    assert "exa_search" in monitor.tools
    assert "exa_get_contents" in monitor.tools


def test_email_lookup_uses_exa_tools(agent):
    """email-lookup node uses exa_search and exa_get_contents."""
    lookup = next(n for n in agent.nodes if n.id == "email-lookup")
    assert "exa_search" in lookup.tools
    assert "exa_get_contents" in lookup.tools


def test_email_drafter_uses_save_data(agent):
    """email-drafter node uses save_data to persist draft queue."""
    drafter = next(n for n in agent.nodes if n.id == "email-drafter")
    assert "save_data" in drafter.tools


def test_queue_review_uses_file_tools(agent):
    """queue-review node uses save_data, append_data, and serve_file_to_user."""
    review = next(n for n in agent.nodes if n.id == "queue-review")
    for tool in ["save_data", "append_data", "serve_file_to_user"]:
        assert tool in review.tools, f"queue-review is missing tool: {tool}"


def test_intake_node_has_no_tools(agent):
    """intake node requires no tools (client-facing, HITL only)."""
    intake = next(n for n in agent.nodes if n.id == "intake")
    assert intake.tools == [] or intake.tools is None


# ---------------------------------------------------------------------------
# Goal & constraint checks
# ---------------------------------------------------------------------------


def test_goal_id(agent):
    """Goal ID matches expected value."""
    assert agent.goal.id == "sdr-linkedin-monitor"


def test_success_criteria_count(agent):
    """Agent goal has 4 success criteria."""
    assert len(agent.goal.success_criteria) == 4


def test_success_criteria_weights_sum_to_one(agent):
    """Success criteria weights sum to 1.0."""
    total = sum(sc.weight for sc in agent.goal.success_criteria)
    assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, expected 1.0"


def test_hard_constraints(agent):
    """Agent has at least two hard constraints (no-fabrication and no-send)."""
    hard = [c for c in agent.goal.constraints if c.constraint_type == "hard"]
    hard_ids = {c.id for c in hard}
    assert "c-no-fabrication" in hard_ids
    assert "c-no-send" in hard_ids
    assert "c-quota-cap" in hard_ids


# ---------------------------------------------------------------------------
# Data flow checks
# ---------------------------------------------------------------------------


def test_intake_output_keys(agent):
    """intake node produces icp_config, daily_quota, pitch_copy."""
    intake = next(n for n in agent.nodes if n.id == "intake")
    assert set(intake.output_keys) == {"icp_config", "daily_quota", "pitch_copy"}


def test_linkedin_monitor_input_keys(agent):
    """linkedin-monitor receives icp_config and daily_quota from intake."""
    monitor = next(n for n in agent.nodes if n.id == "linkedin-monitor")
    assert "icp_config" in monitor.input_keys
    assert "daily_quota" in monitor.input_keys


def test_queue_review_input_keys(agent):
    """queue-review receives drafted_emails from email-drafter."""
    review = next(n for n in agent.nodes if n.id == "queue-review")
    assert "drafted_emails" in review.input_keys


# ---------------------------------------------------------------------------
# Info method
# ---------------------------------------------------------------------------


def test_info_method(agent):
    """info() returns a dict with required keys."""
    info = agent.info()
    for key in [
        "name",
        "version",
        "description",
        "goal",
        "nodes",
        "edges",
        "entry_node",
        "terminal_nodes",
        "client_facing_nodes",
    ]:
        assert key in info, f"Missing key in info(): {key}"
    assert info["name"] == "SDR LinkedIn Monitor"
    assert info["entry_node"] == "intake"
    assert "queue-review" in info["terminal_nodes"]


# ---------------------------------------------------------------------------
# Agent.json consistency
# ---------------------------------------------------------------------------


def test_agent_json_exists():
    """agent.json exists alongside the package."""
    from pathlib import Path
    import sdr_linkedin_monitor

    pkg_dir = Path(sdr_linkedin_monitor.__file__).parent
    agent_json = pkg_dir / "agent.json"
    assert agent_json.exists(), "agent.json not found in package directory"


def test_agent_json_parses():
    """agent.json can be parsed as valid JSON."""
    from pathlib import Path
    import sdr_linkedin_monitor

    pkg_dir = Path(sdr_linkedin_monitor.__file__).parent
    agent_json = pkg_dir / "agent.json"
    data = json.loads(agent_json.read_text())
    assert data["agent"]["id"] == "sdr_linkedin_monitor"
    assert data["metadata"]["node_count"] == 5
    assert data["metadata"]["edge_count"] == 4
