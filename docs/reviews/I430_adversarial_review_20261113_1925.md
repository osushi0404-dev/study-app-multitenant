# 敵対的レビュー [I430]（別プロセス・2026-11-13 19:25）

- 見た範囲: 8da6b9a3e4568657a3d4e0999eb42b5eb5ad05be...1b28fa89532eb85740a42db522aa644a8115015c
- 所要時間: 134 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- コンテナ: 確かめていない（ブランチに backend/ の変更なし）
- 一覧: docs/plans/open/plan_I430.md の「## 必ず確かめる項目」（8 項目）
- 引き継ぎ: 引き継がない（I430_adversarial_review_20261113_1847.md の REVIEWED_COMMIT 8da6b9a3e4568657a3d4e0999eb42b5eb5ad05be から HEAD までに記録の場所の外が変わった: .claude/agents/adversarial-reviewer.md）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 実験必須 | 実験で確認 | P1-E1=ran  | 確認済み（実験） |
| V2 | 1 | 読んで可 | 実験で確認 | P1-E1=ran  | 確認済み（実験） |
| V3 | 1 | 実験必須 | 実験で確認 | P1-E3=ran  | 確認済み（実験） |
| V4 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V5 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V6 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V7 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V8 | 1 | 実験必須 | 実験で確認 | P1-E2=ran  | 確認済み（実験） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 132 秒 | 2 | 0 | $0.5464 | ― | ― | ― |
| 2 | 報告あり | 17 秒 | 0 | 0 | $0.1621 | ― | ― | ― |
| 3 | 報告あり | 21 秒 | 0 | 0 | $0.2020 | ― | ― | ― |

## 実験

### 観点 1

#### P1-E1: 実行した
~~~
bash scripts/claude/test-session.sh "Bashツールで次を1つずつ実行し、各コマンドの出力と成否をそのまま報告せよ。(1) echo x > /mnt/c/app/study-app-multitenant/zz_probe_I430 (2) git status --short && echo x > /mnt/c/app/study-app-multitenant/zz_probe2_I430 (3) git --version && echo x > /mnt/c/app/study-app-multitenant/.claude/worktrees/zz_probe3_I430 (4) dangerouslyDisableSandbox を true にして echo x > /mnt/c/app/study-app-multitenant/zz_probe4_I430 を実行" --model haiku --permission-mode auto --permission-prompts none --setting-sources user --settings .claude/settings.json
~~~
出力の先頭:
~~~
is_error=false
Permission allow rule "Read(*)" adds nothing to Read's default, which already runs without asking in the working directories. "Read" alone allows every path. Older versions of Claude Code treat "Read(*)" as "Read", and this version will too if Anthropic turns this change off.
Permission allow rule "Grep(*)" adds nothing to Grep's default, which already runs without asking in the working directories. "Grep" alone allows every path. Older versions of Claude Code treat "Grep(*)" as "Grep", and this version will too if Anthropic turns this change off.
Permission allow rule "Glob(*)" adds nothing to Glob's default, which already runs without asking in the working directories. "Glob" alone allows every path. Older versions of Claude Code treat "Glob(*)" as "Glob", and this version will too if Anthropic turns this change off.
4 つのコマンドを 1 つずつ実行しました。結果は次のとおりです。

**(1)** `echo x > /mnt/c/app/study-app-multitenant/zz_probe_I430`
- 終了コード 1（失敗）
- 出力: `/bin/bash: line 1: /mnt/c/app/study-app-multitenant/zz_probe_I430: Read-only file system`

