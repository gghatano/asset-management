"""ダッシュボードの E2E テスト (Playwright)。"""

from __future__ import annotations

from playwright.sync_api import Page, expect


def test_dashboard_shows_title(page: Page, dashboard_url: str) -> None:
    page.goto(dashboard_url)
    expect(page).to_have_title("積立投資 評価額トラッカー")
    expect(page.get_by_role("heading", name="積立投資 評価額トラッカー")).to_be_visible()


def test_dashboard_renders_kpi_cards(page: Page, dashboard_url: str) -> None:
    page.goto(dashboard_url)
    expect(page.get_by_test_id("kpi")).to_be_visible()
    expect(page.get_by_test_id("kpi-current-value")).to_contain_text("5,920,000")
    expect(page.get_by_test_id("kpi-total-invested")).to_contain_text("5,860,000")
    expect(page.get_by_test_id("kpi-profit-loss")).to_contain_text("60,000")
    expect(page.get_by_test_id("kpi-profit-loss-rate")).to_contain_text("1.02%")


def test_full_dashboard_charts_render(page: Page, dashboard_full_url: str) -> None:
    page.goto(dashboard_full_url)
    for testid in [
        "chart-market-value",
        "chart-total-invested",
        "chart-profit-loss",
        "chart-by-asset-stack",
        "chart-allocation",
    ]:
        expect(page.get_by_test_id(testid)).to_be_visible()
    # Plotly が描画した SVG が KPI/グラフセクション以下に存在すること
    expect(page.locator("section[data-testid='chart-market-value'] svg").first).to_be_visible()


def test_full_dashboard_tables_visible(page: Page, dashboard_full_url: str) -> None:
    page.goto(dashboard_full_url)
    expect(page.get_by_test_id("table-holdings")).to_be_visible()
    expect(page.get_by_test_id("table-monthly-purchases")).to_be_visible()
    expect(page.get_by_test_id("table-latest-prices")).to_be_visible()
    expect(page.get_by_test_id("table-holdings")).to_contain_text("サンプル投信 A")


def test_full_dashboard_monthly_purchase_kpi(page: Page, dashboard_full_url: str) -> None:
    page.goto(dashboard_full_url)
    expect(page.get_by_test_id("kpi-monthly-purchase")).to_contain_text("50,000")
