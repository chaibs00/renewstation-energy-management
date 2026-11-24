"""Central configuration: environment variables, paths and physical constants."""

import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "silver")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_SSLMODE = os.getenv("DB_SSLMODE", "disable")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PACKAGE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = Path(os.getenv("SCHEMA_PATH", PACKAGE_DIR.parent / "sql" / "schema.sql"))
MODEL_DIR = Path(os.getenv("MODEL_DIR", "models"))
MODEL_PATH = MODEL_DIR / "energy_predictor.pkl"

# ---------------------------------------------------------------------------
# Location and weather (Open-Meteo)
# ---------------------------------------------------------------------------
LATITUDE = 33.5731
LONGITUDE = -7.5898
TIMEZONE = "Africa/Casablanca"

HISTORY_START = datetime(2024, 1, 1)
FORECAST_DAYS = 7
FORECAST_PAST_DAYS = 7  # recent days the archive API may not have yet

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
HTTP_TIMEOUT_S = 60

# ---------------------------------------------------------------------------
# Solar station (PV)
# ---------------------------------------------------------------------------
PV_PEAK_POWER_KW = 800.0        # 1,455 panels x 550 W
PV_AREA_M2 = 3754.0
MODULE_EFFICIENCY_STC = 0.225
INVERTER_EFFICIENCY = 0.97
TEMPERATURE_COEFFICIENT = -0.004  # -0.4 % per degree C
NOCT_C = 45.0                     # nominal operating cell temperature

# ---------------------------------------------------------------------------
# Batteries
# ---------------------------------------------------------------------------
BATTERIES = {
    "main": {"capacity_kwh": 3000.0, "max_charge_kw": 600.0, "max_discharge_kw": 600.0},
    "backup": {"capacity_kwh": 1000.0, "max_charge_kw": 200.0, "max_discharge_kw": 200.0},
}
BATTERY_INIT_TIMESTAMP = HISTORY_START

# ---------------------------------------------------------------------------
# Forecasting
# ---------------------------------------------------------------------------
FORECAST_HORIZON_HOURS = 168
