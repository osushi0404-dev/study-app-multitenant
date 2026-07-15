# I113 計画書: /close に base 追従チェックを追加（pr-base-sync.sh 新設・mergeStateStatus 単一ソース）

## 基本情報
- **計画書ID**: plan_I113
- **関連イシュー**: #210（ローカル: docs/issues/open/I113.md）
- **Draft PR**: #219
- **作成根拠資料**: docs/issues/open/I113.md（起点イシュー・設計確認メモで方式確定済み）
- **実装後評価**: docs/reviews/open/I113_review.md
- **作成日**: 2026-07-16

## 1. 背景/目的

### 原因の概要
/close スキルには「PR が base（develop）の最新を含んでいるか」を確認する手順がなく、close 作業中〜マージ依頼後に別 PR が develop にマージされると、ブランチ保護（up-to-date 要求）で PR がマージ不能（out-of-date）になる。検知は人間の GitHub 画面目視頼み（fail-open）だった。

### 詳細な原因分析
- 実証事象（2026-07-15・I107/PR #202）: /close 完了時点で CI 全グリーンだったが、直後に PR #201（I103・app トラック）が develop にマージされ、PR #202 が out-of-date 化。ユーザー報告を受けて手動で fetch→merge→push→CI 再確認を実施した。
- 2 worktree 並行運用（wt-harness / study-app-multitenant）では、close 前後に他トラックの PR が base へマージされる事象は構造的に再発する。
- 根本原因: /close スキル（`.claude/skills/close/SKILL.md`）に base 鮮度の確認ステップ・確認タイミングの定義が存在しないこと。

### 修正アプローチ（全体像）
GitHub の判定値 `mergeStateStatus` を単一ソースとする決定論的チェックを **scripts/claude/pr-base-sync.sh** として新設し、/close の2箇所（step 0＝開始時・step 5 直後＝`gh pr ready` 後）から呼び出す。step 0 は**取り込みのみ**（push/CI なし・push は step 3 の close コミットに相乗り）、step 5 直後は**フルチェック**（BEHIND なら merge→push→CI 待機）。合格条件は「**BEHIND / DIRTY でない ＋ CI 全グリーン**」（本リポジトリはユーザー Approve がマージ条件のため、承認前の正常な最終状態は BLOCKED。CLEAN を要求すると正常系で永遠に合格しない）。コンフリクトは自動解決せず STOP（fail-closed）。

### 調査結果（事前調査）
- **環境前提確認**: `gh`（認証済み・本セッションで `gh pr view` / `gh issue edit` / `gh pr create` 実走済み）、`git`、`bash`、`timeout` はホストで動作確認済み（code-review.sh が同じ構成で稼働中）。新規インストールなし。
- **スパイク実証（2026-07-16・稼働中セッションで実施済み）**:
  - draft PR（#218）への個別照会 `gh pr view 218 --json mergeStateStatus` → **`BEHIND` が返る**（draft でも遅れは検知できる。DRAFT 値にマスクされない）
  - 一覧照会 `gh pr list --json mergeStateStatus` → 全 draft PR が **`UNKNOWN`**（計算が走らない）。**チェックは PR 番号指定の個別照会を使う**（設計確認メモに記録済み）
  - mergeStateStatus 全8値（BEHIND/BLOCKED/CLEAN/DIRTY/DRAFT/HAS_HOOKS/UNKNOWN/UNSTABLE）を GitHub GraphQL docs（reference/pulls の MergeStateStatus）と照合済み。分岐はイシュー「解決方針」に確定記載
- **決定論ゲートのベースライン実走（2026-07-16・TDD Red）**:
  - `grep -n "pr-base-sync" .claude/skills/close/SKILL.md` → **NO-HIT（exit 1）**（呼び出し文言の不在を検知できる）
  - `ls scripts/claude/pr-base-sync.sh scripts/claude/tests/test_pr_base_sync.sh` → **exit 2（両ファイル不在）**
  - 維持系ゲート文字列の現状 HIT 確認: `gh pr ready`（SKILL.md L132）・staged スコープガード文言（L116）は現状存在
