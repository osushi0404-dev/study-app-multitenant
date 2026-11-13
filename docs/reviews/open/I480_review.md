# I480 レビュー: SECURITY=yes でも Low・再現なしの指摘は軽い指摘の一覧に回す

## 変更概要
- retro の台帳の振り分け（`code-review.sh --route`）で、`SECURITY=yes` でも `SEV=Low` かつ `REPRO=no` の行は軽い指摘の一覧に回す。retro 4-0 の「最優先」の条件と review-rules の要約を合わせる

## 変更点
- `scripts/claude/code-review.sh`: `route_reasons()` の `SECURITY=yes` の条件・guard の行のコメント（一覧 I208 F1 の同梱）
- `.claude/skills/retro/SKILL.md`: 手順 4-0 の振り分けと最優先の条件
- `docs/runbooks/review-rules.md`: 振り分けの要約
- `scripts/claude/tests/test_i202_ledger_cleanup.sh`: Q7・FG-Q7 の直し、Q10・FG-Q10a〜c の追加
- `docs/reviews/backlog/I208.md`: F1 の行を消す

## 影響範囲
- Backend/Frontend/DB/Config: ハーネスの retro の振り分けだけ（`blocking()`・レビューの合否は変えない）

## テスト結果
- 自動: `test_i202_ledger_cleanup.sh` pass=163 fail=0・`test_i205_stop_criteria.sh` pass=91 fail=0・CI OK・コードレビュー OK（`docs/reviews/I480_code_review_20261113_1142.md`）
- 手動: No.1・No.2 とも OK（Claude）。Human の項目なし

## 計画との差分
- なし

## ロールバック
- このブランチのコミットを revert する

## 振り返り
### かんたんなまとめ
#### 良かった点
- 過去のレビュー記録で影響を先に数えた（一覧に移る指摘は延べ 18 行で、Medium 以上で再現なしの秘密情報の指摘は 0 行）ので、緩める範囲が狭いと確かめてから進められた（理由: 安全側の決まりを緩める変更で、根拠を数字で持てた）
- 条件を 3 つの部分に分けて、それぞれを壊すと落ちるテストを付けた（理由: 「緩めすぎ」と「緩め足りない」の両方を CI が毎回確かめる）
- 計画レビューの指摘（「最優先」の条件を行全体で探すと、アプリ本体の行まで拾う）を実装の前に直せた
- 止めずに最後まで進み、手戻りが無かった
#### 今回の問題への直接の対処
- なし（手戻り・見逃しが無かった）
#### 同じ問題を次回から防ぐ改善
- なし（下の見送り 2 件を参照）
#### 見送り
- 計画に書いていなかったテスト（FG-Q5）の追従が実装中に要った。条件の文字列を置き換えて壊すテストが、もう 1 か所あったため。→ 実装中にすぐ気づき、計画変更記録に書いて直した。手戻りが無いので、新しい手順は足さない
- 1 回の操作の中で読み込みと実行をまとめたコマンドが、作業場所の外に出ないかを確かめられないとして断られた。→ スクリプトのファイルに分けて流して済んだ。既に記憶している「コマンドを 1 つずつ流す」の決まりの範囲で、新しい手順は足さない

### 詳細
#### 良かった点
- 計画前に過去の台帳を集計して影響範囲を確定（harness 8・guard 10 が一覧へ・app 10 は後続イシューのまま・Medium 以上で再現なしは 0）
- FG-Q10a〜c と FG-Q7 で、条件の 3 つの部分をそれぞれ失敗注入で固定
- plan-review の Warning（`--route issue` の行頭の `SECURITY=` の欄）を実装前に反映
#### 是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| - | - | 該当なし | - |
#### 予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| - | - | 該当なし | - | - |
#### 見送り（手順 2.7）
- FG-Q5 の追従の計画漏れ: 4 問の 2（その場で捕まり手戻りなし）。計画変更記録 2 に記録済み
- 複合の bash -c が worktree の隔離で断られた: 4 問の 2（スクリプトに分けて解消・手戻りなし）。既存の memory（Bash は複合化せず単体で実行）の範囲
#### 観点の確認
- 成果: AC1〜AC5 を満たした（TC-01〜TC-03・manual No.1〜2）。目的（最優先の後続の連鎖を止める）の効果は、次の見張りのイシューの retro で `--route` の出力を見れば確かめられる
- セキュリティ: アプリのコードの変更なし。緩めたのは Low かつ再現なし・app 以外の行だけで、`blocking()` は不変（TC-02）。security-review は高リスク NO で実施なし（残余リスク処遇・設計ルール昇格はスキップ）
- ベストプラクティス・モダン開発・指示ファイル: 追加の観点なし
- 台帳の残り F1（一覧の行に SECURITY の欄が無い）は、イシューの目的（連鎖を止める）の穴ではない（一覧は計画で実装対象のファイルに当たる行を見るので埋もれない）ため一覧に回した

## 自律判断の記録
- [plan-review] 計画レビュー OK（Warning 1 件: 最優先の条件を `後続イシューにする理由:` より後ろに限る形に直した。文言の明確化なので再レビューはしない） — 方式・範囲・受け入れ条件を変えないため
- [plan-review] 高リスク判定は NO（PLAN_VERDICT: OK）なので design-security-review を飛ばして implement へ — スクリプトの判定どおり
- [implement] /simplify は整理役 4 体を起こさず自分で 4 観点を見た（指摘なし） — 差分が条件 1 行・コメント 1 行・テスト 1 ブロック・文言 3 か所と小さく、4 体は過剰（memory: 小さな直しに重い工程を回さない）
- [implement] FG-Q5 の壊し方も新しい条件の行（`SEC_COND`）を置き換える形に直した — 前の `if sec == "yes":` の文字列が本体から消え、写しが作れなくなるため（計画 §4 の Q7・Q10 の直しに付随。判定は変えない）
- [review-gate] コードレビュー OK・CI OK・高リスク NO（敵対的レビューは不要）。台帳の残り Low 3 件（F1〜F3）は止めない指摘なので直さず retro へ — 止める指摘だけを直す決まり（I197）
- [test-gate] gate-check OK・手元で流し直すテストなし（heavy の委譲なし）・手動テスト 2 項目を Claude が実施して OK — Human の項目が無いので retro へ
- [retro] 台帳の残り 3 件: F1・F2・F3 → docs/reviews/backlog/I480.md（後続イシュー 0 件）。F1 は目的の穴ではないことを確かめてから一覧へ
- [retro] 改善案 2 件はどちらも見送り（その場で捕まり手戻りなし）・新規起票・同梱なし

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
STAGE_DONE: retro NEXT: close
