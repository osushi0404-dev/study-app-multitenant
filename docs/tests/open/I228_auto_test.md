# I228 自動テスト: 敵対的レビューの確認済みの引き継ぎ・空振りした実験の扱い

実行コマンド: 下の「## 決定論ゲート（自動実走）」の各行（ハーネスのテスト。pytest・Jest・E2E は無い）

結果:
- 実装前（ステップ 1）: 新しい 17 件だけが落ちる（pass=116 fail=17）ことを確かめた
- 実装後: TC-01 pass=134 fail=0・TC-02 pass=174／157

## 実行記録
- 2026-11-13 review-gate の決定論ゲート（code-review.sh 自動実走・docs/reviews/I228_code_review_20261113_0112.md）: 4 行とも exit=0。test-gate に委譲（heavy）は無し

## TC-01: `scripts/claude/tests/test_i197_adversarial_process.sh`（既存＋I228 の追加）

一時の git リポジトリ（`develop` に base・`feature/I900-x` に変更 1 つ）で `adversarial-review.sh` を丸ごと流す。claude はスタブ。各ケースの合否は `ck` の期待値との一致で、ファイル全体は fail が 0 のとき exit 0。

| ケース | 準備 | 期待（すべて満たして PASS） | 守る受け入れ条件 |
|---|---|---|---|
| A29 引き継ぐ | 1 周目＝A1（V1 実験必須を実験で確認・OK）。その後に計画書の「## 計画変更記録」だけを直してコミット。2 周目の観点 1 は `ITEM: V1 RESULT=read` | 2 周目: exit 0・`ADVERSARIAL_VERDICT: OK`・`UNVERIFIED: 0`・V1 の判定が `確認済み（前の周から引き継ぎ: I900_adversarial_review_` で始まる・記録に `- 引き継ぎ:` と 1 周目の記録のファイル名・観点 1 の入力に「前の周から引き継ぎ済み」 | AC1 |
| A30 コードが変わったら引き継がない | A29 と同じ。ただし 1 周目の後に `a.txt` を変えてコミット | 2 周目: exit 1・`ADVERSARIAL_VERDICT: HIGH`・V1 が `未検証`・記録の引き継ぎの行に `a.txt` | AC1 |
| A31 項目の行が変わったら引き継がない | 1 周目の後に計画書の V1 の内容の文言だけを変えてコミット（記録の場所の中だけの変更） | 2 周目: V1 が `未検証`・HIGH・記録に「行が変わったため引き継がない: V1」 | AC1 |
| A32 祖先でなければ引き継がない | 過去の記録（ROUNDS: 1・`REVIEWED_COMMIT` は HEAD の祖先でないコミット・表に V1 `確認済み（実験）`）を置く | V1 が `未検証`・HIGH・記録の引き継ぎの行に「祖先でない」 | AC1 |
| A33 前の周で未検証なら引き継がない | 1 周目の観点 1 が `ITEM: V1 RESULT=read`（V1 未検証・HIGH）。記録だけを直してコミット。2 周目も read | 2 周目: V1 が `未検証`・HIGH | AC1 |
| A34 連鎖 | A29 の後に記録だけを直してコミットし、3 周目（`ADV_ROUND_LIMIT=3`）も read | 3 周目: V1 が `確認済み（前の周から引き継ぎ: ` で始まり、元は 2 周目の記録・OK | AC1 |
| A35 本文の偽の表の行を読まない | 過去の記録の「## 確かめる項目の結果」では V1 が `未検証`、「## 各観点の報告」の本文に `\| V1 \| 1 \| 実験必須 \| x \| x \| 確認済み（実験） \|` の行。REVIEWED_COMMIT は HEAD（祖先）、その後は記録だけの変更 | V1 が `未検証`・HIGH | AC1 |
| A36 コマンドが見つからない実験は数えない | A1 と同じ。スタブの実験役の P1-E1 の出力を `timeout: failed to run command ‘python’: No such file or directory` にする（I455 の記録の実物をそのまま・曲線引用符のまま） | V1 が `未検証`・HIGH・記録に「実行できなかった（コマンドが見つからない）」・2 回目のレビュー役の入力に `docker compose exec -T backend` | AC2 |
| A36b コンテナが止まっている | P1-E1 の出力を `service "backend" is not running` にする | V1 が `未検証` | AC2 |
| A37 正しい「無い」の実験は数える | P1-E1 の出力を `ls: cannot access 'x': No such file or directory` にする | V1 が `確認済み（実験）`・OK | AC2 |
| A38 案内の文 | A1 の観点 1 の入力 | 入力の「## 実験の約束」に `docker compose exec -T backend` | AC2 |
| FG-A30 | 本体の写しで `changed_outside_records` の結果を無視（常に 0 扱い）にする | A30 の準備で V1 が `確認済み`（＝A30 が落ちる） | AC1 の FG |
| FG-A31 | 写しで項目の行の比較を外す（今の一覧に id があれば引き継ぐ） | A31 の準備で V1 が `確認済み` | AC1 の FG |
| FG-A32 | 写しで、起点が比べる相手に戻ったら引き継がない確かめを外す（`REVIEWED_COMMIT` をそのまま使う） | A32 の準備で V1 が `確認済み` | AC1 の FG |
| FG-A35 | 写しで節の絞り込みを外す（記録全体の表の行を読む） | A35 の準備で V1 が `確認済み` | AC1 の FG |
| FG-A36 | 写しで `noexec` の振り分けを外す | A36 の準備で V1 が `確認済み` | AC2 の FG |
| 既存 A1〜A28・L・S・FG | 変更なし | すべて PASS（回帰なし） | AC4 |

## TC-02: `adversarial-review.sh` を読み込む既存のテスト（回帰）
- `scripts/claude/tests/test_i193_official_flow.sh`・`scripts/claude/tests/test_i202_ledger_cleanup.sh` が exit 0（AC4）

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i197_adversarial_process.sh
bash scripts/claude/tests/test_i193_official_flow.sh
bash scripts/claude/tests/test_i202_ledger_cleanup.sh
bash -n scripts/claude/adversarial-review.sh
```

## 再発防止記録（fix-loop・2026-11-13）
- なぜ失敗したか: review-gate §3-1 に足したコンテナの確かめ `docker compose ps --status running --services` が、allow の `Bash(docker compose ps)`（引数なしの完全一致）に当たらず、承認画面が出た（手動テスト No.3）
- 何を変えたか: 確かめを省き、常に `docker compose up -d backend`（冪等・allow の `Bash(docker compose up *)`）を流す形にした
- セキュリティ上の考慮点: 承認画面が出るのは止まる向きで、危ない操作が通る問題ではない。設定（`.claude/settings.json`）は変えていない
- 次回どう防ぐか: 手順書に Claude が流すコマンドを足すときは、`check-permission-prompt.sh` でその形（または同じ allow の規則に当たる副作用の無い形）を先に確かめる。今回は手動テストに足した行で捕まえた
- 確かめた結果: 手動 No.3（`docker compose up --help`）exit 0・TC-01 pass=134 fail=0
