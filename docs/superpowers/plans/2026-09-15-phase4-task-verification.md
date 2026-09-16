# P4-A1：任务执行与独立验证 Implementation Plan

> **执行约定：**按 Task 逐项执行，使用未勾选步骤跟踪。本文是实施计划，不是执行授权；当前不得执行代码修改、外部调用、提交或子代理委派。获准实施后先核对前置阶段和工作区已有改动，再按测试失败→最小实现→测试通过推进。

**Status:** 初稿，待评审；所有实施步骤未执行。

**Goal:** 建立可重置的真实 Agent 任务执行与独立结果验证，交付 6 个种子任务。

**Architecture:** benchmarks 管理 Task/Trial、环境、runner 与 verifier；evaluation 提供结果模型与四态聚合；独立 run 记录被测执行和验证。

**Tech Stack:** Python 3.11+、Pydantic v2、typing.Protocol、Typer/Rich、pytest、ruff、mypy、现有 Trace Core。真实执行使用已授权的 Agent/MCP/容器环境；新增外部依赖另行确认。

**Prerequisite:** P4-P 验收通过；真实 runner 的版本、隔离环境、可用工具和预算已获授权。

**Canonical Spec:** [正式规格](../../specs/evaluation-diagnosis-engine.md)。

**Design:** [本批设计](../specs/2026-09-15-phase4-task-verification-design.md)。

**Roadmap:** [总实施计划](2026-09-15-phase4-implementation-roadmap.md)。

---

## File Structure

以下为本阶段计划创建/修改/迁移的文件，不表示这些文件已经存在。Modify 包括前置阶段按计划创建的文件；实际开始时必须核对。

- `Create: src/lumiagent/benchmarks/__init__.py`
- `Create: src/lumiagent/benchmarks/models.py`
- `Create: src/lumiagent/evaluation/models.py`
- `Create: src/lumiagent/evaluation/outcomes.py`
- `Create: tests/benchmarks/test_models.py`
- `Create: tests/evaluation/test_outcomes.py`
- `Create: src/lumiagent/benchmarks/environment.py`
- `Create: src/lumiagent/benchmarks/environments/__init__.py`
- `Create: src/lumiagent/benchmarks/environments/container.py`
- `Create: tests/benchmarks/test_environment.py`
- `Create: src/lumiagent/benchmarks/runners/__init__.py`
- `Create: src/lumiagent/benchmarks/runners/base.py`
- `Create: src/lumiagent/benchmarks/runners/claude_code.py`
- `Create: benchmarks/configs/claude-code.example.json`
- `Create: tests/benchmarks/test_claude_code_runner.py`
- `Create: src/lumiagent/benchmarks/verifier.py`
- `Create: src/lumiagent/benchmarks/artifacts.py`
- `Create: tests/benchmarks/test_verifier.py`
- `Create: src/lumiagent/benchmarks/execution.py`
- `Create: src/lumiagent/benchmarks/storage.py`
- `Modify: src/lumiagent/cli.py`
- `Modify: .gitignore`
- `Create: tests/benchmarks/test_execution.py`
- `Create: tests/benchmarks/test_storage.py`
- `Create: tests/test_cli_bench.py`
- `Create: benchmarks/eval-suite/suite.json`
- `Create: benchmarks/eval-suite/README.md`
- `Create: benchmarks/eval-suite/tasks/coding_bug_001/task.json`
- `Create: benchmarks/eval-suite/tasks/coding_interface_001/task.json`
- `Create: benchmarks/eval-suite/tasks/mcp_pagination_001/task.json`
- `Create: benchmarks/eval-suite/tasks/mcp_update_001/task.json`
- `Create: benchmarks/eval-suite/tasks/combined_context_001/task.json`
- `Create: benchmarks/eval-suite/tasks/combined_readonly_001/task.json`
- `Create: tests/benchmarks/test_seed_suite.py`

阶段结束后才创建：`docs/reports/phase4-task-verification-technical-report.zh-CN.md`。

共同更新：`docs/HANDOFF.zh-CN.md` 和本计划的实际执行状态；README/PROJECT_SPEC 仅在对应实现验证后更新交付状态。

