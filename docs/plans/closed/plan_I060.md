# plan_I060: CLAUDE.md と runbooks の棚卸し・最新化

## 基本情報
- **計画書ID**: plan_I060
- **関連イシュー**: #122
- **Draft PR**: #125
- **作成根拠資料**: docs/issues/open/I060.md（設計確認メモ /grill-me 反映済み）
- **実装後評価**: （未作成）
- **作成日**: 2026-06-02
- **改訂**: 2026-06-12 D16 を追加（実装後コードレビュー I060_code_review_20260612_0057.md の Medium 指摘を受け AC3/AC4 を完遂）。旧 plan_I060_2.md は本文へ統合し削除。

---

## 1. 背景/目的

`CLAUDE.md` は参照先として 9 本の runbook を列挙しているが、`docs/runbooks/` 配下は同日以降に実体が変化しており、参照漏れ・実体乖離・相互矛盾が蓄積している。本イシューでは CLAUDE.md と `docs/runbooks/*`（全14本）を横断点検し、**参照整合性・実体整合性・相互整合性**の3観点で乖離を解消して最新化する。あわせて、再発防止として「新規 runbook 追加時に CLAUDE.md 参照先一覧を更新する」手順を `template-sync.md` に組み込む。

設計判断は /grill-me（イシューファイル「設計確認メモ」）で確定済み:
- 参照先一覧は**全14 runbook を網羅列挙**する
- CLAUDE.md に **PostToolUse(posttooluse_check.py)** を1行追記する
- 再発防止手順は **template-sync.md** に追記する
- 乖離一覧は**本計画書**に記録する
- 実体（コード/設定）側の修正が必要な場合は**別イシューに切り出す**（本イシューはドキュメント側を実体に合わせる）
- 対象14ファイルの**全文リライト**（文体・細部含む。ただしセマンティクス不変・新規セクション増設はしない）

---

## 2. 調査結果（棚卸し監査の実体突き合わせ）

並列監査エージェント4本 + 本文での grep 裏取りにより、以下を実体確認した。

### 実体（ground truth）
- 実在スキル（`.claude/skills/`、11個）: close, code-review, fix-loop, grill-me, implement, issue-bootstrap, plan-issue, plan-issue-review, retro, security-review, test
- 実在フック: `scripts/claude/hooks/pretooluse_guard.py`（PreToolUse=危険操作ブロック）/ `scripts/claude/hooks/posttooluse_check.py`（PostToolUse=Edit/Write 後の `.py`/`.json`/`.yaml` 構文チェック）
- 実在 runbook（`docs/runbooks/`、14本）: workflow, plan-writing-rules, danger-ops, common-commands, issue-flow, ux-rules, backend-check, review-rules, template-sync, pre-commit, branch-protection-setup, mcp-github-setup, mcp-usage, onboarding
- pre-commit フック（`.pre-commit-config.yaml`、10個）: check-yaml, end-of-file-fixer, trailing-whitespace, check-added-large-files, check-merge-conflict, detect-secrets, ruff, bandit, **shellcheck**, eslint
- テストテンプレ実体（`docs/tests/templates/`）: `auto_test_template.md` / `manual_test_template.md` のみ（`error_log_template.md` / `test_record_template.md` は**不在**）
- `rules/ultimate_django_coding_standards.md` / `rules/react-coding-standards-integrated.md`: 実在（CLAUDE.md 参照は健全）
- `.claude/settings.json` deny: `Bash(curl *)` は deny リストに含まれる
- **CLAUDE.md の現行参照先は 9 本**（実 grep で確認）。イシュー I060.md:14 の「8 本」は誤り（実体は 9 本）。本計画書は **現行9本 + 追加5本 = 14本** を正とする。
- **I059 波及確認（乖離なし）**: I059 で追加された issue-review（自己完結度レビュー）は issue-flow.md:110 に反映済み。`issue_template.md` の構成参照も issue-flow.md と整合（残る `test_record_template.md` 参照は D6 で別途修正）。

### 既存ベースライン
- 本イシューはドキュメントのみ。Backend/Frontend テスト・lint のベースライン計測は対象外（コード変更なし）。

