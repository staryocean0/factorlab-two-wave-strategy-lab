# 两浪研究继续入口：v0.5.6 D2 multiview 否定，下一步只读跨 offset 分歧归因（2026-09-06）

## 当前状态

冻结上游研究基线仍是：

> **v0.5.2 TCSS exact-ridge parent identity + v0.5.4 full-cycle-scale qualification**

方向/父状态层仍未验收。

准确状态链：

**v0.5.0 TCSS representation ✅ → v0.5.1 sliding five-extrema scale selector ❌ → v0.5.2 exact-ridge parent identity ✅ → qualification attribution ✅ → v0.5.3 birth-scale TCSS ER ❌ → v0.5.4 full-cycle-scale qualification ✅ → v0.5.5 D1 semantic attribution ✅ → v0.5.6 D2 whole-envelope main5m ✅ / multiview ❌ → cross-offset disagreement attribution pending。**

PR #1 继续 Draft，不合并 main。整个 morphology 尚未验收；不进入第三浪/H1/H2、收益、交易或生产。

## 优先阅读

1. `docs/research/two_wave_d1_envelope_translation_results_v056.md` — v0.5.6 最终负向裁决
2. `docs/research/two_wave_d1_envelope_translation_results_v056_main5m.md` — v0.5.6 主5m机制 PASS
3. `docs/research/two_wave_d1_envelope_translation_protocol_v056.md` — v0.5.6 结果前协议
4. `docs/research/two_wave_d1_envelope_translation_preanalysis_v056.md` — whole-envelope 金融/数学预分析
5. `docs/research/two_wave_d1_semantic_attribution_results_v055.md` — v0.5.5 只读归因
6. `docs/research/two_wave_cycle_scale_qualification_results_v054.md` — 当前 qualification 基线
7. `docs/research/two_wave_extremum_ridge_results_v052.md` — 当前 parent identity 基线

## 金融合同不变

目标是在某个 K 线级别识别**连续、同尺度、完整的两个 raw-price reversal waves**，再用这两个波的父级几何区分：

- range
- uptrend
- downtrend
- uncertain

低点起算 `L0 -> H1 -> L1 -> H2 -> L2`，高点起算对称。

必须继续满足：

- raw-price reversal 语义；严格单调 raw price 不得被 detrended component 伪造出完整波；
- append future 后 confirmed 结构/分类不得改写；
- available_at 与计算确认时钟分离；
- coverage ≠ accuracy；direction ≠ channel；IoU 只作切片稳定性；
- 不按收益、第三浪或案例美观度选择公式/阈值。

## 冻结上游 A：v0.5.2 parent identity

v0.5.2 已通过并冻结：

- confirmed extrema 跨 causal TCSS scales 形成 immutable ridge IDs；
- parent family = exact five ridge IDs；
- intervening child ridges 全部 causally certified dead 后才允许 tuple birth；
- raw projection 回 exact raw-price extrema；
- 18/18 prefix zero rewrite；
- lineage anomaly = 0；
- case_02 90/3 假结构未复活。

不得回头修改 ridge linking、ridge death、tuple identity、tuple birth 或 raw projection 来补方向分类。

## 冻结上游 B：v0.5.4 qualification

当前 same-scale qualification 的关键语义：

> **完整 reversal cycle 的总时间尺度定义 same-scale；对应半浪 duration allocation 只保留为 morphology diagnostic。**

`corresponding_leg_duration_mismatch` 已从 hard rejection 降为 diagnostic；以下继续冻结：

- full-cycle duration ratio = 2.0
- min/max cycle、pair、min leg
- amplitude
- raw path efficiency >= 0.5
- jump share <= 0.5
- flat / clock / confirmation
- deterministic non-overlap ledger

v0.5.4 正式 18/18 prefix zero rewrite，native 5m offset IoU 四项均较 v0.5.2 改善。

## v0.5.5：D1 semantic attribution

在不改现有 D1 的情况下，对主 `5m_offset_0` 的 v0.5.4 qualified records 做只读归因。

主 5m：734 qualified：

- D1 range 4
- uncertain 371
- uptrend 187
- downtrend 172

371 个 uncertain 的主要 subtype：

- same_phase_reversal_conflict 243
- strong_net_with_opposed_phase 40
- coherent_but_subthreshold 36
- opposite_envelope_conflict 18
- single_phase_dominant 17
- large_migration_without_coherent_direction 17

318/371 属于明确几何冲突；185/371 的完整 upper/lower envelope 已经同向且两条均越过冻结 0.15。

