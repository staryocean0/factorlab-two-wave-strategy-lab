# 衍生品测量/执行池历史白皮书

> 当前分层：原始坐标归Layer 1；基差、展期、moneyness、IV/Greeks/Rho和波动率面
> 归Layer 2；报价可执行性、深度、费用、收益结构和账户归Layer 4。当前边界见
> [`timing_option_volatility_l1_l2_layer4_whitepaper.md`](timing_option_volatility_l1_l2_layer4_whitepaper.md)。

状态：V1.4 已接入 DataHub schedule-bound 曲线 v2、scoped 合约身份 v2 和 CFFEX 3 秒 v4。IV/Greeks/Rho 覆盖已重算；CFFEX 3 秒已 ready，连续 L1 与市场冲击继续 fail-closed。
权限：`strategy_authority=false`，不授予下单或生产权。

## 1. 目标

历史第5池同时装了测量与执行属性。当前`derivatives_execution_pool.py`只保留兼容
facade和就绪矩阵；测量权威已迁到`timing_layer1_option_market.py`、
`timing_layer2_derivative_market_measurements.py`和`timing_layer2_option_volatility.py`。

## 2. 为什么不能把 DataHub 字段直接当执行池

中金所官方日频 CSV 只暴露 `delta`。没有官方 IV、gamma、vega、theta、rho。3 秒产品提供正成交活跃度、价格和成交量共同轴，但没有连续 L1、主动买卖方向或深度。CloudRidge 里的 `cffex_option_atm_vol_proxy` 是 Brenner–Subrahmanyam 代理，不是本池认证引擎。

因此：基础行情继续只读 DataHub；高阶量必须有独立引擎、独立 measurement_kind、独立就绪矩阵。

## 3. 定价合同

CFFEX IO/HO/MO 是买方支付权利金、卖方缴纳保证金的欧式现金交割期权。远期取**同月股指期货结算价**（IO→IF，HO→IH，MO→IM），定价使用
`V=exp(-rT)·Black76(F,K,σ,T)`。折现率固定读取 DataHub
`cn_treasury_discount_curve_cn_official_20060301_20260825_v2_20260826` 的 3M/6M/1Y schedule-bound 曲线；只使用 15:00 报价收盘前满足 `available_at < quote_close` 的最后曲线，并按剩余期限在线性区间内插值。小于 3M 使用 3M，超过 1Y fail-closed；staleness 上限 4 天。同一 `available_at×tenor` 若有多个同时可见 period，按 `period DESC, published_at DESC, source_record_id DESC` 唯一选择。本口径把官方发布的 spot-yield 百分数直接转小数作为连续利率研究代理，因为源未给 day-count/复利细节；它不是交易所官方 Greeks。后果：

- IV、delta_model、gamma、vega、theta 与 rho 可在**同时具有权威到期日、折现率和同月远期**的行上识别；缺同月期货保持 `missing_forward`；
- rho 固定为“观测期货远期保持不变”时对折现率的偏导：`rho=-T·V`，同时发布每单位利率与每 1bp 两种单位；它不包含利率先改变期货基差再传入期权的总暴露；
- 2006-03-01 起的官方曲线覆盖已进入固定 research grant；长假后 staleness 超 4 天或期限超出 3M–1Y 的行保持 `missing_risk_free_rate`；
- 到期日及更短报价 fail-closed，不编日内 tenor；
- 权利金优先 `settlement`，非正则 `close`；价格上下界与内在价值均乘折现因子，越界报价不求解。

时间用 ACT/365.25，从报价日 15:00 收到最后交易日 15:00。生产物化读取 DataHub 固定身份产品
`derivative_contract_identity_cn_cffex_index_option_20191223_20260825_v2_20260826` 的 10,234 行，不再使用 FactorLab 本地规则补丁。10,058 条到期日已解析；176 条 2027 still-listed 合约因尚无权威日历而保持空值，按行标记 `missing_contract_expiry_metadata`。

## 4. 3 秒日内边界

FactorLab 固定登记 DataHub 版本
`derivative_trade_activity_cn_cffex_3s_20191223_20260825_v4_20260826`。它有 103,448,690 条正成交观察桶，V2 registry、certified claim 和 exact research serving grant 均可解析。物理 manifest 的 candidate 字样是不可变 legacy producer envelope；V2 registration 只允许补入与 lineage edge 一致的 `dataset_inputs`，其他漂移 fail closed。因 exact serving 链已通过，当前标 `ready`。

