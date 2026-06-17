## 基本情報
- **計画書ID**: plan_I064
- **関連イシュー**: #130
- **Draft PR**: #132
- **作成根拠資料**: docs/issues/open/I064.md（レビュー命名・状態管理規約の一本化）
- **実装後評価**: docs/reviews/open/I064_review.md（または未作成）
- **作成日**: 2026-06-15

---

## 1. 背景/目的

レビュー（および計画書ヘッダ）のファイル命名・状態管理について、**新旧2系統の規約が併存**している。規約ドキュメント（`review-rules.md` / `plan-writing-rules.md` ヘッダ / `issue-flow.md`）が旧系統（`reviewXXX` 通し番号・`_post` 別ファイル・`in_progress` 状態）のままで、実運用・スクリプト（`IXXX_*` 系統・open/closed の2状態）から乖離している。

本イシューは、規約ドキュメント3ファイルを実運用に即した新系統へ一本化し、新旧併存を解消する。**ドキュメント規約のみの変更**で、スクリプト・スキル・テンプレート・hooks は既に新系統のため変更しない（調査結果で確認済み）。

### 正準規約（I064 grill-me Q1 で確定）
- 命名（新系統4種）:
  - `IXXX_review.md` — `/plan-issue` が作成するライフサイクルレビュー（`open/` → `closed/`）。実装後評価は本ファイルの「テスト結果」「計画との差分」に集約する。
  - `IXXX_code_review_<timestamp>.md` / `IXXX_plan_review_<timestamp>.md` / `IXXX_issue_review_<timestamp>.md` — スクリプトが生成する時系列の監査記録（`docs/reviews/` **直下**に蓄積。open/closed 管理外・移動しない＝Q3 の現状をそのまま記述）。
- 状態: `open` / `closed` の2系統。
- 廃止: `reviewXXX` グローバル通し番号 / `_post` 別ファイル実装後評価 / `in_progress` 状態。
- 旧ファイル `review001〜003`（`docs/reviews/closed/` に現存）: **リネームせず履歴として残し**、「旧形式（廃止・履歴・リネーム不要）」と注記する（Q2）。

---

## 2. 調査結果（事前調査・必須）

### 環境前提
- 本イシューはドキュメント編集のみ。追加ツール不要（Read/Edit/grep/git のみ）。Backend/Frontend テストの実行対象なし。

### 参照実在性・grep 検証（実施済み）
| 確認項目 | コマンド/方法 | 結果 |
|---------|--------------|------|
| `review001〜003` の現存 | `ls docs/reviews/closed/review00*.md` | `review001_I004.md` / `review002_I005.md` / `review003_I007.md` 実在（履歴として残す対象） |
| `in_progress` ディレクトリの実在 | `ls -d docs/reviews/in_progress` | **存在しない**（幽霊ディレクトリ。規約のみに残存） |
| reviews ディレクトリ構成 | `ls -d docs/reviews/*/` | `open/` `closed/` `templates/` のみ（in_progress なし） |
| スクリプトの生成形式 | `grep REVIEW_FILE= scripts/claude/*.sh` | 3本とも `docs/reviews/${ISSUE}_{code,plan,issue}_review_${TIMESTAMP}.md`（新系統・直下）。**変更不要** |
| close スキルの移動対象 | `grep review .claude/skills/close/SKILL.md` | `docs/reviews/open/I${ISSUE_NUM}_*.md` を `closed/` へ（新系統）。**変更不要** |
| review_template.md の形式 | `head docs/reviews/templates/review_template.md` | `# I### レビュー: <title>`（新系統・テスト結果/計画との差分セクションあり）。**変更不要** |

### 旧系統参照の残存箇所（scope 内＝是正対象。legacy 除く）
`grep -rnE "reviewXXX|review[0-9]{3}_|reviews/in_progress|_post" docs/runbooks/ .claude/ scripts/` の結果、是正対象は **3ファイルのみ**:

- **`docs/runbooks/review-rules.md`**（最多）: L12, L18, L23, L44-60（採番ロジック）, L70, L126, L129, L139, L201-209, L211-221（採番bash）, L231, L244, L274-286（ステータス管理 + `in_progress` mv）
- **`docs/runbooks/plan-writing-rules.md`**: L180（`作成根拠資料: reviewXXX_IXXX`）。ヘッダ基本情報ブロック全体は L177-183。
- **`docs/runbooks/issue-flow.md`**: L241（命名規則 `plan_I{番号}_{概要}.md`）、L347/L365（close 用グロブ `plan_IXXX_*.md`。計画時に判明・スコープ追加）。L257/L366/L395-398 等のレビュー命名は既に新系統（`IXXX_review.md`）。

### 是正不要（既に新系統 or scope 外）と確認した箇所
- `docs/runbooks/legacy/CLAUDE.md.20260302`: 旧スナップショット。**legacy のため対象外**（AC でも「legacy 除く」と明記）。
- `docs/runbooks/workflow.md` L140/L151 の `"status": "in_progress"`: これは **TodoWrite のタスク状態フィールド**であり、`reviews/in_progress` ディレクトリ参照ではない。**誤検出・対象外**（本イシューで触らない）。
- `.claude/skills/*` / `scripts/claude/*` / hooks / `review_template.md`: 既に新規約（上表）。**変更不要**。

---

## 3. 受け入れ条件（Acceptance Criteria）

- [ ] `review-rules.md` に `reviewXXX_IYYY` / `_post` / `in_progress` 状態の記述が残っていない（`review001〜003` の「旧形式（廃止・履歴）」注記を除く）→ TC-01
- [ ] `review-rules.md` の命名・状態管理が実運用（`IXXX_*`・open/closed・`scripts/claude/*.sh` の生成形式）と一致 → TC-02
- [ ] `plan-writing-rules.md` のヘッダ基本情報ブロック（L177-183）が実体一致（`作成根拠資料`=issue パス / `実装後評価`=`IXXX_review.md` or 未作成 / `Draft PR` 行あり）、`reviewXXX`/`_post` 概念が残っていない → TC-03
- [ ] `issue-flow.md` の計画書命名が `plan_I###.md`（L241）、close 用グロブが新旧両対応（L347/L365）→ TC-04
- [ ] runbook 間でレビュー/計画書の命名規約に矛盾がない（`grep -rnE "reviewXXX|review[0-9]{3}_|reviews/in_progress" .claude/ docs/runbooks/ scripts/`（legacy・`review001〜003` 履歴注記を除く）で旧形式残存ゼロ）→ TC-05
- [ ] `.claude/skills/*` / `scripts/claude/*` / hooks / `review_template.md` が変更されていない（既に新規約）→ TC-06
- [ ] 命名無関係部分（レビュー必須要素 A/B/C/D・`.claude/skills/` 変更時の準拠チェックリスト）が保持されている → TC-07
- [ ] `review001〜003` に「旧形式（廃止・履歴・リネーム不要）」注記がある → TC-08

---

## 4. 影響範囲（想定）

- **Backend**: なし
- **Frontend**: なし
- **DB**: なし
- **Config/Infra**: `docs/runbooks/review-rules.md` / `docs/runbooks/plan-writing-rules.md` / `docs/runbooks/issue-flow.md`（ドキュメント規約のみ）
- **セキュリティ影響**: なし（バックエンド・フロントエンドのコード変更なし。入力処理・認証認可・機密データ・依存ライブラリの変更なし）
- **P3/P5/P8（データ整合性・運用設計・コスト）**: 影響なし（DB・外部API・新規インフラの変更なし）
- **P6（性能・UX）**: 影響なし（UI 変更・データ量/外部API懸念なし）
- **依存関係ファイル（requirements/package）**: 変更なし → Dockerfile/compose への波及なし

---

## 5. 変更点一覧（ファイル / 箇所）

### 5-1. `docs/runbooks/review-rules.md`（新系統へ是正・命名無関係部分は保持）