---

## 3. 乖離一覧（修正前 → 修正後）※AC「乖離一覧を計画書に記録」充足

| # | ファイル:行 | 観点 | 現状（修正前） | 実体/正 | 修正後 |
|---|------------|------|----------------|---------|--------|
| D1 | CLAUDE.md:14-22 | 参照 | runbook 9本のみ列挙 | 実在14本 | 未掲載5本（pre-commit / branch-protection-setup / mcp-github-setup / mcp-usage / onboarding）を追記し全14本網羅 |
| D2 | CLAUDE.md:40 | 実体 | hooks は PreToolUse のみ記載 | PostToolUse も実在 | PostToolUse(posttooluse_check.py=Edit/Write後の構文検証) を1行追記 |
| D3 | template-sync.md | 相互/再発防止 | 新規 runbook 追加時の CLAUDE.md 同期手順なし | — | 「新規 runbook 追加時に CLAUDE.md 参照先一覧を更新」手順を、既存の「ルール変更時に関連ファイルを同時更新する」不変条件の直後（ステップ2 と ステップ3 の間）に追記 |
| D4 | template-sync.md:26 | 実体 | `docs/tasks/templates/*.md` を確認対象に列挙 | tasks/templates は不在 | 不在の確認対象行を削除（実在テンプレ群に整理） |
| D5 | pre-commit.md:38-46 | 実体 | フック表に9個（shellcheck 欠落） | config は10個 | `shellcheck`（対象 `scripts/`）の行を表に追加 |
| D6 | issue-flow.md:251 | 実体 | `test_record_template.md` を参照 | 不在 | `auto_test_template.md` / `manual_test_template.md` に修正 |
| D7 | issue-flow.md:156,299 | 実体 | `error_log_template.md` を参照 | テンプレ不在（運用ファイル `error_IXXX.md` は存在） | テンプレ参照を削除し「`docs/tests/open/error_IXXX.md` を新規作成（テンプレなし）」に修正。テンプレ新設は本イシュー対象外（別イシュー候補） |
| D8 | issue-flow.md:395-398 | 相互 | レビューファイル名 `reviewXXX_IXXX.md` | 他箇所(257,366)は `IXXX_review.md` | `IXXX_review.md` に統一 |
| D9 | workflow.md:36,69 ↔ issue-flow.md:153 | 相互 | retro が「必須」(workflow) と「任意」(issue-flow) で矛盾 | 運用実態=`/retro` の**実施は毎回必須**（指摘内容への対応は裁量） | **issue-flow.md を「必須」に統一**（workflow.md に合わせる）。retro の*実施*は必須／*指摘への対応*は内容次第で省略可、というニュアンスが伝わる表現にする（「対応は任意」と「実施は任意」を混同しない） |
| D10 | common-commands.md（7箇所） | 実体 | `docker-compose`（旧形式）と `docker compose`（新形式）が混在 | 両形式 allow だが不統一 | `docker compose`（新形式）に統一 |
| D11 | backend-check.md:359-362 | 参照 | `scripts/test_api_integration.sh` を保存・実行と記載 | スクリプト不在（実在は db_backup.sh / db_restore.sh） | 非実在スクリプトの保存・実行記述を削除（手順は本文の手動実行に留める） |
| D12 | backend-check.md（curl 手順全般） | 実体 | `curl` による API 検証手順を多数記載 | `Bash(curl *)` は settings.json で deny | 「これらの curl/API 直叩き手順は Claude では実行不可（deny）。ユーザー手動 or CI 前提」の注記を冒頭に追加（手順自体は残す・軽微注記） |
| D13 | onboarding.md:43 | 実体 | hooks は pretooluse_guard.py のみ | posttooluse も実在 | posttooluse_check.py（構文検証）を追記 |
| D14 | onboarding.md:24,30-38 | 実体 | スキル表・フローに `/grill-me` 欠落 | grill-me 実在（issue-bootstrap と plan-issue の間） | スキル表とフロー図に `/grill-me` を追記 |
| D15 | workflow.md / plan-writing-rules.md / review-rules.md / ux-rules.md / danger-ops.md / mcp-github-setup.md / mcp-usage.md / branch-protection-setup.md | 文体 | 重大な実体乖離なし（スキル名・フック・危険操作定義は実体と整合） | — | 全文リライト方針（下記）に沿って文体・表現・リンク健全性のみ点検整備（セマンティクス不変） |
| **D16** | workflow.md:17,20 / issue-flow.md:18,39,187,451 / onboarding.md:105 | 実体(AC3)・相互(AC4) | 不在ディレクトリ `in_progress/` をディレクトリ規約・読込パス・ツリー図に列挙 | 実在は `open/` `closed/`（+`templates/`）のみ（`ls -d docs/issues/in_progress docs/reviews/in_progress` → No such file） | `in_progress` 記載を削除し `open`/`closed` の2系統に統一。grep ヘルパーのコメントも修正。**`workflow.md:140,151` の `"status": "in_progress"`（TodoWrite 状態値）は変更しない** |

