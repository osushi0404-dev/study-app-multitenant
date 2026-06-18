# plan_I067: スキル前提分岐の明文化（plan-issue 既コミット時／test 計画駆動／retro・close ハンドオフ是正）

## 基本情報
- **計画書ID**: plan_I067
- **関連イシュー**: #135
- **Draft PR**: #（作成後に追記）
- **作成根拠資料**: docs/issues/open/I067.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I067_review.md
- **作成日**: 2026-06-18

---

## 1. 背景/目的

整備済みの規定スキルが「典型ケースしか想定しておらず、前提が崩れると実行時に破綻し、その場の判断で別手段に逃げる」問題（I062 監査由来）を、**スキル指示文（`.claude/skills/*/SKILL.md`）の分岐明文化**で根治する。

本イシューはドキュメント（スキル指示文）整備であり、Backend/Frontend/DB のコード変更は無い。

### 調査結果（証拠・根本原因）

#### 現象1: plan-issue の branch→issue コミット→draft PR がイシュー既コミット時に破綻
- 規定（`plan-issue/SKILL.md` step 2-3）: `git add docs/issues/open/I###.md` → `git commit -m "docs: create issue I###"` → `git push` → `gh pr create --draft`。
- 破綻: イシューファイルが既にベースブランチ（develop）にコミット済みだと `git commit` が **no-op**（変更なし）になり、続く `gh pr create` が **「No commits between develop and feature/…」でエラー**になる。

**機械検証で確定した真因**（このイシュー自身が同じ事故状態にある＝ドッグフーディング）:
```
$ git log --all --oneline | grep -i "create issue I062"   → 該当なし（plan-issue の commit ステップは一度も成立していない）
$ git log --all --oneline --diff-filter=A -- "docs/issues/**/I067.md"
  8df421b close(I063): docs open→closed 移動 + 完了情報追記 + retro P1/P2 バックログ
$ git show --stat 8df421b
  docs/issues/{open => closed}/I063.md
  docs/issues/open/I066.md          ← 未コミットのバックログ issue が巻き込まれた
  docs/issues/open/I067.md          ← 同上（本イシュー自身）
  docs/reviews/I066_issue_review_*.md / I067_issue_review_*.md
```
→ `/close I063` の commit ステップが、retro が `/issue-bootstrap` で作成した**未コミットのバックログ issue ファイル（I066.md / I067.md）を一括 `git add` で巻き込み**、develop にコミットしてしまった。これにより I066/I067 の plan-issue 初コミットが no-op 化する。I062 も同パターン（`f0d2c4b close(I064)` が I062.md を develop へコミット）。

- `issue-bootstrap/SKILL.md` は `cp` でローカル作成するのみで **コミットしない**（正しい）。漏れは **close（および retro ハンドオフ）の broad な `git add`** にある。`close/SKILL.md` step 3 は freeform の「commit/push して PR を更新」で、staging 範囲の指定が無い（`grep "git add" close/SKILL.md` → 該当なし）。

#### 現象2: /test が app 変更前提で、非app 変更時に「何を正の自動テストとするか」が無い
- 規定（`test/SKILL.md`）: env 判定後に backend `pytest` / frontend `jest` / `playwright e2e` を実行する手順のみ。
- 破綻: Backend/Frontend 変更が無いイシュー（スクリプト/ドキュメント/スキル定義のみ）では規定テストが無関係。実行者ごとに代替手段がばらつき、検証の再現性が失われる（I062 は規定テスト未実行のまま「非該当」宣言し、スキル未記載のスクリプトを独自に正として採用）。

#### 根本原因（一般化）
スキルが典型ケース（イシューは新規・未コミット／変更は app コード）のみを想定し、前提が崩れるケースの分岐が文書化されていない。

### 環境前提確認
- 編集対象は `.claude/skills/{plan-issue, test, retro, close}/SKILL.md` の 4 ファイルのみ（いずれも実在を確認済み）。
- 本イシューの追記で新規に参照する外部パスは導入しない（既存ファイル `docs/tests/open/I###_auto_test.md` パターンと上記 4 スキルの相互参照のみ）。
- 既存テスト/lint のベースライン計測は不要（コード変更・lint 対象変更が無いため）。

---

