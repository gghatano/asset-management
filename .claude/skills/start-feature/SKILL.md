---
name: start-feature
description: 新しい作業を始めるときに、`develop` を最新化したうえで `feature/*` ブランチと git worktree を切る手順を案内する。「新機能の作業を始めたい」「worktree を切って」「ブランチを作って作業したい」などのときに使う。
---

# feature ブランチと worktree の作成

`docs/development.md` の「3. git worktree 運用」に準拠する。

## 1. ブランチ名を決める

| 種別 | プレフィックス | 例 |
| --- | --- | --- |
| 新機能 | `feature/` | `feature/fetch-prices` |
| バグ修正 | `fix/` | `fix/portfolio-calc-rounding` |
| 設定・依存 | `chore/` | `chore/bump-uv` |
| ドキュメントのみ | `docs/` | `docs/update-spec` |

kebab-case、短く要点を表す名前にする。

## 2. 前提

- リポジトリ本体（`main` チェックアウト済み）が `~/work/asset-management/` にある想定
- worktree 親ディレクトリは `~/work/asset-management.wt/`
- 初回のみ `mkdir -p ~/work/asset-management.wt && git worktree add ~/work/asset-management.wt/develop develop` で develop の worktree を作っておく

## 3. 手順

```bash
# 1. develop を最新化
cd ~/work/asset-management.wt/develop
git pull --ff-only

# 2. feature ブランチを切ってリモートに登録
git switch -c feature/<name>
git push -u origin feature/<name>

# 3. 並行作業のために本体側から worktree を切る
cd ~/work/asset-management
git worktree add ../asset-management.wt/feature-<name> feature/<name>

# 4. その worktree で開発開始
cd ../asset-management.wt/feature-<name>
uv sync
```

## 4. 作業中の注意

- 同じブランチを 2 つの worktree でチェックアウトしない
- `.venv` は worktree ごとに作る（`uv sync` を毎回実行）
- コミット前に `uv run ruff check . && uv run ruff format --check .` を回しておくと CI で落ちにくい

## 5. マージ後のクリーンアップ

```bash
cd ~/work/asset-management
git fetch --prune
git worktree remove ../asset-management.wt/feature-<name>
git branch -d feature/<name>
```
