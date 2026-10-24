# I181 自動テスト: レビュー工程の余分・過剰を見直して開発を速くする

実行コマンド: `bash scripts/claude/tests/test_adversarial_trigger.sh` / `bash scripts/claude/tests/test_i181_review_slim.sh` ＋ 既存の review 関連テスト（R 群）

- アプリ（backend / frontend）のコード変更は無いため pytest・Jest・E2E は対象外。
- すべて、`code-review.sh` の関数を source して呼ぶか、一時 git リポジトリ・複製ファイル・指示ファイルの読み取りで動く決定論テスト。各スクリプトは全 TC 合格で exit 0、1 つでも不合格なら非ゼロで終わる（**合否は exit code**）。
- 否定・不在・回帰を見る TC には失敗注入（FG）を付け、スクリプトの中で毎回、注入した複製に当てて不合格になることを確かめる（正常系だけで合格する false-green を防ぐ）。

結果:
- backend: 対象外（コード変更なし）
- frontend: 対象外（コード変更なし）
- 計画時（実装前・2026-10-24）: 下記「ベースライン」
- 実装前の赤（ステップ 1）: （実装時に記録）
- 実装時: （実装時に記録）

## ベースライン（実装前・2026-10-24）
| テスト | 結果 |
|-------|------|
| `test_adversarial_trigger.sh` | pass=40 fail=0 |
| `test_review_gates.sh` | PASS=67 FAIL=0 |
| `test_review_verdict.sh` | PASS=55 FAIL=0 |
| `test_fix_review.sh` | pass=97 fail=0 |
| `test_review_commit_lifecycle.sh` | PASS=30 FAIL=0 SKIP=1（shellcheck 未インストール） |
| `test_i182_docs.sh` | pass=9 fail=0 |

## テストケース

### P. パス判定（`scripts/claude/tests/test_adversarial_trigger.sh` を更新）
テスト環境: `REVIEW_LIB_SOURCE_ONLY=1 source scripts/claude/code-review.sh` で関数だけを読み込み、`path_risk_trigger "<改行区切りのパス>"` の出力（YES/NO）を見る。既存の `detect_risk_flag`・`combine_risk`・`adversarial_stage_decision`・`emit_decision_lines` の TC（risk・combine・decision・emit・wire の 4 行を除く）は変えない。

| TC | 入力 | 期待 |
|----|------|------|
| P1 | 例外の各パス（1 つずつ）: `.github/workflows/ci.yml`・`.github/workflows/e2e.yml`・`.github/CODEOWNERS`・`.pre-commit-config.yaml`・`.secrets.baseline`・`scripts/claude/hooks/pretooluse_guard.py`・`.claude/settings.json`・`.claude/settings.local.json` | 8 件とも YES |
| P2 | 例外に当たらないハーネスの各パス（1 つずつ。旧テストで YES だったものを NO に書き換え）: `scripts/git-hooks/pre-push`・`scripts/claude/code-review.sh`・`scripts/claude/tests/test_review_gates.sh`・`scripts/claude/hooks/posttooluse_check.py`・`.claude/skills/code-review/SKILL.md`・`.claude/review-agents/code-reviewer.md`・`.claude/agents/reviewer.md`・`CLAUDE.md`・`docs/runbooks/workflow.md`・`docs/runbooks/review-rules.md` | 10 件とも NO |
| P3 | I180 と同じ形（再発防止）: `.claude/skills/retro/SKILL.md` と `scripts/claude/tests/test_i180_retro_triage.sh` の 2 行 | NO |
| P4 | 似た名前（先頭一致・完全一致の確認）: `docs/.github/x.md`・`backend/.pre-commit-config.yaml`・`.secrets.baseline.bak`・`scripts/claude/hooks/pretooluse_guard.py.orig`・`.claude/settings.json.bak`・`backend/app/views.py`・空入力 | 7 件とも NO |
| P5 | 名前変更（再発防止）: 一時 git リポジトリ（`develop` に `.github/workflows/ci.yml`、`feat` で `git mv` して `off.yml`）で、`code-review.sh` の `GIT_FILES=` 行と同じ git コマンド（`git -c core.quotePath=false diff develop...HEAD --name-only --no-renames`）の出力を `path_risk_trigger` に渡す | YES |
| P6 | 混在: `backend/app/views.py`・`frontend/src/App.tsx`・`.github/workflows/ci.yml` の 3 行 | YES |
| P7 | 配線（厳密文字列）: `code-review.sh` に `GIT_FILES=$(git -c core.quotePath=false diff origin/develop...HEAD --name-only --no-renames)` の行がある（`grep -qF`）。既存の wire 4 行も残す | exit 0 |
| FG-P1 | 失敗注入: `code-review.sh` を一時ディレクトリへ複製し、`path_risk_trigger` の `case` 行から例外のパターンを 1 つずつ外した 6 通りの複製を作る（外せたことを確かめ、外せなければその FG 自体を不合格）。それぞれを source して、外したパターンに当たる P1 の入力を渡す | 6 通りとも NO（＝P1 が一覧の欠落を捕まえることの証明） |
| FG-P2 | 失敗注入: P5 と同じ一時リポジトリで `--no-renames` を付けない git コマンドの出力を渡す | NO（＝P5 が名前変更のすり抜けを再現していることの証明） |

