# Trace Core MVP 技术实现报告

## 1. 实现背景

本次实现对应 LumiAgent 第一版需求规格：Trace Core MVP。该阶段目标不是接入真实 Agent、MCP Server 或前端 UI，而是先建立 LumiAgent 的通用 Agent Trace / Eval Core 数据底座。

本次实现完成后，LumiAgent 已经可以用统一模型表达一次 Agent Run，并支持 Span Tree、Event、Artifact、Evaluation、Diagnosis、JSON 序列化、结构校验、便捷构造 API 和示例 trace fixture。

## 2. 技术选型

### 2.1 Python 3.11+

Trace Core 继续采用 Python，原因是 LumiAgent 后续需要接入 Agent、LLM、RAG、MCP 和评测生态，而这些生态在 Python 中最成熟。Python 也更适合快速构建评测、诊断、fixture 和 SDK 型能力。

### 2.2 Pydantic v2

核心数据模型使用 Pydantic v2，主要考虑：

- 能够清晰定义结构化数据模型；
- 支持字段默认值、枚举、嵌套模型和验证器；
- 与当前项目已有模型风格一致；
- 后续可直接服务 CLI、API、fixture、UI view model 等 JSON 数据流。

### 2.3 标准库优先

Trace Core 只依赖标准库和 Pydantic，没有依赖 LLM、RAG、MCP、FastAPI、ChromaDB 等外部业务模块。这样可以保证：

- Core 足够轻量；
- 后续适配器不会污染核心模型；
- 测试不依赖外部服务；
- Trace 数据模型可以独立复用。

### 2.4 pytest / ruff / mypy

测试和质量验证使用：

- `pytest`：验证模型、序列化、校验器、builder 和 fixtures；
- `ruff`：统一导入排序、语法风格和静态 lint；
- `mypy`：验证 tracing 包的类型正确性。

## 3. 语法规范与代码风格

本次实现遵循项目现有 Python 风格：

- 所有模块使用 `from __future__ import annotations`；
- 枚举使用 Python 3.11 的 `StrEnum`；
- 数据模型使用 Pydantic `BaseModel`；
- 使用 `Field(default_factory=...)` 避免可变默认值问题；
- 使用 `field_validator` 和 `model_validator` 表达局部字段和跨字段约束；
- 使用 `datetime.UTC` 生成 timezone-aware UTC 时间；
- 使用 `X | None` 类型写法，符合 Python 3.11 风格；
- 行宽遵循 ruff 配置的 100 字符限制；
- `tracing` 模块不反向依赖 `llm`、`tools`、`rag`、`platform` 等业务模块。

## 4. 模块设计

本次新增独立包：

```text
src/lumiagent/tracing/
├── __init__.py
├── builder.py
├── enums.py
├── models.py
├── serializer.py
└── validator.py
```

### 4.1 `enums.py`

负责定义 Trace Core 的稳定枚举：

- `RunStatus`
- `SpanStatus`
- `SpanKind`
- `EventLevel`
- `ArtifactKind`
- `TargetType`
- `Severity`

这些枚举让 JSON 输出和后续 UI/API 使用稳定字符串值，避免散落 magic string。

### 4.2 `models.py`

负责定义核心数据模型：

- `AgentRun`
- `Span`
- `Event`
- `Artifact`
- `Evaluation`
- `Diagnosis`

其中 `Span` 是核心对象，支持通过 `children` 形成 Span Tree。

`Evaluation` 和 `Diagnosis` 不是外置临时结构，而是 Trace Core 的一等对象。这样后续评测和诊断结果可以直接追溯到对应 run/span 及 evidence span。

### 4.3 `serializer.py`

负责提供稳定 JSON/dict round-trip：

- `to_dict`
- `to_json`
- `from_dict`
- `from_json`

序列化策略：

- 枚举输出为字符串；
- datetime 输出为 ISO 8601 UTC 字符串；
- JSON 结构可作为后续 UI、fixture、CLI、API 的统一数据格式。

### 4.4 `validator.py`

负责结构校验，不负责业务评测。

当前校验能力包括：

- root span 不允许有 parent；
- span_id 在 run 内唯一；
- span.run_id 必须与 AgentRun 一致；
- parent_span_id 必须存在；
- children 的 parent_span_id 必须指向父 span；
- evaluation / diagnosis 的 target_id 必须存在；
- evidence_span_ids 必须指向已有 span。

### 4.5 `builder.py`

提供最小便捷构造 API：

- `TraceBuilder.start_span`
- `TraceBuilder.end_span`
- `TraceBuilder.add_event`
- `TraceBuilder.add_artifact`
- `TraceBuilder.add_evaluation`
- `TraceBuilder.add_diagnosis`
- `TraceBuilder.build`

Builder 的定位是降低手写 Span Tree 的成本，但第一版没有引入 async context manager，避免过早复杂化。

## 5. 代码设计模式

### 5.1 Core / Adapter 分离

本次只实现 Trace Core，不实现 Coding Agent Adapter、MCP Proxy、LangChain Adapter 或 Claude Code Hooks。

这样可以保证：

```text
Trace Core 是稳定底座；
Coding Agent / MCP 只是未来适配层；
业务接入不会污染核心模型。
```

