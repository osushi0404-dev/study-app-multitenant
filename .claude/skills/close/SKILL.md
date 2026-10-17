---
name: close
description: Move docs open→closed and finalize PR description; request merge.
argument-hint: "I###"
disable-model-invocation: true
allowed-tools: Read, Bash, Write, Edit, Glob, Grep
---

# /close

前提: ユーザー検証OK。

（事前チェック）直近のコードレビューで Medium 以上の指摘が未対応のまま残っていないか確認する。未対応がある場合は、計画書に是正ステップを追記するかインライン修正を先に完了させてから以降のステップに進む。

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
   # exit 0 → 続行 / exit 1 → STOP してユーザーに報告（マージコンフリクト等・自動解決しない）
   # exit 2 → mergeStateStatus=UNKNOWN が継続。値を報告し続行可否をユーザーに確認
   ```
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
   合格条件は「**BEHIND / DIRTY でない ＋ CI 全グリーン**」（CLEAN は要求しない。ユーザーの
   Approve がマージ条件のため、承認前の正常な最終状態は BLOCKED＝CI 全緑・承認待ちのみ）。
   - exit 0 → step 6 のマージ依頼へ進む
   - exit 1 → STOP してユーザーに報告（マージコンフリクト・CI fail・DRAFT 残留等。自動解決しない）
   - exit 2 → mergeStateStatus=UNKNOWN が継続。値を報告し続行可否をユーザーに確認
6) ユーザーへ GitHub 上で Approve & Merge を依頼
