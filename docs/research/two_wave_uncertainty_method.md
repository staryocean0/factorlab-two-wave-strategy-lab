# 两浪形态指标的日历 block 不确定性实现

状态：`morphology_replication_not_yet_accepted`。本文件解释新增实现，不修改已经冻结的 `two_wave_evaluation_protocol_v0_1.md`，也不把合成测试或开发行情统计变成人工正确答案。`annotations.py` 原有点估计入口保持不变；新增入口为 `uncertainty.evaluate_block_bootstrap(runs)`。

## 1. 输入与可以报告的内容

每个 run 提供完整 DataHub `product_id`、固定配置的 `export`、用于把审查索引映射到日期的 `bars`，以及标准 `two_wave_annotations@1.0` 文档 `annotations`。可直接使用 `reconcile_annotations(...)` 返回的 `adjudicated_reference`。产品身份必须保留频率、偏移与实际导出产品差别；不能把 `daily_proxy` 的每日抽样当成完整日线 OHLC。

仅 `fully_reviewed=true` / `complete_reviewed=true` 的窗口进入主要计分；没有两浪的完整负例窗口也保留在 block 内，不能把没有标签的窗口从误检分母删除。声明必须是真正的布尔值，字符串 `"false"` 或两个字段冲突会报错。相同离线几何或同一在线截止时刻的重复几何必须先去重或仲裁，不能多画几次增加支持数。

来源声明中的明确反证会直接拒绝输入：算法/合成来源、已显示算法、非独立标注、未盲、在线已见未来。文档级反证不能被一条记录的“human”姓名覆盖。缺少来源字段仍不能证明独立性；兼容旧格式不构成来源验收。必须继续完成盲标注和人工仲裁。

本入口只支持 `bar_end` 理想同步前缀。显式声明 `online_clock="information_available_time"` 的输入会被拒绝，因为现有匹配器只检查确认 bar 与截断 bar；不能将该检查冒充真实可得性时钟。当前历史 PIT 仍未验证。

## 2. 日历合并先于抽样

`build_calendar_blocks(windows)` 把核心窗口端点映射为上海日历日期，闭区间相交即合并，同一日期也保守合并。跨产品、跨频率、跨尺度以及传递相交均使用同一 block；跨年相交也不能按年度硬切开。

采用日历日而非日内时刻，是此补充实现的保守假设：同一天两个不相交日内核心不被假定为独立行情。上下文不另算样本；仍按原协议以最后极值所在核心计分。非重叠的核心不等于已经证明市场时间依赖消失，跨核心的长结构和较长记忆仍是有限样本局限。

block 身份由合并后的起止日期确定。产品只持有对同一 block 的引用；不会各复制一个独立样本。离线与在线的完整审查集合、计分、重采样和结果始终分别运行。

## 3. 产品/年度分层如何与共同抽样一致

直接对每个产品年度分别抽 block，会让同一段日历行情在不同频率得到不同抽样次数，破坏共同依赖。实现采用更细的联合分层：每个 block 的**参与签名**是它涉及的全部 `(product_id, config_id, scale_id, year)` 组合。

具有相同参与签名的 block 在一个重采样层内抽样。一个含 `n` 个 block 的层，每次按等概率有放回抽 `n` 次；同一个 block 得到的整次数权重，应用于它的所有产品、年度、尺度和计分类别。这样每个产品/尺度/年度的 block 数保持不变，跨年 block 也整体重采样。不同参与签名不互借样本。

重采样固定为 2,000 次、种子 `20260905`。为使调用顺序及无关层的加入不改变已有层的抽样，随机子流种子取 `sha256("20260905/参与签名")` 前 8 字节的大端整数，使用 NumPy `default_rng` 和 multinomial。输出保存 NumPy 版本、种子派生规则、联合分层清单及权重矩阵 SHA256。

默认要求每个相关联合层至少有 5 个日历 block。这是**新增的保守实现下限，原 v0.1 没有预注册该具体数字**，不能称为用户指定阈值，也不等于 5 个 block 已足够可靠。API 的 `min_blocks` 参数仅用于显式研究设计记录，不用于选择识别参数或宣告验收。稀疏层绝不回退为逐结构抽样。

## 4. 计分、CI 与失败关闭

几何匹配完全复用原实现：同产品配置/频率/尺度/相位、每个极值 ±2 bar、一对一最大匹配数优先、总距离最小、分类盲匹配。在线确认晚于截止时刻的预测不能参与该前缀。重复在线前缀是相关观察，保留在同一个日历 block，不成为新独立 block。

每个 block、产品、年度分别保存预测数、参考观察数、匹配数、混淆矩阵和未匹配预测类别数。每次 bootstrap 对这些**整数计数整体加权**，重新计算 precision、recall、三类 macro-F1、算法明确分类覆盖和参考端明确分类覆盖；周期与两浪分别报告。macro-F1 包含未检出、拒判，以及未匹配明确类别预测造成的假阳性，与原点估计定义一致。

