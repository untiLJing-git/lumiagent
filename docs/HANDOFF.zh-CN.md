# LumiAgent 后续工作交接记录

本文档用于在不同设备或新的 Claude Code 会话中继续 LumiAgent 开发时快速恢复上下文。

## 当前项目

- 本地路径：`D:\Project\resume\lumiagent`
- GitHub 仓库：`untiLJing-git/lumiagent`
- 当前主分支：`main`

## 已完成内容

1. 第一阶段 Trace Core MVP 已完成并合入 `main`。
2. 已实现 `src/lumiagent/tracing/`：
   - `models.py`
   - `enums.py`
   - `serializer.py`
   - `validator.py`
   - `builder.py`
   - `__init__.py`
3. 已有测试：
   - `tests/tracing/test_models.py`
   - `tests/tracing/test_serializer.py`
   - `tests/tracing/test_validator.py`
   - `tests/tracing/test_builder.py`
   - `tests/tracing/fixtures/generic_agent_run.json`
   - `tests/tracing/fixtures/coding_agent_trace_sample.json`
4. 已有中文技术报告：
   - `docs/reports/trace-core-mvp-technical-report.zh-CN.md`
5. README 已拆成中英文：
   - `README.md`
   - `README.zh-CN.md`
6. 架构图已改为 Mermaid 源文件和 SVG：
   - `docs/diagrams/*.mmd`
   - `docs/assets/*.svg`
7. 所有阶段性修改已提交并推送到远程 `main`。
   - 最新阶段提交：`7960cf0 Add Mermaid architecture diagrams`

## 当前验证状态

使用本地源码路径验证通过：

```powershell
$env:PYTHONPATH = "src"
python -m pytest -v
python -m ruff check src/lumiagent/tracing tests/tracing
python -m mypy src/lumiagent/tracing
```

验证结果：

```text
pytest: 18 passed
ruff: All checks passed
mypy: Success: no issues found in 6 source files
```

注意：如果当前环境没有执行 `pip install -e ".[dev]"`，直接运行 `pytest` 可能出现：

```text
ModuleNotFoundError: No module named 'lumiagent'
```

可以先设置 `PYTHONPATH=src`，或安装 editable 包。

## 后续会话需要遵守的偏好

- Git commit message 不要包含 `Claude Co-Authored-By` trailer。
- LumiAgent 每次实现完成后，都要写中文技术报告到 `docs/reports/`。
- LumiAgent 架构图优先使用 Mermaid；需要图片时用 Mermaid CLI 导出 SVG 到 `docs/assets/`。
- 每次代码或文档改动后，都要运行相关测试或验证命令。

## 下一步建议

下一阶段建议进入 **MCP Tool Chain Model**，但不要直接开始写代码。应先做需求规格和设计文档，明确：

- MCP server connection span
- tool discovery span
- tool schema snapshot
- tool call / result
- tool arguments
- permission / error / latency
- 如何映射到现有 `AgentRun / Span / Event / Artifact / Evaluation / Diagnosis`

## 第二阶段设计倾向

- 暂不接真实 MCP Server。
- 暂不做 UI。
- 暂不做完整诊断引擎。
- 尽量不新增大量专用 `SpanKind`。
- MCP 细节优先通过 `metadata` 和 `artifact` 表达，保持 Trace Core 稳定。

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
