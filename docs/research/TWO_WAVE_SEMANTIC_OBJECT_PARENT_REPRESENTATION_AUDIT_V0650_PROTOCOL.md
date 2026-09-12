# Two-Wave v0.6.50 — Semantic-Object / Parent-Representation Audit Protocol

Status: **frozen before any v0.6.50 reference-conditioned object-correspondence statistics are read**.

## 1. Question

v0.6.48 independently confirmed only `16/120` hidden v0.6.18 candidate cases as complete same-scale two-wave parents. v0.6.49 then found no strongly supported existing qualification-failure family. The next upstream question is therefore not another qualification threshold:

> Does the algorithmic published five-anchor parent object itself correspond to the parent object that the independent annotators could see and label in the frozen 96-bar v0.6.48 chart?

This is a **read-only representation audit**. It cannot create or tune a qualification rule, direction rule, amplitude cutoff, parent-boundary threshold, or production policy.

## 2. Frozen inputs

Use only:

- `data/development/5m_offset_0.parquet`, SHA256 `bea21fa9dd9532e21605511e07561b33d5569f86f69f5a487507531593b14c48`;
- frozen v0.6.48 packet selection semantics (`LOOKBACK_BARS=96`);
- sampling commitment SHA256 `f4eeff13c1408c1ca3bf938c0cd8abc4dad961f63ed6a4a4158f243cd5b024c8`;
- frozen final independent reference labels SHA256 `321ce484f7f3f62bf6ff9d7d45de666e77d0cd17001b63a258a3e274e529884d`;
- the exact frozen v0.6.18 candidate-generation/publication chain already reused by v0.6.48/v0.6.49.

Candidate membership must reconstruct exactly `120` hidden candidate cases with `104` reference `no` and `16` reference `yes`.

No annotator notes or confidence may be used. No D1/v0.6.25 state, future bars, return, PnL, harmless offset, or downstream outcome may be used.

## 3. Deterministic algorithmic object per candidate cutoff

At each candidate cutoff, collect all v0.6.18-qualified published identities at that cutoff.

If exactly one identity exists, use it.

If multiple identities exist, choose a canonical representative **without looking at the reference label** by lexicographic order of:

1. `published_raw_occurrence_bars` tuple;
2. `phase` string.

Also report the number of multi-identity cutoffs. No best-match-to-human identity selection is permitted.

The algorithmic parent is the canonical published five-anchor tuple `(m0,m1,m2,m3,m4)`.

## 4. Frozen 96-bar chart coordinate system

For candidate cutoff `c`, the human chart contains source bars `[c-95, ..., c]`, mapped to visible positions `0..95`.

Map every algorithmic anchor to visible position:

`mi_visible = mi - (c - 95)`.

Frozen visibility diagnostics:

- `algorithmic_parent_fully_visible`: all five positions lie in `[0,95]`;
- `algorithmic_start_visible_position = m0_visible`;
- `algorithmic_end_visible_position = m4_visible`;
- `right_edge_gap_bars = 95 - m4_visible = c - m4`;
- `algorithmic_parent_span_bars = m4 - m0`;
- `algorithmic_parent_span_fraction = (m4-m0)/95`.

These are representation diagnostics, not candidate gates.

## 5. Reference-positive human-anchor correspondence

Use `p0..p4` only from the **frozen final reference label row** and only when all five are present and valid.

A human-anchor row is usable only if:

- reference presence is `yes`;
- all `p0..p4` are integers in `[0,95]`;
- `p0 < p1 < p2 < p3 < p4`.

Do not backfill missing human anchors from A/B/C source sheets, notes, chart inspection, or model pivots.

For each usable case compute:

- five-anchor mean absolute error: `mean(|mi_visible-pi|)`;
- normalized five-anchor MAE: previous value / 95;
- start-boundary absolute error: `|m0_visible-p0|`;
- end-boundary absolute error: `|m4_visible-p4|`;
- interval intersection-over-union (IoU) between `[m0_visible,m4_visible]` and `[p0,p4]`;
- algorithmic/human span ratio using `max(span_model,span_human)/min(span_model,span_human)`;
- containment category: `model_inside_human`, `human_inside_model`, `mutual_equal_boundaries`, `partial_overlap`, or `disjoint`.

