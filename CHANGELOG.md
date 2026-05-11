# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)（緩く運用）。

## [Unreleased]

### Documentation
- `docs/spec.md` 8.2: 例示 quantity を計算結果に合わせて修正 (11828.38 → 11828.16)
- `docs/spec.md` 6.3: 外貨建て換算の `<currency_lower>_jpy` 運用と `usd_jpy` の設定例を追記
- `README.md`: Live URL / quick start / Phase 1 完了状態を反映
- `.claude/skills/release/SKILL.md`: Pages environment protection の落とし穴を追記
- `CHANGELOG.md`: 新規作成

## [0.1.0] - 2026-05-11

Phase 1: ローカルで動く最小版 + 日次バッチ (release PR #19)

### Added
- `src/fetch_prices.py`: 価格取得アダプタ (yfinance / Yahoo!ファイナンス JP / 固定値)、前回値フォールバック (#14)
- `src/generate_transactions.py`: 月次購入展開と JPY 換算 (#15)
- `src/calculate_portfolio.py`: 日次評価計算 (簿価 / 評価額 / 損益 / weight) (#16)
- `src/build_dashboard.py`: Plotly グラフとテーブル付き dashboard、`data-testid` で E2E から検証可能 (#17)
- `.github/workflows/update-portfolio.yml`: 日次バッチ (cron 22:00 UTC + workflow_dispatch) (#18)
- `.github/workflows/ci.yml`: lint / unit + integration / e2e の 3 ジョブ
- `.github/workflows/deploy-pages.yml`: main push で actions/deploy-pages 経由でルートに公開
- `tests/unit/`, `tests/integration/`, `tests/e2e/`: 87 ケース
- `config/`: 初期サンプル YAML
- `docs/spec.md`, `docs/development.md`, `CLAUDE.md`: 設計書・開発ルール・Claude Code 用指針
- `.claude/skills/`: add-asset / start-feature / release のプロジェクトスキル
- `.github/ISSUE_TEMPLATE/`, `.github/PULL_REQUEST_TEMPLATE.md`

### Notes
- Pages デプロイは `main` のみ。`develop` の確認はローカル静的サーバで行う
- `github-pages` environment の Deployment branches は `main` のみ許可で初期化される
