# CSI1000 development data

Every Parquet file in `development/` contains only `000852.SH` and only
2015-01-05 through 2020-12-31.

The files are filtered from frozen DataHub-built bar products. `timestamp` is a
timezone-aware UTC bar-end timestamp. `bar_end_shanghai` is the same instant in
Asia/Shanghai. `timestamp_source_serialized` retains the original string, whose
`Z` suffix wrapped a Shanghai wall-clock label in the source export.

These are signal/index rows, not tradable fills. `volume` is optional and mostly
unavailable for the CSI1000 index. Do not fill it. Do not manufacture missing
prices or locally resample a new wall-clock frequency.

Available products include the 1-minute terminal replay and the DataHub-built
5m, 15m, 30m, 60m and daily research views permitted by the included FactorLab
clock contracts. See `manifest.json` for exact row counts, schemas and hashes.

Rows from 2021 onward are intentionally absent. They remain outside the cloud
development information set.