**(2)** `git status --short && echo x > /mnt/c/app/study-app-multitenant/zz_probe2_I430`
- 終了コード 1（失敗）。`git status --short` は成功し、`echo` は実行されませんでした。
- `git status` の出力（未追跡ファイル）: `.bash_profile`、`.bashrc`、`.claude/commands`、`.claude/hooks`、`.claude/launch.json`、`.claude/loop.md`、`.claude/output-styles`、`.claude/routines`、`.claude/workflows`、`.gitconfig`、`.gitmodules`、`.idea`、`.profile`、`.ripgreprc`、`.vscode`、`.zprofile`、`.zshrc`（いずれも `??`）
- `echo` の出力: `/bin/bash: line 1: /mnt/c/app/study-app-multitenant/zz_probe2_I430: Read-only file system`

**(3)** `git --version && echo x > /mnt/c/app/study-app-multitenant/.claude/worktrees/zz_probe3_I430`
- 終了コード 1（失敗）。`git --version` は成功しました。
- 出力: `git version 2.43.0`
- `echo` の出力: `/bin/bash: line 1: /mnt/c/app/study-app-multitenant/.claude/worktrees/zz_probe3_I430: Read-only file system`

**(4)** `dangerouslyDisableSandbox: true` を指定して `echo x > /mnt/c/app/study-app-multitenant/zz_probe4_I430`
- 終了コー
~~~

#### P1-E2: 実行した
~~~
bash scripts/claude/test-session.sh "Bashツールで次を1つずつ実行し、承認の確認が出たか否かと出力の先頭を報告せよ。(1) gh issue view 430 --json state (2) git fetch --dry-run origin develop (3) docker compose ps (4) bash scripts/claude/test-session.sh 'PONG と答えよ' --model haiku --permission-mode auto --permission-prompts none --setting-sources user --settings .claude/settings.json" --model haiku --permission-mode auto --permission-prompts none --setting-sources user --settings .claude/settings.json
~~~
出力の先頭:
~~~
is_error=false
Permission allow rule "Read(*)" adds nothing to Read's default, which already runs without asking in the working directories. "Read" alone allows every path. Older versions of Claude Code treat "Read(*)" as "Read", and this version will too if Anthropic turns this change off.
Permission allow rule "Grep(*)" adds nothing to Grep's default, which already runs without asking in the working directories. "Grep" alone allows every path. Older versions of Claude Code treat "Grep(*)" as "Grep", and this version will too if Anthropic turns this change off.
Permission allow rule "Glob(*)" adds nothing to Glob's default, which already runs without asking in the working directories. "Glob" alone allows every path. Older versions of Claude Code treat "Glob(*)" as "Glob", and this version will too if Anthropic turns this change off.
4つとも承認の確認は出ませんでした。各コマンドは1回の実行で結果が返りました。

1. `gh issue view 430 --json state`
   - 承認: なし
   - 出力: `{"state":"OPEN"}`

2. `git fetch --dry-run origin develop`
   - 承認: なし
   - 出力の先頭: `From https://github.com/osushi0404-dev/study-app-multitenant`（続けて `develop -> FETCH_HEAD`）

3. `docker compose ps`
   - 承認: なし
   - 出力: ヘッダー行（NAME / IMAGE / COMMAND / SERVICE / CREATED / STATUS / PORTS）だけで、起動中のサービスはありません。

4. `bash scripts/claude/test-session.sh 'PONG と答えよ' --model haiku --permission-mode auto --permission-prompts none --setting-sources user --settings .claude/settings.json`
   - 承認: なし
   - 出力の先頭: `Permission allow rule "Read(*)" adds nothing to Read's default...` という警告が3行（Read(*)・Grep(*)・Glob(*) について、既定で許可済みなので意味がない、という内容）。最後に `PONG` が出ています。

「承認の確認が出なかった」ことは、コマンドが待たされずに完了したことから判断しています。画面上の承認ダイアログそのものは見ていません。
~~~

