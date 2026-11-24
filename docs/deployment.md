# Deployment

## Huawei Cloud design

The platform was designed for Huawei Cloud during the competition:

| Huawei Cloud service | Role | Local equivalent |
|---|---|---|
| ECS (Elastic Cloud Server) | Runs Airflow, the API and the dashboard | Docker containers |
| GaussDB for PostgreSQL | Silver-layer database | `postgres:16` container |
| OBS (Object Storage Service) | Model file and backups | `./models` folder |
| ModelArts | Model training | `retrain_model` DAG |

The code only needs a PostgreSQL-compatible database, so moving to GaussDB means changing the `DB_*` variables in `.env`.

## Running locally

```bash
make env       # create .env, then edit the passwords
make up        # build and start every service
make init      # initialization DAG: schema, weather history, consumption history
make train     # train the consumption model
make predict   # daily prediction DAG
```

| Service | URL |
|---|---|
| Dashboard | http://localhost |
| API | http://localhost:8000 |
| Airflow | http://localhost:8080 |

On first start, Postgres runs the files in `pipelines/sql/`: it creates the `airflow` database and the silver tables.
To start from an empty database again: `docker compose down -v`.

## Running the pipeline without Docker

```bash
cd pipelines
pip install -r requirements-dev.txt
cp ../.env.example .env          # point DB_HOST to your database
python -m renewstation init-db
python -m renewstation ingest-weather --mode full
python -m renewstation simulate-energy --mode full
python -m renewstation init-batteries
python -m renewstation train
python -m renewstation run-daily
python -m pytest -q
```