3 秒共同可依赖轴是成交活跃度、末价、成交量和 source-time uncertainty。历史父源可能带成交时点 L1，但 TDX 增量没有同一盘口合同，所以 FactorLab 禁止把该可选列提升为连续价差。市场冲击仍需主动方向或深度。

## 5. 就绪矩阵

| 能力 | 何时 ready | 失败关闭 |
|---|---|---|
| 日频合约 OHLC/结算 | 官方 1d | 无 |
| 股指期货 1m | canonical raw 1m | 无 |
| 基差 / 展期 / 持仓成交 / moneyness | 官方 close + 指数 close | 无 |
| 官方 Delta | 非空比例 | 部分缺失则 partial |
| 隐波 / 偏度期限 / gamma·vega·theta | 折现 Black-76，且全历史 `ok_ratio>=0.80` | 缺利率/到期日/远期或比例过低则 partial/blocked |
| rho | 同上；固定远期的每 bp 模型敏感度 | 不得冒充交易所官方值或总利率暴露 |
| 期权 3 秒成交活跃度 | 固定 DataHub 版本 + 验证过的 V2 registration envelope + exact serving | ready |
| 买卖价差 | 连续、跨源一致的 L1 合同 | 3 秒共同轴不含连续 L1，blocked |
| 市场冲击 | 永不 | 无深度/逐笔 |

V1 schema freeze（2026-08-24）与旧 V1.1/V1.2/V1.3 结果只读保留审计。当前合同是 V1.4。

## 6. 产物

```text
artifacts/market_state/derivatives_execution_pool_v1/
  cffex_index_derivative_daily_contracts.parquet
  cffex_index_futures_daily_basis.parquet
  cffex_index_futures_daily_roll_state.parquet
  cffex_index_option_daily_surface_reference.parquet   # moneyness，不含 IV
  cffex_index_option_daily_iv_greeks.parquet           # Black-76
  cffex_index_option_daily_iv_surface.parquet          # ATM/25Δ/期限
  cffex_index_option_3s_source_receipt.json            # 固定 3 秒源身份，不复制明细
  execution_capability_readiness.parquet
  manifest.json
```

旧 moneyness 参考表保留，避免把 V1 消费者静默换成 IV 表。

## 7. 权限

本池是研究基础设施。就绪不等于策略有效，更不等于场内 MO 或场外 1000 期权可交易。LAT 执行端变体必须另开 `$strategy-slice-rebuild` 分支，不得把本池字段写成运行时规则。

新 `/Tick` 全品类源的 ETF/商品期权当前只有 17 日样本画像与远端 inventory；两个 consumer contract 均为 `denied_source_inventory_only_no_materialized_version`。FactorLab 不为它们创建空适配器，等待各自固定 3 秒产品和 serving grant。

## 8. 2026-09-01 CSI1000 专属日内子链说明

V1.4 的“无连续L1”结论约束的是跨产品公共3秒轴，不否认后续 DataHub v5 为 CSI1000 MO 提供的**成交后快照型**一档盘口。当前分层为：

```text
衍生品执行池 V1.4
  -> 跨产品日频基差、展期、日频IV/Greeks

CSI1000 DataHub v5 / router @1.4
  -> MO成交后快照L1、同月IM、PIT曲线、合约匹配与执行回放

CSI1000 option lifecycle cost map @1.0
  -> 5分钟快照价差+往返28元的Delta等价成本地图

CSI1000 MO quote-change BBO binding @1.0
  -> 2025-09-01..2026-08-25连续一档报价状态、价差、mid与一档容量
```

快照链可以识别采样时点的Bid/Ask和一档数量；新quote-change链可以连续重建MO一档状态并计算L1 BBO报价变化OFI。当前有界执行只在`order_units <= displayed opposite-side L1 size`时使用Ask1/Bid1，超出即fail closed。新源无aggressor与逐订单分类，partial impact也明确`true_counterfactual_impact_ready=false`；这些是不声称的可选高阶能力，不再阻塞有界一档研究。
