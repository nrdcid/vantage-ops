# Predictive Ops

Phase 0 scaffold for a mini ASI-style predictive operations decision-support
system: predict disruption risk, rank courses of action, and explain the result
with cited evidence.

## Phase 0

The initial scope is the ORD/JFK/ATL corridor during summer convective-weather
months. The scaffold provides:

- a small, typed configuration surface driven by environment variables;
- download helpers for BTS and Aviation Weather Center files;
- a join-key inspection command for BTS airport codes and AWC station IDs;
- a testable Python package and local-only data directories.

No data is downloaded during installation. Put source files under `data/raw/`
and run:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python -m vantage.data_sources --help
python -m vantage.join_keys --bts data/raw/bts.csv --awc data/raw/awc.csv
pytest
```

## Phase 1

Build the validated corridor dataset with a time-safe METAR join:

```bash
VANTAGE_START_DATE=2026-01-01 VANTAGE_END_DATE=2026-01-09 \
  build-dataset
```

The command writes `data/processed/flights_weather.csv`, labels flights with a
15-minute departure delay or cancellation as disrupted, and reports weather
join coverage. The current raw METAR file has no ORD/JFK/ATL stations, so its
reported weather match rate is expected to be zero until a matching export is
added.

The download command accepts explicit URLs because BTS exports and AWC cache
locations vary by month and should be recorded in a reproducible manifest.
