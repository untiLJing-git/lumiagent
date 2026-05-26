# LumiAgent

[English](README.md)

LumiAgent 是一个 Agent Trace / Eval Core，用于记录、回放、评估和诊断 Agent Run。

当前 MVP 聚焦于框架无关的 Trace 数据底座：一次 Agent Run 会被表达为包含事件、产物、评估和诊断结果的嵌套 Span Tree。第一阶段应用方向是 Coding Agent 与 MCP Tool Chain 的可观测性和失败诊断。

## 为什么需要 LumiAgent

Agent 系统正在变得越来越依赖工具和工作流，但很多失败仍然很难解释：

- Agent 是否检索到了正确上下文？
- Agent 是否调用了正确工具？
- 工具参数是否生成正确？
- Agent 是否误读了工具返回结果？
- 验证步骤是否充分？
- 某个评估或诊断结论的证据来自哪些 span？

LumiAgent 从回答这些问题所需的数据底座开始：建立结构化、可回放、可评估、可诊断的 Agent Trace 模型。

## 当前状态

**第一阶段：Trace Core MVP — 已完成**

已实现能力：

- 支持嵌套 Span Tree 的 Agent Run 模型
- Span 事件与产物记录
- 支持 evidence span 引用的 Evaluation 与 Diagnosis 记录
- 稳定的 run、span、event、artifact、target、severity 枚举值
- JSON/dict 序列化与反序列化
- span ID、父子关系、target 引用、evidence span 引用的结构校验
- 便捷构造 API：`TraceBuilder`
- 通用 Agent 与 Coding Agent trace fixture

**第二阶段：MCP Tool Chain Model — 已完成**

已实现能力：

- `src/lumiagent/adapters/mcp/` 下的 MCP adapter/convention 层
- 稳定的 MCP span 与 artifact `metadata.type` 约定
- 位于通用 Trace Core 之外的 `McpFailureType` taxonomy
- 面向 schema snapshot、tool call、execution summary、failure evidence、result consumption 的轻量 MCP evidence schema
- 用于 MCP tool-chain span、artifact、result 和 failure evidence 的 builder helpers
- 成功和失败 MCP trace fixtures，覆盖 `argument_invalid`、`tool_execution_failed`、`result_misinterpreted`

产品价值：

- 保留 Agent 如何发现工具、看到 schema、生成参数、执行 MCP 工具、消费结果的结构化证据。
- 将 MCP 保持为 adapter evidence layer，使 Phase 3 Coding Agent Trace 与 Phase 4 Evaluation / Diagnosis 可以消费稳定证据，同时不污染 Core 模型。

规格与报告：

- [`docs/specs/mcp-tool-chain-model.md`](docs/specs/mcp-tool-chain-model.md)
- [`docs/reports/trace-core-mvp-technical-report.zh-CN.md`](docs/reports/trace-core-mvp-technical-report.zh-CN.md)
- [`docs/reports/mcp-tool-chain-model-technical-report.zh-CN.md`](docs/reports/mcp-tool-chain-model-technical-report.zh-CN.md)

## 快速示例

```python
from lumiagent.tracing import SpanKind, TraceBuilder, to_json

builder = TraceBuilder(name="coding agent run", input_value={"task": "fix failing test"})

agent_span = builder.start_span("Coding Agent", kind=SpanKind.AGENT)
search_span = builder.start_span(
    "Search files",
    kind=SpanKind.TOOL,
    parent_span_id=agent_span,
    metadata={"operation": "file_search"},
)
builder.end_span(search_span, output={"matches": ["src/lumiagent/tracing/models.py"]})
builder.end_span(agent_span, output={"result": "trace captured"})

run = builder.build(output={"status": "done"})
print(to_json(run))
```

## 架构

![Trace Core Model](docs/assets/trace-core-model.svg)

Mermaid 源文件：[`docs/diagrams/trace-core-model.mmd`](docs/diagrams/trace-core-model.mmd)

![MCP Tool Chain Evidence Layer](docs/assets/mcp-tool-chain-evidence-layer.svg)

Mermaid 源文件：[`docs/diagrams/mcp-tool-chain-evidence-layer.mmd`](docs/diagrams/mcp-tool-chain-evidence-layer.mmd)

Trace Core 刻意保持与具体 Agent 框架解耦。Coding Agent 支持、MCP Tool Chain 捕获、SDK hooks、CLI wrappers 和 transcript importers 都应作为核心模型之上的适配层实现。

MCP Tool Chain 层是 adapter evidence layer：它记录工具发现、schema snapshot、参数生成、权限、执行结果、失败证据和结果消费，同时不向 Trace Core 添加 MCP 专用字段。

## 路线图

### MVP 阶段（近期）

- [x] Trace Schema / Span Tree Core
- [x] MCP Tool Chain evidence model
- [ ] MCP 采集 + 展示链（统一 `CaptureStrategy` 入口）
- [ ] Coding Agent trace model + Claude Code hooks 采集 + CLI Viewer
- [ ] Evaluation / Diagnosis Agent（基于 LumiAgent 自身 Agent 基础设施）
- [ ] Replay / Visualization 数据准备

### 未来阶段

- [ ] 采集 SDK + MCP Proxy
- [ ] Web UI
- [ ] 专家知识库 + 高级诊断
- [ ] 多 Agent 可视化 + 性能优化

当前 MVP 的非目标：

- 通用 LangSmith/Langfuse 克隆
- Prompt 管理平台
- 通用 RAG 评估平台
- 完整多 Agent 编排框架

## 项目结构

```text
src/lumiagent/
├── adapters/
│   └── mcp/
│       ├── __init__.py
│       ├── builder.py
│       ├── conventions.py
│       ├── schemas.py
│       └── taxonomy.py
└── tracing/
    ├── __init__.py
    ├── builder.py
    ├── enums.py
    ├── models.py
    ├── serializer.py
    └── validator.py

tests/
├── adapters/mcp/
│   ├── fixtures/
│   ├── test_fixtures.py
│   ├── test_mcp_builder.py
│   ├── test_schemas.py
│   └── test_taxonomy.py
└── tracing/
    ├── fixtures/
    ├── test_builder.py
    ├── test_models.py
    ├── test_serializer.py
    └── test_validator.py

docs/
├── reports/
│   ├── trace-core-mvp-technical-report.zh-CN.md
│   └── mcp-tool-chain-model-technical-report.zh-CN.md
└── specs/
    └── mcp-tool-chain-model.md
```

## 安装

```bash
pip install -e ".[dev]"
```

要求 Python 3.11+。

## 验证

```bash
python -m pytest -v
python -m ruff check src/lumiagent/tracing src/lumiagent/adapters tests/tracing tests/adapters
python -m mypy src/lumiagent/tracing src/lumiagent/adapters
```

如果当前环境没有以 editable mode 安装本项目，可以使用本地源码路径运行：

```powershell
$env:PYTHONPATH = "src"
python -m pytest -v
python -m ruff check src/lumiagent/tracing src/lumiagent/adapters tests/tracing tests/adapters
python -m mypy src/lumiagent/tracing src/lumiagent/adapters
```

## 技术栈

| 领域 | 技术 |
| --- | --- |
| 语言 | Python 3.11+ |
| 数据模型 | Pydantic v2 |
| 测试 | pytest |
| Lint | ruff |
| 类型检查 | mypy |

## 许可证

MIT
