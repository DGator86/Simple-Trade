from __future__ import annotations

import time
from abc import ABC, abstractmethod
from datetime import date

import pandas as pd
import requests

from simple_trade.data.schema import Timeframe


class ProviderError(RuntimeError):
    pass


class Provider(ABC):
    name: str

    def __init__(self, session: requests.Session | None = None, max_retries: int = 4):
        self.session = session or requests.Session()
        self.max_retries = max_retries

    @classmethod
    @abstractmethod
    def from_env(cls) -> Provider: ...

    @abstractmethod
    def bars(self, symbol: str, timeframe: Timeframe, start: date, end: date) -> pd.DataFrame:
        """Return bars in the common schema for [start, end] inclusive."""

    def _get(self, url: str, **kwargs) -> dict:
        """GET JSON, retrying 429 and 5xx with exponential backoff."""
        for attempt in range(self.max_retries + 1):
            resp = self.session.get(url, timeout=30, **kwargs)
            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt == self.max_retries:
                    break
                retry_after = resp.headers.get("Retry-After")
                time.sleep(float(retry_after) if retry_after else 2**attempt)
                continue
            if not resp.ok:
                raise ProviderError(
                    f"{self.name}: HTTP {resp.status_code} for {url}: {resp.text[:300]}"
                )
            return resp.json()
        raise ProviderError(f"{self.name}: HTTP {resp.status_code} after retries for {url}")


def require_env(name: str) -> str:
    import os

    value = os.environ.get(name)
    if not value:
        raise ProviderError(f"environment variable {name} is not set (see .env.example)")
    return value