### D. 指示ファイル・runbook の記述（新規 `scripts/claude/tests/test_i181_review_slim.sh`）
テスト環境: 指定した見出しから次の同じ深さの見出しまでを「節」として切り出し（`test_i182_docs.sh` と同じ方式）、必要な語の有無を見る。各 FG はファイルの複製に注入して当てる。

| TC | 内容 | 期待 |
|----|------|------|
| D1 | `.claude/skills/code-review/SKILL.md` の `## 3.` の節に `15 分`・`攻め筋は 1 体 3 本`・`1 周 3 体`・`イシュー全体で 2 周`・`REVIEWED_COMMIT`・`ROUNDS:`・`{REVIEW_BASE}`・`run_in_background`・`sleep 900`・`TaskStop`・`時間切れ` がある | exit 0 |
| D2 | `.claude/skills/code-review/SKILL.md` と `docs/runbooks/review-rules.md` に `最大 3 周`・`総数 15`・`loop-until-dry`・`動的観点`・`最大 5 エージェント` が無い（`! grep -q`） | exit 0 |
| D3 | SKILL.md の `## 3.` の節と、review-rules.md の `## 高リスク変更の敵対的レビューステージ` の節の両方に `種類ごと`・`止める場所・方式の見直し` がある | exit 0 |
| D4 | `.claude/review-agents/adversarial-reviewer.md` に `{REVIEW_BASE}`・`攻め筋は最大 3 本`・`12 分`・`15 分`・`ulimit -v`・`timeout 60`・`処理量の欠陥` がある。「守る範囲（脅威モデル）」の節（A10）に `普通の書き方による事故`・`わざと回避する書き方`・`Low`・`件数に数えない`・`danger-ops.md` がある | exit 0 |
| D5 | review-rules.md の `## 高リスク変更の敵対的レビューステージ` の節に `GitHub が最後の守り`・`danger-ops.md`・`path_risk_trigger`・例外の 6 パターン（`.github/*`・`.pre-commit-config.yaml`・`.secrets.baseline`・`scripts/claude/hooks/pretooluse_guard.py`・`.claude/settings.json`・`.claude/settings.local.json`）がある | exit 0 |
| D6 | 集合の一致: `code-review.sh` の `path_risk_trigger` の `case` 行のパターン集合 ＝ `code-reviewer.md` の「【harness 固有】GitHub から復旧できない例外」の行のバッククォートのパターン集合（`scripts/claude/code-review.sh` などの参照用のパスは、`(正は` 以降を除いて比べる）＝ `plan-reviewer.md` の同じ行のパターン集合 | exit 0 |
| D7 | `.claude/skills/fix-loop/SKILL.md` の手順 3（`3) 対応方法` から `3.5)` の前まで）と、`plan-reviewer.md` の `### P8.` の節の両方に `新しい安全装置`・`復旧`・`最後の守り`・`danger-ops.md`・`I179 retro P1` がある | exit 0 |
| D8 | D1・D3・D4・D5 の節の中でバッククォートで書いたパス（`/` を含むもの。`<…>`・`*`・`{`・空白を含むものは除く）が実在する（`test_i182_docs.sh` の DOC6 と同じ方式） | exit 0 |
| D9 | `code-reviewer.md` の「高リスク判定の条件」の節に、アプリの条件 11 項目（`認証・認可・ロール変更` 〜 `画面制御していてもAPI直叩きで事故りうる変更`）が残り、`【harness 固有・Yes にしない】` の行がある。旧行 `【harness 固有】hooks・ガード・権限設定・レビュー基盤` と `【harness 固有】指示階層` が無い | exit 0 |
| D10 | 4-9（棚卸しで減らすもの）: review-rules.md の `## 高リスク変更の敵対的レビューステージ` の節に `計画レビューのやり直しは、計画の方式・範囲・受け入れ条件を変えたときだけ` がある（動的観点の削除は D2 で見る） | exit 0 |
| FG-D10 | review-rules.md の複製の対象の節からその 1 項目を消す → D10 | 非ゼロ |
| FG-D1 | SKILL.md の複製から `sleep 900` を消す → D1 | 非ゼロ |
| FG-D2 | review-rules.md の複製に `最大 3 周` を足す → D2 | 非ゼロ |
| FG-D3 | review-rules.md の複製の対象の節から `止める場所・方式の見直し` を消す → D3 | 非ゼロ |
| FG-D4 | adversarial-reviewer.md の複製から `ulimit -v` を消す → D4／複製の「守る範囲」の節から `件数に数えない` を消す → D4 | どちらも非ゼロ |
| FG-D5 | review-rules.md の複製の対象の節から `.secrets.baseline` を消す → D5 | 非ゼロ |
| FG-D6 | code-reviewer.md の複製の例外の行から `.github/*` を消す → D6／plan-reviewer.md の複製の例外の行に `CLAUDE.md` を足す → D6 | どちらも非ゼロ |
| FG-D7 | fix-loop/SKILL.md の複製から追加した 1 項目を消す → D7 | 非ゼロ |
| FG-D8 | SKILL.md の複製の `## 3.` の節に `` `docs/runbooks/no_such_file.md` `` を足す → D8 | 非ゼロ |
| FG-D9 | code-reviewer.md の複製から `マルチテナント境界変更` を消す → D9 | 非ゼロ |

