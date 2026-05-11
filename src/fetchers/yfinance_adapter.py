"""yfinance を使った ETF / 株式の Fetcher."""

from __future__ import annotations

from datetime import date, timedelta

from src.fetchers.base import PriceFetcher, PriceFetcherError, PriceQuote


class YFinanceFetcher(PriceFetcher):
    """yfinance.Ticker(...).history で終値を取る."""

    source_name = "yfinance"

    def fetch(self, asset: dict, target_date: date) -> PriceQuote:
        try:
            import yfinance as yf  # noqa: PLC0415 - 遅延 import で起動を軽く
        except ImportError as e:
            raise PriceFetcherError("yfinance is not installed") from e

        ticker = yf.Ticker(asset["source_code"])
        # target_date 当日 ± 数日を引いて最新を採用（休場日対策）
        start = target_date - timedelta(days=5)
        end = target_date + timedelta(days=1)
        try:
            hist = ticker.history(start=start, end=end, auto_adjust=False)
        except Exception as e:  # noqa: BLE001 - yfinance の例外型は不安定なので広く拾う
            raise PriceFetcherError(f"yfinance fetch failed: {e}") from e

        if hist is None or hist.empty:
            raise PriceFetcherError(
                f"yfinance returned empty for {asset['source_code']} @ {target_date}"
            )

        close = float(hist["Close"].iloc[-1])
        return PriceQuote(
            asset_id=asset["asset_id"],
            date=target_date,
            price=close,
            currency=asset.get("currency", "USD"),
            source=self.source_name,
        )
