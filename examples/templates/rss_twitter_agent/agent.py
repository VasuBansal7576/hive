"""Agent graph construction for modern RSS-to-Twitter Agent."""

from __future__ import annotations

import os
from pathlib import Path

from framework.graph import Constraint, EdgeCondition, EdgeSpec, Goal, SuccessCriterion
from framework.graph.edge import GraphSpec
from framework.graph.executor import ExecutionResult
from framework.llm import LiteLLMProvider
from framework.llm.provider import LLMProvider, LLMResponse, Tool
from framework.llm.stream_events import FinishEvent, ToolCallEvent
from framework.runner.tool_registry import ToolRegistry
from framework.runtime.agent_runtime import AgentRuntime, create_agent_runtime
from framework.runtime.execution_stream import EntryPointSpec

from .config import default_config, metadata
from .helpers import (
    fetch_rss_data,
    generate_threads_data,
    post_to_twitter_data,
    summarize_articles_data,
)
from .nodes import (
    approve_node,
    complete_node,
    fetch_node,
    generate_node,
    post_node,
    process_node,
)


goal = Goal(
    id="rss-twitter-modern",
    name="RSS-to-Twitter Automation",
    description=(
        "Fetch RSS articles, generate Twitter thread drafts, request user approval, "
        "and post approved threads with Playwright automation."
    ),
    success_criteria=[
        SuccessCriterion(
            id="rss-fetch",
            description="RSS feed is fetched and parsed",
            metric="article_count",
            target=">=1",
            weight=0.2,
        ),
        SuccessCriterion(
            id="thread-generation",
            description="Thread drafts are generated",
            metric="thread_count",
            target=">=1",
            weight=0.4,
        ),
        SuccessCriterion(
            id="approval-gate",
            description="User makes explicit yes/no posting decision",
            metric="approval_present",
            target="true",
            weight=0.2,
        ),
        SuccessCriterion(
            id="posting",
            description="Approved threads are posted successfully",
            metric="post_success",
            target="true when approved",
            weight=0.2,
        ),
    ],
    constraints=[
        Constraint(
            id="human-approval-required",
            description="Posting to Twitter requires explicit user approval",
            constraint_type="safety",
            category="approval",
        ),
        Constraint(
            id="include-source-link",
            description="Threads should include source links from feed articles",
            constraint_type="quality",
            category="content",
        ),
    ],
)

nodes = [fetch_node, process_node, generate_node, approve_node, post_node, complete_node]