- **既存テストの事前実行**: 本イシューはアプリコード・アプリテストに触れない（bash スクリプト＋スキル Markdown のみ）ため、backend pytest / frontend Jest のベースラインは対象外。既存 `scripts/claude/tests/*.sh` 群には影響しない（新規 1 本追加のみ）。
- **消費箇所の確認**: `gh pr checks` の pending 待機・fail STOP は code-review.sh（L214-237）に既存実装があり、同型ロジックを pr-base-sync.sh に持つ（コピー独立・code-review.sh は無改変）。/close SKILL.md を参照する他ファイルへの影響なし。

## 2. 受け入れ条件（イシューの AC を転記）
- [ ] scripts/claude/pr-base-sync.sh が新設され、mergeStateStatus の個別照会（`gh pr view <番号> --json mergeStateStatus`）・BEHIND 時の fetch/merge・コンフリクト時 STOP を実装している
- [ ] 同スクリプトが2モードを持つ: 取り込みのみ（push/CI なし・step 0 用）とフル（push＋CI 待機・step 5 直後用）
- [ ] フルモードの合格条件が「BEHIND / DIRTY でない ＋ CI 全グリーン」で実装されている（CLEAN 必須にしない）
- [ ] mergeStateStatus 全8値（CLEAN / BEHIND / BLOCKED / DIRTY / DRAFT / HAS_HOOKS / UNKNOWN / UNSTABLE）の分岐が設計確認メモの確定内容どおりに実装されている（UNKNOWN/DRAFT リトライ=5秒×6回・CI 待機=15秒間隔・上限600秒）
- [ ] .claude/skills/close/SKILL.md の step 0 と `gh pr ready` 直後（マージ依頼の前）の2箇所にスクリプト呼び出しが記載されている
- [ ] マージコンフリクト時（merge 失敗または DIRTY）は自動で進めず STOP してユーザーに報告する停止条件がスクリプト・SKILL.md の双方に明記されている
- [ ] scripts/claude/tests/test_pr_base_sync.sh が存在し、全ケース pass する（決定論ゲート）

## 3. 影響範囲
- Backend: なし（コード変更なし）
- Frontend: なし（コード変更なし）
- DB: なし
- Config/Infra:
  - `scripts/claude/pr-base-sync.sh`（新規・チェック本体）
  - `scripts/claude/tests/test_pr_base_sync.sh`（新規・決定論ゲート）
  - `.claude/skills/close/SKILL.md`（変更・step 0 と step 5 直後にスクリプト呼び出し追加）
- 依存関係ファイル（requirements*.txt / package*.json）の変更なし → Dockerfile / docker-compose.yml への波及なし
- **P3/P5/P8 影響なし**（DB変更・アプリの外部API/非同期/バッチ・新規インフラ/外部サービスなし。gh は既存導入済みツール）／**P6 影響なし**（UI・性能懸念なし）／**P9 影響なし**（個人情報・未成年・テナントデータを扱わない）
- **セキュリティ影響なし**（アプリコード変更なし。スクリプトは gh の既存認証情報を使う読み取り照会＋feature ブランチへの通常 git 操作のみ。新規権限・機密データ・依存ライブラリ追加なし。入力は引数の PR 番号とモード文字列のみで、モードは許可値 2 択を検証する）

## 4. 変更点一覧（具体）

### 4-1. `scripts/claude/pr-base-sync.sh`（新規・チェック本体）
**修正方針**: mergeStateStatus を単一ソースに、`sync`（step 0 用・取り込みのみ）と `final`（Ready 後用・フル）の2モードを実装する。終了コードで /close の進行を決定論的に制御する（0=続行 / 1=STOP / 2=UNKNOWN 上限・ユーザー確認）。リトライ間隔・CI 待機はイシュー確定値を既定とし、テストから環境変数（`PBS_*`）で上書き可能にする（I109/I114 の差し替え方式に準拠）。

