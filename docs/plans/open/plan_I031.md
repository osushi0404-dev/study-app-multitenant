# I031 計画書: issue-flow.md の採番ロジックを issue-bootstrap スキルの実装に統一

## 基本情報
- **計画書ID**: plan_I031
- **関連イシュー**: #69
- **作成根拠資料**: docs/proposals/I026_ai_dev_improvement_proposal.md（改善案 C）
- **実装後評価**: （未作成）
- **作成日**: 2026-04-10

---

## 1. 背景/目的

3点の問題を本イシューで一括修正する。

### A: issue-flow.md の採番ロジック乖離

`docs/runbooks/issue-flow.md` の採番ロジック説明が `issue-bootstrap` スキルの実装と乖離している。

| | docs 記載（現状） | スキル実装（正） |
|--|----------------|----------------|
| ロジック | ローカル最大番号 + GitHub issue 件数 + 1 | FS最大値 と git履歴最大値の**大きい方** + 1 |
| ファイル取得 | `ls docs/issues/open/*.md ...` | `find docs/issues -name "*.md"` |
| GitHub 参照 | `gh issue list` で件数を取得（必須） | 不要（git log で代替） |

放置すると、Claude が docs を参照して手動採番した場合に番号衝突・欠番が生じるリスクがある。

### B: docs/tests/open/ への I039 テストファイル残留

`docs/tests/open/I039_auto_test.md`・`I039_manual_test.md` が残留している。
`docs/tests/closed/` には正しく存在しており、open 側は I039 クローズ時の移動漏れ。

### C: close/SKILL.md のテストケースコメント不明瞭

```bash
# テストケース
for f in docs/tests/open/I${ISSUE_NUM}_*.md; do
  [ -f "$f" ] && mv "$f" docs/tests/closed/
done
```

glob は機能的に auto/manual 両ファイルを処理できるが、`# テストケース` というコメントだけでは
「auto と manual の 2 種類を一括処理している」意図が伝わらず、将来の誤解・改変リスクがある。

---

## 2. 受け入れ条件

- [ ] `issue-flow.md` の採番ロジック説明が `issue-bootstrap` スキルの実装（FS最大値・git履歴最大値の大きい方 + 1）と一致している
- [ ] `gh issue list` を用いた旧採番ロジックの記述がすべて削除されている
- [ ] `docs/tests/open/` に I039 のテストファイルが残っていない
- [ ] `close/SKILL.md` の `# テストケース` コメントが auto/manual 両ファイルを移動することを明示している

---

## 3. 影響範囲

- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: `docs/runbooks/issue-flow.md`・`.claude/skills/close/SKILL.md`・`docs/tests/open/`

---

## 4. 変更点一覧（具体）

### 4-A: `docs/runbooks/issue-flow.md`（3箇所）

旧採番ロジックが以下の 3 箇所に存在する。すべて新ロジックに置換する。

**箇所1**: 「イシュー新規作成時の採番ルール」セクション（冒頭）

変更前:
```
新イシュー番号 = ローカル最大番号 + GitHub登録件数 + 1
...
LOCAL_MAX=$(ls docs/issues/open/*.md ...)
GITHUB_COUNT=$(gh issue list --state all --limit 1000 ...)
NEXT_NUM=$((LOCAL_MAX + GITHUB_COUNT + 1))
```

変更後:
```
新イシュー番号 = max(FS最大値, git履歴最大値) + 1
...
FS_MAX=$(find docs/issues -name "*.md" 2>/dev/null | grep -oP '\d+(?=\.md)' | sort -n | tail -1)
GIT_MAX=$(git log --all --oneline -- "docs/issues/**" | grep -oP 'I0*\d+' | grep -oP '\d+' | sort -n | tail -1)
FS_NUM=$((10#${FS_MAX:-0}))
GIT_NUM=$((10#${GIT_MAX:-0}))
if [ "$FS_NUM" -gt "$GIT_NUM" ]; then LAST_NUM=$FS_NUM; else LAST_NUM=$GIT_NUM; fi
NEXT_NUM=$((LAST_NUM + 1))
ISSUE_NUM=$(printf "%03d" $NEXT_NUM)
```

