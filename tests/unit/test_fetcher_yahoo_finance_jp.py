"""YahooFinanceJpFetcher のユニットテスト. HTTP はモック."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from src.fetchers.base import PriceFetcherError
from src.fetchers.yahoo_finance_jp import (
    YahooFinanceJpFetcher,
    parse_price_from_html,
)


def test_parse_price_from_sample_html(fixtures_dir: Path) -> None:
    html = (fixtures_dir / "yahoo_finance_jp_sample.html").read_text(encoding="utf-8")
    price = parse_price_from_html(html)
    assert price == 42272.0


def test_parse_price_no_match_raises() -> None:
    with pytest.raises(PriceFetcherError):
        parse_price_from_html("<html><body>no price here</body></html>")


def test_parse_skips_too_small_values() -> None:
    # 「+150円」のような差分値（基準価額レンジ外）は採用しない
    html = "<p>+50円</p><p>42,000円</p>"
    assert parse_price_from_html(html) == 42000.0


def test_fetch_uses_fetch_html_and_parser(fixtures_dir: Path) -> None:
    html = (fixtures_dir / "yahoo_finance_jp_sample.html").read_text(encoding="utf-8")
    asset = {
        "asset_id": "emaxis_slim_sp500",
        "source_code": "03311187",
        "currency": "JPY",
    }
    with patch("src.fetchers.yahoo_finance_jp.fetch_html", return_value=html) as mock_fetch:
        q = YahooFinanceJpFetcher().fetch(asset, date(2026, 5, 1))
    mock_fetch.assert_called_once()
    assert "03311187" in mock_fetch.call_args.args[0]
    assert q.price == 42272.0
    assert q.currency == "JPY"
    assert q.source == "yahoo_finance_jp"


def test_fetch_html_failure_propagates() -> None:
    asset = {"asset_id": "x", "source_code": "00000000", "currency": "JPY"}
    with (
        patch(
            "src.fetchers.yahoo_finance_jp.fetch_html",
            side_effect=PriceFetcherError("network down"),
        ),
        pytest.raises(PriceFetcherError),
    ):
        YahooFinanceJpFetcher().fetch(asset, date(2026, 5, 1))
