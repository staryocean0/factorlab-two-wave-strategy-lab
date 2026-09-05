# 项目级择时策略统一评价工作流

> **唯一 current 评价入口。** 三层研发评价和桶内反事实只是本中台组件，不是并列中台。
> 组件页：[`三层评价组件`](market_state_timing_strategy_stage_evaluation_workflow.md)、
> [`路由反事实组件`](market_state_timing_evaluation_workflow.md)。

> **V4 事件证据更新（2026-08-13）**：权威的“行情供给—抓取—漏抓”结论必须来自
> 策略无关机会事件账本、完整候选×机会矩阵和责任仓生命周期账本。适配器预填的
> 聚合捕获率只保留兼容，不再是权威证据。跨期归因使用 `M/F/B/R`，分开市场供给、
> 工具架构、工具族内路由与当前参数失配。

动态参数候选还必须遵循
[稳定性优先与因子失败归因工作流](market_state_dynamic_parameter_reliability_workflow.md)。
禁止以事后全样本最优静态参数为基线，禁止用一个累计收益、加权总分或人为捕获率阈值裁决漂移。

## 1. 两种入口

先阅读[统一评价中台白皮书](../ops/market_state_timing_evaluation_platform_whitepaper.md)。

### 1.1 权威事件级入口

可以只评价一个冻结策略，不强制伪造静态—动态配对。适配器必须同时交付：

1. `event_opportunity_ledger.csv`：一行一个、与被评策略信号无关的上涨/下跌机会；
2. `event_capture_ledger.csv`：每个候选对每个机会恰好一行，包含抓取幅度、同/反向 K 线和首次抓取剩余空间；
3. `candidate_claim_ledger.csv`：一行一个候选责任仓生命周期，用于查出未匹配同向真实机会的假认领；
4. 可选 `mfbr_input_ledger.csv`：同执行、同成本、同期末平仓下的 `M/F/B/R`。

`M`是市场事后上限，`F`是已注册工具族动作事后上限，`B`是当期事后最佳的已注册固定候选，
`R`是当前候选。`F/B`只是研究上界，不产生信号、参数、路由或生产权。

### 1.2 静态—动态公共评分表入口

旧入口仍保留。同一时期、方向和状态单元必须恰好有一行静态候选和一行因果动态候选。
新产物使用 `causal_dynamic`；`six_axis_dynamic`只为旧产物兼容。

必填身份字段：

```text
candidate_id, parameter_mode, period, period_role,
period_start, period_end_exclusive,
opportunity_side, state_cell_id,
opportunity_ledger_digest, execution_semantics_digest, cost_model_digest,
parameter_policy_digest, six_axis_manifest_digest, carrier_manifest_digest,
ledger_status
```

必填市场潜力、收益守恒和策略能力字段：

```text
elapsed_years, market_opportunity_count,
market_opportunity_supply, market_opportunity_bars,
market_scale_oracle_net_value_per_year,
tool_family_oracle_net_value_per_year,
realized_net_value_per_year,
opportunity_capture_rate, opportunity_recall_rate,
mean_remaining_opportunity_fraction,
gross_value_per_opportunity, net_value_per_opportunity,
net_value_per_1000_bars, conversion_efficiency,
daily_sharpe, max_drawdown, turnover_cost_per_opportunity
```

嵌套价值必须使用同仓位集、最小持有 K 线数、执行网格、签名买入/卖出成本和期末平仓。
`period_role`只能是 `development`、`repeat_audit`、`aggregate_blackbox`；上涨和下跌必须分账。

## 2. 构建零数据合同

```bash
PYTHONPATH=src python scripts/build_market_state_timing_evaluation_platform.py
PYTHONPATH=src python scripts/validate_market_state_timing_evaluation_platform.py
```

默认输出：

```text
artifacts/market_state/timing_evaluation_platform_v4/
```

零数据构建只固化合同与迁移盘点，不对任何策略宣称有效。

## 3. 运行评价

### 3.1 事件账本与 M/F/B/R

