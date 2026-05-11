"""calculate_portfolio のユニットテスト。"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from src.calculate_portfolio import (
    AssetSnapshot,
    DailySnapshot,
    compute_daily_portfolio,
    compute_holdings,
    compute_market_value,
    compute_snapshots_for_date,
    date_range,
)
from src.generate_transactions import Transaction


@pytest.fixture
def assets() -> list[dict]:
    return [
        {
            "asset_id": "fund_a",
            "name": "Fund A",
            "asset_type": "mutual_fund",
            "currency": "JPY",
            "unit_price_base": 10000,
        },
        {
            "asset_id": "etf_us",
            "name": "ETF US",
            "asset_type": "etf",
            "currency": "USD",
        },
        {
            "asset_id": "cash_jpy",
            "name": "現金",
            "asset_type": "cash",
            "currency": "JPY",
        },
    ]


@pytest.fixture
def prices_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"date": date(2026, 5, 1), "asset_id": "fund_a", "price": 40000.0},
            {"date": date(2026, 5, 5), "asset_id": "fund_a", "price": 42000.0},
            {"date": date(2026, 5, 1), "asset_id": "etf_us", "price": 100.0},
            {"date": date(2026, 5, 1), "asset_id": "usd_jpy", "price": 150.0},
        ]
    )


@pytest.fixture
def initial_positions() -> list[dict]:
    return [
        {
            "asset_id": "fund_a",
            "quantity": 1_000_000,
            "book_value_jpy": 4_000_000,
        },
        {
            "asset_id": "cash_jpy",
            "quantity": 100_000,
            "book_value_jpy": 100_000,
        },
    ]


class TestDateRange:
    def test_inclusive(self) -> None:
        assert list(date_range(date(2026, 5, 1), date(2026, 5, 3))) == [
            date(2026, 5, 1),
            date(2026, 5, 2),
            date(2026, 5, 3),
        ]

    def test_single_day(self) -> None:
        assert list(date_range(date(2026, 5, 1), date(2026, 5, 1))) == [date(2026, 5, 1)]


class TestComputeHoldings:
    def test_only_initial(self, initial_positions: list[dict]) -> None:
        h = compute_holdings(initial_positions, [], date(2026, 5, 1))
        assert h["fund_a"]["quantity"] == 1_000_000
        assert h["fund_a"]["book_value_jpy"] == 4_000_000

    def test_adds_purchases_within_date(self, initial_positions: list[dict]) -> None:
        txs = [
            Transaction(date(2026, 5, 5), "fund_a", 50_000, 42000, 11904.76, "NISA"),
        ]
        h = compute_holdings(initial_positions, txs, date(2026, 5, 5))
        assert h["fund_a"]["quantity"] == pytest.approx(1_000_000 + 11904.76)
        assert h["fund_a"]["book_value_jpy"] == 4_050_000

    def test_excludes_future_purchases(self, initial_positions: list[dict]) -> None:
        txs = [
            Transaction(date(2026, 5, 5), "fund_a", 50_000, 42000, 11904.76, "NISA"),
        ]
        h = compute_holdings(initial_positions, txs, date(2026, 5, 4))
        assert h["fund_a"]["quantity"] == 1_000_000

    def test_creates_holding_for_new_asset(self) -> None:
        txs = [Transaction(date(2026, 5, 5), "vt", 20_000, 15000, 1.33, "特定")]
        h = compute_holdings([], txs, date(2026, 5, 5))
        assert h["vt"]["quantity"] == pytest.approx(1.33)
        assert h["vt"]["book_value_jpy"] == 20_000


class TestComputeMarketValue:
    def test_mutual_fund(self, prices_df: pd.DataFrame) -> None:
        asset = {
            "asset_id": "fund_a",
            "asset_type": "mutual_fund",
            "currency": "JPY",
            "unit_price_base": 10000,
        }
        # quantity 1,200,000 × 42272 / 10000 を仕様 8.4 から検算 → 5,072,640
        df = pd.DataFrame([{"date": date(2026, 5, 1), "asset_id": "fund_a", "price": 42272.0}])
        mv = compute_market_value(asset, 1_200_000, df, date(2026, 5, 1))
        assert mv == pytest.approx(5_072_640)

    def test_etf_with_fx(self, prices_df: pd.DataFrame) -> None:
        asset = {"asset_id": "etf_us", "asset_type": "etf", "currency": "USD"}
        # 2 株 × (100 USD × 150) = 30,000
        mv = compute_market_value(asset, 2, prices_df, date(2026, 5, 1))
        assert mv == pytest.approx(30_000)

    def test_cash(self, prices_df: pd.DataFrame) -> None:
        asset = {"asset_id": "cash_jpy", "asset_type": "cash", "currency": "JPY"}
        mv = compute_market_value(asset, 100_000, prices_df, date(2026, 5, 1))
        assert mv == 100_000

    def test_no_price_returns_none(self, prices_df: pd.DataFrame) -> None:
        asset = {
            "asset_id": "fund_b",
            "asset_type": "mutual_fund",
            "currency": "JPY",
            "unit_price_base": 10000,
        }
        assert compute_market_value(asset, 100, prices_df, date(2026, 5, 1)) is None


class TestComputeSnapshotsForDate:
    def test_returns_daily_and_per_asset(
        self,
        assets: list[dict],
        initial_positions: list[dict],
        prices_df: pd.DataFrame,
    ) -> None:
        daily, snaps = compute_snapshots_for_date(
            target_date=date(2026, 5, 5),
            initial_positions=initial_positions,
            transactions=[],
            assets=assets,
            prices_df=prices_df,
        )
        assert isinstance(daily, DailySnapshot)
        assert all(isinstance(s, AssetSnapshot) for s in snaps)
        assert len(snaps) == 2  # fund_a と cash_jpy
        # fund_a の market_value = 1,000,000 × 42000 / 10000 = 4,200,000
        fund = next(s for s in snaps if s.asset_id == "fund_a")
        assert fund.market_value_jpy == pytest.approx(4_200_000)
        # cash_jpy = 100,000
        cash = next(s for s in snaps if s.asset_id == "cash_jpy")
        assert cash.market_value_jpy == 100_000
        # 合計 4,300,000、簿価 4,100,000、損益 +200,000
        assert daily.total_market_value_jpy == pytest.approx(4_300_000)
        assert daily.total_book_value_jpy == 4_100_000
        assert daily.profit_loss_jpy == pytest.approx(200_000)

    def test_weights_sum_to_one(
        self,
        assets: list[dict],
        initial_positions: list[dict],
        prices_df: pd.DataFrame,
    ) -> None:
        _, snaps = compute_snapshots_for_date(
            target_date=date(2026, 5, 5),
            initial_positions=initial_positions,
            transactions=[],
            assets=assets,
            prices_df=prices_df,
        )
        assert sum(s.weight for s in snaps) == pytest.approx(1.0)

    def test_forward_fill_uses_previous_price(
        self,
        assets: list[dict],
        initial_positions: list[dict],
        prices_df: pd.DataFrame,
    ) -> None:
        # 5/3 は fund_a の価格データなし → 5/1 の 40000 が使われる
        _, snaps = compute_snapshots_for_date(
            target_date=date(2026, 5, 3),
            initial_positions=initial_positions,
            transactions=[],
            assets=assets,
            prices_df=prices_df,
        )
        fund = next(s for s in snaps if s.asset_id == "fund_a")
        # 1,000,000 × 40000 / 10000 = 4,000,000
        assert fund.market_value_jpy == pytest.approx(4_000_000)


class TestComputeDailyPortfolio:
    def test_each_day_in_range(
        self,
        assets: list[dict],
        initial_positions: list[dict],
        prices_df: pd.DataFrame,
    ) -> None:
        daily, by_asset = compute_daily_portfolio(
            initial_positions=initial_positions,
            transactions=[],
            assets=assets,
            prices_df=prices_df,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 3),
        )
        assert [d.date for d in daily] == [
            date(2026, 5, 1),
            date(2026, 5, 2),
            date(2026, 5, 3),
        ]
        # 3 日 × 2 銘柄 = 6 行
        assert len(by_asset) == 6

    def test_purchases_increase_holdings_over_time(
        self,
        assets: list[dict],
        initial_positions: list[dict],
        prices_df: pd.DataFrame,
    ) -> None:
        txs = [
            Transaction(date(2026, 5, 5), "fund_a", 50_000, 42000, 11904.76, "NISA"),
        ]
        daily, by_asset = compute_daily_portfolio(
            initial_positions=initial_positions,
            transactions=txs,
            assets=assets,
            prices_df=prices_df,
            start_date=date(2026, 5, 4),
            end_date=date(2026, 5, 5),
        )
        fund_4 = next(s for s in by_asset if s.date == date(2026, 5, 4) and s.asset_id == "fund_a")
        fund_5 = next(s for s in by_asset if s.date == date(2026, 5, 5) and s.asset_id == "fund_a")
        assert fund_5.quantity > fund_4.quantity
        assert fund_5.book_value_jpy == fund_4.book_value_jpy + 50_000
