"""Hour-by-hour battery simulation: charge from solar surplus, discharge on deficit.

Whatever the battery cannot absorb is exported to the grid, and whatever it
cannot supply is imported from the grid.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd

from renewstation import config

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class BatteryConfig:
    battery_type: str         # "main" or "backup"
    capacity_kwh: float
    max_charge_kw: float
    max_discharge_kw: float


def battery_configs() -> list[BatteryConfig]:
    return [BatteryConfig(name, **spec) for name, spec in config.BATTERIES.items()]


def simulate_series(df: pd.DataFrame, cfg: BatteryConfig, start_energy_kwh: float) -> pd.DataFrame:
    """Simulate one battery. `df` needs: timestamp, consumption_kwh, solar_kwh."""
    stored = max(0.0, min(float(start_energy_kwh), cfg.capacity_kwh))
    records = []

    for row in df.sort_values("timestamp").itertuples(index=False):
        consumption = float(row.consumption_kwh)
        solar = float(getattr(row, "solar_kwh", 0.0))
        net = solar - consumption  # > 0 surplus, < 0 deficit
        soc_start = 100.0 * stored / cfg.capacity_kwh if cfg.capacity_kwh > 0 else 0.0

        if net >= 0:
            charge = max(min(net, cfg.max_charge_kw, cfg.capacity_kwh - stored), 0.0)
            discharge = 0.0
            new_stored = stored + charge
            grid_export, grid_import = max(net - charge, 0.0), 0.0
        else:
            need = -net
            discharge = max(min(need, cfg.max_discharge_kw, stored), 0.0)
            charge = 0.0
            new_stored = stored - discharge
            grid_import, grid_export = max(need - discharge, 0.0), 0.0

        new_stored = max(0.0, min(new_stored, cfg.capacity_kwh))
        ts = pd.Timestamp(row.timestamp)
        records.append(
            {
                "id": f"{ts.strftime('%Y%m%d%H')}_{cfg.battery_type}",
                "timestamp": ts,
                "battery_type": cfg.battery_type,
                "battery_capacity_kwh": cfg.capacity_kwh,
                "solar_production_kwh": solar,
                "consumption_kwh": consumption,
                "net_energy_kwh": net,
                "soc_start_pct": soc_start,
                "soc_end_pct": 100.0 * new_stored / cfg.capacity_kwh if cfg.capacity_kwh > 0 else 0.0,
                "energy_stored_kwh": new_stored,
                "battery_charge_kwh": charge,
                "battery_discharge_kwh": discharge,
                "grid_import_kwh": grid_import,
                "grid_export_kwh": grid_export,
            }
        )
        stored = new_stored

    return pd.DataFrame.from_records(records)


def _simulate_all(df: pd.DataFrame, start: datetime, predicted: bool) -> pd.DataFrame:
    from renewstation.db import battery_repo

    frames = []
    for cfg in battery_configs():
        init = battery_repo.last_energy_before(start, cfg.battery_type, cfg.capacity_kwh)
        log.info("%s battery starts at %.1f / %.0f kWh", cfg.battery_type, init, cfg.capacity_kwh)
        frames.append(simulate_series(df, cfg, init))
    out = pd.concat(frames, ignore_index=True)
    out["is_predicted"] = predicted
    return out


def _merge(consumption: pd.DataFrame, solar: pd.DataFrame) -> pd.DataFrame:
    df = consumption.merge(solar, on="timestamp", how="left")
    df["solar_kwh"] = df["solar_kwh"].fillna(0.0)
    return df


def init_states() -> None:
    """Start both batteries full at the beginning of the history."""
    from renewstation.db import battery_repo

    ts = pd.Timestamp(config.BATTERY_INIT_TIMESTAMP)
    rows = [
        {
            "id": f"{ts.strftime('%Y%m%d%H')}_{cfg.battery_type}",
            "timestamp": ts,
            "battery_type": cfg.battery_type,
            "battery_capacity_kwh": cfg.capacity_kwh,
            "solar_production_kwh": 0.0,
            "consumption_kwh": 0.0,
            "net_energy_kwh": 0.0,
            "soc_start_pct": 100.0,
            "soc_end_pct": 100.0,
            "energy_stored_kwh": cfg.capacity_kwh,
            "battery_charge_kwh": 0.0,
            "battery_discharge_kwh": 0.0,
            "grid_import_kwh": 0.0,
            "grid_export_kwh": 0.0,
            "is_predicted": False,
        }
        for cfg in battery_configs()
    ]
    battery_repo.upsert_states(pd.DataFrame(rows), "battery_state_real")
    log.info("Batteries initialised at 100 percent")


def run_real_yesterday() -> None:
    """Real battery states for yesterday, from archived consumption and weather."""
    from renewstation.db import battery_repo, energy_repo, weather_repo
    from renewstation.db.archive import yesterday_bounds
    from renewstation.simulation.solar import hourly_solar_kwh

    start, end = yesterday_bounds()
    consumption = energy_repo.read_hourly_total("energy_consumption_hourly_archive", start, end)
    if consumption.empty:
        log.warning("No archived consumption for %s, nothing to simulate", start.date())
        return

    solar = hourly_solar_kwh(weather_repo.read_archive(start, end))
    states = _simulate_all(_merge(consumption, solar), start, predicted=False)
    battery_repo.delete_range("battery_state_real", start, end)
    battery_repo.upsert_states(states, "battery_state_real")


def _consumption_pattern(days: int = 30) -> pd.DataFrame:
    """Fallback: average district consumption per hour of day over the last `days` days."""
    from renewstation.db import energy_repo

    end = datetime.now()
    hourly = energy_repo.read_hourly_total("energy_consumption_hourly_archive", end - timedelta(days=days), end)
    if hourly.empty:
        raise RuntimeError("No consumption history to build a fallback pattern.")
    hourly["hour"] = hourly["timestamp"].dt.hour
    pattern = hourly.groupby("hour")["consumption_kwh"].mean()
    return pattern.reindex(range(24)).fillna(pattern.mean()).rename("consumption_kwh").reset_index()


def run_predicted() -> None:
    """Battery states for the next 7 days, from ML consumption and PV production forecasts."""
    from renewstation.db import battery_repo, energy_repo, weather_repo
    from renewstation.simulation.solar import hourly_solar_kwh

    start = datetime.now().replace(minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=config.FORECAST_HORIZON_HOURS)

    consumption = energy_repo.read_hourly_total("predicted_energy_consumption_hourly", start, end)
    if consumption.empty:
        log.warning("No consumption forecast found, using the 30-day average profile instead")
        hours = pd.DataFrame({"timestamp": pd.date_range(start, end, freq=pd.Timedelta(hours=1), inclusive="left")})
        hours["hour"] = hours["timestamp"].dt.hour
        consumption = hours.merge(_consumption_pattern(), on="hour").drop(columns="hour")

    solar = hourly_solar_kwh(weather_repo.read_forecast(start, end))
    states = _simulate_all(_merge(consumption, solar), start, predicted=True)
    battery_repo.upsert_states(states, "battery_state_predicted")
