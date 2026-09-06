# 两浪研究继续入口：v0.5.8 direction 失败已被 identity confound 重解释，进入 v0.6.0 morphology identity audit（2026-09-06）

## 当前安全状态

冻结上游仍是：

> **v0.5.2 TCSS exact-ridge parent identity + v0.5.4 full-cycle-scale qualification**

操作基线仍是 **v0.4.3**；全局状态仍为 `morphology_replication_not_yet_accepted`。PR #1 保持 Draft，不合并 main。不进入第三浪/H1/H2、收益、交易、OOS 或生产。

当前研究链：

**v0.5.0 TCSS representation ✅ → v0.5.1 sliding family ❌ → v0.5.2 exact-ridge identity ✅ → v0.5.4 full-cycle qualification ✅ → v0.5.5 D1 attribution → v0.5.6 D2 multiview ❌ → v0.5.7b endpoint-D2 route ❌ → v0.5.8 PAWCT selected-output R1 ❌ → v0.5.9 identity attribution ⇒ direction adjudication 被 event-identity confound → v0.6.0 qualified morphology identity audit pending local five-view replay。**

## 最重要的新结论

v0.5.8 正式 run `34011528190` / artifact `9982711773` 的 frozen verdict `PAWCT_representation_candidate_fail` **历史上仍成立**，但只能解释为：

> **exclusive selected-record timeline 输出的跨 slicing 稳定性失败。**

它不能继续被解释为“PAWCT 对同一个金融两浪事件的 parent translation 已被证伪”。

原因来自只读 v0.5.9 attribution：

- v0.5.8 全部 82 个 PAWCT large-margin sign-flip pair / 5,596 bars 中，五锚点最大 occurrence-time 差的**最小值就是 1,163 分钟**；
- target `D1=uncertain + D2_harm` 的 22 个 large-margin flip pair / 1,566 bars 同样从 **1,163 分钟**起步；
- 所以没有任何 large-margin failure 是“同一两浪只差一根/几根 5m K线”的情形；
- 1m—480m 的完整 locality sweep 中，locally aligned 子集始终 **0 large-margin PAWCT flip**；
- 用一根 nominal 5m bar 的严格 audit-locality（五个 anchor 全部 <=5m）看，262 selected pairs / 54,722 bars：phase match=100%，D1 label agreement=96.4493%，D2=93.8014%，PAWCT large-margin flip=0。

因此下一步必须先修正/审计**金融事件 identity 与 selected packing 的混合**，不是再发明一个方向公式。

## 现行 exclusive ledger 的结构性问题

v0.5.4 仍复用 v0.5.1 `CharacteristicExclusiveLedger`：

priority 首先按 `confirmation_bar`，然后 scale level/start/end/id；qualified tuple 只有 `start_bar >= current_selected_end` 才 selected，否则被 overlap-suppressed。

本地用 artifact 中**原 class 源码**执行的最小反例已经证明：

- A `[20,80]`、B `[30,90]`，几何/资格/尺度不变；
- A confirm=60, B=61 → A winner；
- 只把 A confirm 改成62 → B winner；
- 即 1-bar confirmation jitter 足以更换整组五 extrema identity。

更重要的金融语义反例：七个连续 alternating extrema 形成三条完整 wave 时，`(W1,W2)` 与 `(W2,W3)` 都是合法的两浪观察；exclusive packing 却会因为 overlap 抑制后者。**non-overlap 不是原始 morphology 需求。**

主 5m frozen v0.5.5 qualified evidence：

- 734 qualified records；
- legacy selected 404；
- 330（44.96%）被 packing 抑制；
- 356 个 strict overlap components 中 178 个非平凡；最大 component 11 records；
- 按 `(phase, five raw occurrence bars)` 合并同一金融 identity 的多尺度重复后，734 → **712 canonical identities**；
- 21 个 duplicate-scale groups / 43 records，所有组 D1/三相几何一致；
- 712 个 canonical qualified identities 里只有 404 个有 legacy selected member，**308（43.26%）合法 identity 被 exclusive packing 完全隐藏**。

