# v0.5 TCSS 多尺度父级表示 POC：正式结果

日期：2026-09-05

状态：`representation_level_pass_not_parent_recognizer_accepted`

操作基线：**v0.4.3（不变）**

本结果只回答 time-causal scale-space (TCSS) 是否值得继续作为父级数学表示候选；不建立 v0.5 新基线，不改资格/D1，不进入第三浪、收益、交易或生产。

## 1. 结果前协议与正式证据

结果前研究文件：

- `docs/research/two_wave_multiscale_pre_research_v050.md`
- `docs/research/two_wave_multiscale_poc_protocol_v050.md`

核心实现：

- `src/factor_lab/visual_structure/two_wave/multiscale_v050.py`
- `tests/unit/test_two_wave_multiscale_v050.py`
- `scripts/run_two_wave_multiscale_tcss_poc.py`
- `scripts/run_two_wave_multiscale_tcss_poc_fast.py`

正式执行 HEAD：`373d15a51ca14cc30f1979e49315e5e044e2bc0b`

正式 GitHub Actions：**run `33966220967`，success**。

正式 artifact：

- artifact id：`9969542304`
- name：`two-wave-multiscale-tcss-v050-373d15a51ca14cc30f1979e49315e5e044e2bc0b`
- bytes：`60,589`
- SHA256：`7a8ea5312371fe3c9fcfeeaaedab2f19f5813f3be62e5bae874beeb9e7934a9b`
- expires：`2026-10-05T12:33:08Z`

测试：**371 tests / 0 failures / 0 errors / 0 skipped**。

包边界校验通过：14 个冻结数据产品，749,337 行，2015-01-05 至 2020-12-31；`fresh_oos=false`、`production_authority=false`、`registered_use_authority=false`。

## 2. 本轮真正验证的数学假说

v0.4.4 的失败不是“候选太多”，而是所谓父级并没有真正吞掉造成碎片化的微摆：父周期与两周期候选的 `collapsed_local_pivots` 中位数均为 0。

TCSS 本轮测试的是不同的层级机制：

> 价格经过一个事前冻结、严格单边递归的尺度空间；随着尺度增加，细尺度极值应逐步消失，而较粗结构继续存活。父级身份来自同一尺度层，而不是“第一次达到 12 根就闭合”。

14 层尺度格在真实结果生成前已经冻结，为 0.5 根起步的半倍频程几何格。这里的 `sigma` 是因果平滑核的标准差，不是周期长度、父腿长度，也不是旧 `12—48` 的变形。

首轮金融语义继续是 **raw-price reversal wave**。严格单调 raw price 合成硬门必须输出 0 个完整两浪；残差/模态中的 detrended cycle 不允许冒充原价格反转。

## 3. 因果性：通过

六个冻结视图：

- `5m_offset_0` ... `5m_offset_4`
- `1m_official`

每个视图分别执行 25% / 50% / 75% 固定前缀，共 **18 次**。

对每个前缀、每个尺度，逐字段比较：

- TCSS scale-space 数值；
- 已确认 extrema；
- 已确认 two-wave candidates。

正式结果：**18/18 全部通过，confirmed rewrite count = 0。**

这说明当前递归实现没有依靠未来样本回填历史。滤波延迟没有做离线左移补偿。

## 4. 真正层级粗化：通过，而且与 v0.4.4 有本质差别

### 4.1 主 5m 极值随尺度严格减少

`5m_offset_0` 的 14 层 extrema 数：

`28667 -> 24679 -> 19451 -> 14231 -> 9819 -> 6803 -> 4789 -> 3291 -> 2235 -> 1579 -> 1107 -> 801 -> 599 -> 427`

coarsest / finest = **1.4895%**。

其余原生 5m 也全部严格粗化：

- offset_1：`27657 -> 415`，1.5005%
- offset_2：`27655 -> 415`，1.5006%
- offset_3：`27579 -> 415`，1.5048%
- offset_4：`27327 -> 415`，1.5186%

1m 诊断：`80957 -> 1955`，2.4149%。

这不是准确率指标，但证明表示本身确实建立了一个有序粗化族，而不是 v0.4.4 那种“父级名称改变、内部微摆基本没有被折叠”。