> **D16 はスコープ拡大ではない**: 不在パス参照の削除であり、既出の D4（不在 `tasks/templates` 削除）・D11（不在スクリプト削除）と同種。AC3「実体整合」・AC4「矛盾解消」を*完遂*する補完であって新規 AC ではない。運用フローは元から open→closed の2状態で `in_progress` を使っておらず、運用セマンティクスは不変。実装後コードレビュー（I060_code_review_20260612_0057.md）が workflow.md と review-rules.md の2箇所を Medium 検出したのを契機に、改訂時の `grep -rn in_progress docs/runbooks/` で本 PR 変更済みの issue-flow.md・onboarding.md にも残存することを確認して全数を D16 にまとめた。

### 別イシューに切り出す項目（本 PR では実施しない）
| 項目 | 理由 | 提案 |
|---|---|---|
| `review-rules.md` の旧レビュー番号体系（`reviewXXX_IYYY` / `in_progress` 状態管理 / `_post`）と `plan-writing-rules.md:180` のヘッダ例 `reviewXXX_IXXX` を現行 `IXXX_*` 体系へ再編 | 旧体系は歴史的に実在（`review001_I004` 〜 `review003_I007`）し単なる誤記ではない。「正準のレビュー命名・状態管理をどちらに統一するか」という運用設計判断を伴い、文体最新化（I060 の主旨）を超える。`review_template.md`・採番ロジック・`_post` の要否まで波及する | **新規フォローイシュー**として起票。本 PR の review-rules.md は D15（文体）のみに留める |

### スコープ外として除外した監査提案（記録）
監査エージェントが提示した以下は「最新化」を超える**機能・分量の追加**であり、CLAUDE.md「短く保つ」精神を runbook にも適用する観点から**本イシューでは実施しない**:
- danger-ops.md を 3〜5倍に拡充して「実装者ガイド化」する
- 各 runbook に「関連ドキュメント」ナビゲーション目次を新設する
- ux-rules.md にスキル連携の指南を新規追加する

---

## 4. 影響範囲

| 層 | 影響 |
|----|------|
| Backend | なし（P3/P5/P8 影響なし） |
| Frontend | なし（P6 影響なし） |
| DB | なし |
| Config/Infra | `.claude/settings.json` / `scripts/claude/hooks/*` / `.pre-commit-config.yaml` は**読み取り点検のみ**。記述齟齬はドキュメント側を実体に合わせて修正。実体側の修正が必要なケースは別イシューに切り出す（例: D7 の error_log テンプレ新設） |

**セキュリティ影響なし**（バックエンド・フロントエンドのコード変更なし。認証・認可・入力処理の変更なし。ドキュメント記述の正確化のみ）。

---

## 5. 全文リライト方針（D15 および全ファイル共通の原則）

