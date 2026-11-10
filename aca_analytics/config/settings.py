"""Application settings loaded from environment variables / .env file."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qsl

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_PLACEHOLDERS = {"your_api_key_here", "your_user", "your_password", "your-remote-host.example.com"}


class ConfigError(ValueError):
    """Raised when the .env configuration is missing or invalid. Lists every problem found."""


class _Problems:
    """Collects configuration problems so the user can fix them all in one go."""

    def __init__(self) -> None:
        self.items: list[str] = []

    def require(self, name: str, hint: str) -> str:
        value = os.getenv(name, "").strip()
        if not value:
            self.items.append(f"{name} is missing or empty in .env. {hint}")
            return ""
        if value in _PLACEHOLDERS or value.startswith("your_"):
            self.items.append(f"{name} still has the placeholder value. {hint}")
        return value

    def integer(self, name: str, default: int) -> int:
        raw = os.getenv(name, "").strip() or str(default)
        try:
            return int(raw)
        except ValueError:
            self.items.append(f"{name} must be a whole number (got {raw!r}). Example: {name}={default}")
            return default

    def raise_if_any(self) -> None:
        if self.items:
            details = "\n  - ".join(self.items)
            raise ConfigError(
                f"Configuration problems found ({len(self.items)}). Please update your .env file:\n  - {details}"
            )


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
        problems = _Problems()

        raw_dir = Path(os.getenv("RAW_DATA_DIR", "data/raw"))
        if not raw_dir.is_absolute():
            raw_dir = PROJECT_ROOT / raw_dir

        base_url = problems.require("API_BASE_URL", "Example: API_BASE_URL=https://api.apilayer.com")
        if base_url and not base_url.startswith(("http://", "https://")):
            problems.items.append("API_BASE_URL must start with http:// or https://")

        api = APISettings(
            base_url=base_url,
            endpoint=problems.require("API_ENDPOINT", "Example: API_ENDPOINT=/media_stack/news"),
            api_key=problems.require("API_KEY", "Paste your API key after API_KEY="),
            key_header=os.getenv("API_KEY_HEADER", "X-API-Key").strip() or "X-API-Key",
            key_prefix=os.getenv("API_KEY_PREFIX", "").strip(),
            key_param=os.getenv("API_KEY_PARAM", "").strip(),
            timeout=problems.integer("API_TIMEOUT", 30),
            id_field=os.getenv("API_ID_FIELD", "id").strip() or "id",
            data_key=os.getenv("API_DATA_KEY", "").strip(),
            query_params=dict(parse_qsl(os.getenv("API_QUERY_PARAMS", "").strip())),
        )
        database = DatabaseSettings(
            host=problems.require("DB_HOST", "Set it to your remote MySQL host name or IP."),
            port=problems.integer("DB_PORT", 3306),
            user=problems.require("DB_USER", "Set it to your MySQL user name."),
            password=problems.require("DB_PASSWORD", "Set it to your MySQL password."),
            name=problems.require("DB_NAME", "Example: DB_NAME=aca_analytics"),
            ssl_ca=os.getenv("DB_SSL_CA", "").strip(),
        )
        ssl_ca = database.ssl_ca
        if ssl_ca and not Path(ssl_ca).is_file():
            problems.items.append(f"DB_SSL_CA points to a file that does not exist: {ssl_ca}")

        problems.raise_if_any()
        return cls(
            api=api,
            database=database,
            raw_data_dir=raw_dir,
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )
