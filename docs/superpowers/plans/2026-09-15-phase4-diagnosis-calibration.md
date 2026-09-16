# P4-B1：诊断与校准 Implementation Plan

> **执行约定：**按 Task 逐项执行，使用未勾选步骤跟踪。本文是实施计划，不是执行授权；当前不得执行代码修改、外部调用、提交或子代理委派。获准实施后先核对前置阶段和工作区已有改动，再按测试失败→最小实现→测试通过推进。

**Status:** 初稿，待评审；所有实施步骤未执行。

**Goal:** 形成有证据、可弃判的诊断，并以48条审核轨迹和三个基线验证质量。

**Architecture:** diagnosis 使用只读证据工具和受限模型网关，输出结构化假设与反证；校准评分器单独读取标签，模型只接收证据视图。

**Tech Stack:** Python 3.11+、Pydantic v2、typing.Protocol、Typer/Rich、pytest、ruff、mypy、现有 Trace Core。真实执行使用已授权的 Agent/MCP/容器环境；新增外部依赖另行确认。

**Prerequisite:** P4-A2 验收通过；模型调用、校准数据来源和人工审核流程已获授权。

**Canonical Spec:** [正式规格](../../specs/evaluation-diagnosis-engine.md)。

**Design:** [本批设计](../specs/2026-09-15-phase4-diagnosis-calibration-design.md)。

**Roadmap:** [总实施计划](2026-09-15-phase4-implementation-roadmap.md)。

---

## File Structure

以下为本阶段计划创建/修改/迁移的文件，不表示这些文件已经存在。Modify 包括前置阶段按计划创建的文件；实际开始时必须核对。

- `Create: src/lumiagent/diagnosis/__init__.py`
- `Create: src/lumiagent/diagnosis/models.py`
- `Create: tests/diagnosis/test_models.py`
- `Create: src/lumiagent/diagnosis/tools.py`
- `Create: src/lumiagent/diagnosis/knowledge.py`
- `Create: src/lumiagent/diagnosis/providers.py`
- `Create: tests/diagnosis/test_tools.py`
- `Create: tests/diagnosis/test_providers.py`
- `Create: src/lumiagent/diagnosis/engine.py`
- `Create: tests/diagnosis/test_engine.py`
- `Create: src/lumiagent/diagnosis/report.py`
- `Modify: src/lumiagent/cli.py`
- `Create: tests/diagnosis/test_report.py`
- `Create: tests/test_cli_diagnose.py`
- `Create: benchmarks/eval-suite/calibration/manifest.json`
- `Create: benchmarks/eval-suite/calibration/rubric.v1.json`
- `Create: benchmarks/eval-suite/calibration/acceptance.v1.json`
- `Create: benchmarks/eval-suite/calibration/README.md`
- `Create: tests/benchmarks/test_calibration_dataset.py`
- `Create: src/lumiagent/benchmarks/calibration.py`
- `Create: src/lumiagent/benchmarks/baselines.py`
- `Create: tests/benchmarks/test_calibration.py`
- `Create: tests/benchmarks/test_baselines.py`

阶段结束后才创建：`docs/reports/phase4-diagnosis-calibration-technical-report.zh-CN.md`。

共同更新：`docs/HANDOFF.zh-CN.md` 和本计划的实际执行状态；README/PROJECT_SPEC 仅在对应实现验证后更新交付状态。

## 执行前检查

- [ ] 核对正式规格、本阶段设计和依赖阶段的实际验收结果。
- [ ] 检查 git status，保留已有用户改动，不执行全仓库格式化或批量覆盖。
- [ ] 记录现有测试与主线 lint/type 基线；旧 legacy 的已知问题单独列出，不算新主线已解决的问题。
- [ ] 新文件与接口按本计划创建；若前置实际接口发生变化，先更新设计与计划，不能临时绕过合同。

命令均从仓库根目录的 PowerShell 执行，先设置 `$env:PYTHONPATH = "src"`。下面的 FAIL/PASS 是预期，不是已运行结果。失败必须来自目标断言或尚未实现的接口；依赖缺失、临时目录权限等环境错误不能当作 TDD 的有效失败。

---

### Task 1: 诊断合同与弃判结果

**Spec:** §10.1/10.2；§18.3。

**Files:**
- `Create: src/lumiagent/diagnosis/__init__.py`
- `Create: src/lumiagent/diagnosis/models.py`
- `Create: tests/diagnosis/test_models.py`

- [ ] **Step 1: 编写失败测试**

假设、责任层、支持/反对证据、建议和验证方案均有约束；abstained 不产生假 Core Diagnosis；无实验引用不能标 intervention_supported；允许同一问题多个原因。

- [ ] **Step 2: 运行并确认目标失败**

```powershell
python -m pytest tests/diagnosis/test_models.py -v
```

