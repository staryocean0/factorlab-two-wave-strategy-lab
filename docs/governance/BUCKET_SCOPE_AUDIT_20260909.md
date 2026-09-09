# Three-bucket scope audit — 2026-09-09

## Authoritative split

| Bucket | Owns | Does not own |
|---|---|---|
| Two-Wave | causal completed-wave / parent-structure recognition; Range / UpTrend / DownTrend / Uncertain | concrete reversal payoff strategies; STAR50 risk-state routing; live execution |
| Trend–Reversion | concrete reversal / mean-reversion strategies including R1/R2 | generic range/up/down recognizer; STAR50 risk-state switching |
| STAR50 Filter | bottom-layer K-line volatility/risk properties and causal Unsafe/Recovering/HighVol switching | concrete payoff strategies; generic parent-structure trend/range recognizer |

## Findings for Two-Wave

- The original Two-Wave handoff is correctly scoped: two complete same-scale waves must be identified causally before parent classification.
- Imported Layer 1/2/3 dependency closure may contain modules whose names sound economic/strategy-related; they remain infrastructure dependencies/reference material and do not broaden the active research mandate.
- The K-line recognizer v1-v13 lineage from Trend–Reversion is relevant but semantically different. Its key evidence has been migrated into `docs/archive/migrated_kline_state_recognizer_from_trend_reversion_20260909/` as supporting evidence only.

No migrated historical classifier may bypass morphology replication acceptance.

`production_authority=false`.
