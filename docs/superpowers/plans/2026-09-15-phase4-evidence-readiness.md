# P4-P：证据就绪与旧评测隔离 Implementation Plan

> **执行约定：**按 Task 逐项执行，使用未勾选步骤跟踪。本文是实施计划，不是执行授权；本批已获代码实施与本地验证授权；未获提交、外部付费运行或子代理委派授权。获准实施后先核对前置阶段和工作区已有改动，再按测试失败→最小实现→测试通过推进。

**Status:** 2026-09-15 人工评审已通过；P4-P 实现与本地验收完成，未提交 Git。

**Goal:** 修复源事件身份、调用配对、时序与引用，保留采集缺口，并隔离旧聊天评测入口。

**Architecture:** 在 Claude Code / Coding adapter 内增加关联、顺序和证据校验，保持 Trace Core 框架无关；旧包移至 legacy_eval，不实现正式评分。

**Tech Stack:** Python 3.11+、Pydantic v2、typing.Protocol、Typer/Rich、pytest、ruff、mypy、现有 Trace Core。真实执行使用已授权的 Agent/MCP/容器环境；新增外部依赖另行确认。

**Prerequisite:** 正式规格和本阶段设计完成评审；不依赖其他 Phase 4 实现。

**Canonical Spec:** [正式规格](../../specs/evaluation-diagnosis-engine.md)。

**Design:** [本批设计](../specs/2026-09-15-phase4-evidence-readiness-design.md)。

**Roadmap:** [总实施计划](2026-09-15-phase4-implementation-roadmap.md)。

---

## File Structure

以下为本批实施文件与复用范围，已按实际实现核对；未将后续阶段文件提前创建。

- `Modify: src/lumiagent/adapters/claude_code/events.py`
- `Modify: src/lumiagent/adapters/claude_code/hooks.py`
- `Inspect/reuse: src/lumiagent/adapters/claude_code/sanitizer.py`
- `Modify: src/lumiagent/adapters/coding/events.py`
- `Create: tests/adapters/claude_code/test_event_identity.py`
- `Create: src/lumiagent/adapters/claude_code/correlation.py`
- `Modify: src/lumiagent/adapters/claude_code/converter.py`
- `Create: tests/adapters/claude_code/test_correlation.py`
- `Create: src/lumiagent/adapters/coding/evidence.py`
- `Create: tests/adapters/coding/test_evidence_integrity.py`
- `Modify: tests/adapters/claude_code/test_converter.py`
- `Create: src/lumiagent/adapters/coding/ordering.py`
- `Modify: src/lumiagent/adapters/coding/normalizer.py`
- `Modify: src/lumiagent/adapters/coding/validator.py`
- `Modify: src/lumiagent/adapters/coding/viewer.py`
- `Create: tests/adapters/coding/test_source_ordering.py`
- `Move: src/lumiagent/evaluation/__init__.py -> src/lumiagent/legacy_eval/__init__.py`
- `Move: src/lumiagent/evaluation/suite.py -> src/lumiagent/legacy_eval/suite.py`
- `Move: src/lumiagent/evaluation/evaluators.py -> src/lumiagent/legacy_eval/evaluators.py`
- `Move: src/lumiagent/evaluation/metrics.py -> src/lumiagent/legacy_eval/metrics.py`
- `Create: src/lumiagent/evaluation/__init__.py`
- `Modify: src/lumiagent/cli.py`
- `Modify: pyproject.toml`
- `Create: evals/README.md`
- `Create: tests/test_cli_eval_migration.py`

阶段结束后才创建：`docs/reports/phase4-evidence-readiness-technical-report.zh-CN.md`。

共同更新：`docs/HANDOFF.zh-CN.md` 和本计划的实际执行状态；README/PROJECT_SPEC 仅在对应实现验证后更新交付状态。

## 执行前检查

- [x] 核对正式规格、本阶段设计和依赖阶段的实际验收结果。
- [x] 检查 git status，保留已有用户改动，不执行全仓库格式化或批量覆盖。
- [x] 记录现有测试与主线 lint/type 基线；旧 legacy 的已知问题单独列出，不算新主线已解决的问题。
- [x] 新文件与接口按本计划创建；若前置实际接口发生变化，先更新设计与计划，不能临时绕过合同。

命令均从仓库根目录的 PowerShell 执行，先设置 `$env:PYTHONPATH = "src"`。下面的 FAIL/PASS 是预期，不是已运行结果。失败必须来自目标断言或尚未实现的接口；依赖缺失、临时目录权限等环境错误不能当作 TDD 的有效失败。

---

### Task 1: 源事件身份与采集能力

**Spec:** §6 EVD-02/03/04；§15。

