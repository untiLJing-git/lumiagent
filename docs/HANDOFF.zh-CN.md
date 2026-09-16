# LumiAgent 后续工作交接记录

本文档用于在不同设备或新的 Claude Code 会话中继续 LumiAgent 开发时快速恢复上下文。

## 当前项目

- 本地路径：`D:\Projects\github\lumiagent`
- GitHub 仓库：`untiLJing-git/lumiagent`
- 当前主分支：`main`
- 当前主分支阶段：Phase 3 Coding Agent Trace Model 已完成
- 当前文档进展：2026-09-15 已形成 Phase 4 加强版规格初稿，待评审；任务来源已收集，A1 六个 instance 已写入 `benchmarks/eval-suite/sources/a1_selection.json`；尚未构造 `task.json`，P4-P 已实现并完成本地验收，旧 eval 已隔离；P4-A1/A2/B1/B2 尚未实现。

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
5. `ClaudeCodeHooksStrategy` 已在 `PROJECT_SPEC` 第 7.6 节明确为开放预留：hooks 采集路径保持有效，strategy 门面延后，不阻塞 Phase 4。
6. README 已拆成中英文并更新到 Phase 3 状态：
   - `README.md`
   - `README.zh-CN.md`
7. 架构图使用 Mermaid 源文件和 SVG：
   - `docs/diagrams/*.mmd`
   - `docs/assets/*.svg`
   - Phase 3 新增：`coding-agent-capture-flow.mmd` / `coding-agent-capture-flow.svg`
8. 关键规格与报告：
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

## 预留但不阻塞 Phase 4 的路径

- `ClaudeCodeHooksStrategy` 保持开放预留。Claude Code 官方 hooks 仍是文档化产品能力；Phase 3 已用 hooks 写入 `events.jsonl` 再 converter 成 `AgentRun`。
- 预留的是 CaptureStrategy 门面，不是另一套采集机制。不要关掉 hooks 路径，也不要在 Phase 4 之前实现这个类。
- 后续若补 strategy，应复用 `ClaudeCodeTraceConverter` / `TraceWriter`，并可评估订阅 `UserPromptSubmit`、`Stop`、`SessionStart`、`SessionEnd` 以减少对 transcript 的依赖。

## Phase 4 规格与下一步

正式需求入口：[Phase 4 加强版规格](specs/evaluation-diagnosis-engine.md)。P4-P 已人工评审、实现及本地验收；其余四批仍待评审/未实现。同步更新了中英文项目总规格和 README，并标记早期路线文档中的冲突要求。

2026-09-15 已收集 Phase 4 任务来源：公开索引在 [`benchmarks/eval-suite/sources/`](../benchmarks/eval-suite/sources/)，完整 parquet/jsonl 与上游 clone 在本地 `.lumiagent/sources/`（已 gitignore）。A1 选定见 [`a1_selection.json`](../benchmarks/eval-suite/sources/a1_selection.json)。这不是 6/24 个任务资产已验收。

实施顺序：

1. P4-P 已完成；下一步评审并按授权执行 P4-A1。来源收集可与 P4-P 并行，按 SOURCE_CATALOG 选定 6 个 instance。
2. P4-P（已完成）：证据引用、同名调用关联、源时序与能力声明、legacy eval 隔离。
3. P4-A1：任务、Trial、真实 Agent runner、独立 verifier 和 6 个任务。
4. P4-A2：技能化 Evaluation、证据审计、24 个任务及真实多步 MCP 验收。
5. P4-B1：Diagnosis、48 条审核轨迹、留出校准及简单基线对照。
6. P4-B2：两个不同层级的受控改进实验、最小 Experiment 和复跑比较。

必须保留的边界：

- 不先实现自己的 Coding Agent；优先复用现有 Claude Code hooks 路径。
- 不要求实现 `ClaudeCodeHooksStrategy`，不替换现有 hooks 采集源。
- Evaluation 不等于规则，Diagnosis 不等于 LLM；二者均需可验证证据。
- 离线审计不自动执行命令；未知结果不算成功。
- 原始 trace 不覆盖；报告级引用用于跨 run 证据。
- ReActEngine 等按需复用；旧 EvaluationSuite 不作为新评测基础。
- 最小 Trial/Experiment 属于 Phase 4；Phase 5 复用其数据生成 view model。

P4-P 已通过反例测试修复引用失效、同名调用误配、树序与源时序混用，以及转换时间被当作源时间的问题。历史缺失证据不会补造：v1 或部分 trace 可读，但相应预检显示 unknown。

文档入口：[Phase 4 总实施计划](superpowers/plans/2026-09-15-phase4-implementation-roadmap.md)。五个批次各有一份设计与一份实施计划，P4-P 任务已执行，其余批次未执行；正式需求仍以 `docs/specs/evaluation-diagnosis-engine.md` 为准。

`docs/reports/` 只存放阶段实现技术报告。前次错误放入的规格交付记录已移除；Phase 4 报告要等各批实现并验证后创建，不生成占位文件。

## P4-P 当前实现与验证（2026-09-15）

- 实际报告：[P4-P 证据就绪与旧评测隔离技术报告](reports/phase4-evidence-readiness-technical-report.zh-CN.md)。
- 最终 pytest：225 passed、1 个既有 asyncio_mode 配置警告；ruff 通过；mypy 38 个主线文件通过。
- 11 个已提交 fixtures Core 往返和原文件只读检查通过；已执行计划指定真实脱敏 fixture 的 show --checks。
- 旧包为 `lumiagent.legacy_eval`，命令为 `lumi legacy-eval`；`lumi eval` 只提示迁移并退出 2，不初始化 Agent。
- 已提交 JSON fixtures、Trace Core 与既有 MCP 实现保持不变。sanitizer 复用已有实现；缺 ID 配对等旧测试补足可信前提，未知路径单独覆盖。
- 首次 P4-P 验收未新开外部会话；2026-09-15 随后经授权补充了 Flask-5014 的真实 Claude Code 验证，见下节。来源收集和 A1 正式任务资产仍单独管理。
- 未提交 Git，未启动 P4-A1。原有 Phase 3 的 163 测试记录是历史基线，不代表当前 P4-P 的结果。

## P4-P 真实会话补充验证（2026-09-15）

- 任务：已选实例 `pallets__flask-5014`；Claude Code 2.1.236，只在独立副本编辑一个文件，禁用 shell/MCP/子 Agent。
- 有效基线 1 failed / 59 passed；候选补丁审核后独立验证 60 passed。宿主 Python 3.13 的两条 pkgutil 弃用警告采用相同的前后兼容规则，不是官方 harness 成绩。
- 7 条真实 hooks，3 对调用 + 1 条被 PreToolUse 门禁拒绝的 Read 请求；无错误配对，Core 与证据审计通过。
- hooks 无源时间/序号，流程检查 unknown、覆盖 partial；原生 CLI success 和独立测试通过没有被混成流程 pass。当前 hooks-only RunStatus=pending 不应作为任务失败依据，A1 需独立记录真实生命周期和门禁结果。
- 本地材料：`.lumiagent/benchmarks/p4p-real-flask-5014-20260915/`；可运行其中 replay_validate.py 离线重放，无模型费用。
- 详细结果与范围见 [P4-P 技术报告](reports/phase4-evidence-readiness-technical-report.zh-CN.md) 第 10 节。没有据此标记 P4-A1 完成，也未提交原始材料。

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
