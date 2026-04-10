# I033 計画書: GitHub Projects カンバンと Milestones（Phase 1〜3）の設定

## 基本情報
- **計画書ID**: plan_I033
- **関連イシュー**: #76
- **作成根拠資料**: docs/proposals/I026_ai_dev_improvement_proposal.md（改善案 J）
- **実装後評価**: （未作成）
- **作成日**: 2026-04-11

---

## 1. 背景/目的
- 改善イシュー（I028〜I036）の進捗が一目でわからない状態
- GitHub Projects ボードと Milestones を設定することで、改善フェーズの進捗を可視化する
- 作業はすべて `gh` CLI で実施（UI 操作なし）

---

## 2. 受け入れ条件
- [ ] Milestones 3件（Phase 1〜3）が GitHub 上に作成されている
- [ ] 各改善イシューが対応する Milestone に紐づいている
- [ ] GitHub Projects ボードが作成され、改善イシューが登録されている
- [ ] I034・I035・I036 に GitHub Issue 番号が登録されている

---

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: GitHub リポジトリの Projects・Milestones、docs/issues/open/I034.md・I035.md・I036.md（GitHub Issue 番号追記）

---

## 4. 変更点一覧（具体）

### GitHub 操作（gh CLI）
| 操作 | 対象 |
|------|------|
| GitHub Issue 作成 | I034・I035・I036（各 .md ファイルに番号追記） |
| Milestone 作成 | Phase 1・Phase 2・Phase 3 |
| Issue → Milestone 紐づけ | I028〜I036 の全 GitHub Issue |
| Projects ボード作成 | "AI Dev Improvement（Phase 1〜3）" |
| Projects への Issue 追加 | I028〜I036 の全 GitHub Issue |

### ファイル変更
| ファイル | 変更内容 |
|---------|---------|
| docs/issues/open/I034.md | `## 関連資料` に GitHub Issue 番号追記 |
| docs/issues/open/I035.md | `## 関連資料` に GitHub Issue 番号追記 |
| docs/issues/open/I036.md | `## 関連資料` に GitHub Issue 番号追記 |

---

## 5. 実装手順（ステップ）

### ステップ 1: I034・I035・I036 の GitHub Issue 作成

```bash
# I034
ISSUE_34=$(gh issue create \
  --title "I034: pre-commit hooks の導入（シークレット検出・コード品質チェック）" \
  --body "$(cat docs/issues/open/I034.md)" \
  --label "enhancement" \
  --json url --jq '.url')
echo "I034: $ISSUE_34"

# I035
ISSUE_35=$(gh issue create \
  --title "I035: Sequential Thinking・Web Search MCP の評価と導入" \
  --body "$(cat docs/issues/open/I035.md)" \
  --label "enhancement" \
  --json url --jq '.url')
echo "I035: $ISSUE_35"

# I036
ISSUE_36=$(gh issue create \
  --title "I036: workflow.md の /retro 推奨化" \
  --body "$(cat docs/issues/open/I036.md)" \
  --label "documentation" \
  --json url --jq '.url')
echo "I036: $ISSUE_36"
```

作成後、返却された Issue 番号を各 .md ファイルの `## 関連資料` に追記する。

### ステップ 2: Milestones 3件の作成

```bash
# Phase 1
MS1=$(gh api repos/osushi0404-dev/study-app-multitenant/milestones \
  --method POST \
  --field title="Phase 1: settings.json 改善・Dependabot・PR テンプレート（I028・I029）" \
  --field description="改善イシュー Phase 1: I028, I029" \
  --jq '.number')
echo "Phase 1 Milestone: $MS1"

# Phase 2
MS2=$(gh api repos/osushi0404-dev/study-app-multitenant/milestones \
  --method POST \
  --field title="Phase 2: GitHub MCP・採番ロジック修正・Branch protection・Projects・pre-commit（I030〜I034）" \
  --field description="改善イシュー Phase 2: I030, I031, I032, I033, I034" \
  --jq '.number')
echo "Phase 2 Milestone: $MS2"

# Phase 3
MS3=$(gh api repos/osushi0404-dev/study-app-multitenant/milestones \
  --method POST \
  --field title="Phase 3: Sequential Thinking・Web Search MCP・/retro 推奨化（I035・I036）" \
  --field description="改善イシュー Phase 3: I035, I036" \
  --jq '.number')
echo "Phase 3 Milestone: $MS3"
```

