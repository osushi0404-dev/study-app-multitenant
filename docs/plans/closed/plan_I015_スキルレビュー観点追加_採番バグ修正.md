# plan_I015_スキルレビュー観点追加_採番バグ修正

## 基本情報
- **計画書ID**: plan_I015_スキルレビュー観点追加_採番バグ修正
- **関連イシュー**: #34
- **作成根拠資料**: docs/issues/open/I015.md
- **実装後評価**: （未作成）
- **作成日**: 2026-03-28

---

## 背景/目的

1. `/code-review` スキルに「ベストプラクティス・セキュリティ・モダン開発観点」のレビューステップを追加し、実装後に発覚するセキュリティ・設計問題を減らす。
2. 計画書・テスト文書を同3観点でレビューする `/plan-issue-review` スキルを新規作成する。`/plan-issue` への埋め込みは行わず独立スキルとして分離する（`/code-review` の命名規則に準拠）。
3. `/issue-bootstrap` スキルの採番スクリプトで `printf "%d"` が0埋め数値を8進数として解釈するバグを修正する（014→12→次番号013になる問題）。

---

## 受け入れ条件（Acceptance Criteria）
- [ ] `/code-review` の手順にベストプラクティス・セキュリティ・モダン開発観点のチェック項目が追加されている
- [ ] `/plan-issue-review` スキルが新規作成され、計画書・テスト文書を同3観点でレビューする手順が含まれている
- [ ] `/plan-issue-review` でレビュー NG の場合に計画書修正→再実行のフローが明記されている
- [ ] 各観点のチェック項目が具体的で（例：「N+1クエリ」「認証漏れ」「OWASP Top 10」等）、曖昧でない
- [ ] `/plan-issue` の末尾に `/plan-issue-review` への案内が追加されている
- [ ] `CLAUDE.md` のスキル一覧に `/plan-issue-review` が追加されている
- [ ] `docs/runbooks/workflow.md` のフロー・スキル一覧・フェーズ移行テーブルに `/plan-issue-review` が追加されている
- [ ] `docs/runbooks/issue-flow.md` のフロー図・フェーズ2詳細に `/plan-issue-review` ステップが追加されている
- [ ] 既存の手順フローを壊していない（ステップ番号の整合性、STOP条件等）
- [ ] `/issue-bootstrap` の採番スクリプトで `I014` の次が `I015` と正しく算出される（8進数誤解釈が修正されている）

---

## 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: なし
- 変更ファイル:
  - `.claude/skills/code-review/SKILL.md`（追記）
  - `.claude/skills/plan-issue/SKILL.md`（末尾に案内追加のみ）
  - `.claude/skills/issue-bootstrap/SKILL.md`（採番スクリプト修正）
  - `.claude/skills/plan-issue-review/SKILL.md`（新規作成）
  - `CLAUDE.md`（スキル一覧に1行追加）
  - `docs/runbooks/workflow.md`（フロー・スキル一覧・フェーズ移行テーブル更新）
  - `docs/runbooks/issue-flow.md`（フロー図・フェーズ2詳細更新）

---

## 変更点一覧

| ファイル | 変更種別 | 概要 |
|---------|---------|------|
| `.claude/skills/code-review/SKILL.md` | 追記 | ステップ6として3観点レビュー追加、旧6を7に繰り下げ |
| `.claude/skills/plan-issue-review/SKILL.md` | 新規作成 | 計画書・テスト文書の3観点レビュースキル |
| `.claude/skills/plan-issue/SKILL.md` | 末尾追記 | 完了案内に `/plan-issue-review` を追加 |
| `.claude/skills/issue-bootstrap/SKILL.md` | 修正 | 採番スクリプトの8進数誤解釈バグを修正 |
| `CLAUDE.md` | 追記 | スキル一覧に `/plan-issue-review` を追加 |
| `docs/runbooks/workflow.md` | 追記・修正 | フロー・スキル一覧・フェーズ移行テーブルに `/plan-issue-review` を追加 |
| `docs/runbooks/issue-flow.md` | 追記 | フロー図・フェーズ2詳細に `/plan-issue-review` ステップを追加 |

---

## 実装手順

### ステップ1: `/code-review/SKILL.md` 修正

**修正アプローチ**: 既存ステップ5（品質・ロジック確認）の直後に新ステップ6として3観点レビューを追加する。旧ステップ6（OK/NG判断）は7に繰り下げる。

**変更後のステップ構成**:
```
1) CI 確認
2) 計画書・受け入れ条件を読む
3) 実装差分を確認
4) 受け入れ条件との照合・報告
5) コードの品質・ロジック上の問題があれば追記
6) ベストプラクティス・セキュリティ・モダン開発観点のレビュー  ← 新規追加
7) ユーザーへ OK/NG の判断を求める                              ← 旧6を繰り下げ
```

