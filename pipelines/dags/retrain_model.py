"""Daily at 00:00: retrain the consumption model on the latest data.

The new model overwrites models/energy_predictor.pkl in one atomic step,
so no cleanup task is needed.
"""

from datetime import datetime

from airflow import DAG
from airflow.operators.empty import EmptyOperator

from _common import DEFAULT_ARGS, cli_task

with DAG(
    dag_id="retrain_model",
    description="Retrain the energy consumption model (RandomForest)",
    start_date=datetime(2025, 11, 13),
    schedule="0 0 * * *",
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["renewstation", "mlops", "retrain"],
) as dag:
    start = EmptyOperator(task_id="start")
    retrain = cli_task("retrain_energy_model", "train", 45)
    end = EmptyOperator(task_id="end")

    start >> retrain >> end
