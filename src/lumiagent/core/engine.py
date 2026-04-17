"""ReAct engine - the core reasoning-action loop."""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Optional

from lumiagent.config import Settings
from lumiagent.core.context import AgentContext, ContextBuilder
from lumiagent.core.memory import MemoryManager
from lumiagent.logging import get_logger
from lumiagent.models.llm import LLMRequest, LLMResponse
from lumiagent.models.message import AgentResponse, MessageContent, UnifiedMessage

if TYPE_CHECKING:
    from lumiagent.llm.router import LLMRouter
    from lumiagent.tools.registry import ToolRegistry

logger = get_logger(__name__)


class ReActEngine:
    """ReAct (Reasoning + Acting) loop engine."""

    def __init__(
        self,
        settings: Settings,
        llm_router: LLMRouter,
        tool_registry: ToolRegistry,
        memory: MemoryManager,
        context_builder: ContextBuilder,
    ) -> None:
        self.settings = settings
        self.llm = llm_router
        self.tools = tool_registry
        self.memory = memory
        self.context_builder = context_builder
        self.max_iterations = settings.max_react_iterations

    async def run(self, message: UnifiedMessage) -> AgentResponse:
        """Execute the ReAct loop for a single message."""
        trace: list[dict] = []

        # Build initial context
        ctx = await self.context_builder.build(
            message, tool_schemas=self.tools.get_schemas()
        )

        for step in range(self.max_iterations):
            logger.debug("ReAct step", step=step + 1)

            # Thought + Action: call LLM
            llm_request = LLMRequest(
                messages=ctx.to_messages(),
                tools=ctx.tool_schemas or None,
                temperature=0.7,
                max_tokens=4096,
            )

            try:
                llm_response = await self.llm.chat(llm_request)
            except Exception:
                logger.exception("LLM call failed", step=step)
                return AgentResponse.text("Sorry, I encountered an error processing your request.")

            trace.append({
                "step": step + 1,
                "type": "thought",
                "content": llm_response.content,
                "tool_calls": [tc.model_dump() for tc in llm_response.tool_calls],
                "tokens": llm_response.usage.total_tokens,
                "latency_ms": llm_response.latency_ms,
            })

            # If no tool calls, we have our final answer
            if not llm_response.has_tool_calls:
                response = AgentResponse.text(llm_response.content)
                response.trace = trace

                # Store in memory
                await self.memory.store_turn(
                    channel_id=message.channel_id,
                    user_message=message,
                    agent_response=response,
                )
                return response

            # Add assistant message with tool calls to context
            ctx.add_assistant(llm_response.content, tool_calls=llm_response.tool_calls)

            # Execute tool calls (parallel when possible)
            tool_tasks = []
            for tc in llm_response.tool_calls:
                tool_tasks.append(self._execute_tool(tc.id, tc.name, tc.arguments))

            results = await asyncio.gather(*tool_tasks, return_exceptions=True)

            # Add observations to context
            for tc, result in zip(llm_response.tool_calls, results):
                if isinstance(result, Exception):
                    observation = f"Error: {result}"
                else:
                    observation = result.output if result.status.value == "success" else f"Error: {result.error}"

                ctx.add_tool_result(tc.id, observation)
                trace.append({
                    "step": step + 1,
                    "type": "observation",
                    "tool": tc.name,
                    "result": observation[:500],
                })

        # Exceeded max iterations
        logger.warning("ReAct loop exceeded max iterations", max=self.max_iterations)
        return AgentResponse(
            content=MessageContent.from_text(
                "I've reached the maximum number of reasoning steps. Here's what I found so far: "
                + (llm_response.content if llm_response else "No conclusion reached.")
            ),
            trace=trace,
            error=True,
        )

    async def _execute_tool(self, tool_call_id: str, tool_name: str, arguments_json: str):
        """Execute a single tool call."""
        import json

        try:
            args = json.loads(arguments_json) if arguments_json else {}
        except json.JSONDecodeError:
            from lumiagent.models.tool import ToolResult, ToolResultStatus
            return ToolResult(
                tool_name=tool_name,
                status=ToolResultStatus.ERROR,
                error=f"Invalid JSON arguments: {arguments_json}",
            )

        return await self.tools.execute(tool_name, **args)
