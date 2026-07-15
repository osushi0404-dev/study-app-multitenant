# I114 レビュー: /retro 対ユーザー出力の平易化（記録・詳細フォーマット維持）

## 基本情報
- **対象計画書**: docs/plans/open/plan_I114.md
- **関連イシュー**: #212（docs/issues/open/I114.md）
- **Draft PR**: #217

## レビュー目的
- 平易化ルールが「置換（省略ではない）」「経緯・理由の保持」「記録・詳細フォーマットの維持」の 3 原則を欠落なく明文化していること
- 既存の詳細表・5 Whys 内部手続き・手順4/5 のコマンドガイドと承認ゲートが無改変であること（R1〜R4 で機械検証）
- 決定論ゲート（14 項目）が false-green でないこと（TDD Red・注入検証の記録）

## 期待する成果
- /retro の報告・確認が「平易版 → 詳細版」の順で提示され、前提知識のないユーザーにも「何が・なぜ・どうする」が読み取れる
- 「対話は平易・資料（詳細版）は維持」の分離原則が retro スキルの手順として恒久化され、将来の他スキル横展開の雛形になる

## 変更概要
- retro SKILL.md に「対ユーザー出力の平易化ルール」セクション（5 原則＋文例）を追加し、手順2.5/3/4/5 に適用指示を追記。手順3 の報告は平易版→詳細版の併記に変更（詳細版は無改変維持）。決定論ゲートスクリプトを新設。

## 変更点
- `.claude/skills/retro/SKILL.md`: 平易化ルールセクション追加（計画 4-1）＋手順2.5/3/4/5 への適用指示追記（計画 4-2〜4-5）
- `scripts/claude/tests/test_i114_retro_plain_output.sh`: 新規（決定論ゲート 14 項目・`I114_TEST_SKILL` による注入検証対応）
- `docs/issues/open/I114.md`: 実装対象・影響範囲へテストスクリプト 1 行追記＋GitHub #212 同期（計画ステップ3）

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.claude/skills/retro/SKILL.md`・`scripts/claude/tests/test_i114_retro_plain_output.sh`（運用スキル・決定論ゲートのみ）

## 実装結果評価
- 計画書 4-1〜4-6 のとおり実装（TDD: 計画時 Red＝G1〜G10 全 NO-HIT → 実装後 Green＝14/14 OK）。plan review Warning（手順4/5 の粒度パリティ）は計画書へ記入例 2 行を反映してから実装。code review は Low 1 件（手順4/5 の記入例は手順3 の構造化テンプレートより簡素・許容判断）のみで VERDICT: OK・高リスク判定 No。
- 品質: pre-commit（shellcheck 含む）全 pass。

## テスト結果
- 自動: `test_i114_retro_plain_output.sh` **exit 0（14/14 OK）** を実装時・code-review 時・/test 時の 3 回確認。false-green 注入検証 2 件（R1 行削除・G2 行削除の一時コピー差し替え）とも NG 検知・exit 1。pytest / Jest / E2E は非該当（アプリコード変更なし）。
- 手動: M1〜M4 **全 OK**。M5 は /retro I114 自体が新フォーマットの前倒し実演となりユーザー確認済み（マージ後の次回 /retro でも通常運用として確認継続・非ブロック）。

## 計画との差分
- なし（手順4/5 の記入例 2 行は plan review Warning 対応として計画書を先に更新したうえで実装。機能仕様の変更なし）

## ロールバック
- SKILL.md 変更＋スクリプト追加コミットの revert（データ・インフラ影響なし）