### ステップ 3: Issue を Milestone に紐づける

既知の GitHub Issue 番号:
- I028 = #58, I029 = #60（Phase 1）
- I030 = #71, I031 = #69, I032 = #73, I033 = #76, I034 = 作成後に確認（Phase 2）
- I035 = 作成後に確認, I036 = 作成後に確認（Phase 3）

```bash
REPO="osushi0404-dev/study-app-multitenant"

# Phase 1
for NUM in 58 60; do
  gh api repos/$REPO/issues/$NUM --method PATCH --field milestone=$MS1
done

# Phase 2（I034番号は作成後に代入）
for NUM in 71 69 73 76 $I034_NUM; do
  gh api repos/$REPO/issues/$NUM --method PATCH --field milestone=$MS2
done

# Phase 3（I035・I036番号は作成後に代入）
for NUM in $I035_NUM $I036_NUM; do
  gh api repos/$REPO/issues/$NUM --method PATCH --field milestone=$MS3
done
```

### ステップ 4: GitHub Projects ボードの作成

```bash
PROJECT_NUM=$(gh project create \
  --owner osushi0404-dev \
  --title "AI Dev Improvement（Phase 1〜3）" \
  --format json | jq '.number')
echo "Project number: $PROJECT_NUM"
```

### ステップ 5: Projects に Issue を追加

```bash
OWNER="osushi0404-dev"
REPO_URL="https://github.com/osushi0404-dev/study-app-multitenant/issues"

for ISSUE_NUM in 58 60 71 69 73 76 $I034_NUM $I035_NUM $I036_NUM; do
  gh project item-add $PROJECT_NUM \
    --owner $OWNER \
    --url "$REPO_URL/$ISSUE_NUM"
done
```

### ステップ 6: コミット・プッシュ

```bash
git add docs/issues/open/I034.md docs/issues/open/I035.md docs/issues/open/I036.md
git commit -m "docs(I033): add GitHub Issue numbers to I034/I035/I036"
git push
```

---

## 6. テスト計画
### 自動
- なし（コード変更なし）

### 手動
- GitHub UI で Milestones 3件の存在確認
- 各 Issue の Milestone 紐づけ確認
- GitHub Projects ボードの存在確認・Issue 登録確認

---

## 7. ロールバック
- Milestones 削除: `gh api repos/osushi0404-dev/study-app-multitenant/milestones/{number} --method DELETE`
- Projects 削除: `gh project delete {number} --owner osushi0404-dev`
- Issue の Milestone 解除: `gh api repos/.../issues/{number} --method PATCH --field milestone=null`
- I034〜I036 の GitHub Issue は閉じずに残す（別タスクで参照されるため）

---

## 8. Risk & 回避策
| リスク | 可能性 | 回避策 |
|--------|--------|--------|
| gh project コマンドの権限不足 | 低 | `gh auth status` で権限確認後に実行 |
| Milestone 名の重複 | 低 | 作成前に `gh api .../milestones` で既存確認 |
| I034〜I036 の Issue 番号取得失敗 | 低 | `gh issue list --limit 5` で直後に番号確認 |
| Projects v2 API の制限 | 中 | `gh project list` で quota 確認 |

---

## 9. 承認ポイント
- [ ] 実装手順（gh CLI コマンド群）に問題がないか
- [ ] Milestone 名称（Phase 1〜3）が意図通りか
- [ ] Projects ボード名 "AI Dev Improvement（Phase 1〜3）" でよいか（**仮定で決めた**）
- [ ] I034/I035/I036 の GitHub Issue をこのタスク内で作成することに同意済み（**ユーザー確認済み**）
- [ ] セキュリティ影響なし（Backend/Frontend コード変更なし、GitHub 設定のみ）
- [ ] Danger Ops なし
