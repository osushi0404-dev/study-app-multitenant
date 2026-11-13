# I493 レビュー: API のスキーマから画面の型を作る（ダッシュボードの overview から）

## 変更概要
- シリアライザから OpenAPI のスキーマ（`backend/openapi.yaml`）を作り、そこから画面の TS の型（`frontend/src/types/api/schema.d.ts`）を作る仕組みを入れる。作り直し忘れは CI で止める。今回はダッシュボードの overview の手書きの型を置き換える（計画: docs/plans/open/plan_I493.md）

## 変更点
- （実装後に書く）

## 影響範囲
- Backend/Frontend/DB/Config: 計画書「3. 影響範囲」のとおり（DB の変更なし）

## テスト結果
- 自動: （実装後に書く）
- 手動: （test-gate で書く）

## 計画との差分
- （実装後に書く）

## ロールバック
- PR を revert し、backend・celery のイメージを作り直す（`docker compose up -d --build backend celery celery-beat`）。DB の変更なし

## 自律判断の記録
- [plan] 契約に入れる API を一覧（`CONTRACT_PATHS`）で絞り、警告 0 を条件にした — 全 API を入れると警告 61・エラー 136 で、中身の正しくない型ができるため（スパイク 1）
- [plan] 型を作る道具をリポジトリ直下の `tools/api-types/` に置いた — 画面のイメージ（`COPY . .`・`.dockerignore` なし）に入れず、画面の TypeScript 4.9.5 と分けるため
- [plan] 実行時の形の確かめ（`isDashboardOverview`）を残した — 型は実行時に消え、TC-22 の 0 埋めの防止がこれに頼っているため
- [plan-review] 計画レビューの判定は HIGHRISK（`.github` の変更）。Warning 3 件・Info 1 件は計画書と手動テストを直して対応し、再レビューはしない — 方式・範囲・受け入れ条件を変えていないため
- [plan-review] 新しいジョブ `api-types` を必須チェックの一覧に足し、登録は close でユーザーにお願いする — bot に管理者の権限が無いため

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: design-security-review