```bash
#!/bin/bash
# I113: /close 用 base 追従チェック（mergeStateStatus 単一ソース・fail-closed）
# 使い方: bash scripts/claude/pr-base-sync.sh <sync|final> [PR番号]
#   sync  = /close step 0 用: BEHIND なら origin/<base> を merge するだけ（push/CI なし）
#   final = gh pr ready 直後用: BEHIND なら merge→push→CI 待機。
#           合格条件は「BEHIND/DIRTY でない ＋ CI 全グリーン」（CLEAN は要求しない＝Approve 待ちの BLOCKED は正常）
# 終了コード: 0=続行OK / 1=STOP（コンフリクト・CI fail・DRAFT 残留・未知値） / 2=UNKNOWN 上限（続行可否をユーザー確認）
set -u

MODE="${1:?Usage: pr-base-sync.sh <sync|final> [PR番号]}"
case "$MODE" in sync|final) ;; *) echo "⚠️ MODE は sync / final のみ: $MODE"; exit 1 ;; esac
PR_NUM="${2:-}"
if [ -z "$PR_NUM" ]; then
  PR_NUM=$(gh pr view --json number -q .number) || { echo "⚠️ PR を特定できません"; exit 1; }
fi

RETRY_INTERVAL="${PBS_RETRY_INTERVAL:-5}"   # UNKNOWN/DRAFT 再取得間隔（秒）＝イシュー確定値
RETRY_MAX="${PBS_RETRY_MAX:-6}"             # 再取得回数（計30秒）＝イシュー確定値
CI_INTERVAL="${PBS_CI_INTERVAL:-15}"        # CI ポーリング間隔（秒）＝code-review.sh と同値
CI_TIMEOUT="${PBS_CI_TIMEOUT:-600}"         # CI 待機上限（秒）＝code-review.sh と同値
LOOP_MAX="${PBS_LOOP_MAX:-3}"               # final の BEHIND 追従再チェック上限

BASE=$(gh pr view "$PR_NUM" --json baseRefName -q .baseRefName) || { echo "⚠️ baseRefName 取得失敗"; exit 1; }

# 取得失敗・空値は return 1（fail-closed）。エラーメッセージは >&2（$() にキャプチャさせない）
get_status() {
  local v
  v=$(gh pr view "$PR_NUM" --json mergeStateStatus -q .mergeStateStatus) || { echo "⚠️ mergeStateStatus 取得失敗" >&2; return 1; }
  [ -n "$v" ] || { echo "⚠️ mergeStateStatus が空値" >&2; return 1; }
  printf '%s\n' "$v"
}

# UNKNOWN（と final の DRAFT）は反映ラグの可能性があるためリトライして確定値を得る。
# 途中の取得失敗も return 1 で呼び出し元へ伝播する（fail-closed）
resolve_status() {
  local s i=0
  s=$(get_status) || return 1
  while [ "$i" -lt "$RETRY_MAX" ]; do
    case "$s" in
      UNKNOWN) ;;                                # 常にリトライ対象
      DRAFT) [ "$MODE" = "final" ] || break ;;   # sync では DRAFT は確定値（step 0 の正常状態）
      *) break ;;
    esac
    sleep "$RETRY_INTERVAL"; i=$((i+1))
    s=$(get_status) || return 1
  done
  echo "$s"
}

merge_base() {
  git fetch origin "$BASE" || { echo "⚠️ git fetch 失敗"; exit 1; }
  if ! git merge "origin/$BASE" --no-edit; then
    echo "⛔ マージコンフリクト。自動解決しません（fail-closed）。競合ファイル:"
    git diff --name-only --diff-filter=U
    git merge --abort
    echo "（作業ツリーは merge 前の状態に復元済み。解決方針をユーザーに確認してから再実行）"
    exit 1
  fi
}

ci_wait() {  # code-review.sh L214-237 と同型: pending 待機・fail 時 STOP
  local elapsed=0 out
  while :; do
    out=$(gh pr checks "$PR_NUM" 2>&1 || true)
    if echo "$out" | grep -q "fail"; then echo "⛔ CI 失敗:"; echo "$out"; exit 1; fi
    echo "$out" | grep -q "pending" || return 0
    if [ "$elapsed" -ge "$CI_TIMEOUT" ]; then echo "⚠️ CI タイムアウト（${CI_TIMEOUT}秒）"; exit 1; fi
    echo "  pending... ${elapsed}s / ${CI_TIMEOUT}s"
    sleep "$CI_INTERVAL"; elapsed=$((elapsed + CI_INTERVAL))
  done
}

if [ "$MODE" = "sync" ]; then
  # $() はサブシェルのため、resolve_status 内の失敗は || で親に伝播させる（fail-open 防止）
  S=$(resolve_status) || { echo "⛔ mergeStateStatus が取得できません。STOP してユーザーに報告"; exit 1; }
  case "$S" in
    BEHIND)  merge_base; echo "✅ base（origin/${BASE}）を取り込みました（push は step 3 の close コミットに相乗り）" ;;
    DIRTY)   echo "⛔ DIRTY（マージ不能・コンフリクト予測）。STOP してユーザーに報告"; exit 1 ;;
    UNKNOWN) echo "⚠️ UNKNOWN が ${RETRY_MAX} 回リトライ後も継続。続行可否をユーザーに確認"; exit 2 ;;
    *)       echo "✅ 追従不要（mergeStateStatus=${S}）" ;;   # CLEAN/HAS_HOOKS/BLOCKED/UNSTABLE/DRAFT
  esac
  exit 0
fi

# final モード
n=0
while :; do
  S=$(resolve_status) || { echo "⛔ mergeStateStatus が取得できません。STOP してユーザーに報告"; exit 1; }
  case "$S" in
    BEHIND)
      n=$((n+1))
      if [ "$n" -gt "$LOOP_MAX" ]; then echo "⛔ base が進み続けています（${LOOP_MAX} 回追従済み）。STOP してユーザーに報告"; exit 1; fi
      merge_base
      git push || { echo "⚠️ git push 失敗"; exit 1; }
      ci_wait ;;                                   # 追従後に再チェック（ループ先頭へ）
    DIRTY)   echo "⛔ DIRTY（コンフリクト）。STOP してユーザーに報告"; exit 1 ;;
    DRAFT)   echo "⛔ Ready 化後も DRAFT のまま（gh pr ready が効いていない可能性）。STOP してユーザーに報告"; exit 1 ;;
    UNKNOWN) echo "⚠️ UNKNOWN が ${RETRY_MAX} 回リトライ後も継続。続行可否をユーザーに確認"; exit 2 ;;
    BLOCKED|UNSTABLE) ci_wait; echo "✅ CI 全グリーン（${S}＝Approve 待ち等）。マージ依頼へ進めます"; exit 0 ;;
    CLEAN|HAS_HOOKS)  echo "✅ ${S}（マージ可・CI 通過）。マージ依頼へ進めます"; exit 0 ;;
    *)       echo "⚠️ 未知の mergeStateStatus: ${S}。STOP してユーザーに報告"; exit 1 ;;
  esac
done
```

