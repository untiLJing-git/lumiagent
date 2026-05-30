# LumiAgent 后续工作交接记录

本文档用于在不同设备或新的 Claude Code 会话中继续 LumiAgent 开发时快速恢复上下文。

## 当前项目

- 本地路径：`D:\Projects\github\lumiagent`
- GitHub 仓库：`untiLJing-git/lumiagent`
- 当前主分支：`main`
- 当前主分支阶段：Phase 3 Coding Agent Trace Model 已完成

## 已完成内容

1. 第一阶段 Trace Core MVP 已完成并合入 `main`。
   - `AgentRun`、`Span`、`Event`、`Artifact`、`Evaluation`、`Diagnosis`、`Annotation`
   - JSON/dict 序列化、结构校验、`TraceBuilder`
   - `BuilderTraceWriter` 最小增量 writer
2. 第二阶段 A：MCP Tool Chain Evidence Model 已完成。
   - MCP conventions、taxonomy、schemas、builder helpers
   - MCP 成功与失败 fixtures
3. 第二阶段 B：MCP Capture + Display Chain 已完成。
   - `CaptureStrategy`
   - `McpClientRuntime` / `StdioMcpClientRuntime`
   - `ExplicitToolSelector`
   - `McpCaptureStrategy` / `McpTraceMapper`
   - `lumiagent capture mcp` 与 `lumiagent show`
4. 第三阶段：Coding Agent Trace Model 已完成。
   - `src/lumiagent/adapters/coding/`：framework-agnostic Coding Agent conventions、schemas、normalizer、validator、viewer
   - `src/lumiagent/adapters/claude_code/`：hooks、setup、events、transcript enrichment、converter、sanitizer
   - Claude Code hooks capture：`PreToolUse`、`PostToolUse`、`PostToolUseFailure`、`PermissionRequest`
   - hook activation 状态：`active`、`needs_reload`、`not_in_claude_code`
   - `lumiagent trace <session-id>` 与 `lumiagent show --checks`
   - synthetic coding fixtures 与 sanitized real Claude Code fixture
5. README 已拆成中英文并更新到 Phase 3 状态：
   - `README.md`
   - `README.zh-CN.md`
6. 架构图使用 Mermaid 源文件和 SVG：
   - `docs/diagrams/*.mmd`
   - `docs/assets/*.svg`
   - Phase 3 新增：`coding-agent-capture-flow.mmd` / `coding-agent-capture-flow.svg`
7. 关键规格与报告：
   - `docs/specs/trace-core-mvp.md`
   - `docs/specs/mcp-tool-chain-model.md`
   - `docs/specs/mcp-capture-display-chain.md`
   - `docs/specs/coding-agent-trace-model.md`
   - `docs/reports/trace-core-mvp-technical-report.zh-CN.md`
   - `docs/reports/mcp-tool-chain-model-technical-report.zh-CN.md`
   - `docs/reports/mcp-capture-display-chain-technical-report.zh-CN.md`
   - `docs/reports/coding-agent-trace-model-technical-report.zh-CN.md`

## 当前验证状态

主分支 `main` 在 Phase 3 完成后已通过以下 fresh verification：

```powershell
$env:PYTHONPATH = "src"
python -m pytest -v
python -m ruff check src/lumiagent/tracing src/lumiagent/adapters tests/tracing tests/adapters
python -m mypy src/lumiagent/tracing src/lumiagent/adapters
```

验证结果：

```text
pytest: 163 passed
ruff: All checks passed
mypy: Success: no issues found in 32 source files
```

CLI / real-path smoke verification：

```powershell
$env:PYTHONPATH = "src"
python -m lumiagent.cli show tests/adapters/claude_code/fixtures/real_session_sanitized_trace.json --checks
```

输出包含 `Semantic Summary`、`Span Tree`、`Workflow Checks`，且 workflow status 为 `pass`。

## 后续会话需要遵守的偏好

- Git commit message 不要包含 `Claude Co-Authored-By` trailer。
- LumiAgent 每次实现完成后，都要写中文技术报告到 `docs/reports/`。
- LumiAgent 架构图优先使用 Mermaid；需要图片时用 Mermaid CLI 导出 SVG 到 `docs/assets/`。
- 每次代码或文档改动后，都要运行相关测试或验证命令。
- 不要提交本地 `.claude/settings.json`；Claude Code hooks 应通过 `lumiagent setup claude-code` 在本地生成。

## 下一步建议

下一阶段建议进入 **Phase 4: Evaluation / Diagnosis Engine**，但不要直接开始写代码。应先做需求规格和设计文档，明确：

- Diagnosis Agent 如何消费 Phase 3 `workflow_check` artifacts
- trace analysis tool set：`read_span_tree`、`inspect_span`、`extract_evidence`、`query_knowledge`、`compare_arguments`、`check_workflow_pattern`、`compare_traces`
- deterministic rule engine 与 LLM reasoning layer 的边界
- Evaluation / Diagnosis schema 输出：score、reason、evidence span、suggested fix
- 如何 dogfood：Diagnosis Agent 自身执行过程也应可被 trace 捕获

## 换设备后的建议启动命令

```bash
git clone https://github.com/untiLJing-git/lumiagent
cd lumiagent
pip install -e ".[dev]"
python -m pytest -v
```

如果不想安装 editable 包，可以临时使用：

```powershell
$env:PYTHONPATH = "src"
python -m pytest -v
```
