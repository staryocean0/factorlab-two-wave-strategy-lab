# 中证1000 MO 生命周期 Delta 等价成本地图 V1 白皮书

> 四层归属：`4 执行标的/账户测试`。当前统一入口见 [`timing_layer4_execution@1.0`](timing_layer4_execution_registry@1.0.json)。

基础设施：`csi1000_trade_instrument_router_v1p3`  
扩展：`csi1000_trade_instrument_router@1.2`  
性质：交易工具成本测量，不是择时策略，不生成方向 Alpha。

## 1. 要解决的问题

V1.2 已能在单个 route time 上组装完整 MO 分母、同步 L1、严格同月 IM、期限利率、Bid/Mid/Ask IV、Black-76 Greeks 和 EAS，但没有把这些能力铺成历史生命周期地图。

V1.3 将成本按以下维度物化：

- Call/Put；
- ITM/ATM/OTM 与更细 Delta 档；
- DTE 与近月/次月/远月代理；
- 日内开盘、上午、中午后、尾盘和每个五分钟时点；
- 年度与交叉维度。

## 2. 主指标

一张 MO 的 Delta 等价标的名义敞口为：

```text
delta_notional_rmb = abs(delta_F) × IM_forward × 100
```

同一时刻买 ASK、卖 BID 的可识别立即全回转成本为：

```text
spread_cash = (Ask1 - Bid1) × 100
fee_cash    = 14 + 14 = 28元

identified_hurdle_bp
  = 10000 × (spread_cash + fee_cash) / delta_notional_rmb
```

它等于现有路由器的：

```text
EAS_full_spread_bp + fee_delta_equivalent_bp
```

乘数在价差项中约掉，但在28元固定费率项中不能约掉。

## 3. 为什么不用期权权利金作分母

`(Ask-Bid)/Mid`只能回答价差占权利金多少。深实值、平值和深虚值承担的指数方向敞口不同，不能用该指标公平比较。Delta 等价分母把成本统一到“承载一单位指数方向风险需要多少BP”。

深虚值 Delta 过小时不使用 denominator floor 美化；`abs(delta)<0.05`直接失败关闭。

## 4. 因果与数据合同

- MO：固定 v5，成交触发的3秒快照观察，不冒充连续 BBO；
- 路由网格：每5分钟；
- 报价：`bucket_end <= route_time`且最多陈旧120秒；
- IM：完全同月，`bar_end`和`available_at`严格早于 route time，最多陈旧120秒；
- 利率：PIT可见期限曲线，按剩余期限在3m/6m/1y插值，最多陈旧4日；
- Greeks：Bid/Mid/Ask IV全部成功且单调后，以Mid IV计算Black-76 Delta；
- 数据期：2022-07-22至2024-12-31，全部是已消费开发测量；不读取策略收益和2025以后明细。

## 5. 生命周期分类

### 虚实值

基于绝对 Delta：

- ITM：`abs(delta)>0.60`；
- ATM：`0.40<=abs(delta)<=0.60`；
- OTM：`abs(delta)<0.40`。

另保留 Deep ITM/ITM/ATM/OTM/Deep OTM 五档。该分类是成本地图坐标，不是选合约命令。

### 期限

- DTE：0–3、4–7、8–14、15–30、31–60、61–120、120以上；
- 近月代理：0–30日；次月代理：31–60日；远月代理：60日以上。

### 日内

保留每个五分钟时点，并汇总为开盘5分钟、开盘后10分钟、上午主体、午后开盘5分钟、午后主体、14:30后和收盘5分钟。

## 6. 权限边界

该地图只识别价差和固定手续费：

- 市场冲击无法由L1识别；
- MO v5不是连续BBO；
- Theta已经包含在实际权利金路径中，不在立即成交门槛中重复扣除；
- 地图不自动生成时段禁入、DTE阈值或“最佳档位”；
- 与策略结合时，策略另提供预期标的运动BP，再计算`成本BP/预期运动BP`。

因此`complete_all_in_cost_ready=false`、`routing_authority=false`、`production_authority=false`。

## 7. 实际物化结果

2022-07-22至2024-12-31共扫描18,067,403条MO快照，形成1,386,080个五分钟因果报价坐标；1,011,220个坐标完成严格同月IM、期限利率、Bid/Mid/Ask IV、Delta和成本计算，覆盖1,815个合约、594个交易日。

