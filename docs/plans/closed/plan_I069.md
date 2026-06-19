# plan_I069: レビュー記録（timestamped review）の commit ライフサイクル根治

## 基本情報
- **計画書ID**: plan_I069
- **関連イシュー**: #141
- **Draft PR**: #143
- **作成根拠資料**: docs/issues/open/I069.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I069_review.md
- **作成日**: 2026-06-19

---

## 1. 背景/目的

### 原因の概要（平易な説明）
レビュー結果を書き出すスクリプト（`plan-issue-review.sh` / `code-review.sh` / `issue-review.sh`）は、
タイムスタンプ付きレビュー記録ファイルを**書く（`> file`）だけで git に commit していない**。
従来は `/close` の旧 broad な `git add` が、この未追跡ファイルを「ついで」に巻き込んで commit していたため、
close が記録ファイルを `git mv` で `closed/` へ移す時点では追跡済みになっていて成立していた。

ところが I067 で `/close` を **scoped `git add -u` ＋ 決定論ゲート**（未追跡を構造的に除外＝正しい挙動）へ変えたため、
broad add の副次効果が消え、「レビュー記録が未追跡のまま close に到達 → `git mv` が `fatal: not under version control` で失敗」
という潜在バグが顕在化した。**生成物（レビュー記録）の commit 責任が誰にも明示されていなかった**ことが根本原因。

### 詳細な原因分析（エラー発生の流れ）
1. `/issue-bootstrap` が `issue-review.sh` を実行 → `docs/reviews/I###_issue_review_<ts>.md` を**未追跡で**書き出す。
2. `/plan-issue-review` `/code-review` も `docs/reviews/I###_{plan,code}_review_<ts>.md` を**未追跡で**書き出す。
3. （I067 以前）`/close` の broad `git add` が、これら未追跡ファイルを偶然 staging → commit → 追跡済みになる。
4. （I067 以後）`/close` は `git add -u`（追跡済みの変更のみ）＋決定論ゲートに変更。未追跡ファイルは staging されない。
5. `/close` step 1 の `git mv docs/reviews/I###_..._review_<ts>.md docs/reviews/closed/` が**未追跡ファイルに対して失敗**:
   ```
   fatal: not under version control, source=docs/reviews/I067_code_review_20260618_1906.md
   ```
6. I067 close 実行中に手動 `git add`→`git mv` で回収して完走させた（暫定対処）。

### 問題の根本原因（コードレベル）
- `scripts/claude/plan-issue-review.sh:116` / `scripts/claude/code-review.sh:118` / `scripts/claude/issue-review.sh:57`
  はいずれも `printf '%s\n' "$REVIEW_CLEAN" > "$REVIEW_FILE"` で**書くだけ**（`git commit` を grep しても 0 件）。
- 生成物のコミット責任が broad add という曖昧な経路に暗黙依存していた。

### 解決方針（採用＝/grill-me 2026-06-19 確定）
- **案A（理想・根治）= 生産者がコミットする**: `plan-issue-review.sh` / `code-review.sh` は、review ファイルを書いた直後に
  **その1ファイルのみ**を path-scoped で `git add`→`git commit` する（feature ブランチ前提・auto-push しない・他 index/作業ツリーに触れない）。
  - **ブランチガード（本計画で確定・絶対ルール3 から導出）**: 保護ブランチ（`develop`/`main`/detached HEAD）上では commit せず
    未追跡のまま残す。無条件 commit だと万一 develop 上で実行された際に develop 直 commit（絶対ルール3 違反）になるため。
    未追跡で残ったものは close（案B）が回収する。
- **案A'＝ issue-review は commit しない**: `issue-review.sh` は `/issue-bootstrap` 中（多くは develop 上）に走るため、
  案A をそのまま適用すると develop 直 commit になる。よって commit せず未追跡のまま残し、回収は close（案B）に委ねる。
  意図をコメントで明記する。
- **案B（保険・単一回収点）= close が拾う**: `.claude/skills/close/SKILL.md` step 1 の timestamped 監査記録 回収ループで、
  `git mv` の**直前に** `git add -- "$f"` を入れ、未追跡（issue-review 等）でも `git mv` が失敗しないようにする。
  I067 導入の scoped staging（step 3 の `git add -u`）／決定論ゲートは**一切変更しない**。

### 採用理由 / 非採用
- 生産者がコミットする（案A）＝未追跡ウィンドウを根絶する根治。`set -e` 下でも review ファイルが作成時点で追跡される。
- 案B-only（close のみ回収）は close 失敗は直るが、作成〜close 間の未追跡ウィンドウ（ブランチ破棄で監査喪失）が残る対症療法のため非採用。
- 案A＋案A'＋案B（保険）の併用を採用。`.claude/skills/plan-issue/SKILL.md` は**変更対象外**（issue-review 記録の回収は close に集約）。

