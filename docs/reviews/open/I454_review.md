# I454 レビュー: 見張りの環境変数の表示の後退（ps -A e）と書き先の取りこぼしを直す

## 変更概要
見張り（`scripts/claude/hooks/pretooluse_guard.py`）の `ps -A e`・`ps -ef e` が確認にならない後退（F10）を、値を取るオプションの一覧で直す。書き先の見分け方を 1 つの関数（`_write_targets`）にまとめて別ワークツリーの停止を広げ、コンテナ内では通す形でも /tmp/ 以外への書き込みを見る。（実装の後に implement 段階が直す）

## 変更点
- 5-1 `pretooluse_guard.py` `_cmd_external`・`_PS_VALUE_OPT_RE`（新規）: `ps` の BSD 形式の e は、値を取るオプションの後ろだけを値として読み飛ばす（F10・F11）。`declare`／`typeset` は `+` で始まるオプションだけの形も表示（F12）
- 5-2 `_opt_values`: まとめ書きを getopt と同じに読む（`-vt/x`）
- 5-3 `_COPY_CMDS`・`_write_targets`（新規）: 書き先の見分け方を 1 つに。`_bash_write_targets`・`_has_write_intent`・`_record_writes` が使い、`_ctr_write_targets` は消した。sed の式の付着形・`install -d` を扱う
- 5-4 `_container_risky`・`_container_safe`・`_analyze`・`_OPT_PATH_RE`（新規）: /tmp/ 以外への書き込み（リダイレクト・`_write_targets`・`--opt=/絶対パス`）は通す形でも常に見る。`writes` のフラグを消し、docker の包みを外すときはホスト側の `write_to` を消す
- 5-5 `scripts/claude/tests/test_i444_guard_gaps.sh`: 失敗の注入の置き換え文字列を新しいコードに合わせた
- テスト `scripts/claude/tests/test_i454_guard_env_writes.sh`（新規・44 件・FG-01〜FG-04）
- 5-6 `docs/runbooks/danger-ops.md` 4.・`docs/runbooks/worktree.md` §9: 正の関数の名前と代表の形
- 一覧: `docs/reviews/backlog/I444.md` の F11・F12・F13 を消した
- 見張りの行数: +65／−84（差し引き −19）

## 影響範囲
- ハーネスの見張り・そのテスト・手順書だけ。アプリのコードの変更なし

## テスト結果
（test-gate 段階が書く）

## 計画との差分
（各段階が書く）

## ロールバック
PR を revert する（データの変更なし）。見張りが起動できなくなったときは、ユーザーが端末で `! git restore scripts/claude/hooks/pretooluse_guard.py`。

## 自律判断の記録
- [plan] ps は値を取るオプションの一覧で読む（BSD 形式のまとめ書きは見ない＝確認側） — 「直前の語が - で始まる」の近似が F10 を生んだため（計画書 5-1）
- [plan] `-vt/x` は `_opt_values` を getopt と同じ規則にして直す — 他の呼び出し元も同じ規則にそろい、行数も減る（計画書 5-2・既存テストの全件一致をスパイクで確認）
- [plan] 調べて見つけた sed の式の付着形（`-es/a/b/`）とホスト側のリダイレクトの取り違えも直す — 同じ書き先の判定の取りこぼし・誤りで、問題 2・3 の根本原因の範囲（計画書 5-3・5-4）
- [plan] 通す形の分岐ごとの書き込みの除外は残す — 離した形の値（`--basetemp /app/x`）が書き込みの理由では見えず、消すと確認を外す範囲が広がる（計画書 5-4）
- [plan] 一覧 I444 の F11・F12・F13 は同梱、F7 は残す（計画書 9）
- [plan-review] 計画レビューの Warning 3 件（守る対象の明記・FG-03 の全文・TC-06 の記録欄）を直し、再レビューはしない — 方式・範囲・受け入れ条件を変えないため（計画変更記録 1）
- [implement] 新しいテストのファイルは、Write の道具が使えない間に既存のテストを写して Edit で書き換えて作った（ヒアドキュメントはワークツリーの外を指しうるとして拒否された） — 中身は auto_test の TC-01〜TC-04 と 1 対 1
- [implement] /simplify の指摘 5 件を反映し、3 件は見送った — 見送りは停止の範囲を広げる・短くならない・既存のテストの形とそろえるため（計画変更記録 2）
- [implement] TC-06 で見つけた `--rootdir=/app` の不要な確認 12 件に対し、`_OPT_PATH_RE` から `--rootdir=`・`--confcutdir=` だけを除いた（計画変更記録 3・03g） — 普通の作業に確認を出さない目的に合わせ、粗い判定（fail-closed）は保つ。2 回目の /simplify は未コミットの直しだけを対象にし、4 観点とも直す指摘なし（Low 2 件は「名前が増えたら定数に切り出す」で見送り）。直した後の corpus diff（基準 fba609bb）は新しく確認 0 件・新しく停止 2 件（別ワークツリーを移動元にする計画どおりの形）
- [fix-loop] 止める指摘 F1・F3（High）を案 A で直した: `_opt_values` の新しく読む形を「直後が英字以外」（`-vt/x`）に絞り、`install -d` は英字だけの語で見る — 診断レビュー PASS（`I454_fix_diagnosis_20261112_0955.md`）。案 B（`-t` の付着形を別に読む）は書き先の見分け方が 2 か所に分かれ受け入れ条件 4 とずれる、案 C（値を取る文字の一覧）は粗い判定の方針に反する。F2 は同じ関数の直しで結果として直る。F4〜F9 は止める指摘ではないので直さない（retro へ）。TC-07（失敗の注入つき）を足した

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: design-security-review

STAGE_DONE: design-security-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
