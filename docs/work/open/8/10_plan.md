---
github_issue_number: 8
plan_id: plan_I8_docs-work-restructure
created_at: 2026-03-08
status: pending_approval
---

# 計画書 — Issue #8: docs/work ディレクトリ再構成

## 基本情報

- **計画書ID**: plan_I8_docs-work-restructure
- **関連イシュー**: #8
- **作成日**: 2026-03-08

---

## 1. 背景 / 目的

### 現状の問題
- 成果物が `docs/issues/`, `docs/plans/`, `docs/tests/`, `docs/reviews/` に分散
- ローカル採番（`I001`）と GitHub Issue番号が一致せず主キーが曖昧
- 状態遷移（open→closed）でファイルごとに移動が必要 → 移動漏れが起きやすい
- `issue-bootstrap` がローカル採番を生成してから GH Issue を作成する（順序が逆）

### 目的
- GitHub Issue番号を主キーに統一し「1 Issue = 1 フォルダ」に集約
- スキルの `issue-bootstrap` を「GH Issue先行 or 番号指定」の2モードに変更
- 状態遷移をフォルダ移動のみに単純化（`open/` → `closed/`）

---

## 2. 受け入れ条件

- [ ] `docs/work/{open|closed}/{issue}/` が成果物の唯一のルートである
- [ ] `/issue-bootstrap [title]`（Mode A）が GH Issue を先に作成し、番号をキーにフォルダを作る
- [ ] `/issue-bootstrap {number}`（Mode B）が既存 GH Issue のフォルダをローカルに作る
- [ ] `/plan` が `docs/work/open/{issue}/` 配下に成果物を生成する
- [ ] `/implement`, `/fix-loop`, `/close` が新パスを読み書きする
- [ ] `/close` が `docs/work/open/{issue}/` → `docs/work/closed/{issue}/` にフォルダを移動できる
- [ ] CI（plan-gate）が `docs/work/**/10_plan.md` の存在を確認する
- [ ] `docs/indices/WORK_INDEX.md` と `REVIEW_INDEX.md` が `build_indices.py` で生成される
- [ ] 旧ディレクトリ（`docs/issues/`, `docs/plans/`, `docs/tests/`, `docs/reviews/`）に DEPRECATED 表記が付く
- [ ] `CLAUDE.md` と `docs/runbooks/` の記述が新構成と矛盾しない

---

## 3. 影響範囲

| 区分 | 変更対象 |
|------|---------|
| 新規ディレクトリ | `docs/work/`, `docs/indices/` |
| 新規ファイル | テンプレ 7 種、索引 3 種、スクリプト 2 種 |
| 更新ファイル | skills 5 種、CI 1 種、runbooks 3 種、CLAUDE.md |
| 廃止（read-only化） | `docs/issues/`, `docs/plans/`, `docs/tests/`, `docs/reviews/` |
| アプリコード | **なし**（バックエンド・フロントエンドへの変更なし） |

---

## 4. 変更点一覧

### 4.1 新規作成

#### ディレクトリ（.gitkeep で確保）
```
docs/work/open/          # 作業中 Work Item
docs/work/closed/        # 完了 Work Item
docs/work/templates/     # テンプレ集約
docs/indices/            # 索引
```

#### テンプレ（`docs/work/templates/`）
| ファイル | 内容 |
|---------|------|
| `00_issue.md` | GH Issue 内容の固定化スナップショット |
| `10_plan.md` | 計画書（承認ゲート） |
| `20_test_auto.md` | 自動テスト（コマンド・期待結果・記録） |
| `21_test_manual.md` | 手動テスト（手順・期待結果・実施記録） |
| `30_review.md` | レビュー記録（RID必須） |
| `40_error_log.md` | NG記録（NG時のみ作成） |
| `90_closeout.md` | 完了サマリ（/close 時に作成） |

#### 索引（`docs/indices/`）
| ファイル | 内容 |
|---------|------|
| `WORK_INDEX.md` | 全 Work Item の一覧（スクリプト生成） |
| `REVIEW_INDEX.md` | 全レビューの一覧（スクリプト生成） |
| `review_seq.json` | RID 採番カウンタ（初期値: `{"next": 1}`） |

