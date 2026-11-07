# I227 レビュー: レビューの判定を機械が読む形・変数に置き換える

## 変更概要
- `/security-review` の「差分なし」の判定を、表示の文字列の部分一致から本体の変数 `NO_DELTA`（引数）に替える
- 判定の行（`<名前>: <数>`）の正規表現を `findings_line_present()` の 1 か所にまとめる
- 組み込みのレビューの「読めたか」を、種類ごとの決まった形（`/security-review` は `SECURITY_FINDINGS` の行・`/code-review` は JSON として読める指摘の配列）だけで決める

## 変更点
- （実装後に記入）

## 影響範囲
- Backend/Frontend/DB: なし
- Config（ハーネス）: `scripts/claude/code-review.sh`・`scripts/claude/tests/test_i212_review_base.sh`・`scripts/claude/tests/test_i193_official_flow.sh`・`.claude/skills/review-gate/SKILL.md`・`docs/reviews/backlog/I212.md`

## テスト結果
- 自動: （test-gate で記入）
- 手動: （test-gate で記入）

## 計画との差分
- （実装後に記入）

## ロールバック
- PR を revert する（設定・データの変更なし）

## 自律判断の記録
- [plan] `/code-review` の「読めたか」を判定の行ではなく公式の決まった出力の形（JSON の指摘の配列）で決める — スパイク 2 回で `/code-review` が `--append-system-prompt` の指示に従わず、囲みの JSON 配列だけを出したため。受け入れ条件 2 の狙い（文の形に左右されない）は変えず、文言を合わせた
- [plan] 「差分なし」は既存の変数 `NO_DELTA` を引数で渡す — 判定の前にいつも決まっていて、中身の照合を残さない
- [plan] 一覧の I212 F5・F7 を同梱、ほかは残す — F7 は受け入れ条件 3 そのもの、F5 は直す行と同じ行の文言
