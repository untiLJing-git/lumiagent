# Coding Agent Trace Model 技术报告

## 背景与目标

Phase 3 建立框架无关的语义 Coding Agent Trace Model，并以 Claude Code hooks 与最小 transcript enrichment 作为首个真实 Coding Agent 采集适配路径。目标是证明 Coding Agent 从用户请求、任务理解、上下文收集、工具动作、代码修改、验证、失败恢复、结果解释到最终回复的过程，可以被结构化采集、归一化、转换、预检和查看。

本阶段延续 LumiAgent 的产品定位：trace 是一等产品数据，Coding Agent 与 MCP 只是建立在通用 Agent Trace / Eval Core 之上的首批应用场景。本阶段没有把核心模型绑定到 Claude Code、LangChain、LangGraph 或任何单一 Agent 框架。

## 需求范围

本阶段实现：

- Coding Agent trace conventions。
- action evidence 与 semantic evidence schema。
- 最小 `BuilderTraceWriter`，用于增量 hooks capture 到 `AgentRun`。
- Claude Code hook event schema、JSONL reader/writer、hook entrypoint、setup helper 和 converter。
- best-effort transcript enrichment。
- deterministic workflow validator。
- `lumiagent trace`、`lumiagent show --checks`、`lumiagent setup claude-code` CLI 集成。
- synthetic coding fixtures 与 sanitized real session fixture。
- sanitizer 与 raw capture `.gitignore` 保护。

本阶段不实现：

- Phase 4 Evaluation / Diagnosis Engine。
- LLM-based diagnosis、score 或复杂 suggested fix。
- 完整 Claude Code 内部 transcript 解析。
- Phase 2b `McpTraceMapper` 迁移。
- Web UI、TUI、Replay ViewModel、trace diff、SDK decorator、MCP proxy、数据库 writer 或实时流式服务。

## 架构设计

核心链路：

```text
Claude Code hooks events + optional transcript enrichment
  -> normalized Coding Agent events
  -> BuilderTraceWriter
  -> AgentRun
  -> WorkflowValidator
  -> CLI trace review
```

模块边界：

- `src/lumiagent/adapters/coding/`：框架无关的 Coding Agent 语义层，包含 conventions、schemas、normalizer、validator 和 viewer。
- `src/lumiagent/adapters/claude_code/`：Claude Code 专属采集适配层，包含 hook event schema、hook entrypoint、setup、transcript enrichment、sanitizer 和 converter。
- `src/lumiagent/tracing/builder_writer.py`：最小 TraceWriter 实现，内部复用既有 TraceBuilder。
- `src/lumiagent/cli.py`：只做 CLI 编排和 viewer routing，不承载 trace 语义。

此边界保证 Coding Agent 语义不依赖 Claude Code 内部格式，Claude Code 适配器也不会污染 Trace Core。MCP capture 继续保留在既有 mapper 路径上，没有被强制迁移到 TraceWriter。

## 技术选择

- 使用 Pydantic 表达 hook event、normalized event、action evidence、semantic evidence 和 workflow finding schema。
- 使用 span metadata 的 `domain/type/source/source_event_ids/evidence_types` 承载 Coding Agent 语义，避免新增大量 Core `SpanKind`。
- 使用 artifacts 保存结构化 action/semantic/workflow evidence，让 span tree 保持可浏览，同时保留机器可读证据。
- 使用 deterministic workflow rules 完成高信心预检，不引入 LLM 诊断，避免越界到 Phase 4。
- transcript enrichment 采用 best-effort 策略；hook-only trace 是最低可靠闭环。
- sanitizer 采用递归结构清洗、token-like key redaction、文本 pattern redaction 和项目路径替换，保证 committed fixture 不包含本地 raw capture 信息。

## 语法与风格规则

- Python 代码使用 `from __future__ import annotations`，类型注解优先。
- Pydantic model 使用 `ConfigDict(extra="forbid")` 约束 schema 外字段。
- 测试文件名避免与既有 MCP/tracing 测试模块同名，防止 pytest import mismatch。
- Claude Code setup 只合并兼容的 settings shape；遇到已有不兼容 hooks shape 时显式失败，不静默覆盖用户配置。
- hook payload 进入 LumiAgent-owned events 前进行 redaction，事件 safety 标记为 `redacted`。

## 设计模式与实现亮点

### 语义归一化

