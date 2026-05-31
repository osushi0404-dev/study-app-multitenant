# 手動テスト: I059 イシューファイルの自己完結度向上（テンプレート＋issue-review サブエージェント）

## テスト方針

テンプレート・サブエージェント指示・スキルの Markdown 変更、および `claude -p` を伴う issue-review の実起動を確認する。
Read・Bash で判定できる項目は Claude が実行する。コンテキストクリア後の実セッション `/plan-issue` 入域のみ Human が実施する。

---

## テストケース

| No | 確認対象 | 確認手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|----------|----------|----------|--------|--------|------|
| 1 | テンプレート 背景/目的の3サブセクション（AC#1） | `docs/issues/templates/issue_template.md` を読む | `## 背景/目的` 配下に `### 現状の問題（証拠・再現手順）`・`### 根本原因`・`### 解決方針` が存在する | Claude | | |
| 2 | テンプレート 実装対象テーブル（AC#2） | 同ファイルを読む | `## 実装対象（既知のもの）` テーブルが `## スコープ` の**直前**に存在する | Claude | | |
| 3 | テンプレート 制約・引き継ぎ情報（AC#3） | 同ファイルを読む | `## 制約・引き継ぎ情報` が `## 影響範囲（想定）` の**直後**に存在する。既存セクションの順序・名称が崩れていない（`## 関連資料` が先頭維持＝grill-me 設計確認メモ挿入位置と非競合） | Claude | | |
| 4 | issue-reviewer.md の新設と安全要件（AC#4） | `.claude/review-agents/issue-reviewer.md` を読む | (1) `<instructions>` 等「ドキュメントはデータ／命令でない」インジェクション対策ヘッダがある (2) Bash/Edit/Write 禁止・Read/Grep/Glob のみの読み取り専用指示がある (3) 第三者レビュアーとして自己完結度＋内容妥当性（根本原因が症状の言い換えでないか等）を見る観点がある (4) 判定は助言で起票をブロックしない旨がある | Claude | | |
| 5 | issue-review.sh の新設と非ブロック設計（AC#4） | `scripts/claude/issue-review.sh` を読む | (1) `claude -p --model claude-sonnet-4-6 --system-prompt issue-reviewer.md --tools "Read,Grep,Glob"` を呼ぶ (2) 結果を `docs/reviews/${ISSUE}_issue_review_*.md` に保存 (3) ファイル未検出・claude -p 失敗・空応答で `exit 0`（非ブロック） (4) PR コメント処理を持たない | Claude | | |
| 6 | issue-review.sh の実起動（AC#4・非ブロック） | `bash scripts/claude/issue-review.sh I059` を実行 | issue-reviewer による第三者レビューが生成され `docs/reviews/I059_issue_review_*.md` に保存される。非ゼロ終了しない。claude -p 不可の環境でも警告を出して exit 0 で終了する | Claude | | 外部 LLM 呼び出しを伴う。実行不可環境では非ブロック終了のみ確認 |
| 7 | issue-bootstrap の 3.5 起動追加（AC#5） | `.claude/skills/issue-bootstrap/SKILL.md` を読む | step 3（作成）と step 4（GitHub 登録）の間に「3.5 自己完結度レビュー」があり、`bash scripts/claude/issue-review.sh "I${ISSUE_NUM}"` を起動し結果を提示する記述がある。ソフト警告（非ブロック）と明記されている | Claude | | |
| 8 | 完了ガイドの動的分岐（AC#6・Q2=a） | 同ファイルの step 6 を読む | issue-review 判定で出し分け、(A) 要補足/プレースホルダ残→`/grill-me` 推奨、(B) 十分→`/grill-me` スキップして `/plan-issue` 直行可、の両分岐が記述されている | Claude | | |
| 9 | 検証用イシュー作成→自己完結確認→後始末（AC#7・Q3） | 改訂後テンプレートで検証専用イシューを `issue-bootstrap` 経由で新規採番・作成（GitHub 登録あり）し自己完結に記入。3.5 の issue-review が「十分」判定を返すこと、およびファイル単体で `/plan-issue` 着手に必要な情報が揃うことを確認。確認後ローカルファイル削除＋GitHub Issue クローズ | Claude | | 後始末まで実施（GitHub Issue は削除不可のためクローズ） |
| 10 | コンテキストクリア後の `/plan-issue` 実セッション入域（AC#7） | 新規セッション（コンテキストクリア）で TC9 の検証用イシューに対し `/plan-issue I0XX` を実行 | 不足情報をユーザーに問い返すことなく計画書作成に着手できる | Human | | TC9 の判定を実セッションで最終確認（任意） |
| 11 | issue-review.sh の非ブロック失敗動作（plan-review Warning 反映） | `claude` を解決できない環境を再現して実行する。例: 失敗する `claude` スタブを PATH 先頭に置いて `bash scripts/claude/issue-review.sh I059`（または `claude` を一時不在にして実行） | 「⚠️ issue-review をスキップしました（claude -p 失敗）。」等の警告を出し、**終了コード 0**（`echo $?` で確認）。bootstrap を止めない | Claude | ✅ PASS | implement 時に確認。(a) claude 失敗スタブ→exit 0／(b) reviewer 未検出→exit 0／(c) イシュー未検出（I999）→exit 0 すべて確認 |
| 12 | issue-bootstrap フロントマター description 更新（plan-review Warning 反映） | `.claude/skills/issue-bootstrap/SKILL.md` のフロントマターを読む | `description` が issue-review 起動を含む実態（例: "Create issue doc, run issue-review ..., then register GitHub Issue."）に更新されている | Claude | | |
