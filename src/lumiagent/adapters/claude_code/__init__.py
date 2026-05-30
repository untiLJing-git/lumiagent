"""Claude Code capture adapter."""
from lumiagent.adapters.claude_code.converter import ClaudeCodeTraceConverter
from lumiagent.adapters.claude_code.events import (
    ClaudeCodeHookEvent,
    read_hook_events,
    write_hook_event,
)
from lumiagent.adapters.claude_code.setup import (
    ClaudeCodeSettingsError,
    ClaudeCodeSetupResult,
    configure_claude_code_hooks,
)
from lumiagent.adapters.claude_code.transcript import (
    TranscriptEnrichment,
    TranscriptSemanticItem,
    enrich_transcript,
)

__all__ = [
    "ClaudeCodeHookEvent",
    "ClaudeCodeSettingsError",
    "ClaudeCodeSetupResult",
    "ClaudeCodeTraceConverter",
    "TranscriptEnrichment",
    "TranscriptSemanticItem",
    "configure_claude_code_hooks",
    "enrich_transcript",
    "read_hook_events",
    "write_hook_event",
]
