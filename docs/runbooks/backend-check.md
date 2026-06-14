# バックエンドチェック必須ルール

## データベース・モデル整合性チェック必須ルール

### エラー対応・ロジック修正時の自動診断手順
モデル関連のエラーが発生した場合や、ロジック修正を依頼された場合は、**必ず以下の順序で診断・修正を実行**すること：

#### 1. 基本整合性診断（必須実行）
```bash
# 未適用マイグレーション確認
python manage.py showmigrations

# モデル定義チェック
python manage.py check --database default

# 未適用マイグレーション検出
python manage.py makemigrations --check --dry-run
```

#### 2. テーブル・モデル対応チェック（必須実行）
```python
# Djangoシェルで以下を実行
from django.apps import apps
from django.db import connection

# 対象モデルのフィールド一覧取得
model = apps.get_model('app_name', 'ModelName')
model_fields = [f.name for f in model._meta.get_fields() if hasattr(f, 'column')]
print(f"モデルフィールド: {model_fields}")

# データベースの実際のカラム一覧取得
table_name = model._meta.db_table
with connection.cursor() as cursor:
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = %s", [table_name])
    db_columns = [row[0] for row in cursor.fetchall()]
print(f"DBカラム: {db_columns}")

# 不一致チェック
missing_in_model = set(db_columns) - set([f.column for f in model._meta.get_fields() if hasattr(f, 'column')])
missing_in_db = set([f.column for f in model._meta.get_fields() if hasattr(f, 'column')]) - set(db_columns)
if missing_in_model or missing_in_db:
    print(f"⚠️  不一致検出!")
    print(f"DBにあるがモデルにない: {missing_in_model}")
    print(f"モデルにあるがDBにない: {missing_in_db}")
```

#### 3. 修正優先順位の判定ルール
不一致が検出された場合の対応優先順位：

**A. DBにあるがモデルにないフィールド（高優先度）**
→ モデル定義にフィールド追加が必要
→ マイグレーション漏れの可能性

**B. モデルにあるがDBにないフィールド（中優先度）**
→ マイグレーション実行が必要
→ `python manage.py migrate`を実行

**C. 型の不一致（低優先度）**
→ マイグレーションでの型変更が必要

#### 4. 自動修正フロー
不一致検出時の標準対応手順：

1. **マイグレーション状態確認**
```bash
python manage.py showmigrations app_name | grep "\[ \]"
```
未適用があれば `python manage.py migrate` を実行

2. **モデル定義修正**
不足フィールドをマイグレーション定義を参考に追加：
```python
# マイグレーションファイルから正しい定義をコピー
# 例: 0004_subject_organization.py の内容を参考にモデルを修正
```

3. **動作確認**
```python
# 修正後の動作確認（必須）
from app.models import Model
instance = Model.objects.first()
print(instance.field_name)  # エラーが発生しないことを確認
```

#### 5. 修正完了の検証ルール（セルフチェック）
修正後は**必ず**以下をすべて実行して問題ないことを確認：

**A. モデルアクセス確認**
```python
model_instance = Model.objects.first()
for field in model._meta.get_fields():
    if hasattr(field, 'name') and hasattr(model_instance, field.name):
        value = getattr(model_instance, field.name)
        print(f"{field.name}: {value}")
```

**B. ORM操作確認**
```python
# フィルタリング動作確認
queryset = Model.objects.filter(**{修正したフィールド名: テスト値})
print(f"フィルタリング結果: {queryset.count()}件")

# 関連操作確認（ForeignKeyの場合）
if hasattr(model_instance, '修正したフィールド名'):
    related_obj = getattr(model_instance, '修正したフィールド名')
    print(f"関連オブジェクト: {related_obj}")
```

**C. API動作確認**
関連するAPIエンドポイントを実行してエラーが発生しないことを確認

**D. ログ確認**
```bash
tail -f backend/logs/django.log
# エラーログが出力されていないことを確認
```

#### 6. 報告ルール
修正完了時は以下を必ず報告：

1. **検出された不一致の詳細**
2. **実施した修正内容**
3. **修正前後の動作確認結果**
4. **関連する他の箇所への影響確認結果**
5. **再発防止のための提案**（該当する場合）

### 対象となるエラーパターン
以下のエラーが発生した場合は、上記の診断ルールを**必ず**適用：

