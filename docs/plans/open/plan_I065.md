# plan_I065: レビュー監査記録（IXXX_*_review_<ts>）のライフサイクル整理

## 基本情報
- **計画書ID**: plan_I065
- **関連イシュー**: #131
- **Draft PR**: #137
- **作成根拠資料**: docs/issues/open/I065.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I065_review.md（または未作成）
- **作成日**: 2026-06-17

---

## 1. 背景/目的

### 現状の問題
レビュースクリプト（`code-review.sh` / `plan-issue-review.sh` / `issue-review.sh`）が生成する
**timestamped 監査記録**（`I###_{code,plan,issue}_review_<ts>.md`）が `docs/reviews/` **直下**に
無制限に蓄積し、issue クローズ後も整理されない。

- 保存先（スクリプト実装・確認済み）:
  - `scripts/claude/code-review.sh:46` `REVIEW_FILE="docs/reviews/${ISSUE}_code_review_${TIMESTAMP}.md"`
  - `scripts/claude/plan-issue-review.sh:46` 同形式（`_plan_review_`）
  - `scripts/claude/issue-review.sh:14` 同形式（`_issue_review_`）
  - いずれも `docs/reviews/` 直下（`open/`・`closed/` の外）。
- `/close`（`.claude/skills/close/SKILL.md` step 1）が移動するのは
  `docs/reviews/open/I${NUM}_*.md`（= `IXXX_review.md` ライフサイクルファイル）のみ。
  **直下の timestamped 記録は移動対象外**で据え置かれる。
- 実測（2026-06-17 / develop ベース）: `ls docs/reviews/*.md | wc -l` = **64件**が直下に堆積
  （issue 起票時の記載は 52 件だったが、以後の I062〜I064 クローズで増加）。

### 根本原因
レビュー監査記録に**ライフサイクル管理が無い**。スクリプトが `open/closed` の外（直下）へ保存し、
`/close` もそれらを回収しないため「作りっぱなし」になる。
`IXXX_review.md`（open→closed 管理あり）と扱いが非対称。

### 解決方針（案A・/grill-me で確定。review スクリプトは触らない）
直下蓄積を解消し、`/close` を回収係にして issue 単位でライフサイクル管理する:
1. `.claude/skills/close/SKILL.md` に「当該 issue の `docs/reviews/I${NUM}_*_review_*.md` を `closed/` へ `git mv`」を追加。
2. 同 close 手順に「plan 内 `## レビュー結果` リンク `../../reviews/<basename>` → `../../reviews/closed/<basename>` 更新」を追加（Q3・リンク切れ防止）。
3. `docs/runbooks/review-rules.md` の「直下に蓄積・移動しない」記述をライフサイクル反映に更新（I064 整合・後述）。
4. 遡及整理（一度きり）: **クローズ済み issue（I054〜I064）の直下記録のみ `git mv` で `closed/` へ**。
5. open 中の I065〜I067 の記録は据え置き（各 `/close` 時に回収）。

---

## 2. 調査結果

### 環境前提確認
- `git` 利用可（`git mv` 履歴保持移動が前提）。本イシューは **markdown 編集＋ファイル移動のみ**。
  backend/frontend のコード変更なし。インストールを要するツールなし。

### クローズ状態の実測（遡及対象の確定）
イシュー本文は遡及対象を「I054〜I061」と記載していたが、執筆後に **I062・I063・I064 もクローズ済み**
となった（`docs/issues/closed/` に I062〜I064 実在 / `docs/plans/closed/` に plan 実在）。
これらの `/close` は既に実行済みで、本機能が無いため timestamped 記録が直下に取り残されている。
**ユーザー承認により、遡及対象を「現クローズ全件 I054〜I064」に確定**（取り残しゼロ）。

