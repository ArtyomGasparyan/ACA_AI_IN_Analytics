"""Data access: insert/upsert rows into a table."""
from __future__ import annotations

from typing import Any, Sequence

from aca_analytics.database.connection import MySQLConnection
from aca_analytics.database.schema import validate_identifier
from aca_analytics.utils.logger import get_logger

logger = get_logger(__name__)


class Repository:
    def __init__(self, connection: MySQLConnection, table: str, key_columns: Sequence[str] = ("external_id",)) -> None:
        self.connection = connection
        self.table = validate_identifier(table)
        self.key_columns = tuple(validate_identifier(c) for c in key_columns)

    def upsert_many(self, rows: Sequence[dict[str, Any]], batch_size: int = 500) -> int:
        """Insert rows; update non-key columns when the unique key already exists."""
        if not rows:
            logger.info("No rows to insert")
            return 0

        columns = [validate_identifier(c) for c in rows[0].keys()]
        update_cols = [c for c in columns if c not in self.key_columns]
        placeholders = ", ".join(["%s"] * len(columns))
        col_list = ", ".join(f"`{c}`" for c in columns)
        query = f"INSERT INTO `{self.table}` ({col_list}) VALUES ({placeholders})"
        if update_cols:
            updates = ", ".join(f"`{c}` = VALUES(`{c}`)" for c in update_cols)
            query += f" ON DUPLICATE KEY UPDATE {updates}"

        values = [tuple(row[c] for c in columns) for row in rows]
        affected = 0
        for start in range(0, len(values), batch_size):
            affected += self.connection.executemany(query, values[start:start + batch_size])
        logger.info("Upserted %d rows into '%s'", len(values), self.table)
        return affected

    def count(self) -> int:
        result = self.connection.fetchall(f"SELECT COUNT(*) AS total FROM `{self.table}`")
        return int(result[0]["total"])
