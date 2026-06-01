# 手動テスト: I059 イシューファイルの自己完結度向上（テンプレート＋issue-review サブエージェント）

## テスト方針

テンプレート・サブエージェント指示・スキルの Markdown 変更、および `claude -p` を伴う issue-review の実起動を確認する。
Read・Bash で判定できる項目は Claude が実行する。コンテキストクリア後の実セッション `/plan-issue` 入域のみ Human が実施する。

実施日: 2026-06-01（/test 実行）

---

## テストケース

| No | 確認対象 | 確認手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|----------|----------|----------|--------|--------|------|
| 1 | テンプレート 背景/目的の3サブセクション（AC#1） | `docs/issues/templates/issue_template.md` を読む | `## 背景/目的` 配下に `### 現状の問題（証拠・再現手順）`・`### 根本原因`・`### 解決方針` が存在する | Claude | ✅ PASS | grep 3サブセクション一致 |
| 2 | テンプレート 実装対象テーブル（AC#2） | 同ファイルを読む | `## 実装対象（既知のもの）` テーブルが `## スコープ` の**直前**に存在する | Claude | ✅ PASS | 実装対象=L17 < スコープ=L22 |
| 3 | テンプレート 制約・引き継ぎ情報（AC#3） | 同ファイルを読む | `## 制約・引き継ぎ情報` が `## 影響範囲（想定）` の**直後**に存在する。既存セクションの順序・名称が崩れていない（`## 関連資料` が先頭維持＝grill-me 設計確認メモ挿入位置と非競合） | Claude | ✅ PASS | 影響範囲=L31<制約=L37<Danger=L40。関連資料が先頭 |
| 4 | issue-reviewer.md の新設と安全要件（AC#4） | `.claude/review-agents/issue-reviewer.md` を読む | (1) インジェクション対策ヘッダ (2) Read/Grep/Glob のみの読み取り専用 (3) 第三者レビュアー＋自己完結度＋内容妥当性観点 (4) 判定は助言で起票をブロックしない旨 | Claude | ✅ PASS | (1)(2)(3)(4) すべて確認。stdin 言及（code-review Low対応）も確認 |
| 5 | issue-review.sh の新設と非ブロック設計（AC#4） | `scripts/claude/issue-review.sh` を読む | (1) `claude -p --model claude-sonnet-4-6 --tools "Read,Grep,Glob"` (2) `docs/reviews/${ISSUE}_issue_review_*.md` に保存 (3) ファイル未検出・claude -p 失敗・空応答で `exit 0` (4) PR コメントなし | Claude | ✅ PASS | exit 0 が4箇所（reviewer未検出/イシュー未検出/claude失敗/空応答）。PRコメントなし確認 |
| 6 | issue-review.sh の実起動（AC#4） | `bash scripts/claude/issue-review.sh I059` を実行 | issue-reviewer による第三者レビューが生成・保存される。非ゼロ終了しない | Claude | ✅ PASS | I059 を「判定:十分／grill-me スキップ可」と判定、exit 0。生成物は使い捨てのため削除済み |
| 7 | issue-bootstrap の 3.5 起動追加（AC#5） | `.claude/skills/issue-bootstrap/SKILL.md` を読む | step 3 と step 4 の間に「3.5 自己完結度レビュー」があり `bash scripts/claude/issue-review.sh "I${ISSUE_NUM}"` を起動。ソフト警告（非ブロック）明記 | Claude | ✅ PASS | step 3.5 追加・ソフト明記確認 |
| 8 | 完了ガイドの動的分岐（AC#6・Q2=a） | 同ファイルの step 6 を読む | (A) 要補足/プレースホルダ残→`/grill-me` 推奨、(B) 十分→`/grill-me` スキップして `/plan-issue` 直行可、の両分岐 | Claude | ✅ PASS | A/B分岐＋skip明記確認 |
| 9 | 検証用イシュー作成→自己完結確認→後始末（AC#7・Q3） | 改訂テンプレートで検証用イシュー I061 を作成し自己完結に記入。issue-review が「十分」判定を返し、ファイル単体で `/plan-issue` 着手に必要な情報が揃うことを確認。GitHub 登録（Q3=a）後、ローカル削除＋GitHub クローズ | Claude | ✅ PASS | 記入前=要補足（プレースホルダ全検出・A分岐実証）／記入後=十分（B分岐・grill-me スキップ推奨）。GitHub #124 作成→CLOSED、ローカル I061 削除済み（未コミットのため番号も未消費） |
| 10 | コンテキストクリア後の `/plan-issue` 実セッション入域（AC#7） | 新規セッション（コンテキストクリア）で検証用イシューに対し `/plan-issue` を実行 | 不足情報を問い返すことなく計画書作成に着手できる | Human | ⏳ 任意 | TC9 で**ゼロ文脈のサブエージェント**が「十分」判定済み＝代理検証は充足。実セッションでの最終確認は任意 |
| 11 | issue-review.sh の非ブロック失敗動作（plan-review Warning 反映） | 失敗する `claude` スタブを PATH 先頭に置く等で再現し `bash scripts/claude/issue-review.sh I059` | 警告を出し**終了コード 0**。bootstrap を止めない | Claude | ✅ PASS | implement 時確認。(a) claude失敗→exit0／(b) reviewer未検出→exit0／(c) イシュー未検出(I999)→exit0 |
| 12 | issue-bootstrap フロントマター description 更新（plan-review Warning 反映） | `.claude/skills/issue-bootstrap/SKILL.md` のフロントマターを読む | `description` が issue-review 起動を含む実態に更新されている | Claude | ✅ PASS | "...run issue-review (self-completeness), then register GitHub Issue." 確認 |

---

## 自動テスト（`I059_auto_test.md`）結果
- AT1 shellcheck（pre-commit 経由）: ✅ PASS
- AT2 `bash -n`: ✅ PASS

## CI（PR #123）
- Backend Lint & Security / Backend Tests / Frontend Lint & Security / Frontend Tests / Frontend Type Check: ✅ pass
- E2E Tests (Playwright): /test 実行時点では最新 push 分が pending（本変更はアプリ非該当）
