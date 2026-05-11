# 積立投資 評価額トラッカー 設計書

## 1. 目的

毎月定額で購入する金融商品の価格変動を取得し、初期保有分と積立購入分を合算して、資産評価額・累計投資額・評価損益の時間変化を可視化する。

証券口座や家計簿サービスとは連携せず、以下の入力情報から評価額を再現する。

- 初期保有資産
- 毎月の購入対象商品
- 毎月の購入金額
- 金融商品の価格データ

## 2. 対象スコープ

### 対象

- 投資信託
- ETF
- 株式
- 現金相当の初期残高
- 月次積立
- 評価額推移の表示
- 商品別構成比の表示
- 元本・評価額・損益の推移表示

### 対象外

- 証券口座との自動連携
- 売却取引
- 配当・分配金の厳密な再投資管理
- 税金計算
- 為替の厳密な約定日処理
- NISA枠の残高管理
- 家計簿機能

## 3. 想定構成

```text
config/
  assets.yaml              # 商品マスタ
  initial_positions.yaml   # 初期保有
  monthly_purchases.yaml   # 毎月購入設定

data/
  prices/                  # 取得した価格データ
  transactions/            # 自動生成した購入履歴
  portfolio/               # 評価結果

src/
  fetch_prices.py
  generate_transactions.py
  calculate_portfolio.py
  build_dashboard.py

public/
  index.html
  assets/
```

## 4. 技術スタック

- Python 3.12
- uv
- pandas
- yfinance
- plotly
- pyyaml
- GitHub Actions
- GitHub Pages

補足：

- GitHub Pagesは静的ファイル配信を前提とする。
- StreamlitはPythonサーバが必要なため、GitHub Pagesとは相性が悪い。
- そのため、PlotlyでHTMLを生成してGitHub Pagesに配置する。

## 5. 入力ファイル

### 5.1 商品マスタ `config/assets.yaml`

```yaml
assets:
  - asset_id: emaxis_slim_sp500
    name: "eMAXIS Slim 米国株式（S&P500）"
    asset_type: "mutual_fund"
    currency: "JPY"
    price_source: "yahoo_finance_jp"
    source_code: "03311187"
    unit_price_base: 10000
    enabled: true

  - asset_id: vt
    name: "Vanguard Total World Stock ETF"
    asset_type: "etf"
    currency: "USD"
    price_source: "yfinance"
    source_code: "VT"
    unit_price_base: 1
    enabled: true

  - asset_id: cash_jpy
    name: "日本円現金"
    asset_type: "cash"
    currency: "JPY"
    price_source: "fixed"
    source_code: "JPY"
    unit_price_base: 1
    enabled: true
```

S&P500は、初期サンプルとして eMAXIS Slim 米国株式（S&P500） を入れる。投信協会コードは `03311187`。同ファンドはS&P500指数、配当込み・円換算ベースへの連動を目指す商品として公表されている。

### 5.2 初期保有 `config/initial_positions.yaml`

```yaml
as_of: "2026-05-01"

positions:
  - asset_id: emaxis_slim_sp500
    quantity: 1200000
    quantity_unit: "口"
    book_value_jpy: 4500000

  - asset_id: vt
    quantity: 20
    quantity_unit: "株"
    book_value_jpy: 360000

  - asset_id: cash_jpy
    quantity: 1000000
    quantity_unit: "円"
    book_value_jpy: 1000000
```

### 5.3 毎月購入設定 `config/monthly_purchases.yaml`

```yaml
monthly_purchases:
  - asset_id: emaxis_slim_sp500
    amount_jpy: 50000
    purchase_day: 5
    start_month: "2026-05"
    end_month: null
    account_type: "NISA"

  - asset_id: vt
    amount_jpy: 20000
    purchase_day: 10
    start_month: "2026-05"
    end_month: null
    account_type: "特定"

  - asset_id: cash_jpy
    amount_jpy: 30000
    purchase_day: 25
    start_month: "2026-05"
    end_month: null
    account_type: "現金"
```

## 6. 価格取得仕様

### 6.1 投資信託

投資信託は、当初はYahoo!ファイナンス等で確認できる基準価額を取得対象とする。
eMAXIS Slim 米国株式（S&P500） はYahoo!ファイナンス上で `03311187` として時系列・基準価額が確認できる。

取得方法は以下の順で実装する。

1. 取得アダプタを抽象化する
2. 最初は手動CSV投入にも対応する
3. 可能であればHTML取得・パースを実装する
4. 取得失敗時は前回価格を利用する

### 6.2 ETF / 株式

ETF・株式は yfinance を利用して終値を取得する。

```text
source_code: VT
source_code: VTI
source_code: 2558.T
source_code: 1655.T
```

### 6.3 為替

外貨建て資産は、USD価格 × USD/JPYで円換算する。
初期実装では JPY 資産を中心にし、外貨建てETFは追加実装扱いでもよい。

#### 運用上の取り扱い（Phase 1 実装で確定）

円換算用の為替は、価格 CSV (`data/prices/prices.csv`) に通常の asset と同じ形式で記録する。
asset_id は `<currency_lower>_jpy` 形式（例: `usd_jpy`）。
`generate_transactions` / `calculate_portfolio` は購入・評価時にこの asset_id を引いて掛け合わせる。

実価格取得を有効にする場合は `config/assets.yaml` に以下のような entry を追加する。

