# I180 手動テスト: Pillow を 13.0.0 に更新（既知脆弱性 8 件の解消）

- 関連: docs/issues/open/I180.md / docs/plans/open/plan_I180.md / Draft PR #303
- 実行環境: wt-harness の Docker（このワークツリーのディレクトリで `docker compose ...`）。ステップ 1 の再ビルド（TC-AUTO-00）の後に実施する
- 範囲: 自動テストではカバーされない「再ビルドしたイメージでの起動」を確かめる。アップロードの流れ（multipart → 検証 → 保存）は既存の結合テスト（`test_I073_image_update.py`・TC-AUTO-06）が実際の Pillow とファイル保存で確かめている
- **Human の手順は置かない**: 画面・フロントエンドの変更が無く、下の確認はすべてコマンドの出力で観測できるため（計画書 §7「手動テストの範囲」）

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `docker compose exec -T backend curl -sS -i http://localhost:8000/health/` | 1 行目が `HTTP/1.1 200 OK`、本文が `{"status": "ok"}`（再ビルド後の runserver が起動し、`problems.utils` の `from PIL import Image` を含むアプリの読み込みに成功している） | Claude | OK | 2026-10-21 実施（13.0.0）: `HTTP/1.1 200 OK` / `{"status": "ok"}`。実装前（12.3.0）も同じ |
| 2 | `docker compose logs --no-color celery` | `celery@<コンテナID> ready.` の行がある。`ImportError` / `ModuleNotFoundError` の行が無い。`Traceback` があれば、すべて既知の `Received unregistered task of type 'core.tasks.cache_maintenance_task'` に付くものである | Claude | OK | 2026-10-21 実施: `celery@7c6cc45876af ready.` あり。`ImportError` / `ModuleNotFoundError` / `Traceback` は 0 件（観測窓 10:03:49〜10:07:20 では既知の未登録タスクも未着）。`update_daily_analytics_task` / `send_study_reminders_task` が `succeeded`。既知の既存不具合（I151 計画書 §2-8・beat が 30 分ごとに送る未登録タスク）は主作業側の稼働中 worker で出ている（2026-10-21 確認）。本イシューの対象外 |
| 3 | `docker compose logs --no-color celery-beat` | `beat: Starting...` の行がある。`ImportError` / `ModuleNotFoundError` / `Traceback` の行が無い | Claude | OK | 2026-10-21 実施: `beat: Starting...` あり・エラー行 0 件。`Scheduler: Sending due task` が継続 |
| 4 | `docker compose exec -T backend python -c "import PIL.features as f; print(f.check('webp'), f.check('jpg'), f.check('zlib'))"` | `True True True`（受理形式 WebP・JPEG・PNG の処理系が 13.0.0 のイメージに入っている） | Claude | OK | 2026-10-21 実施: `True True True`。新規テスト（TC-AUTO-04）の前提の確認 |
| 5 | 計画書 §2-3（8 件の CVE が影響する処理）と §2-4（非互換変更の該当有無）を Read で確認する | §2-3 に 8 件すべての CVE ID と影響する処理・到達性がある。§2-4 にリリースノートの非互換変更・非推奨の全 10 項目と、本リポジトリの利用箇所との突き合わせ結果（該当 0 件）がある | Claude | OK | 2026-10-21 確認: §2-3 は 8 行（CVE-2026-112895 / 112400 / 112397 / 112896 / 112897 / 112395 / 112404 / 112899）、§2-4 は 10 行・該当 0 件。AC-7 |

結論: OK（全 5 項目。Human の手順なし）
