"""Project configuration for the initial corridor and date window."""

from dataclasses import dataclass
from datetime import date
import os


@dataclass(frozen=True)
class Settings:
    airports: tuple[str, ...] = ("ORD", "JFK", "ATL")
    start_date: date = date(2024, 6, 1)
    end_date: date = date(2024, 8, 31)
    raw_dir: str = "data/raw"
    processed_dir: str = "data/processed"

    @classmethod
    def from_env(cls) -> "Settings":
        airports = tuple(
            code.strip().upper()
            for code in os.getenv("VANTAGE_AIRPORTS", "ORD,JFK,ATL").split(",")
            if code.strip()
        )
        return cls(
            airports=airports,
            start_date=date.fromisoformat(os.getenv("VANTAGE_START_DATE", "2024-06-01")),
            end_date=date.fromisoformat(os.getenv("VANTAGE_END_DATE", "2024-08-31")),
            raw_dir=os.getenv("VANTAGE_RAW_DIR", "data/raw"),
            processed_dir=os.getenv("VANTAGE_PROCESSED_DIR", "data/processed"),
        )

    def validate(self) -> None:
        if len(self.airports) < 2:
            raise ValueError("VANTAGE_AIRPORTS must contain at least two airport codes")
        if self.start_date > self.end_date:
            raise ValueError("VANTAGE_START_DATE must be on or before VANTAGE_END_DATE")

