# I202 自動テスト: I197・I205 の台帳に残った指摘と、見送った共通化を片付ける

実行コマンド（例）: アプリのコード変更が無いため `docker compose exec backend python -m pytest`・`docker compose exec frontend npm test`・E2E は非該当（CI では今までどおり動く）

結果:
- backend: 非該当
- frontend: 非該当

## テストケース

合否はすべて終了コード（合格=exit 0・不合格=非ゼロ）。否定の判定（「止まらない」「変わらない」「NO のまま」）には失敗注入（FG: 本体の一時コピーの判定の要を壊すと、対応する項目が不合格になることを確かめる）を付ける。実際の claude は使わない（`CLAUDE_BIN` にスタブを渡す。`test_i205_stop_criteria.sh` の W 群と同じやり方）。

| TC | 内容 | 期待値 | 結果 |
|---|---|---|---|
| TC-01 | `bash scripts/claude/tests/test_i202_ledger_cleanup.sh`（新設）。下の R・L・W・A・G・D の各項目と FG | exit 0・`fail=0` | 実装前のため未実行 |
| TC-02 | `bash scripts/claude/tests/test_i197_review_ledger.sh`（R17・FG-R17 を消し、R14 の 3 周目に FG・R16 のコメントと FG の分割）・`bash scripts/claude/tests/test_i205_stop_criteria.sh`（H7 の設定の後片付け・H10 の追加） | どちらも exit 0・`fail=0`（ベースライン: 64・90 項目） | 実装前のため未実行（ベースラインは計画の調査結果のとおり pass=64・pass=90） |
| TC-03 | 影響を受けうるテスト: `test_adversarial_trigger.sh`・`test_i193_official_flow.sh`・`test_i181_review_slim.sh`・`test_i197_adversarial_process.sh`・`test_review_commit_lifecycle.sh`・`test_review_gates.sh`・`test_review_verdict.sh` | どれも exit 0 | 実装前のため変更後は未実行。ベースライン（2026-10-27・develop 33d2e29）: `test_adversarial_trigger.sh` pass=60・`test_i193_official_flow.sh` pass=160・`test_i181_review_slim.sh` pass=29・`test_i197_adversarial_process.sh` pass=115・`test_review_commit_lifecycle.sh` PASS=30 SKIP=1・`test_review_gates.sh` PASS=67・`test_review_verdict.sh` PASS=58（どれも fail=0） |
| TC-04 | `bash scripts/claude/tests/run-all.sh`（CI の Harness Tests ジョブで確かめる。手元では流し直さない） | CI の Harness Tests が pass | 実装前のため未実行 |

### TC-01 の項目
一時の git リポジトリ（develop に `backend/x.py`〔20 行〕・`scripts/claude/a.sh`〔20 行〕・`.github/workflows/ci.yml`〔20 行〕を置き、feature ブランチで行を変える）と、手書きの FINDING 行・台帳で確かめる。

R F5（計画の見立てを超えた高リスクの目印・AC1）:
- R1 `FINDING: F1 SEV=Low … STOP=- RISK=up | m` を読める（形の崩れにならない）。台帳の行が `RISK=up` を持つ。`RISK=` の無い FINDING 行は `RISK=-`
- R2 `RISK=down`・`RISK=` のような値は形の崩れ（`ledger_update` が 2）
- R3 `ledger_risk <台帳>`: `RISK=up` の行が 1 行あれば `YES`、無ければ `NO`。前の形（`RISK=` の欄の無い I205 の形・I197 の形）の台帳の行だけなら `NO`
- R4 書き直し: 前の周で `RISK=up` の指摘を、同じ番号で `RISK=` なしに書き直しても `RISK=up` が残る
- R5 目印は止めるかどうかを変えない: harness・`SEV=Low STOP=- RISK=up`・再現あり → `ledger_verdict` は OK
- R6 本体の通し（スタブ・計画レビューの判定 No・パスの判定 NO）: スタブのレビュー役が `RISK=up` の FINDING 行を書く → `ADVERSARIAL_STAGE: REQUIRED`・記録の `RISK: YES`・証跡に `台帳の目印=YES`
- R7 R6 の後、目印の無い差分のレビュー（2 周目）→ `ADVERSARIAL_STAGE: REQUIRED` のまま
- R8 R6 の後、rebase で前の `REVIEWED_COMMIT` が祖先でなくなった全体のレビュー（目印なし）→ `REQUIRED` のまま（前の記録の台帳を見る）
- R9 目印が一度も無い通し → `ADVERSARIAL_STAGE: NOT_REQUIRED`・`RISK: NO`
- R10 R6 の記録で `gate-check.sh` を動かす → 敵対的レビューの記録を求めて exit 1（`REASON=missing`）

