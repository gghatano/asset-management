"""日次ポートフォリオ評価。

初期保有 + 累積購入から、日付ごとの数量・簿価・評価額・損益を計算し、
2 種類の CSV (portfolio_daily.csv / portfolio_by_asset.csv) に書き出す。

仕様: docs/spec.md 7.4, 7.5, 8.3, 8.4
"""

from __future__ import annotations

import argparse
import csv
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from src.calculate import market_value_etf, market_value_mutual_fund, profit_loss
from src.config import load_assets, load_initial_positions
from src.generate_transactions import (
    Transaction,
    jpy_price,
    load_prices_csv,
    lookup_price,
)

logger = logging.getLogger(__name__)

DAILY_HEADER = [
    "date",
    "total_book_value_jpy",
    "total_market_value_jpy",
    "profit_loss_jpy",
    "profit_loss_rate",
]
BY_ASSET_HEADER = [
    "date",
    "asset_id",
    "quantity",
    "book_value_jpy",
    "market_value_jpy",
    "profit_loss_jpy",
    "weight",
]


@dataclass(frozen=True)
class AssetSnapshot:
    date: date
    asset_id: str
    quantity: float
    book_value_jpy: float
    market_value_jpy: float
    profit_loss_jpy: float
    weight: float


@dataclass(frozen=True)
class DailySnapshot:
    date: date
    total_book_value_jpy: float
    total_market_value_jpy: float
    profit_loss_jpy: float
    profit_loss_rate: float


def date_range(start: date, end: date) -> Iterator[date]:
    """[start, end] inclusive のすべての日付を yield"""
    current = start
    while current <= end:
        yield current
        current = current + timedelta(days=1)


def compute_holdings(
    initial_positions: list[dict[str, Any]],
    transactions: list[Transaction],
    target_date: date,
) -> dict[str, dict[str, float]]:
    """target_date 時点の各 asset の {quantity, book_value_jpy}。"""
    holdings: dict[str, dict[str, float]] = {}
    for pos in initial_positions:
        holdings[pos["asset_id"]] = {
            "quantity": float(pos["quantity"]),
            "book_value_jpy": float(pos["book_value_jpy"]),
        }
    for tx in transactions:
        if tx.date > target_date:
            continue
        h = holdings.setdefault(tx.asset_id, {"quantity": 0.0, "book_value_jpy": 0.0})
        h["quantity"] += tx.quantity
        h["book_value_jpy"] += tx.amount_jpy
    return holdings


def compute_market_value(
    asset: dict[str, Any],
    quantity: float,
    prices_df: pd.DataFrame,
    target_date: date,
) -> float | None:
    """JPY 換算後の評価額。価格未取得は None。"""
    asset_type = asset.get("asset_type", "mutual_fund")
    currency = asset.get("currency", "JPY")
    asset_id = asset["asset_id"]

    if asset_type == "cash":
        return quantity  # 1 円 = 1 円

    if asset_type == "mutual_fund":
        price = lookup_price(prices_df, asset_id, target_date)
        if price is None:
            return None
        unit_base = int(asset.get("unit_price_base", 10000))
        return market_value_mutual_fund(quantity, price, unit_base)

    if asset_type in ("etf", "stock"):
        price_jpy = jpy_price(prices_df, asset_id, currency, target_date)
        if price_jpy is None:
            return None
        return market_value_etf(quantity, price_jpy)

    return None


def compute_snapshots_for_date(
    target_date: date,
    initial_positions: list[dict[str, Any]],
    transactions: list[Transaction],
    assets: list[dict[str, Any]],
    prices_df: pd.DataFrame,
) -> tuple[DailySnapshot, list[AssetSnapshot]]:
    """指定日の DailySnapshot と AssetSnapshot 一覧を返す。

    market_value が取れない asset は 0 として扱う（ログ警告）。
    weight は market_value 合計に対する比。合計 0 の場合は 0。
    """
    asset_by_id = {a["asset_id"]: a for a in assets}
    holdings = compute_holdings(initial_positions, transactions, target_date)

    raw: list[tuple[str, float, float, float]] = []
    # (asset_id, quantity, book_value, market_value)
    for asset_id, h in holdings.items():
        asset = asset_by_id.get(asset_id)
        if asset is None:
            logger.warning("asset_id=%s が assets.yaml に無い。market_value=0", asset_id)
            mv = 0.0
        else:
            mv_opt = compute_market_value(asset, h["quantity"], prices_df, target_date)
            if mv_opt is None:
                logger.warning(
                    "%s の %s 時点 market_value 取得不可。0 として扱う",
                    asset_id,
                    target_date.isoformat(),
                )
                mv = 0.0
            else:
                mv = mv_opt
        raw.append((asset_id, h["quantity"], h["book_value_jpy"], mv))

    total_market = sum(mv for _, _, _, mv in raw)
    total_book = sum(bv for _, _, bv, _ in raw)
    pl, pl_rate = profit_loss(total_market, total_book)

    asset_snapshots = [
        AssetSnapshot(
            date=target_date,
            asset_id=asset_id,
            quantity=quantity,
            book_value_jpy=book_value,
            market_value_jpy=mv,
            profit_loss_jpy=mv - book_value,
            weight=(mv / total_market) if total_market else 0.0,
        )
        for asset_id, quantity, book_value, mv in raw
    ]

    daily = DailySnapshot(
        date=target_date,
        total_book_value_jpy=total_book,
        total_market_value_jpy=total_market,
        profit_loss_jpy=pl,
        profit_loss_rate=pl_rate,
    )
    return daily, asset_snapshots