`normalizer.py` 将 source-specific 工具事件映射为稳定 Coding Agent conventions：`file_search`、`file_read`、`code_edit`、`shell_command`、`test_run`、`verification`、`git_diff`、`permission_request`、`approval_decision` 等。

真实 Claude Code hook payload 使用 `tool_input` / `tool_response`，实现中已兼容该形态，同时保留旧测试中的 `arguments` / `result` 结构，保证 synthetic fixture 与真实 hook 输入都能被正确分类。

### Pre/Post 工具调用配对

Claude Code 一次工具调用可能产生 `PreToolUse` 与 `PostToolUse` 两个事件。converter 在写入 span 前进行相邻 request/result 配对，输出单个 action span，并在 metadata 中保留两个 source event id，避免一个工具调用生成两个误导性 span。

### Claude Code Hook Activation Flow

`setup.py` 将 Claude Code hook 配置与当前会话 activation 检查拆开处理。`configure_claude_code_hooks()` 负责安全合并 `.claude/settings.json`，注册 `PreToolUse`、`PostToolUse`、`PostToolUseFailure` 和 `PermissionRequest`；`inspect_claude_code_hook_activation()` 只读取环境变量和 `.lumiagent/sessions/<session-id>/events.jsonl`，用于判断当前会话是否真的已经触发 hooks。

activation 状态分为三类：

- `active`：当前 Claude Code session 已存在非空 events JSONL，说明 hooks 已在本会话写入事件。
- `needs_reload`：检测到 session id，但 events 文件不存在或为空，说明 settings 可能已配置但当前运行中的 Claude Code 尚未热加载 hooks；用户需要打开 `/hooks` 后关闭，或重启 Claude Code，再触发任意工具调用并运行 `lumiagent setup claude-code --verify`。
- `not_in_claude_code`：未检测到 `CLAUDE_CODE_SESSION_ID` 或 `LUMIAGENT_SESSION_ID`，只能确认 settings 写入，无法判断运行时 activation。

该设计避免把“配置已写入”等同于“当前会话 hooks 已生效”，也为真实采集验证提供了可重复的检查路径。

### Workflow Validator

workflow validator 以 `AgentRun` 为输入，不依赖 Claude Code adapter。当前规则覆盖：

- code edit 后缺少 test/verification。
- failed test 后缺少 recovery。
- failed shell command 后缺少 recovery。
- denied approval 后仍执行 risky action。
- unresolved error 后直接 final response。

检查结果写入 `workflow_check` span 的 JSON artifact，定位为 workflow review finding，而不是 Phase 4 的 evaluation/diagnosis record。

### CLI 集成

- `lumiagent trace <session-id> -o trace.json`：从 `.lumiagent/sessions/<session-id>/events.jsonl` 转换为 AgentRun JSON。
- `lumiagent show trace.json --checks`：根据 trace domain 自动路由 Coding Agent viewer 或 MCP viewer。
- `lumiagent setup claude-code`：安全合并 Claude Code hooks 配置。

## 验证结果

Task 15 已运行以下全量验证命令：

```powershell
$env:PYTHONPATH = "src"; python -m pytest -v
```

结果：`157 passed in 0.68s`。

```powershell
$env:PYTHONPATH = "src"; python -m ruff check src/lumiagent/tracing src/lumiagent/adapters src/lumiagent/capture tests/tracing tests/adapters tests/capture tests/test_cli_coding_trace.py
```

结果：`All checks passed!`。

```powershell
$env:PYTHONPATH = "src"; python -m mypy src/lumiagent/tracing src/lumiagent/adapters src/lumiagent/capture
```

结果：`Success: no issues found in 34 source files`。

Task 13 针对 sanitizer、hooks、fixtures、validator 和 viewer 的局部验证结果为 `21 passed in 0.15s`。

CLI trace smoke test：

```powershell
$env:PYTHONPATH = "src"; python -m lumiagent.cli trace session_1 -o .lumiagent/traces/session_1-raw.json
```

结果：

```text
Trace written: .lumiagent\traces\session_1-raw.json
Workflow checks: pass
Transcript enrichment: unavailable
```

CLI show smoke test：

```powershell
$env:PYTHONPATH = "src"; python -m lumiagent.cli show .lumiagent/traces/session_1-raw.json --checks
```

结果包含：

```text
Semantic Summary
Span Tree
Workflow Checks
  status: pass
  findings: none
```

验证过程中发现 PowerShell `Set-Content -Encoding utf8` 在当前环境会写入 BOM，导致 JSONL 首行解析失败。最终改用 Python `Path.write_text(..., encoding="utf-8")` 生成 smoke test JSONL，确认 CLI trace/show 均可正常执行。

