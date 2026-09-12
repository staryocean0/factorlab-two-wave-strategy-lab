# 项目级 K 线市场状态地基白皮书

> 四层归属：Layer 2 K 线测量。A0–D 是可复用事实，不属于策略 OS，也不授予
> 路由、参数或生产权限。

## 当前阶段

当前已完成 **A0 契约门**、**A1 日线单频率竖切**、
**A2 1d+60m 因果核心完整版**、**B 事后历史地图/严格因果相似期**、
**C1.2 具体择时工具字典**、**C1.3 多尺度时间稳定性地图**和
**D Baylum 统一日更发布**。A2 已建立云脊指数 1d+60m 完整属性、严格因果
在线状态、可信 checkpoint、全量/增量等价、不可变版本目录、双摘要和原子 internal
`current`；B/C 分别建立隔离的历史研究产品和方法证据产品。D 把 CloudRidge
levels 与同源市场状态包先暂存、再由父仓写入唯一统一发布回执。

C 仍然只是方法选择的研究先验，`production_authority=false`，不产生买卖信号、
不自动切换策略。D 只授予数据发布权，不授予策略生产权。

地基另设[择时经验公式注册层](market_state_empirical_formula_whitepaper.md)，用于保存
已经能写成可复算关系、同时具备适用边界和反证、但尚不是因子或路由的研究知识。
首条登记短周期跨尺度相对换手凹坑；机器入口为
`src/factor_lab/market_state/empirical_formula_registry.py`。该层与Feature/Factor
Library、13工具公式/参数注册表分离，四类权限全部为`false`。

R2 之后另设逐工具条件关系中间层，用同一工具的镜像参数、八个样本外年份和
层级多重检验认证“属性变化—参数方向”。其权威入口为
[专项白皮书](market_state_tool_conditioned_relationship_whitepaper.md)与
[工作流](../user/market_state_tool_conditioned_relationship_workflow.md)；
当前单因子证据按 70/80/90/95% 条件命中率分层，承认未剥离因素的干扰，
但同时要求最低样本量和跨折跨年复现；完整参数方向仍须镜像两侧成立。
已执行结果为 1 个独立单侧条件关联、0 个完整镜像规律。
首个低自由度多因子状态机原型已证伪原始因子平铺投票：两个频谱
激活代理 Spearman 为 `0.7116`，联合模型相对最佳单因子的样本外
边际为负。该结果不否定多因子，而是把下一层的数学对象收紧为
“机制块内压缩 + 机制块间交互”。
关系证据仍不等于动态调参、工具路由或生产授权。

## D 统一发布合同

D 的共同身份不是只比较日期，而是同时绑定：

- 精确 DataHub `source_dataset_version`、源内容摘要和源 watermark；
- `carrier_id`、`carrier_definition_version`；
- 由本批 CloudRidge 60m levels 实际计算的 carrier watermark；
- CloudRidge levels 文件 SHA256，以及市场状态确实由同一文件派生的证明。

CloudRidge stage 会把 levels 复制到以内容寻址的 stage 目录，不引用可能被下一轮
日更覆盖的 `output/.../current` 文件；若同一 stage id 已存在但字节不同，立即失败。
统一回执核验 stage manifest 和组件文件两层 SHA256，生产 loader 还会重算 A2
inventory 的逐产物字节/语义摘要。

发布顺序固定为：

```text
stage CloudRidge levels
→ 从同一 levels 派生 1d+60m panel 并构建/验证 A2
→ stage market-state 并核对共同身份/输入字节
→ 写不可变 Baylum release receipt
→ 原子推进唯一 Baylum current
→ 才允许发布 CloudRidge / Timing / Risk-Off 结果
```

父仓唯一数据发布权威为：

```text
../output/baylum-release/versions/<release_id>/manifest.json
../output/baylum-release/current/manifest.json
```

FactorLab 的 `output/market-state-foundation/current/manifest.json` 从 D 起只是
构建阶段指针，`production_authority=false`。生产消费者必须通过
`BaylumReleaseLoader` 解析父仓 `current`；直接把 FactorLab internal current
当生产回执会失败。统一回执本身也固定
`strategy_production_authority=false`，策略授权仍走各自生产门。

