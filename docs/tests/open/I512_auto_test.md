# I512 自動テスト: 計画で受け入れた残余リスクを、後続イシュー・最優先から外して一覧へ回す

実行コマンド: 下の「決定論ゲート」。pytest・Jest・E2E は対象のコードが無いので対象外（CI の `scripts/claude/tests/run-all.sh` も同じテストを流す）

結果:
- 計画時のベースライン（2026-11-14・変更前）: `test_i202_ledger_cleanup.sh` pass=163 fail=0
- 実行記録（2026-11-14・implement・/simplify の後）: `bash scripts/claude/tests/test_i512_accepted_risk.sh` exit 0（pass=34 fail=0・TC-01〜TC-05・TC-07 と各 FG）／`bash scripts/claude/tests/test_i202_ledger_cleanup.sh` exit 0（pass=163 fail=0）／`bash scripts/claude/tests/test_i205_stop_criteria.sh` exit 0（pass=91 fail=0）
- 変えた文書を読む関係のテスト（test_adversarial_trigger・test_i114・test_i180・test_i181・test_i182・test_i185・test_i197 の 2 本・test_i224・test_review_verdict）は合格。test_i193_official_flow の F9（run-all.sh の 3 項目）だけが、サンドボックスで uv の一時ファイル（`~/.cache/uv`）を書けずに失敗（今回の変更と関係なし・CI が正）

共通の準備（新しいテスト `scripts/claude/tests/test_i512_accepted_risk.sh` の中）: 一時のディレクトリに計画書 `plan.md` を作る。「## 8. Risk & 回避策」の表に `| R1: a | b | 回避 |`・`| R2: c | d | 受け入れ |`・`| R4：e | f |  受け入れ  |`（全角コロン・前後の空白）を置き、その後ろに `## 9. 確定事項` の節と、節の外に `| R5: x | y | 受け入れ |` を置く。`code-review.sh` は `REVIEW_LIB_SOURCE_ONLY=1` で関数だけ読み込む。失敗の注入はテストの中で `code-review.sh` の写しを壊して流す（本物は書き換えない）。最後に「壊した写しがすべて作れた（置き換え前の文字列が本体にある）」を確かめる