## 执行前检查

- [ ] 核对正式规格、本阶段设计和依赖阶段的实际验收结果。
- [ ] 检查 git status，保留已有用户改动，不执行全仓库格式化或批量覆盖。
- [ ] 记录现有测试与主线 lint/type 基线；旧 legacy 的已知问题单独列出，不算新主线已解决的问题。
- [ ] 新文件与接口按本计划创建；若前置实际接口发生变化，先更新设计与计划，不能临时绕过合同。

命令均从仓库根目录的 PowerShell 执行，先设置 `$env:PYTHONPATH = "src"`。下面的 FAIL/PASS 是预期，不是已运行结果。失败必须来自目标断言或尚未实现的接口；依赖缺失、临时目录权限等环境错误不能当作 TDD 的有效失败。

---

### Task 1: 任务、Trial 与结果模型

**Spec:** §7；§8.2；§9.1；§18。

**Files:**
- `Create: src/lumiagent/benchmarks/__init__.py`
- `Create: src/lumiagent/benchmarks/models.py`
- `Create: src/lumiagent/evaluation/models.py`
- `Create: src/lumiagent/evaluation/outcomes.py`
- `Create: tests/benchmarks/test_models.py`
- `Create: tests/evaluation/test_outcomes.py`

- [ ] **Step 1: 编写失败测试**

TaskSpec 拒绝重复 requirement_id、非法预算和未知字段；agent-visible 视图不含验收秘密；测试 fail 优先、unknown 不算成功、全部不适用为 unknown，以及版本往返。

- [ ] **Step 2: 运行并确认目标失败**

```powershell
python -m pytest tests/benchmarks/test_models.py tests/evaluation/test_outcomes.py -v
```

Expected: FAIL。新模型和 outcomes 模块不存在。

- [ ] **Step 3: 实现最小可用行为**

实现 TaskSpec、AgentConfig、TrialRecord、VerifierResult、EvaluationItem；模型显式 schema_version。outcomes 只处理有证据的单项状态，不读取 AgentRun.status 猜任务结果。

- [ ] **Step 4: 重跑测试并检查改动范围**

```powershell
python -m pytest tests/benchmarks/test_models.py tests/evaluation/test_outcomes.py -v
```

Expected: PASS，所有上述断言成立。检查新旧合同、错误路径、输入不变性和类型边界；不得删掉失败断言或以固定假结果满足测试。

---

### Task 2: 隔离环境与生命周期

**Spec:** §5.2；§7.1；§15。

**Files:**
- `Create: src/lumiagent/benchmarks/environment.py`
- `Create: src/lumiagent/benchmarks/environments/__init__.py`
- `Create: src/lumiagent/benchmarks/environments/container.py`
- `Create: tests/benchmarks/test_environment.py`

- [ ] **Step 1: 编写失败测试**

fake 环境验证 prepare/healthcheck/reset/cleanup 顺序；拒绝宿主敏感目录、Docker socket、越界路径、未授权网络；启动失败和取消也执行清理，不吞掉原始错误。

- [ ] **Step 2: 运行并确认目标失败**

```powershell
python -m pytest tests/benchmarks/test_environment.py -v
```

Expected: FAIL。环境接口和隔离策略未实现。

- [ ] **Step 3: 实现最小可用行为**

定义 Environment Protocol 与受控容器实现；资源上限、挂载、网络和秘密注入由受审核配置控制。纯临时目录不能作为安全实现，外部运行前验证容器后端与固定环境摘要。

- [ ] **Step 4: 重跑测试并检查改动范围**

```powershell
python -m pytest tests/benchmarks/test_environment.py -v
```

Expected: PASS，所有上述断言成立。检查新旧合同、错误路径、输入不变性和类型边界；不得删掉失败断言或以固定假结果满足测试。

---

### Task 3: 真实 Claude Code runner 与版本配置

**Spec:** §3.1；§5.2；§7.2。

**Files:**
- `Create: src/lumiagent/benchmarks/runners/__init__.py`
- `Create: src/lumiagent/benchmarks/runners/base.py`
- `Create: src/lumiagent/benchmarks/runners/claude_code.py`
- `Create: benchmarks/configs/claude-code.example.json`
- `Create: tests/benchmarks/test_claude_code_runner.py`

