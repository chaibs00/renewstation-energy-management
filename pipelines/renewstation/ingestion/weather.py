"""Real hourly weather for Casablanca from the Open-Meteo API.

- History (archive API) since 2024-01-01 -> weather_archive_hourly
- Forecast (forecast API), including the last few days the archive API
  does not have yet:
    past hours   -> weather_archive_hourly (never overwrites archive values)
    future hours -> weather_forecast_hourly
"""

import logging
from datetime import datetime, timedelta

import pandas as pd
import requests

from renewstation import config

log = logging.getLogger(__name__)

HOURLY_VARIABLES = [
    "temperature_2m",
    "relativehumidity_2m",
    "precipitation",
    "precipitation_probability",
    "weathercode",
    "windspeed_10m",
    "winddirection_10m",
    "pressure_msl",
    "cloudcover",
    "shortwave_radiation",
]

# Open-Meteo name -> database column
COLUMN_MAP = {
    "temperature_2m": "temperature_c",
    "relativehumidity_2m": "humidity_pct",
    "precipitation": "precipitation_mm",
    "precipitation_probability": "precipitation_probability_pct",
    "windspeed_10m": "wind_speed_kmh",
    "winddirection_10m": "wind_direction_deg",
    "pressure_msl": "pressure_hpa",
    "cloudcover": "cloud_cover_pct",
    "shortwave_radiation": "solar_radiation_w_m2",
}

WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Depositing rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Light rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Light snow", 73: "Moderate snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Light rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    85: "Light snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm with light hail", 99: "Thunderstorm with heavy hail",
}


def describe_weather(code) -> str:
    if code is None or pd.isna(code):
        return None
    return WMO_CODES.get(int(code), f"Code {int(code)}")


def to_dataframe(hourly: dict) -> pd.DataFrame:
    """Convert the `hourly` block of an Open-Meteo response to database columns."""
    df = pd.DataFrame(hourly)
    df["forecast_timestamp"] = pd.to_datetime(df["time"])
    df = df.rename(columns=COLUMN_MAP)
    if "precipitation_probability_pct" not in df.columns:  # not served by the archive API
        df["precipitation_probability_pct"] = 0
    df["precipitation_probability_pct"] = df["precipitation_probability_pct"].fillna(0)
    df["weather_conditions"] = df["weathercode"].map(describe_weather)
    df["forecast_date"] = df["forecast_timestamp"].dt.date
    df["forecast_time"] = df["forecast_timestamp"].dt.time
    # Recent hours can come back empty from the archive API
    return df.dropna(subset=["temperature_c"]).reset_index(drop=True)


def _get(url: str, params: dict, variables: list[str] = HOURLY_VARIABLES) -> pd.DataFrame:
    base = {
        "latitude": config.LATITUDE,
        "longitude": config.LONGITUDE,
        "hourly": ",".join(variables),
        "timezone": config.TIMEZONE,
    }
    response = requests.get(url, params={**base, **params}, timeout=config.HTTP_TIMEOUT_S)
    response.raise_for_status()
    return to_dataframe(response.json()["hourly"])


def fetch_history(start: datetime, end: datetime) -> pd.DataFrame:
    # The archive API has no precipitation probability (it is an observed value)
    variables = [v for v in HOURLY_VARIABLES if v != "precipitation_probability"]
    df = _get(
        config.OPEN_METEO_ARCHIVE_URL,
        {"start_date": start.date().isoformat(), "end_date": end.date().isoformat()},
        variables,
    )
    return df[(df["forecast_timestamp"] >= start) & (df["forecast_timestamp"] <= end)]


def fetch_forecast(past_days: int = config.FORECAST_PAST_DAYS) -> pd.DataFrame:
    return _get(
        config.OPEN_METEO_FORECAST_URL,
        {"forecast_days": config.FORECAST_DAYS, "past_days": past_days},
    )


def backfill_history() -> None:
    """Make sure the archive covers HISTORY_START -> today, filling gaps at both ends."""
    from renewstation.db import weather_repo

    start = config.HISTORY_START
    end = datetime.combine(datetime.now().date(), datetime.min.time()).replace(hour=23)
    existing_min, existing_max = weather_repo.archive_coverage(start, end)
    log.info("Archived weather covers %s .. %s", existing_min, existing_max)

    ranges = []
    if existing_min is None:
        ranges.append((start, end))
    else:
        if existing_min > start:
            ranges.append((start, existing_min - timedelta(hours=1)))
        if existing_max < end:
            ranges.append((existing_max + timedelta(hours=1), end))

    for gap_start, gap_end in ranges:
        log.info("Downloading weather history %s .. %s", gap_start, gap_end)
        weather_repo.upsert_archive(fetch_history(gap_start, gap_end))


def update_forecast(past_days: int = config.FORECAST_PAST_DAYS) -> None:
    from renewstation.db import weather_repo

    df = fetch_forecast(past_days)
    now = datetime.now()
    past, future = df[df["forecast_timestamp"] < now], df[df["forecast_timestamp"] >= now]
    weather_repo.upsert_archive(past, overwrite=False)
    weather_repo.upsert_forecast(future)
    log.info("Forecast: %d future hours, %d recent past hours", len(future), len(past))


def run(mode: str = "forecast") -> None:
    """full = history + forecast (initialization), forecast = daily update."""
    if mode == "full":
        backfill_history()
        update_forecast(config.FORECAST_PAST_DAYS)
    elif mode == "forecast":
        update_forecast(past_days=2)
    else:
        raise ValueError(f"Unknown mode: {mode}")
