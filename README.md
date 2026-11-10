# ACA_AI_IN_Analytics

Python project that pulls data from an API-key protected JSON API, stores the raw responses as files, and loads them into a remote MySQL database (database, tables, and data are created/inserted by the code).

## Project structure

```
ACA_AI_IN_Analytics/
├── aca_analytics/            # Reusable package
│   ├── config/settings.py    # Settings loaded from .env
│   ├── clients/api_client.py # APIClient: API-key auth, retries, JSON parsing
│   ├── models/record.py      # Record: API item -> DB row
│   ├── database/
│   │   ├── connection.py     # MySQLConnection: remote connection (SSL optional)
│   │   ├── schema.py         # TableSchema, SchemaManager (create DB/tables)
│   │   └── repository.py     # Repository: batch upsert
│   ├── services/pipeline.py  # IngestionPipeline: API -> raw file -> MySQL
│   └── utils/                # Logging, RawDataStorage
├── data/
│   ├── raw/                  # Raw JSON downloaded from the API
│   └── processed/            # Cleaned / derived files
├── tests/
├── main.py                   # CLI entry point
├── .env                      # Local secrets (not committed)
├── .env.example              # Template for .env
└── requirements.txt          # Pinned dependencies
```

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # then edit .env with real values
```

## Configuration (`.env`)

| Variable | Description |
|---|---|
| `API_BASE_URL`, `API_ENDPOINT` | API location |
| `API_KEY` | API key (required) |
| `API_KEY_HEADER` / `API_KEY_PREFIX` | Header name (default `X-API-Key`) and optional prefix such as `Bearer` |
| `API_ID_FIELD` | JSON field that uniquely identifies a record (default `id`) |
| `API_DATA_KEY` | Key holding the list of records, empty if the response is a list |
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | Remote MySQL connection |
| `DB_SSL_CA` | Optional CA certificate path to enforce SSL |
| `RAW_DATA_DIR`, `LOG_LEVEL` | Storage folder and log level |

`.env` is git-ignored; never commit secrets.

## Usage

```powershell
python main.py init-db   # create database and tables
python main.py fetch     # API -> data/raw/api_<timestamp>.json
python main.py load      # latest raw file -> MySQL (upsert by external_id)
python main.py run       # all of the above
```

Default table `api_records`: `id`, `external_id` (unique), `payload` (JSON), `ingested_at`.
To add tables, define a new `TableSchema` in `aca_analytics/database/schema.py` and pass it to `SchemaManager`.

## Tests

```powershell
pytest
```

## Notes

- Identifiers are validated and values are always parameterized to prevent SQL injection.
- The MySQL user needs `CREATE` privilege for `init-db`; if the database already exists, only table privileges are needed.
- Remote MySQL must allow your IP; use `DB_SSL_CA` for encrypted connections.