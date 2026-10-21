# 実装レビュー [I174]（再レビュー・fix-loop 手順5.5・独立サブエージェント）

- 実施方法: 前回（`docs/reviews/I174_fix_implementation_review_20261017_0130.md`）と同じく、同じ指示書で I174 の差分だけを材料にした独立サブエージェント。前回NG の解消を fail-closed で検証。
- 前提の確認（reviewer の実測）: 既存テスト全件合格（container 536・push 87・worktree 27・checkout 14・settings 12）。作業ツリー版・HEAD 版（`b1cf7aa`）・develop 版の 3 つで比較。

## 前回NG指摘の解消
| 指摘 | 解消 | 根拠 |
|---|---|---|
| HIGH: `_quote_state` が `#` のコメントを扱わず `# don't` の後の `<<'EOF'` を読み落とす | 解消 | ホストの `# don't worry⏎... shell <<'EOF' ...delete... EOF` は 2（HEAD は 0）。`ls # it's fine`・`# say "hi`・`ls;# it's` の後も 2。素の docker exec も 2。compose の読み取りヒアドキュメントは 0。`# Let's write⏎cat > f <<'EOF'⏎git push origin main⏎EOF` は 0。テスト A145〜A147・P71・P72 |
| Info: `echo "$(cat /dev/zero)"` で固まる | 解消 | `_read_exec_file` に `os.path.isfile`。`/dev/zero`・`/dev/urandom`・`/proc/self/fd/0` はすぐ 0。テスト P73 |
| Info: deny の残余リスク | 解消 | 計画書 0-10 の残余リスクに追記 |

回帰の確認: `echo a#b`・URL の `#frag`・`${#x}`・`$#`・`$((16#ff))`・`echo 'a # b'`・`echo "x #'"`・複数行の引用符の中の `#`・行末が `\` のコメントは、どれも後ろのヒアドキュメントを正しく判定。例外で落ちる入力は見つからない。

## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| HIGH | 回帰・副作用（fail-closed） | コメントの中の `<<EOF` をヒアドキュメントの始まりとして扱い、次の行から先の本当のコマンドを本文として飲み込む（bash では `# note <<EOF⏎echo EXECUTED` の 2 行目が実行されることを実測）。`_cut_heredocs` の `repl` が、`<<` の前がコメントかどうかを見ていない。実測（作業ツリー／HEAD／develop）: `# <<EOF⏎rm -rf backend` は 0／0／2、`ls # <<EOF⏎rm -rf backend` は 0／0／2、`# <<EOF⏎git push --force origin main` は 0／2／2（今回の差分の回帰）、`# example: cat <<EOF⏎docker compose exec ... manage.py flush --noinput` は 0、`# see <<EOF⏎... psql -c "DROP TABLE x"` は 0、`# note <<X⏎docker compose exec backend some_unknown_cmd` は 0（compose は develop では settings の ask が受け止めていた）。分類: **(a) 実行の不備**（`repl` の中で `<<` より前がコメントなら置き換えない。テストも足す） | `pretooluse_guard.py` の `_cut_heredocs`・`_quote_state` |
| Medium | スコープ整合（記録） | `docs/tests/open/I174_auto_test.md` の TC-01 の期待値が `pass=527`・「527 ケース」のままで、ケース表に A145〜A147・P71〜P73 が無い（実際は 536）。分類: (a) 実行の不備 | `docs/tests/open/I174_auto_test.md` |

VERDICT: HIGH

## fix-loop の扱い
- 実装レビュー（手順5.5）の連続 NG が 2 回に達したため、共通ルール「ループ暴走ガード」により自動の差し戻しを止め、ユーザーにエスカレーションした。