Expected: FAIL。诊断模型未实现。

- [ ] **Step 3: 实现最小可用行为**

实现 DiagnosisItem、DiagnosisReport、InterventionPlan 和弃判结构；稳定失败类型与责任层分开，复用 EvidenceRef/Evaluation ID，不重复保存原始大日志。

- [ ] **Step 4: 重跑测试并检查改动范围**

```powershell
python -m pytest tests/diagnosis/test_models.py -v
```

Expected: PASS，所有上述断言成立。检查新旧合同、错误路径、输入不变性和类型边界；不得删掉失败断言或以固定假结果满足测试。

---

### Task 2: 只读证据工具、知识接口和模型网关

**Spec:** §8.3；§10.3；§15。

**Files:**
- `Create: src/lumiagent/diagnosis/tools.py`
- `Create: src/lumiagent/diagnosis/knowledge.py`
- `Create: src/lumiagent/diagnosis/providers.py`
- `Create: tests/diagnosis/test_tools.py`
- `Create: tests/diagnosis/test_providers.py`

- [ ] **Step 1: 编写失败测试**

拒绝越界 URI、隐藏答案/标签和 shell 请求；恶意 artifact 仅作数据；空 KnowledgeProvider 可用；无模型配置有明确错误；模型无效 JSON 有上限重试且费用可记录。

- [ ] **Step 2: 运行并确认目标失败**

```powershell
python -m pytest tests/diagnosis/test_tools.py tests/diagnosis/test_providers.py -v
```

Expected: FAIL。工具权限与模型适配接口不存在。

- [ ] **Step 3: 实现最小可用行为**

定义窄模型网关和只读工具协议，必要时适配现有 provider 并单测，不将旧 Agent runtime 全部接入。知识查询可为空。费用/调用预算由程序控制，不能由模型自行突破。

- [ ] **Step 4: 重跑测试并检查改动范围**

```powershell
python -m pytest tests/diagnosis/test_tools.py tests/diagnosis/test_providers.py -v
```

Expected: PASS，所有上述断言成立。检查新旧合同、错误路径、输入不变性和类型边界；不得删掉失败断言或以固定假结果满足测试。

---

### Task 3: 有限诊断循环与独立 trace

**Spec:** §10；§9.2。

**Files:**
- `Create: src/lumiagent/diagnosis/engine.py`
- `Create: tests/diagnosis/test_engine.py`

- [ ] **Step 1: 编写失败测试**

明确失败、反证、多原因、环境问题、证据缺失、工具超时、取消和预算耗尽；每个返回引用可解析；trace 不混入被测 run；成本单独计算。

- [ ] **Step 2: 运行并确认目标失败**

```powershell
python -m pytest tests/diagnosis/test_engine.py -v
```

Expected: FAIL。诊断引擎尚不存在。

- [ ] **Step 3: 实现最小可用行为**

实现 diagnose(report, evidence, policy) 的受限状态机，用 fake provider 验证多步工具调查。输出要通过 schema 和 evidence audit。解析或证据失败返回明确 error/abstained，不输出未经审计的结论。

- [ ] **Step 4: 重跑测试并检查改动范围**

```powershell
python -m pytest tests/diagnosis/test_engine.py -v
```

Expected: PASS，所有上述断言成立。检查新旧合同、错误路径、输入不变性和类型边界；不得删掉失败断言或以固定假结果满足测试。

---

### Task 4: 报告渲染与 diagnose CLI

**Spec:** §10.1；§13；§14.1。

**Files:**
- `Create: src/lumiagent/diagnosis/report.py`
- `Modify: src/lumiagent/cli.py`
- `Create: tests/diagnosis/test_report.py`
- `Create: tests/test_cli_diagnose.py`

- [ ] **Step 1: 编写失败测试**

事实与假设清楚区分，反证/备选解释/验证方案不丢失；输入只读、输出保护、schema error退出码正确；未授权执行调查被拒；Core 导出满足原模型约束。

- [ ] **Step 2: 运行并确认目标失败**

```powershell
python -m pytest tests/diagnosis/test_report.py tests/test_cli_diagnose.py -v
```

Expected: FAIL。诊断CLI与报告尚不存在。

- [ ] **Step 3: 实现最小可用行为**

同一 DiagnosisReport 生成 JSON 和中文 Markdown，提供 diagnose report --output；默认只读取获准 bundle，运行任何干预需在 B2 另获批准。

- [ ] **Step 4: 重跑测试并检查改动范围**

```powershell
python -m pytest tests/diagnosis/test_report.py tests/test_cli_diagnose.py -v
```

Expected: PASS，所有上述断言成立。检查新旧合同、错误路径、输入不变性和类型边界；不得删掉失败断言或以固定假结果满足测试。

---

