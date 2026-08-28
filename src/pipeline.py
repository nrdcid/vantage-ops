"""Phase 1 data validation, cleaning, and BTS/METAR joining."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

try:
    from .config import Settings
except ImportError:  # Support the repository's legacy flat src layout.
    from config import Settings


# BTS uses numeric airport identifiers while METAR uses ICAO station names.
AIRPORT_IDS = {"ORD": 13930, "JFK": 12478, "ATL": 10397}
BTS_COLUMNS = {
    "FL_DATE",
    "OP_UNIQUE_CARRIER",
    "ORIGIN_AIRPORT_ID",
    "DEST_AIRPORT_ID",
    "CRS_DEP_TIME",
    "DEP_DELAY",
    "ARR_DELAY",
    "CANCELLED",
    "DISTANCE",
}
METAR_COLUMNS = {"station", "valid", "tmpf", "dwpf", "relh", "drct", "sknt", "vsby", "gust", "wxcodes", "metar"}


@dataclass(frozen=True)
class ValidationReport:
    bts_rows_read: int
    flight_rows: int
    weather_rows: int
    weather_matches: int
    bts_start: str
    bts_end: str
    weather_start: str
    weather_end: str

    @property
    def weather_match_rate(self) -> float:
        return self.weather_matches / self.flight_rows if self.flight_rows else 0.0


def _require_columns(frame: pd.DataFrame, required: set[str], source: str) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{source} is missing required columns: {', '.join(missing)}")


def _scheduled_timestamp(date_values: pd.Series, hhmm_values: pd.Series) -> pd.Series:
    """Convert BTS's integer HHMM field into a timezone-naive UTC timestamp."""
    times = pd.to_numeric(hhmm_values, errors="coerce").fillna(0).astype(int).astype(str).str.zfill(4)
    # BTS occasionally uses 2400 for midnight; normalize it to the following day.
    midnight = times.eq("2400")
    times = times.where(~midnight, "0000")
    result = pd.to_datetime(date_values.dt.strftime("%Y-%m-%d") + " " + times, errors="coerce")
    return result + pd.to_timedelta(midnight.astype(int), unit="D")


def load_flights(path: Path, settings: Settings) -> tuple[pd.DataFrame, int]:
    """Load, validate, and filter BTS flights to the configured corridor/date window."""
    frame = pd.read_csv(path, usecols=lambda column: column in BTS_COLUMNS, low_memory=False)
    _require_columns(frame, BTS_COLUMNS, "BTS file")
    rows_read = len(frame)
    frame["flight_date"] = pd.to_datetime(frame["FL_DATE"], format="mixed", errors="coerce")
    if frame["flight_date"].isna().any():
        raise ValueError("BTS file contains unparseable FL_DATE values")
    frame["origin"] = frame["ORIGIN_AIRPORT_ID"].map({AIRPORT_IDS[a]: a for a in settings.airports if a in AIRPORT_IDS})
    frame["destination"] = frame["DEST_AIRPORT_ID"].map({AIRPORT_IDS[a]: a for a in settings.airports if a in AIRPORT_IDS})
    frame = frame[
        frame["flight_date"].dt.date.between(settings.start_date, settings.end_date)
        & frame["origin"].notna()
        & frame["destination"].notna()
        & (frame["origin"] != frame["destination"])
    ].copy()
    frame["scheduled_departure"] = _scheduled_timestamp(frame["flight_date"], frame["CRS_DEP_TIME"])
    if frame["scheduled_departure"].isna().any():
        raise ValueError("BTS file contains unparseable CRS_DEP_TIME values")
    frame["cancelled"] = frame["CANCELLED"].fillna(0).astype(bool)
    frame["delayed"] = frame["DEP_DELAY"].fillna(0).ge(15)
    frame["disrupted"] = frame["cancelled"] | frame["delayed"]
    return frame.reset_index(drop=True), rows_read


def load_weather(path: Path) -> pd.DataFrame:
    """Load METAR observations and normalize station names to IATA-like codes."""
    frame = pd.read_csv(path, low_memory=False)
    _require_columns(frame, METAR_COLUMNS, "METAR file")
    frame["observation_time"] = pd.to_datetime(frame["valid"], errors="coerce")
    if frame["observation_time"].isna().any():
        raise ValueError("METAR file contains unparseable valid timestamps")
    frame["airport"] = frame["station"].astype(str).str.strip().str.upper().str.removeprefix("K")
    keep = ["airport", "observation_time", "tmpf", "dwpf", "relh", "drct", "sknt", "vsby", "gust", "metar"]
    return frame[keep].sort_values(["airport", "observation_time"]).reset_index(drop=True)


def join_weather(flights: pd.DataFrame, weather: pd.DataFrame) -> pd.DataFrame:
    """Attach the latest report no more than three hours before each departure."""
    left = flights.copy()
    left["_row_order"] = range(len(left))
    # merge_asof requires each merge key to be globally sorted, even when `by`
    # is supplied. The row-order column restores the caller's order afterward.
    left = left.sort_values(["scheduled_departure", "origin"])
    right = weather.rename(columns={"airport": "origin", "observation_time": "weather_time"}).copy()
    right = right.rename(columns={column: f"weather_{column}" for column in right.columns if column not in {"origin", "weather_time"}})
    joined = pd.merge_asof(
        left,
        right.sort_values(["weather_time", "origin"]),
        left_on="scheduled_departure",
        right_on="weather_time",
        by="origin",
        direction="backward",
        tolerance=pd.Timedelta(hours=3),
    )
    return joined.sort_values("_row_order").drop(columns="_row_order").reset_index(drop=True)


def build_dataset(bts_path: Path, metar_path: Path, output_path: Path, settings: Settings) -> ValidationReport:
    flights, rows_read = load_flights(bts_path, settings)
    weather = load_weather(metar_path)
    joined = join_weather(flights, weather)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joined.to_csv(output_path, index=False)
    weather_matches = int(joined["weather_time"].notna().sum())
    return ValidationReport(
        rows_read,
        len(joined),
        len(weather),
        weather_matches,
        flights["flight_date"].min().date().isoformat() if len(flights) else "none",
        flights["flight_date"].max().date().isoformat() if len(flights) else "none",
        weather["observation_time"].min().isoformat() if len(weather) else "none",
        weather["observation_time"].max().isoformat() if len(weather) else "none",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the validated BTS/METAR Phase 1 dataset")
    parser.add_argument("--bts", type=Path, default=Path("data/raw/T_ONTIME_REPORTING.csv"))
    parser.add_argument("--metar", type=Path, default=Path("data/raw/METAR_DATA.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/flights_weather.csv"))
    args = parser.parse_args(argv)
    settings = Settings.from_env()
    settings.validate()
    report = build_dataset(args.bts, args.metar, args.output, settings)
    print(f"Wrote {report.flight_rows:,} corridor flights to {args.output}")
    print(f"BTS rows read: {report.bts_rows_read:,}; flight dates: {report.bts_start} to {report.bts_end}")
    print(f"METAR rows: {report.weather_rows:,}; coverage: {report.weather_start} to {report.weather_end}")
    print(f"Weather matches: {report.weather_matches:,} ({report.weather_match_rate:.1%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