## 2. 受け入れ条件（Acceptance Criteria）
- [ ] `plan-issue/SKILL.md` に「イシューが既にベースへコミット済みの場合」の分岐が明記され、その手順どおりに進めれば `gh pr create` がエラーにならない（invariant も併記）
- [ ] `test/SKILL.md` に「計画書（auto_test.md）が指定する自動テストを正とし、指定が無い場合のみ既定 pytest/Jest/E2E にフォールバックする」分岐が明記され、`description` も更新される
- [ ] `retro/SKILL.md` に「バックログ issue ファイルはローカル未コミットのまま残す（ベースへコミットしない）」ハンドオフ invariant が明記される
- [ ] `close/SKILL.md` step 3 の staging が close 対象ファイルに限定され、未コミットのバックログ issue ファイルを巻き込まないことが明記される（`git add -A`/`.`/`docs` 禁止）
- [ ] I062/I067 と同等の状況（イシュー既コミット・非app変更）を分岐文言に当てはめて規定どおり完走できることを文書レビュー（TC-08）で確認

---

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: `.claude/skills/plan-issue/SKILL.md` / `test/SKILL.md` / `retro/SKILL.md` / `close/SKILL.md`（スキル指示文のみ）

P3/P5/P8 影響なし（DB変更なし・外部API/非同期/バッチなし・新規インフラ/依存ライブラリ追加なし）。
P6 影響なし（UI なし・データ量/外部API 懸念なし）。
セキュリティ影響なし（バックエンド・フロントエンドのコード変更なし。スキル指示文の編集のみで認証・認可・入力処理・依存関係に変更なし）。

---

## 4. 変更点一覧

| # | ファイル | 変更内容 |
|---|---------|---------|
| A | `.claude/skills/plan-issue/SKILL.md` | step 2 付近に invariant（イシューは feature ブランチで初コミット／ベース事前コミット禁止）と「既コミット時」分岐（issue commit スキップ→計画書 docs コミットで draft PR）を追記 |
| B | `.claude/skills/test/SKILL.md` | 冒頭に「自動テストの選択（計画駆動）」節を追加（auto_test.md を正・指定なし時のみ既定にフォールバック・非該当を明記）。既定手順 0-3 を「フォールバック」と明示。`description` を更新 |
| C | `.claude/skills/retro/SKILL.md` | step 4（予防処置への対応）に、バックログ issue ファイルはローカル未コミットのまま残す invariant を注記 |
| D | `.claude/skills/close/SKILL.md` | step 3 を「scoped staging（`git add -u`）＋ `git add -A`/`.`/`docs` 禁止＋未追跡バックログ issue は未コミットのまま残す」に具体化 |

---

## 5. 実装手順（ステップ）

> 各ステップの検証は自動テスト文書（`docs/tests/open/I067_auto_test.md`）の TC を参照。本文には検証コマンドを書かない。

### ステップ1: plan-issue/SKILL.md に invariant＋既コミット分岐を追記（変更A）
**修正方針**: 「イシューは feature ブランチで初コミットするのが原則」という invariant を明記し、既にベースへコミット済みの場合の代替手順を示す。これにより `gh pr create` の「No commits between …」エラーを回避できる。

`#### 2. イシューファイルのコミット・プッシュ` のコードブロック直後に以下を追記:

```markdown
**前提（invariant）**: イシューファイルは **plan-issue が feature ブランチで初コミットする**のが原則。`/issue-bootstrap` はローカル作成（未コミット）に留め、develop 等のベースブランチへ事前コミットしない（retro/close のハンドオフでも同様）。同一ファイルシステム上の untracked ファイルは context clear をまたいでも残り、別コンテキストの plan-issue が拾える（develop 事前コミットもハンドオフ PR も不要）。

**分岐（イシューが既にベースへコミット済みの場合）**: 何らかの理由でイシューファイルが既にベースブランチ（develop）にコミット済みのときは、上記 `git commit -m "docs: create issue I###"` は **no-op** になり、続く `gh pr create` が **「No commits between develop and feature/…」でエラー**になる。この場合は次の手順で進める:
1. `docs: create issue` コミットを **スキップ**する。
2. 生成物の計画書 docs（plan / tests / review）を先に commit する（例: `git commit -m "docs: plan I### (issue already on base)"`）。
3. その docs コミットを push し、それを基に `gh pr create --draft --base develop` を実行する（差分が生じるため PR 作成は成功する）。
```
→ 検証: TC-01

### ステップ2: test/SKILL.md を計画駆動に更新（変更B）
**修正方針**: 実行する自動テストを「計画書のテスト計画（auto_test.md）」を正とし、指定が無い場合のみ既定（pytest/Jest/E2E）にフォールバックする。app/非app の分岐は設けない。`description` も計画駆動である旨に更新する。

