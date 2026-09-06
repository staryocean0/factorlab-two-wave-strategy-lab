# v0.5.6 D2 whole-envelope translation：最终 multiview 裁决

日期：2026-09-06  
最终状态：**`rejected_multiview_label_stability`**

冻结上游：

> **v0.5.2 TCSS exact-ridge parent identity + v0.5.4 full-cycle-scale qualification**

本实验只研究父级 `range / uptrend / downtrend / uncertain` 的方向/状态定义，不修改 parent、qualification、raw projection、ledger、clock，不使用收益或后续第三浪结果。

## 1. 假说与结果前协议

v0.5.5 只读归因表明，旧 D1 的 371 个 qualified `uncertain` 中 243 个属于 `same_phase_reversal_conflict`；185 个 uncertain 的完整 upper/lower envelope 实际已经同向且两者都越过原冻结 `0.15`。

因此 v0.5.6 事前冻结的单组件假说是：父级状态首先由**完整 upper/lower envelope 的总迁移**决定，而不是要求共享 envelope 上的每一个局部子步都单调。

保持平均周期振幅归一化与 `phase_tolerance=0.15` 不变：

- `net = s0 + s1`
- low-start：`E_lower=net, E_upper=s2`
- high-start：`E_upper=net, E_lower=s2`
- 两条 envelope 都 `>0.15` -> uptrend
- 两条都 `<-0.15` -> downtrend
- 两条都满足 `|E|<=0.15` -> range
- 其余 -> uncertain

`s0/s1` 局部反号继续保存为 morphology diagnostic。

协议：`docs/research/two_wave_d1_envelope_translation_protocol_v056.md`  
预分析：`docs/research/two_wave_d1_envelope_translation_preanalysis_v056.md`

## 2. 数值边界实现修复不是研究调参

早期 synthetic run 暴露两个 IEEE 浮点问题：

1. `0.35 + (-0.30)` 不能用裸 `==0.05`；
2. `0.10+0.05` 的机器表示可能略高于 `0.15`。

实现仅加入 `NUMERIC_EPSILON=1e-12` 作为数值比较保护，并增加测试证明 `0.150001` 仍然属于 clear translation。因此研究阈值没有从 `0.15` 被实质放松。

Node.js 20 deprecation 是 GitHub Actions warning，与研究失败无关。

## 3. 主 5m mechanism：PASS

正式 run：`34009093294` — success  
artifact：`9981922969`  
SHA256：`a93bd6f45d15feeef29a0ee271810d55c734f4d47bba53e9f84b784540ac6316`

`5m_offset_0`：

- evaluated 38,049
- qualified 734
- selected 404

所有冻结上游 exact match：

- candidate identity
- qualification flags / rejection reasons
- selected record IDs
- selected occurrence intervals
- D0/D1 historical fields
- confirmation / availability clock

D1 qualified：range 4 / uncertain 371 / uptrend 187 / downtrend 172  
D2 qualified：range 22 / uncertain 185 / uptrend 280 / downtrend 247

D1 selected：range 3 / uncertain 218 / uptrend 101 / downtrend 82  
D2 selected：range 17 / uncertain 106 / uptrend 155 / downtrend 126

数量变化本身不是通过理由。

D1->D2 qualified transition：

- range -> range 4
- uncertain -> uptrend 105
- uncertain -> downtrend 80
- uncertain -> range 18
- uncertain -> uncertain 168
- uptrend -> uptrend 175
- uptrend -> uncertain 12
- downtrend -> downtrend 167
- downtrend -> uncertain 5

没有 D1 uptrend 直接翻成 D2 downtrend，也没有反向情况。

22 个 D2 range 中 21 个存在 `s0*s1<0`。这支持其主视图金融语义：parent range 可以包含大幅内部摆动，只要两条完整父级 envelope 没有明确同向迁移。

主 5m 结果详见：`docs/research/two_wave_d1_envelope_translation_results_v056_main5m.md`。

## 4. 因果性：18/18 PASS

### Native 5m

正式 five-view run：`34009427027`，执行 commit `266bac6389098169598084667fcb46897a53ccf2`。

- precheck / full regression：PASS
- 五个 native 5m view shard：全部 PASS
- 每个 view full + 25/50/75%：**15/15 prefix zero rewrite**
- v0.5.4 -> v0.5.6 selected IDs / intervals：exact match

每个 native-view artifact：

- offset_0：`9982054238`
- offset_1：`9982052651`
- offset_2：`9982053168`
- offset_3：`9982051672`
- offset_4：`9982051902`

### 1m official

正式 parallel run：`34009436754` — success  
final artifact：`9982103606`  
SHA256：`f1513a9559b094c63813630418f342b9b75f4039fb4668ab76b48579ba0a68d5`

