# イシューフロー

詳細なイシューフロー運用ルールを定義します。
`docs/runbooks/workflow.md` の「フロー」セクションも合わせて参照してください。

## イシュー新規作成時の採番ルール
新しいイシューを作成する際は、**ローカルイシューファイルの最大番号** と **GitHubイシューの登録件数** の両方を考慮して採番する。

### 採番ルール
**新イシュー番号 = ローカル最大番号 + GitHub登録件数 + 1**

例:
- ローカル0件 + GitHub2件 → 0+2+1 = **003**
- ローカル最大3 + GitHub1件 → 3+1+1 = **005**
- ローカル最大5 + GitHub0件 → 5+0+1 = **006**

```bash
# ローカルイシューファイルの最大番号を取得（open/in_progress/closed 全て確認）
LOCAL_MAX=$(ls docs/issues/open/*.md docs/issues/in_progress/*.md docs/issues/closed/*.md 2>/dev/null \
  | grep -o '[0-9]\+\.md' | sed 's/\.md//' | sort -n | tail -1)
LOCAL_MAX=${LOCAL_MAX:-0}

# GitHubイシューの登録件数を取得（open + closed）
GITHUB_COUNT=$(gh issue list --state all --limit 1000 --json number | jq 'length')
GITHUB_COUNT=${GITHUB_COUNT:-0}

# 新しいイシュー番号を採番
NEXT_NUM=$((LOCAL_MAX + GITHUB_COUNT + 1))
ISSUE_NUM=$(printf "%03d" $NEXT_NUM)
echo "次のイシュー番号: $ISSUE_NUM"
```

**重要**: closed ディレクトリも必ず確認すること。GitHub 件数取得には `gh` コマンドが必要（未認証の場合は `gh auth login` を実施）。

## イシュー作成時の自動実行フロー（必須）

ユーザーから「イシューファイルを作成して」または「新しいイシューを作成して」という指示を受けた場合は、**必ず以下の手順を自動的に実行**すること：

### 1. イシュー番号の採番
```bash
# ローカルイシューファイルの最大番号を取得（open/in_progress/closed 全て確認）
LOCAL_MAX=$(ls docs/issues/open/*.md docs/issues/in_progress/*.md docs/issues/closed/*.md 2>/dev/null \
  | grep -o '[0-9]\+\.md' | sed 's/\.md//' | sort -n | tail -1)
LOCAL_MAX=${LOCAL_MAX:-0}

# GitHubイシューの登録件数を取得（open + closed）
GITHUB_COUNT=$(gh issue list --state all --limit 1000 --json number | jq 'length')
GITHUB_COUNT=${GITHUB_COUNT:-0}

# 新しいイシュー番号を採番（ローカル最大番号 + GitHub件数 + 1）
NEXT_NUM=$((LOCAL_MAX + GITHUB_COUNT + 1))
ISSUE_NUM=$(printf "%03d" $NEXT_NUM)
```

### 2. イシューファイル作成
```bash
# テンプレートからイシューファイル作成
cp docs/issues/templates/issue_template.md docs/issues/open/${ISSUE_NUM}.md
# 内容を編集（タイトル、概要等をユーザーの指示に基づいて記載）
```

### 3. 作業用ブランチの自動作成（必須）
```bash
# developブランチから分岐してfeatureブランチを作成
git checkout develop
git pull origin develop  # 最新のdevelopを取得（リモートがある場合）
git checkout -b feature/I${ISSUE_NUM}-[概要を英語化したもの]
```

**重要**: 必ず**developブランチをベース**にfeatureブランチを作成すること。mainブランチからは作成しない。

**ブランチ命名規則**:
- フォーマット: `feature/I{イシュー番号3桁}-{概要を英語化してケバブケース}`
- 例:
  - `feature/I030-media-asset-models`
  - `feature/I031-dashboard-performance`
  - `feature/I032-user-authentication-fix`

