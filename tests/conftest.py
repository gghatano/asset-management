"""プロジェクト共通の pytest フィクスチャ。"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def repo_root() -> Path:
    return ROOT


@pytest.fixture
def config_dir() -> Path:
    return ROOT / "config"


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).resolve().parent / "fixtures"
