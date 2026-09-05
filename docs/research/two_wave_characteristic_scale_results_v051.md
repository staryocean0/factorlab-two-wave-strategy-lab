# v0.5.1 TCSS characteristic-scale 自动尺度实验：正式结果与否定归因

日期：2026-09-05

状态：`synthetic_scale_selection_pass_real_parent_recognizer_fail`

操作基线：**v0.4.3（不变）**

本轮只验证：能否在 v0.5.0 已通过的 TCSS 因果多尺度表示上，使用事前冻结的自动 characteristic-scale 规则，把“存在于尺度空间中的正确父级两浪”稳定地选成唯一、可投影到 raw price、可送入冻结资格/D1/互斥发布的生产候选。

本轮没有修改资格阈值、D1、收益、第三浪、交易或生产权限。

## 1. 结果前协议与正式证据

结果前协议：

- `docs/research/two_wave_characteristic_scale_protocol_v051.md`

核心实现：

- `src/factor_lab/visual_structure/two_wave/characteristic_scale_v051.py`
- `tests/unit/test_two_wave_characteristic_scale_v051.py`
- `scripts/run_two_wave_characteristic_scale_v051.py`
- `.github/workflows/two-wave-characteristic-scale-v051.yml`

正式执行 HEAD：`8ee854b9a40c1eebacd92c9ce9a8c53837963dfd`

正式 GitHub Actions：**run `33969298881`，success**。

正式 artifact：

- artifact id：`9970661191`
- name：`two-wave-characteristic-scale-v051-8ee854b9a40c1eebacd92c9ce9a8c53837963dfd`
- bytes：`46,225`
- SHA256：`28756eb1c07db3c2a8b45f52bfdc416f8c062554735d8ac16059972de66273c0`
- expires：`2026-10-05T13:51:59Z`

全量回归：**379 tests / 0 failures / 0 errors / 0 skipped**。

六视图 × 25%/50%/75%：**18 次固定前缀重放全部通过**。

数据边界仍为仓库冻结的 2015-01-05 至 2020-12-31 development material；`fresh_oos=false`、`trade_authority=false`、`production_authority=false`。

## 2. v0.5.1 冻结的数学选择器

v0.5.1 没有人工选择 sigma，也没有用 `12—48`、case 标签、D1、IoU 或收益反推尺度。

每个同一尺度的五-extrema TCSS candidate 计算共同尺度响应：

`Q = min_k [ sigma^(3/2) * signed_second_difference_k ]`

即二阶 temporal derivative、`gamma=3/4`，取五个相位点中最弱的正曲率响应作为 common-scale gate。

相邻尺度上的候选五点按：

- 相同起始 phase；
- corrected temporal center；
- 因果 confirmation 顺序；
- 单调一对一 greedy matching；

连接成 candidate family。

一个 family 的尺度 `j` 只有在：

`Q_j > Q_(j-1)` 且 `Q_j >= Q_(j+1)`

时才成为 characteristic event。必须等待更粗邻层已确认，所以尺度身份也有独立 confirmation clock，禁止事后左移。

随后把选中的 filtered 五点投影回五个 exact raw-close extrema，再完整调用 v0.4.3 的冻结资格、D1 与互斥账本。

## 3. 合成数学门：通过

正式全量测试证明：

- 严格单调 raw price 不会凭空产生 characteristic two-wave；
- 单周期的自动 characteristic scale 随真实波长增加而系统向粗尺度移动；
- 父频 + 子频共存时能够出现分离的 characteristic scales；
- scale identity 不依赖旧 `12—48`；
- raw projection 与 qualification 分层；
- prefix append 不改写已经 confirmed 的 characteristic event / raw projection / ledger history。

因此本轮失败**不是**“scale-normalized derivative 作为一般时间尺度估计理论完全错误”。它在合成信号层实现了预期性质。