统一发布使用 `fcntl.flock` 串行化，版本目录内容寻址且不可覆盖；current 经同文件
系统临时文件、`fsync`、`os.replace` 和父目录 `fsync` 原子推进。构建、核验、回执
写入、版本发布、current 提交前后均有故障注入测试：提交前失败保持旧 current，
提交后失败留下完整的新 current，原命令重跑复用相同 release id。

`--check-only` 对比 DataHub 当前精确 1m qfq dataset version/watermark 与统一回执。
即使尾日相同，只要源版本或水位推进，也报告 `market_state_stale` 并要求重建，
不得用旧市场状态冒充最新数据。

### D 首次正式发布证据（2026-07-29）

- DataHub：`bars_cn_a_1m_qfq_canonical_deep_value_domain_repair_20260628`，
  watermark `2026-06-24T15:00:00Z`；
- CloudRidge stage：`cloudridge-stage-b1f3316835dd6a19`；
- A2：`market-state-a2-b40a83985466e8a0`；
- market-state stage：`market-state-stage-e91e584917180237`；
- Baylum release：`baylum-release-c7c2a73b5b5510f9`，
  semantic digest
  `sha256:c7c2a73b5b5510f9dd434ca7157283772c7619056c16cf7bc7fec5ca4b4331da`。

首次发布 `reused_existing=false`，同参重跑 `reused_existing=true`；生产 loader
完成 A2 inventory 深验，父仓 `--check-only` 返回 `status=ready`、
`fresh=true`、`action=no_new_data`。

## A2 实现合同

A2 current 的权威频率固定为 `1d + 60m`。已发表的 1d/60m/15m 包仍是官方会话旧口径只读对照；若做双尺度过渡，按 [`unified_offset_data_and_backtest_whitepaper.md`](unified_offset_data_and_backtest_whitepaper.md) 的可选菜单另出 14:00/14:30 或更细相位版，不原地改这个包。，完整 V1 包含 34 个物理
属性，每个属性在 `20/60/120` 交易 session 尺度上计算；两个频率共物化
204 条 `MarketAttributeSpec`。日线和 60m 使用不同 FeatureSpec，但通过
`physical_attribute_id` 对应同一物理概念。

A2 的 N 日窗口是 N 个实际交易 session，不是 `N × 固定 bars/day`：

- 缺 bar 保持缺失，不用更早 bar 补数量；
- 节假日不计经济时间，半日市和日内状态按有效交易分钟计算；
- 已完成 60m bar 在其 timestamp 到达时立即可用，未完成 bar 不进入；
- EWMA 用有效交易分钟换算半衰，而不是默认每日固定根数。

checkpoint 同时绑定父 bundle、代码版本、配置摘要、状态政策版本和各
频率上游历史前缀摘要。只有严格尾部追加才允许 incremental；任一历史前缀改动、
代码/配置/状态政策改动都回退 full rebuild。候选包先完整验证，再用
`fcntl.flock + parent compare-and-swap + os.replace/fsync` 推进 current；
并发构建最多一个胜者。

A2 性能门为 `market_state_a2_budget@1.0`，详见
`ADR-027-market-state-a2-performance-budget.md`。它以 A1 正式包的输出吞吐、每输出行
峰值内存和每输出行产物字节为基线，不使用拍脑袋的绝对秒数。

## A2 正式 1d+60m 证据

2026-07-29 使用精确 DataHub 版本与代码提交
`5dd579f3ae7fc4a714c2e915cfa2aea674328a95` 完成正式全量构建：

- 日线源：`bars_cn_a_1d_qfq_canonical_20260626_sina_auto`，哈希
  `ee853b66bb41a8582041cc29ba64151688b86adc`；
- 60m 源：`bars_cn_a_60m_qfq_canonical_20260626_sina_auto`，哈希
  `fd2dbede44e7d85ba926611f484b206b644317f1`；
- 两个源均为 DataHub `READY`、质量分 95、重复数 0、消费者准入 `granted`；
- 正式不可变包：`market-state-a2-1256a9cc828dab35`；
- 语义摘要：
  `sha256:1256a9cc828dab35819f399cf91f3af123cdf2328f418e6a037762f0bf2dcae8`；
- 输入 4487 根日线和 17940 根 60m，生成 2287554 条属性及同数量在线状态；
- 日线属性 457674 条、60m 属性 1829880 条，逻辑键重复为 0，状态有效占比
  95.66%；