---

## 2. 受け入れ条件（Acceptance Criteria）
- [ ] **AC1**: I067 と同等の状況（scoped add 運用でレビュー記録が未追跡のまま close に到達）を再現し、
  `/close` の `git mv` が `fatal: not under version control` を起こさず完走する（→ TC-B1）。
- [ ] **AC2**: plan-issue-review / code-review の記録が、生成スクリプトによって追跡（commit）される（案A）。
  ただし保護ブランチ上では commit されず未追跡で残る（ブランチガード）（→ TC-A1・A1b・A2〜A5）。
- [ ] **AC3**: issue-review 記録が develop へ直 commit されない（案A'）ことが保証され、close（案B）で正しく回収される（→ TC-A6・A6b・TC-B1）。
- [ ] **AC4**: close の scoped staging／決定論ゲート（I067 導入分・step 3）が壊れていない
  （未追跡の無関係ファイルは依然巻き込まない／I### スコープ外 staged を拒否する）ことを回帰確認（→ TC-B2・TC-B3）。
- [ ] **AC5**: 変更スクリプトが shellcheck（pre-commit）を通過し、`bash -n` 構文チェックに合格する（→ TC-C1・TC-C2）。
- [ ] **AC6**: 既存 `test_review_verdict.sh`（PASS=55）が非退行（→ TC-C3）。

---

## 3. 影響範囲（Backend/Frontend/DB/Config）
- **Backend**: なし
- **Frontend**: なし
- **DB**: なし
- **Config/Infra**:
  - `scripts/claude/plan-issue-review.sh`（案A: ブランチガード付き commit ヘルパ追加・本体配線）
  - `scripts/claude/code-review.sh`（案A: 同上）
  - `scripts/claude/issue-review.sh`（案A': commit しない旨のコメント追記のみ。挙動変更なし）
  - `.claude/skills/close/SKILL.md`（案B: timestamped 回収ループに `git add -- "$f"` を1行追加）
  - `scripts/claude/tests/test_review_commit_lifecycle.sh`（新規・案A/案B の git fixture 単体テスト）
- **CI/Docker 波及**: なし（`scripts/claude` を参照する GitHub workflow・Dockerfile・docker-compose は存在しない＝grep 0 件）。
  pre-commit の shellcheck（`files: ^scripts/`）が変更スクリプトを検査する → shellcheck-clean 必須。

---

## 4. 変更点一覧（ファイル/関数）

| ファイル | 関数/箇所 | 変更内容 |
|---------|----------|---------|
| `scripts/claude/plan-issue-review.sh` | 新規 `commit_review_artifact()`（SOURCE_ONLY ガード上に定義） | 案A: 引数1ファイルのみ path-scoped で add→commit。保護ブランチ（develop/main/HEAD/空）はスキップ。非ブロック。 |
| 〃 | 本体（REVIEW_FILE 保存直後） | `commit_review_artifact "$REVIEW_FILE" "$ISSUE" "plan-review"` を配線 |
| `scripts/claude/code-review.sh` | 新規 `commit_review_artifact()`（同一実装） | 案A: 同上 |
| 〃 | 本体（REVIEW_FILE 保存直後） | `commit_review_artifact "$REVIEW_FILE" "$ISSUE" "code-review"` を配線 |
| `scripts/claude/issue-review.sh` | 本体（REVIEW_FILE 保存直後） | 案A': commit しない旨と理由（develop 直 commit 回避・close 案B が回収）をコメントで明記。**挙動変更なし** |
| `.claude/skills/close/SKILL.md` | step 1 timestamped 回収ループ | 案B: `git mv "$f" docs/reviews/closed/` の**直前**に `git add -- "$f"` を追加 |
| `scripts/claude/tests/test_review_commit_lifecycle.sh` | 新規 | 案A（ブランチガード・path-scoped・他 index 不可侵）／案B（未追跡回収）／回帰の git fixture 単体テスト |

### commit ヘルパ（案A）の設計（共通実装）
両スクリプトの `REVIEW_LIB_SOURCE_ONLY` ガード行より**上**に、テストから source 可能な形で定義する:

