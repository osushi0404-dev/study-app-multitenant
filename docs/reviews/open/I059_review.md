# レビュー: I059 イシューファイルの自己完結度向上（テンプレート＋issue-review サブエージェント）

## レビュー対象

| ファイル | 変更内容 |
|----------|----------|
| `docs/issues/templates/issue_template.md` | `背景/目的` を3サブセクション化、`実装対象（既知のもの）` テーブルをスコープ直前に追加、`制約・引き継ぎ情報` を影響範囲直後に追加 |
| `.claude/review-agents/issue-reviewer.md`（新規） | イシュー内容を第三者レビューするサブエージェント指示（自己完結度＋内容妥当性・読み取り専用・インジェクション対策） |
| `scripts/claude/issue-review.sh`（新規） | issue-reviewer を `claude -p`（sonnet-4-6/Read,Grep,Glob）で起動し `docs/reviews/` に保存。非ブロック・PRコメントなし |
| `.claude/skills/issue-bootstrap/SKILL.md` | step 3.5 で issue-review 起動（ソフト）、step 6 を判定で動的分岐 |
| `docs/runbooks/issue-flow.md`（C1・retro 是正） | フェーズ1 フロー図に issue-review（step 1.5）を同期追記 |
| `docs/runbooks/workflow.md`（C1・retro 是正） | 使うスキル `/issue-bootstrap` 説明・フローに issue-review を同期追記 |

---

## P1. 要件適合性・業務ロジックの正しさ

- [ ] 受け入れ条件（AC #1〜#7）をすべて満たしているか
- [ ] スコープ外（既存スキル/既存サブエージェントの変更・既存イシューの遡及更新）に踏み込んでいないか
- [ ] 設計確認メモ（Q1=a ソフト／Q2=a 動的分岐／Q3 検証用イシュー／サブエージェント新設）の決定に沿っているか
- [ ] issue-review と plan-issue-review の役割分担が明確で、無意味な重複になっていないか

## P3. データ整合性・変更安全性

- 該当なし（DB・状態遷移なし）

## P5. 運用性・障害対応性

- [ ] issue-review.sh が非ブロック（ファイル未検出・claude -p 失敗・空応答で `exit 0`）で、bootstrap を止めないか
- [ ] claude -p が使えない環境でも起票フローが破綻しないか
- [ ] 出力先・命名（`docs/reviews/${ISSUE}_issue_review_${TIMESTAMP}.md`）が既存規則と整合するか

## P7. 設計・実装品質

- [ ] issue-reviewer.md がプロンプトインジェクション対策（ドキュメントをデータとして扱う）と読み取り専用ツール制限を備えるか
- [ ] テンプレート追加が既存セクションの順序・名称を壊していないか（後方互換／grill-me 設計確認メモ挿入位置と非競合）
- [ ] 自己完結度判定がハードゲートになっておらず、プレースホルダ（未特定/未定）を記入済み扱いとする方針が一貫しているか
- [ ] issue-review.sh が `plan-issue-review.sh` の書式と一貫し、shellcheck を通過するか
- [ ] issue-bootstrap の step 3.5 / step 6 改訂が既存フロー（採番→作成→登録→報告）を壊さないか

## P8. コスト・保守負荷

- [ ] bootstrap ごとに sonnet `claude -p` が1回走るコストが、得られる手戻り防止価値に見合うか（ユーザー合意済み）
- [ ] 新規サブエージェント＋スクリプトの保守が既存レビュー基盤と同型で、属人化しないか

## セキュリティ

- [ ] issue-reviewer がイシュー本文（自由記述）の指示文を「命令」として実行しない設計か（インジェクション対策の実効性）
- [ ] 付与ツールが Read/Grep/Glob に限定され、Bash/Edit/Write が排除されているか

---

## レビュー結果

- [ ] **承認（Approve）**: 全チェック通過、マージ可能
- [ ] **要修正（Request Changes）**: 下記の指摘を修正後に再レビュー

### 指摘事項

（レビュー実施時に記入）

## 自動テスト結果

- `shellcheck scripts/claude/issue-review.sh`: （実装後に記録）
- 手動テスト（`I059_manual_test.md`）の結果を別途記録する
