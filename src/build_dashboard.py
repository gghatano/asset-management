"""HTML ダッシュボードを生成する。

`data/portfolio/portfolio_daily.csv` と `data/portfolio/portfolio_by_asset.csv`
を読み込み、KPI + Plotly のグラフ + 各種テーブルを `public/index.html` に
出力する。各セクションには E2E 用に `data-testid` を付ける。

仕様: docs/spec.md 第9節
"""

from __future__ import annotations

import argparse
import logging
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go

from src.config import load_assets, load_monthly_purchases

logger = logging.getLogger(__name__)


DEFAULT_KPI: dict[str, Any] = {
    "current_value_jpy": 0,
    "total_invested_jpy": 0,
    "profit_loss_jpy": 0,
    "profit_loss_rate": 0.0,
    "monthly_purchase_jpy": 0,
}

PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.2.min.js"

# Finance/fintech 系の落ち着いた配色
COLOR_BG = "#f6f8fb"
COLOR_SURFACE = "#ffffff"
COLOR_BORDER = "#e2e8f0"
COLOR_TEXT = "#0f172a"
COLOR_MUTED = "#64748b"
COLOR_ACCENT = "#1d4ed8"
COLOR_SUCCESS = "#059669"
COLOR_DANGER = "#dc2626"
COLOR_GRID = "#eef2f7"
CHART_PALETTE = ["#1d4ed8", "#059669", "#d97706", "#7c3aed", "#0891b2", "#db2777"]


# -------------------- KPI --------------------


def derive_kpi(
    daily_df: pd.DataFrame | None,
    monthly_purchases: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """ポートフォリオ CSV と月次設定から KPI を計算。"""
    kpi = dict(DEFAULT_KPI)
    if daily_df is not None and not daily_df.empty:
        latest = daily_df.sort_values("date").iloc[-1]
        kpi["current_value_jpy"] = float(latest["total_market_value_jpy"])
        kpi["total_invested_jpy"] = float(latest["total_book_value_jpy"])
        kpi["profit_loss_jpy"] = float(latest["profit_loss_jpy"])
        kpi["profit_loss_rate"] = float(latest["profit_loss_rate"])
    if monthly_purchases:
        kpi["monthly_purchase_jpy"] = sum(int(p.get("amount_jpy", 0)) for p in monthly_purchases)
    return kpi


def latest_date(*dfs: pd.DataFrame | None) -> str | None:
    """与えられた DataFrame 群から date 列の最大値を ISO 文字列で返す。"""
    candidates: list[Any] = []
    for df in dfs:
        if df is None or df.empty or "date" not in df.columns:
            continue
        candidates.append(df["date"].max())
    if not candidates:
        return None
    return _format_date(max(candidates))


# -------------------- グラフ --------------------


def _apply_chart_layout(fig: go.Figure, height: int = 300) -> None:
    fig.update_layout(
        template="plotly_white",
        colorway=CHART_PALETTE,
        font={
            "family": "system-ui, -apple-system, sans-serif",
            "color": COLOR_TEXT,
            "size": 12,
        },
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 50, "r": 20, "t": 10, "b": 40},
        height=height,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": -0.3,
            "xanchor": "left",
            "x": 0,
        },
        xaxis={
            "showgrid": False,
            "linecolor": COLOR_BORDER,
            "tickcolor": COLOR_BORDER,
            "tickfont": {"color": COLOR_MUTED},
        },
        yaxis={
            "gridcolor": COLOR_GRID,
            "linecolor": COLOR_BORDER,
            "tickcolor": COLOR_BORDER,
            "tickfont": {"color": COLOR_MUTED},
        },
    )


def _chart_div(fig: go.Figure, testid: str, title: str, div_id: str) -> str:
    body = fig.to_html(include_plotlyjs=False, full_html=False, div_id=div_id)
    return (
        f'<section class="card chart-card" data-testid="{testid}">'
        f'<h2 class="card-title">{escape(title)}</h2>'
        f'<div class="chart-body">{body}</div>'
        "</section>"
    )


