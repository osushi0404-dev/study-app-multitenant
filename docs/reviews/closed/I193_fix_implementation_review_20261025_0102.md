# 実装レビュー [I193]
## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| Info | 方針一致 | 診断メモの H1・H2・M1・M2・M3・M5・L1・L2 は、どれも方針どおりの案 A で実装されている。M4 は採らない方針どおり、コードに変更がない。 | flow-stage.sh、proceed/SKILL.md、gate-check.sh、code-review.sh、review-gate/SKILL.md |
| Info | 回帰・副作用 | `extract_gate_commands`（code-review.sh:256）は gate-check.sh から source で読み込まれる。`ISSUE` は gate-check.sh:16 で設定済みで、`GC_TMP` も `trap` の前に作られる。PR コメントを切り詰める `sed` の見出し文字列は、code-review.sh:555 で出力される見出しと一致する。 | gate-check.sh、code-review.sh |
| Info | 回帰・副作用 | `GATE_BASE` の存在確認は、`dirty` の判定より後ろに移った。`dirty` と `base` が同時に起きたときは `dirty` が先に出る。G12 は clean な状態で動くため、既存テストには影響しない。 | gate-check.sh |
| Info | エッジケース | `branch_patch_of` は `@@` と `index` で始まる行を除く。差分の内容行は `+`、`-`、空白のどれかで始まるため、内容行を誤って除くことはない。REVIEWED_COMMIT の時点にファイルが無かった場合は空文字との比較になり、「変更あり」として数えられる。これは fail-closed 側の動きで妥当。 | gate-check.sh の `diff_outside_records` |
| Info | 回帰・副作用 | `wait_ci` は、ジョブ名を読めないと `NO_JOBS` で即座に exit 1 にする。以前は時間切れまで待って exit 3 になっていた。review-gate/SKILL.md に対応する分岐が追加されており、C10b のテストも新しい動作に更新されている。 | code-review.sh の `wait_ci`、review-gate/SKILL.md |

テストは、G14（develop の取り込み）、G15（決定論ゲートの節）、G16（テンプレート）、G17（空白を含む名前）、F11、S13 が追加されている。G 系の一時リポジトリは feature ブランチにする形に直されており、実際の使い方に合っている。セキュリティの後退や、スコープ外の変更は見当たらない。

VERDICT: OK
