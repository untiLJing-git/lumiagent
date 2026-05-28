# MCP Capture + Display Chain 技术报告

## 背景与产品价值

本阶段围绕 LumiAgent 的 Coding Agent 与 MCP Tool Chain 观测能力，验证从真实第三方 MCP Server 发起工具调用、捕获 Span Tree Trace、落盘为 JSON、再通过 CLI 展示摘要的端到端链路。该链路将 MCP 初始化、工具发现、工具选择、工具执行与失败诊断结构化为可回放、可评估、可诊断的 Agent Run 数据，为后续定位工具误选、参数错误、运行时失败和结果误读提供基础证据。

## 需求范围与非目标

本批次范围：

- 在隔离 worktree 中应用前序提交，形成完整 MCP capture/display 实现基线。
- 运行完整自动化验证：pytest、ruff、mypy。
- 使用真实第三方 `@modelcontextprotocol/server-filesystem` MCP Server 验证成功捕获与工具不存在失败捕获。
- 通过 `lumiagent.cli show` 展示捕获后的 Trace 摘要。
- 记录精确验证结果与环境相关问题。

非目标：

- 不扩展 LumiAgent 为通用 MCP 编排框架。
- 不实现新的 MCP Server 或修改第三方 MCP 包。
- 不提交真实运行生成的 `.lumiagent/traces/*.json` Trace 文件。
- 不在本阶段新增 dashboard、prompt 管理或通用 LLM observability 能力。

## 技术选择

- 使用 Python CLI 作为 MCP capture/display 的最小可执行入口，保持核心 Trace Model 与具体 Agent 框架解耦。
- 使用 stdio transport 启动真实 MCP Server，验证当前 runtime 对第三方 MCP Server 的兼容性。
- 使用 `npx -y @modelcontextprotocol/server-filesystem` 作为第三方 MCP 验证对象，因为它能提供稳定、可本地复现的文件读取工具。
- 使用 JSON Trace 文件作为 capture 与 show 之间的边界，便于后续 replay、evaluation 和 transcript/importer 复用。
- 使用 pytest、ruff、mypy 覆盖行为正确性、代码风格和静态类型边界。

## 架构与设计模式

当前实现保持分层边界：

- `src/lumiagent/tracing`：框架无关的 Run、Span、Event、Artifact、Evaluation、Diagnosis 与序列化/校验能力。
- `src/lumiagent/adapters/mcp`：MCP runtime、selector、mapper、capture strategy、viewer 等适配层能力。
- `src/lumiagent/capture`：capture strategy 抽象协议，便于后续接入 SDK、hooks、MCP proxy 或 CLI wrapper。
- `src/lumiagent/cli.py`：提供 `capture mcp` 与 `show` 的用户可执行入口。

设计上采用 Strategy、Mapper、Typed Failure Taxonomy 与 Viewer Summary 模式：capture strategy 负责运行时编排，mapper 将 runtime 结果转换为 Trace，selector 显式记录工具选择证据，viewer 从 Trace 中提取人类可读摘要。

## 实现要点

- MCP capture 将初始化、工具发现、工具选择和工具执行组织为嵌套 Span Tree。
- 成功路径记录被请求工具、实际选中工具、执行状态和 Trace 摘要。
- 失败路径可将工具不存在映射为 `tool_not_found`，并在 diagnosis/evidence 中保留 requested tool 与 evidence span。
- CLI 输出路径可写入 `.lumiagent/traces/`，但本批次不提交这些运行产物。
- PowerShell 直接传入内联 JSON 参数时遇到引号转义问题；使用 Bash 运行同等命令后成功完成真实 MCP 验证。该问题属于 Windows shell 参数转义差异，不影响 Python CLI 在收到合法 JSON 字符串后的功能验证。

## 第三方 MCP 验证结果

环境支持 `npx` 与第三方包下载/执行。真实 MCP 验证结果如下。

成功捕获命令：

```bash
PYTHONPATH=src python -m lumiagent.cli capture mcp --transport stdio --server-command "npx" --server-arg "-y" --server-arg "@modelcontextprotocol/server-filesystem" --server-arg "$PWD" --tool "read_file" --arguments '{"path":"README.md"}' -o ".lumiagent/traces/filesystem-read-success.json"
```

结果：命令退出码为 0，生成 `.lumiagent/traces/filesystem-read-success.json`。标准输出包含 npm 警告：

```text
npm warn deprecated glob@10.5.0: Old versions of glob are not supported, and contain widely publicized security vulnerabilities, which have been fixed in the current version. Please update. Support for old versions may be purchased (at exorbitant rates) by contacting i@izs.me
```

成功 Trace 展示命令：

```bash
PYTHONPATH=src python -m lumiagent.cli show ".lumiagent/traces/filesystem-read-success.json"
```

