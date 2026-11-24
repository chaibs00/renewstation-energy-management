"""Run once: create tables, load weather history, simulate consumption, fill batteries."""

from datetime import datetime

from airflow import DAG
from airflow.operators.empty import EmptyOperator

from _common import DEFAULT_ARGS, cli_task

with DAG(
    dag_id="initialization",
    description="Schema + weather history + consumption history + batteries at 100%",
    start_date=datetime(2025, 11, 13),
    schedule=None,
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["renewstation", "init"],
) as dag:
    start = EmptyOperator(task_id="start")
    create_schema = cli_task("create_schema", "init-db", 5)
    weather_history = cli_task("weather_history", "ingest-weather --mode full", 30)
    energy_history = cli_task("energy_history", "simulate-energy --mode full", 90)
    init_batteries = cli_task("init_batteries", "init-batteries", 5)
    mark_done = cli_task("mark_initialized", "mark-initialized", 5)
    end = EmptyOperator(task_id="end")

    start >> create_schema >> weather_history >> energy_history >> init_batteries >> mark_done >> end
