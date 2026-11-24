"""Shared PostgreSQL connection and bulk-load helpers."""

import logging
from contextlib import contextmanager
from io import StringIO
from pathlib import Path

import pandas as pd

from renewstation import config

log = logging.getLogger(__name__)


def connect():
    """Open a new connection to the silver database."""
    import psycopg2

    return psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        sslmode=config.DB_SSLMODE,
    )


@contextmanager
def cursor():
    """Yield a cursor inside a transaction: commit on success, rollback on error."""
    conn = connect()
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def read_sql(query: str, params=None) -> pd.DataFrame:
    """Run a SELECT and return the result as a DataFrame."""
    with cursor() as cur:
        cur.execute(query, params)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
    return pd.DataFrame(rows, columns=columns)


def copy_into_temp(cur, df: pd.DataFrame, temp_table: str, like_table: str) -> None:
    """Create a temp table shaped like `like_table` and COPY the DataFrame into it.

    The DataFrame columns must be in the same order as the target table.
    """
    cur.execute(
        f"CREATE TEMP TABLE {temp_table} (LIKE {like_table} INCLUDING DEFAULTS) ON COMMIT DROP"
    )
    buffer = StringIO()
    df.to_csv(buffer, index=False, header=False, na_rep="NULL")
    buffer.seek(0)
    columns = ", ".join(df.columns)
    cur.copy_expert(
        f"COPY {temp_table} ({columns}) FROM STDIN WITH (FORMAT csv, NULL 'NULL')", buffer
    )


def run_sql_file(path: Path) -> None:
    """Execute a .sql file (used to create the schema)."""
    sql = Path(path).read_text(encoding="utf-8")
    with cursor() as cur:
        cur.execute(sql)
    log.info("Executed %s", path)


def set_metadata(key: str, value: str) -> None:
    with cursor() as cur:
        cur.execute(
            """
            INSERT INTO pipeline_metadata (key, value) VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
            """,
            (key, value),
        )
