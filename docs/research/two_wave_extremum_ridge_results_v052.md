# v0.5.2 TCSS Extremum Trajectory / Exact-Ridge Tuple：正式结果与判定

日期：2026-09-06

状态：`parent_identity_pass_qualification_pending`

操作基线：**v0.4.3（不变）**。v0.5.2 只通过了“父级结构 identity / topology 能否稳定送入 raw-price candidate layer”这一层；**没有升级为新的完整 recognizer 基线**，也没有进入第三浪、收益、交易或生产。

## 1. 冻结研究问题

结果前协议：`docs/research/two_wave_extremum_ridge_protocol_v052.md`。

唯一组件变化：将 v0.5.1 的跨尺度 five-extrema sliding candidate-window identity 改为：

1. 单个 confirmed extremum 的跨尺度 causal ridge identity；
2. exact five-ridge tuple；
3. 内部 child ridge death 后 exact tuple 首次成为连续五条 ridge 的自然 birth scale。

`12—48`、raw projection、v0.4.3 qualification、D1、non-overlap ledger 全部冻结，不参与 ridge linking / tuple birth。

## 2. 正式执行证据

### 2.1 原六视图 run

- run：`33973525292`
- 完整 regression：`387 tests / 0 failures / 0 errors / 0 skipped`
- 五个 native 5m full runs 均完成；lineage anomaly 全部为 0
- 随后进入 `1m_official` 重建时 runner 收到 shutdown signal，exit 143

因此该 run 的失败是执行编排/runner shutdown，不是研究断言失败。为避免把执行问题误判为研究失败，后续只拆 CI 证据包，不改数学代码和判据。

### 2.2 five-view 正式包

- run：`33976108720`，**success**
- artifact id：`9972596486`
- artifact SHA256：`7db037db6d21d42f37120a289b156156bd9af795f69e58e2d4b3a37b47bdb4b5`
- regression：`387 / 0 / 0 / 0`
- `5m_offset_0..4 × 25/50/75% = 15` 次 prefix replay：**全部逐字段通过，confirmed rewrite count=0**

### 2.3 1m causal diagnostic 正式包

- run：`33976118420`，**success**
- artifact id：`9972464179`
- artifact SHA256：`ba597667d0f8d6af39509713b7e2bba1cd021da3fc756ce943e4cd48d6b9bc82`
- `1m_official × 25/50/75% = 3` 次 prefix replay：**全部通过**
- lineage anomaly：0

合并两个独立证据包，原协议要求的 **18 次真实 prefix replay 全部通过**。

## 3. 五个 native 5m：ridge lineage 无异常

| view | tuple births | evaluated | frozen-v0.4.3 qualified | selected | lineage anomalies |
|---|---:|---:|---:|---:|---:|
| offset_0 | 38,636 | 38,049 | 425 | 256 | 0 |
| offset_1 | 37,176 | 36,624 | 376 | 225 | 0 |
| offset_2 | 37,062 | 36,499 | 391 | 240 | 0 |
| offset_3 | 36,937 | 36,378 | 406 | 242 | 0 |
| offset_4 | 36,689 | 36,164 | 418 | 253 | 0 |

没有出现“coarse extrema 大规模凭空生成、无法继承 fine ancestor”的正常化现象。

## 4. 原生 5m offset 稳定性：四项全部改善

IoU 仅用于边界稳定性，不是准确率。

| offset | v0.4.3 IoU | v0.5.2 IoU | 变化 |
|---|---:|---:|---:|
| offset_1 | 26.42% | **31.53%** | +5.10 pct |
| offset_2 | 20.27% | **23.92%** | +3.66 pct |
| offset_3 | 22.86% | **27.51%** | +4.65 pct |
| offset_4 | 28.00% | **32.44%** | +4.44 pct |

这与 v0.5.1 的“四项全部系统性下降”方向相反，说明 exact-ridge identity 至少没有把 native 5m slicing perturbation 放大成新的 candidate-window identity 滑移。

## 5. case_00：父级 identity 已恢复，但冻结资格仍拒绝

旧固定区间 `[48720,48801]`：

- tuple birth overlap：80
- evaluated overlap：83
- qualified：0
- selected：0

关键变化不是数量，而是最接近旧父结构的 exact-ridge candidate：

- birth sigma：约 `4`
- raw five points：`[48720,48749,48754,48768,48801]`
- cycles：`34 / 47`
- legs：`29 / 5 / 14 / 33`
- reference interval IoU：`1.0`（只作固定审计，不参与 model selection）
- internal child deaths：2
- prior internal ridges：7
- v0.4.3 excess local pivots beyond five：**4**