「全文リライト」は以下の制約下で行う。これを逸脱する変更（新規セクション増設・運用ルールの新設・分量の大幅増）は計画外とし実施しない:
1. **セマンティクス不変**: 運用ルール・手順の意味を変えない（例外は D9 の retro 必須統一のみ。これは承認ポイントで明示確認）
2. **実体整合**: スキル名・フック・パス・コマンド・テンプレ参照を §2 の実体に一致させる
3. **文体整備**: 表記ゆれ統一（`docker compose` / 用語）・誤字・冗長表現・古い言い回しの修正
4. **リンク健全性**: 他 runbook・rules・テンプレへの相対パス参照が実在ファイルに解決すること
5. **増設禁止**: 「短く保つ」方針を踏襲し、新しい見出し・新規運用ルールを足さない（§3 除外項目の通り）

---

## 6. 変更点一覧（ファイル別）

- `CLAUDE.md`: D1（参照先5本追記）/ D2（PostToolUse 追記）
- `docs/runbooks/template-sync.md`: D3（CLAUDE.md 同期手順追記）/ D4（tasks/templates 整理）
- `docs/runbooks/workflow.md`: D9（retro 必須に統一・issue-flow と表現整合）/ D15（文体）/ D16（17,20 の `in_progress` 削除。140,151 は不変）
- `docs/runbooks/issue-flow.md`: D6 / D7 / D8 / D9（retro 必須）/ D15（文体）/ D16（18,39,187 コメント・451 読込パスの `in_progress` 削除）
- `docs/runbooks/pre-commit.md`: D5（shellcheck 追記）/ D15
- `docs/runbooks/common-commands.md`: D10（docker compose 統一）/ D15
- `docs/runbooks/backend-check.md`: D11（非実在スクリプト削除）/ D12（curl 注記）/ D15
- `docs/runbooks/onboarding.md`: D13（posttooluse 追記）/ D14（grill-me 追記）/ D15 / D16（105 ツリー図の `in_progress` 削除）
- `docs/runbooks/danger-ops.md` / `plan-writing-rules.md` / `review-rules.md` / `ux-rules.md` / `mcp-github-setup.md` / `mcp-usage.md` / `branch-protection-setup.md`: D15（文体・リンク健全性のみ）

---

## 7. 実装手順（ステップ）

ドキュメント変更のため「層を縦に貫く」垂直スライスは存在しない。代わりに**依存順（インデックス→同期機構→意味変更→実体整合→文体）**でステップを切る。各ステップ完了後の整合性検証は自動テスト文書の TC に委譲する（本文に検証コマンドを書かない）。

> **実装状況（重要・再実行防止）**: ステップ1〜6（D1〜D15）は commit `e0ca732` で**適用済み**。`/implement` での残作業は **ステップ7（D16）のみ**。ステップ1〜6 は冪等性確認（該当 TC が pass するか）に留め、既に適用済みの箇所を再編集しないこと。

### ステップ1: CLAUDE.md の最新化（インデックス確定）【依存なし・最初に実施】
- D1: 「0. 参照先」に未掲載5本を追記し全14本を網羅する。セットアップ/環境構築系（onboarding / pre-commit / branch-protection-setup / mcp-github-setup / mcp-usage）は既存の運用系リストと区別できる並びで列挙する。各行に1行ラベルを付す。
- D2: 「3. 権限と二重ガード」に PostToolUse(posttooluse_check.py) の1行を追記する。
- → TC-01, TC-02, TC-11 参照

### ステップ2: 再発防止（同期機構）の組み込み【ステップ1完了が前提＝参照先確定後】
- D3: `template-sync.md` に「新規 runbook 追加時に CLAUDE.md 参照先一覧を更新する」手順を追記する。
- D4: `template-sync.md` の不在テンプレ確認対象（tasks/templates）を実在群に整理する。
- → TC-10 参照

### ステップ3: ワークフロー2大文書の意味整合【承認ポイントで D9 を確定後に実施】
- D9: `workflow.md` / `issue-flow.md` の retro 記述を「必須」に統一する。
- D6 / D7 / D8: `issue-flow.md` のテンプレ参照誤り・レビューファイル命名を実体に合わせる。
- → TC-04, TC-05, TC-06 参照

### ステップ4: セットアップ/品質ゲート文書の実体整合
- D5: `pre-commit.md` のフック表に shellcheck を追記。
- D13 / D14: `onboarding.md` に posttooluse_check.py と /grill-me を追記。
- → TC-03, TC-09 参照