L 判定の穴（AC2）:
- L1 I205-F3: guard のファイル（`.github/workflows/ci.yml`）の、ブランチで触っていない行（`LINE=1`）の High（再現なし）→ delta・HIGH。ブランチが変えていない guard のファイルの High → outside・OK
- L2 I205-F4: `FILE=.GITHUB/workflows/ci.yml` の種類は guard。`FILE=Scripts/Claude/a.sh` は harness
- L3 I205-F5: 要約に `| 再現:` を含む行 `… | 要約 A | 再現: x の中身 | 再現: 本当の再現` → 台帳の要約が `要約 A | 再現: x の中身`・REPRO=yes。`| 再現: なし`・`| 再現: -`・`| 再現: None`・`| 再現:  N/A ` → REPRO=no。`| 再現: なしでも落ちる` → REPRO=yes
- L4 I197-F12: 1 回のレビューで新しい番号 `F3` を 2 回書く → 台帳に F3 が 1 行だけ（`F4` に振り直されない）。前の周の resolved の番号を使った行は、今までどおり新しい番号に振り直す
- L5 I197-F18: リポジトリの中の実在のファイル `..foo.sh`（ブランチで変えていない）への High → outside。`../x` → delta
- L6 台帳の限界: 前の周に止めない open の指摘 F2（harness・`STOP=-`）がある差分のレビューで、レビュー役が `FINDING: F2 … STATUS=resolved` と書く → 台帳の F2 が resolved（新しい番号に振り直されない）。書かなければ open のまま
- L7 `ledger_open_rest <台帳>`: `STATUS=open` で止めない行だけを出す（止める行・resolved の行は出ない）

W 本体の細部（スタブで通し）:
- W1 差分のレビューで、レビュー役への入力に `#### 台帳の残り` の節があり、止めない open の指摘の番号が出る
- W2 I197-F13: 前の台帳が空の差分のレビューの入力に `台帳の最大の番号: なし（新しい指摘は F1 から）` があり、`台帳の最大の番号: F` の行が無い
- W3 I197-F14: レビュー役が失敗（スタブが exit 1）→ 証跡に `読める FINDING 行が無い` が無い。FINAL_VERDICT は BLOCKER
- W4 空の範囲: 起点の後に記録の場所だけを変えた差分のレビュー → レビュー役（`--agent code-reviewer`）も組み込みの `/code-review` も呼ばれない。前の周の止める指摘が残っていれば FINAL_VERDICT は HIGH、無ければ OK。記録に `LEDGER_ROUND: 2`
- W5 I205-F9: 記録の「## 止める指摘」の節の見出しの次に `（再現は本文の同じ番号の FINDING 行）`

A 敵対的レビュー（`adversarial-review.sh`・claude のスタブ）:
- A1 F6: 2 観点の実験役のスタブが、それぞれ始まりと終わりの時刻をファイルに書く（1 秒待つ）→ 区間が重ならない
- A2 F7: 前の記録の `REVIEWED_COMMIT` が HEAD の祖先でない → `review_base` が `ADV_BASE` を返す。祖先なら SHA を返す
- A3 F8: 拒否の件数を読めない（`claude_log_denials` が失敗するログ）→ その観点の拒否が `読めない`・VERDICT が OK にならない
- A4 空の括弧: note が空の観点の「観点ごとの実行」の行に `報告あり（）` が無い

