---
name: release
description: `develop` の内容を `main` に取り込むリリース PR を作成・マージするときに使う。「リリースしたい」「develop を main に反映」「公開したい」などのときに発動する。
---

# リリース手順

`develop` を `main` にマージし、GitHub Pages を公開対象として更新する。`docs/development.md` の「5. リリースフロー」に準拠する。

## 1. 事前確認

- `develop` の CI が green か確認
- `develop` の動作確認（最新の dashboard が想定どおり生成されるか）
- `docs/spec.md` の更新が反映されているか
- 未マージの重要 PR が残っていないか

## 2. バージョン

セマンティックバージョニング（緩めに運用）。

- `vX.Y.0`: 機能追加・スキーマ変更
- `vX.Y.Z`: 軽微な修正

## 3. リリース PR の作成

```bash
gh pr create \
  --base main \
  --head develop \
  --title "release: vX.Y.Z" \
  --body "<このリリースに含まれる変更の要約>"
```

または GitHub MCP の `create_pull_request` を使用する。

## 4. PR 本文の例

```markdown
## このリリースに含まれる変更

- feat: ...
- fix: ...
- docs: ...

## 動作確認

- [ ] develop での dashboard 生成
- [ ] 価格取得ジョブの直近成功
```

## 5. マージ方式

- **Merge commit** を使う（Squash ではない）
- `main` 上にリリースポイントを残すため

## 6. マージ後

```bash
# 必要なら tag を打つ
git fetch origin
git checkout main
git pull --ff-only
git tag vX.Y.Z
git push origin vX.Y.Z
```

その後、`main` 側の GitHub Actions が GitHub Pages を更新する。

## 7. ロールバック

問題が発生した場合は revert PR を `main` で作成する。直接 force push はしない。

## 8. Pages デプロイの落とし穴

過去にハマった点をメモ:

- **`github-pages` environment は default branch (`main`) からしかデプロイ不可**。`develop` などからの deploy ジョブは "rejected by environment protection rules" で弾かれる。develop 用の staging を再導入したい場合は Settings > Environments > github-pages の Deployment branches に追加する
- **Public / Private 切替後に旧 protection rule が残骸として残る** ことがある。Settings > Environments で `github-pages` を一度削除して再生成すると default に戻る
- **Pages の Source は "GitHub Actions"** にする。"Deploy from a branch" だと `actions/deploy-pages` が使えない
- リリース PR をマージしてから Pages 反映まで通常 1〜2 分。`https://gghatano.github.io/asset-management/` が 403 / 404 のときは workflow の deploy ジョブのログを確認
