import pytest

from aca_analytics.config import ConfigError, Settings

ALL_VARS = [
    "API_BASE_URL", "API_ENDPOINT", "API_KEY", "API_KEY_HEADER", "API_KEY_PREFIX",
    "API_KEY_PARAM", "API_TIMEOUT", "API_ID_FIELD", "API_DATA_KEY", "API_QUERY_PARAMS",
    "DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME", "DB_SSL_CA",
    "RAW_DATA_DIR", "LOG_LEVEL",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for name in ALL_VARS:
        monkeypatch.delenv(name, raising=False)
    # Use an empty, temporary env file so the real .env is never read.
    return tmp_path / "empty.env"


def test_reports_all_missing_variables(clean_env):
    with pytest.raises(ConfigError) as exc:
        Settings.from_env(clean_env)
    message = str(exc.value)
    for name in ("API_BASE_URL", "API_ENDPOINT", "API_KEY", "DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"):
        assert name in message


def test_valid_configuration(monkeypatch, clean_env):
    values = {
        "API_BASE_URL": "https://api.example.com",
        "API_ENDPOINT": "/news",
        "API_KEY": "secret",
        "DB_HOST": "db.example.com",
        "DB_USER": "user",
        "DB_PASSWORD": "pw",
        "DB_NAME": "db",
        "API_QUERY_PARAMS": "limit=10&languages=en",
    }
    for k, v in values.items():
        monkeypatch.setenv(k, v)
    settings = Settings.from_env(clean_env)
    assert settings.api.query_params == {"limit": "10", "languages": "en"}
    assert "secret" not in repr(settings.api)
    assert "pw" not in repr(settings.database)


def test_invalid_port_message(monkeypatch, clean_env):
    monkeypatch.setenv("DB_PORT", "abc")
    with pytest.raises(ConfigError) as exc:
        Settings.from_env(clean_env)
    assert "DB_PORT must be a whole number" in str(exc.value)
