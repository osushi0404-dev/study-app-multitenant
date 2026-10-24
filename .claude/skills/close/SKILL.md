---
name: close
description: "/plan-issue・/proceed の流れの中でだけ呼ぶ段階のスキル（自分から呼ばない）。振り返りの後、記録を closed へ移し、PR 説明を整え、自律判断と振り返りをまとめてユーザーに Approve & Merge を依頼する。最後に STAGE_DONE を書く。"
argument-hint: "I###"
user-invocable: false
---

# close（クローズ段階）

前提: 人の手動テストが OK（または人の分が無い）で、retro 段階が済んでいる（`STAGE_DONE: retro NEXT: close`）。

止めてユーザーに聞くのは `docs/runbooks/workflow.md`「止めて聞く条件」に当たるときだけ（マージの依頼は別。ユーザーだけが行える）。技術的な問題（develop との食い違いなど）は自分で解決し、決めたことは `docs/reviews/open/I###_review.md` の「## 自律判断の記録」に `- [close] 決めたこと — 理由` で書く。この段階が書いてよいのは `docs/reviews/`・`docs/tests/`・`docs/issues/`・`docs/plans/` だけ。

（事前チェック・必須・決定論）レビュー済みの HEAD か:
```bash
bash scripts/claude/gate-check.sh I###
```
exit 1 なら、レビューを通っていない変更がある。`docs/reviews/open/I###_review.md` の末尾に `STAGE_DONE: close NEXT: review-gate` を書いて終わる（review-gate からやり直す）。

0) PR のベースブランチ確認と base 追従（必須）:
   ```bash
   # cross-repo チェック（I146）: 自前の PR であることを最初に確認する
   gh pr view <PR番号> --json isCrossRepository -q .isCrossRepository
   # → "false" であること。"true"（fork 由来の外部 PR）なら **STOP**。
   #   base 追従も CI 対応もせず、CONTRIBUTING.md の方針に沿って方針コメント付きで close する
   #   （手順: docs/runbooks/workflow.md「外部（fork）からの PR の扱い」）。

   gh pr view --json baseRefName --jq '.baseRefName'
   # → "develop" であること。"main" の場合は以下で修正してから続行:
   # gh pr edit <PR番号> --base develop

   # base 追従チェック（I113）: BEHIND なら origin/develop を取り込む（push/CI はしない。
   # push は step 3 の close コミットに相乗りさせ、CI 実行を1回にまとめる）
   bash scripts/claude/pr-base-sync.sh sync
   # exit 0 → 続行
   # exit 1 → マージコンフリクト等。解決を試みる（下）
   # exit 2 → mergeStateStatus=UNKNOWN が継続。1 回だけ実行し直し、続けば自律判断の記録に書いて続行する
   ```
   exit 1 のとき: 食い違いを解決して commit する。解決のために要件・基本設計・UI/UX の判断が要るとき（どちらの変更を残すかで仕様や画面が変わるとき）だけ止める（止める条件 1）。記録の場所の外を直した・取り込んだときは、`STAGE_DONE: close NEXT: review-gate` を書いて終わる（取り込んだ変更を含めてレビューを通り直す）