```bash
PYTHONPATH=src python scripts/build_market_state_timing_evaluation_platform.py \
  --event-opportunity-ledger /absolute/path/to/event_opportunity_ledger.csv \
  --event-capture-ledger /absolute/path/to/event_capture_ledger.csv \
  --candidate-claim-ledger /absolute/path/to/candidate_claim_ledger.csv \
  --mfbr-ledger /absolute/path/to/mfbr_input_ledger.csv \
  --mfbr-reference-period development_2009_2017 \
  --output-dir /absolute/path/to/evaluation-package
```

当前三专项桶（不含 IIR）可复现样板：

```bash
PYTHONPATH=src python scripts/evaluate_market_state_three_specialist_no_iir_event_attribution_v1.py
```

### 3.2 静态—因果动态对照

```bash
PYTHONPATH=src python scripts/build_market_state_timing_evaluation_platform.py \
  --scorecard /absolute/path/to/common_scorecard.csv \
  --dynamic-reliability-package /absolute/path/to/reliability-package \
  --factor-failure-gate-package /absolute/path/to/factor-gate-package \
  --output-dir /absolute/path/to/evaluation-package

PYTHONPATH=src python scripts/validate_market_state_timing_evaluation_platform.py \
  --output-dir /absolute/path/to/evaluation-package
```

## 4. 输出怎么读

| 文件 | 应该回答的问题 |
|---|---|
| `event_opportunity_ledger.csv` | 真实机会的起点、极值、幅度和持续时间 |
| `event_opportunity_capture_summary.csv` | 每个候选抓到、部分抓到和漏掉了哪些机会 |
| `candidate_claim_summary.csv` | 哪些责任仓是没有匹配真实同向机会的假认领 |
| `mfbr_attribution.csv` | `M/F/B/R` 四层价值和三个可修复缺口是否精确闭合 |
| `mfbr_period_weakness_attribution.csv` | 收益变化由供给、架构、族内路由、当前参数各贡献多少 |
| `market_potential.csv` | 旧聚合评分表入口的市场潜力摘要 |
| `nested_potential_attribution.csv` | 旧聚合入口的 M/F/R 兼容归因 |
| `static_dynamic_comparison.csv` | 动态、静态是 Pareto 占优还是存在权衡 |
| `dynamic_parameter_generalization.csv` | 跨期总账差异；不能单独宣告稳定、过拟合或泛化 |

权威阅读顺序：

1. 先确认机会账本与图形一致；机会层只判“记得准不准”，没有策略通过/不通过；
2. 查候选×机会矩阵，确定抓到、漏掉和入场剩余空间；
3. 查责任仓，确定假认领、反向 K 线和损失；
4. 确认 `R=M-(M-F)-(F-B)-(B-R)` 在数值容差内闭合；
5. 比较 `ΔM`、`-Δ(M-F)`、`-Δ(F-B)` 和 `-Δ(B-R)`，再定向研究市场供给、新工具、路由或参数。

`B-R≈0`只说明当前候选在“已注册的有界固定参数族”中接近当期事后最佳，
不能宣称全局最优或“策略没有任何问题”。动态候选还必须提交块级稳定性账本、完整状态所有权和真实成本重定价。

## 5. 旧策略适配原则

- 机会定义、真/弱/假命中阈值由策略适配器注册，但机会生成不得使用该策略信号；
- 路由策略用固定桶外反事实评价目标桶；
- walk-forward 只生成因果候选，不替代三层最终评分；
- 旧累计收益、夏普和回撤可映射，但“抓住/漏掉”必须补事件账本；
- 缺层时写“不适用/证据不足”，不得伪造零值让平台通过。

V62 的跨期匹配调用仍兼容旧路径，新开发应直接使用
`factor_lab.market_state.timing_matched_attribution`。

## 6. 黑箱纪律

封印后的 2021—2026 只允许输入整段聚合评分表。事件机会、责任仓、单年、图形和 M/F/B/R 明细均不得进入。
聚合行还必须传入独立授权过程生成的
`market_state_timing_aggregate_blackbox_receipt@1.0`：

```bash
  --aggregate-blackbox-receipt /absolute/path/to/one_shot_blackbox_receipt.json
```

收据必须绑定精确聚合时期、评分表摘要、授权摘要和打开时间，并明确 `details_exposed=false`。
若需要解释黑箱退化，必须回到 2009—2020 的同类机会做匹配与图形归因，不能拆开黑箱找参数。
