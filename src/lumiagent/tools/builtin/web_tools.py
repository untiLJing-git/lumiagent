"""Web search and fetch tools."""
from __future__ import annotations

from typing import Any

import httpx

from lumiagent.models.tool import ToolResult, ToolResultStatus
from lumiagent.tools.base import BaseTool


class WebSearchTool(BaseTool):
    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Search the web for information. Returns search results with titles, URLs, and snippets."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "count": {"type": "integer", "description": "Number of results (default: 5)"},
            },
            "required": ["query"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query", "")
        # Placeholder: integrate with actual search API (e.g., SerpAPI, Bing, etc.)
        return ToolResult(
            tool_name=self.name,
            output=f"[Web search stub] Query: {query}\nIntegrate with SerpAPI/Bing/Google to get real results.",
        )


class WebFetchTool(BaseTool):
    @property
    def name(self) -> str:
        return "web_fetch"

    @property
    def description(self) -> str:
        return "Fetch content from a URL and return the text content."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default: 30)"},
            },
            "required": ["url"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        url = kwargs.get("url", "")
        timeout = kwargs.get("timeout", 30)

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                text = response.text[:10000]  # Limit output size
                return ToolResult(
                    tool_name=self.name,
                    output=text,
                    metadata={"status_code": response.status_code, "url": str(response.url)},
                )
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolResultStatus.ERROR,
                error=str(e),
            )
