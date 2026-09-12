# Current verification workflow

The scientific checkpoint is read from `experiments/two_wave_m0_authority.json`.
This workflow validates the repository; it does not open an experiment or grant authority.

## Execution order and resource boundary

Use the current session when its checkout, interpreter and dependencies are actually
available. Otherwise hand the bounded missing step to the local model through
`cloud_local_communication.md`. GitHub Actions are a last resort and quota is
currently unavailable. Do not dispatch, rerun or repeatedly push to test quota.

The retained `.github/workflows/ci.yml` has no push, PR or scheduled trigger. Manual
execution additionally requires both the explicit confirmation input and repository
variable `TWO_WAVE_ACTIONS_ALLOWED=true`. Neither is permission to change science.
A skipped or unrun job is not a green verification result. Existing branch protections
must not be bypassed. Use `[skip ci]` on maintenance commits as an additional precaution.

## Full verification on a complete checkout

Use Python 3.11 with dependencies from the unchanged `pyproject.toml`. Keep virtual
environments and receipts outside the repository's bounded surface.

```bash
python3.11 -m venv /tmp/two-wave-verify-venv
/tmp/two-wave-verify-venv/bin/python -m pip install -e .
/tmp/two-wave-verify-venv/bin/python scripts/verify_repository.py \
  --report /tmp/two-wave-verification.json
```

The shared entrypoint executes, in order:

1. Current-authority, document, archive, binding, workflow, tracked-file inventory,
   protected-tree, Python-syntax and shell-syntax checks.
2. Original frozen-source and Development-data validation, including all data hashes,
   row counts, timestamp/OHLC invariants, the immutable fifteen-tool prefix and slot boundary.
3. The complete pytest suite, including the original scientific regressions.

Any failure stops downstream steps and remains a failure in the receipt. The current
interpreter/commands/exit codes/output are recorded. `--static-only` is explicitly
labelled partial, and a Python version outside the package contract cannot produce a
full-success receipt. No command runs historical scientific outcome runners.

## Updating current documents

Edit the machine authority only when backed by the corresponding adjudication and
then run `python scripts/check_repository_consistency.py --write-docs`. That command
has a fixed six-document write allowlist. It does not rewrite result files, reference
labels, protocols, the seed manifest, source modules or data.

Do not append a new current-status paragraph while leaving an obsolete current
paragraph intact. The checker compares each generated document with the full
expected rendering and checks every displayed metric against pinned evidence.

## Historical replay and retirement

Scientific runners and adapters remain historical/dependency code, not an active job
queue. In particular v0.7.6's authoritative historical adapter is the `_retry.py`
runner and v0.7.7's is the `_formal.py` runner. Do not delete their base modules merely
because a wrapper superseded their CLI path.

The old v0.7.7 governance writer is archived; invoking its original CLI path exits 2.
The import-only compatibility API serves existing historical tests against the archived
schema-1.32 authority. It never defines the current schema-2.0 authority.

## Acceptance record

The full checkout/Python-3.11 verification receipt is still required for this cleanup.
Current-session unit/syntax checks are recorded separately. Only an actual completed
receipt can close task `TW-CONSISTENCY-20260912-01`; neither historical CI nor a directory
inventory is full-regression evidence.