### 总体成本

| 指标 | 中位数 | P90 |
|---|---:|---:|
| 价差+28元 Delta等价成本 | 8.70bp | 23.41bp |
| 单独价差 EAS | 6.46bp | 20.00bp |
| 单独28元费率 | 1.47bp | — |

总体中位数下，价差约占已识别成本的74%，仍是第一大项。

### 虚实值

| 档位 | 中位成本 | P90 |
|---|---:|---:|
| ITM | 6.81bp | 18.56bp |
| ATM | 6.58bp | 18.25bp |
| OTM | 10.75bp | 25.99bp |
| Deep OTM | 12.44bp | 27.99bp |

ATM在总体中位数略低于ITM，但ITM的固定费率最低；OTM特别是Deep OTM明显更贵。该表是全体期限和时段混合结果，不授权“永远选ATM”。

### 期限

| 期限 | 中位成本 | P90 |
|---|---:|---:|
| 0–30日 | 6.52bp | 13.96bp |
| 31–60日 | 9.17bp | 20.10bp |
| 60日以上 | 19.40bp | 41.27bp |

跨虚实值控制后仍保持同方向：例如ATM 0–3日约3.66bp、15–30日约5.24bp、61–120日约14.06bp、120日以上约18.82bp。远月较贵主要来自EAS，不是28元手续费。

### 日内

| 时段 | 中位成本 | P90 |
|---|---:|---:|
| 09:35–09:45 | 10.36bp | 28.84bp |
| 09:45–11:30 | 8.72bp | 22.92bp |
| 13:05–14:30 | 8.31bp | 21.96bp |
| 14:30–14:55 | 8.37bp | 22.33bp |
| 14:55–15:00 | 10.19bp | 43.53bp |

开盘和最后5分钟都明显变贵，尾盘主要表现为右尾恶化。精确五分钟中，09:35中位10.74bp；13:30–14:25大多约8.1–8.5bp；15:00只有61个交易日、7,537行可用，成本中位30.53bp、P90 84.36bp，不能与全样本等权解释。

09:30与13:00没有形成正式可用桶，是因为严格同月IM必须早于route time；基础设施没有用开盘后才出现的IM回填开盘当刻。

### 交叉极值示例

- 成本较低的大样本区域：近月ATM，午后主体/14:30后，中位约4.6–4.8bp；
- 成本较高区域：远月OTM，开盘后10分钟或尾盘，中位约24–25bp；
- 远月ITM尾盘样本中位约54.36bp，但只有1,735行，属于高风险诊断格而非自动禁入规则。

2023总体中位约6.56bp，2024约10.16bp，说明成本面会年度漂移，静态阈值不能从本开发地图直接获得。

## 8. 五位一体

- 文档/白皮书：本文件及`csi1000_trade_instrument_router@1.3.json`；
- 代码：`csi1000_option_lifecycle_cost_map.py`；
- 测试：`test_csi1000_option_lifecycle_cost_map.py`；
- 工作流：`docs/user/csi1000_option_lifecycle_cost_map_v1_workflow.md`；
- 可执行构建/验证：`build_...v1.py`与`validate_...v1.py`。

机器入口为 `docs/ops/csi1000_option_lifecycle_cost_map@1.0.json`。它将本工具登记为项目级基础设施，而不是 LAT、IIR 或任何单一策略的专属资产。

## 9. 历史成本等效迁移

当早期历史没有 MO 合约、IV 和 Greeks 时，本工具只允许做以下有限迁移：

```text
equivalent_net_bp
  = signed_underlying_gross_bp
  - identified_round_trip_hurdle_bp
```

这不是伪造历史期权价格，而是把真实 MO 的价差与固定费率统一成标的 Delta 等价 BP，再用于早期标的路径的成本压力评价。2022-07-22至2024-12-31的冻结校准使用25个周期根、11个虚实值档，共968,892条有效记录：275个单元均值的总体 Spearman 为0.7430，盈亏符号一致率84.0%；2022H2、2023、2024三段 Spearman 分别为0.7411、0.6054、0.7779，全部越过0.60门槛。

因此，`identified_cost_equivalent_historical_backcast` 已成为研究基础设施能力；但历史 IV、Gamma、Theta、跟踪基差和冲击仍未识别，不能称为真实历史期权回放，也不自动授权任何策略选择。
