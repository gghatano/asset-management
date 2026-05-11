"""価格取得バッチのエントリポイント。

config/assets.yaml に登録された全銘柄について価格を取得し、
data/prices/prices.csv に追記する。失敗時は前回値をフォールバック。
"""

from __future__ import annotations

import argparse
import csv
import logging
from collections.abc import Iterable
from datetime import date as date_type
from datetime import datetime
from pathlib import Path

from src.config import load_assets
from src.fetchers.base import PriceFetcherError, PriceQuote
from src.fetchers.factory import get_fetcher

logger = logging.getLogger(__name__)

PRICES_HEADER = ["date", "asset_id", "price", "currency", "source"]


def load_existing_prices(csv_path: Path) -> list[dict]:
    """既存の prices.csv を読み込む。無ければ空."""
    if not csv_path.exists():
        return []
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def last_price_for(rows: list[dict], asset_id: str) -> dict | None:
    """asset_id に対する最新行を返す（date 降順）."""
    matched = [r for r in rows if r["asset_id"] == asset_id]
    if not matched:
        return None
    return max(matched, key=lambda r: r["date"])


def fetch_one(
    asset: dict,
    target_date: date_type,
    existing_rows: list[dict],
) -> PriceQuote:
    """1 銘柄分の価格を取得。失敗時は前回値を使う."""
    fetcher = get_fetcher(asset["price_source"])
    try:
        return fetcher.fetch(asset, target_date)
    except PriceFetcherError as e:
        logger.warning("fetch failed for %s: %s", asset["asset_id"], e)
        prev = last_price_for(existing_rows, asset["asset_id"])
        if prev is None:
            raise
        logger.info("falling back to previous price for %s: %s", asset["asset_id"], prev)
        return PriceQuote(
            asset_id=asset["asset_id"],
            date=target_date,
            price=float(prev["price"]),
            currency=prev["currency"],
            source=f"{prev['source']}+fallback",
        )


def append_quotes(csv_path: Path, quotes: Iterable[PriceQuote]) -> None:
    """価格 CSV に追記する。ファイルが無ければヘッダ付きで作成."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not csv_path.exists()
    with csv_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(PRICES_HEADER)
        for q in quotes:
            writer.writerow([q.date.isoformat(), q.asset_id, q.price, q.currency, q.source])


def run(
    config_dir: Path,
    csv_path: Path,
    target_date: date_type,
) -> list[PriceQuote]:
    """全銘柄の取得と CSV 追記を 1 ジョブ走らせる."""
    assets = [a for a in load_assets(config_dir) if a.get("enabled", True)]
    existing = load_existing_prices(csv_path)
    quotes: list[PriceQuote] = []
    for asset in assets:
        try:
            q = fetch_one(asset, target_date, existing)
        except PriceFetcherError as e:
            logger.error("could not fetch nor fallback for %s: %s", asset["asset_id"], e)
            continue
        quotes.append(q)
    append_quotes(csv_path, quotes)
    return quotes


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="価格を取得して CSV に追記する")
    parser.add_argument("--date", type=str, default=None, help="YYYY-MM-DD 形式")
    parser.add_argument(
        "--config-dir", type=Path, default=Path("config"), help="config ディレクトリ"
    )
    parser.add_argument(
        "--csv", type=Path, default=Path("data/prices/prices.csv"), help="出力 CSV パス"
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = _parse_args()
    target = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date_type.today()
    quotes = run(args.config_dir, args.csv, target)
    logger.info("wrote %d rows to %s", len(quotes), args.csv)


if __name__ == "__main__":
    main()
