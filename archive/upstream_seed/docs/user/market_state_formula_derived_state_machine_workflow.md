# 市场状态13工具公式派生—联合状态机 V3 工作流

> 四层拆分：公式倒推/结构依赖合同属于 Layer 3a；联合状态机研究属于 Layer 3b。
> 3b 可被更完整 Layer 2 测量取代，不是长期底座；既有公式与状态拓扑未改。

版本：V3.0
状态：**实现候选；只有确定性机器重建通过，且外部流程确认审阅与测试无阻断项后，才可宣布当前权威**
适用范围：13 个已登记市场状态工具的无标签公式派生、有界联合机制研究与冻结规则验收。

> 本文是 V3 候选用户工作流；机器验收只由 [V3 基础设施验收证据](../ops/evidence/market_state_formula_derived_infrastructure_v3_acceptance_20260731.md) 中可由当前项目代码重复计算的自洽证据决定。代码、架构审阅和完整测试仍是发布流程的人工/代理停止门，但仓库内文本不冒充独立机器证明。五类实证先行结果见 [五类联合状态机证据](../ops/evidence/market_state_formula_derived_five_family_pilots_20260731.md)，V2 只读基线见 [V2 跨轮基础设施验收证据](../ops/evidence/market_state_cross_round_infrastructure_acceptance_20260731.md)。数学边界、决策理由和对外分派格式分别由 [统一数学白皮书](../ops/market_state_formula_derived_state_machine_whitepaper.md)、[ADR-029](../adr/ADR-029-market-state-formula-derived-joint-policy-v3.md) 和 [外部 AI 提示词](market_state_formula_derivation_external_ai_prompts.md) 承接。

## 1. 规范结果和证据边界

三段的唯一合法流向为：

```text
第一段：公式派生与注册层
  -> FormulaDerivationPreparationPackage
第二段：联合机制识别与嵌套验证层
  -> JointResearchDecisionPackage
第三段：冻结因果规则机械验收层
  -> BacktestAcceptancePackage | return_to_formula_derivation
```

任何产物中的陈述都必须唯一落入以下类型，不得混写或暗中升格：

| 机器键 | 中文标签 | 可以证明什么 | 不可以证明什么 |
| --- | --- | --- | --- |
| `structural_dependency` | 结构依赖 | 某 K 线量、参数、分支或状态在公式上可能改变输出或动作。 | 历史关联或未来效用。 |
| `empirical_association` | 实证关联 | 在已声明样本、切分和多重性口径下观察到的条件联系。 | 结构必然性或因果经济价值。 |
| `causal_economic_claim` | 因果经济主张 | 只能由新鲜、严格时序样本外证据和另行授权支持。 | 第一段推导或本基础设施本身均不自动授予。 |

状态派生 ≠ 经济有效性。公式能确定哪些输入会改变工具状态，但无法从自身推出下一期收益的条件分布。因此，第一段的“可执行”只表示可确定性重建和审计，不表示可获利、可生产或可路由。

## 2. 全局数据、权限和中文字段合同

三段均必须把 2021-01-01 至 2026-12-31 声明为封存区间 `sealed_interval=2021-01-01/2026-12-31`，不读取、不拆解、不以其结果设计公式、阈值、分支或停止规则。台账至少必须保存：

```text
post_2020_rows_read=0
post_2020_rows_used=0
production_authority=false
dynamic_parameter_authority=false
tool_routing_authority=false
```

上述权限在准备、识别、验收、失败返回和恢复后均必须为 false；任一 authority 字段为 true 必须失败关闭。

报告标题、表头和字段解释优先使用中文。每个机器包必须提供完整的 `field_labels_zh`，将每个机器键唯一映射到中文字段标签；不得只翻译顶层字段或用英文表头代替映射。

## 3. 第一段：零数据公式派生与注册

中文名称：**公式派生与注册层**
英文名称：**Formula Derivation & Registration Layer**

第一段的强制数据隔离是：

```text
market_data_rows_read=0
return_rows_read=0
empirical_validation_executed=false
```

