"""factory get_fetcher のテスト."""

from __future__ import annotations

import pytest

from src.fetchers.factory import available_sources, get_fetcher
from src.fetchers.fixed import FixedFetcher
from src.fetchers.yahoo_finance_jp import YahooFinanceJpFetcher
from src.fetchers.yfinance_adapter import YFinanceFetcher


@pytest.mark.parametrize(
    ("source", "cls"),
    [
        ("fixed", FixedFetcher),
        ("yfinance", YFinanceFetcher),
        ("yahoo_finance_jp", YahooFinanceJpFetcher),
    ],
)
def test_factory_returns_expected_class(source: str, cls: type) -> None:
    fetcher = get_fetcher(source)
    assert isinstance(fetcher, cls)


def test_unknown_source_raises() -> None:
    with pytest.raises(ValueError):
        get_fetcher("not_a_real_source")


def test_available_sources_lists_known() -> None:
    sources = available_sources()
    assert {"fixed", "yfinance", "yahoo_finance_jp"} <= set(sources)
