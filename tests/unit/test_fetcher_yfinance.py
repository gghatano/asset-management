"""YFinanceFetcher のユニットテスト. yfinance.Ticker をモックする."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.fetchers.base import PriceFetcherError
from src.fetchers.yfinance_adapter import YFinanceFetcher


def _hist_df(close: float) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [close - 0.5],
            "High": [close + 1.0],
            "Low": [close - 1.0],
            "Close": [close],
            "Volume": [1000],
        },
        index=pd.DatetimeIndex(["2026-05-01"], name="Date"),
    )


def test_returns_close_price() -> None:
    asset = {"asset_id": "vt", "source_code": "VT", "currency": "USD"}
    fake_ticker = MagicMock()
    fake_ticker.history.return_value = _hist_df(128.5)
    with patch("yfinance.Ticker", return_value=fake_ticker):
        q = YFinanceFetcher().fetch(asset, date(2026, 5, 1))
    assert q.price == pytest.approx(128.5)
    assert q.currency == "USD"
    assert q.source == "yfinance"


def test_empty_history_raises() -> None:
    asset = {"asset_id": "vt", "source_code": "VT", "currency": "USD"}
    fake_ticker = MagicMock()
    fake_ticker.history.return_value = pd.DataFrame()
    with patch("yfinance.Ticker", return_value=fake_ticker), pytest.raises(PriceFetcherError):
        YFinanceFetcher().fetch(asset, date(2026, 5, 1))


def test_ticker_exception_wrapped() -> None:
    asset = {"asset_id": "vt", "source_code": "VT", "currency": "USD"}
    fake_ticker = MagicMock()
    fake_ticker.history.side_effect = RuntimeError("network down")
    with patch("yfinance.Ticker", return_value=fake_ticker), pytest.raises(PriceFetcherError):
        YFinanceFetcher().fetch(asset, date(2026, 5, 1))
