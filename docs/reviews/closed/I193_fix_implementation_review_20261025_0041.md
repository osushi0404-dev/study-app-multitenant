# 実装レビュー [I193]

HEAD 固定やパス判定など、差分から確認できる範囲では回帰を見つけていません。9 件の fix-loop 診断（F1〜F9）は、差分で方針どおりに実装されています。

関数の存在、変数の初期化順、ワークフローのジョブ名は、`Grep` と `Read` でコードを確認しました。スクリプトとテストは実行していません。

## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| Info | 方針一致 | F1〜F9 はすべて診断の推奨案 A どおりです。F1 は gate-check が `path_risk_trigger` と `combine_risk` を再評価し、比べる相手が無いときは `REASON=base` で fail-closed にします。F2 は `REASON` を出し分け、dirty を先に判定します。F3 は close で記録を open へ戻します。F4 は headRefOid の一致とジョブ名の出そろいを見ます。F5 は `kill_tree`、F6 は HEAD ドリフトの BLOCKER 化、F7 は `set +e`、F8 は `cd` です。F9 の警告行除去も入っています。方針外の変更は見当たりません。`docs/issues/open/I186`・`I188`・`I189`・`I191`・`I192` と各 issue_review は、このイシュー以外の起票記録の未追跡ファイルです。変更の本体ではありません。 | 差分全体 |
| Info | 回帰・副作用 | `expected_ci_jobs` は `ci.yml` と `e2e.yml` の `jobs.*.name` を読みます。`ci.yml` の 6 ジョブと `e2e.yml` の 1 ジョブには、matrix も expression の名前もありません。`e2e.yml` に `paths` フィルタも無く、PR で常に動きます。このため、ジョブ名のずれで待ち続ける問題は今のところ起きません。ただし将来、ジョブ名に matrix や `${{ }}` を使うか、ワークフローに `paths` を足すと、成功しないまま時間切れ（exit 3）になります。これは fail-closed なので許容できます。`CI_WORKFLOWS` の既定値は、ワークフロー追加時に更新が必要です。 | `wait_ci` / `expected_ci_jobs` |
| Info | 回帰・副作用 | `gate-check` の高リスク判定は `merge-base(GATE_BASE, HEAD)` からの差分を使います。`code-review.sh` の `GIT_FILES` と範囲が完全に同じかは、この差分だけでは確認できません。`gate-check` は記録の RISK 行との OR で見ているので、`code-review.sh` より緩くなることはなく、安全側にずれます。 | `gate-check.sh` の `BRANCH_FILES` |
| Info | 方針一致 | `test-gate` の「記録の最後から 2 番目の `STAGE_DONE:` 行」による連続戻りの判定は、文章としてやや分かりにくいです。ただし、止める側に倒す記述なので問題はありません。 | `test-gate/SKILL.md` |

VERDICT: OK
