# 两浪研究继续入口：v0.6.0 qualified identity 正式裁决 Route M（2026-09-06）

## 当前安全状态

冻结上游仍是：

> **v0.5.2 TCSS exact-ridge parent identity + v0.5.4 full-cycle-scale qualification**

操作基线仍为 **v0.4.3**。全局状态仍为：

`morphology_replication_not_yet_accepted`

PR #1 保持 Draft，不合并 main。禁止进入 H1/H2、第三浪、收益/P&L、fresh OOS、paper trading 或 production；`trade_authority=false`。

## 当前研究链

**v0.5.0 TCSS representation ✅ → v0.5.1 sliding family ❌ → v0.5.2 exact-ridge identity ✅ → v0.5.4 full-cycle qualification ✅ → v0.5.5 D1 attribution → v0.5.6 D2 multiview ❌ → v0.5.7b endpoint-D2 ❌ → v0.5.8 PAWCT selected-output R1 ❌ → v0.5.9 证明旧 direction adjudication 被 event-identity confound 主导 → v0.6.0 qualified financial identity / exclusive packing 解耦 → five-view frozen replay 正式裁决 **Route M**。**

正式结果：`docs/research/two_wave_qualified_identity_results_v060.md`。

## v0.6.0 本地 replay 已被云端验收

本地任务：`CL-20260906-002`。

- frozen research commit: `4643133f518299d6710f3c1cc01b6399b9482c31`
- local execution commit: `a45a3a986df80228daa500af3c95e67c7f475ff5`
- local result commit: `2d41cba048d8c62d0aca19ac501764a03082941c`
- 云端正式结果 commit: `7e090de73309b61d4c592fae3883149474dff233`
- frozen research diff check: 研究文件无漂移；execution commit 相对 frozen 只多 `AGENTS.md` 与交接文档
- 五个 parquet 的 SHA256 / bytes / rows / date range 与 frozen `data/manifest.json` 一致
- 2015-01-05—2020-12-31 development only
- 未本地 resample；无 2021+；fresh OOS=false
- focused governance + v0.6.0 tests: **37 passed**
- v0.6.0 runner: exit 0
- `validate_theme_package.py` exit 1 仅因后加入的 `AGENTS.md` handoff protocol 造成 source-closure drift；不是研究实现或输入 drift，云端已用 commit comparison 独立确认

raw qualified counts 完全复现冻结 checkpoint：

`734 / 691 / 691 / 721 / 746`

canonical identities：

`712 / 673 / 678 / 700 / 728`

legacy selected identities：

`404 / 371 / 382 / 392 / 392`

## 因果 gate 已通过

v0.6.0 新 identity-event stream：

- 5 views × 25% / 50% / 75% = **15/15 prefix checks passed**
- confirmed rewrite count = **0**
- later same-anchor scale evidence 只能 append，不改写已发布 financial identity

这说明 v0.6.0 identity publication 本身满足当前 frozen causal requirement。

## 正式 cross-view 结果

严格 same-event relation 仍然只允许：

- same start phase；
- ordered five raw-extremum occurrence timestamps 逐位置比较；
- 五个 delta 全部 `<= 5 minutes`；
- mutual-unique only；
- ambiguity 不 tie-break；
- D1/D2/PAWCT/IoU/amplitude/outcome 不参与 identity matching。

### all canonical qualified

| pair | strict matches | main match | ambiguous main/other | main unmatched | hidden by legacy packing | hidden fraction |
|---|---:|---:|---:|---:|---:|---:|
| offset0 vs 1 | 180 | 25.28% | 1 / 1 | 531 | 109 | 60.56% |
| offset0 vs 2 | 129 | 18.12% | 0 / 0 | 583 | 75 | 58.14% |
| offset0 vs 3 | 129 | 18.12% | 1 / 0 | 582 | 74 | 57.36% |
| offset0 vs 4 | 184 | 25.84% | 1 / 1 | 527 | 104 | 56.52% |

### legacy selected-only

strict matches：

`72 / 54 / 55 / 81`

main match fractions：

`17.82% / 13.37% / 13.61% / 20.05%`