def compute_daily_portfolio(
    initial_positions: list[dict[str, Any]],
    transactions: list[Transaction],
    assets: list[dict[str, Any]],
    prices_df: pd.DataFrame,
    start_date: date,
    end_date: date,
) -> tuple[list[DailySnapshot], list[AssetSnapshot]]:
    """日付範囲分の snapshot を返す。"""
    daily_list: list[DailySnapshot] = []
    asset_list: list[AssetSnapshot] = []
    for d in date_range(start_date, end_date):
        daily, snaps = compute_snapshots_for_date(
            d, initial_positions, transactions, assets, prices_df
        )
        daily_list.append(daily)
        asset_list.extend(snaps)
    return daily_list, asset_list


def write_daily_csv(snapshots: list[DailySnapshot], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(DAILY_HEADER)
        for s in snapshots:
            writer.writerow(
                [
                    s.date.isoformat(),
                    _format_money(s.total_book_value_jpy),
                    _format_money(s.total_market_value_jpy),
                    _format_money(s.profit_loss_jpy),
                    f"{s.profit_loss_rate:.4f}",
                ]
            )


def write_by_asset_csv(snapshots: list[AssetSnapshot], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(BY_ASSET_HEADER)
        for s in sorted(snapshots, key=lambda x: (x.date, x.asset_id)):
            writer.writerow(
                [
                    s.date.isoformat(),
                    s.asset_id,
                    _format_quantity(s.quantity),
                    _format_money(s.book_value_jpy),
                    _format_money(s.market_value_jpy),
                    _format_money(s.profit_loss_jpy),
                    f"{s.weight:.4f}",
                ]
            )


def _format_money(v: float) -> str:
    """金額: 整数なら整数で、小数なら 2 桁に丸めて文字列化。"""
    if float(v).is_integer():
        return str(int(v))
    return f"{v:.2f}"


def _format_quantity(v: float) -> str:
    if float(v).is_integer():
        return str(int(v))
    return f"{v:.4f}".rstrip("0").rstrip(".")


def load_transactions_csv(path: Path) -> list[Transaction]:
    if not path.exists():
        return []
    transactions: list[Transaction] = []
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            transactions.append(
                Transaction(
                    date=datetime.strptime(row["date"], "%Y-%m-%d").date(),
                    asset_id=row["asset_id"],
                    amount_jpy=float(row["amount_jpy"]),
                    price=float(row["price"]),
                    quantity=float(row["quantity"]),
                    account_type=row["account_type"],
                )
            )
    return transactions


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="日次ポートフォリオ評価 CSV を生成")
    parser.add_argument(
        "--start",
        type=date.fromisoformat,
        default=None,
        help="開始日 (YYYY-MM-DD)。未指定時は initial_positions.yaml の as_of",
    )
    parser.add_argument(
        "--end",
        type=date.fromisoformat,
        default=date.today(),
        help="終了日 (YYYY-MM-DD)。デフォルト today",
    )
    parser.add_argument("--config-dir", type=Path, default=Path("config"))
    parser.add_argument(
        "--transactions",
        type=Path,
        default=Path("data/transactions/generated_purchases.csv"),
    )
    parser.add_argument("--prices", type=Path, default=Path("data/prices/prices.csv"))
    parser.add_argument(
        "--daily-output",
        type=Path,
        default=Path("data/portfolio/portfolio_daily.csv"),
    )
    parser.add_argument(
        "--by-asset-output",
        type=Path,
        default=Path("data/portfolio/portfolio_by_asset.csv"),
    )
    args = parser.parse_args()

    assets = load_assets(args.config_dir)
    initial = load_initial_positions(args.config_dir)
    initial_positions = initial["positions"]
    as_of = datetime.strptime(initial["as_of"], "%Y-%m-%d").date()
    start = args.start or as_of

    transactions = load_transactions_csv(args.transactions)
    prices_df = load_prices_csv(args.prices)

    daily, by_asset = compute_daily_portfolio(
        initial_positions, transactions, assets, prices_df, start, args.end
    )
    write_daily_csv(daily, args.daily_output)
    write_by_asset_csv(by_asset, args.by_asset_output)
    logger.info(
        "%d 日分を %s と %s に書き出しました",
        len(daily),
        args.daily_output,
        args.by_asset_output,
    )


if __name__ == "__main__":
    main()
