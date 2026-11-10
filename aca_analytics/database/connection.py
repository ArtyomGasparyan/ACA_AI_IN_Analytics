"""Remote MySQL connection wrapper."""
from __future__ import annotations

from typing import Any, Sequence

import mysql.connector
from mysql.connector import Error as MySQLError

from aca_analytics.config import DatabaseSettings
from aca_analytics.utils.logger import get_logger

logger = get_logger(__name__)


class MySQLConnection:
    """Context-managed MySQL connection. Commits on success, rolls back on error.

    Use ``use_database=False`` to connect to the server without selecting a
    database (needed to create the database itself).
    """

    def __init__(self, settings: DatabaseSettings, use_database: bool = True) -> None:
        self.settings = settings
        self.use_database = use_database
        self._conn = None

    def connect(self) -> None:
        params: dict[str, Any] = {
            "host": self.settings.host,
            "port": self.settings.port,
            "user": self.settings.user,
            "password": self.settings.password,
            "connection_timeout": 15,
        }
        if self.use_database:
            params["database"] = self.settings.name
        if self.settings.ssl_ca:
            params["ssl_ca"] = self.settings.ssl_ca
            params["ssl_verify_cert"] = True
        try:
            self._conn = mysql.connector.connect(**params)
        except MySQLError as exc:
            raise ConnectionError(
                f"Could not connect to MySQL at {self.settings.host}:{self.settings.port}: {exc}"
            ) from exc
        logger.info("Connected to MySQL at %s:%s", self.settings.host, self.settings.port)

    def close(self) -> None:
        if self._conn is not None and self._conn.is_connected():
            self._conn.close()
            logger.info("MySQL connection closed")
        self._conn = None

    def execute(self, query: str, params: Sequence[Any] | None = None) -> int:
        """Run a single statement; returns affected row count."""
        cursor = self._cursor()
        try:
            cursor.execute(query, params or ())
            return cursor.rowcount
        finally:
            cursor.close()

    def executemany(self, query: str, rows: Sequence[Sequence[Any]]) -> int:
        cursor = self._cursor()
        try:
            cursor.executemany(query, rows)
            return cursor.rowcount
        finally:
            cursor.close()

    def fetchall(self, query: str, params: Sequence[Any] | None = None) -> list[dict[str, Any]]:
        cursor = self._conn.cursor(dictionary=True) if self._conn else self._cursor()
        try:
            cursor.execute(query, params or ())
            return cursor.fetchall()
        finally:
            cursor.close()

    def commit(self) -> None:
        self._require_conn().commit()

    def rollback(self) -> None:
        self._require_conn().rollback()

    def _require_conn(self):
        if self._conn is None:
            raise RuntimeError("Not connected. Call connect() or use a 'with' block.")
        return self._conn

    def _cursor(self):
        return self._require_conn().cursor()

    def __enter__(self) -> "MySQLConnection":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type is None:
                self.commit()
            else:
                self.rollback()
        finally:
            self.close()
