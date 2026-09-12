# 项目级 K 线市场状态地基工作流

> 四层归属：A0–D 市场事实统一由 Layer 2 入口承接。策略 OS 只能消费这些事实，
> 不再拥有或重写地基属性；本文不输出认领、动作或仓位。

## 现在能做什么

A0—D 允许登记契约、构建 1d+60m 严格因果市场事实、查看隔离的历史地图/相似期，
并把基础设施当作“具体择时工具字典”查询；R2F 还可查询工具公式、
绩效恒等式、机制和因子映射：

1. 在现有 Feature Library 登记一个确定频率的 `FeatureSpec`；
2. 用精确 `feature_id + feature_version + frequency` 生成引用；
3. 生成不可随 active registry 漂移的 FeatureSpec snapshot；
4. 把一个 READY、通过市场状态消费者质量准入、带哈希和水位的 DataHub
   版本固定为输入；
5. 全量或可信增量生成 1d+60m 完整属性和因果 online state；
6. 在隔离的 B 研究包查看事后历史段与严格因果相似期；
7. 在隔离的 C1.2 证据包查看 IIR、低通、巴特沃斯、傅里叶、小波、R3、布林、
   价格通道、趋势线、均线等具体工具在属性状态下的收益、胜率、盈亏比和换手
   方向关系；
8. 在 C1.3 多尺度时间稳定性地图中，检查上述关系能否同时经受粗细窗口和错位
   窗口复现；
9. 在 R2F 检查 13 个工具的公式、11 类机制、43 条映射边和 34 个唯一因子，
   并读取已执行的相对损失差、机制联合与条件增量研究证据；
10. 在逐工具条件关系层检查属性是否稳定指向该工具的参数上调或下调；
11. 在[择时经验公式注册层](market_state_empirical_formula_workflow.md)查询已经形成
    数学关系但尚未成为因子或路由的有界经验、反例和候选用途；
12. 验证双摘要、不可变版本和原子 internal current；
13. 通过明确 deprecated 的宽表兼容旧 CloudRidge 重叠字段；
14. 在父仓把 CloudRidge 与同源市场状态提交为一份唯一 Baylum 发布回执。
15. 在[群体相关性工作流](group_correlation_market_state_workflow.md)构建全市场/制造业跨股票面板日度指标，并将两个股票池统一注册为不改写冻结 A2 的纯指标增量包；指标注册不声明策略有效性。

现在仍不能用本模块自动切换策略。C 是方法选择先验，不是产品路由；D 的统一
回执只授权数据批次，不授权任何策略生产状态。

## D 统一日更

正式入口仍是父仓：

```bash
python3 ../scripts/run_baylum_data_update_workflow.py --skip-upload
```

父流程会先独立更新全市场/制造业群体相关指标，再生成 CloudRidge 60m levels并调用市场状态发布 CLI。群体指标入口为：

```bash
PYTHONPATH=src uv run python scripts/run_group_correlation_daily_update.py \
  --datahub-root /home/starryocean/桌面/量化/unified_datahub
```

其输出固定为纯测量数据，包含两个群体、三指标、20/60/120日三个窗口；不执行工具映射或策略验证。随后父流程调用：

```bash
PYTHONPATH=src uv run python scripts/stage_market_state_baylum_release.py \
  --levels-csv <cloudridge-60m-levels.csv> \
  --dataset-version <exact-1m-qfq-version> \
  --datahub-api-base http://127.0.0.1:8400 \
  --market-state-output-root output/market-state-foundation \
  --release-stage-root ../output/baylum-release/staging \
  --code-version <immutable-code-version> \
  --carrier-definition-version cloudridge-beta-index-v1

PYTHONPATH=src uv run python scripts/publish_baylum_release.py \
  --cloudridge-stage-manifest <cloudridge-stage-manifest> \
  --market-state-stage-manifest <market-state-stage-manifest> \
  --release-root ../output/baylum-release

PYTHONPATH=src uv run python scripts/validate_baylum_release.py \
  --manifest ../output/baylum-release/current/manifest.json
```