**箇所2**: 「イシュー作成時の自動実行フロー ステップ1」セクション → 同様に置換

**箇所3**: 「フェーズ1: イシュー準備 ステップ1」セクション → 同様に置換

各箇所の重要注記も更新:
- 旧: 「GitHub 件数取得には `gh` コマンドが必要（未認証の場合は `gh auth login` を実施）」
- 新: 「ファイルシステムだけでなく git 履歴も必ず確認すること（closed から削除されたイシューも番号として使用済み）」

### 4-B: `docs/tests/open/` の残留ファイル削除

```bash
mv docs/tests/open/I039_auto_test.md docs/tests/closed/
mv docs/tests/open/I039_manual_test.md docs/tests/closed/
```

（`docs/tests/closed/` に同名ファイルが既に存在するため、上書き前に確認する）

### 4-C: `.claude/skills/close/SKILL.md` のコメント改善

変更前:
```bash
# テストケース
for f in docs/tests/open/I${ISSUE_NUM}_*.md; do
```

変更後:
```bash
# テストケース（auto_test・manual_test の両ファイルを一括移動）
for f in docs/tests/open/I${ISSUE_NUM}_*.md; do
```

---

## 5. 実装手順（ステップ）

1. `docs/tests/closed/` に I039 の同名ファイルが存在することを確認する
2. `docs/tests/open/I039_auto_test.md`・`I039_manual_test.md` を `docs/tests/closed/` へ上書き移動する（内容は同一のため問題なし）
3. `docs/runbooks/issue-flow.md` の箇所1（採番ルールセクション）を新ロジックに書き換える
4. `docs/runbooks/issue-flow.md` の箇所2（自動実行フロー ステップ1）を新ロジックに書き換える
5. `docs/runbooks/issue-flow.md` の箇所3（フェーズ1 ステップ1）を新ロジックに書き換える
6. `.claude/skills/close/SKILL.md` の `# テストケース` コメントを改善する
7. 旧キーワードの残留がないことを grep で確認する
8. コミット: `docs: fix issue-flow numbering logic and close skill comment (I031)`

---

## 6. テスト計画

### 自動
- `grep -n "GITHUB_COUNT\|gh issue list.*number\|LOCAL_MAX + GITHUB" docs/runbooks/issue-flow.md` → 0件

### 手動
- `issue-flow.md` の採番ロジック説明が新ロジックと一致していることを目視確認
- `docs/tests/open/` に I039 ファイルが残っていないことを確認
- `close/SKILL.md` のコメントが改善されていることを確認

---

## 7. ロールバック

`git revert` または各ファイルを `git checkout develop -- <file>` で復元。
コード・データへの影響なし。

---

## 8. Risk & 回避策

| リスク | 回避策 |
|--------|--------|
| issue-flow.md の置換漏れ（3箇所のうち一部が残る） | 実装後に `grep -n "GITHUB_COUNT" docs/runbooks/issue-flow.md` で確認 |
| docs/tests/closed/ への上書きで内容が変わる | 移動前に closed 側と open 側のファイル内容が同一であることを確認 |

---

## 9. 承認ポイント

### セキュリティ
- **セキュリティ影響なし**（docs・スキルコメントのみ変更。コード・認証・データへの影響なし）

### 設計判断
| 判断項目 | 根拠 |
|---------|------|
| 修正対象は `issue-flow.md`・`close/SKILL.md`・残留ファイル移動の3点 | イシューに明記されている |
| `issue-flow.md` の旧ロジックを 3 箇所すべて同一の新ロジックに統一 | issue-flow.md の現状から判断（仮定で決めた） |
| `close/SKILL.md` はコメント改善のみ（ロジック変更なし） | イシューに明記されている |
| I039 残留ファイルは上書き移動（closed 側と内容同一のため） | ファイル内容を事前確認する |

- [ ] 変更対象3点（issue-flow.md・close/SKILL.md・残留ファイル移動）
- [ ] issue-flow.md の旧ロジック 3 箇所すべてを新ロジックに統一する方針
- [ ] close/SKILL.md はコメント改善のみ（ロジック変更なし）
- [ ] Danger Ops: なし
- [ ] テスト計画（grep 確認 + 手動目視）
