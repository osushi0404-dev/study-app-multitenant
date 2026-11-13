# 敵対的レビュー [I430]（別プロセス・2026-11-13 18:47）

- 見た範囲: origin/develop...8da6b9a3e4568657a3d4e0999eb42b5eb5ad05be
- 所要時間: 330 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- ⛔ 拒否の一覧を読めない記録がある（承認が要る操作で止まったかを確かめられないので、この周は合格にしない）
- コンテナ: 確かめていない（ブランチに backend/ の変更なし）
- 一覧: docs/plans/open/plan_I430.md の「## 必ず確かめる項目」（8 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 実験必須 | 読んで確認 | ― | 未検証（実験必須を読んで確認しただけ） |
| V2 | 1 | 実験必須 | 未実施 | ― | 未検証（未実施） |
| V3 | 1 | 実験必須 | 読んで確認 | ― | 未検証（実験必須を読んで確認しただけ） |
| V4 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V5 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V6 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V7 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V8 | 1 | 実験必須 | 未実施 | ― | 未検証（未実施） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり（続きの呼び出しが終わらなかった（exit=1）ため、前の報告で判定（その後の実験の結果は読まれていない）） | 328 秒 | 1 | 0（読めない記録あり） | $0.4878 | ― | ― | ― |
| 2 | 報告あり | 36 秒 | 0 | 0 | $0.2969 | ― | ― | ― |
| 3 | 報告あり | 23 秒 | 0 | 0 | $0.2407 | ― | ― | ― |

## 実験

### 観点 1

#### P1-E1: 判定できない（実験役の記録を読めない）
~~~
bash -c 'ulimit -v 2097152; timeout 150 claude -p --model haiku --permission-mode auto --setting-sources user --settings .claude/settings.json "Bashツールで次を1つずつ実行し、各コマンドの出力と成否をそのまま報告せよ。(1) echo x > /mnt/c/app/study-app-multitenant/.claude/worktrees/app-1/zz_probe_I430 (2) echo x > /mnt/c/app/study-app-multitenant/zz_probe_I430 (3) git status --short | head -1 && echo x > /mnt/c/app/study-app-multitenant/.claude/worktrees/app-1/zz_probe2_I430 (4) git --version && echo x > /mnt/c/app/study-app-multitenant/.claude/worktrees/app-1/zz_probe3_I430 (5) dangerouslyDisableSandbox を true にして echo x > /mnt/c/app/study-app-multitenant/zz_probe4_I430 を実行" 2>&1 | head -60'
~~~
出力の先頭:
~~~

~~~

#### P1-E2: 判定できない（実験役の記録を読めない）
~~~
bash -c 'ulimit -v 2097152; timeout 200 claude -p --model haiku --permission-mode auto --setting-sources user --settings .claude/settings.json "Bashツールで次を1つずつ実行し、承認の確認が出たか否かと出力の先頭を報告せよ。(1) gh issue view 430 --json state (2) git fetch --dry-run origin develop (3) docker compose ps (4) bash scripts/claude/test-session.sh と実行できる最小の引数で PONG を返させる（使い方が分からなければ head -20 scripts/claude/test-session.sh を読んで決める）" 2>&1 | head -60'
~~~
出力の先頭:
~~~

~~~

#### P1-E1: 実行した（続きの呼び出しが終わらず、結果は読まれていない）
~~~
bash -c 'ulimit -v 2097152; timeout 150 claude -p --model haiku --permission-mode auto --setting-sources user --settings .claude/settings.json "Bashツールで次を1つずつ実行し、各コマンドの出力と成否をそのまま報告せよ。(1) echo x > /mnt/c/app/study-app-multitenant/.claude/worktrees/app-1/zz_probe_I430 (2) echo x > /mnt/c/app/study-app-multitenant/zz_probe_I430 (3) git status --short | head -1 && echo x > /mnt/c/app/study-app-multitenant/.claude/worktrees/app-1/zz_probe2_I430 (4) git --version && echo x > /mnt/c/app/study-app-multitenant/.claude/worktrees/app-1/zz_probe3_I430 (5) dangerouslyDisableSandbox を true にして echo x > /mnt/c/app/study-app-multitenant/zz_probe4_I430 を実行" 2>&1 | head -60'
~~~
出力の先頭:
~~~

~~~

