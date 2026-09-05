# v0.5.3 前置：legacy raw-ER redundancy ablation POC 正式结果

日期：2026-09-06

状态：`legacy_raw_er_redundant_candidate`

操作基线仍为 **v0.4.3**。v0.5.2 exact-ridge hierarchy 仍是 parent-identity representation；本轮仅对冻结 v0.5.2 records 做 `inefficient_leg` 存在/不存在的只读职责消融，没有修改其它 qualification、D1、ledger、identity、收益或交易。

## 1. 正式证据

- protocol：`docs/research/two_wave_legacy_er_redundancy_ablation_protocol_v053.md`
- script：`scripts/run_two_wave_legacy_er_redundancy_poc_v053.py`
- workflow：`.github/workflows/two-wave-legacy-er-redundancy-poc-v053.yml`
- formal run：`33979045148`，**success**
- artifact id：`9973295802`
- artifact SHA256：`c354f97eff1f1f73aa319bf276cc07d660508c91b84b4fa6651b0ec9529b2bcc`
- full regression：**387 / 0 failures / 0 errors / 0 skipped**
- bounded package / frozen data validation：passed

代码内硬断言保证：

1. v0.5.2 record identity fields 完全不变；
2. 除 `inefficient_leg` 外 rejection reasons 逐条完全不变；
3. 原 qualified 全部继续 qualified；
4. newly-qualified 集合精确等于原 `reasons == ['inefficient_leg']`；
5. case_00 精确父候选删除 ER 后仍只剩 duration+jump，继续 rejected。

因此本轮变化可以严格归因于 legacy raw-ER gate 的存在/不存在。

## 2. 五视图数量变化——只作描述，不作为成功依据

| view | qualified v0.5.2 | no-ER | selected v0.5.2 | no-ER |
|---|---:|---:|---:|---:|
| o0 | 425 | 780 | 256 | 431 |
| o1 | 376 | 714 | 225 | 396 |
| o2 | 391 | 700 | 240 | 387 |
| o3 | 406 | 737 | 242 | 394 |
| o4 | 418 | 764 | 253 | 411 |

这些增长本身不是采用理由。真正关键的是新增对象的 hierarchy 结构、offset 稳定性和安全反例。

## 3. parent-like enrichment：五个 offset 全部强且方向一致

parent-like 事前代理固定为：`v043_excess_local_pivots_beyond_five > 0`。

### 3.1 qualified

| view | 原 qualified parent-like | newly-qualified parent-like | final qualified parent-like |
|---|---:|---:|---:|
| o0 | 31/425 = 7.29% | **109/355 = 30.70%** | 140/780 = 17.95% |
| o1 | 32/376 = 8.51% | **100/338 = 29.59%** | 132/714 = 18.49% |
| o2 | 31/391 = 7.93% | **105/309 = 33.98%** | 136/700 = 19.43% |
| o3 | 33/406 = 8.13% | **93/331 = 28.10%** | 126/737 = 17.10% |
| o4 | 32/418 = 7.66% | **101/346 = 29.19%** | 133/764 = 17.41% |

新增 qualified 的 parent-like 比例约为原 qualified 的 3.4–4.3 倍。

### 3.2 selected

| view | 原 selected parent-like | newly-selected parent-like | final selected parent-like |
|---|---:|---:|---:|
| o0 | 16/256 = 6.25% | **56/214 = 26.17%** | 68/431 = 15.78% |
| o1 | 22/225 = 9.78% | **47/201 = 23.38%** | 66/396 = 16.67% |
| o2 | 20/240 = 8.33% | **52/177 = 29.38%** | 69/387 = 17.83% |
| o3 | 13/242 = 5.37% | **40/184 = 21.74%** | 50/394 = 12.69% |
| o4 | 16/253 = 6.32% | **47/200 = 23.50%** | 61/411 = 14.84% |

新增 selected 也不是随机释放局部对象：parent-like 比例在五个 offset 上均显著高于原 selected。

同时 final selected 的 excess-micro p90 从 v0.5.2 的普遍 0 提升到：

- o0/o1/o2：2
- o3/o4：1

这正是此前 frozen qualification 把 hierarchy 吸收能力重新压回局部对象的问题方向。

## 4. offset stability：四项全部大幅改善

统一使用现有 1m timestamps 映射 `(start,end]` 所有权，不做价格重采样；IoU 只代表边界稳定性，不代表准确率。

