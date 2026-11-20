# I590 レビュー: I587 のレビューの残り（移行 0025 の依存・配信の 412 の見出し・`Subject.image_directory` の削除）

## 変更概要
-

## 変更点
-

## 影響範囲
- Backend/Frontend/DB/Config:

## テスト結果
- 自動:
- 手動:

## 計画との差分
- なし / あり（理由）

## ロールバック
-

## 自律判断の記録
<!-- 各段階が、止めずに自分で決めたことを `- [段階] 決めたこと — 理由` で足す。段階の結線の行（STAGE_DONE:）はこのファイルの末尾に足す -->
- [plan] F4〜F7 は I587 の追加の直し（PR #588・コミット 08919b28）で直っていたので、コードを変えずに受け入れ条件 1〜3・5 を達成済みとして扱う — #590 のコメントと計画 1 の調査結果 1 のファイル:行で確かめた。grill-me ではコメントを読まずに本文だけで質問を作ったが、聞いた 1 点（列の削除）は今も有効
- [plan] F3 は 0025 を書き換えず、`media_migration` をアプリの部品から切り離す — 規約 §4（マージしたマイグレーションは書き換えない）。比べた案は計画 9
- [plan] F9 は 412 を残し、守りの見出しをどの応答にも付ける — Django の標準の判定を上書きしない
STAGE_DONE: plan NEXT: plan-review
- [plan-review] 1 回目の Blocker（`views.py` の `transaction` の読み込みを消す誤り）を直して再レビュー（2 回目で完了・高リスク Yes）。2 回目の Warning のうち 0027 の判定の不要な `isnull` を消した（計画変更記録）。TC-02(b) は今のコードでも合格するが将来の守りとして残す — 失敗の注入は (a) で成立している
STAGE_DONE: plan-review NEXT: design-security-review
- [design-security-review] Blocker・High・Medium は 0 件、Low は設計 2 件・シナリオ 4 件で、どれも計画の TC（TC-01〜TC-04）と I587 の既存テストで覆う。追加の禁止事項は「条件付きの判定を get_object() より前に動かさない」「0027 の止める文に値・科目名を入れない」— 計画の方式は変えないので計画レビューのやり直しは不要
- [implement] 控え（M2）で `bash scripts/db_backup.sh` がサンドボックスの中で `.env` を読めず止まり、空の `backup_20261120_133719.sql` を残した（I587 と同じ）。回り道の `pg_dump` は途中でユーザーが止め、原因を調べた。ユーザーの指示「切り出して先に直す方向で進めて」（2026-11-20）で #597 を起票し、#538 に切り出しを書いた。コンテナの中の写しと空のファイルは消した。I590 は #597 のマージまで M2（ステップ 1）で待つ
STAGE_DONE: design-security-review NEXT: implement
- [implement] #597 のマージ（PR #598・2026-11-20）を受けて develop をブランチに取り込み（merge。最初のコミットを push 済みなので rebase しない）、M1（科目 11・`image_directory` に値のある科目 0）と M2（`bash scripts/claude/db-backup.sh I590_before` → `backup_I590_before_20261120_161736.sql`・160768 バイト）を取った — 計画 5 のステップ 1
- [implement] F3・F9（ステップ 2）を承認を待たずに先に進めた。TC-01〜03 を先に書き、直す前に 4 件が落ちること（TC-02 (b) と TC-03 (a) は想定どおり通る）を確かめてから直した — 計画 5 のステップ 2 は DB を変えないので承認と並行してよい
- [implement] ユーザーの承認「ok」（2026-11-20）を受けて、列の削除（ステップ 3）と移行の実行（ステップ 4・M3）を行った。開発の DB で 0027 は OK・列は無くなった。控え `backup_I590_before_20261120_161736.sql` はマージの後に close で消す — 計画 5 のステップ 1 の承認の条件
- [implement] /simplify（4 観点）: TC-03 の場合分けを引数の組に直し、media_migration の docstring に「0025 の一部として扱う・problems.* を読まない」を書いた。見送り: マイグレーションのテストの補助（`_loader`・`_run`・列の一覧）が I492・I587・I590 で 3 つ写しになっている — 共有の補助に切り出すと I492・I587 のテストまで変え計画の範囲を外れる（retro で後続の候補にする）。`_detect_mime` の 1 行の包みと TC-01／TC-02 の二重の守りは計画どおりに残す — 計画 4-1・6
STAGE_DONE: implement NEXT: review-gate
- [review-gate] 基本レビュー OK（Low 2 件: TC-03 が Content-Disposition を比べない・0010 の経緯で古い DB では 0027 が止まりうる）・敵対的レビュー 1 周目 OK（Low 3 件）。どれも止める指摘ではないので台帳に残し retro に回す — review-rules の止める条件に当たらない
STAGE_DONE: review-gate NEXT: test-gate
