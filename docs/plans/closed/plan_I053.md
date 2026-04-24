# plan_I053: Django migration 依存ルールを ultimate_django_coding_standards.md に追記する

## 基本情報
- **計画書ID**: plan_I053
- **関連イシュー**: #108
- **作成根拠資料**: I050 振り返り（予防処置 #1）
- **実装後評価**: （未作成）
- **作成日**: 2026-04-24

---

## 1. 背景/目的

I050 で `problems/0004_subject_organization_alter_subject_name_and_more` が
`accounts/0010_update_organization_structure`（Organization テーブルの DELETE → CREATE 再作成 migration）への依存を欠落させていたことが判明した。

根本原因は「FK を追加する migration の dependencies ルール」が
`rules/ultimate_django_coding_standards.md` に明文化されていなかったことにある。

本イシューでは、この経緯と具体例を同ファイルの Section 4「モデル設計」に
`### マイグレーション` サブセクションとして追記し、同様のミスを将来防ぐ。

---

## 2. 受け入れ条件

- [ ] `rules/ultimate_django_coding_standards.md` に「FK 追加 migration の dependencies ルール（再作成 migration を含める）」が記載されている
- [ ] 記載内容が具体例（I050 の事例）を含み、将来の開発者が意図を理解できる

---

## 3. 影響範囲

- Backend: なし（ドキュメント変更のみ）
- Frontend: なし
- DB: なし
- Config/Infra: E2E テスト設定（`e2e/playwright.config.ts`・`e2e/tests/auth.spec.ts`）

> **追記（fix-loop）**: `/test I053` 実行中にローカル E2E の既存バグが顕在化したため、
> E2E インフラの修正を本イシューのスコープに含める。

---

## 4. 変更点一覧

| ファイル | 変更種別 | 内容 |
|---|---|---|
| `rules/ultimate_django_coding_standards.md` | 追記 | Section 4「モデル設計」末尾（カスタムマネージャー節の直後）に `### マイグレーション` サブセクションを新設 |
| `e2e/playwright.config.ts` | 修正 | `chromium-authed` の `testMatch`（負の先読み regex）を削除し `testIgnore: '**/auth.spec.ts'` に置換。`chromium-unauthed` の `testMatch` を glob に統一 |
| `e2e/tests/auth.spec.ts` | 修正 | 先頭に `test.use({ storageState: { cookies: [], origins: [] } })` を追加し、どのプロジェクトで実行されても未認証状態が保証されるよう二重防御を実装 |

---

## 5. 実装手順

### ステップ 1: `rules/ultimate_django_coding_standards.md` に追記（実装済み）

**対象箇所**: Section 4「モデル設計」の `### カスタムマネージャー` コードブロック終了直後（`---` 区切り線の前）

**追記内容（以下をそのまま挿入）**:

````markdown
### マイグレーション

#### FK 追加 migration の dependencies ルール

FK（外部キー）を追加する migration を作成する際、参照先テーブルが
別の migration で **DELETE → CREATE 再作成** されている場合は、
その再作成 migration を `dependencies` に明示的に含めること。

Django の migration グラフは FK の参照先テーブルが「どの migration で作られたか」
を最初の `CreateModel` から追跡する。テーブルが一度 `DeleteModel` → `CreateModel`
で再作成されると、再作成 migration への依存を手動で追加しない限り、
Django は旧来の `CreateModel` migration（再作成前）を参照先と誤認識する。
これにより FK を追加した migration が再作成 migration より先に実行される可能性があり、
整合性エラーや `django.db.utils.ProgrammingError` を引き起こす。

**ルール**:
> FK を追加する migration を書く際は、参照先テーブルの migration 履歴を確認し、
> 後続の migration で `DeleteModel` → `CreateModel` が行われていれば、
> その migration 番号を `dependencies` に追加すること。

**具体例（I050 の事例）**:

`problems/0004` は `accounts.Organization` に FK を追加する。
`accounts/0010` では Organization テーブルを DELETE → CREATE で再作成している。
この場合、`problems/0004` の `dependencies` に `accounts/0010` を明示しなければ、
FK migration が再作成 migration より前に実行されうる。

```python
# ❌ 悪い例: 再作成 migration が dependencies に含まれていない
class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0009_organization_user_users_organiz_ca9165_idx_and_more'),
        ('problems', '0003_field_problem_field_usersubjectaccess_and_more'),
    ]

# ✅ 良い例: 再作成 migration を明示的に含める
class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0009_organization_user_users_organiz_ca9165_idx_and_more'),
        ('accounts', '0010_update_organization_structure'),  # explicit: ensure table recreated before FK
        ('problems', '0003_field_problem_field_usersubjectaccess_and_more'),
    ]
```

