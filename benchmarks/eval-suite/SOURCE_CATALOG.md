# 评测套件任务来源目录

- 日期：2026-09-15
- 状态：来源池已锁定；公开索引已收集；A1 六个 instance 已选定（见 [`sources/a1_selection.json`](sources/a1_selection.json)）；`task.json` 与 11.3 审核尚未开始。
- 正式规格：[evaluation-diagnosis-engine.md](../../docs/specs/evaluation-diagnosis-engine.md) 第 4、11 节。
- 对应设计：[P4-A1 任务验证设计](../../docs/superpowers/specs/2026-09-15-phase4-task-verification-design.md)。

本文只锁定「从哪些公开评测集借鉴任务形态」，不宣称 6/24 个种子任务已经构造完成，也不把公开榜分数当作 LumiAgent 验收。

## 1. 使用规则

1. 每套公开评测最多借 **任务形态和少量候选 instance**，改写成 LumiAgent 的 TaskSpec 与独立 verifier。
2. 不接入对方完整 harness，不把对方 hidden tests 暴露给被测 Agent。
3. 仓库快照、数据库种子和隐藏测试默认放在本地 `.lumiagent/`；提交到本仓库的只包括任务清单、来源指针、许可记录和允许公开的环境定义。
4. GPL / copyleft 上游代码不得整仓搬进本仓库。
5. DeepSWE 等从零撰写的任务记为合成/原创，**不计入**规格要求的「至少 12 个真实 issue 来源」。
6. A1 六个任务全部优先选 **可冻结、可本地重置、不依赖个人云账号** 的路径。

## 2. 锁定的来源池

| 角色 | 套件 | A1 是否抽实例 | 说明 |
|------|------|---------------|------|
| 缺陷修复模板 | SWE-bench Verified | 是 | 真实 GitHub issue + 隐藏测试；只抽 1 条小 Python 实例 |
| 跨文件/第二仓库 | Multi-SWE-bench mini | 是 | 满足「两个独立仓库 / 非单一 Python」；优先于整仓引入 SWE-Bench Pro |
| 跨文件备选指针 | SWE-Bench Pro 公开集 | 仅指针 | 更难、更贴近接口变更；公开集多为 GPL，只记 instance_id，不vendor 源码 |
| MCP 状态更新 | MCPMark Postgres / Filesystem | 是 | Apache-2.0；可本地 Docker 重置；程序化验收 |
| MCP 分页/只读形态 | MCP-Universe | 形态 | 真实 server 与长程工具链；A1 必须改成冻结本地种子，不用实时外部 API |
| 跨工具规划参考 | MCP-Bench | 否（A1） | 模糊多跳、多 server；A2 组合任务再考虑 |
| 隔离与过程设计 | Terminal-Bench 2.1 | 否 | 只借鉴容器、超时、清理；3.0 仍在变，不作种子 |
| 新鲜度/Windows 对照 | SWE-bench-Live 冻结 split | 否（A1） | A1 容器按 Linux；Windows split 留作本机对照 |
| 反污染扩充 | DeepSWE | 否（A1） | 手写 verifier 好，但不算真实 issue 来源 |

明确不进入来源池：全量 SWE-bench、HumanEval/MBPP/LiveCodeBench、BFCL/ToolBench、OSWorld/WebArena、LiveMCPBench/MCPEval（主验收为 LLM-as-judge）。

## 3. A1 六个任务的来源绑定

| 任务 ID | 场景 | 主来源 | 冻结方式 | 不采用的捷径 |
|---------|------|--------|----------|--------------|
| `coding_bug_001` | 仓库缺陷修复 | SWE-bench Verified 一条小实例 | 固定 repo commit、FAIL_TO_PASS 与回归测试；隐藏测试只给 verifier | 不跑 500 条，不用已饱和榜当主指标 |
| `coding_interface_001` | 跨文件接口变更 | Multi-SWE-bench mini | 选多文件、非单仓 Python 的一条；许可记入 source metadata | 不把 SWE-Bench Pro 的 GPL 树提交进仓库 |
| `mcp_pagination_001` | MCP 分页检索 | MCP-Universe 的分页形态 | 自备冻结数据种子 + 可重置 MCP；检查多页完整性与终止条件 | 不连实时网页/行情 API |
| `mcp_update_001` | MCP 状态更新 | **MCPMark PostgreSQL**（次选 Filesystem 写） | 本地 Postgres Docker + 样本库；独立检查目标行与副作用 | A1 不用 GitHub MCP（要 token、难隔离） |
| `combined_context_001` | 取上下文后改代码并验证 | 同工作区 **Filesystem MCP** + SWE 风格 issue | 文档/issue 放在 MCP 可见目录，代码仓与隐藏测试隔离 | A1 不用 GitHub issue API |
| `combined_readonly_001` | 只读或权限受限调查 | MCPMark Filesystem 只读/拒写 | 无写权限仍须给出有证据的分析；越权修改为硬约束失败 | 不把「未改文件」单独当成成功 |

这 6 个计入后续 24 个种子，不重复计数。当前选定：

| 任务 ID | 已选实例 |
|---------|----------|
| `coding_bug_001` | SWE-bench Verified `pallets__flask-5014`（BSD-3-Clause，<15 min，1 文件 / 1 个 FAIL_TO_PASS） |
| `coding_interface_001` | Multi-SWE-bench mini `mockito__mockito-3129`（MIT，Java 公开 API，3 文件） |
| `mcp_pagination_001` | MCP-Universe GitHub issue 枚举形态（如 `github_task_0009/0010`）+ 本地冻结种子（**尚未构造**） |
| `mcp_update_001` | MCPMark `easy/chinook/update_employee_info`（Apache-2.0） |
| `combined_context_001` | Filesystem MCP + SWE-bench Verified `psf__requests-1921`（Apache-2.0） |
| `combined_readonly_001` | MCPMark `easy/folder_structure/structure_analysis` 的只读改编 |

许可与哈希见 [`sources/LICENSES.md`](sources/LICENSES.md) 和 [`sources/inventory.json`](sources/inventory.json)。构造 `task.json` 时仍须走规格 11.3。

## 4. A2 扩充时的用法

- Coding 继续从 Verified / Multi-SWE mini 抽，必要时用 SWE-Bench Pro **指针** 补长程接口任务。
- MCP 第二类 server 保持「可写可验」（Postgres/Filesystem）与「只读分页」分开，不把 Notion/Playwright 当默认。
- 留出集按仓库/issue 族分组，不按 trace 随机拆。
- DeepSWE、Terminal-Bench、SWE-bench-Live Windows 只用于标记为合成或对照的扩充，并在 manifest 写明构造方式。

## 5. 当前未决项

- [x] 为 `coding_bug_001` 选定 Verified `instance_id` 并记录上游许可。
- [x] 为 `coding_interface_001` 选定 Multi-SWE mini 实例（或 Pro 指针）。
- [ ] 为 `mcp_pagination_001` 设计冻结种子与本地 MCP 契约。
- [x] 为 `mcp_update_001` 选定 MCPMark Postgres 任务；Chinook 备份仍待在 A1 环境下载。
- [ ] 为两个组合任务写 Agent 可见说明，并与隐藏测试隔离。
- [ ] 预划 6 个任务的开发/留出归属，供 A2 扩到 24 时同组划分。
- [ ] 按规格 11.3 构造并审核 6 个 `task.json`（属 P4-A1，不在本次收集范围）。
