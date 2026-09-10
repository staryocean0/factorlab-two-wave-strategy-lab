# Two-Wave v0.6.27 state-relative margin rescue protocol

Date: 2026-09-10
Status: frozen before outcome replay

## Research question

Can the validated v0.6.25 margin-gating contribution be made state-fair without tuning a new threshold, by expressing confidence as distance to the frozen state boundary relative to that state's own decision scale?

## Frozen upstream

- primary object: `two_wave_parent_structure_recognizer`;
- parent identity: v0.5.2;
- same-scale semantics: v0.5.4;
- immutable raw publication: v0.6.5;
- qualification policy: v0.6.18, unchanged;
- direction stability baseline: historical D1;
- rescue source: v0.6.23 four-support endpoint-erosion unanimous Huber consensus;
- v0.6.25 contribution: an absolute margin gate improves pooled exact agreement but is structurally state-asymmetric;
- v0.6.26 diagnostic: Range keep fraction 7.40% versus combined Trend 86.99%, with all introduced harm one-sided rescue.

No future return, PnL, H1/H2, third wave, 2021+, 2026 data, or cross-offset runtime feature is permitted.

## Single frozen challenger

No candidate menu and no threshold search.

1. If D1 is `Range`, `UpTrend`, or `DownTrend`, return D1 unchanged.
2. If D1 is `Uncertain`, compute the frozen v0.6.23 endpoint-erosion Huber consensus on the same single-view completed parent window.
3. If the four support views do not unanimously produce the same decisive state, remain `Uncertain`.
4. Compute the frozen consensus margin to the frozen Huber decision boundary.
5. Apply one state-relative confidence requirement derived from the already-used v0.6.25 trend gate:
   - frozen relative confidence fraction = `0.10 / 0.50 = 0.20`;
   - `UpTrend` / `DownTrend`: require `margin / 0.50 >= 0.20`, exactly equivalent to the v0.6.25 absolute `margin >= 0.10` rule;
   - `Range`: require `margin / 0.15 >= 0.20`, equivalent to `margin >= 0.03`.
6. Otherwise remain `Uncertain`.

The purpose is not to make Range easier ad hoc. It is to impose the same dimensionless boundary-confidence fraction on decision regions whose frozen widths differ.

## Frozen evaluation universe

Use only the v0.6.18 strict same-financial-identity pairs where both slicing views are v0.6.18-qualified.

Frozen controls that must reproduce exactly:

- filtered mutual-unique pairs: 57,029;
- raw strict same-event pairs: 29,453;
- both-v0.6.18-qualified pairs: 1,462;
- D1 exact: 1,400 / 1,462 = 95.7592%;
- D1 pooled decisive coverage: 48.9056%;
- D1 decisive agreement: 100%;
- D1 opposite UpTrend/DownTrend conflicts: 0.

Cross-offset information is evaluation-only and may not enter the candidate.

## Frozen promotion gate

The v0.6.27 direction component passes only if all conditions hold:

- upstream frozen controls reproduce exactly;
- D1 decisive override count = 0;
- each of offsets 1-4 has exact four-state agreement >= D1 on that offset;
- pooled exact four-state agreement >= D1;
- pooled decisive coverage >= 65%;
- pooled decisive coverage >= D1 + 15 percentage points;
- each offset side decisive coverage >= 55%;
- pooled decisive agreement >= 99.5%;
- opposite UpTrend/DownTrend conflict count = 0;
- pooled decisive state shares: UpTrend >=15%, DownTrend >=15%, Range >=2%;
- at least one D1-Uncertain record is rescued.

A pass installs only the best-supported **direction research component**. It does not change global morphology acceptance, trading authority, production authority, or the historical full-recognizer baseline.

A reject keeps D1 as the historical stability baseline and retains any local contribution separately. No post-result threshold tuning inside v0.6.27 is allowed.
