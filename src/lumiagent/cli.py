"""CLI entry point for LumiAgent."""
from __future__ import annotations

import asyncio
import json
import pathlib  # noqa: TC003
from typing import Annotated, Any

import click
import typer
from rich.console import Console

app = typer.Typer(
    name="lumi",
    help="LumiAgent - Multi-platform AI Agent with ReAct, RAG, and MCP",
    no_args_is_help=True,
)
console = Console()
capture_app = typer.Typer(help="Capture traces from external systems.")
app.add_typer(capture_app, name="capture")


@app.command()
def chat(
    platform: str = typer.Option("cmd", help="Platform to use: cmd, web"),
    model: str | None = typer.Option(None, help="Override primary LLM model"),
    debug: bool = typer.Option(False, help="Enable debug logging"),
) -> None:
    """Start interactive chat session."""
    asyncio.run(_run_chat(platform, model, debug))


async def _run_chat(platform: str, model: str | None, debug: bool) -> None:
    from lumiagent.config import get_settings
    from lumiagent.logging import setup_logging

    settings = get_settings()
    if debug:
        settings.debug = True
        settings.log_level = "DEBUG"
    if model:
        settings.openai_model = model

    setup_logging(level=settings.log_level)
    settings.ensure_dirs()

    from lumiagent.agent import create_agent

    agent = await create_agent(settings)

    console.print("\n[bold green]🚀 LumiAgent[/bold green] v0.1.0")
    console.print(
        f"Platform: [cyan]{platform}[/cyan] | Model: [cyan]{settings.openai_model}[/cyan]"
    )
    console.print("Type [bold]exit[/bold] or [bold]quit[/bold] to stop.\n")

    await agent.start(platforms=[platform])


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Server host"),
    port: int = typer.Option(8000, help="Server port"),
) -> None:
    """Start Agent as web server (REST + WebSocket)."""
    asyncio.run(_run_serve(host, port))


async def _run_serve(host: str, port: int) -> None:
    from lumiagent.config import get_settings
    from lumiagent.logging import setup_logging

    settings = get_settings()
    settings.platform.web_host = host
    settings.platform.web_port = port
    settings.platform.cmd_enabled = False

    setup_logging(level=settings.log_level)
    settings.ensure_dirs()

    from lumiagent.agent import create_agent

    agent = await create_agent(settings)
    console.print(f"[bold green]🌐 LumiAgent Server[/bold green] on {host}:{port}")
    await agent.start(platforms=["web"])


@app.command()
def ingest(
    source: str = typer.Argument(help="File or directory path to ingest"),
    collection: str = typer.Option("default", help="Knowledge collection name"),
) -> None:
    """Ingest documents into the RAG knowledge base."""
    asyncio.run(_run_ingest(source, collection))


async def _run_ingest(source: str, collection: str) -> None:
    from lumiagent.config import get_settings
    from lumiagent.logging import setup_logging
    from lumiagent.rag.embedder import OpenAIEmbedder
    from lumiagent.rag.pipeline import RAGPipeline

    settings = get_settings()
    setup_logging(level=settings.log_level)

    embedder = OpenAIEmbedder(
        api_key=settings.openai_api_key,
        model=settings.embedding_model,
    )
    rag = RAGPipeline(config=settings.rag, embedder=embedder)

    with console.status(f"Ingesting {source}..."):
        count = await rag.ingest(source, collection=collection)

    console.print(f"[green]✅ Ingested {count} chunks into collection '{collection}'[/green]")


@app.command(name="eval")
def evaluate(
    eval_set: str = typer.Argument(help="Name of the evaluation set"),
    output: str | None = typer.Option(None, help="Output report path"),
) -> None:
    """Run evaluation suite against the Agent."""
    asyncio.run(_run_eval(eval_set, output))