**概要の英語化ルール**:
- 日本語の概要をシンプルな英語に変換
- スペースは`-`（ハイフン）に変換
- 最大5単語程度に要約
- 例:
  - 「問題・解説画像の複数対応」→ `media-asset-models`
  - 「ダッシュボードのパフォーマンス改善」→ `dashboard-performance`
  - 「ユーザー認証のバグ修正」→ `user-authentication-fix`

### 4. GitHubイシューの登録（必須）
```bash
# ghコマンドでGitHubにイシューを登録
gh issue create \
  --title "I${ISSUE_NUM}: [イシュータイトル]" \
  --body "$(cat docs/issues/open/${ISSUE_NUM}.md)" \
  --label "[種別に応じたラベル]"
```

**ラベル設定**:
- Bug → `bug`
- Feature → `enhancement`
- Documentation → `documentation`
- Refactoring → `refactoring`

**注意事項**:
- GitHubイシュー番号とローカルイシュー番号は異なる場合がある（GitHub側は自動採番）
- ローカルイシュー番号（例: I035）をタイトルに含めることで紐づけを明確にする
- `gh auth login`で認証済みであることが前提

### 5. ユーザーへの報告
ブランチ作成・GitHubイシュー登録後、必ず以下を報告：

```
✅ イシュー#XXX を作成しました: [タイトル]
📂 ファイル: docs/issues/open/XXX.md
🌿 ブランチ作成: feature/IXXX-[概要]
🔗 GitHubイシュー: [GitHubイシューURL]

このブランチで作業を開始します。
```

---

## イシューフロー（統合ルール）

イシューの作成から完了・クローズまでの統一フローを以下に定める。

### フロー図

```
【イシューフロー】

=== フェーズ1: イシュー準備 ===
1. イシューファイル作成（テンプレート：docs/issues/templates/issue_template.md）
    ↓
2. イシューブランチ作成（feature/IXXX-概要）
    ↓
3. GitHubイシュー登録
    ↓
4. ユーザーがイシューファイルを確認
    ↓
5. ユーザーがイシューファイルを承認
    ↓

=== フェーズ2: 計画・設計 ===
6. 計画書作成
    ↓
7. テストケース作成（2種類を別ファイルで作成）
   - ユーザーテストケース（docs/tests/open/IXXX_manual_test.md）
   - 自動テストケース（docs/tests/open/IXXX_auto_test.md）
    ↓
8. レビューファイル作成（テンプレート：docs/reviews/templates/review_template.md）
   ※実装結果評価セクションは空欄のまま作成
    ↓
9. ユーザーが計画書・テストケースを確認
    ↓
10. ユーザーが計画書・テストケースを承認
    ↓
10.5. /plan-issue-review によるベストプラクティス・セキュリティ・モダン開発観点レビュー（OK/NG）
   - NG の場合 計画書・テスト文書修正 → 10.5 に戻る
    ↓

=== フェーズ3: 実装・テスト ===
11. 実装
    ↓
12. 自動テスト実行（ユニットテスト等）
    ↓
13. レビューファイルに実装結果を記入
    ↓
14. ユーザーがテスト（ユーザーテストケースに基づく）
    ↓
─────────────────────────────────────────
    ↓ OK                    ↓ NG
─────────────────────────────────────────
14.5. /retro I### （任意）  15. レビューにNG結果記入
      または直接フェーズ4へ 16. エラー管理ファイル作成（初回）
    ↓                          または追記（2回目以降）
    ↓                          （docs/tests/templates/error_log_template.md）
    ↓                     17. エラー対応計画書を新規作成
    ↓                          （docs/plans/open/に新規作成、元の計画書は上書きしない）
    ↓                     18. 承認待ち → 修正
    ↓                     19. 再テスト（14に戻る）
─────────────────────────────────────────
    ↓ ←────────────────────┘（OKになったら）
─────────────────────────────────────────
    ↓

=== フェーズ4: クローズ処理 ===
20. レビューにOK結果記入
21. テストケース → closed/
22. エラー管理ファイル → closed/（該当する場合）
23. 計画書 → closed/（エラー対応計画書含む全て）
24. イシューファイル → closed/
25. featureブランチをdevelopにマージ
26. レビューファイル → closed/
27. GitHubイシューをクローズ
```