- 全量核心构建 818.42 秒，输出吞吐 5590.16 行/秒，高于冻结下限
  4768.69；产物约 91.80 MB，归一化内存与字节预算也通过；
- 独立验证入口复核 13 个产物、schema、文件摘要、语义摘要、质量门与性能门，
  结果 `valid=true`。

A2 的 synthetic hostile tests 另行证明：可信尾部追加的 incremental 与同输入 full
语义完全相等；历史前缀修订强制回退 full；并发 CAS 只允许一个合法父版本胜出。
B 必须绑定上述不可变父包，retro 产物不得反向进入 online loader。

## B 正式历史地图与因果相似期证据

2026-07-29 在当前 A2 正式父包上重新生成 B 研究包：

- B 不可变包：`market-state-b-90287580692ce6e8`；
- 语义摘要：
  `sha256:90287580692ce6e8d217eb34c50bdbba823f56e3e73424163958e33f98a2965c`；
- 父包严格绑定 `market-state-a2-b40a83985466e8a0` 及其语义摘要；
- `retro_segmentation_policy_v1` 逐属性维度生成 63864 个历史段，最短物理持续期
  5 个交易 session；每段带稳定 id、属性族、方向、强度、起止、持续期、主导轴，
  并明确 `causal=false / uses_future=true / data_mode=retro`；
- `similarity_policy_v1` 对 1d、60m 各输出 10 个当前相似期，窗口 20 个交易
  session；候选结束严格早于查询窗口开始，不含自身、重叠或未来；
- 相似距离先按 `physical_attribute_id` 收口重复尺度，再按属性族等权；缺失族按
  有效族重新归一，未填 0；7 个属性族均有 leave-one-family-out 敏感性记录；
- B manifest 只允许 `research / visualization / taxonomy`，送入 online、backtest
  或 live consumer 会硬拒绝；A2 online current 中没有 B 路径；
- 独立验证结果 `valid=true`，5 个产物逐文件摘要复核通过；同代码同父包复跑得到
  相同 bundle id/语义摘要并返回 `reused_existing=true`。

B 的历史地图可以用完整历史形成更清晰的事后章节，因此不能作为交易信号；只有
`market_state_similar_periods.csv` 使用 online 前缀事实，但它仍只是描述性参照，
不自动授权策略路由。

## C1.2 正式具体择时工具字典

### C1.2 口径修订

旧 C1.1 有两个真实缺口：13 个已发现工具中只有 10 个完成实证，三个原生
15 分钟工具被延期；时间上也只有一个发现段和一个审计段，单次跨期碰巧成立
仍可能被误记为稳定关系。C1.2 据此重写完成门；当前永久口径是本白皮书、
[市场状态工作流](../user/market_state_foundation_workflow.md)、机器 Schema、代码与测试，
不依赖一次性开发计划。

旧 C 包和 C1.1 包只保留为历史产物，不再代表当前工具字典完成态。C1.2 已在
当前 A2 父包上用截至 2020 年的有界数据重新构建：

- C1.2 不可变包：`market-state-tool-c-d643f9a74fbac169`；
- 语义摘要：
  `sha256:d643f9a74fbac16990e6be589689741914109671d41196ff446574040da3b1f3`；
- 父包严格绑定 `market-state-a2-b40a83985466e8a0` 及其语义摘要，父包推进后
  旧 C fail closed；
- `tool_source_inventory.json` 独立发现 13 个具体工具，registry 登记 13 个，
  benchmark 执行 13 个，证据覆盖 13 个，`deferred=0`；
- 十个通用工具仍直接执行冻结的 1d/60m 实现；频率选择性布林、巴特沃斯低通
  残差包络、V57 因果非对称弧形状态空间包络直接调用各自原生 15 分钟代码，
  不以日线、60 分钟或替代公式冒充；
- 其中频率选择性布林有原生通道决策；后两者的原始合同明确是
  `geometry_only`，因此只在原生几何上冻结同一条“中轨方向”观察探针，不虚构
  上下轨交易规则。其证据回答的是这条透明探针，不把几何工具误称为完整策略；
- 15 分钟属性和状态使用与 A2 同一套严格因果公式，由有界文件
  `cloudridge_15m_levels_through_20201231.csv` 生成；在线状态的滚动次序统计
  优化已与原逐窗公式逐值回归等价；
