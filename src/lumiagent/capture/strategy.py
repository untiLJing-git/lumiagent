"""Generic capture strategy protocol."""
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from lumiagent.tracing import AgentRun


class CaptureStrategy(Protocol):
    def capture(self) -> AgentRun: ...
