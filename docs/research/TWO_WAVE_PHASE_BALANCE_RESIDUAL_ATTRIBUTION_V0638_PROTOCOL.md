# Two-Wave v0.6.38 phase-balance residual attribution protocol

Date: 2026-09-11
Status: frozen before residual replay

## Purpose

Diagnose what v0.6.37 phase balancing actually removed from the rejected v0.6.35 full-distribution Wasserstein Range rescue, and what one-sided cross-slicing residuals remain after phase balancing.

This is diagnostic evidence only. It changes no recognizer, label, threshold, qualification rule, promotion gate, or authority.

## Frozen upstream

- qualification champion: v0.6.18;
- direction comparison base: v0.6.25;
- v0.6.35: bar-equal complete-cycle W1, normalized by parent amplitude, all four endpoint supports required, ceiling `0.15`;
- v0.6.37: the same W1 ceiling and four supports, but each complete cycle is a 50/50 mixture of its first and second leg distributions;
- same 1,462 both-v0.6.18-qualified strict same-event pairs;
- no future outcomes, P&L, H1/H2, third wave, 2021+, or 2026 selection data.

## Frozen decomposition A: v0.6.35 -> v0.6.37 exact-status transition

For every one of the 1,462 pairs, compare exact four-state agreement under v0.6.35 and v0.6.37:

- `phase_balance_repaired_v0635_nonexact`: v0.6.35 non-exact, v0.6.37 exact;
- `phase_balance_harmed_v0635_exact`: v0.6.35 exact, v0.6.37 non-exact;
- `both_exact`;
- `both_nonexact`.

Report counts by class and by offset.

## Frozen decomposition B: remaining v0.6.37 one-sided changes vs v0.6.25

For every pair where v0.6.37 changes exactly one side relative to v0.6.25, classify exact four-state semantics exactly as in v0.6.36:

- `introduced_harm`: v0.6.25 was exact and v0.6.37 is non-exact;
- `repaired_old_nonexact`: v0.6.25 was non-exact and v0.6.37 becomes exact;
- `persistent_nonexact`: both are non-exact.

For the changed side additionally record whether v0.6.35 also rescued the same v0.6.25 `Uncertain` state to `Range`:

- `shared_bar_equal_and_phase_balanced_rescue`;
- `phase_balanced_only_rescue`.

Report the cross-tabulation of semantic class by rescue origin.

## Hard interpretation constraints

- Do not infer or tune any new W1 threshold from v0.6.38.
- Do not promote a weighting-consensus rule merely because a subgroup looks favorable in this diagnostic.
- Any later recognizer must be a separately frozen candidate before its replay.
- v0.6.25 remains the strongest pooled-exact direction contribution unless a later frozen challenger passes the existing promotion gates.
- v0.6.18 remains qualification champion.
- independent morphology acceptance remains false; trading and production remain closed.
