# Two-Wave Layer 3 Research Control Plane

This private repository is a bounded FactorLab research theme package. Its
purpose is to implement and validate a causal two-complete-wave parent-structure
recognizer. It is not an authority to trade, mutate the local FactorLab current
pointer, or promote a strategy.

## Read order

1. `README.md`
2. `docs/INDEX.md`
3. `docs/user/two_wave_strategy_handoff_prompt.md`
4. `docs/governance/data_usage_declaration.json`
5. `docs/governance/layer3_tool16_candidate_slot.json`
6. The current Layer 1/2/3 contracts linked from `docs/INDEX.md`

## Frozen boundaries

- `tool_registry_v1_5` is the immutable current fifteen-tool prefix.
- The proposed sixteenth identity is
  `two_wave_parent_structure_recognizer`; it is only a candidate slot.
- Do not edit V1.5 in place. A candidate registry must be a new V1.6 descendant
  that preserves all fifteen identities byte-for-byte and appends exactly one
  research-only tool.
- The current Layer 3 architecture is
  `timing_layer3_strategy_architecture@2.2`; the current identity registry is
  `timing_strategy_identity_registry@2.2`. Neither has a registered usable
  strategy.
- This branch is infrastructure/shape-recognition research. It may not emit a
  position, choose an option contract, claim economic routing authority, or
  alter Layer 4.
- Never use result-driven calendar rules. Never call any provided year, date,
  event, or hand-labelled example a runtime state.

## Data contract

- All shipped market rows are `000852.SH` CSI1000 index signal data.
- The only shipped interval is 2015-01-05 through 2020-12-31 and its role is
  `development_material`.
- 2009-2014 minute history is unavailable for this index. The standard twelve
  2009-2020 strategy-slice promotion contract therefore cannot pass here.
- 2021 and later rows are physically absent and must not be downloaded,
  inferred, requested over the network, or fabricated.
- Data is index signal data, not a tradable fill surface. Index returns may not
  be reported as executable IM, ETF, or option returns.
- Timestamps in the package are normalized timezone-aware UTC bar-end times.
  The source serialized Shanghai wall clock is retained separately for audit.
- Use the supplied DataHub-built bar views. Do not resample new wall-clock
  frequencies locally.

## Required research order

1. Freeze the recognition specification and evaluation protocol before reading
   outcome metrics.
2. Implement online pivots/cycles, same-scale pairing, two-wave envelope and
   classification, versioned events, replay export, annotation support and
   targeted synthetic tests.
3. Prove prefix invariance: streaming and batch replay must produce identical
   confirmed events on every identical data prefix; appended future rows may
   not rewrite confirmed history.
4. Evaluate morphology against independent labels. Algorithm-produced labels
   are never ground truth. If labels are absent, report
   `morphology_replication_not_yet_accepted`.
5. Only after morphology acceptance may the third-wave hypothesis be opened.
6. Only after the statistical stage is frozen may a trading baseline be opened.

Do not optimize trading P&L to select the recognizer. Do not skip directly to a
ZigZag breakout backtest. Do not add fixed third-wave exits, profit targets,
timeouts, automatic reversal, or same-direction-break exits to the user baseline.

## Deliverables

- Put new reusable code under `src/factor_lab/market_state/` or
  `src/factor_lab/visual_structure/`.
- Put unit tests under `tests/unit/`.
- Put the executable workflow under `scripts/`.
- Put specifications and results under `docs/`.
- Put generated, reviewable results under `cloud_results/`; do not modify
  `data/development/`.
- Every conclusion must identify what was actually executed, the sample count,
  failures, unresolved gaps, and authority status.

Run at minimum:

```bash
python scripts/validate_theme_package.py
pytest -q tests/unit/test_market_state_tool_registry_v1_5.py \
  tests/unit/test_timing_infrastructure_four_layer_inventory.py \
  tests/unit/test_timing_layer2_measurement_boundary.py \
  tests/unit/test_timing_layer3_strategy_boundary.py \
  tests/unit/test_timing_layer3_orchestration.py \
  tests/unit/test_timing_strategy_identity_registry.py
```

No production, paper-trading, registered-use, parameter-selection, or fresh-OOS
authority is available in this repository.
