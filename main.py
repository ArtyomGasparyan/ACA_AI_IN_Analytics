"""Command line entry point.

Usage:
    python main.py init-db   # create database and tables
    python main.py fetch     # API -> data/raw/*.json
    python main.py load      # latest raw file -> MySQL
    python main.py run       # init-db + fetch + load
"""
import argparse
import sys

from aca_analytics.clients import APIError
from aca_analytics.config import ConfigError, Settings
from aca_analytics.services import IngestionPipeline
from aca_analytics.utils import get_logger, setup_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="API to MySQL ingestion")
    parser.add_argument("command", choices=["init-db", "fetch", "load", "run"])
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    setup_logging(settings.log_level)
    logger = get_logger("main")
    pipeline = IngestionPipeline(settings)

    try:
        if args.command == "init-db":
            pipeline.init_database()
        elif args.command == "fetch":
            pipeline.fetch()
        elif args.command == "load":
            total = pipeline.load()
            logger.info("Rows in table: %d", total)
        else:
            total = pipeline.run()
            logger.info("Pipeline finished. Rows in table: %d", total)
    except (APIError, ConnectionError, FileNotFoundError, ValueError) as exc:
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
