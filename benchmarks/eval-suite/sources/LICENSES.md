# 来源许可记录

收集日期：2026-09-15。本文件只记录许可结论，不复制上游全文。

| 套件 | 数据集/代码许可 | 上游仓库许可 | 本仓库保存什么 |
|------|------------------|--------------|----------------|
| SWE-bench Verified | MIT（SWE-bench 代码与数据集发布） | 各 instance 仓库自有许可 | 公开索引；gold patch / 测试名留在 `.lumiagent/sources/raw` |
| Multi-SWE-bench mini | CC0（ByteDance 声明），须遵守原仓库许可 | 见各 instance | 公开索引；完整 jsonl 留在本地 raw |
| SWE-Bench Pro 公开集 | 评测代码 MIT；公开集来自 copyleft 仓库 | GPL 等，**禁止 vendor 源码树** | 仅 `instance_id` / repo 指针 |
| SWE-bench-Live lite/verified | MIT | 各仓库自有许可 | 冻结 split 公开索引 |
| MCPMark | Apache-2.0 | Postgres 样本库另有来源（Chinook 等） | 任务 meta/标题；`verify.py` 不进 git |
| MCP-Universe | Apache-2.0 | 任务常依赖实时外部 API | 任务路径索引与分页形态，不用 live API |
| MCP-Bench | 见上游仓库 | 28 个 live server | 104 条任务 ID 索引，A1 不抽实例 |
| Terminal-Bench 2.1 | Apache-2.0 | 任务环境各异 | 任务名清单，A1 不抽实例 |
| DeepSWE | Apache-2.0 | 手写 verifier | 任务名清单；**不计入真实 issue** |

## A1 已选定实例的仓库许可

| 任务 | 实例 | 仓库许可 |
|------|------|----------|
| coding_bug_001 | pallets/flask#5014 | BSD-3-Clause |
| coding_interface_001 | mockito/mockito#3129 | MIT |
| combined_context_001 | psf/requests#1921 | Apache-2.0 |
| mcp_update_001 | MCPMark `update_employee_info` | Apache-2.0 |
| combined_readonly_001 | MCPMark `structure_analysis` | Apache-2.0 |

Chinook 样本库将在 A1 环境搭建时按 MCPMark `docs/mcp/postgres.md` 下载到 `.lumiagent/sources/`，不提交。
