# FactorLab Two-Wave Strategy Lab

Bounded research repository for the CSI1000 (`000852.SH`) two-wave parent-structure recognizer. This repository is a research and reproducibility surface only; it has **no production, trading, or registry authority**.

## Current status — 2026-09-12

The canonical machine authority is [`experiments/two_wave_m0_authority.json`](experiments/two_wave_m0_authority.json), currently `two_wave_m0_authority@1.33` with global status:

`v0708_external_validation_evidence_gap_no_candidate_opened_no_direction_winner`

The current Development chain is:

1. **v0.7.1** — F3 persistence-dominant nonconsecutive ridge quintet selected as the repaired semantic-object family (`8/11` anchored cases). It is a Development representation, not active morphology authority.
2. **v0.7.4** — prefix-causal lifecycle representation supported; the one case lacking permanent C1 certification remains live/unresolved rather than disappearing.
3. **v0.7.5** — immutable provisional raw publication supported for all `1543` observed lifecycle objects; raw semantic support `9/11`.
4. **v0.7.6** — historical v0.6.18 qualification successfully transplanted: `115` qualified publications, `9/11` semantic support, zero interface/contract violations.
5. **v0.7.7** — D1 and v0.6.25 direction stack successfully transplanted on all `115` qualified publications. v0.6.25 legally rescues `19` D1-uncertain publications, but is **semantically neutral to D1** on the frozen supported reference subset (`7/9` exact for both; `2/9` uncertain for both).
6. **v0.7.8** — external-evidence availability audit found no currently connected evidence source that can legitimately reopen direction authority. No new candidate, protocol, scoring, or threshold change was opened.

Two external-validation weaknesses remain binding:

- **v0.6.47 temporal replication:** D1 exact `242/253`; v0.6.25 exact `238/253`.
- **v0.6.48 independent reference calibration:** only `16/120` candidate cases had reference-confirmed presence; D1 and v0.6.25 were each exact on `5/16`.

Therefore:

- `active_semantic_parent_authority = null`
- `parent_direction.winner = null`
- `morphology_acceptance = false`
- `trade_authority = false`
- `production_authority = false`
- no in-sample direction challenger is currently authorized.

Direction research may reopen only after **both** of these exist and are preregistered before scoring: (A) genuinely new CSI1000 temporal evidence not already consumed by v0.6.47 or later validation, and (B) independently produced Two-Wave morphology/reference labels with frozen provenance, case universe, and labeling protocol.

## Data boundary

The repository itself ships only CSI1000 Development bar views for `2015-01-05..2020-12-31`. Post-2020 bars are not shipped here.

External temporal material was nevertheless consumed under the separately frozen v0.6.47 protocol: 2024, 2025, and `2026-01-05..2026-08-21`. Those slices are **already consumed validation evidence** and must not be relabeled as fresh evidence. The v0.7.8 audit found no connected post-`2026-08-21` CSI1000 minute extension and no new independent Two-Wave reference-label pack.

See [`docs/governance/data_usage_declaration.json`](docs/governance/data_usage_declaration.json) for the current declaration.

## Canonical entry points

- Human-readable research index: [`docs/INDEX.md`](docs/INDEX.md)
- Machine authority: [`experiments/two_wave_m0_authority.json`](experiments/two_wave_m0_authority.json)
- Human authority snapshot: [`docs/research/TWO_WAVE_M0_AUTHORITY.md`](docs/research/TWO_WAVE_M0_AUTHORITY.md)
- v0.7.7 direction adjudication: [`experiments/two_wave_lifecycle_qualified_direction_v0707/ADJUDICATION.json`](experiments/two_wave_lifecycle_qualified_direction_v0707/ADJUDICATION.json)
- v0.7.8 evidence audit: [`docs/research/TWO_WAVE_EXTERNAL_VALIDATION_EVIDENCE_AVAILABILITY_V0708.md`](docs/research/TWO_WAVE_EXTERNAL_VALIDATION_EVIDENCE_AVAILABILITY_V0708.md)
- v0.7.8 adjudication: [`experiments/two_wave_external_validation_availability_v0708/ADJUDICATION.json`](experiments/two_wave_external_validation_availability_v0708/ADJUDICATION.json)
- Repository component status: [`docs/governance/repository_component_status.json`](docs/governance/repository_component_status.json)

## Timing-infrastructure compatibility

The broader FactorLab timing stack remains a **shared frozen infrastructure contract**, not Two-Wave scientific authority. Its four-layer inventory is preserved at [`docs/ops/timing_infrastructure_four_layer_inventory@1.0.json`](docs/ops/timing_infrastructure_four_layer_inventory@1.0.json). The compatibility shell keeps the layer boundaries explicit: **数据时钟** → **K线测量** → research/decision semantics → **执行标的**. Two-Wave work may reuse those frozen infrastructure contracts but may not silently collapse measurement and routing authority.

## Repository layout

- `src/factor_lab/visual_structure/two_wave/` — current and historical Two-Wave research implementations. Versioned historical modules are retained for reproducibility; filenames alone do not confer authority.
- `scripts/` — formal runners, diagnostics, and maintenance tools. Historical runners are reproducibility assets, not current authority.
- `tests/` — regression, causal-contract, replay, and governance tests.
- `experiments/` — formal aggregate results, result cards, adjudications, and the current machine authority.
- `docs/research/` — frozen protocols, scientific adjudications, and research ledgers.
- `docs/governance/` — package/data/authority boundaries and repository consistency state.
- `docs/reference/` and `docs/archive/` — frozen imported/reference/history surfaces. They are not current authority unless explicitly cited by a current protocol.
- `.github/workflows/ci.yml` — the only long-lived workflow. Formal one-shot research/governance workflows are deleted after completion.

## Validation

The repository is fail-closed through:

```bash
python scripts/validate_theme_package.py
pytest -q
```

The validator checks the frozen source/data closure, repository surface, tool-registry boundary, current v0.7.8 authority, governance declarations, and active workflow surface.

## Historical material

The repository intentionally retains historical v0.5.x/v0.6.x/v0.7.x protocols, runners, modules, tests, and experiment results when they are needed to reproduce a formal conclusion. “Historical” means **not current authority**, not “safe to delete.” Current status must be read from the canonical entry points above rather than inferred from the newest-looking module name.
