# R7 native 1m rejected-excursion — cloud review

日期：2026-09-16

Identity：`R7_native_1m_rejected_excursion_v1`

## 1. Execution integrity

R7 preanalysis / protocol / runner / tests / execution freeze 均在任何 real-data R7 outcome 可见前冻结。

受控执行：GitHub Actions run `35041836335`，job `104623175080`，head `2b2b1b4781c87f3355a29531fb9c660a89b4ff1b`，conclusion=`success`。

- frozen synthetic tests：4/4 passed；
- frozen blobs 与 1m / 5m source SHA：passed；
- local resampling=false；M0 structure cache=false；R5-B1 feature=false；
- BLACKBOX=false；post-2020=false；PnL=false；fresh-OOS claim=false；production authority=false。

Artifact=`10425302159`，digest=`sha256:5d84bbf3382d36ff96e99f1107a8ee51ccd9d6626929c4aa791ea7ce27597c7f`。

## 2. Supply

总 candidates=`64,215`。

TRAIN=`42,787`；VALIDATION=`21,428`；2019=`10,736`；2020=`10,692`。

TRAIN positive/negative rejection=`8,692 / 8,864`；VALIDATION=`5,216 / 5,180`。

因此 `supply_supported=true`。

## 3. Coefficient direction

TRAIN-fit B1 rejection coefficient=`-0.5327696`。

Descriptive local B1 rejection coefficient：

- VALIDATION pooled=`-0.3954504`；
- 2019=`-0.3938415`；
- 2020=`-0.3969619`。

四组符号一致且均符合预注册 `<0`，所以 `coefficient_direction_supported=true`。

## 4. Fixed TRAIN prediction

固定 TRAIN-fit B0/B1 后：

- VALIDATION：MSE `1.6598473 -> 1.6349713`，relative improvement=`1.4987%`；
- 2019：`1.7444188 -> 1.7207890`，relative improvement=`1.3546%`；
- 2020：`1.5749278 -> 1.5488004`，relative improvement=`1.6590%`。

三组均改善，因此 `fixed_prediction_supported=true`。

## 5. Directional symmetry

相对 frozen TRAIN-B0 prediction：

- positive rejected excursion：n=`5,216`，mean residual=`-0.2192279`；
- negative rejected excursion：n=`5,180`，mean residual=`+0.2037727`。

两边都符合“路径 excursion 被拒绝后，下一段 residual 朝 excursion 反方向”的预注册机制。因此 `directional_symmetry_supported=true`。

## 6. Formal adjudication

`R7_supported_for_one_bounded_diagnostic`

R7 比 R5-B1 的原始增量更大，但仍然只是 reusable TRAIN/VALIDATION broad research，不是 fresh OOS、交易策略或 BLACKBOX qualification。

只授权一次 bounded diagnostic，用固定时间块与 feature-only magnitude bins 检查时间稳定性和连续强度形状。不得修改 R7 model/path/horizon/sigma，也不得直接进入 specialist、BLACKBOX、PnL 或复杂模型。
