"""calculate_portfolio のインテグレーションテスト。"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import pytest
import yaml

from src.calculate_portfolio import (
    compute_daily_portfolio,
    load_transactions_csv,
    write_by_asset_csv,
    write_daily_csv,
)
from src.generate_transactions import load_prices_csv


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
    (cfg / "initial_positions.yaml").write_text(
        yaml.safe_dump(
            {
                "as_of": "2026-05-01",
                "positions": [
                    {
                        "asset_id": "fund_a",
                        "quantity": 1_000_000,
                        "quantity_unit": "口",
                        "book_value_jpy": 4_000_000,
                    },
                    {
                        "asset_id": "cash_jpy",
                        "quantity": 100_000,
                        "quantity_unit": "円",
                        "book_value_jpy": 100_000,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    (cfg / "monthly_purchases.yaml").write_text(
        yaml.safe_dump({"monthly_purchases": []}), encoding="utf-8"
    )
    return cfg


@pytest.fixture
def sample_prices_csv(tmp_path: Path) -> Path:
    p = tmp_path / "prices.csv"
    p.write_text(
        "date,asset_id,price,currency,source\n"
        "2026-05-01,fund_a,40000,JPY,fixed\n"
        "2026-05-02,fund_a,41000,JPY,fixed\n"
        "2026-05-03,fund_a,42000,JPY,fixed\n",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def sample_transactions_csv(tmp_path: Path) -> Path:
    p = tmp_path / "tx.csv"
    p.write_text(
        "date,asset_id,amount_jpy,price,quantity,account_type\n"
        "2026-05-02,fund_a,50000,41000,12195.12,NISA\n",
        encoding="utf-8",
    )
    return p


def test_pipeline_writes_two_csvs(
    sample_config_dir: Path,
    sample_prices_csv: Path,
    sample_transactions_csv: Path,
    tmp_path: Path,
) -> None:
    from src.config import load_assets, load_initial_positions

    assets = load_assets(sample_config_dir)
    initial = load_initial_positions(sample_config_dir)["positions"]
    transactions = load_transactions_csv(sample_transactions_csv)
    prices_df = load_prices_csv(sample_prices_csv)

    daily, by_asset = compute_daily_portfolio(
        initial, transactions, assets, prices_df, date(2026, 5, 1), date(2026, 5, 3)
    )
    daily_csv = tmp_path / "daily.csv"
    by_asset_csv = tmp_path / "by_asset.csv"
    write_daily_csv(daily, daily_csv)
    write_by_asset_csv(by_asset, by_asset_csv)

    # daily.csv: header + 3 行
    daily_rows = list(csv.DictReader(daily_csv.open(encoding="utf-8")))
    assert [r["date"] for r in daily_rows] == [
        "2026-05-01",
        "2026-05-02",
        "2026-05-03",
    ]

    # 5/1: fund_a 1e6 × 40000/10000 = 4e6 + cash 100,000 = 4,100,000、簿価 4,100,000
    d1 = daily_rows[0]
    assert d1["total_market_value_jpy"] == "4100000"
    assert d1["total_book_value_jpy"] == "4100000"
    assert d1["profit_loss_jpy"] == "0"

    # 5/2: fund_a (1e6 + 12195.12) × 41000/10000 + cash 100,000
    d2 = daily_rows[1]
    expected_fund_5_2 = (1_000_000 + 12195.12) * 41000 / 10000
    assert float(d2["total_market_value_jpy"]) == pytest.approx(expected_fund_5_2 + 100_000, abs=1)

    # by_asset.csv: 3日 × 2銘柄 = 6 行
    ba_rows = list(csv.DictReader(by_asset_csv.open(encoding="utf-8")))
    assert len(ba_rows) == 6
    # weight 検算: 5/1 fund_a の weight = 4,000,000 / 4,100,000 ≈ 0.9756
    fund_5_1 = next(r for r in ba_rows if r["date"] == "2026-05-01" and r["asset_id"] == "fund_a")
    assert float(fund_5_1["weight"]) == pytest.approx(4_000_000 / 4_100_000, abs=0.001)


def test_csv_headers(
    sample_config_dir: Path,
    sample_prices_csv: Path,
    sample_transactions_csv: Path,
    tmp_path: Path,
) -> None:
    from src.config import load_assets, load_initial_positions

    assets = load_assets(sample_config_dir)
    initial = load_initial_positions(sample_config_dir)["positions"]
    transactions = load_transactions_csv(sample_transactions_csv)
    prices_df = load_prices_csv(sample_prices_csv)
    daily, by_asset = compute_daily_portfolio(
        initial, transactions, assets, prices_df, date(2026, 5, 1), date(2026, 5, 1)
    )
    daily_csv = tmp_path / "daily.csv"
    by_asset_csv = tmp_path / "by_asset.csv"
    write_daily_csv(daily, daily_csv)
    write_by_asset_csv(by_asset, by_asset_csv)

    assert daily_csv.read_text(encoding="utf-8").splitlines()[0] == (
        "date,total_book_value_jpy,total_market_value_jpy,profit_loss_jpy,profit_loss_rate"
    )
    assert by_asset_csv.read_text(encoding="utf-8").splitlines()[0] == (
        "date,asset_id,quantity,book_value_jpy,market_value_jpy,profit_loss_jpy,weight"
    )
