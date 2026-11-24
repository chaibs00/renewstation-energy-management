"""Writes for predicted_solar_production."""

import logging

import pandas as pd

from renewstation.db.connection import copy_into_temp, cursor

log = logging.getLogger(__name__)

SOLAR_COLUMNS = [
    "timestamp",
    "temperature_c",
    "humidity_pct",
    "cloud_cover_pct",
    "solar_radiation_w_m2",
    "ghi_w_m2",
    "dni_w_m2",
    "dhi_w_m2",
    "cell_temperature_c",
    "dc_power_kw",
    "ac_power_kw",
    "predicted_production_kwh",
]


def upsert_predicted(df: pd.DataFrame) -> None:
    if df.empty:
        log.info("predicted_solar_production: nothing to write")
        return
    data = df[SOLAR_COLUMNS].copy()
    data["timestamp"] = pd.to_datetime(data["timestamp"])
    columns = ", ".join(SOLAR_COLUMNS)
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in SOLAR_COLUMNS[1:])
    with cursor() as cur:
        copy_into_temp(cur, data, "tmp_solar", "predicted_solar_production")
        cur.execute(
            f"""
            INSERT INTO predicted_solar_production ({columns})
            SELECT {columns} FROM tmp_solar
            ON CONFLICT (timestamp) DO UPDATE SET {updates}
            """
        )
        written = cur.rowcount
    log.info("predicted_solar_production: %d rows written", written)