“零行”包括市场 OHLCV、收益、标签、回测结果、样本外摘要和任何能反推经济排名的聚合量。允许输入只有冻结源公式、实现引用、参数目录、时钟/预热合同、内部因子池注册快照和确定性无收益 fixture。

第一段必须确定性派生、编译、去重并注册以下四类可执行对象：

1. `FormulaComputationGraph`（实现绑定公式图）：覆盖原始 `timestamp/open/high/low/close`→冻结工具公式→`target_position`→下一根执行与 `cost_bps` 路径，保存完整 `ToolFormulaSpec`、版本化公式见证、panel executor 引用、节点运算符、输入、K 线/参数/状态引用、`available_at`、预热、证据等级、源引用和 canonical digest。V3 的公式字符串不是可移植 DSL，也不由通用解释器执行；运行时必须先逐字段核对公式、属性、单位、节点形状、源码见证和执行器身份，再分派登记 callable。禁止用已派生状态冒充原始 K 线入口，也禁止把 Donchian 等工具错误套用 OLS 属性。
2. `ParameterContrastDerivation`（参数对照派生）：对每个登记 profile pair 生成 `delta_output_formula`、`delta_position_formula`、分歧谓词、原子贡献、精确性等级和 digest，并在无收益 fixture 上与双 profile 直接重算差一致。
3. `FormulaNativeAttributeSpec`（公式原生 K 线属性）：由图节点、margin、核差、残差比、分支指示和状态记忆派生，保存上游谱系、PIT/`available_at`、单位、预热、缺失政策和因果计算器。先查内部因子池的等价 FactorSpec；无等价项时登记可解析 callable 的 FactorSpec，再实际 upsert discovered CandidateAsset，并登记零数据 SearchScope。候选身份必须哈希完整 `FactorSpec`，包括 callable/类型、参数、输入输出 schema、预处理版本、源引用、标签与 feature 引用；任一执行语义不同都不得去重为同一候选。`upsert_candidate_from_spec` 的实际写入口同样失败关闭：直提完整载荷除字段精确外，还必须含非空执行 AST、算子、字段、规范源引用、输入谱系、表达式摘要和缺失政策；旧式搜索 envelope 必须先由内部 `spec_registry` 恢复完整 FactorSpec，未注册或疑似残缺完整载荷不得降级到旧哈希。CandidateAsset 的规范 `source_refs` 永远来自已哈希 FactorSpec；每轮数据发现来源另存 `discovery_source_refs`，只追加后者，不得改写身份谱系。快照或字符串声明不能代替这条真实注册链。
4. `InteractionStateMachineTemplate`（交互/状态机模板）：只从图拓扑派生原子属性、允许运算符、分支谓词、状态记忆、执行滞后、遗传性要求、叶覆盖下限、训练内自由参数、简化规则和 multiplicity family，不用收益挑结构。

上述对象必须是数值可执行合同：`source_attribute`、`source_target_position`、`execution_lag` 和 `transaction_cost` 都要由只接收原始五列的实现绑定 panel executor 执行；任何重新哈希后的 `causal_formula`、`signal_formula`、`ToolFormulaSpec`、源码见证或执行器引用漂移都必须在数值计算前失败。`FormulaComputationGraph.from_dict` 本身必须拒绝未知字段、错误 schema ID、中文标签漂移、重新哈希的节点/源合同多余字段和错误语义摘要；不能要求每个调用者另行跑 schema validator 才安全。图产生的仓位/成本再与另一条公开 benchmark adapter 路径逐数组核对。参数对照还要在确定性、零收益标签 fixture 上实际执行两侧冻结画像，保存 fixture、两侧输出摘要和动作分歧数；只保存公式字符串不算验证，也不得把实现绑定 IR 宣称为可移植公式解释器。

第一段还必须把系数、指数、分支、阈值、尺度和状态记忆写成具体有限轴，枚举并哈希冻结每棵完整表达式树。每棵树的原子和运算符都必须属于已登记家族；零数据 SearchScope 同时绑定 FactorSpec 摘要与全部尝试清单摘要。第二段不得才发明轴值或表达式。

所有代数等价、正系数、不改变排序的正指数及其他已声明的单调别名必须按 canonical digest 折叠，但原始登记和折叠理由仍须进入台账。阈值、`min/max`、比较和状态分支必须产生 branch predicate、signed margin 和可达性拓扑，不得因导数几乎处处为零而宣称无影响。

