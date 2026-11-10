"""Orchestrates: API -> raw JSON file -> MySQL."""
from __future__ import annotations

from pathlib import Path

from aca_analytics.clients import APIClient
from aca_analytics.config import Settings
from aca_analytics.database import API_RECORDS_TABLE, MySQLConnection, Repository, SchemaManager
from aca_analytics.models import Record
from aca_analytics.utils.file_storage import RawDataStorage
from aca_analytics.utils.logger import get_logger

logger = get_logger(__name__)


class IngestionPipeline:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.storage = RawDataStorage(settings.raw_data_dir)

    def init_database(self) -> None:
        """Create the remote database (if allowed) and all tables."""
        db = self.settings.database
        with MySQLConnection(db, use_database=False) as server:
            SchemaManager.create_database(server, db.name)
        with MySQLConnection(db) as conn:
            SchemaManager(conn).create_tables()

    def fetch(self) -> Path:
        """Download data from the API and store it in data/raw."""
        with APIClient(self.settings.api) as client:
            records = client.fetch_records()
        logger.info("Fetched %d records", len(records))
        return self.storage.save(records)

    def load(self, raw_file: Path | None = None) -> int:
        """Read a raw JSON file (latest by default) and upsert it into MySQL."""
        raw_file = raw_file or self.storage.latest()
        items = self.storage.load(raw_file)
        records = [Record.from_api(i, self.settings.api.id_field) for i in items]

        with MySQLConnection(self.settings.database) as conn:
            SchemaManager(conn).create_tables()
            repo = Repository(conn, API_RECORDS_TABLE.name)
            repo.upsert_many([r.to_row() for r in records])
            return repo.count()

    def run(self) -> int:
        """Full flow: init schema, fetch, load. Returns total rows in the table."""
        self.init_database()
        raw_file = self.fetch()
        return self.load(raw_file)
