# v0.6.9 path-metric sampling-resolution response：正式结果与云端裁决

日期：2026-09-06

状态：`metrics_have_opposed_resolution_semantics_requiring_property_redefinition`

操作基线仍为 **v0.4.3**；全局状态仍为 `morphology_replication_not_yet_accepted`。本轮是 measurement-semantics audit，不修改 qualification rule、threshold、identity、matcher、projection、publication、direction、outcome 或 trading logic。

## 1. 结果前冻结与执行身份

结果前文件：

- `docs/research/two_wave_path_metric_resolution_response_preanalysis_v069.md`
- `docs/research/two_wave_path_metric_resolution_response_protocol_v069.md`

正式 helper：`src/factor_lab/visual_structure/two_wave/path_metric_resolution_response_v069.py`，Git blob `f7ee5dec71b2055c762f9be08fc22171b2a8b2c6`。

Synthetic tests：**7/7 PASS**。

正式全量前，500 个真实 v0.6.5 published identities 的 native 5m 四腿 efficiency / jump-share / flat-share 与 v0.6.6 frozen qualification cache 做逐项 exact-equivalence：**500/500 PASS**。

执行层曾在 strict-pair overlay gate 错把 upstream 已冻结 aggregate 24 个 v0.6.1 target-repaired disagreements 人工分摊成 `9/6/4/5`。runner 在正式 interpretation 前被 hard assertion 拦截。重新读取 v0.6.7 pair evidence 后，真实逐-offset counts 是 `10/7/3/4 = 24`。v0.6.9 frozen protocol 本身只冻结 aggregate `80 target repaired / 24 disagreement`，因此协议无需改动；只修正 runtime bookkeeping 后完整重跑。本修正不改变任何研究数学或 v0.6.9 metric output。

## 2. Hard controls 全部闭合

Published identities：

```text
38,176 / 36,737 / 36,619 / 36,480 / 36,264
aggregate = 184,276
```

四腿 observations：**737,104**。

Strict same-event pair controls：

```text
8,381 / 5,770 / 6,204 / 9,098
aggregate = 29,453
both-qualified control = 482
qualification disagreements = 699
v0.6.1 target repaired = 80
其中 qualification disagreement = 24
```

无 behavioral control drift。

## 3. Nested-partition 数据/数学检查通过

737,104 条 leg observations 中：

- exact aligned nested legs：**736,826**
- non-aligned：**278 = 0.0377%**
- common timestamp close mismatch：**0**
- `TV1 + 1e-12 < TV5` violation：**0**
- `E1 > E5 + 1e-12` violation：**0**

所以 observed resolution response 不是由 close mismatch 或 theorem violation 造成。Non-aligned legs 只保留为数据 overlay，不参加 exact theorem assertion。

## 4. Aggregate resolution response

5m → supplied 1m：

| metric | median | p90 | p99 | mean |
|---|---:|---:|---:|---:|
| `TV1/TV5` | 1.4123 | 2.1157 | 4.2317 | 1.5817 |
| `E1-E5` | -0.2063 | -0.0521 | 0.0000 | -0.2398 |
| `J1-J5` | -0.2505 | -0.0654 | -0.0033 | -0.2887 |

五个 harmless offsets 的 median 几乎一致：TV refinement 约 1.40–1.42；efficiency delta 约 -0.204 到 -0.211；jump delta 约 -0.245 到 -0.252。

这证明 resolution effect 是广泛、重复的 measurement effect，不是单一 offset 异常。

## 5. Frozen 0.5 threshold crossing 呈相反方向

### Efficiency

Leg-level：

```text
pass -> pass  436,182  (59.18%)
pass -> fail  214,380  (29.08%)
fail -> fail   86,542  (11.74%)
```

Nested refinement 下 `E1 <= E5` 是数学约束，所以不存在合法的 fail→pass。细化分辨率会系统性让 efficiency gate **更严格**。

Identity-level `inefficient_leg`：

```text
pass -> fail  97,027 / 184,276 = 52.65%
fail -> fail  48,343
pass -> pass  38,906
```

即超过一半 published identities 在 shared fine path 上新增 inefficient rejection。

### Jump share

Leg-level：

```text
fail -> pass  258,735  (35.10%)
fail -> fail   14,398  (1.95%)
pass -> pass  463,971  (62.95%)
```

Jump share 没有 refinement monotonicity theorem；实际数据中绝大多数 response 向下，但存在正 delta。Frozen 0.5 gate 上本样本没有形成 pass→fail crossing，却有大面积 fail→pass。