1) docs/*/open の対象 I### ファイルを closed へ移動（以下を順番に実行）:
   ```bash
   ISSUE_NUM="###"  # 実際のイシュー番号（3桁）に置き換える

   # ISSUE_NUM が3桁の数字であることを確認（パストラバーサル防止）
   if ! [[ "$ISSUE_NUM" =~ ^[0-9]{3}$ ]]; then
     echo "⚠️ ISSUE_NUM が3桁の数字ではありません: $ISSUE_NUM"
     exit 1
   fi

   # イシューファイル（I###.md 形式優先、旧 ###.md 形式にも対応）
   if [ -f "docs/issues/open/I${ISSUE_NUM}.md" ]; then
     git mv docs/issues/open/I${ISSUE_NUM}.md docs/issues/closed/
   elif [ -f "docs/issues/open/${ISSUE_NUM}.md" ]; then
     git mv docs/issues/open/${ISSUE_NUM}.md docs/issues/closed/
   else
     echo "⚠️ イシューファイルが見つかりません（I${ISSUE_NUM}.md / ${ISSUE_NUM}.md）"
   fi

   # 計画書
   [ -f "docs/plans/open/plan_I${ISSUE_NUM}.md" ] && git mv "docs/plans/open/plan_I${ISSUE_NUM}.md" docs/plans/closed/

   # テストケース（auto_test・manual_test の両ファイルを一括移動）
   for f in docs/tests/open/I${ISSUE_NUM}_*.md; do
     [ -f "$f" ] && git mv "$f" docs/tests/closed/
   done

   # レビュー（ライフサイクルファイル IXXX_review.md）
   for f in docs/reviews/open/I${ISSUE_NUM}_*.md; do
     [ -f "$f" ] && git mv "$f" docs/reviews/closed/
   done

   # timestamped 監査記録（直下）を closed/ へ回収（I065）
   # glob は IXXX_{code,plan,issue}_review_<ts>.md に一致。
   # IXXX_review.md（lifecycle・_review_ を含まない）には非マッチ＝誤回収しない。
   PLAN="docs/plans/closed/plan_I${ISSUE_NUM}.md"   # close 実行内で一定（ループ外へ）
   for f in docs/reviews/I${ISSUE_NUM}_*_review_*.md; do
     [ -f "$f" ] || continue
     base="$(basename "$f")"
     esc="${base//./\\.}"   # sed LHS 用に正規表現メタ文字 . をエスケープ
     # 案B(I069): 未追跡（issue-review 等＝案A' 経路）でも git mv が "fatal: not under version control" で
     # 失敗しないよう、mv の直前にその1ファイルのみを追跡化する。追跡済みファイルには no-op。
     git add -- "$f"
     git mv "$f" docs/reviews/closed/
     # plan 内 ## レビュー結果 リンクを closed/ 向きに更新（リンク切れ防止・Q3）
     [ -f "$PLAN" ] && sed -i "s#(\.\./\.\./reviews/${esc})#(../../reviews/closed/${base})#g" "$PLAN"
   done
   ```
   移動後、open に残留ファイルがないことを必ず確認:
   ```bash
   ls docs/issues/open/ docs/plans/open/ docs/tests/open/ docs/reviews/open/
   ```
2) PR テンプレートを読み込み、各セクションを実装内容で埋めて PR 説明を更新する:
   ```bash
   # テンプレートを確認
   cat .github/pull_request_template.md
   ```
   テンプレートの各セクション（概要・関連イシュー・変更点・テスト確認・ロールバック手順・参照ドキュメント）を
   イシュー・計画書・テスト結果をもとに埋め、gh pr edit で PR 説明を更新する:
   ```bash
   gh pr edit <PR番号> --body "$(cat <<'EOF'
   ## 概要
   ...（実装内容を記載）

   ## 関連イシュー
   Closes #...

   ## 変更点
   ...

   ## テスト確認
   - [x] CI（自動テスト）pass 確認
   - [x] 手動テスト確認

   ## ロールバック手順
   ...

   ## 参照ドキュメント
   ...
   EOF
   )"
   ```
   テンプレートが存在しない場合は「目的/変更点/テスト/ロールバック/参照パス」を手動で記載する。
3) commit/push して PR を更新する。
   **staging は close 対象の I### 関連ファイルに限定する**（step 1 の `git mv` で移動した issue/plan/tests/reviews と、完了情報追記などで編集した追跡済みファイルのみ）。
   ```bash
   # 追跡済みファイルの変更（git mv 済みの move・完了情報追記）だけを staging する。
   git add -u
   # ⚠️ `git add -A` / `git add .` / `git add docs` は使わない。
   #    retro が /issue-bootstrap で作成した未コミットのバックログ issue ファイル（別 I###.md）を
   #    巻き込み、当該イシューの plan-issue 初コミットを no-op 化させる（I062/I067 の事故原因）。

   # 決定論ゲート: staged に I### スコープ外が混ざっていないか検証（番号をアンカーして誤マッチ回避）。
   STAGED=$(git diff --cached --name-only)
   if echo "$STAGED" | grep -vE "I${ISSUE_NUM}([^0-9]|$)" | grep -q .; then
     echo "⚠️ close 対象（I${ISSUE_NUM}）以外が staged されています。確認してください:"
     echo "$STAGED"
     # → スコープ外（特に docs/issues/open/ の別 I###.md）を unstage してから続行する。
     exit 1
   fi

   git commit -m "close(I${ISSUE_NUM}): ..."
   git push
   ```
   `git status` に未追跡のバックログ issue ファイル（`docs/issues/open/` 配下の別 I###.md 等）が出る場合は、**コミットせず未追跡のまま残す**。
4) PR のベースブランチが `develop` であることを確認・修正:
   ```bash
   gh pr view <PR番号> --json baseRefName -q .baseRefName
   # develop でなければ修正
   gh pr edit <PR番号> --base develop
   ```
5) Draft PRをReadyに切り替え: `gh pr ready <PR番号>`

5.5) base 追従の最終チェック（マージ依頼の直前・必須）:
   ```bash
   bash scripts/claude/pr-base-sync.sh final
   # PR番号は省略可（step 0 と同じ・カレントブランチの PR を自動特定。明示指定も可）
   ```
   合格条件は「**BEHIND / DIRTY でない ＋ CI 全グリーン**」（CLEAN は要求しない。develop は
   Code Owners（`oshui0404`）の承認が必須、main は承認 1 件が必須で push・マージできるのは
   `oshui0404` だけの設定のため（main には CODEOWNERS が無い・`docs/runbooks/branch-protection-setup.md`）、
   承認前の正常な最終状態は BLOCKED＝CI 全緑・承認待ちのみ）。
   - exit 0 → step 6 のマージ依頼へ進む
   - exit 1 → 原因を見て直す。マージコンフリクトは step 0 と同じ扱い。CI fail は `STAGE_DONE: close NEXT: fix-loop` を書いて終わる。DRAFT 残留は step 5 をやり直す
   - exit 2 → mergeStateStatus=UNKNOWN が継続。1 回だけ実行し直し、続けば報告に書いて step 6 へ進む
6) 結線とマージ依頼（必須）:
   - `docs/reviews/closed/I###_review.md` の末尾に `STAGE_DONE: close NEXT: merge` を足して commit/push する
   - ユーザーへ GitHub 上で Approve & Merge を依頼する（承認とマージはユーザー `oshui0404` だけが行える。
     承認の後に develop への追従などでコミットが入ると承認は取り消されるため、その場合は再承認を依頼する）。
     手動テスト文書に、承認の後・マージの前に行う確認がある場合は、まず承認だけを依頼し、その確認を終えてからマージを依頼する。そのような確認がない場合は、承認とマージを一度に依頼する。
   - 依頼と一緒に、平易な言葉で次をまとめて報告する（retro の平易化ルール）:
     1. 何を変えたか（PR の概要）
     2. Claude が自分で決めたこと（「## 自律判断の記録」の要点。止めずに進めた判断と理由）
     3. 振り返りの結果（直したもの・同梱したイシュー・起票したイシュー・見送りと理由）
