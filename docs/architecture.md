# Architecture

```
Open-Meteo API ──> Airflow pipelines ──> PostgreSQL (silver) ──> Node.js API ──> React dashboard
                   (pipelines/)           (10 tables)             (api/)          (dashboard/)
```

| Component | Folder | Role |
|---|---|---|
| Airflow | `pipelines/dags/` | Schedules the steps; each task runs `python -m renewstation <command>` |
| Python package | `pipelines/renewstation/` | Ingestion, simulation, ML training and forecasting |
| PostgreSQL | `pipelines/sql/` | Silver layer: history, live data and 7-day forecasts |
| Node.js API | `api/` | Read-only REST API (`/api/solar/...`) used by the dashboard |
| React dashboard | `dashboard/` | Energy, solar, battery and weather pages |

## Python package

| Module | What it does |
|---|---|
| `config.py` | Environment variables, location, PV and battery constants |
| `db/` | Connection helpers and one repository per table group |
| `ingestion/weather.py` | Real weather history and forecast from Open-Meteo |
| `simulation/buildings.py` | The 17 buildings, equipment ranges and house profiles |
| `simulation/energy.py` | Synthetic hourly consumption driven by real weather |
| `simulation/solar.py` | Physical PV model (800 kWp) |
| `simulation/battery.py` | Hour-by-hour battery charge / discharge and grid exchange |
| `forecasting/features.py` | Calendar features shared by simulation, training and prediction |
| `forecasting/train.py` | RandomForest training, model saved to `models/energy_predictor.pkl` |
| `forecasting/predict.py` | 7-day consumption forecast for every building |
| `__main__.py` | Command-line entry point |

## Commands

| Command | Used by |
|---|---|
| `init-db` | `initialization` DAG |
| `ingest-weather --mode full` | `initialization` DAG |
| `simulate-energy --mode full` | `initialization` DAG |
| `init-batteries`, `mark-initialized` | `initialization` DAG |
| `ingest-weather --mode forecast` | `daily_prediction` DAG |
| `archive-yesterday` | `daily_prediction` DAG |
| `simulate-energy --mode yesterday` | `daily_prediction` DAG |
| `battery-real` | `daily_prediction` DAG |
| `predict-energy`, `predict-solar`, `predict-battery` | `daily_prediction` DAG |
| `train` | `retrain_model` DAG |
| `run-daily` | Manual: every daily step in order |
