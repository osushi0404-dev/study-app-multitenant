# 実装レビュー [I174]（再レビュー・4 回目・fix-loop 手順5.5・独立サブエージェント）

- 実施方法: 前回までと同じく、同じ指示書で I174 の差分だけを材料にした独立サブエージェント。前回NG（`docs/reviews/I174_fix_implementation_review_20261017_0230.md`）の解消を fail-closed で検証。連続 NG 3 回のエスカレーションの後、ユーザーの了承（2026-10-17「推奨のやり方で」）で 4 回目を実施。今回から脅威モデル「事故」を重大度の基準として明示した。

## 前回NG指摘の解消
| 指摘 | 解消 | 根拠 |
|---|---|---|
| HIGH: `)` の直後の `#` をコメントと見なさず、次の行を飲み込んでいた | 解消 | コメント判定を `_is_comment_start` の 1 か所にまとめ、`_COMMENT_PREV = " \t;&|()<>"` に `)` `<` `>` を追加。`_scan_quotes` と `_strip_comments` の両方が呼ぶ。実測: `(true)#<<EOF⏎rm -rf backend`・`(ls)#<<EOF⏎git push --force origin main`・`(true)#<<EOF⏎docker compose exec -T backend python manage.py flush --noinput` は exit 2、`(cd /tmp)#<<X⏎docker compose exec backend some_unknown_cmd` は ask。テスト A155〜A157・C56 |
| Info: ホストの素の python3 の `shutil.rmtree('backend')` の残余リスク | 解消 | 計画書 0-10 の「残余リスク（受け入れ・追記）」に明記 |

## 実行した検証（reviewer）
- 自動テスト全件合格: container 559・settings 12・push 87・checkout 14・worktree 27
- `#` がコメントでない形（`echo a#b`・URL の `#frag`・`${#x}`・`$#`・`$((16#ff))`・引用符の中・`\#x`・`x=1#2`・`(git status)#c`・`echo a#<<EOF`・`manage.py test #note`・`python3 -c "print(1)#x"`）はすべて素通し・例外なし
- `#` が語の途中の形の次の行の危険コマンド（`echo a#b⏎rm -rf backend` 等）はすべて exit 2
- 従来のコメントの形の次の行の危険コマンドはすべて exit 2
- 止めすぎる側（受け入れ済み）: `echo $(true)#<<EOF⏎rm…` は exit 2
- Python コードの中の `#` も正しく扱う
- 素通しになった形（`true>#<<EOF`・`cat <#<<EOF`・`{ true; }#<<EOF`・`echo "x"#<<EOF`・`echo 'a'#<<EOF`）は bash 本体でも次の行が実行されないか本物のヒアドキュメントで、取りこぼしではない
- スコープ: 対象ファイル内。計画書 0-10 の追記が案 C と今回の修正に対応

## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| Info | 回帰・副作用 | `_scan_quotes` の docstring が「空白・; & \| ( の直後」のままで、`)` `<` `>` の追加が反映されていない（動作に影響なし）→ 修正済み | `scripts/claude/hooks/pretooluse_guard.py` |

VERDICT: OK
