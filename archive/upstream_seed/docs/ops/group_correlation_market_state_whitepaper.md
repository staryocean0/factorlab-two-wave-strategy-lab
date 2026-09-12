# 群体相关性市场状态基础设施白皮书

## 1. 决策摘要

现有 CloudRidge 已经计算全市场 Pearson 相关矩阵和每股 Fisher-z 平均强度，但历史产品只发布成分、覆盖、换手和指数点位，没有连续发布群体结构时间序列。本基础设施复用现有矩阵语义，新增全市场与制造业核心池的日度群体相关指标，并以独立市场状态增量包统一发布。

指标是每天重算的市场事实，不判断自身“有效或无效”，也不默认连接择时工具。所有新产物固定：

```text
production_authority=false
factor_lifecycle_mutation=false
single_stock_authorized=false
measurement_registration=true
strategy_effectiveness_claim=false
```

## 2. 指数合成级 PIT 的裁决

DataHub 的固定自定义行业输入不是严格个股 PIT，但它明确授权：

```text
consumer_contract=cn_a_custom_industry_index_construction_grade.v1
capability=offline_fixed_version_custom_industry_index_construction
```

因此可以用于数千只股票的群体统计，不能用于单股行业判断。实现同时保存两类成员口径质量收据：

1. 2013—2020严格 CSRC 已发布快照的成员 precision/recall/Jaccard 和同期序列对照；
2. 固定种子的1%/5%/10%删除、添加、互换扰动。

制造业核心主定义包含机械制造、电子制造、化工制造、其他轻工制造、食品饮料和家用电器。成员数量来自固定版本，不写死为公式常数。

## 3. 数学合同

对交易日 `t`、群体 `U`、回看窗口 `L`：

```text
z_ij = arctanh(clip(corr(r_i, r_j), -0.999999, 0.999999))
group_corr_level = tanh(mean_{i<j}(z_ij))
b_i = mean_j(z_ij)
group_corr_dispersion = q75_i(b_i) - q25_i(b_i)
```

共同模式使用标准化收益矩阵 `X`：每只股票只在有限观测上去均值，再归一化为单位长度，缺失标准化收益填0。资产相关估计为 `X.T @ X`，其非零特征值与最多120×120的 `X @ X.T` 完全相同：

```text
group_common_mode_share = lambda_max(X.T X) / trace(X.T X)
```

这样获得确定性 PSD 估计，并避免每天对约3000×3000矩阵做 O(N³) 完整特征分解。pairwise-complete Pearson 矩阵可能非PSD，负特征质量仍在最多64只股票的确定性等距子矩阵上记录，字段同时披露诊断资产数，不能把局部诊断冒充全矩阵精确负质量。

高相关只说明一起动；持续下跌同样可以高度相关。指标公式不据此推导买卖方向。

## 4. 因果与身份

- 行情必须显式使用 DataHub `1d qfq_canonical` 固定版本。
- DataHub qfq 行的 `available_at` 记录整个固定数据产物的物化时间；交易决策可见性则来自已完成日 K 线的交易日收盘。适配器同时保留 `source_materialized_at` 和 `available_date=trading_day`，禁止混为一个时间。
- 每行保存观察日15:00完成时间、15:30属性可用时间和下一交易日 `actionable_from`。
- 改写 `t+1` 以后数据不得改变 `t` 属性。
- 逻辑键为群体、群体版本、观察日、窗口、指标和估计器版本。
- DataHub新不可变版本若旧历史前缀完全一致，可以可信追加尾部；源历史、成员版本、代码或公式改变时不信任旧尾部，强制全量重建。
- 全量和可信增量必须生成相同长表语义摘要。

## 5. 架构

```text
DataHub exact qfq bars + fixed index-grade bulk members
  -> correlation_matrix_engine
  -> group_correlation_timeseries_service
  -> immutable group product
  -> FeatureSpecSnapshot + MarketAttributeSpec additive pack
```

冻结 A2 是从单一 CloudRidge 载体 K 线计算的属性集合；群体相关性来自跨股票面板，因此不原地修改 A2。新包只引用自己的父群体产品和精确 FeatureSpec snapshot。

## 6. 成员口径质量说明

| 门 | 要求 |
|---|---:|
| 对严格制造业快照 precision | ≥90% |
| 完整制造业命名所需 recall | ≥70% |
| index-grade 与严格池同期序列 Spearman | ≥0.90 |
| 同期高中低状态一致率 | ≥85% |
| 10%扰动 level/common-mode Spearman 中位/5%分位 | ≥0.95 / ≥0.90 |
| 10%扰动 dispersion Spearman 中位/5%分位 | ≥0.90 / ≥0.80 |
| 10%扰动三状态一致率中位 | ≥85% |

这些门描述固定制造业核心池与严格历史快照之间的可比程度，不决定指标是否发布。两个股票池的时序均进入统一指标包；质量结果作为元数据随包保存。

## 7. 下游策略研究边界

历史上曾额外生成十四工具关系、条件残差和冗余收据。这些是可删除、可重做的下游研究消费者，不属于指标本体的验收条件。关系通过或失败都不得改变指标行、指标目录、每日更新时间或股票池覆盖。

## 8. 性能合同

三个摘要复用同一相关矩阵。共同模式通过最大120×120低秩 Gram 求谱；pairwise 负特征诊断最多64资产。基准脚本比较同设备、同输入的：

- 三指标总耗时 / 仅矩阵耗时 ≤1.30；
- 三指标峰值内存 / 仅矩阵峰值内存 ≤1.50。

日常构建先比较DataHub逻辑摘要、历史前缀和当前水位：无新增直接复用，前缀一致只计算新观察日，历史修订必须重建，不能为了速度静默沿用旧值。

## 9. 实现清单

- 矩阵与三指标：`src/factor_lab/market_correlation/services/correlation_matrix_engine.py`
- 日度产品：`contracts_group_timeseries.py`、`group_correlation_timeseries_service.py`
- 自动日更：`group_correlation_daily_update.py`、`scripts/run_group_correlation_daily_update.py`
- 制造业治理：`manufacturing_universe.py`
- 市场状态注册：`group_correlation_attributes.py`、`group_correlation_bundle.py`
- 可选成员质量和性能入口：`scripts/audit_manufacturing_*.py`、`scripts/benchmark_group_correlation_timeseries.py`
- 历史十四工具与残差脚本保留为下游研究，不由指标日更调用。

## 10. 当前权威状态

全市场和制造核心池均已使用DataHub最新READY日线版本 `bars_cn_a_1d_qfq_canonical_20260626_sina_auto` 完成2009—2026真实全量产品。两个包尾日均为2026-06-26，各37,716行、原始指标空值0、重复逻辑键0；统一包 `market-state-group-corr-b962bdc5288d271c` 包含两个群体、18个指标规格和75,432行属性。

制造核心池对严格历史快照及900次成员扰动的旧收据继续作为口径说明，但不再阻断指标注册。三个指标的20/60/120日版本全部保留；相互冗余或对策略没有增量，不构成删除时序数据的理由。

父仓 `run_baylum_data_update_workflow.py` 已在正常发布、仅拉取和CloudRidge无新增三条路径之前调用群体指标日更。真实首轮全量重建后，相同命令再次运行返回 `reused`；统一包仍固定 `strategy_effectiveness_claim=false`、`production_authority=false`。

实施和真实数据裁决见[验收证据](evidence/group_correlation_market_state_acceptance_20260804.md)。