G 共通化（gate-check の挙動を変えない）:
- G1 `review_records I### code_review` が、`docs/reviews/` と `docs/reviews/closed/` の記録をファイル名の時刻順に出す（`_2` の付いた同じ分の記録はその後ろ）
- G2 `record_reviewed_commit`: 最後の `REVIEWED_COMMIT:` の SHA。無ければ空
- G3 `branch_own_files develop <rev>`: 改行・引用符を含まないが空白・`[` を含むパス（`docs2/a [b].md`）がそのままの名前で出る。記録の場所は出ない
- G4 一時リポジトリで、OK の記録・レビューの後の変更あり・高リスクで敵対的レビューなし、の 3 つの状態の `gate-check.sh` の出力（`GATE_CHECK:` の行と終了コード）が、付け替える前の `gate-check.sh`（テストの中で develop 33d2e29 の版の `gate-check.sh` と `code-review.sh` を `git show` で取り出し、`GATE_CHECK_LIB` で組み合わせたもの）と同じ
- G5 I205-F12: `[` を含むファイル名 `x[1].txt` と `x1.txt` があり、ブランチが `x[1].txt` だけを変えた → `delta_hunks` の塊に `x1.txt` が出ない

D 指示ファイル（静的）:
- D1 `.claude/agents/code-reviewer.md` に `RISK=up`・`台帳の残り`・`消した位置の HEAD の行番号` があり、`触れていれば Blocker として FINDING 行に書く` が無い
- D2 `.claude/skills/review-gate/SKILL.md` に `台帳の目印` と `必ず確かめる項目` があり、`計画レビューの判定とパスの判定で決まり、周ごとに変わらない` が無い
- D3 `docs/runbooks/review-rules.md` に `台帳の目印` があり、`計画レビューの判定とパスの判定で決め、周ごとに変えない` が無い

FG（失敗注入。一時コピーを壊すと、その項目が不合格になる）:
- FG-R3 `risk` モードを常に `NO` にする → R3・R6 が不合格
- FG-R4 書き直しで `RISK=up` を残す処理を外す → R4 が不合格
- FG-R6 本体で `RISK_LEDGER` を `combine_risk` に入れない → R6 が NOT_REQUIRED
- FG-R8 前の記録の台帳を見ない（今回の台帳だけ）→ R8 が NOT_REQUIRED
- FG-L1 guard のファイル単位の判定を外す → L1 が OK
- FG-L2 `kind_of` の casefold を外す → L2 の 1 つ目が app
- FG-L3 最後の `| 再現:` で分けずに最初で分ける → L3 の要約が切れる。「なし」の判定を外す → `再現: なし` が REPRO=yes
- FG-L4 `seen` を外す → L4 で F4 に振り直される
- FG-L6 `shown` を止める指摘だけに戻す → L6 で F2 が新しい番号に振り直され、F2 は open のまま
- FG-W3 食い違いの検査の `REVIEWER_RAN` の条件を外す → W3 に `読める FINDING 行が無い` が出る
- FG-W4 空の範囲の扱いを外す → W4 でレビュー役が呼ばれる
- FG-A1 `flock` を外す → A1 の区間が重なる
- FG-A2 祖先の確認を外す → A2 で祖先でない SHA が返る
- FG-G5 `--literal-pathspecs` を外す → G5 で `x1.txt` が出る
- FG-D1〜D3 対象のファイルの写しから語を 1 つ消す → その D が不合格

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i202_ledger_cleanup.sh
bash scripts/claude/tests/test_i197_review_ledger.sh
bash scripts/claude/tests/test_i205_stop_criteria.sh
bash scripts/claude/tests/test_adversarial_trigger.sh
bash scripts/claude/tests/test_i193_official_flow.sh
bash scripts/claude/tests/test_i181_review_slim.sh
bash scripts/claude/tests/test_i197_adversarial_process.sh
bash scripts/claude/tests/test_review_commit_lifecycle.sh
bash scripts/claude/tests/test_review_gates.sh
bash scripts/claude/tests/test_review_verdict.sh
```
