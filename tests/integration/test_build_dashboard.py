"""build_dashboard のインテグレーションテスト（ブラウザなし）。"""

from __future__ import annotations

from pathlib import Path

from src.build_dashboard import build, render_html


def test_render_html_contains_title() -> None:
    html = render_html()
    assert "積立投資 評価額トラッカー" in html
    assert 'data-testid="kpi"' in html


def test_render_html_formats_kpi() -> None:
    html = render_html(
        {
            "current_value_jpy": 5920000,
            "total_invested_jpy": 5860000,
            "profit_loss_jpy": 60000,
            "profit_loss_rate": 0.0102,
        }
    )
    assert "5,920,000" in html
    assert "60,000" in html
    assert "1.02%" in html


def test_build_writes_file(tmp_path: Path) -> None:
    out = tmp_path / "public" / "index.html"
    result = build(out)
    assert result == out
    assert out.exists()
    assert "積立投資" in out.read_text(encoding="utf-8")
