# Broad Reversal / Mean-Reversion Research Control Plane

This repository historically developed the causal two-complete-wave parent-structure recognizer. As of 2026-09-08, repository-wide authority is broader:

> **discover and compare broad reversal / mean-reversion mechanisms using causal multi-scale structure, while retaining the two-wave stack as the M0 measurement foundation.**

The repository is a direction finder, not a single-strategy optimizer. It has no authority to trade, mutate the local FactorLab current pointer, promote a production strategy, or alter Layer 4.

## Repository-wide authority order

Read in this order when deciding what the project should do next:

1. `CONTINUE_HERE.md`
2. `docs/governance/reversal_mean_reversion_program_charter_v1.json`
3. `docs/governance/reversal_mean_reversion_program_state_v1.json`
4. `docs/research/reversal_mean_reversion_program_whitepaper_v1.md`
5. this `AGENTS.md`
6. post-reset lane-specific protocols / preanalysis
7. historical two-wave v0.x documents, authoritative only inside their specific M0 / historical identity

An unfinished `next_action` in an older two-wave document does not control repository-wide direction unless the current program state explicitly promotes it.

## M0 — two-wave structure measurement foundation

All existing causal two-wave work remains valid evidence for its own identity. M0 covers:

- online pivots and complete waves;
- same-scale pairing;
- parent envelope / drift / overlap / efficiency / roughness / duration / density;
- streaming, batch replay and prefix invariance;
- bar-support / offset / session information-set semantics;
- morphology replication infrastructure.

Current M0 status remains `morphology_replication_not_yet_accepted`. The operational baseline remains v0.4.3.

The v0.6.17 authoritative-source formal replay remains a legitimate M0 task (`CL-20260908-005`) and must retain its frozen protocol, source identity, fail-closed semantics and evidence labels. It does **not** block results-blind broad-program preanalysis that does not claim accepted morphology.

## Broad-program primary lanes

Give comparable shallow budgets to these mechanisms before taking one deep:

1. `R1_cross_scale_pullback`
   - intact parent trend + opposite lower-scale shock;
   - ask whether parent integrity adds information beyond counter-move severity about recovery before parent failure.

2. `R2_range_boundary_reversion`
   - range-like parent + boundary excursion;
   - ask whether temporary overshoot / failed breakout can be separated from genuine transition to trend.

3. `R3_structural_exhaustion_transition`
   - directional parent whose structural quality deteriorates;
   - ask whether degradation raises reversal/transition risk before a simple direction flip.

Secondary directions include statistical-state extremes. Relative-value / overnight dislocation is a sibling/delegated specialist, not the default mainline here.

## Common scientific coordinate system

Every new reversal hypothesis must declare before outcome inspection:

1. **scale** — lower / current / parent;
2. **parent state** — trend / range / transition / unknown;
3. **deviation object** — what exactly is abnormal;
4. **recovery/failure criterion** — what counts as reversion and what counts as state change.

A mean may be a line, band, trajectory, wave structure, distribution, relative relationship or statistical state. Do not reduce mean reversion to moving-average distance.

## Research style

Stage-1 broad discovery is deliberately shallow:

- keep 2–3 mechanisms alive in parallel;
- use small comparable candidate budgets;
- establish phenomenon -> causal observability -> chronological stability first;
- do not select by trading P&L;
- do not repeatedly tune one lane while the others have not received comparable first passes;
- promote strong lanes to dedicated identities;
- hold ambiguous lanes without rescue tuning;
- close failed lanes instead of increasing complexity until they work.

A statistical property reverting toward its own normal state is **not** by itself evidence of price mean reversion.

## Frozen infrastructure boundaries

- `tool_registry_v1_5` is the immutable current fifteen-tool prefix.
- `two_wave_parent_structure_recognizer` remains only a research candidate slot unless separately accepted.
- Do not edit V1.5 in place.
- The current Layer 3 architecture / identity registries remain research infrastructure; no registered usable strategy is granted by this repo.
- Never use result-driven calendar rules. Never call a year, date, event or hand-labelled example a runtime state.
- Direction/D1/D2/PAWCT, the old third-wave hypothesis, trading P&L, fresh OOS, paper trading and production remain frozen unless a new post-reset identity explicitly and validly opens them.

## Data contract

