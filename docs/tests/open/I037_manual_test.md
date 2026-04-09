# I037 手動テスト計画書

## 基本情報
- **関連イシュー**: I037
- **関連計画書**: plan_I037_issue-bootstrap軽量化とplan-issueへのブランチ管理移行.md
- **作成日**: 2026-04-09

---

## 手動テストケース

| # | 確認内容 | 操作手順 | 期待結果 | 結果(OK/NG) |
|---|---------|---------|---------|------------|
| MT-1 | `/issue-bootstrap` 実行後にブランチが変わらない | 任意のブランチで `/issue-bootstrap テストイシュー` を実行 | 実行前後で `git branch --show-current` の出力が変わらない | |
| MT-2 | `/issue-bootstrap` 実行後のイシューファイルに GitHub Issue 番号が記録されている | MT-1 で作成したイシューファイルを開く | `## 関連資料` に `GitHub Issue: #XX` が記載されている | |
| MT-3 | `/issue-bootstrap` 実行後にブランチが存在しない | MT-1 実行後に `git branch -a` を確認 | MT-1 で作成したイシュー番号のブランチが存在しない | |
| MT-4 | `/plan-issue` 実行後に develop ベースのフィーチャーブランチが作成される | MT-1 のイシューに対して `/plan-issue I###` を実行 | `feature/I###-...` ブランチが作成されている | |
| MT-5 | `/plan-issue` 実行後にイシューファイルがコミット済み | MT-4 実行後に `git log --oneline -3` を確認 | `docs: create issue I###` のコミットが存在する | |
| MT-6 | `/plan-issue` 実行後に Draft PR が作成されている | MT-4 実行後に `gh pr list --state open` または GitHub を確認 | 対象イシューの Draft PR が存在する | |
| MT-7 | `CLAUDE.md` にスキル一覧が記載されていない | `CLAUDE.md` の `## 2. 使うスキル` セクションを確認 | スキル一覧ではなく `workflow.md` への参照1行のみ | |
| MT-8 | `workflow.md` に全スキル一覧が記載されている | `docs/runbooks/workflow.md` の `## 使うスキル` セクションを確認 | 全スキル（/issue-bootstrap〜/close）が一覧されており、`/issue-bootstrap` と `/plan-issue` の説明が新しい責務を反映している | |

---

## テスト結果

| # | 結果 | 確認日 | 備考 |
|---|------|--------|------|
| MT-1 | 保留 | — | develop マージ後・I038 着手時に確認 |
| MT-2 | 保留 | — | develop マージ後・I038 着手時に確認 |
| MT-3 | 保留 | — | develop マージ後・I038 着手時に確認 |
| MT-4 | 保留 | — | develop マージ後・I038 着手時に確認 |
| MT-5 | 保留 | — | develop マージ後・I038 着手時に確認 |
| MT-6 | 保留 | — | develop マージ後・I038 着手時に確認 |
| MT-7 | OK | 2026-04-09 | `CLAUDE.md` は参照1行のみ ✓ |
| MT-8 | OK | 2026-04-09 | `workflow.md` に全9スキル一覧・新しい責務の説明 ✓ |
