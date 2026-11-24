"""Train the consumption model (RandomForest) on the archived consumption data.

Same setup as the competition version: random 80/20 split stratified by building.
"""

import logging
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from renewstation import config
from renewstation.forecasting.features import CATEGORICAL_FEATURES, FEATURE_COLUMNS, NUMERIC_FEATURES

log = logging.getLogger(__name__)

TARGET = "use_kw"
MODEL_PARAMS = {
    "n_estimators": 500,
    "max_depth": 28,
    "min_samples_split": 4,
    "min_samples_leaf": 1,
    "random_state": 42,
    "n_jobs": -1,
}


def build_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer(
        [
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(drop="first", handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ]
    )
    return Pipeline([("preprocessor", preprocessor), ("model", RandomForestRegressor(**MODEL_PARAMS))])


def evaluate(y_true, y_pred) -> dict:
    mae = mean_absolute_error(y_true, y_pred)
    return {
        "mae_kw": mae,
        "rmse_kw": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": r2_score(y_true, y_pred),
        "within_mae_pct": float(np.mean(np.abs(np.asarray(y_true) - y_pred) <= mae) * 100),
    }


def train(df: pd.DataFrame) -> tuple[Pipeline, dict]:
    """Fit the pipeline on a DataFrame holding FEATURE_COLUMNS and the target."""
    X, y = df[FEATURE_COLUMNS], df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=X["building"]
    )
    pipeline = build_pipeline()
    log.info("Training RandomForest on %d rows", len(X_train))
    pipeline.fit(X_train, y_train)
    y_pred = np.clip(pipeline.predict(X_test), 0, None)
    return pipeline, evaluate(y_test, y_pred)


def save_model(pipeline: Pipeline) -> None:
    """Write the model atomically, so a running prediction never reads half a file."""
    config.MODEL_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = config.MODEL_PATH.with_suffix(".tmp")
    joblib.dump(pipeline, tmp_path)
    os.replace(tmp_path, config.MODEL_PATH)
    log.info("Model saved to %s", config.MODEL_PATH)


def run() -> dict:
    from renewstation.db import energy_repo

    df = energy_repo.read_training_data()
    if df.empty:
        raise RuntimeError("No consumption history found. Run the initialization first.")
    log.info("Loaded %d historical rows", len(df))

    pipeline, metrics = train(df)
    log.info(
        "MAE %.3f kW | RMSE %.3f kW | R2 %.4f | %.1f%% of predictions within +/- MAE",
        metrics["mae_kw"], metrics["rmse_kw"], metrics["r2"], metrics["within_mae_pct"],
    )
    save_model(pipeline)
    return metrics
