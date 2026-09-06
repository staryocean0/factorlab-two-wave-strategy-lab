# v0.6.9 Frozen protocol — path-metric sampling-resolution response audit

Date: 2026-09-06

Status: **FROZEN BEFORE ANY v0.6.9 RESOLUTION-RESPONSE OUTPUT IS READ**

This audit changes no qualification rule, threshold, identity, matcher, projection, publication, direction, outcome or trading logic.

## 1. Hard controls

Reproduce v0.6.8 published-identity / canonical-path counts:

```text
published identities = 38,176 / 36,737 / 36,619 / 36,480 / 36,264
canonical path unavailable = 0 / 0 / 0 / 0 / 0
```

Reproduce v0.6.6 pair controls:

```text
published strict pairs = 8,381 / 5,770 / 6,204 / 9,098
both-qualified = 482
qualification disagreement = 699
v0.6.1 target repaired = 80, of which disagreement = 24
```

Any drift stops interpretation.

## 2. Native 5m leg path

For each published identity and each leg `[raw_k, raw_{k+1}]`, use the native-view close rows from the first anchor bar through the second anchor bar, inclusive.

Compute exactly:

```text
changes = abs(diff(close))
TV5 = sum(changes)
E5 = abs(last-first)/TV5 if TV5>0 else 0
J5 = max(changes)/TV5 if TV5>0 else 1
F5 = mean(changes==0)
```

These values must match the frozen v0.6.6 leg efficiency/jump/flat values. A random exact-equivalence gate must pass before full interpretation.

## 3. Canonical 1m leg path

Use the same absolute published anchor-time interval on supplied `1m_official` exactly as v0.6.8.

Compute TV1/E1/J1/F1 with identical formulas.

No interpolation, resampling, fill, smoothing or synthetic point.

## 4. Partition-alignment audit

For each leg report:

- whether both published endpoints have exact supplied 1m rows;
- whether every native-view bar timestamp inside the leg has an exact supplied 1m row;
- whether corresponding 5m/1m closes are exactly equal at common timestamps;
- path row counts.

Only aligned legs enter the exact nested-partition theorem check. Non-aligned legs remain reported separately; do not drop their existence silently.

## 5. Exact theorem checks

For every aligned leg assert with a fixed numerical implementation tolerance only for floating arithmetic:

```text
TV1 + 1e-12 >= TV5
E1 <= E5 + 1e-12
```

The `1e-12` is not a research tolerance or threshold; it is only an arithmetic assertion guard and may not be used in any financial classification.

Report violation count. Any material violation requires data/alignment debugging before interpretation.

## 6. Resolution-response distributions

For aligned legs report distributions of:

- `TV1/TV5` where TV5>0;
- `E1/E5` where E5>0;
- `E1-E5`;
- `J1-J5`;
- `F1-F5`;
- native leg duration bars;
- fine/coarse row-count ratio.

Required summary statistics: count, min, median, p90, p99, max, mean. No winsorization.

## 7. Frozen threshold crossing matrices

Using existing 0.5 only as a label, report per-leg 5m→1m matrices for:

Efficiency (`pass` iff >=0.5), jump (`pass` iff <=0.5), flat (`pass` iff <=0.5):

```text
pass->pass
pass->fail
fail->pass
fail->fail
```

No candidate qualification is produced.

## 8. Identity-level path-reason transitions

For each identity compute path reason flags from its four legs at 5m and 1m and report 2x2 transitions separately for:

- inefficient_leg;
- jump_dominated_leg;
- flat_dominated_leg.

The v0.6.8 per-view candidate path reason counts must be reproduced by the 1m side.

## 9. Duration overlay

Report response statistics by exact native leg duration and the pre-registered bins:

`1-3`, `4-5`, `6-11`, `12-23`, `24+` bars.

Report Spearman rank association between native leg duration and:

- TV refinement ratio;
- efficiency delta;
- jump delta.

Correlation is descriptive only.

## 10. Strict-pair overlays

On the frozen 29,453 strict-pair universe, without changing pair labels, separately summarize leg-level response for:

- 482 v0.6.6 both-qualified pairs;
- 699 v0.6.6 disagreement pairs;
- 80 v0.6.1 target repaired pairs, split into 56 v0.6.6 agreement and 24 disagreement.

No outcome fields.

## 11. Synthetic gates

Tests must cover:

- exact native metric reproduction;
- nested refinement TV monotonicity / efficiency non-increase;
- non-identifiability of fine variation from coarse endpoints;
- jump share non-monotonicity counterexample (do not assume a theorem that is false);
- constant path convention;
- future append after leg end does not affect metrics;
- no direction/outcome dependency.

## 12. Required outputs

Write to:

`cloud_results/cloud_chat_v069_path_metric_resolution_response/`

Required compact files:

```text
summary.json
per_view_response.json
threshold_crossings.json
identity_reason_transitions.json
duration_overlay.json
strict_pair_overlays.json
data_identity.json
execution_receipt.json
```

## 13. Interpretation rule

No threshold fitting and no replacement metric in v0.6.9.

Allowed adjudications only:

- `resolution_scaling_is_structured_enough_for_normalization_research`;
- `resolution_response_is_too_heterogeneous_for_simple_threshold_remap`;
- `metrics_have_opposed_resolution_semantics_requiring_property_redefinition`;
- `mixed_resolution_response_requires_more_audit`.

The adjudication must explicitly address efficiency and jump separately.

Duration-geometry remains out of scope.

Global state remains `morphology_replication_not_yet_accepted`; direction/outcome/trading remain frozen.
