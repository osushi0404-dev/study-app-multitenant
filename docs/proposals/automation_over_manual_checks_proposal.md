# 提案：機械的チェックの自動化 - 手動ルール・AIレビュー依存からの脱却

- **作成日**: 2026-04-27
- **作成者**: Claude Code（調査・分析）
- **ステータス**: 提案中

---

## 背景と問題認識

現在のワークフローでは「本来 GitHub Actions・linter・pre-commit で機械的に保証できるチェック」が
スキルファイル・runbook・コーディング規約ドキュメントに手動手順として記載されており、
以下の問題が生じている。

1. **Claude の実行コストが上がる** — linter が1秒で判定できることに LLM が思考リソースを使う
2. **再現性が下がる** — 手動手順は「忘れ」「解釈ぶれ」が発生する
3. **CI との重複** — 同じチェックをローカルでも CI でも手動でも行い、三重になっている箇所がある
4. **「自動検出すべき問題」と「設計判断が必要な問題」が混在** — AI レビューの焦点が散漫になる

---

## 現状の問題箇所（調査結果）

### A. CI と手動ルールの重複（完全に冗長）

| チェック | CI 自動化 | 手動ルールの場所 |
|---------|----------|----------------|
| `makemigrations --check` | ✅ `ci.yml` backend-lint | `backend-check.md` §1 必須実行手順 |
| flake8 | ✅ `ci.yml` backend-lint | `/implement` SKILL.md 手順2 |
| bandit | ✅ `ci.yml` backend-lint | `/implement` SKILL.md 手順2 |
| ESLint | ✅ `ci.yml` frontend-lint | `/implement` SKILL.md 手順2 |
| TypeScript 型チェック | ✅ `ci.yml` frontend-typecheck | `/implement` SKILL.md 手順2 |
| `npm audit` | ❌ CI に**未設定** | `/implement` SKILL.md 手順2 |
| Python 依存関係脆弱性スキャン（`pip-audit`） | ❌ CI に**未設定** | 手動手順なし（空白地帯） |

**根本原因**: pre-commit フックに lint が含まれていないため、「コミット前に手動実行してください」という手順が生まれた。
現在の pre-commit は `detect-secrets` / `check-yaml` / `trailing-whitespace` 等のみ。

`npm audit` については手動実行ルールはあるが CI に追加されておらず、フロントエンドの依存関係セキュリティが
自動保証されていない。さらに Python 側の依存関係脆弱性スキャン（`pip-audit` 等）は手動手順すら存在しない空白地帯になっている。
`bandit` はコードのセキュリティパターン検出であり、依存パッケージの CVE 検出ではない点に注意。
なお `dependabot.yml` は設定済みで依存関係更新 PR は自動生成されるが、これは「更新 PR の自動化」であり
「現在の deps に既知 CVE がないことの PR ゲート」は別途 CI に組み込む必要がある。

### B. 機械的に自動化できるのに手動・AI 依存になっているもの

#### B-1. `backend-check.md` のAPI統合テスト手順
`curl` コマンドを 10〜20 個手動実行してレスポンスを目視確認するルール（§2）。
認証トークン取得 → 各エンドポイント呼び出し → `jq` でフィールド確認 → ログ確認、という手順が
詳細に記述されている。

**本来あるべき姿**: pytest integration test として書き、`backend-test` CI ジョブで自動実行。
この手順書は「テストが書かれていないことの代替ドキュメント」になってしまっている。

#### B-2. `/code-review` SKILL.md のCI確認ステップ（手順1）
```bash
gh pr checks [PR番号]
```
Claude が CI の pass/pending/fail を手動確認している。

**本来あるべき姿**: Branch Protection Rules（Required status checks）を設定すれば
CI が通らないと PR がマージ不可になり、Claude が確認する必要なし。
`docs/runbooks/branch-protection-setup.md` が存在するが設定状況は要確認。

#### B-3. `review-rules.md` のスキルファイルチェックリスト（7項目）
`.claude/skills/` 配下のファイル変更時に Claude が目視で7項目確認するルール。