**Files:**
- `Modify: src/lumiagent/adapters/claude_code/events.py`
- `Modify: src/lumiagent/adapters/claude_code/hooks.py`
- `Inspect/reuse: src/lumiagent/adapters/claude_code/sanitizer.py`
- `Modify: src/lumiagent/adapters/coding/events.py`
- `Create: tests/adapters/claude_code/test_event_identity.py`

- [x] **Step 1: 编写失败测试**

新增 test_missing_source_identity_does_not_reuse_evt_1、test_ingestion_order_is_not_source_order、test_legacy_events_remain_readable、test_redaction_preserves_call_identity；验证相同默认 sequence 的两个不同动作不会被当成同一事件。

- [x] **Step 2: 运行并确认目标失败**

```powershell
python -m pytest tests/adapters/claude_code/test_event_identity.py tests/adapters/claude_code/test_hooks.py tests/adapters/claude_code/test_events.py -v
```

Expected: FAIL。旧 hooks 缺身份时重复使用 evt_1，新能力字段或版本行为尚未提供。

- [x] **Step 3: 实现最小可用行为**

区分源事件 ID 与本地采集 ID，新增可空 call_id/来源范围和能力声明；缺字段时可读并标记 unknown。源数据不被本地默认序号覆盖，脱敏保留关联键但移除敏感值。新旧 schema 往返均须测试。

- [x] **Step 4: 重跑测试并检查改动范围**

```powershell
python -m pytest tests/adapters/claude_code/test_event_identity.py tests/adapters/claude_code/test_hooks.py tests/adapters/claude_code/test_events.py -v
```

Expected: PASS，所有上述断言成立。检查新旧合同、错误路径、输入不变性和类型边界；不得删掉失败断言或以固定假结果满足测试。

---

### Task 2: 并发调用配对与去重

**Spec:** §6 EVD-02。

**Files:**
- `Create: src/lumiagent/adapters/claude_code/correlation.py`
- `Modify: src/lumiagent/adapters/claude_code/converter.py`
- `Create: tests/adapters/claude_code/test_correlation.py`

- [x] **Step 1: 编写失败测试**

构造 A请求→B请求→A结果→B结果，参数和返回必须同 ID；再覆盖逆序返回、permission 插入、重复事件、重试、缺 ID、缺结果和子任务重复 call_id。缺 ID 用例应保留 ambiguous，而不是猜配。

- [x] **Step 2: 运行并确认目标失败**

```powershell
python -m pytest tests/adapters/claude_code/test_correlation.py tests/adapters/claude_code/test_converter.py -v
```

Expected: FAIL。当前实现会把 B 请求与 A 结果合并，或未提供关联模块。

- [x] **Step 3: 实现最小可用行为**

以来源范围和 call_id 维护多请求映射；仅去除已证明重复的事件。保留原事件 ID 与关联状态。converter 消费关联结果，不再使用单一 pending+工具名配对。

- [x] **Step 4: 重跑测试并检查改动范围**

```powershell
python -m pytest tests/adapters/claude_code/test_correlation.py tests/adapters/claude_code/test_converter.py -v
```

Expected: PASS，所有上述断言成立。检查新旧合同、错误路径、输入不变性和类型边界；不得删掉失败断言或以固定假结果满足测试。

---

### Task 3: 单次构建与 adapter 引用校验

**Spec:** §6 EVD-01；§9.3。

**Files:**
- `Modify: src/lumiagent/adapters/claude_code/converter.py`
- `Create: src/lumiagent/adapters/coding/evidence.py`
- `Create: tests/adapters/coding/test_evidence_integrity.py`
- `Modify: tests/adapters/claude_code/test_converter.py`

- [x] **Step 1: 编写失败测试**

新增 test_finding_references_final_run、test_old_dangling_reference_is_reported、test_group_creation_does_not_add_unused_spans；对“编辑但未验证”逐个确认 finding 的 evidence_span_ids 在最终 run 中，验证输入历史文件未被改写。

- [x] **Step 2: 运行并确认目标失败**

```powershell
python -m pytest tests/adapters/coding/test_evidence_integrity.py tests/adapters/claude_code/test_converter.py tests/tracing/test_validator.py -v
```

Expected: FAIL。现有二次构建使 finding 引用悬空，Core validator 不检查 artifact 内引用。

- [x] **Step 3: 实现最小可用行为**

在唯一动作 run 上附加检查结果并重新验证；显式创建语义组而非 setdefault 中调用有副作用函数。adapter validator 检查已知 artifact 内引用，Core validator 不导入 adapter。

- [x] **Step 4: 重跑测试并检查改动范围**

```powershell
python -m pytest tests/adapters/coding/test_evidence_integrity.py tests/adapters/claude_code/test_converter.py tests/tracing/test_validator.py -v
```