**チェック手順**:
1. `makemigrations` 後、生成された migration の `dependencies` を確認する
2. 参照先アプリの migration 履歴を `git log -- <app>/migrations/` で確認する
3. 参照先テーブルに `DeleteModel` + `CreateModel` のセットが存在する場合、
   その `CreateModel` を含む migration 番号を `dependencies` に追加する
````

---

### ステップ 2: E2E テスト設定の修正（fix-loop 追加）

**背景**: `/test I053` 実行時に既存バグが顕在化。`playwright.config.ts` の `testMatch` 負の先読み regex の部分一致バグにより、`chromium-authed`（認証済み）プロジェクトが `auth.spec.ts` を誤って実行していた。

**修正方針**: 設定レベルの防御（testIgnore glob）＋テストレベルの防御（test.use 自己宣言）の二重防御。

#### 2-1: `e2e/playwright.config.ts`

```ts
// chromium-authed プロジェクト
// Before（負の先読み regex のバグ）:
testMatch: /(?!.*auth\.spec).*\.spec\.ts/,

// After（明示的な除外）:
testIgnore: '**/auth.spec.ts',
// testMatch は省略（デフォルトで全 .spec.ts にマッチ）
```

```ts
// chromium-unauthed プロジェクト
// Before:
testMatch: /auth\.spec\.ts/,

// After（glob に統一）:
testMatch: '**/auth.spec.ts',
```

#### 2-2: `e2e/tests/auth.spec.ts`

```ts
// ファイル先頭の test.describe の前に追加
// 未認証状態を自己宣言。chromium-authed で誤実行されても auth state が混入しない。
test.use({ storageState: { cookies: [], origins: [] } });
```

> **スコープ補足**: この `test.use()` はファイルスコープで全 describe に適用されるが、
> `ログアウトフロー` describe 内の `test.use({ storageState: user_a.json })` が
> Playwright の内側優先ルールにより上書きされるため、ログアウトテストの認証状態には影響しない。

**依存関係**: ステップ 1 と独立して実施可能。

---

## 6. テスト計画

### 自動テスト

- ドキュメント変更（ステップ 1）: 対象なし
- E2E 修正（ステップ 2）: ローカル E2E `docker compose --profile e2e run --rm e2e` で全テスト pass を確認

### 手動テスト

`docs/tests/open/I053_manual_test.md` を参照。

---

## 7. ロールバック

```bash
git revert HEAD
```

- `rules/ultimate_django_coding_standards.md`: revert のみで元に戻る。DB・コード変更なし。
- `e2e/playwright.config.ts` / `e2e/tests/auth.spec.ts`: revert で元の状態に戻る。ただし元の状態はバグあり（`chromium-authed` が auth.spec.ts を誤実行）のため、ロールバックは非推奨。

---

## 8. Risk & 回避策

| リスク | 影響 | 回避策 |
|---|---|---|
| 追記位置が適切でなく将来の追記と重複する | 低（ドキュメントのみ） | Section 4 末尾の固定位置に配置し、migration ルールはここに集約するコメントを残す |
| コード例が実際のファイル名と乖離する | 低 | 実ファイル名ではなく `problems/0004`・`accounts/0010` という省略形で記載し、本文で I050 の事例と明記する |
| `testIgnore` の glob パターンが将来のファイル構成変更で機能しなくなる | 低 | `auth.spec.ts` の `test.use()` 宣言が二重防御になっているため、config 側が崩れても動作する |
| `test.use({ storageState: ... })` が Playwright のバージョンアップで挙動変更 | 低 | Playwright 公式 API であり後方互換性が保たれている。変更時は CHANGELOG で確認する |

---

## 9. 承認ポイント

### セキュリティ影響
**セキュリティ影響なし**（ドキュメント変更のみ）

### P3/P5/P8 影響
**影響なし**（DB変更・外部API・インフラ変更なし）

### P6 影響
**影響なし**（フロントエンド変更・パフォーマンス懸念なし）

### 設計判断の明示

| 設計判断 | 根拠 |
|---|---|
| Section 4「モデル設計」末尾への追記 | イシューに明記済み（/grill-me 確認済み）。co-location 原則・Django 業界標準に準拠 |
| `### マイグレーション` というサブセクション名 | イシューに明記済み |
| 省略形ファイル名（`problems/0004`）を使用 | 実ファイル名が長すぎるため可読性を優先。I050 の事例と本文で明記することで特定可能 |
| ❌/✅ コード例形式 | 既存の standards ファイルの記法（Section 14 等）と一致させる |

### チェックリスト

- [ ] Section 4「カスタムマネージャー」の直後（`---` の前）に正しく挿入されているか
- [ ] ❌ 悪い例・✅ 良い例のコードが正確か（実際の I050 migration と一致するか）
- [ ] 「チェック手順」3 ステップが理解しやすいか
- [ ] Markdown の見出しレベルが既存の `###` スタイルと統一されているか
