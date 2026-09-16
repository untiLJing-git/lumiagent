# P4-A2：技能化评测与证据审计 Implementation Plan

> **执行约定：**按 Task 逐项执行，使用未勾选步骤跟踪。本文是实施计划，不是执行授权；当前不得执行代码修改、外部调用、提交或子代理委派。获准实施后先核对前置阶段和工作区已有改动，再按测试失败→最小实现→测试通过推进。

**Status:** 初稿，待评审；所有实施步骤未执行。

**Goal:** 交付八个评测技能、固定计划、证据审计、eval CLI 和 24 个种子任务。

**Architecture:** evaluation 通过只读 EvidenceIndex 和 SkillRegistry 组合检查，使用统一模型和结果聚合；MCP 映射留在 adapters，报告保存跨 run 引用。

**Tech Stack:** Python 3.11+、Pydantic v2、typing.Protocol、Typer/Rich、pytest、ruff、mypy、现有 Trace Core。真实执行使用已授权的 Agent/MCP/容器环境；新增外部依赖另行确认。

**Prerequisite:** P4-A1 验收通过；Task/Trial/VerifierResult 与基础四态接口已经固定。

**Canonical Spec:** [正式规格](../../specs/evaluation-diagnosis-engine.md)。

**Design:** [本批设计](../specs/2026-09-15-phase4-skill-evaluation-design.md)。

**Roadmap:** [总实施计划](2026-09-15-phase4-implementation-roadmap.md)。

---

## File Structure

以下为本阶段计划创建/修改/迁移的文件，不表示这些文件已经存在。Modify 包括前置阶段按计划创建的文件；实际开始时必须核对。

- `Modify: src/lumiagent/evaluation/models.py`
- `Create: src/lumiagent/evaluation/evidence.py`
- `Create: tests/evaluation/test_evidence.py`
- `Create: tests/evaluation/test_report_models.py`
- `Create: src/lumiagent/evaluation/skills/__init__.py`
- `Create: src/lumiagent/evaluation/skills/base.py`
- `Create: src/lumiagent/evaluation/skills/outcome.py`
- `Create: src/lumiagent/evaluation/skills/workflow.py`
- `Create: src/lumiagent/evaluation/skills/mcp.py`
- `Create: src/lumiagent/evaluation/skills/claims.py`
- `Create: tests/evaluation/test_skills.py`
- `Create: src/lumiagent/evaluation/planner.py`
- `Create: src/lumiagent/evaluation/engine.py`
- `Create: src/lumiagent/evaluation/permissions.py`
- `Create: tests/evaluation/test_planner.py`
- `Create: tests/evaluation/test_engine.py`
- `Create: src/lumiagent/adapters/coding/mcp.py`
- `Modify: src/lumiagent/adapters/coding/normalizer.py`
- `Modify: src/lumiagent/adapters/claude_code/converter.py`
- `Create: tests/adapters/coding/test_mcp_evidence_bridge.py`
- `Create: tests/evaluation/test_mcp_workflows.py`
- `Create: src/lumiagent/evaluation/report.py`
- `Modify: src/lumiagent/evaluation/__init__.py`
- `Modify: src/lumiagent/cli.py`
- `Create: tests/evaluation/test_report.py`
- `Create: tests/test_cli_eval.py`
- `Modify: tests/test_cli_eval_migration.py`
- `Modify: benchmarks/eval-suite/suite.json`
- `Modify: benchmarks/eval-suite/README.md`
- `Create: benchmarks/eval-suite/splits.json`
- `Create: benchmarks/eval-suite/provenance.json`
- `Create: tests/benchmarks/test_suite_contract.py`
- `Create: tests/evaluation/test_controls.py`

阶段结束后才创建：`docs/reports/phase4-skill-evaluation-technical-report.zh-CN.md`。

共同更新：`docs/HANDOFF.zh-CN.md` 和本计划的实际执行状态；README/PROJECT_SPEC 仅在对应实现验证后更新交付状态。

## 执行前检查

- [ ] 核对正式规格、本阶段设计和依赖阶段的实际验收结果。
- [ ] 检查 git status，保留已有用户改动，不执行全仓库格式化或批量覆盖。
- [ ] 记录现有测试与主线 lint/type 基线；旧 legacy 的已知问题单独列出，不算新主线已解决的问题。
- [ ] 新文件与接口按本计划创建；若前置实际接口发生变化，先更新设计与计划，不能临时绕过合同。

命令均从仓库根目录的 PowerShell 执行，先设置 `$env:PYTHONPATH = "src"`。下面的 FAIL/PASS 是预期，不是已运行结果。失败必须来自目标断言或尚未实现的接口；依赖缺失、临时目录权限等环境错误不能当作 TDD 的有效失败。

