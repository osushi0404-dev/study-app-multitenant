# I109 計画書: 依存脆弱性ドリフトの定期検知 — develop への scheduled 監査（pip-audit / npm audit）と fail 時の自動起票

## 基本情報
- **計画書ID**: plan_I109
- **関連イシュー**: #205（ローカル: docs/issues/open/I109.md）
- **Draft PR**: #211
- **作成根拠資料**: docs/issues/open/I109.md（起点イシュー・設計確認メモで方式確定済み）
- **実装後評価**: docs/reviews/closed/I109_review.md
- **作成日**: 2026-07-15

## 1. 背景/目的
- 依存の既知脆弱性チェック（pip-audit / npm audit）が PR 時 CI でのみ実行されるため、リポジトリ無変更でも時間経過で発生する新規 CVE（環境ドリフト）の検知が「誰かが PR を出した時」まで遅延し、全 PR の CI が一斉 fail して無関係イシューをブロックする（実証: I108 / Pillow CVE 5件・2026-07-14）。
- GitHub Actions の scheduled workflow で develop に対し毎日監査を実行し、fail 時に GitHub イシューを自動起票（重複防止付き）することで、露出期間を最大 24 時間に短縮し、PR 契機の一斉ブロックを予防する。

### 調査結果（事前調査・ツール実走）
- **ツール実走（grill 時 2026-07-15）**: `pip-audit -r requirements.txt`（backend）= **0 件**。`npm audit --audit-level=critical --omit=dev`（frontend）= critical **0 件**（high 7 / moderate 7 / low 10 の計 24 件は critical 未満で exit 0）。→ **CI と同一条件の定期監査は初日からグリーン**で、導入直後の計画外修正は発生しない。24 件の滞留は別イシュー対応とユーザー決定済み（I109 スコープ外）。
- **環境前提確認**: `gh` 認証済み（osushi0404-bot・repo/workflow スコープ）。actionlint / yamllint はホスト未インストール → YAML 検証は PyYAML（`python3 -c "import yaml"` 確認済み）＋ grep 不変条件で行う。pip-audit はホスト venv で実走確認済み・CI では `backend/requirements-dev.txt` の `pip-audit==2.10.0` を使用（workflow も同一の導入経路にする）。
- **リポジトリ状態**:
  - default branch = `main`（README.md のみ）。GitHub Actions の `schedule` / `workflow_dispatch` は **default branch 上に workflow 定義がないと発火・実行できない**（GitHub 仕様）。→ default branch を develop へ切り替える（イシュー設計確認メモで確定・オーナー手作業）。
  - `.github/dependabot.yml`（I028）は default branch 外のため現在不活性。develop 化により weekly version updates が有効化される副作用がある（後述 Risk）。
  - bot アカウントは admin 権限なし → default branch 切替・（必要時の）Actions 権限設定はオーナーのブラウザ操作。
- **未実証の外部挙動（スパイク二分岐 (2) 該当）**: 「schedule / workflow_dispatch が default branch 化された develop 上の workflow で実際に発火・実行できること」「Actions の `GITHUB_TOKEN` で `gh issue create` が成功すること（リポジトリの Workflow permissions 設定に依存）」は稼働中セッションでは実証不能（workflow が default branch にマージされて初めて実行可能になるため）。→ **未実証と明記**し、実装ステップ1（default branch 切替＋検証）を前提ゲート、develop マージ後の live 検証（手動テスト Phase B）を後続ゲートとする。不成立なら計画をやり直す。
- **既存テストの事前実行**: 本イシューはアプリコード・アプリテストに触れない（workflow YAML＋シェルスクリプト＋runbook のみ）ため、backend pytest / frontend Jest のベースライン実行は対象外。関連するベースラインは上記の監査ツール実走（完了）。既存の `scripts/claude/tests/*.sh` 群には影響しない（新規テストスクリプトを追加するのみ）。

