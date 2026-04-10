# I032 計画書: GitHub Branch protection rules 設定手順書の作成と適用

## 基本情報
- **計画書ID**: plan_I032
- **関連イシュー**: #73
- **作成根拠資料**: docs/proposals/I026_ai_dev_improvement_proposal.md（改善案 I）
- **実装後評価**: （未作成）
- **作成日**: 2026-04-10

---

## 1. 背景/目的

現状、直 push のブロックは `.claude/settings.json` の deny ルールと `pretooluse_guard.py` のみで行っており、
Claude Code 経由の操作のみが対象。GitHub Web UI・他のツール経由の push は防止できていない。

Branch protection rules を設定することで：
- GitHub 側でも物理的に直 push をブロックできる二重ガードになる
- CI が通らない状態でのマージを GitHub が拒否できる
- 管理者（自分）も迂回できない強制ゲートになる

---

## 2. 受け入れ条件

- [ ] `docs/runbooks/branch-protection-setup.md` が作成されている
- [ ] ユーザーが手順書に従って `develop` に Branch protection rules を適用している
- [ ] ユーザーが手順書に従って `main` に Branch protection rules を適用している
- [ ] `develop` への直 push が GitHub 側でもブロックされることを確認している
- [ ] `main` への直 push が GitHub 側でもブロックされることを確認している
- [ ] CI が通らない PR は `develop`・`main` へのマージが GitHub 側でブロックされることを確認している

---

## 3. 影響範囲

- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: GitHub リポジトリ Settings（ユーザーが GUI 操作）、`docs/runbooks/` にドキュメント追加

---

## 4. 変更点一覧

### 4-A: `docs/runbooks/branch-protection-setup.md`（新規作成）

以下の内容を含む手順書を作成する：

1. **設定値一覧**（develop / main の違いを表形式で明示）
2. **GitHub Settings 操作手順**（スクリーンショット不要・文字説明でステップ列挙）
3. **CI 必須チェックの登録方法**（status checks の名前を明示）
4. **動作確認手順**（直 push / CI 失敗 PR のブロック確認方法）
5. **ロールバック方法**（設定を削除・緩和する手順）

#### 設定値（計画）

| 設定項目 | develop | main |
|---------|---------|------|
| Require a pull request before merging | ON | ON |
| Required number of approvals | 0 | **1** |
| Dismiss stale reviews when new commits are pushed | OFF | ON |
| Require status checks to pass before merging | ON | ON |
| Require branches to be up to date | ON | ON |
| Required status checks（5件） | 全5ジョブ | 全5ジョブ |
| Do not allow bypassing the above settings | ON | ON |
| Allow force pushes | OFF | OFF |
| Allow deletions | OFF | OFF |

#### CI 必須チェックの名前（ci.yml の `name:` フィールド）

```
Backend Lint & Security
Backend Tests
Frontend Type Check
Frontend Lint & Security
Frontend Tests
```

**注意**: status checks の名前は GitHub Actions の `jobs.<job_id>.name` の値。
CI が一度も実行されていないと候補に表示されないため、PR を1件通してから登録する。

---

## 5. 実装手順（ステップ）

1. `docs/runbooks/branch-protection-setup.md` を作成する
2. コミット・プッシュして Draft PR を更新する
3. ユーザーが手順書を読み、GitHub Settings で `develop` の設定を適用する
4. ユーザーが手順書を読み、GitHub Settings で `main` の設定を適用する
5. ユーザーが動作確認（直 push ブロック・CI 失敗 PR のマージブロック）を実施する

---

## 6. テスト計画

### 自動
- 対象が GitHub Settings（GUI操作）のため自動テストなし
- `docs/runbooks/branch-protection-setup.md` の存在確認のみ：
  ```bash
  ls docs/runbooks/branch-protection-setup.md
  ```

### 手動
- `develop` への直 push が拒否されることを確認
- `main` への直 push が拒否されることを確認
- CI 失敗状態の PR が `develop`・`main` にマージできないことを確認
- `main` への PR で 1 approval なしにマージできないことを確認

---

## 7. ロールバック

GitHub Settings > Branches > Branch protection rules で対象ブランチのルールを削除する。
コード・データへの影響なし。即時復元可能。

---

## 8. Risk & 回避策

| リスク | 回避策 |
|--------|--------|
| 設定後に既存の Draft PR がマージできなくなる | Draft PR はそもそもマージ不可のため影響なし |
| main への PR で自分が approve できない（solo） | GitHub はセルフ approve が可能（デフォルト許可） |
| CI の status checks 名が見つからない | PR を1件通してから登録する（手順書に明記） |
| Require branches to be up to date で PR 更新が増える | 想定内の運用コスト。安全性を優先 |

---

## 9. 承認ポイント

### セキュリティ
- **セキュリティ影響なし**（GitHub Settings 変更のみ。コード・データへの影響なし）
- むしろ設定後はセキュリティが向上（直 push ブロック・CI 強制の二重化）

### 設計判断
| 判断項目 | 根拠 |
|---------|------|
| develop: Required approvals = 0 | ソロプロジェクト前提（イシューに明記） |
| main: Required approvals = 1 | セキュリティ・BP 観点からユーザー承認済み |
| Dismiss stale reviews: main のみ ON | main は最新コードでの承認を保証するため |
| 全5 CI ジョブを必須チェックに登録 | ci.yml の全ジョブを対象（イシューに明記） |
| Allow force pushes: OFF（両ブランチ） | 監査証跡保持・コミット偽造防止のため |

- [ ] 変更対象: `docs/runbooks/branch-protection-setup.md`（新規作成）のみ
- [ ] 設定値（develop: approvals=0 / main: approvals=1）
- [ ] 必須 CI チェック: 全5ジョブ（Backend Lint & Security / Backend Tests / Frontend Type Check / Frontend Lint & Security / Frontend Tests）
- [ ] Do not allow bypassing: ON（管理者も対象）
- [ ] Danger Ops: なし
- [ ] テスト計画（手動: 直 push ブロック・CI 失敗 PR ブロック確認）
