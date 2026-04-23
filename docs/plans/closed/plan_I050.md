# plan_I050: migration チェーンの型不整合を修正し CI フレッシュ DB で migrate を通す

## 基本情報
- **計画書ID**: plan_I050
- **関連イシュー**: #104
- **作成日**: 2026-04-24

---

## 1. 背景/目的

### 原因の概要
`problems/0004`（Subject.organization FK 追加）は `accounts/0009`（Organization UUID pk）にのみ依存しており、
`accounts/0010`（Organization を integer AutoField に作り直し）への依存が欠落している。
Django の migration executor はアルファベット順（`accounts` → `problems`）という暗黙の処理順に頼ることで
たまたま正しく動いているが、これはフレームワーク実装に依存した脆弱な保証である。

### 詳細な原因分析

**I049 実施時に判明した問題の全体像**

| migration | 操作 | 備考 |
|-----------|------|------|
| `accounts/0009` | Organization を **UUID** pk で作成 | 初期定義 |
| `accounts/0010` | Organization を **DELETE → CREATE (AutoField integer)** で作り直し | `accounts/0009` 依存 |
| `problems/0004` | Subject.organization FK を追加 | `accounts/0009` **のみ**依存 ← 問題箇所 |
| `accounts/0021` | `organization_id` → `id` リネーム＋FK 再追加＋UUID→INTEGER 条件変換 | I049 で追加した安全網 |

**フレッシュ DB での依存グラフ（問題のある実行順）**

Django は `accounts/0010` と `problems/0004` の両方が `accounts/0009` に依存することを知っているが、
両者の**相互順序**は定義されていない。アルファベット順の処理で `accounts/0010` が先に走るため
現在の CI では問題が出ていないが、これは暗黙の保証である。

もし `problems/0004` が `accounts/0010` より先に実行された場合：
1. `problems/0004`: Organization は UUID pk → `problems_subject.organization_id` が **UUID** 型で作成される
2. `accounts/0010`: Organization を `DROP TABLE ... CASCADE`（FK 制約を自動削除）→ AutoField で再作成
3. `problems_subject.organization_id` は UUID 型のまま残る
4. `accounts/0021`: FK 再追加時に `uuid` vs `integer` の型不一致 → `ProgrammingError`

**I049 で導入した安全網（`accounts/0021` の条件付き型変換）**

```sql
DO $$
BEGIN
  IF (data_type of problems_subject.organization_id) = 'uuid' THEN
    ALTER TABLE problems_subject ALTER COLUMN organization_id TYPE INTEGER USING NULL;
  END IF;
END $$;
```

これにより「どちらの実行順でも CI が通る」ようになった。しかし根本原因（明示的な依存欠落）は未修正。

### 根本原因
`problems/0004` の `dependencies` リストに `accounts/0010` が含まれていないため、
migration executor が実行順序を保証できない。

---

## 2. 受け入れ条件

- [ ] フレッシュ DB（`postgres_data` volume なし）で `python manage.py migrate` がエラーなく完走する
- [ ] 既存ローカル DB（migration 適用済み）で `python manage.py migrate` を実行しても追加変更なく正常終了する
- [ ] CI（`ci.yml` Backend Tests ジョブ）が pass する

---

## 3. 影響範囲

- Backend: `backend/problems/migrations/0004_subject_organization_alter_subject_name_and_more.py`（`dependencies` 追加のみ）
- Frontend: なし
- DB: スキーマ変更なし。`dependencies` の変更は migration の実行順序メタデータのみを変える
- Config/Infra: なし

---

## 4. 変更点一覧

| ファイル | 変更内容 |
|---------|---------|
| `backend/problems/migrations/0004_subject_organization_alter_subject_name_and_more.py` | `dependencies` に `('accounts', '0010_update_organization_structure')` を追加 |

---

## 5. 実装手順

### ステップ 1: `problems/0004` の dependencies を修正

`backend/problems/migrations/0004_subject_organization_alter_subject_name_and_more.py` の
`dependencies` リストに `('accounts', '0010_update_organization_structure')` を追加する。

