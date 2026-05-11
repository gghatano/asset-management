"""fetch_prices のインテグレーションテスト. ネットワーク無し."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from src.fetch_prices import (
    append_quotes,
    fetch_one,
    last_price_for,
    load_existing_prices,
    run,
)
from src.fetchers.base import PriceFetcherError, PriceQuote


def _fake_fetcher_for(asset: dict, target_date: date) -> PriceQuote:
    """price_source ごとに固定の値を返すダミー fetch."""
    price_map = {
        "yahoo_finance_jp": 42272.0,
        "yfinance": 128.5,
        "fixed": 1.0,
    }
    return PriceQuote(
        asset_id=asset["asset_id"],
        date=target_date,
        price=price_map[asset["price_source"]],
        currency=asset.get("currency", "JPY"),
        source=asset["price_source"],
    )


def test_run_writes_csv(tmp_path: Path, config_dir: Path) -> None:
    csv_path = tmp_path / "prices.csv"
    with patch(
        "src.fetch_prices.get_fetcher",
        side_effect=lambda src: _StubFetcher(),
    ):
        quotes = run(config_dir, csv_path, date(2026, 5, 1))
    assert csv_path.exists()
    text = csv_path.read_text(encoding="utf-8")
    assert text.splitlines()[0] == "date,asset_id,price,currency,source"
    assert any(q.asset_id == "emaxis_slim_sp500" for q in quotes)
    assert any(q.asset_id == "vt" for q in quotes)
    assert any(q.asset_id == "cash_jpy" for q in quotes)


def test_append_quotes_creates_and_appends(tmp_path: Path) -> None:
    csv_path = tmp_path / "p.csv"
    q1 = PriceQuote("x", date(2026, 5, 1), 100.0, "JPY", "fixed")
    q2 = PriceQuote("x", date(2026, 5, 2), 101.0, "JPY", "fixed")
    append_quotes(csv_path, [q1])
    append_quotes(csv_path, [q2])
    lines = csv_path.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("date,asset_id")
    assert "2026-05-01" in lines[1]
    assert "2026-05-02" in lines[2]


def test_load_existing_prices_returns_empty_when_missing(tmp_path: Path) -> None:
    assert load_existing_prices(tmp_path / "missing.csv") == []


def test_last_price_for() -> None:
    rows = [
        {"date": "2026-04-30", "asset_id": "vt", "price": "120.0"},
        {"date": "2026-05-01", "asset_id": "vt", "price": "128.5"},
        {"date": "2026-05-01", "asset_id": "other", "price": "1.0"},
    ]
    last = last_price_for(rows, "vt")
    assert last["price"] == "128.5"
    assert last_price_for(rows, "nonexistent") is None


def test_fetch_one_falls_back_on_error() -> None:
    asset = {
        "asset_id": "vt",
        "price_source": "yfinance",
        "currency": "USD",
        "source_code": "VT",
    }
    existing = [
        {
            "date": "2026-04-30",
            "asset_id": "vt",
            "price": "127.0",
            "currency": "USD",
            "source": "yfinance",
        }
    ]
    with patch("src.fetch_prices.get_fetcher", side_effect=lambda src: _RaisingFetcher()):
        q = fetch_one(asset, date(2026, 5, 1), existing)
    assert q.price == 127.0
    assert q.source.endswith("+fallback")


def test_fetch_one_raises_when_no_previous() -> None:
    asset = {
        "asset_id": "vt",
        "price_source": "yfinance",
        "currency": "USD",
        "source_code": "VT",
    }
    with (
        patch("src.fetch_prices.get_fetcher", side_effect=lambda src: _RaisingFetcher()),
        pytest.raises(PriceFetcherError),
    ):
        fetch_one(asset, date(2026, 5, 1), [])


class _StubFetcher:
    def fetch(self, asset: dict, target_date: date) -> PriceQuote:
        return _fake_fetcher_for(asset, target_date)


class _RaisingFetcher:
    def fetch(self, asset: dict, target_date: date) -> PriceQuote:
        raise PriceFetcherError("simulated failure")
