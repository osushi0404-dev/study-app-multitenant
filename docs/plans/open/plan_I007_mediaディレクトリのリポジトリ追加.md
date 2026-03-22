# I007 計画書: backend/media をリポジトリに含める

## 基本情報
- **計画書ID**: plan_I007_mediaディレクトリのリポジトリ追加
- **関連イシュー**: #007 (GitHub #19)
- **作成根拠資料**: docs/issues/open/007.md
- **実装後評価**: （未作成）
- **作成日**: 2026-03-23

---

## 1. 背景/目的
- `backend/media/` は `.gitignore` により除外されており、開発環境間でメディアファイルが共有されない
- `git clone` 後に画像が存在しないため、DBに保存されたファイルパスの参照が 404 になる
- `backend/media/` をリポジトリに含め、`git clone` だけで画像参照まで動作する状態にする

## 2. 調査結果

### 現状
- `.gitignore` に以下の3エントリが存在し、`backend/media/` は二重に除外されている
  - 17行目: `media/`（任意パスの `media/` ディレクトリ全体を除外）
  - 20行目: `backend/media/`（明示的な除外）
  - 43行目: `backend_media/`（別ディレクトリ・今回は無関係）
- `backend/media/` には以下のファイルが存在する
  ```
  backend/media/bk/problems/aws-saa/questions/q02_problem.png
  backend/media/org/company_osushi_is_funny/subjects/business-english/problem/013f643f-....png
  backend/media/org/company_osushi_is_funny/subjects/data-science/problem/013f643f-....png
  backend/media/org/company_osushi_is_funny/subjects/financial-planning/problem/013f643f-....png
  backend/media/org/cute_school/subjects/high-school-english/problem/013f643f-....png
  backend/media/org/personal/subjects/aws-saa/problem/q02_problem.png
  ```
- Django 設定（`backend/core/settings.py`）:
  ```python
  MEDIA_URL = '/media/'
  MEDIA_ROOT = BASE_DIR / 'media'   # → backend/media/ と一致
  ```
- 開発環境での配信（`backend/core/urls.py`）:
  ```python
  if settings.DEBUG:
      urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
  ```
  → `DEBUG=True` であれば `/media/<path>` で画像配信される設定は既に正しい

### 問題の本質
git が `backend/media/` を無視しているため `git clone` 後に画像が存在しない。
Django の配信設定は正常であり、ファイルさえ存在すれば参照は機能する。

---

## 3. 受け入れ条件
- [ ] `.gitignore` から `backend/media/` が除外されなくなっている
- [ ] `backend/media/` 以下の全ファイルが git 管理下に入っている
- [ ] `git clone` 後に `backend/media/` が存在する
- [ ] Django の `MEDIA_URL` / `MEDIA_ROOT` 設定でファイルが正しく配信される
- [ ] フロントエンドから画像 URL にアクセスして 200 が返る
- [ ] DB に保存されているファイルパスと実際のファイルが一致している

## 4. 影響範囲
- Backend: `.gitignore` 変更のみ
- Frontend: なし
- DB: なし
- Config/Infra: なし

## 5. 変更点一覧

| ファイル | 変更内容 |
|----------|---------|
| `.gitignore` | 17行目の `media/` の直後に `!backend/media/` を追加、20行目の `backend/media/` を削除 |
| `backend/media/**` | git 管理下に追加（コミット） |

### `.gitignore` の修正方針
`media/` の汎用除外は残しつつ、`backend/media/` だけを否定パターンで再包含する。
git の否定ルール「後の行が優先、かつ親ディレクトリが除外されていなければ再包含可能」を利用する。

```diff
 # Media files
 media/
+!backend/media/
-backend/media/
```

これにより `backend/media/` のみ追跡対象となり、他の `media/` ディレクトリは引き続き除外される。

## 6. 実装手順

1. `.gitignore` を修正
   - `media/` の直後の行に `!backend/media/` を追加
   - `backend/media/` の行を削除

2. `backend/media/` 以下のファイルを `git add`

3. コミット・プッシュ

4. 動作確認（詳細は手動テスト文書参照）

## 7. テスト計画
- 自動: docs/tests/open/I007_auto_test.md 参照
- 手動: docs/tests/open/I007_manual_test.md 参照

## 8. ロールバック
- `.gitignore` を元に戻し（`!backend/media/` 削除・`backend/media/` 再追加）、`git rm -r --cached backend/media/` でキャッシュから除外すれば完全に戻せる
- ファイル自体はローカルに残るため、データ損失リスクなし

## 9. Risk & 回避策
| リスク | 回避策 |
|--------|--------|
| 今後ユーザーがアップロードしたファイルが誤ってコミットされる | 現状のワークフロー上は CLI 操作でのみ commit するため、意図せずコミットされるリスクは低い。必要に応じて `.gitignore` に新しいアップロードパスを追加する |
| `media/` の否定パターンが他環境で意図しない動作をする | 否定パターンのルールは git の標準仕様であり、動作は安定している |

## 10. 承認ポイント
- [ ] 変更内容（`.gitignore` 修正アプローチ）
- [ ] Danger Ops（無）
- [ ] テスト計画
