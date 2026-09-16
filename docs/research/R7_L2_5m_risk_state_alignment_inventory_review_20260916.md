# R7 × Layer2 5m risk-state alignment inventory — review

日期：2026-09-16

正式结论：`ALIGNMENT_SUPPORTED_FOR_STATE_CONDITIONED_DIAGNOSTIC`

## 执行审计

- valid run: `35045961422`
- job: `104635704272`
- execution head: `e519c0b8e30e479d491cc9aaf35bfea24e3554ea`
- 4/4 synthetic tests passed
- artifact id: `10427041303`
- artifact digest: `sha256:161e4befcc4c2d85c299c85cb0e5e65eb7283ebc24d33fca4c2ba8f0975b7e85`
- R7 future outcome read: false
- R7 model fit performed: false
- BLACKBOX / post-2020 Layer3 / PnL: false

v1 run `35045576776` stopped at receipt construction because Python used lowercase `false`; no receipt/outcome was printed. v2 run `35045769704` produced an outcome-blind alignment result and exposed one 2020 state mismatch out of 11,664 bars. The mismatch was traced to comparator initialization: Layer3's cross-repo comparator carried 2019 rolling history while frozen Layer2 V9's physical reference begins at the 2020 file boundary. The scientific gate remained exact 100%. v3 corrected only this comparator boundary; the full-history 2015–2020 consumer replay and all bucket/supply gates were unchanged.

## Cross-repository equivalence

With the same 2020 physical boundary:

- common 5m rows: `11664`
- close max absolute difference: `0.0`
- finalized risk-state agreement: `1.0`

Therefore the clean-room Layer3 replay reproduces the pinned Layer2 finalized 5m state semantics exactly on the available canonical overlap.

## Layer3 full-history replay

- input 5m rows: `70114`
- trading days: `1462`
- complete 48-bar days: `1459`
- excluded incomplete days: `2016-01-04`, `2016-01-07`, `2017-08-24`
- replayed rows: `70032`

R7 endpoint eligibility remains `64215` without reading future outcome. State matched rows=`64152`, fraction=`0.9990189208128942`.

## Fixed consumer buckets

Primary two-bucket map remains frozen:

- `LOW_RISK = NORMAL`
- `RISK_ACTIVE = UNSAFE or RECOVERING`

Three-state counts are retained for audit; no state threshold or mapping was selected from R7 outcomes.

| sample | LOW_RISK | RISK_ACTIVE | UNSAFE | RECOVERING |
|---|---:|---:|---:|---:|
| TRAIN | 37,955 | 4,769 | 1,629 | 3,140 |
| VALIDATION | 19,004 | 2,424 | 705 | 1,719 |
| 2019 | 9,678 | 1,058 | 289 | 769 |
| 2020 | 9,326 | 1,366 | 416 | 950 |

All predeclared supply gates pass.

## Permission consequence

Authorized next step: one frozen outcome-aware `R7_L2_5m_risk_bucket_calibration_diagnostic_v1` comparing the global R7 B1 against one low-capacity two-bucket interaction model fit on TRAIN and applied unchanged to VALIDATION / 2019 / 2020.

Not authorized: threshold search, alternative bucket remapping, use of unsupported Layer2 Phase-1 recovery probabilities, parameter grid search, BLACKBOX, post-2020 Layer3 outcome, PnL/Sharpe, paper trading, or production.
