# asset-management

積立投資の評価額を自動取得・可視化する個人用トラッカー。

- 仕様: [`docs/spec.md`](docs/spec.md)
- 開発ルール: [`docs/development.md`](docs/development.md)
- Claude Code 用指針: [`CLAUDE.md`](CLAUDE.md)

## セットアップ

```bash
uv sync
```

## 開発

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest tests/unit tests/integration
```

## ローカルで dashboard を確認

`develop` の途中状態を確認するときはローカルで開く（Pages デプロイは `main` のみ）。

```bash
uv run python -m src.build_dashboard --output public/index.html
python -m http.server -d public 8000
# → http://localhost:8000
```

機能追加は `develop` から `feature/*` を切る。詳細は `docs/development.md`。
