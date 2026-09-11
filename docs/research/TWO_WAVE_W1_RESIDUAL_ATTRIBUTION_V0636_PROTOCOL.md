# Two-Wave v0.6.36 W1 residual attribution protocol

Date: 2026-09-11
Status: frozen before residual replay

## Purpose

Diagnose the remaining one-sided cross-slicing changes created by the rejected v0.6.35 two-cycle Wasserstein Range rescue. This is diagnostic evidence only; it changes no recognizer, label, threshold, qualification rule, or authority.

## Frozen upstream

- qualification: v0.6.18;
- direction comparison base: v0.6.25;
- v0.6.35 Wasserstein rule: empirical cycle-1 vs cycle-2 W1, normalized by parent amplitude, all four endpoint supports required, ceiling `0.15`;
- same 1,462 both-v0.6.18-qualified strict same-event pairs;
- no future outcomes, P&L, H1/H2, third wave, 2021+, or 2026 selection data.

## Frozen decomposition

For every pair where v0.6.35 changes exactly one side relative to v0.6.25, classify the pair using exact four-state agreement:

- `introduced_harm`: v0.6.25 was exact and v0.6.35 is non-exact;
- `repaired_old_nonexact`: v0.6.25 was non-exact and v0.6.35 becomes exact;
- `persistent_nonexact`: both are non-exact.

For the changed side record, define:

`w1_slack = 0.15 - max_normalized_cycle_wasserstein`

where the max is across the same four frozen endpoint supports. A rescued record has non-negative slack by construction.

Report group counts and slack median / q25 / q75, plus the fraction with `w1_slack <= 0.03`.

## Frozen authorization gate for any later W1-margin challenger

A later W1-margin challenger is authorized only if ALL are true:

1. `introduced_harm` sample size >= 20;
2. `repaired_old_nonexact` sample size >= 20;
3. median introduced-harm slack is at least `0.03` smaller than median repaired slack;
4. at least 70% of introduced-harm changed sides have slack `<=0.03`;
5. at most 40% of repaired changed sides have slack `<=0.03`.

The `0.03` diagnostic separation is frozen here as 20% of the inherited `0.15` morphology tolerance; it is not fitted from v0.6.36 outcomes.

If any gate fails, W1-margin tuning is **not authorized** and the next research step must change the measurement rather than search nearby W1 thresholds.

Independent morphology acceptance remains false. Trading and production remain closed.