---

### Task 1: 证据引用、报告模型与解析边界

**Spec:** §9.2/9.3；§18.1/18.2。

**Files:**
- `Modify: src/lumiagent/evaluation/models.py`
- `Create: src/lumiagent/evaluation/evidence.py`
- `Create: tests/evaluation/test_evidence.py`
- `Create: tests/evaluation/test_report_models.py`

- [ ] **Step 1: 编写失败测试**

JSON Pointer、日志行和完整对象三种定位互斥；跨 run artifact 可解析但不会写入目标 run 的 evidence_span_ids；摘要错误、断链、路径穿越、输入版本冲突均拒绝。

- [ ] **Step 2: 运行并确认目标失败**

```powershell
python -m pytest tests/evaluation/test_evidence.py tests/evaluation/test_report_models.py -v
```

Expected: FAIL。证据引用和报告模型尚不存在。

- [ ] **Step 3: 实现最小可用行为**

实现 EvidenceRef、EvidenceIndex、EvalPlan 和 EvaluationReport；输入对象只读，解析范围由授权 bundle 根目录约束。复用 P4-A1 EvaluationItem 和四态，不重新定义 Task 或 Trial。

- [ ] **Step 4: 重跑测试并检查改动范围**

```powershell
python -m pytest tests/evaluation/test_evidence.py tests/evaluation/test_report_models.py -v
```

Expected: PASS，所有上述断言成立。检查新旧合同、错误路径、输入不变性和类型边界；不得删掉失败断言或以固定假结果满足测试。

---

### Task 2: 技能注册与程序化检查

**Spec:** §8.1/8.3/8.4。

**Files:**
- `Create: src/lumiagent/evaluation/skills/__init__.py`
- `Create: src/lumiagent/evaluation/skills/base.py`
- `Create: src/lumiagent/evaluation/skills/outcome.py`
- `Create: src/lumiagent/evaluation/skills/workflow.py`
- `Create: src/lumiagent/evaluation/skills/mcp.py`
- `Create: src/lumiagent/evaluation/skills/claims.py`
- `Create: tests/evaluation/test_skills.py`

- [ ] **Step 1: 编写失败测试**

覆盖八个正式技能名；缺 verifier 输出时结果 unknown；失败后无关动作不算恢复；不存在要求不适用可跳过；模型宣称与测试日志相反时保留反证；每项都引用实际证据。

- [ ] **Step 2: 运行并确认目标失败**

```powershell
python -m pytest tests/evaluation/test_skills.py -v
```

Expected: FAIL。技能协议与八种检查未实现。

- [ ] **Step 3: 实现最小可用行为**

注册 Skill Protocol 的版本、权限、适用条件和预算。outcome/regression 读取独立验证结果，claims 可用受约束抽取并校验；没有可用模型时未知，不用占位输出冒充推断。

- [ ] **Step 4: 重跑测试并检查改动范围**

```powershell
python -m pytest tests/evaluation/test_skills.py -v
```

Expected: PASS，所有上述断言成立。检查新旧合同、错误路径、输入不变性和类型边界；不得删掉失败断言或以固定假结果满足测试。

---

### Task 3: 固定路由、调查计划与执行引擎

**Spec:** §5.1；§8.2/8.3；§10.3；§15。

**Files:**
- `Create: src/lumiagent/evaluation/planner.py`
- `Create: src/lumiagent/evaluation/engine.py`
- `Create: src/lumiagent/evaluation/permissions.py`
- `Create: tests/evaluation/test_planner.py`
- `Create: tests/evaluation/test_engine.py`

- [ ] **Step 1: 编写失败测试**

相同 Task 对不同候选产生相同验收计划；必需项漏路由为 unknown；skill 异常局部化；离线模式任何执行/联网请求被阻止；LLM 不可覆盖有效 deterministic fail。

- [ ] **Step 2: 运行并确认目标失败**

```powershell
python -m pytest tests/evaluation/test_planner.py tests/evaluation/test_engine.py -v
```

Expected: FAIL。固定计划与有限权限执行器不存在。

- [ ] **Step 3: 实现最小可用行为**

在候选可见前固定基础计划及摘要；调查分支只扩展证据，遵守同一预算策略。执行引擎记录自身 trace 与错误，复用 outcomes 聚合。权限入口默认只读，不以模型文本授权工具。

- [ ] **Step 4: 重跑测试并检查改动范围**

```powershell
python -m pytest tests/evaluation/test_planner.py tests/evaluation/test_engine.py -v
```