展示结果：

```text
Run: MCP capture npx.read_file
Status: success
- MCP Tool Chain 
  - MCP Initialization 
  - MCP Tool Discovery 
  - MCP Tool Selection 
  - MCP Tool Execution: read_file 
Tool Selection
  requested: read_file
  selected: read_file
```

失败捕获命令：

```bash
PYTHONPATH=src python -m lumiagent.cli capture mcp --transport stdio --server-command "npx" --server-arg "-y" --server-arg "@modelcontextprotocol/server-filesystem" --server-arg "$PWD" --tool "read_me" --arguments '{"path":"README.md"}' -o ".lumiagent/traces/filesystem-tool-not-found.json"
```

结果：命令退出码为 0，生成 `.lumiagent/traces/filesystem-tool-not-found.json`。输出：

```text
Secure MCP Filesystem Server running on stdio
Client does not support MCP Roots, using allowed directories set from server args: [
  'D:\Projects\github\lumiagent\.claude\worktrees\agent-a7fa2d4fc4579ba63'
]
.lumiagent\traces\filesystem-tool-not-found.json
```

失败 Trace 展示命令：

```bash
PYTHONPATH=src python -m lumiagent.cli show ".lumiagent/traces/filesystem-tool-not-found.json"
```

展示结果：

```text
Run: MCP capture npx.read_me
Status: error
- MCP Tool Chain 
  - MCP Initialization 
  - MCP Tool Discovery 
  - MCP Tool Selection 
Tool Selection
  requested: read_me
  selected: None
MCP Failure
  type: tool_not_found
  requested tool: read_me
  evidence spans: span_24bab9a7f84348cab0d199859eef5a90
```

补充：按需求给出的 PowerShell 内联 JSON 命令直接运行时失败，错误为：

```text
Exit code 2
Usage: python -m lumiagent.cli capture mcp [OPTIONS]
Try 'python -m lumiagent.cli capture mcp --help' for help.
+- Error ---------------------------------------------------------------------+
| Invalid value: arguments must be a JSON object                              |
+-----------------------------------------------------------------------------+
```

随后使用 Bash 保持相同 CLI 语义并正确传递 JSON 字符串，真实第三方 MCP 成功与失败链路均验证通过。

## 自动化验证结果

完整验证命令与结果如下。

```powershell
$env:PYTHONPATH = "src"; python -m pytest -v
```

结果：

```text
98 passed, 1 warning in 0.54s
```

唯一警告：

```text
PytestConfigWarning: Unknown config option: asyncio_mode
```

```powershell
$env:PYTHONPATH = "src"; python -m ruff check src/lumiagent/tracing src/lumiagent/adapters src/lumiagent/capture tests/tracing tests/adapters tests/capture tests/test_cli_mcp.py
```

结果：

```text
All checks passed!
```

```powershell
$env:PYTHONPATH = "src"; python -m mypy src/lumiagent/tracing src/lumiagent/adapters src/lumiagent/capture
```

结果：

```text
Success: no issues found in 20 source files
```

## 兼容性与扩展性

当前 capture/display 链路与核心 Trace Model 解耦，后续可扩展到更多 MCP Server、更多 transport、MCP proxy、Coding Agent CLI wrapper 和 transcript importer。MCP Failure Taxonomy 与 evidence artifact 可继续扩充参数校验失败、权限失败、transport 失败、工具执行失败、结果误读等诊断类型。

Windows PowerShell 对内联 JSON 参数的转义方式与 Bash 不同，建议后续补充文档或 CLI 参数能力，例如支持 `--arguments-file`，以降低跨 shell 使用成本。真实 MCP Server 输出的 stderr/stdout 信息也可能因第三方包版本变化而变化，测试应优先验证结构化 Trace 语义而不是依赖第三方日志文本。

## 风险、权衡与后续建议

风险与权衡：

- 真实第三方 MCP 验证依赖 `npx`、网络/package cache 和第三方包版本，存在环境波动。
- PowerShell JSON 传参容易受引号转义影响，用户体验存在改进空间。
- 当前 viewer 是摘要展示，适合快速诊断，但不是完整 replay UI。
- 第三方 MCP Server 的安全策略和 allowed directory 行为可能影响跨平台复现。

后续建议：

- 增加 `--arguments-file` 或标准输入读取参数的能力，避免 shell JSON 转义问题。
- 为真实 MCP smoke test 增加可选标记，区分稳定单元测试与环境依赖集成测试。
- 扩展 show 命令，支持输出关键 artifacts、diagnoses 和 failure evidence 的详细视图。
- 将第三方 MCP 验证经验沉淀到用户文档，但继续避免将核心模型耦合到单个 MCP Server。
