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


# -------------------- グラフ --------------------


def _chart_div(fig: go.Figure, testid: str, title: str, div_id: str) -> str:
    body = fig.to_html(include_plotlyjs=False, full_html=False, div_id=div_id)
    return f'<section class="chart" data-testid="{testid}"><h2>{escape(title)}</h2>{body}</section>'


def build_market_value_chart(daily_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        data=[
            go.Scatter(
                x=daily_df["date"],
                y=daily_df["total_market_value_jpy"],
                name="評価額",
                mode="lines",
            )
        ]
    )
    fig.update_layout(title=None, xaxis_title="日付", yaxis_title="評価額 (円)", height=320)
    return fig


def build_invested_chart(daily_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        data=[
            go.Scatter(
                x=daily_df["date"],
                y=daily_df["total_book_value_jpy"],
                name="累計投資額",
                mode="lines",
            )
        ]
    )
    fig.update_layout(title=None, xaxis_title="日付", yaxis_title="累計投資額 (円)", height=320)
    return fig


def build_profit_loss_chart(daily_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        data=[
            go.Scatter(
                x=daily_df["date"],
                y=daily_df["profit_loss_jpy"],
                name="評価損益",
                mode="lines",
            )
        ]
    )
    fig.update_layout(title=None, xaxis_title="日付", yaxis_title="評価損益 (円)", height=320)
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
            )
        )
    fig.update_layout(title=None, xaxis_title="日付", yaxis_title="評価額 (円)", height=360)
    return fig


def build_allocation_chart(by_asset_df: pd.DataFrame) -> go.Figure:
    latest_date = by_asset_df["date"].max()
    latest = by_asset_df[by_asset_df["date"] == latest_date]
    fig = go.Figure(
        data=[
            go.Pie(
                labels=latest["asset_id"],
                values=latest["market_value_jpy"],
                hole=0.3,
            )
        ]
    )
    fig.update_layout(title=None, height=360)
    return fig


# -------------------- テーブル --------------------


def _table(
    headers: list[str],
    rows: list[list[str]],
    testid: str,
    title: str,
) -> str:
    head = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{escape(c)}</td>" for c in r) + "</tr>" for r in rows)
    return (
        f'<section class="table" data-testid="{testid}">'
        f"<h2>{escape(title)}</h2>"
        f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
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
        )
    latest_date = by_asset_df["date"].max()
    latest = by_asset_df[by_asset_df["date"] == latest_date].sort_values(
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
    )


def build_latest_prices_table(prices_df: pd.DataFrame | None) -> str:
    if prices_df is None or prices_df.empty:
        return _table(
            ["asset_id", "日付", "価格", "通貨", "ソース"],
            [],
            testid="table-latest-prices",
            title="最新価格一覧",
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
            '<p data-testid="status">スケルトン版です。データが投入されると'
            "実際の KPI とグラフが表示されます。</p>"
        )

    cv = int(round(kpi["current_value_jpy"]))
    ti = int(round(kpi["total_invested_jpy"]))
    pl = int(round(kpi["profit_loss_jpy"]))
    pl_rate = kpi["profit_loss_rate"]
    mp = int(kpi["monthly_purchase_jpy"])

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>積立投資 評価額トラッカー</title>
  <script src="{PLOTLY_CDN}"></script>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #222; }}
    h1 {{ margin-top: 0; }}
    h2 {{ font-size: 1.1rem; margin: 1.5rem 0 0.5rem; }}
    .kpi {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
    }}
    .kpi-card {{ border: 1px solid #ddd; border-radius: 8px; padding: 1rem; }}
    .kpi-label {{ color: #666; font-size: 0.85rem; }}
    .kpi-value {{ font-size: 1.5rem; font-weight: bold; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 0.4rem 0.6rem; text-align: left; }}
    th {{ background: #f5f5f5; }}
    .chart, .table {{ margin-top: 1.5rem; }}
  </style>
</head>
<body>
  <h1>積立投資 評価額トラッカー</h1>
  <section class="kpi" data-testid="kpi">
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
      <div class="kpi-value" data-testid="kpi-profit-loss">{pl:,} 円</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-label">評価損益率</div>
      <div class="kpi-value" data-testid="kpi-profit-loss-rate">{pl_rate:.2%}</div>
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
