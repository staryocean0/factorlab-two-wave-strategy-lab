# v0.6.13 step-count / resolution-normalized concentration：正式结果与云端裁决

日期：2026-09-07

状态：`step_count_normalization_reduces_duration_bias_but_not_cross_resolution_gap`

操作基线仍为 **v0.4.3**；全局状态仍为 `morphology_replication_not_yet_accepted`。本轮只审计 threshold-free movement-weight concentration profile；没有修改 qualification、threshold、identity、matcher、projection、publication、roughness candidate、direction、outcome 或 trading logic。

## 1. 结果前冻结

- `docs/research/two_wave_step_count_normalized_concentration_preanalysis_v0613.md`
- `docs/research/two_wave_step_count_normalized_concentration_protocol_v0613.md`
- helper blob `21160853e418b1b05199b8735613b3ab2d2c5350`
- test blob `a177c193576a739f2b5500b55a0f65b894da2761`

Synthetic tests：**9/9 PASS**。

注册 profile 对 movement weights `w_i=x_i/sum(x)` 同时保留：

```text
C_inf = log(n * max w)
C_1   = log(n) - ShannonEntropy(w)
C_2   = log(n * sum(w^2))
```

三维坐标均事前冻结，未事后挑 winner；对所有 increment 做等比例 k-fold subdivision 时三者严格不变。

## 2. Hard controls 全部闭合

```text
published identities = 38,176 / 36,737 / 36,619 / 36,480 / 36,264
published raw strict pairs = 8,381 / 5,770 / 6,204 / 9,098 = 29,453
both-qualified = 482
qualification disagreements = 699
target repaired = 80 = 56 agreement + 24 disagreement
```

v0.6.10 oracle-comparable **117,805 pair-leg** control也精确复现：native J5 abs-diff median `0.0539310318`；fine J1 `0.0064740521`；origin-jump median `0.0169575462`。

第一次 aggregation 曾错误地把 raw J control availability 绑到 profile 的 `n>=2` 定义；该执行口径在 interpretation 前被发现，随后将 raw J 与 profile availability 解耦并完整重跑。Profile 数学/协议没有改动。

## 3. Step-count normalization 显著削弱 duration bias

Cross-resolution absolute-gap vs native step-count Spearman：

```text
raw |J5-J1|  -0.884
C_inf gap     0.174
C_1 gap      -0.223
C_2 gap      -0.036
```

原 raw max-share error 对 step count 有极强机械依赖；normalized profile 后 `C_1/C_2` 明显减弱，`C_2` 已接近零 rank association。

冻结 bins 中 raw J gap median 从 `1-3` bars 的 `0.4772` 降到 `24+` 的 `0.0438`；`C_1` gap median约为 `0.1694 / 0.1311 / 0.1122 / 0.0958 / 0.1061`，`C_2` 约为 `0.2406 / 0.1949 / 0.1770 / 0.1700 / 0.2563`。

## 4. Native→fine cross-resolution gap 仍 materially 存在

| component | Spearman(native,fine) | abs-gap median | signed native-fine median |
|---|---:|---:|---:|
| `C_inf` | 0.714 | 0.5185 | -0.5185 |
| `C_1` | 0.437 | 0.1247 | -0.1013 |
| `C_2` | 0.514 | 0.2047 | -0.1833 |

三者 native→fine signed median 都为负，说明真实 1m refinement 不是把每个 5m movement 均匀复制，而是引入 unequal subdivisions、cancellation 与新的 local movement structure。尤其 `C_inf` 的 24+ bars gap median 反而升到约 `0.9223`。

## 5. Fine profile 跨 harmless slicer 稳定，但 native profile不能等价恢复

| metric | comparable pair-legs | median | p90 |
|---|---:|---:|---:|
| native J5 | 117,812 | 0.0539 | 0.2206 |
| native `C_inf` | 104,582 | 0.1659 | 0.4249 |
| native `C_1` | 104,582 | 0.0922 | 0.2739 |
| native `C_2` | 104,582 | 0.1293 | 0.3583 |
| fine `C_inf` | 117,805 | 0.0360 | 0.1845 |
| fine `C_1` | 117,805 | 0.0176 | 0.0905 |
| fine `C_2` | 117,805 | 0.0267 | 0.1258 |

Fine profile 在 shared supplied-1m path 上保持较小 cross-slicer disagreement；问题仍是 native 5m increments 得到的 profile 与 fine profile 不是同一个 measurement。

## 6. Origin refinement 仍显示真实 coarse sampling aliasing

五-origin range median：

```text
C_inf 0.3984
C_1   0.2292
C_2   0.3109
```

Fine vs origin-median absolute gap median约为 `0.3966 / 0.0874 / 0.1424`。因此 normalized profile 仍受到 coarse origin/refinement path 的真实结构影响，而不只是 step-count replication。

## 7. 三维 profile 高度相关

Aggregate Spearman：

```text
native C_inf↔C_1 0.799
native C_inf↔C_2 0.880
native C_1↔C_2   0.978
fine   C_inf↔C_1 0.814
fine   C_inf↔C_2 0.898
fine   C_1↔C_2   0.976
```

尤其 `C_1/C_2` 基本描述同一个 concentration ordering。按冻结规则仍全部保留，没有事后删维。

## 8. Availability 是额外限制

```text
published legs           737,104
native profile defined   664,001
fine profile defined     737,070
both native+fine         663,972
```

约一成 published legs 因 native 只有一个 increment 而无法定义 normalized profile，不能忽略这项 coverage 代价。

## 9. Frozen strata 不推翻主结论

Both-qualified、qualification-disagreement、target repaired 与 target disagreement 中，fine `C1/C2` cross-slicer difference仍较小，而 native→fine gap持续存在。没有关键 target stratum 证明 native normalized profile 已经等价于 fine property。

## 10. 正式裁决

> **`step_count_normalization_reduces_duration_bias_but_not_cross_resolution_gap`**

解释：

1. Rényi/KL-to-uniform normalization 消除了 uniform subdivision 下纯 step-count replication 的 concentration 漂移；
2. 实证上 raw J error 的强 step-count dependence 被显著削弱，特别是 `C_1/C_2`；
3. 但真实 5m→1m refinement 含 unequal subdivisions、cancellation 与新的 local movement，因此 native/fine profile 仍有系统 level shift 与有限 rank correspondence；
4. fine profile 本身跨 slicer 较稳定，但 native 5m profile不能可靠代表它；
5. 三个坐标高度相关且 native availability 有损失，所以 v0.6.13 不允许 property promotion。

## 11. 下一步

下一步只允许另开 results-blind **native multiscale/refinement-aware concentration representation preanalysis**：不再拟合 native scalar 到 J1，而研究 native data 内部能否构造多个 causal sub-partitions / scale-response profile，对真实 refinement uncertainty做显式表示。

不得拟合 qualification threshold、duration correction或 outcome；roughness erosion candidate保持冻结；supplied 1m继续只能作为 audit oracle。

当前全局状态仍为：`morphology_replication_not_yet_accepted`。
