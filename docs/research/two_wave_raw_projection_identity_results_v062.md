# v0.6.2 raw-projection financial identity audit — 正式结果与云端裁决

日期：2026-09-06

状态：`projection_single_valued_but_cross_slicer_unstable_sampling_aliasing_primary_with_window_semantics_residual`

操作基线仍为 **v0.4.3**；全局状态仍为 `morphology_replication_not_yet_accepted`。本轮是只读 projection identity audit，**没有修改** v0.5.2 ridge、v0.5.4 qualification、v0.6.0 matcher、packing、D1/D2/PAWCT、收益或交易逻辑。

## 1. 结果前冻结

- preanalysis：`docs/research/two_wave_raw_projection_identity_preanalysis_v062.md`
- frozen protocol：`docs/research/two_wave_raw_projection_identity_protocol_v062.md`
- frozen implementation head：`ed395bd14c32931caa272ea51d7633ea151fb083`
- helper blob：`b076e31036601278499ee3a4b699658db2ae9bc9`
- tests blob：`d15316ec0447b10c7b0690e0c285db3f2d6d1e99`

当前被审计的旧 projection 仍是 `sequential_raw_close_extreme_inside_filtered_phase_bounds`。

## 2. 执行证据边界

本轮在 ChatGPT 网页 Chat 的当前 runtime 中实际执行。五个 native 5m parquet 与 `1m_official.parquet` 来自用户上传的仓库 ZIP，SHA256 / bytes 全部与 frozen manifest 一致；无 resample、无 2021+。

当前 Chat Python 3.13 没有 `pyarrow`；尝试通过平台下载 PyPI 官方 `pyarrow-19.0.1` wheel 仍无法落入 shell。因此数据 I/O 继续使用只读 mini-Parquet runtime bridge。核心研究数学来自 GitHub frozen source；v0.6.2 helper 在正式验收前按 Git blob SHA 同步为**精确 frozen 文件**，9/9 frozen tests PASS。五视图采用两视图/cache orchestration 以控制内存。

这不是整仓原环境字节级 replay，但 decisive data identities、v0.6.0/v0.6.1 hard controls 与 frozen v0.6.2 helper 全部闭合。

## 3. Hard controls

- qualified：`734 / 691 / 691 / 721 / 746`
- canonical qualified：`712 / 673 / 678 / 700 / 728`
- v0.6.0 pair controls：四组全部精确复现
- v0.6.1 post-tuple targets：`191 / 195 / 194 / 209`
- v0.6.1 projection-displacement：`191 / 194 / 193 / 209`
- v0.6.2 frozen helper tests：**9/9 PASS**

任何一个数字如果漂移，本轮不得解释；本次无漂移。

## 4. 单视图：projection 是单值函数，不是 duplicate-scale member 冲突

| view | canonical filtered tuples | single-valued | no-valid | multi-valued |
|---|---:|---:|---:|---:|
| offset0 | 38,634 | 38,047 | 587 | **0** |
| offset1 | 37,175 | 36,623 | 552 | **0** |
| offset2 | 37,061 | 36,498 | 563 | **0** |
| offset3 | 36,935 | 36,376 | 559 | **0** |
| offset4 | 36,688 | 36,163 | 525 | **0** |

所有 no-valid 的现行原因都是 `raw_projection_not_actual_turn`。因此 v0.6.2 排除“同一 canonical filtered tuple 因不同 birth evidence 投成多个 raw identity”为主要机制。当前 projection 在单视图内是 well-defined 的；问题发生在 harmless slicing 改变后。

## 5. 全 filtered-tuple match universe：raw projection 大面积失稳

| pair | mutual-unique filtered tuples | raw strict | raw displaced | invalid group | raw displaced / valid |
|---|---:|---:|---:|---:|---:|
| 0 vs 1 | 14,784 | 7,638 | 6,975 | 171 | 47.73% |
| 0 vs 2 | 12,725 | 5,188 | 7,311 | 226 | 58.49% |
| 0 vs 3 | 13,412 | 5,593 | 7,534 | 285 | 57.39% |
| 0 vs 4 | 16,108 | 8,332 | 7,453 | 323 | 47.22% |

Aggregate：57,029 个 mutual-unique filtered-tuple pairs；1,005 个 projection-invalid groups。其余 56,024 valid pairs 中，**29,273（52.25%）raw identity displaced**。

因此 v0.6.1 的 projection 问题不是只存在于少数 downstream qualified target；它是 filtered-parent → 5m-raw projection 的广泛表示问题。

## 6. 主要机制：5m sampling-lattice aliasing

把每侧**现有 frozen 5m projection window**保持不变，只把窗口内的 argmax/argmin 数据源换成 supplied `1m_official` canonical path，作为 audit-only diagnostic：

| pair | 5m raw displaced | 1m strict | 1m still displaced | 1m recovery |
|---|---:|---:|---:|---:|
| 0 vs 1 | 6,975 | 5,397 | 1,578 | 77.38% |
| 0 vs 2 | 7,311 | 5,573 | 1,738 | 76.23% |
| 0 vs 3 | 7,534 | 5,728 | 1,806 | 76.03% |
| 0 vs 4 | 7,453 | 5,735 | 1,718 | 76.95% |

