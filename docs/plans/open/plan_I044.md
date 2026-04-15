## 基本情報
- **計画書ID**: plan_I044
- **関連イシュー**: #91
- **作成根拠資料**: docs/proposals/review_design_proposal.md
- **実装後評価**: （未作成）
- **作成日**: 2026-04-15

---

## 背景/目的

現行フローでは実装前の深掘りセキュリティレビューが存在しない。

- `/plan-issue-review` は表層チェック（認可要件が計画書に明示されているか等）に留まる
- `/code-review` は実装後のため、設計上の問題を発見してもコスト高なリワークが発生する

高リスク変更（認証・認可変更、マルチテナント境界変更、外部公開API追加等）において、
`/implement` の前に設計レベルで深掘りする `/security-review` スキルを新設することで事故を防ぐ。

---

## 受け入れ条件

- [ ] `.claude/skills/security-review/SKILL.md` が存在する
- [ ] スキルの入力として計画書・イシュー・権限モデル・DB変更案を読む手順が含まれる
- [ ] セキュリティ設計観点の出力（設計上の重大リスク・実装上の禁止事項・必須の防御条件）が定義されている
- [ ] 攻撃シナリオ観点の出力（入口・想定権限・想定操作・守るべき条件・自動テスト化対象・手動確認対象・残余リスク）が定義されている
- [ ] 出力に重大度区分（Blocker/High/Medium/Low）の列が含まれる
- [ ] Blocker が残っている場合は STOP し `/implement` を案内しない停止条件が明記されている
- [ ] レビュー結果を計画書末尾の `## セキュリティレビュー結果` セクションに追記する手順が含まれる
- [ ] `/retro` の振り返り観点に「残余リスクの処遇（High以上はイシュー化・Medium以下は任意）」が追加されている
- [ ] `/retro` の振り返り観点に「今回の security-review の発見を設計ルールに昇格できるか」が追加されている
- [ ] `docs/runbooks/workflow.md` のフロー説明に「高リスク判定 Yes の場合は `/security-review` を実行」が追記されている
- [ ] スキルファイルが Claude Code ベストプラクティスに準拠している（allowed-tools 最小権限・disable-model-invocation・argument-hint・description・500行以内）

---

## 影響範囲

- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: なし
- スキルファイル（新規）: `.claude/skills/security-review/SKILL.md`
- スキルファイル（変更）: `.claude/skills/retro/SKILL.md`
- ドキュメント（変更）: `docs/runbooks/workflow.md`

---

## 調査結果

バックエンド・フロントエンドのコード変更なし。既存テスト・lint 実行は不要。

### 既存スキルの確認

**`/plan-issue-review` の高リスク判定出力**（すでに実装済み・I043 で追加）:
```
## 高リスク判定
判定: Yes / No
該当条件: [リスト、なければ「なし」]
推奨: （Yes の場合）`/implement` 前に `/security-review $ARGUMENTS` を実行してください。
     （No の場合）そのまま `/implement $ARGUMENTS` へ進めてください。
```
→ SKILL.md が存在すれば、/plan-issue-review からの案内が機能する。

**`/retro` の振り返り表**（既存）:
- 「セキュリティ」行はあるが、残余リスク処遇・設計ルール昇格の観点がない
- 追記で対応できる（設計変更不要）

---

## 変更点一覧

| # | ファイル | 変更種別 | 変更内容の概要 |
|---|---------|---------|-------------|
| 1 | `.claude/skills/security-review/SKILL.md` | 新規 | security-review スキルを新設 |
| 2 | `.claude/skills/retro/SKILL.md` | 変更 | 振り返り表にセキュリティ関連2行を追加 |
| 3 | `docs/runbooks/workflow.md` | 変更 | スキル一覧・フロー・移行テーブルに security-review を追記 |

---

## 実装手順

ステップ1〜3はすべて独立しており、並行実施可能。

---