```
1. allowed-tools で最小権限が設定されているか
2. disable-model-invocation: true が設定されているか
3. argument-hint が記載されているか
4. description に「いつ使うか」が含まれているか（250文字以内）
5. 指示文に明確な停止条件・完了条件が記載されているか
6. $ARGUMENTS 等の変数が一貫して使われているか
7. SKILL.md が 500行以内か
```

**本来あるべき姿**: シェルスクリプト数行で静的チェック可能。
GitHub Actions のパスフィルタ（`paths: ['.claude/skills/**']`）で変更時のみ実行。

### C. linter が担当できるのにAIレビューが確認しているもの

`rules/ultimate_django_coding_standards.md` / `react-coding-standards-integrated.md` に記載された規約のうち、
命名規則・インポート順序・空白・未使用変数などは flake8 / ESLint / tsc が自動検出できる。
しかし「linter が自動検出」か「設計判断が必要な手動確認」かの区別が明記されていないため、
AI レビュー（`/plan-issue-review` / `/code-review`）が linter の仕事まで担おうとしてしまう。

---

## 提案：改善イシューの分割

以下の4つのイシューに分割して対応することを提案する。

### イシュー①（高優先）
**タイトル**: `pre-commit に静的チェックを追加し npm audit を CI に組み込んでコード品質・依存関係セキュリティを自動保証する`

**やること**:
- `.pre-commit-config.yaml` に flake8（または Ruff） / bandit / ESLint フックを追加
  - CI の設定（対象ディレクトリ・フラグ）と揃えること（例: bandit は `-ll` で MEDIUM 以上のみ）
  - ESLint は `pass_filenames: false` で `src/` 全体を対象にする設定が必要
  - **実装時確認事項**: ESLint を pre-commit から呼ぶには開発者ローカルに Node.js が必要。WSL2 環境では `language: node` フックを使う方法が標準だが、`node_modules` の初期化タイミングを確認すること
- CI の `frontend-lint` ジョブに `npm audit --audit-level=high --omit=dev` を追加
  - **unfixable vulnerabilities の扱い**: トランザクティブ依存の修正不可 CVE で CI が恒常的に失敗するリスクがある。`.nsprc` またはコメント付き `package.json` の `overrides` で既知の許容例外を管理する方針をチームで決定してから追加すること
  - Dependabot（設定済み）との役割分担: Dependabot = 更新 PR の自動生成、`npm audit` in CI = 現在の deps の CVE ゲート
- CI に `pip-audit` による Python 依存関係脆弱性スキャンを追加（`backend-lint` ジョブに追記）
  - `pip-audit` は PyPA 公式ツールで `requirements.txt` ベースのスキャンが可能
  - `--ignore-vuln` で既知の許容例外を管理できる
  - **実装手順**: `backend/requirements-dev.txt` に `pip-audit` を追記すること（CI の `backend-lint` ジョブは `pip install -r backend/requirements-dev.txt` でインストールするため、追記しないと CI で利用不可）
- `bandit` の除外設定を `backend/setup.cfg` に切り出す（現在は CI の CLI 引数 `-x ./\*/migrations/,./\*/tests/ -ll` で指定されており、pre-commit と設定がずれるリスクがある。`setup.cfg` に `[bandit]` セクションで設定すると pre-commit・CI 両方が自動的に同じ設定を使う）
- `frontend/package.json` の `eslintConfig` で `eslint-plugin-security` は **`"plugin:security/recommended-legacy"` として有効化済み**（コード確認済み・対応不要）。CI の ESLint ジョブ実行時にセキュリティ lint が既に走っている
- `/implement` SKILL.md 手順2 の手動 lint・audit 実行指示を「pre-commit と CI が自動実行」に書き換え
- `docs/runbooks/pre-commit.md` のフック一覧を更新
- `detect-secrets` の JWT 検出ギャップを確認する。`e2e/.auth/` に Playwright 認証状態ファイル（JWT を含む）が生成されるが、`e2e/.gitignore` に `.auth/` が記載済みのため git 追跡は防がれている（対応済み）。ただし `detect-secrets` はデフォルトで JWT パターンを検出しないため、他のファイルへの JWT ハードコードを見逃すリスクがある。`detect-secrets scan` で現状を確認し、必要であれば `JwtTokenDetector` を `.pre-commit-config.yaml` の `args` に追加する
- `rules/ultimate_django_coding_standards.md` / `react-coding-standards-integrated.md` に「自動チェック対象（linter が強制）」と「設計判断が必要な手動確認対象」の区分を明示する（各規約項目に ✅ linter / 👁 manual のマーカーを追記するか、セクションを分割する）

