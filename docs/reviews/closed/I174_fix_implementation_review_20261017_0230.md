# 実装レビュー [I174]（再レビュー・3 回目・fix-loop 手順5.5・独立サブエージェント）

- 実施方法: 前回までと同じく、同じ指示書で I174 の差分だけを材料にした独立サブエージェント。前回NG（`docs/reviews/I174_fix_implementation_review_20261017_0200.md`）の解消を fail-closed で検証。連続 NG 2 回のエスカレーションの後、ユーザーの了承（2026-10-17「推奨のやり方で」）で 3 回目を実施。

## 前回NG指摘の解消
| 指摘 | 解消 | 根拠 |
|---|---|---|
| HIGH: コメントの中の `<<EOF` をヒアドキュメントの始まりとして扱い、次の行を飲み込む | 一部解消（同じ種類の穴が残る） | 前回の 6 つの再現は作業ツリー版ですべて 2（`# note <<X⏎... some_unknown_cmd` は ask）。`ls;#<<EOF`・`ls\|#<<EOF`・`ls &#<<EOF`・`(true) #<<EOF`・`echo $(echo hi) # <<EOF`・バッククォート・`ls\⏎# <<EOF`・`echo hi # <<-EOF` の後の rm -rf も 2。ただし、コメントの始まりと見なす直前の文字に `)` が無く、`(cmd)#<<X⏎...` が残る（指摘 1） |
| Medium: 自動テスト文書の件数とケース表 | 解消 | TC-01 は `pass=552`。ケースの ID の集合はテストスクリプトと文書で一致（comm で差分なし）。実行も `pass=552 fail=0`・settings `pass=12 fail=0` |

回帰・副作用の確認で問題がなかったもの: `#` がコメントでない形（`echo a#b`・URL の `#frag`・`${#x}`・`$#`・`$((16#ff))`・引用符の中・`\#`・`x=1#2`・`{ ls; }#<<EOF`・`echo $(true)#<<EOF`・複数行の引用符の中）・本物のヒアドキュメント本文の中の `#`（manage.py shell・psql・bash・cat）・`$(...)` の中のコメント・250 件のランダム入力で例外なし・前回までに直した形。

## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| HIGH | 前回NG の未解消・回帰（fail-closed） | `)` の直後の `#` をコメントと見なさず、後ろの `<<EOF` をヒアドキュメントとして扱って次の行を飲み込む。実測（作業ツリー／HEAD／develop）: `(true)#<<EOF⏎rm -rf backend` は 0／0／2、`(ls)#<<EOF⏎git push --force origin main` は 0／2／2（今回の差分の回帰）、`(true)#<<EOF⏎docker compose exec -T backend python manage.py flush --noinput` は 0、`(cd /tmp)#<<X⏎docker compose exec backend some_unknown_cmd` は 0。bash では `(…)#` から行末がコメントで、次の行が実行される（実測）。`case` の `pattern)#…` も同じ見込み。分類: **(a) 実行の不備**（コメントの始まりと見なす直前の文字に `)` を足し、2 か所の判定を 1 つの関数にまとめる。4 形をテストに足す） | `pretooluse_guard.py` の `_scan_quotes`・`_strip_comments` |
| Info | 回帰・副作用（範囲外の確認） | ホストの素の python3 での `shutil.rmtree('backend')` は素通し（計画書 0-10 の方針どおり・回帰ではない）。残余リスクとして明記するかの判断材料 | 計画書 0-10 |
| Info | 回帰・副作用 | compose で存在しないモジュールを import する読み取りコードが確認になる（止める側・問題なし） | `_SAFE_IMPORT_ROOTS` |

VERDICT: HIGH

## fix-loop の扱い
- 実装レビュー（手順5.5）の連続 NG が 3 回になった。ループ暴走ガードにより自動の差し戻しを止め、ユーザーにエスカレーションした。
