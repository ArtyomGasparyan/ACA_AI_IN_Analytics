"""Domain model for a record received from the API."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Record:
    external_id: str
    payload: dict[str, Any]

    @classmethod
    def from_api(cls, item: dict[str, Any], id_field: str = "id") -> "Record":
        if id_field not in item:
            raise ValueError(f"Record is missing id field '{id_field}'")
        return cls(external_id=str(item[id_field]), payload=item)

    def to_row(self) -> dict[str, Any]:
        """Column -> value mapping matching the `api_records` table."""
        return {
            "external_id": self.external_id,
            "payload": json.dumps(self.payload, ensure_ascii=False),
        }
