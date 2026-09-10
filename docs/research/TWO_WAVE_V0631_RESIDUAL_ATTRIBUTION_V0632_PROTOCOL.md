# Two-Wave v0.6.32 v0.6.31 residual attribution protocol

Date: 2026-09-10
Status: frozen before row-level attribution replay

## Purpose

Explain why the rejected v0.6.31 mutual-median Range rescue increased Range coverage but reduced cross-slicing exact agreement.

This is a read-only diagnostic. It changes no recognizer, qualification rule, direction rule, threshold, label, or authority.

## Frozen controls

- qualification policy remains v0.6.18;
- evaluation universe remains the same 1,462 strict same-financial-identity pairs where both views are v0.6.18-qualified;
- v0.6.25 pooled exact must reproduce as 1402/1462;
- v0.6.31 pooled exact must reproduce as 1384/1462;
- v0.6.31 change topology must reproduce exactly: both=17, main_only=14, other_only=12, none=1419;
- v0.6.31 new Range rescues across all five views must reproduce as 154;
- all v0.6.31 changes remain exactly Uncertain -> Range;
- D1 decisive overrides remain zero.

## Frozen attribution

For each pair with exactly one side changed by v0.6.31, classify the pair into exactly one semantic class using only the pre-v0.6.31 v0.6.25 pair and the post-v0.6.31 pair:

1. `introduced_harm`: v0.6.25 was exact and v0.6.31 becomes non-exact.
2. `repaired_old_nonexact`: v0.6.25 was non-exact and v0.6.31 becomes exact.
3. `neutral_nonexact`: both versions remain non-exact.

For the changed side, recompute the frozen v0.6.31 mutual-median containment evidence on all four frozen v0.6.23 endpoint supports.

For each support, define two normalized signed containment slacks:

- cycle-1 median relative to cycle-2 IQR: `min(m1-q25_2, q75_2-m1) / IQR_2`;
- cycle-2 median relative to cycle-1 IQR: `min(m2-q25_1, q75_1-m2) / IQR_1`.

Positive means inside, zero means on the boundary, negative means outside. A v0.6.31 changed side necessarily has all eight slacks >= 0.

Record for each changed side:

- minimum of the eight normalized slacks (`min_containment_slack_iqr`);
- median of the eight slacks;
- support-level minimum slack for `full`, `left_eroded_1`, `right_eroded_1`, `both_eroded_1`;
- which support owns the global minimum slack;
- frozen v0.6.27 Range consensus margin.

For the unchanged paired side, compute the same evidence where available, including which support first fails mutual containment and its most negative normalized slack.

## Output

Produce:

- exact control reproduction;
- counts of introduced_harm / repaired_old_nonexact / neutral_nonexact among the 26 one-sided changes;
- min-containment-slack distributions by semantic class;
- support-owner counts of the smallest slack;
- failing-support counts on the unchanged side;
- row-level audit JSONL for all one-sided changed pairs.

No new decision threshold is authorized by this protocol. Any subsequent repair must be preregistered as a new version after this attribution is read.

Global morphology acceptance remains false. Trading and production authority remain false.
