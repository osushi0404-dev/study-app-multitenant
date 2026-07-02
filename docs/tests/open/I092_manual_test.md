# I092 手動テスト: worktree ベースの並行トラック運用 runbook 化

自動テスト（I092_auto_test.md）が AC の記載有無を決定論的に検証する。本文書では、自動テストで機械判定しにくい**手順の再現性・可読性**を確認する。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `docs/runbooks/worktree.md` を Read で開く | ファイルが存在し、目的/用語/トラック設計/作成手順/独立セッション/セットアップ(docker compose)/並行衝突(ポート)/共有・非共有/採番/引き継ぎ/現構成の各セクションが揃っている | Claude | | 自動 TC-A1〜A9・A13 と重複だが目視で構成の通読性を確認 |
| 1b | セットアップ節が Docker 前提（`docker compose up -d`・backend `.env` コピー）で、ホストの venv/pip/npm 手順が書かれていないことを確認 | Docker 手順のみ。venv/pip install/npm install の記述が無い | Claude | | 既存アーキ整合（前提訂正の反映確認） |
| 2 | runbook の worktree 作成手順のコマンドを読み、ベースブランチが `origin/develop` になっているか確認 | `git worktree add ... origin/develop` の形。`main` は使わない旨の注意がある | Claude | | 再発防止（main 事故）の要 |
| 3 | runbook の「現時点のトラック構成」表を読む | 「参考・日付つき」と明示され、ハーネス改善=wt-harness、アプリ開発=study-app-multitenant（採番権威）が記載 | Claude | | 2層構成の具体例側 |
| 4 | runbook 本文（手順部）がプレースホルダ（`<track>` / `I<番号>`）で一般化されているか確認 | 手順本文が I092 固有名に依存せず一般形。固有値は参考表に隔離 | Claude | | AC「一般表現」 |
| 5 | `CLAUDE.md` を開き、追加された参照行の位置とリンクを確認 | 「0. 参照先」運用・ルール: の 2 番目（`- 運用フロー: docs/runbooks/workflow.md` の直後）に `- 並行トラック運用（worktree）: docs/runbooks/worktree.md` があり、リンク先が実在 | Claude | | 自動 TC-A10/A11 と重複だが位置の妥当性を目視 |
| 6 | runbook を初見の運用者になったつもりで通読し、記載どおりに新 worktree を作れる粒度か判断 | 手順が具体コマンドまで書かれ、文脈ゼロでも迷わず実行できると判断できる | Human | | 可読性・再現性の最終的な感覚確認（Claude では代替不可） |

## 実施メモ
- No.1〜5 は Read/Bash（grep・test -f）で Claude が実施可能。
- No.6 のみ「文脈ゼロの運用者にとって迷わず実行できるか」という感覚的判断のため Human 実施。