## 2. 受け入れ条件（イシューの AC を転記）
- [ ] default branch が develop に変更されている（オーナー手作業・schedule 発火の前提）
- [ ] scheduled workflow が毎日 JST 7:00（cron `0 22 * * *` UTC）に develop（`ref: develop` 明示）へ PR ゲートと同一条件の監査（`pip-audit -r requirements.txt` / `npm audit --audit-level=critical --omit=dev`）を実行する
- [ ] 監査 fail 時に GitHub イシューが自動起票される（ラベル `dependency-audit`・GITHUB_TOKEN に issues:write 権限）
- [ ] 監査種別（backend / frontend）ごとに open イシュー最大 1 本に抑止される（既存 open があれば新規作成せずコメント追記）
- [ ] workflow_dispatch による手動トリガーで検知動作（グリーン時・fail 時の両方）を検証済み
- [ ] 検知時の運用手順（自動起票 → /issue-bootstrap でローカル I### 起票）が runbook に記載されている

## 3. 影響範囲
- Backend: なし（コード変更なし）
- Frontend: なし（コード変更なし）
- DB: なし
- Config/Infra:
  - `.github/workflows/dependency-audit.yml`（新規）
  - `scripts/claude/dependency-audit-issue.sh`（新規・起票/重複防止ロジック）
  - `scripts/claude/tests/test_i109_dependency_audit.sh`（新規・決定論ゲート）
  - `docs/runbooks/dependency-audit.md`（新規・検知時運用）＋ `CLAUDE.md` の参照先リストに 1 行追記
  - リポジトリ設定（GitHub 上・ファイル外）: default branch main → develop（オーナー手作業）・ラベル `dependency-audit` 作成（`gh label create`）
  - 副作用: default branch の develop 化により既存 `.github/dependabot.yml` の weekly version updates が有効化される（Risk 参照）
- 依存関係ファイル（requirements*.txt / package*.json）の変更なし → Dockerfile / docker-compose.yml への波及なし

## 4. 変更点一覧（具体）

### 4-1. `.github/workflows/dependency-audit.yml`（新規）
**修正方針**: PR ゲート（ci.yml の Backend Lint & Security / Frontend Lint & Security）と**同一ツール・同一条件**の監査を、schedule（毎日 JST 7:00）と workflow_dispatch（手動検証用）で実行する。fail 時のみ起票スクリプトを呼ぶ。simulate_failure 入力は fail 経路の live 検証用テストフック（choice 制限で誤用防止）。

```yaml
name: Dependency Audit

on:
  schedule:
    - cron: '0 22 * * *'  # UTC 22:00 = JST 翌朝 7:00（毎日）
  workflow_dispatch:
    inputs:
      simulate_failure:
        description: '検知動作テスト用: 監査を強制 fail させる対象'
        type: choice
        options: [none, backend, frontend]
        default: none

permissions:
  contents: read
  issues: write

jobs:
  backend-audit:
    name: Backend Dependency Audit
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
        with:
          ref: develop   # default branch がどちらでも監査対象を develop に固定
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
          cache-dependency-path: backend/requirements-dev.txt
      - name: Install dev dependencies
        run: pip install -r backend/requirements-dev.txt
      - name: pip-audit
        working-directory: backend
        run: |
          if [ "${{ inputs.simulate_failure }}" = "backend" ]; then
            echo "SIMULATED FAILURE (workflow_dispatch テスト)" | tee /tmp/audit_backend.txt
            exit 1
          fi
          set -o pipefail
          pip-audit -r requirements.txt 2>&1 | tee /tmp/audit_backend.txt
      - name: Report failure as issue
        if: failure()
        env:
          GH_TOKEN: ${{ github.token }}
        run: bash scripts/claude/dependency-audit-issue.sh backend /tmp/audit_backend.txt

  frontend-audit:
    name: Frontend Dependency Audit
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
        with:
          ref: develop
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
      - name: npm audit
        working-directory: frontend
        run: |
          if [ "${{ inputs.simulate_failure }}" = "frontend" ]; then
            echo "SIMULATED FAILURE (workflow_dispatch テスト)" | tee /tmp/audit_frontend.txt
            exit 1
          fi
          set -o pipefail
          npm audit --audit-level=critical --omit=dev 2>&1 | tee /tmp/audit_frontend.txt
      - name: Report failure as issue
        if: failure()
        env:
          GH_TOKEN: ${{ github.token }}
        run: bash scripts/claude/dependency-audit-issue.sh frontend /tmp/audit_frontend.txt
```