| 箇所 | 現状（旧系統） | 是正後（新系統） |
|------|--------------|----------------|
| L8-15 計画書ヘッダ例 | `計画書ID: plan_[タイプ]_[概要]_[連番]` / `作成根拠資料: reviewXXX_IXXX` | `計画書ID: plan_I###` / `作成根拠資料: docs/issues/open/IXXX.md`。`plan-writing-rules.md` のヘッダと統一し、本ファイルは要点のみ記載しヘッダ正本は `plan-writing-rules.md` を参照させる |
| L17-23 作成根拠資料/実装後評価の説明 | `review001_I010` 例 / `review002_I010_post（実装結果評価）` | 作成根拠資料=起点 issue パス例。実装後評価=`IXXX_review.md`（または未作成）。`_post` 概念を削除 |
| L25-184「計画書対応完了時の必須レビュー作成ルール」 | `reviewXXX_IXXX_post` を `cp` で新規作成する通し番号採番フロー（bash 採番ブロック含む） | 新系統に簡素化: 実装後評価は **`/plan-issue` が作成済みの `IXXX_review.md`** に記録（「テスト結果」「計画との差分」セクション）。別ファイル `_post` 作成・通し番号採番ロジックは廃止。レビュー作成の必須性・相互参照の趣旨は残す |
| L200-221「ファイル命名規則と通し番号管理」 | `reviewXXX_IYYY.md` / `_post` / 通し番号採番 bash | `IXXX_review.md`（ライフサイクル）/ `IXXX_{code,plan,issue}_review_<timestamp>.md`（スクリプト生成・直下蓄積）。通し番号採番を廃止し issue 番号で一意 |
| L231 レビュー番号 | `# レビュー #003`（通し番号） | issue 番号基準の表記に是正（または削除） |
| L244 相互参照リンク例 | `../reviews/open/reviewXXX_IYYY.md` | `../reviews/open/IXXX_review.md` |
| L272-286「ステータス管理 / ファイル移動」 | 3状態 `Open`→`In Progress`→`Closed`、`mv ... in_progress ...` | 2状態 `open`/`closed`。`in_progress` 廃止。`IXXX_review.md` は `open/`→`closed/`（`/close` が移動）。timestamped 監査記録は **`docs/reviews/` 直下に蓄積・open/closed 管理外・移動しない**現状を記述（Q3） |
| 任意の適切な箇所 | （なし） | 注記追加: 「旧形式 `review001〜003`（`reviewXXX` 通し番号）は廃止・履歴として `closed/` に残す・リネーム不要」（Q2） |
| L247-271 レビュー内容の必須要素 A/B/C/D | — | **保持**（命名無関係・Q4） |
| L288-306 レビュー活用方法・重要な注意事項・README 参照 | — | **変更しない**（旧系統トークンを含まず命名無関係。誤修正防止のため明示・Info指摘） |
| L308-327 スキル変更時の準拠チェックリスト | — | **保持**（命名無関係・Q4） |

> 方針: 旧系統トークンの置換と、意味を失う通し番号採番 bash ブロックの除去で、`review-rules.md` は現状（327行）より**簡素化**する（イシュー注記「分量を膨らませず最小記述」）。レビュー作成の必須性・A/B/C/D・知識共有・準拠チェックリストの趣旨は維持する。

### 5-2. `docs/runbooks/plan-writing-rules.md`（ヘッダ基本情報ブロック L177-183 全体）

現状（L177-183）:
```markdown
## 基本情報
- **計画書ID**: plan_I###
- **関連イシュー**: #XXX
- **作成根拠資料**: reviewXXX_IXXX（問題分析と改善提案）
- **実装後評価**: （未作成）
- **作成日**: YYYY-MM-DD
```

