# v0.5.4 完整周期尺度资格：正式 multiview / causal adjudication 与最终判定

日期：2026-09-06  
状态：`qualification_layer_pass_promote_composite_research_baseline`

## 1. 最终判定

v0.5.4 **通过冻结的 qualification 晋级门**。

从本轮起，后续两浪形态研究使用的组合研究基线定义为：

- **parent identity / hierarchy：v0.5.2 TCSS exact-ridge tuple birth**；
- **same-scale qualification：v0.5.4 full-cycle-scale qualification**；
- `corresponding_leg_duration_mismatch`：仅保留为 morphology diagnostic，不再作为 same-scale hard rejection；
- 完整周期 duration、pair duration、amplitude、raw path efficiency、jump share、flat、clock、confirmation 等其它冻结 hard rules 保持不变；
- **D1 range / uptrend / downtrend / uncertain 仍是冻结旧层，尚未完成独立验收。**

因此这里的“升格 baseline”只表示 **parent + qualification 研究栈成为下一阶段的固定上游**，不表示整个 morphology 已验收，更不表示可以进入第三浪、收益、交易或生产。

## 2. 结果前假说没有变化

金融语义是：

> “同尺度”应由两个完整 reversal cycles 的时间尺度相近来约束，而不应强迫两个周期内部的对应半浪具有近似相同的 phase allocation。

所以本轮唯一变化始终是：

`corresponding_leg_duration_mismatch: hard rejection -> diagnostic`

冻结数值没有事后改动：

- `duration_ratio = 2.0` 不变；
- min/max cycle、min/max pair、min leg 不变；
- amplitude 不变；
- raw leg path efficiency `>= 0.5` 不变；
- jump share `<= 0.5` 不变；
- TCSS / ridge / exact tuple identity / raw projection 不变；
- D1 / deterministic non-overlap ledger 不变。

结果前协议：`docs/research/two_wave_cycle_scale_qualification_protocol_v054.md`。

## 3. 主 5m 机制门

正式主 5m 证据已单独归档：`docs/research/two_wave_cycle_scale_qualification_results_v054_main5m.md`。

- run：`33984455043` — success
- commit：`17108111ec9d5e6066f9f8718bcfebf4059b1c36`
- artifact：`9974744445`
- artifact SHA256：`217348e93d47a3364a4c3496e2752743923bba7cf6626c3dcf15e92078c95469`

`5m_offset_0`：

- evaluated：38,049
- parent candidate identity exact match：true
- v0.5.2 qualified：425
- v0.5.4 qualified：734
- newly qualified：309
- lost qualified：0
- newly qualified 集合与事前 attribution 的 `corresponding_leg_duration_mismatch` exclusive-only 集合：完全一致

2018 已通过父结构未丢失；case_02 的 90/3 / 1-bar pathology 没有复活；case_00 没有被本轮声称解决。

因此主 5m 通过后才进入本文件所记录的 multiview adjudication。

## 4. 五个 native 5m：15/15 prefix zero rewrite

原 five-view 单 job run `33984731405` 在已经完成 offset_0..3 后收到 runner shutdown，属于执行编排失败，不作为研究结果。

只改变 CI 调度、不改变任何数学代码或判据后，正式并行 run：

- run：`33998425000` — **success**
- execution commit：`38abebf1970f019d95b9edf1fd1cfa8d3e1e330d`
- final artifact：`9978815239`
- artifact SHA256：`0ef8ac22b4b69befd39d1b5e516b3c95bd3f396976cdbc5a7f0b8352515998cf`
- final artifact bytes：200,519

五个 native 5m 分别独立执行 full + 25% / 50% / 75% prefix。所有 15 个 prefix 对以下字段均逐项一致：

- v0.5.2 ridge nodes
- ridge edges
- ridge deaths
- lineage anomalies
- exact tuple births
- raw projection
- v0.5.2 evaluated records
- v0.5.2 selected records
- v0.5.4 evaluated records
- v0.5.4 selected records

**15/15 `confirmed_rewrite_count = 0`。**

### 4.1 五视图单组件结果

| view | evaluated | v0.5.2 qualified | v0.5.4 qualified | newly qualified | v0.5.2 selected | v0.5.4 selected |
|---|---:|---:|---:|---:|---:|---:|
| 5m_offset_0 | 38,049 | 425 | 734 | 309 | 256 | 404 |
| 5m_offset_1 | 36,624 | 376 | 691 | 315 | 225 | 371 |
| 5m_offset_2 | 36,499 | 391 | 691 | 300 | 240 | 382 |
| 5m_offset_3 | 36,378 | 406 | 721 | 315 | 242 | 392 |
| 5m_offset_4 | 36,164 | 418 | 746 | 328 | 253 | 392 |

五个 view 均满足：

1. candidate identity exact match；
2. lost v0.5.2 qualified = 0；
3. 新增 qualified 严格来自冻结的 duration-only rejection 集合；
4. 其它 qualification reason 不变。

数量增加本身不作为晋级理由。

## 5. Native-5m offset stability：四项全部改善

IoU 只解释为 K 线切片边界稳定性，不解释为准确率。

