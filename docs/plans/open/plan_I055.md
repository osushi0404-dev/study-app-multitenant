# plan_I055: pre-commit に静的チェックを追加し npm audit を CI に組み込んでコード品質・依存関係セキュリティを自動保証する

## 基本情報
- **計画書ID**: plan_I055
- **関連イシュー**: #114
- **作成根拠資料**: docs/proposals/automation_over_manual_checks_proposal.md（イシュー①）
- **実装後評価**: （未作成）
- **作成日**: 2026-04-28

---

## 1. 背景/目的

現在のワークフローでは以下の問題がある：

- flake8・bandit・ESLint は CI でのみ実行され、pre-commit フックに含まれていないため「コミット前に手動実行してください」という手順が `/implement` SKILL.md に残っている
- npm audit は CI 未設定・手動実行ルールのみで、フロントエンド依存関係の脆弱性が PR ゲートで自動保証されていない
- pip-audit は手動手順すら存在しない空白地帯
- bandit の除外設定が CI の CLI 引数に散在しており、pre-commit との設定乖離リスクがある
- CI で pre-commit と同じチェックを個別ステップで再実装しているため、設定が二重管理になっている

本イシューでこれらを自動化し、機械的チェックをツールに完全委譲する。

---

## 2. 調査結果

### テストベースライン（Docker 経由）
- **Backend**: 25 passed, 3 warnings（DeprecationWarning のみ）
- **Frontend**: 7 passed, 2 suites

### lint ベースライン
- **flake8**: 0 errors（`backend/setup.cfg` の設定が適用済み）
- **bandit**: CI で確認済み（pass 状態）
- **ESLint**: 12 problems（0 errors, 12 warnings）— すべて `eslint-plugin-security` の `detect-object-injection` 警告（`QuizManagement.tsx:724`）。エラーは 0 件。

### npm audit 現状
- **high/critical 合計**: 27件
- **`npm audit fix` で修正可能**: 16件（axios, express, flatted, glob, jsonpath 等）
- **修正不可**: 11件（すべて `react-scripts` のトランザクティブ依存）
  - `@svgr/plugin-svgo`, `@svgr/webpack`, `css-minimizer-webpack-plugin`, `css-select`, `nth-check`, `react-scripts`, `rollup-plugin-terser`, `serialize-javascript` 等
  - CRA の EOL 問題であり CRA を使い続ける限り解消不可
  - CI 閾値は `--audit-level=critical`（high は react-scripts 問題で恒常的に出るため）

### Ruff 互換性（ステップ1実行済み）
- 実行コマンド: `pipx run ruff check backend/ --select E,F,W --line-length 120 --exclude "*/migrations/*" --exclude staticfiles --statistics`
- 検出違反: **E501 × 8件**（行長超過、すべて日本語文字列を含む行）
- Ruff 固有の新規違反: **ゼロ**（E501 は flake8 も同条件で検出する pre-existing issue）
- **判定: Step 2A（Ruff 移行）に進む**

### detect-secrets 現状
- `e2e/.auth/` は `e2e/.gitignore` に記載済み → JWT ファイルは git 追跡対象外（対応済み）
- detect-secrets はデフォルトで JWT パターンを検出しない → ステップ7で確認・対応

---

## 3. 受け入れ条件