唯一交接物 `FormulaDerivationPreparationPackage` 组合上述四类对象、内部因子池注册快照、可识别性报告、零数据台账和 `field_labels_zh`。只有图可重建、参数差可对账、属性 PIT 合法、模板有界、注册完整时，状态才可为 `ready_for_joint_mechanism_identification`。该状态不是有效因子证明。

## 4. 五大公式家族与精确覆盖

13 个工具必须在五大家族中恰好出现一次，规范计数固定为 `4/3/2/2/2=13`：

| 家族 ID | 中文家族标签 | 工具数 |
| --- | --- | ---: |
| `spectral_bandpass_component_filters` | 频谱/带通分量滤波器 | 4 |
| `lowpass_background_adaptive_centerlines` | 低通背景与自适应中轴 | 3 |
| `moving_average_kernel_components_trends` | 均线核派生分量与趋势 | 2 |
| `volatility_adaptive_breakout_channels` | 波动率自适应突破通道 | 2 |
| `price_extrema_regression_geometry_channels` | 价格极值/回归几何通道 | 2 |
| **合计** | **五大公式家族** | **13** |

频谱分量家族必须保存转移函数/递归状态、频响/时域核差、群延迟、预热、频带能量和方向连续度。低通家族必须保存中轴方向、新息/残差、适应增益和状态转移。均线核家族优先用精确权重展开、快慢核差和交叉 margin。波动通道家族必须分开中轴、宽度、上下轨、进入和退出分支。价格几何家族必须分开极值年龄/移出效应与 OLS 斜率、中心线、残差尺度及轨道 margin。

## 5. 分量 K 线、执行时钟与 BDCI

所有输出滤波分量的工具必须使用同一个 `Δcomponent-after-close/next-bar` 语义：

```text
delta_component_t = component_t - component_(t-1)
component_direction_t = sign(delta_component_t)
state_available_at = component_bar_t.close_time
action_available_at = next_execution_bar
```

即：只在分量 K 线 `t` 完整收线后，才能用 `Δcomponent` 的涨跌方向确定状态；第一根已收线的方向翻转只能在下一根执行 K 线生效。禁止将分量数值正负（component value sign）、分量零轴穿越（component zero crossing）、相位峰谷（phase peaks/troughs）或未完成 K 线偷换为动作语义。

BDCI 只是诊断量（`diagnostic_only`），用于评估 `Δcomponent` 方向连续度、分支支持和过度平滑风险。BDCI 不是默认 alpha、不是经济有效性证明，不得未经单独注册就成为阈值门、动作规则或 authority 来源。

## 6. 第二段：完整联合策略家族的嵌套时序样本外验证

第二段入口必须先对第一段持久化目录执行完整独立验证，并把通过验证的第一段 `semantic_digest` 写入五类试运行包；缺少、漂移或未完成 FactorSpec/CandidateAsset/SearchScope 注册链的第一段一律不得读取行情。第二段物化与重建使用纯构造模式，不再查询或写入可变 FactorSpec 注册表。

中文名称：**联合机制识别与嵌套验证层**
英文名称：**Joint Mechanism Identification & Validation Layer**

第二段的评价单位是一个完整、有界、预注册的联合策略家族（complete bounded pre-registered joint-policy family），而不是一个裸原子因子。每个家族在看到对应外层结果前必须冻结属性集合、运算符、分支/叶、阈值、系数、指数、时间尺度、状态记忆、执行滞后、候选上限、支持度下限、多重性族和停止理由。

不存在通用 F1/F2/F3 强遗传性前置门；不要求 F1 先通过，也不要求所有低阶主效应先显著，才允许已登记的双因子、三因子或状态机进入联合评价。乘积、XOR/同或、三因子奇偶和 U 形关系都可以没有低阶边际信息，但这不授权无限组合搜索。每个家族必须显式选择 `heredity_requirement=none|weak|strong`；默认不得将 `strong` 用作全局准入条件。单因子结果只是主效应诊断和路由证据，不是公式原生联合策略的必要条件。

