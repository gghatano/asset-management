"""src.config のテスト。"""

from __future__ import annotations

from pathlib import Path

from src.config import load_assets, load_initial_positions, load_monthly_purchases


def test_load_assets_returns_list(config_dir: Path) -> None:
    assets = load_assets(config_dir)
    assert isinstance(assets, list)
    assert len(assets) >= 1
    asset_ids = {a["asset_id"] for a in assets}
    assert "emaxis_slim_sp500" in asset_ids


def test_load_assets_required_fields(config_dir: Path) -> None:
    required = {"asset_id", "name", "asset_type", "currency", "price_source"}
    for asset in load_assets(config_dir):
        missing = required - asset.keys()
        assert not missing, f"{asset.get('asset_id')} に欠落フィールド: {missing}"


def test_load_initial_positions(config_dir: Path) -> None:
    payload = load_initial_positions(config_dir)
    assert "as_of" in payload
    assert "positions" in payload
    assert isinstance(payload["positions"], list)


def test_load_monthly_purchases(config_dir: Path) -> None:
    purchases = load_monthly_purchases(config_dir)
    assert isinstance(purchases, list)
    for p in purchases:
        assert 1 <= p["purchase_day"] <= 28, "purchase_day は 1〜28 にする"