| 区分 | issue | 直下記録の有無 | 本イシューでの扱い |
|------|-------|----------------|--------------------|
| クローズ済み | I054, I055, I057, I058, I059, I060, I061, I062, I063, I064 | 有（後述件数） | **遡及で `closed/` へ移動** |
| open（進行中） | I065, I066, I067 | 各 1件（issue_review） | **据え置き**（各 `/close` で回収） |

> 注: I056 は欠番（issue 自体が存在しない）。

### 直下記録の件数（移動前ベースライン・2026-06-17 develop）

| issue | 直下件数 | issue | 直下件数 |
|------:|--------:|------:|--------:|
| I054 | 1 | I060 | 5 |
| I055 | 14 | I061 | 3 |
| I057 | 2 | I062 | 6 |
| I058 | 20 | I063 | 3 |
| I059 | 4 | I064 | 3 |

- **遡及対象（I054〜I064）合計 = 61件**
- **据え置き（open I065〜I067）= 3件**（`I065_issue_review_20260614_1432.md` / `I066_issue_review_20260617_0102.md` / `I067_issue_review_20260617_0107.md`）
- 直下総数 = 64件、`closed/` 既存 = 53件
- **期待最終状態**: 直下 = 3件（open のみ）、`closed/` = 53 + 61 = **114件**、総数保存 64+53 = 3+114 = **167件**（記録の消失なし）

### closed plan のリンク実在（リンク切れ防止対象）
I054〜I064 の `docs/plans/closed/plan_I###.md` はいずれも timestamped 記録への相対リンク
`](../../reviews/I###_{plan,code,issue}_review_<ts>.md)` を保持（`plan-issue-review.sh:101-102` が追記）。
リンク数: I054=1 / I055=9 / I057=1 / I058=12 / I059=2 / I060=2 / I061=1 / I062=3 / I063=1 / I064=1。
記録を `closed/` へ移動する際、対応する plan のこれらリンクも `closed/` 向きに更新しないとリンク切れになる。

### glob の安全性（lifecycle ファイルを誤回収しない）
回収 glob `I${NUM}_*_review_*.md` は timestamped 記録（`I062_code_review_<ts>.md` 等。
部分文字列 `_review_` を含む）に一致するが、ライフサイクルファイル `I062_review.md`
（`_review.` であって `_review_` を含まない）には**一致しない**。
よって `/close` の回収手順は `IXXX_review.md` を誤って動かさない（既存の open/closed 管理を侵さない）。

### review-rules.md の該当記述（I064 整合・要更新箇所）
`docs/runbooks/review-rules.md` の以下が「直下に蓄積・移動しない」を明記しており、本イシューの挙動変更と齟齬が出るため更新が必須:
- `:27-29` 監査記録3行の備考列「`docs/reviews/` 直下に時系列で蓄積（open/closed 管理外・移動しない）」「同上」
- `:38` 「timestamped 監査記録（…）: `docs/reviews/` 直下に蓄積する（open/closed の外。スクリプトが直下に保存し、移動しない）。」

---

## 3. 影響範囲
- **Backend**: なし
- **Frontend**: なし
- **DB**: なし
- **Config/Infra**:
  - `.claude/skills/close/SKILL.md`（回収・plan リンク更新手順の追加）
  - `docs/runbooks/review-rules.md`（ライフサイクル記述の更新・I064 整合）
  - 既存記録の遡及移動（`docs/reviews/I054〜I064_*_review_*.md` 61件 → `docs/reviews/closed/`）
  - 遡及移動に伴う `docs/plans/closed/plan_I054〜I064.md` のリンク更新
- **review スクリプト（`scripts/claude/{code-review,plan-issue-review,issue-review}.sh`）**: **変更なし**（案A・保存先は直下のまま。I062 と非衝突）
- close フローに関わるため、変更後は close 相当ロジックを sandbox で動作確認（TC-S1）。

