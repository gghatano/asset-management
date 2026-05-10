"""E2E (Playwright) 用のフィクスチャ。

生成された HTML を file:// で開く方式。後で実サーバ起動が必要になったら
http_server フィクスチャを追加する。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.build_dashboard import build


@pytest.fixture(scope="session")
def dashboard_url(tmp_path_factory: pytest.TempPathFactory) -> str:
    out_dir = tmp_path_factory.mktemp("dashboard")
    out = out_dir / "index.html"
    build(
        out,
        kpi={
            "current_value_jpy": 5920000,
            "total_invested_jpy": 5860000,
            "profit_loss_jpy": 60000,
            "profit_loss_rate": 0.0102,
        },
    )
    return f"file://{Path(out).resolve()}"
