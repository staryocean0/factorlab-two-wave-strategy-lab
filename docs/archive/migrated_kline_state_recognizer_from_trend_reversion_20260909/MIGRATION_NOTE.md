# Migrated K-line state-recognizer evidence from Trend–Reversion

Date: 2026-09-09

## Why this package moved

A causal K-line state-recognizer research lineage (`v1` through `v13`) was mistakenly developed on research branches of `factorlab-trend-reversion-regime-lab`.

The current bucket split assigns:

- concrete reversal / mean-reversion strategies (R1/R2 and related MR/REV work) to `factorlab-trend-reversion-regime-lab`;
- bottom-layer volatility / Unsafe / Recovering / HighVol risk-state work to `factorlab-star50-filter-lab`;
- causal classification of market structure into range / uptrend / downtrend to this Two-Wave bucket.

Therefore the K-line recognizer's key authority and results are preserved here as supporting state-classification evidence.

## Important semantic boundary

This migrated recognizer is **not automatically the Two-Wave recognizer**.

The Two-Wave contract requires causally confirmed same-scale complete waves and parent-structure morphology before classifying `Range / UpTrend / DownTrend / Uncertain`. The migrated lineage instead used a different causal feature/classification surface and also included a `Shock` state.

Accordingly:

- historical v10 remains the winner **inside the migrated recognizer lineage only**;
- it does not replace `two_wave_parent_structure_recognizer` or satisfy morphology replication acceptance;
- useful components may be compared, adapted or used as baselines only after an explicit Two-Wave protocol preserves the Two-Wave morphology semantics.

## Source provenance

Source repository: `staryocean0/factorlab-trend-reversion-regime-lab`

Latest source research branch audited for migration: `research/kline-recognizer-persistence-prior-v13`.

Historical branches and full code/results remain in the source Git history and are not deleted by this scope repair.

This directory preserves the key authority/champion/contribution records and decisive v10-v13 result cards so the research knowledge is not lost when the source bucket is repaired.

`production_authority=false`.