#### スクリプト（`scripts/`）
| ファイル | 機能 |
|---------|------|
| `build_indices.py` | `docs/work/` をスキャンして WORK_INDEX・REVIEW_INDEX を再生成 |
| `move_work_item.sh` | `docs/work/open/{issue}/` → `docs/work/closed/{issue}/` へ移動 |

---

### 4.2 スキル更新（`.claude/skills/`）

#### `/issue-bootstrap`（大幅改修）

**引数による2モード切り替え:**

```
引数が数字のみ → Mode B（既存 GH Issue のローカル化）
引数がテキスト  → Mode A（新規 GH Issue 作成）
```

**Mode A フロー:**
1. `gh issue create --title "[title]" --body "..."` で GH Issue 作成
2. 返ってきた番号 `$ISSUE_NUM` を主キーとして使用
3. `docs/work/open/$ISSUE_NUM/00_issue.md` 作成（GH Issue 内容をスナップショット）
4. ブランチ作成: `git checkout -b feature/I${ISSUE_NUM}-[slug]`
5. コミット・プッシュ
6. Draft PR 作成

**Mode B フロー:**
1. `gh issue view $ARGUMENTS --json number,title,body` で既存 GH Issue を取得
2. `docs/work/open/$ARGUMENTS/00_issue.md` 作成
3. ブランチ作成: `git checkout -b feature/I${ARGUMENTS}-[GHタイトルから自動生成]`
4. コミット・プッシュ
5. Draft PR 作成

**廃止する処理:**
- ローカル採番ロジック（`ls docs/issues/open/*.md | ...`）
- `docs/issues/open/` への書き込み

---

#### `/plan`（パス変更）

```diff
- 必読: docs/issues/open/$ARGUMENTS_*.md
+ 必読: docs/work/open/$ARGUMENTS/00_issue.md

- 生成物:
-   docs/plans/open/$ARGUMENTS_plan.md
-   docs/tests/open/$ARGUMENTS_manual_test.md
-   docs/tests/open/$ARGUMENTS_auto_test.md
-   docs/reviews/open/$ARGUMENTS_review.md
+ 生成物:
+   docs/work/open/$ARGUMENTS/10_plan.md
+   docs/work/open/$ARGUMENTS/20_test_auto.md
+   docs/work/open/$ARGUMENTS/21_test_manual.md
+   docs/work/open/$ARGUMENTS/30_review_{RID}.md
+   # RID は docs/indices/review_seq.json から採番・インクリメント
```

---

#### `/implement`（パス変更）

```diff
- 必読:
-   docs/plans/open/$ARGUMENTS_plan.md
-   docs/tests/open/$ARGUMENTS_auto_test.md
-   docs/tests/open/$ARGUMENTS_manual_test.md
-   docs/reviews/open/$ARGUMENTS_review.md
+ 必読:
+   docs/work/open/$ARGUMENTS/10_plan.md       # 最新 (10_plan_N.md)
+   docs/work/open/$ARGUMENTS/20_test_auto.md
+   docs/work/open/$ARGUMENTS/21_test_manual.md
+   docs/work/open/$ARGUMENTS/30_review_*.md

- 記録先: docs/reviews と docs/tests
+ 記録先: docs/work/open/$ARGUMENTS/ 配下（既存ファイルを更新）
```

---

#### `/fix-loop`（パス変更）

```diff
- 差分計画: docs/plans/open/$ARGUMENTS_plan.md に追記
+ 差分計画: docs/work/open/$ARGUMENTS/10_plan_2.md を新規作成（上書き禁止）
+            （3回目以降は 10_plan_3.md …）
+ NG記録:   docs/work/open/$ARGUMENTS/40_error_log.md を作成/追記
```

---

#### `/close`（パス変更 + フォルダ移動）

```diff
- docs/*/open の対象 I### ファイルを closed へ移動
+ 1) docs/work/open/$ARGUMENTS/90_closeout.md を作成（完了サマリ）
+ 2) git mv docs/work/open/$ARGUMENTS docs/work/closed/$ARGUMENTS
+ 3) scripts/build_indices.py を実行して索引を再生成
+ 4) コミット・プッシュ → PR 更新
+ 5) Approve & Merge を依頼
```

---

### 4.3 CI 更新（`.github/workflows/plan-gate.yml`）