全8値の分岐根拠（イシュー「解決方針」の確定内容と 1:1 対応）:
| 値 | sync（step 0） | final（Ready 後） |
|----|---------------|-------------------|
| CLEAN / HAS_HOOKS | 続行 | 合格（exit 0） |
| BEHIND | fetch+merge のみ（push/CI なし） | merge→push→CI 待機→再チェック（上限 LOOP_MAX 回） |
| BLOCKED | 続行（CI は step 3 以降で走る） | `gh pr checks` 併読: 全緑=Approve 待ちの正常（exit 0）・fail=STOP・pending=待機 |
| UNSTABLE | 続行（同上） | 同上（fail=STOP・pending=待機・全緑=exit 0） |
| DIRTY | STOP（exit 1） | STOP（exit 1） |
| UNKNOWN | 5秒×6回リトライ→継続なら exit 2 | 同左 |
| DRAFT | 正常・続行（step 0 は draft 中） | リトライ→残留なら STOP（exit 1） |

### 4-2. `.claude/skills/close/SKILL.md` — step 0 に sync モード呼び出しを追加
**修正方針**: 既存の baseRefName 確認ブロックに追記する（同じ確認タイミング・イシュー「制約・引き継ぎ情報」の統合方針）。終了コードごとの進行指示を明記する。