- 每个工具同时从做多捕获和空仓规避两个职责观察，并计算每棒净收益、正收益率、
  盈亏比、换手、完整交易胜率、完整交易盈亏比和交易期望；
- 发现段固定为 2009—2014；公式、方向和阈值冻结后，分别在 2015—2016、
  2017—2018、2019—2020 三个互不重叠区间独立验证；
- 一条关系只有在发现段成立且三个验证段 `3/3` 均保持方向、最低强度、年度块
  一致性、关系形状和样本门时，才允许标记 `supported`；通过一段或两段均不算；
- `tool_state_affinity_fold_evidence.parquet` 保存每条关系 × 每个验证段的
  样本数、三桶值、效应、方向、形状、通过状态和失败原因，摘要表只做对账；
- 共生成 32,844 条关系和 98,532 条逐折证据；960 条通过 3/3 门，
  31,884 条如实保留为 rejected/unknown；
- 独立 validator 复核 10 个产物、13/13 工具覆盖和逐折摘要，结果
  `valid=true`；最晚研究日期 `2020-12-31`，
  `blackbox_opened=false`、`parent_fresh=true`；
- 旧的 2015—2020 `audit_*` 列和 `method_*` 文件只保留兼容投影，不能替代
  三段逐折证据，也不能代表全部具体工具。

C1.2 仍采用“先定性、后定量”，但把稳定性门从一次审计提升为三次独立复现。
发现段先比较属性 `low / normal / high` 状态下的真实绩效并冻结方向；验证段不
重新选择公式、方向或阈值。线性关系和 U 型/倒 U 型分别验证，不能把非单调关系
压成一个正负号。

任何 supported 行都是方向证据，不是独立因子。`noise_ratio` 与
`path_efficiency` 等互补属性、同一物理属性的不同尺度可能相关，不能直接计票
生成路由。`rejected_formula_not_rejected_factor=true` 只否定当前固定
benchmark/尺度/职责公式，不宣称该物理属性永远无效。

### C1.2 冻结证据与当前十五工具视图的边界

C1.2 的13工具、32,844条关系与其摘要保持原样，不能为了追加工具重写历史证据。
当前 `tool_registry_v1_5` 从V1.4十四工具前缀追加 LAT 通道
`lowpass_bandpass_lat_channel`，并在
[组合优先级白皮书](market_state_timing_priority_composition_whitepaper.md)中保持双侧
空瀑布；其首个三级双向增量见
[择时策略路由白皮书](market_state_timing_strategy_routing_whitepaper.md)。它尚未取得
C1.2关系认证、固定能力证书或路由权。历史V1.3跳变工具的
独立责任已撤销，因此不进入现役十五工具视图。LAT 六桶是方法锁，不是新的注册身份。

## C1.3 多尺度时间稳定性地图

C1.2 的三折门仍不足以代表权威时间稳定：两年合并后的同向可能掩盖单年反向，
自然年边界也可能掩盖错位年度的反向。C1.3 因而把 2009—2020 的全部完整窗口
作为地位相同的复现实验，冻结：

- 对齐4年/3年/2年/1年/半年；
- 4月、7月、10月起算的错位1年；
- 4月起算的错位半年。

共 9 套切分、105 个完整窗口。窗口存在嵌套和重叠，只用于切分敏感性压力测试，
不冒充 105 份独立样本。每条关系同时审计线性与曲线候选；结果分为全窗口稳定、
跨切分稳定但有空缺、稀疏同向、方向冲突和无实质信号，样本不足另行保存。

真实计算形成 3,447,654 条逐窗口明细和 65,688 条候选关系摘要：

- 不可变包：`market-state-tool-stability-51536b0fcb91dee8`；
- 语义摘要：
  `sha256:51536b0fcb91dee898a6fcae2677338e5234d5a03b301d337ce88af61239114f`；

- 全窗口都有实质信号且同向：0；
- 9 套切分均复现、同向但有空缺：31 行；
- 稀疏同向：3,560 行；
- 实质方向冲突：47,587 行；
- 无实质信号：14,510 行。