是正後:
```markdown
## 基本情報
- **計画書ID**: plan_I###
- **関連イシュー**: #XXX
- **Draft PR**: #XX
- **作成根拠資料**: docs/issues/open/IXXX.md（起点イシュー）
- **実装後評価**: docs/reviews/open/IXXX_review.md（または未作成）
- **作成日**: YYYY-MM-DD
```
- `作成根拠資料`: `reviewXXX_IXXX` → 起点 issue パス。
- `実装後評価`: フィールドは残し、意味を `IXXX_review.md`（または未作成）に更新。`_post` 概念を排除。
- `Draft PR` 行を補完（実プラン実体＝`/plan-issue` が Draft PR を作るため）。

### 5-3. `docs/runbooks/issue-flow.md`

| 箇所 | 現状 | 是正後 |
|------|------|--------|
| L241 計画書命名規則 | `plan_I{イシュー番号}_{概要}.md` | `plan_I###.md`（再作成時 `plan_I###_N.md`） |
| L347 close 用 for グロブ | `for PLAN_FILE in docs/plans/open/plan_IXXX_*.md; do` | `for PLAN_FILE in docs/plans/open/plan_IXXX*.md; do`（無印 `plan_I###.md` と再作成 `plan_I###_N.md` の双方にマッチ） |
| L365 close 後の参照例 | `計画書: docs/plans/closed/plan_IXXX_*.md` | `計画書: docs/plans/closed/plan_IXXX*.md` |

---

## 6. 実装手順（ステップ）

ドキュメント規約の整合変更のため、**ファイル単位で縦に貫通**（各ファイルを是正→直後に grep で残存ゼロ確認＝TC）。ステップ間に依存はなく独立だが、全体整合（TC-05）は全ステップ完了後に確認する。

- **ステップ1: `review-rules.md` の是正（最大の変更）**
  - 5-1 表のとおり、旧系統トークン（`reviewXXX`/`_post`/`in_progress`/通し番号採番）を新系統へ置換し、意味を失う採番 bash ブロックを除去。A/B/C/D・準拠チェックリストは保持。`review001〜003` 履歴注記を追加。
  - → TC-01 / TC-02 / TC-07 / TC-08 参照

- **ステップ2: `plan-writing-rules.md` ヘッダ基本情報ブロック（L177-183）の是正**
  - 5-2 のとおり `作成根拠資料`/`実装後評価`/`Draft PR` を是正。
  - → TC-03 参照

- **ステップ3: `issue-flow.md` の計画書命名・close グロブの是正（L241/L347/L365）**
  - 5-3 のとおり是正。
  - → TC-04 参照

- **ステップ4: 全域整合の最終確認**
  - 3ファイル是正後、scope 全体で旧形式残存ゼロ・命名無関係部分の保持・他ファイル無変更を確認。
  - → TC-05 / TC-06 参照

---

## 7. テスト計画（自動/手動）

- **自動（Claude 機械実行・`docs/tests/open/I064_auto_test.md`）**: TC-01〜TC-08。grep による旧形式残存ゼロ確認、新系統トークン存在確認、命名無関係部分の保持確認、他ファイル無変更確認（`git diff --name-only` が3ファイルのみ）。
- **手動（`docs/tests/open/I064_manual_test.md`）**: 規約文書の可読性・新旧併存解消の通読確認。テキスト通読は Claude で実施可（ブラウザ操作・UX 確認は不要なため Human 項目なし）。
- テストレベル: ドキュメント整合のため**静的検証（grep/diff）中心**。ユニット/結合/E2E は非該当。
- 再発防止: TC-05（全域 grep 残存ゼロ）が、旧形式の再混入を検出する回帰テストを兼ねる。

---

## 8. ロールバック

- 3ファイルのドキュメント変更のみ。問題があれば `git checkout -- docs/runbooks/{review-rules,plan-writing-rules,issue-flow}.md` で復元、または PR をマージしない／revert する。
- サービス再起動・マイグレーション等は不要（コード・DB 変更なし）。

---

## 9. Risk & 回避策