**追加するステップ6の内容**:
```markdown
6) ベストプラクティス・セキュリティ・モダン開発観点のレビュー:
   実装差分を以下の観点で確認し、問題があれば報告する。問題がなければ「問題なし」と記載する。

   **ベストプラクティス:**
   - rules/ultimate_django_coding_standards.md（Backend）/ rules/react-coding-standards-integrated.md（Frontend）の重要原則との重大な逸脱がないか
   - 責務分離が適切か（Fat View・Fat Component になっていないか）
   - 重複・冗長なコードが生まれていないか

   **セキュリティ:**
   - 認証・認可チェックの漏れ（未認証アクセス可能なエンドポイント、権限外操作の許容）
   - 入力検証・サニタイズ漏れ（シリアライザ/フォームによる検証があるか）
   - SQLインジェクション・XSS・CSRF 等 OWASP Top 10 相当のリスク
   - 秘密情報（APIキー・パスワード）のハードコードや意図しない露出
   - 過剰な権限付与・情報過多なレスポンス

   **モダンなウェブアプリ開発:**
   - REST API 設計の一貫性（HTTPステータスコード・命名規則・レスポンス形式）
   - 非同期処理・エラーハンドリングが適切に実装されているか
   - パフォーマンス上の明らかな問題（N+1 クエリ、不要な全件取得、未ページネーション）
   - アクセシビリティ（Frontend: aria属性・セマンティックHTML・キーボード操作）
```

---

### ステップ2: `/plan-issue-review/SKILL.md` 新規作成

**作成アプローチ**: `/code-review` と同じ構造（フロントマター・手順・OK/NG案内）で作成する。対象は実装コードではなく計画書・テスト文書。

**ファイルパス**: `.claude/skills/plan-issue-review/SKILL.md`

**ファイル内容**:
```markdown
---
name: plan-issue-review
description: Review plan and test docs for best practices, security, and modern web dev.
argument-hint: "I###"
disable-model-invocation: true
allowed-tools: Read, Glob, Grep
---

# /plan-issue-review

前提: /plan-issue 完了・生成ドキュメント作成済み。

1) 対象ドキュメントを読む:
   - docs/issues/open/$ARGUMENTS.md
   - docs/plans/open/$ARGUMENTS_plan.md（または plan_$ARGUMENTS_*.md）
   - docs/tests/open/$ARGUMENTS_manual_test.md
   - docs/tests/open/$ARGUMENTS_auto_test.md

2) ベストプラクティス・セキュリティ・モダン開発観点でレビューし、結果を報告する:
   問題がなければ各観点「問題なし」と記載する。

   **ベストプラクティス:**
   - rules/ultimate_django_coding_standards.md / rules/react-coding-standards-integrated.md の重要原則に反する設計が計画書に含まれていないか
   - 責務分離が適切か（Fat View・Fat Component になる設計になっていないか）
   - テストケースが適切なレベルで書かれているか（ユニット/結合/E2E の使い分け）

   **セキュリティ:**
   - エンドポイントごとの認証・認可要件が計画書に明示されているか
   - 入力検証・サニタイズの実装方針が含まれているか
   - OWASP Top 10 相当のリスク（XSS・CSRF・SQLi・認可不備等）への対策が考慮されているか
   - テストケースに権限外アクセス拒否・不正入力のケースが含まれているか

   **モダンなウェブアプリ開発:**
   - REST API 設計が一貫しているか（HTTPステータスコード・命名規則・レスポンス形式）
   - フロントエンドの状態管理・非同期処理の設計方針が適切か
   - パフォーマンス上の懸念（N+1・ページネーション設計等）が考慮されているか
   - アクセシビリティ要件が必要な場合に含まれているか

3) ユーザーへ OK/NG の判断を求める:
   - OK: 「✅ プランレビュー完了。`/implement $ARGUMENTS` を実行してください。」
   - NG: 「❌ レビュー NG。計画書・テスト文書を修正してから `/plan-issue-review $ARGUMENTS` を再実行してください。」
```

---

### ステップ3: `/plan-issue/SKILL.md` 末尾追記

**修正アプローチ**: 既存の「完了したら承認ポイントを提示して停止する」の後に、承認後の次ステップ案内を1行追加する。

**追加内容**（`完了したら「承認ポイント」を提示して停止する。` の後に追加）:
```markdown
承認後の次のステップ: `/plan-issue-review $ARGUMENTS` を実行して計画書・テスト文書をレビューしてください。
```

---

### ステップ4: `/issue-bootstrap/SKILL.md` 採番バグ修正

**バグの原因**:
```bash
# 問題のあるコード
LAST_NUM=$(printf "%d\n%d\n" "${FS_MAX:-0}" "${GIT_MAX:-0}" | sort -n | tail -1)
# printf "%d" "014" → 8進数として解釈 → decimal 12
# 結果: LAST_NUM=12 → NEXT=13 → ISSUE_NUM=013（誤り）
```