edges = [
    EdgeSpec(
        id="fetch-to-process",
        source="fetch",
        target="process",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="process-to-generate",
        source="process",
        target="generate",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="generate-to-approve",
        source="generate",
        target="approve",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="approve-to-post",
        source="approve",
        target="post",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="should_post == True",
        priority=1,
    ),
    EdgeSpec(
        id="approve-to-complete",
        source="approve",
        target="complete",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="should_post == False",
        priority=-1,
    ),
    EdgeSpec(
        id="post-to-complete",
        source="post",
        target="complete",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
]

entry_node = "fetch"
entry_points = {"start": "fetch"}
terminal_nodes = ["complete"]
pause_nodes: list[str] = []


class _RSSTwitterMockLLM(LLMProvider):
    """Deterministic mock LLM for dry-run testing."""

    model = "rss-twitter-mock"

    def __init__(self, run_context: dict | None = None):
        self._run_context = run_context or {}
        self._seen: set[str] = set()

    def complete(
        self,
        messages,
        system: str = "",
        tools: list[Tool] | None = None,
        max_tokens: int = 1024,
        response_format=None,
        json_mode: bool = False,
        max_retries: int | None = None,
    ) -> LLMResponse:
        return LLMResponse(content="mock", model=self.model, stop_reason="mock_complete")

    def complete_with_tools(
        self,
        messages,
        system: str,
        tools: list[Tool],
        tool_executor,
        max_iterations: int = 10,
    ) -> LLMResponse:
        return LLMResponse(content="mock", model=self.model, stop_reason="mock_complete")

    async def stream(
        self,
        messages,
        system: str = "",
        tools: list[Tool] | None = None,
        max_tokens: int = 4096,
    ):
        lowered = system.lower()
        calls: list[tuple[str, dict]] = []
        phase = "unknown"
        auto_approve = bool(self._run_context.get("auto_approve", True))

        if "you fetch rss articles" in lowered:
            phase = "fetch"
            calls.extend(
                [
                    (
                        "fetch_rss_data",
                        {
                            "feed_url": self._run_context.get("feed_url", "https://news.ycombinator.com/rss"),
                            "max_articles": int(self._run_context.get("max_articles", 3)),
                        },
                    ),
                    ("set_output", {"key": "articles", "value": self._run_context.get("mock_articles", [{"title": "Mock Story", "link": "https://example.com", "summary": "mock", "source": "RSS"}])}),
                ]
            )
        elif "you summarize rss articles" in lowered:
            phase = "process"
            calls.extend(
                [
                    ("summarize_articles_data", {"articles": self._run_context.get("mock_articles", [{"title": "Mock Story", "link": "https://example.com", "summary": "mock", "source": "RSS"}])}),
                    (
                        "set_output",
                        {
                            "key": "summaries",
                            "value": self._run_context.get("mock_summaries", [{"title": "Mock Story", "url": "https://example.com", "hook": "Mock hook", "points": ["Point 1", "Point 2"], "why_it_matters": "Because demo", "hashtags": ["#AI"]}]),
                        },
                    ),
                ]
            )
        elif "you generate twitter threads" in lowered:
            phase = "generate"
            calls.extend(
                [
                    ("generate_threads_data", {"summaries": self._run_context.get("mock_summaries", [])}),
                    (
                        "set_output",
                        {
                            "key": "threads",
                            "value": self._run_context.get("mock_threads", [{"title": "Mock Story", "tweets": ["🧵 Mock", "1/ detail", "2/ insight", "3/ CTA https://example.com #AI"]}]),
                        },
                    ),
                ]
            )
        elif "thread approval checkpoint" in lowered:
            phase = "approve"
            approved_threads = self._run_context.get("mock_threads", [{"title": "Mock Story", "tweets": ["🧵 Mock", "1/ detail", "2/ insight", "3/ CTA"]}])
            calls.append(("set_output", {"key": "should_post", "value": auto_approve}))
            calls.append(("set_output", {"key": "approved_threads", "value": approved_threads if auto_approve else []}))
        elif "you post approved threads" in lowered:
            phase = "post"
            calls.append(("set_output", {"key": "post_results", "value": {"success": True, "message": "mock posted"}}))
        elif "you finalize run status" in lowered:
            phase = "complete"
            status = "posted" if auto_approve else "skipped"
            calls.append(("set_output", {"key": "workflow_status", "value": status}))

        if phase in self._seen:
            calls = []
        elif phase != "unknown":
            self._seen.add(phase)

        for idx, (tool_name, tool_input) in enumerate(calls, 1):
            yield ToolCallEvent(
                tool_use_id=f"mock_tool_{idx}",
                tool_name=tool_name,
                tool_input=tool_input,
            )

        yield FinishEvent(stop_reason="mock_complete", model=self.model)


class RSSTwitterAgent:
    """Modern RSS-to-Twitter agent using AgentRuntime."""

    def __init__(self, config=None):
        self.config = config or default_config
        self.goal = goal
        self.nodes = nodes
        self.edges = edges
        self.entry_node = entry_node
        self.entry_points = entry_points
        self.pause_nodes = pause_nodes
        self.terminal_nodes = terminal_nodes
        self._graph: GraphSpec | None = None
        self._agent_runtime: AgentRuntime | None = None
        self._tool_registry: ToolRegistry | None = None
        self._storage_path: Path | None = None

    def _build_graph(self) -> GraphSpec:
        return GraphSpec(
            id="rss-twitter-modern-graph",
            goal_id=self.goal.id,
            version="2.0.0",
            entry_node=self.entry_node,
            entry_points=self.entry_points,
            terminal_nodes=self.terminal_nodes,
            pause_nodes=self.pause_nodes,
            nodes=self.nodes,
            edges=self.edges,
            default_model=self.config.model,
            max_tokens=self.config.max_tokens,
            loop_config={
                "max_iterations": 40,
                "max_tool_calls_per_turn": 12,
                "max_history_tokens": 32000,
            },
            conversation_mode="continuous",
            identity_prompt=(
                "You are an RSS-to-Twitter automation agent that fetches articles, creates "
                "engaging thread drafts, asks for explicit approval, and posts approved threads."
            ),
        )

    def _register_local_tools(self) -> None:
        if self._tool_registry is None:
            return
        self._tool_registry.register_function(
            fetch_rss_data,
            name="fetch_rss_data",
            description="Fetch and parse RSS feed data",
        )
        self._tool_registry.register_function(
            summarize_articles_data,
            name="summarize_articles_data",
            description="Summarize articles for thread generation",
        )
        self._tool_registry.register_function(
            generate_threads_data,
            name="generate_threads_data",
            description="Generate Twitter threads from summaries",
        )
        self._tool_registry.register_function(
            post_to_twitter_data,
            name="post_to_twitter_data",
            description="Post threads to Twitter using Playwright",
        )

    def _setup(self, mock_mode: bool = False, run_context: dict | None = None) -> None:
        storage_root = Path(
            os.environ.get("HIVE_AGENT_STORAGE_ROOT", str(Path.home() / ".hive" / "agents"))
        )
        self._storage_path = storage_root / "rss_twitter_agent"
        self._storage_path.mkdir(parents=True, exist_ok=True)

        self._tool_registry = ToolRegistry()
        self._register_local_tools()

        if mock_mode:
            llm = _RSSTwitterMockLLM(run_context=run_context)
            graph_nodes = [n.model_copy(update={"tools": []}) for n in self.nodes]
        else:
            llm = LiteLLMProvider(
                model=self.config.model,
                api_key=self.config.api_key,
                api_base=self.config.api_base,
            )
            graph_nodes = self.nodes

        self._graph = self._build_graph().model_copy(update={"nodes": graph_nodes})

        tools = list(self._tool_registry.get_tools().values())
        tool_executor = self._tool_registry.get_executor()
        entry_point_specs = [
            EntryPointSpec(
                id="start",
                name="Start RSS-to-Twitter",
                entry_node=self.entry_node,
                trigger_type="manual",
                isolation_level="isolated",
            )
        ]

        self._agent_runtime = create_agent_runtime(
            graph=self._graph,
            goal=self.goal,
            storage_path=self._storage_path,
            entry_points=entry_point_specs,
            llm=llm,
            tools=tools,
            tool_executor=tool_executor,
        )

    async def start(self, mock_mode: bool = False, run_context: dict | None = None) -> None:
        if self._agent_runtime is None:
            self._setup(mock_mode=mock_mode, run_context=run_context)
        if not self._agent_runtime.is_running:
            await self._agent_runtime.start()

    async def stop(self) -> None:
        if self._agent_runtime and self._agent_runtime.is_running:
            await self._agent_runtime.stop()
        self._agent_runtime = None

    async def run(self, context: dict, mock_mode: bool = False) -> ExecutionResult:
        await self.start(mock_mode=mock_mode, run_context=context)
        try:
            result = await self._agent_runtime.trigger_and_wait(
                entry_point_id="start",
                input_data=context,
            )
            return result or ExecutionResult(success=False, error="Execution timeout")
        finally:
            await self.stop()

    def info(self) -> dict:
        return {
            "name": metadata.name,
            "version": metadata.version,
            "description": metadata.description,
            "entry_node": self.entry_node,
            "terminal_nodes": self.terminal_nodes,
            "nodes": [n.id for n in self.nodes],
            "client_facing_nodes": [n.id for n in self.nodes if n.client_facing],
        }

    def validate(self) -> dict:
        errors: list[str] = []

        node_ids = {n.id for n in self.nodes}
        if self.entry_node not in node_ids:
            errors.append(f"entry_node '{self.entry_node}' not in nodes")

        for edge in self.edges:
            if edge.source not in node_ids:
                errors.append(f"edge {edge.id} has unknown source '{edge.source}'")
            if edge.target not in node_ids:
                errors.append(f"edge {edge.id} has unknown target '{edge.target}'")

        return {"valid": not errors, "errors": errors, "warnings": []}


default_agent = RSSTwitterAgent()
