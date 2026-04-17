# LumiAgent

Multi-platform AI Agent framework with ReAct reasoning, RAG knowledge retrieval, MCP tool integration, and systematic evaluation.

## Architecture

```
┌─────────────────────────────────────────────────┐
│           Platform Layer (多平台适配)             │
│     CMD │ Web │ WeChat │ Feishu │ DingTalk      │
├─────────────────────────────────────────────────┤
│              Message Bus (消息总线)               │
├─────────────────────────────────────────────────┤
│           Agent Core (ReAct 核心引擎)             │
│    Context Builder │ Memory │ Sub-Agents        │
├───────────────────┬─────────────────────────────┤
│    Tool Layer     │       LLM Layer             │
│  Built-in + MCP   │  OpenAI/Claude/DeepSeek     │
├───────────────────┴─────────────────────────────┤
│              RAG Layer (知识检索)                 │
├─────────────────────────────────────────────────┤
│          Evaluation Layer (评估体系)              │
└─────────────────────────────────────────────────┘
```

## Features

- **Multi-Platform**: CMD, Web (REST + WebSocket), WeChat, Feishu, DingTalk
- **ReAct Engine**: Reasoning + Acting loop with configurable max iterations
- **Memory System**: Short-term (conversation), Long-term (SQLite + vector), Proactive recall, Auto-compression
- **LLM Routing**: Primary/fallback/round-robin strategies across OpenAI, Anthropic, DeepSeek, etc.
- **Tool System**: Built-in tools (bash, file I/O, web, Python, cron) + MCP hot-plug support
- **RAG Pipeline**: Document loading → Chunking → Embedding → Vector search → Reranking
- **Evaluation Suite**: Response quality, tool usage, RAG accuracy, safety, latency metrics

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env with your API keys

# Interactive chat
lumi chat

# Web server
lumi serve --port 8000

# Ingest knowledge
lumi ingest ./docs --collection my-knowledge

# Run evaluation
lumi eval sample_eval

# List tools
lumi tools
```

## Project Structure

```
src/lumiagent/
├── __init__.py              # Package version
├── agent.py                 # Agent assembly & wiring
├── cli.py                   # CLI commands (typer)
├── config.py                # Pydantic Settings
├── logging.py               # Structured logging (structlog)
├── models/                  # Data models (Pydantic v2)
│   ├── message.py           # UnifiedMessage, Platform, MessageContent
│   ├── llm.py               # LLMRequest, LLMResponse, ChatMessage
│   ├── tool.py              # ToolResult, MCPServerConfig
│   └── memory.py            # MemoryEntry, ConversationTurn
├── platform/                # Multi-platform adapters
│   ├── base.py              # PlatformAdapter ABC
│   ├── manager.py           # PlatformManager
│   ├── cmd_adapter.py       # Terminal/CLI adapter
│   ├── web_adapter.py       # FastAPI REST + WebSocket
│   ├── feishu_adapter.py    # Feishu/Lark adapter
│   ├── dingtalk_adapter.py  # DingTalk adapter
│   └── wechat_adapter.py    # WeChat adapter
├── llm/                     # LLM provider layer
│   ├── base.py              # LLMProvider ABC
│   ├── openai_provider.py   # OpenAI-compatible (+ DeepSeek, Qwen)
│   ├── anthropic_provider.py # Claude
│   └── router.py            # LLMRouter with strategies
├── core/                    # Agent core engine
│   ├── engine.py            # ReAct loop
│   ├── context.py           # Context builder
│   ├── memory.py            # 4-tier memory system
│   └── sub_agent.py         # Sub-agent manager
├── tools/                   # Tool system
│   ├── base.py              # BaseTool ABC
│   ├── registry.py          # ToolRegistry
│   ├── mcp_bridge.py        # MCP protocol bridge
│   └── builtin/             # Built-in tools
│       ├── bash_tool.py
│       ├── file_tools.py
│       ├── web_tools.py
│       ├── python_exec.py
│       └── cron_tool.py
├── rag/                     # RAG pipeline
│   ├── pipeline.py          # End-to-end RAG
│   ├── loader.py            # Document loaders
│   ├── splitter.py          # Text splitters
│   ├── embedder.py          # Embedding providers
│   ├── vector_store.py      # Vector DB (ChromaDB)
│   └── reranker.py          # Result reranking
└── evaluation/              # Evaluation framework
    ├── suite.py             # EvaluationSuite
    ├── evaluators.py        # Dimension evaluators
    └── metrics.py           # Score, EvalCase, EvalReport
```

## Configuration

All configuration via `.env` file or environment variables. See [.env.example](.env.example).

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| Web Framework | FastAPI + uvicorn |
| CLI | Typer + Rich |
| LLM | OpenAI SDK, Anthropic SDK |
| Vector DB | ChromaDB |
| Database | SQLite (aiosqlite) |
| Logging | structlog |
| Config | Pydantic Settings |
| MCP | Official MCP Python SDK |

## License

MIT
