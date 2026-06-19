# I068 自動テスト（計画駆動）

- **関連計画書**: docs/plans/open/plan_I068.md
- **正とする自動テスト**: 下記 TC-A〜TC-M
- **既定テスト**: pytest / Jest / Playwright E2E は **非該当**（app コード変更なし）。`/test` 時に「非該当」と記録する。
- 実行者: すべて Claude。TC-A〜E は P3 スクリプト単体（一時 fixture）、TC-F〜L は文書 grep、TC-M は shellcheck。
- **P3 スクリプトは TDD**: TC-A〜E は implement の Red（スクリプト未作成で失敗）→ Green（実装後 PASS）で実行・記録する。

## P3 スクリプト単体（`scripts/claude/check-memo-body-paths.sh`）
fixture は heredoc で一時生成（`docs/issues/open/I900.md` 等の使い捨て番号、テスト後に削除）。

| TC | 内容 | 手順（要点） | 期待結果 |
|----|------|------------|---------|
| TC-A | 整合ケース | メモのパスが全て本文（実装対象/影響範囲）にある fixture で実行 | 終了コード 0・`✅ memo ⊆ body 整合` を出力 |
| TC-B | 不一致ケース（異常系） | メモにあって本文に無いパスを含む fixture で実行 | 終了コード **1**・不足パスを一覧表示（`- <path>`） |
| TC-C | プレースホルダ除外 | メモ内のパスが `未特定・grill-me で確認` 行にある fixture | 終了コード 0（プレースホルダ行のパスは比較対象外） |
| TC-D | バックティック無し無視 | メモ内にバックティック無しのパス様文字列のみ（本文に無い） | 終了コード 0（バックティック囲みでないものは抽出しない） |
| TC-E | 引数検証（パストラバーサル防止） | 不正引数 `../../etc` 等で実行 | 非処理（`^I[0-9]{3}$` 不一致で警告し処理しない・任意ファイルを読まない） |

## ドキュメント/ルール grep
| TC | 対象 | コマンド | 期待結果 |
|----|------|---------|---------|
| TC-F | grill-me に P3 実行 do | `grep -F "check-memo-body-paths.sh" .claude/skills/grill-me/SKILL.md` | ヒット（本文整合直後に実行する do が存在） |
| TC-G | plan-reviewer に P3 backstop | `grep -F "設計メモ" .claude/review-agents/plan-reviewer.md && grep -F "実装対象" .claude/review-agents/plan-reviewer.md` | 両ヒット（メモ↔本文反映の backstop 観点） |
| TC-H | plan-writing-rules の P2 拡張 | `grep -F "セマンティクス" docs/runbooks/plan-writing-rules.md` | ヒット（消費箇所列挙が概念/セマンティクス変更に拡張） |
| TC-I | plan-reviewer に P2 gate | `grep -F "中核概念" .claude/review-agents/plan-reviewer.md` | ヒット（概念変更の全消費箇所更新の観点） |
| TC-J | plan-writing-rules の P1 do | `grep -F "パリティ" docs/runbooks/plan-writing-rules.md` | ヒット（分岐コマンド粒度パリティの do） |
| TC-K | plan-reviewer に P1 gate | `grep -F "非対称" .claude/review-agents/plan-reviewer.md` | ヒット（分岐の非対称な省略を検出する観点） |
| TC-L | code-reviewer に P1 gate | `grep -F "非対称" .claude/review-agents/code-reviewer.md` | ヒット（同上・code 側 gate） |

## 静的解析・ドッグフード
| TC | 内容 | コマンド | 期待結果 |
|----|------|---------|---------|
| TC-M | shellcheck | `shellcheck scripts/claude/check-memo-body-paths.sh` | エラーなし（pre-commit shellcheck 通過） |
| TC-N(ドッグフード) | 実イシューで整合 | `bash scripts/claude/check-memo-body-paths.sh I068` | 終了コード 0・`✅`（本イシュー本文は memo ⊆ body 整合） |

## 既定テスト（フォールバック）— 非該当
| 種別 | 判定 | 理由 |
|------|------|------|
| pytest / Jest / Playwright E2E | 非該当 | app（Backend/Frontend/DB/UI）変更なし |

## 実行記録（/implement・/test 時に記入）
| TC | 結果(PASS/FAIL) | 備考 |
|----|------|------|
| TC-A | | |
| TC-B | | |
| TC-C | | |
| TC-D | | |
| TC-E | | |
| TC-F | | |
| TC-G | | |
| TC-H | | |
| TC-I | | |
| TC-J | | |
| TC-K | | |
| TC-L | | |
| TC-M | | |
| TC-N | | |
