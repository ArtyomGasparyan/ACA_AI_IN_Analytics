"""Database / table schema definitions and creation."""
from __future__ import annotations

import re
from dataclasses import dataclass

from aca_analytics.database.connection import MySQLConnection
from aca_analytics.utils.logger import get_logger

logger = get_logger(__name__)

_IDENTIFIER = re.compile(r"^[A-Za-z0-9_]{1,64}$")


def validate_identifier(name: str) -> str:
    """Guard against SQL injection in identifiers (table/column/database names)."""
    if not _IDENTIFIER.match(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return name


@dataclass(frozen=True)
class TableSchema:
    name: str
    ddl: str  # full CREATE TABLE IF NOT EXISTS statement

    def __post_init__(self) -> None:
        validate_identifier(self.name)


API_RECORDS_TABLE = TableSchema(
    name="api_records",
    ddl="""
        CREATE TABLE IF NOT EXISTS api_records (
            id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            external_id  VARCHAR(512)    NOT NULL,
            payload      JSON            NOT NULL,
            ingested_at  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
                                         ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            UNIQUE KEY uq_api_records_external_id (external_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
)


class SchemaManager:
    """Creates the database and tables. Add new TableSchema objects to extend."""

    def __init__(self, connection: MySQLConnection, tables: list[TableSchema] | None = None) -> None:
        self.connection = connection
        self.tables = tables if tables is not None else [API_RECORDS_TABLE]

    @staticmethod
    def create_database(server_connection: MySQLConnection, name: str) -> None:
        """Create the database. `server_connection` must be opened with use_database=False."""
        name = validate_identifier(name)
        server_connection.execute(
            f"CREATE DATABASE IF NOT EXISTS `{name}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        logger.info("Database '%s' ready", name)

    def create_tables(self) -> None:
        for table in self.tables:
            self.connection.execute(table.ddl)
            logger.info("Table '%s' ready", table.name)
