"""Synthetic hourly consumption for the 17 buildings, driven by real weather.

Each building gets an occupancy curve (people present), from which lighting,
HVAC and special-equipment loads are derived. HVAC reacts to the real outdoor
temperature: heating below 15 C, cooling above 28 C.
"""

import logging
import random
from datetime import datetime

import numpy as np
import pandas as pd

from renewstation import config
from renewstation.forecasting.features import add_time_features
from renewstation.simulation.buildings import (
    HVAC_RANGE,
    LIGHTING_RANGE,
    OCCUPANCY_RANGE,
    SPECIAL_EQUIPMENT_RANGE,
    Building,
    buildings,
    house_profile,
)

log = logging.getLogger(__name__)

COMFORT_TEMP_C = 21.0
BASE_SEED = 42


def _on_vacation(building_type: str, profile, month: int) -> bool:
    return building_type == "House" and profile is not None and month in profile["vacation_months"]


def occupancy_series(df, building_type, size_factor, profile=None) -> list[int]:
    """Number of people present each hour, smoothed and with small noise."""
    base_min, base_max = OCCUPANCY_RANGE[building_type]
    base_min, base_max = int(base_min * size_factor), int(base_max * size_factor)
    prev, result = 0.5, []

    for row in df.itertuples(index=False):
        hour, weekend, holiday = row.hour_of_day, row.is_weekend, row.is_holiday

        if building_type == "House" and profile:
            if row.month_num in profile["vacation_months"]:
                target = 0.05
            elif hour in (6, 7, 8):
                target = 0.85
            elif 9 <= hour <= 16:
                if profile.get("high_daytime_usage", False):
                    target = 0.75
                else:
                    target = 0.20 if not weekend else 0.70
            elif 17 <= hour <= 22:
                target = 0.95
            else:
                target = 1.0
        elif building_type == "Hospital":
            if hour in (7, 15, 23):
                target = 0.90
            elif hour <= 5:
                target = 0.55
            elif hour in (9, 10, 11, 14, 16):
                target = 0.88
            else:
                target = 0.75
        elif building_type == "School":
            if row.is_school_vacation:
                target = 0.05
            elif weekend or holiday:
                target = 0.02
            elif hour in (7, 8):
                target = 0.55
            elif 9 <= hour <= 14:
                target = 0.95
            elif hour == 15:
                target = 0.45
            elif hour in (16, 17):
                target = 0.25
            else:
                target = 0.03
        elif building_type == "Office":
            if weekend:
                target = 0.05
            elif holiday:
                target = 0.02
            elif row.day_of_week == 4:  # Friday: people leave early
                target = 0.82 if hour < 16 else 0.25
            elif hour in (6, 7):
                target = 0.18
            elif hour in (8, 9):
                target = 0.70
            elif hour in (10, 11, 14, 15, 16):
                target = 0.88
            elif hour in (12, 13):
                target = 0.55
            elif hour in (17, 18):
                target = 0.35
            else:
                target = 0.05
        elif building_type == "Industry":
            if weekend:
                target = 0.60
            elif hour in (6, 7, 14, 15, 22, 23):
                target = 0.92
            elif 8 <= hour <= 13:
                target = 0.90
            elif 16 <= hour <= 21:
                target = 0.78
            else:
                target = 0.65
        else:
            target = 0.5

        level = 0.7 * prev + 0.3 * target
        prev = level
        level = np.clip(level + np.random.normal(0, 0.04), 0, 1)
        result.append(max(0, int(base_min + (base_max - base_min) * level)))
    return result


def lighting_series(df, building_type, efficiency, occupancy, profile=None) -> list[float]:
    base_min, base_max = LIGHTING_RANGE[building_type]
    base_max *= efficiency
    max_occupancy = OCCUPANCY_RANGE[building_type][1]
    result = []

    for i, row in enumerate(df.itertuples(index=False)):
        natural_light = row.solar_radiation_w_m2 / 950
        occ_factor = occupancy[i] / max_occupancy if max_occupancy > 0 else 0

        if _on_vacation(building_type, profile, row.month_num):
            need = 0.02
        elif building_type == "School" and row.is_school_vacation:
            need = 0.08
        elif building_type == "Hospital":
            if row.hour_of_day <= 5:
                need = 0.45 * occ_factor
            else:
                need = (1 - float(natural_light) * 0.6) * occ_factor
        elif occ_factor < 0.1:
            need = 0.08 * occ_factor
        else:
            need = (1 - natural_light * 0.75) * occ_factor

        if building_type in ("Office", "School") and occ_factor < 0.3:
            need *= 0.6

        light = base_min + (base_max - base_min) * np.clip(need, 0, 1)
        result.append(max(0, light + np.random.normal(0, 0.025 * light)))
    return result


