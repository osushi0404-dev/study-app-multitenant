# I174 敵対的レビュー（/code-review 20261021_1509 の後・第 2 周）

- 対象: HEAD 03ae0e8。範囲は `b49532d..HEAD`（計画 0-15・0-16 と第 1 周の修正）
- 周回: 第 2 周（3 エージェント並列・各 15 分の時間上限・実測 2〜5 分）。この /code-review の累計エージェント数 6

## 観点と結果

| 観点 | NEW_CRITICAL | NEW_HIGH | 備考 |
|------|------|------|------|
| 1. ロジック回避・実機 repro | 0 | 2 | — |
| 2. テストの false-green・tautology | 0 | 0 | Medium 1 |
| 3. 要件・脅威モデルの網羅漏れ | 0 | 1 | Low 2 |

## findings と対応

| # | 重大度 | 観点 | 指摘 | 対応 |
|---|------|------|------|------|
| 1 | High | ロジック | 第 1 周 #1 の `_CD_COND_RE` は cd の後ろを `[^;&\|\n]*` で読むため、`false && cd sub 2>&1; git checkout -- f`・`&>/dev/null` を条件付きの cd として見つけられず素通し（実行で変更が消えた・push も同様） | 正規表現をやめ、`_segments` と同じ区切り方で演算子を読む `_segments_ops`・`_cd_conditional` に置き換え（リダイレクトの `2>&1`・`&>`・`>&2` は区切りとして数えない）。テスト G100・G101 |
| 2 | High | ロジック | `cd link/..`（link はシンボリックリンク）を、見張りはリンクを先にたどって別の場所と読み、bash（論理パスで `..` を畳む）と食い違って素通し（実行で変更が消えた） | cd の先は bash と同じく文字の上で `..` を畳んでから realpath（`os.path.normpath` → `realpath`）。`-C` は git が chdir するので realpath のまま。テスト G102 |
| 3 | High | 要件（セキュリティ必須条件） | 見張りの `git status` が、索引に入った入れ子のリポジトリ（サブモジュール・gitlink）の中へ入り、その中の clean フィルタを承認前に実行（`git checkout -- .`・`-- sub`・対象が読めない形の `:/` で PWNED） | status に `--ignore-submodules=all`、実行する git に `-c submodule.recurse=false`。checkout / restore はサブモジュールの中身を戻さないので意味の上でも正しい（変更がサブモジュールの中だけのときの止めすぎ〔Low〕も解消）。テスト G103・G104（外した複製で PWNED を確認） |
| 4 | Medium | テスト | 見張りのテストが `CLAUDE_PROJECT_DIR` を外しておらず、この変数が書き出された環境で流すと一時リポジトリが「信頼しない場所」になり、多数が FAIL・確認を期待するテストは中身と関係なく通る | 見張りを動かすテスト 6 本（container・push・checkout・worktree・matrix・oracle）の冒頭で `unset CLAUDE_PROJECT_DIR`。`CLAUDE_PROJECT_DIR` を付けて流しても全件合格を確認 |
| 5 | Low | 要件（余計な確認） | `_NESTED_SHELL_RE`・`_scoped` を引用符の中にも当てるため、`cd … && git commit -m "fix(I179): eval …" && git push` が確認になる（このリポジトリのコミットの書き方で毎回出る） | `_loc_ambiguous` は引用符の中を除いてから判定。テスト XP79（0） |

## 決定論ゲート

gates=38 failed=0（container 769・push 168・checkout 112・worktree 30・matrix 301・作業記録の再判定 新しく確認・停止 0・差分テスト 3,984 件 見逃し 0）。

## 判定

新規 High 3 件（#1〜#3・修正済み）。第 3 周（最終周）で修正を含めて再度反証する。

VERDICT: HIGH