## 4. 主 5m：自动 selector 没有把 v0.5.0 的父级粗化传递到生产候选

`5m_offset_0`：

- TCSS candidate features / scale：`28663, 24675, 19447, 14227, 9815, 6799, 4785, 3287, 2231, 1575, 1103, 797, 595, 423`
- candidate family members：`118,422`
- family 数：`28,692`
- characteristic events：`3,121`
- raw projection valid：`2,945`
- projection invalid：`176`，全部为 `raw_projection_not_actual_turn`
- evaluated raw pairs：`2,945`
- 冻结 v0.4.3 资格通过：`57`
- 互斥发布：`45`
- 发布标签：`uptrend=11 / downtrend=10 / uncertain=24 / range=0`

资格通过与发布最终只来自 scale level 4/5/6，即 sigma 约 `2 / 2.828 / 4`。

注意：发布少、覆盖低本身不是失败判据；真正的失败来自**父级机制与边界稳定性**。

### 4.1 父级微摆吸收几乎消失

v0.5.0 的关键正结果是：随 TCSS 尺度增大，一个两浪内部真正可以吸收多个 v0.4.3 局部 extrema；例如 sigma 8 时额外微极值中位数为 4。

但 v0.5.1 最终 45 个发布对象：

- `excess v0.4.3 local pivots beyond five`：median **0**
- p90 **0**
- max `2`
- 只有 **4 / 45** 个发布对象实际吸收了任何额外 v0.4.3 微摆。

所以 v0.5.1 自动尺度身份把系统又拉回了“基本局部五点”的区域，**没有把 v0.5.0 已证明存在的父级粗化能力传递到最终识别层。**

### 4.2 characteristic event 有很长的尺度选择延迟尾部

全部 characteristic events 的 scale-selection delay：

- median `5 bars`
- p90 `46`
- p99 `221`
- max `911`

冻结资格中的 `confirmation_delay<=8` 最终把已发布对象限制在较短延迟，因此 selected delay median 6、max 8；但 selector 本身大量 family 要等很久才能在粗尺度邻层确认局部最大值。

这不是未来函数，但说明当前 family / local-scale-max 机制会生成大量很迟才确定的尺度身份。

## 5. 五个原生 5m offset：四项边界 IoU 全部恶化

IoU 只表示不同 5m 切片起点下发布区间的边界稳定性，不是准确率。

| offset | v0.4.3 | v0.5.1 | 变化 |
|---|---:|---:|---:|
| offset_1 | 26.42% | **15.56%** | -10.86 pct |
| offset_2 | 20.27% | **8.32%** | -11.95 pct |
| offset_3 | 22.86% | **14.37%** | -8.49 pct |
| offset_4 | 28.00% | **24.09%** | -3.91 pct |

**四项全部恶化。**

这比覆盖率下降更有判别力：如果 characteristic scale 真正在恢复同一 underlying parent structure，原生 5m 切片起点变化后不应系统性更不稳定。

因此 v0.5.1 不能升级为新 recognizer。

## 6. case_00：正确 sigma 区间仍存在，但 selector 选成了“滑动后的另一组五点”

v0.5.0 已证明 case_00 在 sigma 约 2.828—5.657 出现目标父级粗化，其中 sigma 4 的 filtered candidate 为规整大结构，cycle 约 `34/43`，审计 IoU 约 0.859。

v0.5.1 在旧区间 `[48720,48801]`：

- evaluated overlap：`11`
- qualified：`0`
- selected：`0`

最接近对象只是：

- sigma 2.828：raw `[48749,48754,48768,48801,48806]`，cycle `19/38`，legs `5/14/33/5`；
- sigma 4：raw `[48749,48801,48806,48811,48836]`，cycle `57/30`，legs `52/5/5/25`。

也就是说，**sigma 4 本身并没有消失；消失的是“同一组父级五点身份”。**

