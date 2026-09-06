# Two-Wave Layer 3 Research Control Plane

This private repository is a bounded FactorLab research theme package. Its
purpose is to implement and validate a causal two-complete-wave parent-structure
recognizer. It is not an authority to trade, mutate the local FactorLab current
pointer, or promote a strategy.

## Read order

1. `README.md`
2. `docs/INDEX.md`
3. `docs/user/two_wave_strategy_handoff_prompt.md`
4. `docs/governance/data_usage_declaration.json`
5. `docs/governance/layer3_tool16_candidate_slot.json`
6. The current Layer 1/2/3 contracts linked from `docs/INDEX.md`

## Frozen boundaries

- `tool_registry_v1_5` is the immutable current fifteen-tool prefix.
- The proposed sixteenth identity is
  `two_wave_parent_structure_recognizer`; it is only a candidate slot.
- Do not edit V1.5 in place. A candidate registry must be a new V1.6 descendant
  that preserves all fifteen identities byte-for-byte and appends exactly one
  research-only tool.
- The current Layer 3 architecture is
  `timing_layer3_strategy_architecture@2.2`; the current identity registry is
  `timing_strategy_identity_registry@2.2`. Neither has a registered usable
  strategy.
- This branch is infrastructure/shape-recognition research. It may not emit a
  position, choose an option contract, claim economic routing authority, or
  alter Layer 4.
- Never use result-driven calendar rules. Never call any provided year, date,
  event, or hand-labelled example a runtime state.

## Data contract

- All shipped market rows are `000852.SH` CSI1000 index signal data.
- The only shipped interval is 2015-01-05 through 2020-12-31 and its role is
  `development_material`.
- 2009-2014 minute history is unavailable for this index. The standard twelve
  2009-2020 strategy-slice promotion contract therefore cannot pass here.
- 2021 and later rows are physically absent and must not be downloaded,
  inferred, requested over the network, or fabricated.
- Data is index signal data, not a tradable fill surface. Index returns may not
  be reported as executable IM, ETF, or option returns.
- Timestamps in the package are normalized timezone-aware UTC bar-end times.
  The source serialized Shanghai wall clock is retained separately for audit.
- Use the supplied DataHub-built bar views. Do not resample new wall-clock
  frequencies locally.

## Required research order

1. Freeze the recognition specification and evaluation protocol before reading
   outcome metrics.
2. Implement online pivots/cycles, same-scale pairing, two-wave envelope and
   classification, versioned events, replay export, annotation support and
   targeted synthetic tests.
3. Prove prefix invariance: streaming and batch replay must produce identical
   confirmed events on every identical data prefix; appended future rows may
   not rewrite confirmed history.
4. Evaluate morphology against independent labels. Algorithm-produced labels
   are never ground truth. If labels are absent, report
   `morphology_replication_not_yet_accepted`.
5. Only after morphology acceptance may the third-wave hypothesis be opened.
6. Only after the statistical stage is frozen may a trading baseline be opened.

Do not optimize trading P&L to select the recognizer. Do not skip directly to a
ZigZag breakout backtest. Do not add fixed third-wave exits, profit targets,
timeouts, automatic reversal, or same-direction-break exits to the user baseline.

## Deliverables

- Put new reusable code under `src/factor_lab/market_state/` or
  `src/factor_lab/visual_structure/`.
- Put unit tests under `tests/unit/`.
- Put the executable workflow under `scripts/`.
- Put specifications and results under `docs/`.
- Put generated, reviewable results under `cloud_results/`; do not modify
  `data/development/`.
- Every conclusion must identify what was actually executed, the sample count,
  failures, unresolved gaps, and authority status.

Run at minimum:

```bash
python scripts/validate_theme_package.py
pytest -q tests/unit/test_market_state_tool_registry_v1_5.py \
  tests/unit/test_timing_infrastructure_four_layer_inventory.py \
  tests/unit/test_timing_layer2_measurement_boundary.py \
  tests/unit/test_timing_layer3_strategy_boundary.py \
  tests/unit/test_timing_layer3_orchestration.py \
  tests/unit/test_timing_strategy_identity_registry.py
```

No production, paper-trading, registered-use, parameter-selection, or fresh-OOS
authority is available in this repository.

## 云端—本地交接协议（默认不生效）

### 生效条件