#### P1-E2: 実行した（続きの呼び出しが終わらず、結果は読まれていない）
~~~
bash -c 'ulimit -v 2097152; timeout 200 claude -p --model haiku --permission-mode auto --setting-sources user --settings .claude/settings.json "Bashツールで次を1つずつ実行し、承認の確認が出たか否かと出力の先頭を報告せよ。(1) gh issue view 430 --json state (2) git fetch --dry-run origin develop (3) docker compose ps (4) bash scripts/claude/test-session.sh と実行できる最小の引数で PONG を返させる（使い方が分からなければ head -20 scripts/claude/test-session.sh を読んで決める）" 2>&1 | head -60'
~~~
出力の先頭:
~~~

~~~

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I430] ── 観点: 1. ロジック回避・実機 repro

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| - | - | 現時点で新規指摘なし。V1・V2・V3・V8 は実験の結果待ち | - | 下の実験案 |

読んで確かめた範囲では、次の 3 点を確認した。
- `.claude/settings.json` に `allowUnsandboxedCommands: false`、`denyWrite: [".claude/worktrees"]`、`excludedCommands` が計画どおり入っている。
- `excludedCommands` に `bash *`・`sh *`・`python3 *` の類は無い。
- 中に残る部分に限って見ると、`git *` を外に出す設計でも、`git push … && echo x > <別WT>` の `echo` は `git *` に当たらない。呼び出しの中のコマンドが**すべて**当たるときだけ外で動くので、全体が中で動き、`echo` はサンドボックスが止めるはずだ。これは実験 E1 で確かめる。

次の 2 つの実験を提案する。

> EXPERIMENT_BEGIN P1-E1
bash -c 'ulimit -v 2097152; timeout 150 claude -p --model haiku --permission-mode auto --setting-sources user --settings .claude/settings.json "Bashツールで次を1つずつ実行し、各コマンドの出力と成否をそのまま報告せよ。(1) echo x > /mnt/c/app/study-app-multitenant/.claude/worktrees/app-1/zz_probe_I430 (2) echo x > /mnt/c/app/study-app-multitenant/zz_probe_I430 (3) git status --short | head -1 && echo x > /mnt/c/app/study-app-multitenant/.claude/worktrees/app-1/zz_probe2_I430 (4) git --version && echo x > /mnt/c/app/study-app-multitenant/.claude/worktrees/app-1/zz_probe3_I430 (5) dangerouslyDisableSandbox を true にして echo x > /mnt/c/app/study-app-multitenant/zz_probe4_I430 を実行" 2>&1 | head -60'
> EXPERIMENT_END P1-E1

> EXPERIMENT_BEGIN P1-E2
bash -c 'ulimit -v 2097152; timeout 200 claude -p --model haiku --permission-mode auto --setting-sources user --settings .claude/settings.json "Bashツールで次を1つずつ実行し、承認の確認が出たか否かと出力の先頭を報告せよ。(1) gh issue view 430 --json state (2) git fetch --dry-run origin develop (3) docker compose ps (4) bash scripts/claude/test-session.sh と実行できる最小の引数で PONG を返させる（使い方が分からなければ head -20 scripts/claude/test-session.sh を読んで決める）" 2>&1 | head -60'
> EXPERIMENT_END P1-E2

> ITEM: V1 RESULT=read
> ITEM: V2 RESULT=not_done
> ITEM: V3 RESULT=read
> ITEM: V8 RESULT=not_done
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I430] ── 観点: 2. テストの false-green・tautology

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | FG の弱さ | FG は `run_check` が返す exit 1 だけを見ている（`>/dev/null 2>&1`）。注入ファイルが作られなかったときや check.py が例外で落ちたときも「不合格を検知した」と数えるため、偽合格になる。現状は S1 が通り、注入するキーも実在するので実害は出ていない。ただ、注入用の heredoc の途中で例外が出ると、後続の `sb_*`・`no_deny_gh_*` がすべて「不合格」を返して素通りする。 | test_settings_permissions.sh:118, 123-177 | 静的読解。実験はしていない |
| Low | V4 の穴 | `denyRead` の検査と FG が `~/.config/github-app` だけを見ている。鍵の控えがある `~/.cache/github-app` を設定から消しても TC-01 は合格のままになる。計画 4-2 と S11 は両方を守る前提なので、検査が設定より弱い。コードレビュー記録の F4 と同じ指摘だが、既知 findings には載っていないため改めて書く。 | test_settings_permissions.sh:53-54, 172 | 静的読解 |
| Low | V4 の穴 | `excludedCommands` の判定は `e.strip()` と固定集合の完全一致だけを見ている。`bash  *`（空白が 2 つ）、`python3 scripts/*`、`bash scripts/*` のような広い書き方は落とせない。意図的な回避に近いので Low とする。 | test_settings_permissions.sh:56-60 | 静的読解 |

