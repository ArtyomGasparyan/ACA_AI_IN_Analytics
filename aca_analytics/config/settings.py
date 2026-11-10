"""Application settings loaded from environment variables / .env file."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qsl

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class APISettings:
    base_url: str
    endpoint: str
    api_key: str = ""
    key_header: str = "X-API-Key"
    key_prefix: str = ""
    key_param: str = ""  # if set, send the key as this query parameter instead of a header
    timeout: int = 30
    id_field: str = "id"
    data_key: str = ""
    query_params: dict[str, str] = field(default_factory=dict)

    def __repr__(self) -> str:  # never expose the API key
        return f"APISettings(base_url={self.base_url!r}, endpoint={self.endpoint!r}, api_key='***')"


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    user: str
    password: str
    name: str
    port: int = 3306
    ssl_ca: str = ""

    def __repr__(self) -> str:  # never expose the password
        return f"DatabaseSettings(host={self.host!r}, port={self.port}, user={self.user!r}, name={self.name!r})"


@dataclass(frozen=True)
class Settings:
    api: APISettings
    database: DatabaseSettings
    raw_data_dir: Path
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> "Settings":
        load_dotenv(env_file or PROJECT_ROOT / ".env")

        raw_dir = Path(os.getenv("RAW_DATA_DIR", "data/raw"))
        if not raw_dir.is_absolute():
            raw_dir = PROJECT_ROOT / raw_dir

        return cls(
            api=APISettings(
                base_url=_require("API_BASE_URL"),
                endpoint=_require("API_ENDPOINT"),
                api_key=_require("API_KEY"),
                key_header=os.getenv("API_KEY_HEADER", "X-API-Key"),
                key_prefix=os.getenv("API_KEY_PREFIX", "").strip(),
                key_param=os.getenv("API_KEY_PARAM", "").strip(),
                timeout=int(os.getenv("API_TIMEOUT", "30")),
                id_field=os.getenv("API_ID_FIELD", "id"),
                data_key=os.getenv("API_DATA_KEY", "").strip(),
                query_params=dict(parse_qsl(os.getenv("API_QUERY_PARAMS", "").strip())),
            ),
            database=DatabaseSettings(
                host=_require("DB_HOST"),
                port=int(os.getenv("DB_PORT", "3306")),
                user=_require("DB_USER"),
                password=_require("DB_PASSWORD"),
                name=_require("DB_NAME"),
                ssl_ca=os.getenv("DB_SSL_CA", "").strip(),
            ),
            raw_data_dir=raw_dir,
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )
