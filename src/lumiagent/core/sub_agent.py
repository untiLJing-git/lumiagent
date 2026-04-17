"""Sub-agent management for task decomposition and delegation."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from lumiagent.logging import get_logger
from lumiagent.models.message import AgentResponse, MessageContent, UnifiedMessage, Platform

if TYPE_CHECKING:
    from lumiagent.core.engine import ReActEngine

logger = get_logger(__name__)


@dataclass
class SubAgentTask:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    description: str = ""
    status: str = "pending"  # pending / running / completed / failed
    result: Optional[AgentResponse] = None


class SubAgentManager:
    """Manages sub-agents for parallel task decomposition."""

    def __init__(self, engine_factory=None) -> None:
        self._engine_factory = engine_factory
        self._tasks: dict[str, SubAgentTask] = {}

    async def delegate(self, task_description: str, parent_message: UnifiedMessage) -> AgentResponse:
        """Delegate a task to a sub-agent."""
        task = SubAgentTask(description=task_description)
        self._tasks[task.id] = task

        logger.info("Delegating to sub-agent", task_id=task.id, task=task_description[:100])

        try:
            task.status = "running"

            if self._engine_factory:
                engine = self._engine_factory()
                sub_message = UnifiedMessage.text(
                    text=task_description,
                    platform=parent_message.platform,
                    channel_id=f"sub_{task.id}",
                    user_id=parent_message.user_id,
                    user_name=parent_message.user_name,
                )
                result = await engine.run(sub_message)
            else:
                result = AgentResponse.text(f"[Sub-agent not configured] Task: {task_description}")

            task.status = "completed"
            task.result = result
            return result

        except Exception as e:
            task.status = "failed"
            logger.exception("Sub-agent failed", task_id=task.id)
            return AgentResponse.text(f"Sub-agent error: {e}")

    def get_task(self, task_id: str) -> SubAgentTask | None:
        return self._tasks.get(task_id)

    def list_tasks(self) -> list[SubAgentTask]:
        return list(self._tasks.values())