### ステップ5: コマンド系文書の実体整合
- D10: `common-commands.md` の `docker-compose` を `docker compose` に統一。
- D11 / D12: `backend-check.md` の非実在スクリプト記述削除・curl 注記追加。
- → TC-07, TC-08 参照

### ステップ6: 残り runbook の文体リライト（D15）
- `danger-ops.md` / `plan-writing-rules.md` / `review-rules.md` / `ux-rules.md` / `mcp-github-setup.md` / `mcp-usage.md` / `branch-protection-setup.md` を §5 の方針で点検整備する。
- **セマンティクス不変の明示**: D15 対象ファイルはコミットメッセージ／PR コメントで「**文体のみ改変・セマンティクス不変**」と宣言し、実装後レビューでレビュアーが意味変更の有無を判断しやすくする（指摘 W-3 対応）。
- → TC-11, TC-12 参照（全 runbook 横断のリンク健全性・参照整合）

### ステップ7: dead `in_progress` ディレクトリ参照の削除【D16・改訂で追加】
- `workflow.md:17,20`「ディレクトリ規約」から `in_progress` を削除し `open` / `closed` の2系統にする。
- `issue-flow.md:18,39,187` の grep ヘルパーコメント `open/in_progress/closed 全て` を `open/closed 全て` に修正。
- `issue-flow.md:451` の `open/XXX.md または in_progress/XXX.md` を `open/XXX.md または closed/XXX.md` に修正。
- `onboarding.md:105` のディレクトリツリーから `in_progress` を削除。
- `workflow.md:140,151` の `"status": "in_progress"`（TodoWrite 状態値）は**触らない**。
- → TC-13 参照

**依存関係**: ステップ1 → ステップ2（参照先確定が前提）。ステップ3 は D9 承認後。ステップ4・5・6・7 は相互に独立（並行実施可）。

---

## 8. テスト計画（自動/手動）

- 自動テスト（`docs/tests/open/I060_auto_test.md`）: grep/ls による参照整合性・実体整合性の機械検証（TC-01〜TC-13）。すべて Claude が実行可能。TC-13 は D16（dead `in_progress` 参照除去・TodoWrite 状態値は除外）を検証。
- 手動テスト（`docs/tests/open/I060_manual_test.md`）: 文体・可読性・「短く保つ」感覚の通読確認（一部 Human）。No.9 で D16 のディレクトリ規約一貫性を確認。
- バグ修正イシューではないため再発防止テストは D3（同期手順）の存在確認（TC-10）で代替する。D16 の「不在パス取りこぼし」再発は TC-13 が防止テストを兼ねる。認可・テナント境界テストは該当なし（コード変更なし）。

---