Expected: PASS，所有上述断言成立。检查新旧合同、错误路径、输入不变性和类型边界；不得删掉失败断言或以固定假结果满足测试。

---

### Task 4: 完成 MCP 证据衔接与多步评测

**Spec:** §6 EVD-05；§8.4。

**Files:**
- `Create: src/lumiagent/adapters/coding/mcp.py`
- `Modify: src/lumiagent/adapters/coding/normalizer.py`
- `Modify: src/lumiagent/adapters/claude_code/converter.py`
- `Create: tests/adapters/coding/test_mcp_evidence_bridge.py`
- `Create: tests/evaluation/test_mcp_workflows.py`

- [ ] **Step 1: 编写失败测试**

多步调用关联到实际 server/schema 摘要；合法参数但错误对象失败；分页遗漏、部分成功、工具错误、限流与权限区别处理；缺 schema 时契约检查 unknown；旧显式 capture 保持兼容。

- [ ] **Step 2: 运行并确认目标失败**

```powershell
python -m pytest tests/adapters/coding/test_mcp_evidence_bridge.py tests/evaluation/test_mcp_workflows.py tests/adapters/mcp/test_capture.py -v
```

Expected: FAIL。Phase 3 通用 fallback 尚未提供完整 MCP 证据桥接。

- [ ] **Step 3: 实现最小可用行为**

把真实 Agent MCP 行为归一化为已有 MCP evidence conventions，并保存 schema 来源。证据由获准调用路径采集，不为本批实现通用代理；不修改 Core 为 MCP 增加字段。

- [ ] **Step 4: 重跑测试并检查改动范围**

```powershell
python -m pytest tests/adapters/coding/test_mcp_evidence_bridge.py tests/evaluation/test_mcp_workflows.py tests/adapters/mcp/test_capture.py -v
```

Expected: PASS，所有上述断言成立。检查新旧合同、错误路径、输入不变性和类型边界；不得删掉失败断言或以固定假结果满足测试。

---

### Task 5: JSON/中文报告、Core 导出与 eval CLI

**Spec:** §9.3；§13；§14。

**Files:**
- `Create: src/lumiagent/evaluation/report.py`
- `Modify: src/lumiagent/evaluation/__init__.py`
- `Modify: src/lumiagent/cli.py`
- `Create: tests/evaluation/test_report.py`
- `Create: tests/test_cli_eval.py`
- `Modify: tests/test_cli_eval_migration.py`

- [ ] **Step 1: 编写失败测试**

同一结构化结果生成 JSON 和中文报告；Core 导出通过 validate_run；源文件字节不变；重复 assessment 独立；旧 eval-set 名称不启动旧 Agent；退出码、任务缺失和已有输出保护正确。

- [ ] **Step 2: 运行并确认目标失败**

```powershell
python -m pytest tests/evaluation/test_report.py tests/test_cli_eval.py tests/test_cli_eval_migration.py -v
```

Expected: FAIL。当前 eval 仍是 P4-P 预留提示，报告渲染与新输入尚未存在。

- [ ] **Step 3: 实现最小可用行为**

提供 eval trace --task 的离线语义，不自动调用测试或网络。实现 report-level EvidenceRef 和副本导出，完整呈现未知与反证；将 P4-P 迁移提示测试更新为新旧入口输入隔离，不删除迁移覆盖。

- [ ] **Step 4: 重跑测试并检查改动范围**

```powershell
python -m pytest tests/evaluation/test_report.py tests/test_cli_eval.py tests/test_cli_eval_migration.py -v
```

Expected: PASS，所有上述断言成立。检查新旧合同、错误路径、输入不变性和类型边界；不得删掉失败断言或以固定假结果满足测试。

---

### Task 6: 扩充24任务、留出清单与可靠性控制集

**Spec:** §11.2–11.5；§12.3；§17。

**Files:**
- `Modify: benchmarks/eval-suite/suite.json`
- `Modify: benchmarks/eval-suite/README.md`
- `Create: benchmarks/eval-suite/splits.json`
- `Create: benchmarks/eval-suite/provenance.json`
- `Create: tests/benchmarks/test_suite_contract.py`
- `Create: tests/evaluation/test_controls.py`

- [ ] **Step 1: 编写失败测试**

12/6/6 总数、至少12真实来源、至少8分组留出、独立仓库/server 覆盖；派生项不计种子；假通过/缺证据/测试篡改/注入对照样例均被正确处理。

- [ ] **Step 2: 运行并确认目标失败**

```powershell
python -m pytest tests/benchmarks/test_suite_contract.py tests/evaluation/test_controls.py -v
```