def hvac_series(df, building_type, insulation, occupancy, profile=None) -> list[float]:
    base_min, base_max = HVAC_RANGE[building_type]
    max_occupancy = OCCUPANCY_RANGE[building_type][1]
    indoor_temp = COMFORT_TEMP_C
    result = []

    for i, row in enumerate(df.itertuples(index=False)):
        outdoor_temp = row.outdoor_temp_c
        occ_factor = occupancy[i] / max_occupancy if max_occupancy > 0 else 0

        # Indoor temperature follows outdoors slowly, plus solar and occupant gains
        indoor_temp = 0.88 * indoor_temp + 0.12 * outdoor_temp
        indoor_temp += row.solar_radiation_w_m2 / 48000
        indoor_temp += occ_factor * 1.3

        if _on_vacation(building_type, profile, row.month_num):
            need = 0.05
        elif outdoor_temp < 15:  # heating
            heating = max(COMFORT_TEMP_C - indoor_temp, 0) / (18 * insulation)
            if building_type == "House" and profile:
                factor = {"gas": 0.30, "heatpump": 0.65}.get(profile["heating_type"], 1.2)
                need = heating * factor
            else:
                need = heating * occ_factor
        elif outdoor_temp > 28:  # cooling
            cooling = max(indoor_temp - COMFORT_TEMP_C, 0) / (16 * insulation)
            if building_type == "House" and profile:
                need = cooling * (1.5 if profile["has_ac"] else 0.25)
            else:
                need = cooling * occ_factor
        else:  # mild weather
            diff = abs(indoor_temp - COMFORT_TEMP_C)
            if building_type == "School" and row.is_school_vacation:
                need = 0.10
            elif building_type == "Hospital":
                need = (diff / (17 * insulation)) * 0.85
            else:
                need = (diff / (20 * insulation)) * occ_factor * 0.6

        time_factor = 1.08 if row.is_peak_hour and occ_factor > 0.5 else 0.95
        load = base_min + (base_max - base_min) * np.clip(need * time_factor, 0, 1.6)
        result.append(max(0, load + np.random.normal(0, 0.06 * load)))
    return result


def equipment_series(df, building_type, modernity, occupancy, profile=None) -> list[float]:
    base_min, base_max = SPECIAL_EQUIPMENT_RANGE[building_type]
    if building_type == "House" and profile:
        if profile.get("high_equipment", False):
            base_max *= 1.4
        elif profile.get("low_equipment", False):
            base_max *= 0.6
    base_max *= modernity
    max_occupancy = OCCUPANCY_RANGE[building_type][1]
    result = []

    for i, row in enumerate(df.itertuples(index=False)):
        occ_factor = occupancy[i] / max_occupancy if max_occupancy > 0 else 0

        if _on_vacation(building_type, profile, row.month_num):
            base = 0.05  # fridge only
        elif building_type == "School" and row.is_school_vacation:
            base = 0.08
        else:
            base = 0.35

        if building_type == "Hospital":
            variable = 0.90 if 6 <= row.hour_of_day <= 20 else 0.60
        elif building_type == "Industry":
            variable = 0.85 if occ_factor > 0.3 else 0.50
        elif building_type == "School" and row.is_school_vacation:
            variable = 0.10
        else:
            variable = occ_factor

        equip = base_min + (base_max - base_min) * (base + variable * 0.65)
        result.append(max(0, equip + np.random.normal(0, 0.035 * equip)))
    return result


def simulate_building(weather: pd.DataFrame, building: Building, seed_offset: int = 0) -> pd.DataFrame:
    """Hourly consumption of one building. `weather` must hold the model weather columns."""
    seed = BASE_SEED + building.number + seed_offset
    np.random.seed(seed)
    random.seed(seed)

    if building.type == "Industry":
        size_factor = np.random.uniform(1.1, 1.3) if building.number == 1 else np.random.uniform(0.5, 0.9)
    else:
        size_factor = np.random.uniform(0.7, 1.3)
    efficiency = np.random.uniform(0.75, 1.25)
    insulation = np.random.uniform(0.7, 1.3)
    modernity = np.random.uniform(0.85, 1.15)

    profile = None
    if building.type == "House":
        profile = house_profile(building.number)
        np.random.seed(1000 + building.number + seed_offset)

    df = add_time_features(weather, "time_ts").reset_index(drop=True)
    df["is_school_vacation"] = df["month_num"].isin([6, 7, 8]).astype(int)

    occupancy = occupancy_series(df, building.type, size_factor, profile)
    df["lighting_kw"] = lighting_series(df, building.type, efficiency, occupancy, profile)
    df["hvac_kw"] = hvac_series(df, building.type, insulation, occupancy, profile)
    df["special_equipment_kw"] = equipment_series(df, building.type, modernity, occupancy, profile)

    total = df["lighting_kw"] + df["hvac_kw"] + df["special_equipment_kw"]
    df["use_kw"] = (total * (1 + np.random.normal(0, 0.012, len(df)))).clip(lower=0)
    df["building"] = building.name
    return df.drop(columns=["is_school_vacation"])


def simulate_district(weather: pd.DataFrame, seed_offset: int = 0) -> pd.DataFrame:
    """Consumption of all 17 buildings for the hours in `weather`."""
    frames = []
    for building in buildings():
        df = simulate_building(weather, building, seed_offset)
        log.info("%-10s mean load %.2f kW", building.name, df["use_kw"].mean())
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def prepare_weather(raw: pd.DataFrame) -> pd.DataFrame:
    """Rename weather columns from the DB to the simulator/model names."""
    weather = raw.rename(columns={"timestamp": "time_ts", "temperature_c": "outdoor_temp_c"})
    weather = weather.dropna(subset=["outdoor_temp_c", "solar_radiation_w_m2"])
    return weather[["time_ts", "outdoor_temp_c", "humidity_pct", "cloud_cover_pct", "solar_radiation_w_m2"]]


def run(start: datetime, end: datetime, seed_offset: int = 0) -> None:
    """Simulate consumption for [start, end) from archived weather and store it."""
    from renewstation.db import energy_repo, weather_repo

    weather = prepare_weather(weather_repo.read_archive(start, end))
    if weather.empty:
        raise RuntimeError(f"No archived weather between {start} and {end}.")
    log.info("Simulating %d hours x 17 buildings (%s .. %s)", len(weather), start, end)
    energy_repo.upsert_consumption(simulate_district(weather, seed_offset))


def run_full_history() -> None:
    run(config.HISTORY_START, datetime.now())


def run_yesterday() -> None:
    from renewstation.db.archive import yesterday_bounds

    start, end = yesterday_bounds()
    run(start, end, seed_offset=start.toordinal())