### ステップ1: `.claude/skills/security-review/SKILL.md` 新規作成

**フロントマター**:
```yaml
---
name: security-review
description: Pre-implementation security deep-dive for high-risk changes. Run when /plan-issue-review outputs 高リスク判定 Yes, before /implement. Reviews design risks + attack scenarios, appends results to plan document, stops if Blocker found.
argument-hint: "I###"
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Edit
---
```

**スキルの処理フロー**（手順として SKILL.md に記述）:

1. **対象ドキュメントを読む**
   - 必須: `docs/issues/open/$ARGUMENTS.md`、`docs/plans/open/plan_$ARGUMENTS.md`
   - 計画書の影響範囲に応じて関連バックエンドファイルを特定して読む（permissions.py, views.py, serializers.py, models.py, urls.py）
   - バックエンド変更がない場合は「コード変更なし」と明記してスキップ

2. **セキュリティ設計レビュー**（8分類）
   - 認証・認可（最小権限・エンドポイントごとの必須要件）
   - マルチテナント（他テナントデータへの参照・操作）
   - 入力検証（バリデーション・サニタイズ方針）
   - 機密情報（パスワード・トークン・個人情報のログ/レスポンス露出）
   - OWASP Top 10（XSS・SQLi・CSRF・IDOR等）
   - ファイル操作（拡張子・サイズ・パス検証）
   - 外部通信（SSRF・認証情報漏洩）
   - 依存ライブラリ（新規追加の既知脆弱性）
   - 出力: `| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項/必須防御条件） |` テーブル

3. **攻撃シナリオレビュー**
   - 新規/変更されるエンドポイント・機能を特定
   - 攻撃者の想定操作（認証バイパス・権限昇格・他テナントアクセス等）を列挙
   - 出力: `| # | 入口 | 想定権限 | 想定操作 | 守るべき条件 | 自動テスト化対象 | 手動確認対象 | 残余リスク | 重大度 |` テーブル
   - コード変更なしの場合は「攻撃シナリオなし（コード変更なし）」

4. **レビュー結果サマリー出力**
   - Blocker/High/Medium/Low の件数を設計レビュー・シナリオ別に集計

5. **計画書末尾に `## セキュリティレビュー結果` セクションを追記**（Edit を使用）
   - 実施日・設計レビュー結果テーブル・シナリオレビュー結果テーブル・残余リスク処遇欄を追記

6. **停止条件チェック**
   - Blocker が1件でも残っている場合: ⛔ STOP。計画書修正・再実行を指示。`/implement` は案内しない。
   - Blocker なしの場合: ✅ 完了。`/implement $ARGUMENTS` を案内。

---

### ステップ2: `.claude/skills/retro/SKILL.md` の振り返り表に2行追加

既存の `| **セキュリティ** | ...` 行の直後に追記:

```markdown
| **残余リスク処遇** | security-review を実施した場合、残余リスクの処遇を決定したか？High 以上はイシュー化・Medium 以下は判断任意。実施していない場合はスキップ。 |
| **設計ルール昇格** | 今回の security-review で発見した問題パターンを、grill-me の確認観点または plan-issue-review のチェック項目に昇格できるか？実施していない場合はスキップ。 |
```

---

### ステップ3: `docs/runbooks/workflow.md` の更新

**変更A: スキル一覧を更新**（`/plan-issue-review I###` 行を以下に置き換え、直後に新行を挿入）:
```
- /plan-issue-review I### : 計画書・テスト文書をベストプラクティス・セキュリティ・モダン開発観点でレビュー（OK かつ高リスク判定 Yes → /security-review、No → /implement へ）
- /security-review I### : 高リスク変更の実装前セキュリティ深掘り（設計レビュー + 攻撃シナリオ）。/plan-issue-review で高リスク判定 Yes 時のみ実行（Blocker なし → /implement へ）
```