验证必须是永久研发窗加互斥外层块（fixed-development time-series OOS）：

1. 先冻结永久研发边界 `T0`；候选选择、覆盖门、公式归因、Oracle 残差和下一轮回流只允许读取 `[0,T0)`；
2. 只在永久研发窗内部做分支可达性、最小叶覆盖、状态切换数、行为指纹去重与有界自由参数选择；`T0` 之后的外层块互斥，任何外层行永远不得回收进后续训练或诊断；
3. 改动任一或全部外层结果时，选择指纹、冻结候选、原子归因、Oracle gap 与继续研发路由必须不变；外层结果只能接受或拒绝整个家族；
4. 对所有预注册且符合结构真值门的完整策略执行完整族评价，不得只报最优候选；
5. 时间块置换/重采样不得打乱时序和状态记忆。每一个零分布样本必须重放与观测统计完全相同的训练覆盖门、行为指纹去重、空池回退、内层效用选择和外层聚合过程；不得在观测统计筛选后却让 null 从未筛选全家族直接取最大值。外层证据使用该完整选择过程的 maxT 或预先声明的等价多重性规则。

搜索预算不再以 `factor_depth` 代表。每次尝试必须把下列全部自由度记入注册台账与 multiplicity 分母：

| 机器键 | 中文字段标签 |
| --- | --- |
| `operator_count` | 运算符数 |
| `coefficient_count` | 系数数 |
| `exponent_count` | 指数数 |
| `branch_count` | 分支数 |
| `threshold_count` | 阈值数 |
| `scale_count` | 时间/物理尺度数 |
| `state_memory_count` | 状态记忆数 |

叶数、最大深度、最小叶支持、状态拓扑、执行滞后、等价别名折叠前的原始尝试数和折叠后的行为数也必须分别记录。预算超限、未预注册、外层泄漏、分支支持不足或家族未完整评价均必须失败关闭，不得缩小报告分母。

第二段读取任何样本前还必须生成 `FormulaFeatureMaterializationReceipt`。该收据从授权的 2020 年及以前原始 K 线出发，调用冻结公开工具适配器，绑定 `graph_digest`、`derivation_package_digest`、FactorSpec 摘要、benchmark 摘要、冻结频率/参数、原始 K 线内容摘要、项目内数据源相对路径、源文件字节 SHA、聚合版本、观测时点、公式属性行、基线动作、前瞻收益、成本和下一根执行语义。持久化 validator 必须重新打开源文件并从当前权威注册表重建 package、FactorSpec、benchmark、参数画像、规范 OHLC 和完整实证包；调用者提供合法 SHA 或重算自摘要不能建立来源真实性。只持久化聚合摘要，不保存逐行特征、动作或交易盈亏。

第二段必须顺序执行结构真值门、训练内覆盖门、联合价值门与残差回流门。`JointResearchDecisionPackage` 的合法裁决是 `accepted_joint_policy|diagnostic_joint_candidate|underpowered_defer|return_to_formula_derivation|return_to_external_factor_registration|exhausted_registered_family_stop`。只有 `accepted_joint_policy` 可进入第三段；它仍不授予生产、动态参数或工具路由权。

## 7. Task5 40/160 先行边界

Task5 `causal_trendline_channel` 的登记参数轴固定为 `window_bars=40/160`。第一段必须从 OLS 公式确定性展开 `slope_40-slope_160`、中心线差、残差尺度比、轨道 margin 和信号分歧谓词，把最近 40 根与 160 窗中更旧样本的贡献分开。不得先从泛化趋势因子池猜代理公式。

Round003 中 `intraday_range__raw` 对 40/160 切换的局部正信号只是 `diagnostic_only` 历史线索：它的裁决仍是 `change_mechanism`，未冻结 F1、未打开 F2，也未进入 Stage 3。Round003 不是公式原生状态的必要条件、充分条件、阈值选择依据或经济有效性证明；不得用它反向修改第一段推导，也不得读取 2021—2026 细节补强该线索。

## 8. 第三段：冻结规则的机械重放

中文名称：**冻结因果规则机械验收层**
英文名称：**Frozen Causal Rule Mechanical Acceptance Layer**