因此 canonical qualified identity 明显比 legacy selected-only 更完整；但是 main canonical universe 在四个 harmless offsets 上仍约 **74%–82% unmatched**。

## 为什么正式裁决是 Route M

### packing 确实有结构性污染

现有 strict qualified matches 中，**56.52%–60.56%** 会被 legacy exclusive packing 隐藏。并且 all-qualified strict matches 在四组比较中都远高于 selected-only。

所以：

> **exclusive packing 永久保持 downstream；它不能重新取得 morphology identity authority。**

### 但 packing 不是唯一问题

四个 offset 中 canonical qualified 的 main strict-match coverage 只有约 **18.1%–25.8%**。绝大多数 identity 没有 strict counterpart。

同时 ambiguity 几乎为零，因此问题不是 evaluator 的多匹配/tie-break，而是：

> **harmless slicing 改变后，大多数 frozen qualified financial identities 本身没有形成同一五-anchor local identity。**

这正好符合冻结 protocol 的 Route M：

> packing hides substantial stable identities, but qualified identity remains materially unstable.

Route Q 被拒绝；不能回到 direction adjudication。

Route U 单独也不完整，因为 packing 确实隐藏了大量已经稳定存在的 strict identities。

## D1/PAWCT 当前权限

在已经 strict matched 的 qualified pairs 上，D1 same-label 为约 **95.1%–96.9%**。这个现象值得保留，但只允许作为 diagnostic。

**不得据此 promotion D1、D2 或 PAWCT。**

v0.5.9 已证明 selected-output 旧失败混入 identity confound；v0.6.0 又证明 identity coverage 本身还没过关。因此 direction 仍被冻结。

## 下一研究前沿

下一步不是发明新的 direction formula，也不是直接调 ridge/qualification 参数。

应先做一个**冻结的 unmatched-identity decomposition audit**，回答：为什么约 74%–82% canonical main identities 在 harmless 5m offsets 上没有 strict same-event counterpart？

建议 decomposition 至少区分：

1. phase mismatch；
2. candidate/anchor topology 不同（无法形成对应五 extrema）；
3. 五个 ordered anchors 存在近邻，但一个或多个 occurrence displacement > 5m；
4. same/near anchors 在另一 slicing 出现，但被 scale qualification survival 改变；
5. birth-scale / ridge family evidence 路径不同；
6. genuinely different parent family；
7. 数据/session boundary 造成的可解释 slicing edge effect。

**先冻结 decomposition relation 和报告口径，再看结果。** 不得看完 near-miss distribution 后倒推阈值去“提高匹配率”。

现在本地已把五个 view 的完整 `canonical_qualified_identities.json` / causal events / evidence events 提交到仓库，因此上述一部分只读 decomposition 可以由云端直接做；若需要回到 raw bars/qualified ledger body 而当前云端仍无法读取 parquet，则再按 `AGENTS.md` Protocol 1/2 写新的本地交接，不使用 Actions。

## 优先阅读

1. `docs/research/two_wave_qualified_identity_results_v060.md`
2. `cloud_results/local_v060_qualified_identity_audit/summary.json`
3. `cloud_results/local_v060_qualified_identity_audit/data_identity.json`
4. `docs/research/two_wave_qualified_identity_audit_protocol_v060.md`
5. `docs/research/two_wave_cross_slicer_identity_attribution_v059.md`
6. `docs/research/two_wave_morphology_identity_layer_preanalysis_v060.md`
7. `src/factor_lab/visual_structure/two_wave/morphology_identity_v060.py`
8. `scripts/run_two_wave_qualified_identity_audit_v060.py`
9. `docs/research/two_wave_cycle_scale_qualification_results_v054.md`
10. `docs/research/two_wave_extremum_ridge_results_v052.md`

## 禁止事项

- 不因 matched subset 的高 D1 agreement 自动复活 direction；
- 不调 D1/D2/PAWCT 来逃避 identity 问题；
- 不按这次结果事后发明 identity matching cutoff；
- 不按 coverage、label balance、案例美观或收益选 recognizer；
- 不重新用 exclusive packing 定义 morphology observation；
- 不进入 H1/H2 / third-wave / outcomes / trading；
- 不使用 GitHub Actions。
