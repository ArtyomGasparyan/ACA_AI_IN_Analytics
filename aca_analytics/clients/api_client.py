"""Authenticated client for a JSON API using an API key."""
from __future__ import annotations

from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from aca_analytics.config import APISettings
from aca_analytics.utils.logger import get_logger

logger = get_logger(__name__)


class APIError(Exception):
    """Raised when the API request fails or returns invalid JSON."""


class APIClient:
    def __init__(self, settings: APISettings) -> None:
        self.settings = settings
        self.session = self._build_session()

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update({"Accept": "application/json"})
        if not self.settings.key_param:
            value = self.settings.api_key
            if self.settings.key_prefix:
                value = f"{self.settings.key_prefix} {value}"
            session.headers[self.settings.key_header] = value

        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        session.mount("https://", HTTPAdapter(max_retries=retry))
        session.mount("http://", HTTPAdapter(max_retries=retry))
        return session

    def get(self, endpoint: str | None = None, params: dict[str, Any] | None = None) -> Any:
        """GET an endpoint and return the decoded JSON body."""
        endpoint = endpoint or self.settings.endpoint
        url = f"{self.settings.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        params = {**self.settings.query_params, **(params or {})}
        if self.settings.key_param:
            params[self.settings.key_param] = self.settings.api_key
        logger.info("GET %s", url)
        try:
            response = self.session.get(url, params=params, timeout=self.settings.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.JSONDecodeError as exc:
            raise APIError(
                f"Response from {url} is not valid JSON. Check API_BASE_URL and API_ENDPOINT in .env."
            ) from None
        except requests.HTTPError as exc:
            # Do not include exc text: the URL may contain the API key.
            status = exc.response.status_code if exc.response is not None else None
            raise APIError(f"Request to {url} failed with HTTP {status}. {self._hint(status)}") from None
        except requests.RequestException as exc:
            raise APIError(
                f"Request to {url} failed: {type(exc).__name__}. "
                "Check your internet connection and that API_BASE_URL in .env is correct."
            ) from None

    def _hint(self, status: int | None) -> str:
        if status in (401, 403):
            if self.settings.key_param:
                where = f"API_KEY and API_KEY_PARAM ('{self.settings.key_param}')"
            else:
                where = f"API_KEY and API_KEY_HEADER ('{self.settings.key_header}')"
            return (
                f"The API rejected your credentials. Check {where} in .env, "
                "and that your subscription/plan is active."
            )
        if status == 404:
            return "Endpoint not found. Check API_BASE_URL and API_ENDPOINT in .env."
        if status == 429:
            return "Rate limit or monthly quota reached. Wait, reduce requests, or upgrade your plan."
        if status is not None and status >= 500:
            return "The API server had an error. Try again later."
        if status == 422 or status == 400:
            return "The API rejected the request parameters. Check API_QUERY_PARAMS in .env."
        return "Check the API settings in .env."

    def fetch_records(self, endpoint: str | None = None, params: dict[str, Any] | None = None) -> list[dict]:
        """Return the list of records, honoring the optional API_DATA_KEY."""
        body = self.get(endpoint, params)
        if isinstance(body, dict) and "error" in body:
            err = body["error"]
            detail = err.get("info") or err.get("message") if isinstance(err, dict) else err
            raise APIError(f"API returned an error: {detail}. Check API_KEY and API_QUERY_PARAMS in .env.")
        if self.settings.data_key:
            if not isinstance(body, dict) or self.settings.data_key not in body:
                raise APIError(
                    f"Key '{self.settings.data_key}' not found in the API response. "
                    "Fix API_DATA_KEY in .env (leave it empty if the response is a plain list)."
                )
            body = body[self.settings.data_key]
        if isinstance(body, dict):
            body = [body]
        if not isinstance(body, list):
            raise APIError("Unexpected API response shape; expected a list of records")
        return body

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "APIClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
