"""Reads and writes for the energy consumption tables (archive, live, predicted)."""

import logging
from datetime import datetime

import pandas as pd

from renewstation.db.connection import copy_into_temp, cursor, read_sql
from renewstation.forecasting.features import FEATURE_COLUMNS

log = logging.getLogger(__name__)

ENERGY_COLUMNS = [
    "id",
    "time_ts",
    "building",
    "winter_flag",
    "spring_flag",
    "summer_flag",
    "fall_flag",
    "outdoor_temp_c",
    "humidity_pct",
    "cloud_cover_pct",
    "solar_radiation_w_m2",
    "hour_of_day",
    "day_of_week",
    "month_num",
    "day_of_year",
    "is_weekend",
    "is_holiday",
    "is_peak_hour",
    "lighting_kw",
    "hvac_kw",
    "special_equipment_kw",
    "use_kw",
]
_UPDATE_COLUMNS = [c for c in ENERGY_COLUMNS if c not in ("time_ts", "building")]
LIVE_WINDOW_HOURS = 48


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data["time_ts"] = pd.to_datetime(data["time_ts"])
    data["id"] = data["time_ts"].dt.strftime("%Y%m%d%H") + "_" + data["building"].astype(str)
    for col in ("lighting_kw", "hvac_kw", "special_equipment_kw"):
        if col not in data.columns:
            data[col] = None
    return data[ENERGY_COLUMNS]


def _insert(cur, table: str, where: str = "") -> int:
    columns = ", ".join(ENERGY_COLUMNS)
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in _UPDATE_COLUMNS)
    cur.execute(
        f"""
        INSERT INTO {table} ({columns})
        SELECT {columns} FROM tmp_energy {where}
        ON CONFLICT (time_ts, building) DO UPDATE SET {updates}
        """
    )
    return cur.rowcount


def upsert_consumption(df: pd.DataFrame) -> None:
    """Write simulated consumption to the archive, and the last 48 h to the live table."""
    data = _prepare(df)
    with cursor() as cur:
        copy_into_temp(cur, data, "tmp_energy", "energy_consumption_hourly_archive")
        archived = _insert(cur, "energy_consumption_hourly_archive")
        live = _insert(
            cur,
            "energy_consumption_hourly_live",
            f"WHERE time_ts >= NOW() - INTERVAL '{LIVE_WINDOW_HOURS} hours'",
        )
    log.info("Consumption: %d rows archived, %d rows in live table", archived, live)


def upsert_predictions(df: pd.DataFrame) -> None:
    """Write ML consumption forecasts to predicted_energy_consumption_hourly."""
    data = _prepare(df)
    with cursor() as cur:
        copy_into_temp(cur, data, "tmp_energy", "predicted_energy_consumption_hourly")
        written = _insert(cur, "predicted_energy_consumption_hourly")
    log.info("Predicted consumption: %d rows written", written)


def read_training_data() -> pd.DataFrame:
    """All archived consumption rows with the model features and target."""
    df = read_sql(
        f"""
        SELECT time_ts, {", ".join(FEATURE_COLUMNS)}, use_kw
        FROM energy_consumption_hourly_archive
        WHERE use_kw IS NOT NULL AND use_kw > 0
        """
    )
    numeric = [c for c in FEATURE_COLUMNS if c != "building"] + ["use_kw"]
    df[numeric] = df[numeric].apply(pd.to_numeric, errors="coerce").astype(float)
    return df


def read_hourly_total(table: str, start: datetime, end: datetime) -> pd.DataFrame:
    """District consumption: sum of all buildings per hour in [start, end)."""
    df = read_sql(
        f"""
        SELECT time_ts AS timestamp, SUM(use_kw) AS consumption_kwh
        FROM {table}
        WHERE time_ts >= %s AND time_ts < %s
        GROUP BY time_ts
        ORDER BY time_ts
        """,
        (start, end),
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["consumption_kwh"] = pd.to_numeric(df["consumption_kwh"]).astype(float)
    return df
