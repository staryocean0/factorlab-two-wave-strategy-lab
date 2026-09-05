# 两浪研究继续入口：v0.5.1 自动尺度选择真实验证失败，下一步转 extremum trajectories（2026-09-05）

## 当前状态

**操作研究基线继续是 v0.4.3。**

当前已经得到两层不同结论：

- v0.5.0 TCSS：`promotable_raw_reversal_representation_candidate` —— 表示层证明可以因果地随尺度吞掉微摆；
- v0.5.1 candidate-family characteristic-scale：`synthetic_scale_selection_pass_real_parent_recognizer_fail` —— 合成尺度选择成立，但真实金融父级识别失败，不能升级 recognizer。

PR #1 继续 Draft，不合并 main；没有进入第三浪、收益、交易或生产。

优先阅读：

1. [v0.5.1 自动尺度实验正式结果与否定归因](docs/research/two_wave_characteristic_scale_results_v051.md)
2. [v0.5.1 结果前协议](docs/research/two_wave_characteristic_scale_protocol_v051.md)
3. [v0.5.0 TCSS 正式表示层结果](docs/research/two_wave_multiscale_tcss_results_v050.md)
4. [v0.5 跨学科数学预研究](docs/research/two_wave_multiscale_pre_research_v050.md)
5. [v0.4.3 当前操作基线结果](docs/research/two_wave_confirmation_ablation_results_v043.md)
6. [v0.4.4 绝对周期父级定义否定结论](docs/research/two_wave_hierarchy_results_v044.md)

`docs/research/two_wave_qualification_preanalysis_v052.md` 仅是**条件预分析**；由于 v0.5.1 未通过真实 parent-recognizer 门，当前不得启动其中的资格实验。

## 金融合同没有改变

目标仍是：在某个 K 线级别上，识别**连续、同尺度、完整的两个原价格反转波形**，然后才根据这两个波的整体漂移/上下相位迁移区分父状态：震荡、上涨趋势、下跌趋势或不确定。

生产语义继续是 `raw-price reversal wave`：

- 低点起算：`L0 -> H1 -> L1 -> H2 -> L2`；高点起算对称；
- 两个周期共享中间同相位端点；
- 严格单调 raw price 不得因为 IMF/RC/wavelet detail 中存在 detrended cycle 而伪造 raw reversal；
- 计算确认时间和 raw `available_at` 必须分开；
- 已确认历史追加未来后不得重写。

旧 `12—48` 继续只能作为**自然层级候选形成后的目标周期资格/诊断带**，不得定义 parent birth/death、不得选择 characteristic scale。

## v0.5.0 已经确认的正结论仍有效

正式 TCSS run `33966220967`：371 tests、18 次 prefix replay 全部通过。

主 5m 14 层 extrema 数从约 28.7k 严格粗化到 427；一个 TCSS 两浪内部额外吸收的 v0.4.3 微 extrema 中位数在 sigma 5.657 起变为 1，sigma 8 为 4，sigma 11.314 为 7。

case_00 随尺度出现：

`13/6 -> 13/14 -> 19/21 -> 20/21 -> 22/43 -> 34/43 -> 35/42 -> 37/51`

2018 / 2019 / 2020 固定窗口也在中尺度出现规整父级结构。

所以目前**不要否定 TCSS 表示本身**。它确实做到了 v0.4.4 做不到的“父层吞掉子摆”。

## v0.5.1 正式证据

正式执行 HEAD：`8ee854b9a40c1eebacd92c9ce9a8c53837963dfd`

正式 GitHub Actions：**run `33969298881` success**。

正式 artifact：

- id `9970661191`
- bytes `46,225`
- SHA256 `28756eb1c07db3c2a8b45f52bfdc416f8c062554735d8ac16059972de66273c0`
- expires `2026-10-05T13:51:59Z`

**379 tests / 0 failures / 0 errors / 0 skipped。**

六视图 × 25%/50%/75% = **18 次固定前缀重放全部通过。**

主 `5m_offset_0`：

- characteristic events：3,121
- valid raw projection：2,945
- evaluated raw pairs：2,945
- 冻结 v0.4.3 资格通过：57
- 互斥发布：45
- labels：up 11 / down 10 / uncertain 24 / range 0

发布数量与覆盖率不作为准确率。

## v0.5.1 为什么被否定

### 1. 父级微摆吸收没有传递到最终发布

45 个 selected 中：

- `excess v0.4.3 local pivots beyond five` median = **0**
- p90 = **0**
- max = 2
- 只有 **4 / 45** 真正吸收任何额外 v0.4.3 微摆。

这与 v0.5.0 中尺度层明确能吸收多个微摆形成强烈反差。

### 2. 五个原生 5m offset 边界稳定性四项全部恶化

| offset | v0.4.3 | v0.5.1 |
|---|---:|---:|
| 1 | 26.42% | **15.56%** |
| 2 | 20.27% | **8.32%** |
| 3 | 22.86% | **14.37%** |
| 4 | 28.00% | **24.09%** |

所以自动 selector 没有把 underlying parent structure 变得更稳定。

### 3. case_00 仍然 0 qualified / 0 selected

v0.5.0 在 sigma 4 曾出现约 `34/43` 的目标粗结构；v0.5.1 在同一个 sigma 4 选出的却是另一组滑动五点，例如 raw `52/5/5/25`、cycle `57/30`。

**问题不是“sigma 4 不存在”，而是 candidate family 在尺度间换了五点成员。**

### 4. 2018 / 2019 同样证明 selector 先于资格层错位