31 行最高可用候选去除 turnover 在两个职责下复用同一序列的机械重复后，只剩
20 条不同经济关系，其中直接涉及绩效的只有 9 条。C1.2 原 960 条 supported
中，只有 12 行、去重后 6 条进入该层，且全部只是换手关系；17 行降为稀疏同向，
931 行出现方向冲突，没有一条旧绩效关系进入最高可用层。

因此 C1.2 `supported` 已降级为历史候选，C1.3 成为当前时间稳定性查询层。
但 C1.3 仍明确 `conditional_independence_tested=false`：时间稳定不能剥离
路径效率、噪声比、趋势强度等相关属性的混杂，不能自动投票、路由或调参。
详细原理见
`docs/ops/market_state_tool_temporal_stability_whitepaper.md`。

## C2 工具参数响应层

R0 完整画像/研究合同见
[`market_state_tool_capability_contract_whitepaper.md`](market_state_tool_capability_contract_whitepaper.md)；
R1 固定能力见
[`market_state_tool_fixed_capability_whitepaper.md`](market_state_tool_fixed_capability_whitepaper.md)；
第一代 R2 根状态轴见
[`market_state_tool_root_axis_audit_whitepaper.md`](market_state_tool_root_axis_audit_whitepaper.md)。

C2/R3 已在 2009—2020 完成。三条根状态中，IIR 空仓画像因 R1
无稳定固定回退而不进入搜索；Haar 空仓与布林做多各用冻结的 9 点
参数面完成 4 次扩展式外层验证。两项实验都是 0/4 正增益折，因此
`certified_dynamic_count=0`，当前状态不具备调参权。

预注册合同保留在
`docs/ops/market_state_tool_parameter_response_c2_preview.md`，正式结果见
`docs/ops/market_state_tool_parameter_response_whitepaper.md`。R4 随后使用 R1
已认证的固定画像完成同角色直接胜负：9 个画像、16 个对、
22 个根轴实验和 21,771 个完整分歧事件中，没有跨期稳定排名
反转通过。因此不强行创建 R5 路由器，回退 R1 固定画像。详细见
`docs/ops/market_state_tool_pairwise_battle_whitepaper.md`。

## R2F 公式机制桥与第二代 R2 已执行验证

第一代 R2 解释单工具的绝对表现，R3/R4 却需要解释参数或工具之间的
相对损失差，目标不一致。R2F 因而从 13 个工具的实现公式倒推 11 类机制，
登记 43 条机制—因子映射。去重后是 34 个唯一因子：21 个已有属性和
13 个 `proposed` 待建因子。

第二代 R2 的永久验证合同已冻结并完成首次执行：

1. 以完整分歧/持仓事件为独立样本；
2. 以 `D_e^(A,B) = U_e(A) - U_e(B)` 为相对目标；
3. 先做支持度审计，再做机制内联合与条件增量验证；
4. 先定性冻结单调/凸/凹/阈值形状，再在训练内定系数、幂次和阈值；
5. 仅允许公式、量纲或因果链预注册的交互；
6. 用四个扩展式外层折覆盖 2013—2020，所有选择只在各折训练内；
7. 6 个月/1 年/2 年错位窗只做压力测试，不冒充独立票或选模依据；
8. 机制家族是多重检验单位，不把 43 条映射当作 43 个独立发现；
9. 允许平局或 model confidence set，不强选历史冠军；
10. 2021—2026 只能在公式、门槛、交互和停止门全部冻结后一次聚合打开。

详细原理见
[公式机制白皮书](market_state_tool_formula_mechanism_whitepaper.md)，执行口径见
[公式机制工作流](../user/market_state_tool_formula_mechanism_workflow.md)。

真实开发又补出“已有模型之后”的独立中间层：当前模型必须先冻结，原始参数
效用差、条件切换增量与可修复遗憾不得混用；下一因子必须来自最大未解释公式
Gap，且因子与全局加分、状态机、单向 Override、Veto 等动作几何分别裁决。
该层使用 `market_state_tool_formula_residual_attempt@1.0` 固化基线、目标、分支、
数据新鲜度和失败指纹，并由
`market_state_tool_formula_residual_failure_registry@1.0` 加锁保存项目级失败历史，
仍不授予动态调参、工具路由或生产权限。

