# v0.6.12 native-5m concentration deployable-proxy：正式结果与云端裁决

日期：2026-09-07

状态：`native_ohlc_proxies_do_not_reliably_track_fine_concentration`

操作基线仍为 **v0.4.3**；全局状态仍为 `morphology_replication_not_yet_accepted`。本轮不修改 qualification、threshold、identity、matcher、projection、publication、roughness candidate、direction、outcome 或 trading logic。

## 1. 结果前冻结

- `docs/research/two_wave_concentration_deployable_proxy_preanalysis_v0612.md`
- `docs/research/two_wave_concentration_deployable_proxy_protocol_v0612.md`
- primary runtime proxy：`J_TR = max(true range) / sum(true range)`
- helper blob `49903c1e14fc2ea3a5458dfdcce1dd90cfa13843`
- test blob `2e2d78e3e4c424420e2e7c39381af5d920191512`

Synthetic tests：**9/9 PASS**。Helper 接口只接受单一 native-5m OHLC leg，不接受 1m、alternate offset、counterpart、direction 或 outcome。

## 2. Hard controls / oracle references 全部闭合

```text
published identities = 38,176 / 36,737 / 36,619 / 36,480 / 36,264
published raw strict = 8,381 / 5,770 / 6,204 / 9,098 = 29,453
qualification matrix = 482 / 28,272 / 352 / 347
target repaired = 80 = 56 agreement + 24 disagreement
```

全部 native pair-leg = **117,812**；其中 supplied-1m oracle 两侧均可比较的 v0.6.10 universe = **117,805**。

在这 117,805 上精确复现：

```text
native J5 abs-diff median       = 0.053931032
fine J1 abs-diff median         = 0.006474052
origin-jump median abs-diff     = 0.016957546
```

无 oracle-control drift。

## 3. J_TR 有结构改善，但幅度不足以构成可靠 fine proxy

全部 native pair-leg cross-slicer：

```text
J_close median abs diff = 0.053933
J_TR    median abs diff = 0.039807
J_HL    median abs diff = 0.038873
```

`J_TR` vs `J_close` paired signs：

```text
smaller = 70,835
equal   =  6,442
larger  = 40,535
```

所以 true range 确实降低了一部分 bar-origin sensitivity，但不是压倒性一致。

## 4. 对 fine J1：相对 J5 改善，但存在巨大的系统性 resolution bias

Side-leg oracle error：

```text
|J_close-J1| median = 0.258232, p90 = 0.587699
|J_TR-J1|    median = 0.215079, p90 = 0.511364
```

Paired side-leg 中 `J_TR` error smaller / equal / larger：

`185,627 / 20,298 / 29,692`。

因此 J_TR 比 close-only J5 更接近 J1 是真实信号；但 median absolute error 仍约 **0.215**，远大于 J1 本身的 cross-slicer instability。更严重的是 fixed native bracket 对 J1：

```text
inside = 10,616 / 235,617 = 4.51%
below native bracket = 224,866
```

即 fine J1 几乎总在三个 native concentration measures 的下方。这是 resolution/step-count mismatch，不是一个可接受的 native error envelope。

## 5. 对 origin-jump median：没有稳定胜过现有 J5

```text
|J_close-origin_median| median = 0.039810
|J_TR-origin_median|    median = 0.038792
```

虽然 aggregate median 略降，但 paired side-leg：

`J_TR smaller / equal / larger = 103,693 / 20,298 / 111,626`。

J_TR 实际上在更多 side-leg 上比 J_close 更差，因此不能宣称它可靠估计 origin-ensemble center。

Native bracket 对 origin median 的 empirical coverage = **45.64%**，也不足以形成可靠 envelope。

## 6. 注册的 native uncertainty signal 失败

`proxy_spread = max(J_close,J_TR,J_HL)-min(...)` 的 Spearman：

```text
vs actual origin_jump_range                0.075
vs |J_close-origin_median|                 0.130
vs |J_TR-origin_median|                    0.030
vs |J_close-J1|                            0.105
vs |J_TR-J1|                              -0.038
```

Aggregate association 很弱，因此不能用这个 spread 作为 bar-origin aliasing/error warning proxy。

## 7. Duration dependence 揭示根本问题

`|J_TR-J1|` median 随 native leg duration：

```text
1-3 bars    0.399
4-5 bars    0.238
6-11 bars   0.155
12-23 bars  0.090
24+ bars    0.041
```

这表明 concentration scalar 本身强烈受 step count / sampling resolution 调制。v0.6.12 禁止事后拟合 duration correction，因此不做修补。

## 8. Frozen target strata 没有把候选救回来

Target repaired 的 J_TR cross-slicer median `0.03706`，优于 J_close `0.04770`；target disagreement 也从 `0.05058` 降到 `0.04317`。但对 J1 的绝对误差仍大，且 aggregate uncertainty proxy / bracket 失败。因此不能以 target subset 的局部改善 promotion candidate。

## 9. 正式裁决

> **`native_ohlc_proxies_do_not_reliably_track_fine_concentration`**

解释：

1. true-range concentration 比 close-only J5 有部分 cross-slicer / J1-error 改善；
2. 但 native concentrations 与 fine J1 存在强烈的 resolution-level bias，fixed bracket 对 J1 仅约 4.5% coverage；
3. J_TR 对 origin-jump median 没有 paired-consistent 优势；
4. 注册的 `proxy_spread` 无法可靠指示真实 origin uncertainty；
5. error 随 leg duration/step count 大幅变化，说明继续找一个单尺度 native concentration scalar作为 fine proxy方向不成立。

v0.6.12 不 promoted `J_TR`，也不拟合 duration correction。

## 10. 下一步

下一 formal research step 应回到 concentration property semantics：先做 results-blind **step-count / resolution-normalized concentration preanalysis**，研究 `max-share` 是否必须替换为对 number of increments 明确协变的 concentration descriptor，而不是继续拟合 OHLC→J1 映射。

仍禁止 qualification threshold、matcher/projection/publication 修改、roughness re-optimization、direction/outcome/P&L、第三浪、fresh OOS、paper trading 或 production。