另外可代数证明：旧 D1 range 若三个 `|si|<=0.15`，则同相位三点最大 span<=0.30，另一 envelope span<=0.15，所以旧 `span<=0.5` 是冗余条件。range 稀少不能通过放松 `0.5` span gate 解决。

## v0.5.6：whole-envelope D2

结果前冻结：仍用相同 amplitude normalization 和 `phase_tolerance=0.15`，只把父级 hard vote 改为完整 upper/lower envelope 的总迁移。

- `net=s0+s1`
- low-start：`E_lower=net, E_upper=s2`
- high-start：`E_upper=net, E_lower=s2`
- 两条都 >0.15 -> uptrend
- 两条都 <-0.15 -> downtrend
- 两条都 |E|<=0.15 -> range
- 其余 -> uncertain

`s0/s1` 局部反号只作 morphology diagnostic。

### Main 5m：机制 PASS

run `34009093294` success，artifact `9981922969`。

- evaluated 38,049
- qualified 734
- selected 404
- upstream candidate / qualification / selected IDs / intervals exact match
- D1 qualified `4 / 371 / 187 / 172`（range/uncertain/up/down）
- D2 qualified `22 / 185 / 280 / 247`

22 个 D2 range 中 21 个存在 `s0*s1<0`：主视图上 D2 能表达“父级边界总体不迁移但内部有大摆动”的 range 语义。

但数量更均衡不是接受理由。

### Causality：18/18 PASS

Native five-view run `34009427027`：五个 view full + 25/50/75% 全部通过，**15/15 zero rewrite**。

1m parallel run `34009436754`：25/50/75% 全部通过，**3/3 zero rewrite**；final artifact `9982103606`。

所以 D2 没有未来改写问题。

### Multiview label stability：正式 FAIL

D1 与 D2 使用**完全相同 selected intervals**；boundary IoU 因此精确相同。只比较共同拥有区间的 label agreement。

冻结 hard gate 规定：若 D2 在四个 native offset 上全部比 D1 差，则直接否定。

实际结果：

| offset | D1 same-label | D2 same-label | D2-D1 |
|---|---:|---:|---:|
| 1 | 78.0399% | 76.3050% | -1.7349pp |
| 2 | 78.4855% | 73.6850% | -4.8005pp |
| 3 | 76.4696% | 72.1744% | -4.2952pp |
| 4 | 83.9950% | 82.1246% | -1.8704pp |

`worse_count=4/4`，mean delta = **-3.1752pp**。

Failure diagnostic：run `34009928175` success，artifact `9982147148`，SHA256 `1968b70bef5053dcaf1979bbf399013d326f9c415a02645dd47c82581e294d0a`。

因此：

> **v0.5.6_rejected_multiview_label_stability**

不得调 `0.15`、修改 hard gate、挑案例或看收益把 D2 救回。

## 下一安全停点：cross-offset disagreement attribution

不要立即实现 v0.5.7。

下一轮先冻结一个**只读跨 offset 分歧归因协议**，只研究为什么 D2 比 D1 更容易受 native 5m slicing 影响。

必须至少拆解：

1. disagreement 是否集中在 `0.15` 边界附近；
2. `E_upper / E_lower` 哪条更容易在 offsets 间换符号或跨阈值；
3. `s0/s1/s2` 各自的跨 offset 稳定性；
4. `net=s0+s1` 是否放大 endpoint allocation / raw projection 误差；
5. low-start / high-start 对称性；
6. D2 range / trend / uncertain 哪类迁移最不稳定；
7. birth scale、amplitude ratio、corresponding-leg duration diagnostic、cycle duration 与 disagreement 的关系；
8. 大 margin disagreement 与 threshold-near disagreement 必须分开，避免错误归因成“阈值问题”。

只读 attribution 完成后，先做金融/数学 fit preanalysis，再决定是否存在 v0.5.7 单组件候选。没有机制证据就不实现新分类器。

## 不变边界

- 只用仓库现有 2015—2020 development 行情；
- 主目标 `000852.SH` 原生 `5m_offset_0`；其余 native 5m 只作边界稳健性，1m 只作因果诊断；
- 不价格重采样，不新增 fresh OOS；
- `trade_authority=false`；
- 负向实验原样保留；
- PR #1 继续 Draft，不合并 main；
- D1 通过后才进入 independent morphology acceptance；在那之前不进入 H1/H2 / outcomes / trading。