**ツール選定の判断点（実装時に決定）**:
- `rules/ultimate_django_coding_standards.md` では Ruff（flake8 + isort + pyupgrade の代替）を推奨している
- 今回 flake8 → Ruff へ移行するか、flake8 を維持して pre-commit に追加するかを実装前に確認する
- Ruff に移行する場合: CI・pre-commit 両方を Ruff に統一、`requirements-dev.txt` の flake8 を Ruff に置き換え

**効果**: implement 時の手動 lint・audit 実行が不要になる。フロントエンド・バックエンド両方の依存関係セキュリティが CI で対称的に保証される。
CI との役割分担が明確になる（commit 前 = pre-commit による高速フィードバック、PR = CI による環境パリティ保証）。

### イシュー②（高優先）
**タイトル**: `backend-check.md の API 統合テスト手順を pytest に変換して CI で自動実行する`

**やること**:
- `backend-check.md` §2 の curl コマンド群を `backend/tests/integration/` 以下の pytest テストに変換
  - DRF の `APIClient` と `pytest-django` の `@pytest.mark.django_db` を使用すること
  - テストユーザー・パスワードは `conftest.py` の `fixture` 経由で生成し、ハードコード禁止
  - **マルチテナント境界テスト必須**: 組織Aのユーザーが組織Bのデータを取得できないことを assertする
- 既存の `backend-test` CI ジョブ（PostgreSQL サービス付き）で自動実行されることを確認
- `backend-check.md` から curl 手順を削除し「`backend/tests/integration/` を参照」に置き換え
- `backend-check.md` §1（モデル整合性チェック手順）を改訂する。現在「毎回必ず実行してください」という必須手順として書かれているが、CI（`makemigrations --check`）で自動保証済みのため、**「CI がマイグレーション乖離を検出したときにローカルで診断する手順」に書き直す**。必須手順 → トラブルシュートリファレンスに位置づけを変更することで、CI との役割が明確になる

**効果**: 修正のたびに 10〜20 個の curl コマンドを手動実行する手順が消える。
テナント分離を含む回帰テストとして常時 CI で実行される。

### イシュー③（中優先）
**タイトル**: `Branch Protection の現状確認・E2E 必須チェック追加と CI ジョブ依存関係を整備して自動品質ゲートを強化する`

**前提確認（実装前に必須）**:
- `docs/runbooks/branch-protection-setup.md`（I032 / GitHub Issue #73 で実施済み）が存在するため、Branch Protection 自体は設定済みの可能性が高い
- 「確認・設定」ではなく「**現状確認が先決**」。GitHub Settings で実際の設定状態を確認してから作業範囲を決定する

**やること**:
- develop / main の Branch Protection 現状を GitHub Settings で確認
- **E2E テストの required checks 追加（高確率で漏れあり）**: `e2e.yml` は存在するが `branch-protection-setup.md` の必須チェックリストに E2E が含まれていない。`E2E Tests (Playwright)` を Required status checks に追加することを検討する
  - **実装前に判断が必要なトレードオフ**: E2E は Docker を起動して Playwright を実行する構成で実行時間が長く（5分以上の可能性）、全 PR で必須にすると feature → develop の日常的なマージ待ち時間が大幅に増える。以下のいずれかを選択する:
    - **案A（厳格）**: 全 PR で E2E を required にする。品質ゲートは完全だが PR のサイクルタイムが増加する
    - **案B（バランス）**: develop → main の PR のみ E2E を required にする（`main` ブランチの Branch Protection のみに追加）。feature → develop は CI のみで十分とする
    - **案C（ラベル制御）**: GitHub Actions の `if:` 条件でラベル付き PR のみ E2E を実行する（柔軟だが管理が複雑）
  - チームの開発サイクルと許容できる待ち時間をもとに実装前に決定すること
