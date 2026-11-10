import json

import pytest

from aca_analytics.database.schema import validate_identifier
from aca_analytics.models import Record


def test_record_from_api_and_row():
    record = Record.from_api({"id": 7, "name": "x"})
    row = record.to_row()
    assert row["external_id"] == "7"
    assert json.loads(row["payload"]) == {"id": 7, "name": "x"}


def test_record_missing_id():
    with pytest.raises(ValueError):
        Record.from_api({"name": "x"})


def test_identifier_validation():
    assert validate_identifier("api_records") == "api_records"
    with pytest.raises(ValueError):
        validate_identifier("bad; DROP TABLE x")