(1) frontmatter の `description` を更新:
- 変更前: `Run automated tests (pytest + Jest) and prompt manual test verification.`
- 変更後: `Run the plan-specified automated tests (default: pytest + Jest + E2E) and prompt manual test verification.`

(2) `前提: /code-review OK。` の直後に「自動テストの選択（計画駆動）」節を追加:
```markdown
## 自動テストの選択（計画駆動）
実行する自動テストは **計画書のテスト計画（`docs/tests/open/$ARGUMENTS_auto_test.md`）が正**。
- auto_test.md が **専用の自動テスト**（例: `bash scripts/...` の専用スクリプト・特定 TC）を指定している場合: **それを正として実行**し結果を記録する。auto_test.md が「非該当」と明記した既定テスト（pytest/Jest/E2E のいずれか）は実行せず「非該当」と記録する。
- auto_test.md が自動テストを **指定していない場合のみ**: 下記の既定（pytest → Jest → E2E）にフォールバックする。

app/非app の区別では分岐しない。Backend/Frontend 変更が無いイシューでは、auto_test.md が専用テストを正と指定し pytest/Jest/E2E を「非該当」と明記する運用になる。
```

(3) 既定手順の見出しを明示（現 step 0 の直前に追加）:
```markdown
### 既定の自動テスト（auto_test.md に指定が無い場合のフォールバック）
```
→ 検証: TC-02・TC-03・TC-04

### ステップ3: retro/SKILL.md にバックログ未コミット invariant を注記（変更C）
**修正方針**: 予防処置/是正処置を `/issue-bootstrap` でバックログ起票する際、その issue ファイルをベースへコミットしないことを明記し、close 側の事故（現象1）の発生源を断つ。

step 4 のコードブロック（予防処置への対応ガイド）の直後に以下を追記:
```markdown
   **（ハンドオフ invariant）** `/issue-bootstrap` で起票したバックログのイシューファイルは **ローカル作成（未コミット）のまま**にする。develop 等のベースへコミットしない。コミットすると当該イシューの `/plan-issue` の初コミットが no-op 化し draft PR が失敗する（plan-issue の invariant 参照）。イシューは各自の `/plan-issue` が feature ブランチで初コミットする。
```
→ 検証: TC-05

### ステップ4: close/SKILL.md step 3 を scoped staging に具体化（変更D）
**修正方針**: close の commit が close 対象の I### 関連ファイルのみを staging し、未コミットのバックログ issue ファイルを巻き込まないようにする。`git add -A`/`.`/`docs` の broad add を明示的に禁止する。

step 3「commit/push して PR を更新」を以下に置き換える:
```markdown
3) commit/push して PR を更新する。
   **staging は close 対象の I### 関連ファイルに限定する**（step 1 の `git mv` で移動した issue/plan/tests/reviews と、完了情報追記などで編集した追跡済みファイルのみ）。
   ```bash
   # 追跡済みファイルの変更（git mv 済みの move・完了情報追記）だけを staging する。
   git add -u
   # ⚠️ `git add -A` / `git add .` / `git add docs` は使わない。
   #    retro が /issue-bootstrap で作成した未コミットのバックログ issue ファイル（別 I###.md）を
   #    巻き込み、当該イシューの plan-issue 初コミットを no-op 化させる（I062/I067 の事故原因）。
   git commit -m "close(I###): ..."
   git push
   ```
   `git status` に未追跡のバックログ issue ファイル（`docs/issues/open/` 配下の別 I###.md 等）が出る場合は、**コミットせず未追跡のまま残す**。
```
→ 検証: TC-06

### ステップ5: 整合性・完走シナリオの文書レビュー
**修正方針**: 4 ファイルの frontmatter 妥当性と、I062/I067 ケースを新文言に当てはめた完走シナリオを文書レビューで確認する。
→ 検証: TC-07・TC-08（手動 No.1 含む）

**依存関係**: ステップ1〜4 は相互独立（並行可）。ステップ5 はステップ1〜4 完了後。

---

## 6. テスト計画（自動/手動）

### 自動テスト（計画駆動 — 本イシュー自身が新 test/SKILL.md 設計のドッグフーディング）
- **本イシューの正とする自動テスト**: `docs/tests/open/I067_auto_test.md` の TC-01〜TC-07（追記文言の存在を `grep -F` で機械検証＋frontmatter 妥当性）。Claude が `/test` 時に実行・記録する。
- **既定テスト**: pytest / Jest / Playwright E2E は **非該当**（Backend/Frontend/DB のコード変更なし）。`/test` 実行時に「非該当」と明示記録する。
- テストレベル: 本イシューはドキュメント整備のためユニット/結合/E2E は不適用。検証は文字列存在検証（決定論ゲート）＋文書レビュー（敵対的確認）で行う。
- 認証・認可・テナント境界テスト: 該当なし（認可変更なし）。

