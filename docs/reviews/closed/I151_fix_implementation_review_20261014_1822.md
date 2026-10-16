# 実装レビュー [I074]

## 指摘一覧

| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| HIGH | 前回NG指摘の未解消（fail-closed）**(a) 実行の不備** | `backend/tmp_test_images/` に `test_1_red.png`〜`test_6_purple.png` の 6 件が依然として存在する。前回レビューで「I151 doc-only スコープ外の未追跡バイナリが誤って staging されると PR を汚染するリスク」として HIGH 判定した指摘。diff に削除・`.gitignore` 追記・説明のいずれも現れていない。承認済み方針（T1〜T21）は doc 更新のみであり、アプローチ自体の誤りではなく **この cleanup を実行し忘れた実行の不備**。 | `backend/tmp_test_images/test_{1..6}_*.png` |
| Info | スコープ整合 | T1〜T21 の doc 変更（SSOT化・TC-AUTO-13 rewrite・TC-AUTO-16 拡張・I155 スコープ拡大・§8 branch protection 手順追加・R5/R8 訂正）は診断メモの方針と一致しており、スコープ逸脱・回帰懸念なし。 | docs/tests/closed/I151_auto_test.md ほか4ファイル |
| Info | `backend/media/` 未追跡 PNG | `backend/media/org/personal/subjects/i073-manual/` 配下の 7 件は `.gitignore` で除外されていれば PR 汚染リスクは低いが、念のため `git check-ignore` で確認推奨。前回指摘の「高リスク」対象外のため今回は Info 扱い。 | `backend/media/org/personal/subjects/i073-manual/*.png` |

---

**解消手順（HIGH）**: `backend/tmp_test_images/` を `.gitignore` に追記するか、ディレクトリごと削除する（I151 スコープで生成されたファイルでなければ削除が根治）。staging 前に `git status` で追跡されていないことを確認してから再レビューへ進むこと。

VERDICT: HIGH