v0.5.0 中那个能够表达大结构的 sigma 4 五点仍存在于尺度空间，但 v0.5.1 的 candidate-family local maximum 连接到了另一组滑动窗口，最终没有把目标结构选出来。

这就是本轮最关键的失败归因。

## 7. 固定窗口进一步证明：问题主要发生在 characteristic candidate identity，不应马上怪资格层

### 2018-06-20

v0.5.0 中间尺度曾清晰出现：

- sigma 1.414/2：约 `17/18`
- sigma 4：约 `24/27`

v0.5.1 则只有 3 个重叠 evaluated object，0 qualified / 0 selected；最接近的是 sigma 1.414 的 raw `28/6`，另两个已经跳到 sigma 11.3/22.6 的超大结构。

因此这里**不是**原来的 `0.308 < 0.5` 资格边界问题先暴露，而是 selector 已经没有把 v0.5.0 的规整中尺度父结构送进资格层。

### 2019-04-15

v0.5.0 中间尺度存在 `15/13`、`25/23`、`25/42` 等结构。

v0.5.1 旧窗口 5 个 evaluated object 全部是错位或明显过粗对象，0 qualified / 0 selected；多个 characteristic scales 跳到 sigma 8、11.3、22.6。

这再次说明：candidate family 在 extrema 随尺度湮灭后发生了**成员滑移**。

### 2020-07-15

这里有一部分 downstream 资格问题已经重新出现：

- sigma 5.657 的 raw candidate cycle `39/38`，仅因 `inefficient_leg + confirmation_too_late` 被拒；
- sigma 2.828 的 raw candidate cycle `21/35`，仅因 `inefficient_leg` 被拒。

这说明以后资格层确实仍值得独立实验，但它不是当前最高优先级，因为 case_00 / 2018 / 2019 在进入资格层前就已经选错结构。

## 8. 安全反例没有回归，但不足以通过

### case_02

旧 90/3 假浪没有复活：旧窗口 15 evaluated / 0 qualified / 0 selected。短腿、jump、长周期、确认过晚等约束继续挡住坏结构。

### case_11

只发布一个局部 downtrend：raw cycle `38/41`，不是旧跨数周巨型五点。

### case_14

47 evaluated / 0 qualified / 0 selected；粗尺度巨型对象存在于审计层，但没有通过冻结资格进入发布。

所以 v0.4.3 已取得的主要安全性没有被破坏。但这不足以抵消主目标失败。

## 9. case_10 给出一个重要的“后续资格/D1仍需研究”证据，但现在不能抢跑

case_10 中 v0.5.1 出现 raw `[8692,8699,8724,8739,8751]`，与旧视觉窗口几乎完全一致（只差首点 1 bar，审计 IoU 约 0.983），characteristic sigma 5.657。

它仍被：

- `corresponding_leg_duration_mismatch`
- `inefficient_leg`
- `confirmation_too_late`

拒绝。

这证明资格边界/D1 独立问题依然真实。但由于其他核心窗口在 selector 层已经错位，**当前不能通过修改资格来“救”v0.5.1。**

`docs/research/two_wave_qualification_preanalysis_v052.md` 因此继续保持 `conditional_preanalysis_not_protocol_frozen`，不启动。

## 10. 失败根因：跨尺度“候选五点窗口”不是稳定的 feature identity

v0.5.1 的数学错误发生在方法映射层，而不是 Lindeberg 的 temporal scale-selection 理论本身。

尺度空间的基本事实是：随尺度增加，局部 extrema 会漂移并在 bifurcation 中成对湮灭。于是：

- fine scale 的连续五 extrema：`e1,e2,e3,e4,e5`
- 某个中间微 extrema 消失后，coarse scale 的连续五 extrema 可能变成：`e1,e2,e5,e6,e7`

如果先把“连续五点窗口”当成 feature，再按窗口中心去跨尺度连接，那么 family identity 会在 extrema 消失时自然滑动到邻近的另一组五点。