**修正後のコード**（`# 大きい方を採用` のブロックを置き換え）:
```bash
# 大きい方を採用（$((10#...)) で8進数誤解釈を防ぐ）
FS_NUM=$((10#${FS_MAX:-0}))
GIT_NUM=$((10#${GIT_MAX:-0}))
if [ "$FS_NUM" -gt "$GIT_NUM" ]; then
  LAST_NUM=$FS_NUM
else
  LAST_NUM=$GIT_NUM
fi
if [ "$LAST_NUM" -eq 0 ]; then
  ISSUE_NUM="001"
else
  NEXT_NUM=$((LAST_NUM + 1))
  ISSUE_NUM=$(printf "%03d" $NEXT_NUM)
fi
echo "次のイシュー番号: $ISSUE_NUM"
```

`$((10#014))` は bash 算術展開の基数指定構文で、`014` を必ず10進数の14として解釈する。

---

### ステップ5: `CLAUDE.md` スキル一覧更新

**修正アプローチ**: `## 2. 使うスキル` セクションの `/plan-issue` 行の直後に `/plan-issue-review` を追加する。

**追加内容**（`/plan-issue` 行の直後）:
```markdown
- /plan-issue-review I### : 計画書・テスト文書をベストプラクティス・セキュリティ・モダン開発観点でレビュー（OK なら /implement へ）
```

---

### ステップ6: `docs/runbooks/workflow.md` 更新

**修正アプローチ**: 3箇所を更新する。

**① フロー（ステップ一覧）**: `/plan-issue` と `/implement` の間に挿入
```
2. /plan-issue I### → ユーザーが計画書確認（OK/NG）
3. /plan-issue-review I### → 計画書・テスト文書レビュー（OK/NG）  ← 追加
   - NG の場合 計画書修正 → /plan-issue-review に戻る
4. /implement I### → ...（旧3を繰り下げ）
...（以降も繰り下げ）
```

**② スキル呼び出しルール** の禁止スキル一覧（行29付近）:
```
（`/issue-bootstrap` `/plan-issue` `/plan-issue-review` `/implement` `/code-review` `/test` `/fix-loop` `/retro` `/close`）
```
- 現在 `/retro` がリストから欠落しているため追加する

**③ フェーズ移行テーブル**:
- 「計画書承認後」行の案内先を `/implement` → `/plan-issue-review` に変更
- 新行を追加:

| タイミング | Claude がやること |
|-----------|-----------------|
| plan-issue-review OK 後 | 「`/implement I###` を入力してください」と案内 |
| plan-issue-review NG 後 | 「計画書・テスト文書を修正してから `/plan-issue-review I###` に戻ってください」と案内 |

---

### ステップ7: `docs/runbooks/issue-flow.md` 更新

**修正アプローチ**: フェーズ2（計画・設計）に `/plan-issue-review` ステップを追加する。

**① フロー図（フェーズ2）**: ステップ10（ユーザー承認）と旧ステップ11（実装）の間に挿入
```
10. ユーザーが計画書・テストケースを承認
    ↓
10.5. /plan-issue-review によるベストプラクティス・セキュリティ・モダン開発観点レビュー（OK/NG）
   - NG の場合 計画書・テスト文書修正 → 10.5 に戻る
    ↓
11. 実装（変わらず）
```

**② フロー図（フェーズ3→4の境界）**: テスト OK 後の retro フェーズが欠落しているため追加
```
14. ユーザーがテスト
    ↓ OK
14.5. /retro （任意） → /close へ
      または直接 /close へ
    ↓
=== フェーズ4: クローズ処理 ===
```

**③ フェーズ2の詳細セクション**（「ステップ9-10: ユーザー確認・承認」の後に追加）:
```markdown
**ステップ10.5: /plan-issue-review の実行**
- `docs/plans/open/` と `docs/tests/open/` の生成ドキュメントをベストプラクティス・セキュリティ・モダン開発観点でレビュー
- NG の場合: 計画書・テスト文書を修正してから再実行
- OK の場合: フェーズ3（実装）へ進む
```

---

## テスト計画

自動テスト: `docs/tests/open/I015_auto_test.md` 参照
手動テスト: `docs/tests/open/I015_manual_test.md` 参照

---

## ロールバック

スキルファイル・CLAUDE.md・runbooks のみ変更のため、`git revert` で即座に元に戻せる。リスクなし。

---

## Risk & 回避策

| リスク | 対策 |
|-------|------|
| 新ステップ追加でスキルの指示が長くなりすぎ、AIが全ステップを実行しなくなる | 各追加ステップは簡潔に書き、「問題なければ問題なし」の1行で済む構造にする |
| `/plan-issue-review` のスキルが見つからない対象ドキュメントを読もうとする | ファイルパスのパターンを複数記載し（plan.md / plan_I###_*.md）対応する |
| 採番修正で他の数値処理に副作用 | `$((10#...))` は採番用変数のみに適用、影響範囲を最小化 |
