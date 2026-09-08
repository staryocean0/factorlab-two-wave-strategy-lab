# T1 transitory-shock supply/alignment audit — 云端独立复核

日期：2026-09-08  
任务：`CL-20260908-006`  
Research identity：`T1_transitory_component_after_extreme_intraday_shock_v1`  
本地回传 commit：`c96f50d8bbc2d08253bd4176791c87e3fcdf4bc3`

## 云端结论

本地 supply/alignment 执行本身验收通过，从 `local_reported` 升级为：

`CLOUD REVIEWED / COMPLETED`

但 frozen supply gate **未通过**，因此 T1 当前 identity 的正式状态是：

`T1_current_data_event_supply_insufficient / CLOSED_BEFORE_OUTCOME`

不得执行 post-event reversal / continuation outcome。

## 1. Frozen execution identity

云端重新核对 execution freeze：

- theory intake blob = `792e768ed8d7fb1808583a49f16d42b9c7438f97`；
- supply protocol blob = `49615926077f1f2e45e08f427f745363581e2e26`；
- runner blob = `9bc4533dacb5914ee63b5d9d82a745694031b917`；
- tests blob = `e6acd417a74e4164e77f195db739b5328b8e0542`。

Frozen parameters：

- prior reference bars = `960`；
- extreme threshold = `abs(robust_z) >= 5.0`；
- event fine support = exactly `5` native 1m terminal rows；
- minimum aligned supply = BUILD `150`, 2019 `50`, 2020 `50`；
- outcome execution authorized = false；
- GitHub Actions authorized = false。

本地结果提交没有获得修改这些门槛的权限。

## 2. Source identity

本地 receipt 与 frozen source identity 一致：

### Native 5m

- path = `data/development/5m_offset_0.parquet`；
- rows = `70,114`；
- SHA256 = `bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48`。

### Event-path 1m

- path = `data/development/1m_official.parquet`；
- rows = `350,561`；
- SHA256 = `755217afce9dec383e48cd46d591402fa90dc50897abeb3dc7097c9a18a109d4`。

- symbol = `000852.SH`；
- admitted dates = `2015-01-05..2020-12-31`；
- post-2020 rows read = false。

这里的 1m 数据只用于检查 **当前已经完成的 extreme 5m bar 自身**的 terminal path；它不是 CL-005 的 authoritative DataHub source-support identity，两条任务的数据角色不能混淆。

## 3. Supply gate 复核

Frozen gate 与实际结果：

| partition | extreme events | aligned events | minimum | result |
|---|---:|---:|---:|---|
| BUILD 2015–2018 | 366 | 364 | 150 | PASS |
| 2019 | 48 | 48 | 50 | **FAIL** |
| 2020 | 87 | 87 | 50 | PASS |

BUILD 两个 rejected events 的原因被明确 ledger：

- `support_count_3 = 1`；
- `support_count_4 = 1`。

2019/2020 没有 alignment rejection。

因此 failure 不是对齐错误造成的；冻结 5-sigma event definition 在 2019 本身只产生 `48` 个可对齐事件，低于结果前冻结的 `50`。

## 4. Evidence boundary

本地 receipt 明确记录：

- `post_event_outcomes_read = false`；
- `future_return_read = false`；
- `reversal_or_continuation_label_read = false`；
- `PnL_read = false`；
- `post_2020_rows_read = false`；
- `outcome_execution_authorized = false`。

云端没有发现可以合法打开 T1 outcome 的依据。

## 5. 一个额外但不用于救 gate 的描述事实

`within_bar_retrace_fraction` 在三个 partition 的 median 和 p75 都是 `0.0`。这说明在 frozen 5-sigma extreme bars 中，大部分事件到 5m close 时并没有表现出该定义下的明显 terminal retrace。

该描述**不参与 supply gate，也不能被用来重新设计 threshold/path variable**。既然 2019 supply 已 fail，本 identity 在读取 post-event outcome 之前就关闭。

## 6. 禁止的后验动作

因 supply failure，不允许：

- 把 5-sigma 降到 4.5/4/3 sigma；
- 把 prior window 960 改短；
- 对正负 shock 分别设阈值；
- 换其它 5m offset；
- 只选某些时段；
- 新增 RSI/MACD/roughness/event-density；
- 填 volume 或发明 spread/order-book/news proxy；
- 直接运行 frozen future outcome；
- 把 48/50 描述成“接近通过所以可以继续”。

## 7. 科学解释边界

本结果只说明：

> **在当前 2015–2020 CSI1000 数据、960-bar past-only normalization、5 robust-sigma extreme event 和 exact 5×1m alignment 这一个冻结 identity 下，年度供给门未满足。**

它不证明“暂时性价格压力/冲击来源区分”这一大类机制在经济学上错误；但当前 T1 v1 已经失去 outcome budget。

未来重开至少需要：

- materially new data，且重新在 outcome 前冻结 evidence roles；或
- 一个独立理论先定义的新 identity，而不是利用本次 48/50 结果改参数。

## 8. 最终权限

`CL-20260908-006 = CLOUD REVIEWED / COMPLETED`

`T1_transitory_component_after_extreme_intraday_shock_v1 = CLOSED_BEFORE_OUTCOME`

- T1 outcome execution = false；
- fresh OOS = false；
- PnL / paper trading / production = false。
