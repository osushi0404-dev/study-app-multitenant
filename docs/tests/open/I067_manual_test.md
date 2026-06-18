# I067 手動テスト

- **関連計画書**: docs/plans/open/plan_I067.md
- 中心は文書レビュー（完走シナリオ・文言の明確性）。コード/UI なし。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | **完走シナリオ（AC#3）**: 新 `plan-issue/SKILL.md` の自動判定分岐に、I062/I067 の状況（イシューが既に develop へコミット済み）を当てはめて机上トレースする | `git log` 判定が `ISSUE_ALREADY_ON_BASE` を返し、「issue commit スキップ → 計画書 docs コミット → push → `gh pr create`」経路に自動で入り、「No commits between …」エラーに遭遇せず draft PR が作成できる、と文言上たどれる | Claude | OK | `git log` 判定が `ISSUE_ALREADY_ON_BASE` を返すことを実機確認。本 PR #139 自身がこの経路（docs コミット基点）で「No commits」エラーなく作成済み＝実証 |
| 2 | **計画駆動 test の整合確認**: 新 `test/SKILL.md` の「自動テストの選択（計画駆動）」節を読み、本イシューの `I067_auto_test.md`（pytest/Jest/E2E を非該当・TC-01〜08 を正と指定）がその分岐どおりに実行される手順になっているか確認 | auto_test.md が専用テストを指定 → それを正として実行し pytest/Jest/E2E を「非該当」記録、という分岐に当てはまる | Claude | OK | 本 `/test I067` 実行自体が計画駆動経路で TC-01〜08（PASS=8）を正として実行し pytest/Jest/E2E を非該当記録＝分岐どおり動作を実証 |
| 3 | **close 巻き込み防止＋ゲートの机上確認**: 新 `close/SKILL.md` step 3 で、(a) `git add -u` が未追跡バックログ issue を staging しないこと、(b) 万一 I### スコープ外（別 I###.md）が staged された場合に決定論ゲート（`grep -vE "I${ISSUE_NUM}([^0-9]|$)"`）が検出して中断することを、文言・git 仕様から確認 | (a) `git add -u` は追跡済み変更のみ staging するため未追跡バックログ issue は含まれない。(b) スコープ外が staged されればゲートが `exit 1` で中断する。両者で I062/I067 の事故が再発しないと確認できる。番号アンカーで `I0670` 等の誤検知も無いと確認 | Claude | OK | ゲート機能検証: I067のみ=PASS / I068混入=TRIPPED / I0670=TRIPPED（アンカーが別 issue を正しく区別）。`git add -u` は未追跡を構造的に除外 |
| 4 | **デッドリンク/相互参照確認**: 4 スキルへの追記内で言及する他スキル/パス（plan-issue/test/retro/close、`docs/tests/open/$ARGUMENTS_auto_test.md`）が実在し、誤った参照が無いか確認 | 言及パス・スキル名がすべて実在し、リンク切れが無い | Claude | OK | plan-issue/test/retro/close/issue-bootstrap の SKILL.md・docs/tests/open/ をすべて `test -f`/`test -d` で実在確認。リンク切れなし |
| 5 | **文言の明確性レビュー**: 4 スキルの追記文が運用者にとって曖昧でなく、通常時/既コミット時・指定あり/なしの分岐が誤解なく読めるか最終確認 | 追記文の意図が一読で伝わり、誤運用を誘発する曖昧さが無い | Human | | 文章の分かりやすさ（主観）の最終サインオフ |
