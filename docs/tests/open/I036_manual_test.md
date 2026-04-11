# I036 手動テスト: workflow.md の /retro 推奨化

## テスト概要
`docs/runbooks/workflow.md` の `/retro` が「推奨」として記載され、省略可能ケースの基準が明記されていることを確認する。

## テストケース

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `docs/runbooks/workflow.md` のフロー step 7 を確認する | `/retro` に `（任意）` という表記がなく、「推奨（テスト OK 後は原則実施）」相当の文言がある | Claude | - | |
| 2 | `docs/runbooks/workflow.md` のフロー step 7 を確認する | 省略可能なケース（小規模修正等）の基準が明記されている | Claude | - | |
| 3 | `docs/runbooks/workflow.md` のスキル呼び出しルール表（test OK 後）を確認する | `/retro` を先に案内し推奨である旨の文言がある | Claude | - | |
| 4 | `CLAUDE.md` を目視確認する | `/retro` に関する直接的な変更がなく、workflow.md 参照のみであることを確認 | Claude | - | |

## 合否判定
- すべてのテストが OK: テスト合格
- 1 つでも NG: 修正後に再テスト