Expected: PASS，所有上述断言成立。检查新旧合同、错误路径、输入不变性和类型边界；不得删掉失败断言或以固定假结果满足测试。

---

### Task 4: 源时序与 MCP 身份保留

**Spec:** §6 EVD-03/04/05。

**Files:**
- `Create: src/lumiagent/adapters/coding/ordering.py`
- `Modify: src/lumiagent/adapters/coding/normalizer.py`
- `Modify: src/lumiagent/adapters/coding/validator.py`
- `Modify: src/lumiagent/adapters/claude_code/converter.py`
- `Modify: src/lumiagent/adapters/coding/viewer.py`
- `Create: tests/adapters/coding/test_source_ordering.py`

- [x] **Step 1: 编写失败测试**

测试失败→编辑→成功复验在分组前后语义一致；没有顺序证据时返回 unknown；源时间缺失不产出真实耗时；最终回答不因 enrichment 被放到所有动作之前；未知 MCP 名称及原始返回保持可见。

- [x] **Step 2: 运行并确认目标失败**

```powershell
python -m pytest tests/adapters/coding/test_source_ordering.py tests/adapters/coding/test_coding_validator.py tests/adapters/coding/test_normalizer.py tests/adapters/coding/test_coding_viewer.py -v
```

Expected: FAIL。旧 validator 使用树序，normalizer 会将未识别工具映射成普通 shell。

- [x] **Step 3: 实现最小可用行为**

提供 before/after/concurrent/unknown 查询；validator 使用源关系而非 DFS。源时间和 ingestion 标志写入 adapter metadata。保留 MCP 原始身份与 schema 缺口，不在本批发明完整 MCP 自动评测。

- [x] **Step 4: 重跑测试并检查改动范围**

```powershell
python -m pytest tests/adapters/coding/test_source_ordering.py tests/adapters/coding/test_coding_validator.py tests/adapters/coding/test_normalizer.py tests/adapters/coding/test_coding_viewer.py -v
```

Expected: PASS，所有上述断言成立。检查新旧合同、错误路径、输入不变性和类型边界；不得删掉失败断言或以固定假结果满足测试。

---

### Task 5: 隔离 legacy eval 与预留新入口

**Spec:** §14.2。

**Files:**
- `Move: src/lumiagent/evaluation/__init__.py -> src/lumiagent/legacy_eval/__init__.py`
- `Move: src/lumiagent/evaluation/suite.py -> src/lumiagent/legacy_eval/suite.py`
- `Move: src/lumiagent/evaluation/evaluators.py -> src/lumiagent/legacy_eval/evaluators.py`
- `Move: src/lumiagent/evaluation/metrics.py -> src/lumiagent/legacy_eval/metrics.py`
- `Create: src/lumiagent/evaluation/__init__.py`
- `Modify: src/lumiagent/cli.py`
- `Modify: pyproject.toml`
- `Create: evals/README.md`
- `Create: tests/test_cli_eval_migration.py`

- [x] **Step 1: 编写失败测试**

验证 eval 迁移提示的非零退出码和无 Agent 初始化；legacy-eval --help 说明遗留；用替身确认 legacy 调用目标；新 evaluation 不重导出 EvaluationSuite，既有 capture/show 不受影响。

- [x] **Step 2: 运行并确认目标失败**

```powershell
python -m pytest tests/test_cli_eval_migration.py tests/test_cli_mcp.py tests/test_cli_coding_trace.py -v
```

Expected: FAIL。当前 eval 会启动旧 Agent，legacy-eval 不存在，新包还导出旧 suite。

- [x] **Step 3: 实现最小可用行为**

单独核对四个原文件和目标路径后迁移、更新包内 import 与惰性 CLI import。保留旧样例但标记 legacy，修正产品描述。只验证迁移接线，不修复或扩展旧评分器；旧包不进入新主线依赖。

- [x] **Step 4: 重跑测试并检查改动范围**

```powershell
python -m pytest tests/test_cli_eval_migration.py tests/test_cli_mcp.py tests/test_cli_coding_trace.py -v
```

Expected: PASS，所有上述断言成立。检查新旧合同、错误路径、输入不变性和类型边界；不得删掉失败断言或以固定假结果满足测试。

---

### Task 6: 全量验证、真实路径与阶段技术报告

**Files:**
- Create after verification: `docs/reports/phase4-evidence-readiness-technical-report.zh-CN.md`
- Modify after verification: `docs/HANDOFF.zh-CN.md`、本计划与已验收的 README/PROJECT_SPEC 状态。

- [x] **Step 1: 运行自动化验证**

