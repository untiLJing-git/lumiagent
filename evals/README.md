# 遗留聊天评测样例

此目录的 `sample_eval.json` 属于初始聊天 Agent 的旧评分器，不是 Phase 4 任务基准集。

旧入口为 `lumi legacy-eval sample_eval`；该命令已弃用，旧评分器存在已知缺陷，不保证可用。本次只迁移命名和入口，没有修复或扩展其评分逻辑。

`lumi eval` 现仅提示迁移并以退出码 2 结束，不启动聊天 Agent。正式 trace evaluation 留给 P4-A1/A2；不要在此目录添加新的 Phase 4 基准任务。
