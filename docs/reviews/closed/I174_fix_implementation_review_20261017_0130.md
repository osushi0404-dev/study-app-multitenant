# 実装レビュー [I174]（fix-loop 手順5.5・独立サブエージェント）

- 実施方法: `scripts/claude/fix-implementation-review.sh` は 3 回とも `claude -p` が失敗して未実施（`docs/reviews/I174_fix_implementation_review_20261017_0054.md`・`_0059.md`・`_0109.md`）。原因は、スクリプトが作業ツリーの未追跡ファイルをすべて材料に添付する作りで、このワークツリーには他イシューの未追跡ファイルが 107 個（約 613KB）あり、材料が大きすぎたこと（I174 の差分は 8 ファイル・約 600 行）。同じ指示書（`.claude/review-agents/fix-implementation-reviewer.md`）を使い、I174 の差分だけを材料にした独立サブエージェントでレビューした。スクリプトの不具合は別イシューで扱う（範囲外）。
- 前提の確認（reviewer の実測）: 既存テスト全件合格（container 527・push 87・worktree 27・checkout 14・settings 12）。第 3 周の再現コマンド（診断表の #1〜#6・#11・#7・#8）はすべて期待どおり。一覧外の呼び出し（`exec`・`from os import system`・別名の QuerySet 変数の update 等）は compose で ASK。

## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| HIGH | 回帰・副作用 | 前の行のコメントに `'` があると、ヒアドキュメントを読み落とす（新しく入った回帰）。新設の `_quote_state` が `#` のコメントを扱わず、`# don't worry` の `'` を引用符の開始と数え、次の行以降の `<<'EOF'` を引用符の中と判断して切り出さない。実測（head＝HEAD 版・new＝作業ツリー版）: ホストの `# don't worry⏎cd backend && python manage.py shell <<'EOF' ... .delete() ... EOF` は head＝2・new＝0、素の docker exec でも new＝0、compose の読み取りだけのヒアドキュメントは new＝ASK、同じ delete を compose で流すと head＝2・new＝ASK、`# Let's write notes⏎cat > f <<'EOF'⏎git push origin main ...` は push の誤停止が残る。分類: **(a) 実行の不備**（引用符の外の `#`〔行頭か空白の直後〕から行末を飛ばせば直る）。テストにもケースを足すべき | `pretooluse_guard.py` の `_quote_state` / `_cut_heredocs` |
| Info | 回帰・副作用 | `"$(cat X)"` があると X を読みに行くので、`echo "$(cat /dev/zero)"` で guard がフックの時間切れまで固まる（new は timeout 124・head は 0）。`os.path.isfile` で普通のファイルに限れば防げる | `_subst_content` / `_read_exec_file` |
| Info | スコープ | deny の絞り込みが Read にも及び、将来 `backend/.env.prod` のような名前を置くと Read の deny が効かない（Bash 側は `_SECRET_PATH_RE` が捕まえる）。残余リスクとして記録するとよい | `.claude/settings.json` |
| Info | 方針一致 | ホストの素の python で、API パスの文字列・`os.environ` の読み出しを含むものは ASK（案 C の 5 項どおり・回帰ではない） | `_code_findings` |

VERDICT: HIGH