既存 step 0 のコードブロックを以下に変更:
```bash
gh pr view --json baseRefName --jq '.baseRefName'
# → "develop" であること。"main" の場合は以下で修正してから続行:
# gh pr edit <PR番号> --base develop

# base 追従チェック（I113）: BEHIND なら origin/develop を取り込む（push/CI はしない。
# push は step 3 の close コミットに相乗りさせ、CI 実行を1回にまとめる）
bash scripts/claude/pr-base-sync.sh sync
# exit 0 → 続行 / exit 1 → STOP してユーザーに報告（コンフリクト等・自動解決しない）
# exit 2 → mergeStateStatus=UNKNOWN が継続。値を報告し続行可否をユーザーに確認
```

### 4-3. `.claude/skills/close/SKILL.md` — step 5 直後に final モード呼び出しを追加
**修正方針**: `gh pr ready` の直後・マージ依頼（step 6）の直前に、新規 step として挿入する（最終防衛線＝I107 実証事象の捕捉点）。

```markdown
5.5) base 追従の最終チェック（マージ依頼の直前・必須）:
   ```bash
   bash scripts/claude/pr-base-sync.sh final
   # PR番号は省略可（step 0 と同じ・カレントブランチの PR を自動特定。明示指定も可）
   ```
   合格条件は「**BEHIND / DIRTY でない ＋ CI 全グリーン**」（CLEAN は要求しない。ユーザーの
   Approve がマージ条件のため、承認前の正常な最終状態は BLOCKED＝CI 全緑・承認待ちのみ）。
   - exit 0 → step 6 のマージ依頼へ進む
   - exit 1 → STOP してユーザーに報告（マージコンフリクト・CI fail・DRAFT 残留等。自動解決しない）
   - exit 2 → mergeStateStatus=UNKNOWN が継続。値を報告し続行可否をユーザーに確認
```

### 4-4. `scripts/claude/tests/test_pr_base_sync.sh`（新規・決定論ゲート）
**修正方針**: 実 GitHub に依存せず全分岐を検証するため、一時ディレクトリに **gh / git のスタブ**を置き `PATH` 先頭に挿して実行する（スタブは呼び出し引数をログに記録し、状態値はケースごとのキューから返す）。`PBS_*` を 0〜1 秒に上書きして高速実行する。1 ケースでも不一致なら非ゼロ終了（fail-closed）。テスト対象スクリプトのパスは `TARGET_SCRIPT="${TARGET_SCRIPT:-scripts/claude/pr-base-sync.sh}"` で外部注入可能にする（TC-02 の false-green 注入＝改変コピーへの差し替えに使う。I114 の `I114_TEST_SKILL` と同方式）。