def build_market_value_chart(daily_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        data=[
            go.Scatter(
                x=daily_df["date"],
                y=daily_df["total_market_value_jpy"],
                name="評価額",
                mode="lines",
                line={"width": 2.5},
                fill="tozeroy",
                fillcolor="rgba(29, 78, 216, 0.08)",
            )
        ]
    )
    _apply_chart_layout(fig)
    fig.update_yaxes(title_text="JPY")
    return fig


def build_invested_chart(daily_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        data=[
            go.Scatter(
                x=daily_df["date"],
                y=daily_df["total_book_value_jpy"],
                name="累計投資額",
                mode="lines",
                line={"width": 2.5, "color": COLOR_MUTED},
            )
        ]
    )
    _apply_chart_layout(fig)
    fig.update_yaxes(title_text="JPY")
    return fig


def build_profit_loss_chart(daily_df: pd.DataFrame) -> go.Figure:
    pl = daily_df["profit_loss_jpy"]
    color = COLOR_SUCCESS if (not pl.empty and pl.iloc[-1] >= 0) else COLOR_DANGER
    fig = go.Figure(
        data=[
            go.Scatter(
                x=daily_df["date"],
                y=pl,
                name="評価損益",
                mode="lines",
                line={"width": 2.5, "color": color},
                fill="tozeroy",
                fillcolor=f"rgba({_hex_to_rgb(color)}, 0.08)",
            )
        ]
    )
    _apply_chart_layout(fig)
    fig.update_yaxes(title_text="JPY", zeroline=True, zerolinecolor=COLOR_BORDER, zerolinewidth=1)
    return fig


