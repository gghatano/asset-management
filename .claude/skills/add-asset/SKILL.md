---
name: add-asset
description: 新しい金融商品（投資信託・ETF・株式・現金など）を本トラッカーに追加するときに使う。`config/assets.yaml` への追記、`config/initial_positions.yaml` / `config/monthly_purchases.yaml` の整合確認、必要に応じた価格取得アダプタの拡張、`docs/spec.md` の更新を一括で案内する。
---

# 新しい資産の追加

ユーザーが「銘柄を追加したい」「商品を増やしたい」「assets.yaml に追加」などと言ったときに発動する。

## 1. ヒアリング

以下を確認する。不足していれば AskUserQuestion で聞く。

- `asset_id`（snake_case の一意 ID）
- 商品名（表示名）
- 種別: `mutual_fund` / `etf` / `stock` / `cash`
- 通貨: `JPY` / `USD` など
- 価格ソース: `yahoo_finance_jp` / `yfinance` / `fixed` / 手動 CSV
- ソースコード（投信協会コード、ティッカーなど）
- 単位基準価額 (`unit_price_base`)：投信は通常 10000、ETF/株式は 1
- 初期保有量と簿価（あれば）
- 月次購入額・購入日・口座区分（NISA/特定/iDeCo/現金）

## 2. 編集対象

優先順:

1. `config/assets.yaml` に商品エントリを追加
2. 初期保有がある場合 `config/initial_positions.yaml` に追加
3. 月次購入する場合 `config/monthly_purchases.yaml` に追加
4. 価格ソースが既存アダプタで賄えない場合のみ `src/fetch_prices.py` を拡張
5. スキーマや前提が変わるなら `docs/spec.md` の該当節も更新

## 3. バリデーション観点

- `asset_id` の重複なし
- `currency` と `price_source` が整合している（例: `yfinance` で `JPY` ティッカーは `.T` 付き）
- `unit_price_base` が種別と整合（投信は 10000、それ以外は 1）
- `start_month` は `YYYY-MM` 形式
- `purchase_day` は 1〜28（月末扱いを避ける）

## 4. 動作確認

```bash
uv run python src/fetch_prices.py        # 新銘柄の価格が取得できるか
uv run python src/generate_transactions.py
uv run python src/calculate_portfolio.py
uv run python src/build_dashboard.py
```

## 5. PR

- ブランチ名: `feature/add-asset-<asset_id>`
- タイトル例: `feat: <商品名> を追加`
- 仕様変更を伴う場合は `docs/spec.md` も同 PR で更新

## 注意

- 過去に遡って初期保有を増やすと評価額の履歴が遡及して変わる。意図的でない場合は `start_month` と `as_of` の整合を必ず確認する
- 外貨建ての場合、為替の取得タイミングで評価額が変動する点を許容できるか確認
