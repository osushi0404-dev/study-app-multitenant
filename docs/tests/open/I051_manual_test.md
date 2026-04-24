# 手動テスト: I051 — e2e/.env.e2e.example を作成してローカル E2E セットアップを簡略化する

## テスト目的
`e2e/.env.e2e.example` が正しく作成されており、受け入れ条件を満たすことを確認する。

## 前提条件
- 実装完了後（`e2e/.env.e2e.example` が存在する状態）

## テストケース

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `e2e/.env.e2e.example` が存在することを確認する | ファイルが存在する | Claude | | |
| 2 | `e2e/.env.e2e.example` の内容を確認し、`E2E_TEST_PASSWORD=` の行が含まれているか確認する | `E2E_TEST_PASSWORD=` の行が存在する | Claude | | |
| 3 | `e2e/.env.e2e.example` に実際のパスワード（英数字の文字列）が含まれていないことを確認する | `E2E_TEST_PASSWORD=` の値が空（プレースホルダーのみ） | Claude | | |
| 4 | `docs/runbooks/common-commands.md` に `cp e2e/.env.e2e.example e2e/.env.e2e` コマンドが存在することを確認する | コマンドが存在する | Claude | | |
| 5 | `e2e/.env.e2e.example` が `.gitignore` の対象外であることを確認する（コミットできる状態か） | `git status` で `e2e/.env.e2e.example` が追跡対象として表示される | Claude | | |
