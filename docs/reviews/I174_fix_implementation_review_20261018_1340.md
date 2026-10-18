# I174 fix-implementation レビュー（2026-10-18・代替実施）

`fix-implementation-review.sh` が `claude -p` の失敗で未実施（`I174_fix_implementation_review_20261018_1333.md`・SKIP）だったため、同じ指示書（`.claude/review-agents/fix-implementation-reviewer.md`）の独立サブエージェントで代わりに実施した。以下はその出力。

# 実装レビュー [I174]
## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| BLOCKER | 回帰・セキュリティ後退／方針との一致 | (a) 実行の不備。`$'…'` を `"…"` に書き換える処理で、`\x6d`・`\055`・`\n` などのエスケープが「\ を外した文字」になる（`\x6d` → `x6d`）。書き換え後の文字列は bash が作る文字列と別物になり、元の `$` も消える。HEAD では「宛先が動的な push」として確認だった `git push origin $'\x6dain'`・`git push origin $'ma\x69n'` が素通し（bash では main への push）。`git reset $'\x2d\x2dhard' origin/develop`・`rm $'-\x72f' build_tmp` も素通しのまま。 | `pretooluse_guard.py` `_join_continuations` の `$'` 分岐 |
| HIGH | エッジケース漏れ（テスト） | 差分テストに、危険なコマンドの引数そのものを `$'…'` のエスケープで書く形が無い。印を出す関数が `reset --hard` と `push --force` だけを見るので、保護ブランチへの push（`git push origin main`）を bash 側で「実行された」と判定しない。 | `guard_bash_oracle.py` の `CONTEXTS`／`DANGERS`／`STUBS` |
| Medium | 方針との一致 | 診断は「ヒアドキュメントが閉じない形も確認」としたが、`unsure` は「引用符が閉じていない」ときだけ（bash も本文として扱い実行しないので見逃しではない）。計画書と実装をそろえる。 | `pretooluse_guard.py` の `_analyze`・`plan_I174.md` 0-13 |
| Low | 副作用 | `bash -c 'DANGER_OK=1 git push origin main'` が ASK から 2 に（止める側の変化）。`_cmd_danger` と `_danger_reasons` の push の判定が重なり、理由が二重に出ることがある。 | `_cmd_danger` の push 判定 |
| Medium | スコープ整合 | `docs/issues/open/I157.md` の変更は I174 と無関係。I174 のコミットに含めない。 | `docs/issues/open/I157.md` |

VERDICT: BLOCKER