### P3/P5/P8 影響
- セキュリティ影響なし（バックエンド・フロントエンドのコード変更なし）。`ISSUE_NUM` は既存の3桁数値バリデーション（`^[0-9]{3}$`）を踏襲しパストラバーサルを防止。
- P3（データ整合性: DB）影響なし。P5（運用設計: 外部API/非同期）影響なし。P8（コスト）影響なし。
- 依存関係ファイル（requirements*.txt / package*.json）の変更なし → Dockerfile/compose 波及なし。

### P6（性能・UX）影響
- UI なし・データ量/外部API 懸念なし → **P6 影響なし**。

---

## 4. 変更点一覧

| ファイル | 変更内容 |
|---------|---------|
| `.claude/skills/close/SKILL.md` | step 1 の bash ブロック末尾に (a) 直下 timestamped 監査記録を `closed/` へ `git mv`、(b) 対応 plan の `## レビュー結果` リンクを `closed/` 向きに `sed` 更新、の手順を追加 |
| `docs/runbooks/review-rules.md` | `:27-29` 備考列・`:38` の「直下に蓄積・移動しない」記述を「open 中は直下に蓄積、`/close` で当該 issue 分を `closed/` へ回収」に更新（I064 整合） |
| `docs/reviews/I054〜I064_*_review_*.md`（61件） | 一度きりの遡及 `git mv` で `docs/reviews/closed/` へ移動 |
| `docs/plans/closed/plan_I054〜I064.md` | 上記移動に伴い `## レビュー結果` の相対リンクを `../../reviews/closed/<basename>` へ更新 |
| `scripts/claude/*.sh`（review 3本） | **変更なし** |

---

## 5. 実装手順（ステップ）

> 各ステップの検証はすべて自動テスト文書（`I065_auto_test.md`）の TC として記述する。ステップ本文に検証コマンドは置かない。

### ステップ2: `/close` に回収＋リンク更新手順を追加（メカニズム本体）
**修正方針**: `/close` を timestamped 監査記録の「回収係」にする。`close/SKILL.md` の step 1 末尾
（`reviews/open/I${NUM}_*.md` 移動の後）へ以下を追記する。

```bash
   # timestamped 監査記録（直下）を closed/ へ回収（I065）
   # glob は IXXX_{code,plan,issue}_review_<ts>.md に一致。
   # IXXX_review.md（lifecycle・_review_ を含まない）には非マッチ＝誤回収しない。
   for f in docs/reviews/I${ISSUE_NUM}_*_review_*.md; do
     [ -f "$f" ] || continue
     base="$(basename "$f")"
     git mv "$f" docs/reviews/closed/
     # plan 内 ## レビュー結果 リンクを closed/ 向きに更新（リンク切れ防止・Q3）
     PLAN="docs/plans/closed/plan_I${ISSUE_NUM}.md"
     [ -f "$PLAN" ] && sed -i "s#(\.\./\.\./reviews/${base})#(../../reviews/closed/${base})#g" "$PLAN"
   done
```

- `[ -f "$f" ] || continue`: 該当記録が無い場合のリテラル glob 文字列を回避（冪等）。
- `sed` 区切りに `#` を使用（パスの `/` と衝突回避）。`base` は英数・`_`・`.` のみで sed メタ文字を含まない。
- → 振る舞いは **TC-S1** 参照。文言存在は **TC-01** 参照。
- 依存: なし（独立）。

### ステップ3: `review-rules.md` のライフサイクル記述更新（I064 整合）
**修正方針**: I064 が記述した「直下に蓄積・移動しない」現状を、本イシューの新挙動に合わせて更新。

- `:27-29` 備考列「`docs/reviews/` 直下に時系列で蓄積（open/closed 管理外・移動しない）」/「同上」
  → 「issue が open の間は `docs/reviews/` 直下に蓄積。`/close` 実行時に当該 issue 分を `closed/` へ回収（I065）」