v0.5.1 在这里主要得到的是错位后的 `19/38, legs 5/14/33/5`，以及更粗的 `57/30, legs 52/5/5/25` family。v0.5.2 已恢复到以旧区间起点 `48720` 开始、并真实吸收多个局部微摆的 parent-scale candidate。

该 candidate 当前被 frozen qualification 拒绝：

- `corresponding_leg_duration_mismatch`
- `inefficient_leg`
- `jump_dominated_leg`

所以当前失败已经从“父级 identity 错位”下移到资格层；不能再通过修改 ridge identity 来救它。

## 6. 微摆吸收：candidate 层恢复，但 frozen qualification 仍偏向局部对象

主 5m offset_0：

- qualified with absorbed v0.4.3 micro pivots：`31 / 425`
- selected with absorbed micro pivots：`16 / 256`
- selected excess pivots：median `0`、p90 `0`、p99 `2`、max `6`

对比 v0.5.1：最终 45 个 selected 中只有 4 个吸收任何额外微摆，median/p90 均 0、max 2。

v0.5.2 的上限和绝对数量明显恢复，且 case_00 可直接看到 +4 微摆的父级结构；但 **selected median/p90 仍为 0**，说明 frozen qualification / ledger 最终仍主要放行局部对象。因此不能把 v0.5.2 宣称为完整形态验收。

1m diagnostic 也给出相同方向的辅助证据：2,573 selected 中 443 个吸收额外 v0.4.3 微极值，p90=2、max=8。

## 7. 固定窗口与安全反例

### 2018-06-20

恢复一个 qualified/selected 对象：

- raw `[40397,40408,40421,40442,40450]`
- cycles `24/29`
- classification `uncertain`

说明 v0.5.1 的 characteristic-window identity 错位已不再是这里的主问题。

### 2019-04-15

58 evaluated / 0 qualified / 0 selected。结构已进入 exact-ridge candidate layer，但资格仍未放行。

### 2020-07-15

恢复一个 qualified/selected downtrend：

- raw `[64581,64605,64611,64642,64654]`
- cycles `30/43`

### case_02

旧 90/3 假浪没有复活：99 evaluated / 0 qualified / 0 selected。

### case_11 / case_14

没有发布跨数周巨型五点；发布对象仍是局部/中尺度结构。安全反例未出现 v0.4.3 之前的结构性回归。

## 8. 正式判定

按 v0.5.2 结果前协议，本轮判定为：

**`parent_identity_pass_qualification_pending`**

原因：

1. 18 次真实 prefix 全过；
2. 六视图所见 lineage anomaly=0；
3. case_00 的 parent candidate identity 明显恢复，并能审计到内部 child-ridge death / 微摆吸收；
4. 2018/2020 中间尺度结构重新进入 qualification / publication；
5. case_02 90/3 不复活，case_11/14 不出现巨型跨周发布；
6. 四项 native 5m offset IoU 全部高于 v0.4.3，而不是 v0.5.1 的系统性恶化；
7. 但最终 selected 的微摆吸收 median/p90 仍为 0，case_00 与 2019 等仍被 frozen qualification 拒绝。

因此：

- **TCSS exact-ridge hierarchy route 不止损；**
- **v0.5.2 作为 parent-identity representation 被保留；**
- **完整 recognizer 操作基线仍为 v0.4.3；**
- 下一轮只能研究 qualification 的一个独立数学组件；
- 不允许回头调 ridge linking / tuple birth 来补资格失败。

## 9. 下一步：先做 qualification failure attribution，不直接调阈值

旧 `two_wave_qualification_preanalysis_v052.md` 提出了 `same-scale leg efficiency`，但它是基于 v0.5.1 结果写的 conditional preanalysis。v0.5.2 新结果显示 case_00 同时存在 duration mismatch、inefficient leg 和 jump dominated 三类拒绝，不能机械认定 efficiency 就是下一唯一主因。

因此 v0.5.3 协议冻结前先做**只读失败归因**，对 v0.5.2 固定 candidate 统计：

- rejection reason frequency；
- 单一失败原因频次；
- leave-one-reason-out 的反事实新增 qualified 数；
- 按 birth scale / absorbed-micro-pivot 分层；
- 固定 cases/windows 的 reason decomposition。

这一步不得修改任何阈值、公式、D1、ledger 或 candidate identity。只有归因结果明确后，才冻结 v0.5.3 的单组件假说。
