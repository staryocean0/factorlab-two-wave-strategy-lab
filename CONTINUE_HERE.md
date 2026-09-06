# 两浪研究继续入口：v0.5.4 qualification 已正式通过，下一步独立研究 D1（2026-09-06）

## 当前状态

当前组合研究基线已经从旧 v0.4.3 升格为：

> **v0.5.2 TCSS exact-ridge parent identity + v0.5.4 full-cycle-scale qualification**

准确状态链：

**v0.5.0 TCSS representation ✅ → v0.5.1 sliding five-extrema scale selector ❌ → v0.5.2 exact-ridge parent identity ✅ → qualification attribution ✅ → v0.5.3 birth-scale TCSS ER hypothesis ❌ → v0.5.4 full-cycle-scale qualification ✅ → D1 range/trend pending。**

这里的 baseline 升格只表示下一阶段研究的上游 parent + qualification 已冻结；**整个两浪 morphology 尚未验收**，因为 D1 仍是旧层。

PR #1 继续 Draft，不合并 main；没有进入第三浪、收益、交易或生产。

## 优先阅读

1. [v0.5.4 最终 multiview / causal adjudication](docs/research/two_wave_cycle_scale_qualification_results_v054.md)
2. [v0.5.4 主 5m 机制审计](docs/research/two_wave_cycle_scale_qualification_results_v054_main5m.md)
3. [v0.5.4 结果前协议](docs/research/two_wave_cycle_scale_qualification_protocol_v054.md)
4. [v0.5.2 exact-ridge parent identity 正式结果](docs/research/two_wave_extremum_ridge_results_v052.md)
5. [qualification attribution](docs/research/two_wave_qualification_attribution_results_v052.md)
6. [v0.5.3 scale-aligned efficiency 否定结果](docs/research/two_wave_scale_aligned_qualification_results_v053.md)
7. [v0.5.0 TCSS 表示层结果](docs/research/two_wave_multiscale_tcss_results_v050.md)
8. [v0.5.1 自动尺度 selector 否定结果](docs/research/two_wave_characteristic_scale_results_v051.md)

## 金融合同不变

目标仍是：在某个 K 线级别上，识别**连续、同尺度、完整的两个原价格 reversal waves**，然后根据这两个波的整体漂移、同相位端点迁移和包络迁移区分父状态：

- range
- uptrend
- downtrend
- uncertain

生产语义仍是 raw-price reversal wave：

- 低点起算：`L0 -> H1 -> L1 -> H2 -> L2`；高点起算对称；
- 两个周期共享中间同相位端点；
- 严格单调 raw price 不得因为任何 detrended component 伪造 reversal；
- 已确认结构追加未来后不得改写；
- 计算确认时间和原数据 availability metadata 分开处理；
- coverage 不等于 accuracy；direction 不等于 channel；H16 不等于两浪 span。

## 已冻结上游 A：v0.5.2 parent identity

v0.5.2 已正式通过 `parent_identity_pass_qualification_pending`，其结论现在作为固定上游保留。

核心定义：

1. confirmed extremum 跨 TCSS scales 形成 immutable ridge identity；
2. 五点 parent family 由 exact five ridge IDs 定义；
3. child ridges death 后，exact tuple 首次成为连续五条 surviving ridges 的 scale 定义自然 birth；
4. parent birth 不由 `12—48` 绝对 bar-count 决定；
5. raw projection 回 exact raw-price extrema；
6. append future 不得改写 ridge / death / tuple / raw projection。

正式证据：

- five-view run `33976108720` success；artifact `9972596486`
- 1m run `33976118420` success；artifact `9972464179`
- 18/18 prefix replay 全部通过
- native 5m offset IoU 相对 v0.4.3 四项全部改善
- case_00 恢复能吸收多个微摆的 parent candidate identity
- case_02 90/3 假结构未复活

不得回头改 ridge linking / tuple birth 来修后续资格或 D1 问题。

## qualification attribution 与 v0.5.3 否定

v0.5.2 后先做了 rejection attribution，没有直接调阈值。

归因显示 `corresponding_leg_duration_mismatch` 存在大量 exclusive-only near-pass；与此同时 case_00 还混有 efficiency / jump 等其它拒绝，因此没有把所有资格问题偷换成一个阈值问题。

v0.5.3 尝试把 raw leg ER 换成 birth-scale causal TCSS ER，阈值仍为 0.5。主 5m 机制结果正式否定：

- v0.5.2 qualified 425 → v0.5.3 206
- lost qualified 292
- 2018 已通过的 24/29 父结构反而被 birth-scale ER 单独拒绝
- case_00 没有改善

所以 **birth-scale TCSS leg efficiency 不是当前资格语义的正确修复**，不得通过调低 0.5 复活该路线。

## 已冻结上游 B：v0.5.4 full-cycle-scale qualification

v0.5.4 的唯一语义变化：

> `corresponding_leg_duration_mismatch` 从 same-scale hard rejection 降为 morphology diagnostic。

理由：同尺度应优先约束两个**完整 reversal cycles** 的总时间尺度；对应半浪的时间占比可以因为 phase allocation、趋势漂移、局部速度不同而明显变化。