25/50/75% 三个 shard 全部 PASS：**3/3 prefix zero rewrite**。

因此 D2 因果门合计：

> **18/18 confirmed classification zero rewrite。**

所以 v0.5.6 的否定原因不是未来改写。

## 5. Frozen multiview label-stability gate：FAIL

协议事前规定：在 D1/D2 selected intervals 完全相同的前提下，将各 native 5m offset 映射到已有 `1m_official` 时间戳，只比较共同拥有区间上的 label agreement；如果 D2 对主视图的 same-label fraction 在四个 offset 上**全部低于 D1**，则 D2 直接否定，不得调阈值或改验收门救回。

正式 aggregate 恰好触发该 hard gate：

> `AssertionError: D2 label agreement is systematically lower than D1 on all four native offsets`

因为 hard gate 在正常 final summary 写盘前抛出，后续只读 failure diagnostic 重新下载五个已经成功的 view artifacts，不重跑 recognizer、不改判据，只保存精确数值。

failure diagnostic：

- run `34009928175` — success
- diagnostic commit `407ba1ef0f0586022229ed8f9524d9c488571e73`
- artifact `9982147148`
- SHA256 `1968b70bef5053dcaf1979bbf399013d326f9c415a02645dd47c82581e294d0a`

精确结果：

| native offset | boundary IoU | D1 same-label | D2 same-label | D2-D1 |
|---|---:|---:|---:|---:|
| offset_1 | 36.7874% | 78.0399% | 76.3050% | **-1.7349pp** |
| offset_2 | 31.3383% | 78.4855% | 73.6850% | **-4.8005pp** |
| offset_3 | 31.2142% | 76.4696% | 72.1744% | **-4.2952pp** |
| offset_4 | 35.0993% | 83.9950% | 82.1246% | **-1.8704pp** |

- worse_count = **4/4**
- mean D2-D1 = **-3.1752pp**

Boundary IoU 对 D1/D2 完全相同，因为 D2 不允许修改 selected intervals。这里下降的是**方向/状态标签稳定性**，不是 parent 边界稳定性。

## 6. 为什么这是一个有价值的负结果

v0.5.6 同时证明了三件不同的事：

1. **whole-envelope translation 有合理的主视图金融语义。** 它能把大量 D1 的局部子步冲突解释为完整 upper/lower envelope 的父级迁移。
2. **公式是因果稳定的。** 18/18 prefix zero rewrite，不能把失败归因于未来信息或确认时钟。
3. **但它对 native 5m 切片更敏感。** 四个 offset 的共同拥有区间 label agreement 全部低于 D1。

因此不能因为主视图 `uncertain` 从 371 降到 185、`range` 从 4 增到 22，就把 D2 宣称为更好的父级分类器。coverage / decisiveness 不等于 accuracy 或 robustness。

最可能需要进一步研究的不是 `0.15` 数值，而是：

> 为什么用 `s0+s1` 形成整条 shared-envelope net migration 后，会比局部 D1 投票更容易受到 5m bar-boundary / raw projection endpoint allocation 的扰动？

这是下一轮只读归因问题，不是立即修改公式的问题。

## 7. 最终裁决

冻结协议下：

- main5m mechanism：PASS
- upstream zero drift：PASS
- synthetic semantics：PASS
- 18/18 causality：PASS
- selected interval identity：PASS
- native-5m label stability：**FAIL（4/4 systematic worsening）**

因此正式状态为：

> **`v0.5.6_rejected_multiview_label_stability`**

D2 whole-envelope translation **不升格为 parent-direction baseline**，不得通过调 `phase_tolerance`、修改 hard gate、挑案例或查看收益复活。

冻结上游仍是：

> **v0.5.2 exact-ridge parent identity + v0.5.4 full-cycle-scale qualification**

D1 父级状态分类仍未验收。

## 8. 下一安全停点

在任何 v0.5.7 新分类公式之前，先做只读 **cross-offset disagreement attribution**，重点分解：

- D1 与 D2 disagreement 是否集中在 `0.15` 附近；
- D2 的 `E_upper / E_lower` 哪一条在 offset 间更容易跨零/跨阈值；
- D1 的 `s0/s1/s2` 哪一项更稳定；
- 是否主要来自 `net=s0+s1` 对 raw endpoint allocation 的误差累积；
- low-start / high-start 是否对称；
- D2 range / trend 哪类最不稳；
- disagreement 与 birth scale、amplitude ratio、corresponding-leg duration diagnostic 是否有关；
- 大 margin 的 disagreement 与 threshold-near disagreement 必须分开。

先冻结归因协议，再运行真实数据。未找到机制前不设计 v0.5.7。

仍不进入 independent morphology acceptance、H1/H2、收益或交易。