- `Cannot resolve keyword 'field_name' into field`
- `AttributeError: 'Model' object has no attribute 'field_name'`
- `django.db.utils.OperationalError: no such column`
- `django.core.exceptions.FieldError`
- マイグレーション関連エラー全般

### 例外ルール
以下の場合はこのルールを適用せず、個別対応：
- 新規プロジェクト作成時
- テスト環境のセットアップ時
- システムモデル（auth, contenttypes等）の問題
- サードパーティライブラリ由来の問題

---

## バックエンド修正時のAPI統合テスト必須ルール

> **注記（実行主体）**: 以下の `curl` を用いた API 直叩き手順は、`.claude/settings.json` で `Bash(curl *)` が deny されているため **Claude Code は実行できない**。ユーザーが手動で実行するか、CI／pytest の API テストで代替すること。Claude が自動検証する場合は `docker compose exec backend python manage.py test`（または pytest）の API テストを用いる。

### バックエンドロジック修正後の自動検証手順
バックエンドの修正（モデル、ビュー、サービス等）を行った場合は、**必ず以下の順序でAPI統合テストを実行**すること：

#### 1. 関連API特定（必須実行）
修正したロジックに関連するAPIエンドポイントを特定：
```bash
# 修正対象がSubjectServiceの場合の例
grep -r "subject_service\|SubjectService" backend/ --include="*.py" | grep -E "(views\.py|serializers\.py)"
# → 使用箇所からAPIエンドポイントを特定
```

#### 2. 認証トークン取得（必須実行）
```bash
# テスト用ユーザーでログインしてトークン取得
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com", "password":"testpass"}'

# レスポンスからtokenを抽出して環境変数に設定
export TOKEN="取得したトークン"
```

#### 3. 影響を受けるAPI全てをテスト（必須実行）

**A. ダッシュボード関連API**
```bash
echo "=== ダッシュボードAPI テスト ==="
curl -X GET http://localhost:8000/api/dashboard/overview/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq '.'

curl -X GET http://localhost:8000/api/dashboard/analytics/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq '.'
```

**B. 学習統計関連API**
```bash
echo "=== 学習統計API テスト ==="
curl -X GET http://localhost:8000/api/studylogs/statistics/overview/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq '.'

curl -X GET http://localhost:8000/api/studylogs/statistics/by_subject/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq '.'
```

**C. 科目関連API**
```bash
echo "=== 科目API テスト ==="
curl -X GET http://localhost:8000/api/problems/subjects/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" | jq '.'
```

#### 4. フロントエンド期待レスポンス形式の検証（必須実行）

**A. フロントエンドの期待形式を調査**
```bash
# React コンポーネントから期待するレスポンス形式を確認
grep -r "api.*dashboard\|api.*statistics\|api.*subjects" frontend/src/ --include="*.ts" --include="*.tsx" -A 5 -B 5
```

**B. レスポンス構造の詳細検証**
```bash
# 各APIのレスポンス構造を詳細確認
echo "=== ダッシュボード overview レスポンス構造 ==="
curl -s -X GET http://localhost:8000/api/dashboard/overview/ \
  -H "Authorization: Bearer $TOKEN" | jq 'keys'

echo "=== 学習統計 overview レスポンス構造 ==="
curl -s -X GET http://localhost:8000/api/studylogs/statistics/overview/ \
  -H "Authorization: Bearer $TOKEN" | jq 'keys'

echo "=== 科目一覧 レスポンス構造 ==="
curl -s -X GET http://localhost:8000/api/problems/subjects/ \
  -H "Authorization: Bearer $TOKEN" | jq '.[0] | keys' 2>/dev/null || echo "配列が空または形式が異なる"
```

#### 5. レスポンス内容の妥当性検証（必須実行）

**A. 科目データの整合性確認**
```bash
echo "=== 科目データ確認 ==="
SUBJECTS=$(curl -s -X GET http://localhost:8000/api/problems/subjects/ -H "Authorization: Bearer $TOKEN")
echo "$SUBJECTS" | jq '.[].name'
SUBJECT_COUNT=$(echo "$SUBJECTS" | jq 'length')
echo "取得した科目数: $SUBJECT_COUNT"
```

