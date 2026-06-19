# I069 レビュー記録

- **関連計画書**: docs/plans/open/plan_I069.md
- **関連イシュー**: #141 / **Draft PR**: #143

## レビュー対象
- `scripts/claude/plan-issue-review.sh`（案A: `commit_review_artifact` 追加＋本体配線・ブランチガード）
- `scripts/claude/code-review.sh`（案A: 同上）
- `scripts/claude/issue-review.sh`（案A': commit しない旨のコメント追記のみ・挙動変更なし）
- `.claude/skills/close/SKILL.md`（案B: timestamped 回収ループに `git add -- "$f"` を追加）
- `scripts/claude/tests/test_review_commit_lifecycle.sh`（新規・案A/案B git fixture 単体テスト）

## レビュー観点
- 受け入れ条件（AC1〜AC6）を満たすか
- **案A**: review ファイル1点のみ path-scoped で add→commit し、他 index/作業ツリーに触れないか（TC-A3）。auto-push しないか。
- **ブランチガード**: develop/main/detached HEAD/空ブランチで commit をスキップし未追跡で残すか（絶対ルール3＝develop 直 commit 禁止の構造的保証・TC-A4/A5）
- **案A'**: issue-review が develop 直 commit を回避し、commit を配線していないか（TC-A6）
- **案B**: close 回収ループで未追跡 review が `git mv` 失敗（`fatal: not under version control`）を起こさず回収されるか（TC-B1）
- **AC4 回帰**: I067 の scoped staging（`git add -u`）／決定論ゲート（step 3）が改変されていないか（TC-B2/B3）。broad add への逆戻りが無いか。
- 非ブロック設計（commit 失敗でレビューフローを止めない）の妥当性
- shellcheck（pre-commit）通過・既存テスト非退行（TC-C1〜C3）
- セキュリティ影響（app/依存/認可変更なし・commit は path-scoped）の妥当性
- スコープ逸脱が無いか（plan-issue/SKILL.md は変更しない・I067 ゲート本体は触らない）

## plan-issue-review 記録
- 実行: 2026-06-19 / レビューファイル: `docs/reviews/I069_plan_review_20260619_1219.md`
- **VERDICT: OK**（高リスク判定: No）→ `/implement I069` 可
- 助言 4 件（Blocker なし）すべてテスト文書へ反映済み:
  - W1: TC-A6 の grep がコメント行を除外せず偽陽性リスク → コメント行除外フィルタ（`grep -vE '^[[:space:]]*#'`）に修正
  - W2: TC-A6 の期待結果（コメント存在）と検証コマンドの乖離 → コメント存在確認を **TC-A6b** に分離
  - W3: TC-A1 が plan-issue-review.sh のみ検証（code-review.sh 非対称）→ **TC-A1b** を追加して両スクリプト検証
  - Info1: source 時の `set -euo pipefail` 伝播 → auto_test のテスト実装上の注意に隔離方針（`set +e +o pipefail`／サブシェル）を明記

## /test 記録
- 実行: （/test I069 実行後に追記）

## code-review 記録
- 実行: （/code-review I069 実行後に追記）
