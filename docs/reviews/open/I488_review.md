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
- [implement] 書式の共通ファイル（`components/statistics/format.ts`）・件数の共通のシリアライザ・科目のカードの `section`・円グラフを秒で描く・棒の高さを分の小数第 1 位に — どれも計画の範囲の中の作り方の細部で、方式・範囲・受け入れ条件を変えないので再レビューはしない（計画変更記録に記録）
- [implement] `/simplify` の 4 観点の指摘のうち、区切りの 1 回のなめ方・3 つの状態の変換の共通化（`hooks/queryLoadState.ts`・ダッシュボードのフックも使う）・`hasCounts` の使い回しなどを直し、クエリ数がデータで変わる案・差分の外に広がる案は見送った — 見送りの理由は計画変更記録
- [implement] タブの切り替えのテストは `fireEvent.click` にした — `userEvent.click`（v13）では MUI のタブが切り替わらず、TC-24 が前のタブの文言で偶然通る形だったため
- [implement] 画面確認（e2e_user_a・1440）で、統計画面が新しい応答で出て API が 200・新しいエラーが無いことを確かめた（`.evidence/I488/impl-statistics-1440-a*.png`）。細かい確かめは test-gate の手動テストで行う

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