Expected: FAIL。suite 目前只有6项，尚未提供全量来源/分组和控制集。

- [ ] **Step 3: 实现最小可用行为**

补齐剩余18个带实际来源或合成标记的任务及资产，在 suite 显式列出路径。冻结分组来源与留出使用规则。控制集与真实任务分开计数，不能把已有 fixture 换名凑数。

- [ ] **Step 4: 重跑测试并检查改动范围**

```powershell
python -m pytest tests/benchmarks/test_suite_contract.py tests/evaluation/test_controls.py -v
```

Expected: PASS，所有上述断言成立。检查新旧合同、错误路径、输入不变性和类型边界；不得删掉失败断言或以固定假结果满足测试。

---

### Task 7: 全量验证、真实路径与阶段技术报告

**Files:**
- Create after verification: `docs/reports/phase4-skill-evaluation-technical-report.zh-CN.md`
- Modify after verification: `docs/HANDOFF.zh-CN.md`、本计划与已验收的 README/PROJECT_SPEC 状态。

- [ ] **Step 1: 运行自动化验证**

```powershell
$env:PYTHONPATH = "src"
python -m pytest -v
python -m ruff check src/lumiagent/tracing src/lumiagent/adapters src/lumiagent/capture src/lumiagent/evaluation src/lumiagent/benchmarks src/lumiagent/cli.py tests
python -m mypy src/lumiagent/tracing src/lumiagent/adapters src/lumiagent/capture src/lumiagent/evaluation src/lumiagent/benchmarks
git diff --check
```

Expected: tests 全部通过，ruff/mypy 无新增主线问题，diff 无空白错误。命令覆盖本阶段和前置阶段模块。若已有 CLI 或其他基线问题阻止验收，须列明并完成经确认的必要修复，不能静默移除检查路径；legacy 评分器的全量治理不属于本阶段。

- [ ] **Step 2: 执行真实路径验收**

使用 P4-A1 真实运行报告与受控 bundle，并准备已审核的24任务清单；外部运行先确认预算和权限。

```powershell
$env:PYTHONPATH = "src"
python -m lumiagent.cli bench run benchmarks/eval-suite/suite.json --agent .lumiagent/config/claude-code.json --repeat 1 --output .lumiagent/benchmarks/p4-a2-acceptance
```

Expected: 24项来源、划分和 verifier 均通过资产校验；运行报告包含逐项检查、有效引用和未知项；至少一条真实 Agent 多步 MCP 路径通过证据审计。

如果缺少真实环境、模型权限、审核数据或预算，记录阻塞，保持本项未勾选。单元测试替身不能代替真实验收；不为凑结果创建“真实”合成 fixture。

- [ ] **Step 3: 验证完成后撰写中文阶段实现技术报告**

只在实现与上述验证完成后创建指定报告，包含技术选择、语法与风格、设计模式、实现要点、真实命令/退出码/结果、真实路径证据、兼容性、偏差、风险和后续工作。不得写规格交付记录，不预建报告占位，不把 Expected 复制成实际结果。

- [ ] **Step 4: 更新交接和阶段状态**

核对覆盖表，填写实际执行证据，已完成步骤才勾选。只有全部退出条件成立才标记本阶段完成；报告和文档完成不能替代代码验收。

- [ ] **Step 5: 按独立授权整理提交**

仅在用户授权提交时，检查并提交本批明确文件，不使用 `git add .` 混入其他工作。不添加 Claude Co-Authored-By trailer。未获授权时保留工作区并说明未提交。

## Spec Coverage

| 要求 | 任务 |
|---|---|
| §9.2/9.3；§18.1/18.2 | Task 1 |
| §8.1/8.3/8.4 | Task 2 |
| §5.1；§8.2/8.3；§10.3；§15 | Task 3 |
| §6 EVD-05；§8.4 | Task 4 |
| §9.3；§13；§14 | Task 5 |
| §11.2–11.5；§12.3；§17 | Task 6 |
| 阶段验收、实际技术报告与状态更新 | Task 7 |

## Self-Review / Execution Handoff

- [ ] 所有需求映射到具体 Task、文件、测试和验收步骤。
- [ ] 依赖阶段接口和本计划的 Create/Modify/Move 文件表已核对。
- [ ] 数据规模、权限、未知状态和报告边界与正式规格一致。
- [ ] 自动化和真实验证结果已记录；未执行任务没有勾选。
- [ ] 下一阶段只在本阶段验收完成并获得实施授权后启动。

当前交接状态：**计划已编写，待评审；未执行。**不自动触发本计划中的命令、真实运行、提交或委派。