不将重复抽到同一 block 解释为新的几何对象，也不对抽样副本再次跨副本匹配。汇总指标按对象计数合并，不是产品等权平均；产品、配置、尺度和年度计数同时保留。

原全局匹配可能在两个不相交核心、或年度边界的 ±2 bar 容差内跨边界成功。此时直接加总局部匹配与原全局指标可能不一致。实现检查全部计数是否一致；不一致就保存两套计数和错误，保留全局点估计，**该模式的 CI 全部 withheld**。不放宽容差、重新分窗或偷偷改变主匹配规则来得到区间。此类情况下年度行只是局部计数诊断，不能视为与全局匹配可加的年度归因。

CI 为 2.5% 与 97.5% 百分位，NumPy `quantile(method="linear")`。没有可计分独立参考、没有完整审查窗口、相关联合层稀疏或计数不可加时，CI 为 `null` 并列出原因。某指标在任何一次抽样中分母为零，也将该指标 CI 置为 `null`，报告有效抽样次数；不能悄悄删除这些抽样并缩窄区间。

所有 CI 即使成功计算，`accepted` 仍为 `false`；标签数量、三类支持、独立性、仲裁、敏感性和形态验收是其他门。区间不是 H1/H2、收益、交易、V1.6 注册或 fresh-OOS 的授权。

## 5. 本次实际窗口设计审计

命令：

```bash
python scripts/audit_two_wave_window_blocks.py \
  --results cloud_results/two_wave_continuation/baseline_full_replay \
  --output cloud_results/two_wave_continuation/window_block_audit.json
```

读取现有 6 视图、基准 `reversal_log=0.01` 的固定窗口，并使用原 Parquet 18,992 行时间戳映射。没有运行新的行情识别、没有生成标签，也没有计算真实形态 CI。

| 已实际使用的视图 | 实际导出频率 | 原窗口数 | 仅在该产品内合并后的 block 数 |
|---|---|---:|---:|
| 30m_offset_15 | 30m | 12 | 12 |
| 60m_offset_30 | 60m | 6 | 6 |
| 60m_offset_45 | 60m | 6 | 6 |
| daily_noon_close_1130 | 1d | 6 | 6 |
| daily_proxy_close_1400 | 60m | 6 | 6 |
| daily_proxy_close_1430 | 30m | 6 | 6 |

跨产品联合合并后，42 个预选核心只有 **6 个日历 block**：2015—2020 每年一个，均涵盖该年全部 6 个产品。全年窗口把其间较短频率窗口连接起来；每个年度联合层只有 1 个 block，即使重复抽 2,000 次也不会获得该年度的时间变动证据。6 个联合层全部稀疏。

因此真实结果 `confidence_intervals_95=null`；独立参考数与完整审查窗口数均为 0。这是采样设计的可审计限制，不能通过将同一年产品各算独立 block、拆成独立两浪或只删除不利的全年产品解决。后续若需改变窗口设计，应另起协议版本、说明原因并保留旧清单，不能看标签结果后选窗。

CLI 也可读取以后完整运行目录中的 14 个视图，但本次仅执行以上 6 个，不能把工具支持范围写成实际覆盖范围。

## 6. 收到人工参考后的可运行入口

```bash
python scripts/evaluate_two_wave_reference_uncertainty.py \
  --run-dir cloud_results/two_wave_continuation/baseline_full_replay/30m_offset_15/reversal_0.01 \
  --annotations path/to/adjudicated_reference.json \
  --output cloud_results/two_wave_continuation/reference_uncertainty.json
```

`--annotations` 可指向标准参考文档，或完整仲裁输出中的 `adjudicated_reference`。联合评估多个产品时，按相同顺序重复 `--run-dir` 和 `--annotations`，每个目录只接收对应产品/配置/尺度的文档；身份不一致会报错，不能把一份单产品标签套给另一个产品。

CLI 读取已有 config、pivots、cycles、structures、events 和 summary，验证配置哈希、数量、确认索引与供应商数据清单。只加载原导出使用的行情前缀，保留输入、源码、冻结规范与协议哈希，不重新运行识别器。

本次已实际用同一个命令入口加载 `30m_offset_15` 的原 `annotations_empty.json`；结果保存在 `cloud_results/two_wave_continuation/reference_uncertainty_empty_status.json`。这是 **1 视图、8,765 行的空参考执行检查**，离线和在线指标区间均为 `null`，不能与上面的 6 视图窗口设计审计混称为已完成真实参考评价。

## 7. 实现验证

`tests/unit/test_two_wave_uncertainty.py` 使用显式合成夹具验证：传递重叠、跨年不切断、上海日期归属、跨产品共享权重与年度边际数保持、离线/在线分开、确认延迟不回填、无标签/稀疏层不给区间、确定性重跑、原匹配点值一致、重复几何拒绝、明确非独立来源拒绝、未支持时钟拒绝、完整审查标志类型、零分母抽样不被静默丢弃，以及跨边界匹配不可加时拒绝区间。合成区间只检验算法实现，不是市场形态验收结果。
