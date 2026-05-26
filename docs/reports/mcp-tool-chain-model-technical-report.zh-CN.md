# MCP Tool Chain Model 技术报告

## 阶段目标

本阶段建立 MCP Tool Chain Evidence Layer，用于记录 Coding Agent 使用 MCP 工具链时的结构化证据。该层不直接接入真实 MCP SDK 或 MCP Server，而是先稳定 MCP 工具链在 LumiAgent Trace Core 上的表达方式，为后续 Coding Agent Trace 与 Evaluation / Diagnosis 提供可消费证据。

## 技术选择

- 继续复用 Trace Core 的 `AgentRun / Span / Event / Artifact`。
- 在 `src/lumiagent/adapters/mcp/` 中新增 MCP adapter/convention 层。
- 使用 `metadata.type` 表达 MCP 语义，避免污染 Core enum。
- 使用 Pydantic v2 定义轻量 evidence schema。
- 使用 JSON fixtures 固化成功链路、调用前失败、执行失败和结果误读场景。

## 语法与风格规则

- Python 代码使用 `from __future__ import annotations`。
- 枚举使用 `StrEnum`，保持序列化值稳定。
- Pydantic schema 使用 `BaseModel`、`Field` 与 `field_validator` 表达轻量约束。
- MCP 相关常量集中在 `conventions.py`，避免 metadata 字符串漂移。
- Core tracing 模块保持不变，MCP 语义只存在于 adapter 层。

## 设计模式

- **Core / Adapter 分离**：`src/lumiagent/tracing/` 继续保持框架无关；MCP 语义放在 `src/lumiagent/adapters/mcp/`。
- **Convention over Core Mutation**：MCP 流程 span 使用 `SpanKind.CUSTOM + metadata.type`；实际工具执行使用 `SpanKind.TOOL + metadata.type = "mcp_tool_execution"`。
- **Artifact for Large Structured Data**：tool schema snapshot 和 tool result 放入 artifact，不塞进 span metadata。
- **Evidence-first Failure Modeling**：`McpFailureType` 只定义基础失败类型，Phase 2 记录 evidence，Phase 4 再生成完整 diagnosis。

## 实现亮点

- `McpFailureType` 覆盖连接、发现、schema、选择、参数、权限、执行、结果消费和恢复证据不足等失败类型。
- `McpToolSchemaSnapshot`、`McpToolCallInput`、`McpToolExecutionSummary`、`McpFailureEvidence`、`McpResultConsumptionEvidence` 提供轻量结构化约束。
- Builder helpers 统一生成 MCP spans、artifacts、events 和 evidence metadata。
- Fixtures 覆盖：
  - 成功 MCP flow；
  - `argument_invalid` 调用前失败；
  - `tool_execution_failed` 执行阶段失败；
  - `result_misinterpreted` 调用后结果消费错误。

## 验证结果

本阶段运行了以下命令：

```powershell
python -m pytest -v
python -m ruff check src/lumiagent/tracing src/lumiagent/adapters tests/tracing tests/adapters
python -m mypy src/lumiagent/tracing src/lumiagent/adapters
```

结果：

```text
pytest: 40 passed, 1 warning
ruff: All checks passed!
mypy: Success: no issues found in 12 source files
```

其中 pytest warning 为当前环境中的配置提示：`Unknown config option: asyncio_mode`。

## 风险与取舍

- 本阶段不接真实 MCP SDK，因此 connection/discovery 仍是 trace convention，不是 runtime capture。
- `result_misinterpreted` 只记录局部 MCP result consumption evidence，不判断完整 Coding Agent 任务成败。
- Retry/Fallback/Recovery 暂用通用 span/event 表达，后续可在 workflow recovery 层统一设计。
- 为保持 Core 稳定，本阶段没有新增 MCP-specific `SpanKind` 或 `ArtifactKind`。

## 后续建议

- Phase 3 在 Coding Agent Trace 中消费 MCP evidence layer。
- Phase 4 将 `McpFailureType` 映射为 Evaluation / Diagnosis 输出。
- 后续 MCP SDK 接入时，在 `src/lumiagent/adapters/mcp/` 下新增 runtime capture 模块，例如 SDK capture、client hooks 或 server proxy。