## v0.6.0 语义修正

Morphology 层正式区分：

1. **qualified financial identity**：`(start_phase, e0,e1,e2,e3,e4)`；
2. **scale evidence**：同五 raw anchors 在不同 birth scale 的后续证据；
3. **exclusive packing**：仅作为 downstream/legacy diagnostic，不再有权定义“这个两浪事件是否存在”。

因果发布规则：

- 第一个 qualified member 确认时，发布 immutable identity event；
- 后续 same-anchor 更粗/更细 scale member 只能 append evidence；
- 不回写原 identity 的 member_count/member_ids/confirmation；
- 不 suppression rolling two-wave windows；
- 不救 rejected candidate；
- 不用 cross-view、direction、outcome 或收益选择 identity。

本地 v0.6.0 helper 单测 **8/8 PASS**，包括 later-scale evidence 的 exact append-only prefix 语义。

## v0.6.0 冻结 cross-view audit

只用于 evaluator，不进入单视图 recognizer：

- offset0 vs offset1..4；
- same start phase；
- 五个 occurrence timestamps 位置对应；
- 每个 delta <= **一根 nominal 5m bar**；
- 只接受 mutual-unique edge；
- 多匹配直接记 ambiguous，不 post-hoc tie-break；
- interval IoU / D1 / D2 / PAWCT / outcome 都不参与 identity matching。

要比较两套输出：

- all canonical qualified identities；
- legacy selected identities。

如果 qualified pool 已有清晰同事件结构而 selected 丢失它们，packing 是主要污染源；如果 qualified pool 自身仍大面积 absent/ambiguous，就继续 upstream ridge/qualification identity，不碰 direction。

## 当前执行限制

用户已明确：**GitHub Actions 没额度，后续该自己算的自己算。**

因此：

- 不启动/重跑任何 Action；
- 已完成的历史 run/artifact 允许只读下载；
- 新 POC/统计/测试优先当前本地 runtime；
- Git 提交使用 `[skip ci]`，不依赖 CI；
- 当前 runtime 尚无法取得 repo 中 parquet 二进制（GitHub connector UTF-8 限制，container 无公网 DNS）；不能用端点近似 raw path，也不能伪造数据。

本地五视图 runner 已准备：`scripts/run_two_wave_qualified_identity_audit_v060.py`。一旦 active runtime 能看到仓库 frozen parquet，就执行 full five-view + 25/50/75 prefix，共 15 个 prefix checks，并输出 qualified-vs-selected identity decomposition。

## 优先阅读

1. `docs/research/two_wave_cross_slicer_identity_attribution_v059.md`
2. `docs/research/two_wave_morphology_identity_layer_preanalysis_v060.md`
3. `docs/research/two_wave_qualified_identity_audit_protocol_v060.md`
4. `src/factor_lab/visual_structure/two_wave/morphology_identity_v060.py`
5. `scripts/run_two_wave_qualified_identity_audit_v060.py`
6. `docs/research/two_wave_d1_phase_aligned_translation_protocol_v058.md` / v0.5.8 PAWCT result artifacts
7. `docs/research/two_wave_cycle_scale_qualification_results_v054.md`
8. `docs/research/two_wave_extremum_ridge_results_v052.md`

## 禁止事项不变

- 不改 v0.5.2 ridge linking/death/birth 来补方向；
- 不重新调 v0.5.4 qualification threshold；
- 不按 coverage 数量、label balance、案例美观或收益选模型；
- 不把 v0.5.9 post-hoc attribution 冒充 independent morphology acceptance；
- 不因 identity confound 自动“复活/通过” PAWCT；它必须等 strict same-event replay 后再 adjudicate；
- 不进入 H1/H2 / 第三浪 / outcomes / trading。
