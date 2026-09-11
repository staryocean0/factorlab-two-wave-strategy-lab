# Two-Wave v0.6.44 native high/low envelope direction attribution

Formal run: **`34616273360`**  
Raw formal result commit: **`f4128a8ef1aaf6e1f1f205af64a9fef77302d19b`**  
Final governance category: **`v0644_high_low_envelope_redundant_or_unstable`**

Frozen universe reproduced: **1462** pairs; D1 exact = **1400**; v0.6.25 exact = **1402**.

| quantity | v0.6.25 exact median | v0.6.25 nonexact median | P(nonexact > exact) |
|---|---:|---:|---:|
| pair mean anchor outward excursion | 0.031419 | 0.033307 | 0.508060 |
| pair mean envelope adjustment L1 | 0.041850 | 0.042725 | 0.498027 |
| envelope-adjustment view distance L1 | 0.053364 | 0.059681 | 0.557834 |
| mean-anchor-excursion view delta | 0.019266 | 0.019655 | 0.489063 |
| envelope stability gain L1 | 0.004101 | 0.009066 | 0.532798 |

Positive stability-gain fraction, v0.6.25 exact: `0.555635`.  
Positive stability-gain fraction, v0.6.25 nonexact: `0.550000`.

Per-offset median stability gain (`close view distance - envelope view distance`):

- `5m_offset_1`: all `+0.004762`; exact `+0.004591`; nonexact `+0.009066`;
- `5m_offset_2`: all `+0.002451`; exact `+0.002394`; nonexact `+0.015500`;
- `5m_offset_3`: all `-0.000776`; exact `-0.001423`; nonexact `+0.021857`;
- `5m_offset_4`: all `+0.005283`; exact `+0.005334`; nonexact `-0.006993`.

## Adjudication

The native high/low envelope is a genuinely different **input source** from the historical close-only direction chain, but it does not produce a coherent direction/stability mechanism on the frozen universe:

- the fixed exact-vs-nonexact rank statistics remain near `0.5`; the largest is only `0.557834` for envelope-adjustment view distance;
- the outward-excursion and adjustment magnitudes do not separate v0.6.25 exact from nonexact pairs (`0.508060` and `0.498027` rank probabilities);
- positive stability-gain incidence is essentially identical in exact and nonexact groups (`55.56%` vs `55.00%`);
- the pooled stability gain is small, and cross-offset behavior is not coherent: offset 3 is negative for the broad population while offset 4 is negative for the nonexact group;
- the envelope adjustment itself is small relative to the underlying close-migration scale and does not explain the remaining exact-consistency failures.

Therefore the frozen category is **`v0644_high_low_envelope_redundant_or_unstable`**.

`gate_authorized=false`  
`challenger_authorized=false`  
`recognizer_changed=false`  
`qualification_changed=false`  
`direction_winner_changed=false`  
`morphology_acceptance=false`  
`trade_authority=false`  
`production_authority=false`

The native-anchor high/low envelope route is closed. No threshold, rescue, veto, high/low D1 replacement, or post-hoc composite with the closed W1/shape/sign families is authorized.