最终 diff 审查补充了真实 Claude Code 采集场景校验：`setup claude-code` 现在注册 `PreToolUse`、`PostToolUse`、`PostToolUseFailure` 和 `PermissionRequest`，覆盖已实现的工具请求、工具结果、失败结果和权限请求语义；converter 已验证 `PermissionRequest` 夹在 `PreToolUse` 与 `PostToolUse` 之间时不会打断工具调用配对。独立只读审查未发现真实采集路径阻塞问题。

真实 Hooks 采集验证补充：用户打开 `/hooks` 后，当前 Claude Code 会话已热加载 `.claude/settings.json`。随后触发真实 `Read`、`PowerShell` 等工具调用，hook 自动写入 `.lumiagent/sessions/99e84769-efe0-409d-a660-8fc33a8cab6c/events.jsonl`，再运行 `lumiagent trace 99e84769-efe0-409d-a660-8fc33a8cab6c` 和 `lumiagent show ... --checks`，生成 `.lumiagent/traces/99e84769-efe0-409d-a660-8fc33a8cab6c-raw.json`。输出包含 `Context Gathering`、`Read file`、`Request permission`、`Workflow Checks status: pass`。此前还通过 hook entrypoint pipe-test 生成 `.lumiagent/sessions/real-hook-pipe-test/events.jsonl`，验证 hook stdin payload 到 trace/show/checks 的闭环。为降低用户误解，`lumiagent setup claude-code` 现在会输出当前 session activation 状态；`lumiagent setup claude-code --verify` 可单独检查 `active`、`needs_reload` 或 `not_in_claude_code`，当需要热加载时会提示打开 `/hooks` 或重启 Claude Code。

真实 session transcript 验证补充：自动 hook payload 中提供了主 session transcript 路径 `C:/Users/Administrator/.claude/projects/D--Projects-github-lumiagent/99e84769-efe0-409d-a660-8fc33a8cab6c.jsonl`。使用该真实 transcript 运行 `--transcript-path` 后，enrichment 成功提取 `user_prompt`、`task_understanding`、`final_response`，并与真实自动 hooks events 共同转换为 `.lumiagent/traces/99e84769-efe0-409d-a660-8fc33a8cab6c-transcript-raw.json`。`lumiagent show ... --checks` 输出包含 Semantic Summary、Span Tree、Workflow Checks。中文乱码问题已通过 CLI stdout/stderr UTF-8 reconfigure 修复，真实输出可以正确显示中文。PowerShell 测试命令前缀 `$env:PYTHONPATH = "src";` 曾导致 test_run 识别漏判，已通过 token 序列匹配修复；最终真实 transcript + hooks trace 输出 `Workflow Checks status: pass`、`findings: none`。subagent transcript `C:\Users\Administrator\.claude\projects\D--Projects-github-lumiagent--claude-worktrees-phase3-coding-agent-trace-model\99e84769-efe0-409d-a660-8fc33a8cab6c\subagents\agent-a72a3b5a8e236e1f7.jsonl` 也已验证 enrichment 成功并输出 `pass`。

## 风险与权衡

- Claude Code hook payload 可能随版本变化；当前实现兼容真实 `tool_input/tool_response` 和内部 synthetic `arguments/result`，但未来仍需通过 fixtures 捕捉变更。
- transcript enrichment 不是稳定合同；因此它只提供 semantic evidence 增强，不能阻塞 hooks-only trace。
- sanitizer 是防护层而不是密钥扫描器；raw capture 仍必须只保存在本地 `.lumiagent/`，不能提交。
- workflow validator 是 deterministic pre-check，可能存在误报或漏报；结果只作为 workflow checks，不输出最终诊断结论。
- setup helper 为了保护用户配置，对不兼容 hooks shape 选择显式失败而非自动修复；这牺牲了一点自动化便利性，但避免静默删除用户已有配置。

## 后续建议

- Task 15 继续补充 CLI smoke test，并将 smoke test 结果追加到本报告。
- Phase 4 Diagnosis Agent 可消费 workflow checks 作为 deterministic evidence，而不是重新推断基础工作流问题。
- Phase 5 Replay / Visualization 可基于 semantic summary、span tree 和 workflow_check artifact 构建 view model。
- 后续可评估更多 Coding Agent capture sources，但应保持 `adapters/coding/` 的框架无关边界。
