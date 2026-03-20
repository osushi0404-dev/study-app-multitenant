# 問題データ管理システム

## 📋 概要

このディレクトリは、学習アプリで使用する問題データを管理します。
マークダウン形式で問題を作成し、Djangoコマンドでデータベースに登録できます。

## 📂 ディレクトリ構造

```
backend/data/
├── problems/                    # 問題データ専用ディレクトリ
│   ├── templates/              # 問題作成用テンプレート
│   │   └── Question_Template_Minimal_4Choice.md
│   ├── aws_cert/               # AWS資格試験問題
│   ├── high_school/            # 高校科目問題（今後追加）
│   ├── junior_high/            # 中学科目問題（今後追加）
│   ├── bookkeeping/            # 簿記問題（今後追加）
│   └── ds_kentei/              # DS検定問題（今後追加）
└── README.md                   # このファイル
```

### ディレクトリの命名規則

- **科目グループ**: スネークケース（例: `aws_cert`, `high_school`）
- **マークダウンファイル**: スネークケース（例: `cloud_practitioner.md`, `math_1a.md`）

## 📝 マークダウン形式仕様

### 基本構造

問題は以下の形式で記述します：

```markdown
### Q1
**試験**：CLF-C02
**問題タイプ**：単一選択（4択・正解は1つ）
**問題文**：クラウドコンピューティングの主な利点として正しいものはどれですか？
**選択肢**：
- A. 初期コストが高い
- B. スケーラビリティが高い
- C. 物理サーバーの管理が必要
- D. インターネット接続が不要
**正解**：B
**解説**：クラウドコンピューティングの主な利点はスケーラビリティです。必要に応じてリソースを迅速に拡張・縮小できるため、需要の変動に柔軟に対応できます。
---

### Q2
...
```

### 必須セクション

| セクション | 形式 | 説明 |
|----------|------|------|
| **問題番号ヘッダー** | `### Q[番号]` | 見出しレベル3で問題の区切りを示す |
| **問題文** | `**問題文**：[内容]` | 問題の本文（10〜10000文字） |
| **選択肢** | `**選択肢**：` + 箇条書き | `- A. [選択肢A]` の形式 |
| **正解** | `**正解**：[A\|B\|C\|D]` | 正解の選択肢ID（複数の場合は `A,C` のように記載） |

### 任意セクション

| セクション | 形式 | 説明 |
|----------|------|------|
| **解説** | `**解説**：[内容]` | 正解の理由や解説（最大10000文字） |
| **試験** | `**試験**：[試験コード]` | 試験種別や科目コード |
| **問題タイプ** | `**問題タイプ**：[タイプ]` | 問題の種別（単一選択、複数選択等） |

### 詳細仕様

詳細な仕様は以下のドキュメントを参照してください：
- [マークダウンパーサー詳細設計](../docs/detailed_design/backend/problem_data_management/02_markdown_parser.md)

### テンプレートファイル

問題作成用のテンプレートファイルを用意しています：
- **最小構成テンプレート**: [`templates/Question_Template_Minimal_4Choice.md`](problems/templates/Question_Template_Minimal_4Choice.md)

テンプレートをコピーして使用してください。

## 🚀 問題データの登録方法

### 1. マークダウンファイルの準備

1. 科目グループディレクトリを作成（必要に応じて）
   ```bash
   mkdir -p backend/data/problems/[科目グループ名]
   ```

2. マークダウンファイルを作成
   ```bash
   # 例: AWS認定クラウドプラクティショナー
   touch backend/data/problems/aws_cert/cloud_practitioner.md
   ```

3. テンプレートを参考に問題を記述

### 2. 科目IDの確認

登録先の科目IDを確認します：

```bash
docker-compose exec backend python manage.py shell -c "
from problems.models import Subject
for s in Subject.objects.all():
    print(f'ID: {s.id}, Name: {s.name}')
"
```

### 3. コマンド実行

#### ドライラン（テスト実行）

実際には登録せず、パース結果のみ確認します：

```bash
docker-compose exec backend python manage.py import_problems \
  --file=backend/data/problems/aws_cert/cloud_practitioner.md \
  --subject-id=20 \
  --dry-run
```

#### 実際の登録

```bash
docker-compose exec backend python manage.py import_problems \
  --file=backend/data/problems/aws_cert/cloud_practitioner.md \
  --subject-id=20 \
  --created-by=admin@example.com
```

### 4. 登録結果の確認

```bash
docker-compose exec backend python manage.py shell -c "
from problems.models import Problem
problems = Problem.objects.filter(subject_id=20)
print(f'登録された問題数: {problems.count()}')
for p in problems[:3]:
    print(f'- {p.question[:50]}...')
"
```

