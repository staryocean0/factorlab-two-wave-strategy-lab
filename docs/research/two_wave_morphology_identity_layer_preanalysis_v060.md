# v0.6.0 Preanalysis — separate two-wave morphology identity from event packing

## Financial requirement first

The target is to recognize **two consecutive complete same-scale raw-price waves**. If three same-scale complete waves `W1, W2, W3` exist consecutively, then both rolling observations `(W1,W2)` and `(W2,W3)` are legitimate two-wave morphology observations.

Nothing in the financial requirement says that recognized two-wave observations must be non-overlapping. Non-overlap can later be useful for trade de-duplication, position accounting, or independent-event statistics, but those are downstream concerns and are explicitly inactive in the morphology stage.

Therefore the current exclusive greedy ledger mixes two different semantic layers:

1. **recognition / financial identity** — which complete two-wave observations exist?;
2. **packing / ownership** — which overlapping observations should own a timeline segment for downstream use?

This coupling can change the recognized event identity when confirmation timing changes, even if the set of qualified morphology candidates is unchanged.

## Evidence motivating the correction

1. v0.5.8 large-margin PAWCT failures all have at least one five-anchor displacement >=1,163 minutes. They are not local perturbations of the same event.
2. The exact current ledger changes winner under a one-bar confirmation-order perturbation.
3. Main 5m has 734 qualified records but only 404 selected; 330 are overlap-suppressed.
4. 178 of 356 main-view overlap components are nontrivial; largest contains 11 qualified tuples.
5. Identical raw five-anchor financial identities can be born as multiple scale-evidence records: main 5m has 21 such duplicate groups / 43 records, but all duplicate groups have identical D1/phase geometry. Birth scale is therefore evidence about the same event, not necessarily a separate financial event.

## Candidate mathematical objects

### A. Canonical qualified financial identity — preferred

Define the single-view financial identity as:

`I = (start_phase, e0, e1, e2, e3, e4)`

where `e0..e4` are the five confirmed raw-price extremum occurrences of the complete two-wave observation.

Within one view:

- exact duplicates with the same five raw occurrence bars and same start phase are **one financial identity**;
- multiple birth-scale levels are retained as `scale_evidence`, not emitted as duplicate events;
- rolling windows with different five-anchor tuples remain different events even if their intervals overlap;
- every member must already pass the frozen qualification; canonicalization does not rescue rejected candidates;
- conflicting D1 geometry among exact same-anchor duplicates is a hard anomaly, not a tie to resolve.

### Causal publication detail

The **identity event** is immutable and is published when the first qualified member carrying that `(phase, five anchors)` identity is confirmed. A later same-anchor birth at another scale must not rewrite the earlier event. It is emitted as an append-only `scale_evidence` record linked to the already-published identity. Therefore full-run aggregation may show multiple scale members, but the causal event ledger itself never backfills `member_count`, `member_ids` or a later confirmation time into history.

This object is causal because it is constructed only from already-confirmed qualified members. It uses no future outcomes and no cross-view information.

### B. Exclusive packing — downstream diagnostic only

Keep the legacy ledger as a separate derived view for backward compatibility and later de-duplication experiments, but remove `selected` from morphology-identity authority.

`selected` may answer “which events does this packing policy keep?” It must not answer “which two-wave financial events exist?”.

### C. Delayed causal overlap-component representative

If a later trading/statistics layer truly requires one representative per overlap component, a delayed causal component-closure policy can be researched then. It is not preferred now because:

- transitive overlap components can grow;
- representative choice is another arbitrary model component;
- waiting for bounded closure adds latency;
- the financial morphology task does not require exclusivity in the first place.

### D. More direction formulas — rejected for now

Do not test another endpoint, envelope, PAWCT variant, filter or regression until event identity is separated from packing. Current evidence says the large direction failures are conditioned on comparing different five-extremum events.

## Cross-view audit semantics

Cross-view information must never enter the single-view recognizer. It is allowed only in an audit evaluator.

For adjacent supplied 5m offset views, a **strict local identity audit edge** is defined mechanically, not fitted:

- same start phase;
- five extrema compared position-by-position;
- every occurrence timestamp differs by at most **one nominal 5m bar width**;
- no outcome/direction label is used in matching.

If one event has multiple strict edges, it is **ambiguous** and is not tie-broken. Only mutual-unique edges count as same-event audit matches.

The one-bar relation is a semantic locality definition tied to the frozen 5m K-line scale. It is not a classifier threshold and is not used by production recognition.

## Expected architecture

`TCSS/ridge births -> frozen qualification -> canonical qualified morphology identities`

Then two separate consumers:

- morphology audit / direction research: uses canonical identities;
- optional legacy packing diagnostic: applies the exclusive ledger afterward.

This preserves all causal upstream work while preventing packing order from redefining financial identity.

## Safety / non-goals

- no requalification;
- no threshold change;
- no cross-view selection in recognizer;
- no future outcomes;
- no H1/H2, third wave, P&L or trading;
- no promotion of v0.5.8 PAWCT from this attribution alone;
- no claim of independent morphology accuracy without labels;
- operational baseline remains v0.4.3.