```bash
# 案A(I069): レビュー記録（生産物）は生産者がコミットする。引数の1ファイルのみを path-scoped で
# add→commit（他の index/作業ツリーに触れない・auto-push しない・後続 close が push）。
# ブランチガード: 保護ブランチ（develop/main/detached HEAD/取得失敗）では commit せず未追跡のまま残す
#   （develop 直 commit 禁止＝絶対ルール3。未追跡分は close 案B が回収）。
# 非ブロック: add/commit が失敗してもレビューフロー（呼び出し元）は止めない。
commit_review_artifact() {
  local file="$1" issue="$2" kind="$3" branch
  branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
  case "$branch" in
    develop|main|HEAD|"")
      echo "ℹ️ ブランチ '${branch:-detached}' のため ${file} は commit しません（close 案B が回収）。"
      return 0 ;;
  esac
  if ! git add -- "$file" 2>/dev/null; then
    echo "⚠️ git add 失敗（未追跡のまま・close 案B が回収）: ${file}"
    return 0
  fi
  git commit -q -m "docs(${issue}): ${kind} 記録" -- "$file" 2>/dev/null \
    || echo "⚠️ git commit 失敗（未追跡のまま・close 案B が回収）: ${file}"
  return 0
}
```

> 設計判断:
> - `git commit -- "$file"` でパス限定コミットするため、呼び出し前に staging 済みの**無関係ファイルは新コミットに含まれない**（他 index 不可侵）。
> - `case` の保護対象に `HEAD`（detached）・空文字（rev-parse 失敗）を含め、想定外コンテキストでの誤 commit を防ぐ。
> - 非ブロック（`return 0`）方針は既存スクリプトの「レビューフローを止めない」設計と一貫。失敗時は未追跡のまま残り close 案B が回収するため監査記録は失われない。

---

## 5. 実装手順（ステップ）

> 垂直スライス: 本イシューは「レビュー記録の commit ライフサイクル」という単一機能を、生産者（案A/A'）と回収点（案B）の
> 両端で薄く貫通する。未知リスクは無い（既存 bash スクリプト経路の踏襲）。TDD（新規の振る舞い＝スクリプトの commit 副作用）を適用する。

### ステップ1: 案A/案B のテストを先に作成（Red）
`scripts/claude/tests/test_review_commit_lifecycle.sh` を新規作成し、案A（commit_review_artifact）・案B（close 回収ループ）の
git fixture 単体テスト（TC-A1〜A6・TC-B1〜B3・TC-C1〜C3）を実装する。この時点では `commit_review_artifact` 未定義・close 未修正のため
該当 TC は Red（失敗）になることを確認・記録する。
→ 検証は TC-A1〜C3（自動テスト文書）参照。

### ステップ2: 案A 実装（plan-issue-review.sh / code-review.sh）
両スクリプトに `commit_review_artifact()` を `REVIEW_LIB_SOURCE_ONLY` ガード上に追加し、REVIEW_FILE 保存直後に配線する。
→ TC-A1〜A5 が Green になる。→ TC-A1〜A5 参照。

### ステップ3: 案A' 実装（issue-review.sh）
`issue-review.sh` の REVIEW_FILE 保存直後に「commit しない（develop 直 commit 回避・close 案B が回収）」旨のコメントを明記する（挙動変更なし）。
→ TC-A6 参照。

### ステップ4: 案B 実装（close/SKILL.md）
`.claude/skills/close/SKILL.md` step 1 の timestamped 回収ループで `git mv "$f" docs/reviews/closed/` の直前に
`git add -- "$f"` を追加し、`# 案B(I069):` のコメントを付す。I067 の scoped staging／決定論ゲート（step 3）は変更しない。
→ TC-B1〜B3 が Green になる。→ TC-B1〜B3 参照。

### ステップ5: 全テスト実行・静的解析（Green 確認）
新規テスト・既存テスト・shellcheck・bash -n を実行し全 PASS を記録する。
→ TC-A1〜C3 参照。

---

## 6. テスト計画（自動/手動）

### テストレベルの選択
- **ユニット（スクリプト単体・git fixture）**: 案A の commit_review_artifact、案B の回収ループ挙動を一時 git repo で検証（決定論的）。
  → 正とする自動テスト = `scripts/claude/tests/test_review_commit_lifecycle.sh`（TC-A1〜C3）。
- **結合/E2E**: 非該当（app コード変更なし。`/close` 全体フローは GitHub PR を要するため手動）。
- **既定テスト（pytest/Jest/Playwright）**: 非該当（Backend/Frontend/DB 変更なし）。`/test` 時に「非該当」と記録する。

### 認可・テナント境界テスト
- 非該当（認証・認可・テナントスコープの変更なし。スクリプト/スキル指示文の編集のみ）。

### 再発防止テスト（バグ修正の必須要件）
- AC1（`git mv` 完走）= TC-B1 が I067 の `fatal: not under version control` 再発を恒久的に検出する回帰テスト。

詳細は以下に分離記載:
- 自動: `docs/tests/open/I069_auto_test.md`（TC-A1〜A6・TC-B1〜B3・TC-C1〜C3）
- 手動: `docs/tests/open/I069_manual_test.md`

---

