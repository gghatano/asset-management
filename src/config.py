"""config/*.yaml の読み込み。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_assets(config_dir: Path) -> list[dict[str, Any]]:
    return _load_yaml(config_dir / "assets.yaml")["assets"]


def load_initial_positions(config_dir: Path) -> dict[str, Any]:
    return _load_yaml(config_dir / "initial_positions.yaml")


def load_monthly_purchases(config_dir: Path) -> list[dict[str, Any]]:
    return _load_yaml(config_dir / "monthly_purchases.yaml")["monthly_purchases"]
