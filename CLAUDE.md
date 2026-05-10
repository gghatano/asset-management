# プロジェクト指針 (Claude Code 用)

このリポジトリは「積立投資 評価額トラッカー」。設計の詳細は `docs/spec.md`、開発ルールは `docs/development.md` を参照する。Claude Code で作業する際の最低限の指針をここにまとめる。

## 1. リポジトリ構成

```text
config/   # 入力 YAML (人手で編集)
data/     # 自動生成 (手動編集禁止)
public/   # 自動生成 (手動編集禁止)
src/      # ロジック本体 (人手で編集)
docs/     # 仕様・開発ルール
.claude/  # Claude Code 用スキル
```

## 2. 開発フロー

- ベースブランチ: `develop`
- リリース時のみ `develop` → `main`
- 機能追加は `feature/<名前>`、バグ修正は `fix/<名前>`、設定系は `chore/<名前>`、ドキュメントのみは `docs/<名前>`
- Conventional Commits（`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`, `perf:`）
- マージは Squash 推奨。リリース PR (`develop` → `main`) のみ Merge commit
- 詳細は `docs/development.md`

## 3. 実行コマンド

```bash
uv sync                              # 依存導入
uv run python src/<script>.py        # 各ステップを単体実行
uv run ruff check .                  # lint
uv run ruff format .                 # format
uv run ruff format --check .         # format チェック (CI と同じ)
```

## 4. 守ってほしいこと

- `data/` と `public/` は GitHub Actions が更新する。コードからの書き換えロジックは `src/` 配下に置き、生成物自体を手で編集しない
- `config/*.yaml` のスキーマ変更は `docs/spec.md` を同じ PR で更新する
- 価格取得は失敗してもジョブ全体が落ちないように、`src/fetch_prices.py` のレベルでフォールバック（前回値利用など）を入れる
- 為替・基準価額・株価の取得元は明示する（CSV の `source` 列、または取得ログ）

## 5. 何を書かないか

- 売却・税金・配当再投資の厳密な処理は対象外（`docs/spec.md` 第2節）
- 証券口座連携や認証情報を扱うコードを追加しない
- ハードコードした個人情報・口座番号を含めない

## 6. Claude Code 用のスキル

`.claude/skills/` 配下にプロジェクト固有のスキルがある。該当する作業時には自動的に参照される想定。

- `add-asset`: 新しい金融商品を追加する手順
- `start-feature`: feature ブランチと worktree を切る手順
- `release`: `develop` から `main` へのリリース PR 作成手順