- [ ] `git commit` 時に Ruff（または flake8）/ bandit / ESLint が自動実行され、エラーがあればコミットがブロックされる
- [ ] CI の lint ジョブは `pre-commit run --all-files` を実行する（個別ツールステップを削除）
- [ ] CI の `frontend-lint` ジョブで `npm audit --audit-level=critical` が実行される
- [ ] CI の `backend-lint` ジョブで `pip-audit` が実行される
- [ ] bandit の除外設定が `backend/setup.cfg` の `[bandit]` セクションに集約されている
- [ ] `detect-secrets` の JWT 検出状況を確認し、対応方針を `docs/runbooks/pre-commit.md` に記録している
- [ ] `/implement` SKILL.md 手順2 から手動 lint・audit の実行指示が「pre-commit / CI が自動実行」に書き換えられている
- [ ] `docs/runbooks/pre-commit.md` のフック一覧が最新の状態に更新されている
- [ ] コーディング規約ドキュメント冒頭に「linter が自動強制する範囲（ツール名・参照先）」と「手動レビュー対象（設計判断・マルチテナント制約・パフォーマンス設計等）」の両方が明示されている
- [ ] Backend テスト: 25 passed 以上（ベースライン維持）
- [ ] Frontend テスト: 7 passed 以上（ベースライン維持）
- [ ] CI の全ジョブが pass する

---

## 4. 影響範囲

| 層 | 変更ファイル |
|----|------------|
| Config | `.pre-commit-config.yaml`、`backend/setup.cfg`（`[flake8]` 削除・`[bandit]` 追加）、`backend/pyproject.toml`（新規: Ruff 設定）、`backend/requirements-dev.txt` |
| CI | `.github/workflows/ci.yml` |
| Frontend | `frontend/package.json`（`overrides` 追加、`npm audit fix` による `package-lock.json` 更新） |
| Skills | `.claude/skills/implement/SKILL.md` |
| Docs | `docs/runbooks/pre-commit.md`、`rules/ultimate_django_coding_standards.md`、`rules/react-coding-standards-integrated.md` |
| DB | なし |

---

## 5. 実装手順

### ステップ1【完了】Ruff 互換性確認（ブロッキング判断）

実行コマンド（`pipx run` をホストで実行。Ruff は静的解析のみで実行環境に依存しないため Docker 不要）:
```bash
pipx run ruff check backend/ --select E,F,W --line-length 120 \
  --exclude "*/migrations/*" --exclude staticfiles --statistics
```
> **注**: `W503`・`E203` は flake8 固有コードで Ruff には存在しないため `--ignore` 不要。

**結果: E501 × 8件（Ruff 固有違反ゼロ）→ Step 2A（Ruff 移行）に進む**

### ステップ2A【Ruff 移行】backend/setup.cfg・requirements-dev.txt を更新

**2A-0: E501 を修正する（8件、すべて日本語文字列を含む行）**

以下の 8箇所を文字列分割または変数抽出で 120文字以内に収める:
- `backend/core/management/commands/analyze_logs.py:230`
- `backend/problems/ai_generator.py:69`
- `backend/problems/serializers.py:290`
- `backend/problems/utils.py:86`
- `backend/problems/utils.py:258`
- `backend/studylogs/mistake_analysis.py:318`
- `backend/studylogs/mistake_analysis.py:330`
- `backend/studylogs/mistake_analysis.py:390`

修正後に再チェック:
```bash
pipx run ruff check backend/ --select E,F,W --line-length 120 \
  --exclude "*/migrations/*" --exclude staticfiles
# → Found 0 errors を確認
```

**2A-1: `backend/requirements-dev.txt` の `flake8` を `ruff` に置き換え**
```
ruff==0.15.12
bandit==1.7.9
pip-audit==x.x.x
```

**2A-2: `backend/setup.cfg` の `[flake8]` セクションを削除し `backend/pyproject.toml` に移行**

```toml
[tool.ruff]
line-length = 120
exclude = ["*/migrations/*", ".venv", "staticfiles"]

[tool.ruff.lint]
select = ["E", "F", "W"]
```
> **注**: `W503`・`E203` は Ruff に存在しないルールのため `ignore` 不要。

### ステップ2B【flake8 維持の場合】requirements-dev.txt に bandit 設定集約のみ

現状維持。ステップ3へ進む。

### ステップ3 bandit 設定を `backend/setup.cfg` に集約

