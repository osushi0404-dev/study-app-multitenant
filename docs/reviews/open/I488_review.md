# I488 レビュー: 学習統計の画面をクイズの記録から出す

## 変更概要
- 学習統計（`GET /api/dashboard/analytics/`・`/statistics`）の数字を、クイズの答えの記録（`QuizAnswer`）から出す。#473 の集計（`backend/dashboard/selectors.py`）を使い回し、応答の形をシリアライザと OpenAPI の型で固定する
- 期間（7・30・90・365 日）と区切り（日・週・月）・科目の絞り込み・科目別の内訳・状態ごとの表示。書き出しのボタンと「間違いパターン」のタブを外す

## 変更点
- （実装後に書く。計画書 4.3 のとおり）

## 影響範囲
- Backend/Frontend/DB/Config: Backend `backend/dashboard/`・`backend/core/openapi.py`・`backend/core/settings.py`（OpenAPI の選択肢の名前）・境界テスト 3 本／Frontend `Statistics.tsx`・`components/statistics/`・`hooks/useStatistics.ts`・`dashboard.service.ts`・`types.ts`・`types/api/`／DB なし／Config なし

## テスト結果
- 自動: （実装後に書く）
- 手動: （test-gate で書く）

## 計画との差分
- （実装後に書く）

## ロールバック
- PR を revert する（DB・設定の値の変更なし）

## 自律判断の記録
- [plan] 区切り（31 日以下は日・180 日以下は週・それ以上は月）・週は月曜始まり・端の区切りは期間で切る — 設計確認メモで「計画で決める」とされた点。ISO 週と同じで、期間の合計とグラフの合計を一致させるため
- [plan] 科目別の内訳は科目の選択に関係なく全科目（「科目別（全科目）」）— 1 科目だけの円グラフは意味が無く、ダッシュボードの「（全科目）」の見せ方にそろえる
- [plan] グラフの道具は `recharts` のまま（`chart.js` への統一と依存の削除は retro で別イシューにするか決める）— 本イシューの目的と関係しない差分を増やさない
- [plan] E2E を足さない — 画面と API の形のずれは、契約のテスト・OpenAPI から作る型・形の確かめで止め、実際の流れは手動テスト No.5 で確かめる
- [plan-review] 計画レビューの Warning 2・Info 2 を直し、再レビューはしない — 方式・範囲・受け入れ条件を変えない記述の具体化だけ（計画変更記録に記録）

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