**変更前:**
```python
dependencies = [
    ('accounts', '0009_organization_user_users_organiz_ca9165_idx_and_more'),
    ('problems', '0003_field_problem_field_usersubjectaccess_and_more'),
]
```

**変更後:**
```python
dependencies = [
    ('accounts', '0009_organization_user_users_organiz_ca9165_idx_and_more'),
    ('accounts', '0010_update_organization_structure'),
    ('problems', '0003_field_problem_field_usersubjectaccess_and_more'),
]
```

**この変更の安全性について:**
- Django は migration を `(app, name)` のペアで管理する。`dependencies` リストは実行順序の制約のみを表す。
- 変更後に既存 DB（migration 適用済み）で `migrate` を実行しても "already applied" と判断され、
  SQL は一切実行されない。
- 生成される SQL も変化しない（依存関係メタデータのみの変更）。

### ステップ 2: migration drift チェック

```bash
docker compose exec backend python manage.py makemigrations --check
```

"No changes detected" が返ることを確認する（dependencies の変更はモデル定義の変更ではないため）。

### ステップ 3: 既存ローカル DB での冪等性確認

```bash
docker compose exec backend python manage.py migrate
```

"No migrations to apply" または全 migration が "OK" と表示されることを確認する。

### ステップ 4: フレッシュ DB での動作確認（CI push でトリガー）

ローカルでのフレッシュ DB 確認は volume の作り直しが必要なため、CI push で代替する。
push 後に `ci.yml` の Backend Tests ジョブが pass することで確認とする。

---

## 6. テスト計画

### 自動テスト
- CI `ci.yml` の Backend Tests ジョブで `python manage.py migrate` がフレッシュ DB で完走することを確認
- Backend pytest が引き続き全件 pass することを確認

### 手動テスト
- なし（変更は migration metadata のみ。UI/API の振る舞いに変化なし）

---

## 7. ロールバック

1. `problems/0004` の `dependencies` から `('accounts', '0010_update_organization_structure')` を削除して revert
2. push して CI を再実行
3. DB 側の変更はないため、DB 操作は不要

---

## 8. Risk & 回避策

| リスク | 影響 | 回避策 |
|--------|------|--------|
| フォーク環境で `accounts/0010` より後に `problems/0004` を適用済みの状態がある | なし（`dependencies` 変更は適用済み migration に影響しない） | 既存 DB は対象外 |
| `accounts/0021` の条件付き UUID→INTEGER 変換が不要になる | なし（no-op として残るが害はない） | 将来の squash 時に整理できる |
| CI pipeline の順序変更により意図しない実行順が生じる | 軽微 | 本 PR の修正でその可能性を排除する |

---

## 9. 承認ポイント

以下の設計判断についてご確認ください。

**イシューに明記されている項目:**
- [x] `problems/0004` の依存関係を修正して暗黙依存を排除する（grill-me で確認済み）
- [x] モデル定義は変更しない（`Organization.id` は `AutoField` のまま）
- [x] migration squash は今回のスコープ外

**仮定で決めた設計判断:**
- [仮定] `accounts/0021` の条件付き変換ロジックはそのまま残す（no-op として許容）
  → 削除すると `accounts/0021` が軽量になるが、squash 時の作業として分離する方が安全
- [仮定] ローカルフレッシュ DB テストは CI push で代替とする
  → ローカルで volume 削除するとシード済みデータが消えるため、CI 確認が妥当

**セキュリティ影響:**
- なし。`dependencies` の変更は migration メタデータのみであり、認証・認可・データアクセス制御に変化なし。

**P3/P5/P8 影響:**
- P3（データ整合性）: スキーマ変更なし。migration の実行順序保証のみ。
- P5（運用性）: なし。
- P8（コスト・保守負荷）: migration 依存グラフが明示的になることで将来の squash 等が容易になる。

**P6 影響:** なし（フロントエンド変更・大量データ・外部API連携なし）