- `ci.yml` のジョブ依存関係を最適化:
  - `backend-test` に `needs: [backend-lint]` を追加
  - `frontend-test` に `needs: [frontend-lint, frontend-typecheck]` を追加
  - **注意**: `needs` で依存ジョブが失敗すると依存先は「skipped」になる。Branch Protection は「skipped」を「未通過」扱いするため PR はブロックされる。これは**意図した正常動作**だが、運用者が「テストが走っていないのになぜブロックされるのか」と混乱しないよう `docs/runbooks/branch-protection-setup.md` にこの挙動を追記すること
- `/code-review` SKILL.md から `gh pr checks` による手動確認ステップを削除
  （CI 失敗時は branch protection がマージをブロックするため Claude の手動確認は不要）

**効果**: E2E 失敗でもマージできてしまう現状の穴が塞がれる。Claude が CI 状態を手動確認する1ステップが消える。lint 失敗時に無駄なテスト実行が止まり CI コスト・フィードバック速度が改善する。

### イシュー④（中優先）
**タイトル**: `スキルファイルバリデーションを GitHub Actions で自動化し review-rules.md の手動チェックリストを削除する`

**やること**:
- `.claude/skills/` 変更検出 → バリデーションスクリプト実行の GitHub Actions ジョブを追加
- チェック項目: `argument-hint` 存在、`description` 250文字以内、`SKILL.md` 500行以内、`allowed-tools` 記載、`disable-model-invocation` 記載
- `review-rules.md` の手動7項目チェックリストをスクリプト実行に置き換え

**効果**: スキルファイル変更時の AI レビュー負荷が下がる。ルール違反が PR で自動検出される。

---

## 対応しない項目（スコープ外）

- Python 側の静的型チェック（mypy + django-stubs）の CI 追加 → 既存コードへの型アノテーション追加が前提になるため導入コストが高い。`--ignore-missing-imports` と新規ファイルのみチェックする段階的採用オプションもあるが、既存コードの品質把握コストがかかるため、設計から専用イシューで行う
- GitHub Actions のバージョン SHA ピン固定 → `actions/checkout@v4` 等のメジャーバージョン固定はサプライチェーン攻撃（アクション改ざん）に対して脆弱。完全な対策は SHA ハッシュ固定（`actions/checkout@11bd71...`）だが、Dependabot はタグ更新 PR を自動生成するものであり SHA ピンとは別物のため、Dependabot があっても SHA ピンなしでは改ざんリスクは残る。より即効性のある改善として、各ジョブに `permissions: contents: read` 等の最小権限を明示する（現在 `permissions:` が未設定のため GITHUB_TOKEN がデフォルトの書き込み権限を持つ）。SHA ピン・`permissions:` ともにセキュリティ要件が高まった際の改善候補として記録する

---

## 期待される効果

- **Claude の思考リソース**: linter/CI に任せられるチェックから解放 → 設計・ビジネスロジックのレビューに集中
- **ワークフローのステップ数削減**: `/implement` の手動 lint ステップ、`/code-review` のCI確認ステップが消える
- **再現性向上**: 「手動でやってください」が「ツールが自動でやる」に変わる
- **セキュリティの対称保証**: npm audit（フロントエンド）と pip-audit（バックエンド）が CI に入り、依存関係の脆弱性が PR 単位で両側から検出される
- **CI コスト削減**: ジョブ依存関係の整備により lint 失敗時に後続テストが早期終了する
- **E2E 品質ゲート**: E2E テストが Branch Protection の必須チェックに加わり、E2E 失敗でマージできてしまう穴が塞がれる