| TC | AC | 内容 | 期待（合格=exit 0） | 失敗の注入 |
|---|---|---|---|---|
| TC-01 | AC1 | 台帳: A1 `SEV=Medium KIND=guard REPRO=no SECURITY=yes ACCEPTED=R2`・A2 `SEV=Medium KIND=guard REPRO=no SECURITY=no ACCEPTED=R4`・A3 `SEV=Low KIND=harness REPRO=no SECURITY=yes ACCEPTED=R2`・A4 `SEV=Medium KIND=harness REPRO=no SECURITY=yes ACCEPTED=R2`。`ledger_route issue <台帳> plan.md`・`ledger_route backlog <台帳> plan.md` | issue 側が空・backlog 側が A1〜A4 の 4 行。A1 の行は `- F1 SEV=Medium REPRO=no KIND=guard SECURITY=yes FILE=x | s1 | 一覧に回した理由: 再現なし／計画で受け入れ（R2）` と完全一致。A2 の理由は `再現なし／計画で受け入れ（R4）`（全角コロン・空白の行も読める） | FG-01a: `route_reasons()` の目印の分岐を外すと A1・A2・A4 が issue 側で不合格／FG-01b: 一覧の理由に「計画で受け入れ」を足す処理を外すと A1 の完全一致が不合格／FG-01c: `accepted_risks()` が全角コロンを読まない写しで A2 が issue 側で不合格 |
| TC-02 | AC2・AC3 | 台帳: B1 目印なし `SEV=Medium KIND=guard REPRO=no SECURITY=yes`・B2 `SEV=High KIND=guard REPRO=no SECURITY=yes ACCEPTED=R2`・B3 `SEV=Medium KIND=harness REPRO=yes SECURITY=yes ACCEPTED=R2`・B4 `SEV=Medium KIND=app REPRO=no SECURITY=yes ACCEPTED=R2`。同じ計画書で振り分ける | issue 側が B1〜B4 で、4 行とも `後続イシューにする理由:` より後ろに `SECURITY=yes` がある（最優先の条件のまま）。B4 の理由は `SECURITY=yes・アプリ本体`。backlog 側は空。標準エラーに B2・B3・B4 の `目印を使わない:` が 3 行 | FG-02a: 効く条件から `RANK[e[0]] <= 1` を外すと B2 が backlog 側で不合格／FG-02b: `e[5] == "no"` を外すと B3 が backlog 側で不合格／FG-02c: `e[3] != "app"` を外すと B4 の理由が `アプリ本体` だけになり（最優先から外れる）不合格 |
| TC-03 | AC4 | 止める判定: C1 `SEV=High KIND=guard SCOPE=delta REPRO=no SECURITY=yes ACCEPTED=R2`・C2 `SEV=Medium KIND=harness SCOPE=delta STOP=flow REPRO=yes ACCEPTED=R2`・C3 `SEV=Medium KIND=app SCOPE=delta REPRO=yes ACCEPTED=R2` の台帳と、同じ行から目印を除いた台帳。`ledger_verdict`・`ledger_blocking` を比べる | 目印あり・なしで `ledger_verdict` がどちらも `HIGH`・`ledger_blocking` の番号の並びが同じ（F1,F2,F3）。振り分けでも 3 行とも issue 側で理由に `止める指摘` | FG-03: `blocking()` の先頭に `if e[10] != "-": return False` を足した写しで、目印ありの `ledger_verdict` が `OK` になり不合格 |
| TC-04 | AC6 | 前の形と形の崩れ: (a) `ledger_update full` に目印の無い FINDING 行を通した LEDGER 行が、変更前の形（`RISK=- SECURITY=`、`ACCEPTED` の文字が無い）と完全一致 (b) 目印つきの FINDING 行は `RISK=- ACCEPTED=R2 SECURITY=` の並び (c) `parse_findings` の列の数が目印の有無で同じ 8 列 (d) `ACCEPTED=x`・`ACCEPTED=` の FINDING 行は形の崩れ（exit 2）(e) I197・I205・I202 の形の LEDGER 行（`test_i202_ledger_cleanup.sh` の Q4 と同じ行）で `ledger_verdict` が `HIGH OK`・`ledger_route backlog` が今までの行 (f) 同じ番号の書き直しで目印を外すと台帳の目印も消える | (a)〜(f) すべて期待どおり | FG-04a: `ledger_line()` が目印の無い行にも ` ACCEPTED=-` を書く写しで (a) が不合格／FG-04b: `parse` を `g[:7] + g[8:]` に戻した写しで (c) が不合格（9 列）／FG-04c: `merged()` の目印を前の値優先にした写しで (f) が不合格 |
| TC-05 | AC5 | 照合の失敗: A1 と同じ行（目印 `ACCEPTED=R2`）を、(1) 計画書の引数なし (2) 存在しないパス (3) 「## 8.」の節の無い計画書 (4) R2 の行の無い計画書 (5) R2 の処遇が `回避` (6) 目印 `ACCEPTED=R5`（節の外の行）(7) 目印 `ACCEPTED=R1`（処遇が回避）で振り分ける。さらに本物の入口 `--route issue I900`（一時のリポジトリ・計画書なし）と `--route issue ../x`・`--route issue 'I9*'` | (1)〜(7) すべて issue 側で、理由に `SECURITY=yes・guard の Medium 以上`。入口は計画書なしで issue 側・標準エラーに `計画書: なし`。`../x`・`I9*` は exit 2 | FG-05a: 目印があれば効く（why_not を空にする）写しで (1)〜(8) が backlog 側で不合格。入口: 連番の計画書 plan_I900_2.md があればそちらで照合する（find_plan_file）／FG-05b: `accepted_risks()` の節の終わりの判定を外した写しで (6) が backlog 側で不合格／FG-05c: 処遇の完全一致を「受け入れ を含む」にした写しで、`| R6: g | h | 受け入れない |` の行を足した計画書の (8) `ACCEPTED=R6` が backlog 側で不合格／FG-05d: 第 3 引数の確かめを外した写しで `../x` が exit 2 にならず不合格 |
| TC-06 | AC6（回帰） | 既存の台帳・止める判定のテスト | `bash scripts/claude/tests/test_i202_ledger_cleanup.sh`・`bash scripts/claude/tests/test_i205_stop_criteria.sh` がどちらも exit 0（`test_i202` は一覧の行の `SECURITY=` に合わせて期待を直した Q3・Q8・Q9・`BL_FORM` を含む） | 既存の各 FG |
| TC-07 | AC8 | `docs/reviews/backlog/I430.md` に F1〜F3 の行があり、`test_i202_ledger_cleanup.sh` の `BL_FORM` に合う | 新しいテストの中で `grep -qE "^- F1 SEV=Medium REPRO=no KIND=guard SECURITY=yes FILE=\.claude/settings\.json \| .* \| 一覧に回した理由: 再現なし／計画で受け入れ（plan_I430 の R2）$"`（F2・F3 も同じ形）と `BL_FORM` の照合がどれも exit 0 | FG-07: 一時の写しから F2 の行を消すと不合格 |

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i512_accepted_risk.sh
bash scripts/claude/tests/test_i202_ledger_cleanup.sh
bash scripts/claude/tests/test_i205_stop_criteria.sh
```

## 再発防止記録（fix-loop・2026-11-14）
- なぜ失敗したか: commit 時の shellcheck SC2143 に合わせて TC-07 の形の照合を `! grep … | grep -qvE` に書き換えた。pipefail の下では `grep -q` が先に終わると前の grep が SIGPIPE で終わり `!` が反転しうる（I210 の決まり）。CI の `test_pipefail_negated_grep.sh` G1 が捕まえた
- 何を変えたか: 件数の比較 `[ "$(… | grep -cvE "$BL_FORM")" -eq 0 ]` にした（SC2143 にも当たらない）。形の照合が効いていることを確かめる FG-07b（形の崩れた行を足した写しは不合格）を足した
- セキュリティ: 影響なし（テストの書き方だけ）
- 次回どう防ぐか: 手元で流すテストの選び方に、変えたファイル名を読むテストに加えて、scripts/claude の全スクリプトを走査するテスト（test_pipefail_negated_grep.sh など）を入れる
- 確かめた結果: `test_i512_accepted_risk.sh` exit 0（pass=35 fail=0）・`test_pipefail_negated_grep.sh` exit 0（pass=10 fail=0）
- 実行記録（2026-11-14・test-gate）: `bash scripts/claude/gate-check.sh I512` exit 0（GATE_CHECK: OK）。heavy の委譲は無いので手元で流し直していない（CI が正）

## 再発防止記録（fix-loop 2 回目・retro から・2026-11-14）
- なぜ失敗したか: `accepted_risks()` が同じ R 番号の受け入れでない行と、HTML コメントの中の行を考えていなかった（TC-05 の照合の失敗の列挙に「同じ番号の食い違い」「コメントの中」が無かった）。コードレビューの台帳 F1 で見つかった
- 何を変えたか: 受け入れの番号の集合から受け入れでない行の番号を引く・`<!--` から `-->` までの行を読まない。TC-05 に (9) 同じ R2 の回避と受け入れ (10) コメントの中だけの受け入れ を足し、FG-05e（引き算を外す）・FG-05f（コメントを読む）で不合格になることを確かめた
- セキュリティ: 回避と書いた残余リスクが一覧に落ちる穴を塞いだ（止める判定は元から変わらない）
- 次回どう防ぐか: 照合を作るときは「合う」の条件だけでなく「同じ鍵が食い違う」「無効な場所（コメント）にある」を照合の失敗の列挙に入れる（このイシューの TC-05 の形）
- 確かめた結果: `test_i512_accepted_risk.sh` exit 0（pass=38 fail=0）・`test_i202_ledger_cleanup.sh` exit 0（163/163）・`test_pipefail_negated_grep.sh` exit 0（10/10）・本物の plan_I512 の R3 は効いたまま

## 再発防止記録（fix-loop 3 回目・2026-11-14）
- なぜ失敗したか: 計画書の読み方を行ごとの特例（コメントの開き・閉じ）で積み上げたため、Markdown の書き方の組み合わせ（行の途中で開くコメント・閉じて開き直す行・コードの囲み）が漏れた。テストも「効かない向き」だけで、「コメントの後の表を読む」向きが無かった（台帳 F7〜F10）
- 何を変えたか: 閉じたコメントを全文から正規表現で取り除き、閉じていない <!-- から後ろは読まない。8 の節にコードの囲みがあれば受け入れを全部効かせない（粗い fail-closed）。共有のテストの計画書を雛形と同じ複数行のコメントつきにした（TC-01 がそのまま通る＝コメントの後の表を読む）。TC-05 を 15 通りに、FG-05f（取り除かない）・FG-05g（切らない）・FG-05h（囲みを見ない）・FG-05i（コメントが閉じない読み方）を足した
- セキュリティ: 回避・例の行が一覧に落ちる穴を、列挙でなく粗い規則で塞いだ（止める判定は元から変わらない）
- 次回どう防ぐか: 文書を機械で読む照合では、行ごとの特例を足さず、無効な場所を全文から先に取り除く・読めない形があれば全部効かせない形を最初から選ぶ（同種の指摘が 2 回続いたら粗い形に倒す決まりのとおり）
- 確かめた結果: `test_i512_accepted_risk.sh` exit 0（pass=41 fail=0）・`test_i202_ledger_cleanup.sh` exit 0（163/163）・`test_pipefail_negated_grep.sh` exit 0（10/10）・本物の plan_I512 の R3 は効いたまま

## 再発防止記録（fix-loop 4 回目・2026-11-14）
- なぜ失敗したか: 囲みを「8 の節の中」だけで見ていたため、前の節の囲みの中の 8 の例を本物として読み、囲みの中の <!-- で本物が切られた（台帳 F11・F12）。本文でないところを全文から先に取り除く形になっていなかった
- 何を変えたか: 囲み（``` と ~~~・行頭から空白 3 つまで・閉じていなければ後ろを全部）を全文から先に取り除き、その後で閉じたコメントを取り除く。8 の節の囲みの特例は消した。TC-05 を 17 通りに（前の節の囲みの中の 8 の例 2 形・閉じていない囲み）、囲みの中の <!-- で本物が切られない肯定（fok）、FG-05h（囲みを取り除かない写しで 3 通りが効き fok が切られる）
- 次回どう防ぐか: 文書の構造を読む照合は「本文でないところ（囲み・コメント）を全文から先に取り除く → 節を読む」の順で最初から作る
- 確かめた結果: `test_i512_accepted_risk.sh` exit 0（pass=43 fail=0）・`test_i202_ledger_cleanup.sh` exit 0（163/163）・`test_pipefail_negated_grep.sh` exit 0（10/10）・本物の plan_I512 の R3 は効いたまま
- 実行記録（2026-11-14・test-gate 2 回目・fix-loop 4 回目の後）: `bash scripts/claude/gate-check.sh I512` exit 0（GATE_CHECK: OK・REVIEWED_COMMIT 0a59b190）。manual_test No.2・No.3 を流し直して同じ結果（R3 だけが一覧・I430 は F1〜F3 が後続イシュー）。heavy の委譲は無い
