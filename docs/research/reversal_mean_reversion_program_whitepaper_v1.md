# 广义反转与均值回归研究白皮书 v1

日期：2026-09-08  
项目：`broad_reversal_mean_reversion_discovery_program_v1`

## 1. 项目重新定位

本仓库历史上以“两浪父结构识别器”为中心，已经积累了大量关于因果拐点、同尺度、父结构、路径属性、跨 offset、session support 与信息集边界的研究。

这些工作继续有效，但从现在开始它们的仓库级角色改变为：

> **M0：广义反转/均值回归研究的结构测量底座。**

本仓库不再以“把某一个两浪 recognizer 优化到最好”为唯一目标，而是利用这套结构语言去发现和比较多类反转/均值回归机制。

## 2. 核心科学问题

均值回归不等于“价格离均线远了就回来”。

真正的问题是：

> **在当前尺度和市场状态下，眼前的偏离只是完整父状态中的低一级波动，还是父状态本身已经改变？**

所谓“均值”可以是：

- 价格中心；
- 震荡区间；
- 趋势通道；
- 两个已完成波浪定义出的父级结构；
- 某状态下的正常轨迹；
- 统计分布的中心/区间；
- 多资产之间的正常相对关系；
- 路径效率、波动率、振幅、事件密度等统计属性的正常状态。

因此反转策略的公共骨架不是某一条公式，而是四个问题：

1. **尺度是什么？**
2. **父级状态是什么？**
3. **偏离了什么正常状态？**
4. **什么事件算回归，什么事件算父状态改变？**

## 3. M0：两浪结构语言的正确角色

现有两浪研究回答的是：

- 如何因果地识别完整波形；
- 如何定义同一尺度；
- 如何用两个完整波形成局部父结构；
- 如何描述漂移、覆盖、粗糙度、路径集中度、尺度一致性与信息集；
- 如何保证 streaming / replay / prefix 不被未来重写。

这些都是**测量问题**。

M0 的输出可以作为后续策略研究的坐标，例如：

- parent signed drift；
- trend/range/transition 的连续状态；
- parent width / envelope；
- overlap / convergence / expansion；
- path efficiency / roughness；
- wave duration / event density；
- parent boundary；
- lower-wave 与 parent-wave 的相对尺度。

但 M0 本身不能自动推出：

- 应该买还是卖；
- 第三浪一定怎么走；
- 趋势一定延续；
- 反转一定赚钱。

当前 v0.6.17 authoritative-source formal replay 仍然是 M0 自己的合法未完成任务；其 evidence、freeze 与 blocker 全部保留。只是它不再成为整个仓库唯一允许推进的事项。

## 4. 第一批三条主研究路线

### R1：趋势中的跨尺度回撤

场景：

父级已经表现为较明确的上涨或下跌结构，低一级突然出现反方向的快速波动。

主问题：

> 在同样严重的反向波动下，哪些事前可见的父级完整性特征能区分“次一级回撤”与“父级趋势反转开始”？

典型交易原型：

- 上涨父趋势中的急跌后逢低买；
- 下跌父趋势中的急涨后逢高卖。

第一阶段不研究最终下单，而只研究：

- recovery-before-parent-failure；
- parent integrity 是否提供相对 counter-move severity 的增量信息；
- 这种增量是否跨时期/尺度稳定。

### R2：震荡边界 / 假突破回归

场景：

父级结构更像低漂移的震荡包络，价格短暂越过已有边界。

主问题：

> 越界之后，什么信息能够区分“暂时 overshoot / 假突破”与“父级震荡已经转成新趋势”？

第一阶段重点比较：

- 突破幅度；
- 父级 drift/overlap/efficiency；
- 突破速度；
- 局部波动扩张；
- 越界后先回区间还是先形成同向父级扩展。

不允许为了提高命中率反复更换震荡定义和边界阈值。

### R3：结构衰竭 / 状态切换反转

场景：

父级仍有方向，但结构质量开始恶化，例如：