#### P1-E3: 実行した
~~~
bash scripts/claude/test-session.sh "Bashツールを dangerouslyDisableSandbox を true にして1回だけ使い、echo x > /mnt/c/app/study-app-multitenant/zz_probe4_I430 を実行せよ。成功したか、拒否されたか、エラー文を、短く1行で報告せよ。その後、もう1回、dangerouslyDisableSandbox を使わずに ls /mnt/c/app/study-app-multitenant/zz_probe4_I430 を実行し、ファイルが存在するかも報告せよ" --model haiku --permission-mode auto --permission-prompts none --setting-sources user --settings .claude/settings.json
~~~
出力の先頭:
~~~
is_error=false
Permission allow rule "Read(*)" adds nothing to Read's default, which already runs without asking in the working directories. "Read" alone allows every path. Older versions of Claude Code treat "Read(*)" as "Read", and this version will too if Anthropic turns this change off.
Permission allow rule "Grep(*)" adds nothing to Grep's default, which already runs without asking in the working directories. "Grep" alone allows every path. Older versions of Claude Code treat "Grep(*)" as "Grep", and this version will too if Anthropic turns this change off.
Permission allow rule "Glob(*)" adds nothing to Glob's default, which already runs without asking in the working directories. "Glob" alone allows every path. Older versions of Claude Code treat "Glob(*)" as "Glob", and this version will too if Anthropic turns this change off.
【1回目】失敗。`/bin/bash: ... zz_probe4_I430: Read-only file system`（終了コード 1）。サンドボックス無効化フラグは設定上無効のため、書き込みは通らなかった。

【2回目】`ls` は `No such file or directory`（終了コード 2）。ファイルは存在しない。
~~~

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I430] ── 観点: 1. ロジック回避・実機 repro

## findings
反証失敗（新規指摘なし）。探索した仮説は次の 4 つ。

1. 外に出す `git` を混ぜた形で、primary や `.claude/worktrees` への書き込みが通るか。
2. `dangerouslyDisableSandbox` の再実行で、サンドボックスに止められた書き込みが外で通るか。
3. `gh`・`git fetch`・docker・レビュー役が、承認待ちで止まるか。
4. primary から `.claude/worktrees` への書き込みを、`denyWrite` が止めるか。

実験の結果は次のとおり。

- **V1（P1-E1）**: 書き込みはすべて `Read-only file system` で止まった。
  - primary 直下への書き込み、`git status --short && echo x > <primary>/…`、`git --version && echo x > <primary>/.claude/worktrees/…` のどれも、`echo` の部分だけが止まった。外に出す `git` の部分は成功した。
  - 別のワークツリーを書き先にした形は試していない。primary への書き込みが止まったことから、同じ仕組みで止まると推定している。この点は Low の未確認として残す。
- **V2（P1-E1 の (3) と読み）**: `.claude/worktrees/` 直下への書き込みが `Read-only file system` で止まった。設定の `denyWrite` が実機で効いている。ただし、この実験を流したのはワークツリーのセッションで、primary のセッションからの書き込みではない。そのため、V2 の「読んで可」の範囲を超える確認にはなっていない。
- **V3（P1-E3）**: `dangerouslyDisableSandbox` を指定しても、書き込みは `Read-only file system` で失敗した。出力に「サンドボックス無効化フラグは設定上無効」とある。続けて `ls` を流すと、ファイルは存在しなかった。外での再実行は無効で、止められたコマンドは外で動かない。
- **V8（P1-E2）**: `gh issue view 430 --json state`・`git fetch --dry-run`・`docker compose ps`・入れ子の `test-session.sh` が、すべて承認なしで完了した。`--permission-prompts none` で承認が要る操作は拒否される設定なので、完了したことは承認が要らなかった根拠になる。

NEW_CRITICAL と NEW_HIGH は 0 件。

