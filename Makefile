SCHEDULER = docker exec -it renewstation-airflow-scheduler

.PHONY: help env up down logs init train predict daily test

help:
	@echo "make env      create .env from .env.example"
	@echo "make up       build and start every service"
	@echo "make down     stop every service"
	@echo "make logs     follow the logs"
	@echo "make init     run the initialization DAG (weather + consumption history)"
	@echo "make train    train the consumption model"
	@echo "make predict  run the daily prediction DAG"
	@echo "make test     run the unit tests locally"

env:
	@test -f .env || (cp .env.example .env && echo "AIRFLOW_UID=$$(id -u)" >> .env && echo ".env created, edit the passwords")

up:
	mkdir -p models logs
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

init:
	$(SCHEDULER) airflow dags unpause initialization
	$(SCHEDULER) airflow dags trigger initialization

train:
	$(SCHEDULER) python -m renewstation train

predict:
	$(SCHEDULER) airflow dags unpause daily_prediction
	$(SCHEDULER) airflow dags trigger daily_prediction

daily:
	$(SCHEDULER) python -m renewstation run-daily

test:
	cd pipelines && python -m pytest -q
