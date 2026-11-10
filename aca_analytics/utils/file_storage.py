"""Persist and read raw JSON files."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aca_analytics.utils.logger import get_logger

logger = get_logger(__name__)


class RawDataStorage:
    """Save API responses as timestamped JSON files in the raw data folder."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    def save(self, data: Any, prefix: str = "api") -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = self.directory / f"{prefix}_{stamp}.json"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Raw data saved to %s", path)
        return path

    def load(self, path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    def latest(self, prefix: str = "api") -> Path:
        files = sorted(self.directory.glob(f"{prefix}_*.json"))
        if not files:
            raise FileNotFoundError(f"No raw files with prefix '{prefix}' in {self.directory}")
        return files[-1]
