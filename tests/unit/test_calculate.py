"""src.calculate のユニットテスト。

仕様: docs/spec.md 「7. 計算ロジック」
"""

from __future__ import annotations

import pytest

from src.calculate import (
    market_value_etf,
    market_value_mutual_fund,
    profit_loss,
    purchase_quantity_etf,
    purchase_quantity_mutual_fund,
)


class TestPurchaseQuantityMutualFund:
    def test_spec_example(self) -> None:
        # spec 7.1: 50,000 / 40,000 * 10,000 = 12,500
        assert purchase_quantity_mutual_fund(50000, 40000) == 12500.0

    def test_real_price(self) -> None:
        # 50,000 / 42,272 * 10,000 ≈ 11,828.16
        # NOTE: spec 8.2 のサンプル値 11828.38 は spec 側の丸め誤差。
        # 計算結果（実測 11828.16）を正とする。
        assert purchase_quantity_mutual_fund(50000, 42272) == pytest.approx(11828.16, abs=0.01)

    def test_zero_price_raises(self) -> None:
        with pytest.raises(ValueError):
            purchase_quantity_mutual_fund(50000, 0)


class TestPurchaseQuantityEtf:
    def test_basic(self) -> None:
        assert purchase_quantity_etf(20000, 20000) == 1.0

    def test_fractional(self) -> None:
        assert purchase_quantity_etf(20000, 18000) == pytest.approx(20000 / 18000)

    def test_zero_price_raises(self) -> None:
        with pytest.raises(ValueError):
            purchase_quantity_etf(20000, 0)


class TestMarketValueMutualFund:
    def test_spec_example(self) -> None:
        # spec 8.4: 1,200,000 口 × 42,272 / 10,000 = 5,072,640
        assert market_value_mutual_fund(1200000, 42272) == pytest.approx(5072640)


class TestMarketValueEtf:
    def test_basic(self) -> None:
        # 20 株 × 18,000 円 = 360,000 円
        assert market_value_etf(20, 18000) == 360000


class TestProfitLoss:
    def test_positive(self) -> None:
        # spec 8.3: 5,920,000 - 5,860,000 = 60,000、率 ≈ 0.0102
        pl, rate = profit_loss(5920000, 5860000)
        assert pl == 60000
        assert rate == pytest.approx(0.0102, abs=0.0001)

    def test_negative(self) -> None:
        pl, rate = profit_loss(900, 1000)
        assert pl == -100
        assert rate == pytest.approx(-0.1)

    def test_zero_book_value(self) -> None:
        pl, rate = profit_loss(100, 0)
        assert pl == 100
        assert rate == 0.0
