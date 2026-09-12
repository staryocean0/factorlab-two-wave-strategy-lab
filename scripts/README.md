# Scripts

`scripts/` contains three kinds of utilities:

1. **formal historical runners** used to reproduce a frozen experiment;
2. **diagnostic/build helpers** used by current or historical protocols;
3. **repository maintenance/validation tools**.

Historical runner scripts are intentionally retained after their one-shot GitHub workflow is deleted. A runner remaining in this directory does **not** mean the experiment is active or authorized to rerun with changed semantics.

## Current maintenance entry points

- `validate_theme_package.py` — fail-closed package/data/source-closure/current-authority validation used by CI.
- `apply_repository_consistency_refresh.py` — idempotent maintenance utility that promotes the machine authority to the already-adjudicated v0.7.8 evidence-availability state; it is not a scientific scorer.

## Authority rule

Formal current status comes from `experiments/two_wave_m0_authority.json`, not from the presence of a script. Completed formal science/governance one-shot workflows are removed from `.github/workflows/`; their runners remain here only when needed for reproducibility.

Do not repurpose an old formal runner for a new scientific question without a new frozen protocol and a clearly versioned adapter/runner.
