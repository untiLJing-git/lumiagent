# P4-B2：改进实验与对照复跑 Implementation Plan

> **执行约定：**按 Task 逐项执行，使用未勾选步骤跟踪。本文是实施计划，不是执行授权；当前不得执行代码修改、外部调用、提交或子代理委派。获准实施后先核对前置阶段和工作区已有改动，再按测试失败→最小实现→测试通过推进。

**Status:** 初稿，待评审；所有实施步骤未执行。

**Goal:** 以两个不同层级的受控实验检验建议，记录全部结果、回归及限制。

**Architecture:** 最小 Experiment 包装既有 Trial pipeline；干预授权、可比较性和统计单独建模，不建立新执行/评分引擎。

**Tech Stack:** Python 3.11+、Pydantic v2、typing.Protocol、Typer/Rich、pytest、ruff、mypy、现有 Trace Core。真实执行使用已授权的 Agent/MCP/容器环境；新增外部依赖另行确认。

**Prerequisite:** P4-B1 验收通过；干预方案、未调参任务、授权资源和预算均已明确并冻结。

**Canonical Spec:** [正式规格](../../specs/evaluation-diagnosis-engine.md)。

**Design:** [本批设计](../specs/2026-09-15-phase4-improvement-experiments-design.md)。

**Roadmap:** [总实施计划](2026-09-15-phase4-implementation-roadmap.md)。

---

## File Structure

以下为本阶段计划创建/修改/迁移的文件，不表示这些文件已经存在。Modify 包括前置阶段按计划创建的文件；实际开始时必须核对。

- `Create: src/lumiagent/benchmarks/experiments.py`
- `Create: tests/benchmarks/test_experiments.py`
- `Create: src/lumiagent/benchmarks/interventions.py`
- `Create: tests/benchmarks/test_interventions.py`
- `Create: src/lumiagent/benchmarks/scheduler.py`
- `Modify: src/lumiagent/benchmarks/execution.py`
- `Modify: src/lumiagent/benchmarks/storage.py`
- `Create: tests/benchmarks/test_scheduler.py`
- `Create: src/lumiagent/benchmarks/comparison.py`
- `Create: src/lumiagent/benchmarks/report.py`
- `Modify: src/lumiagent/cli.py`
- `Create: tests/benchmarks/test_comparison.py`
- `Create: tests/test_cli_experiment.py`
- `Create: benchmarks/eval-suite/experiments/README.md`
- `Create: benchmarks/eval-suite/experiments/workflow-gate.json`
- `Create: benchmarks/eval-suite/experiments/tool-schema.json`
- `Create: src/lumiagent/diagnosis/intervention_evidence.py`
- `Create: tests/benchmarks/test_experiment_assets.py`
- `Create: tests/diagnosis/test_intervention_evidence.py`

阶段结束后才创建：`docs/reports/phase4-improvement-experiments-technical-report.zh-CN.md`。

共同更新：`docs/HANDOFF.zh-CN.md` 和本计划的实际执行状态；README/PROJECT_SPEC 仅在对应实现验证后更新交付状态。

## 执行前检查

- [ ] 核对正式规格、本阶段设计和依赖阶段的实际验收结果。
- [ ] 检查 git status，保留已有用户改动，不执行全仓库格式化或批量覆盖。
- [ ] 记录现有测试与主线 lint/type 基线；旧 legacy 的已知问题单独列出，不算新主线已解决的问题。
- [ ] 新文件与接口按本计划创建；若前置实际接口发生变化，先更新设计与计划，不能临时绕过合同。

命令均从仓库根目录的 PowerShell 执行，先设置 `$env:PYTHONPATH = "src"`。下面的 FAIL/PASS 是预期，不是已运行结果。失败必须来自目标断言或尚未实现的接口；依赖缺失、临时目录权限等环境错误不能当作 TDD 的有效失败。

---

### Task 1: 实验注册与可比较性合同

**Spec:** §7.2；§12.1。

**Files:**
- `Create: src/lumiagent/benchmarks/experiments.py`
- `Create: tests/benchmarks/test_experiments.py`

- [ ] **Step 1: 编写失败测试**

记录任务、版本、环境、rubric、verifier与配置摘要；拒绝任务版本不匹配、重复repeat键、未定义主指标和无效运行判据；冻结后变更须创建新版本。

- [ ] **Step 2: 运行并确认目标失败**

```powershell
python -m pytest tests/benchmarks/test_experiments.py -v
```

Expected: FAIL。最小实验模型尚未实现。

- [ ] **Step 3: 实现最小可用行为**

实现 ExperimentSpec 和注册记录，task/config/repeat 为调度键，复用 TrialRecord 及 storage。注册时不执行外部任务，签名或摘要不代替用户授权。

