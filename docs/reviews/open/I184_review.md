# I184 レビュー: I179 のワークツリー運用を既存の環境に適用する

## 基本情報
- **関連イシュー**: #312（docs/issues/open/I184.md）
- **計画書**: docs/plans/open/plan_I184.md
- **Draft PR**: #313
- **テスト文書**: docs/tests/open/I184_auto_test.md・docs/tests/open/I184_manual_test.md

## レビュー対象
| 計画 | 対象 | 内容 |
|------|------|------|
| 4-1 | primary `refs/remotes/origin/HEAD` | `origin/develop` に合わせる |
| 4-2 | harness-1・harness-2 | 公式 `claude --worktree` で作成 |
| 4-3 | primary の `docs/issues/open/`・`docs/reviews/` | wt-harness から 37 件をコピー（未コミット） |
| 4-4〜4-7 | wt-harness・Docker volume 4 つ・I181 ブランチ | バックアップ → 削除（危険操作）→ 撤去 |
| 4-8 | ラベル `track:harness`・`track:app` | 説明文からワークツリー名を外す |
| 4-11 | ラベル `danger-approved`（新規）・PR #313 | 危険操作の承認の印として作成・付与 |
| 4-9・4-10 | `docs/runbooks/worktree.md` | §7 反映のタイミング・§11 手順 4 の注意・手順の不足の修正 |

## コピーの一覧（ステップ 3 で記入）
<!-- copied-begin -->
<!-- copied-end -->

| コピーしなかったもの | 理由 |
|--------------------|------|
| （ステップ 3 で記入） | |

## 危険操作の承認（ステップ 4 で記入）
- 未実施

## 手順の不足（ステップ 6 で記入）
- 未実施
