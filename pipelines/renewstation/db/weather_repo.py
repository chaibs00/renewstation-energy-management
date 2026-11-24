"""Reads and writes for weather_archive_hourly and weather_forecast_hourly."""

import logging
from datetime import datetime

import pandas as pd

from renewstation.db.connection import copy_into_temp, cursor, read_sql

log = logging.getLogger(__name__)

WEATHER_COLUMNS = [
    "forecast_timestamp",
    "forecast_date",
    "forecast_time",
    "temperature_c",
    "humidity_pct",
    "precipitation_mm",
    "precipitation_probability_pct",
    "weather_conditions",
    "wind_speed_kmh",
    "wind_direction_deg",
    "pressure_hpa",
    "cloud_cover_pct",
    "solar_radiation_w_m2",
]
VALUE_COLUMNS = WEATHER_COLUMNS[3:]


def _upsert(df: pd.DataFrame, table: str, overwrite: bool) -> None:
    if df.empty:
        log.info("%s: nothing to write", table)
        return
    data = df[WEATHER_COLUMNS]
    columns = ", ".join(WEATHER_COLUMNS)
    if overwrite:
        updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in VALUE_COLUMNS)
        conflict = f"DO UPDATE SET {updates}"
    else:
        conflict = "DO NOTHING"
    with cursor() as cur:
        copy_into_temp(cur, data, "tmp_weather", table)
        cur.execute(
            f"""
            INSERT INTO {table} ({columns})
            SELECT {columns} FROM tmp_weather
            ON CONFLICT (forecast_timestamp) {conflict}
            """
        )
        written = cur.rowcount
    log.info("%s: %d rows written", table, written)


def upsert_archive(df: pd.DataFrame, overwrite: bool = True) -> None:
    """Write observed weather. overwrite=False keeps values already archived."""
    _upsert(df, "weather_archive_hourly", overwrite)


def upsert_forecast(df: pd.DataFrame) -> None:
    _upsert(df, "weather_forecast_hourly", overwrite=True)


def archive_coverage(start: datetime, end: datetime):
    """Return (min, max) archived timestamps inside [start, end]."""
    with cursor() as cur:
        cur.execute(
            """
            SELECT MIN(forecast_timestamp), MAX(forecast_timestamp)
            FROM weather_archive_hourly
            WHERE forecast_timestamp >= %s AND forecast_timestamp <= %s
            """,
            (start, end),
        )
        return cur.fetchone()


def _read(table: str, start: datetime, end: datetime) -> pd.DataFrame:
    df = read_sql(
        f"""
        SELECT forecast_timestamp AS timestamp, temperature_c, humidity_pct,
               cloud_cover_pct, solar_radiation_w_m2
        FROM {table}
        WHERE forecast_timestamp >= %s AND forecast_timestamp < %s
        ORDER BY forecast_timestamp
        """,
        (start, end),
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    for col in ["temperature_c", "humidity_pct", "cloud_cover_pct", "solar_radiation_w_m2"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)
    return df


def read_archive(start: datetime, end: datetime) -> pd.DataFrame:
    """Observed hourly weather in [start, end)."""
    return _read("weather_archive_hourly", start, end)


def read_forecast(start: datetime, end: datetime) -> pd.DataFrame:
    """Forecast hourly weather in [start, end)."""
    return _read("weather_forecast_hourly", start, end)
