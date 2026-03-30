"""Agent graph construction for SDR LinkedIn Monitor Agent."""

from typing import Any, TYPE_CHECKING
from pathlib import Path

from framework.graph import (
    EdgeSpec,
    EdgeCondition,
    Goal,
    SuccessCriterion,
    Constraint,
    NodeSpec,
)
from framework.graph.edge import GraphSpec
from framework.graph.executor import ExecutionResult, GraphExecutor
from framework.runtime.event_bus import EventBus
from framework.runtime.core import Runtime
from framework.llm import LiteLLMProvider
from framework.runner.tool_registry import ToolRegistry

from .config import default_config, metadata, RuntimeConfig
from .nodes import (
    intake_node,
    linkedin_monitor_node,
    email_lookup_node,
    email_drafter_node,
    queue_review_node,
)

if TYPE_CHECKING:
    from framework.config import RuntimeConfig

# Goal definition
goal: Goal = Goal(
    id="sdr-linkedin-monitor",
    name="SDR LinkedIn Monitor",
    description=(
        "Monitor LinkedIn for 'I'm hiring' and 'Just started a new role' posts "
        "from VP of Engineering and CTO titles at Series B+ companies, look up "
        "their verified corporate email, draft a highly personalized cold email "
        "for each, and queue up to 50 per day for SDR review."
    ),
    success_criteria=[
        SuccessCriterion(
            id="sc-signal-detection",
            description=(
                "Finds qualifying LinkedIn posts matching target titles and "
                "company stage filters"
            ),
            metric="qualified_leads_found",
            target=">=1",
            weight=0.25,
        ),
        SuccessCriterion(
            id="sc-email-lookup",
            description=("Attempts corporate email lookup for every qualified lead"),
            metric="email_lookup_attempted",
            target="true",
            weight=0.20,
        ),
        SuccessCriterion(
            id="sc-personalization",
            description=(
                "Every drafted email references a specific, verified detail "
                "about the lead's company (product launch, blog post, or milestone)"
            ),
            metric="emails_personalized",
            target="true",
            weight=0.30,
        ),
        SuccessCriterion(
            id="sc-queue-delivered",
            description=(
                "User receives a downloadable HTML report with all drafted emails"
            ),
            metric="queue_delivered",
            target="true",
            weight=0.25,
        ),
    ],
    constraints=[
        Constraint(
            id="c-no-fabrication",
            description=(
                "Never fabricate leads, email addresses, or company details — "
                "only report what was found from real sources"
            ),
            constraint_type="hard",
            category="quality",
        ),
        Constraint(
            id="c-quota-cap",
            description="Respect the daily quota — never exceed 50 emails per run",
            constraint_type="hard",
            category="scope",
        ),
        Constraint(
            id="c-no-send",
            description=("Never send any email — only draft for human review"),
            constraint_type="hard",
            category="safety",
        ),
        Constraint(
            id="c-professional-tone",
            description=(
                "All drafted emails must be professional, genuine, and under 120 words"
            ),
            constraint_type="soft",
            category="quality",
        ),
    ],
)

# Node list
nodes: list[NodeSpec] = [
    intake_node,
    linkedin_monitor_node,
    email_lookup_node,
    email_drafter_node,
    queue_review_node,
]