```diff
- const isPlanDoc = (p) => p.startsWith("docs/plans/open/") || p.startsWith("docs/plans/closed/");
+ const isPlanDoc = (p) => /^docs\/work\/(open|closed)\/\d+\/10_plan/.test(p);
```

（旧パスの確認を廃止し、新パスのみをチェック）

---

### 4.4 runbooks 更新

| ファイル | 変更内容 |
|---------|---------|
| `docs/runbooks/workflow.md` | 成果物パスを `docs/work/` に更新 |
| `docs/runbooks/issue-flow.md` | bootstrap フロー・ファイルパスを更新 |
| `docs/runbooks/plan-writing-rules.md` | 計画書パスを `docs/work/open/{issue}/10_plan.md` に更新 |

---

### 4.5 CLAUDE.md 更新

`docs/runbooks/template-sync.md` の参照先と、スキル説明内のパス例を新構成に合わせて更新。

---

### 4.6 旧ディレクトリの廃止（read-only化）

各旧ディレクトリに `DEPRECATED.md` を追加:
```
docs/issues/DEPRECATED.md
docs/plans/DEPRECATED.md
docs/tests/DEPRECATED.md
docs/reviews/DEPRECATED.md
```

内容:
```
このディレクトリは廃止されました。
成果物は docs/work/{open|closed}/{issue_number}/ に移行しています。
新規ファイルの作成・更新は禁止です。
```

既存のテンプレートファイルは `docs/work/templates/` に移管し、旧ディレクトリから削除。

---

## 5. 実装手順（順序厳守）

```
Step 1: docs/work/ ディレクトリ作成（open/, closed/, templates/）
Step 2: docs/indices/ 作成（review_seq.json, WORK_INDEX.md, REVIEW_INDEX.md の雛形）
Step 3: docs/work/templates/ にテンプレ 7 種を作成
Step 4: scripts/build_indices.py 作成
Step 5: scripts/move_work_item.sh 作成
Step 6: 旧テンプレを docs/work/templates/ へ移管 → 旧 templates/ フォルダを削除
Step 7: 旧ディレクトリに DEPRECATED.md を追加
Step 8: .claude/skills/ の 5 つの SKILL.md を更新
Step 9: .github/workflows/plan-gate.yml を更新
Step 10: docs/runbooks/ 3 ファイルを更新
Step 11: CLAUDE.md を更新
Step 12: scripts/build_indices.py を実行して初期索引生成
Step 13: 全変更をコミット・プッシュ
```

---

## 6. ロールバック

このイシューはアプリコードを変更しないため、影響範囲はドキュメントとツール設定のみ。

```bash
# PR をクローズ / ブランチを削除するだけでロールバック完了
git checkout develop
git branch -d feature/I8-docs-work-restructure
```

旧ディレクトリは削除せず read-only 化するだけなので、merge 前のロールバックは完全。

---

## 7. Risk & 回避策

| リスク | 回避策 |
|--------|--------|
| スキル更新漏れで旧パスを参照し続ける | Step 8 完了後に全 SKILL.md を grep して旧パス（`docs/plans/`, `docs/issues/`）が残っていないことを確認 |
| CI の `isPlanDoc` 更新漏れで plan-gate が通らない | Step 9 で更新後、本 PR 自体で CI が通ることを確認（本 PR は docs のみなので plan-gate 対象外だが、正規表現は手動レビューで確認） |
| RID 衝突（並行ブランチ） | 後勝ち PR 側でリナンバー + `build_indices.py` 再実行 |
| `review_seq.json` の不整合 | `build_indices.py` が `docs/work/` をスキャンして自動修正できるように設計 |

---

## 8. 承認ポイント

```
📋 計画書を作成しました: docs/work/open/8/10_plan.md

⏸️ 承認待ち中: 実際の修正作業は開始しません
✅ 承認いただけましたら「OK」または「承認」とお答えください
❌ 修正が必要でしたら具体的な指示をお願いします
```

### 承認チェックリスト

- [ ] 2モード（Mode A / Mode B）の issue-bootstrap 設計に同意
- [ ] `open / closed` の2状態管理（in_progress なし）に同意
- [ ] `docs/indices/` の索引方式（スクリプト自動生成）に同意
- [ ] 旧ディレクトリを削除せず DEPRECATED 化する方針に同意
- [ ] 実装順序（Step 1〜13）に問題なし