| offset vs main | v0.4.3 | v0.5.2 | v0.5.4 | v0.5.4 - v0.5.2 |
|---|---:|---:|---:|---:|
| offset_1 | 26.42% | 31.53% | **36.79%** | **+5.26 pct** |
| offset_2 | 20.27% | 23.92% | **31.34%** | **+7.42 pct** |
| offset_3 | 22.86% | 27.51% | **31.21%** | **+3.71 pct** |
| offset_4 | 28.00% | 32.44% | **35.10%** | **+2.66 pct** |

- `worse_count = 0`
- `all_four_worse = false`
- mean IoU delta vs v0.5.2 = **+4.760 pct**

冻结协议只要求“不得系统性恶化”；实际结果是四项全部同向改善，因此稳定性门通过。

## 6. 1m official：3/3 prefix zero rewrite

最初顺序 1m workflow：

- run：`33998434083`
- package validation：通过
- full regression：通过
- 在 full + 三个 prefix 的核心计算阶段最终被取消，未形成正式结果 artifact

因此它不参与研究裁决。

为解决纯执行时长问题，只拆调度、不改变研究实现：三个 shard 分别独立执行同一个 frozen full run 与一个 prefix，再由 aggregate 只读汇总，不重新运行模型。

正式 1m 并行证据：

- run：`33999025314` — **success**
- execution commit：`c4ad36e5707c8233ef3076c5d9e2c95d1b31216d`
- final artifact：`9979148052`
- artifact SHA256：`5104f4dac1432efa582f6a95e8ea38c2a5e58ee1c27395ca5c6c88461fe97949`
- final artifact bytes：48,182

`1m_official`：

- rows：350,561
- v0.5.2 evaluated：110,268
- v0.5.2 qualified：4,882
- v0.5.2 selected：2,573
- v0.5.4 evaluated：110,268
- v0.5.4 qualified：9,459
- v0.5.4 selected：3,797
- duration-only newly qualified：4,577
- candidate identity exact match：true

三个 prefix：

| fraction | bars | confirmed rewrite |
|---|---:|---:|
| 25% | 87,640 | 0 |
| 50% | 175,280 | 0 |
| 75% | 262,920 | 0 |

三段均对 ridge / lineage / tuple / raw projection / v0.5.2 ledger / v0.5.4 ledger 全字段检查通过。

**1m = 3/3 prefix zero rewrite。**

## 7. 冻结协议最终逐项裁决

1. **parent candidate identity 与 v0.5.2 完全一致：PASS**
2. **所有非 corresponding-leg rejection 完全冻结：PASS**
3. **18/18 prefix zero rewrite：PASS**（native 5m 15/15 + 1m 3/3）
4. **full-cycle scale hard rules 不退化：PASS**
5. **jump / short / efficiency / amplitude 安全门不联动放松：PASS**
6. **case_02 明显 90/3 假结构不复活：PASS**
7. **native-5m offset stability 不系统性恶化：PASS；实际 4/4 改善**
8. **机制解释来自 scale 与 phase allocation 解耦，而不是 qualified / selected 数量：PASS**

因此 v0.5.4 的冻结晋级条件全部满足。

## 8. 研究解释

本轮支持的不是“对应半浪时长没有信息”，而是更窄的结论：

> **对应半浪在两个完整周期中的时间分配属于 morphology / phase allocation，而不是 same-scale identity 本身。**

同尺度资格应首先约束两个完整 reversal cycles 的总时间尺度；在完整周期相近的前提下，趋势漂移、相位不对称、局部速度差异可以使 leg1 vs leg3、leg2 vs leg4 明显不同。

因此对应腿 duration ratio 继续保留为诊断字段，未来可用于 D1 / morphology 分析，但不得重新偷偷作为同尺度 hard gate。

## 9. 基线升格的准确含义

旧完整 recognizer 操作基线 `v0.4.3` 到这里不再承担下一阶段研究的上游身份。

下一阶段冻结上游改为组合栈：

> **`v0.5.2 exact-ridge parent identity + v0.5.4 full-cycle-scale qualification`**

简称研究基线 **v0.5.4 qualification stack**。

这仍然：

- `trade_authority = false`
- `fresh_oos = false`
- 只使用 2015—2020 development 数据
- 不按收益选参
- 不生产部署

并且 **D1 尚未晋级**，所以不能把当前栈称为“最终两浪形态识别器”。

## 10. 下一安全停点：D1 range / trend 独立研究

上游 parent identity 与 qualification 到此冻结。下一轮只能独立处理 D1：

- 不改 TCSS / ridge linking / tuple birth；
- 不回滚 v0.5.4 full-cycle qualification；
- 不用收益优化 D1；
- 不把 `uncertain` 或未覆盖伪装成 range；
- 必须先做 D1 failure attribution / semantic preanalysis，再冻结单组件协议；
- 特别审计当前 `range` 极少、`uncertain` 较多的根因，区分：中心漂移、同相位端点迁移、上下包络迁移、幅度变化、相位不对称，而不是直接调一个 `phase_tolerance`。

正确顺序更新为：

**v0.5.2 parent identity ✅ → v0.5.4 qualification ✅ → D1 range/trend → 独立 morphology acceptance → H1/H2 → outcomes/trading。**

PR #1 继续保持 Draft；不合并 main。
