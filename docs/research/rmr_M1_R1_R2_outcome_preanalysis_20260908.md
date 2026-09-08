# M1 R1/R2 outcome preanalysis — parent structure + single causal deviation

Date: 2026-09-08  
Measurement identity: `M1_parent_structure_plus_single_shock_event_adapter_v1`

M1-S0 supply-only screening passed before any post-trigger first-passage outcome was read:

- R1 triggers: BUILD 275, 2019 57, 2020 69;
- R2 triggers: BUILD 713, 2019 172, 2020 164.

Supply receipt:

`docs/research/cloud_session_20260908_broad_rmr_M1_S0_event_supply_receipt_v1.json`

This authorizes an outcome screen under the exact already-frozen trigger definitions. It does not authorize trigger/scale/model changes.

## R1 — parent trend + single counter-shock

Parent state remains the mature published L5 M0 structure on `5m_offset_0`.

Event remains exactly:

- after parent publication, maintain the parent-direction running extreme;
- trigger at the first opposite close move of at least `0.5 × parent amplitude`;
- 0.5 is inherited from the reciprocal of old v0.4.3 `amplitude_ratio=2.0`, not selected from R1 outcomes;
- if the parent structural failure boundary is hit before shock trigger, no event.

Outcome after trigger:

- recovery = first close returning to the pre-trigger running extreme;
- failure = first close reaching the frozen parent structural failure boundary;
- censor at parent expiry, trigger+96 bars, or calendar-year end, whichever comes first;
- no intrabar high/low inference.

Probability models, fit on 2015–2018 only:

1. `severity_only = [severity]`;
2. `parent_integrity_only = [abs_drift, overlap, parent_eff]`;
3. `parent_plus_severity = [severity, abs_drift, overlap, parent_eff]`.

Primary comparison is 3 versus 1. Model family is frozen standardized logistic regression, no tuning/calibration/threshold.

R1 can progress only if:

- resolved BUILD >=150;
- resolved 2019 >=50;
- resolved 2020 >=50;
- parent+severity pooled 2019–2020 Brier < severity-only;
- parent+severity pooled log-loss < severity-only;
- Brier improves in both 2019 and 2020;
- standardized integrity projection `coef(abs_drift)-coef(overlap)+coef(parent_eff) > 0`.

## R2 — parent range / envelope + first close excursion

Parent state remains the same mature published L5 M0 structure.

Event remains exactly:

- first 5m close strictly above parent envelope high or below envelope low;
- no additional excursion threshold;
- severity = outside log-distance / frozen parent envelope width.

Outcome:

- re-entry = first close back to nearest frozen envelope edge;
- continuation = first close the same outside distance farther in the breakout direction;
- censor at parent expiry, trigger+96 bars, or calendar-year end.

Probability models:

1. `excursion_severity_only = [severity]`;
2. `parent_range_state_only = [abs_drift, overlap, parent_eff]`;
3. `parent_plus_excursion_state = [severity, abs_drift, overlap, parent_eff]`.

R2 can progress only if:

- resolved BUILD >=150;
- resolved 2019 >=50;
- resolved 2020 >=50;
- combined pooled Brier < severity-only;
- combined pooled log-loss < severity-only;
- Brier improves in both 2019 and 2020;
- standardized range-likeness projection `-coef(abs_drift)+coef(overlap)-coef(parent_eff) > 0`.

If parent-only is informative but the combined model fails the exact gate, report the mechanism as mixed/hold; do not post-hoc change the baseline or formula.

## Evidence roles and claims

- BUILD: 2015–2018 consumed development;
- chronological check: 2019–2020, not fresh;
- post-2020 unread;
- no PnL;
- no morphology-acceptance claim;
- no production authority.

## Forbidden after results

- change 0.5 shock fraction;
- add R2 distance threshold;
- change L5, view or 96-bar validity;
- add volatility/break-speed/technical filters;
- pick one direction/year/offset;
- change first-passage boundary;
- lower resolved sample gates;
- use R1/R2 v1 or M1 results to tune the event definition.
