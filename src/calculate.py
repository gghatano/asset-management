"""ポートフォリオ計算の純粋関数群。

仕様: docs/spec.md 「7. 計算ロジック」
"""

from __future__ import annotations


def purchase_quantity_mutual_fund(amount_jpy: float, price: float, unit_base: int = 10000) -> float:
    """投資信託の購入口数。

    >>> purchase_quantity_mutual_fund(50000, 40000)
    12500.0
    """
    if price <= 0:
        raise ValueError("price must be positive")
    return amount_jpy / price * unit_base


def purchase_quantity_etf(amount_jpy: float, price_jpy: float) -> float:
    """ETF / 株式の購入数量。小数株を許容する。"""
    if price_jpy <= 0:
        raise ValueError("price_jpy must be positive")
    return amount_jpy / price_jpy


def market_value_mutual_fund(quantity: float, price: float, unit_base: int = 10000) -> float:
    """投資信託の評価額 = 保有口数 × 基準価額 ÷ unit_base"""
    return quantity * price / unit_base


def market_value_etf(quantity: float, price_jpy: float) -> float:
    """ETF / 株式の評価額 = 保有数量 × 円換算価格"""
    return quantity * price_jpy


def profit_loss(market_value: float, book_value: float) -> tuple[float, float]:
    """評価損益と評価損益率を返す。

    book_value が 0 のときは率は 0 を返す（ゼロ除算回避）。
    """
    pl = market_value - book_value
    rate = pl / book_value if book_value else 0.0
    return pl, rate
