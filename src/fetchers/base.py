"""価格取得アダプタの抽象基底。

各 `price_source` (yfinance / yahoo_finance_jp / fixed / ...) ごとに
このクラスを継承して `fetch` を実装する。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class PriceQuote:
    """1 銘柄・1 日の価格."""

    asset_id: str
    date: date
    price: float
    currency: str
    source: str


class PriceFetcherError(Exception):
    """価格取得に失敗したことを表す例外."""


class PriceFetcher(ABC):
    """価格取得アダプタの共通インターフェイス."""

    source_name: str = ""

    @abstractmethod
    def fetch(self, asset: dict, target_date: date) -> PriceQuote:
        """1 銘柄分の価格を取得する。

        失敗時は `PriceFetcherError` を送出する（呼び出し側でフォールバック）。
        """
        raise NotImplementedError
