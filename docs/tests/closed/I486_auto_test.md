# I486 自動テスト: 敵対的レビューの実験の環境（コンテナ）と空振りの見分けを決定論にする

実行コマンド: 下の「決定論ゲート」。pytest・Jest・E2E は変えないので CI に任せる（`harness-tests` がハーネステストを流す）。

| TC | 内容 | 期待値（合格＝exit 0） | 失敗の注入（FG） | 結果 |
|---|---|---|---|---|
| TC-01 | `test_i197_adversarial_process.sh` の A39〜A45（計画 4-2）と既存の A・L・S・FG | 最終行 `pass=N fail=0`・exit 0。A39: exit 0・`docker_calls` に `compose up -d --build --wait backend`・記録に `コンテナ: backend を起こして確かめた`。A40・A41: exit 2・`ADVERSARIAL_ERROR: CONTAINER`・claude の呼び出し 0。A42: `docker_calls` 無し。A43: exit 0・OK。A44: V1 `未検証`。A45: 2 回目の入力に `P1-E2 から`・出し直しで V1 `確認済み（実験）`。A46（計画変更）: 1 周目に backend の変更あり・記録だけ直した 2 周目でも `docker_calls` の `compose up` が 2 行 | テスト自身の FG-A40〜FG-A46（FG-A46: 判定を見る範囲に戻すと up が 1 行）（守りを一時の写しで外すと対応する A が不合格の値になる）。実装前に A39〜A45 が FAIL になることも確かめる（計画 5 のステップ 1） | 実装前は A39〜A42・A44・A45 と FG が FAIL（pass=140 fail=14）。実装後 pass=154 fail=0。code-review.sh の決定論ゲートでも exit=0 |
| TC-02 | 台帳から F1・F2・F6・F7・F8 が消えた | `! grep -q` が exit 0（下のゲート 5 行） | 今の台帳（行がある）に対して実行すると exit 1 | 実装前 exit 1（FG）→ 実装後 exit 0（code-review.sh の決定論ゲート） |
| TC-03 | review-gate の §3-1 から手で起こす手順が消えた | `! grep -q` が exit 0 | 今の SKILL.md（行がある）に対して実行すると exit 1 | 実装前 exit 1（FG）→ 実装後 exit 0（code-review.sh の決定論ゲート） |

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

## 実行記録
- 2026-11-13 09:07 `bash scripts/claude/code-review.sh I486` の決定論ゲート 7 行 → すべて exit 0（docs/reviews/I486_code_review_20261113_0907.md）。test-gate に任された重いテストは無し
- 2026-11-13 10:23 F1 の直しの後 `bash scripts/claude/code-review.sh I486` の決定論ゲート → exit 0（docs/reviews/I486_code_review_20261113_1023.md）。test_i197 pass=156 fail=0（A46・FG-A46 を含む）