### R. 回帰
| TC | コマンド | 期待 |
|----|------|------|
| R1 | `bash scripts/claude/tests/test_adversarial_trigger.sh`（P 群を含む更新後） | fail=0（exit 0） |
| R2 | `bash scripts/claude/tests/test_review_gates.sh` | FAIL=0（exit 0） |
| R3 | `bash scripts/claude/tests/test_review_verdict.sh` | FAIL=0（exit 0。code-reviewer.md・plan-reviewer.md の VERDICT 契約が壊れていない） |
| R4 | `bash scripts/claude/tests/test_fix_review.sh` | fail=0（exit 0。fix-loop/SKILL.md の既存の手順が壊れていない） |
| R5 | `bash scripts/claude/tests/test_review_commit_lifecycle.sh` | FAIL=0（exit 0） |
| R6 | `bash scripts/claude/tests/test_i182_docs.sh` | fail=0（exit 0。review-rules.md の I182 の節が壊れていない） |
| R7 | `bash -n scripts/claude/code-review.sh`・`bash -n scripts/claude/tests/test_adversarial_trigger.sh`・`bash -n scripts/claude/tests/test_i181_review_slim.sh` | exit 0 |

## 決定論ゲート（自動実走）
<!--
  code-review.sh が下の ```bash ブロックを 1 行 1 コマンドで実走し、実 exit code を VERDICT に注入する。
  許可（実走）: `bash scripts/claude/tests/*.sh` / `grep -q 文言 file` / `! grep -q 文言 file` / `python3 -m json.tool file` / `bash -n file` / `python3 -m py_compile file`
  1 行 1 コマンド・チェーン不可。
-->
```bash
# P 群・既存の判定の TC（R1）
bash scripts/claude/tests/test_adversarial_trigger.sh
# D 群
bash scripts/claude/tests/test_i181_review_slim.sh
# R2〜R6
bash scripts/claude/tests/test_review_gates.sh
bash scripts/claude/tests/test_review_verdict.sh
bash scripts/claude/tests/test_fix_review.sh
bash scripts/claude/tests/test_review_commit_lifecycle.sh
bash scripts/claude/tests/test_i182_docs.sh
# R7
bash -n scripts/claude/code-review.sh
bash -n scripts/claude/tests/test_adversarial_trigger.sh
bash -n scripts/claude/tests/test_i181_review_slim.sh
```

## 計画時の自己検証
- P 群・D 群のスクリプトは実装ステップ 1 で作る（計画時点では対象の実装が無いので実行できない）。各 FG は、スクリプトの中で注入した複製に当てて非ゼロ（P 群は期待と違う NO）になることを毎回確かめる形にしてある。
- P5・FG-P2 の前提（名前変更が既定では新しい名前だけになる）は、計画時のスパイクで確認済み（計画書 3-2）。
- 計画時に実行できたものはベースライン（上表）とスパイク（計画書 3-2）。
