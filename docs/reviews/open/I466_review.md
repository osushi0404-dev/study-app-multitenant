# I466 レビュー: 間違い分析と苦手を優先した出題を画面につなぐ

## 変更概要
- ダッシュボードの「間違いやすい分野（全科目）」に、難易度別の苦手と急いだ間違いの 1 行を足す
- クイズに 3 つ目のモード `weak`（苦手を優先）を足し、「学習を開始」の副ボタンとおすすめの「練習する」から始める
- 苦手の判定を `backend/problems/services/weakness.py` にまとめ、材料を `QuizAnswer` にそろえる
- 使われない分析（保存型の間違い分析・適応的な問題選択の 2 つの API・その定期処理とキャッシュ）を消す（表は残す）
- 定期処理の間隔を本番の値（`crontab`）にする

## 変更点
- （実装後に書く。計画書 `docs/plans/open/plan_I466.md` の 4 章のとおり）

## 影響範囲
- Backend/Frontend/DB/Config: 計画書 3 章のとおり（DB は `QuizSession.mode` の選択肢の追加だけ）

## テスト結果
- 自動: （CI の結果を書く）
- 手動: （test-gate で書く）

## 計画との差分
- （実装後に書く）

## ロールバック
- PR を revert し、`python manage.py migrate problems 0022` で選択肢を戻す（データの変更なし）

## 自律判断の記録
- [plan] grill-me でユーザーが「BP・UI/UX の観点でベストなやり方で」と任せたので、画面の細部（「難易度別」の小見出しを科目別の一覧の下に置く・急いだ間違いは info の 1 行・「苦手を優先」の印・終えた回の「もう一度挑戦」は同じモード・2 周目も苦手を優先の並べ方）は止めずに決めた — 任された範囲で、既存のカード・印の作りにそろえるのが最も迷わない
- [plan-review] 計画レビュー OK（Warning 3 件）。3 件とも直した（難易度の対応は既存の difficulty.py を使う・4.7 に test_I473 の更新・TC-31 を 3 本に分ける）。再レビューはしない — 方式・範囲・受け入れ条件を変えない

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