- 相邻同相位高低点推进减弱；
- overlap 增加；
- 路径效率下降；
- 波幅收敛或扩张异常；
- 下级反向事件密度上升；
- 父级结构接近 transition/uncertain，而不是稳定 trend。

主问题：

> 能否在“明确反向突破已经发生”之前，识别趋势正在从完整状态走向衰竭/转换，从而提高对反转风险的事前区分？

这条线不是为了提前抄顶抄底，而是研究：

- parent-state deterioration；
- continuation hazard 与 reversal hazard 的相对变化；
- 哪些结构退化只是噪声，哪些能跨时期稳定。

## 5. 次级方向

### R4：统计状态极端

路径效率、波动率、频带振幅、事件密度、波浪时长等统计属性可能自己也有“均值”。

但必须区分：

> **统计量自己回归，不等于价格回归。**

只有当一个统计状态对价格 recovery/extension 或 parent-state transition 提供稳定增量信息时，才值得升级为策略机制。

### R5：相对价值 / 隔夜错位

跨指数、跨资产、隔夜 gap 等属于广义均值回归的一个子类。

本仓只把它作为框架中的一个案例/兄弟专题，不应因为已有较成熟研究就把整个项目重新缩回这一条线。

## 6. 研究节奏

本仓的角色是**方向发现器**。

第一阶段采用“广而浅”原则：

1. 每条路线只允许很小的候选预算；
2. 优先使用相同数据、相同尺度语言、相同评价方式；
3. 先验证现象和机制，不先优化交易收益；
4. 每条线都必须允许被关闭；
5. 三条主线至少各完成一轮可比较浅测后，才允许把最强方向交给专门身份深挖。

禁止：

- 一个方向连续几十轮细调，而其他方向尚未得到同等浅测；
- 失败后不断增加过滤器直到成功；
- 用 trading PnL 挑 recognizer / parent-state formula；
- 把已消费年份重新称 fresh；
- 因为某个统计量自己很稳定就自动当成价格 alpha。

## 7. 因果与证据治理

所有后续路线继承现有两浪项目最严格的因果规则：

- 只使用当时已经确认的波形/父结构；
- candidate pivot 不等于 confirmed pivot；
- appended future rows 不得重写已确认历史；
- 结构状态必须带产生/生效时点；
- 同一根 K 线内高低顺序未知时不得伪造路径；
- 算法自己生成的标签不是 morphology ground truth；
- 数据分区和审计角色必须在结果前冻结；
- 失败、样本不足和 unresolved 结果都要保留。

## 8. 现有 v0.6.17 如何继续

v0.6.17 是 M0 的一个前沿测量任务：验证 session-aware information-set bounds 在 authoritative DataHub source surface 上的 coverage/tightness。

它继续按原冻结协议执行：

`full local Stage 1 pytest/conformance -> authoritative support topology -> price-blind bound registry -> oracle replay -> cloud review`

但其状态为：

`M0 specialist pending / does not block broad program preanalysis`

只有当某项策略结论明确依赖“v0.6.17 morphology/measurement 已被接受”时，才必须先等 M0 闭合。

## 9. 当前执行阶段

接下来不继续发明 v0.6.18/v0.6.19 去无限完善 measurement。

当前仓库级 next action 是：

1. 冻结广义反转的公共 measurement vocabulary；
2. 给 R1/R2/R3 分别写 results-blind 浅层 preanalysis；
3. 盘点现有 2015-2020 数据和已发布的两浪因果 artifacts，选择三条线都能公平使用的最小数据面；
4. 在不声称 fresh OOS 的前提下，做第一轮可比较机制筛选；
5. 再决定谁值得进入专门深挖身份。

M0 v0.6.17 formal replay 可由本地 authoritative-source 执行链并行完成。

## 10. 权限边界

本白皮书不授予：

- FactorLab registry mutation；
- Layer 4 交易执行；
- paper trading；
- production；
- fresh-OOS 结论；
- PnL 驱动参数选择。

本阶段只能形成：

- 测量规范；
- 机制证据；
- 失败/暂存结论；
- 值得交接给专门研究身份的候选方向。