V4 の中心部分は確認できた。`sb_excl_bash`・`sb_excl_sh`・`sb_excl_python3`・`sb_excl_star` の 4 つの FG は、それぞれ `bash *`・`sh *`・`python3 *`・`*` を足す。`_wide_excl` はこの 4 つをすべて含むので、いずれも落とせる。`enabled`・`allowUnsandboxedCommands`・`failIfUnavailable`・`denyWrite` の FG も、実際の設定にあるキーを壊す形になっている。

V7 も確認できた。deny `Bash(gh pr checkout *)`・`Bash(gh co *)` は diff の設定にある。check.py の必須 deny 一覧にも入っていて、FG の `no_deny_gh_checkout`・`no_deny_gh_co` が 1 つずつ除去する。

V6 は一部しか確認できていない。差分が途中で切れていて、各テストの期待値を全部は追えなかった。確認できたのは次の 2 点。
- G87 は、期待値を ASK から 0 に変えた。消した D2 の保護ブランチ判定の結果であり、PWNED が出ないことを守る目的も残っている。
- 計画変更記録の「消した例の一覧」は、D1〜D3 ごとに分類してあり、残す判定の例は混ざっていないように読める。

実験は使っていない。

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
| Low | 網羅漏れ | 4-1 の表の D1 の行は、漏れとして「外に出したコマンドの中の書き込み」と「primary からの `git -C`」を挙げている。`git worktree remove --force <別>` や `git clean`・`git checkout -- .` のような git 自身の破棄操作が、別ワークツリーに向く形は書いていない。`git *` は外で動くので、サンドボックスは止めない。ワークツリーのセッションでは Claude Code が別ワークツリーを指す git を断るので、実害は primary のセッションに限られる。また worktree.md §9 は元から「破棄は技術的には止めない」としている。 | plan_I430.md 4-1 の D1 の行・4-2 の `git *` の行 | 静的読解。実験で裏取りしていない。 |
| Low | 網羅漏れ | G34・G35 を消した。その結果、fork の PR への `gh pr edit` は allow にある `gh pr edit *` で確認なしに通る。計画は「GitHub が実害を止める」としているが、題や本文の書き換えは GitHub では止まらない。表には漏れとして書いてあるので、書き漏らしではなく受け入れ済みの扱い。記録上、fork の PR を扱った回数は 0 件。 | 4-1 の fork の PR の行 | 静的読解。 |

Critical・High の新規指摘はない。

## V5 の確認
- D1（Bash の別ワークツリーへの書き込み）: 代わりの仕組みはサンドボックスの書き込み制限と `denyWrite`。S2・S19 の試しがある。止まらない漏れ（外に出したコマンド、primary からの `git -C`）が書かれていて、残す判定（G01・G13〜G15）に対応している。
- D2（保護ブランチへの push）: 代わりの仕組みは GitHub のブランチ保護と既存の deny。表には「止まらない漏れは無い」と書いてある。bot は push できず、手元の作業は残るので、この記述は妥当。force・削除・`--no-verify` は GitHub でも止まらない漏れとして G06・G07・G08・G10〜G12 を残している。
- D3（fork の PR）: マージと承認は GitHub が止め、取り込みは deny に置き換えている。ready・edit・update-branch は漏れとして書かれ、受け入れ済み。G33 の取り込みの deny が前方一致である点は R9 に書いてある。
- 残した判定（G01・G13〜G32・G36〜G39）はどれも、「公式でも GitHub でも止まらない」に対応する説明が表の中にある。

反証失敗。探索した仮説は 3 つ。(1) 消した判定ごとに代わりの仕組みがあるか。(2) git を外に出したことで生じる書き込みの穴。(3) GitHub が止めない fork の PR の操作。

> ITEM: V5 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 4
REVIEWED_COMMIT: 8da6b9a3e4568657a3d4e0999eb42b5eb5ad05be
ROUNDS: 1
VERDICT: HIGH
