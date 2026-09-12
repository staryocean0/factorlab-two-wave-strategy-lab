# v0.6.50 Semantic-Object / Parent-Representation Audit — Result Card

Formal workflow run: `34666720984`  
Protocol: `docs/research/TWO_WAVE_SEMANTIC_OBJECT_PARENT_REPRESENTATION_AUDIT_V0650_PROTOCOL.md`  
Protocol freeze commit: `f7c80c2331c7bbefbe1dd4dcc4b0669e92c2113a`  
Formal raw result commit: `51657926c71e0308d64a233405f9363073e8997b`

## Frozen controls

- source SHA256: `bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48`
- final reference SHA256: `321ce484f7f3f62bf6ff9d7d45de666e77d0cd17001b63a258a3e274e529884d`
- sampling commitment SHA256: `f4eeff13c1408c1ca3bf938c0cd8abc4dad961f63ed6a4a4158f243cd5b024c8`
- candidate cases: `120` = `104` reference-no + `16` reference-yes
- v0.6.18 qualified publications available: `2115`
- multi-identity candidate cutoffs: `2`
- canonical multi-identity selection was fixed lexicographically before reading correspondence results.

No annotator notes/confidence, direction prediction, future outcome, PnL, harmless-offset signal, threshold fit, or case-level residual table was used.

## Window visibility / maturity

The frozen 96-bar annotation packet did **not** truncate the algorithmic parent object:

- reference-no full visibility: `104/104 = 100%`
- reference-yes full visibility: `16/16 = 100%`

The object was also not systematically stale at the chart cutoff:

- reference-no right-edge gap median: `4` bars (`Q1=3`, `Q3=6`)
- reference-yes right-edge gap median: `4` bars (`Q1=3`, `Q3=5.25`)
- `P(gap_no > gap_yes)+0.5*tie = 0.5018028846153846`

Thus neither packet/window visibility failure nor right-edge staleness is supported.

## Parent span

Algorithmic parent span is somewhat smaller in reference-negative cases, but not strongly enough under the frozen rule:

- reference-no median span fraction: `0.4473684210526316`
- reference-yes median span fraction: `0.5473684210526316`
- `P(span_no < span_yes)+0.5*tie = 0.6213942307692307`
- frozen strong-support threshold: `>=0.70`

Therefore no fragment-size mechanism or minimum-span gate is authorized.

## Direct human-anchor correspondence

`11/16` reference-positive cases contain complete valid frozen final-reference `p0..p4`, exceeding the preregistered minimum of `8`; direct correspondence is therefore identifiable.

Across those 11 cases:

- median parent-interval IoU: `0.7741935483870968`
- median normalized five-anchor MAE: `0.12421052631578948`
- median start-boundary absolute error: `17` bars
- median end-boundary absolute error: `4` bars
- median model/human span ratio: `1.2678571428571428`

Containment:

- partial overlap: `5/11 = 45.45%`
- model inside human: `3/11 = 27.27%`
- human inside model: `1/11 = 9.09%`
- equal outer boundaries: `1/11 = 9.09%`
- disjoint: `1/11 = 9.09%`

The frozen strong-correspondence rule required IoU `>=0.70` **and** normalized anchor MAE `<=0.08`; only the IoU side passes. The frozen strong-boundary-mismatch rule required IoU `<0.50` or normalized anchor MAE `>0.15`; neither condition passes.

Therefore the direct mapping is **mixed / indeterminate**, not strong correspondence and not strong mismatch.

## Formal verdict

**`v0650_parent_representation_correspondence_not_identified`**

The evidence rules out three simple explanations:

1. the model parent was outside the human chart;
2. the model parent ended too early relative to the cutoff;
3. a simple systematically smaller model parent explains the reference failures.

At the same time, the 11 human-positive anchored cases show a structured asymmetry: outer intervals overlap fairly well, the model end boundary is close to the human end, but the model start boundary and the five-anchor sequence are materially less aligned. Because the preregistered thresholds place the aggregate result between strong correspondence and strong mismatch, this is only a descriptive clue, not a new rule.

## Authority effect

- qualification changed: **false**
- direction winner changed: **false**
- morphology acceptance: **false**
- trade authority: **false**
- production authority: **false**

No span threshold, boundary tolerance, pivot-remapping rule, or semantic-object challenger is authorized from v0.6.50.

The next legitimate research breakpoint is a separately frozen **left-boundary / internal-pivot correspondence decomposition** using only the frozen human-positive anchored cases plus aggregate negative-case context. It must remain read-only and cannot fit a new recognizer to the v0.6.48 labels.
