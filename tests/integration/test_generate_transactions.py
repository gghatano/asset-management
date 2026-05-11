"""generate_transactions のインテグレーションテスト。

サンプル config + 価格 CSV を入力に、期待 CSV と一致するか検証。
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import pytest
import yaml

from src.generate_transactions import (
    generate_transactions,
    load_prices_csv,
    write_transactions_csv,
)


@pytest.fixture
def sample_config_dir(tmp_path: Path) -> Path:
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "assets.yaml").write_text(
        yaml.safe_dump(
            {
                "assets": [
                    {
                        "asset_id": "fund_a",
                        "name": "Fund A",
                        "asset_type": "mutual_fund",
                        "currency": "JPY",
                        "price_source": "fixed",
                        "source_code": "A",
                        "unit_price_base": 10000,
                        "enabled": True,
                    },
                    {
                        "asset_id": "etf_us",
                        "name": "ETF US",
                        "asset_type": "etf",
                        "currency": "USD",
                        "price_source": "yfinance",
                        "source_code": "US",
                        "unit_price_base": 1,
                        "enabled": True,
                    },
                    {
                        "asset_id": "cash_jpy",
                        "name": "現金",
                        "asset_type": "cash",
                        "currency": "JPY",
                        "price_source": "fixed",
                        "source_code": "JPY",
                        "unit_price_base": 1,
                        "enabled": True,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    (cfg / "monthly_purchases.yaml").write_text(
        yaml.safe_dump(
            {
                "monthly_purchases": [
                    {
                        "asset_id": "fund_a",
                        "amount_jpy": 50000,
                        "purchase_day": 5,
                        "start_month": "2026-05",
                        "end_month": "2026-06",
                        "account_type": "NISA",
                    },
                    {
                        "asset_id": "etf_us",
                        "amount_jpy": 30000,
                        "purchase_day": 10,
                        "start_month": "2026-05",
                        "end_month": "2026-05",
                        "account_type": "特定",
                    },
                    {
                        "asset_id": "cash_jpy",
                        "amount_jpy": 20000,
                        "purchase_day": 25,
                        "start_month": "2026-05",
                        "end_month": "2026-05",
                        "account_type": "現金",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    (cfg / "initial_positions.yaml").write_text(
        yaml.safe_dump({"as_of": "2026-05-01", "positions": []}), encoding="utf-8"
    )
    return cfg


@pytest.fixture
def sample_prices_csv(tmp_path: Path) -> Path:
    prices = tmp_path / "prices.csv"
    prices.write_text(
        "date,asset_id,price,currency,source\n"
        "2026-05-01,fund_a,40000,JPY,fixed\n"
        "2026-05-05,fund_a,42000,JPY,fixed\n"
        "2026-06-05,fund_a,43000,JPY,fixed\n"
        "2026-05-10,etf_us,100,USD,yfinance\n"
        "2026-05-10,usd_jpy,150,JPY,yfinance\n",
        encoding="utf-8",
    )
    return prices


def test_pipeline_writes_expected_csv(
    sample_config_dir: Path, sample_prices_csv: Path, tmp_path: Path
) -> None:
    from src.config import load_assets, load_monthly_purchases

    assets = load_assets(sample_config_dir)
    purchases = load_monthly_purchases(sample_config_dir)
    prices_df = load_prices_csv(sample_prices_csv)

    transactions = generate_transactions(assets, purchases, prices_df, date(2026, 6, 30))

    output = tmp_path / "transactions.csv"
    write_transactions_csv(transactions, output)

    rows = list(csv.DictReader(output.open(encoding="utf-8")))
    by_key = {(r["date"], r["asset_id"]): r for r in rows}

    # fund_a 5/5 (40000... 5/1 forward fill ではなく 5/5 の 42000)
    fund_5_5 = by_key[("2026-05-05", "fund_a")]
    assert fund_5_5["amount_jpy"] == "50000"
    assert fund_5_5["price"] == "42000"
    # 50000 / 42000 * 10000 = 11904.7619... → "11904.7619"
    assert fund_5_5["quantity"].startswith("11904")

    # fund_a 6/5
    fund_6_5 = by_key[("2026-06-05", "fund_a")]
    assert fund_6_5["price"] == "43000"

    # etf_us 5/10: 100 USD * 150 JPY = 15000 JPY、quantity 30000 / 15000 = 2
    etf = by_key[("2026-05-10", "etf_us")]
    assert etf["price"] == "15000"
    assert etf["quantity"] == "2"
    assert etf["account_type"] == "特定"

    # cash_jpy 5/25
    cash = by_key[("2026-05-25", "cash_jpy")]
    assert cash["price"] == "1"
    assert cash["quantity"] == "20000"


def test_csv_has_header(sample_config_dir: Path, sample_prices_csv: Path, tmp_path: Path) -> None:
    from src.config import load_assets, load_monthly_purchases

    assets = load_assets(sample_config_dir)
    purchases = load_monthly_purchases(sample_config_dir)
    prices_df = load_prices_csv(sample_prices_csv)
    transactions = generate_transactions(assets, purchases, prices_df, date(2026, 6, 30))
    output = tmp_path / "out.csv"
    write_transactions_csv(transactions, output)
    first_line = output.read_text(encoding="utf-8").splitlines()[0]
    assert first_line == "date,asset_id,amount_jpy,price,quantity,account_type"
