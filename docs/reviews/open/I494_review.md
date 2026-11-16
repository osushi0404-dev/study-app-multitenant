# I494 レビュー: 学ぶ科目を後から選び直せるようにする

## 変更概要
- 設定画面に「学ぶ科目」のカードを足し、利用者が会員登録の後でも自分の組織の科目から学ぶ科目を選び直せるようにする（`PUT /api/user/subjects/`・`GET /api/user/subjects/available/`）
- ダッシュボードの科目 0 件の案内を、組織に科目があればこのカードへの導線にする

## 変更点
- （実装後に記入）

## 影響範囲
- Backend/Frontend/DB/Config: 計画書 3 章のとおり（DB・Config の変更なし）

## テスト結果
- 自動: （CI の結果を記入）
- 手動: （test-gate で記入）

## 計画との差分
- なし

## ロールバック
- PR を revert する（マイグレーション・依存の変更なし）

## 自律判断の記録
- [plan] 書き換えの API を「選んだ一覧を丸ごと置き換える PUT」にした — 画面がチェックの全体を送る形と合い、冪等で単純
- [plan] 組織の科目の一覧は新しい `GET /api/user/subjects/available/` にした — 既存の `/api/subjects/` はページ分け 20 件・問題数の集計つきで選ぶ画面に合わない
- [plan] 新しい 2 つの経路を API の契約（I493）に入れた — 画面の型を手書きしない
- [plan] キャッシュは確定の後（on_commit）に消す — シグナルはトランザクションの中で消すので、確定の前に古い値が入り直す隙がある
- [plan] 文言とカードの中の細かい並びは設計確認メモの決定から導いた（新しい価値判断は無いので止めない）

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
