# 评测套件来源收集产物

本目录只保存**可进仓库的指针、许可记录和公开索引**。完整 parquet/jsonl、上游 clone、gold patch、隐藏测试和数据库备份放在本地 `.lumiagent/sources/`，不要提交。

重新收集：

```powershell
$env:PYTHONPATH = "src"
python benchmarks/eval-suite/scripts/collect_sources.py
```

A1 选定结果见 `a1_selection.json`，许可见 `LICENSES.md`。这不等于 `task.json` 已构造，也不等于规格 11.3 审核完成。

本地缓存（不提交）：

- `.lumiagent/sources/raw/`：SWE-bench Verified/Pro、Multi-SWE mini、SWE-bench-Live 冻结 split
- `.lumiagent/sources/repos/`：MCPMark、MCP-Universe、MCP-Bench 稀疏 clone