- [ ] **Step 4: 重跑测试并检查改动范围**

```powershell
python -m pytest tests/benchmarks/test_experiments.py -v
```

Expected: PASS，所有上述断言成立。检查新旧合同、错误路径、输入不变性和类型边界；不得删掉失败断言或以固定假结果满足测试。

---

### Task 2: 干预因素与授权边界

**Spec:** §10.1；§12.1；§15。

**Files:**
- `Create: src/lumiagent/benchmarks/interventions.py`
- `Create: tests/benchmarks/test_interventions.py`

- [ ] **Step 1: 编写失败测试**

仅允许声明的主要因素变化；预算、资源或写操作超出授权拒绝；授权失效/摘要变化需再确认；诊断建议文件本身不构成许可。

- [ ] **Step 2: 运行并确认目标失败**

```powershell
python -m pytest tests/benchmarks/test_interventions.py -v
```

Expected: FAIL。干预校验和授权合同不存在。

- [ ] **Step 3: 实现最小可用行为**

实现配置差异验证和授权记录，绑定实验摘要、有效期、资源和预算。baseline/candidate 的非目标因素必须固定；不自动改生产prompt、schema或权限。

- [ ] **Step 4: 重跑测试并检查改动范围**

```powershell
python -m pytest tests/benchmarks/test_interventions.py -v
```

Expected: PASS，所有上述断言成立。检查新旧合同、错误路径、输入不变性和类型边界；不得删掉失败断言或以固定假结果满足测试。

---

### Task 3: 受控调度、取消与恢复

**Spec:** §5.2；§12.1；§15。

**Files:**
- `Create: src/lumiagent/benchmarks/scheduler.py`
- `Modify: src/lumiagent/benchmarks/execution.py`
- `Modify: src/lumiagent/benchmarks/storage.py`
- `Create: tests/benchmarks/test_scheduler.py`

- [ ] **Step 1: 编写失败测试**

不同trial隔离、环境每次重置；成功写操作不因恢复重复运行；取消保留已完成/未运行项；超预算停止；未知外部副作用需人工确认后才能重试。

- [ ] **Step 2: 运行并确认目标失败**

```powershell
python -m pytest tests/benchmarks/test_scheduler.py tests/benchmarks/test_execution.py tests/benchmarks/test_storage.py -v
```

Expected: FAIL。实验级调度和恢复策略尚未实现。

- [ ] **Step 3: 实现最小可用行为**

通过既有 execution 运行基线和候选，新增检查点和受限重试策略。动态状态记录配对时间和限制。保存全部终态，不静默丢弃失败，也不伪造未执行trial。

- [ ] **Step 4: 重跑测试并检查改动范围**

```powershell
python -m pytest tests/benchmarks/test_scheduler.py tests/benchmarks/test_execution.py tests/benchmarks/test_storage.py -v
```

Expected: PASS，所有上述断言成立。检查新旧合同、错误路径、输入不变性和类型边界；不得删掉失败断言或以固定假结果满足测试。

---

### Task 4: 比较指标、报告与实验 CLI

**Spec:** §12.2；§14.1；§16 P4-B2。

**Files:**
- `Create: src/lumiagent/benchmarks/comparison.py`
- `Create: src/lumiagent/benchmarks/report.py`
- `Modify: src/lumiagent/cli.py`
- `Create: tests/benchmarks/test_comparison.py`
- `Create: tests/test_cli_experiment.py`

- [ ] **Step 1: 编写失败测试**

含unknown、环境失败、取消和无成功时分母正确；缺费用不输出0；版本不匹配拒绝；负向结果保留；show/compare默认只读；未授权--experiment不调用runner。

- [ ] **Step 2: 运行并确认目标失败**

```powershell
python -m pytest tests/benchmarks/test_comparison.py tests/test_cli_experiment.py -v
```

Expected: FAIL。比较器与experiment命令不存在。

- [ ] **Step 3: 实现最小可用行为**

实现 show/compare与bench run --experiment；输出每任务计数、全部成功重复比例、回归、成本及限制，不默认独立性。ComparisonReport 使用独立assessment引用，不修改源trial。

- [ ] **Step 4: 重跑测试并检查改动范围**

```powershell
python -m pytest tests/benchmarks/test_comparison.py tests/test_cli_experiment.py -v
```

Expected: PASS，所有上述断言成立。检查新旧合同、错误路径、输入不变性和类型边界；不得删掉失败断言或以固定假结果满足测试。

---

### Task 5: 两个实验资产与诊断证据回写

**Spec:** §10.1；§12；§16 P4-B2。

