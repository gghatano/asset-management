# asset-management

積立投資の評価額を自動取得・可視化する個人用トラッカー。

- 公開 dashboard: https://gghatano.github.io/asset-management/
- 仕様: [`docs/spec.md`](docs/spec.md)
- 開発ルール: [`docs/development.md`](docs/development.md)
- Claude Code 用指針: [`CLAUDE.md`](CLAUDE.md)
- 変更履歴: [`CHANGELOG.md`](CHANGELOG.md)

## できること

- `config/assets.yaml` / `initial_positions.yaml` / `monthly_purchases.yaml` から積立シミュレーション
- 価格は yfinance / Yahoo!ファイナンス JP / 固定値で取得（失敗時は前回値フォールバック）
- 日次の評価額・累計投資額・損益・商品別 weight を集計
- Plotly + テーブルで dashboard を出力し GitHub Pages に公開
- GitHub Actions で毎日 22:00 UTC 自動更新

## セットアップ

```bash
uv sync
```

## 開発

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest tests/unit tests/integration
# 初回のみ
uv run playwright install --with-deps chromium
uv run pytest tests/e2e
```

## ローカルで dashboard を確認

Pages デプロイは `main` のみ。`develop` の途中状態を見るときはローカルで開く。

```bash
# 全パイプラインを通す
uv run python -m src.fetch_prices
uv run python -m src.generate_transactions
uv run python -m src.calculate_portfolio
uv run python -m src.build_dashboard --output public/index.html

# 静的サーバで開く
python -m http.server -d public 8000
# → http://localhost:8000
```

## ブランチ運用

機能追加は `develop` から `feature/*` を切り、Squash で `develop` にマージ。リリース時のみ `develop` → `main` を Merge commit でマージする。詳細は [`docs/development.md`](docs/development.md)。
