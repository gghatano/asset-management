"""月次購入の展開と購入履歴 CSV の生成。

config/monthly_purchases.yaml に基づき、`start_month` から `today` まで
毎月の購入を展開し、purchase_day における価格 (forward fill) を引いて
口数・数量を計算する。

外貨建て (USD など) の場合は prices.csv に格納された為替 asset
(`<currency_lower>_jpy` 例: `usd_jpy`) を利用して JPY 換算する。

仕様: docs/spec.md 7.1〜7.3、8.2
"""

from __future__ import annotations

import argparse
import csv
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.calculate import purchase_quantity_etf, purchase_quantity_mutual_fund
from src.config import load_assets, load_monthly_purchases

logger = logging.getLogger(__name__)

TRANSACTIONS_HEADER = [
    "date",
    "asset_id",
    "amount_jpy",
    "price",
    "quantity",
    "account_type",
]


@dataclass(frozen=True)
class Transaction:
    date: date
    asset_id: str
    amount_jpy: float
    price: float
    quantity: float
    account_type: str


def _parse_month(s: str) -> date:
    """`YYYY-MM` を月初の date に変換する。"""
    return datetime.strptime(s, "%Y-%m").date()


def _next_month(d: date) -> date:
    """同じ日付で翌月に進める。"""
    if d.month == 12:
        return d.replace(year=d.year + 1, month=1)
    return d.replace(month=d.month + 1)


def iter_purchase_dates(
    start_month: str,
    end_month: str | None,
    purchase_day: int,
    today: date,
) -> Iterator[date]:
    """`start_month` から `today` まで、毎月 `purchase_day` 日付を yield する。

    end_month が指定されたら、その月までを含む。
    purchase_day は 1〜28 を想定する（spec の運用ルール）。
    """
    start = _parse_month(start_month).replace(day=purchase_day)
    end_limit = _parse_month(end_month).replace(day=purchase_day) if end_month else None
    current = start
    while current <= today:
        if end_limit is not None and current > end_limit:
            break
        yield current
        current = _next_month(current)


def lookup_price(prices_df: pd.DataFrame, asset_id: str, target_date: date) -> float | None:
    """asset_id について target_date 以前で最新の価格 (forward fill)。

    無ければ None を返す。
    """
    matched = prices_df[(prices_df["asset_id"] == asset_id) & (prices_df["date"] <= target_date)]
    if matched.empty:
        return None
    return float(matched.sort_values("date").iloc[-1]["price"])


def jpy_price(
    prices_df: pd.DataFrame,
    asset_id: str,
    currency: str,
    target_date: date,
) -> float | None:
    """円換算後の価格を返す。

    JPY なら raw 価格をそのまま、それ以外は `<currency>_jpy` の為替で換算。
    為替が取得できない場合は None。
    """
    raw = lookup_price(prices_df, asset_id, target_date)
    if raw is None:
        return None
    if currency.upper() == "JPY":
        return raw
    fx_id = f"{currency.lower()}_jpy"
    fx = lookup_price(prices_df, fx_id, target_date)
    if fx is None:
        return None
    return raw * fx


def generate_transactions(
    assets: list[dict[str, Any]],
    monthly_purchases: list[dict[str, Any]],
    prices_df: pd.DataFrame,
    today: date,
) -> list[Transaction]:
    """月次購入設定を元に Transaction を展開する。

    価格未取得・為替未取得の購入はログ警告のうえ skip。
    """
    asset_by_id = {a["asset_id"]: a for a in assets}
    transactions: list[Transaction] = []
    for p in monthly_purchases:
        asset = asset_by_id.get(p["asset_id"])
        if asset is None:
            logger.warning("asset_id=%s が assets.yaml に無い。skip", p["asset_id"])
            continue
        amount = float(p["amount_jpy"])
        purchase_day = int(p["purchase_day"])
        account_type = p["account_type"]
        for d in iter_purchase_dates(p["start_month"], p["end_month"], purchase_day, today):
            tx = _build_transaction(asset, amount, account_type, d, prices_df)
            if tx is not None:
                transactions.append(tx)
    return transactions


def _build_transaction(
    asset: dict[str, Any],
    amount_jpy: float,
    account_type: str,
    purchase_date: date,
    prices_df: pd.DataFrame,
) -> Transaction | None:
    asset_type = asset["asset_type"]
    asset_id = asset["asset_id"]
    currency = asset.get("currency", "JPY")

    if asset_type == "cash":
        return Transaction(
            date=purchase_date,
            asset_id=asset_id,
            amount_jpy=amount_jpy,
            price=1.0,
            quantity=amount_jpy,
            account_type=account_type,
        )

    if asset_type == "mutual_fund":
        price = lookup_price(prices_df, asset_id, purchase_date)
        if price is None:
            logger.warning("%s の %s 時点価格なし。skip", asset_id, purchase_date.isoformat())
            return None
        unit_base = int(asset.get("unit_price_base", 10000))
        quantity = purchase_quantity_mutual_fund(amount_jpy, price, unit_base)
        return Transaction(
            date=purchase_date,
            asset_id=asset_id,
            amount_jpy=amount_jpy,
            price=price,
            quantity=quantity,
            account_type=account_type,
        )

    if asset_type in ("etf", "stock"):
        price_jpy = jpy_price(prices_df, asset_id, currency, purchase_date)
        if price_jpy is None:
            logger.warning(
                "%s の %s 時点 JPY 換算価格なし。skip",
                asset_id,
                purchase_date.isoformat(),
            )
            return None
        quantity = purchase_quantity_etf(amount_jpy, price_jpy)
        return Transaction(
            date=purchase_date,
            asset_id=asset_id,
            amount_jpy=amount_jpy,
            price=price_jpy,
            quantity=quantity,
            account_type=account_type,
        )

    logger.warning("未対応の asset_type=%s (asset_id=%s)。skip", asset_type, asset_id)
    return None


def write_transactions_csv(transactions: list[Transaction], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(TRANSACTIONS_HEADER)
        for t in sorted(transactions, key=lambda x: (x.date, x.asset_id)):
            writer.writerow(
                [
                    t.date.isoformat(),
                    t.asset_id,
                    int(t.amount_jpy),
                    _format_number(t.price),
                    _format_number(t.quantity),
                    t.account_type,
                ]
            )


def _format_number(v: float) -> str:
    """末尾の余分な 0 を落として書き出す。"""
    if float(v).is_integer():
        return str(int(v))
    return f"{v:.4f}".rstrip("0").rstrip(".")


def load_prices_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="月次購入履歴 CSV を生成")
    parser.add_argument(
        "--today",
        type=date.fromisoformat,
        default=date.today(),
        help="計算上の today (YYYY-MM-DD)",
    )
    parser.add_argument("--config-dir", type=Path, default=Path("config"))
    parser.add_argument("--prices", type=Path, default=Path("data/prices/prices.csv"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/transactions/generated_purchases.csv"),
    )
    args = parser.parse_args()

    assets = load_assets(args.config_dir)
    monthly_purchases = load_monthly_purchases(args.config_dir)
    prices_df = load_prices_csv(args.prices)
    transactions = generate_transactions(assets, monthly_purchases, prices_df, args.today)
    write_transactions_csv(transactions, args.output)
    logger.info("%d 行を %s に書き出しました", len(transactions), args.output)


if __name__ == "__main__":
    main()
