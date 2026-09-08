# v0.6.17 session-aware information-set bounds — 云端独立复核

日期：2026-09-08  
任务：`CL-20260908-005`  
本地回传 commit：`c96f50d8bbc2d08253bd4176791c87e3fcdf4bc3`

## 云端结论

本地执行从 `local_reported` 升级为：

`CLOUD REVIEWED / COMPLETED`

云端接受 frozen protocol 允许的正式裁决：

`session_aware_bounds_valid_but_structural_gap_nonidentifiability_is_material`

这是一项 **measurement / identifiability** 结论，不是 morphology acceptance，也不是交易或方向结论。

全局状态继续保持：

- operational baseline = `v0.4.3`；
- morphology = `morphology_replication_not_yet_accepted`；
- Direction / D1 / D2 / PAWCT / 第三浪 / outcome / PnL / fresh OOS / paper trading / production 均未解冻。

## 1. Frozen identity 复核

云端重新读取当前活跃分支并核对：

- preanalysis blob = `77f54c7a8e3699997450eaad941ed13b1e561b3a`；
- protocol blob = `f0f6acd06c7ccacd331ed9938f77ff68c9519cfa`；
- freeze commit = `61eba4c80215bb07375e59d3c53e8ac2b989ff28`。

未发现本地结果提交改写 frozen preanalysis / protocol。

本地 execution receipt 报告：

- execution surface = `local_codex_controller`；
- GitHub Actions = false；
- implementation base = `0edb9cf08b38141b68e513e58020fc8d5cbd8312`；
- `pytest -q tests/unit/test_two_wave_session_aware_information_set_bounds_v0617.py` exit 0，14 passed；
- formal runner exit 0；
- future outcome 未使用。

## 2. Authoritative source identity 复核

云端接受 source identity 与 CL-004 已验收 authority 一致：

- DataHub committed HEAD = `ba780790acd8e9a558e4e01f9474b6e79265d818`；
- accepted contract archive blob = `accb183f695880c5524f7263bfdfae1debe006a0`；
- symbol = `000852.SH`；
- source kind = `market_index_transaction_derived_1m`；
- source rows = `349,923`；
- date range = `2015-01-05..2020-12-31`；
- 2021+ rows loaded = `0`；
- FactorLab `1m_official` was not used as source support。

保留已有 provenance caveat：v8 目录下 hardlink 文件内部可能保留旧 `dataset_version` 字段；本 replay 沿用 CL-004 已验收的 hive-directory v8 identity，而不是用 hardlink 内残留列重新定义数据集。

## 3. Native 5m identity gate

五个 frozen views 全部 exact replay：

| view | rows | construction | missing/extra labels | OHLC mismatch |
|---|---:|---|---:|---:|
| offset0 | 70,114 | official v2 | 0 / 0 | 0 |
| offset1 | 67,192 | wall-clock v1 | 0 / 0 | 0 |
| offset2 | 67,192 | wall-clock v1 | 0 / 0 | 0 |
| offset3 | 67,193 | wall-clock v1 | 0 / 0 | 0 |
| offset4 | 67,191 | wall-clock v1 | 0 / 0 | 0 |

同时 empty support、last-support-close mismatch、assigned-close-outside-envelope 均为 0。

因此 source/native identity gate 通过。

## 4. Price-blind topology 与 pre-oracle checkpoint

云端复核本地 topology / execution receipt：

- native transitions = `338,877`；
- maximum actual support-source count = `6`；
- fully enveloped transitions = `327,189`；
- transitions containing actual unenveloped source rows = `11,688`；
- offset0 structural-gap transitions = `0`；
- offset1–4 各 `2,922`。

本地在读取 oracle 之前先持久化 bounds registry：

- rows = `737,104`；
- pre-oracle registry SHA256 = `824bbba91b666f49ea44717a6b8aed505e56998b0aadaeaa092e13a05c0e8dc9`；
- oracle prices read at checkpoint = false。