```powershell
$env:PYTHONPATH = "src"
python -m pytest -v
python -m ruff check src/lumiagent/tracing src/lumiagent/adapters src/lumiagent/capture src/lumiagent/evaluation src/lumiagent/cli.py tests
python -m mypy src/lumiagent/tracing src/lumiagent/adapters src/lumiagent/capture src/lumiagent/evaluation
git diff --check
```

Expected: tests 全部通过，ruff/mypy 无新增主线问题，diff 无空白错误。命令覆盖本阶段和前置阶段模块。若已有 CLI 或其他基线问题阻止验收，须列明并完成经确认的必要修复，不能静默移除检查路径；legacy 评分器的全量治理不属于本阶段。

- [x] **Step 2: 执行真实路径验收**

本批无新外部运行命令。使用既有真实脱敏 fixture 执行 show --checks，并补充关联/时序反例；真实来源缺失字段须如实显示。

```powershell
$env:PYTHONPATH = "src"
python -m lumiagent.cli show tests/adapters/claude_code/fixtures/real_session_sanitized_trace.json --checks
```

Expected: CLI 可读取旧 fixture，保留语义摘要；证据质量或版本问题明确显示，不被包装为 Phase 4 正式评分。

如果缺少真实环境、模型权限、审核数据或预算，记录阻塞，保持本项未勾选。单元测试替身不能代替真实验收；不为凑结果创建“真实”合成 fixture。

- [x] **Step 3: 验证完成后撰写中文阶段实现技术报告**

只在实现与上述验证完成后创建指定报告，包含技术选择、语法与风格、设计模式、实现要点、真实命令/退出码/结果、真实路径证据、兼容性、偏差、风险和后续工作。不得写规格交付记录，不预建报告占位，不把 Expected 复制成实际结果。

- [x] **Step 4: 更新交接和阶段状态**

核对覆盖表，填写实际执行证据，已完成步骤才勾选。只有全部退出条件成立才标记本阶段完成；报告和文档完成不能替代代码验收。

- [ ] **Step 5: 按独立授权整理提交（未获授权，未执行；不阻塞代码与本地验收）**

仅在用户授权提交时，检查并提交本批明确文件，不使用 `git add .` 混入其他工作。不添加 Claude Co-Authored-By trailer。未获授权时保留工作区并说明未提交。

## Spec Coverage

| 要求 | 任务 |
|---|---|
| §6 EVD-02/03/04；§15 | Task 1 |
| §6 EVD-02 | Task 2 |
| §6 EVD-01；§9.3 | Task 3 |
| §6 EVD-03/04/05 | Task 4 |
| §14.2 | Task 5 |
| 阶段验收、实际技术报告与状态更新 | Task 6 |

## Self-Review / Execution Handoff

- [x] 所有需求映射到具体 Task、文件、测试和验收步骤。
- [x] 依赖阶段接口和本计划的 Create/Modify/Move 文件表已核对。
- [x] 数据规模、权限、未知状态和报告边界与正式规格一致。
- [x] 自动化和真实验证结果已记录；未执行任务没有勾选。
- [x] 下一阶段只在本阶段验收完成并获得实施授权后启动。

当前交接状态：**P4-P 实现及本地验收完成；未提交，未启动 P4-A1。**实际技术选择与验证见 [P4-P 技术报告](../../reports/phase4-evidence-readiness-technical-report.zh-CN.md)。

### 实际执行记录（2026-09-15）

- Task 1：先观察到新增身份测试 9 failed、已有相关测试 8 passed；实现后 17 passed。
- Task 2：先确认关联模块缺失的预期导入失败；实现后关联与身份合计 19 passed。
- Task 3/4：先确认新证据/时序接口缺失的预期失败；实现后基础证据、时序、关联合计 26 passed，随后补充并修复边界反例。
- Task 5：先确认 5 个迁移测试失败；迁移后随全量测试通过。四个 legacy 模块除 import 命名空间外与原实现一致。
- Task 6：最终 225 passed、1 个既有 asyncio_mode 警告；ruff 通过；mypy 38 个源码文件通过；11 个旧 fixtures Core 往返与只读检查通过。
- 真实来源验证：按本计划执行既有 real_session_sanitized_trace 的 show --checks；显示历史 unknown 与 stored pass，未新开外部 Agent/MCP 会话。
- 兼容调整：旧配对正例补足 call_id；合成完整工作流明确声明源顺序、相关性和覆盖范围；缺证据的旧预检改为 unknown，保留反例覆盖。
- sanitizer 已满足保留身份/脱敏要求，因此复用而未无意义改写。必要的 CLI 格式与输入边界修复已完成。
- 本批未改动 Trace Core 或既有 MCP 实现；保留用户及并行来源收集改动。不自动提交或启动后续阶段。