## 9. ロールバック
- すべて単一 PR(#125) 内のドキュメント変更。`git revert` または該当コミットの取り消しで原状復帰可能。サービス再起動・マイグレーション不要。

---

## 10. Risk & 回避策
| Risk | 回避策 |
|------|--------|
| D9（retro 必須統一）がワークフローの運用意図と異なる | 承認ポイントで明示確認してから実施。NG なら「両文書とも任意」に倒す選択肢も提示 |
| 全文リライトでセマンティクスを意図せず変えてしまう | §5 の「セマンティクス不変」を厳守。意味変更は D9 のみと宣言。差分レビューで逐次確認 |
| スコープ外提案（danger-ops 拡充等）に引きずられ肥大化 | §3 除外項目を明記済み。増設禁止を方針に固定 |
| D7（error_log テンプレ不在）を本イシューで作ろうとして scope creep | テンプレ新設はしない。参照を実体に合わせ、テンプレ要否は別イシュー候補として注記 |
| D16 で `"status": "in_progress"`（TodoWrite 値）まで誤削除する | 変更対象を行番号で限定（workflow.md は 17,20 のみ）。TC-13 の grep は `"status"` 行を除外して検証 |
| review-rules.md を中途半端に直して新たな不整合を生む | review-rules.md は本 PR では D15（文体）のみ。命名体系・in_progress 状態管理の再編は §3「別イシュー切り出し」へ一括 |

---

## 11. 設計判断の明示

| 設計判断 | 区分 |
|----------|------|
| 参照先一覧を全14本網羅にする | イシューに明記（設計確認メモ Q1） |
| PostToolUse を CLAUDE.md に1行追記、詳細は docstring 委譲 | イシューに明記（Q2） |
| 再発防止手順は template-sync.md に追記 | イシューに明記（Q3） |
| 乖離一覧は計画書に記録 | イシューに明記（Q4） |
| 実体修正は別イシュー切り出し（ドキュメントを実体に合わせる） | イシューに明記（Q5） |
| 全文リライト実施 | イシューに明記（Q6） |
| D9: retro を「必須」に統一（issue-flow を workflow に合わせる） | **イシューに明記**（ユーザー確認済み: /retro は毎回実施・指摘対応は裁量） |
| D7: error_log テンプレは新設せず参照のみ修正 | 仮定（Q5「実体作成は別イシュー」の解釈）→ 承認ポイントで確認 |
| D12: curl 手順は注記追加に留め手順自体は残す | 仮定（手動/CI 前提と解釈）→ 承認ポイントで確認 |
| スコープ外提案（danger-ops 拡充・ナビ目次・ux スキル連携）を実施しない | 仮定（「短く保つ」方針の適用）→ 承認ポイントで確認 |
| D16: dead `in_progress` 参照を削除し AC3/AC4 を完遂（対象は本 PR 変更済みの workflow.md / issue-flow.md / onboarding.md の3ファイル） | 仮定（コードレビュー指摘の補完）→ 承認ポイントで確認 |
| D16: `"status": "in_progress"`（TodoWrite 値）は変更しない | 確定（ディレクトリではない） |
| review-rules.md / plan-writing-rules.md の `reviewXXX` 命名体系再編は別フォローイシュー | 仮定（運用設計判断を伴うため切り出し）→ 承認ポイントで確認 |

---

## 12. 承認ポイント（チェックリスト）

以下をご確認のうえ承認してください。**特に ★ は仮定で決めた設計判断です。**

1. 乖離一覧（§3、D1〜D15）の対象と修正方針でよいか
2. ~~D9~~: **確定済み**（retro の実施は毎回必須／指摘対応は裁量。issue-flow.md を「必須」に統一）
3. ★ **D7**: 不在の `error_log_template.md` は**新設せず**、issue-flow.md の参照を「テンプレなしで `error_IXXX.md` を新規作成」に修正し、テンプレ新設は別イシュー候補に回す方針でよいか
4. ★ **D12**: backend-check.md の curl 手順は**削除せず注記追加**（Claude では deny・手動/CI 前提）に留める方針でよいか
5. ★ **スコープ外除外**（§3）: danger-ops.md の大幅拡充・各 runbook へのナビ目次新設・ux-rules へのスキル連携追記は**実施しない**でよいか
6. CLAUDE.md 参照先5本のラベル・並び（運用系と区別したセットアップ群）でよいか
7. 全文リライトを §5 の制約（セマンティクス不変・増設禁止）で進めてよいか
8. ★ **D16**（改訂で追加）: 不在ディレクトリ `in_progress/` 参照を workflow.md(17,20) / issue-flow.md(18,39,187,451) / onboarding.md(105) から削除し AC3/AC4 を完遂する。対象は本 PR 変更済みの3ファイルに限定、`workflow.md:140,151` の TodoWrite 状態値は不変。でよいか
9. ★ **別イシュー切り出し**: `review-rules.md` の旧レビュー番号体系（`reviewXXX_IYYY` / `in_progress` 状態管理 / `_post`）と `plan-writing-rules.md:180` の再編は本 PR に含めず新規フォローイシューへ。でよいか

## レビュー結果
- [20260603_1719 判定: ✅ 完了](../../reviews/I060_plan_review_20260603_1719.md)

## レビュー結果
- [20260613_1149 判定: ✅ 完了](../../reviews/I060_plan_review_20260613_1149.md)
