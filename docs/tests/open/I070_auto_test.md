# I070 自動テスト（機械検証）

- **関連イシュー**: #144
- **計画書**: docs/plans/open/plan_I070.md
- 文書配線イシューのため、各追加内容を `grep` / `test -e` で決定論的に検証する。`/test` で Claude が全件実行し結果を記入する。

| TC | 目的 / 対応AC | 検証コマンド | 期待結果 | 結果 |
|----|--------------|-------------|----------|------|
| TC-A1 | 設計思想文書が版管理下にある（前提・ステップ1） | `git ls-files --error-unmatch docs/proposals/learning_app_quality_criteria.md` | 終了コード 0（tracked）。ファイル実在（`test -f` も 0） | 未 |
| TC-A2 | CLAUDE.md §0 に設計思想文書リンク（AC1） | `grep -q "プロダクト品質基準" CLAUDE.md && grep -q "docs/proposals/learning_app_quality_criteria.md" CLAUDE.md` | 双方ヒット（終了コード 0）。リンク先は TC-A1 で実在確認済み | 未 |
| TC-A3a | plan-writing-rules に §14・§15（AC2） | `grep -qE "^14\) 学習効果設計" docs/runbooks/plan-writing-rules.md && grep -qE "^15\) プライバシー" docs/runbooks/plan-writing-rules.md` | 双方ヒット（終了コード 0） | 未 |
| TC-A3b | §14/§15 が §10-13 と同粒度＝「該当する場合のみ」条件付き（AC2・I068 P1 パリティ） | `grep -E "^1[45]\)" docs/runbooks/plan-writing-rules.md` | 各行に「〜がある場合のみ」相当の条件文が含まれる（番号＋タイトル＋条件の形式が §10-13 と一致） | 未 |
| TC-A3c | §14/§15 が C1/C2 を参照（配線） | `grep -A6 "^14\)" docs/runbooks/plan-writing-rules.md | grep -q "C1"; grep -A6 "^15\)" docs/runbooks/plan-writing-rules.md | grep -q "C2"` | §14 が C1、§15 が C2 を参照 | 未 |
| TC-A4 | review-rules に両文書への参照（AC3） | `grep -q "learning_app_quality_criteria.md" docs/runbooks/review-rules.md && grep -q "review_perspective_framework.md" docs/runbooks/review-rules.md` | 双方ヒット（終了コード 0） | 未 |
| TC-A5a | review_perspective_framework に逆参照セクション §8（AC4） | `grep -qE "^## 8\." docs/proposals/review_perspective_framework.md && grep -q "learning_app_quality_criteria.md" docs/proposals/review_perspective_framework.md` | §8 見出しと設計思想文書への参照が存在 | 未 |
| TC-A5b | §8 の対応表が §6 の 4 行と整合（AC4） | `F=docs/proposals/review_perspective_framework.md; grep -q "C4 マルチテナント ↔ P1" $F && grep -q "C8 セキュリティ ↔ P2" $F && grep -q "C7 フェールセーフ" $F && grep -q "C3 アクセシビリティ ↔ P6" $F`（§6 = learning_app_quality_criteria.md L129-132 の4行と同一文言） | 4 対応すべて一致（過不足なし・終了コード 0） | 未 |
| TC-A5c | C2↔P9（I071予定）・C1観点なしの明記（AC4） | `F=docs/proposals/review_perspective_framework.md; grep -q "C2" $F && grep -q "P9" $F && grep -q "I071" $F && grep -q "C1" $F && grep -qE "観点なし\|意図的" $F` | C2↔P9（I071で追加予定）と C1 意図的に観点なしの双方が明記（終了コード 0） | 未 |
| TC-A5d | C5/C6 が §8 に意図的省略と明記（Info 反映・読者フレンドリー） | `grep -q "C5" docs/proposals/review_perspective_framework.md && grep -q "C6" docs/proposals/review_perspective_framework.md`（§8 の C5/C6 省略理由 Note 内） | §8 に「C5・C6 は §6 に一対一対応がなく省略（意図的）」旨の Note がある | 未 |
| TC-A6a | issue_template に「## 関連する品質基準」（AC5） | `grep -qx "## 関連する品質基準" docs/issues/templates/issue_template.md` | 見出しが存在（終了コード 0） | 未 |
| TC-A6b | issue_template が儀式化していない＝チェックボックス列でない（AC5・AC6） | 「## 関連する品質基準」セクション本文に `- [ ]` 形式のチェックボックスが含まれない。代わりに「該当なし」「すべて埋める必要はない」等の文言を含む | チェックボックス 0 個・形骸化防止文言あり | 未 |
| TC-A7a | 形骸化防止文言（AC6） | §14・§15 が「該当する場合のみ含める／該当しない場合は記載不要」の前提文（plan-writing-rules L27-30）配下にあり、issue_template セクションに「該当なし」可の文言がある | 全追加セクションに「該当する場合のみ」または「該当なし可」相当が存在 | 未 |
| TC-A7b | memo↔body 決定論ゲート（I068 P3） | `bash scripts/claude/check-memo-body-paths.sh I070` | 終了コード 0（不一致なし／検証対象なし） | 未 |
| TC-A7c | 参照先実在性 全件（デッドリンクなし） | 追加した全リンクパスを `test -e` で全件検証 | 全パス実在（MISS 0 件） | 未 |

## 実行記録
- 実行日: （未実施）
- PASS / FAIL 件数: -
