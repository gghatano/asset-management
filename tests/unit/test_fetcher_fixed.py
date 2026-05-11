"""FixedFetcher のユニットテスト."""

from __future__ import annotations

from datetime import date

from src.fetchers.fixed import FixedFetcher


def test_returns_price_1() -> None:
    f = FixedFetcher()
    asset = {
        "asset_id": "cash_jpy",
        "currency": "JPY",
        "source_code": "JPY",
        "unit_price_base": 1,
    }
    q = f.fetch(asset, date(2026, 5, 1))
    assert q.price == 1.0
    assert q.asset_id == "cash_jpy"
    assert q.currency == "JPY"
    assert q.source == "fixed"
    assert q.date == date(2026, 5, 1)


def test_uses_currency_default_jpy() -> None:
    f = FixedFetcher()
    asset = {"asset_id": "x", "source_code": "X"}
    q = f.fetch(asset, date(2026, 5, 1))
    assert q.currency == "JPY"
