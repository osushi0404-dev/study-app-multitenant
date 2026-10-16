# 実装レビュー [I074]

## 指摘一覧

| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| HIGH | スコープ | `backend/tmp_test_images/` に `test_1_red.png` 〜 `test_6_purple.png` の 6 件の未追跡バイナリ PNG が存在する。I151（文書更新）の範囲外であり、診断 T1〜T21 のどこにも記載がない。バイナリファイルは一度コミットされると git 履歴に永続残存し除去コストが高い。`git add .` 等で誤ってステージされた場合、I151 PR への混入が起きる。同じく `backend/media/org/personal/subjects/i073-manual/explanation/` (3 件) と `problem/` (4 件) にも未追跡 PNG が存在する（こちらは `media/` が gitignore 対象であれば自然に除外されるが確認は必要）。**コミット前に `backend/tmp_test_images/` の PNG を作業ツリーから除去するか、I151 のコミット手順（パス指定コミット）に明示的な除外確認を加えること。分類: (a) 実行の不備** — 承認済み方針（案1）の文書変更は正しく実装されている。 | 未追跡新規ファイル `backend/tmp_test_images/*.png` / `backend/media/org/personal/subjects/i073-manual/**/*.png` |
| Info | 対応方針との一致 | TC-AUTO-05 の検証内容が `requirements / settings に無い` → `requirements / requirements-dev / settings に無い` に変更されている。診断 T3（TC 一覧への列追加）に明示はないが、実際の判定スクリプトの対象（requirements-dev.txt も検査）を正確に反映する小改善であり、合否基準の厳格化方向で害はない。 | `I151_auto_test.md` TC 一覧 TC-AUTO-05 行 |
| Info | スコープ | `docs/issues/open/I074.md` ほか多数のイシュー・レビュー文書・`docs/proposals/dashboard_improvement_proposal.md` が未追跡で存在する。プロジェクトの「パス指定コミット」慣行に従う限り問題は生じないが、誤ってまとめてステージしないよう留意すること。 | 未追跡新規ファイル多数（`docs/` 配下の他イシュー・レビュー文書） |

---

**追跡変更（git diff）の診断 T1〜T21 との照合結果**（参考）: 5 ファイル（I151.md・I155.md・plan_I151.md・I151_auto_test.md・I151_manual_test.md）のすべての変更が診断で承認された T1〜T21 に対応しており、逸脱・取り残しは検出されなかった。SSOT 化（合格条件列）、TC-AUTO-06/07 の exit 1 統一、TC-AUTO-13 のビルド手順と flaky 判定追加、TC-AUTO-16 の 2 段目コミット内容照合、I155 の連鎖削除範囲更新、§8 の branch protection 一時解除手順、R8（PBKDF2 反復回数）の追記、いずれも方針どおり実装されている。

VERDICT: HIGH