`backend/setup.cfg` に `[bandit]` セクションを追加（bandit 1.7.x は INI 形式の setup.cfg をサポートする）：
```ini
[bandit]
skips = B101
exclude_dirs = migrations,tests
level = 2  # MEDIUM 以上（-ll 相当）
```

**設定読み込み検証（必須）**: `[bandit]` セクション追加後、以下で正しく読み込まれることを確認する：
```bash
# 自動検出で設定が適用されるか確認（出力に "[bandit] section" または設定値が含まれるか）
docker compose exec backend bandit -r . -f txt 2>&1 | head -10
```

出力に設定が反映されていない（空またはデフォルト値のみ）場合は `--configfile` を明示するフォールバックを使用する:
```bash
docker compose exec backend bandit -r . --configfile setup.cfg -f txt 2>&1 | head -10
```

`ci.yml` の bandit コマンドから除外引数を削除し、設定ファイル自動読み込みに変更。自動検出が確認できなかった場合は `--configfile setup.cfg` を明示する:
```yaml
- name: bandit
  run: bandit -r .          # または bandit -r . --configfile setup.cfg
  working-directory: backend
```

### ステップ4 pip-audit をベースライン確認・CI 追加

```bash
# Docker 内で pip-audit をインストールしてベースライン確認
docker compose exec backend pip install pip-audit
docker compose exec backend pip-audit -r requirements.txt
```

結果を確認し、既知の問題には `--ignore-vuln VULN-ID` を付与する方針を決定してから CI に追加する。

`backend/requirements-dev.txt` に追記：
```
pip-audit==x.x.x
```

### ステップ5 npm audit fix・overrides 設定

```bash
cd frontend
npm audit fix              # 16件の自動修正可能な脆弱性を修正
```

`frontend/package.json` に `overrides` を追加して react-scripts のトランザクティブ依存を安全なバージョンに固定：
```json
"overrides": {
  "nth-check": ">=2.0.1",
  "postcss": ">=8.4.31"
}
```

修正後の状態を確認：
```bash
npm audit --audit-level=critical
```

### ステップ6 pre-commit フック追加

`.pre-commit-config.yaml` に以下を追加（Ruff 採用の場合は Ruff フック、flake8 維持の場合は flake8 フック）：

**Ruff 採用の場合:**
```yaml
- repo: https://github.com/astral-sh/ruff-pre-commit
  rev: v0.x.x
  hooks:
    - id: ruff
      args: [--fix]
```

**flake8 維持の場合:**
```yaml
- repo: https://github.com/PyCQA/flake8
  rev: 7.0.0
  hooks:
    - id: flake8
      language_version: python3
```

**bandit（共通）:**
```yaml
- repo: https://github.com/PyCQA/bandit
  rev: 1.7.9
  hooks:
    - id: bandit
      args: ["-c", "backend/setup.cfg"]
      files: ^backend/
      exclude: ^backend/.*/migrations/|^backend/.*/tests/
```

**ESLint（共通）:**
```yaml
- repo: local
  hooks:
    - id: eslint
      name: ESLint
      language: system
      entry: bash -c 'cd frontend && npx eslint src/ --ext .ts,.tsx --max-warnings 0'
      pass_filenames: false
      files: ^frontend/src/
```
> **設計根拠**: `language: system` を採用することで既存の `frontend/node_modules` をそのまま使用できる。`language: node` では `additional_dependencies` にすべての ESLint プラグイン（eslint-plugin-security 等）を列挙する必要があり、WSL2 環境での環境差異リスクが高い。

### ステップ7 detect-secrets JWT 検出確認

```bash
# detect-secrets の現在の設定確認
cat .secrets.baseline | python3 -m json.tool | grep -i "plugin"
```

JWT パターンが検出対象外の場合は、`.secrets.baseline` を再生成して JWT 検出を有効化する：
```bash
# detect-secrets の利用可能プラグインを確認
detect-secrets scan --list-all-plugins

# JwtTokenDetector が利用可能な場合、baseline を再生成
detect-secrets scan --use-all-plugins > .secrets.baseline
detect-secrets audit .secrets.baseline  # 誤検知を除外
```

