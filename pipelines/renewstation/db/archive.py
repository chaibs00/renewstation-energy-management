"""Daily archiving: move yesterday's weather and consumption into the archive tables."""

import logging
from datetime import datetime, timedelta

from renewstation.db.connection import cursor
from renewstation.db.energy_repo import ENERGY_COLUMNS
from renewstation.db.weather_repo import VALUE_COLUMNS

log = logging.getLogger(__name__)


def yesterday_bounds(now: datetime | None = None) -> tuple[datetime, datetime]:
    """[start, end) of yesterday, as naive datetimes."""
    today = (now or datetime.now()).date()
    start = datetime.combine(today - timedelta(days=1), datetime.min.time())
    return start, start + timedelta(days=1)


def archive_weather(start: datetime, end: datetime) -> None:
    """Copy forecast weather for [start, end) into the archive."""
    values = ", ".join(VALUE_COLUMNS)
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in VALUE_COLUMNS)
    with cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO weather_archive_hourly
                (forecast_timestamp, forecast_date, forecast_time, {values})
            SELECT forecast_timestamp, forecast_timestamp::date, forecast_timestamp::time, {values}
            FROM weather_forecast_hourly
            WHERE forecast_timestamp >= %s AND forecast_timestamp < %s
            ON CONFLICT (forecast_timestamp) DO UPDATE SET {updates}
            """,
            (start, end),
        )
        log.info("Weather archived: %d rows (%s .. %s)", cur.rowcount, start, end)


def archive_energy(start: datetime, end: datetime) -> None:
    """Copy live consumption for [start, end) into the archive."""
    columns = ", ".join(ENERGY_COLUMNS)
    updates = ", ".join(
        f"{c} = EXCLUDED.{c}" for c in ENERGY_COLUMNS if c not in ("time_ts", "building")
    )
    with cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO energy_consumption_hourly_archive ({columns})
            SELECT {columns} FROM energy_consumption_hourly_live
            WHERE time_ts >= %s AND time_ts < %s
            ON CONFLICT (time_ts, building) DO UPDATE SET {updates}
            """,
            (start, end),
        )
        log.info("Consumption archived: %d rows (%s .. %s)", cur.rowcount, start, end)


def archive_yesterday() -> None:
    start, end = yesterday_bounds()
    archive_weather(start, end)
    archive_energy(start, end)
