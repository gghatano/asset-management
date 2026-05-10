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
```

機能追加は `develop` から `feature/*` を切る。詳細は `docs/development.md`。