## 7. ロールバック
- スクリプト/スキル/テストの編集のみ。`git revert` で完全に元へ戻せる（DB・インフラ・外部サービスへの副作用なし）。
- 案A の commit ヘルパは非ブロック（失敗時 `return 0`）のため、万一の不具合でもレビューフロー本体は停止しない。
- サービス再起動不要（ランタイムコード非該当）。

---

## 8. Risk & 回避策

| Risk | 影響 | 回避策 |
|------|------|--------|
| commit ヘルパが想定外ブランチ（detached 等）で誤 commit | 絶対ルール3 違反 | `case` で develop/main/HEAD/空 をスキップ。TC-A4 で develop スキップ、TC-A5 で detached スキップを検証 |
| `git commit -- "$file"` が呼び出し前 staging 済みファイルを巻き込む | 他 index 汚染 | パス限定コミットで無関係 staged は含めない。TC-A3 で「事前 staged ファイルが新コミットに含まれない」ことを検証 |
| 案B の `git add` が close 決定論ゲート（step 3）を壊す | スコープ外巻き込み回帰 | step 3 は変更しない。回収対象は I### スコープの review のみ。TC-B2/B3 で回帰確認 |
| shellcheck（pre-commit）違反でコミット不可 | 実装ブロック | `SC2016`（正規表現リテラル）等は局所 disable。`git rev-parse`/`git add --` の安全な書式を使用。TC-C1 で確認 |
| commit ヘルパが空コミット/no-op で非ゼロ終了 | レビューフロー停止 | `|| echo`＋`return 0` で非ブロック化。TC-A2 で正常 commit、エラーパスは握りつぶし |

---

## 9. 承認ポイント（ユーザーが OK を返すチェックリスト）

### 設計判断の明示（イシュー明記 / 仮定 の区別）
- ✅ **案A = plan-issue-review/code-review が review 1ファイルを path-scoped commit**（イシュー明記・/grill-me 確定）
- ✅ **案A' = issue-review は commit しない（コメント明記）**（イシュー明記）
- ✅ **案B = close 回収ループに `git add` 追加（git mv 直前）**（イシュー明記）
- ✅ **plan-issue/SKILL.md は変更しない**（イシュー明記・回収は close に集約）
- ⚙️ **ブランチガード（develop/main/detached で commit スキップ）**: イシュー本文の案A は「feature ブランチ前提」とのみ記載。
  本計画で **絶対ルール3（develop/main 直 commit 禁止）から導出**して確定（無条件 commit の develop 直 commit リスクを構造的に排除）。
  → ユーザー確認済み（2026-06-19・「ブランチガード入り（推奨）」を選択）。
- ⚙️ **テストファイルは新規 `test_review_commit_lifecycle.sh`**（既存 `test_review_verdict.sh` とは分離）: 仮定（I062 名の既存ファイルに混在させず I069 を独立管理）。

### セキュリティ・ベストプラクティスチェック
- **セキュリティ影響なし**: Backend/Frontend/DB のコード変更なし。認証・認可・入力経路・機密データの扱いに変更なし。
- スクリプトは既存の read-only レビュー（`--tools "Read,Grep,Glob"`）経路を踏襲。commit は path-scoped（`git add -- "$file"` / `git commit -- "$file"`）で意図しないファイルを巻き込まない。
- 依存ライブラリの追加・更新なし（pip-audit/npm audit 非該当）。
- セキュリティスキャン: 静的解析は shellcheck（pre-commit）。bandit/npm audit は非該当（Python/JS アプリコード変更なし）。

### データ整合性・運用性・コスト（P3/P5/P8）
- **P3/P5/P8 影響なし**: DB 変更・外部 API・非同期/バッチ・新規インフラ・依存関係ファイル（requirements/package）変更なし。Dockerfile/docker-compose への波及なし（grep 0 件）。

### 性能・UX（P6）
- **P6 影響なし**: UI なし・データ量/外部 API 懸念なし。

### テスト計画チェック
- 再発防止テスト（TC-B1）あり。テストレベル（ユニット=git fixture／結合・E2E=非該当）を明示。認可/テナント境界テストは非該当（変更なし）。

### 設計品質チェック
- アンチパターン（broad add への逆戻り）を禁止し path-scoped を徹底。null/空ブランチ・detached を `case` で統一処理。例外処理は非ブロック方針で統一。ハードコード値なし（commit message は引数組み立て）。

---

承認後の次のステップ: `/plan-issue-review I069` を実行して計画書・テスト文書をレビューしてください。

## レビュー結果
- [20260619_1219 判定: ✅ 完了](../../reviews/closed/I069_plan_review_20260619_1219.md)

## 完了情報
- **完了日時**: 2026-06-19 19:38:15
- **対応者**: Claude Code
- **レビュー結果**: OK（plan-issue-review OK / code-review OK・Low 2件は自己修正/受容 / 自動テスト PASS=30 FAIL=0）