async def _run_eval(eval_set: str, output: str | None) -> None:
    from lumiagent.config import get_settings
    from lumiagent.logging import setup_logging

    settings = get_settings()
    settings.evaluation.enabled = True
    setup_logging(level=settings.log_level)

    from lumiagent.agent import create_agent
    from lumiagent.evaluation.suite import EvaluationSuite

    agent = await create_agent(settings)
    suite = EvaluationSuite(config=settings.evaluation)

    async def agent_run_fn(question: str) -> tuple[str, Any, dict[str, Any]]:
        from lumiagent.models.message import Platform, UnifiedMessage

        msg = UnifiedMessage.text(
            text=question,
            platform=Platform.CMD,
            channel_id="eval",
            user_id="evaluator",
        )
        response = await agent.engine.run(msg)
        return response.content.text or "", response.trace, {}

    console.print(f"[yellow]Running evaluation: {eval_set}[/yellow]")
    report = await suite.run(eval_set, agent_run_fn)

    report_path = suite.save_report(report, output)
    console.print(f"\n[bold]Overall Score: {report.overall_score:.2%}[/bold]")
    console.print(f"Report saved to: [cyan]{report_path}[/cyan]")

    for cat, score in sorted(report.summary.items()):
        color = "green" if score >= 0.7 else "yellow" if score >= 0.4 else "red"
        console.print(f"  [{color}]{cat}: {score:.2%}[/{color}]")


def _parse_json_object(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter("arguments must be a JSON object") from exc
    if not isinstance(parsed, dict):
        raise typer.BadParameter("arguments must be a JSON object")
    return parsed


@capture_app.command(name="mcp")
def capture_mcp(
    server_command: Annotated[
        str,
        typer.Option(..., help="MCP server command to execute."),
    ],
    tool: Annotated[str, typer.Option(..., help="MCP tool name to call.")],
    output: Annotated[
        pathlib.Path,
        typer.Option(..., "-o", "--output", help="Trace JSON output path."),
    ],
    transport: Annotated[str, typer.Option(help="MCP transport to use.")] = "stdio",
    server_arg: Annotated[
        list[str] | None,
        typer.Option(
            "--server-arg",
            help="Argument to pass to the MCP server. Repeat for multiple arguments.",
        ),
    ] = None,
    arguments: Annotated[str, typer.Option(help="JSON object arguments for the MCP tool.")] = "{}",
    timeout_seconds: Annotated[
        int,
        typer.Option("--timeout", "--timeout-seconds", help="MCP runtime timeout in seconds."),
    ] = 30,
) -> None:
    """Capture one MCP tool call as a LumiAgent trace."""

    parsed_arguments = _parse_json_object(arguments)

    from lumiagent.adapters.mcp.capture import McpCaptureConfig, McpCaptureStrategy
    from lumiagent.tracing.serializer import to_json

    config = McpCaptureConfig(
        transport=transport,
        server_command=server_command,
        server_args=server_arg or [],
        tool_name=tool,
        arguments=parsed_arguments,
        timeout_seconds=timeout_seconds,
    )
    try:
        run = McpCaptureStrategy(config=config).capture()
    except NotImplementedError as exc:
        message = str(exc) or "MCP capture is not implemented yet"
        raise click.ClickException(
            f"MCP stdio capture is not implemented yet: {message}"
        ) from exc

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(to_json(run), encoding="utf-8")
    console.print(str(output))


@app.command()
def show(
    trace_path: Annotated[pathlib.Path, typer.Argument(help="Trace JSON file to render.")],
) -> None:
    """Render a plain-text MCP trace summary."""

    from lumiagent.adapters.mcp.viewer import render_mcp_trace_summary
    from lumiagent.tracing.serializer import from_json

    try:
        run = from_json(trace_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise click.ClickException(f"Invalid trace JSON: {exc}") from exc
    for line in render_mcp_trace_summary(run):
        console.print(line)


@app.command()
def tools() -> None:
    """List all registered tools."""
    asyncio.run(_list_tools())


async def _list_tools() -> None:
    from lumiagent.tools.registry import ToolRegistry

    registry = ToolRegistry()
    registry.register_defaults()

    console.print("[bold]Registered Tools:[/bold]\n")
    for schema in registry.get_schemas():
        console.print(f"  [cyan]{schema.name}[/cyan] - {schema.description}")


if __name__ == "__main__":
    app()
