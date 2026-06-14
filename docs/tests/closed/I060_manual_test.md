# I060 手動テスト（文体・可読性・整合の通読確認）

対象: `CLAUDE.md` および `docs/runbooks/*`。自動テスト（I060_auto_test.md）で機械検証できない「読みやすさ・文体一貫性・短く保てているか」を確認する。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `CLAUDE.md` を通読する | 参照先が運用系とセットアップ系で見分けやすく整理され、本体は「短く保つ」方針どおり肥大していない（新規ルールが増えていない） | Human | OK | 通読確認済み |
| 2 | `CLAUDE.md` の「3. 権限と二重ガード」を読む | PreToolUse / PostToolUse の2フックが各1行で簡潔に併記され、何をするフックか一読で分かる | Claude | OK | CLAUDE.md:48 PreToolUse / :49 PostToolUse の2行併記を確認 |
| 3 | `docs/runbooks/template-sync.md` の追記手順を読む | 「新規 runbook を追加したら CLAUDE.md 参照先一覧を更新する」が手順の流れの中で自然な位置に置かれ、迷わず辿れる | Claude | OK | ステップ2.5（bash付き）が自然な位置に存在 |
| 4 | `workflow.md` と `issue-flow.md` の retro 記述を読み比べる | 両文書で retro の必須/任意の扱いが一致しており矛盾がない | Claude | OK | 両文書とも retro「必須」で一致 |
| 5 | `common-commands.md` を通読する | docker コマンドが `docker compose`（新形式）で統一され、コピペでそのまま使える | Claude | OK | 旧形式0件・新形式16件 |
| 6 | `backend-check.md` の curl 手順を読む | 「Claude では実行不可（deny）・手動/CI 前提」の注記があり、誤って Claude が実行して失敗する誤解が生じない | Claude | OK | backend-check.md:147 に注記あり |
| 7 | 変更した全 runbook を通読する | 文体・用語が統一され、誤字・冗長・古い言い回しが解消されている（セマンティクスは変わっていない） | Human | OK | 通読確認済み（セマンティクス不変） |
| 8 | `pre-commit.md` のフック表と実際の commit 時フック出力を見比べる | 表のフック一覧（shellcheck 含む10個）が実際に走るフックと一致する | Claude | OK | pre-commit.md=10個・config=10個・本セッションの実 commit フック出力10個が一致（ログ照合により Claude 実施） |
| 9 | `workflow.md` `issue-flow.md` `onboarding.md` のディレクトリ規約・ツリー図を読む | ディレクトリ構成が `open` / `closed`（+`templates`）の実在2系統で一貫し、不在の `in_progress` が記載されていない（D16） | Claude | OK | 3ファイルにディレクトリ in_progress 参照なし（status 値のみ） |
