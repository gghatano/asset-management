"""generate_transactions のユニットテスト。

仕様: docs/spec.md 7.1〜7.3、8.2
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from src.generate_transactions import (
    Transaction,
    _build_transaction,
    generate_transactions,
    iter_purchase_dates,
    jpy_price,
    lookup_price,
)


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


class TestIterPurchaseDates:
    def test_yields_each_month_until_today(self) -> None:
        dates = list(
            iter_purchase_dates(
                start_month="2026-05",
                end_month=None,
                purchase_day=5,
                today=date(2026, 7, 10),
            )
        )
        assert dates == [date(2026, 5, 5), date(2026, 6, 5), date(2026, 7, 5)]

    def test_respects_end_month(self) -> None:
        dates = list(
            iter_purchase_dates(
                start_month="2026-05",
                end_month="2026-06",
                purchase_day=5,
                today=date(2026, 12, 31),
            )
        )
        assert dates == [date(2026, 5, 5), date(2026, 6, 5)]

    def test_no_output_before_start_month(self) -> None:
        dates = list(
            iter_purchase_dates(
                start_month="2027-01",
                end_month=None,
                purchase_day=5,
                today=date(2026, 12, 31),
            )
        )
        assert dates == []

    def test_yields_first_month_when_today_equals_purchase_day(self) -> None:
        dates = list(
            iter_purchase_dates(
                start_month="2026-05",
                end_month=None,
                purchase_day=5,
                today=date(2026, 5, 5),
            )
        )
        assert dates == [date(2026, 5, 5)]

    def test_year_boundary(self) -> None:
        dates = list(
            iter_purchase_dates(
                start_month="2026-11",
                end_month="2027-02",
                purchase_day=10,
                today=date(2027, 12, 31),
            )
        )
        assert dates == [
            date(2026, 11, 10),
            date(2026, 12, 10),
            date(2027, 1, 10),
            date(2027, 2, 10),
        ]


class TestLookupPrice:
    def test_exact_date(self, prices_df: pd.DataFrame) -> None:
        assert lookup_price(prices_df, "fund_a", date(2026, 5, 5)) == 42000.0

    def test_forward_fill_uses_latest_before(self, prices_df: pd.DataFrame) -> None:
        # 5/3 は無いので 5/1 の 40000 が使われる
        assert lookup_price(prices_df, "fund_a", date(2026, 5, 3)) == 40000.0

    def test_no_history_returns_none(self, prices_df: pd.DataFrame) -> None:
        assert lookup_price(prices_df, "unknown", date(2026, 5, 5)) is None


class TestJpyPrice:
    def test_jpy_currency_returns_raw(self, prices_df: pd.DataFrame) -> None:
        assert jpy_price(prices_df, "fund_a", "JPY", date(2026, 5, 5)) == 42000.0

    def test_usd_converts_with_fx(self, prices_df: pd.DataFrame) -> None:
        # 100 USD × 150 (USD/JPY) = 15000 JPY
        assert jpy_price(prices_df, "etf_us", "USD", date(2026, 5, 1)) == 15000.0

    def test_usd_without_fx_returns_none(self) -> None:
        df = pd.DataFrame([{"date": date(2026, 5, 1), "asset_id": "etf_us", "price": 100.0}])
        assert jpy_price(df, "etf_us", "USD", date(2026, 5, 1)) is None


class TestBuildTransactionMutualFund:
    def test_quantity_matches_calculate_helper(self, prices_df: pd.DataFrame) -> None:
        asset = {
            "asset_id": "fund_a",
            "asset_type": "mutual_fund",
            "currency": "JPY",
            "unit_price_base": 10000,
        }
        tx = _build_transaction(asset, 50000, "NISA", date(2026, 5, 5), prices_df)
        assert tx is not None
        # 50000 / 42000 * 10000 = 11904.76...
        assert tx.price == 42000.0
        assert tx.quantity == pytest.approx(50000 / 42000 * 10000)
        assert tx.account_type == "NISA"

    def test_no_price_returns_none(self, prices_df: pd.DataFrame) -> None:
        asset = {
            "asset_id": "fund_b",
            "asset_type": "mutual_fund",
            "currency": "JPY",
            "unit_price_base": 10000,
        }
        assert _build_transaction(asset, 50000, "NISA", date(2026, 5, 5), prices_df) is None


class TestBuildTransactionEtf:
    def test_usd_converted_quantity(self, prices_df: pd.DataFrame) -> None:
        asset = {"asset_id": "etf_us", "asset_type": "etf", "currency": "USD"}
        tx = _build_transaction(asset, 30000, "特定", date(2026, 5, 1), prices_df)
        assert tx is not None
        # JPY price = 100 USD × 150 = 15000、quantity = 30000 / 15000 = 2.0
        assert tx.price == 15000.0
        assert tx.quantity == pytest.approx(2.0)


class TestBuildTransactionCash:
    def test_quantity_equals_amount(self, prices_df: pd.DataFrame) -> None:
        asset = {"asset_id": "cash_jpy", "asset_type": "cash", "currency": "JPY"}
        tx = _build_transaction(asset, 30000, "現金", date(2026, 5, 1), prices_df)
        assert tx is not None
        assert tx.price == 1.0
        assert tx.quantity == 30000.0


class TestGenerateTransactions:
    def test_skips_unknown_asset(self, prices_df: pd.DataFrame) -> None:
        result = generate_transactions(
            assets=[],
            monthly_purchases=[
                {
                    "asset_id": "ghost",
                    "amount_jpy": 1000,
                    "purchase_day": 5,
                    "start_month": "2026-05",
                    "end_month": None,
                    "account_type": "NISA",
                }
            ],
            prices_df=prices_df,
            today=date(2026, 5, 31),
        )
        assert result == []

    def test_combines_multiple_purchases(self, prices_df: pd.DataFrame) -> None:
        assets = [
            {
                "asset_id": "fund_a",
                "asset_type": "mutual_fund",
                "currency": "JPY",
                "unit_price_base": 10000,
            },
            {"asset_id": "cash_jpy", "asset_type": "cash", "currency": "JPY"},
        ]
        purchases = [
            {
                "asset_id": "fund_a",
                "amount_jpy": 50000,
                "purchase_day": 5,
                "start_month": "2026-05",
                "end_month": "2026-05",
                "account_type": "NISA",
            },
            {
                "asset_id": "cash_jpy",
                "amount_jpy": 30000,
                "purchase_day": 25,
                "start_month": "2026-05",
                "end_month": "2026-05",
                "account_type": "現金",
            },
        ]
        result = generate_transactions(assets, purchases, prices_df, date(2026, 5, 31))
        assert len(result) == 2
        assert {t.asset_id for t in result} == {"fund_a", "cash_jpy"}

    def test_returns_transaction_dataclass(self, prices_df: pd.DataFrame) -> None:
        assets = [{"asset_id": "cash_jpy", "asset_type": "cash", "currency": "JPY"}]
        purchases = [
            {
                "asset_id": "cash_jpy",
                "amount_jpy": 30000,
                "purchase_day": 25,
                "start_month": "2026-05",
                "end_month": "2026-05",
                "account_type": "現金",
            }
        ]
        result = generate_transactions(assets, purchases, prices_df, date(2026, 5, 31))
        assert isinstance(result[0], Transaction)
