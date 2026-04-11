# I036 手動テスト: workflow.md の /retro 必須化

## テスト概要
`docs/runbooks/workflow.md` の `/retro` が「必須」として記載され、フロー step 7 とスキル呼び出し表の両方で必須である旨が明確になっていることを確認する。

## テストケース

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `docs/runbooks/workflow.md` のフロー step 7 を確認する | `/retro` に `（任意）` という表記がなく、「必須」の文言がある | Claude | OK | |
| 2 | `docs/runbooks/workflow.md` のフロー step 7 を確認する | `/retro` が `/close` の前のステップとして明示されている | Claude | OK | |
| 3 | `docs/runbooks/workflow.md` のスキル呼び出しルール表（test OK 後）を確認する | `/retro` が必須として案内されている | Claude | OK | |
| 4 | `CLAUDE.md` を目視確認する | `/retro` に関する直接的な変更がなく、workflow.md 参照のみであることを確認 | Human | OK | |

## 合否判定
- すべてのテストが OK: テスト合格
- 1 つでも NG: 修正後に再テスト