### 各ステップの詳細

#### フェーズ1: イシュー準備

**ステップ1: イシューファイル作成**
- テンプレート: `docs/issues/templates/issue_template.md`
- 保存先: `docs/issues/open/`
- 命名規則: `XXX.md`（XXX: 3桁のイシュー番号）

```bash
# ローカルイシューファイルの最大番号を取得（open/in_progress/closed 全て確認）
LOCAL_MAX=$(ls docs/issues/open/*.md docs/issues/in_progress/*.md docs/issues/closed/*.md 2>/dev/null \
  | grep -o '[0-9]\+\.md' | sed 's/\.md//' | sort -n | tail -1)
LOCAL_MAX=${LOCAL_MAX:-0}

# GitHubイシューの登録件数を取得（open + closed）
GITHUB_COUNT=$(gh issue list --state all --limit 1000 --json number | jq 'length')
GITHUB_COUNT=${GITHUB_COUNT:-0}

# 新しいイシュー番号を採番（ローカル最大番号 + GitHub件数 + 1）
NEXT_NUM=$((LOCAL_MAX + GITHUB_COUNT + 1))
ISSUE_NUM=$(printf "%03d" $NEXT_NUM)

# テンプレートからコピー
cp docs/issues/templates/issue_template.md docs/issues/open/${ISSUE_NUM}.md
```

**ステップ2: イシューブランチ作成**
- developブランチをベースにfeatureブランチを作成
- 命名規則: `feature/I{イシュー番号3桁}-{概要を英語化してケバブケース}`

```bash
git checkout develop
git pull origin develop  # 最新のdevelopを取得
git checkout -b feature/I${ISSUE_NUM}-[概要を英語化したもの]
```

**ステップ3: GitHubイシュー登録**
```bash
gh issue create \
  --title "I${ISSUE_NUM}: [イシュータイトル]" \
  --body "$(cat docs/issues/open/${ISSUE_NUM}.md)" \
  --label "[種別に応じたラベル]"
```

**ステップ4-5: ユーザー確認・承認**
- ユーザーがイシューファイルの内容を確認
- 承認後、フェーズ2に進む

#### フェーズ2: 計画・設計

**ステップ6: 計画書作成**
- テンプレート: `docs/plans/templates/plan_template.md`
- 保存先: `docs/plans/open/`
- 命名規則: `plan_I{イシュー番号}_{概要}.md`

**ステップ7: テストケース作成**
2種類のテストケースを**別ファイル**で作成：

| 種類 | ファイル名 | 内容 |
|------|-----------|------|
| ユーザーテスト | `IXXX_manual_test.md` | ユーザーしか実施できないテスト項目 |
| 自動テスト | `IXXX_auto_test.md` | ユニットテスト、統合テスト等の自動テスト項目 |

- テンプレート: `docs/tests/templates/test_record_template.md`
- 保存先: `docs/tests/open/`

**ステップ8: レビューファイル作成**
- テンプレート: `docs/reviews/templates/review_template.md`
- 保存先: `docs/reviews/open/`
- 命名規則: `IXXX_review.md`（XXX: イシュー番号3桁）
- **重要**: 実装結果評価セクションは空欄のまま作成

レビューファイルの記載タイミング：
| 記載タイミング | 記載する項目 |
|---------------|-------------|
| ステップ8（実装前） | 基本情報、対象計画書、レビュー目的、期待する成果 |
| ステップ13（実装後） | 実装結果評価、品質評価、技術的評価 |
| ステップ15/20（テスト後） | テスト結果、発見した問題・改善点、最終判定 |

