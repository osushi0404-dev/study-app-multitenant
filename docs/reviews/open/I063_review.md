# I063 実装レビュー

- **関連イシュー**: #129
- **計画書**: docs/plans/open/plan_I063.md
- **自動テスト**: docs/tests/open/I063_auto_test.md
- **手動テスト**: docs/tests/open/I063_manual_test.md

## レビュー対象（実装後に評価する）
- `.claude/skills/implement/SKILL.md`（手順3〜4間の git diff 反映検証＋ハード STOP）
- `docs/runbooks/plan-writing-rules.md`「計画書作成前の事前調査（必須）」（参照先実在性の全件機械検証＝item2/C1検証手順、規約是正時の消費箇所全件列挙＝P1 do層）
- `.claude/skills/grill-me/SKILL.md`（必須確認のツール実行・全件確定＝item3、手順4の本文整合更新＝item4、手順4末尾の `gh issue edit` 同期＝item5）
- `docs/runbooks/review-rules.md`（`:110` デッドリンク削除＝C1 同梱）

## 観点（実装後にチェック）
- [ ] 受け入れ条件 10 項目（plan_I063 セクション2）をすべて満たすか
- [ ] item1: 完了案内**前**に検証が入り、未反映時は**完了案内を出さず停止**する手順になっているか（後置きで案内後に検証する誤りがないか）
- [ ] item1: `git diff origin/develop...HEAD --name-only`（3点ドット）で記載され、既存の手順番号（1〜4）と他スキルからの参照が壊れていないか（3.5 挿入で番号維持）
- [ ] item2: 参照実在性検証が `plan-writing-rules.md`「事前調査（必須）」に置かれ、`plan-issue/SKILL.md` には**入れていない**か（Q3 棲み分け維持）
- [ ] item2/C1: 検証対象に「既存デッドリンクも含む」ことが明記されているか
- [ ] P1 do層: 「宣言箇所だけでなく消費箇所（グロブ・ループ・相互参照・スクリプト）」の語が含まれ、宣言箇所のみで完了する誤読を防いでいるか
- [ ] item3: 「概算でなく実行して全件分類・確定」が観点として明記されているか
- [ ] item4: 整合更新の対象に「解決方針・スコープ・実装対象・受け入れ条件」が列挙されているか
- [ ] item5: `gh` 不可環境の **skip（非ブロック・警告のみ）** 分岐が明記されているか
- [ ] （W1）item5 が `gh issue edit --body-file`（`--body "$(cat)"` ではない）で記述されているか
- [ ] （W2）item3 が「実行省略不可」を明示し、grill-me「必須確認」冒頭の「質問を省略してよい」前置きに巻き込まれていないか
- [ ] C1: `review-rules.md` から `docs/reviews/README.md` 参照が消え、運用情報の欠落がないか（本体は review-rules.md 自身に存在）
- [ ] 追加文言が `I060`/`I061` 等の固有技術名に依存しない一般化表現か
- [ ] 計画書に記載のないファイル変更がないか（4ファイル限定）
- [ ] grep 存在確認 TC-01〜09 と振る舞いスモーク TC-S1/S2 が PASS か

## レビュー結果
- **計画レビュー** (`/plan-issue-review I063`): ✅ 完了（`VERDICT: OK` / 高リスク No）。`docs/reviews/I063_plan_review_20260617_1702.md`。Warning×2（W1: `gh issue edit --body-file` 採用 / W2: item3「実行省略不可」明示）・Info×1（git diff は未 push を検出しない＝Q1 設計確定で変更不要）。W1/W2 を計画書・auto_test・本レビュー観点に反映済み。
- **コードレビュー** (`/code-review I063`): （未実施）
- **自動テスト** (`/test I063`): （未実施。プロトタイプは TC-S1/S2 で 2026-06-17 PASS 済み）
- **手動テスト**: （未実施。grill-me 実走の観察記録は Human 判断）

## メモ
- 影響範囲は Backend/Frontend/DB なし（ワークフロー定義ドキュメントのみ）。セキュリティ影響なし。
- スコープは 2026-06-17 にユーザー確認の上 7 項目で確定（追加検討の P1 do層 / C1 同梱を統合）。
