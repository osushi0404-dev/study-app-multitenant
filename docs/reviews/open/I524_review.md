# I524 レビュー: ダッシュボードの確かめ用データを各科目・各曜日 10 問以上にし、開発の起動のたびに作り直す

## 変更概要
- 確かめ用データ（`seed_dashboard_verify`）の直近 7 日を、解答の無い 1 日を除いて全科目 10〜20 問（同じ日・科目は違う問題・科目ごとに日ごとの数がすべて違う）にする
- 開発の環境の起動のたびに、compose の一度きりのサービス `dashboard-verify-seed` が作り直す（`--soft-stop`）
- #508 から移した F5・F6・F9・F10 を直す

## 変更点
- `backend/dashboard/verify_data.py`: `PROBLEMS_PER_SUBJECT = 20`・`RECENT_COUNT_RANGE`・`OUTSIDE_COUNT_RANGE` を足した。量と境目を `_day_groups` で先に決め（解答の無い日 1 日・直近 6 日は全科目・科目ごとに `rng.sample` で重ならない 10〜20 問）、`plan_answers` は正誤・時間・時刻だけを乱数で足す。F6（過去の日の `span` を `DAYTIME_HOURS * 3600` にし docstring を「開始以上・終わり未満」に）・F9（`VerifyDataError` の docstring）
- `backend/dashboard/management/commands/seed_dashboard_verify.py`: `--soft-stop`（`VerifyDataError` のときだけ `確かめ用のデータは作りませんでした: <理由>` を出して正常に終わる）
- `docker-compose.yml`: 一度きりのサービス `dashboard-verify-seed`（backend が healthy の後・`e2e/.env.e2e` を読む・`--soft-stop`）
- `backend/dashboard/tests/test_I524_dashboard_verify_volume.py`（新規）: TC-01〜TC-07。`test_I513_seed_dashboard_verify.py`: TC-49 を `Counter` で比べる（F5）
- `docs/runbooks/frontend-verify.md`: §11 を新しい作り（量・起動のたびの作り直し・ログの読み方・`--wait` の注意）に。§12 の 1 語（一覧 I468 F5 の同梱）。`docs/reviews/backlog/I468.md` から F5 の行を消した

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
- [plan-review] Warning 2 件は手動 No.2 の備考の追記と実装時の確認で対応し、再レビューはしない — 方式・範囲・受け入れ条件を変えないため
- [implement] 量の組み立てを `_day_groups` という小さな関数に分けた — 計画 4-1 が許した形。境目と量を先に決める順が関数の境で読める
- [implement] 手順書 §11 に「ログは起動のたびに後ろへ足されるので最後の `種:` から下が今のデータ・起動の数秒後に出る」を足した — 2 回目の起動の直後にログを読んだら 1 回目の分しか出ておらず、時刻つきで読み直して分かったため（計画 4-5 の「出力の読み方」の範囲）
- [implement] `/simplify`（4 観点）の指摘のうち、`_day_groups` の直近の日を科目ごとの `zip` にする・TC-01 の日ごとの合計を `Counter` 1 行にする、の 2 件を直した — 振る舞いを変えない簡潔化
- [implement] `/simplify` の残りは見送った: (1) `--soft-stop` がほかの組織の同じメール（異常）まで正常終了にする → 計画 4-2・9 が「`VerifyDataError` を正常終了」と決めており、変えると振る舞いが変わる。起動を止めないことはどちらでも同じで、案内はログに出る (2) TC-07 の準備が I513 の `_other_user` と重なる → 共通のヘルパーのファイルを足すのは計画の範囲の外で、10 行ほど (3) compose の backend の設定の 5 つ目の写し・共通のイメージ名 → ファイルに YAML のアンカーが無く、`e2e-init` と同じ書き方。範囲の外 (4) 問題の `get_or_create` を 40 回・セッションを 1 件ずつ作る → 起動 1 回に数十ミリ秒で、効き目が無い (5) テストの数（10〜20 など）を定数から読まない → 決まりをコードと別に固定する意図
- [implement] 画面の下見（計画の手順 5）: 2 回目の起動（種 544354802）の後、`/dashboard`「すべて」の棒の読み上げと合計の行がログと一字一句同じ（11/11 だけ 0 問・ほかは 25〜36 問）。正式な記録は test-gate

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: implement

STAGE_DONE: implement NEXT: review-gate

STAGE_DONE: review-gate NEXT: test-gate