- Shipped market rows are `000852.SH` CSI1000 index signal data.
- The original package interval is 2015-01-05 through 2020-12-31 and is consumed/development material, never fresh.
- 2021+ rows are not authorized merely because a broad lane exists; any new data role must be frozen before outcome read.
- Data is index signal data, not a tradable fill surface. Do not report index returns as executable IM/ETF/option returns.
- Timestamps and bar-support semantics must follow the frozen DataHub contracts for the identity being executed.
- Use supplied DataHub-built bar views. Do not silently resample new wall-clock frequencies locally.
- For v0.6.17 specifically, accepted authoritative DataHub support is the 349,923-row source surface; FactorLab 350,561-row `1m_official` is not an exact replacement.
- Binary Parquet being undisplayable in UI is not missing data if it exists after clone; use Python/pyarrow.

## Causal requirements

- candidate pivots may move; confirmed historical events may not be rewritten by future rows;
- save event occurrence, confirmation, classification and executable times separately;
- no centered windows, bilateral smoothing, future extrema, full-sample normalization or hindsight parameters in online signals;
- batch replay must use the same streaming semantics;
- OHLC alone does not reveal within-bar high/low order;
- algorithm-generated structure labels are not independent morphology ground truth;
- every evidence interval must keep its actual development / repeat / holdout / fresh role.

## Current required repository-wide order

1. maintain this broad authority reset;
2. freeze common scale / parent-state / deviation / recovery vocabulary;
3. write bounded results-blind R1/R2/R3 preanalysis;
4. inventory a common existing data/evidence surface for a fair first screen;
5. execute comparable low-capacity probes without fresh-OOS or P&L claims;
6. compare lanes before any dedicated deep research;
7. continue M0 v0.6.17 formal replay in parallel when the authoritative local execution path is available.

Do not respond to the broad reset by inventing v0.6.18/v0.6.19 measurement tweaks unless the program state explicitly returns research budget to M0.

## Deliverables

- reusable measurement code: `src/factor_lab/market_state/` or `src/factor_lab/visual_structure/`;
- tests: `tests/unit/`;
- executable workflows: `scripts/`;
- specifications / decisions: `docs/`;
- reviewable generated results: `cloud_results/`;
- never modify raw development data merely to make a result pass.

Every conclusion must state actual execution location, sample count, failures/unresolved gaps, evidence role and authority status.

No production, paper-trading, registered-use, unrestricted parameter-selection or fresh-OOS authority is available by default.

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

适用于已激活协作后的计算、测试和证据检查。某一步因云端缺少所需数据而无法执行时，云端 AI 必须将该步骤写入 `docs/ops/cloud_local_communication.md`，并在当次回复中明确告知用户任务编号、阻断原因、文档路径和需要本地大模型完成的事项。不能只说“等待数据”、静默跳过，或默认要求把全部原始数据搬到云端。

交接只需一份可执行记录：任务目标与所需结论、代码分支/提交、已完成和未执行的步骤、缺失的最小数据及口径、执行命令或实施步骤、预期输出和验收条件。已有同一任务记录则复用，不反复索取同一批文件。

本地大模型完成后，在同一沟通记录中反馈实际代码版本、数据范围与必要身份摘要、命令与退出码、结果及产物位置、失败或未验证事项；大数据和大产物留本地，只回传必要的小报告或可访问文档。

云端收到反馈后先读取并复核，区分“本地已反馈”与“云端已复核”，注明复核范围和结论后继续。不能把本地报告称为云端独立全量复验，也不能将未执行或失败项改写为通过。

### Protocol 2：计算执行位置与工作流优先级

**仅在本协议已生效时：** 当前云端会话直接执行 -> 请求本地大模型执行 -> 最后才考虑 GitHub Actions。

能在当前云端会话用实际 Python/终端完成的计算、测试、静态检查和小规模验证，优先自己运行。写了代码、给出命令或推测结果都不等于实际执行。

云端确实无法完成时，按 Protocol 1 交接给本地。只有前两种方式不适用、且 Actions 能取得输入并有可用额度时，才把 Actions 作为最后选择，并记录理由。

用户告知 Actions 无额度期间，不主动派发或反复 push 试探。适用的文档提交使用 `[skip ci]`，避免无意义计算。

报告每一步的实际执行地点、已完成/未执行状态和证据位置。缺数据或额度不会自动否定策略，也不构成让无关步骤停工的理由。
