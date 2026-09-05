# 两浪研究继续入口：v0.5 TCSS 表示层 POC 通过，但父级识别器未验收（2026-09-05）

## 当前状态

**操作研究基线继续是 v0.4.3。** v0.4.4 已作为负向层级实验归档；v0.5 TCSS 目前只晋级为 `promotable_raw_reversal_representation_candidate`，不是新 recognizer、不是新基线。

优先阅读：

- [v0.5 TCSS 正式 POC 结果](docs/research/two_wave_multiscale_tcss_results_v050.md)
- [v0.5 跨学科数学预研究](docs/research/two_wave_multiscale_pre_research_v050.md)
- [v0.5 结果前 POC 冻结协议](docs/research/two_wave_multiscale_poc_protocol_v050.md)
- [v0.4.4 正式否定结论](docs/research/two_wave_hierarchy_results_v044.md)
- [v0.4.3 当前操作基线结果](docs/research/two_wave_confirmation_ablation_results_v043.md)

## 金融需求没有改变

首轮生产语义仍是 **raw-price reversal wave**：低点起算必须是 `L0 -> H1 -> L1 -> H2 -> L2`（高点起算对称），两个完整周期共享中间同相位端点，五个父级 extrema 属于同一可审计尺度。

严格单调 raw price 不得因为去趋势 RC/IMF/wavelet detail 中存在周期就被伪装成两个原价格反转波。`detrended_cycle_only` 必须和 raw-reversal 分开。

父状态的震荡/上涨趋势/下跌趋势判定仍在两个完整同尺度波形成立之后；当前不改资格层和 D1。

## 为什么 v0.5 允许直接从原价格建立多尺度父级表示

v0.4.4 已证明，如果父级始终被 v0.4.3 的局部切割表示锁死，13、16、17、19、25 根等合法微周期会继续切碎目标大结构。

因此 v0.5 允许事前冻结、严格因果的多尺度算子直接作用于原价格；v0.4.3 局部 extrema 继续作为 audit overlay，专门检验父层实际吸收了多少旧微摆，但不再控制父级闭合。

`12—48` 继续只作为后续目标周期资格/诊断带，**不得用于父级闭合或尺度选择。**

## 跨学科预筛选结论

按“金融语义 -> 数学层级性质 -> 在线因果性 -> 前缀稳定性”筛选：

1. **P0：Time-causal scale-space (TCSS)**：最直接对应 v0.4.4 的失败机制；尺度增大应系统吸收细极值。
2. **P1：Trailing/causal SSA**：检验“低频父振荡 + 高频扰动”，但必须防止 trailing window 推进后重写历史。
3. **P1：Causal wavelet/filter bank**：必须严格单边，禁止双边 CWT / `filtfilt` / future padding，并报告延迟与 ringing。
4. **Oracle/reference：Persistence、EMD/EEMD/HHT、SST/VMD**：在未证明 prefix-native 前不能生成生产事件。
5. **Control：Directional Change；Auxiliary：Change Point Detection**。

没有必须选赢家的要求。

## TCSS 正式结果

正式执行 HEAD：`373d15a51ca14cc30f1979e49315e5e044e2bc0b`

正式 GitHub Actions：**run `33966220967` success**。

正式 artifact：

- id `9969542304`
- SHA256 `7a8ea5312371fe3c9fcfeeaaedab2f19f5813f3be62e5bae874beeb9e7934a9b`
- 60,589 bytes
- expires `2026-10-05T12:33:08Z`

**371 tests / 0 failures / 0 errors / 0 skipped。**

六视图 × 25%/50%/75% = **18 次固定前缀重放全部通过，confirmed rewrite count = 0**。

主 `5m_offset_0` 的 14 层 extrema 数严格粗化：

`28667 -> 24679 -> 19451 -> 14231 -> 9819 -> 6803 -> 4789 -> 3291 -> 2235 -> 1579 -> 1107 -> 801 -> 599 -> 427`

