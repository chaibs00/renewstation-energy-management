"""Reads and writes for battery_state_real and battery_state_predicted."""

import logging
from datetime import datetime

import pandas as pd

from renewstation.db.connection import copy_into_temp, cursor

log = logging.getLogger(__name__)

BATTERY_TABLES = ("battery_state_real", "battery_state_predicted")
BATTERY_COLUMNS = [
    "id",
    "timestamp",
    "battery_type",
    "battery_capacity_kwh",
    "solar_production_kwh",
    "consumption_kwh",
    "net_energy_kwh",
    "soc_start_pct",
    "soc_end_pct",
    "energy_stored_kwh",
    "battery_charge_kwh",
    "battery_discharge_kwh",
    "grid_import_kwh",
    "grid_export_kwh",
    "is_predicted",
]
_UPDATE_COLUMNS = [c for c in BATTERY_COLUMNS if c not in ("timestamp", "battery_type")]


def _check(table: str) -> None:
    if table not in BATTERY_TABLES:
        raise ValueError(f"Unknown battery table: {table}")


def upsert_states(df: pd.DataFrame, table: str) -> None:
    """Upsert hourly battery states on (timestamp, battery_type)."""
    _check(table)
    if df.empty:
        log.info("%s: nothing to write", table)
        return
    data = df.copy()
    data["timestamp"] = pd.to_datetime(data["timestamp"])
    if data["timestamp"].dt.tz is not None:
        data["timestamp"] = data["timestamp"].dt.tz_convert("UTC").dt.tz_localize(None)
    data["is_predicted"] = data["is_predicted"].astype(bool)
    data = data[BATTERY_COLUMNS]

    columns = ", ".join(BATTERY_COLUMNS)
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in _UPDATE_COLUMNS)
    with cursor() as cur:
        copy_into_temp(cur, data, "tmp_battery", table)
        cur.execute(
            f"""
            INSERT INTO {table} ({columns})
            SELECT {columns} FROM tmp_battery
            ON CONFLICT (timestamp, battery_type) DO UPDATE SET {updates}, updated_at = NOW()
            """
        )
        written = cur.rowcount
    log.info("%s: %d rows written", table, written)


def last_energy_before(timestamp: datetime, battery_type: str, default_kwh: float) -> float:
    """Energy stored in the battery at the last real state before `timestamp`.

    Falls back to `default_kwh` (a full battery) when no state exists yet.
    """
    with cursor() as cur:
        cur.execute(
            """
            SELECT energy_stored_kwh FROM battery_state_real
            WHERE battery_type = %s AND timestamp < %s
            ORDER BY timestamp DESC LIMIT 1
            """,
            (battery_type, timestamp),
        )
        row = cur.fetchone()
    if row is None or row[0] is None:
        return default_kwh
    return float(row[0])


def delete_range(table: str, start: datetime, end: datetime) -> None:
    _check(table)
    with cursor() as cur:
        cur.execute(f"DELETE FROM {table} WHERE timestamp >= %s AND timestamp < %s", (start, end))
        deleted = cur.rowcount
    log.info("%s: %d old rows removed for %s .. %s", table, deleted, start, end)