四类频谱带通工具的 33 个公式候选属性另有独立测量层：
[频谱工具 K线属性测量层白皮书](market_state_spectral_kline_attribute_measurement_whitepaper.md)
与
[工作流](../user/market_state_spectral_kline_attribute_measurement_workflow.md)。
其参数、尺度与后续研究外键由
[参数—属性跨轮基础设施白皮书](market_state_cross_round_infrastructure_whitepaper.md)
和
[工作流](../user/market_state_cross_round_infrastructure_workflow.md)
统一约束；任何未映射广义参数或未绑定实验的假说都失败关闭。
该层完成 14 个既有属性复用审计、19 个新增属性实现、严格因果尺度换算和
标准研究底表，但 108 条关系全部保持待实证，不能越权改写为有效因子。

公式先验与设计包继续保持 `market_data_rows_read=0`、
`research_executed=false`；独立实证包已使用 2009—2020 完成 554 组比较和
282,034 个完整分歧事件。0 个因子达到跨配对支持，0 个机制通过 11 家族
多重检验，44 个工具对总公式只构成局部候选。机制有效性、动态参数、
工具路由和生产权仍全部为 `false`，2021—2026 读取行数为 0。

## A1 正式 DataHub 竖切证据

2026-07-29 已通过本地 DataHub HTTP 正式服务闭合真实输入缺口：

- HTTP：`http://127.0.0.1:8400`，health 与精确 dataset 请求均返回 200；
- 精确源版本：`bars_cn_a_1d_qfq_canonical_20260626_sina_auto`；
- DataHub 状态 `READY`，内容哈希
  `ee853b66bb41a8582041cc29ba64151688b86adc`；
- DataHub 质量分 95、重复数 0、质量报告空值数 0，水位
  `2026-06-26T15:00:00Z`；
- A1 消费者准入：
  `factorlab_market_state_bars_source_admission@1.0 = granted`；
- 正式不可变包：`market-state-a1-df9dd78dfbf6e6f7`；
- 语义摘要：
  `sha256:df9dd78dfbf6e6f7ad14b4b4f1d4c7108ccc2e142e31be79d266a2f03debcdc8`；
- 输入 4487 根日线，生成 148071 条属性与 148071 条在线状态；
- 首次全量构建 24.84 秒、180.63 输入行/秒；质量门通过，逻辑键重复为 0，
  在线状态有效占比 95.71%；
- 11 个不可变产物逐文件/语义摘要复验通过；同代码、同输入复跑返回
  `reused_existing=true`，bundle id 与语义摘要完全不变。

这些证据只闭合 A1 研究地基，不产生策略切换或生产授权。

## A1 代表属性与尺度

A1 仅用已完成日线 close，覆盖方向、路径、幅度、波动、尾部不对称和记忆：

- BDCI、BCI imbalance、WBI；
- path efficiency、mean absolute return；
- realized volatility、volatility-of-volatility；
- 上/下行半波动、尾部能量集中度；
- lag-1 return autocorrelation。

测量尺度固定为 `fast_20d / medium_60d / slow_120d`，`structural_252d`
只是严格 `t-1` 标准化参考。旧 `100d` 只能叫 `legacy_100d`，不得冒充
`slow_120d`。A1 不再生成“属性窗口 × 均线窗口”全笛卡尔积。

## 严格因果在线状态

`state_policy_v1` 的数值全部收口于版本化配置：

- 当前值只与前 252 个已完成交易日比较，最少 120 个有效历史；
- 位置低于等于 0.20 进 low、高于等于 0.80 进 high，退出用 0.25/0.75
  滞回；
- 20d/60d 半衰 EWMA 差用历史 IQR 标准化，IQR 退化时回退 MAD；
- 状态最少驻留 5 个有效交易日，无效观测不累积年龄；
- `confidence` 是历史完整度、数据完整度和边界距离三者的最小值，不从策略收益
  反推。

向输入追加未来 K 线不能改变既有属性或在线状态前缀。日线的 `available_at`
不早于当日 15:00（Asia/Shanghai）。

## 不可变构建与双摘要

A1 只允许 full build。版本目录为：

```text
output/market-state-foundation/versions/<bundle_id>/online/
```

Parquet/CSV/JSON/Markdown 产物在 `artifact_inventory.json` 中分别记录：

- `file_sha256`：实际字节完整性；
- `semantic_digest`：固定列、dtype、行序、NaN 语义后的内容幂等性。