- [ ] **Step 1: 编写失败测试**

替身进程验证 argv 数组、工作区、版本采集、有限环境变量、超时、取消和非零退出；用临时 hooks 日志验证 converter 被调用；不得记录凭证或用拼接 shell 执行任务文本。

- [ ] **Step 2: 运行并确认目标失败**

```powershell
python -m pytest tests/benchmarks/test_claude_code_runner.py -v
```

Expected: FAIL。runner 和配置合同不存在。

- [ ] **Step 3: 实现最小可用行为**

实现 AgentRunner.run 与 ClaudeCodeRunner，配置可执行文件、版本探测、参数模板和预算。实现时核对获准 CLI 版本再锁定参数；采集用现有 hooks，不要求 CaptureStrategy 门面。示例配置不含密钥。

- [ ] **Step 4: 重跑测试并检查改动范围**

```powershell
python -m pytest tests/benchmarks/test_claude_code_runner.py -v
```

Expected: PASS，所有上述断言成立。检查新旧合同、错误路径、输入不变性和类型边界；不得删掉失败断言或以固定假结果满足测试。

---

### Task 4: 独立 verifier 与候选产物

**Spec:** §8.1；§9.1；§11.3；§15。

**Files:**
- `Create: src/lumiagent/benchmarks/verifier.py`
- `Create: src/lumiagent/benchmarks/artifacts.py`
- `Create: tests/benchmarks/test_verifier.py`

- [ ] **Step 1: 编写失败测试**

未修复候选 fail、参考修复 pass、错误修复被拒；修改仓库内测试不能改变权威验收；verifier 崩溃输出 unknown，断言失败输出 fail；MCP 对象成功更新但额外副作用被检出。

- [ ] **Step 2: 运行并确认目标失败**

```powershell
python -m pytest tests/benchmarks/test_verifier.py -v
```

Expected: FAIL。独立验证和产物隔离尚未实现。

- [ ] **Step 3: 实现最小可用行为**

将候选应用到干净基线并运行受保护检查，分别保存 execution_status 和逐项结果。产生独立 verifier AgentRun 与可寻址日志、文件或状态 artifact。

- [ ] **Step 4: 重跑测试并检查改动范围**

```powershell
python -m pytest tests/benchmarks/test_verifier.py -v
```

Expected: PASS，所有上述断言成立。检查新旧合同、错误路径、输入不变性和类型边界；不得删掉失败断言或以固定假结果满足测试。

---

### Task 5: Trial 编排、存储与 bench CLI

**Spec:** §5.2；§7.2；§13；§14.1；§15。

**Files:**
- `Create: src/lumiagent/benchmarks/execution.py`
- `Create: src/lumiagent/benchmarks/storage.py`
- `Modify: src/lumiagent/cli.py`
- `Modify: .gitignore`
- `Create: tests/benchmarks/test_execution.py`
- `Create: tests/benchmarks/test_storage.py`
- `Create: tests/test_cli_bench.py`

- [ ] **Step 1: 编写失败测试**

每个 repeat 使用独立工作区和 trial_id；失败、取消、超时仍保存；预算未确认时 runner 不被调用；已有输出和越界路径被拒；--fail-on-task-failure 四种结果正确。

- [ ] **Step 2: 运行并确认目标失败**

```powershell
python -m pytest tests/benchmarks/test_execution.py tests/benchmarks/test_storage.py tests/test_cli_bench.py -v
```

Expected: FAIL。bench 子命令与 Trial 存储尚未存在。

- [ ] **Step 3: 实现最小可用行为**

通过单一 execution pipeline 编排并在 finally 清理。存储使用原子新建、输入摘要和独立 run 引用。bench run 输出 trial-index，预留 experiment_id，不写比较引擎。将新增本地输出目录加入 .gitignore。

- [ ] **Step 4: 重跑测试并检查改动范围**

```powershell
python -m pytest tests/benchmarks/test_execution.py tests/benchmarks/test_storage.py tests/test_cli_bench.py -v
```