### Task 5: 构建审核轨迹与冻结校准协议

**Spec:** §11.6；§12.3。

**Files:**
- `Create: benchmarks/eval-suite/calibration/manifest.json`
- `Create: benchmarks/eval-suite/calibration/rubric.v1.json`
- `Create: benchmarks/eval-suite/calibration/acceptance.v1.json`
- `Create: benchmarks/eval-suite/calibration/README.md`
- `Create: tests/benchmarks/test_calibration_dataset.py`

- [ ] **Step 1: 编写失败测试**

至少48条、六类每类至少4、至少24自然真实、至少16分组留出；两名独立审核者信息完整，争议有记录；未冻结数值阈值或来源重叠时禁止留出运行。

- [ ] **Step 2: 运行并确认目标失败**

```powershell
python -m pytest tests/benchmarks/test_calibration_dataset.py -v
```

Expected: FAIL。校准资产与冻结协议尚未存在。

- [ ] **Step 3: 实现最小可用行为**

收集并脱敏真实运行，受控注入单独标记；保存审核标签与证据视图的隔离关系。仅使用开发集制定具体评分表、弃判计分和最低数值阈值，经评审后记录摘要和冻结时间；禁止运行后修改验收线。

- [ ] **Step 4: 重跑测试并检查改动范围**

```powershell
python -m pytest tests/benchmarks/test_calibration_dataset.py -v
```

Expected: PASS，所有上述断言成立。检查新旧合同、错误路径、输入不变性和类型边界；不得删掉失败断言或以固定假结果满足测试。

---

### Task 6: 三个基线、指标与留出执行入口

**Spec:** §12.3；§16 P4-B1。

**Files:**
- `Create: src/lumiagent/benchmarks/calibration.py`
- `Create: src/lumiagent/benchmarks/baselines.py`
- `Modify: src/lumiagent/cli.py`
- `Create: tests/benchmarks/test_calibration.py`
- `Create: tests/benchmarks/test_baselines.py`

- [ ] **Step 1: 编写失败测试**

规则、单次Judge、技能诊断使用同一证据政策；标签不进入provider请求；分子分母、假通过、弃判、无效运行和成本正确；冻结摘要变更或未审核标签阻止执行。

- [ ] **Step 2: 运行并确认目标失败**

```powershell
python -m pytest tests/benchmarks/test_calibration.py tests/benchmarks/test_baselines.py -v
```

Expected: FAIL。校准 runner 与基线比较未实现。

- [ ] **Step 3: 实现最小可用行为**

实现 bench calibrate 入口和离线可复算指标；运行日志完整保留。规则无可用归因时明确弃判，而不是编造基线。真实调用使用获准模型，fake结果不得写为真实校准。

- [ ] **Step 4: 重跑测试并检查改动范围**

```powershell
python -m pytest tests/benchmarks/test_calibration.py tests/benchmarks/test_baselines.py -v
```

Expected: PASS，所有上述断言成立。检查新旧合同、错误路径、输入不变性和类型边界；不得删掉失败断言或以固定假结果满足测试。

---

### Task 7: 全量验证、真实路径与阶段技术报告

**Files:**
- Create after verification: `docs/reports/phase4-diagnosis-calibration-technical-report.zh-CN.md`
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

先确认48条资产审核完毕和 acceptance 数值已冻结，再授权使用真实模型；不得在首次看到留出结果后补阈值。

```powershell
$env:PYTHONPATH = "src"
python -m lumiagent.cli bench calibrate benchmarks/eval-suite/calibration/manifest.json --policy benchmarks/eval-suite/calibration/acceptance.v1.json --output .lumiagent/benchmarks/p4-b1-calibration
```

Expected: 三条基线的完整留出指标、证据审计和费用有记录；达到冻结门槛才能验收，否则保留失败与阻塞，不改样本或阈值使结果通过。

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
| §10.1/10.2；§18.3 | Task 1 |
| §8.3；§10.3；§15 | Task 2 |
| §10；§9.2 | Task 3 |
| §10.1；§13；§14.1 | Task 4 |
| §11.6；§12.3 | Task 5 |
| §12.3；§16 P4-B1 | Task 6 |
| 阶段验收、实际技术报告与状态更新 | Task 7 |

## Self-Review / Execution Handoff

- [ ] 所有需求映射到具体 Task、文件、测试和验收步骤。
- [ ] 依赖阶段接口和本计划的 Create/Modify/Move 文件表已核对。
- [ ] 数据规模、权限、未知状态和报告边界与正式规格一致。
- [ ] 自动化和真实验证结果已记录；未执行任务没有勾选。
- [ ] 下一阶段只在本阶段验收完成并获得实施授权后启动。

当前交接状态：**计划已编写，待评审；未执行。**不自动触发本计划中的命令、真实运行、提交或委派。