**B. ダッシュボードの科目データ確認**
```bash
echo "=== ダッシュボード科目データ確認 ==="
DASHBOARD=$(curl -s -X GET http://localhost:8000/api/dashboard/overview/ -H "Authorization: Bearer $TOKEN")
echo "$DASHBOARD" | jq '.subject_progress[]?.subject' 2>/dev/null || echo "科目進捗データなし"
```

**C. 統計画面の科目データ確認**
```bash
echo "=== 統計科目データ確認 ==="
STATS=$(curl -s -X GET http://localhost:8000/api/studylogs/statistics/by_subject/ -H "Authorization: Bearer $TOKEN")
echo "$STATS" | jq '.[].subject_name' 2>/dev/null || echo "統計データなし"
```

#### 6. エラー処理の確認（必須実行）

**A. 不正なリクエストでのエラーレスポンス確認**
```bash
echo "=== エラーハンドリング確認 ==="
# 認証なしでのアクセス
curl -X GET http://localhost:8000/api/dashboard/overview/ \
  -H "Content-Type: application/json" -w "%{http_code}\n" -o /dev/null

# 無効なトークンでのアクセス
curl -X GET http://localhost:8000/api/dashboard/overview/ \
  -H "Authorization: Bearer invalid_token" \
  -H "Content-Type: application/json" -w "%{http_code}\n" -o /dev/null
```

#### 7. パフォーマンス確認（推奨実行）
```bash
echo "=== パフォーマンス確認 ==="
time curl -s -X GET http://localhost:8000/api/dashboard/overview/ \
  -H "Authorization: Bearer $TOKEN" > /dev/null

for i in {1..3}; do
  echo "実行 $i 回目:"
  time curl -s -X GET http://localhost:8000/api/dashboard/overview/ \
    -H "Authorization: Bearer $TOKEN" > /dev/null
done
```

#### 8. ログ確認（必須実行）
```bash
echo "=== ログ確認 ==="
tail -n 50 backend/logs/django.log | grep -E "(ERROR|CRITICAL|Exception)" || echo "エラーログなし"
tail -n 10 backend/logs/django.log | grep -E "(GET|POST).*200"
```

### テスト完了の判定基準
以下を**すべて**満たすことを確認：

✅ **HTTPステータス**: 全APIで200レスポンス取得
✅ **レスポンス形式**: JSONが正しく構造化されている
✅ **データ整合性**: 組織/会員ごとの適切なデータフィルタリング
✅ **必須フィールド**: フロントエンドが期待するフィールドが存在
✅ **エラーハンドリング**: 不正リクエストで適切なエラーレスポンス
✅ **パフォーマンス**: レスポンス時間が許容範囲内（通常2秒以内）
✅ **ログ確認**: エラーログが出力されていない

### フロントエンド期待形式チェックリスト

**ダッシュボード API (`/api/dashboard/overview/`)**
```javascript
{
  "today": {
    "study_time": number,
    "problems_attempted": number,
    "problems_correct": number,
    "accuracy": number
  },
  "active_session": object | null,
  "study_streak": number,
  "weekly_summary": {
    "total_time": number,
    "total_problems": number,
    "total_correct": number,
    "accuracy": number
  },
  "recent_quizzes": array,
  "subject_progress": array,
  "upcoming_goals": array
}
```

**学習統計 API (`/api/studylogs/statistics/overview/`)**
```javascript
{
  "total_study_time": number,
  "total_study_time_display": string,
  "total_problems_attempted": number,
  "total_problems_correct": number,
  "overall_accuracy": number,
  "study_days": number,
  "current_streak": number,
  "longest_streak": number,
  // ... その他統計データ
}
```

### テスト失敗時の対処法

**パターン1: 500エラー**
```bash
tail -f backend/logs/django.log
# モデル整合性チェックルールを適用
```

**パターン2: レスポンス形式不一致**
```bash
# APIレスポンスとフロントエンド期待形式を比較
# シリアライザーやビューの修正が必要
```

**パターン3: データが期待通りでない**
```bash
# Djangoシェルで同一条件でデータ取得テスト
# フィルタリングロジックの確認
```

---

## バックエンド修正時の要件適合性テスト必須ルール

### 修正ロジックの要件適合性検証手順
バックエンドの修正完了後、API統合テストに加えて、**ユーザーの指示・要望通りの挙動をするかを必ず検証**すること：

