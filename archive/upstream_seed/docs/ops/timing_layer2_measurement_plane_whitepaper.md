# Timing Layer 2 Measurement Plane V2 白皮书

状态：Current @2.3 / causal provider and offline material split  
合同：[`timing_layer2_measurement_plane@2.3.json`](timing_layer2_measurement_plane@2.3.json)  
计划：[`../user/timing_layer2_measurement_plane_v2_execution_plan.md`](../user/timing_layer2_measurement_plane_v2_execution_plan.md)  
权限：测量用途；无策略、参数、路由或生产权

## 当前裁决

Layer 2不是单纯的属性时间序列仓库。当前它只允许四类明示身份：

1. `causal_feature_provider`：当下市场属性和下一阶段属性的因果预测卡；
2. `offline_target_or_research_material`：未来属性标签、oracle或回溯图谱，不得当运行时feature；
3. `definition_compatibility_discovery`：定义、旧路径、目录和兼容入口，不得冒充causal provider；
4. `migrated_to_layer3`：需要具体strategy/tool效果的研究。

`tool_conditioned_relationships`和`tool_attribute_relationship_maps`已从Layer 2撤出，迁入
Layer 3 `StrategyConditionalEffectResearch`。去掉具体策略/tool名称后问题不再成立，就不是
Layer 2。

Phase A历史17资产分母中，只有群体相关时序达到当时`ready`定义；15个为
`partial`，Cloudridge旧日线属性为`compatibility`。当前@2.3保留这些质量裁决，
但不再把具体tool条件效果计入Layer 2 causal provider。

Phase A 不读取策略收益，不新增指标。它完成：

1. `Layer2MeasurementCoordinate@1.0`；
2. 17/17 能力矩阵；
3. Layer 1 DataHub 墙钟权威与 shifted-session 唯一例外；
4. 实际属性池 current pointer/source 数对账；
5. Layer 2 输出禁用字段与 authority 门。

## current 对账 incident

机器 current 指向 `snapshot-13ad9f2949d66ccf`，其 catalog 当前含 74 个 source。
共享入口仍分别记录 63、69 个 source 和旧 `snapshot-d2b8282253fcf2fe`。V2 合同
以机器指针与 catalog 重算为当前事实，并把共享文档更新留给控制器合流；不改写旧
snapshot，也不把 source 数漂移解释成科学结果。

## 公共坐标

每条测量必须绑定载体、真实 Layer 1 view、物理期限、观测时点、可用时点、source
receipt、估计器版本、成员版本、缺口政策和质量状态。FactorLab 墙钟 bar 权威默认
非法；唯一例外是显式 `shifted_session_clock` 研究载体。

公共坐标解决三个旧问题：同名窗口物理时长不同、年度汇总冒充逐棒状态、策略脚本
自行解释缺口和可见时点。

## 下一阶段

Phase B 先逐棒展开已有可精确对账公式，不新增收益驱动阈值。年度统计中没有自然
逐棒身份的字段必须用显式物理上下文窗升版，不能静默复用年度名字。

## Phase B1 结果

`timing_layer2_pit_core@1.0` 已逐棒发布36个2/4/8/16物理日公式和6个K线形态
充分统计。30个可由年度 reducer 精确还原的旧核心字段最大绝对误差不超过
`1e-15`；前缀不变和连续段 reset 通过。

冻结公式对两点窗口不定义 signed OLS t，因此逐棒 `ols_slope_t_signed_2d` 为
unavailable；旧年度 `_safe_median` 把空集映射为0，仅作为兼容 reducer 保留。
V2没有伪造两点t统计量。`no_buffer_reversal_rate`和`bipower_jump_share`仍保持
年度身份，等待B2显式上下文窗合同。

## Phase C 基础结果

`timing_layer2_extended_measurements@1.0` 已发布三个严格因果族：量价/流动性、
路径生命周期和同刻横截面结构。固定5/20/60物理日是测量菜单，不是策略选中的
唯一窗口；消费者可同时读取，不得由Layer 2选winner。

成交额变化近乎常数时，价格—成交额滚动相关不可识别。实现将pandas可能产生的
正负无穷统一转为NaN，不以0伪装“零相关”。`reclaim`是收回边际测量，不是
`claim`认领动作；输出禁门按字段token而非模糊子串判断。

当前只发布K线可得量价，不读取真实盘口OFI/depth。第二凝结核研究仍在主控验收链，
本阶段只提供广度、尾部、集中度和可选群体纯度原语，没有继承锚点日期或winner参数。

## Phase D 结果

`timing_layer2_phase_relationship@1.0` 已发布分量相位年龄与滚动载体关系。分量值
由调用者提供的因果IIR/Haar/brickwall/论文核产生；V2只测斜率、加速度、方向、
phase age、zero-cross age和RMS能量，不复制滤波公式。

所谓“主导周期”只用连续能量加权周期与集中度表示，不输出离散频段winner。载体
关系按canonical pair和20/60/120物理日同时输出双向beta、双向残差、双向lag1相关、
相对强弱与共同左尾频率；不选择领先载体。动态群体消费时必须绑定
`membership_version`。

## Phase E/F/G 结果

Phase E发布通用多载体Future Path Provider V2：V1三类目标保持支持，新增路径
低效和jump burden两个实验目标。训练前缀与后续校准块物理分离，q10/q50/q90
来自校准残差经验分位；最新特征不完整时abstain，不填值、不预测方向。新目标只
获得基础设施身份，尚无经济有效性或策略权。

Phase F为REAKA、绿波、Residual Risk-Off、CSI1000 LAT和T0发布只读deep-copy
adapter，数值不变换、不带阈值、不修改任何策略模块。三份加法overlay已发布
到属性池内容寻址current（具体ID从`current.json`读取），共84个source；旧snapshot未覆盖。

Phase G以`timing_layer2_measurement_plane@2.1`完成原计划版本继承；@2.2新增期权IV/HV。
当前@2.3不改任何测量公式，只完成causal/offline/兼容/策略效果分层。第二凝结核仍未在
缺少主控验收时晋升；Future V2实验目标仍标unvalidated。这些诚实限制不妨碍
测量基础设施完成，也不得被解释成策略失败。