验收只认 `../output/baylum-release/current/manifest.json`。FactorLab A2
`current` 是 stage pointer，不能代替统一回执。父流程只有在回执核验
`valid=true` 后，才继续发布 CloudRidge、Timing 和 Risk-Off 结果。
CloudRidge stage 自带不可变 `levels.csv` 快照，因此下一次覆盖日更工作目录不会
让旧回执失效。

检查日更状态：

```bash
python3 ../scripts/run_baylum_data_update_workflow.py \
  --check-only \
  --skip-remote-check
```

关注 `baylum_release_current.status`：

- `ready`：精确源版本与水位和 DataHub 当前一致；
- `market_state_stale`：DataHub 已推进，统一回执尚未推进；
- `market_state_missing`：尚无统一回执；
- `market_state_invalid`：回执、stage 字节或共同身份核验失败。

## 全量构建

```bash
PYTHONPATH=src uv run python scripts/build_market_state_foundation.py \
  --source-csv <cloudridge-1d.csv> \
  --dataset-evidence-json <datahub-ready-response.json> \
  --dataset-version <exact-dataset-version> \
  --code-version <immutable-code-version> \
  --output-root output/market-state-foundation
```

必须显式提供 exact DataHub dataset version 的正式 HTTP 响应。响应必须包含
READY、嵌套 manifest、内容哈希、watermark、quality report 引用和质量明细；
FactorLab 再按 `factorlab_market_state_bars_source_admission@1.0`
做消费者级准入。不要向响应手工添加 dataset-global `research_ready=true`。
A1 不接受 incremental 选项。

构建后验证 internal current：

```bash
PYTHONPATH=src uv run python scripts/validate_market_state_foundation.py \
  --manifest output/market-state-foundation/current/manifest.json
```

## C1.2 具体工具字典

正式构建：

```bash
PYTHONPATH=src uv run python scripts/build_market_state_foundation_c.py \
  --online-manifest output/market-state-foundation/current/manifest.json \
  --code-version <immutable-code-version>
```

独立验证：

```bash
PYTHONPATH=src uv run python scripts/validate_market_state_foundation_c.py
```

权威入口是：

```text
output/market-state-foundation/evidence/current/manifest.json
```

按工具或中文别名查询：

```bash
PYTHONPATH=src uv run python scripts/query_market_state_tool_dictionary.py \
  --tool IIR \
  --metric gain_loss_ratio \
  --conclusion supported \
  --limit 20

PYTHONPATH=src uv run python scripts/query_market_state_tool_dictionary.py \
  --tool 布林 \
  --action-role cash_avoidance \
  --metric trade_win_rate \
  --limit 20
```

`tool_source_inventory.json`、`tool_registry.json` 和
`tool_state_affinity_evidence.parquet` 是关系主表；
`tool_state_affinity_fold_evidence.parquet` 是逐验证段证据。发现清单、工具本体、
benchmark 和实证四层独立对账，当前均为 13 个，延期数为 0。十个通用工具执行
1d/60m benchmark；频率选择性布林、巴特沃斯低通残差包络和非对称弧形状态
空间包络直接执行原生 15m 代码，并使用同一套因果市场属性/状态公式。策略名称
和版本只存在于 `source_strategy_refs`，用于追溯工具来源，不参与工具身份或
关系主键。
旧 `method_family_registry.json` 和 `method_state_affinity_evidence.parquet` 只是兼容
投影。

当前正式 C1.2 包为 `market-state-tool-c-d643f9a74fbac169`，语义摘要为
`sha256:d643f9a74fbac16990e6be589689741914109671d41196ff446574040da3b1f3`。
它包含 32,844 条关系和 98,532 条逐折证据；960 条满足 3/3 验证门，
31,884 条被如实拒绝或记为证据不足。独立验证为 `valid=true`，研究数据最晚
日期为 2020-12-31，`blackbox_opened=false`。

只把 `conclusion=supported` 理解为“2009—2014 发现并冻结的方向，在
2015—2016、2017—2018、2019—2020 三个互不重叠验证段全部通过”，不能理解
为生产可交易。旧的 2015—2020 `audit_*` 列只是兼容汇总，不能替代逐段门禁。
`unknown`/`none` 不是未研究：应同时查看
`tests_executed` 与 `insufficient_reason`。2021—2026 不得用于 C 机制发现、阈值
调整或失败归因。

