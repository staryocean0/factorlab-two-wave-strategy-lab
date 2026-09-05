# FactorLab Two-Wave Layer 3 Research Theme

This is a private, minimal cloud research package for the proposed sixteenth
FactorLab timing tool: `two_wave_parent_structure_recognizer`.

The package gives Codex Cloud enough context to implement and test the
recognizer without uploading the 2 TiB local DataHub or the 283 GiB FactorLab
working tree. It includes:

- the user's full two-wave handoff prompt;
- the current FactorLab Layer 1/2/3 timing contracts and their Python import
  closure;
- the immutable fifteen-tool V1.5 registry prefix;
- the current Layer 3 architecture/identity indexes;
- FactorLab strategy-research governance;
- DataHub-built CSI1000 bar views for 2015-2020 development only;
- package validation and regression tests.

It intentionally excludes Layer 4 economics, raw transaction data, options,
futures, private credentials, local outputs, historical FactorLab Git history,
and all post-2020 CSI1000 rows.

The canonical infrastructure shell is
`docs/ops/timing_infrastructure_four_layer_inventory@1.0.json`: 数据时钟 →
K线测量 → Layer 3策略研究 → 执行标的。Only the first three layers are
executable in this theme; the execution layer is present as a boundary contract.

## Start here

```bash
python -m pip install -e .
python scripts/validate_theme_package.py
pytest -q
```

Then follow [`docs/user/cloud_execution_prompt.md`](docs/user/cloud_execution_prompt.md).

## Scientific status

`infrastructure_candidate_waiting_morphology_replication`

This repository may produce a research candidate and a pull request. It cannot
install the tool into the authoritative local FactorLab registry or claim that
the strategy works.
