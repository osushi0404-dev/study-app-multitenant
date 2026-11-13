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
- [design-security-review] Medium 2 件（CI の `npm ci` で依存の install スクリプトが動く・失敗の注入の `npx` がネットから取り直しうる）を、`--ignore-scripts` と `./node_modules/.bin/openapi-typescript` で計画に反映し、V6 を足した。計画レビューはやり直さない — 方式・範囲・受け入れ条件を変えていないため
- [implement] 実装のコミットだけ `SKIP=eslint` にした — ワークツリーのホストに eslint が無くフックが exit 127 で止まる既知の問題（#468・I473 と同じ）。同じ `npm run lint`（--max-warnings 0）を frontend のコンテナで流して違反 0 件を確かめた。CI の ESLint は通常どおり流れる
- [implement] /simplify の 4 観点の指摘のうち 4 件を直し、4 件を見送った（理由は計画変更記録）— 直したのは選択肢の一覧の増減の検知・check のパスの 1 か所化・TC-02 の注入の書式依存の除去・スキーマ生成を 1 回に
- [implement] 画面の確かめ（Playwright）は test-gate の手動 No.1 に回した — 画面の動きは変えておらず（型の読み込み先と、選択肢の確かめの書き方だけ）、選択肢の確かめは Dashboard.test.tsx（10 件通過）で見ている
- [implement] backend・celery のイメージを作り直したところ、celery・celery-beat が起動直後に落ちた。原因は今回と無関係（celery の部品 kombu の新しい版が redis-py 6.1 以上を求めるが、`requirements.txt` は `redis==5.0.1` に固定。作業の開始時から celery は動いていなかった）。別イシューとして起票する — 本イシューの範囲外で、本番のイメージでも同じことが起こりうるため → I499（#499）として起票した
- [review-gate] コードレビューは OK（台帳に Low 4 件・止める指摘なし）、敵対的レビューは 1 周目で OK（V1〜V6 すべて確認済み・新しい指摘なし）。Low は retro で扱う — 止める条件に当たらないため

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: design-security-review

STAGE_DONE: design-security-review NEXT: implement

STAGE_DONE: implement NEXT: review-gate

STAGE_DONE: review-gate NEXT: test-gate
