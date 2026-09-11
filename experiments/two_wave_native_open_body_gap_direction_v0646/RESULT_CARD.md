# Two-Wave v0.6.46 native open/body/gap direction attribution

Formal attribution: **`v0646_native_open_body_gap_fixed_statistics_complete_pending_governance_category`**

Frozen universe reproduced: **1462** pairs; D1 exact = **1400**; v0.6.25 exact = **1402**.

| quantity | v0.6.25 exact median | v0.6.25 nonexact median | P(nonexact > exact) |
|---|---:|---:|---:|
| pair mean abs anchor body | 0.191741 | 0.182911 | 0.478959 |
| pair mean abs oriented-body mean | 0.185693 | 0.181067 | 0.486591 |
| pair mean abs opening gap | 0.007592 | 0.008021 | 0.550856 |
| open-adjustment view distance L1 | 0.137121 | 0.132670 | 0.525915 |
| open stability gain L1 | -0.045523 | -0.032284 | 0.548990 |

Positive open-stability-gain fraction, v0.6.25 exact: `0.261056`.
Positive open-stability-gain fraction, v0.6.25 nonexact: `0.283333`.
Per-offset gain medians: `{'5m_offset_1': {'all': -0.03077267167087688, 'v0625_exact': -0.030388265172707384, 'v0625_nonexact': -0.03753271341579051}, '5m_offset_2': {'all': -0.07183381171573364, 'v0625_exact': -0.07871249558973076, 'v0625_nonexact': -0.008874694440202807}, '5m_offset_3': {'all': -0.06505691107348047, 'v0625_exact': -0.065737371902968, 'v0625_nonexact': -0.060062886026750174}, '5m_offset_4': {'all': -0.030406031686660652, 'v0625_exact': -0.030288317053895272, 'v0625_nonexact': -0.04717112905394007}}`.

Interpretation category is intentionally assigned only by the pre-frozen governance readout. No threshold, classifier, rescue or veto is authorized by this raw statistics bundle.
