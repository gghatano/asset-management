"""現金など固定価格資産の Fetcher."""

from __future__ import annotations

from datetime import date

from src.fetchers.base import PriceFetcher, PriceQuote


class FixedFetcher(PriceFetcher):
    """価格が常に固定（cash の 1.0 など）の Fetcher.

    `asset["unit_price_base"]` が指定されていればそれを使う。
    現金は 1 JPY = 1 quantity なので、価格は 1.0 を返す。
    """

    source_name = "fixed"

    def fetch(self, asset: dict, target_date: date) -> PriceQuote:
        return PriceQuote(
            asset_id=asset["asset_id"],
            date=target_date,
            price=1.0,
            currency=asset.get("currency", "JPY"),
            source=self.source_name,
        )
