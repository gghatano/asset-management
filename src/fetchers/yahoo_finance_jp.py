"""Yahoo!ファイナンス（日本）から投資信託の基準価額を取る Fetcher."""

from __future__ import annotations

import re
from datetime import date

from src.fetchers.base import PriceFetcher, PriceFetcherError, PriceQuote

_PRICE_PATTERN = re.compile(r"([0-9][0-9,]*)\s*円")
_TAG_PATTERN = re.compile(r"<[^>]+>")


def _strip_tags(html: str) -> str:
    """HTML タグを取り除いてテキスト断片だけ残す（粗くて良い）."""
    return _TAG_PATTERN.sub(" ", html)


def parse_price_from_html(html: str) -> float:
    """投信ページの HTML から基準価額を抽出する。

    優先順:
    1. 「基準価額」キーワード以降に出てくる最初の「N,NNN 円」
    2. キーワードが無い場合は HTML 全体から「妥当な値」の最初

    抽出できない場合は `PriceFetcherError`。
    """
    text = _strip_tags(html)
    # 「基準価額」以降を優先
    anchor = text.find("基準価額")
    search_target = text[anchor:] if anchor >= 0 else text
    for source in (search_target, text):
        for match in _PRICE_PATTERN.finditer(source):
            raw = match.group(1).replace(",", "")
            try:
                value = float(raw)
            except ValueError:
                continue
            if 1000 <= value <= 1_000_000:
                return value
    raise PriceFetcherError("price not found in Yahoo Finance JP HTML")


def fetch_html(url: str) -> str:
    """Yahoo Finance の HTML を GET する（薄いラッパ）."""
    import requests  # noqa: PLC0415 - 遅延 import

    headers = {
        "User-Agent": ("Mozilla/5.0 (asset-management-tracker; +https://github.com/gghatano)"),
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception as e:  # noqa: BLE001
        raise PriceFetcherError(f"HTTP fetch failed: {e}") from e
    return resp.text


class YahooFinanceJpFetcher(PriceFetcher):
    """投信協会コードで Yahoo!ファイナンスから基準価額を取る."""

    source_name = "yahoo_finance_jp"
    base_url = "https://finance.yahoo.co.jp/quote/{code}"

    def fetch(self, asset: dict, target_date: date) -> PriceQuote:
        url = self.base_url.format(code=asset["source_code"])
        html = fetch_html(url)
        price = parse_price_from_html(html)
        return PriceQuote(
            asset_id=asset["asset_id"],
            date=target_date,
            price=price,
            currency=asset.get("currency", "JPY"),
            source=self.source_name,
        )