**変更B: フロー step 3 に高リスクパスを追記**:
```
3. /plan-issue-review I### → 計画書・テスト文書レビュー（OK/NG）
   - NG（Edit/Write で修正可能）: Claude が自分で修正 → /plan-issue-review に戻る
   - NG（設計判断が必要）: 選択肢を提示してユーザー確認 → 承認後修正 → /plan-issue-review に戻る
   - OK かつ高リスク判定 Yes: /security-review へ
3.5. /security-review I###（高リスク判定 Yes の場合のみ）→ Blocker 解消後 /implement へ
4. /implement I### → 実装・型チェック・push
```

**変更D: スキル呼び出しルールのワークフロースキル一覧に追加**:
現在の一覧:
```
ワークフロースキル（`/issue-bootstrap` `/grill-me` `/plan-issue` `/plan-issue-review` `/implement` `/code-review` `/test` `/fix-loop` `/retro` `/close`）
```
変更後:
```
ワークフロースキル（`/issue-bootstrap` `/grill-me` `/plan-issue` `/plan-issue-review` `/security-review` `/implement` `/code-review` `/test` `/fix-loop` `/retro` `/close`）
```

**変更E: フェーズ移行テーブルを更新**:
`| plan-issue-review OK 後 | ...` の1行を以下の4行に置き換える（変更B とセットで更新）:
```
| plan-issue-review OK 後（高リスク判定 No） | 「`/implement I###` を入力してください」と案内 |
| plan-issue-review OK 後（高リスク判定 Yes） | 「`/security-review I###` を実行してから `/implement I###` へ進んでください」と案内 |
| security-review Blocker なし後 | 「`/implement I###` を入力してください」と案内 |
| security-review Blocker あり後 | Blocker を解消してから `/security-review I###` を再実行するよう案内。`/implement` は案内しない |
```

---

## テスト計画

### 自動テスト（Claude が実施）

| 項目 | 確認方法 |
|------|---------|
| security-review/SKILL.md の存在確認 | ファイルパス確認 |
| フロントマター必須フィールドの存在確認 | Grep で各フィールドを確認 |
| `disable-model-invocation: true` の設定確認 | Grep |
| `allowed-tools` に Read/Glob/Grep/Edit が含まれる | Grep |
| SKILL.md が 500 行以内 | wc -l |
| retro/SKILL.md に「残余リスク処遇」行が存在する | Grep |
| retro/SKILL.md に「設計ルール昇格」行が存在する | Grep |
| workflow.md に「security-review」の記述が存在する | Grep |
| workflow.md のフロー説明に「高リスク判定 Yes」の記述がある | Grep |

### 手動テスト（Human が実施）

| 項目 | 確認内容 |
|------|---------|
| /security-review 実行時の出力形式 | セキュリティ設計レビューテーブル・攻撃シナリオテーブル・サマリーが出力されるか |
| 計画書への追記 | `## セキュリティレビュー結果` セクションが plan_*.md 末尾に追記されるか |
| Blocker 停止動作 | Blocker があるシナリオで STOP し /implement が案内されないか |

---

## ロールバック

変更はすべて Markdown ファイル（スキル・runbook）のため、`git revert` で即時ロールバック可能。
サービスへの影響なし。

---

## Risk & 回避策

| リスク | 可能性 | 対処 |
|--------|--------|------|
| SKILL.md が 500 行を超える | 低（設計上 150 行程度） | 手順を簡潔に保つ。詳細説明は構造で表現 |
| retro 追記行の挿入位置が意図しない箇所になる | 低 | 「セキュリティ行の直後」と計画書に明記して実装 |
| workflow.md の移行テーブル更新漏れ | 低 | 受け入れ条件チェックが網羅しているため発見しやすい |
| スキルファイル変更のみ → コード変更なしの場合に攻撃シナリオを誤って列挙する | 低 | SKILL.md に「コード変更なしの場合はスキップ」を明示 |
