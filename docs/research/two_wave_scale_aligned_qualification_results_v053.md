# v0.5.3 birth-scale 因果 TCSS 腿效率：主 5m 结果与否定结论

日期：2026-09-06  
状态：`rejected_as_qualification_hypothesis`  
操作研究基线：**v0.4.3**  
冻结 parent identity 上游：**v0.5.2 exact-ridge tuple birth**

## 1. 结果前协议

协议：`docs/research/two_wave_scale_aligned_qualification_protocol_v053.md`

本轮只允许修改一个组件：

- 旧：raw close 上的四腿 path efficiency；
- 新：tuple 已事前确定的 `birth_scale_id` 对应、未左移的 causal TCSS log-price 上的四腿 path efficiency；
- 数值阈值 `min_leg_efficiency = 0.5` 完全不变；
- duration / amplitude / jump / flat / clock / confirmation / D1 / ledger 全部冻结。

禁止使用收益、覆盖、case 结果或 offset IoU 反选公式。

## 2. 正式执行证据

第一次 workflow run `33983660192` 在真实数据加载前因 runner plumbing 错误终止：`load_development_bars()` 少传 frozen manifest path。该 run 未产生真实研究结果，因此不参与假说判定。

仅修复数据加载调用后，正式重跑：

- commit：`f02ec2375577faad79f2ae255da0ce70d69646e5`
- run：`33983827917`
- artifact：`9974563999`
- artifact SHA256：`ae3d3c5472af7b83f6c57bc26e42f0b257782e3b85da56dcde2194f9e8cdd941`
- package validation：通过
- full regression：通过
- main-5m mechanism audit：通过全部 invariant assertions

因此下面是第一份、也是唯一一份按冻结协议产生的 v0.5.3 主 5m 真实结果。

## 3. Parent candidate identity 完全冻结成功

`5m_offset_0`：

- v0.5.2 evaluated candidates：38,049
- v0.5.3 evaluated candidates：38,049
- candidate identity exact match：**True**
- 所有非-efficiency rejection reasons 的 presence/absence 对每个 candidate 均保持不变
- `trade_authority=False`
- `future_outcome_used=False`

所以本轮可以干净归因于 efficiency measurement scale 单组件。

## 4. 核心结果：birth-scale ER 整体更严格，而不是更合理地吸收子摆

### 4.1 min-leg ER 分布

raw-close min-leg ER：

- p10 = 0.321
- median = 0.621
- p90 = 0.862
- p99 = 0.974

birth-scale causal-TCSS min-leg ER：

- p10 = 0.076
- median = 0.449
- p90 = 0.956
- p99 = 1.000

TCSS ER 并不是对 raw ER 的单调“去噪提升”。它使分布更两极化：高端更接近 1，但低端和中位数显著下降。

### 4.2 `inefficient_leg` 拒绝

- v0.5.2 raw ER：11,437
- v0.5.3 birth-scale ER：20,850

增加 **9,413** 个 efficiency rejection。

### 4.3 qualified / selected 仅作描述，不作为目标

- v0.5.2 qualified：425
- v0.5.3 qualified：206
- v0.5.2 selected：256
- v0.5.3 selected：166
- newly qualified：73
- lost qualified：292

在 v0.5.2 中，仅因 `inefficient_leg` 一项被拒绝的 candidate 有 355 个；v0.5.3 只释放其中 73 个。

这不是简单的“更严格也许更好”问题，因为结果前协议要求新定义首先修复已知的机制错位，而不是任意压缩候选。

## 5. 关键固定窗口否定了预期机制

### 5.1 2018-06-20

冻结窗口 bar range `[40402, 40449]`：

- v0.5.2 overlapping candidates：54
- v0.5.3 overlapping candidates：54
- v0.5.2 qualified：1
- v0.5.3 qualified：0

最相关的 coarse parent：

- raw extrema：`[40397, 40408, 40421, 40442, 40450]`
- filtered extrema：`[40402, 40413, 40426, 40447, 40453]`
- cycles：`24 / 29`
- legs：`11 / 13 / 21 / 8`
- birth scale level：6
- birth sigma：4 bars
- raw min-leg ER：**0.53281**
- birth-scale min-leg ER：**0.29883**

它在 v0.5.3 中被 **`inefficient_leg` 单独拒绝**。

也就是说，在一个本来已经通过 raw efficiency、且形态周期并不极端的固定父结构上，birth-scale TCSS ER 反而制造了新的拒绝。这与本轮的核心机制假说相反。

### 5.2 case_00

冻结 range `[48720, 48801]`：

- v0.5.2 overlap：83
- v0.5.3 overlap：83
- 两者 qualified 均为 0

代表性父候选：

- raw extrema `[48720,48749,48754,48768,48801]`
- cycles `34 / 47`
- legs `29 / 5 / 14 / 33`
- birth level 6 / sigma 4
- raw min-leg ER `0.46863`
- birth-scale ER `0.40555`
- rejection：`corresponding_leg_duration_mismatch + inefficient_leg + jump_dominated_leg`

另一个 level-5 candidate 的 birth-scale ER 甚至从 raw `0.46863` 降至 `0.18967`。

因此 v0.5.3 没有解决 case_00 的 qualification 问题，也没有证据支持“父级 TCSS 内部路径更适合作为同尺度 ER”。

## 6. 判定

**v0.5.3 否定。**

具体否定的是：

> “保持阈值 0.5 不变，把四腿 path efficiency 从 raw close 改到 exact-ridge tuple 的 birth-scale causal TCSS，就能更正确地衡量父级腿的同尺度路径效率。”

这条假说在主 5m 机制审计已失败，按结果前协议：

- 不扩六视图；
- 不做 18 次 prefix；
- 不计算 v0.5.3 offset IoU；
- 不调低 0.5；
- 不把 v0.5.3 升格为 baseline；
- 不修改 v0.5.2 representation / ridge identity。

## 7. 保留结论

v0.5.2 的 parent identity 结论不受影响，仍为：

`parent_identity_pass_qualification_pending`

操作研究 baseline 仍为 v0.4.3。

下一步不是继续改 efficiency，而是对 **v0.5.2 frozen qualification** 做无参数、无收益的 rejection attribution：

1. 每条规则的总拒绝数；
2. 每条规则的 exclusive-only 拒绝数；
3. “只移除这一条规则”会新增多少 qualified；
4. rejection pair / higher-order co-occurrence；
5. 按 birth-scale / cycle-duration / leg-duration 分层；
6. 2018 / 2019 / 2020 固定窗口与 case_00/02/11/14 的 rejection chain；
7. 在这些证据上事前冻结下一项单组件 qualification 假说。

在 attribution 完成前，不直接把 duration_ratio、jump_share 或 amplitude threshold 改成新的数值。