設計メモ:
- 判定一貫性: pip-audit は CI と同じ `requirements-dev.txt`（`pip-audit==2.10.0` 固定）経由で導入し、コマンドも ci.yml と同一。npm audit はレジストリの advisory DB と package-lock.json だけで判定される（node_modules 不要）ため `npm ci` は省略する（判定は CI と同一・実行時間短縮）。
- schedule 実行時は `inputs.simulate_failure` が空文字になり、比較は不成立 → 通常監査が走る（テストフックは schedule 経路に影響しない）。
- `${{ inputs.simulate_failure }}` は choice 型（3 値固定）のためシェル展開インジェクションの余地なし。

### 4-2. `scripts/claude/dependency-audit-issue.sh`（新規）
**修正方針**: 起票・重複防止ロジックを workflow YAML から分離し、ローカルで gh スタブによる決定論テストを可能にする（YAML 内ベタ書きだと live 実行以外で検証不能）。重複防止は「監査種別ごとに open 最大 1 本」: ラベル `dependency-audit` の open イシューをタイトル前方一致（アンカー付き・完全プレフィックス）で検索し、既存があればコメント追記・なければ新規作成。

```bash
#!/usr/bin/env bash
# I109: scheduled 依存監査 fail 時の GitHub イシュー自動起票（重複防止付き）
# 使い方: dependency-audit-issue.sh <backend|frontend> <監査出力ファイル>
# 前提: GH_TOKEN（issues:write）。GitHub Actions からは github.token を渡す。
set -euo pipefail

KIND="${1:?usage: dependency-audit-issue.sh <backend|frontend> <audit-output-file>}"
OUT_FILE="${2:?usage: dependency-audit-issue.sh <backend|frontend> <audit-output-file>}"
case "$KIND" in backend|frontend) ;; *) echo "KIND は backend|frontend のみ" >&2; exit 2 ;; esac
[ -f "$OUT_FILE" ] || { echo "監査出力ファイルが存在しない: $OUT_FILE" >&2; exit 2; }

LABEL="dependency-audit"
TITLE_PREFIX="[dependency-audit] ${KIND}:"
TITLE="${TITLE_PREFIX} 依存脆弱性を検知（scheduled audit）"

BODY_FILE="$(mktemp)"
trap 'rm -f "$BODY_FILE"' EXIT
{
  echo "## 検知内容（$(date -u +%Y-%m-%dT%H:%M:%SZ) UTC）"
  echo '```'
  cat "$OUT_FILE"
  echo '```'
  echo ""
  echo "## 対応手順"
  echo "docs/runbooks/dependency-audit.md を参照（/issue-bootstrap でローカルイシュー化して対応する）。"
} > "$BODY_FILE"