未改变：

- full-cycle `duration_ratio = 2.0`
- min/max cycle
- min/max pair
- min leg
- amplitude
- raw path efficiency `>=0.5`
- jump share `<=0.5`
- flat / clock / confirmation
- TCSS / ridge / tuple / raw projection
- D1 / ledger

### 主 5m

正式 run `33984455043` success；artifact `9974744445`。

`5m_offset_0`：

- evaluated 38,049
- v0.5.2 qualified 425
- v0.5.4 qualified 734
- newly qualified 309
- lost qualified 0
- 新增集合严格等于事前冻结的 corresponding-leg duration-only 集合

数量增加不是接受理由；接受理由是单组件 attribution、完整周期 hard gate 保留及安全反例不退化。

### 五个 native 5m

正式并行 run `33998425000` success。

final artifact：

- id `9978815239`
- SHA256 `0ef8ac22b4b69befd39d1b5e516b3c95bd3f396976cdbc5a7f0b8352515998cf`

五视图 full + 25/50/75%：**15/15 prefix zero rewrite**。

Offset IoU（仅边界稳定性）：

| offset | v0.5.2 | v0.5.4 | delta |
|---|---:|---:|---:|
| 1 | 31.53% | 36.79% | +5.26 pct |
| 2 | 23.92% | 31.34% | +7.42 pct |
| 3 | 27.51% | 31.21% | +3.71 pct |
| 4 | 32.44% | 35.10% | +2.66 pct |

`worse_count=0`，mean delta = +4.760 pct。

### 1m official

单 job run `33998434083` 在 package validation 和 full regression 都成功后，于核心 full+prefix 计算阶段被取消，没有形成正式结果，因此不参与裁决。

只拆 CI 调度、不改研究实现后：

- parallel run `33999025314` — success
- execution commit `c4ad36e5707c8233ef3076c5d9e2c95d1b31216d`
- final artifact `9979148052`
- SHA256 `5104f4dac1432efa582f6a95e8ea38c2a5e58ee1c27395ca5c6c88461fe97949`

1m 25% / 50% / 75% 三个 prefix：**3/3 zero rewrite**。

因此整个 v0.5.4：

> **18/18 prefix zero rewrite，正式通过 multiview causal/stability adjudication。**

## v0.5.4 最终资格门

冻结协议八项条件全部 PASS：

1. parent identity exact match；
2. 非 corresponding-leg rejection 全冻结；
3. 18/18 prefix zero rewrite；
4. full-cycle scale hard rules 不退化；
5. jump / short / efficiency / amplitude 不联动放松；
6. case_02 90/3 pathology 不复活；
7. native 5m offset stability 不恶化，实际 4/4 改善；
8. 机制解释来自 scale / phase-allocation 解耦，而不是候选数量增加。

所以后续不再使用 v0.5.2 的 corresponding-leg duration hard rejection 作为研究资格基线，也不回滚到 v0.4.3 parent construction。

## 仍未解决：D1

当前 qualification 通过不代表 D1 正确。

现有输出仍表现出：

- `uncertain` 较多；
- `range` 极少；
- direction 与 channel 语义仍需要拆分；
- 对应半浪 duration diagnostic、中心漂移、同相位 extrema 迁移、upper/lower envelope 漂移、幅度变化之间的关系尚未独立归因。

下一轮禁止直接调 `phase_tolerance` 或其它 D1 阈值。

## 下一安全停点：D1 semantic attribution / preanalysis

代码前先回答金融语义：

> 在已经确认的两个完整、同尺度 reversal cycles 上，什么数学量真正对应“父级震荡 vs 上涨趋势 vs 下跌趋势”，哪些量只是波形不对称或速度差？

建议下一轮先做**只读 D1 failure attribution**，冻结 parent + qualification，不修改输出：

1. 分解现有 D1 的每个组成项及其冲突来源；
2. 对 qualified records 统计 range/up/down/uncertain 形成路径；
3. 分离 center drift、same-phase endpoint drift、upper-envelope drift、lower-envelope drift、amplitude drift、phase allocation；
4. 审计 `uncertain` 是“信息不足”还是“规则互相冲突”；
5. case_00 / 2018 / 2019 / 2020 与 case_02/11/14 只做固定审计，不用于选参数；
6. 五个 native 5m 边界稳定性继续作为稳健性门，不当准确率；
7. 先形成金融语义映射和数学预分析，再冻结一个单组件 D1 协议。

若 D1 通过，才进入独立 morphology acceptance；**仍然不进入收益/交易。**

正确顺序：

**v0.5.2 parent identity ✅ → v0.5.4 qualification ✅ → D1 range/trend → independent morphology acceptance → H1/H2 → outcomes/trading。**

## 不变边界

- 只用仓库现有 2015—2020 development 行情；
- 不新增 fresh OOS，不价格重采样；
- 主目标 `000852.SH` 原生 `5m_offset_0`；其余 native 5m 只作边界稳健性，1m 只作诊断；
- `trade_authority=false`；
- 不按收益选参；
- 负向实验原样保留；
- **PR #1 继续 Draft，不合并 main。**
