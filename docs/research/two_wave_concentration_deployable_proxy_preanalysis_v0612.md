# v0.6.12 Preanalysis — native-5m deployable proxy for fine concentration / origin aliasing

Date: 2026-09-07

Status: **WRITTEN BEFORE ANY v0.6.12 REAL-DATA PROXY OUTPUT IS READ**

## 1. Why this workstream is now authorized

v0.6.10 established that supplied-1m `fine_concentration = J1` and the five-origin `origin_jump_median` are materially more stable across harmless 5m slicings than native close-to-close `J5`:

```text
native J5 cross-slicer abs-diff median        0.053931
fine concentration J1 median                  0.006474
origin-jump median median                     0.016958
```

v0.6.11 separately addressed roughness endpoint sensitivity and is now closed with a positive structural result. The workstreams remain separated: v0.6.12 does not change or combine the roughness erosion candidate.

The remaining concentration question is deployability: supplied `1m_official` cannot be assumed to be a production input. We therefore ask whether information already present in one causal native 5m OHLC stream can approximate the fine concentration property and signal when native bar-origin aliasing is large.

## 2. Runtime information firewall

The registered runtime candidate may use only native 5m OHLC bars inside the already-published raw leg interval. It may not use:

- supplied 1m rows;
- any alternate 5m offset;
- counterpart-view information;
- future bars after the leg endpoint;
- direction, qualification outcome, P&L or future returns.

The supplied 1m path and five-origin ensemble remain **audit oracles only**.

## 3. Frozen native quantities

For one published leg with native bars `a..b`, use transitions `j=a+1..b` so the number of native steps matches the close-path definition.

### A. Native close concentration — control

```text
DC_j = abs(C_j - C_{j-1})
J_close = max(DC) / sum(DC)    if sum(DC)>0
```

This is the existing native `J5` and remains the control, not a new candidate.

### B. Native true-range concentration — primary registered proxy

For every transition bar `j`:

```text
TR_j = max(
    H_j - L_j,
    abs(H_j - C_{j-1}),
    abs(L_j - C_{j-1})
)
```

Then:

```text
J_TR = max(TR) / sum(TR)       if sum(TR)>0
```

Rationale fixed before results: true range uses native high/low plus the prior close, so it can retain within-bar amplitude and gap information that close-only `J5` discards, while remaining causal and directly deployable from a single native 5m OHLC feed.

### C. High-low range concentration — diagnostic control

```text
R_j = H_j - L_j
J_HL = max(R) / sum(R)         if sum(R)>0
```

This separates the contribution of pure within-bar range from the previous-close/gap term in true range. It is not allowed to replace the primary proxy after results.

## 4. Frozen native uncertainty descriptor

No learned error model is allowed in v0.6.12.

When all three native concentrations are defined, register:

```text
proxy_spread = max(J_close, J_TR, J_HL) - min(J_close, J_TR, J_HL)
```

Interpretation is pre-registered only as a possible native warning signal: when different causal OHLC summaries disagree strongly, concentration measurement may be more sensitive to hidden intrabar path / bar origin.

No cutoff on `proxy_spread` is introduced.

## 5. Non-fitted empirical bracket

For audit only define the native bracket:

```text
proxy_lower = min(J_close, J_TR, J_HL)
proxy_upper = max(J_close, J_TR, J_HL)
proxy_width = proxy_upper - proxy_lower
```

Report whether `J1` and `origin_jump_median` fall inside this bracket. Observed coverage is **empirical only**; v0.6.12 makes no claim that the bracket is a mathematical bound.

No bracket expansion or fitted multiplier may be added after results.

## 6. Audit oracles

Using the same supplied `1m_official` path as v0.6.10, compute for the exact published leg interval:

```text
J1 = max(abs(diff(1m close))) / sum(abs(diff(1m close)))
```

and the already-frozen five-origin:

```text
origin_jump_median
origin_jump_range
```

These quantities are never passed to the runtime proxy function.

## 7. Frozen questions

v0.6.12 must answer, without fitting:

1. Is `J_TR` closer to `J1` and/or `origin_jump_median` than native `J_close`?
2. Is `J_TR` more stable than `J_close` across the frozen 29,453 strict same-event pairs?
3. Does `proxy_spread` correlate with actual origin uncertainty (`origin_jump_range`) and native-origin error?
4. Does the fixed native bracket achieve useful oracle coverage without becoming trivially wide?
5. Are these relationships consistent across all four harmless offsets and frozen duration bins?

## 8. No model selection

v0.6.12 may not:

- fit a linear/nonlinear mapping from native OHLC to the 1m oracle;
- choose weights among `J_close/J_TR/J_HL`;
- choose the best candidate by a downstream qualification result;
- fit a duration correction;
- fit a threshold or uncertainty cutoff.

The primary proxy is `J_TR` because it was registered before real v0.6.12 output.

## 9. Frozen universes / strata

Primary cross-slicer universe remains:

```text
8,381 / 5,770 / 6,204 / 9,098 = 29,453 strict same-event pairs
```

Corresponding four legs are aligned by ordinal.

Descriptive overlays only:

- 482 v0.6.6 both-qualified pairs;
- 699 qualification-disagreement pairs;
- 80 v0.6.1 target-repaired pairs;
- 56 target agreement / 24 target disagreement subsets.

No stratum can redefine the proxy.

## 10. Duration bins

Use the already-frozen native leg-duration bins only:

`1-3`, `4-5`, `6-11`, `12-23`, `24+` bars.

Report oracle error / proxy spread by bin. No duration-dependent remapping is allowed in v0.6.12.

## 11. Interpretation choices

Allowed adjudications only:

- `native_true_range_concentration_is_viable_for_separate_proxy_poc`;
- `native_proxy_tracks_center_but_uncertainty_envelope_is_too_wide`;
- `native_ohlc_proxies_do_not_reliably_track_fine_concentration`;
- `mixed_proxy_evidence_requires_more_preanalysis`.

A positive result authorizes only a later separately frozen property/qualification POC. It does not create a qualification rule.

## 12. Global firewall

Global state remains `morphology_replication_not_yet_accepted`; operational baseline remains v0.4.3.

No threshold fitting, matcher/projection/publication change, roughness re-optimization, direction/D1/D2/PAWCT, third-wave, outcomes/P&L, fresh OOS, paper trading or production is allowed in v0.6.12.
