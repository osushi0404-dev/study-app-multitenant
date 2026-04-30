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
- [ ] bandit の除外設定が `backend/.bandit`（INI 形式）に集約され、bandit の自動検出（`.bandit` INI 形式は bandit 1.7.x が自動検出）で CI・pre-commit の両方に適用されている
- [ ] `detect-secrets` の JWT 検出状況を確認し、対応方針を `docs/runbooks/pre-commit.md` に記録している
- [ ] `/implement` SKILL.md 手順2 から手動 lint・audit の実行指示が「pre-commit / CI が自動実行」に書き換えられている
- [ ] `docs/runbooks/pre-commit.md` のフック一覧が最新の状態に更新されている
- [ ] コーディング規約ドキュメント冒頭に「linter が自動強制する範囲（ツール名・参照先）」と「手動レビュー対象（設計判断・マルチテナント制約・パフォーマンス設計等）」の両方が明示されている
- [ ] Backend テスト: 25 passed 以上（ベースライン維持）
- [ ] Frontend テスト: 7 passed 以上（ベースライン維持）
- [ ] CI の全ジョブが pass する
- [ ] `docs/runbooks/plan-writing-rules.md` の事前調査セクションに「lint/audit/scan 系ツール導入イシューでは計画前にツールを実際に実行し副作用ファイルを列挙する」という原則が追加されている
- [ ] `.claude/review-agents/code-reviewer.md` に「CI 全ジョブ pass かつテスト結果欄空白 → /test 実施前の正常状態として Low 以下で扱う」という条件付き基準が追加されている

---

## 4. 影響範囲

| 層 | 変更ファイル |
|----|------------|
| Config | `.pre-commit-config.yaml`、`backend/setup.cfg`（`[flake8]` 削除）、`backend/pyproject.toml`（新規: Ruff 設定）、`backend/.bandit`（新規: bandit YAML 設定）、`backend/requirements-dev.txt` |
| CI | `.github/workflows/ci.yml` |
| Frontend | `frontend/package.json`（`overrides` 追加、`npm audit fix` による `package-lock.json` 更新）、`frontend/src/Login.tsx`（`<a href="#">` → `<button type="button">` に変更: ESLint `--max-warnings 0` 達成のために必要。アクセシビリティ上も正しい修正）、`frontend/src/pages/QuizManagement.tsx`（`eslint-disable-next-line security/detect-object-injection` を 3箇所追加: `--max-warnings 0` 達成のために必要。ランダムアクセスではなく定数インデックスで安全） |
| Skills | `.claude/skills/implement/SKILL.md` |
| Docs | `docs/runbooks/pre-commit.md`、`rules/ultimate_django_coding_standards.md`、`rules/react-coding-standards-integrated.md`、`docs/runbooks/plan-writing-rules.md`（ステップ11）、`.claude/review-agents/code-reviewer.md`（ステップ12） |
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

→ TC-03 参照（pre-commit run --all-files の pass を確認）

**2A-1: `backend/requirements-dev.txt` の `flake8` を `ruff` に置き換え**
```
ruff==0.15.12
bandit==1.7.9
pip-audit==2.10.0
pytest==8.3.4
pytest-django==4.9.0
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

### ステップ3 bandit 設定を `backend/.bandit`（YAML）に集約

bandit 1.7.x は `setup.cfg` を自動検出しないが、`.bandit` ファイルをプロジェクトレベルで自動検出する。INI 形式（`[bandit]` セクション）で作成すると `--configfile` 不要で自動適用される。

`backend/.bandit`（新規作成、INI 形式）:
```ini
[bandit]
skips = B101
exclude_dirs = migrations,tests
```

→ TC-11 参照（pre-commit run bandit --all-files の pass を確認）

**検証結果（実施済み）**:
```
[main] INFO Found project level .bandit file: backend/.bandit
[main] INFO Using ini file for skipped tests
[main] INFO cli exclude tests: B101
```
→ 自動検出・B101 skip 適用ともに確認済み。

`ci.yml` の bandit コマンドから CLI 除外引数を削除する（自動検出で代替）:
```yaml
- name: bandit
  run: bandit -r .
  working-directory: backend
