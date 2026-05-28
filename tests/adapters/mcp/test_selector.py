import pytest

from lumiagent.adapters.mcp.runtime import McpToolDefinition
from lumiagent.adapters.mcp.selector import ExplicitToolSelector, McpToolSelection
from lumiagent.adapters.mcp.taxonomy import McpFailureType


def test_explicit_tool_selector_selects_requested_tool() -> None:
    selector = ExplicitToolSelector()
    selection = selector.select(
        requested_tool_name="read_file",
        tools=[
            McpToolDefinition(name="list_directory"),
            McpToolDefinition(name="read_file", input_schema={"type": "object"}),
        ],
    )

    assert isinstance(selection, McpToolSelection)
    assert selection.requested_tool_name == "read_file"
    assert selection.selected_tool_name == "read_file"
    assert selection.available_tool_names == ["list_directory", "read_file"]
    assert selection.selection_strategy == "explicit"


def test_explicit_tool_selector_raises_tool_not_found() -> None:
    selector = ExplicitToolSelector()

    with pytest.raises(ValueError) as exc_info:
        selector.select(
            requested_tool_name="read_me",
            tools=[McpToolDefinition(name="read_file")],
        )

    assert "tool_not_found" in str(exc_info.value)


def test_tool_selection_serializes_as_evidence() -> None:
    selection = McpToolSelection(
        requested_tool_name="read_file",
        selected_tool_name="read_file",
        available_tool_names=["read_file"],
        reason="Tool name was provided by CLI.",
    )

    assert selection.model_dump(mode="json") == {
        "requested_tool_name": "read_file",
        "selected_tool_name": "read_file",
        "available_tool_names": ["read_file"],
        "selection_strategy": "explicit",
        "reason": "Tool name was provided by CLI.",
    }


def test_selector_failure_type_constant_is_tool_not_found() -> None:
    assert McpFailureType.TOOL_NOT_FOUND.value == "tool_not_found"