#### 1. 要件適合性テストの実行（必須）

**A. 指示内容の再確認**
```bash
echo "=== 修正要件の確認 ==="
echo "指示内容: [実際の修正指示を記載]"
echo "期待する挙動: [期待される動作を具体的に記載]"
echo "対象画面/API: [影響を受ける画面・API]"
```

**C. 画面別要件適合性確認**

**B. データフィルタリング検証（科目管理の場合）**
```bash
echo "=== データフィルタリング検証 ==="

# 組織1のユーザーでテスト
TOKEN_ORG1=$(curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"org1_user@example.com", "password":"testpass"}' | jq -r '.token')

SUBJECTS_ORG1=$(curl -s -X GET http://localhost:8000/api/problems/subjects/ -H "Authorization: Bearer $TOKEN_ORG1")
echo "組織1の科目数: $(echo "$SUBJECTS_ORG1" | jq 'length')"

# 組織2のユーザーでテスト
TOKEN_ORG2=$(curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"org2_user@example.com", "password":"testpass"}' | jq -r '.token')

SUBJECTS_ORG2=$(curl -s -X GET http://localhost:8000/api/problems/subjects/ -H "Authorization: Bearer $TOKEN_ORG2")
echo "組織2の科目数: $(echo "$SUBJECTS_ORG2" | jq 'length')"

# データ分離確認
if [ "$(echo "$SUBJECTS_ORG1" | jq 'length')" != "$(echo "$SUBJECTS_ORG2" | jq 'length')" ] || \
   [ "$(echo "$SUBJECTS_ORG1" | jq -c 'sort')" != "$(echo "$SUBJECTS_ORG2" | jq -c 'sort')" ]; then
  echo "✅ 組織間でデータが適切に分離されています"
else
  echo "❌ 組織間でデータ分離が機能していません"
fi
```

**A. 指示された要件の動作確認**

**B. エッジケースの確認**

**C. 挙動確認テスト（必須実行）**
```python
# Djangoシェルでの動作確認
python manage.py shell -c "
from django.contrib.auth import get_user_model
from core.subject_service import SubjectService

User = get_user_model()
user1 = User.objects.filter(organization_id=1).first()
user2 = User.objects.filter(organization_id=2).first()

subjects1 = list(SubjectService.get_user_subjects(user1))
subjects2 = list(SubjectService.get_user_subjects(user2))

print(f'組織1ユーザーの科目数: {len(subjects1)}')
print(f'組織2ユーザーの科目数: {len(subjects2)}')

if set([s.name for s in subjects1]) == set([s.name for s in subjects2]):
    print('❌ 組織間で同じ科目が返されています（データ分離不備）')
else:
    print('✅ 組織ごとに異なる科目が返されています')
"
```

#### 2. 要件適合性の判定基準

**A. データ取得要件確認**

**B. フロントエンド期待動作との照合**

以下を**すべて**満たすことを確認：

✅ **指示要件適合**: ユーザーの指示通りの動作をする
✅ **データ正確性**: 組織/会員ごとのデータが要件通り取得される
✅ **画面間整合性**: 複数画面で一貫したデータ表示
✅ **フロントエンド適合**: Reactコンポーネントが期待する形式
✅ **エッジケース対応**: 特殊なケース（組織未所属等）で適切な動作
✅ **既存機能非破綻**: 修正により他機能が影響を受けていない
✅ **パフォーマンス維持**: 修正前と同等以上のパフォーマンス

### 修正完了時の必須報告項目
修正完了時は以下を**必ず**報告すること：

1. **要件適合性確認結果**
   - 指示内容の実装状況
   - 期待する挙動の動作確認結果
   - データフィルタリングの動作確認

2. **API統合テスト結果**
   - 全関連APIの動作状況
   - レスポンス形式の適合性
   - エラーハンドリングの動作

3. **画面影響確認結果**
   - ダッシュボード画面への影響
   - 学習統計画面への影響
   - 問題管理画面への影響

4. **検証時に発見した課題**
   - 期待と異なる動作があった場合の詳細
   - 修正が必要な追加の箇所

5. **今後の推奨事項**
   - さらなる改善提案
   - 関連する他機能への影響可能性