```

### ステップ4 pip-audit ベースライン確認・依存関係アップグレード・CI 追加

**4-0: pip-audit ベースライン確認（実施済み）**

```bash
pipx run pip-audit -r backend/requirements.txt
```

結果: 58件の CVE が 7パッケージで検出。**すべてに修正バージョンが存在**するため `--ignore-vuln` は使用せず、全パッケージをアップグレードする。

**4-1: pytest を requirements.txt（本番）から requirements-dev.txt へ移動**

`requirements.txt` に pytest/pytest-django が混入しておりプロダクション Docker イメージの攻撃対象を増やしている。`requirements-dev.txt` に移動する。

**4-2: requirements.txt の依存関係アップグレード**

| パッケージ | 変更 | 理由 |
|---|---|---|
| Django 4.2.7 → 4.2.30 | LTS 内パッチ | 45件の CVE を修正 |
| DRF 3.14.0 → 3.15.2 | マイナー | CVE-2024-21520 |
| simplejwt 5.3.0 → 5.5.1 | マイナー | CVE-2024-22513 |
| python-dotenv 1.0.0 → 1.2.2 | マイナー | CVE-2026-28684 |
| Pillow 10.1.0 → 10.3.0 → **12.2.0** | マイナー→**メジャー（実装中に判明）** | CVE-2023-50447, CVE-2024-28219（10.3.0）+ CVE-2026-25990, CVE-2026-40192（12.2.0）。pip-audit が CI で 10.3.0 の新規 CVE 2件を検出。修正バージョンが 12.1.1/12.2.0 のみのため 12.2.0 に追加アップグレード。Backend テスト 25 passed でリグレッションなしを確認済み |
| gunicorn 21.2.0 → 22.0.0 | メジャー | CVE-2024-1135, CVE-2024-6827（HTTP インジェクション） |

**4-3: アップグレード後のリグレッション確認**

```bash
docker compose build backend
docker compose exec backend python3 -m pytest --tb=short -q
```

テストが通過したら pip-audit を CI に追加する。

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
  rev: v0.15.12
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
      files: ^backend/
      exclude: ^backend/.*/migrations/|^backend/.*/tests/
```
> `backend/.bandit`（INI 形式）が自動検出されるため `--configfile` 不要。
> **設計根拠（exclude の二重定義ではない理由）**: pre-commit の `exclude:` は pre-commit がファイルリストをフィルタする層（bandit に渡す前の段階）で機能する。`backend/.bandit` の `exclude_dirs` は bandit が直接呼ばれた場合（CI 直接実行・ローカル手動実行）に機能する。両者は異なる実行レイヤーを担うため冗長ではなく、どちらのコンテキストでも確実に除外されることを保証する多層防御。

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

### ステップ6b bandit Low 発見への対処（実装中に判明）

`pre-commit run --all-files` 実行時に bandit が 8件の Low severity 発見を検出し、exit 1 となることが判明。
pre-commit の bandit フックは `-ll` なしで実行するため Low 発見もブロックになる。
プランの方針「LOW は # nosec で抑制・理由記載必須」に従い、修正可能なものは修正し、受容するものはコードに根拠を記録する。

**発見一覧と処置方針:**