## 🔧 コマンドオプション

| オプション | 必須 | デフォルト | 説明 |
|-----------|------|-----------|------|
| `--file` | ✅ | なし | マークダウンファイルのパス |
| `--subject-id` | ✅ | なし | 登録先の科目ID |
| `--created-by` | ❌ | 管理者ユーザー | 作成者のメールアドレス |
| `--difficulty` | ❌ | 1 | デフォルト難易度（1-3） |
| `--dry-run` | ❌ | False | テスト実行モード（実際には登録しない） |
| `--skip-duplicates` | ❌ | False | 重複問題をスキップ |

### 使用例

```bash
# 高校数学IAの問題を登録
docker-compose exec backend python manage.py import_problems \
  --file=backend/data/problems/high_school/math_1a.md \
  --subject-id=10 \
  --difficulty=2

# 簿記3級の問題を登録（重複スキップ）
docker-compose exec backend python manage.py import_problems \
  --file=backend/data/problems/bookkeeping/level_3.md \
  --subject-id=15 \
  --difficulty=1 \
  --skip-duplicates
```

## 📊 運用フロー

1. **問題作成**: マークダウンエディタで問題を作成
2. **ファイル配置**: `backend/data/problems/[科目グループ]/[科目名].md` に保存
3. **ドライラン**: `--dry-run` でパース結果を確認
4. **本番登録**: 確認後、実際にコマンド実行
5. **動作確認**: アプリで問題が表示されることを確認

## 🐛 トラブルシューティング

### 問題がパースされない

**症状**: パース失敗のメッセージが表示される

**原因と対処法**:
- **必須セクションの不足**: `**問題文**：`、`**選択肢**：`、`**正解**：` がすべて存在するか確認
- **問題番号ヘッダーの形式**: `### Q[番号]` の形式になっているか確認（見出しレベル3が必須）
- **選択肢の形式**: `- A. [内容]` の形式になっているか確認（`-` の後にスペース、アルファベット + `.` + スペース）
- **正解の指定**: `**正解**：B` のように選択肢IDが正しく指定されているか確認

### 重複登録される

**症状**: 同じ問題が複数回登録される

**対処法**:
- `--skip-duplicates` オプションを使用
- 既存の問題を削除してから再登録

### 選択肢の順序がおかしい

**症状**: 選択肢の表示順序が意図と異なる

**原因**: 選択肢のアルファベットが正しく昇順（A, B, C, D...）になっていない

**対処法**: マークダウンファイルで選択肢を昇順に修正

### ファイルが見つからない

**症状**: `FileNotFoundError` が表示される

**原因**: ファイルパスが間違っているか、ファイルが存在しない

**対処法**:
- ファイルパスが正しいか確認（Dockerコンテナ内のパスであることに注意）
- ファイルが実際に存在するか確認: `docker-compose exec backend ls -la [ファイルパス]`

### 科目IDが見つからない

**症状**: `InvalidSubjectError` が表示される

**原因**: 指定した科目IDがデータベースに存在しない

**対処法**:
- 科目IDを再確認: `docker-compose exec backend python manage.py shell -c "from problems.models import Subject; print(list(Subject.objects.values_list('id', 'name')))"`
- 科目が存在しない場合は、事前に科目を作成

## 📖 関連ドキュメント

- **詳細設計書**:
  - [アーキテクチャ設計](../docs/detailed_design/backend/problem_data_management/01_architecture.md)
  - [マークダウンパーサー](../docs/detailed_design/backend/problem_data_management/02_markdown_parser.md)
  - [データフロー](../docs/detailed_design/backend/problem_data_management/07_data_flow.md)

- **計画書**:
  - [問題データ管理構造構築](../docs/plans/open/plan_004_I023_問題データ管理構造構築.md)

- **イシュー**:
  - [#023 問題データ管理構造構築](../docs/issues/open/023.md)

## 🔐 セキュリティ注意事項

- **機密情報の記載禁止**: 問題データに個人情報や機密情報を含めないでください
- **ファイルサイズ制限**: 1ファイルあたり最大50MB（約5000問）まで
- **入力検証**: コマンド実行時に自動的に入力検証が行われます
- **バックアップ**: 重要なデータは定期的にバックアップしてください

## 📝 変更履歴

| 日付 | バージョン | 変更内容 | 担当者 |
|------|-----------|---------|--------|
| 2025-10-15 | 1.0.0 | 初版作成 | Claude Code |

---

**次のステップ**: [マークダウンテンプレート](problems/templates/Question_Template_Minimal_4Choice.md)を参照して問題を作成してください。
