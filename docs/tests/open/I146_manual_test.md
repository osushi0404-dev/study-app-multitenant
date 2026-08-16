# I146 手動テスト: 外部コード寄稿の受付方針明示と cross-repo PR ゲート

対象: PreToolUse ガードの実挙動（ハーネス上での block / ask）・GitHub 上での文書表示

**「実施環境」列について**: 権限モード／フックのロードに依存する挙動は、稼働中セッションではプロンプトの発生源を区別できず検証にならない。該当 TC は**プレーン default の新規セッション**で実施する（`docs/runbooks/plan-writing-rules.md`「ハーネス挙動テストの実施環境」）。

**テスト用の外部 PR**: PR #257（close 済み・head=`Dodothereal:fix/247-i138-plan-writing-rules`）。close 済みでも `gh pr view 257 --json isCrossRepository` は `true` を返すため、ガードの実挙動確認に使える（実際のマージは起こり得ないので安全）。

| No | 手順 | 期待結果 | 実施者 | 実施環境 | 実結果 | 備考 |
|---:|------|----------|--------|----------|--------|------|
| 1 | ステップ1完了直後のゲート。新規セッションを開き、`gh pr merge 257 --squash` を実行しようとする | ツールが実行されず、`[guard] PR 257 は fork（外部リポジトリ）由来です...` の趣旨のメッセージでブロックされる（exit 2 相当）。マージ API は呼ばれない | Human | プレーン default 新規セッション | | ステップ2以降へ進むゲート。不成立なら設計をやり直す |
| 2 | 同セッションで `gh pr edit 257 --base develop` を実行しようとする | ハードブロックではなく**確認プロンプト**が出る。プロンプトの理由文に fork 由来である旨が含まれる。`.claude/settings.json` で `Bash(gh pr edit *)` が allow されているにもかかわらず確認が出ること | Human | プレーン default 新規セッション | | hook の ask が allow ルールに優先することの確認 |
| 3 | 同セッションで `gh pr view 257 --json state` を実行する | 確認なしでそのまま実行できる（read-only は素通し） | Human | プレーン default 新規セッション | | 過剰ブロックでないことの確認 |
| 4 | 同セッションで自前 PR（#261）に対し `gh pr ready 261` 相当の操作を行う | 従来どおり確認なしで実行できる（自前 PR の挙動は不変） | Human | プレーン default 新規セッション | | AC-12 の実機確認 |
| 5 | `CONTRIBUTING.md` を Read で開き、(a) PR を受け付けない方針と理由、(b) イシューは受け付けるが対応を約束しない旨、(c) `SECURITY.md` への誘導が、英語と日本語の両方にあることを確認する | 3 点すべてが英語セクションと日本語セクションの双方に存在する | Claude | - | ✅ OK (2026-08-13) | 英語 L5-24 / 日本語 L32-51。(a) は理由 2 点（記録が伴う必要／`docs/runbooks/`・`.claude/` が自動レビューの基準）付きで両言語に記載。(b) L20/L47。(c) L24/L51 |
| 6 | `SECURITY.md` を Read で開き、報告経路と「公開 Issue に書かない」旨を確認する。メールアドレスが書かれていないことも確認する | Security タブからの報告手順が書かれており、メールアドレスの記載がない | Claude | - | ✅ OK (2026-08-13) | Security タブ→「Report a vulnerability」の手順（L7/L25）。「公開イシューではなく非公開で」（L5/L23）。全文にメールアドレスの記載なし |
| 7 | `.github/pull_request_template.md` を Read で開き、冒頭 1 行が追加され、既存項目が変わっていないことを確認する | 冒頭に外部 PR を受け付けない旨と CONTRIBUTING.md へのリンクがあり、既存の見出し・項目は変更されていない | Claude | - | ✅ OK (2026-08-13) | `git show 24fdea8 -- .github/pull_request_template.md` の差分は先頭 2 行の追加のみ（引用 1 行＋空行）。`## 概要` 以降の既存項目に変更なし |
| 8 | GitHub のリポジトリページで Security タブを開く | 「Report a vulnerability」ボタンが表示される（Private vulnerability reporting が有効） | Human | Human 目視 | ✅ OK (2026-08-15) | ユーザーが Settings → Advanced Security から有効化。読み取り API `gh api repos/osushi0404-dev/study-app-multitenant/private-vulnerability-reporting` = `{"enabled":true}` で裏取り済み（= Security タブに Report a vulnerability が出る状態） |
| 9 | GitHub で新規 PR 作成画面を開く | 本文テンプレートの冒頭に追加した 1 行が表示される | Human | Human 目視 | | |
| 10 | `docs/runbooks/workflow.md` の新規セクションを Read で開き、手順 1〜5 が具体コマンド付きで書かれていることを確認する | `gh pr view --json isCrossRepository` / `gh pr comment` / `gh pr close` の具体コマンドが含まれ、「Actions を承認しない」「base 追従・CI 対応をしない」が明記されている | Claude | - | ✅ OK (2026-08-13) | workflow.md L247-261「外部（fork）からの PR の扱い」。手順 1〜5 を確認。L252 に `gh pr view <PR番号> --json isCrossRepository -q .isCrossRepository`、L255 に `gh pr comment` / `gh pr close`。L253「Actions の実行を承認しない」・L254「base 追従・CI 対応・レビューをしない」を明記 |
| 11 | ステップ1完了直後のゲート（MCP 経路）。新規セッションで MCP ツール `mcp__github__update_pull_request_branch`（owner=osushi0404-dev / repo=study-app-multitenant / pull_number=257）を呼ぼうとする | 確認プロンプトが出て、理由文に fork 由来である旨と head リポジトリ名（`Dodothereal/study-app-multitenant`）が含まれる。承認しなければ API は呼ばれない | Human | プレーン default 新規セッション | | ハーネスが MCP の `tool_input` を hook にそのまま渡すことの実地確認（計画書 §2-4(2)）。スキーマ上のキー名は S9 で確認済みだが、実データの確認はここで行う |