### C1.2 之后的十五工具组合入口

C1.2 的13工具关系证据保持冻结，不因新增工具而重写。当前研究注册表是
`tool_registry_v1_5`：V1.4 先追加论文核多尺度趋势作为第十四工具，再追加
LAT 通道 `lowpass_bandpass_lat_channel` 作为第十五工具。组合层仍是上涨捕获与
下跌防护两条空优先级瀑布；进入
[择时策略组合优先级工作流](market_state_timing_priority_composition_workflow.md)。
LAT 六桶方法见
[做多六桶工作流](market_state_lat_six_bucket_hf_method_workflow.md) 与
[做空六桶工作流](market_state_lat_short_six_bucket_hf_method_workflow.md)。
空框架之上的三级双向原型进入
[三层双向择时策略路由工作流](market_state_timing_strategy_routing_workflow.md)。这只是增量
身份和组合骨架，尚未把第十四、第十五工具补算进旧 C1.2 关系包，也未授予路由权。

需要一个统一入口同时查询"公共状态 + 工具专属因子 + 执行约束"时，进入
[六轴与工具专属因子统一基础设施工作流](market_state_unified_timing_factor_infrastructure_workflow.md)；
该入口复用而不复制六轴与冻结 R2F 包，第 14/15 工具为 append-only 扩展，所有权限为 false。

## C1.3 多尺度时间稳定性地图

构建：

```bash
PYTHONPATH=src uv run python \
  scripts/build_market_state_tool_temporal_stability.py \
  --code-version <immutable-code-version>
```

验证：

```bash
PYTHONPATH=src uv run python \
  scripts/validate_market_state_tool_temporal_stability.py
```

权威入口：

```text
output/market-state-foundation/temporal-stability/current/manifest.json
```

当前不可变包为 `market-state-tool-stability-51536b0fcb91dee8`，语义摘要为
`sha256:51536b0fcb91dee898a6fcae2677338e5234d5a03b301d337ce88af61239114f`。

C1.3 对每条关系同时保存线性、曲线候选，并在4年、3年、2年、1年、半年及
错位1年/半年共9套切分、105个完整窗口中复核。当前正式结果没有任何关系达到
“105个窗口全部有信号且同向”；31行达到“9套切分均复现且无反向”，去除
turnover 在两个职责下的机械重复后为20条，其中直接涉及绩效的只有9条。

C1.2 原960条 supported 中，12行、去重后6条进入该层，且全部只是换手关系；
17行降为稀疏同向，931行出现实质反向。今后不能只查 C1.2 `supported`，
还必须查 C1.3 的 `stability_status`。

105个窗口存在嵌套和重叠，不能当作105个独立样本计算置信度。
`cross_partition_stable_with_gaps` 也只代表时间复现；
`conditional_independence_tested=false` 表明相关属性混杂尚未被剥离。
详细查询和文件说明见
[多尺度时间稳定性工作流](market_state_tool_temporal_stability_workflow.md)。

## R0—R4 工具能力与首代路由研究档案

当需要追溯“为什么当前没有动态参数/工具路由”时，按层阅读：

1. R0 完整画像、参数研究合同和能力证书：
   [能力合同白皮书](../ops/market_state_tool_capability_contract_whitepaper.md)；
2. R1 稳健固定参数能力：
   [工作流](market_state_tool_fixed_capability_workflow.md) →
   [白皮书](../ops/market_state_tool_fixed_capability_whitepaper.md)；
3. 第一代 R2 根状态轴：
   [工作流](market_state_tool_root_axis_audit_workflow.md) →
   [白皮书](../ops/market_state_tool_root_axis_audit_whitepaper.md)；
4. R3 状态条件化参数响应：
   [工作流](market_state_tool_parameter_response_workflow.md) →
   [白皮书](../ops/market_state_tool_parameter_response_whitepaper.md)；
