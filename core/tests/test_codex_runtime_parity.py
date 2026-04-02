from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import MagicMock

import pytest

from framework.graph.event_loop_node import EventLoopNode, LoopConfig
from framework.graph.node import NodeContext, NodeSpec, SharedMemory
from framework.llm.provider import LLMProvider, LLMResponse
from framework.llm.stream_events import FinishEvent, TextDeltaEvent, ToolCallEvent
from framework.runtime.core import Runtime
from framework.runtime.event_bus import EventBus, EventType
from framework.server.queen_orchestrator import _client_input_counts_as_planning_ask


class MockStreamingLLM(LLMProvider):
    """Mock LLM that replays deterministic stream scenarios."""

    def __init__(self, scenarios: list[list] | None = None):
        self.scenarios = scenarios or []
        self._call_index = 0

    async def stream(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools=None,
        max_tokens: int = 4096,
    ) -> AsyncIterator:
        if not self.scenarios:
            return
        events = self.scenarios[self._call_index % len(self.scenarios)]
        self._call_index += 1
        for event in events:
            yield event

    def complete(self, messages, system="", **kwargs) -> LLMResponse:
        return LLMResponse(content="Summary.", model="mock", stop_reason="stop")


def text_scenario(text: str, input_tokens: int = 10, output_tokens: int = 5) -> list:
    return [
        TextDeltaEvent(content=text, snapshot=text),
        FinishEvent(
            stop_reason="stop",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model="mock",
        ),
    ]


def tool_call_scenario(
    tool_name: str,
    tool_input: dict[str, Any],
    tool_use_id: str = "call_1",
) -> list:
    return [
        ToolCallEvent(tool_use_id=tool_use_id, tool_name=tool_name, tool_input=tool_input),
        FinishEvent(stop_reason="tool_calls", input_tokens=10, output_tokens=5, model="mock"),
    ]


@pytest.fixture
def runtime():
    rt = MagicMock(spec=Runtime)
    rt.start_run = MagicMock(return_value="session_20250101_000000_codex01")
    rt.decide = MagicMock(return_value="dec_1")
    rt.record_outcome = MagicMock()
    rt.end_run = MagicMock()
    rt.report_problem = MagicMock()
    rt.set_node = MagicMock()
    return rt


@pytest.fixture
def memory():
    return SharedMemory()


def build_ctx(
    runtime,
    node_spec: NodeSpec,
    memory: SharedMemory,
    llm: LLMProvider,
    *,
    stream_id: str | None = None,
) -> NodeContext:
    return NodeContext(
        runtime=runtime,
        node_id=node_spec.id,
        node_spec=node_spec,
        memory=memory,
        input_data={},
        llm=llm,
        available_tools=[],
        goal_context="",
        stream_id=stream_id,
    )


@pytest.mark.asyncio
async def test_queen_auto_blocked_input_counts_as_planning_ask(runtime, memory):
    spec = NodeSpec(
        id="queen",
        name="Queen",
        description="Planning node",
        node_type="event_loop",
        output_keys=[],
        client_facing=True,
    )
    llm = MockStreamingLLM(
        scenarios=[text_scenario("I've isolated the root cause. What would you like to do next?")]
    )
    bus = EventBus()
    received = []

    async def capture(event):
        received.append(event)

    bus.subscribe([EventType.CLIENT_INPUT_REQUESTED], capture, filter_stream="queen")

    node = EventLoopNode(event_bus=bus, config=LoopConfig(max_iterations=5))
    ctx = build_ctx(runtime, spec, memory, llm, stream_id="queen")

    async def shutdown():
        await asyncio.sleep(0.05)
        node.signal_shutdown()

    task = asyncio.create_task(shutdown())
    result = await node.execute(ctx)
    await task

    assert result.success is True
    assert len(received) == 1
    event = received[0]
    assert event.data["auto_blocked"] is True
    assert event.data["assistant_text_requires_input"] is True
    assert _client_input_counts_as_planning_ask(event) is True


@pytest.mark.asyncio
async def test_queen_ask_user_emits_result_text_before_question_widget(runtime, memory):
    spec = NodeSpec(
        id="queen",
        name="Queen",
        description="Planning node",
        node_type="event_loop",
        output_keys=[],
        client_facing=True,
    )
    llm = MockStreamingLLM(
        scenarios=[
            tool_call_scenario(
                "ask_user",
                {
                    "question": (
                        "Root cause: the database pool is exhausted.\n\n"
                        "What would you like to do next?"
                    ),
                    "options": ["Rerun", "Stop"],
                },
                tool_use_id="ask_1",
            )
        ]
    )
    bus = EventBus()
    output_events = []
    input_events = []

    async def capture_output(event):
        output_events.append(event)

    async def capture_input(event):
        input_events.append(event)

    bus.subscribe([EventType.CLIENT_OUTPUT_DELTA], capture_output, filter_stream="queen")
    bus.subscribe([EventType.CLIENT_INPUT_REQUESTED], capture_input, filter_stream="queen")

    node = EventLoopNode(event_bus=bus, config=LoopConfig(max_iterations=5))
    ctx = build_ctx(runtime, spec, memory, llm, stream_id="queen")

    async def shutdown():
        await asyncio.sleep(0.05)
        node.signal_shutdown()

    task = asyncio.create_task(shutdown())
    result = await node.execute(ctx)
    await task

    assert result.success is True
    assert [event.data["snapshot"] for event in output_events] == [
        "Root cause: the database pool is exhausted."
    ]
    assert len(input_events) == 1
    assert input_events[0].data["prompt"] == "What would you like to do next?"
    assert input_events[0].data["options"] == ["Rerun", "Stop"]


@pytest.mark.asyncio
async def test_worker_auto_completes_after_duplicate_set_output(runtime, memory):
    spec = NodeSpec(
        id="worker",
        name="Worker",
        description="Internal worker node",
        node_type="event_loop",
        output_keys=["result"],
    )
    llm = MockStreamingLLM(
        scenarios=[
            [
                ToolCallEvent(
                    tool_use_id="set_1",
                    tool_name="set_output",
                    tool_input={"key": "result", "value": "done"},
                ),
                ToolCallEvent(
                    tool_use_id="set_2",
                    tool_name="set_output",
                    tool_input={"key": "result", "value": "done"},
                ),
                FinishEvent(
                    stop_reason="tool_calls",
                    input_tokens=10,
                    output_tokens=5,
                    model="mock",
                ),
            ]
        ]
    )

    node = EventLoopNode(config=LoopConfig(max_iterations=2, max_tool_calls_per_turn=3))
    ctx = build_ctx(runtime, spec, memory, llm, stream_id="worker")

    result = await node.execute(ctx)

    assert result.success is True
    assert result.output["result"] == "done"
    assert llm._call_index == 1
