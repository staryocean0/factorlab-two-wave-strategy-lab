# v0.6.51 Left-Boundary / Internal-Pivot Decomposition — Result Card

Formal workflow run: `34667721079`  
Protocol: `docs/research/TWO_WAVE_LEFT_BOUNDARY_INTERNAL_PIVOT_DECOMPOSITION_V0651_PROTOCOL.md`  
Protocol freeze commit: `ea6511289ab3131565bf13948f37663937e4dc41`

## Frozen universe

The audit reconstructs exactly the `11` v0.6.50 human-positive candidate cases with complete frozen final-reference `p0..p4` anchors. No case-level anchor table is written.

Controls retained:

- source SHA256: `bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48`
- final reference SHA256: `321ce484f7f3f62bf6ff9d7d45de666e77d0cd17001b63a258a3e274e529884d`
- sampling commitment: `f4eeff13c1408c1ca3bf938c0cd8abc4dad961f63ed6a4a4158f243cd5b024c8`
- multi-identity anchored cases: `0`
- no notes/confidence, direction predictions, future outcomes, PnL, threshold fitting or pivot remapping used.

## Ordinal-resolved absolute error

Median absolute model-vs-human anchor error:

- `p0`: **17 bars**
- `p1`: **13 bars**
- `p2`: **6 bars**
- `p3`: **11 bars**
- `p4`: **4 bars**

`9/11` cases have larger absolute error at the start boundary than at the end boundary; only `1/11` is the reverse and `1/11` ties.

Median signed displacement is `+5, +1, 0, +5, 0` bars for `p0..p4`. The start-anchor sign is not unanimous, so the evidence does not support a deterministic fixed shift.

## Rigid translation decomposition

Per-case median signed displacement was removed diagnostically, without changing any model anchor.

- raw five-anchor MAE median: **11.8 bars**
- translation-removed MAE median: **3.8 bars**
- median MAE reduction: **57.53%**

However, the start/end boundary-offset disagreement has median **12 bars** (`Q1=2`, `Q3=14.5`), above the preregistered rigid-translation maximum of `6` bars. Therefore the mismatch cannot be attributed to a single case-level time translation.

## Boundary-normalized internal geometry

After separately normalizing each model and human parent interval to `[0,1]`:

- median internal phase MAE: **0.0839727**
- median leg-share MAE: **0.0756939**
- median center-pivot phase error: **0.0413753**

Per internal ordinal median absolute phase error:

- `p1`: **0.07545**
- `p2`: **0.04138**
- `p3`: **0.04256**

This is far below the preregistered internal-mismatch band (`median phase MAE > 0.12`, or two internal ordinals > `0.12`). Internal phase mismatch is therefore **not supported**.

But the preregistered internal-correspondence / left-boundary rule required median internal phase MAE `<=0.08`. The observed `0.0839727` misses that gate narrowly. The threshold cannot be relaxed after observing the result.

## Frozen decision

- rigid translation dominant: **false**
- left-boundary dominant: **false**
- end-boundary dominant: **false**
- internal pivot/phase mismatch: **false**
- mixed boundary + internal mismatch: **false**
- internal geometry correspondence after boundary normalization: **false**

Formal primary category:

**`v0651_correspondence_decomposition_mixed_or_unresolved`**

## Interpretation

The strongest descriptive evidence remains concentrated toward the left/start side and a removable common temporal component:

- p0 error is much larger than p4;
- 9/11 cases are start-error dominant;
- translation removal reduces median anchor MAE materially;
- internal normalized geometry is much closer than raw anchors.

But the frozen evidence bands deliberately do not authorize a categorical mechanism claim. In particular, `0.08397` may not be rounded or reinterpreted as passing the `0.08` rule.

The next legitimate audit moves away from label-error thresholds and into **algorithmic lineage/provenance**: determine whether ordinal-0 predecessor support / first-valid publication creates a structurally different start-anchor construction from ordinals 1–4. That audit should inspect algorithm mechanics and aggregate lineage evidence, not fit a boundary tolerance to these 11 labels.

## Authority effect

- threshold fitting: **false**
- pivot remapping: **false**
- qualification changed: **false**
- direction winner changed: **false**
- morphology acceptance: **false**
- trade authority: **false**
- production authority: **false**