**Files:**
- `Create: benchmarks/eval-suite/experiments/README.md`
- `Create: benchmarks/eval-suite/experiments/workflow-gate.json`
- `Create: benchmarks/eval-suite/experiments/tool-schema.json`
- `Create: src/lumiagent/diagnosis/intervention_evidence.py`
- `Create: tests/benchmarks/test_experiment_assets.py`
- `Create: tests/diagnosis/test_intervention_evidence.py`

- [ ] **Step 1: 编写失败测试**

两个不同改进层级，每实验至少4个未调参任务，每配置每任务至少3次，覆盖Coding与MCP/组合；没有有效正向实验不能升级原因状态；原假设与无效/负向实验不可丢失。

- [ ] **Step 2: 运行并确认目标失败**

```powershell
python -m pytest tests/benchmarks/test_experiment_assets.py tests/diagnosis/test_intervention_evidence.py -v
```

Expected: FAIL。实验资产与干预证据绑定未实现。

- [ ] **Step 3: 实现最小可用行为**

在观察留出结果前选定workflow验证门禁和工具schema改善实验，填写真实任务/配置摘要与验收指标。正向证据仅支持对应诊断，保留限制和历史版本；无法取得正向结果如实记录阶段未通过。

- [ ] **Step 4: 重跑测试并检查改动范围**

```powershell
python -m pytest tests/benchmarks/test_experiment_assets.py tests/diagnosis/test_intervention_evidence.py -v
```

Expected: PASS，所有上述断言成立。检查新旧合同、错误路径、输入不变性和类型边界；不得删掉失败断言或以固定假结果满足测试。

---

### Task 6: 全量验证、真实路径与阶段技术报告

**Files:**
- Create after verification: `docs/reports/phase4-improvement-experiments-technical-report.zh-CN.md`
- Modify after verification: `docs/HANDOFF.zh-CN.md`、本计划与已验收的 README/PROJECT_SPEC 状态。

- [ ] **Step 1: 运行自动化验证**

```powershell
$env:PYTHONPATH = "src"
python -m pytest -v
python -m ruff check src/lumiagent/tracing src/lumiagent/adapters src/lumiagent/capture src/lumiagent/evaluation src/lumiagent/benchmarks src/lumiagent/diagnosis src/lumiagent/cli.py tests
python -m mypy src/lumiagent/tracing src/lumiagent/adapters src/lumiagent/capture src/lumiagent/evaluation src/lumiagent/benchmarks src/lumiagent/diagnosis
git diff --check
```

Expected: tests 全部通过，ruff/mypy 无新增主线问题，diff 无空白错误。命令覆盖本阶段和前置阶段模块。若已有 CLI 或其他基线问题阻止验收，须列明并完成经确认的必要修复，不能静默移除检查路径；legacy 评分器的全量治理不属于本阶段。

- [ ] **Step 2: 执行真实路径验收**

先审核两个实验合同及其固定配置，将获准配置和预算保存到本地；命令里的输出目录须为新路径。执行前不得先查看用来挑选干预的留出结果。

```powershell
$env:PYTHONPATH = "src"
python -m lumiagent.cli bench run benchmarks/eval-suite/suite.json --experiment benchmarks/eval-suite/experiments/workflow-gate.json --output .lumiagent/benchmarks/p4-b2-workflow
python -m lumiagent.cli bench run benchmarks/eval-suite/suite.json --experiment benchmarks/eval-suite/experiments/tool-schema.json --output .lumiagent/benchmarks/p4-b2-schema
python -m lumiagent.cli experiment show .lumiagent/benchmarks/p4-b2-workflow
python -m lumiagent.cli experiment show .lumiagent/benchmarks/p4-b2-schema
```

Expected: 两个不同层级实验均有完整baseline/candidate/repeat记录。至少一个满足冻结的正向条件且无新硬约束违反；另一个不论结果如何都完整报告，未满足条件不勾选验收。

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
| §7.2；§12.1 | Task 1 |
| §10.1；§12.1；§15 | Task 2 |
| §5.2；§12.1；§15 | Task 3 |
| §12.2；§14.1；§16 P4-B2 | Task 4 |
| §10.1；§12；§16 P4-B2 | Task 5 |
| 阶段验收、实际技术报告与状态更新 | Task 6 |

## Self-Review / Execution Handoff

- [ ] 所有需求映射到具体 Task、文件、测试和验收步骤。
- [ ] 依赖阶段接口和本计划的 Create/Modify/Move 文件表已核对。
- [ ] 数据规模、权限、未知状态和报告边界与正式规格一致。
- [ ] 自动化和真实验证结果已记录；未执行任务没有勾选。
- [ ] 下一阶段只在本阶段验收完成并获得实施授权后启动。

当前交接状态：**计划已编写，待评审；未执行。**不自动触发本计划中的命令、真实运行、提交或委派。
