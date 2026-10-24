# I185 レビュー: 開発環境の総点検と改善

## 変更概要
- 段 A: 開発環境の点検報告書 `docs/proposals/I185_dev_env_review.md` を作成し、改善案の採否を決める
- 段 B: 採用した改善 P1〜P5 を実装する（計画変更記録 2）
  - P1 編集直後の構文チェックの終了コードを 2 にする
  - P2 計画のレビューを人の承認の前に済ませる
  - （P3 fix-loop の自動進行は、敵対的レビュー 2 周で穴が続いたため別イシューへ移した）
  - P4 スキルの `allowed-tools` を外し、制限は `disallowed-tools` にする
  - P5 セッション開始時に状態をフックで渡す
- /close 時: 効果測定イシューの起票と、1 週間後のクラウドの 1 回限りの予約

## 変更点
- （実装後に記入）

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.claude/settings.json`（SessionStart フック追加）・`scripts/claude/hooks/`（posttooluse_check.py の修正・sessionstart_context.py の新規）・`.claude/skills/*/SKILL.md`（11 本の frontmatter・plan-issue の手順・security-review・retro の記述）・`docs/runbooks/workflow.md`・`issue-flow.md`・`onboarding.md`・`review-rules.md`・`.claude/review-agents/plan-reviewer.md`・`scripts/claude/plan-issue-review.sh`（判定不能で止める）・`scripts/migration_verify/lint_skills.py`・`docs/claude-code-structure.md`・`scripts/claude/tests/`（新規 3 本・fixtures・test_review_verdict.sh の更新）

## テスト結果
- 自動: 決定論ゲート 16 件すべて合格（/test・ba27f3f）。pytest・Jest・E2E は非該当（アプリのコード変更なし）。既存のハーネスのテスト 33 本のうち 31 本合格・2 本（D8・DOC6）は今回の変更と無関係の不合格（P12 の別イシューに同梱）
- 手動: No.1〜No.8 すべて OK（全項目 Claude 実施）
- レビュー: 基本レビュー OK（`I185_code_review_20261024_1846.md`）。敵対的レビュー 2 周で上限到達 → ユーザー一任で方式の見直し（`I185_adversarial_review_20261024_1950.md`・VERDICT OK）

## 計画との差分
- あり。計画変更記録 1〜7（承認の回数の数え方・採用した改善の実装内容・プランレビューと security-review の指摘への対応・I### の拾い方・敵対的レビュー 1 周目への対応・P3 を別イシューへ移す方式の見直し）

## ロールバック
- 段 A: 報告書のコミットを `git revert`
- 段 B: 改善ごとのコミットを `git revert`

## 振り返り（/retro・2026-10-24）

### 良かった点
- 作業記録の `permissionDecision` で承認の回数を実数で数えた（推定ではなく）
- 未知のリスク（`/insights` の非対話実行・クラウド予約のコメント可否）をステップ 1 で実証してから進めた
- TDD と、おとり・壊した版による false-green の確認を毎回の修正で行った
- 敵対的レビューが P3 の構造的な穴と、`plan-issue-review.sh` が VERDICT 無しを OK に倒す既存の不具合を見つけた

### 是正処置（本イシュー内で対応済み）
| # | 根本原因 | 対処 |
|---|---|---|
| C1 | `detect_plan_verdict` の保険の判定が最後に OK に倒れる | UNKNOWN で終了コード 1（435d8e0） |
| C2 | P5 の I### の判定が先頭一致（PR のタイトルは `fix: I###` の形） | 最初の I### を拾い、ASCII の数字に限った（bbce399・d5b7482） |

### 予防処置（すべて既存イシューに同梱・新規起票なし）
| # | 根本原因 | 予防策 | 同梱先 |
|---|---|---|---|
| P1 | 守りの部分を確かめる文書テストを部分一致で書くと、削除・反転・挿入を見逃す。偽合格の自己検証が「消した版」だけ | 守りの部分はブロックを丸ごと固定して照合し、偽合格の自己検証は削除・反転・挿入の 3 種類で行う | I094（#180）にコメント済み |
| P2 | レビュー用スクリプトの判定が、判定の行が無い出力を合格に倒す（コードレビュー側に残る） | `detect_code_verdict` も判定不能として止める | I173（#291）にコメント済み |
| P3 | 人の確認を外す改善を、外した後に何が機械で止めるかの設計なしで計画した | 新規の手順・観点は足さない。P3 を作り直す別イシューの前提（報告書 §6）で扱う | P3 の別イシュー（起票予定） |

### 見送り
- `/insights`・クリップボードの安全装置・作業用フォルダの消失: 環境の事情で、代わりの方法で手戻りなく進めた
- 計画時の「承認の印は記録に無い」の誤り: 点検の中で見つかりその場で直した
- 「GitHub の第三者の文章を毎回の文脈に入れない」の観点化: security-review 自体で捕まえた

### 残余リスク処遇
- security-review の Medium 2 件: P5 は対処済み、P3 は外したので解消。Low 4 件は受け入れ（新規イシューなし）
