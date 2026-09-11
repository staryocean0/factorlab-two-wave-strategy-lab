# Two-Wave v0.6.48 Blinded Independent Reference-Label Construction Protocol

Date: 2026-09-12
Status: **frozen before packet generation and before any independent annotation exists**

## 1. Purpose

v0.6.48 does **not** propose another morphology classifier, gate, feature, threshold, or direction challenger.

Its sole purpose is to construct a prediction-blinded human/external reference-label packet for the existing Two-Wave parent morphology contract:

`two complete same-scale waves -> Range / UpTrend / DownTrend / Uncertain`.

The repository audit immediately before this protocol found no existing independent human/external reference-label dataset in the Two-Wave, Trend/Reversion, or STAR50 related repositories. Existing algorithm outputs, result cards and governance `ADJUDICATION` files are explicitly **not** ground truth.

Therefore scoring is blocked until independent labels are returned and frozen.

## 2. Scientific authority entering v0.6.48

Nothing in this protocol changes current authority:

- qualification champion: `v0.6.18 path-gate demotion`;
- parent-direction winner: unset;
- strongest Development pooled-exact direction contribution: `v0.6.25 absolute-margin erosion-consensus rescue`;
- v0.6.47 temporal replication verdict: `v0647_temporal_replication_under_original_v0625_gate_not_all_pass`;
- morphology acceptance: false;
- trade authority: false;
- production authority: false.

No v0.6.48 packet outcome may silently promote v0.6.25 or any other component.

## 3. Data boundary

The label-construction packet uses only the already-shipped CSI1000 Development main view:

`data/development/000852.SH_20150105_20201231_5m_offset_0.parquet`

The source bytes must match the repository manifest before any packet is emitted.

The packet construction period is 2015-01-05 through 2020-12-31. This is **not fresh OOS**. v0.6.48 is therefore a reference-label calibration/construction stage, not sufficient by itself for full morphology acceptance.

No post-2020 data are fetched for this packet. No future return, P&L, H1/H2, third-wave outcome or later-period response enters sampling, rendering or labeling.

## 4. Case universe and frozen sampling

The packet contains exactly **240 cases**, year-balanced across 2015-2020:

- 20 hidden `candidate` cases per year = 120 total;
- 20 hidden `control` cases per year = 120 total.

### 4.1 Candidate stratum

Candidate cases are cutoffs at unique main-view confirmation bars where the frozen v0.6.18 publication/qualification chain has at least one `candidate_qualified=true` parent identity.

The candidate stratum is used only to enrich the packet with enough plausible two-wave structures for reference calibration. It is **not** exposed to annotators.

No D1/v0.6.25 state, direction label, rescue status, confidence, harmless-offset information, future outcome, or P&L participates in candidate selection.

If multiple v0.6.18-qualified identities share one confirmation cutoff, the cutoff remains one case.

### 4.2 Control stratum

Control cases are ordinary main-view cutoffs that:

1. have at least 96 observed 5-minute bars available at or before the cutoff;
2. are not a v0.6.18-qualified confirmation cutoff;
3. have no v0.6.18-qualified confirmation in the preceding 12 main-view bars, inclusive of the cutoff;
4. use no future bars to establish visible case content.

This control stratum probes obvious missed morphology without pretending to be an unbiased market-prevalence sample.

### 4.3 Stable selection rule

Within each year and stratum, eligible case cutoffs are ranked by ascending SHA-256 of:

`v0648-reference-set|<stratum>|<year>|<cutoff_timestamp_utc>`

The first 20 unique cutoffs are selected.

No outcome, prediction class, direction state, price return, confidence score, volatility regime or later information is used for ranking.

If any year/stratum has fewer than 20 eligible cases, packet construction fails closed; sample size may not be silently reduced after inspection.

## 5. Annotator-visible case representation

Each case displays exactly the **96 main-view 5-minute bars ending at the case cutoff**, with bar positions `0..95`.

Visible information is limited to contemporaneously observed OHLC morphology. Absolute date/year and sampling stratum are withheld from the annotator-facing packet to reduce temporal and stratum anchoring.

The packet must not display or encode:

- `candidate` versus `control` stratum;
- v0.6.18 qualification result or rejection reasons;
- model pivot/anchor locations;
- D0/D1/v0.6.25 labels or rescue decisions;
- harmless comparison offsets;
- confidence scores from any model;
- post-cutoff bars;
- future returns/P&L/outcomes;
- STAR50/CSI1000 risk-state labels or other downstream strategy information.

The chart is a neutral OHLC/close representation only. Case filenames and IDs must not disclose the hidden stratum or date.

## 6. Independent annotation contract

Two independent annotators must label every case without seeing model outputs, hidden strata, repository scoring artifacts, each other's labels, or post-cutoff bars.

For every case they record:

- `two_complete_same_scale_waves`: `yes | no | uncertain`;
- `parent_state`: `range | uptrend | downtrend | uncertain | not_applicable`;
- `p0`, `p1`, `p2`, `p3`, `p4`: optional visible bar positions `0..95` identifying five alternating extrema when the annotator believes a two-wave parent exists;
- `confidence`: `high | medium | low`;
- `annotator_id`;
- optional concise notes.

`parent_state=not_applicable` is required when `two_complete_same_scale_waves=no`.

The annotator is judging the semantic object, not reproducing the repository's numeric qualification thresholds. “Same scale” should mean two visibly comparable completed waves belonging to one parent structure, rather than mechanically copying v0.6.18 gates.