検証ケース（期待終了コードと副作用の両方を検証）:
| # | モード | 状態系列（スタブ） | 期待 |
|---|--------|-------------------|------|
| T1 | sync | CLEAN | exit 0・git 呼び出しなし |
| T2 | sync | BEHIND | exit 0・`fetch origin develop`＋`merge origin/develop --no-edit` あり・push なし |
| T3 | sync | DIRTY | exit 1 |
| T4 | sync | DRAFT | exit 0（step 0 の正常状態・リトライしない） |
| T5 | sync | UNKNOWN×継続 | exit 2 |
| T6 | sync | UNKNOWN→BEHIND | exit 0・merge あり（リトライで確定値に到達） |
| T7 | final | CLEAN | exit 0 |
| T8 | final | BLOCKED＋checks 全緑 | exit 0（Approve 待ちの正常） |
| T9 | final | UNSTABLE＋checks fail | exit 1 |
| T10 | final | BEHIND（merge 成功）→BLOCKED＋checks 全緑 | exit 0・push あり |
| T11 | final | BEHIND＋merge 失敗（スタブで注入） | exit 1・`merge --abort` あり |
| T12 | final | DRAFT×継続 | exit 1（Ready 化不全の検知） |
| T13 | final | BEHIND 連続（LOOP_MAX=1 に上書き） | exit 1（追従ループ上限で STOP） |
| T14 | final | HOGE（未知値） | exit 1（fail-closed） |
| T15 | sync | gh pr view 失敗（スタブが exit 1） | exit 1（取得失敗の fail-open 防止） |
| T16 | final | gh pr view 失敗（同上） | exit 1（同上） |

## 5. 実装手順（ステップ）
- **ステップ1**: pr-base-sync.sh を新設する（4-1）。→ 構文検証は TC-03（`bash -n`）参照
- **ステップ2**: test_pr_base_sync.sh を新設し（4-4）、TC-01（T1〜T16 全 pass）と TC-02（false-green 注入: スクリプトの DIRTY 分岐を一時コピー上で `exit 0` に改変し `TARGET_SCRIPT` で差し替え→テストが NG を返すこと）を実行・記録する
- **ステップ3**: close SKILL.md へ 4-2 / 4-3 を反映する。→ TC-03（呼び出し文言 grep）参照
- **ステップ4**: 実機スモーク（manual M2/M3: 本イシュー自身の PR #219 に対する sync 実走・draft 状態での final 実走）を実施し記録する
- 依存関係: ステップ2 はステップ1 の完了が前提。ステップ3 はステップ1 と並行可（呼び出し先の実在はステップ1 で担保）。ステップ4 はステップ1〜3 の完了が前提
- 垂直スライス: スクリプト本体（ステップ1）→ ゲート（ステップ2）→ 消費箇所（ステップ3）→ 実機実証（ステップ4）で、単一トラックの縦貫通（ハーネス運用のみ・レイヤー分割なし）
- 未知リスク先行: 最大の未知（draft PR で BEHIND が取れるか・一覧照会の挙動）は**計画確定前にスパイク実証済み**（調査結果参照）。残る外部依存（`gh pr checks` の出力形式）は稼働中の code-review.sh で実証済みの同型ロジックを使う
- サービス再起動: 不要（bash スクリプト＋Markdown のみ）

## 6. テスト計画
- 自動: docs/tests/open/I113_auto_test.md（TC-01 スタブ決定論テスト T1〜T16・TC-02 false-green 注入・TC-03 SKILL.md 統合 grep＋構文検証）。テストレベル: ユニット相当（gh/git スタブによる分岐網羅）＋静的検証（grep / bash -n）。アプリのユニット/結合/E2E は非該当（アプリコード変更なし）
- 手動: docs/tests/open/I113_manual_test.md（Claude 実施 3 件＋Human 実施 1 件・非ブロック）。実 GitHub に対するスモーク（M2/M3）でスタブと実環境の乖離を補完する
- 再発防止テスト: I107 実証事象（close 後の BEHIND 見逃し）は T10（final: BEHIND→追従→合格）と M3 が捕捉。fail-open 回帰は T14（未知値 STOP）・T15/T16（取得失敗 STOP・plan review Blocker の再発防止）が捕捉
- 認可テスト: 非該当（認可変更なし）
- TDD 適用: ベースライン（Red）は計画時に実走済み（調査結果参照: 呼び出し文言 NO-HIT・スクリプト不在）。実装後に Green（T1〜T14 全 pass・grep 全 HIT）を確認する

