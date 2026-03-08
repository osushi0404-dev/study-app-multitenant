# イシューフロー

`docs/runbooks/workflow.md` の「フロー」セクションも合わせて参照してください。

---

## Work Item とは

GitHub Issue 番号を主キーとした成果物の集合体。

```
docs/work/open/{issue}/
  00_issue.md       ← GH Issue 内容のスナップショット
  10_plan.md        ← 計画書（承認ゲート）
  10_plan_2.md      ← 差分計画（NG時、上書き禁止）
  20_test_auto.md   ← 自動テスト
  21_test_manual.md ← 手動テスト
  30_review_{RID}.md ← レビュー記録
  40_error_log.md   ← NG記録（NG時のみ）
  90_closeout.md    ← 完了サマリ（/close 時に作成）
```

---

## フロー図

```
=== フェーズ1: ブートストラップ ===
1. /issue-bootstrap [title | number]
   Mode A（title）: GH Issue 作成 → 番号確定 → docs/work/open/{issue}/ 作成
   Mode B（number）: 既存 GH Issue → docs/work/open/{issue}/ 作成
   → ブランチ: feature/I{issue}-{slug}
   → Draft PR 作成
     ↓
2. ユーザーが 00_issue.md を確認（OK/NG）

=== フェーズ2: 計画・設計 ===
3. /plan {issue}
   → 10_plan.md 作成
   → 20_test_auto.md 作成
   → 21_test_manual.md 作成
   → 30_review_{RID}.md 作成（RID は docs/indices/review_seq.json から採番）
     ↓
4. ユーザーが計画書を確認（OK/NG）
   NG → 修正 → 4 に戻る

=== フェーズ3: 実装・テスト ===
5. /implement {issue}
   → 計画どおり実装
   → 自動テスト実行 → 20_test_auto.md に記録
   → 30_review_{RID}.md に実装サマリ記録
   → commit/push → PR 更新
     ↓
6. ユーザー検証（21_test_manual.md に基づく）
   ┌─ OK → フェーズ4 へ
   └─ NG → /fix-loop {issue}
              → 40_error_log.md に NG 記録
              → 10_plan_N.md（差分計画）作成 → 承認待ち
              → 承認後に修正 → 再テスト → 6 に戻る

=== フェーズ4: クローズ ===
7. /close {issue}
   → 90_closeout.md 作成（完了サマリ）
   → bash scripts/move_work_item.sh {issue}
     （docs/work/open/{issue}/ → docs/work/closed/{issue}/）
   → python3 scripts/build_indices.py
   → PR description 整備
   → commit/push
   → ユーザーへ Approve & Merge 依頼
     ↓
8. GitHub で Approve & Merge
   → GH Issue を Closed にする
```

---

## ブランチ命名規則

- フォーマット: `feature/I{GitHub Issue番号}-{概要を英語化してケバブケース}`
- 例: `feature/I8-docs-work-restructure`
- スラッグ: タイトルをケバブケース英語化、最大 40 文字

---

## RID（レビュー通し番号）採番

```bash
python3 -c "
import json
with open('docs/indices/review_seq.json') as f:
    d = json.load(f)
rid = f\"R{d['next']:05d}\"
d['next'] += 1
with open('docs/indices/review_seq.json', 'w') as f:
    json.dump(d, f, indent=2)
print(rid)
"
```

衝突時（並行ブランチで同じ RID が作られた場合）:
- 後勝ち PR 側でリナンバー + `build_indices.py` 再実行

---

## コミットメッセージ例

```bash
# ブートストラップ
git commit -m "docs: bootstrap work item for issue #{issue}"

# 計画書作成
git commit -m "docs: add plan for issue #{issue}"

# 実装
git commit -m "feat: implement {summary} (#{issue})"

# クローズ
git commit -m "docs: close work item #{issue}"
```

---

## 重要な注意事項

1. **計画書に書いていない実装は禁止** — 必ず提案→承認→計画更新（新規 10_plan_N.md）
2. **差分計画は上書き禁止** — `10_plan_2.md`, `10_plan_3.md` ... と連番で新規作成
3. **クローズ条件** — `90_closeout.md` が完成していること（スクリプトが確認）
4. **旧ディレクトリへの書き込み禁止** — `docs/issues/`, `docs/plans/`, `docs/tests/`, `docs/reviews/` は廃止済み
