# 実装レビュー [I074]
## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| Info | 回帰・副作用 | `_ansi_c_decode` で `$'\n'` 等の改行を展開すると `"…"` 内に生改行が入る。shlex はダブル引用符内の改行を文字列の一部として扱うため実害は生じないが、`_join_continuations` 後続の `_strip_comments`・継続つなぎ直し処理で理論的に想定外の動作をする可能性がある。差分テスト 1,844 件で bash と一致しており実害なし。 | `_join_continuations` の `$'…'` → `"…"` 変換 |
| Info | 回帰・副作用 | `_cmd_danger` 内の push 判定追加により `eval "DANGER_OK=1 git push origin main"` が停止する（入れ子の `DANGER_OK=1` は解除にならない）。計画書 0-13 で「止める側に寄った変化・意図的」と明記されており回帰ではなく仕様変更。 | `_cmd_danger` push 判定 |

VERDICT: OK