Expected: PASS，所有上述断言成立。检查新旧合同、错误路径、输入不变性和类型边界；不得删掉失败断言或以固定假结果满足测试。

---

### Task 6: 构造六个任务并验证验收器

**Spec:** §4；§11.2/11.3；§16 P4-A1。

**Files:**
- `Create: benchmarks/eval-suite/suite.json`
- `Create: benchmarks/eval-suite/README.md`
- `Create: benchmarks/eval-suite/tasks/coding_bug_001/task.json`
- `Create: benchmarks/eval-suite/tasks/coding_interface_001/task.json`
- `Create: benchmarks/eval-suite/tasks/mcp_pagination_001/task.json`
- `Create: benchmarks/eval-suite/tasks/mcp_update_001/task.json`
- `Create: benchmarks/eval-suite/tasks/combined_context_001/task.json`
- `Create: benchmarks/eval-suite/tasks/combined_readonly_001/task.json`
- `Create: tests/benchmarks/test_seed_suite.py`

- [ ] **Step 1: 编写失败测试**

校验三类各两项、来源/许可/摘要齐全、初始状态可重置、无操作/参考/错误候选的预期；只读任务以禁止副作用为负例。manifest 指向存在的环境、参考解与 verifier 文件。

- [ ] **Step 2: 运行并确认目标失败**

```powershell
python -m pytest tests/benchmarks/test_seed_suite.py -v
```

Expected: FAIL。suite 和任务资产尚不存在，负例/参考验收尚未验证。

- [ ] **Step 3: 实现最小可用行为**

先按 [`benchmarks/eval-suite/SOURCE_CATALOG.md`](../../../benchmarks/eval-suite/SOURCE_CATALOG.md) 选定真实来源并记录，不凭空编造 issue。每个 task 目录补齐 instruction.md、environment、protected verifier/reference 与 source metadata；测试从 manifest 发现资产。保护材料不得挂入 Agent 工作区，运行记录本地保存。

- [ ] **Step 4: 重跑测试并检查改动范围**

```powershell
python -m pytest tests/benchmarks/test_seed_suite.py -v
```

Expected: PASS，所有上述断言成立。检查新旧合同、错误路径、输入不变性和类型边界；不得删掉失败断言或以固定假结果满足测试。

---

### Task 7: 全量验证、真实路径与阶段技术报告

**Files:**
- Create after verification: `docs/reports/phase4-task-verification-technical-report.zh-CN.md`
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

先完成容器后端健康检查并确认版本、预算和全部测试资源授权；从示例创建本地 Agent 配置，不能将未填写模板当作真实配置。

```powershell
$env:PYTHONPATH = "src"
python -m lumiagent.cli bench run benchmarks/eval-suite/suite.json --agent .lumiagent/config/claude-code.json --repeat 1 --output .lumiagent/benchmarks/p4-a1-acceptance
```

Expected: 6 个真实任务均有 Trial、实际 Agent 证据、独立验证与清理记录；Agent 可以成功或失败，但不能用 fake runner 充数或省略失败记录。

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
| §7；§8.2；§9.1；§18 | Task 1 |
| §5.2；§7.1；§15 | Task 2 |
| §3.1；§5.2；§7.2 | Task 3 |
| §8.1；§9.1；§11.3；§15 | Task 4 |
| §5.2；§7.2；§13；§14.1；§15 | Task 5 |
| §4；§11.2/11.3；§16 P4-A1 | Task 6 |
| 阶段验收、实际技术报告与状态更新 | Task 7 |

## Self-Review / Execution Handoff

- [ ] 所有需求映射到具体 Task、文件、测试和验收步骤。
- [ ] 依赖阶段接口和本计划的 Create/Modify/Move 文件表已核对。
- [ ] 数据规模、权限、未知状态和报告边界与正式规格一致。
- [ ] 自动化和真实验证结果已记录；未执行任务没有勾选。
- [ ] 下一阶段只在本阶段验收完成并获得实施授权后启动。

当前交接状态：**计划已编写，待评审；未执行。**不自动触发本计划中的命令、真实运行、提交或委派。
