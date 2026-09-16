# R5-B1 specialist Stage 1 — cloud review

日期：2026-09-16

Specialist identity：`R5_B1_anti_persistence_interaction_specialist_v1`

Stage identity：`R5_B1_specialist_stage1_stability_continuous_shape_v1`

## 1. Execution integrity

科学 preanalysis / protocol / runner / tests / execution freeze 均在 real-data Stage-1 outcome 可见前冻结。

受控执行：GitHub Actions run `35040612069`，head `d2a63178bace7ddee6e756358551bb135ef688d7`，conclusion=`success`。

- 5/5 frozen tests passed；
- frozen artifact blob identities passed；
- source SHA256=`bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48`；
- rows=70,114；symbol=`000852.SH`；max day=`2020-12-31`；
- CL-008 entry reproduction 全部精确通过；
- BLACKBOX=false；post-2020=false；PnL=false；fresh-OOS claim=false；production authority=false。

因此 runner 输出中的 `execution_drift_or_insufficient` **不是 implementation drift**；本次是预注册 S2 supply integrity insufficient。

## 2. S1 — 时间稳定性不支持

预注册要求 TRAIN 至少 6/8 半年块 local interaction<0，且 TRAIN median<0；VALIDATION 至少 3/4 interaction<0、median<0，并且 fixed B1 至少 3/4 MSE improvement>0。

实际：

- TRAIN negative local interaction blocks = `3/8`；
- TRAIN median local interaction = `+0.2381504944`；
- VALIDATION negative local interaction blocks = `3/4`；
- VALIDATION median local interaction = `-0.3379852280`；
- VALIDATION fixed B1 positive MSE-improvement blocks = `4/4`；
- VALIDATION median fixed B1 improvement = `+0.0011195147`。

所以 `S1_time_stability_supported=false`。

重要区别：frozen TRAIN-fit B1 在四个 VALIDATION 半年块都略优于 B0，但 interaction coefficient 本身在 TRAIN 时间块里不稳定；2016H1、2017H1、2017H2、2018H1、2018H2 的 local interaction 为正。不能把固定模型的小幅预测改善等同于一个跨时间稳定的结构机制。

## 3. S2 — frozen decile continuous-shape 因供给漂移不可执行

TRAIN decile 本身显示较强下降形状：

- linear trend = `-1.1725667998`；
- Spearman = `-0.8666666667`；
- bottom20 slope = `+0.1019985436`；
- top20 slope = `-0.0480747218`。

但 TRAIN-fixed top decile 在 VALIDATION 几乎消失：

- VALIDATION pooled decile 10：`17` rows（最低要求 100）；
- 2019 decile 10：`0` rows；
- 2020 decile 10：`17` rows。

因此 `S2 usable=false`，不能按冻结规则给 continuous-shape support。这个现象本身说明 anti-persistence feature distribution 存在明显 chronological displacement。

不得在看到结果后通过合并 top bins、降低 100-row 门槛、改用 validation quantiles 或重新定义 anti-persistence 来“救”本 identity。

## 4. Frozen adjudication 与 program-level consequence

Frozen runner adjudication：

`R5_B1_specialist_stage1_execution_drift_or_insufficient`

更精确的解释是：entry/source/implementation 均完整，S2 因 frozen feature-bin supply insufficient；同时 S1 已经独立失败。

由于 transport 的预注册必要条件是 `S1=true AND S2=true`，本结果无论如何都不授权 transport。

Program-level consequence：

`R5_B1_specialist_stage1_closed_no_transport`

这不是推翻 CL-008。CL-008 仍然证明 B1 的小幅增量具有 validation day breadth 和 5-bin mechanism shape；Stage 1 是更严格的 specialist qualification，结论是该 identity 不足以进一步跨频率/跨指数扩张。

## 5. Authority

- transport research：false；
- HMM/rSLDS/Koopman：false；
- BLACKBOX allocation/read：false；
- economic mapping / PnL / Sharpe：false；
- paper trading / production / Layer 4：false。

下一步回到 broad parent discovery，研究与 B1 独立的新低容量均值回归 identity；不得把新方向设计成 B1 rescue。
