# I430 レビュー: サンドボックスを土台にした見張りの組み直しと許可の設定の整理

## 変更概要
- 公式のサンドボックスを有効にし（中の Bash は承認なしで通す・外での再実行は無効・起こせなければ起動を止める）、docker・gh・git push/fetch/pull・`bash scripts/claude/*` を外に出す
- 見張り（`pretooluse_guard.py`）から、公式・GitHub で代わりに止まる判定（Bash の別ワークツリーへの書き込み・保護ブランチへの push・fork の PR）を消す
- 「見張りに判定を足すときの決まり」を danger-ops.md・plan-writing-rules.md に入れる

## 変更点
- `.claude/settings.json`: `sandbox`（enabled・autoAllow・外での再実行なし・failIfUnavailable・外に出す docker／docker-compose／gh／git／`bash scripts/claude/*`・denyWrite `.claude/worktrees`・denyRead App の鍵・通信なし）、deny `Bash(gh pr checkout *)`・`Bash(gh co *)`、GitHub MCP のフックの登録を削除
- `scripts/claude/hooks/pretooluse_guard.py`: 3,880 → 2,929 行。Bash の別ワークツリーへの書き込み・未カバーの警告・保護ブランチへの push・宛先の決まらない push の確認・`--repo`・fork の PR（gh・MCP）の判定と、それだけが使う関数を削除。安全網の欄を `_NET_KEYS` に一本化
- テスト: `test_pretooluse_gh_pr_guard.sh` を削除。消した判定の例を削除し、書き先の読み方はコンテナの形で確かめ直した（一覧は計画変更記録）。`test_settings_permissions.sh` にサンドボックスの決まりと FG を追加
- 手順書: danger-ops（サンドボックスの節・消した判定の対応表・判定を足すときの決まり）・plan-writing-rules・workflow・worktree・onboarding・claude-code-structure・CLAUDE.md

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.claude/settings.json`（sandbox・deny 2 行・GitHub MCP のフックの登録の削除）・`scripts/claude/hooks/pretooluse_guard.py`・ハーネステスト・手順書（danger-ops・plan-writing-rules・workflow・worktree・onboarding）・CLAUDE.md

## テスト結果
- 自動: 見張りと設定のテスト 19 本が合格（`run-all: pass=19 fail=0`）・TC-08（2,929 行）・TC-10〜12 合格。全体は CI
- 手動: M-01〜M-14 すべて OK（実施者はすべて Claude・`claude -p` の新しいセッション。Human の項目は無い）
- レビュー: コードレビュー OK（2 回）・敵対的レビュー 1 周目 HIGH（実験必須の未検証。実験の書き方の不具合）→ 直して 2 周目 OK（実験必須の項目はすべて実験で確認）

## 計画との差分
- あり（計画書の計画変更記録「2026-11-13 implement の記録」）: `--repo` の判定も削除・一覧 I454 F9 は残す・`docs/claude-code-structure.md` も直した・i454／i463 のテストの例をコンテナの形に置き換えた・この会話の Bash にはサンドボックスが効かなかった

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
- [implement] この会話の Bash にはサンドボックスが効かなかった（会話を始めた時点の設定のまま）ので、最終の設定は新しい `claude -p` で確かめる — 計画の「効く見込み」が外れたが、確かめ方を変えるだけで方式は変わらない
- [implement] `git push --repo` の判定も消した — 保護ブランチの判定を避ける書き方を止めるためだけの判定だったため（計画変更記録）
- [implement] /simplify（4 観点）の指摘のうち、重複の関数・deny の確かめの二重化・安全網の欄の名前の写し（`_NET_KEYS`・`_empty_net`）・使われない変数と引数（`_danger_reasons` の `cmd`・`_norm_push_dest` の `cur_branch`）・古い見出しとコメント・空振りした置換・使われないテストの準備・オラクルの古い条件・散らばった削除の説明コメントを直した。見送り: `_write_targets` を直接比べる表のテスト（新しいテストの作りで範囲の外）・`need_worktree`／`genv` の引数（残す git の場所の判定の中なので触らない）・`_block_cross_worktree` の `kind`・`guard_corpus_diff.py` の `{W}`（任意）・`_current_worktree_root` のキャッシュ（差分の外）
- [review-gate] 敵対的レビュー 1 周目の未検証（V1・V2・V3・V8）は、レビュー役の実験の指示（`claude` を `bash -c`・`timeout` で包んで起こす）がサンドボックスの中で動かないのが原因だったので、指示を直した（新しいセッションは `test-session.sh` を包まずに起こす）。V2 は実験役では確かめられない形なので TC-01・S19・M-04 で覆った — その場の言い直しでなく、今後の高リスクのイシューでも同じ失敗をしないため（ユーザーの指示「ループ・ハーネスの BP と開発効率で問題ないやり方で」）
- [test-gate] M-14 は一時のリポジトリで `bypassPermissions` で流した — 信頼済みでない一時のリポジトリでは allow が無視され、外に出した git が許可の流れで拒否されるため。見たいのは設定ファイルの切り替わりで、サンドボックスの効き方は変わらない
- [test-gate] M-01 で、git を echo とつないだ形が中で動き、サンドボックスが中でだけ置く空のファイルが `git status` に未追跡として見えた — 実際の作業ツリーには無いことを外の `git status` と `ls` で確かめた。danger-ops.md の「git を他とつながない」で扱える範囲なので、追加の直しはしない

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: design-security-review

STAGE_DONE: plan-review NEXT: design-security-review

STAGE_DONE: design-security-review NEXT: implement

STAGE_DONE: implement NEXT: review-gate

STAGE_DONE: review-gate NEXT: test-gate
