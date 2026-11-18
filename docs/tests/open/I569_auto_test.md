# I569 自動テスト: イシューの番号の検査が 3 桁固定で、I1000 から流れ全体が止まる

実行コマンド: ハーネスのスクリプトの変更だけのため、pytest・Jest・E2E は CI に任せる（このイシューでは足さない）。ハーネスのテストは下の決定論ゲート（CI の Harness Tests でも `scripts/claude/tests/run-all.sh` が流す）。

結果:
- backend: 対象外（変更なし）
- frontend: 対象外（変更なし）

## テストケース
テストはすべて `scripts/claude/tests/test_i569_issue_number_digits.sh`（新規・1 本）に置く（TC-10 だけ既存のテスト）。合否はファイル全体の exit code（全項目合格で 0・1 つでも不合格で 1）。各項目は `PASS`／`FAIL <名前> expected=… got=…` を出す。

| TC | 確かめること | 期待値（各項目） |
|---|---|---|
| TC-01 | `flow-stage.sh`: 一時の `REVIEW_DIR`（`open/I1000_review.md` に `STAGE_DONE: plan NEXT: plan-review` の 1 行）で `I1000` を渡すと次の段階を返す。`I12345` も同じ。`I999`（3 桁の回帰）も同じ。`I12`・`I1a`・`I1000x`・空は断る | `I1000`・`I12345`・`I999`: exit 0 で出力に `NEXT_STAGE: plan-review`。不正な 4 値: exit 2 で出力に `使い方` |
| TC-02 | `gate-check.sh`: `I1000` は番号の確かめを通る（記録が無いので別の理由で落ちる）。不正な値は使い方の誤りで断る | `I1000`: 出力に `使い方` を含まない。`I12`・`I1a`・空: exit 1 で出力に `使い方` |
| TC-03 | `adversarial-review.sh`: `I1000` は番号の確かめを通る（イシューファイル・計画書が無いので、レビュー役を起こす前に止まる）。不正な値は断る | `I1000`: 出力に `ADVERSARIAL_ERROR: USAGE` を含まない（`FILES` か、flock の無い環境では `FLOCK`）。`I12`・`I1a`・空: exit 2 で出力に `ADVERSARIAL_ERROR: USAGE` |
| TC-04 | `check-frontend-evidence.sh`: `BASE_REF=HEAD` で `I1000` を渡すと「対象外」で合格。不正な値は断る | `I1000`: exit 0。`I12`・`I1a`・空: exit 2 で出力に `使い方` |
| TC-05 | `check-manual-test-executor.sh`: `I1000` は番号の確かめを通る（文書が無いので別の理由で落ちる）。不正な値は断る | `I1000`: 出力に `使い方` を含まない。`I12`・`I1a`・空: exit 2 で出力に `使い方` |
| TC-06 | close のスキルの番号の確かめ: `.claude/skills/close/SKILL.md` の `ISSUE_NUM" =~` の行から正規表現を取り出し、bash で評価する | 取り出せる（空でない）。`1000`・`12345`・`569`: 一致。`12`・`1a`・`1000x`・空: 不一致 |
| TC-07 | 見張りの画面確認の保存先（`pretooluse_guard.py`・`mcp__playwright__browser_take_screenshot` の `filename`） | `.evidence/I1000/a.png`・`.evidence/I569/a.png`: exit 0（通す）。`.evidence/I12/a.png`・`.evidence/I1a/a.png`・`.evidence/I1000/../../backend/.env`・`.evidence/I1000/sub/x.txt`・`/tmp/x.png`: exit 2（止める） |
| TC-08 | 開始時の文脈（`sessionstart_context.py` の `format_context`） | 題 `feat: I1000 x` → 出力に `#1 I1000 2026-11-18`。題 `I12: x` → `#2 -`。題 `fix: I1000x y` → `#3 -`。題 `I569: x` → `#4 I569 2026-11-18` |
| TC-09 | 3 桁固定の書き方の走査: 追跡しているファイルのうち `scripts/`・`.claude/`・`.github/`・`.pre-commit-config.yaml`（このテストファイル自身は除く）に、`I[0-9]{3}`（後ろが `,` 以外）・`^[0-9]{3}$`・`I[0-9][0-9][0-9]`・`I\d{3}`（後ろが `,` 以外）が無い | 当たり 0 件で合格。当たりがあれば `ファイル:行` を出して不合格 |
| TC-10 | 関係する今のテストが変わらず通る（見張りの保存先・開始時の文脈・画面確認の記録・実施者の確かめ・流れのつなぎ） | 下のゲートの 2〜6 行目がそれぞれ exit 0 |

### 失敗の注入（FG・同じテストファイルの中で行う。本物のファイルは書き換えない）
| FG | 何を壊すか | 期待値 |
|---|---|---|
| FG-01 | TC-09 の走査の関数を、一時のフォルダ（`scripts/a.sh` に `[[ "$X" =~ ^I[0-9]{3}$ ]]`・`.claude/skills/b/SKILL.md` に `^[0-9]{3}$`・`scripts/c.py` に `re.compile(r"I[0-9]{3}/")`・`scripts/d.sh` に `I[0-9][0-9][0-9]` を置いたもの）に流す。あわせて `^I[0-9]{3,}$` だけを置いたフォルダにも流す | 4 形を置いたフォルダ: 不合格（4 件とも当たる）。`{3,}` だけのフォルダ: 合格（0 件） |
| FG-02 | `flow-stage.sh` の写しで番号の確かめの `if` を `if false; then` に置き換え、`I1a` を渡す | 写しに置換が入った（元と違う）・出力に `使い方` が出ない（TC-01 の「不正な値を断る」がこの壊れ方を捕まえる） |
| FG-03 | `pretooluse_guard.py` の写しで `_EVIDENCE_FILE_RE` の正規表現を `r".*"` に置き換え、`.evidence/I1000/../../backend/.env` を渡す | 写しに置換が入った・exit 0（素通し。TC-07 の「止める」がこの壊れ方を捕まえる） |
| FG-04 | close のスキルの写しで番号の確かめの正規表現を `.*` に置き換え、TC-06 と同じ取り出しで `1a` を評価する | 写しに置換が入った・一致（TC-06 の「不一致」がこの壊れ方を捕まえる） |

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i569_issue_number_digits.sh
bash scripts/claude/tests/test_i187_mcp_filename_guard.sh
bash scripts/claude/tests/test_sessionstart_context.sh
bash scripts/claude/tests/test_check_frontend_evidence.sh
bash scripts/claude/tests/test_check_manual_test_executor.sh
bash scripts/claude/tests/test_i193_official_flow.sh
```

## FG の実行記録
- 2026-11-18（計画の時点・実装前）: テストファイルは実装のステップ 1 で作るため、TC-01〜TC-09・FG-01〜FG-04 は実装前のため未実行。走査の対象（TC-09）は、計画の時点の grep で今のリポジトリに 8 か所の当たりがある（＝今は不合格になる）ことを確かめた（計画書の調査結果 2）。`bash scripts/claude/flow-stage.sh I1000` が exit 2（TC-01 の `I1000` の側が今は不合格）も確かめた
- 実装後の合否は review-gate の決定論ゲートの実走で記録する