### 5.2 Composite：Span Tree

`Span.children` 形成天然的组合结构。一次 Agent Run 可以表示为：

```text
AgentRun
└── Span(agent)
    ├── Span(rag)
    ├── Span(llm)
    ├── Span(tool)
    └── Span(evaluator)
```

这种结构适合后续：

- Trace Replay UI；
- Timeline View；
- Span Detail Panel；
- Failure Diagnosis；
- Trace Diff。

### 5.3 Builder Pattern：TraceBuilder

`TraceBuilder` 用于顺序构建 Agent Run。它把创建 span、添加 artifact/event/evaluation/diagnosis 的细节封装起来，降低调用方手工维护嵌套结构的成本。

### 5.4 Validator Pattern：独立结构校验器

结构校验被放在独立 `validator.py`，而不是全部塞进 Pydantic model validator。这样做的原因是：

- Pydantic 适合单对象局部约束；
- run 级别结构约束需要跨整个 Span Tree 检查；
- 后续可以扩展更复杂的 validator，而不污染模型定义。

## 6. 实现亮点

### 6.1 Trace 数据模型已经具备后续扩展基础

本次模型不是只记录 LLM request，而是从一开始就支持：

- LLM
- Tool
- RAG
- Memory
- Evaluator
- Fallback
- Error
- Custom

这保证了 LumiAgent 后续可以继续扩展 Coding Agent Trace、MCP Tool Chain Observability 和 Evaluation/Diagnosis Engine。

### 6.2 Evaluation / Diagnosis 具备 evidence span 追溯能力

`Evaluation` 和 `Diagnosis` 都支持 `evidence_span_ids`，并由 validator 校验引用存在。

这让后续诊断报告可以回答：

```text
这个判断依据来自哪几个 span？
```

这对 Agent 评测和失败归因非常重要。

### 6.3 示例 fixture 覆盖通用 Agent 与 Coding Agent

本次新增两个 fixture：

```text
tests/tracing/fixtures/generic_agent_run.json
tests/tracing/fixtures/coding_agent_trace_sample.json
```

其中 Coding Agent fixture 使用通用 span kind 和 metadata 表达：

- file_search
- file_read
- code_edit
- shell_command
- test_run

这证明第一版通用模型已经能够表达 Coding Agent 基础流程，同时没有过早污染 `SpanKind`。

### 6.4 结构校验和类型检查都已通过

本次实现不仅通过单元测试，还通过：

- `ruff check src/lumiagent/tracing tests/tracing`
- `mypy src/lumiagent/tracing`

说明 Trace Core 的语法、类型和结构质量达到当前阶段要求。

## 7. 验证结果

已执行并通过：

```text
pytest -v
18 passed
```

已执行并通过：

```text
python -m ruff check src/lumiagent/tracing tests/tracing
All checks passed
```

已执行并通过：

```text
python -m mypy src/lumiagent/tracing
Success: no issues found in 6 source files
```

## 8. 风险与取舍

### 8.1 当前只做结构校验，不做业务评测

本次 validator 只保证 trace 结构合法，不判断：

- 工具是否选对；
- 参数是否正确；
- 是否测试充分；
- 是否存在风险命令。

这些属于后续 Evaluation / Diagnosis Engine 的职责。

### 8.2 Coding Agent / MCP 只通过 fixture 体现

第一版没有实现真实 Coding Agent Adapter 或 MCP Proxy，这是刻意取舍。原因是：

```text
没有稳定 Trace Core，后续接入都会变成一次性逻辑。
```

### 8.3 当前环境使用 Anaconda 全局环境

本次执行 `pip install -e .` 和 `pip install -e .[dev]` 时，当前 Anaconda 环境中的部分依赖被升级，并出现了与 Jupyter/Anaconda 生态相关的依赖冲突提示。代码和测试最终通过，但后续建议使用独立虚拟环境，避免污染全局 Python 环境。

## 9. 后续建议

### 9.1 短期建议

下一阶段建议进入：

```text
MCP Tool Chain Model
```

但在实现前应先定义阶段需求规格，明确：

- MCP server connection span；
- tool discovery span；
- tool schema；
- tool call / result；
- permission / error / latency；
- 与现有 Span Tree 的映射方式。

### 9.2 工程建议

建议后续补充：

- 独立虚拟环境使用说明；
- 更轻量的 dev dependency 安装方式；
- CI 流程；
- `tests/fixtures` 的 schema snapshot 校验；
- Trace JSON schema 导出能力。

### 9.3 设计建议

后续不要急于增加大量专用 SpanKind。对于 Coding Agent 和 MCP 细分动作，可以先通过：

```text
kind = tool/custom
metadata.operation = xxx
```

表达。等模式稳定后，再考虑提升为一等枚举。

## 10. 总结

本次实现完成了 LumiAgent Trace Core MVP 的核心地基：

```text
AgentRun + Span Tree + Event + Artifact + Evaluation + Diagnosis
```

它为后续 MCP Tool Chain、Coding Agent Trace、Trace Replay UI、Evaluation Engine 和 Diagnosis Engine 提供了稳定的数据模型基础。