- `:38` 「…直下に蓄積する（open/closed の外。スクリプトが直下に保存し、移動しない）。」
  → 「…issue が open の間は `docs/reviews/` 直下に蓄積し、`/close` が当該 issue 分を `closed/` へ回収する（スクリプトの保存先は直下のまま・移動は `/close` が担当）。」
- → 文言存在は **TC-02 / TC-03** 参照。
- 依存: なし（ステップ2と並行可）。

### ステップ4: 遡及整理（一度きり）— I054〜I064 の直下記録を `closed/` へ
**修正方針**: ステップ2と同型のロジックを、クローズ済み全 issue に対し一括で一度だけ実行する。
履歴保持のため `git mv`。移動前後で総数一致を確認（記録の消失防止）。

```bash
   for n in 054 055 057 058 059 060 061 062 063 064; do
     PLAN="docs/plans/closed/plan_I${n}.md"
     for f in docs/reviews/I${n}_*_review_*.md; do
       [ -f "$f" ] || continue
       base="$(basename "$f")"
       git mv "$f" docs/reviews/closed/
       [ -f "$PLAN" ] && sed -i "s#(\.\./\.\./reviews/${base})#(../../reviews/closed/${base})#g" "$PLAN"
     done
   done
```

- 期待: 61件移動 → 直下 64→3、`closed/` 53→114、総数保存。
- → 件数保存・リンク健全性は **TC-04 / TC-05 / TC-06** 参照。
- 依存: ステップ2のロジック設計に準拠（同型）。論理整合のためステップ2→4 の順で実施。

> **ステップ番号について**: 本イシューは「メカニズム追加（ステップ2-3）＋一度きりの遡及（ステップ4）」の構成。
> 新規 DB/API/UI レイヤーが無いため垂直スライスは「close メカニズム ＋ ドキュメント整合 ＋ 既存データ整理」の単位で縦に切っている。

---

## 6. テスト計画（自動/手動）
- **自動（`I065_auto_test.md`）**:
  - 静的/grep: `close/SKILL.md` の回収・リンク更新手順の存在（TC-01）、`review-rules.md` のライフサイクル記述更新（TC-02/03）、review スクリプト3本の保存先が不変（TC-07）。
  - 振る舞いスモーク: 一時 sandbox で回収＋リンク更新ロジックを実走し、record が `closed/` へ移動・plan リンクが `closed/` 化・lifecycle ファイル非回収を確認（TC-S1）。
  - 遡及検証: 実装後に 直下=3（open のみ）・`closed/`=114・総数保存（TC-04）、移動した記録の plan リンクにデッドリンクが無い（TC-05）、closed/ への移動で重複衝突が無かった（TC-06）。
- **手動（`I065_manual_test.md`）**: 実 `/close` 1件での回収動作確認（Human・将来 issue クローズ時の実走観察）。

### テストレベルの選択
- ユニット相当（grep 存在確認）＋ 結合相当（sandbox での move+sed 実走スモーク）。E2E 不要（UI なし）。
- 認証・認可・テナント境界の検証は対象外（コード変更なし・該当なし）。

---

## 7. ロールバック
- コミット前: `git checkout -- .` および `git status` で未追跡確認。`git mv` は作業ツリー操作のため未コミットなら `git reset` で復元可。
- コミット後: 当該コミットを `git revert`。ファイル移動・リンク編集はすべて git 管理下で可逆。
- review スクリプト・backend/frontend は不変のためサービス再起動不要。

---

