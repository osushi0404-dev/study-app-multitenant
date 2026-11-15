# I524 レビュー: ダッシュボードの確かめ用データを各科目・各曜日 10 問以上にし、開発の起動のたびに作り直す

## 変更概要
- 確かめ用データ（`seed_dashboard_verify`）の直近 7 日を、解答の無い 1 日を除いて全科目 10〜20 問（同じ日・科目は違う問題・科目ごとに日ごとの数がすべて違う）にする
- 開発の環境の起動のたびに、compose の一度きりのサービス `dashboard-verify-seed` が作り直す（`--soft-stop`）
- #508 から移した F5・F6・F9・F10 を直す

## 変更点
- （実装後に書く）

## 影響範囲
- Backend/Frontend/DB/Config: Backend は確かめ用データの中身と管理コマンドだけ。Frontend なし。DB はスキーマの変更なし。Config は `docker-compose.yml` に一度きりのサービスを足す

## テスト結果
- 自動:
- 手動:

## 計画との差分
- なし

## ロールバック
- PR を revert する（7 章）

## 自律判断の記録

STAGE_DONE: plan NEXT: plan-review