No annotator discussion is allowed before both first-pass sheets are submitted and their SHA-256 hashes are frozen.

## 7. Adjudication

A third independent adjudicator sees the same blinded case material plus the two frozen first-pass labels only for disagreement cases.

Adjudication is required when the first two annotators disagree on either:

- two-wave presence (`yes/no/uncertain`), or
- parent state when both assert presence.

The third adjudicator may not see model predictions, hidden stratum, future bars, returns or P&L.

A finalized reference set cannot contain an unresolved disagreement.

## 8. Pre-frozen label-quality gates

These gates are evaluated **before model scoring is unblinded**.

Across all 240 cases:

1. first-pass exact agreement on `two_complete_same_scale_waves` must be at least 85%;
2. Cohen's kappa for the three-way presence label must be at least 0.70 when mathematically defined;
3. among cases where both first-pass annotators label presence `yes`, exact agreement on the four parent states (`range/uptrend/downtrend/uncertain`) must be at least 80%;
4. corresponding parent-state Cohen's kappa must be at least 0.70 when mathematically defined;
5. after adjudication, unresolved disagreements must equal zero.

If prevalence makes a kappa undefined, the exact-agreement gate remains mandatory and the undefined kappa is reported rather than replaced post hoc.

Failure of label-quality gates blocks model/reference scoring. It does not authorize relabeling criteria, dropping difficult cases, or changing the sample after inspection.

## 9. Pre-frozen model/reference metrics for the later scoring stage

The eventual scoring routine is defined now, while reference labels are unknown.

### 9.1 Candidate stratum

After reference labels are finalized and the hidden stratum is unblinded, report:

- reference-confirmed two-wave presence fraction among candidate cases;
- model parent-state exact agreement among reference-confirmed two-wave cases;
- UpTrend-vs-DownTrend opposite-conflict rate;
- model uncertain rate;
- confusion matrix for `range/uptrend/downtrend/uncertain`.

The pre-frozen calibration-support gates are:

- candidate reference-confirmed presence fraction >= 0.80;
- parent-state exact agreement >= 0.85 among reference-confirmed candidate cases;
- UpTrend/DownTrend opposite-conflict rate <= 0.02.

### 9.2 Control stratum

Report the fraction of control cases judged by finalized reference labels to contain a completed same-scale two-wave parent near the right edge of the visible window.

The pre-frozen calibration-support gate is:

- human-positive control miss fraction <= 0.20.

Because the control stratum is enriched by a frozen model-history exclusion rule, it is not an unbiased prevalence estimator and must not be reported as one.

### 9.3 Temporal diagnostics

The same metrics are reported by calendar year, but year-level values are descriptive only in v0.6.48 because each year has only 20 candidate and 20 control cases. No year may be removed after seeing its labels.

## 10. What a v0.6.48 pass can and cannot mean

Even if every label-quality and model/reference calibration gate passes:

- `morphology_acceptance` remains false;
- parent-direction winner remains unset;
- trade authority remains false;
- production authority remains false.

A successful v0.6.48 result may only establish:

`independent_reference_label_calibration_supported_on_frozen_2015_2020_blinded_sample`

Full morphology acceptance still requires a separately frozen independent validation using a fresh held-out reference-label set and the same non-tunable semantics.

A failure means the corresponding semantic or recognition weakness must be recorded. It does **not** authorize threshold fitting against the reference labels.

## 11. Packet outputs

The construction runner must emit at least:

- `ANNOTATOR_README.md`;
- `EMPTY_LABEL_SHEET.csv`;
- `PUBLIC_CASE_MANIFEST.csv` containing only blinded `case_id` and chart filename;
- `cases/<case_id>.png` for 240 cases;
- `PACKET_MANIFEST.json` with source hash, code identity, counts and public-file hashes;
- `SAMPLING_COMMITMENT.json` containing the SHA-256 commitment of the hidden deterministic case mapping, but not the hidden mapping itself;
- `SCORING_BLOCKED.json` stating that no independent labels yet exist and model scoring is forbidden;
- one ZIP containing only annotator-visible material.

The hidden mapping is reproducible from the frozen source bytes, protocol and generator; it is not included in the annotator ZIP.

## 12. Forbidden shortcuts

- use algorithm-produced labels as human/reference truth;
- use migrated v1-v13 state outputs as reference labels;
- show D1/v0.6.25 output to annotators before labels freeze;
- show v0.6.18 pivots/anchors/qualification to annotators;
- show harmless offsets or cross-offset disagreement;
- show post-cutoff bars, future returns, P&L or downstream outcomes;
- stratify by model direction class or later correctness;
- change sample membership after seeing annotations;
- tune v0.6.18/v0.6.25 thresholds on reference labels;
- drop low-confidence or difficult cases post hoc;
- treat a v0.6.48 Development-period calibration pass as full morphology acceptance.

## 13. Frozen execution order

1. freeze this protocol;
2. implement and test packet builder;
3. validate source manifest and build the 240-case blinded packet;
4. freeze packet manifest + sampling commitment;
5. distribute only the annotator ZIP to two independent annotators;
6. freeze both first-pass label-sheet hashes;
7. evaluate label-quality gates;
8. adjudicate disagreements while still model-blind;
9. freeze final reference labels;
10. only then unblind the deterministic hidden mapping and run the pre-frozen scoring metrics;
11. update governance without changing scientific gates post-result.