`performance_baseline.json` 记录参考硬件、输入/输出行数、全量耗时、吞吐和峰值内存；
它只是 A2 冻结预算前的实测基线，不是拍脑袋性能门。`current/manifest.json`
通过同文件系统临时文件、flush/fsync、`os.replace` 和父目录 fsync 原子推进。

2026-07-29 用实际云脊 1d CSV（2008-01-07 至 2026-06-26）测得核心计算基线：
4487 根输入生成 148071 行属性和同数量状态，x86_64/Python 3.11.11
下耗时 16.91 秒，约 265.31 输入根/秒，峰值 RSS 平台计数 333108。
该数值是现有机器的核心 pipeline 实测，不是冻结 SLA；正式包的全链路数值
由每个包内的 `performance_baseline.json` 自身记录。

## 唯一权威

`FeatureSpec` 是公式、数据源、频率、PIT/前瞻风险、`available_at` 和版本的唯一
权威。`MarketAttributeSpec` 只保存：

- 精确 `feature_id + feature_version` 引用；
- 同一物理概念跨频率共享的 `physical_attribute_id`；
- 属性族、测量尺度、状态平滑尺度、标准化参考和状态政策版本。

`MarketAttributeSpec` 不得复制公式、数据源或 PIT 规则。一个 `FeatureSpec` 只表示
一个确定频率；1d 与 60m 必须使用不同 `feature_id`。历史 bundle 保存精确
FeatureSpec snapshot 及语义摘要，重放时不得解析“当前最新版本”。

## 逻辑身份

属性观测的逻辑键为：

```text
carrier_id
+ carrier_definition_version
+ bar_frequency
+ observation_time
+ feature_id
+ feature_version
+ measurement_scale_id
```

`available_at` 是必填时间元数据，但不属于逻辑键。可用时间政策改变时必须生成
新 bundle，不能在同一表中追加一个重复逻辑观测。

状态逻辑键在属性键上增加：

```text
state_smoothing_scale_id
+ normalization_reference_id
+ normalization_policy_version
+ state_policy_version
```

## DataHub 输入冻结

A0 只接受显式请求的精确 DataHub dataset version。输入必须同时满足：

- 返回版本与请求版本完全一致；
- `state=READY`；
- 非空 `dataset_hash` 或等价内容哈希；
- 非空 watermark；
- 可回查的 DataHub manifest 与 quality report 引用；
- DataHub manifest 与 quality report 的版本、质量分相互一致；
- 质量分不低于 90、重复数为 0、质量报告中的空值数为 0；
- 通过
  `factorlab_market_state_bars_source_admission@1.0`
  消费者级准入。

DataHub 的正式合同刻意不在通用 dataset endpoint 发布
dataset-global `research_ready`；研究就绪是按消费者合同派生的结论。A1
不得伪造这个布尔值，也不得把 `READY` 单独升级成研究授权。A1 保存的是
FactorLab 市场状态消费者依据 DataHub 正式 manifest 与 quality report 得出的
准入决定，且仍然 `production_authority=false`。

固定测试证据为
`tests/fixtures/market_state/datahub_ready_dataset_v1.json`。它是合同 fixture，
不是正式市场研究数据。

## online 与 retro 物理隔离

online、retro 与 evidence 使用不同 schema、manifest 类型和 loader：

| 数据面 | uses_future | 允许用途 |
|---|---:|---|
| online | false | research、backtest_feature、live_feature |
| retro | true | research、visualization、taxonomy |
| evidence | 仅评估期使用未来收益 | research、tool_selection_prior |

online manifest 不允许出现 retro/evidence 引用；retro 或 evidence manifest
送入 online loader 必须硬拒绝。三类清单均为 `production_authority=false`。

## 代码与证据

- 契约：`src/factor_lab/market_state/contracts.py`
- 物理 loader：`online_loader.py`、`retro_loader.py`
- A1 属性：`src/factor_lab/market_state/attributes.py`
- 因果标准化/状态：`normalization.py`、`online_state.py`
- 不可变发布：`bundle.py`
- B 历史研究：`retro_map.py`、`similarity.py`、`bundle_b.py`
- C1.2 工具本体/基准/证据：`tool_registry.py`、
  `tool_benchmark_adapters.py`、`tool_affinity.py`、`tool_bundle_c.py`、
  `tool_dictionary.py`、`evidence_loader.py`