```yaml
- asset_id: usd_jpy
  name: "USD/JPY"
  asset_type: "fx"          # 任意。fetch_prices からは price_source のみ参照
  currency: "JPY"
  price_source: "yfinance"
  source_code: "USDJPY=X"
  unit_price_base: 1
  enabled: true
```

`usd_jpy` の価格が無い日は、外貨建て購入はその日 skip され warn ログを残す（ジョブは継続）。

## 7. 計算ロジック

### 7.1 投資信託の購入口数

```text
購入口数 = 購入金額 ÷ 基準価額 × 10000
```

例：

```text
購入金額: 50,000円
基準価額: 40,000円
購入口数: 50,000 ÷ 40,000 × 10,000 = 12,500口
```

### 7.2 評価額

```text
評価額 = 保有口数 × 基準価額 ÷ 10000
```

### 7.3 ETF / 株式の購入数量

```text
購入数量 = 購入金額 ÷ 円換算価格
```

初期実装では小数株を許容する。
実運用に合わせる場合は、単元・整数株・買付余力残を後で実装する。

### 7.4 累計投資額

```text
累計投資額 = 初期簿価 + 累計購入金額
```

### 7.5 評価損益

```text
評価損益 = 現在評価額 - 累計投資額
評価損益率 = 評価損益 ÷ 累計投資額
```

## 8. 出力データ

### 8.1 価格データ `data/prices/prices.csv`

```text
date,asset_id,price,currency,source
2026-05-01,emaxis_slim_sp500,42272,JPY,yahoo_finance_jp
2026-05-01,vt,128.5,USD,yfinance
```

### 8.2 購入履歴 `data/transactions/generated_purchases.csv`

```text
date,asset_id,amount_jpy,price,quantity,account_type
2026-05-05,emaxis_slim_sp500,50000,42272,11828.16,NISA
2026-05-10,vt,20000,128.5,0.99,特定
```

### 8.3 評価結果 `data/portfolio/portfolio_daily.csv`

```text
date,total_book_value_jpy,total_market_value_jpy,profit_loss_jpy,profit_loss_rate
2026-05-01,5860000,5920000,60000,0.0102
```

### 8.4 商品別評価 `data/portfolio/portfolio_by_asset.csv`

```text
date,asset_id,quantity,book_value_jpy,market_value_jpy,profit_loss_jpy,weight
2026-05-01,emaxis_slim_sp500,1200000,4500000,5072640,572640,0.82
```

## 9. ダッシュボード仕様

`public/index.html` に以下を表示する。

### 9.1 KPI

- 現在評価額
- 累計投資額
- 評価損益
- 評価損益率
- 月間購入額

### 9.2 グラフ

- 評価額推移
- 累計投資額推移
- 評価損益推移
- 商品別評価額推移
- 商品別構成比

### 9.3 テーブル

- 商品別保有状況
- 月次購入設定
- 最新価格一覧

## 10. バッチ処理

### 10.1 日次処理

1. 商品マスタを読み込む
2. 価格データを取得する
3. 価格CSVを更新する
4. 月次購入履歴を生成する
5. 日次ポートフォリオ評価を計算する
6. HTMLダッシュボードを生成する
7. GitHub Pagesへ公開する

### 10.2 GitHub Actions

```yaml
name: update-portfolio

on:
  schedule:
    - cron: "0 22 * * *"
  workflow_dispatch:

jobs:
  update:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Install dependencies
        run: uv sync

      - name: Fetch prices
        run: uv run python src/fetch_prices.py

      - name: Generate transactions
        run: uv run python src/generate_transactions.py

      - name: Calculate portfolio
        run: uv run python src/calculate_portfolio.py

      - name: Build dashboard
        run: uv run python src/build_dashboard.py

      - name: Commit generated files
        run: |
          git config user.name "github-actions"
          git config user.email "github-actions@github.com"
          git add data public
          git commit -m "Update portfolio data" || echo "No changes"
          git push
```

## 11. 初期ダミーデータ

初期サンプルでは以下を用意する。

```text
初期保有:
- eMAXIS Slim 米国株式（S&P500）: 4,500,000円分
- VT: 360,000円分
- 日本円現金: 1,000,000円

毎月購入:
- eMAXIS Slim 米国株式（S&P500）: 50,000円
- VT: 20,000円
- 日本円現金: 30,000円
```

## 12. 実装方針

### Phase 1: ローカルで動く最小版

- YAML入力
- ダミー価格CSV
- ポートフォリオ計算
- HTML出力

### Phase 2: 実価格取得

- yfinanceでETF価格取得
- S&P500投信の基準価額取得
- 取得失敗時のフォールバック

### Phase 3: GitHub Pages公開

- GitHub Actionsで日次更新
- `public/index.html` を公開

### Phase 4: 実運用改善

- 価格取得ログ
- 取得失敗通知
- 商品追加時のバリデーション
- NISA / 特定 / iDeCo別集計
- 入金・現金残高の扱い
- 売却取引への対応

## 13. 注意事項

- 本ツールは投資判断を支援するものではなく、保有資産の概算把握を目的とする。
- 基準価額・株価・為替は取得元によりタイミングや値が異なる。
- 投資信託の約定日は購入申込日と一致しない場合がある。
- 初期実装では、購入日の価格で購入したものとして近似する。
- 外貨建てETFは為替レートの取得タイミングにより評価額が変動する。

---

この設計なら、最初に変更すべきファイルは基本的に次の3つだけです。

```text
config/assets.yaml
config/initial_positions.yaml
config/monthly_purchases.yaml
```
