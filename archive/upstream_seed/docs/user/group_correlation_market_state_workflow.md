# 群体相关性市场状态工作流

## 这套基础设施解决什么

它把“全市场股票是不是越来越同步”“制造业内部是不是形成共同模式”做成严格因果的日度时间序列，并作为独立增量包接入市场状态指标目录。指标只负责每天给值，不声明能否预测涨跌，也不自动连接任何择时工具。

首版只有三个物理属性：

| 属性 | 白话解释 | 不能解释什么 |
|---|---|---|
| `group_corr_level` | 股票整体一起涨跌的程度 | 不区分一起涨还是一起跌 |
| `group_corr_dispersion` | 不同股票参与群体共振的差异 | 不是行业轮动方向 |
| `group_common_mode_share` | 一个共同市场模式解释了多少横截面变化 | 不是单独买卖信号 |

三个属性分别计算20、60、120日窗口。当日收盘后生成，最早从下一交易时点消费。

## 两个群体的数据口径边界

1. `cn_a_all_market` 使用精确 DataHub `1d qfq_canonical` 行情版本。
2. `cn_a_manufacturing_core_v1` 使用固定版本的指数合成级行业输入。它允许做数千只股票的群体统计，但永久标记为：
   - `pit_grade=index_construction_only`
   - `single_stock_authorized=false`
   - `strict_first_release_pit=false`
   - `membership_semantics=fixed_version_index_construction_backcast`

两个群体的完整时序都进入统一指标包。严格快照对照和成员扰动只描述制造业历史成员口径的可信程度，不决定指标是否存在，也不阻断指标注册。制造业始终携带上述 PIT 和固定回溯口径，消费者不能把它冒充为严格单股历史行业标签。

## 执行顺序

### 1. 构建制造业核心池

```bash
PYTHONPATH=src uv run python scripts/build_manufacturing_universe.py \
  --dataset-version <exact-custom-industry-version> \
  --output output/group-correlation/universes/manufacturing_core_v1.json
```

请求由客户端固定声明：

```text
consumer_contract=cn_a_custom_industry_index_construction_grade.v1
capability=offline_fixed_version_custom_industry_index_construction
```

接口没有 `symbol` 或 `latest` 参数。

### 2. 构建日度群体相关性产品

```bash
PYTHONPATH=src uv run python scripts/build_group_correlation_timeseries.py \
  --bars <exact-qfq-bars.parquet> \
  --datahub-qfq-layout \
  --members <optional-members.csv> \
  --output-root output/group-correlation/all-market \
  --universe-id cn_a_all_market \
  --universe-version <exact-universe-version> \
  --dataset-version <exact-bars-version> \
  --dataset-hash <sha256> \
  --code-version <immutable-code-version>
```

重复执行会按以下规则处理：

- 输入、代码、公式和历史前缀都一致：只计算新增尾部；
- 没有新增日期：复用原包；
- 历史被修订、源版本或配置改变：强制全量重建；
- 发布使用不可变 `versions/<bundle_id>` 和原子 `current_manifest.json`。

### 3. 可选：记录制造业成员口径质量

```bash
PYTHONPATH=src uv run python scripts/audit_manufacturing_snapshot_semantics.py <固定输入参数>
PYTHONPATH=src uv run python scripts/audit_manufacturing_snapshot_series.py <固定输入参数>
PYTHONPATH=src uv run python scripts/audit_manufacturing_membership_perturbation_full.py <固定输入参数>
PYTHONPATH=src uv run python scripts/audit_manufacturing_group_correlation_registration.py \
  --semantic-audit output/group-correlation/audits/manufacturing_snapshot_semantics_2013_2020.json \
  --strict-series-audit output/group-correlation/audits/manufacturing_snapshot_series_2013_2020/summary.json \
  --perturbation-audit output/group-correlation/audits/manufacturing_membership_perturbation_2013_2020/summary.json \
  --output output/group-correlation/audits/manufacturing_registration_decision.json
```

这些收据只补充成员口径说明，不判断指标投资有效性，也不决定是否发布时序。

### 4. 注册市场状态增量包

```bash
PYTHONPATH=src uv run python scripts/build_group_correlation_market_state_pack.py \
  --group-manifest output/group-correlation/all-market/current_manifest.json \
  --group-manifest output/group-correlation/manufacturing-core/current_manifest.json \
  --manufacturing-quality-audit output/group-correlation/audits/manufacturing_registration_decision.json \
  --output-root output/market-state-foundation/group-correlation \
  --code-version <immutable-code-version>
```

该包不会修改冻结 A2，固定包含两个股票池共18个指标规格。`measurement_registration=true` 只表示可统一查询；`strategy_effectiveness_claim=false`、`production_authority=false` 明确表示没有收益、路由或交易声明。

### 5. 每日自动增量更新

```bash
PYTHONPATH=src uv run python scripts/run_group_correlation_daily_update.py \
  --datahub-root /home/starryocean/桌面/量化/unified_datahub \
  --manufacturing-members output/group-correlation/universes/manufacturing_core_v1.json \
  --output-root output/group-correlation \
  --market-state-output-root output/market-state-foundation/group-correlation
```

父仓每日入口 `python3 ../scripts/run_baylum_data_update_workflow.py` 默认调用该脚本，即使 CloudRidge 没有新数据也会独立核对日线指标水位：

- 同一源版本且水位一致：直接 `reused`，不读取全历史；
- DataHub 发布新不可变版本、旧历史前缀一致：只追加新交易日；
- 历史前缀、成员、公式或代码版本变化：全量重建；
- 两个群体完成后才原子发布统一18指标包。

此前生成的十四工具关系收据属于独立下游研究，不是本指标工作流的组成部分，也不影响每日指标发布。

## 指标完整性失败关闭

- DataHub源版本、逻辑摘要或存储路径不明确：不更新。
- 股票池版本未固定、成员少于2只或窗口覆盖不足：不生成对应值。
- 历史前缀改变：禁止拼接，必须全量重建。
- 原始指标出现空值、重复逻辑键或两个群体水位不一致：不发布统一包。
- 成员质量、指标冗余和策略收益研究可以作为旁路说明，但不能删除指标时序或阻断纯指标注册。
- 任何结果都不自动修改策略、因子生命周期或生产路由。

数学、性能和治理依据见[群体相关性市场状态白皮书](../ops/group_correlation_market_state_whitepaper.md)，当前真实DataHub口径、时序完整性与日更收据见[验收证据](../ops/evidence/group_correlation_market_state_acceptance_20260804.md)。
