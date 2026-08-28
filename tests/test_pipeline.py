from pathlib import Path

import pandas as pd

from vantage.config import Settings
from vantage.pipeline import join_weather, load_flights, load_weather


def test_load_flights_filters_corridor_and_creates_label(tmp_path: Path):
    path = tmp_path / "bts.csv"
    pd.DataFrame(
        {
            "FL_DATE": ["1/1/2026 12:00:00 AM", "1/1/2026 12:00:00 AM"],
            "OP_UNIQUE_CARRIER": ["AA", "AA"],
            "ORIGIN_AIRPORT_ID": [13930, 99999],
            "DEST_AIRPORT_ID": [12478, 12478],
            "CRS_DEP_TIME": [1230, 1000],
            "DEP_DELAY": [15, 0],
            "ARR_DELAY": [20, 0],
            "CANCELLED": [0, 0],
            "DISTANCE": [740, 1],
        }
    ).to_csv(path, index=False)

    flights, rows_read = load_flights(path, Settings(start_date=pd.Timestamp("2026-01-01").date(), end_date=pd.Timestamp("2026-01-01").date()))

    assert rows_read == 2
    assert len(flights) == 1
    assert flights.iloc[0]["origin"] == "ORD"
    assert flights.iloc[0]["delayed"]
    assert flights.iloc[0]["scheduled_departure"].hour == 12


def test_join_weather_uses_only_prior_observation(tmp_path: Path):
    weather_path = tmp_path / "metar.csv"
    pd.DataFrame(
        {
            "station": ["KORD", "KORD"],
            "valid": ["2026-01-01 11:00", "2026-01-01 13:00"],
            "tmpf": [30, 31], "dwpf": [20, 21], "relh": [50, 51], "drct": [0, 0],
            "sknt": [5, 5], "vsby": [10, 10], "gust": [None, None], "wxcodes": [None, None],
            "metar": ["old", "future"],
        }
    ).to_csv(weather_path, index=False)
    weather = load_weather(weather_path)
    flights = pd.DataFrame({"origin": ["ORD"], "scheduled_departure": pd.Timestamp("2026-01-01 12:00")})

    joined = join_weather(flights, weather)

    assert joined.iloc[0]["weather_metar"] == "old"