**ステップ9-10: ユーザー確認・承認**
- ユーザーが計画書・テストケースの内容を確認
- 承認後、ステップ10.5へ進む

**ステップ10.5: /plan-issue-review の実行**
- `docs/plans/open/` と `docs/tests/open/` の生成ドキュメントをベストプラクティス・セキュリティ・モダン開発観点でレビュー
- NG の場合: 計画書・テスト文書を修正してから再実行
- OK の場合: フェーズ3（実装）へ進む

#### フェーズ3: 実装・テスト

**ステップ11: 実装**
- 計画書に基づいた実装作業を実施

**ステップ12: 自動テスト実行**
- `IXXX_auto_test.md`に記載された自動テストを実行
- 全テストが成功することを確認
- **実行不可ケースも NG 扱い**: 構造的・環境的な理由でテストを実行できない場合は失敗と同等に扱い、ステップ15（NGの場合のエラー対応ループ）へ進む。Claude が「ロジックは正しい」と独断で OK 判断することは禁止。

**ステップ13: レビューファイルに実装結果を記入**
- 実装結果評価セクションを記入
- 品質評価、技術的評価を記入

**ステップ14: ユーザーテスト**
- `IXXX_manual_test.md`に基づいてユーザーがテストを実施
- 結果に応じてOK/NGに分岐

#### ステップ15-19: NGの場合のエラー対応ループ

**ステップ15: レビューにNG結果記入**
- レビューファイルにNG結果と発見された問題を記入

**ステップ16: エラー管理ファイル作成/追記**
- 初回: `docs/tests/templates/error_log_template.md`から新規作成
- 2回目以降: 既存ファイルに追記（新規作成しない）
- 保存先: `docs/tests/open/`
- 命名規則: `error_IXXX.md`

**ステップ17: エラー対応計画書を新規作成**
- 元の計画書を上書きしない（`_2`, `_3`...の連番で新規作成）
- 保存先: `docs/plans/open/`

**ステップ18: 承認待ち → 修正**
- ユーザー承認後に修正実施

**ステップ19: 再テスト**
- ステップ14（ユーザーテスト）に戻る

#### フェーズ4: クローズ処理（ステップ20-27）

**ステップ20: レビューにOK結果記入**
```markdown
## テスト結果
- **最終テスト日**: YYYY-MM-DD
- **結果**: OK
- **確認者**: ユーザー
```

**ステップ21: テストケースをclosedに移動**
```bash
# 完了情報を追記（両方のテストファイル）
for TEST_FILE in docs/tests/open/IXXX_*_test.md; do
  echo "## 完了情報" >> "$TEST_FILE"
  echo "- **完了日時**: $(date)" >> "$TEST_FILE"
  echo "- **結果**: OK" >> "$TEST_FILE"
  mv "$TEST_FILE" docs/tests/closed/
done
```

**ステップ22: エラー管理ファイルをclosedに移動（該当する場合）**
```bash
if [ -f "docs/tests/open/error_IXXX.md" ]; then
  echo "## 完了情報" >> docs/tests/open/error_IXXX.md
  echo "- **解決日時**: $(date)" >> docs/tests/open/error_IXXX.md
  mv docs/tests/open/error_IXXX.md docs/tests/closed/
fi
```

**ステップ23: 計画書をclosedに移動**
```bash
# 全ての関連計画書（エラー対応計画書含む）をclosedに移動
for PLAN_FILE in docs/plans/open/plan_IXXX_*.md; do
  echo "## 完了情報" >> "$PLAN_FILE"
  echo "- **完了日時**: $(date)" >> "$PLAN_FILE"
  echo "- **対応者**: Claude Code" >> "$PLAN_FILE"
  echo "- **レビュー結果**: OK" >> "$PLAN_FILE"
  mv "$PLAN_FILE" docs/plans/closed/
done
```