Protocol 1 与 Protocol 2 **默认不生效**。只有在当前任务中被明确告知“你和云端协作”时才生效。同等表述包括“按云端交接协议执行”、“这是云端与本地协作”。

把一项任务发到某个云端主题仓库、并要求该云端会话继续执行，也视为已经明确告知**该云端会话**启用本协议。

### 不生效的情况

正常情况下，许多任务由本地发起、在本地执行。即使本协议已经写进 `AGENTS.md`，只要当前任务没有上述明确告知，本协议就不生效：

- 按普通本地任务继续工作，不要去写交接文档、等待云端，或把步骤发到 GitHub Actions；
- 不要因为本文存在，就把本地任务改写成云端协作任务；
- 未生效时，下面 Protocol 1 / Protocol 2 没有运行时效力。

本协议即使生效，也只改变执行地点和沟通方式，不扩大训练、数据搬迁、金融验收或生产权限。

### Protocol 1：云端缺数据时的文档交接与本地反馈

适用于已激活协作后的计算、测试和证据检查。某一步因云端缺少所需数据而无法执行时，云端 AI 必须将该步骤写入 [云端—本地沟通文档](docs/ops/cloud_local_communication.md)，并在当次回复中明确告知用户任务编号、阻断原因、文档路径和需要本地大模型完成的事项，由用户安排本地大模型接手。不能只说“等待数据”、静默跳过，或默认要求把全部原始数据搬到云端。若沟通文档尚不存在，在首次交接时创建，不要为此先搬数据。

交接只需一份可执行记录：任务目标与所需结论、代码分支/提交、已完成和未执行的步骤、缺失的最小数据及口径、执行命令或实施步骤、预期输出和验收条件。尚无可用执行器时如实写明需要本地实现的部分，不把拟议命令写成已经可以运行。已有同一任务记录则复用，历史大清单用链接定位，不反复复制或索取同一批文件。

本地大模型完成后，在同一沟通记录中反馈实际代码版本、数据范围与必要身份摘要、命令与退出码、结果及产物位置、失败或未验证事项；大数据和大产物留在本地，只回传必要的小报告或可访问的文档。无法直接回写仓库时，由用户转交文档供云端归档；没有本地执行通道时，云端不得声称已经自动派发或执行。

云端收到反馈后先读取并复核，区分“本地已反馈”与“云端已复核”，注明复核范围和结论后继续下游工作。不能把本地报告称为云端独立全量复验，也不能将未执行或失败项改写为通过。等待本地反馈期间，继续不依赖该缺失数据的独立工作。

### Protocol 2：计算执行位置与工作流优先级

**仅在本协议已生效时：** 云端 AI 在当前会话中直接执行 → 请求本地大模型执行 → 最后才考虑 GitHub Actions。本顺序适用于已有及后续云端工作流；工作流列出的命令说明要做什么，不意味着默认交给 Actions。未生效时不要按此顺序改写本地任务。

先按每个步骤检查数据、工具、依赖和资源。能用当前云端会话实际可用的 Python、终端等工具完成的计算、测试、静态检查和小规模验证，优先自己运行并保存真实结果，不能因已有 CI 配置就外包给 Actions。写了代码、给出命令或推测结果都不等于实际执行。

云端确实无法完成时，将该步骤按 Protocol 1 写入沟通文档，请本地大模型在其数据/算力环境执行；若已知云端缺少必要数据，可直接交接，不要求先进行注定失败的试跑。只有前两种方式不适用，且 Actions 能取得所需输入、具有可用额度并处于用户授权的资源范围内，才把 Actions 作为最后选择，并记录理由。无需为了走完顺序重复失败尝试或增加逐步审批。

用户告知 Actions 无可用额度期间，不主动派发、重跑或用反复 push 试探额度。发布前检查相关触发条件，对适用的 push/pull_request 提交使用 `[skip ci]` 等跳过标记，避免仅为保存文档触发计算；其他触发类型需另行确认，不能假定标记通用。不伪造绿色检查、不擅自移除合并保护。额度恢复也不改变上述优先级。

报告每一步的实际执行地点、已完成/未执行状态和证据位置。缺数据或额度不会自动否定策略，也不构成让无关步骤停工的理由；恢复后仅补执行仍必要的未完成步骤，不重复运行已具有适用证据的计算。
