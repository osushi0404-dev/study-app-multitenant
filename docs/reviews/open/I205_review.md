# I205 レビュー: レビューで止める基準を変更の種類で分ける・差分の中かどうかを行で決める

- 計画書: docs/plans/open/plan_I205.md
- イシュー: docs/issues/open/I205.md（#341）
- Draft PR: #342

## 変更概要
（implement 段階で記入）

## 変更点
（implement 段階で記入）

## 影響範囲
ハーネスだけ（`scripts/claude/code-review.sh`・`.claude/agents/code-reviewer.md`・`.claude/skills/review-gate/`・`.claude/skills/fix-loop/`・`.claude/skills/retro/`・`docs/runbooks/review-rules.md`・`scripts/claude/tests/`）。アプリ本体・DB・GitHub の設定は変えない。

## テスト結果
（test-gate 段階で記入）

## 計画との差分
（implement 段階以降で記入）

## ロールバック
PR を revert する。レビューの途中のイシューがあれば、新しい形で書かれたコードレビューの記録の名前を変えて退避する（計画書 7）。

## 自律判断の記録
- [plan] F11・F16（I202）は I205 で直す — 範囲・判定の決め方そのもので、ここで変えないと I205 の判定に既知の抜け道が残るため
- [plan] ハーネスは重大度を見ずに、止める条件の一覧と再現で決める。guard は再現を問わず今の強さのまま — ラベルを下げて関所を通す抜け道を閉じるため／GitHub から戻せない変更を緩める理由が無いため
- [plan] ハーネスの場所の一覧に無いものはアプリ本体（厳しい側）。FILE=- の種類はブランチが変えたファイルから guard＞app＞harness — 知らない場所で甘くならないため
- [plan] 前後の行数は 3 — git の既定の前後の行数と同じで、レビュー役が見る差分の見た目と合うため