## 8. Risk & 回避策
| Risk | 回避策 |
|------|--------|
| 回収 glob が `IXXX_review.md`（lifecycle）を誤って動かす | glob `*_review_*` は `_review_`（両端アンダースコア）必須。`IXXX_review.md` は `_review.` で非マッチ。TC-S1 で明示検証 |
| plan リンク更新で誤置換・二重 `closed/` | `sed` 区切り `#`、`base` は sed メタ文字を含まない英数のみ。`reviews/closed/<base>` は `reviews/<base>` を部分文字列に含まないため冪等。TC-S1/TC-05 で検証 |
| 遡及移動で記録が消失・件数不一致 | 移動前後の総数（直下+closed/）一致を TC-04 で機械検証。`git mv` で履歴保持 |
| 移動先 `closed/` に同名既存があり `git mv` 失敗 | `closed/` 既存53件に I054〜I064 の timestamped は無い（命名が一意）。TC-06 で衝突ゼロを確認 |
| I062〜I064 を遡及対象から漏らす（本文 literal 追従） | ユーザー承認で「現クローズ全件 I054〜I064」に確定。ステップ4の `n` リストに含める |
| I064 の review-rules.md 記述との齟齬 | ステップ3で同時更新（AC 5番）。順序整合 |

---

## 9. 承認ポイント（チェックリスト）

### 要件適合性・業務ロジック
- [ ] 計画は受け入れ条件（AC 5項目）の範囲内。仕様追加・拡大なし。
- [ ] マルチテナント/組織スコープ: 該当なし（ドキュメント・スキル運用のみ）。
- [ ] ステータス遷移: `IXXX_review.md`（open→closed）と timestamped 記録（直下→closed）の経路差を計画に明示済み。

### セキュリティ・ベストプラクティス
- [ ] **セキュリティ影響なし**（backend/frontend のコード変更なし）。`ISSUE_NUM` は既存の `^[0-9]{3}$` バリデーションを踏襲（パストラバーサル防止）。新規依存なし → pip-audit/npm audit 不要。bandit/semgrep 等のコードスキャン対象なし。

### テスト計画
- [ ] バグ（蓄積の放置）再発防止: `/close` 回収手順の振る舞い TC（TC-S1）と遡及件数保存 TC（TC-04）を含む。
- [ ] テストレベル選択（grep 静的＋sandbox 結合）を計画に明示済み。
- [ ] 認可変更なし → テナント境界テストは該当なし。

### データ整合性・運用性・コスト（P3/P5/P8）
- [ ] **P3/P5/P8 影響なし**（DB変更・外部API・新規インフラ・依存変更いずれも無し）。

### 性能・UX（P6）
- [ ] **P6 影響なし**（UI なし・データ量/外部API 懸念なし）。

### 設計品質
- [ ] アンチパターン不採用（スクリプトは触らず最小差分。/close を単一の回収係に集約）。
- [ ] 空値/不在の扱い統一: glob 非マッチ時 `[ -f ] || continue` で安全側。
- [ ] 設定値ハードコード回避: issue 番号は変数（`ISSUE_NUM` / 遡及は明示リスト）。

### 設計判断の明示（イシュー明記 / 仮定の区別）
- [ ] 案A（スクリプト不変・/close 回収係）: **イシュー明記**（Q1）。
- [ ] plan リンクを `closed/` 向きに更新: **イシュー明記**（Q3）。
- [ ] 回収 glob を `*_review_*` とし lifecycle ファイルを除外: **計画での設計判断**（実測で安全性確認済み・TC-S1 で検証）。
- [ ] 遡及対象を「現クローズ全件 I054〜I064」へ拡大: **ユーザー承認で確定**（本文の I054〜I061 から更新。理由＝I062〜I064 も既にクローズ済みで取り残されるため）。
- [ ] `review-rules.md` の同時更新: **イシュー明記**（AC 5番・I064 整合）。

### 文書品質ゲート（自己チェック済み）
- [ ] API/permission_classes/エラーレスポンス/DBフィールド: 本イシューに該当なし（コード変更なし）。
- [ ] 自動テストの期待値（件数・終了コード・移動先パス）を `I065_auto_test.md` に具体記載。
- [ ] 手動テストの期待結果を具体動作で記載。
- [ ] ステップ本文に検証コマンドを残していない（すべて TC に昇格）。

---

承認後の次のステップ: `/plan-issue-review I065` を実行して計画書・テスト文書をレビューする。