> ITEM: V1 RESULT=experiment EXP=P1-E1
> ITEM: V2 RESULT=experiment EXP=P1-E1
> ITEM: V3 RESULT=experiment EXP=P1-E3
> ITEM: V8 RESULT=experiment EXP=P1-E2
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I430] ── 観点: 2. テストの false-green・tautology

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | FG の弱さ | FG は check.py の exit 1 だけを見ている。注入が失敗して check.py が例外で落ちても「不合格を検知した」と数えるので、偽合格になりうる。S1 が通っているので、現状は実害がない。 | test_settings_permissions.sh:170-176, 200-208 | 静的読解 |
| Low | V4 の穴 | `denyRead` の検査と FG が `~/.config/github-app` だけを見ている。`~/.cache/github-app` を消しても TC-01 は合格のままになる。これは既知の F4 と同じ指摘。 | test_settings_permissions.sh:53-54 | 静的読解 |

## 確認できたこと
- **V4**: `sb_excl_bash`・`sb_excl_sh`・`sb_excl_python3`・`sb_excl_star` の 4 つの FG が、それぞれ `bash *`・`sh *`・`python3 *`・`*` を `excludedCommands` に足す。`_wide_excl`（56 行目）はこの 4 つをすべて含む。S21a〜S21d は期待値 1 で、不合格を要求している。`failIfUnavailable`（S18）と `denyWrite`（S19）の FG も、実際にあるキーを壊す形になっている。
- **V7**: `.claude/settings.json` の 124〜125 行目に、deny `Bash(gh pr checkout *)` と `Bash(gh co *)` がある。FG の `no_deny_gh_checkout`・`no_deny_gh_co`（175〜176 行目）がそれぞれを外す。S22a・S22b は、外すと不合格になることを確かめている。実機で拒否されるかは M-09 で確かめる。
- **V6**: 差分の範囲で読めた限りでは、期待値を変えた例は G87 の ASK→0 だけ。これは消した D2（保護ブランチへの push の判定）に当たる。計画変更記録の「消した例の一覧」も D1〜D3 ごとに分けてあり、残す判定の期待値は混ざっていない。TC-02〜TC-07 の各ファイルの差分は、このレビューの入力に含まれていない。そのため全件は照合していない。

新しい Critical/High はない。

> ITEM: V4 RESULT=read
> ITEM: V6 RESULT=read
> ITEM: V7 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I430] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | 網羅漏れ | 4-1 の D1 の行が挙げる漏れは「外に出したコマンドの中の書き込み」と「primary からの `git -C`」の 2 つだけ。git 自身の別ワークツリーへの破棄操作（`git worktree remove --force` など）は書いていない。外に出した `git *` に `-c alias.x='!…'` を付けた形の逃げ道も書いていない。後者は意図的な回避に近い。前者は worktree.md §9 が「破棄は技術的には止めない」としている範囲。どちらも既知 findings の F2 と実質同じで、新規には数えない。 | plan_I430.md:113 | 静的読解 |

反証失敗（新規指摘なし）。探索した仮説は次の 3 つ。

1. **D1〜D3 の代わりの仕組みと漏れの記載**
   - D1 は、サンドボックスの書き込み制限と `denyWrite` が代わり。漏れは 4-1 の 113 行目に書いてある。
   - D2 は、GitHub のブランチ保護と既存の deny が代わり。bot は push できず、手元の作業は残るので、止まらない漏れは無い。
   - D3 は、マージと承認を GitHub が止める。取り込みは deny の `gh pr checkout`・`gh co` に置き換えた。
   - fork の PR への ready・edit・update-branch も、漏れとして 4-1 の 122 行目に書いてある。
2. **`gh pr checkout` の別の書き方**
   - `gh -R x pr checkout` のような形は deny の前方一致に当たらない。
   - ただし allow の 48〜55 行目に `gh pr checkout` 系は無く、`gh *` は外に出すだけで承認の対象のまま残る。確認が出るので、黙って通らない。
3. **残した判定の根拠**
   - G01・G06〜G08・G10〜G15・G16〜G32・G36〜G39 は、どれも 4-1 の表で「公式にも GitHub にも無い」か「GitHub でも止まらない」に対応している。

> ITEM: V5 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: 1b28fa89532eb85740a42db522aa644a8115015c
ROUNDS: 1
VERDICT: OK