### 4.2 v0.4.3 细极值 audit overlay 证明微摆真的被父层吸收

在 `5m_offset_0`，对每个 TCSS 两浪区间统计其内部覆盖的 v0.4.3 已确认局部极值，并计算“超过五个父级 extrema 之外的额外旧局部极值”。

额外 v0.4.3 局部极值中位数：

- sigma 0.5—4：0
- sigma 5.6569：**1**
- sigma 8：**4**
- sigma 11.3137：**7**
- sigma 16：**13**
- sigma 22.6274：**20**
- sigma 32：**29**
- sigma 45.2548：**42**

并且 sigma 5.6569 有 1,982 个候选、sigma 8 有 1,873 个候选内部至少吸收 1 个额外 v0.4.3 局部极值。

因此 TCSS 已经回答了 v0.4.4 最关键的失败问题：**父级粗化在表示层确实发生了。**

## 5. case_00：出现了目标机制，但不能据此事后选尺度

旧 case_00 审计区间为 `[48720, 48801]`。细尺度仍表现为局部碎片：

- sigma 0.5：top `13/6`
- sigma 0.707：top `13/6`
- sigma 1：top `13/14`

随着尺度增加，结构系统性变粗：

- sigma 1.414：`19/21`
- sigma 2：`20/21`
- sigma 2.828：`22/43`
- sigma 4：`34/43`
- sigma 5.657：`35/42`
- sigma 8：`37/51`

与旧 case 区间的审计 IoU（**只用于定位，不是模型选择**）在 sigma 4 达到约 0.859；sigma 5.657 约 0.795。

这说明 v0.4.4 没有做到的事情现在出现了：**微摆不是继续各自形成父周期，而是在更粗尺度被吸收，从而形成跨度更大的两个完整波。**

但本轮协议明确禁止从 case_00 结果反推“sigma=4 最好”。因此这里的正确结论不是“选 sigma=4”，而是：

> TCSS 已证明存在一个能重构目标大结构的尺度区间；下一问题是能否在不知道 case_00 标签、也不看 D1/IoU/收益的情况下，事前、在线、因果地选择 characteristic scale。

## 6. 三个固定窗口：TCSS 避免了 v0.4.4 的“只删除坏对象”问题

### 2018-06-20

中间尺度出现：

- sigma 1.414 / 2：`17/18`
- sigma 4：`24/27`
- sigma 5.657：`19/25`

说明规整的局部结构可以在尺度空间继续存在/粗化。本轮不重跑资格；原 `inefficient_leg` 仍是以后独立资格阈值实验。

### 2019-04-15

v0.4.4 在这里变成 `0候选/0父周期`，属于删除坏对象而不是重构父级。

TCSS 中间尺度则出现：

- sigma 1：`15/13`
- sigma 1.414：`16/13`
- sigma 2：`25/23`
- sigma 2.828 / 4：`25/42`

因此至少在表示层，TCSS 没有通过“删空”获得改善，而是给出持续粗化的结构族。

### 2020-07-15

v0.4.4 曾丢掉 v0.4.3 原有的合格 downtrend 对象。

TCSS 中间尺度仍存在大量可解释结构，例如：

- sigma 2：`18/27`
- sigma 2.828：`39/28`
- sigma 5.657：`41/40`
- sigma 8：`42/39`
- sigma 11.314：`39/41`

本轮没有把这些重新送入资格/D1，因此不能声称恢复了原 downtrend 发布；只能确认表示没有像 v0.4.4 那样把该区域直接删空。

## 7. 为什么 TCSS 仍然不能升级成“父级识别器”

### 7.1 最大未解决问题：characteristic-scale 选择

TCSS 当前输出整个尺度空间，而用户金融需求最终需要一个可审计的父级尺度身份。

case_00 的中间尺度很有吸引力，但**事后看 case_00 选 sigma 会构成数据窥探/反例定制**。

必须先冻结一个只使用截至当时信息的自动尺度选择/尺度持久性规则，例如 time-causal scale selection 或跨尺度 extrema persistence。该规则必须在任何下一轮 case 结果生成前写入协议。