因此即使 common curvature response 的 local maximum 在数学上合法，**它最大化的是一个已经换了成员的 candidate family**，而不是“同一父级五个 extrema 在尺度维度上的 characteristic scale”。

case_00、2018、2019 都直接支持这个归因。

## 11. 跨学科理论复核：下一层应该先建立 extremum trajectories / scale-space primal sketch

这一失败机制与经典 scale-space 理论的解决方式一致。

Lindeberg 的相关工作明确研究：

- local critical points 在 scale-space 中的 trajectories；
- extrema 漂移；
- annihilation / merge / split 等 bifurcation；
- 先把 local extrema / critical points **跨尺度连接成 feature trajectories**，再从 linked structures 提取稳定尺度与显著结构；
- scale-space primal sketch 的目的正是显式表达“不同尺度上的结构之间是什么关系”。

参考：

- Lindeberg, *Scale-Space Behaviour of Local Extrema and Blobs*, JMIV 1992, DOI `10.1007/BF00135225`
- Lindeberg & Eklundh, *On the computation of a scale-space primal sketch*, JVCIR 1991, DOI `10.1016/1047-3203(91)90035-E`
- Lindeberg, *Detecting Salient Blob-Like Image Structures and Their Scales with a Scale-Space Primal Sketch*, IJCV 1993, DOI `10.1007/BF01469346`
- Lindeberg, *Temporal Scale Selection in Time-Causal Scale Space*, JMIV 2017, DOI `10.1007/s10851-016-0691-3`

一维 topological persistence 也给出独立参照：局部 extrema 的 persistence 表示它们对小扰动的稳定性，低 persistence extrema 可以被系统简化。但标准 1D persistence 往往是全域/离线量，因此在本项目中只能先作为 hierarchy oracle，除非另外证明严格 prefix-native。

## 12. 下一安全停点

**不要进入 v0.5.2 资格实验。**

下一轮应先冻结新的表示关系组件：

### `extremum-level scale-space ridge / persistence skeleton`

核心变化只能是：

1. 不再把五点 window 当跨尺度 family 的原子；
2. 先把每个 high/low extremum 在相邻 TCSS scales 上连接成单独的、同 phase、顺序保持、严格因果的 extremum trajectory / ridge；
3. 显式记录 ridge 的 birth/survival/death（或相邻 max-min annihilation）scale；
4. 五个 parent extrema 的身份由 **五个 immutable ridge IDs** 定义；
5. 两浪 candidate 只有在同一 scale interval 内这五条 ridge 同时存在且相邻时才成立；
6. characteristic scale / structural scale 只能在这个**exact ridge tuple 的生存区间**内定义，不能再通过候选中心匹配把另一组五点接进来；
7. raw-reversal projection、资格、D1、互斥账本继续冻结；
8. `12—48` 仍只能在自然 hierarchy candidate 已形成后做 downstream target-scale qualification，不能决定 ridge birth/death。

在代码前必须先完成：

- scale-space trajectory / primal-sketch 文献与数学实现预分析；
- 合成 bifurcation / nested waves / chirp / jump / monotonic gates；
- prefix-native trajectory identity 设计；
- 对 v0.5.0 正例与 v0.5.1 失败窗口的“结果前”验收定义。

若 extremum-ridge 方法仍不能稳定把 v0.5.0 的父级结构传入最终候选，再正式让 tSSA / causal wavelet/filter-bank 与 TCSS 竞争，而不是继续修 TCSS。

## 13. 阶段判定

v0.5.1：

**技术实现通过；合成 characteristic-scale 假说通过；真实金融父级 recognizer 假说否定。**

TCSS v0.5.0 的表示层正结论继续保留；v0.5.1 candidate-window family selector 作为负向消融归档；操作基线继续为 **v0.4.3**。

PR #1 继续 Draft，不合并 main。形态验收前不进入 H1/H2、收益、交易或生产。