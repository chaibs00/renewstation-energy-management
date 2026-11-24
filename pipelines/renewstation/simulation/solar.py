"""Physical PV model: hourly production of the 800 kWp solar station from weather."""

import logging
from datetime import datetime, timedelta

import pandas as pd

from renewstation import config

log = logging.getLogger(__name__)

CLEAR_SKY_PEAK_W_M2 = 950.0
DEFAULT_HUMIDITY_PCT = 50.0


def calculate_production(weather: pd.DataFrame) -> pd.DataFrame:
    """Compute PV output. `weather` needs: timestamp, temperature_c, cloud_cover_pct, solar_radiation_w_m2."""
    df = weather.copy()
    for col in ("temperature_c", "cloud_cover_pct", "solar_radiation_w_m2"):
        df[col] = df[col].astype(float)
    hour = pd.to_datetime(df["timestamp"]).dt.hour

    # 1) Global horizontal irradiance from the weather data
    ghi = df["solar_radiation_w_m2"].clip(lower=0)
    missing = ghi.isna() | (ghi <= 0)
    daytime = hour.between(6, 18)

    # 2) Fallback for daytime hours with no radiation value: clear-sky bell curve
    #    peaking at noon, reduced by cloud cover
    bell = (1 - (hour - 12).abs() / 6.0).clip(lower=0.0)
    ghi_fallback = CLEAR_SKY_PEAK_W_M2 * bell * (1.0 - df["cloud_cover_pct"] / 100.0)

    df["ghi_w_m2"] = ghi
    df.loc[missing & daytime, "ghi_w_m2"] = ghi_fallback[missing & daytime]
    df.loc[missing & ~daytime, "ghi_w_m2"] = 0.0

    # 3) Direct and diffuse components (simple approximations)
    df["dni_w_m2"] = df["ghi_w_m2"] * 1.1
    df["dhi_w_m2"] = df["ghi_w_m2"] * 0.2

    # 4) Cell temperature (NOCT model) and its efficiency loss
    df["cell_temperature_c"] = df["temperature_c"] + (config.NOCT_C - 20.0) * (df["ghi_w_m2"] / 800.0)
    temp_factor = 1.0 + config.TEMPERATURE_COEFFICIENT * (df["cell_temperature_c"] - 25.0)

    # 5) DC power from panel area and module efficiency
    dc = config.PV_AREA_M2 * df["ghi_w_m2"] * config.MODULE_EFFICIENCY_STC * temp_factor / 1000.0
    df["dc_power_kw"] = dc.clip(lower=0.0)

    # 6) AC power after the inverter, capped at the installed peak power
    df["ac_power_kw"] = (df["dc_power_kw"] * config.INVERTER_EFFICIENCY).clip(0.0, config.PV_PEAK_POWER_KW)

    # Hourly steps: kW over one hour = kWh
    df["predicted_production_kwh"] = df["ac_power_kw"]
    if "humidity_pct" not in df.columns:
        df["humidity_pct"] = DEFAULT_HUMIDITY_PCT
    df["humidity_pct"] = df["humidity_pct"].fillna(DEFAULT_HUMIDITY_PCT)
    return df


def hourly_solar_kwh(weather: pd.DataFrame) -> pd.DataFrame:
    """Shortcut used by the battery simulation: timestamp, solar_kwh."""
    if weather.empty:
        return pd.DataFrame(columns=["timestamp", "solar_kwh"])
    out = calculate_production(weather)[["timestamp", "predicted_production_kwh"]]
    return out.rename(columns={"predicted_production_kwh": "solar_kwh"})


def run() -> None:
    """Forecast solar production for the next 7 days and store it."""
    from renewstation.db import solar_repo, weather_repo

    start = datetime.now().replace(minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=config.FORECAST_HORIZON_HOURS)
    weather = weather_repo.read_forecast(start, end).dropna(subset=["temperature_c"])
    if weather.empty:
        raise RuntimeError("No weather forecast found. Run: python -m renewstation ingest-weather")

    solar = calculate_production(weather)
    log.info("Forecast solar production over %d hours: %.1f kWh", len(solar), solar["predicted_production_kwh"].sum())
    solar_repo.upsert_predicted(solar)