其余四个原生 5m 也全部从约 27k extrema 粗化到 415；1m 从 80,957 粗化到 1,955。

更关键的是 v0.4.3 audit overlay：一个 TCSS 两浪内部“超过五个父级点之外”的额外 v0.4.3 局部 extrema 中位数，在 sigma 5.657 起从 0 变为 1，sigma 8 为 4，sigma 11.314 为 7，sigma 16 为 13，后续继续增加。**这证明父层确实吞掉微摆，而不是 v0.4.4 那种 collapsed median=0。**

## case_00：目标机制出现，但禁止事后选尺度

旧 case_00 区间 `[48720,48801]` 随尺度连续演化：

- sigma 0.5：`13/6`
- sigma 1：`13/14`
- sigma 1.414：`19/21`
- sigma 2：`20/21`
- sigma 2.828：`22/43`
- sigma 4：`34/43`
- sigma 5.657：`35/42`
- sigma 8：`37/51`

所以 v0.4.4 未做到的“大结构从微摆中浮现”在 TCSS 中已经出现。

但**绝不能因为 sigma 4 对 case_00 的审计 IoU 最高就选择 sigma 4**。这会把研究重新变成 case 定制。

## 固定窗口

TCSS 没有复制 v0.4.4 的“删除坏对象”模式：

- 2018-06-20：中间尺度出现 `17/18`、`24/27` 等规整结构；原 `inefficient_leg` 仍留给未来独立资格实验。
- 2019-04-15：v0.4.4 曾变成 0 候选/0 父周期；TCSS 中间尺度出现 `15/13`、`25/23`、`25/42` 等连续粗化结构。
- 2020-07-15：TCSS 中间尺度仍有 `18/27`、`39/28`、`41/40`、`42/39` 等结构，没有把该区域删空。

本轮没有重跑资格/D1，因此这些只是表示层证据，不是重新发布交易状态。

## 为什么 TCSS 还不是父级识别器

### 1. characteristic-scale 尚未冻结

TCSS 当前输出整个尺度空间。真正父级 recognizer 还需要一个**只使用截至当时信息、事前冻结的自动 characteristic-scale / cross-scale persistence 规则**。

### 2. 粗尺度天然会出现巨型结构

case_11 / case_14 在非常粗层可以自然形成数百根五点；这是尺度空间本身的正常现象，但说明如果自动尺度选择错误，旧“跨数周巨型五点”风险会回来。因此安全门目前是 `unresolved_until_scale_selection`，不是 pass。

### 3. 原生 5m 边界稳定性的最终结构 IoU 也必须等唯一尺度/发布语义冻结

当前每层有大量重叠候选。把所有候选直接做 coverage 会失去判别力；事后给每个候选挑最高 IoU counterpart 又会引入新的自由度。因此先冻结 scale identity + 发布/互斥规则，再复用既有 1m 时间戳映射计算跨 offset 边界稳定性。

## 下一安全停点

下一轮仍不能直接写“v0.5 新基线”。应并行推进：

1. **TCSS characteristic-scale / persistence 预研究**：研究 time-causal scale selection、尺度归一化 temporal derivatives、跨尺度 extrema persistence 等，只允许因果规则；先协议后代码。
2. **tSSA 与 causal wavelet/filter-bank 独立 POC**：继续作为竞争路线，必须遵守已经冻结的 raw-reversal / detrended-cycle 语义分流和 prefix 门，不能因为看到 TCSS 结果后修改金融目标。

只有某条路线同时解决：表示层、自动尺度身份、安全反例、原生 5m 边界稳定性，才有资格进入新的单组件正式版本。

## 不变边界

只用现有 2015—2020 development 行情，不新增、不重采样；主目标仍为中证1000原生 `5m_offset_0`，其他四个原生 5m 仅稳健性，1m 仅诊断。

不调资格硬阈值，不改 D1，不进入第三浪/收益/交易，不按收益选参数，不开放生产权限。

**PR #1 继续 Draft，不合并 main。**