# 重複防止: 同種（KIND）の open イシューが既にあればコメント追記、なければ新規作成
# --limit 50: gh issue list の既定上限 30 に暗黙依存しない（通常運用の open は種別ごと最大 1 本）
EXISTING="$(gh issue list --label "$LABEL" --state open --limit 50 --json number,title \
  --jq "[.[] | select(.title | startswith(\"${TITLE_PREFIX}\"))][0].number // empty")"

if [ -n "$EXISTING" ]; then
  gh issue comment "$EXISTING" --body-file "$BODY_FILE"
  echo "既存イシュー #${EXISTING} にコメント追記（重複起票を抑止）"
else
  gh issue create --title "$TITLE" --label "$LABEL" --body-file "$BODY_FILE"
  echo "新規イシューを起票"
fi
```

設計メモ:
- タイトル判定は固定プレフィックス `[dependency-audit] backend:` / `[dependency-audit] frontend:` の startswith（完全プレフィックス一致）で行い、部分一致誤判定（HIGH⊂HIGHRISK 型）を避ける。
- 監査出力（CVE 情報）は公開情報のみで機密は含まない（public リポジトリのイシューに掲載可）。

### 4-3. `scripts/claude/tests/test_i109_dependency_audit.sh`（新規・決定論ゲート）
**修正方針**: (a) workflow YAML の構文（PyYAML）と不変条件（cron 値・`ref: develop`・`issues: write`・workflow_dispatch）を grep で検証、(b) 監査コマンドの CI 同一性は **ci.yml とのペア検証**で行う（`pip-audit -r requirements.txt` / `--audit-level=critical --omit=dev` が `.github/workflows/ci.yml` と `dependency-audit.yml` の**両方**に存在することを検証。ci.yml 側の将来変更による乖離も自動検知する）、(c) 起票スクリプトの重複防止分岐を **gh スタブ**（PATH 差し替え・応答固定・呼び出しログ記録）で「既存なし→create のみ」「既存あり→comment のみ」の両分岐とも検証する。検証対象パスは環境変数 `I109_TEST_WF` / `I109_TEST_SCRIPT` で差し替え可能にし（既定は実ファイル）、false-green 注入検証（TC-02）は**実ファイルを改変せず一時コピーの破壊**で行う。既存 `scripts/claude/tests/test_*.sh` の慣例（exit 0/非ゼロ・OK/NG 行出力）に従う。全 TC の合否判定・期待値は docs/tests/open/I109_auto_test.md に記載（→ TC-01〜TC-03 参照）。

### 4-4. `docs/runbooks/dependency-audit.md`（新規）＋ `CLAUDE.md` 1 行追記
**修正方針**: 検知時運用を自己完結で記述する（文脈ゼロのセッションが読んで対応できる状態）。
- 仕組みの概要（毎日 JST 7:00・develop 対象・fail 時に `[dependency-audit]` イシュー起票/追記）
- 検知時の対応手順（イシュー確認 → `/issue-bootstrap` でローカル I### 起票 → 通常イシューフローで対応 → 解消後に dependency-audit イシューを close）
- 手動実行方法（`gh workflow run dependency-audit.yml`・`simulate_failure` はテスト専用である旨）
- 検知漏れ・workflow 自体の失敗時の確認方法（`gh run list --workflow=dependency-audit.yml` / Actions タブ）
- 前提（default branch = develop。main に戻す場合は develop → main マージ後なら schedule は継続する）
- CLAUDE.md の「運用・ルール」リストに `- 依存監査（定期検知）: docs/runbooks/dependency-audit.md` を追記

### 4-5. リポジトリ設定（ファイル外・GitHub 上）
- default branch main → develop: **オーナー（osushi0404-dev）がブラウザで実施**（Settings → General → Default branch）。bot は admin 権限なしのため代行不可。
- ラベル作成: `gh label create dependency-audit --description "scheduled 依存監査の自動起票" --color D93F0B`（既存なら skip・冪等に実行）。

## 5. 実装手順（ステップ）

1. **【前提ゲート・Human】default branch を develop に変更**（オーナーがブラウザで Settings → General → Default branch を変更）→ 完了確認は TC-M1/M2 参照。**このステップの完了が全後続ステップの前提**（未完のまま進めると schedule / workflow_dispatch が発火せず Phase B 検証が不能）。未実証の外部挙動（§調査結果）をここと Phase B で実証し、不成立なら計画をやり直す。
2. ラベル `dependency-audit` を作成（冪等: 既存確認の上 `gh label create`）→ TC-M3 参照。
3. `scripts/claude/dependency-audit-issue.sh`・`.github/workflows/dependency-audit.yml`・`scripts/claude/tests/test_i109_dependency_audit.sh` を新規作成（4-1〜4-3 のコード例どおり）→ TC-01〜TC-03 参照（TC-02 の false-green 注入検証を含めて実行・記録）。
4. `docs/runbooks/dependency-audit.md` 新規作成＋ `CLAUDE.md` に参照 1 行追記（4-4 のとおり）→ TC-04 参照。
5. コミット・プッシュし、PR #211 の CI がグリーンであることを確認 → TC-M4 参照。
6. **【Phase B・develop マージ後】** workflow_dispatch による live 検証（グリーン経路・fail 経路・重複防止・テスト残骸のクリーンアップ）→ TC-M5〜M9 参照。**注**: workflow_dispatch は workflow が default branch（develop）上に存在して初めて実行可能になるため、本ステップのみ「ユーザーテスト → マージ」の通常順序の**後**（クローズ処理のマージ直後・GitHub イシュークローズ前）に実施する順序特例とする（理由と代替不能性は Risk 参照）。

依存関係: ステップ1 は独立（Human・いつでも実施可だがステップ6 までに必須）。ステップ2〜5 は逐次。ステップ6 はステップ5 と develop マージの完了が前提。

## 6. テスト計画
### 自動（docs/tests/open/I109_auto_test.md）
- 決定論ゲート: `bash scripts/claude/tests/test_i109_dependency_audit.sh`（YAML 構文・不変条件 grep・gh スタブによる重複防止 2 分岐）
- false-green 注入検証: 不変条件を一時的に壊した入力で非ゼロ終了を確認（TC-02・実装ステップ3 内で実行・記録）
- 注: 本計画の TC は実装成果物（workflow/スクリプト）を対象とするため、計画承認時点では未実行（対象未作成）。実装ステップ内で全件実行・記録する。
### 手動（docs/tests/open/I109_manual_test.md）
- Phase A（マージ前）: default branch 切替（Human）＋検証・ラベル存在・PR CI グリーン（Claude）
- Phase B（マージ後）: workflow_dispatch の live 検証 — グリーン実行でイシュー 0 件・simulate_failure=backend で起票・再実行でコメント追記（重複防止）・テストイシューのクローズ（Claude）

## 7. ロールバック
- workflow / スクリプト / runbook / CLAUDE.md 追記行の削除（revert コミット 1 つ）。
- ラベル `dependency-audit` は残しても無害（完全撤去する場合は `gh label delete dependency-audit`）。
- default branch はオーナーが Settings で main に戻せる（戻すと本 workflow の schedule も再び不活性化する点に注意）。
- データ・DB・アプリコードへの影響なし（Danger Ops 無し）。

## 8. Risk & 回避策
| Risk | 影響 | 回避策 |
|------|------|--------|
| workflow_dispatch / schedule は default branch 上の workflow しか実行できず、live 検証がマージ前に不能 | fail 経路・重複防止の live 検証がマージ後になる | Phase B を順序特例としてクローズ処理内（マージ直後・イシュークローズ前）に組込み、失敗時は即修正イシュー化。マージ前は gh スタブの決定論テスト（TC-03）で同ロジックを検証済みにする |
| リポジトリの Actions Workflow permissions が read-only 設定だと `permissions: issues: write` がキャップされ起票が 403 | 自動起票が失敗 | Phase B の TC-M6 で検証。失敗時はオーナーがブラウザで Settings → Actions → General → Workflow permissions を確認・変更（Human 対応を runbook に記載） |
| default branch の develop 化で既存 dependabot.yml（weekly version updates）が有効化され、更新 PR（最大 15 本/週）が発生 | PR ノイズ | I028 の本来意図の回復であり許容。初週に量を観察し、過多なら設定調整（open-pull-requests-limit 削減等）を別イシュー化 |
| GitHub 高負荷時に schedule 実行がスキップ・遅延され得る（GitHub 既知挙動） | その日の検知漏れ | daily 実行のため翌日リカバー。手動実行手順と実行履歴確認（gh run list）を runbook に記載 |
| 同日に backend/frontend 両方 fail すると 2 本起票される | 想定内 | 仕様どおり（監査種別ごとに 1 本。両種別 fail は独立事象として別イシューが正しい） |
| 自動起票イシューの放置 | 検知しても対応されない | runbook に「open の dependency-audit イシューは毎朝のコメント追記で更新され続ける」ことを明記し、対応導線（/issue-bootstrap）を記載 |

## 11. 運用設計（バッチ＝scheduled workflow があるため）
- 構造化ログ: GitHub Actions の実行ログに集約（`gh run list --workflow=dependency-audit.yml` / `gh run view <id> --log`）。起票スクリプトは「新規起票/コメント追記」を stdout に明示。
- タイムアウト: 各ジョブ `timeout-minutes: 15`（通常 2〜5 分想定）。
- リトライ: 実装しない（daily 実行が実質リトライ。任意時点で workflow_dispatch 手動実行可）。
- Feature Flag / 段階リリース: 不要（workflow ファイル削除＝即無効化。切り戻しはロールバック参照）。

## 12. コスト・保守見積もり（新規インフラ＝scheduled workflow があるため）
- 実行コスト: public リポジトリのため GitHub Actions 無料。実行時間 ~5 分/日 × 2 ジョブ。
- 運用者の手作業: 検知時のみ（イシュー確認 → /issue-bootstrap）。平常時ゼロ。初期設定でオーナーのブラウザ操作 1 回（default branch 切替）。
- 属人化リスク: runbook（dependency-audit.md）に運用を自己完結で記載し抑止。構成は YAML＋シェル 計 ~150 行で保守負荷小。要件（daily 監査＋起票）に対し過剰な構成ではない（外部サービス・常駐インフラの追加なし）。

## セキュリティ・品質チェック（承認前必須確認の結果）
- **認可・最小権限**: workflow の GITHUB_TOKEN は `permissions: contents: read, issues: write` に明示制限（最小権限）。新規シークレット追加なし。
- **入力**: `simulate_failure` は choice 型 3 値固定でインジェクション余地なし。起票スクリプトの引数は workflow 内部由来のみ・KIND は許可リスト検証。
- **機密データ**: 扱わない。イシュー本文の監査出力は公開 CVE 情報のみ（public リポジトリ掲載可）。
- **依存追加**: なし（pip-audit は既存 requirements-dev.txt の固定版を使用）。
- **スキャン基準**: 本イシューが導入する監査自体の基準 = PR ゲートと同一（pip-audit 全件 fail / npm audit critical のみ fail）。シェルは pre-commit の shellcheck 対象。
- OWASP/XSS/SQLi/CSRF: 該当なし（アプリコード変更なし）。
- **P3（データ整合性）/ P9（プライバシー）影響なし**（DB・個人情報・テナントデータに触れない）。**P6（性能・UX）影響なし**（UI なし・アプリ性能に無関係）。
- **マルチテナント制約**: 該当なし（アプリの業務ロジック変更なし）。
- **テストレベル**: ユニット相当＝gh スタブの決定論テスト（TC-03）/ 結合相当＝workflow_dispatch live 検証（Phase B）。認可テスト＝GITHUB_TOKEN 権限は TC-M6 で live 検証。バグ修正イシューではないため再発防止テストは該当なし（予防装置そのものが本イシュー）。

## 9. 承認ポイント
- [ ] 計画内容（変更点/影響範囲: workflow＋起票スクリプト＋決定論テスト＋runbook 新規、アプリコード変更なし）
- [ ] **前提ゲート**: default branch main → develop の切替を**オーナーがブラウザで実施**すること（実施タイミングは承認後いつでも可・Phase B までに必須）
- [ ] **順序特例**: workflow_dispatch の live 検証（Phase B）を develop マージ後（クローズ処理内・GitHub イシュークローズ前）に実施すること
- [ ] 副作用の許容: dependabot.yml の weekly version updates が有効化されること（ノイズ過多なら別イシューで調整）
- [ ] 仮定で決めた設計判断（下記「設計判断の明示」）の承認
- [ ] Danger Ops: 無し（データ削除・破壊的マイグレーション・大量更新なし。ロールバックはファイル削除＋設定復帰のみ）
- [ ] テスト計画（自動: 決定論ゲート＋false-green 注入検証 / 手動: Phase A・B 2 段階）

## 設計判断の明示（イシュー明記 / 仮定の区別）
| 設計判断 | 出所 |
|---------|------|
| 方式=scheduled workflow・cron 毎日 JST7:00・重複防止=種別ごと open 1 本・判定レベル=CI 同一・default branch 切替・ラベル名 dependency-audit・2 段階起票運用 | **イシューに明記**（設計確認メモ） |
| workflow ファイル名 `dependency-audit.yml` | **イシューに明記**（実装対象） |
| 起票ロジックを `scripts/claude/dependency-audit-issue.sh` に分離（ローカル決定論テストを可能にするため） | **仮定**（イシューは workflow のみ記載。根拠: YAML ベタ書きだと live 実行以外で検証不能） |
| テスト用 `simulate_failure` 入力の追加 | **仮定**（AC「fail 時の検知動作を検証済み」を再現可能にする唯一の安全な手段） |
| runbook は新規 `docs/runbooks/dependency-audit.md`＋CLAUDE.md 参照 1 行（backend-check.md への追記ではなく） | **仮定**（イシューは「対象 runbook は計画時に確定」と委任。BE/FE 両方を跨ぐため専用 runbook が適切） |
| イシュータイトル形式 `[dependency-audit] <kind>: 依存脆弱性を検知（scheduled audit）` | **仮定**（重複判定のアンカーとなる固定プレフィックス） |
| ジョブ timeout-minutes: 15・npm ci 省略（npm audit は lockfile のみで判定） | **仮定**（判定結果に影響しない実行効率の選択） |
| Phase B をマージ後実施とする順序特例 | **仮定**（GitHub 仕様上の制約による。Risk 表参照） |

## レビュー結果
- [20260715_1744 判定: ✅ 完了](../../reviews/closed/I109_plan_review_20260715_1744.md)

## 完了情報
- **完了日時**: 2026-07-15
- **対応者**: Claude Code
- **レビュー結果**: OK（code-review VERDICT: OK・I109_code_review_20260715_1856.md）