# Edge definitions
edges: list[EdgeSpec] = [
    EdgeSpec(
        id="intake-to-linkedin-monitor",
        source="intake",
        target="linkedin-monitor",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="linkedin-monitor-to-email-lookup",
        source="linkedin-monitor",
        target="email-lookup",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="email-lookup-to-email-drafter",
        source="email-lookup",
        target="email-drafter",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="email-drafter-to-queue-review",
        source="email-drafter",
        target="queue-review",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
]

# Graph configuration
entry_node: str = "intake"
entry_points: dict[str, str] = {"start": "intake"}
pause_nodes: list[str] = []
terminal_nodes: list[str] = ["queue-review"]


class SdrLinkedinMonitorAgent:
    """
    SDR LinkedIn Monitor Agent — 5-node linear pipeline.

    Flow: intake → linkedin-monitor → email-lookup → email-drafter → queue-review
    """

    def __init__(self, config: RuntimeConfig | None = None) -> None:
        """
        Initialize the SDR LinkedIn Monitor Agent.

        Args:
            config: Optional runtime configuration. Defaults to default_config.
        """
        self.config = config or default_config
        self.goal = goal
        self.nodes = nodes
        self.edges = edges
        self.entry_node = entry_node
        self.entry_points = entry_points
        self.pause_nodes = pause_nodes
        self.terminal_nodes = terminal_nodes
        self._executor: GraphExecutor | None = None
        self._graph: GraphSpec | None = None
        self._event_bus: EventBus | None = None
        self._tool_registry: ToolRegistry | None = None

    def _build_graph(self) -> GraphSpec:
        """Build the GraphSpec for the SDR LinkedIn Monitor workflow."""
        return GraphSpec(
            id="sdr-linkedin-monitor-graph",
            goal_id=self.goal.id,
            version="1.0.0",
            entry_node=self.entry_node,
            entry_points=self.entry_points,
            terminal_nodes=self.terminal_nodes,
            pause_nodes=self.pause_nodes,
            nodes=self.nodes,
            edges=self.edges,
            default_model=self.config.model,
            max_tokens=self.config.max_tokens,
            loop_config={
                "max_iterations": 100,
                "max_tool_calls_per_turn": 30,
                "max_history_tokens": 32000,
            },
        )

    def _setup(self) -> GraphExecutor:
        """Set up the executor with all components (runtime, LLM, tools)."""
        storage_path = Path.home() / ".hive" / "agents" / "sdr_linkedin_monitor"
        storage_path.mkdir(parents=True, exist_ok=True)

        self._event_bus = EventBus()
        self._tool_registry = ToolRegistry()

        mcp_config_path = Path(__file__).parent / "mcp_servers.json"
        if mcp_config_path.exists():
            self._tool_registry.load_mcp_config(mcp_config_path)

        llm = LiteLLMProvider(
            model=self.config.model,
            api_key=self.config.api_key,
            api_base=self.config.api_base,
        )

        tool_executor = self._tool_registry.get_executor()
        tools = list(self._tool_registry.get_tools().values())

        self._graph = self._build_graph()
        runtime = Runtime(storage_path)

        self._executor = GraphExecutor(
            runtime=runtime,
            llm=llm,
            tools=tools,
            tool_executor=tool_executor,
            event_bus=self._event_bus,
            storage_path=storage_path,
            loop_config=self._graph.loop_config,
        )

        return self._executor

    async def start(self) -> None:
        """Set up the agent (initialize executor and tools)."""
        if self._executor is None:
            self._setup()

    async def stop(self) -> None:
        """Clean up resources."""
        self._executor = None
        self._event_bus = None

    async def trigger_and_wait(
        self,
        entry_point: str,
        input_data: dict[str, Any],
        timeout: float | None = None,
        session_state: dict[str, Any] | None = None,
    ) -> ExecutionResult | None:
        """Execute the graph and wait for completion."""
        if self._executor is None:
            raise RuntimeError("Agent not started. Call start() first.")
        if self._graph is None:
            raise RuntimeError("Graph not built. Call start() first.")

        return await self._executor.execute(
            graph=self._graph,
            goal=self.goal,
            input_data=input_data,
            session_state=session_state,
        )

    async def run(
        self, context: dict[str, Any], session_state: dict[str, Any] | None = None
    ) -> ExecutionResult:
        """Run the agent (convenience method for single execution)."""
        await self.start()
        try:
            result = await self.trigger_and_wait(
                "start", context, session_state=session_state
            )
            return result or ExecutionResult(success=False, error="Execution timeout")
        finally:
            await self.stop()

    def info(self) -> dict[str, Any]:
        """Get agent information for introspection."""
        return {
            "name": metadata.name,
            "version": metadata.version,
            "description": metadata.description,
            "goal": {
                "name": self.goal.name,
                "description": self.goal.description,
            },
            "nodes": [n.id for n in self.nodes],
            "edges": [e.id for e in self.edges],
            "entry_node": self.entry_node,
            "entry_points": self.entry_points,
            "pause_nodes": self.pause_nodes,
            "terminal_nodes": self.terminal_nodes,
            "client_facing_nodes": [n.id for n in self.nodes if n.client_facing],
        }

    def validate(self) -> dict[str, Any]:
        """Validate agent structure for cycles, missing nodes, or invalid edges."""
        errors = []
        warnings = []

        node_ids = {node.id for node in self.nodes}
        for edge in self.edges:
            if edge.source not in node_ids:
                errors.append(f"Edge {edge.id}: source '{edge.source}' not found")
            if edge.target not in node_ids:
                errors.append(f"Edge {edge.id}: target '{edge.target}' not found")

        if self.entry_node not in node_ids:
            errors.append(f"Entry node '{self.entry_node}' not found")

        for terminal in self.terminal_nodes:
            if terminal not in node_ids:
                errors.append(f"Terminal node '{terminal}' not found")

        for ep_id, node_id in self.entry_points.items():
            if node_id not in node_ids:
                errors.append(
                    f"Entry point '{ep_id}' references unknown node '{node_id}'"
                )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }


# Create default instance
default_agent: SdrLinkedinMonitorAgent = SdrLinkedinMonitorAgent()
