# R7 rejected-excursion stability/shape diagnostic — cloud review

日期：2026-09-16

Parent identity：`R7_native_1m_rejected_excursion_v1`

Diagnostic identity：`R7_rejected_excursion_stability_shape_diagnostic_v1`

正式裁决：

`R7_diagnostic_supported_for_specialist_research`

## 1. 执行身份

- branch: `codex/two-wave-phase1-20260905`
- execution commit: `1d9b507544111eb27d05048b2e3ec8d966a1d835`
- GitHub Actions run: `35042530618`
- job: `104625259981`
- workflow conclusion: `success`
- frozen synthetic tests: 4/4 passed
- receipt artifact: `R7-rejected-excursion-diagnostic-receipt`
- artifact id: `10425359412`
- artifact digest: `sha256:26a147a5e22ef505e22249aefac05b7543190d5eef465905180d3f12dc5e2b96`

execution freeze 在真实 diagnostic outcome 之前完成，且 workflow 在 tests/real runner 前重新校验 preanalysis、protocol、diagnostic runner、tests、parent runner 及两份 source SHA。

## 2. Entry reproduction

全部在 absolute tolerance `1e-12` 内通过：

- candidate rows = `64215`
- TRAIN B0 beta = `[0.013752645338616696, 0.04853230586734813]`
- TRAIN B1 beta = `[0.0014301524091757528, 0.06384569479627822, -0.5327696198414725]`
- VALIDATION B0/B1 MSE = `1.6598472863016691 / 1.634971285903517`
- 2019 B0/B1 MSE = `1.7444187739434946 / 1.7207889673268437`
- 2020 B0/B1 MSE = `1.5749277678465021 / 1.5488004452973783`

所以不存在 entry drift。

## 3. D1 — fixed half-year stability

`D1_time_stability_supported = true`

TRAIN 8 个固定半年块中：

- 7/8 local rejection coefficient < 0；
- median coefficient = `-0.7532276662005157`。

唯一相反块是 2015H2：coefficient=`+0.099047357214775`；它被保留，不做 favorable-period 删除。

VALIDATION 4 个固定半年块：

- 4/4 local rejection coefficient < 0；
- median coefficient = `-0.3952872100934446`；
- 4/4 frozen TRAIN-fit B1 MSE improvement > 0；
- median block improvement = `0.02596125433208496`。

具体 VALIDATION coefficients：

- 2019H1 `-0.4357234061`
- 2019H2 `-0.3549901556`
- 2020H1 `-0.3720402395`
- 2020H2 `-0.4185341807`

## 4. D2 — TRAIN-fixed rejection-magnitude shape

`D2_magnitude_shape_supported = true`

TRAIN-only feature quantile edges：

`[0.0854062876494029, 0.20190499178213603, 0.37145347987685473, 0.6597428926880327]`

四组 shape 全部通过：

| group | score-vs-magnitude trend | bottom score | top score | top sign symmetry |
|---|---:|---:|---:|---|
| TRAIN | `+0.2699129481` | `0.1993066044` | `0.5160407177` | pass |
| VALIDATION | `+0.2871813815` | `0.0718275335` | `0.3826933124` | pass |
| 2019 | `+0.2668367352` | `0.0987847943` | `0.3966548420` | pass |
| 2020 | `+0.3106994521` | `0.0420703640` | `0.3712823402` | pass |

VALIDATION top-bin：

- positive rejection mean B0 residual = `-0.4384997955`
- negative rejection mean B0 residual = `+0.3378810143`

2019/2020 top-bin 也都保持同方向 symmetry。

注意：2020 lowest-magnitude bin 的 negative-side mean residual 为 `-0.009244...`，并非所有弱 magnitude 局部都完美对称；冻结 protocol 只要求 top-bin symmetry + overall increasing shape，因此该事实不改变 D2 adjudication，也不能被隐藏或用于事后改 gate。

## 5. 科学解释

R7 当前证据支持一个比 R5-B1 更清楚的低容量机制：在相同 5m endpoint displacement 条件下，native 1m path 中被拒绝的 excursion 含有额外反向信息，而且：

- 方向在 TRAIN/VALIDATION 固定半年块具有较高稳定性；
- 固定 TRAIN 模型在 2019H1..2020H2 四块都改善；
- rejected-excursion magnitude 越大，aligned reversal residual 整体越强；
- 高 magnitude 的上行/下行 rejected excursions 都保持预注册对称方向。

这仍然是 reusable TRAIN/VALIDATION evidence，不是 fresh OOS，也不是交易收益证明。

## 6. 权限结论

允许：建立 `R7_native_1m_rejected_excursion_specialist_v1` specialist lane。

仍不允许：

- BLACKBOX allocation/read；
- post-2020 read；
- PnL/Sharpe model selection；
- 事后挑年份、半年、方向、magnitude threshold；
- 改 path=5m、forward=5m、sigma=240 的 parent identity 后宣称仍是同一验证；
- HMM/rSLDS/Koopman 等 complex regime rescue；
- paper trading / production / Layer4。

Production authority=false。
