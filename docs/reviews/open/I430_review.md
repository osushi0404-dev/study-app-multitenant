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
- [retro] 台帳の残り: F1・F2・F3 → #512（I512・後続イシュー・「次のハーネスの作業で最優先」をコメント）、F4・F5・F6・F7・F8 → `docs/reviews/backlog/I430.md`、F9 → このイシューで直した（計画書の影響範囲と 4-5b に `.claude/agents/adversarial-reviewer.md` を足した）
- [retro] 改善案の振り分け: (1) 敵対的レビューの実験で入れ子の Claude を起こせない → このイシューで直した（review-gate で `.claude/agents/adversarial-reviewer.md`）(2) 受け入れ済みの残余リスクが最優先の後続を作り続ける → 起票 I512（#512）(3) 新しいセッションの起動のたびの許可の設定の警告 → #450 に同梱（コメント）(4) #436 の要否 → #436 に見直しの結果をコメント（閉じるかはユーザーの判断）(5) 設定ファイルの読み取り専用 × git checkout の事故（S22）が計画の試しで見つからなかった → 見送り（design-security-review でその場で見つけ、実装前に直したので手戻りが無い）(6) 同時に 2 つのテストを流して偽の失敗が出た → 見送り（手元の運用の誤りで、その場で気づき、コミット後に流し直して解消）(7) 設定の変更が、開いている会話の Bash に効かなかった → このイシューで記録（close の報告で「開いているセッションは開き直す」と案内する）

## 振り返り

### かんたんなまとめ

**良かった点**
- 公式の文書を読み、22 本の試し（実際にサンドボックスを動かす確かめ）を計画のうちに行った。その結果、「自動モードでは Edit/Write で別のワークツリーに書けてしまう」（見張りに残す判断の根拠）と「サンドボックスの中の git checkout が設定ファイルを古いまま残す」（git を外に出す判断の根拠）を、実装の前に見つけられた
- 見張りが実際に止めた回数を、#436 を待たずに会話の記録から数えた。消す判定（別のワークツリーへの書き込み・保護ブランチへの push・fork の PR）が事故を止めた例は 0 件という根拠で決められた
- 見張りは 3,880 行から 2,929 行になり、判定の約 4 分の 1 を公式と GitHub に任せた。手元のテスト・CI・コードレビュー・敵対的レビュー（2 周目）・手動テスト 14 項目がすべて合格

**今回の問題への直接の対処**
- 敵対的レビューの 1 周目が空振りし、画面にログインの案内が出た。レビュー役の実験が、入れ子の Claude を `bash -c … timeout … claude -p` の形で起こしていて、その形はサンドボックスの中で動くため、Claude につながらなかった。→ レビュー役の指示に「新しいセッションはリポジトリのスクリプト（`test-session.sh`）で、包まずに起こす」と書き足した。もともと「新しいセッションは GitHub に読み取りだけの鍵で起こす」という決まりがあり、その決まりにも合う。2 周目は実験がすべて動いた
- 計画書の影響範囲に、直したレビュー役の指示ファイルが書かれていなかった（レビューの指摘）。→ 書き足した

**同じ問題を次回から防ぐ改善**
- 計画で「受け入れる」と書いた残余リスク（スクリプトを外で動かせる・git を外に出したことの漏れ・fork の PR の確認をやめた）も、レビューの振り分けの仕組みが毎回「最優先の後続イシュー」にしてしまう。振り分けが台帳の重さの欄だけを見て、「計画で受け入れ済みか」を見ないため。見張りの直しが後続を生み続ける形（I444 から I430 まで 6 件）の原因でもある。→ I512（#512）を起票した。計画書に決まった形で書いた受け入れを、スクリプトが照合して、照合できた行だけを一覧に回す（止める判定は変えない）
- 新しいセッションを起こすたびに、許可の設定の「意味の無い行・効かない行」の警告が出る。→ 古い記述を片付ける #450 に同梱した

**見送ったもの（理由つき）**
- 設定ファイルの読み取り専用と git checkout の事故を、計画の試しで見つけられなかった: セキュリティ設計の確認の段階でその場で見つけ、実装の前に直したので、手戻りが無い。手順を足さない
- 2 つのテストを同時に流して、偽の失敗が出た: その場で気づき、コミットの後に流し直して解消した。手順を足さない