5. R4 完整画像两两 Battle：
   [工作流](market_state_tool_pairwise_battle_workflow.md) →
   [白皮书](../ops/market_state_tool_pairwise_battle_whitepaper.md)。

这些都是永久失败/能力证据，不是一次性 Plan。R3 和 R4 首轮候选为 0，
所以当前回退到 R1 固定画像；只能在 R2F/第二代 R2 出现新的相对损失差
证据后重启。

## R2F 公式机制与第二代 R2 实证

深度入口是
[公式先验的择时工具机制工作流](market_state_tool_formula_mechanism_workflow.md)，
原理与当前权限见
[公式—绩效—K线属性机制白皮书](../ops/market_state_tool_formula_mechanism_whitepaper.md)。

公式先验与冻结设计：

```bash
PYTHONPATH=src python scripts/build_market_state_tool_formula_mechanisms.py \
  --output-dir output/market-state-foundation/formula-mechanism/r2f

PYTHONPATH=src python scripts/validate_market_state_tool_formula_mechanisms.py \
  --output-dir output/market-state-foundation/formula-mechanism/r2f

PYTHONPATH=src python \
  scripts/build_market_state_tool_mechanism_validation_spec.py \
  --output-dir output/market-state-foundation/formula-mechanism/validation-spec

PYTHONPATH=src python \
  scripts/validate_market_state_tool_mechanism_validation_spec.py \
  --output-dir output/market-state-foundation/formula-mechanism/validation-spec
```

第二代 R2 实证：

```bash
PYTHONPATH=src uv run python \
  scripts/build_market_state_tool_mechanism_validation.py \
  --output-dir \
  output/market-state-foundation/formula-mechanism/r2-mechanism-validation \
  --profile-workers 8 --validation-workers 8

PYTHONPATH=src uv run python \
  scripts/validate_market_state_tool_mechanism_validation.py \
  --output-dir \
  output/market-state-foundation/formula-mechanism/r2-mechanism-validation
```

验证顺序、交互准入、函数形状、外层折和停止门仍由
`market_state_tool_mechanism_validation_spec@1.0` 冻结。已执行研究覆盖
554 组比较和 282,034 个完整分歧事件；没有因子或机制获得跨配对/家族支持，
局部配对线索不得冒充工具路由。2021—2026 的读取行数为 0，仍封存。

已有模型之后的第 N 个因子不再回到因子名单盲扫，而进入
`market_state_tool_formula_residual_attempt@1.0`：冻结当前模型，区分原始相对
效用 `D`、条件切换增量 `S` 和遗憾 `R`，再从最大公式 Gap 推出一个直接因子，
并把全局加分、条件状态机、单向 Override、Veto 等动作几何分别裁决。
同一失败身份由“公式×基线×数据×Gap×因子×目标×几何×分支×规则”锁定，
并由项目级追加 Registry 而不是 Attempt 自报历史；表示失败不得冒充因子失败。
完整 R0—R8 状态机仍从上面的公式机制工作流渐进进入。

## R2F-M 公式候选属性统一测量层

四类频谱带通工具的 33 个候选属性不得从公式拆解直接跳到实证，也不得为每个
工具编写临时脚本。参数目录与测量层必须先通过
[参数—属性跨轮基础设施工作流](market_state_cross_round_infrastructure_workflow.md)，
证明 13 工具、84 参数、108 假说、33 属性和物理尺度外键完整；再进入
[频谱工具 K线属性测量层工作流](market_state_spectral_kline_attribute_measurement_workflow.md)，
合同、尺度和权限原理见
[测量层白皮书](../ops/market_state_spectral_kline_attribute_measurement_whitepaper.md)。

这一层复用 14 个既有严格历史属性并补齐 19 个公式直接量，物理尺度先按交易日
定义，再换算 1d/60m/15m 根数；输出
`time × tool × broad_parameter × attribute` 研究底表。它只保证定义和计算
正确，不验证 108 条关系，不认证因子，不调参、不回测、不路由。

```bash
PYTHONPATH=src uv run python \
  scripts/build_market_state_spectral_kline_attribute_measurement.py

PYTHONPATH=src uv run python \
  scripts/validate_market_state_spectral_kline_attribute_measurement.py
```