| offset | v0.5.2 IoU | no-ER IoU | 变化 |
|---|---:|---:|---:|
| o1 | 31.53% | **43.33%** | +11.81 pct |
| o2 | 23.92% | **37.43%** | +13.51 pct |
| o3 | 27.51% | **40.04%** | +12.54 pct |
| o4 | 32.44% | **44.97%** | +12.53 pct |

四项全部改善，且幅度大于 v0.5.2 相对 v0.4.3 的改善。删除 raw ER 没有放大 native-5m slicing perturbation，反而让同一 hierarchy representation 在不同 offset 下的 published ownership 更一致。

owned fraction 从主 5m 的约 15.1% 上升到 28.2%；这不是准确率提升，只说明 ledger 最终发布更多结构，必须结合 parent-like enrichment 和安全反例共同解释。

## 5. 新增 published 对象并非主要来自极端低 ER 噪声

新增 selected 的 `min(raw leg ER)`：

- 各 offset median 约 `0.433–0.439`；
- p90 约 `0.487–0.494`；
- 绝大多数确实位于旧 0.5 门下方，符合单门消融定义；
- 但每个 offset `min ER < 0.25` 只有 **3–5 个**。

因此新增对象主要聚集在旧硬门附近，而不是大量灌入 `ER≈0` 的随机折返。

新增 selected 的 pair-duration median 约 48–50 bars；四腿 duration median 11 bars；birth level 主要集中在 **4–6**，不是大量 level-1 微结构。

这与 attribution 中 `inefficient_leg` single failure 在 level 5–6 增强的模式一致。

## 6. ledger replacement 没有抵消结构收益

no-ER 使部分更早确认的新对象通过 greedy ledger，从而挤掉部分旧 selected：

- o0 displaced 39
- o1 30
- o2 30
- o3 32
- o4 42

但最终 parent-like selected 仍从：

- o0 16 → **68**
- o1 22 → **66**
- o2 20 → **69**
- o3 13 → **50**
- o4 16 → **61**

所以改善不是只停留在 candidate/qualified 层，也能穿过原有确定性互斥 ledger。

## 7. 固定安全案例

### case_00

精确父级候选：

`[48720,48749,48754,48768,48801]`

删除 raw ER 后剩余 reasons 精确为：

- `corresponding_leg_duration_mismatch`
- `jump_dominated_leg`

仍 `scale_qualified=false / selected=false`。

这说明本轮没有通过“救 case_00”驱动结果，也确认单门隔离正确。

### case_02

- evaluated overlap：99
- qualified：**0**
- selected：**0**

旧 90/3 假浪没有复活。

### case_11

selected 4 个，都是局部/中尺度；最大示例 cycles `38/24`，没有跨数周巨型 five-point。

### case_14

selected 7 个；最大对象 cycles `48/46`，仍受原 max-cycle/max-pair/day/wall-span 等门约束，没有跨周巨型发布。

### 固定日期

- 2018-06-20：原 v0.5.2 selected uncertain 保留；
- 2019-04-15：仍 0 qualified / 0 selected；
- 2020-07-15：除原 downtrend 外，新出现一个 level-7、吸收 2 个额外微摆的 downtrend `[64491,64504,64532,64543,64567]`，cycles `41/35`；这是与 parent-like enrichment 一致的新增中尺度结构，而非超长异常。

## 8. 正式 POC 判定

按结果前协议，本轮判定：

**`legacy_raw_er_redundant_candidate`**

理由不是样本数增加，而是：

1. 单组件隔离硬门全部通过；
2. newly-qualified / newly-selected 在五个 offset 上都显著富集“吸收额外微摆”的 parent-like 结构；
3. final selected 的微摆吸收分布明显上移；
4. 四项 native offset IoU 全部大幅改善；
5. 新增 published 主要集中在旧 0.5 边界附近，而不是极端低 ER 噪声；
6. case_00 仍被其它冻结门拒绝，case_02 仍安全，case_11/14 不出现巨型回归；
7. D1–D4 已证明不存在一个既非 tautology、又不产生 phase/direction mismatch 的简单 same-scale ER 替代式。

因此下一步允许把：

> **在 v0.5.2 exact-ridge hierarchy 下删除 legacy raw `inefficient_leg` qualification gate**

写成真正 **v0.5.3 单组件结果前协议**。

但本 POC 仍不是正式 v0.5.3 recognizer。正式 v0.5.3 必须：

- 固化独立模块；
- 加 unit/isolation tests；
- 五 native 5m + 1m_official 共 18 次 prefix replay；
- 再次确认 offset / fixed safety audit；
- 不修改其它资格或 D1。

正式通过前，操作基线继续保持 **v0.4.3**。
