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

STAGE_DONE: plan NEXT: plan-review
