# v0.6.3 Preanalysis — phase-window semantics residual audit

Date: 2026-09-06

Status: **written before reading any v0.6.3 residual-detail output**

## Context

v0.6.2 established two facts about the frozen `sequential_raw_close_extreme_inside_filtered_phase_bounds` projection:

1. within one view, canonical filtered tuples have no multi-valued valid projection groups;
2. across mutual-unique filtered-tuple pairs, 29,273 valid pairs have 5m raw projection displacement, of which 22,433 recover strict identity when each side's *existing absolute projection windows* are evaluated on the supplied `1m_official` path.

The remaining 6,840 pairs are therefore not explained by the 5m sampling lattice alone. They are the only primary population for v0.6.3.

This audit does **not** change the projection operator, matcher, ridge, qualification, direction or trading logic.

## Research question

For each v0.6.2 residual pair (`5m raw displaced` + `1m diagnostic displaced`), at the earliest canonical-1m displaced ordinal, which part of the two sides' already-frozen phase-window support prevents the same raw financial anchor from being available to both sides?

The question is about support semantics, not about choosing a replacement anchor.

## Existing frozen window semantics under audit

For filtered anchors `f0..f4`, member confirmation `c`, and sequentially selected raw anchors `r0..r4`:

- ordinal0 lower: `max(0, 2*f0 - f1)`;
- ordinal0..3 upper: `f[k+1] - 1` in the view's own 5m row index;
- ordinal1..4 lower: `r[k-1] + 1`;
- ordinal4 upper: `c`.

These are bar-index/predecessor semantics. Harmless 5m offsets can therefore produce different *absolute-time* windows even when filtered anchors are within one nominal 5m bar.

## Candidate mechanisms to separate before any repair

1. **ordinal0 extrapolated-left support** — `2*f0-f1` is a row-index extrapolation and can amplify calendar/session gaps.
2. **filtered-predecessor upper support** — `f[k+1]-1` refers to the previous row of each slicing lattice, not an absolute-time phase boundary.
3. **sequential lower support** — later lower bounds inherit the prior raw selection and can propagate an earlier difference.
4. **confirmation-tail support** — ordinal4 extends to member confirmation rather than filtered e4.
5. **overlap-path residual** — both canonical 1m selections remain inside both side windows but still differ; this would require path/tie or other support structure, not simple one-sided boundary exclusion.
6. **session-gap amplification overlay** — lunch/overnight gaps may convert a small row-index difference into a large wall-clock support difference.

These mechanisms may coexist. v0.6.3 needs a deterministic primary attribution plus overlays; it must not use outcome quality to choose one.

## Guardrails

- Do not widen the existing `<=5m` identity matcher.
- Do not replace the 5m projection with 1m in this experiment.
- Do not use window intersection as a runtime projection.
- Do not fit any new tolerance from residual distributions.
- Do not use D1/D2/PAWCT, return, outcome, P&L, H1/H2 or third-wave information.
- Do not tune v0.5.2 ridge or v0.5.4 qualification.
- Do not choose a boundary formula after reading which candidate would recover most identities.

## What a valid result can authorize

Only a later, separately frozen repair preanalysis. If one support mechanism clearly dominates across all four offsets and survives the session-gap overlays, the next experiment may propose mathematical invariants for a replacement support definition. If mechanisms remain mixed, they remain separate workstreams.

Global morphology status remains `morphology_replication_not_yet_accepted`.