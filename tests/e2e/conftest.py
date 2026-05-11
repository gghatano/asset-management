"""E2E (Playwright) 用のフィクスチャ。

生成された HTML を file:// で開く方式。後で実サーバ起動が必要になったら
http_server フィクスチャを追加する。
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from src.build_dashboard import build


@pytest.fixture(scope="session")
def dashboard_url(tmp_path_factory: pytest.TempPathFactory) -> str:
    out_dir = tmp_path_factory.mktemp("dashboard")
    out = out_dir / "index.html"
    build(
        out,
        kpi={
            "current_value_jpy": 5920000,
            "total_invested_jpy": 5860000,
            "profit_loss_jpy": 60000,
            "profit_loss_rate": 0.0102,
        },
    )
    return f"file://{Path(out).resolve()}"


@pytest.fixture(scope="session")
def dashboard_full_url(tmp_path_factory: pytest.TempPathFactory) -> str:
    """グラフ・テーブル込みのフル版 dashboard を生成。"""
    out_dir = tmp_path_factory.mktemp("dashboard_full")
    out = out_dir / "index.html"
    daily_df = pd.DataFrame(
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
    by_asset_df = pd.DataFrame(
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
    assets = [
        {
            "asset_id": "fund_a",
            "name": "サンプル投信 A",
            "asset_type": "mutual_fund",
            "currency": "JPY",
        },
        {"asset_id": "cash_jpy", "name": "日本円現金", "asset_type": "cash", "currency": "JPY"},
    ]
    monthly_purchases = [
        {
            "asset_id": "fund_a",
            "amount_jpy": 50000,
            "purchase_day": 5,
            "start_month": "2026-05",
            "end_month": None,
            "account_type": "NISA",
        }
    ]
    prices_df = pd.DataFrame(
        [
            {
                "date": date(2026, 5, 5),
                "asset_id": "fund_a",
                "price": 42000,
                "currency": "JPY",
                "source": "fixed",
            }
        ]
    )
    build(
        out,
        daily_df=daily_df,
        by_asset_df=by_asset_df,
        assets=assets,
        monthly_purchases=monthly_purchases,
        prices_df=prices_df,
    )
    return f"file://{Path(out).resolve()}"