v0.5.0 的中尺度规整结构存在；v0.5.1 characteristic family 却常跳到另一组局部窗口或过粗尺度，因此没有把正确对象送进冻结资格层。

2020 / case_10 又说明资格边界未来仍值得独立研究，但当前不能用调资格去掩盖 selector 错位。

## v0.5.1 失败的数学根因

v0.5.1 把**连续五个 extrema 的 candidate window**当作跨尺度 feature，然后按 corrected center / phase 连接 candidate families。

但尺度增加时，细 extrema 会漂移并发生 annihilation；一个成员消失后，“连续五点窗口”天然会滑到邻近的新成员。

因此一个 family 在数学上可能变成：

`[e1,e2,e3,e4,e5] -> [e1,e2,e5,e6,e7]`

随后即使 `scale-normalized second derivative` 的 local maximum 完全合法，它最大化的也已经不是**同一五个父级 extrema**。

所以：

> **automatic scale-selection 原理没有被否定；把它施加在会滑窗换身份的 five-extrema candidate family 上被否定。**

## 最新跨学科复核

Scale-space 经典路线与当前失败归因一致：

- local extrema / critical points 应先跨尺度连接成 **feature trajectories / extremum paths**；
- 显式记录 extrema drift 与 bifurcation（特别是 annihilation）；
- scale-space primal sketch 的用途正是把“不同尺度上的结构关系”从隐式变成显式；
- 然后才从 linked structures 提取稳定尺度和更高层结构。

核心参考：

- Lindeberg, *Scale-Space Behaviour of Local Extrema and Blobs*, JMIV 1992, DOI `10.1007/BF00135225`
- Lindeberg & Eklundh, *On the computation of a scale-space primal sketch*, JVCIR 1991, DOI `10.1016/1047-3203(91)90035-E`
- Lindeberg, *Detecting Salient Blob-Like Image Structures and Their Scales with a Scale-Space Primal Sketch*, IJCV 1993, DOI `10.1007/BF01469346`
- Lindeberg, *Temporal Scale Selection in Time-Causal Scale Space*, JMIV 2017, DOI `10.1007/s10851-016-0691-3`

一维 topological persistence 可作为“extrema 稳定性/显著性”的独立数学 oracle，但标准实现可能用全域信息，未证明 prefix-native 前不能产生生产事件。

## 下一安全停点：先做 extremum-level ridge / persistence skeleton

下一版**不叫资格 v0.5.2**。先冻结一个新的层级关系实验：

### A. 原子从“五点窗口”下沉到“单个 extremum trajectory”

每个 high/low extremum 在相邻 TCSS scales 上按：

- same phase；
- temporal order preserved；
- no future confirmation；
- one-to-one lineage；

形成 immutable ridge ID。

### B. 显式记录 ridge 生存区间与 annihilation

不能只看某一层中心距离；要知道一个 fine extremum 如何随尺度漂移、何时被更粗尺度真正吞掉。

### C. 五点 parent identity 由五个 ridge IDs 定义

只有五条 ridge 在同一个 scale interval 内同时存在、交替且相邻时，才能组成一个 two-wave structural family。

成员一旦固定，就不允许在后续尺度把邻近的第六、第七个 extremum 滑进来冒充同一 family。

### D. characteristic / structural scale 只能在 exact-ridge tuple 的生存区间内选

可以研究：

- exact tuple 的 log-scale persistence；
- scale-normalized response 在 tuple lifetime 内的局部最大；
- ridge death / child-annihilation 后首次形成的自然 parent level；

但必须在结果前冻结，不能看 case_00 选法。

### E. raw projection、资格、D1、互斥发布继续冻结

特别是不要启动 `two_wave_qualification_preanalysis_v052.md`。只有新 ridge-level selector 首先把 v0.5.0 的好父级结构稳定送到 raw candidate 层，资格研究才重新排回下一位。

## 下一轮的硬门

代码前先冻结：

1. synthetic nested parent/child waves：child extrema 应在 scale 增大时终止，parent ridge IDs 继续存活；
2. exact five-ridge tuple 不得因一个 child death 滑成另一组五点；
3. monotonic / jump / chirp / intermittent oscillation 安全门；
4. 追加未来后，已 confirmed ridge IDs、death events、tuple IDs 不得改写；
5. case_00 / 2018 / 2019：只能检验 v0.5.0 已知父级结构是否由**事前规则**自然传入，不用于选参数；
6. case_02 / 11 / 14 不退化；
7. 五个原生 5m offset 边界稳定性不得再次系统性恶化；
8. 延迟、覆盖、ridge survival 分布全部显式报告。

若 extremum-ridge / primal-sketch 路线仍然失败，再正式让 tSSA / causal wavelet-filter bank 与 TCSS 竞争，而不是继续修 candidate selector。

## 资格与 D1 的排队状态

资格层的 scale-aligned path efficiency 预分析已经写入仓库，但**inactive**。

D1 的 `range=0` 仍是后续独立问题；不能把中心漂移、上下包络迁移、相位冲突继续混成一个阈值后直接调 `phase_tolerance`。

正确顺序现在是：

**extremum trajectory / parent identity → 资格硬边界 → D1 range/trend → 独立 morphology 验收 → H1/H2。**

## 不变边界

只用现有 2015—2020 development 行情，不新增、不重采样。主目标仍为 `000852.SH` 原生 `5m_offset_0`；四个其他原生 5m 仅稳健性，1m 仅诊断。

负向实验原样保留；不按收益选参；不开放 trade authority。

**PR #1 继续 Draft，不合并 main。**