第三段的唯一工作是对 `accepted_joint_policy` 冻结的属性、公式、阈值、系数、指数、分支、状态记忆、可用时点、下一根执行、缺失/预热政策、成本与基线进行逐字机械实现和重放。开始重放前必须从第一段清单重建家族，核对 `attempt_set_digest`，证明候选逐字存在于事前注册清单；还必须使用冻结 `selection_policy` 和收据绑定输入只在永久研发窗重算各折选择与投票，证明该候选确为研发窗胜者。已注册但未被选中的替换候选同样失败。它必须重新校验同一物化收据及行摘要，缺失、非法或不一致的成本不得默认为零；随后验证前缀不变、尾部追加不改历史、1/2 根状态序列化/恢复、分支覆盖、PIT、执行时钟和冻结回测口径。

第三段不得选择或删除属性，不得改阈值/系数/指数/尺度，不得增删分支或状态，不得因回测不好返回第二段偷换研究决定。失败只能用 `implementation|causal|coverage|backtest|robustness` 类型化原因返回 `return_to_formula_derivation`；静默修补后继续验收被禁止。

当前 `BacktestAcceptancePackage@1.0` 固定声明 `evidence_mode=mechanical_same_dataset_replay`、`independent_holdout_evidence=false`：它在与第二段相同的数据和物化收据上做确定性重算，只证明实现、绑定和状态恢复，不是新数据上的独立样本外复现。它不自动转换为 `causal_economic_claim`，也不打开任何 authority；若未来加入独立留出数据，必须升版合同而不能改写该字段。

## 9. 恢复、失败关闭与停止规则

每段 manifest 必须冻结源码、公式、参数、因子池、数据、切分、联合策略家族和输出 digest，完整尝试数、数据使用台账、恢复点和 `field_labels_zh`。恢复只能从最后一个通过项目内自洽 validator 的冻结包开始，不得依赖聊天正文或未入台账的临时决定。

V1 只读父引用使用仓库内完整冻结制品 `output/market-state-foundation/infrastructure-v2/pre-cognitive-preparation/tool_research_preparation.json`：文件 SHA-256 为 `bbfbfd3b5ac298b3fa3f900a6295744fb616bf34ad2b3ac9c57068eaa4916a65`，合同摘要为 `sha256:0ea7dcda15b7f32b3cb64c3d1edbbfe9df051d12a92f3b7161ce668e729f9721`。V3 重建必须同时校验完整父制品、文件摘要、合同摘要和 13 工具覆盖；工作树中其他并行研究不得使 V3 静默换父。若父基础设施确需升级，必须新建冻结证据并升版 V3 输入合同。

遇到以下任一条件必须失败关闭：计算图不能重建冻结工具；参数差与直接重算不等；属性缺 PIT 计算器/FactorSpec 且无 `registration_blocker`；家族超预算或外层泄漏；家族评价不完整；状态机恢复不等价；读取任何 2021—2026 行；任一 authority 为 true。

覆盖口径必须写成 `Stage-1=13/13 工具`、`Stage-2=五类各一个真实来源代表工具`、`真实 Stage-3 交接=0`、`目标感知能力探针=1`。五个真实家族均拒绝，因此没有真实来源决定进入第三段；目标感知探针只证明“登记联合家族可在单原子零边际时走通引擎与机械重放”，明确 `empirical_acceptance_evidence=false`，不得冒充因子发现或实证接受。机器总验收验证 V1/V2 HEAD 字节摘要、物化收据、13 项非空证据、提交/工作树边界和密封数据台账；其接受谓词只由这些可重算事实构成。代码审阅、架构审阅和完整测试输出属于外部发布流程，机器构建器、验证器、Schema 和完成项均不接收这些过程文本，也不以其存在或 verdict/result 卡门。外部流程仍须在审阅阻断或测试失败时停止发布；只是仓库自身不再谎称能够证明 LLM 身份、提示注入免疫性或测试文本真实性。若需独立机器认证，必须接入仓库与当前账户权限之外的签名/CI attestation。经济增量为正仍不是基础设施完成的必要条件；生产化、动态路由和多策略组合不在本工作流范围内。
