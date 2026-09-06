# Codex Cloud Environment — factorlab-two-wave-strategy-lab

This file is operational infrastructure only. It does not change any research formula, threshold, matcher, data contract, or promotion authority.

## Recommended environment settings

- Repository: `staryocean0/factorlab-two-wave-strategy-lab`
- Runtime: Python **3.11**
- Setup script:

```bash
bash .codex/cloud_setup.sh
```

- Maintenance script:

```bash
bash .codex/cloud_maintenance.sh
```

- Secrets: **none required** for the shipped research data and CL-20260906-003.
- Environment variables: none required. Optional: `PYTHONUNBUFFERED=1`.

## Internet access

For the current repository-backed research workflow, keep **Agent internet access = Off**.

Codex Cloud checks out the selected repository/branch before the setup script and the setup phase has network access for dependency installation. The five native 5m Parquet files are tracked directly in git, so the agent phase does not need GitHub/network access merely to read them.

If a later task genuinely requires internet access during the agent phase, enable it per environment with the minimum necessary allowlist/methods. Do not broaden network access just to compensate for a missing checkout or setup failure.

## First-run smoke check

After the environment is created, start a cloud chat on branch:

`codex/two-wave-phase1-20260905`

and ask Codex to run:

```bash
bash .codex/cloud_verify.sh
```

Success requires all five files below to be present in the checked-out workspace and to match `data/manifest.json` by file bytes, SHA256, and Parquet row count:

```text
data/development/5m_offset_0.parquet
data/development/5m_offset_1.parquet
data/development/5m_offset_2.parquet
data/development/5m_offset_3.parquet
data/development/5m_offset_4.parquet
```

## CL-20260906-003 execution

Once the smoke check passes, CL-003 can run entirely inside the Codex Cloud workspace:

```bash
python scripts/validate_theme_package.py

python -m pytest -q \
  tests/unit/test_market_state_tool_registry_v1_5.py \
  tests/unit/test_timing_infrastructure_four_layer_inventory.py \
  tests/unit/test_timing_layer2_measurement_boundary.py \
  tests/unit/test_timing_layer3_strategy_boundary.py \
  tests/unit/test_timing_layer3_orchestration.py \
  tests/unit/test_timing_strategy_identity_registry.py \
  tests/unit/test_two_wave_morphology_identity_v060.py \
  tests/unit/test_two_wave_unmatched_identity_decomposition_v061.py

mkdir -p cloud_results/local_v061_unmatched_identity_decomposition
python scripts/run_two_wave_unmatched_identity_decomposition_v061.py \
  --output cloud_results/local_v061_unmatched_identity_decomposition \
  | tee cloud_results/local_v061_unmatched_identity_decomposition/run.log
```

Before interpreting results, continue to enforce the frozen implementation identity and controls recorded in `docs/ops/cloud_local_communication.md` under `CL-20260906-003`.

## Cache behavior

If package/runtime settings or these setup scripts change, reset the Cloud Environment cache before the next formal run. The maintenance script is intended for cached-container branch refreshes.
