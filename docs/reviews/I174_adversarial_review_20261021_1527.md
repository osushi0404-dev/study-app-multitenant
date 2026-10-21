# I174 敵対的レビュー（/code-review 20261021_1509 の後・第 1 周）

- 対象: HEAD 02a5b20。範囲は前回の敵対的レビュー（_20261021_1140）以降の差分 `b49532d..HEAD`（計画 0-15「場所・対象が 1 つに決まらない git の書き換えは確認」・0-16「見張りが判定のために実行する git を、このリポジトリと worktree に限る」）に絞った（I181 の観点・ユーザー了承）
- 基本レビュー: `docs/reviews/I174_code_review_20261021_1509.md`（FINAL_VERDICT: OK・RISK: YES）
- 周回: 第 1 周（3 エージェント並列・各 15 分の時間上限・実測 3〜6 分）

## 観点と結果

| 観点 | NEW_CRITICAL | NEW_HIGH | 備考 |
|------|------|------|------|
| 1. ロジック回避・実機 repro | 0 | 1 | Medium 1 |
| 2. テストの false-green・tautology | 0 | 0 | Medium 2・Low 2 |
| 3. 要件・脅威モデルの網羅漏れ | 0 | 1 | Medium 1（観点 1 の Medium と同じ）・Low 1 |

## findings と対応

| # | 重大度 | 観点 | 指摘 | 対応 |
|---|------|------|------|------|
| 1 | High | ロジック | 条件付きの cd（`false && cd sub; git checkout -- f`・`true \|\| cd sub; …`・`[ -d ../wt ] \|\| cd ../wt; git push origin HEAD`）を必ず実行される cd と扱い、cd の先だけを調べて素通し（実行で変更が消えた） | `_CD_COND_RE`: `&&`／`\|\|` の右側の cd の後に `;`・改行・`\|\|` が続く形と、`cd X \|\| <exit・return 以外>` は場所が 1 つに決まらない扱い（確認）。`cd X && git …`・`cd X \|\| exit 1; git …` は精密のまま。テスト G88〜G92・XP76・XP77 |
| 2 | High | 要件 | `--git-dir` に信頼する git-dir を書き別の場所で実行する形（`cd <worktree> && git --git-dir=<主の .git> checkout -- f`）が素通し。本物の git は `--work-tree` が無ければ作業ディレクトリを作業ツリーにするが、見張りは信頼する最上位を作業ツリーとして調べていた（0-16 による後退・実行で変更が消えた） | `_git_resolve(loc, need_worktree)`: ファイルの変更を調べるときは、`--git-dir` だけの形は作業ディレクトリが最上位と一致するときだけ信頼（それ以外は確認）。今のブランチ（push の宛先）は git-dir の HEAD で決まるので問わない。テスト G94・G95・XP78（主の .git の push は feature/x 宛てで 0） |
| 3 | Medium | ロジック・要件 | 信頼の起点が見張りの作業ディレクトリ。Bash の作業ディレクトリが入れ子のリポジトリに移っていると、そこを信頼して clean フィルタが判定中に動く（フックの作業ディレクトリが Bash に追随するかは未実証） | 起点を `CLAUDE_PROJECT_DIR`（無ければ作業ディレクトリ）に固定。作業ディレクトリが入れ子のリポジトリなら `_nested_git` で外れる。テスト G93 |
| 4 | Medium | テスト | `_GIT_SAFE_OPTS` を空にしても落ちない（G81 は判定対象の `-c` がもともと渡らないので通る） | G98（信頼するリポジトリ自身の設定の core.fsmonitor でも判定中に実行しない）。外した複製で FAIL を確認 |
| 5 | Medium | テスト | `_clean_git_env` を外しても落ちない（見張りの環境の `GIT_INDEX_FILE` 等で取り消しが素通し） | G99（`GIT_INDEX_FILE` を付けて起動しても 2）。外した複製で FAIL を確認 |
| 6 | Low | テスト | `cd -` を見分ける条件を外しても落ちない（`sub/-` が存在しないことで通っていた） | G97（`sub/-` を作ったうえで `cd sub; cd -; …` が確認）。外した複製で FAIL を確認 |
| 7 | Low | テスト | `--work-tree` だけが食い違う形のテストが無い | G96 |
| 8 | Low | 要件 | danger-ops.md に 0-16（信頼しない場所では確認・判定中に外の設定で実行しない）が書かれていない | danger-ops.md の見張りの 2. に追記 |

## 決定論ゲート

gates=38 failed=0（container 769・push 167・checkout 107・worktree 30・matrix 301・作業記録の再判定 新しく確認・停止 0・差分テスト 3,984 件 見逃し 0）。

## 判定

新規 High 2 件（#1・#2・修正済み）。第 2 周で修正を含めて再度反証する（範囲は引き続き `b49532d..` の差分）。

VERDICT: HIGH
