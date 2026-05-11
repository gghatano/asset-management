"""build_dashboard 拡張のインテグレーションテスト。

サンプル CSV を入力に、HTML が想定の data-testid と KPI を含むか検証。
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from src.build_dashboard import build, render_html


@pytest.fixture
def daily_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "date": date(2026, 5, 1),
                "total_book_value_jpy": 4_100_000,
                "total_market_value_jpy": 4_100_000,
                "profit_loss_jpy": 0,
                "profit_loss_rate": 0.0,
            },
            {
                "date": date(2026, 5, 5),
                "total_book_value_jpy": 4_150_000,
                "total_market_value_jpy": 4_300_000,
                "profit_loss_jpy": 150_000,
                "profit_loss_rate": 0.0361,
            },
        ]
    )


@pytest.fixture
def by_asset_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "date": date(2026, 5, 1),
                "asset_id": "fund_a",
                "quantity": 1_000_000,
                "book_value_jpy": 4_000_000,
                "market_value_jpy": 4_000_000,
                "profit_loss_jpy": 0,
                "weight": 0.9756,
            },
            {
                "date": date(2026, 5, 1),
                "asset_id": "cash_jpy",
                "quantity": 100_000,
                "book_value_jpy": 100_000,
                "market_value_jpy": 100_000,
                "profit_loss_jpy": 0,
                "weight": 0.0244,
            },
            {
                "date": date(2026, 5, 5),
                "asset_id": "fund_a",
                "quantity": 1_000_000,
                "book_value_jpy": 4_000_000,
                "market_value_jpy": 4_200_000,
                "profit_loss_jpy": 200_000,
                "weight": 0.9767,
            },
            {
                "date": date(2026, 5, 5),
                "asset_id": "cash_jpy",
                "quantity": 100_000,
                "book_value_jpy": 100_000,
                "market_value_jpy": 100_000,
                "profit_loss_jpy": 0,
                "weight": 0.0233,
            },
        ]
    )


@pytest.fixture
def assets() -> list[dict]:
    return [
        {
            "asset_id": "fund_a",
            "name": "サンプル投信 A",
            "asset_type": "mutual_fund",
            "currency": "JPY",
        },
        {
            "asset_id": "cash_jpy",
            "name": "日本円現金",
            "asset_type": "cash",
            "currency": "JPY",
        },
    ]


@pytest.fixture
def monthly_purchases() -> list[dict]:
    return [
        {
            "asset_id": "fund_a",
            "amount_jpy": 50000,
            "purchase_day": 5,
            "start_month": "2026-05",
            "end_month": None,
            "account_type": "NISA",
        },
        {
            "asset_id": "cash_jpy",
            "amount_jpy": 30000,
            "purchase_day": 25,
            "start_month": "2026-05",
            "end_month": None,
            "account_type": "現金",
        },
    ]


@pytest.fixture
def prices_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "date": date(2026, 5, 1),
                "asset_id": "fund_a",
                "price": 40000,
                "currency": "JPY",
                "source": "fixed",
            },
            {
                "date": date(2026, 5, 5),
                "asset_id": "fund_a",
                "price": 42000,
                "currency": "JPY",
                "source": "fixed",
            },
        ]
    )


class TestRenderHtmlFull:
    def test_includes_all_testids(
        self,
        daily_df: pd.DataFrame,
        by_asset_df: pd.DataFrame,
        assets: list[dict],
        monthly_purchases: list[dict],
        prices_df: pd.DataFrame,
    ) -> None:
        html = render_html(
            daily_df=daily_df,
            by_asset_df=by_asset_df,
            assets=assets,
            monthly_purchases=monthly_purchases,
            prices_df=prices_df,
        )
        for testid in [
            "kpi",
            "kpi-current-value",
            "kpi-total-invested",
            "kpi-profit-loss",
            "kpi-profit-loss-rate",
            "kpi-monthly-purchase",
            "chart-market-value",
            "chart-total-invested",
            "chart-profit-loss",
            "chart-by-asset-stack",
            "chart-allocation",
            "table-holdings",
            "table-monthly-purchases",
            "table-latest-prices",
        ]:
            assert f'data-testid="{testid}"' in html, f"{testid} が HTML に無い"

    def test_kpi_from_latest_row(
        self,
        daily_df: pd.DataFrame,
        by_asset_df: pd.DataFrame,
        assets: list[dict],
        monthly_purchases: list[dict],
        prices_df: pd.DataFrame,
    ) -> None:
        html = render_html(
            daily_df=daily_df,
            by_asset_df=by_asset_df,
            assets=assets,
            monthly_purchases=monthly_purchases,
            prices_df=prices_df,
        )
        # 最新日 (5/5) の値: market 4,300,000、book 4,150,000、損益 150,000、率 3.61%
        assert "4,300,000" in html  # current value
        assert "4,150,000" in html  # total invested
        assert "150,000" in html  # profit loss
        assert "3.61%" in html  # rate
        # 月間購入額: 50,000 + 30,000 = 80,000
        assert "80,000" in html

    def test_holdings_table_uses_asset_name(
        self,
        by_asset_df: pd.DataFrame,
        assets: list[dict],
        monthly_purchases: list[dict],
    ) -> None:
        html = render_html(
            by_asset_df=by_asset_df, assets=assets, monthly_purchases=monthly_purchases
        )
        assert "サンプル投信 A" in html
        assert "日本円現金" in html

    def test_monthly_purchases_table_shows_amounts(self, monthly_purchases: list[dict]) -> None:
        html = render_html(monthly_purchases=monthly_purchases)
        assert "50,000" in html
        assert "NISA" in html
        assert "現金" in html

    def test_skeleton_when_no_data(self) -> None:
        html = render_html()
        assert 'data-testid="status"' in html
        # KPI は 0 で表示される
        assert 'data-testid="kpi-current-value"' in html
        # チャートのセクションは無い (no chart-market-value)
        assert "chart-market-value" not in html

    def test_plotly_cdn_included(self, daily_df: pd.DataFrame) -> None:
        html = render_html(daily_df=daily_df)
        assert "cdn.plot.ly" in html


class TestBuildFull:
    def test_build_writes_full_html(
        self,
        tmp_path: Path,
        daily_df: pd.DataFrame,
        by_asset_df: pd.DataFrame,
        assets: list[dict],
        monthly_purchases: list[dict],
        prices_df: pd.DataFrame,
    ) -> None:
        out = tmp_path / "public" / "index.html"
        build(
            out,
            daily_df=daily_df,
            by_asset_df=by_asset_df,
            assets=assets,
            monthly_purchases=monthly_purchases,
            prices_df=prices_df,
        )
        text = out.read_text(encoding="utf-8")
        assert 'data-testid="kpi"' in text
        assert 'data-testid="chart-market-value"' in text
        assert 'data-testid="table-holdings"' in text