No pivot permutation, time warp, nearest-neighbor rematching, phase reversal, or case-specific alignment optimization is permitted.

## 6. Frozen reference-no versus reference-yes visibility/staleness diagnostics

For all 120 candidate cases compare reference `no` versus reference `yes` for:

- full-visibility incidence;
- `right_edge_gap_bars` rank probability `P(no>yes)+0.5*tie`;
- `algorithmic_parent_span_fraction` rank probability `P(no<yes)+0.5*tie` (smaller parent is the prespecified failure direction).

These are object-availability/context diagnostics only; they must not be converted into filters.

## 7. Frozen decision rules

### 7.1 Packet/window visibility failure

Strong support only if **both** hold:

1. reference-no not-fully-visible incidence is at least `0.25`;
2. not-fully-visible incidence is at least `0.20` higher in reference-no than reference-yes.

### 7.2 Right-edge staleness

Strong support only if:

- `P(right_edge_gap_no > right_edge_gap_yes)+0.5*tie >= 0.70`.

### 7.3 Fragment-sized algorithmic parent

Strong support only if:

- `P(span_fraction_no < span_fraction_yes)+0.5*tie >= 0.70`.

This is a representation-level diagnostic and does **not** authorize a minimum-span filter.

### 7.4 Direct human-anchor correspondence

Direct correspondence is considered **identified** only if at least `8` of the `16` reference-positive candidate cases have usable frozen final-reference `p0..p4` anchors.

If fewer than `8` are usable, the anchor-correspondence result is `insufficient_frozen_human_anchor_coverage`; do not substitute other labels.

If at least `8` are usable:

- strong correspondence requires median interval IoU `>=0.70` **and** median normalized five-anchor MAE `<=0.08`;
- strong boundary mismatch requires median interval IoU `<0.50` **or** median normalized five-anchor MAE `>0.15`.

Values between these bands are `mixed_or_indeterminate`.

### 7.5 Systematic fragment/over-wide mapping in human-positive cases

Only when direct correspondence is identified:

- `model_fragment_of_human_parent` requires `model_inside_human` incidence `>=0.60` and median model/human span ratio `>=1.25`;
- `model_overwide_relative_to_human_parent` requires `human_inside_model` incidence `>=0.60` and median model/human span ratio `>=1.25`.

Otherwise neither claim is authorized.

## 8. Final adjudication categories

Choose exactly one primary category using the frozen precedence below:

1. `v0650_packet_window_visibility_failure` if §7.1 passes;
2. else `v0650_algorithmic_object_stale_at_reference_cutoff` if §7.2 passes;
3. else `v0650_algorithmic_parent_fragment_sizing_supported` if §7.3 passes **and**, when human-anchor correspondence is identified, §7.5 supports `model_fragment_of_human_parent`;
4. else `v0650_direct_parent_boundary_mismatch` if §7.4 gives strong boundary mismatch;
5. else `v0650_algorithmic_and_human_parent_correspondence_supported_but_presence_semantics_still_fail` if §7.4 gives strong correspondence and §§7.1–7.3 do not pass;
6. else `v0650_parent_representation_correspondence_not_identified`.

If human-anchor coverage is insufficient, category 4/5 cannot be used; category 6 is the default unless 1–3 independently pass.

## 9. Reporting

The formal result may contain only aggregate counts/distributions and the frozen final decision. Do not commit a case-level residual table pairing blinded case IDs with hidden stratum/model anchors/reference labels.

Report:

- input hashes and sampling commitment;
- candidate/reference counts;
- multi-identity count;
- full-visibility incidences by reference presence;
- rank diagnostics for right-edge gap and parent span;
- usable human-anchor count;
- if usable, aggregate anchor MAE / IoU / span-ratio / containment distributions;
- final category and every frozen rule boolean.

## 10. Governance

Whatever the result:

- `qualification_changed=false`;
- `direction_winner_changed=false`;
- `morphology_acceptance=false`;
- `trade_authority=false`;
- `production_authority=false`;
- no threshold fitting or residual gate mining is authorized.

A later semantic-object challenger, if justified, requires its own separately frozen protocol and cannot be fit directly to the v0.6.48 labels under this audit.
