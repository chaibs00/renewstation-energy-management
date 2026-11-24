"""Daily at 00:00: update weather, archive yesterday, then forecast the next 7 days."""

from datetime import datetime

from airflow import DAG
from airflow.operators.empty import EmptyOperator

from _common import DEFAULT_ARGS, cli_task

with DAG(
    dag_id="daily_prediction",
    description="Weather + yesterday's data + 7-day consumption, solar and battery forecasts",
    start_date=datetime(2025, 11, 13),
    schedule="0 0 * * *",
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["renewstation", "daily", "prediction"],
) as dag:
    start = EmptyOperator(task_id="start")
    weather = cli_task("update_weather_forecast", "ingest-weather --mode forecast", 10)
    archive = cli_task("archive_yesterday", "archive-yesterday", 5)
    energy = cli_task("simulate_yesterday_energy", "simulate-energy --mode yesterday", 10)
    battery_real = cli_task("battery_real_yesterday", "battery-real", 10)
    predict_energy = cli_task("predict_energy_7d", "predict-energy", 15)
    predict_solar = cli_task("predict_solar_7d", "predict-solar", 10)
    predict_battery = cli_task("predict_battery_7d", "predict-battery", 10)
    end = EmptyOperator(task_id="end")

    start >> weather >> archive >> energy >> battery_real >> predict_energy
    predict_energy >> predict_solar >> predict_battery >> end
