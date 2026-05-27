# Trace Core MVP 兼容性补丁技术报告

## 背景

本次补丁用于对齐当前 `docs/PROJECT_SPEC.md` 中新增的 Trace Core extension points。原 Trace Core MVP 已能表达基础 AgentRun / Span Tree / Event / Artifact / Evaluation / Diagnosis，但总规格后续补充了 Annotation、Run linking、Span-level serialization 和 TraceWriter Protocol 等未来阶段依赖的稳定接口。

## 需求与范围

本次实现保持 Trace Core 现有结构稳定，只做向后兼容的增量扩展：

- 新增 `Annotation` 模型，用于表达人工审阅反馈。
- 在 `AgentRun` 上新增可选 `parent_run_id` 与 `triggered_by_span_id`。
- 在 `AgentRun` 上新增 `annotations` 列表。
- 新增单 Span 序列化 / 反序列化 helpers。
- 新增 `TraceWriter` protocol，作为未来 hooks、SDK、proxy、importer 的 Core-facing 写入接口。
- 扩展结构校验，覆盖 annotation target/evidence 与 `triggered_by_span_id`。

非目标：

- 不实现真实 capture strategy。
- 不引入持久化、数据库、UI 或 Web API。
- 不实现 `Experiment` 容器；该模型延后到 Phase 5，由 trace diff 和 comparison view model 的需求共同确定 schema。
- 不把 MCP / Coding Agent 专用字段提升进 Core。
- 不修改既有字段名或既有 fixture 结构。

## 技术选择

- 继续使用 Pydantic v2 表达数据模型。
- 继续使用标准库 `json` 与现有 `_to_jsonable` 逻辑保证 enum 与 datetime 序列化一致性。
- 使用 `typing.Protocol` 定义 `TraceWriter`，避免 Core 依赖具体 writer 实现。
- 使用可选字段和默认空列表保证旧 trace JSON 可继续反序列化。

## 实现内容

### Annotation 模型

`Annotation` 与 `Evaluation` 类似，都包含 target 与 evidence span 引用，但语义上表示人工反馈而不是自动评测结果。字段包括：

- `annotation_id`
- `target_type`
- `target_id`
- `author`
- `note`
- `label`
- `evidence_span_ids`
- `metadata`

### Run linking

`AgentRun` 新增：

- `parent_run_id: str | None`
- `triggered_by_span_id: str | None`

其中 `parent_run_id` 不在单 run 校验中解析，因为父 run 可能存储在另一个文件或未来 Experiment 容器中。`triggered_by_span_id` 在存在时必须引用当前 run 内已有 span。

### Span-level serialization

`serializer.py` 新增：

- `span_to_dict`
- `span_to_json`
- `span_from_dict`
- `span_from_json`

这些 helpers 复用与 AgentRun 相同的 enum / datetime 序列化规则，为未来 streaming writer 和 incremental append 做准备。

### TraceWriter Protocol

新增 `src/lumiagent/tracing/writer.py`，定义最小写入协议：

- `start_run`
- `start_span`
- `end_span`
- `add_event`
- `add_artifact`
- `flush`

该协议只描述 Core-facing 写入能力，不绑定内存、文件、数据库或网络实现。

## 兼容性

本次修改保持向后兼容：

- 原有 Trace Core 模型字段未删除、未重命名。
- 新增 `AgentRun` 字段都有默认值。
- 原有 JSON fixture 不需要修改即可继续加载和校验。
- 原有 `TraceBuilder` API 未改变。
- MCP adapter 仍位于 Core 外部，不受本次模型扩展影响。

## 高扩展性与边界控制

- 人工反馈进入 Core 是因为 Annotation 是跨 adapter、跨 UI、跨诊断流程都需要的通用概念。
- `TraceWriter` 只定义协议，不引入具体 capture 行为，避免 Core 与 Claude Code hooks、MCP SDK 或 CLI wrapper 耦合。
- Sanitization 仍作为 capture pipeline hook point 写入规格，不在 Core validator 中硬编码，避免影响性能和职责边界。

## 验证结果

已执行 Trace Core 局部验证：

```powershell
$env:PYTHONPATH = "src"; python -m pytest tests/tracing -v
```

结果：

```text
24 passed, 1 warning
```

后续完整验证命令将在本报告写入后执行：

```powershell
$env:PYTHONPATH = "src"
python -m pytest -v
python -m ruff check src/lumiagent/tracing src/lumiagent/adapters tests/tracing tests/adapters
python -m mypy src/lumiagent/tracing src/lumiagent/adapters
```

## 风险与权衡

- `Annotation` 字段目前保持轻量，没有引入 reviewer identity schema、thread、resolution status 等复杂协作功能，避免偏离 Trace / Eval Core。
- `TraceWriter` 目前只定义协议，没有提供 concrete writer，后续 Phase 2b/3 应按 capture strategy 的实际需求实现。
- `parent_run_id` 暂不做跨文件校验，牺牲单次校验完整性，换取独立 trace 文件的可移植性。

## 后续建议

1. Phase 2b 实现 `CaptureStrategy` 时，让具体 capture strategy 输出 `AgentRun` 并可选择实现 `TraceWriter`。
2. Phase 3 Claude Code hooks converter 可以优先使用 `TraceWriter` 协议，避免依赖 `TraceBuilder` 内部结构。
3. Phase 5 view models 可把 `annotations` 与 `evaluations` / `diagnoses` 一起投影到 diagnosis summary 和 evidence panel。
