-- Runs once, when the Postgres container starts with an empty volume.
-- Airflow keeps its own metadata in a separate database.
CREATE DATABASE airflow;