**ステップ24: イシューファイルをclosedに移動**
```bash
cat >> docs/issues/open/XXX.md << 'EOF'

## 完了情報
- **完了日時**: YYYY-MM-DD HH:MM
- **対応者**: Claude Code
- **実施内容の要約**: [実装内容を簡潔に記載]
- **関連ファイル**:
  - 計画書: docs/plans/closed/plan_IXXX_*.md
  - レビュー: docs/reviews/closed/IXXX_review.md
  - テスト: docs/tests/closed/IXXX_*_test.md
EOF

mv docs/issues/open/XXX.md docs/issues/closed/
```

**ステップ25: featureブランチをdevelopにマージ**
```bash
git checkout develop

git merge feature/IXXX-[概要] --no-ff -m "$(cat <<'EOF'
Merge feature/IXXX: [イシュータイトル]

- 実施内容の要約
- 関連ファイル
- テスト結果: OK

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

git push origin develop
```

**ステップ26: レビューファイルをclosedに移動**
```bash
echo "## クローズ情報" >> docs/reviews/open/reviewXXX_IXXX.md
echo "- **クローズ日時**: $(date)" >> docs/reviews/open/reviewXXX_IXXX.md

mv docs/reviews/open/reviewXXX_IXXX.md docs/reviews/closed/
```

**ステップ27: GitHubイシューをクローズ**
```bash
# GitHubイシュー番号を確認
gh issue list --state open | grep "IXXX"

# イシューをクローズ
gh issue close [GitHub イシュー番号] --comment "実装完了・ユーザーテストOK

## 実施内容
- [実装内容を箇条書きで記載]

## テスト結果
- [テスト結果を記載]

🤖 Generated with Claude Code"
```

### 重要な注意事項

1. **レビューファイルは実装前に作成**: 実装後に作成を忘れないよう、ステップ8で先に作成する
2. **実装結果は後から記入**: レビューファイルの実装結果評価セクションはステップ13で記入
3. **テストケースは2種類**: ユーザーテスト用と自動テスト用を別ファイルで管理
4. **元の計画書を上書きしない**: エラー対応時は必ず新規計画書を作成（履歴保持のため）
5. **エラー管理ファイルは追記方式**: 同一イシューのエラーは1ファイルで管理
6. **全てのファイルをclosedに移動**: テスト、エラー管理、計画書、イシュー、レビューの全て
7. **マージは最後**: 全てのドキュメント更新後にブランチマージを実行
8. **レビューファイルは最後にクローズ**: 全体の振り返りを含めるため最後に移動
9. **GitHubイシューも必ずクローズ**: ローカルファイルのクローズ後、GitHubイシューも忘れずにクローズ
10. **再テストはステップ14に戻る**: エラー対応後の再テストはユーザーテストから再開

---

## イシュー対応中のブランチ運用

### コミット時のルール
```bash
# 計画書作成時
git add docs/plans/
git commit -m "docs: イシュー#XXX の計画書作成"

# 実装時（複数コミットOK）
git commit -m "feat: MediaAssetモデル追加（イシュー#XXX）"
git commit -m "feat: API実装（イシュー#XXX）"

# レビュー・クローズ時
git commit -m "docs: イシュー#XXX レビュー完了・クローズ"
```

### イシュー対応時の必須ルール
イシュー番号（例: 001, #1など）を指定されたら、必ず以下を実行：
1. `/docs/issues/open/XXX.md`または`/docs/issues/in_progress/XXX.md`を読み込む（XXXは指定された番号）
2. `/rules/`配下の関連ルールファイルを確認
3. 特にコード変更時はコーディング標準を厳守
4. **UX設計セクションを計画書に必ず含める**（docs/runbooks/ux-rules.md参照）
5. テスト実行時は該当するテストルールを参照
6. 完了後は対応内容を報告し、承認を待つ

### ブランチ作成失敗時の対処
ブランチ作成に失敗した場合：
1. エラー内容をユーザーに報告
2. 原因を説明（例: ブランチ名の重複、git未初期化等）
3. 対処方法を提案
