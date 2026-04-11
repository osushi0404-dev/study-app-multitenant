# I036 自動テスト: workflow.md の /retro 必須化

## テスト概要
ドキュメント変更のみのイシューのため、自動テスト（pytest / Jest）は対象外。
ファイル存在確認と文言確認をスクリプトで実施する。

## 自動確認項目

| No | 確認内容 | コマンド | 期待結果 | 実結果 | 備考 |
|---:|---------|---------|---------|--------|------|
| 1 | workflow.md に `（任意）` という表記が残っていないこと | `grep -n "任意" docs/runbooks/workflow.md` | マッチなし（0 件） | OK | |
| 2 | workflow.md に「必須」の文言が含まれること | `grep -n "必須" docs/runbooks/workflow.md` | retro に関連して少なくとも 1 件マッチ | OK | 行 31・60 にマッチ |

## 備考
- Backend / Frontend のコード変更なし
- pytest・Jest の実行は不要