| ファイル | ルール | 処置 | 理由 |
|--------|--------|------|------|
| `core/enhanced_logging.py:247` | B110（try-except-pass） | **修正**: `except json.JSONDecodeError:` に変更 | `json.loads` が送出する例外は `json.JSONDecodeError` のみ。silent failure は debug を困難にする |
| `core/management/commands/watch_errors.py:69` | B110（try-except-pass） | **修正**: `except (ValueError, OSError):` に変更 | `int()` → `ValueError`、`read_text()` → `OSError` の組み合わせ。silent failure は debug を困難にする |
| `core/management/commands/watch_errors.py:7` | B404（subprocess import） | **修正**: `import subprocess` を削除 | `call_command` への置き換えで subprocess 自体が不要になる |
| `core/management/commands/watch_errors.py:120` | B603/B607（subprocess.run） | **修正**: `call_command` + `StringIO` に置き換え | Django 慣用パターン。subprocess 不使用で B603/B607 の発生余地をなくす。`analyze_logs` は `self.stdout.write()` で出力するため `stdout=StringIO()` で完全捕捉可能（インターフェース確認済み） |
| `studylogs/adaptive_selection.py:435` | B311（random） | `# nosec B311` | 暗号用途ではなく学習アルゴリズムの探索的選択。`secrets` モジュールは不要 |
| `studylogs/adaptive_selection.py:467` | B311（random） | `# nosec B311` | 同上 |
| `studylogs/adaptive_selection.py:478` | B311（random） | `# nosec B311` | 同上 |

**`call_command` 置き換えの実装（`_analyze_error` メソッド）:**

```python
def _analyze_error(self, request_id):
    """エラーを詳細解析"""
    from io import StringIO
    from django.core.management import call_command
    try:
        output = StringIO()
        call_command('analyze_logs', request_id=request_id, format='claude', stdout=output)
        result = output.getvalue()
        return result if result else None
    except Exception as e:
        self.stdout.write(self.style.ERROR(f'エラー解析失敗: {e}'))
        return None
```

> `--request-id` → `request_id`、`--format` → `format` の変換は Django の `call_command` が自動処理する。
> `analyze_logs` の出力は全て `self.stdout.write()` 経由のため `stdout=StringIO()` で捕捉できることを確認済み。

**設計根拠（`-ll` フラグを採用しない理由）:**
`-ll`（MEDIUM+ のみ）をフック args に追加することは「LOW 発見を一括で非表示にする」ことになり、
将来の新規 Low 発見も検知されなくなる。プランの方針「LOW は # nosec で抑制・理由記載必須」は
「Low 発見に対して意識的な判断（修正 or 受容記録）を必須化する」という意図であるため、
`-ll` は方針をバイパスする。フックはデフォルト（LOW+）で動作させ、発見ごとに対処する。

**設計根拠（`call_command` を採用する理由）:**
`# nosec B603,B607` での抑制は bandit 1.7.9 のカンマ区切りパース挙動により B603 が抑制されないことが実装中に判明。
根本原因は `subprocess` を使った management command 呼び出しというアンチパターンであり、
Django 慣用の `call_command` に置き換えることで B404/B603/B607 の 3件が `# nosec` なしで消える。
これは抑制ではなく修正であり、コード品質も向上する。

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
    - name: Install dependencies
      run: |
        pip install -r backend/requirements.txt
        pip install -r backend/requirements-dev.txt
    - name: pre-commit (lint & security)
      uses: pre-commit/action@v3.0.1
      env:
        SKIP: eslint
    - name: pip-audit
      run: pip-audit -r requirements.txt
      working-directory: backend
      # 本番依存（requirements.txt）のみをスキャン対象とする。
      # 開発依存（requirements-dev.txt: ruff, bandit, pip-audit 自身等）は本番環境に含まれないためスコープ外。
    - name: Check migration drift
      run: python manage.py makemigrations --check --dry-run
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
    - name: ESLint
      run: npx eslint src/ --ext .ts,.tsx --max-warnings 0
      working-directory: frontend
    - name: npm audit
      run: npm audit --audit-level=critical --omit=dev
      working-directory: frontend