### 手動テスト
`docs/tests/open/I067_manual_test.md` を参照。文書レビュー（完走シナリオ・文言の明確性）が中心。

---

## 7. ロールバック
- 変更は 4 ファイルのテキスト追記/置換のみ。`git revert <commit>` または該当ブロックの削除で即時ロールバック可能。サービス再起動不要。

---

## 8. Risk & 回避策
| Risk | 影響 | 回避策 |
|------|------|--------|
| close の `git add -u` が完了情報追記済みファイルを取りこぼす | close の commit が不完全 | step 1 の `git mv` で move は既に staging 済み。`git add -u` は追跡済みの変更（move 先への追記含む）を再 staging するため取りこぼさない。TC-06 で文言確認 |
| 既コミット分岐の手順が plan-issue の通常フロー（PR を先に作る）と順序が逆 | 運用者の混乱 | invariant＋分岐を「step 2 直後」に併記し、通常時/既コミット時の差を明示。本イシュー自身で実地適用し完走確認 |
| 追記文言が冗長でスキルが読みづらくなる | 保守性低下 | 各追記は invariant＋分岐の最小限。既存節構造を壊さず挿入 |

---

## 9. 承認ポイント

### 設計判断の明示（イシュー明記 / 仮定）
| 判断 | 区分 | 根拠 |
|------|------|------|
| plan-issue 本体ロジックは変更せず invariant＋既コミット分岐の追記に留める | **イシュー明記**（設計メモ Q1=A） | I067.md「plan-issue 本体のロジック変更は原則不要」 |
| 既コミット時は issue commit スキップ→計画書 docs コミットで draft PR | **イシュー明記**（解決方針1） | I067.md 解決方針1 |
| /test を計画駆動（auto_test.md を正・指定なし時のみ既定にフォールバック） | **イシュー明記**（設計メモ Q2=B） | I067.md「auto_test.md が指定する自動テストを正として実行、指定が無い場合のみ既定にフォールバック」 |
| retro/close をハンドオフ是正の対象に追加 | **イシュー明記**（設計メモ Q1=A ②・スコープ補足） | I067.md「対象スキルは plan-issue, test, retro, close」 |
| close の scoped staging に **`git add -u`** を採用 | **仮定（イシュー意図からの導出）** | イシューは「close の一括 git add が未コミット backlog を巻き込まない」と意図を明記。具体コマンド `git add -u` は本計画での導出（move は git mv 済みのため `-u` で追跡済み変更のみ staging すれば足りる） |

> `git add -u` の採用のみ「仮定（導出）」です。close で `git add -u` を使うか、より明示的にファイル名指定の `git add docs/issues/closed/... docs/plans/closed/...` を列挙する方式にするか、ご確認ください（既定推奨は `git add -u`）。

### チェックリスト（要件適合性・セキュリティ・テスト計画・設計品質）
- [x] 要件適合性: 受け入れ条件の範囲内（4 スキルの分岐明文化のみ）。命名規約 runbook・スクリプト/close 側ロジック（I066 担当）は触らない
- [x] マルチテナント/組織スコープ: 該当なし（コード変更なし）
- [x] ステータス遷移/承認条件: 該当なし
- [x] セキュリティ: セキュリティ影響なし（コード・依存関係・認可に変更なし）
- [x] テスト計画: 再発防止＝TC-01〜TC-08 が分岐文言の存在と完走シナリオを検証。テストレベル明示済（文字列検証＋文書レビュー、pytest/Jest/E2E は非該当）
- [x] 設計品質: アンチパターンなし。close の broad add 禁止は根治（宣言箇所＝close step 3 を是正）
- [x] 文書品質ゲート: API/permission/DB/エラー応答は該当なし（コード変更なし）。auto_test TC の期待値（grep ヒット）と manual_test の期待結果（具体的な文言・動作）は具体記載済み。実装ステップ本文に検証コマンドを残さず TC 参照に統一済み

### 文書間整合
- 計画書（本書）・auto_test.md・manual_test.md・review.md を同時作成済み。設計（計画駆動 test・scoped staging）変更時は 4 文書を同時更新する。