**約束していた測定の報告**
- I480 の約束（見張りのイシューの振り返りで、最優先の後続が出なくなったか）: 今回も出た（上の受け入れ済みの残余リスク）。原因を特定し #512 で直す
- I228・I486 の約束（敵対的レビューの空振りの効果）: 2 周のうち 1 周が空振り（実験必須の項目が未検証）。原因はサンドボックスと実験の書き方の組み合わせで、このイシューで直した（2 周目は実験必須の 4 項目すべてを実験で確かめた）

### 詳細版

#### 良かった点
- 公式文書（sandboxing.md）＋試し S1〜S22 を計画・セキュリティ設計の段階で行い、外部挙動の前提をすべて実測してから実装した（S18・S22 は方式の決定を変えた）
- 判定の削除の根拠を会話の記録の件数で示した（止めた 72 件・確認 184 件・消す判定の事故の例 0 件）
- AST の参照の関係から、消す判定だけが使う定義を機械で洗い出して消した（消し残し・誤削除を防いだ）

#### 是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | スキル・規約 | 敵対的レビューのレビュー役の指示に、新しい Claude のセッションの起こし方が無く、実験の上限の書き方（`bash -c 'ulimit …; timeout …'`）でそのまま包まれた。サンドボックスの導入で、包まれた `claude` が API につながらなくなった | `.claude/agents/adversarial-reviewer.md` に「`test-session.sh`／`check-permission-prompt.sh` を包まずに書く」を追加（review-gate で実施・2 周目で効き目を確認） |
| C2 | ドキュメント | 計画変更記録で実装対象を足したが、影響範囲と変更点一覧に反映しなかった | 計画書の影響範囲と 4-5b に追記（retro で実施） |

#### 予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| P1 | プロセス | レビューの振り分け（`--route`）が台帳の欄だけで後続・最優先を決め、計画で受け入れ済みかを見ない | 計画書に「受け入れた残余リスク」の欄を決まった形で設け、レビュー役が目印に節と行を書き、スクリプトが計画書と照合できた行だけを一覧へ回す（止める判定には効かせない・照合できなければ今までどおり）→ I512（#512） | `.claude/agents/code-reviewer.md`・`scripts/claude/code-review.sh`・`.claude/skills/retro/SKILL.md`・`docs/runbooks/review-rules.md`・`docs/plans/templates/plan_template.md` |
| P2 | 技術選択 | 公式の許可の書き方の変更で、効かない・意味の無い許可の行が残り、毎回警告が出る | 許可の行を公式の書き方に合わせて片付ける → #450 に同梱 | `.claude/settings.json`・primary の `.claude/settings.local.json` |

#### 5 Whys（P1）
- Why 1: 計画で受け入れ済みの F1・F2 が最優先の後続になった → `--route` が `SECURITY=yes`・guard の Medium 以上を後続・最優先にする
- Why 2: なぜ受け入れ済みでも後続になるのか → 台帳に「受け入れ済み」を表す欄が無く、スクリプトは欄だけで決める（I205 の決定論の方針）
- Why 3: なぜ欄が無いのか → 受け入れは計画書の文章（Risk・漏れの一覧）にしか無く、レビュー役とスクリプトが照合できる形になっていない
- 抽象化: 「計画で受け入れた判断が、決定論の振り分けに伝わる形で書かれていない」は、安全装置に限らず、残余リスクを受け入れるどのイシューでも起きる → 予防処置

#### 残余リスクの処遇（design-security-review・review-gate の /security-review）
- 設計レビューの Medium（外に出すコマンドの最小権限・スクリプトを外で動かせる）: 受け入れ（計画 R2・意図的な回避は対象外）。台帳では F1 として #512 で振り分けの扱いを決める
- 攻撃シナリオ #9（Medium・`bash scripts/claude/*` の書き換え）: 同上
- High 以上の残余リスク: 無し（/security-review の `SECURITY_FINDINGS: 0`）

#### 設計ルールの昇格
- セキュリティ設計の確認で見つけた型「公式の守りが、別の仕組み（git の作業ツリーの書き換え）とぶつかって事故になる」は、計画の「外部/ハーネス挙動依存のスパイク実証」（plan-writing-rules.md）で扱える範囲。今回はその段階でなく設計の確認で見つかったが、手戻りは無いので、観点は足さない（見送り・上の (5)）

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: design-security-review

STAGE_DONE: plan-review NEXT: design-security-review

STAGE_DONE: design-security-review NEXT: implement

STAGE_DONE: implement NEXT: review-gate

STAGE_DONE: review-gate NEXT: test-gate

STAGE_DONE: test-gate NEXT: retro