该顺序满足 frozen protocol 的关键 price-blind requirement。

## 5. Oracle coverage

正式 oracle replay：

- registered N vs actual fine-step mismatch = `0`；
- J coverage failure = `0`；
- C_inf / C_1 / C_2 coverage failure = `0`；
- defined oracle legs = `737,104`；
- full coverage fraction = `1.0`；
- undefined legs = `0`。

因此本轮不是 support-topology 或 oracle-coverage failure。

## 6. Structural-gap nonidentifiability 确认为 material

全部 published legs 中：

- fully enveloped legs = `528,360`；
- structural-gap / universal-bound legs = `208,744`；
- fraction = `0.2831947731`，约 `28.3%`。

这些 gap 并非“墙上时间过了几分钟”本身，而是真实存在、但没有落入当前 native bar envelope 的 source rows。按照 frozen protocol，只要 leg 含此类真实 source gap，就必须保留该 leg 并使用 universal interval，不能删除、并入邻 bar 或用 oracle 事后收窄。

全样本 J bound width：

- median ≈ `0.6900`；
- mean ≈ `0.6388`。

这说明即便 coverage 正确，native 5m OHLC 对细路径集中度的识别仍有实质上限；结构 gap 是其中一项明确且不可通过后验调参消除的来源。

## 7. 两组历史控制数的语义澄清

Frozen handoff 中还列了两个历史控制：

- v0.6.13 `fine profile defined = 737,070`；
- v0.6.10 `oracle-comparable strict pair-leg observations = 117,805`。

本地 v0.6.17 输出为：

- full published-leg bounds registry = `737,104`；
- current complete strict-pair × 4-leg product = `117,812`。

云端不把这两个差额判为 upstream behavioral drift，原因是：

1. 核心 upstream identity controls 原样复现：published identities `38,176 / 36,737 / 36,619 / 36,480 / 36,264`，strict pairs `8,381 / 5,770 / 6,204 / 9,098 = 29,453`，both-qualified `482`，qualification disagreement `699`，repairs `80 = 56 + 24`；
2. `737,070` 是旧 v0.6.13 的 **n>=2 fine-profile availability** 统计，而 v0.6.17 protocol 的 bounds registry 覆盖所有 `184,276 × 4 = 737,104` published legs，包括 N=1；
3. `117,805` 被完整保留为 frozen v0.6.10 historical overlay count；v0.6.17 当前完整 pair-leg product 是 `29,453 × 4 = 117,812`，没有拿新数字回写旧历史。

以后必须同时保留这两种语义，禁止把 `737,104/117,812` 伪称为旧历史 control，也禁止为了“对齐旧数”删除合法 v0.6.17 rows。

## 8. 项目级含义

v0.6.17 现在可以作为一个 **cloud-reviewed interval-valued measurement capability** 使用：

- 当 source support fully enveloped 时，允许使用 frozen finite bounds；
- 当存在 actual structural source gap 时，必须携带 universal / partial-identification uncertainty；
- 不允许把 interval 偷换成一个伪精确的 concentration point proxy。

这意味着未来任何依赖细路径效率、粗糙度、集中度的策略研究，都必须选择以下之一：

1. 使用被正式准入的真实 finer source surface；或
2. 把 interval / partial-identification uncertainty 显式带入研究。

不能仅凭 native 5m OHLC 假定细路径已知。

## 9. 最终权限

`CL-20260908-005 = CLOUD REVIEWED / COMPLETED`

接受 verdict：

`session_aware_bounds_valid_but_structural_gap_nonidentifiability_is_material`

但：

- morphology acceptance = false；
- operational baseline 仍是 v0.4.3；
- 不 promotion `H_end_5`；
- 不授权 concentration proxy / threshold；
- 不授权 direction / third-wave / outcome / PnL / fresh OOS / trading / production。
