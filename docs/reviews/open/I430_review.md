# I430 レビュー: サンドボックスを土台にした見張りの組み直しと許可の設定の整理

## 変更概要
- 公式のサンドボックスを有効にし（中の Bash は承認なしで通す・外での再実行は無効・起こせなければ起動を止める）、docker・gh・git push/fetch/pull・`bash scripts/claude/*` を外に出す
- 見張り（`pretooluse_guard.py`）から、公式・GitHub で代わりに止まる判定（Bash の別ワークツリーへの書き込み・保護ブランチへの push・fork の PR）を消す
- 「見張りに判定を足すときの決まり」を danger-ops.md・plan-writing-rules.md に入れる

## 変更点
- （実装後に記入）

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.claude/settings.json`（sandbox・deny 2 行・GitHub MCP のフックの登録の削除）・`scripts/claude/hooks/pretooluse_guard.py`・ハーネステスト・手順書（danger-ops・plan-writing-rules・workflow・worktree・onboarding）・CLAUDE.md

## テスト結果
- 自動: （実装後に記入）
- 手動: （test-gate で記入）

## 計画との差分
- なし（実装後に更新）

## ロールバック
- PR を revert する。サンドボックスだけ止めるときは `.claude/settings.json` の `sandbox.enabled` を false（Edit はサンドボックスの外）。詳細は計画書 7.

## 自律判断の記録
- [plan] 見張りを公式に置き換える範囲を、Bash の別ワークツリーへの書き込み・保護ブランチへの push・fork の PR の 3 つにした — 試し（S1〜S19）と会話の記録（事故を止めた例 0 件）で、公式・GitHub が代わりに止めることを確かめたため。Edit/Write の別ワークツリーの判定は、auto モードで書けた（S18）ので残す
- [plan] サンドボックスの外に出すスクリプトを `bash scripts/claude/*` のディレクトリごとにした — 一覧に絞っても守りの強さは同じで、一覧の漏れが黙った失敗になるため（ユーザーの「BP の観点で」の指示を受けた点検）
- [plan] allow・`autoMode.environment`・`Read(*)` などは変えない — 承認画面の主な出どころは見張りの確認で、判定役の拒否は 14 日で 1 回ほど。サンドボックスの中のコマンドは allow によらず通るため
- [plan] 安全装置の変更（止めて聞く条件 2）をユーザーに確かめた — 答えは「BP の観点で問題ないやり方で進めて」
- [plan-review] 1 回目の Blocker（`failIfUnavailable` の未実証）は、道具を消さずに `bwrap` を除いた `PATH` で試して実証した（S20）— 環境を壊さずに実機で確かめられたため
- [plan-review] 2 回目の Warning・Info は計画変更記録に書いて直し、計画レビューはやり直さない — 方式・範囲・受け入れ条件を変えないため
- [design-security-review] `git *` をまるごとサンドボックスの外に出し、`allowWrite` を消して `allowedDomains` を空にした — 中では `.claude/settings.json` が読み取り専用で、中の `git checkout` が設定ファイルだけ古く残す事故になった（S22）。サブコマンドの列挙は漏れが同じ事故になるため。方式の変更なので計画レビューをやり直す

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: design-security-review

STAGE_DONE: plan-review NEXT: design-security-review

STAGE_DONE: design-security-review NEXT: implement