- R2F 公式机制/已执行验证：`tool_formula_mechanisms.py`、
  `tool_mechanism_validation_contracts.py`、`tool_mechanism_features.py`、
  `tool_mechanism_validation.py`、`tool_formula_residual_contracts.py`
- D 暂存/统一回执/生产解析：`src/factor_lab/market_state/release.py`
- 构建/验证 CLI：`scripts/build_market_state_foundation.py`、
  `scripts/build_market_state_foundation_a2.py`、
  `scripts/validate_market_state_foundation.py`、
  `scripts/build_market_state_foundation_c.py`、
  `scripts/validate_market_state_foundation_c.py`、
  `scripts/build_market_state_tool_formula_mechanisms.py`、
  `scripts/validate_market_state_tool_formula_mechanisms.py`、
  `scripts/build_market_state_tool_mechanism_validation_spec.py`、
  `scripts/validate_market_state_tool_mechanism_validation_spec.py`、
  `scripts/build_market_state_tool_mechanism_validation.py`、
  `scripts/validate_market_state_tool_mechanism_validation.py`、
  `scripts/validate_market_state_tool_formula_residual_attempt.py`、
  `scripts/stage_market_state_baylum_release.py`、
  `scripts/publish_baylum_release.py`、`scripts/validate_baylum_release.py`
- 唯一 FeatureSpec 版本解析：
  `src/factor_lab/factor_engine/feature_library.py`
- JSON schema：`docs/schemas/json/market_state_online_manifest@1.1.json`、
  `market_state_online_manifest@2.0.json`、`market_state_checkpoint@1.0.json`、
  `market_state_artifact_inventory@1.0.json`、
  `market_state_performance_baseline@1.0.json` 与
  `datahub_pinned_dataset_identity@1.1.json`、
  `market_state_evidence_manifest@1.0.json`、
  `market_state_tool_evidence_manifest@1.2.json`、
  `market_state_tool_formula_mechanism_bundle@1.0.json`、
  `market_state_tool_mechanism_validation_spec@1.0.json`、
  `market_state_tool_mechanism_research@1.0.json`、
  `market_state_tool_formula_residual_attempt@1.0.json`、
  `market_state_tool_formula_residual_failure_registry@1.0.json`、
  `baylum_release_receipt@1.0.json`
- 单元测试：`tests/unit/test_market_state_contracts.py`、
  `tests/unit/test_market_state_affinity_contract.py`、
  `tests/unit/test_market_state_tool_formula_mechanisms.py`、
  `tests/unit/test_market_state_tool_mechanism_validation_contracts.py`、
  `tests/unit/test_market_state_tool_mechanism_features.py`、
  `tests/unit/test_market_state_tool_mechanism_validation.py`、
  `tests/unit/test_market_state_tool_formula_residual_contracts.py`、
  `tests/unit/test_market_state_tool_authority_consistency.py`、
  `tests/unit/test_feature_library.py`

所有机器 JSON 必须带 `field_labels_zh`。A/B/C 已在 FactorLab 内独立验收；D
只在这些前置条件全部通过后，才把本批数据提交给父仓唯一发布回执。

跨股票面板的全市场/制造业群体同步水平、同步离散度和共同模式占比不属于 A2 单载体 K 线属性，以独立增量包实现。权威入口见[群体相关性市场状态白皮书](group_correlation_market_state_whitepaper.md)和[执行工作流](../user/group_correlation_market_state_workflow.md)。

## 永久权威与渐进式披露

当前口径必须由文档、白皮书、代码、测试和工作流五位一体地共同实现。
一次性执行计划可记录开发过程，但不是当前能力、执行口径或生产权的真源。

渐进式阅读链固定为：

```text
ai-readme.md
  → README.md / docs/00-index.md
    → docs/user/README.md / docs/ops/README.md
      → market_state_foundation_workflow.md / whitepaper.md
        → 具体属性、工具、公式机制与验证专题
          → 代码 / Schema / 脚本 / 测试
```

一级入口只说明项目边界和二级去向，不复制低层公式、文件清单或
研究数字。底层权威的一致性由
`tests/unit/test_market_state_tool_authority_consistency.py` 强制。
