"""Shared helpers for the RenewStation DAGs."""

from datetime import timedelta

from airflow.operators.bash import BashOperator

DEFAULT_ARGS = {
    "owner": "renewstation",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}


def cli_task(task_id: str, command: str, timeout_minutes: int = 15) -> BashOperator:
    """A task that runs one `python -m renewstation <command>` step."""
    return BashOperator(
        task_id=task_id,
        bash_command=f"cd /opt/airflow && python -m renewstation {command}",
        execution_timeout=timedelta(minutes=timeout_minutes),
    )