## 7. ロールバック
- `git revert` でスクリプト2ファイル追加＋SKILL.md 変更のコミットを打ち消す（データ・DB・インフラ影響なし）
- 部分ロールバック可: SKILL.md の呼び出し2行を削除すれば挙動は従来どおり（スクリプトは呼ばれなければ無害）

## 8. Risk & 回避策
- **リスク1: `gh pr checks` の出力文字列（fail/pending）が gh CLI 更新で変わる** → 稼働中の code-review.sh と同型を維持し、変更時は両ファイルを同時更新する（plan-writing-rules「消費箇所の全件更新」）。乖離は M2/M3 の実機スモークでも検知される
- **リスク2: mergeStateStatus の反映ラグで誤判定** → UNKNOWN/DRAFT（final）はリトライ（5秒×6回）で吸収。継続時は exit 2/1 で fail-closed に倒し、勝手に進まない
- **リスク3: final の追従中に base が進み続けてループする** → LOOP_MAX（既定3回）で STOP しユーザーに報告
- **リスク4: スタブテストが実環境と乖離** → M2（sync 実走）/M3（draft での final 実走）の実機スモークで補完
- **リスク5: sync モードの merge で作業ツリーが汚れる** → コンフリクト時は競合ファイル一覧を表示後 `git merge --abort` で復元してから STOP（中途半端な競合状態を残さない）

## 9. 設計判断の明示
| 設計判断 | 根拠 |
|---------|------|
| 2箇所挿入（step 0=取り込みのみ / step 5 直後=フル）・push は step 3 相乗り | イシューに明記（/grill-me 設計確認メモで確定） |
| 合格条件「BEHIND/DIRTY でない＋CI 全グリーン」（CLEAN 非要求） | イシューに明記（同上） |
| 全8値の分岐・リトライ 5秒×6回・CI 待機 15秒/600秒 | イシューに明記（同上） |
| 個別照会を使う（一覧照会は UNKNOWN のまま） | イシューに明記（同上・スパイク実測） |
| ファイル名 pr-base-sync.sh / test_pr_base_sync.sh | イシューに明記（実装対象表） |
| 引数 IF（`<sync|final> [PR番号]`・番号省略時はカレントブランチの PR） | **仮定で決めた**（承認前確認 A1） |
| 終了コード 0=続行/1=STOP/2=UNKNOWN ユーザー確認 | **仮定で決めた**（承認前確認 A2） |
| コンフリクト時: 競合ファイル表示→`git merge --abort` で復元→STOP | **仮定で決めた**（承認前確認 A3） |
| final の BEHIND 追従再チェック上限 LOOP_MAX=3 | **仮定で決めた**（承認前確認 A4） |
| テスト方式: gh/git の PATH スタブ＋`PBS_*` 環境変数上書き | **仮定で決めた**（I109/I114 の差し替え方式に準拠・承認前確認 A5） |

## 10. 承認ポイント（ユーザー確認チェックリスト）
- [ ] **スコープ確認**: 変更は新規スクリプト2ファイル＋close SKILL.md の呼び出し追加のみ（イシュー実装対象表のとおり・拡大なし）
- [ ] **仮定 A1〜A5**（セクション9の「仮定で決めた」5件）の内容でよいか
- [ ] **step 5.5 の新設**: 既存 step 5（Ready 化）と step 6（マージ依頼）の間に挿入する構成でよいか
- [ ] コーディング規約（Django/React）: 本イシューはアプリコード変更なしのため非適用（bash は既存 shellcheck pre-commit が適用される）

## レビュー結果
- [20260716_0142 判定: 差し戻し（Blocker 1件）](../../reviews/I113_plan_review_20260716_0142.md)
