# I605 自動テスト: ほかのワークツリーの画像の移行と片付け

実行コマンド（例）: なし（コードを変えない。正は CI の backend・frontend のテスト）

結果:
- backend: （review-gate の CI の結果を書く）
- frontend: （同上）

| TC | 対象 | 手順 | 期待値 | 結果 |
|---|---|---|---|---|
| TC-01 | 手順書だけの変更で既存のテストが壊れない（AC7） | PR #608 の CI（`.github/workflows/ci.yml`）の結果を review-gate の `code-review.sh` が確かめる | backend・frontend のテストがすべて成功（失敗 0） | 実装前のため未実行 |

## 決定論ゲート（自動実走）
<!-- 決定論ゲートは無い。手順書の文言は意図的な変更でしか変わらず、レビューで見る（plan-writing-rules.md「決定論テストの対象の選び方」）。
     手順書の空にする SQL とテストの CLEAR_IMAGE_DIRECTORY_SQL の一致は手動 M8 で見る -->

## 実行記録
-
