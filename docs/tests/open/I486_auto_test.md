# I486 自動テスト: 敵対的レビューの実験の環境（コンテナ）と空振りの見分けを決定論にする

実行コマンド: 下の「決定論ゲート」。pytest・Jest・E2E は変えないので CI に任せる（`harness-tests` がハーネステストを流す）。

| TC | 内容 | 期待値（合格＝exit 0） | 失敗の注入（FG） | 結果 |
|---|---|---|---|---|
| TC-01 | `test_i197_adversarial_process.sh` の A39〜A45（計画 4-2）と既存の A・L・S・FG | 最終行 `pass=N fail=0`・exit 0。A39: exit 0・`docker_calls` に `compose up -d --build --wait backend`・記録に `コンテナ: backend を起こして確かめた`。A40・A41: exit 2・`ADVERSARIAL_ERROR: CONTAINER`・claude の呼び出し 0。A42: `docker_calls` 無し。A43: exit 0・OK。A44: V1 `未検証`。A45: 2 回目の入力に `P1-E2 から`・出し直しで V1 `確認済み（実験）` | テスト自身の FG-A40〜FG-A45（守りを一時の写しで外すと対応する A が不合格の値になる）。実装前に A39〜A45 が FAIL になることも確かめる（計画 5 のステップ 1） | 実装前のため未実行 |
| TC-02 | 台帳から F1・F2・F6・F7・F8 が消えた | `! grep -q` が exit 0（下のゲート 5 行） | 今の台帳（行がある）に対して実行すると exit 1 | 実装前のため未実行（今は行があるので exit 1＝FG の確認は済み） |
| TC-03 | review-gate の §3-1 から手で起こす手順が消えた | `! grep -q` が exit 0 | 今の SKILL.md（行がある）に対して実行すると exit 1 | 実装前のため未実行（今は行があるので exit 1＝FG の確認は済み） |

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i197_adversarial_process.sh
! grep -q "^- F1 " docs/reviews/backlog/I228.md
! grep -q "^- F2 " docs/reviews/backlog/I228.md
! grep -q "^- F6 " docs/reviews/backlog/I228.md
! grep -q "^- F7 " docs/reviews/backlog/I228.md
! grep -q "^- F8 " docs/reviews/backlog/I228.md
! grep -q "docker compose up -d backend" .claude/skills/review-gate/SKILL.md
```
