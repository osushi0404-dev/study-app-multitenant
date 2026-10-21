# I174 敵対的レビュー（/code-review 20261019_0037 の後・第 2 周）

- 対象: HEAD 73fbd19（第 1 周の修正 `I174_adversarial_review_20261020_2001.md` の後）
- 周回: 第 2 周（3 エージェント並列・各 20 分の時間上限・実測 3〜12 分）。この /code-review の累計エージェント数 6
- KNOWN_FINDINGS: 過去の `I174_adversarial_review_*.md` の全 findings・計画 0-11〜0-13 の先送り一覧

## 観点と結果

| 観点 | NEW_CRITICAL | NEW_HIGH | 備考 |
|------|------|------|------|
| 1. ロジック回避・実機 repro | 0 | 2 | Medium 2・Low 2 |
| 2. テストの false-green・tautology | 0 | 1 | Medium 1・Low 1 |
| 3. 要件・脅威モデルの網羅漏れ | 0 | 2 | Medium 1・Low 1（High の 1 件は観点 1 の #1 と同じ） |

## findings と対応

| # | 重大度 | 観点 | 指摘 | 対応 |
|---|------|------|------|------|
| 1 | High | ロジック・要件 | 第 1 周 #1 の修正 (iii) は先頭が xargs / parallel で `git` `push` が独立した語のときだけ。`xargs -I{} sh -c 'git push origin {}'`・`xargs sh -c 'git push origin "$@"' _`・`timeout 60 xargs …`・`env xargs …` が素通し（実機で bare remote に main ができた） | (iii) を「語のどこかに xargs / parallel があり、どこかの語に push という語を含む」に広げた（引用符の中・包んだ形も確認〔ASK〕）。テスト XP8・XP9・XP25 |
| 2 | High | ロジック | 宛先を書かない push・`HEAD` 宛ての push で、今のブランチを見張り自身の作業ディレクトリで調べていた。`git -C <develop の worktree> push`・`cd <そこ> && git push`・`bash -c 'cd … && git push'` が素通し（実機で remote に develop ができた） | `_current_branch(path)` に。`_push_protected_target` は `git -C`（重ねたら連結）とその前の `cd` / `pushd` の先を見る。入れ子のシェルの中は `_analyze` が単純コマンドを順に見ながら `cd` を引き継ぎ、`_cmd_danger` の push 判定に渡す。`-C` の値が変数・置換なら確認。テスト XP10〜XP18 |
| 3 | High | 要件 | `parallel` / `watch` にコマンドを引用符で 1 語に包んで渡す形を展開せず、`parallel 'rm -rf /' ::: x`（`DANGER_OK=1` 付きでも）・`parallel 'git reset --hard {}'`・`watch 'rm -rf backend'` などが素通し | `_expand`: parallel / watch は後ろの語をつないでシェルで実行するので、eval と同じくつないだ文字列を読み直す。テスト H17〜H23（container）・XP24 |
| 4 | High | テスト | 第 1 周 #5 で STUBS を広げたが、それを通るケースが DANGERS に無く測れていない。`rm -fr` / `rm -fR` はどのテストにも無い | DANGERS に `rm -fr`・`rm -fR`・`git push -f`・`git push origin +feature/x`・`git push origin HEAD:main` を追加（cases 1844→3189） |
| 5 | Medium | ロジック | 絶対パス・`git.exe` で呼ぶ git の push を判定しない（`"git" in toks` の完全一致） | `_git_push_parts`: basename が git / git.exe の語の後ろの push を見る。`_cmd_danger` も git.exe を git と扱う。テスト XP19・XP20 |
| 6 | Medium | ロジック | `-o ci.skip` などの値を remote と読み違え、宛先を書かない push の判定が外れる | `_push_positionals`: 値を取るオプション（`-o`・`--push-option`・`--receive-pack`・`--exec`・`--repo`）の値を除く。テスト XP14・XP23 |
| 7 | Medium | 要件 | glob の refspec（`refs/heads/*`）・`git -c push.default=matching push` が保護ブランチへの push と判定されない（実機でリモートの main が更新された） | `_norm_push_dest`: glob が保護ブランチに一致すれば停止。`-c push.default=…` の push は確認。テスト XP21・XP22・XP26・XP27 |
| 8 | Medium | テスト | container の S19 が作業ツリーに `backend/.env` があるときだけ合格する（環境に依存） | S19 は一時ディレクトリに `.env` を作ってそこを検索する形に |
| 9 | Low | ロジック | `@`（HEAD の別名）を今のブランチとして解決しない | `_norm_push_dest` で `@` も解決。テスト XP15 |
| 10 | Low | テスト | 差分テストの「bash が実行しない形」が最上位にしか無い | `bash <<'X'` の中のコメント・ヒアドキュメント本文、`bash -c '… # …'` を追加。これで `bash -c` の中のコメントの push を確認にしていた余計な判定（(ii)）が見つかり、中のコメントを除いてから判定するよう修正 |
| 11 | Low | 要件 | 大規模 rebase は settings.json の ask 頼みだが、`git -C . rebase` 等の形は当たらないことがある | danger-ops.md の「見張りが判定しないもの」に、この形で書かないことを追記 |

## 決定論ゲート（`docs/tests/open/I174_auto_test.md`・38 行）

gates=38 failed=0。container pass=747・push pass=114・matrix pass=301・作業記録の再判定 新しく確認・停止 0 件・差分テスト cases=3189 bash実行=3063 見逃し=0 余計な停止=0。

## 判定

新規 High 4 件（#1〜#4・すべて修正済み）。第 3 周（最終周）で修正を含めて再度反証する。

VERDICT: HIGH
