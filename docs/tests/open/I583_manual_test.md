# I583 手動テスト: 番号のテストを本物のリポジトリの記録に頼らない形にする

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | このワークツリーに `docs/issues/open/I1000.md`・`docs/plans/open/plan_I1000.md`（「## 必ず確かめる項目」の表を含む）・`docs/reviews/open/I1000_review.md` を未追跡で置き、印のファイルを作る差し替えの `claude` を `PATH` の先頭に置いて `bash scripts/claude/tests/test_i569_issue_number_digits.sh` を流す。終わったら 3 つの記録を消す | exit 0・最後の行が `pass=<N> fail=0`（記録が無いときと同じ N）。差し替えの印のファイルができていない。消した後に `git status --porcelain` に I1000 の行が無い | Claude |  | 受け入れ条件 1 を本物のリポジトリで確かめる |

結論: OK / NG