### 7.2 巨型结构仍存在于很粗尺度，这是尺度空间的正常现象，不是已经解决的安全性

因为本轮故意输出全部尺度，所以 case_11 / case_14 在非常粗层自然能形成数百根的五点结构。例如 case_14 在 sigma 32 的审计对象可达到约 `401/602`。

这并不等价于 v0.4.3 安全性回归，因为当前没有“发布这些粗尺度对象”；但它明确说明：**如果 characteristic-scale 规则选错尺度，跨数周巨型五点会重新成为风险。**

因此 case_02、case_11/14 的生产安全门目前状态应记为 `unresolved_until_scale_selection`，不能提前写成 pass。

### 7.3 原生 5m 跨 offset 的最终“结构边界 IoU”尚不能被合理定义为生产指标

五个 offset 在每一尺度的 extrema 粗化都高度一致，coarsest extrema 都约为 415，说明表示计数层面稳定；但当前每个尺度仍有大量重叠 two-wave candidates，没有一个事前冻结的唯一/互斥父级发布层。

如果把所有重叠候选直接并成 coverage mask，几乎必然得到没有判别力的高覆盖；如果事后给每个 main candidate 挑最高 IoU counterpart，又会引入新的匹配自由度。

因此本轮不伪造一个看似完整的“offset IoU”。正确顺序是：**先冻结 characteristic-scale + 互斥/发布语义，再复用既有 1m 时间戳映射计算跨 offset 边界稳定性。**

这属于尚未完成的晋级门，而不是失败后删除指标。

## 8. 延迟成本：必须继续作为硬约束

TCSS 是因果的，但不是零延迟。正式结果记录的累计核平均年龄随尺度增长：

- sigma 2：约 2.40 bars
- sigma 4：约 6.33 bars
- sigma 5.657：约 9.86 bars
- sigma 8：约 15.04 bars
- sigma 11.314：约 22.56 bars
- sigma 16：约 33.38 bars
- sigma 45.255：约 102.53 bars

此外还有 extrema 反转确认延迟。

因此 characteristic-scale 规则不能只追求“形状最好看”；必须把实时可用延迟作为独立成本报告，不做历史左移。

## 9. 阶段判定

TCSS 本轮判定：

**`promotable_raw_reversal_representation_candidate`**

但严格限定为“表示候选”，不是已接受的父级识别器，更不是 v0.5 基线。

已经通过：

- raw-reversal 合成语义硬门；
- 严格因果递归实现；
- 18 次固定前缀零重绘；
- 尺度增加时真实、严格的极值粗化；
- v0.4.3 微摆在父层被实质吸收；
- case_00 / 2019 等窗口出现了机制上预期的从碎片到较大结构的连续尺度演化。

尚未通过/尚未定义：

- 事前因果 characteristic-scale 选择；
- 选择后的 case_02 / case_11/14 生产安全性；
- 选择后的五个原生 5m 边界稳定性；
- 资格层/D1（本轮故意冻结，未验证）。

所以**当前操作基线继续是 v0.4.3。**

## 10. 下一轮冻结顺序

不要现在从 case_00 挑 sigma，也不要立即把 TCSS 写成 v0.5 新 recognizer。

下一轮应并行做两件事：

1. **TCSS characteristic-scale / cross-scale persistence 预研究**：优先研究 time-causal scale selection、尺度归一化 temporal derivatives、extrema persistence 等能够只依赖过去信息的自动尺度身份；先协议，后代码。
2. **继续竞争路线 tSSA / causal wavelet/filter-bank 的独立 POC**：它们必须使用已经冻结的 raw-reversal / detrended-cycle 语义分流和 prefix 门，不能在看到 TCSS 结果后调整金融目标。

只有某条路线最终同时解决“表示 + 自动尺度身份 + 安全反例 + offset 稳定性”，才有资格进入一个新的单组件正式版本。

## 11. 不变边界

- 不新增/下载/重采样行情；
- 不进入 fresh OOS；
- 不按收益、第三浪命中率或交易表现选方法/尺度；
- 不调资格硬阈值；
- 不改 D1；
- PR #1 保持 Draft；
- 不合并 main；
- 不开放真实交易或生产权限。