def build_stacked_by_asset_chart(by_asset_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for asset_id, sub in by_asset_df.sort_values("date").groupby("asset_id"):
        fig.add_trace(
            go.Scatter(
                x=sub["date"],
                y=sub["market_value_jpy"],
                name=str(asset_id),
                stackgroup="one",
                mode="lines",
                line={"width": 0.5},
            )
        )
    _apply_chart_layout(fig, height=340)
    fig.update_yaxes(title_text="JPY")
    return fig


def build_allocation_chart(by_asset_df: pd.DataFrame) -> go.Figure:
    latest_d = by_asset_df["date"].max()
    latest = by_asset_df[by_asset_df["date"] == latest_d]
    fig = go.Figure(
        data=[
            go.Pie(
                labels=latest["asset_id"],
                values=latest["market_value_jpy"],
                hole=0.55,
                marker={"colors": CHART_PALETTE},
                textinfo="percent",
                textfont={"color": COLOR_SURFACE, "size": 13},
            )
        ]
    )
    _apply_chart_layout(fig, height=340)
    fig.update_layout(margin={"l": 20, "r": 20, "t": 20, "b": 40})
    return fig


# -------------------- テーブル --------------------


def _table(
    headers: list[str],
    rows: list[list[str]],
    testid: str,
    title: str,
    align_right: set[int] | None = None,
) -> str:
    right_cols = align_right or set()
    head = "".join(
        f'<th class="{"num" if i in right_cols else ""}">{escape(h)}</th>'
        for i, h in enumerate(headers)
    )
    body_rows = []
    for r in rows:
        cells = "".join(
            f'<td class="{"num" if i in right_cols else ""}">{escape(c)}</td>'
            for i, c in enumerate(r)
        )
        body_rows.append(f"<tr>{cells}</tr>")
    body = "".join(body_rows)
    return (
        f'<section class="card table-card" data-testid="{testid}">'
        f'<h2 class="card-title">{escape(title)}</h2>'
        f'<div class="table-wrap"><table>'
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"
        "</section>"
    )


def build_holdings_table(
    by_asset_df: pd.DataFrame,
    asset_name_by_id: dict[str, str],
) -> str:
    if by_asset_df is None or by_asset_df.empty:
        return _table(
            ["asset_id", "name", "数量", "評価額 (円)", "weight"],
            [],
            testid="table-holdings",
            title="商品別保有状況",
            align_right={2, 3, 4},
        )
    latest_d = by_asset_df["date"].max()
    latest = by_asset_df[by_asset_df["date"] == latest_d].sort_values(
        "market_value_jpy", ascending=False
    )
    rows = [
        [
            str(r["asset_id"]),
            asset_name_by_id.get(str(r["asset_id"]), str(r["asset_id"])),
            _fmt(r["quantity"]),
            f"{int(round(r['market_value_jpy'])):,}",
            f"{float(r['weight']):.2%}",
        ]
        for _, r in latest.iterrows()
    ]
    return _table(
        ["asset_id", "name", "数量", "評価額 (円)", "weight"],
        rows,
        testid="table-holdings",
        title="商品別保有状況",
        align_right={2, 3, 4},
    )


def build_monthly_purchases_table(monthly_purchases: list[dict[str, Any]]) -> str:
    rows = [
        [
            str(p.get("asset_id", "")),
            f"{int(p.get('amount_jpy', 0)):,}",
            str(p.get("purchase_day", "")),
            str(p.get("start_month", "")),
            str(p.get("end_month") or "-"),
            str(p.get("account_type", "")),
        ]
        for p in monthly_purchases or []
    ]
    return _table(
        ["asset_id", "金額", "購入日", "開始月", "終了月", "口座区分"],
        rows,
        testid="table-monthly-purchases",
        title="月次購入設定",
        align_right={1, 2},
    )


def build_latest_prices_table(prices_df: pd.DataFrame | None) -> str:
    if prices_df is None or prices_df.empty:
        return _table(
            ["asset_id", "日付", "価格", "通貨", "ソース"],
            [],
            testid="table-latest-prices",
            title="最新価格一覧",
            align_right={2},
        )
    df = prices_df.sort_values("date").groupby("asset_id").tail(1)
    rows = [
        [
            str(r["asset_id"]),
            _format_date(r["date"]),
            _fmt(r["price"]),
            str(r.get("currency", "")),
            str(r.get("source", "")),
        ]
        for _, r in df.iterrows()
    ]
    return _table(
        ["asset_id", "日付", "価格", "通貨", "ソース"],
        rows,
        testid="table-latest-prices",
        title="最新価格一覧",
        align_right={2},
    )


def _format_date(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _fmt(v: Any) -> str:
    try:
        f = float(v)
    except (ValueError, TypeError):
        return str(v)
    if f.is_integer():
        return f"{int(f):,}"
    return f"{f:,.4f}".rstrip("0").rstrip(".")


def _hex_to_rgb(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    return f"{int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}"


def _pl_tone(pl: float) -> str:
    """profit_loss の符号でクラス名を返す。"""
    if pl > 0:
        return "positive"
    if pl < 0:
        return "negative"
    return "neutral"


# -------------------- HTML --------------------


def render_html(
    kpi: dict[str, Any] | None = None,
    daily_df: pd.DataFrame | None = None,
    by_asset_df: pd.DataFrame | None = None,
    assets: list[dict[str, Any]] | None = None,
    monthly_purchases: list[dict[str, Any]] | None = None,
    prices_df: pd.DataFrame | None = None,
) -> str:
    if daily_df is not None or by_asset_df is not None:
        kpi = derive_kpi(daily_df, monthly_purchases)
    else:
        kpi = {**DEFAULT_KPI, **(kpi or {})}

    asset_name_by_id = {a["asset_id"]: a.get("name", a["asset_id"]) for a in assets or []}

    charts_html = ""
    if daily_df is not None and not daily_df.empty:
        charts_html += _chart_div(
            build_market_value_chart(daily_df),
            testid="chart-market-value",
            title="評価額推移",
            div_id="chart-market-value",
        )
        charts_html += _chart_div(
            build_invested_chart(daily_df),
            testid="chart-total-invested",
            title="累計投資額推移",
            div_id="chart-total-invested",
        )
        charts_html += _chart_div(
            build_profit_loss_chart(daily_df),
            testid="chart-profit-loss",
            title="評価損益推移",
            div_id="chart-profit-loss",
        )
    if by_asset_df is not None and not by_asset_df.empty:
        charts_html += _chart_div(
            build_stacked_by_asset_chart(by_asset_df),
            testid="chart-by-asset-stack",
            title="商品別評価額推移",
            div_id="chart-by-asset-stack",
        )
        charts_html += _chart_div(
            build_allocation_chart(by_asset_df),
            testid="chart-allocation",
            title="商品別構成比",
            div_id="chart-allocation",
        )

    holdings_table = (
        build_holdings_table(by_asset_df, asset_name_by_id) if by_asset_df is not None else ""
    )
    purchases_table = build_monthly_purchases_table(monthly_purchases or [])
    prices_table = build_latest_prices_table(prices_df)

    status_note = ""
    if daily_df is None and by_asset_df is None:
        status_note = (
            '<p class="status-note" data-testid="status">'
            "スケルトン版です。データが投入されると実際の KPI とグラフが表示されます。"
            "</p>"
        )

    cv = int(round(kpi["current_value_jpy"]))
    ti = int(round(kpi["total_invested_jpy"]))
    pl = int(round(kpi["profit_loss_jpy"]))
    pl_rate = kpi["profit_loss_rate"]
    mp = int(kpi["monthly_purchase_jpy"])
    pl_tone = _pl_tone(pl)
    pl_sign = "+" if pl > 0 else ("−" if pl < 0 else "")
    pl_rate_sign = "+" if pl_rate > 0 else ("−" if pl_rate < 0 else "")
    pl_display = f"{pl_sign}{abs(pl):,}"
    pl_rate_display = f"{pl_rate_sign}{abs(pl_rate):.2%}"

    last_updated = latest_date(daily_df, by_asset_df, prices_df)
    updated_html = (
        f'<span class="updated" data-testid="last-updated">最終更新 {escape(last_updated)}</span>'
        if last_updated
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>積立投資 評価額トラッカー</title>
  <script src="{PLOTLY_CDN}"></script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; }}
    :root {{
      color-scheme: light;
      --bg: {COLOR_BG};
      --surface: {COLOR_SURFACE};
      --border: {COLOR_BORDER};
      --text: {COLOR_TEXT};
      --muted: {COLOR_MUTED};
      --accent: {COLOR_ACCENT};
      --success: {COLOR_SUCCESS};
      --danger: {COLOR_DANGER};
    }}
    html, body {{ margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, "Hiragino Kaku Gothic ProN", "Yu Gothic",
                   "Meiryo", system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      -webkit-font-smoothing: antialiased;
    }}
    .container {{ max-width: 1120px; margin: 0 auto; padding: 2rem 1.25rem 3rem; }}
    .page-header {{
      display: flex;
      flex-wrap: wrap;
      align-items: baseline;
      justify-content: space-between;
      gap: 0.75rem;
      margin-bottom: 1.5rem;
      padding-bottom: 1rem;
      border-bottom: 1px solid var(--border);
    }}
    .page-header h1 {{
      margin: 0;
      font-size: 1.5rem;
      letter-spacing: 0.01em;
      font-weight: 700;
    }}
    .page-header .updated {{
      color: var(--muted);
      font-size: 0.85rem;
      font-variant-numeric: tabular-nums;
    }}
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 0.75rem;
      margin-bottom: 1.5rem;
    }}
    .kpi-card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1rem 1.1rem;
    }}
    .kpi-label {{
      color: var(--muted);
      font-size: 0.78rem;
      letter-spacing: 0.04em;
      margin-bottom: 0.25rem;
    }}
    .kpi-value {{
      font-size: 1.5rem;
      font-weight: 700;
      font-variant-numeric: tabular-nums;
      letter-spacing: -0.01em;
    }}
    .kpi-value.positive {{ color: var(--success); }}
    .kpi-value.negative {{ color: var(--danger); }}
    .card {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1rem 1.25rem 1.25rem;
      margin-bottom: 1rem;
    }}
    .card-title {{
      margin: 0 0 0.75rem;
      font-size: 0.95rem;
      font-weight: 600;
      color: var(--text);
      letter-spacing: 0.01em;
    }}
    .chart-card .chart-body {{ margin: 0 -0.25rem; }}
    .table-wrap {{ overflow-x: auto; }}
    table {{
      border-collapse: collapse;
      width: 100%;
      font-size: 0.9rem;
    }}
    thead th {{
      text-align: left;
      font-weight: 600;
      color: var(--muted);
      border-bottom: 1px solid var(--border);
      padding: 0.55rem 0.75rem;
      background: transparent;
    }}
    tbody td {{
      padding: 0.55rem 0.75rem;
      border-bottom: 1px solid var(--border);
      font-variant-numeric: tabular-nums;
    }}
    tbody tr:last-child td {{ border-bottom: none; }}
    tbody tr:hover {{ background: #f8fafc; }}
    th.num, td.num {{ text-align: right; }}
    .status-note {{
      color: var(--muted);
      background: var(--surface);
      border: 1px dashed var(--border);
      border-radius: 12px;
      padding: 1rem 1.25rem;
      margin-bottom: 1rem;
    }}
    .footer {{
      color: var(--muted);
      font-size: 0.78rem;
      text-align: center;
      margin-top: 2rem;
    }}
    @media (max-width: 600px) {{
      .container {{ padding: 1.5rem 1rem 2.5rem; }}
      .page-header h1 {{ font-size: 1.25rem; }}
      .kpi-value {{ font-size: 1.25rem; }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <header class="page-header">
      <h1>積立投資 評価額トラッカー</h1>
      {updated_html}
    </header>
    <section class="kpi-grid" data-testid="kpi">
      <div class="kpi-card">
        <div class="kpi-label">現在評価額</div>
        <div class="kpi-value" data-testid="kpi-current-value">{cv:,} 円</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">累計投資額</div>
        <div class="kpi-value" data-testid="kpi-total-invested">{ti:,} 円</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">評価損益</div>
        <div class="kpi-value {pl_tone}" data-testid="kpi-profit-loss">{pl_display} 円</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">評価損益率</div>
        <div class="kpi-value {pl_tone}" data-testid="kpi-profit-loss-rate">{pl_rate_display}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">月間購入額</div>
        <div class="kpi-value" data-testid="kpi-monthly-purchase">{mp:,} 円</div>
      </div>
    </section>
    {charts_html}
    {holdings_table}
    {purchases_table}
    {prices_table}
    {status_note}
    <footer class="footer">
      Powered by yfinance / Yahoo!ファイナンス JP ・ generated by GitHub Actions
    </footer>
  </div>
</body>
</html>
"""


def build(
    output_path: Path,
    kpi: dict[str, Any] | None = None,
    daily_df: pd.DataFrame | None = None,
    by_asset_df: pd.DataFrame | None = None,
    assets: list[dict[str, Any]] | None = None,
    monthly_purchases: list[dict[str, Any]] | None = None,
    prices_df: pd.DataFrame | None = None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_html(
            kpi=kpi,
            daily_df=daily_df,
            by_asset_df=by_asset_df,
            assets=assets,
            monthly_purchases=monthly_purchases,
            prices_df=prices_df,
        ),
        encoding="utf-8",
    )
    return output_path


def _load_optional_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    df = pd.read_csv(path)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="ダッシュボード HTML を生成")
    parser.add_argument(
        "--output", type=Path, default=Path("public/index.html"), help="出力先 HTML"
    )
    parser.add_argument("--config-dir", type=Path, default=Path("config"))
    parser.add_argument("--daily", type=Path, default=Path("data/portfolio/portfolio_daily.csv"))
    parser.add_argument(
        "--by-asset",
        type=Path,
        default=Path("data/portfolio/portfolio_by_asset.csv"),
    )
    parser.add_argument("--prices", type=Path, default=Path("data/prices/prices.csv"))
    args = parser.parse_args()

    daily_df = _load_optional_csv(args.daily)
    by_asset_df = _load_optional_csv(args.by_asset)
    prices_df = _load_optional_csv(args.prices)
    try:
        assets = load_assets(args.config_dir)
    except FileNotFoundError:
        assets = []
    try:
        monthly_purchases = load_monthly_purchases(args.config_dir)
    except FileNotFoundError:
        monthly_purchases = []

    build(
        args.output,
        daily_df=daily_df,
        by_asset_df=by_asset_df,
        assets=assets,
        monthly_purchases=monthly_purchases,
        prices_df=prices_df,
    )
    logger.info("dashboard を %s に生成しました", args.output)


if __name__ == "__main__":
    main()
