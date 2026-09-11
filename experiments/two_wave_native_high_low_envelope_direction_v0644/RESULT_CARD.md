# Two-Wave v0.6.44 native high/low envelope direction attribution

Formal attribution: **`v0644_native_high_low_envelope_fixed_statistics_complete_pending_governance_category`**

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
Per-offset gain medians: `{'5m_offset_1': {'all': 0.00476191144528316, 'v0625_exact': 0.00459096712977003, 'v0625_nonexact': 0.009065932283269774}, '5m_offset_2': {'all': 0.0024511284571350905, 'v0625_exact': 0.0023940272183979316, 'v0625_nonexact': 0.015499867500368393}, '5m_offset_3': {'all': -0.00077647230217044, 'v0625_exact': -0.001422625607912122, 'v0625_nonexact': 0.02185665270592614}, '5m_offset_4': {'all': 0.005283161333537567, 'v0625_exact': 0.005334152721453954, 'v0625_nonexact': -0.00699296462603538}}`.

Interpretation category is intentionally left for the fixed-statistics governance readout; no threshold, classifier, rescue or veto is authorized by this bundle.
