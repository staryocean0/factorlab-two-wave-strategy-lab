# Current package and data declarations

Use [package scope](package_scope.json) and [data usage](data_usage_declaration.json)
together with the sole [current M0](../../../experiments/two_wave_m0_authority.json).
These declarations describe repository visibility and actual data-use history; they
cannot authorize scoring or override M0's blocked v0.7.8 state.

The same-named files one directory above are immutable **original seed snapshots**,
not current assertions that this public repository must be private or that external
validation never occurred. They remain byte-preserved for source-closure checks.
The package validator consumes the current data declaration for authority checks and
continues hashing both original seed declarations at their original paths.

The corrections were reconciled from maintenance commit
`49bae1a2d1cfb6ffc2fc4e520f6ff5553506bc9c`, without importing its alternative M0 schema
or reviving its automatic CI assumptions. See [reconciliation](../MAINTENANCE_RECONCILIATION_20260912.md).