Aggregate：**22,433 / 29,273 = 76.63%** 的 5m raw displacement 在相同 absolute windows 上改看同一 1m path 后恢复 strict identity。

在 v0.6.1 的 787 个 displacement target 中，**665 / 787 = 84.50%** 恢复 strict identity。

所以当前最强证据是：**5m close sampling lattice aliasing 是 raw-projection instability 的主机制之一，而且在真正导致 v0.6.1 post-tuple loss 的 target 中更强。**

这仍不是授权把 1m diagnostic 直接升级为 recognizer projection；因为还有实质 residual。

## 7. 仍有 residual：当前 phase-window semantics 本身也不稳定

全 universe 中仍有 **6,840 / 29,273 = 23.37%** 的 raw-displaced pairs 在 canonical 1m path 上仍 displaced；v0.6.1 target 中为 **122 / 787 = 15.50%**。

因此“只把 5m close 换成 1m close”不是完整修复。下一步必须先审计现行 window semantics。

### 7.1 第一锚窗口最可疑

Aggregate first-displaced ordinal：

- ordinal0：11,361 / 29,273 = **38.81%**
- ordinal1：18.19%
- ordinal2：16.50%
- ordinal3：14.40%
- ordinal4：12.10%

v0.6.1 target 中 ordinal0 也最高：285 / 787 = **36.21%**。

raw-displaced pairs 中，两个视图选中的 raw anchor 同时落在对方 window 内的比例：

- ordinal0：**70.24%**
- ordinal1：91.25%
- ordinal2：92.16%
- ordinal3：92.52%
- ordinal4：94.11%

在 target 中 ordinal1..4 更达到约 98.9%–99.6%，而 ordinal0 只有 **79.16%**。

现行 ordinal0 lower bound 是 bar-index 外推 `max(0, 2*f0-f1)`；ordinal0..3 upper 又用“下一 filtered bar 的前一条 5m row”。这些 bar-index/predecessor 语义在午休、隔夜等非均匀 wall-clock gap 附近可能把很小的 filtered-anchor displacement 放大为很大的 absolute window-bound displacement。当前结果中的 window-bound max delta 已实际出现小时/跨日量级；这必须在下一轮独立审计，不能在本轮直接改公式。

### 7.2 sequential propagation 不是主解释

只有 **4,600 / 29,273 = 15.71%** 的 displaced pairs 从 first displaced ordinal 开始形成完整 suffix；target 更低，为 **94 / 787 = 11.94%**。

所以“第一个 raw 选择不同 → 所有后续 lower bound 连锁传播”确实存在，但不是主体。

### 7.3 exact ties / plateaus 不是主解释

全 universe 只有 **289 / 29,273 = 0.99%** 的 raw-displaced pairs 涉及现行 5m window 内 exact-extreme tie；target 只有 **5 / 787 = 0.64%**。

所以 last-argextreme tie-breaking 不是当前 instability 的主因。

### 7.4 ordinal4 confirmation tail 不是主解释

现行第五窗口延伸到 filtered member confirmation。绝大多数 displaced pairs 的 tail median / p90 都仍是一根 nominal 5m bar；ordinal4 也只占 first-displaced 的 12.10%（target 9.53%）。存在很长 tail outlier，但不是总体主导机制。

## 8. 正式裁决

v0.6.2 支持以下四条结论：

1. **Single-view projection single-valuedness：PASS。** 没有发现 canonical filtered identity 在不同 birth evidence 下产生多个 valid raw identity。
2. **Cross-slicer raw projection invariance：FAIL。** 在已经 mutual-unique 对齐的 filtered parent pairs 中，约一半 valid pairs 仍 raw displaced。
3. **Primary mechanism：5m sampling-lattice aliasing。** 同一 absolute phase windows 上改看 canonical 1m path，可恢复约 76.6% 全体 displacement / 84.5% v0.6.1 target displacement。
4. **Residual mechanism：phase-window semantics。** 仍有 23.4% / 15.5% 在 canonical 1m path 上不稳定；ordinal0 window support 特别突出。必须先继续 window-semantics residual audit，不能直接把 1m diagnostic promotion 成新 projection。

因此当前不能回到 D1/D2/PAWCT，也不能进入第三浪。

## 9. 下一 formal step

下一步应是**单独冻结 v0.6.3 phase-window semantics residual audit**，只研究 canonical 1m 仍 displaced 的 residual：

- first differing 1m anchor；
- lower vs upper boundary exclusion；
- ordinal0 extrapolated-left-bound contribution；
- filtered-predecessor upper-bound contribution；
- sequential lower-bound contribution；
- member-confirmation tail contribution；
- lunch / overnight gap overlay；
- cross-view window intersection 仅作诊断，不作为 runtime matcher/projection。

v0.6.3 在结果前不得提出赢家 projection，也不得用收益/方向/qualification 选择边界。
