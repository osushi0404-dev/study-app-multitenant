# I050 自動テスト計画

## 対象
plan_I050: migration チェーンの型不整合を修正し CI フレッシュ DB で migrate を通す

## 自動テストケース

| No | テスト内容 | 実施方法 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|-----------|---------|---------|--------|--------|------|
| 1 | `python manage.py migrate` が既存ローカル DB で冪等に動作する | `docker compose exec backend python manage.py migrate` | "No migrations to apply" または全 migration が "OK"（exit 0） | Claude | OK | "No migrations to apply" 確認 |
| 2 | `makemigrations --check` が drift なしで通る | `docker compose exec backend python manage.py makemigrations --check` | "No changes detected"（exit 0） | Claude | OK | "No changes detected" 確認 |
| 3 | CI Backend Tests ジョブが pass する | CI push 後に `gh pr checks` で確認 | 全ジョブ ✅ pass | Claude | OK | Backend Tests ✅ 51s（フレッシュ DB migrate 完走確認）|
| 4 | `problems/0004` の dependencies に `accounts/0010` が含まれる | ファイル内容確認 | `dependencies` に `('accounts', '0010_update_organization_structure')` が存在する | Claude | OK | line 11 に存在確認 |

## 再発防止記録
（実施後に追記）