## R2G 逐工具条件关系认证

第二代 R2 之后的中间层入口是
[逐工具 K线属性条件关系认证工作流](market_state_tool_conditioned_relationship_workflow.md)，
数学与权限边界见
[逐工具条件关系白皮书](../ops/market_state_tool_conditioned_relationship_whitepaper.md)。

它不要求某属性对所有工具都同向，而是在同一工具、频率和参数语义轴内，
要求参数正负两侧镜像一致、八个样本外年份复现，并通过工具内和跨工具
多重检验。该证据只服务后续动态参数研究，不自动产生路由。

当前单因子层按 70/80/90/95% 条件命中率分层，承认尚未剥离的其他因子会
阻碍少数事件，同时用最低 20 次非零改选、至少 3 个外层折和至少 6 个年度
约束小样本假一致。未来多因子层的 100% 指事件归因记账覆盖，不指预测准确
率。已执行结果为 1 个独立单侧条件关联、0 个完整镜像参数规律。
首个公式倒推的 2-of-3 多因子原型亦已冻结执行，结果拒绝：
等权平铺会让高相关的频谱激活代理重复投票。后续多因子必须先按
机制块压缩，再做块间交互；不得直接按原始因子数量投票。
另一个 60 分钟布林对象已将搜索充分性与规律有效性分开：
2,181 个公式/状态树证明训练内可以找到大量赢家，但内层时序选中后
对最佳单因子仅 2/4 外层折严格为正，所以高容量搜索仍不授予路由或调参权。

## 最小检查

```bash
PYTHONPATH=src uv run pytest \
  tests/unit/test_feature_library.py \
  tests/unit/test_market_state_*.py \
  tests/integration/test_market_state_bundle_lifecycle.py \
  tests/integration/test_baylum_market_state_release.py \
  tests/integration/test_baylum_data_update_release_handoff.py \
  -q
```

静态检查：

```bash
uv run ruff check \
  src/factor_lab/market_state \
  src/factor_lab/factor_engine/feature_library.py \
  tests/unit/test_market_state_*.py \
  tests/integration/test_market_state_bundle_lifecycle.py

uv run basedpyright src/factor_lab/market_state
```

## 使用边界

- 不要在 `MarketAttributeSpec` 写公式；回到 Feature Library 建立或升级
  `FeatureSpec`。
- 不要用不带版本的 feature 引用；bundle 必须保存精确 snapshot。
- 不要把 1d 与 60m 塞进同一个 FeatureSpec；它们是不同实现，用
  `physical_attribute_id` 表达同源。
- 不要把 retro manifest 交给回测或实时消费者。
- 不要把 evidence manifest 交给 live feature；它只允许 research 和
  `tool_selection_prior`（旧 C 兼容包仍使用 `method_selection_prior`）。
- 不要把 supported 关系按条数投票；同源属性和不同尺度可能相关。
- 不要把 C1.3 的窗口数量冒充独立样本数，也不要把时间稳定冒充条件独立。
- 不要按策略版本查询 C1.2；先查该策略实际使用的具体工具。
- 不要用方法家族代理替代具体工具；IIR、IIR 低通和巴特沃斯必须分别看证据。
- 不要接受 DataHub 的 latest 隐式漂移；显式请求并核对 exact version。
- `available_at` 是可用时间，不是观测逻辑键的一部分。
- 不要把 `legacy_100d` 当成 `slow_120d`。
- 不要把 A1 中文在线状态报告当成使用未来的事后历史地图。
- 不要把 FactorLab internal current 当成父仓最终生产 release authority。

权威原理与阶段边界见
[项目级 K 线市场状态地基白皮书](../ops/market_state_foundation_whitepaper.md)。

## 旧口径与可选差分重做

本工作流现有 1d+60m+15m 产物仍是官方会话口径。迁移时不要改这些包。若要下午可交易过渡，先跑日线竖切 [`market_state_daily_afternoon_remake_workflow.md`](market_state_daily_afternoon_remake_workflow.md)，再按 `optional_remake_variants('1d'|'60m'|'15m')` 扩到小时/15 分钟。旧包只读。