対応結果（追加 or 不要・理由）を `docs/runbooks/pre-commit.md` に記録する。

### ステップ8【最重要】CI を `pre-commit run --all-files` に統一

`.github/workflows/ci.yml` の `backend-lint` ジョブと `frontend-lint` ジョブを以下のように変更：

```yaml
backend-lint:
  name: Backend Lint & Security
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: '3.11'
        cache: 'pip'
        cache-dependency-path: backend/requirements-dev.txt
    - name: Install dev dependencies
      run: pip install -r backend/requirements-dev.txt
    - name: pre-commit (lint & security)
      uses: pre-commit/action@v3.0.1
    - name: pip-audit
      run: pip-audit -r backend/requirements.txt
      working-directory: backend
    - name: Check migration drift
      run: |
        pip install -r requirements.txt
        python manage.py makemigrations --check --dry-run
      working-directory: backend

frontend-lint:
  name: Frontend Lint & Security
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with:
        node-version: '18'
        cache: 'npm'
        cache-dependency-path: frontend/package-lock.json
    - name: Install dependencies
      run: npm ci
      working-directory: frontend
    - name: npm audit
      run: npm audit --audit-level=critical --omit=dev
      working-directory: frontend
```

> **設計根拠**: CI で `pre-commit run --all-files` を実行することで、ローカルと CI が完全に同じフックを実行することが保証される（設定の二重管理を解消）。個別の flake8・bandit・ESLint ステップは削除し、pre-commit 経由に統一する。

### ステップ9 ドキュメント更新（3ファイル）

**① `/implement` SKILL.md 手順2 の書き換え:**

削除対象（`.claude/skills/implement/SKILL.md` 手順2 の以下の行）：
```
   - Backend: flake8（全エラー修正）/ bandit（MEDIUM 以上を修正対象。LOW は # nosec で抑制・理由記載必須）/ 未使用変数・import の残留がないこと
   - Frontend: react-scripts build（型チェック）/ ESLint（error を修正対象、warning は記録）/ npm audit（high/critical を修正対象、moderate は記録・期限設定）
```

置き換え後：
```
   - lint・セキュリティスキャン・依存関係 CVE チェックは pre-commit（commit 時）と CI（PR 時）が自動実行する。手動実行は不要。
   - ビルド確認: react-scripts build（型エラーが出た場合は修正してから次のステップへ）
```

**② `docs/runbooks/pre-commit.md` フック一覧更新:**
追加した全フックを一覧に反映。detect-secrets JWT 対応方針を記録。

**③ コーディング規約冒頭に linter 範囲の参照を追記（2ファイル）:**
`rules/ultimate_django_coding_standards.md` と `react-coding-standards-integrated.md` の冒頭に以下のセクションを追加：

```markdown
## 自動強制範囲（linter が担当）
以下の規約項目は Ruff（または flake8）/ ESLint / TypeScript が自動検出・ブロックします。
設定の詳細は `backend/pyproject.toml`（Ruff）または `backend/setup.cfg`（flake8）および `frontend/package.json`（ESLint）を参照してください。
- 命名規則（変数・関数・クラス名のパターン）
- import 順序・未使用 import（Ruff / flake8）
- 未使用変数・型エラー（ESLint, tsc）
- セキュリティパターン（bandit, eslint-plugin-security）
- 依存関係の既知 CVE（pip-audit, npm audit）

## 手動レビュー対象（linter が検出できない項目）
以下は AI レビュー（/plan-issue-review・/code-review）および人間によるレビューの対象です:
- 設計パターン（Fat View 排除・サービス/セレクタパターンの適用等）
- マルチテナント制約（組織スコープ・閲覧範囲・操作範囲の制御）
- パフォーマンス設計（N+1・キャッシュ・ページネーション）
- 業務ロジック・ステータス遷移・エッジケースの考慮
- API 設計（URL 設計・レスポンス形式・エラーハンドリング方針）
```

