"""Command-line entry point: python -m renewstation <command>

Initialization (run once, in this order):
    init-db, ingest-weather --mode full, simulate-energy --mode full,
    init-batteries, train

Daily:
    run-daily   (or each step on its own, as the Airflow DAG does)
"""

import argparse
import logging
import sys


def cmd_init_db(args):
    from renewstation import config
    from renewstation.db.connection import run_sql_file

    run_sql_file(config.SCHEMA_PATH)


def cmd_ingest_weather(args):
    from renewstation.ingestion import weather

    weather.run(args.mode)


def cmd_simulate_energy(args):
    from renewstation.simulation import energy

    energy.run_full_history() if args.mode == "full" else energy.run_yesterday()


def cmd_init_batteries(args):
    from renewstation.simulation import battery

    battery.init_states()


def cmd_mark_initialized(args):
    from renewstation.db.connection import set_metadata

    set_metadata("initialization_complete", "true")


def cmd_archive_yesterday(args):
    from renewstation.db import archive

    archive.archive_yesterday()


def cmd_battery_real(args):
    from renewstation.simulation import battery

    battery.run_real_yesterday()


def cmd_train(args):
    from renewstation.forecasting import train

    train.run()


def cmd_predict_energy(args):
    from renewstation.forecasting import predict

    predict.run()


def cmd_predict_solar(args):
    from renewstation.simulation import solar

    solar.run()


def cmd_predict_battery(args):
    from renewstation.simulation import battery

    battery.run_predicted()


DAILY_STEPS = [
    ("ingest-weather", cmd_ingest_weather),
    ("archive-yesterday", cmd_archive_yesterday),
    ("simulate-energy", cmd_simulate_energy),
    ("battery-real", cmd_battery_real),
    ("predict-energy", cmd_predict_energy),
    ("predict-solar", cmd_predict_solar),
    ("predict-battery", cmd_predict_battery),
]


def cmd_run_daily(args):
    log = logging.getLogger("renewstation")
    daily_args = argparse.Namespace(mode="forecast")
    for name, step in DAILY_STEPS:
        log.info("Daily step: %s", name)
        if name == "simulate-energy":
            step(argparse.Namespace(mode="yesterday"))
        else:
            step(daily_args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="renewstation", description="RenewStation pipelines")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db", help="Create the database tables").set_defaults(func=cmd_init_db)

    p = sub.add_parser("ingest-weather", help="Download real weather from Open-Meteo")
    p.add_argument("--mode", choices=["full", "forecast"], default="forecast")
    p.set_defaults(func=cmd_ingest_weather)

    p = sub.add_parser("simulate-energy", help="Simulate building consumption")
    p.add_argument("--mode", choices=["full", "yesterday"], default="yesterday")
    p.set_defaults(func=cmd_simulate_energy)

    commands = [
        ("init-batteries", "Start both batteries full", cmd_init_batteries),
        ("mark-initialized", "Flag the initialization as done", cmd_mark_initialized),
        ("archive-yesterday", "Archive yesterday's weather and consumption", cmd_archive_yesterday),
        ("battery-real", "Simulate yesterday's real battery states", cmd_battery_real),
        ("train", "Train the consumption model", cmd_train),
        ("predict-energy", "Forecast consumption for 7 days", cmd_predict_energy),
        ("predict-solar", "Forecast solar production for 7 days", cmd_predict_solar),
        ("predict-battery", "Forecast battery states for 7 days", cmd_predict_battery),
        ("run-daily", "Run every daily step in order", cmd_run_daily),
    ]
    for name, help_text, func in commands:
        sub.add_parser(name, help=help_text).set_defaults(func=func)
    return parser


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = build_parser().parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
