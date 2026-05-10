"""HTML ダッシュボードを生成する。

現状は最小実装。後続の Issue で portfolio CSV を読み込み、
Plotly でグラフを描画する。
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

DEFAULT_KPI: dict[str, Any] = {
    "current_value_jpy": 0,
    "total_invested_jpy": 0,
    "profit_loss_jpy": 0,
    "profit_loss_rate": 0.0,
}


def render_html(kpi: dict[str, Any] | None = None) -> str:
    kpi = {**DEFAULT_KPI, **(kpi or {})}
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>積立投資 評価額トラッカー</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; }}
    .kpi {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
    }}
    .kpi-card {{ border: 1px solid #ddd; border-radius: 8px; padding: 1rem; }}
    .kpi-label {{ color: #666; font-size: 0.85rem; }}
    .kpi-value {{ font-size: 1.5rem; font-weight: bold; }}
  </style>
</head>
<body>
  <h1>積立投資 評価額トラッカー</h1>
  <section class="kpi" data-testid="kpi">
    <div class="kpi-card">
      <div class="kpi-label">現在評価額</div>
      <div class="kpi-value" data-testid="kpi-current-value">{kpi["current_value_jpy"]:,} 円</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">累計投資額</div>
      <div class="kpi-value" data-testid="kpi-total-invested">{kpi["total_invested_jpy"]:,} 円</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">評価損益</div>
      <div class="kpi-value" data-testid="kpi-profit-loss">{kpi["profit_loss_jpy"]:,} 円</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">評価損益率</div>
      <div class="kpi-value" data-testid="kpi-profit-loss-rate">{kpi["profit_loss_rate"]:.2%}</div>
    </div>
  </section>
  <p data-testid="status">スケルトン版です。実データ反映は後続の Issue で対応します。</p>
</body>
</html>
"""


def build(output_path: Path, kpi: dict[str, Any] | None = None) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_html(kpi), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="ダッシュボード HTML を生成")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("public/index.html"),
        help="出力先 HTML パス",
    )
    args = parser.parse_args()
    build(args.output)


if __name__ == "__main__":
    main()
