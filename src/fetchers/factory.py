"""price_source 文字列から Fetcher インスタンスを返すファクトリ."""

from __future__ import annotations

from src.fetchers.base import PriceFetcher
from src.fetchers.fixed import FixedFetcher
from src.fetchers.yahoo_finance_jp import YahooFinanceJpFetcher
from src.fetchers.yfinance_adapter import YFinanceFetcher

_REGISTRY: dict[str, type[PriceFetcher]] = {
    "fixed": FixedFetcher,
    "yfinance": YFinanceFetcher,
    "yahoo_finance_jp": YahooFinanceJpFetcher,
}


def get_fetcher(price_source: str) -> PriceFetcher:
    """price_source に対応する Fetcher を返す。未知なら ValueError."""
    try:
        cls = _REGISTRY[price_source]
    except KeyError as e:
        raise ValueError(f"unknown price_source: {price_source!r}") from e
    return cls()


def available_sources() -> list[str]:
    return sorted(_REGISTRY.keys())
