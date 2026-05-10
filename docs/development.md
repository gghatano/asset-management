# 開発ルール

個人開発として無理なく続けられる範囲で、最低限の規律を設けるためのルールをまとめる。

## 1. ブランチ戦略

シンプル化した GitFlow を採用する。

| ブランチ | 役割 | マージ元 | マージ先 |
| --- | --- | --- | --- |
| `main` | 本番。GitHub Pages の公開対象。直接コミット禁止 | `develop` のリリースPR | — |
| `develop` | 統合ブランチ。次回リリース内容を集約 | `feature/*`, `fix/*`, `chore/*`, `docs/*` | `main` |
| `feature/*` | 新機能開発 | — | `develop` |
| `fix/*` | バグ修正 | — | `develop`（緊急時のみ `main`） |
| `chore/*` | 設定・依存更新など | — | `develop` |
| `docs/*` | ドキュメントのみ | — | `develop` |

### ブランチ命名

- kebab-case
- プレフィックス + 短い説明
- 例: `feature/fetch-prices`, `fix/portfolio-calc-rounding`, `chore/bump-uv`, `docs/update-spec`

## 2. コミットメッセージ

[Conventional Commits](https://www.conventionalcommits.org/) を採用する。

```text
<type>: <subject>

<body 任意>
```

| type | 用途 |
| --- | --- |
| `feat` | 新機能 |
| `fix` | バグ修正 |
| `docs` | ドキュメントのみ |
| `refactor` | 挙動を変えないリファクタ |
| `test` | テスト追加・修正 |
| `chore` | 設定・依存・ビルド周り |
| `perf` | パフォーマンス改善 |

例:

```text
feat: yfinance による ETF 価格取得を追加
fix: 評価損益の丸め誤差を修正
docs: spec.md の対象スコープを更新
chore: uv.lock を更新
```

- 1コミット 1関心事
- 件名は 50 文字程度を目安。必要なら本文で詳細を書く
- 後から見返した時に「なぜ」が分かるメッセージにする

## 3. git worktree 運用

ブランチごとに作業ディレクトリを分離し、依存物の再インストールやキャッシュ汚染を避ける。

### 推奨レイアウト

```text
~/work/
  asset-management/              # main をチェックアウトした本体 (origin の clone)
  asset-management.wt/           # worktree 用ディレクトリ
    develop/
    feature-fetch-prices/
    fix-portfolio-calc/
```

### 初期セットアップ

```bash
git clone git@github.com:gghatano/asset-management.git
cd asset-management
mkdir -p ../asset-management.wt

# develop を worktree として展開
git fetch origin
git worktree add ../asset-management.wt/develop develop
```

### 機能ブランチを切る

```bash
cd ~/work/asset-management.wt/develop
git pull --ff-only
git switch -c feature/fetch-prices
git push -u origin feature/fetch-prices

# 別作業を並行する場合は別 worktree を切る
cd ~/work/asset-management
git worktree add ../asset-management.wt/feature-fetch-prices feature/fetch-prices
```

### マージ後のクリーンアップ

```bash
cd ~/work/asset-management
git fetch --prune
git worktree remove ../asset-management.wt/feature-fetch-prices
git branch -d feature/fetch-prices
```

### 注意

- `worktree` 同士は同じブランチを同時にチェックアウトできない
- 各 worktree で `uv sync` をそれぞれ実行する（`.venv` は worktree ごとに作る）
- 不要になった worktree は速やかに `git worktree remove` する

## 4. プルリクエスト

- ベースブランチは原則 `develop`。`main` へは `develop` からのリリースPRのみ
- 作成時はドラフトで開き、セルフレビュー後に Ready for review に切替
- 1 PR 1 関心事。肥大化したら分割
- マージ方式は **Squash and merge** を推奨（`develop` の履歴を簡潔に保つ）
- マージ後はリモート / ローカルの作業ブランチを削除する
- 大きな仕様変更時は `docs/spec.md` も同じ PR で更新する

PR テンプレートは `.github/PULL_REQUEST_TEMPLATE.md` を参照。

## 5. リリースフロー

1. `develop` で動作確認
2. `develop` → `main` のリリース PR を作成（タイトル例: `release: v0.2.0`）
3. PR は Squash ではなく **Merge commit** でマージ（`main` 上にリリースポイントを残す）
4. `main` にマージされると GitHub Actions が GitHub Pages を更新
5. 必要に応じて tag を打つ（例: `v0.2.0`）

## 6. 開発環境

- Python 3.12
- [uv](https://docs.astral.sh/uv/)

```bash
uv sync                       # 依存導入
uv run python src/<script>.py # 実行
uv run pytest                 # テスト（追加した場合）
```

## 7. CI / 自動化

- PR では lint / test を実行（追加していくたびに `.github/workflows/` を拡張）
- `main` へのマージで GitHub Pages を更新（詳細は `docs/spec.md` の「10. バッチ処理」）
- 日次バッチ（価格更新）は `main` 上の Actions が走る

## 8. ファイル運用

| パス | 編集主体 | 備考 |
| --- | --- | --- |
| `config/` | 人手 | スキーマは `docs/spec.md` に従う |
| `data/` | Actions が自動更新 | 手動編集禁止 |
| `public/` | Actions が自動生成 | 手動編集禁止 |
| `src/` | 人手 | 機能追加時は `feature/*` で |
| `docs/` | 人手 | 仕様変更は同じ PR で更新 |

## 9. やらないこと（個人開発の割り切り）

- 厳密なコードオーナー / レビュアー必須化
- 厳密なブランチ保護ルール（必要になったら追加）
- セマンティックリリース自動化（必要になったら）
- 過度なテスト網羅（致命的な計算ロジックのみ重点的にカバー）
