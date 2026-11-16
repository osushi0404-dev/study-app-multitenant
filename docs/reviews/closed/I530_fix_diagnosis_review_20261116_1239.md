# 診断レビュー [I530]

## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| Info | 根本原因 | 根本原因は `classify_gate` のコードで裏付けられている。`code-review.sh:396` は `;` `|` `&` `` ` `` `$(` `>` を含む行を UNSAFE にする。`:402-409` の allowlist には `bash -c` も `pre-commit run` も無い。3 行が UNSAFE になった説明として成立する。症状の言い換えではない。 | code-review.sh:385-411 |
| Info | 対応方針 | 案 A は妥当。分割後の行は `! grep -qF …` と `grep -qE …` の形で、メタ文字を含まない。`\(` は `$(` に当たらない。`run_one_gate` は `! grep` で終了コード 1（一致なし）だけを合格にする。ファイル不在（終了コード 2）は不合格になるので、偽の合格は出ない。案 B・C・D を退ける理由も妥当。特に案 D は安全境界を広げるので、範囲外とする判断は正しい。 | 対応方針 |
| Info | 対応方針 | shellcheck をゲートから外すことの代わりに、`bash -n` 4 行を入れ、shellcheck 自体は pre-commit と CI が流すと文書に明記する。この残余リスクの扱いは許容できる。テスト文書の AC に「ゲートで shellcheck を実走」と書いてあれば、その文言も直すこと。 | I530_auto_test.md:57-58, 70 |
| Info | 影響調査 | `grep -n 'bash -c\|pre-commit run' docs/tests/open/*_auto_test.md` を確かめる手順は妥当。実際に確認すると、I530 以外で該当するのは I034_auto_test.md:26 の `pre-commit run --all-files` だけだった。これは古い文書で、ゲートの節に入っているかは未確認。open 配下のこのブランチでは、I530 だけを review-gate に通す前提で足りる。 | I034_auto_test.md:26 |

## 影響調査の網羅性評価
- 同型の書き方（`bash -c` や `pre-commit run` を使うゲート行）は、open の文書を grep して確認する手順になっている。上記のとおり I530 以外に実害のある箇所は見当たらない。
- `classify_gate`・`run_one_gate`・`posttooluse_check.py` は変えない。それぞれ影響しないという記述は、コードを読んで確認できた。
- `! grep` の終了コードの扱いと `\(` の扱いも確認済み。

VERDICT: OK