```

> **設計根拠（ESLint CI 実行経路）**: ESLint は `frontend-lint` ジョブで直接実行する。
> `backend-lint` の `pre-commit/action@v3.0.1` では Node.js 環境がないため ESLint フックを `SKIP=eslint` で除外し、
> `frontend-lint` で Node.js 環境を持つジョブが直接 `npx eslint` を実行することで確実に CI ゲートとなる。
>
> **設計根拠**: CI で `pre-commit run --all-files` を実行することで、ローカルと CI が完全に同じフックを実行することが保証される（設定の二重管理を解消）。個別の flake8・bandit ステップは削除し、pre-commit 経由に統一する。

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

### ステップ10 ワークフロー改善（コードレビュー指摘への対応）

**背景**: 本イシューの実装中、計画書ステップ3に「（必須）検証」として埋め込んだ bandit 自動検出の確認コマンドが、自動テスト文書の TC に昇格されなかったため実装時にスキップされた。コードレビューで後追い検知されたが、これは構造的な問題であるため以下の 3ファイルを変更して再発を防ぐ。

**変更方針（防御の深度）**:
- **予防（計画作成時）**: `plan-writing-rules.md` に規則定義 + `plan-issue` SKILL.md 文書品質ゲートに明示項目追加
- **検知（レビュー時）**: `code-reviewer.md` に確認観点追加

**① `docs/runbooks/plan-writing-rules.md` への追記:**

実装ステップの記述規則として以下を追加する:
```
計画書の実装ステップ内に「確認する」「検証する」等の検証コマンドを書かない。
検証手順は必ず自動テスト文書の TC として記述し、ステップ本文には「→ TC-XX 参照」と書く。
```

**② `.claude/skills/plan-issue/SKILL.md` 文書品質ゲートへの追記:**

既存の6項目チェックリストの末尾に以下を追加する:
```
- [ ] 計画書の各実装ステップ本文内に検証コマンドが残っていないか（ある場合は自動テスト文書のTCに昇格する）
```

**③ `.claude/review-agents/code-reviewer.md` への追記:**

コードレビューの確認観点として以下を追加する:
```
計画書の各実装ステップ本文内に「確認する」「検証する」等の検証コマンドが残っている場合、対応するTCが
自動テスト文書に存在し結果が記録されているか確認する（plan-writing-rules.md のルール遵守確認）
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


### ステップ11【予防処置 P1】plan-writing-rules.md への事前実行原則追記

I055 振り返りで特定した予防処置: lint/audit/scan 系ツール導入時に副作用ファイルが計画外変更になる根本原因への対処。

`docs/runbooks/plan-writing-rules.md` の「lint エラー数の事前計測」セクションに以下の原則を追加する:

```
lint/audit/scan 系ツール（pip-audit・npm audit・mypy・semgrep 等）を導入するイシューでは、
そのツールを計画書作成前に実際に実行し、検出された問題と修正必要ファイルを計画書に列挙する。
初回実行で初めて顕在化するエラー・CVE・警告を計画書作成時点で把握することで、計画外変更を防ぐ。
```

→ TC-15 参照

### ステップ12【予防処置 P2】code-reviewer.md へのテスト結果基準精密化追記

I055 振り返りで特定した予防処置: /code-review がフロー順序を知らずテスト結果欄空白を Medium 指摘した根本原因への対処。

`.claude/review-agents/code-reviewer.md` の P4 テスト妥当性セクションに以下の条件付き基準を追加する:

```
テスト結果文書（I###_auto_test.md）の結果欄が空白の場合、
CI が全ジョブ pass していれば /test スキル実施前の正常状態として Low 以下で扱う。
CI 未 pass またはテスト結果空白かつ CI 状況不明の場合は従来通り Medium 以上で指摘する。
（フロー順序: /implement → /code-review → /test のため /code-review 時点では空白が正常）
```

→ TC-16 参照

---

## レビュー結果
- [20260428_0117 ⛔ 差し戻し → 修正済み](../../reviews/I055_plan_review_20260428_0117.md)

- [20260428_0130 ✅ 完了](../../reviews/I055_plan_review_20260428_0130.md)
- [20260430_0056 ✅ 完了](../../reviews/I055_plan_review_20260430_0056.md)
- [20260430_0255 ✅ 完了](../../reviews/I055_plan_review_20260430_0255.md)
- [20260430_0931 ✅ 完了](../../reviews/I055_plan_review_20260430_0931.md)
- [20260430_0945 ✅ 完了](../../reviews/I055_plan_review_20260430_0945.md)
- [20260430_1057 ✅ 完了](../../reviews/I055_plan_review_20260430_1057.md)
