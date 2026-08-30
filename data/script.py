import requests
from datetime import datetime, timedelta, timezone

url = "https://aviationweather.gov/api/data/metar"

start = datetime(2026, 1, 1, tzinfo=timezone.utc)
end = datetime(2026, 2, 1, tzinfo=timezone.utc)  # exclusive
all_metars = []

day = start
while day < end:
    next_day = day + timedelta(days=1)

    params = {
        "ids": "KDFW",
        "format": "json",
        "date": next_day.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hours": 24,
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    all_metars.extend(response.json())

    day = next_day

print(f"Fetched {len(all_metars)} METARs")