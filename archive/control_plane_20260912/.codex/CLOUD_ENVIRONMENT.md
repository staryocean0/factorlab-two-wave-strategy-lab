# Codex Cloud Environment — factorlab-two-wave-strategy-lab

Operational infrastructure only. This does not change research formulas, thresholds, matchers, data contracts, or promotion authority.

## Recommended environment settings

- Repository: `staryocean0/factorlab-two-wave-strategy-lab`
- Runtime: Python **3.11**
- Setup script: `bash .codex/cloud_setup.sh`
- Maintenance script: `bash .codex/cloud_maintenance.sh`
- Secrets: none required for shipped research data / CL-20260906-003
- Environment variables: none required; optional `PYTHONUNBUFFERED=1`
- Agent internet access: **Off** for the current repository-backed research workflow

Codex Cloud checks out the repository before setup. Setup runs with internet access for dependency installation. The five native 5m Parquet files are tracked in git, so the agent phase does not need network access merely to read them.

## First cloud-chat smoke test

Start the cloud chat on branch `codex/two-wave-phase1-20260905` and run:

```bash
bash .codex/cloud_verify.sh
```

Success means all five native 5m Parquet files are present and match `data/manifest.json` by file bytes, SHA256, and Parquet row count.

## CL-20260906-003

After the smoke test passes, execute CL-003 exactly as frozen in `docs/ops/cloud_local_communication.md` on branch `codex/two-wave-phase1-20260905`.

If environment scripts or runtime/package settings change, reset the Cloud Environment cache before the next formal run.