---

## 6. テスト計画

### 自動テスト
- Backend: `docker compose exec backend python3 -m pytest --tb=short -q`（25 passed 以上）
- Frontend: `docker compose exec frontend npm test -- --watchAll=false`（7 passed 以上）

### 手動テスト
→ `I055_manual_test.md` 参照

---

## 7. ロールバック

設定ファイルの変更のみのため、`git revert` で即時ロールバック可能。
CI の個別ステップ削除は `git revert` で復元できる。
npm audit fix による `package-lock.json` の変更も `git revert` で戻せる。

---

## 8. Risk & 回避策

| リスク | 対策 |
|--------|------|
| Ruff が既存コードを大量に違反検出する | ステップ1で先行確認。違反あれば flake8 維持に切り替え |
| npm audit fix が既存テストを壊す | ステップ5後に Frontend テストを実行して確認 |
| pre-commit フックが遅すぎてコミットを妨害する | bandit は changed files のみ対象。ESLint は既存 12 warnings を事前に 0 件に修正したうえで `--max-warnings 0` を適用する（warnings が残った状態で適用すると既存コードがすべてブロック対象になるため順序が重要） |
| CI の `pre-commit run --all-files` がローカルと環境差異を出す | pre-commit の `rev` をすべてピン固定して再現性を保証 |
| pip-audit で既知の修正不可 CVE が見つかる | `--ignore-vuln VULN-ID` で明示的に除外し理由を requirements-dev.txt にコメント記録 |

---

## 9. セキュリティ・ベストプラクティスチェック

- **依存関係脆弱性**: npm audit（frontend）・pip-audit（backend）を CI に追加することで PR 単位で自動検出される
- **機密データ**: detect-secrets は既に有効。JWT 検出ギャップをステップ7で確認・対応
- **最小権限原則**: CI ジョブへの `permissions:` 追加は今回スコープ外（別途対応）
- **設定の一元管理**: bandit 設定を CLI 引数から setup.cfg に移行することで管理箇所を削減
- **P3/P5/P8 影響なし**: DB 変更なし・外部 API 変更なし・新規インフラリソースなし
- **P6 影響なし**: UI 変更なし

---

## 10. 承認ポイント

以下を確認してから「OK」をお願いします。

### 設計判断（仮定で決めた項目）
| 項目 | 判断内容 | 根拠 |
|------|----------|------|
| Ruff 移行の可否 | ステップ1実行後に決定（イシューに「確認して判断」と明記） | /grill-me 回答 |
| npm audit 閾値 | `--audit-level=critical`（high は react-scripts 問題で恒常的なため） | /grill-me 回答・実測値 |
| CI の lint 構成 | `pre-commit run --all-files` に統一（個別ステップ削除） | /grill-me 回答 |
| ESLint max-warnings | `0`（現在 12 warnings を 0 に修正してから pre-commit 追加） | ベストプラクティス |

### チェックリスト
- [ ] ステップ1 の Ruff 互換性確認でツール選定を決める運用に同意する
- [ ] npm audit 閾値を `--audit-level=critical` とする方針に同意する（high は react-scripts 問題として記録・管理）
- [ ] CI を `pre-commit run --all-files` に統一する方針に同意する
- [ ] ESLint の 12 warnings を 0 にしてから pre-commit フックを追加する運用に同意する


## レビュー結果
- [20260428_0117 ⛔ 差し戻し → 修正済み](../../reviews/I055_plan_review_20260428_0117.md)

- [20260428_0130 ✅ 完了](../../reviews/I055_plan_review_20260428_0130.md)
- [20260430_0056 ✅ 完了](../../reviews/I055_plan_review_20260430_0056.md)