| Risk | 回避策 |
|------|--------|
| `review-rules.md` の大幅是正で命名無関係部分（A/B/C/D・準拠チェックリスト）を誤って削除/改変する | TC-07 で A/B/C/D 見出しと準拠チェックリスト表の存在を grep 確認。置換は命名・状態・採番トークンに限定 |
| `:241` のみ直し `:347/:365` グロブに旧 `_*` が残り新旧併存が再発（I060 D16 取りこぼしと同型） | スコープに :347/:365 を含め（ユーザー承認済み）、TC-04 で3箇所すべてを確認 |
| `workflow.md` の TodoWrite `"status": "in_progress"` を誤検出して触る | 計画書（2章）に誤検出として明記。TC-05 の grep 対象から `reviews/in_progress` ディレクトリ参照に限定 |
| `legacy/CLAUDE.md.20260302` の旧記述を巻き込む | AC・grep とも legacy を除外。本イシューでは触らない |
| スクリプト/スキル/テンプレートを「念のため」変更してしまう | TC-06 で対象3ファイル以外の無変更（`git diff --name-only`）を保証 |

---

## 10. 設計判断の明示（イシュー明記 / 仮定の区別）

| 設計判断 | 区分 | 根拠 |
|---------|------|------|
| 正準命名4種・open/closed 2状態・通し番号/`_post`/`in_progress` 廃止 | **イシュー明記** | I064 設計確認メモ Q1 |
| `review001〜003` はリネームせず履歴注記 | **イシュー明記** | Q2 |
| timestamped 監査記録は「直下蓄積・移動しない」現状をそのまま記述 | **イシュー明記** | Q3 |
| `plan-writing-rules.md` ヘッダブロック全体（L177-183）是正・`Draft PR` 行補完 | **イシュー明記** | Q4 精緻化1 |
| 命名無関係部分（A/B/C/D・準拠チェックリスト）保持 | **イシュー明記** | Q4 |
| timestamped 監査記録のライフサイクル整理はスコープ外 | **イシュー明記** | Q4 精緻化2（I065 で対応） |
| **issue-flow.md :347/:365 グロブの是正を追加** | **承認済みスコープ追加**（イシュー実装対象表は :241 のみ記載） | 計画時に判明。:241 のみ直すと新旧併存が再発するため。ユーザーが「含める」を承認済み。イシュー実装対象表も更新済み |
| `review-rules.md` のヘッダ正本を `plan-writing-rules.md` 参照に寄せ簡素化 | **仮定**（最小記述方針に沿う整理。重複削減） | イシュー注記「分量を膨らませず最小記述」。承認ポイントで確認 |

---

## 11. 承認ポイント

以下を承認いただければ `/implement I064` で実装に進みます（承認なしに Edit/Write は開始しません）。

1. **スコープ拡張（承認済み・再確認）**: `issue-flow.md` の是正を **:241 + :347 + :365 の3箇所**とする（グロブを `plan_IXXX*.md` に是正し新旧併存を防止）。
2. **`review-rules.md` の簡素化方針（仮定の確認）**: 旧 `_post` 通し番号採番フロー（L25-184）を、`/plan-issue` 作成済みの `IXXX_review.md` への実装後評価記録に置き換えて**簡素化**する。さらにヘッダ基本情報の正本は `plan-writing-rules.md` に寄せ、`review-rules.md` 側は重複を削減する。A/B/C/D・準拠チェックリスト・レビュー必須性の趣旨は保持。→ この簡素化方針でよいか確認。
3. **timestamped 監査記録**: Q3 のとおり「`docs/reviews/` 直下に蓄積・移動しない」現状をそのまま記述（ライフサイクル整理は I065）。
4. **セキュリティ影響なし**（ドキュメント規約のみ。コード/DB/依存変更なし）。
5. **テストは静的検証（grep/diff）中心**で Human 項目なし（通読も Claude 実施可）。

ご承認は「OK」「承認」等、修正指示があれば具体的にお願いします。

## レビュー結果
- [20260615_0013 判定: ✅ 完了](../../reviews/closed/I064_plan_review_20260615_0013.md)