Identity-level `jump_dominated_leg`：

```text
fail -> pass  126,196 / 184,276 = 68.48%
fail -> fail   13,852
pass -> pass   44,228
```

所以 sampling refinement 对 jump gate 的主效应与 efficiency **方向相反**：jump gate 大量解除 rejection，而 efficiency gate 大量新增 rejection。

### Flat share

Flat-share transition 基本不变：`pass->pass = 737,089`，仅 15 legs pass→fail。当前主矛盾不是 flat-share。

## 6. Duration dependence 排除简单全局 threshold remap

Spearman：

```text
duration vs TV1/TV5     rho = 0.1755
duration vs E1-E5       rho = 0.1251
duration vs J1-J5       rho = 0.8838
```

Jump response 尤其强烈依赖 leg duration：

```text
1-3 bars   median J1-J5 = -0.4772
4-5 bars   median J1-J5 = -0.2913
6-11 bars  median J1-J5 = -0.1947
12-23 bars median J1-J5 = -0.1159
24+ bars   median J1-J5 = -0.0436
```

Efficiency response 也随 duration 改变，但关系更弱且非单一线性平移。因此没有证据支持“把 0.5 换成一个新的全局常数”就得到 resolution-invariant measurement。

## 7. Strict-pair overlays：resolution response 是广泛性质，不只属于 disagreement subset

Aggregate median：

| stratum | TV ratio | E delta | J delta |
|---|---:|---:|---:|
| 482 both-qualified | 1.3643 | -0.1974 | -0.1726 |
| 699 disagreement | 1.3719 | -0.1969 | -0.1773 |
| target repaired agreement | 1.3320 | -0.1873 | -0.1942 |
| target repaired disagreement | 1.3756 | -0.2105 | -0.2041 |

Disagreement / target-disagreement 的 response 略强，但与 both-qualified / agreement 大量重叠。因此 resolution response 是 measurement system 的普遍性质，不适合用 matcher 或只对 failure subset 打补丁解决。

## 8. 与 v0.6.7 / v0.6.8 的闭环解释

v0.6.7 已看到：

- `jump_dominated_leg` disagreement 在 canonical 1m 上 368/368 → both-pass；
- `inefficient_leg` disagreement在 canonical 1m 上 211/211 → both-fail。

v0.6.8 又看到：直接用 shared 1m + 原 0.5 thresholds 虽把 disagreement 699→173，但 both-qualified 482→103，主要变成 joint rejection。

v0.6.9 解释了为什么：

1. partition refinement 必然增加/保持 observed TV；
2. 相同 endpoints 下 efficiency 必然下降/不升；
3. jump concentration 在真实数据里大幅下降，但 magnitude 强依赖 duration，且不存在对应 monotonic theorem；
4. 因此原 `efficiency >= 0.5` 与 `jump_share <= 0.5` 是 **resolution-specific measurement + threshold**，不是两个 resolution-invariant morphology truths。

## 9. 正式裁决

正式裁决：

> **`metrics_have_opposed_resolution_semantics_requiring_property_redefinition`**

含义：

- resolution scaling 有结构，但不足以支持简单全局 threshold remap；
- efficiency 与 jump 在 refinement 下产生相反方向的 qualification migration；
- jump response 又强烈受 leg duration 调制；
- flat share 当前基本稳定；
- 下一步应先重新定义希望 qualification 表达的 underlying path property，而不是拟合新的 0.5，也不是把 1m 直接 promoted 成 runtime hard gate。

## 10. 下一步允许做什么

如果继续，只允许另开结果前 **path-property redefinition preanalysis**。优先问题：

1. `efficiency` 与 `jump_share` 是否事实上是同一 underlying irregularity 在不同 resolution 下的两个投影；
2. 是否存在基于 multi-resolution curve / refinement response 本身的 threshold-free 或 scale-normalized descriptor；
3. 若 runtime 必须只使用 native 5m，是否能构造对 bar-origin 平移稳定、对 sampling resolution 明确协变的 measurement；
4. replacement property 必须先证明 prefix causality、harmless-slicer invariance 和 synthetic counterexamples，再单独冻结 threshold/qualification 实验；
5. duration-geometry 继续作为独立 secondary workstream，不得与 path-property repair 混在同一轮。

禁止：根据 v0.6.9 直接拟合新 efficiency/jump thresholds；不得回到 D1/D2/PAWCT、第三浪、收益/OOS 或交易。

当前全局状态仍为：

`morphology_replication_not_yet_accepted`
