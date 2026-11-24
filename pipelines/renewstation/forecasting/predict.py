"""Forecast hourly consumption of every building for the next 7 days."""

import logging
from datetime import datetime, timedelta

import joblib
import numpy as np
import pandas as pd

from renewstation import config
from renewstation.forecasting.features import FEATURE_COLUMNS, add_time_features
from renewstation.simulation.buildings import building_names

log = logging.getLogger(__name__)


def load_model():
    if not config.MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found at {config.MODEL_PATH}. Train it first: python -m renewstation train"
        )
    return joblib.load(config.MODEL_PATH)


def build_inputs(weather: pd.DataFrame, buildings: list[str]) -> pd.DataFrame:
    """One row per (hour, building) with the model features."""
    base = weather.rename(columns={"timestamp": "time_ts", "temperature_c": "outdoor_temp_c"})
    base = add_time_features(base, "time_ts")
    frames = [base.assign(building=name) for name in buildings]
    return pd.concat(frames, ignore_index=True)


def predict(model, inputs: pd.DataFrame) -> pd.DataFrame:
    out = inputs.copy()
    out["use_kw"] = np.clip(model.predict(out[FEATURE_COLUMNS]), 0, None)
    return out.sort_values(["building", "time_ts"]).reset_index(drop=True)


def run() -> None:
    from renewstation.db import energy_repo, weather_repo

    model = load_model()
    start = datetime.now().replace(minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=config.FORECAST_HORIZON_HOURS)

    weather = weather_repo.read_forecast(start, end).dropna(subset=["temperature_c"])
    if weather.empty:
        raise RuntimeError("No weather forecast found. Run: python -m renewstation ingest-weather")

    predictions = predict(model, build_inputs(weather, building_names()))
    log.info(
        "Predicted %d rows (%d hours x %d buildings), mean %.3f kW",
        len(predictions), len(weather), predictions["building"].nunique(), predictions["use_kw"].mean(),
    )
    energy_repo.upsert_predictions(predictions)
