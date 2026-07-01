# Claude Code ファイル構成一覧

このプロジェクトで Claude Code（バイブコーディング）が参照するファイルの全体像をまとめたリファレンスです。

---

## ディレクトリ構成（全体図）

```
study-app-multitenant/
│
├── CLAUDE.md                                ← [★ 起点] プロジェクト憲法・絶対ルール
│
├── .claude/                                 ← Claude Code 設定ディレクトリ
│   ├── settings.json                        ← 権限設定（allow / ask / deny）+ hooks
│   ├── settings.local.json                  ← ローカル権限の一時的な追加許可
│   └── skills/                              ← カスタムスキル（スラッシュコマンド）
│       ├── issue-bootstrap/SKILL.md         ← /issue-bootstrap コマンド定義
│       ├── plan/SKILL.md                    ← /plan コマンド定義
│       ├── implement/SKILL.md               ← /implement コマンド定義
│       ├── fix-loop/SKILL.md                ← /fix-loop コマンド定義
│       └── close/SKILL.md                   ← /close コマンド定義
│
├── docs/
│   ├── runbooks/                            ← 詳細ルール集（CLAUDE.md から参照）
│   │   ├── workflow.md                      ← 運用フロー・ブランチ戦略・承認ワークフロー
│   │   ├── plan-writing-rules.md            ← 計画書の書き方・一致性保証ルール
│   │   ├── issue-flow.md                    ← イシュー作成〜クローズの詳細手順（27ステップ）
│   │   ├── danger-ops.md                    ← 危険操作の承認ルール
│   │   ├── common-commands.md               ← よく使うコマンド集
│   │   ├── backend-check.md                 ← バックエンド修正時の診断・検証手順
│   │   ├── review-rules.md                  ← レビューファイルの作成・管理ルール
│   │   ├── ux-rules.md                      ← UX 設計・チェックリスト
│   │   ├── template-sync.md                 ← ルール変更時のテンプレート同期手順
│   │   └── legacy/                          ← 旧ルールファイルのアーカイブ
│   │
│   ├── issues/                              ← イシューファイル（作業チケット）
│   │   ├── open/XXX.md                      ← 対応予定・確認待ち
│   │   ├── in_progress/XXX.md               ← 実装中
│   │   ├── closed/XXX.md                    ← 完了
│   │   └── templates/issue_template.md      ← イシュー作成テンプレート
│   │
│   ├── plans/                               ← 計画書（実装前に作成・承認必須）
│   │   ├── open/plan_IXXX_概要.md           ← 承認待ち・作業中
│   │   ├── closed/                          ← 完了済み
│   │   └── templates/plan_template.md       ← 計画書テンプレート
│   │
│   ├── tests/                               ← テストケース・エラー管理
│   │   ├── open/test_IXXX_manual.md         ← ユーザーが実施するテスト手順
│   │   ├── open/test_IXXX_auto.md           ← 自動テスト（ユニット・統合）手順
│   │   ├── open/error_IXXX.md               ← エラー管理（NG 時に作成・追記方式）
│   │   ├── closed/
│   │   └── templates/
│   │       ├── test_record_template.md
│   │       └── error_log_template.md
│   │
│   └── reviews/                             ← レビューファイル（品質記録）
│       ├── open/reviewXXX_IXXX.md           ← 実装前に枠作成・実装後に結果記入
│       ├── in_progress/                     ← 改善対応中
│       ├── closed/                          ← 全改善完了
│       └── templates/review_template.md     ← レビューテンプレート
│
├── rules/                                   ← コーディング規約（実装時に参照）
│   ├── ultimate_django_coding_standards.md  ← バックエンド規約（Django / DRF）
│   └── react-coding-standards-integrated.md ← フロントエンド規約（React / TypeScript）
│
├── scripts/
│   └── claude/
│       └── hooks/
│           └── pretooluse_guard.py          ← 危険操作をブロックする安全フック（PreToolUse）
│
└── .github/
    └── workflows/
        └── plan-gate.yml                    ← PR マージ前の自動チェック（CI ゲート）
```

---

## ファイル別・役割詳細

### CLAUDE.md（プロジェクト憲法）

**役割**: Claude Code が会話開始時に自動で読み込む「憲法ファイル」。詳細ルールは各 runbook に委譲し、このファイル自体は短く保つ設計。

#### 絶対ルール（5 箇条）

| # | ルール | 違反した場合 |
|---|-------|------------|
| 1 | 計画書に書いていない実装は禁止。より良い案があれば「提案 → 承認 → 計画書更新」が先 | 作業を中断し計画書更新を求める |
| 2 | ユーザー承認なしに Edit/Write/MultiEdit を開始しない（読み取り・調査は可） | 承認待ち宣言を出して停止 |
| 3 | develop/main への直 push 禁止。イシューごとにブランチを作り PR 経由でマージ | 実行自体が deny でブロックされる |
| 4 | 危険操作（データ削除・force push 等）は明示承認制 | `DANGER_OK=1` がない限り hook がブロック |
| 5 | すべての作業は「記録（plan / tests / review）」が残る形で進める | レビューファイルなしでのクローズ禁止 |

#### 参照先マップ

```
CLAUDE.md
├── 運用フロー        → docs/runbooks/workflow.md
├── 計画書の書き方    → docs/runbooks/plan-writing-rules.md
├── 危険操作          → docs/runbooks/danger-ops.md
├── よく使うコマンド  → docs/runbooks/common-commands.md
├── イシューフロー    → docs/runbooks/issue-flow.md
├── UXルール          → docs/runbooks/ux-rules.md
├── バックエンドチェック → docs/runbooks/backend-check.md
├── レビュールール    → docs/runbooks/review-rules.md
├── テンプレート同期  → docs/runbooks/template-sync.md
├── Backend 規約      → rules/ultimate_django_coding_standards.md
└── Frontend 規約     → rules/react-coding-standards-integrated.md
```

---

### .claude/settings.json（権限設定）

Claude Code が実行できる Bash コマンドを 3 段階で制御し、さらに PreToolUse hook で二重ガードする。

#### allow（自動実行・確認なし）

| カテゴリ | 許可コマンド例 |
|---------|-------------|
| ファイル読み取り | `Read(*)`, `Grep(*)`, `Glob(*)`, `cat *`, `head *`, `tail *` |
| Git 調査 | `git status`, `git diff`, `git log *`, `git show *`, `git branch *` |
| Git 操作（安全系） | `git checkout *`, `git switch *`, `git add *`, `git commit *`, `git push`, `git push *` |
| GitHub CLI（読み取り系） | `gh pr view *`, `gh pr status *`, `gh issue *` |
| Docker（読み取り系） | `docker compose ps`, `docker compose logs *`, `docker compose up *`, `docker compose build *` |
| テスト実行 | `docker compose exec backend pytest *`, `docker compose exec frontend npm test *`, `npm run lint *`, `npm run typecheck *` |

#### ask（毎回ユーザー確認が必要）

| カテゴリ | 確認が必要なコマンド例 |
|---------|-------------------|
| Git 破壊系 | `git merge *`, `git rebase *`, `git reset *`, `git cherry-pick *` |
| Docker 操作 | `docker compose exec *`, `docker compose run *`, `docker compose down *` |
| ファイル操作 | `rm *`, `mv *`, `cp *`, `chmod *`, `chown *` |
| DB 操作 | `psql *` |

#### deny（常時禁止・実行不可）

| カテゴリ | 禁止コマンド例 | 理由 |
|---------|-------------|------|
| ネットワーク | `curl *`, `wget *`, `ssh *`, `scp *`, `rsync *` | 外部通信・情報漏洩リスク |
| 権限昇格 | `sudo *` | 管理者操作の防止 |
| データ破壊 | `dd *`, `mkfs *`, `shred *`, `rm -rf / *` | 復元不可能な操作 |
| 保護ブランチへの push | `git push origin develop`, `git push origin main`, `git push * --force*` | 直接 push 禁止（deny はテキスト自明形のバックストップ） |
| シークレット読み書き | `Read(.env)`, `Edit(.env)`, `Write(.env)`, `Read(**/*.pem)`, `Read(**/*.key)` | 機密情報保護 |

#### hooks（PreToolUse）

```json
"PreToolUse": [{
  "matcher": "Bash",
  "hooks": [{
    "type": "command",
    "command": "python3 \"$CLAUDE_PROJECT_DIR\"/scripts/claude/hooks/pretooluse_guard.py"
  }]
}]
```

Bash ツールが呼ばれるたびに `pretooluse_guard.py` を実行し、settings.json の deny だけでは捕捉できないパターンも二重でブロックする。

`git push` は安全な feature push を allow（確認なし）にする一方、**保護ブランチ（develop/main）を宛先とする push はフックが danger-op として既定で block（exit 2）**する。宛先トークンを正規化（先頭 `+` 除去・`src:dst` の dst 採用・`refs/heads/` 除去・`HEAD` は現ブランチ解決）して完全一致判定するため、引数なし push（保護ブランチ上）・refspec・force-shorthand・完全修飾 ref・`--all`/`--mirror`・`--repo` まで一括で捕捉する。release/hotfix の正当なローカル push のみ `DANGER_OK=1`（＋計画書明記＋danger-approved）で解除可。`deny` はテキストで自明な形のバックストップとして残す。

> **動的宛先・force 取りこぼしへの対応（I083 で対応済み）**: 本ガードはコマンド**実行前の生コマンド文字列**を静的に解析する。かつて以下の2クラスがすり抜けたが、I083 で根治した。
> - **動的宛先 → ask に degrade**: コマンド置換 `$(...)`／変数展開 `$VAR`・`${...}`／git エイリアス間接参照（`-c alias.x=...`）／`eval`・`sh -c`・`bash -c` ラッパー等、実行時にしか宛先が確定しない形（例: `git push origin $(git rev-parse --abbrev-ref HEAD)`）は、宛先を安全と断言できないため **ask（確認プロンプト）に degrade** する（hard block ではなく人へ委ねる）。ラッパー検出は `_segments` の先頭トークンによる**構造的**判定で、`bash-feature` 等のブランチ/remote 名の偶然一致では誤発火しない。
> - **force push の取りこぼし → pure `_segments` で捕捉**: force 判定を `_push_has_force`（push セグメントのトークン走査）に置換し、`-f`/`-uf`/`--force-with-lease`/`--force-if-includes`・複合コマンド（`cd foo && git push --force ...`）を捕捉する。旧 `re.match` の潜在誤 block（`git push origin feature; echo "--force"` 等の安全 push を誤遮断）も解消した。
> - **残余の既知限界（脅威モデル外）**: push トークンを**完全に隠蔽**する偽装形（`eval "$VAR"`／`sh -c "$CMD"` で push がコマンド文字列に一切現れない）は検知対象外。本ガードの脅威モデルは「事故による protected/force push の防止」であり、意図的な難読化は対象としない（`DANGER_OK=1` の解除導線と同様に運用者の責任に委ねる）。
> - **既知の残課題（I088 で対応予定）**: `--all`/`--mirror`/`--repo` の判定は現状まだ貪欲正規表現（`.*` がシェル区切りを跨ぐ）のため、複合コマンド（例 `git push origin feature && ls --all`）で無関係な後続トークンに一致し安全 push を誤 block し得る。force と同型の兄弟バグで、I088(#172) が同一修正（`_segments` 化）で根治予定。

---

### .claude/settings.local.json（ローカル追加許可）

**役割**: セッションや作業ごとに一時的なコマンド許可を追記するファイル。

- settings.json と同じ形式で `permissions.allow` に追記する
- `.gitignore` への追記を推奨（機密性の高い一時許可を共有しないため）
- 例：特定の migration コマンドや一時的な調査コマンドを許可する際に使用

---

### .claude/skills/（カスタムスキル）

`/コマンド名` で呼び出せるプロンプトテンプレート。各 `SKILL.md` に Claude が実行すべき手順が記述されており、呼び出すと Claude がその手順に従って自動的に処理を進める。

すべてのスキルは `disable-model-invocation: true`（追加の AI 呼び出しを防ぐ）および `allowed-tools: Read, Bash, Write, Edit, Glob, Grep` で動作する。

---

#### /issue-bootstrap（イシュー起票）

**呼び出し**: `/issue-bootstrap [タイトル]`
**役割**: 新しい開発タスクを起票し、作業環境を一括セットアップする。

| ステップ | 処理内容 |
|---------|---------|
| 1 | リポジトリ確認（`git rev-parse`, `git branch --show-current`） |
| 2 | イシュー番号の採番（open/in_progress/closed 全ディレクトリから最大番号を取得して +1） |
| 3 | `docs/issues/templates/issue_template.md` をコピーして `docs/issues/open/XXX.md` 作成・編集 |
| 4 | `develop` をベースに `feature/IXXX-[英語概要]` ブランチを作成 |
| 5 | イシューファイルを commit・push |
| 6 | `gh issue create` で GitHub Issue を登録（ラベル付き） |
| 7 | `gh pr create --draft` で Draft PR を作成 |
| 8 | ユーザーへの完了報告（ファイルパス・ブランチ名・GitHub URL を提示） |

**ブランチ命名規則**: `feature/I{3桁番号}-{英語概要をケバブケースで最大5単語}`

---

#### /plan（計画書・テスト・レビュー枠の作成）

**呼び出し**: `/plan I###`
**役割**: 実装前に必要な全ドキュメントを作成し、ユーザー承認を待つ。コード変更は一切しない。

**必読ファイル（スキル実行時に参照）**:
- `docs/issues/open/XXX.md`（イシュー定義）
- `docs/runbooks/plan-writing-rules.md`（計画書ルール）
- `rules/ultimate_django_coding_standards.md`
- `rules/react-coding-standards-integrated.md`

**生成ドキュメント**:

| ファイル | 内容 |
|---------|------|
| `docs/plans/open/plan_IXXX_概要.md` | 背景・受入条件・影響範囲・変更点・手順・テスト計画・ロールバック・リスク・承認ポイント |
| `docs/tests/open/test_IXXX_manual.md` | ユーザーが手動で確認する操作手順と期待結果 |
| `docs/tests/open/test_IXXX_auto.md` | ユニットテスト・統合テストの実行コマンドと期待結果 |
| `docs/reviews/open/reviewXXX_IXXX.md` | 基本情報のみ記入・評価セクションは空欄で作成 |

**完了時の出力**（必須）:
```
📋 計画書完了: docs/plans/open/plan_IXXX_概要.md
⏸️ 承認待ち中 - 修正作業は開始しません
✅「OK」で承認、❌ 修正指示をお願いします
```

---

#### /implement（実装・テスト・記録）

**呼び出し**: `/implement I###`
**役割**: 承認済み計画書に従って実装し、テスト・記録・PR 更新までを完結させる。

**必読ファイル（実装前に参照）**:
- `docs/plans/open/plan_IXXX_*.md`
- `docs/tests/open/test_IXXX_auto.md`
- `docs/tests/open/test_IXXX_manual.md`
- `docs/reviews/open/reviewXXX_IXXX.md`

**実行ステップ**:

| ステップ | 処理内容 |
|---------|---------|
| 1 | 計画書を再読し「より良い実装方法がないか」を必ず検討（計画書外の実装は禁止） |
| 2 | 計画書通りにコード実装（Backend/Frontend/DB） |
| 3 | `test_IXXX_auto.md` の自動テストを実行（失敗時は `/fix-loop` へ） |
| 4 | レビューファイルに実装結果・品質評価を記入 |
| 5 | commit/push して PR を更新 |
| 6 | `test_IXXX_manual.md` の要点を提示し、ユーザーの手動テスト結果を待機 |

**重要制約**: 計画書に記載のないファイル・メソッド・変数の変更は即時中断して報告。

---

#### /fix-loop（NG 時の修正ループ）

**呼び出し**: `/fix-loop I###`
**役割**: テスト NG や実装失敗時に原因を記録し、差分計画を立てて承認後に修正する。

| ステップ | 処理内容 |
|---------|---------|
| 1 | NG 内容を「再現手順 / 期待値 / 実際の結果 / ログ」に分解して記録 |
| 2 | `docs/tests/open/error_IXXX.md` に追記（初回は新規作成） |
| 3 | 差分計画を `docs/plans/open/plan_IXXX_概要_N.md`（連番で新規作成）に記載 |
| 4 | 承認待ちで停止 |
| 5 | 承認後に修正 → 再テスト → 記録更新 → ユーザー検証へ |

**重要**: 元の計画書は上書きせず、新しい連番ファイル（`_2`, `_3`...）で追記する。

---

#### /close（クローズ処理）

**呼び出し**: `/close I###`
**前提**: ユーザー検証 OK が出ていること。

| ステップ | 処理内容 |
|---------|---------|
| 1 | `docs/tests/open/test_IXXX_*.md` → `closed/` へ移動（完了情報を末尾に追記） |
| 2 | `docs/tests/open/error_IXXX.md`（存在する場合）→ `closed/` へ移動 |
| 3 | `docs/plans/open/plan_IXXX_*.md`（全関連計画書）→ `closed/` へ移動 |
| 4 | `docs/issues/open/XXX.md` → `closed/` へ移動（完了情報・関連ファイルリストを追記） |
| 5 | featureブランチを develop にマージ（`--no-ff`） |
| 6 | `docs/reviews/open/reviewXXX_IXXX.md` → `closed/` へ移動 |
| 7 | GitHub Issue をクローズ（`gh issue close`） |
| 8 | ユーザーへ GitHub 上での Approve & Merge を依頼 |

---

### docs/runbooks/（詳細ルール集）

CLAUDE.md から参照される詳細ルールをまとめたディレクトリ。Claude Code は実装前・実装中に該当ファイルを参照する。

---

#### workflow.md

**役割**: 開発プロセス全体の標準手順書。

| セクション | 内容 |
|-----------|------|
| ディレクトリ規約 | issues/plans/tests/reviews 各ディレクトリの open/in_progress/closed 構成 |
| フロー定義 | `/issue-bootstrap → /plan → /implement → /fix-loop → /close` の 5 ステップ |
| ゲート | 計画承認前のコード変更禁止・Danger Ops の明示承認必須・直 push 禁止 |
| コマンド実行ルール | 実行前に「何をするコマンドか・なぜ実行するか」を日本語で説明する義務 |
| ロジック修正時の説明 | 修正の意図・修正前の問題点・修正後の改善内容の 3 点を必ず説明 |
| 必須承認ワークフロー | 調査 → 方針検討 → 計画書作成 → 承認待ち宣言 → 承認確認 → 記録 → 作業開始の 8 ステップ |
| ブランチ戦略 | main（本番）/ develop（統合）/ feature/IXXX-xxx（開発）/ hotfix/xxx（緊急修正）の 4 種類 |
| 本番リリースフロー | develop → main のマージ手順・バージョンタグ付与ルール |
| hotfix 運用 | main と develop の**両方**にマージする必須ルール |

---

#### plan-writing-rules.md

**役割**: 計画書に必ず含める項目と、計画書と実装の一致を保証するルールを定義する。

**計画書の必須記載項目（9 項目）**:

| # | 項目 | 内容 |
|---|-----|------|
| 1 | 背景/目的 | なぜこの実装が必要か |
| 2 | 受け入れ条件 | 何ができたら OK か（検証可能な形で） |
| 3 | 影響範囲 | Backend / Frontend / DB / Config への影響 |
| 4 | 変更点一覧 | 変更するファイル・関数・SQL の具体名 |
| 5 | 実装手順 | ステップバイステップの作業手順 |
| 6 | テスト計画 | 自動テスト・手動テストの両方 |
| 7 | ロールバック | 問題発生時の戻し方 |
| 8 | Risk & 回避策 | 想定リスクと対処法 |
| 9 | 承認ポイント | ユーザーが OK を返すためのチェックリスト |

**計画書と実装の一致性保証ルール（3 ステップチェック）**:
1. 実装開始前に計画書を再読
2. 「計画書に記載があるか」「より良い方法はないか」を 5 観点で検討（パフォーマンス/保守性/セキュリティ/拡張性/シンプルさ）
3. 実装中に逸脱を検知したら即座に中断・報告・承認を待つ

**計画書の命名規則**:
```
docs/plans/open/plan_[タイプ]_[概要].md
  タイプ: I[番号] / BUG / FEAT / FIX / MAINT / PERF
  2回目以降: plan_I010_概要_2.md, _3.md...
```

---

#### issue-flow.md

**役割**: イシューの作成からクローズまでの詳細な 27 ステップフローを定義する。

**フェーズ構成**:

| フェーズ | ステップ | 内容 |
|---------|---------|------|
| フェーズ1（イシュー準備） | 1〜5 | ファイル作成・ブランチ作成・GitHub 登録・ユーザー確認 |
| フェーズ2（計画・設計） | 6〜10 | 計画書・テストケース（2種）・レビュー枠作成・ユーザー承認 |
| フェーズ3（実装・テスト） | 11〜19 | 実装・自動テスト・レビュー記入・ユーザーテスト・NG 対応ループ |
| フェーズ4（クローズ） | 20〜27 | レビュー記入・各ファイル closed 移動・マージ・GitHub クローズ |

**イシュー番号の採番ルール**:
```bash
LAST_NUM=$(ls docs/issues/open/*.md docs/issues/in_progress/*.md docs/issues/closed/*.md \
  2>/dev/null | grep -o '[0-9]\+\.md' | sed 's/\.md//' | sort -n | tail -1)
# closed ディレクトリも必ず含めて最大番号を取得し +1 する
```

---

#### danger-ops.md

**役割**: 実行前に計画書明記・ユーザー承認・`DANGER_OK=1` の 3 条件が揃わないと実行できない操作を定義する。

| カテゴリ | 対象操作 |
|---------|---------|
| DB | `DROP` / `TRUNCATE` / WHERE なし `UPDATE`・`DELETE` / 破壊的マイグレーション |
| Git | `force push` / `reset --hard` / 大規模 rebase |
| Docker | `down -v` / `--volumes`（データボリューム削除） |
| Files | `rm -rf` / secrets ファイル操作 |

**実行テンプレートの必須項目**: 影響範囲 / 代替案 / ロールバック方法 / 実行コマンド（`DANGER_OK=1` 付き）

---

#### common-commands.md

**役割**: 開発・デバッグ・テストでよく使うコマンドのリファレンス。

| カテゴリ | コマンド例 |
|---------|----------|
| 開発環境起動 | `docker-compose up -d` |
| ログ確認 | `tail -f backend/logs/django.log` |
| エラー調査 | `python manage.py analyze_logs --last-errors=1` |
| バックエンドテスト | `docker-compose exec backend python manage.py test` |
| フロントエンドテスト | `docker-compose exec frontend npm test` |
| 再起動 | `docker-compose restart frontend backend` |

API エンドポイント一覧・修正済みの既知問題の履歴も記載。

---

#### backend-check.md

**役割**: バックエンドを修正した際に Claude Code が必ず実行する診断・検証手順を定義する。

**3 つのチェックルール**:

| チェック | トリガー | 内容 |
|---------|---------|------|
| DB・モデル整合性チェック | モデル関連エラー発生時 / ロジック修正依頼時 | マイグレーション状態確認 → モデルフィールドと DB カラムの差分チェック → 自動修正フロー |
| API 統合テスト | バックエンド修正後 | 関連 API 特定 → 認証トークン取得 → 全 API テスト → フロントエンド期待形式検証 → パフォーマンス確認 |
| 要件適合性テスト | API テスト後 | 指示内容の再確認 → データフィルタリング検証（組織間分離確認）→ エッジケース確認 |

**テスト完了の判定基準（全て ✅ が必要）**:
- HTTP ステータス 200 / JSON 構造の正確性 / データの組織間分離 / 必須フィールドの存在 / エラーハンドリング / パフォーマンス（2秒以内）/ エラーログなし

---

#### review-rules.md

**役割**: レビューファイルの作成タイミング・命名規則・必須記載項目・ライフサイクルを定義する。

**命名規則**:

| 種別 | 形式 | 例 |
|-----|------|-----|
| イシュー関連 | `reviewXXX_IYYY.md` / `reviewXXX_IYYY_post.md` | `review003_I010_post.md` |
| アドホック対応 | `reviewXXX_AD_YYYYMMDD.md` | `review004_AD_20260303.md` |
| 定期レビュー | `reviewXXX_PR_YYYYMMDD.md` | `review005_PR_20260303.md` |

XXX は全レビューファイル共通の通し番号（3 桁ゼロパディング）。

**記載タイミング**:

| タイミング | 記載する項目 |
|-----------|------------|
| 実装前（/plan 時） | 基本情報・対象計画書・レビュー目的（評価セクションは空欄） |
| 実装後（/implement 時） | 実装結果評価・品質評価・技術的評価 |
| テスト後（OK/NG 判定後） | テスト結果・発見した問題・最終判定 |

**ライフサイクル**: open → in_progress（改善対応中）→ closed（全改善完了・最後に移動）

---

#### ux-rules.md

**役割**: フロントエンド実装時に必ず確認する UX 観点と、計画書への UX セクション必須記載を定義する。

**5 つの UX 原則**:

| 原則 | 要点 |
|-----|-----|
| エラー処理 | コンテキスト維持・即座のフィードバック・次のアクションを明示（404 リダイレクト禁止） |
| ローディング | スケルトンスクリーン・プログレス表示・キャンセル可能性 |
| フォーム入力 | リアルタイムバリデーション・入力値の保持・具体的なエラーメッセージ |
| ナビゲーション | 意味のある URL・ブラウザ履歴の尊重・未保存データの離脱警告 |
| アクセシビリティ | タッチ操作 44px 以上・キーボード操作対応・aria-label・WCAG コントラスト基準 |

**計画書への必須追加セクション**:
```markdown
## UX設計
### 現在のUX課題
### 改善後のユーザー体験
### エラー・例外時の体験
### 成功指標
```

---

#### template-sync.md

**役割**: CLAUDE.md や runbook を変更した際に、対応するテンプレートファイルを同時更新するための手順を定義する。

**実行トリガー**: ファイルヘッダー構造変更 / 命名規則変更 / 文書間の相互参照ルール変更

**手順**:
1. ルール変更を実施
2. 関連テンプレートの存在を確認（`ls docs/*/templates/*.md`）
3. テンプレートが存在する場合は必ず同時更新
4. チェックリストで整合性を確認してコミット

---

### docs/（作業ドキュメント）

実際の開発作業で Claude Code が生成・更新するファイル群。全ディレクトリが `open → (in_progress) → closed` のライフサイクルで管理される。

#### ファイル命名規則まとめ

| ディレクトリ | 命名パターン | 作成タイミング | 作成者 |
|-------------|-----------|-------------|--------|
| `docs/issues/open/` | `XXX.md`（3桁連番） | `/issue-bootstrap` 実行時 | Claude Code |
| `docs/plans/open/` | `plan_[タイプ]_[概要].md` | `/plan` 実行時 | Claude Code |
| `docs/tests/open/` | `test_IXXX_manual.md` / `test_IXXX_auto.md` | `/plan` 実行時 | Claude Code |
| `docs/tests/open/` | `error_IXXX.md` | `/fix-loop` 実行時（NG 時のみ） | Claude Code |
| `docs/reviews/open/` | `reviewXXX_IXXX.md` | `/plan` 実行時（枠のみ） | Claude Code |

#### テンプレートと生成ファイルの関係

```
docs/issues/templates/issue_template.md
  └→ docs/issues/open/XXX.md（コピー後に内容を編集）

docs/plans/templates/plan_template.md
  └→ docs/plans/open/plan_IXXX_概要.md

docs/tests/templates/test_record_template.md
  ├→ docs/tests/open/test_IXXX_manual.md
  └→ docs/tests/open/test_IXXX_auto.md

docs/tests/templates/error_log_template.md
  └→ docs/tests/open/error_IXXX.md（NG 発生時に作成、2回目以降は追記）

docs/reviews/templates/review_template.md
  └→ docs/reviews/open/reviewXXX_IXXX.md
```

---

### rules/（コーディング規約）

実装時に Claude Code が参照するコーディング標準。`/plan` や `/implement` のスキルが参照する必読ファイル。

| ファイル | 対象 | 主な規約内容 |
|---------|------|-----------|
| `ultimate_django_coding_standards.md` | Backend | モデル定義・マイグレーション・ビュー・シリアライザー・パーミッション・テスト・API 設計・セキュリティ |
| `react-coding-standards-integrated.md` | Frontend | コンポーネント設計・カスタムフック・型定義・状態管理・API クライアント・エラー処理・テスト |

---

### scripts/claude/hooks/pretooluse_guard.py（安全フック）

**役割**: `settings.json` の deny リストに加え、パターンマッチで危険な Bash コマンドをプログラム的にブロックする二重ガード。

- Claude Code が Bash ツールを呼び出すたびに自動実行される（PreToolUse フック）
- コマンド内容を解析し、危険なパターン（`DROP TABLE`・`rm -rf`・`force push` 等）を検知したらブロックして理由を返す
- settings.json だけでは防げない動的なコマンド合成にも対応

---

### .github/workflows/plan-gate.yml（CI ゲート）

**役割**: PR マージ前に自動でルール遵守チェックを実行する GitHub Actions ワークフロー。

計画書・レビューファイルの存在確認や命名規則チェックを行い、ドキュメントなしでのマージを防ぐ。

---

## スキル実行フロー（全体像）

```
[ユーザー指示: タスクを実装してほしい]
      │
      ▼
/issue-bootstrap [title]
  ├─ docs/issues/open/XXX.md 作成（テンプレートから）
  ├─ feature/IXXX-xxx ブランチ作成（develop ベース）
  ├─ GitHub Issue 登録（gh issue create）
  ├─ Draft PR 作成（gh pr create --draft）
  └─ ★ ユーザーにイシュー内容を確認（OK/NG）
      │
      ▼ ユーザー「OK」
      │
/plan I###
  ├─ docs/plans/open/plan_IXXX_概要.md（背景/手順/ロールバック等 9 項目）
  ├─ docs/tests/open/test_IXXX_manual.md（手動テスト手順）
  ├─ docs/tests/open/test_IXXX_auto.md（自動テスト手順）
  ├─ docs/reviews/open/reviewXXX_IXXX.md（基本情報のみ、評価欄は空）
  └─ ★ 承認待ちで停止（コード変更禁止）
      │
      ▼ ユーザー「OK」
      │
/implement I###
  ├─ 計画書再読 + 改善案の検討（必須）
  ├─ コード実装（計画書の範囲内のみ）
  ├─ 自動テスト実行（test_IXXX_auto.md に基づく）
  │     └─ 失敗 → /fix-loop へ
  ├─ docs/reviews/ に実装結果・品質評価を記入
  ├─ commit/push・PR 更新
  └─ ★ ユーザーへ手動テスト要点を提示して結果待ち
      │
      ├─ NG ──────────────────────────────┐
      │                                   │
      │  /fix-loop I###                   │
      │   ├─ NG 内容を再現手順/期待/実際/ログで記録 │
      │   ├─ docs/tests/open/error_IXXX.md に追記 │
      │   ├─ 差分計画書を新規作成（連番）         │
      │   └─ ★ 承認待ち → 修正 → 再テスト ───┘
      │
      ▼ ユーザー「OK」
      │
/close I###
  ├─ test_IXXX_*.md → closed/（完了情報追記）
  ├─ error_IXXX.md → closed/（存在する場合）
  ├─ plan_IXXX_*.md（全関連）→ closed/
  ├─ issues/open/XXX.md → closed/
  ├─ feature/IXXX-xxx を develop にマージ（--no-ff）
  ├─ reviewXXX_IXXX.md → closed/（最後）
  ├─ GitHub Issue をクローズ（gh issue close）
  └─ ★ ユーザーへ GitHub 上での Approve & Merge を依頼
```

---

## 権限の二重ガード構造

```
ユーザーの指示
      │
      ▼
Claude Code がツール（Bash）を呼び出し
      │
      ▼
┌─────────────────────────────────────┐
│ [1st ガード] settings.json          │
│                                     │
│  allow → 自動実行                    │
│  ask   → ユーザーに確認プロンプト      │
│  deny  → ブロック（実行不可）          │
└─────────────────────────────────────┘
      │（Bash ツールの場合のみ）
      ▼
┌─────────────────────────────────────┐
│ [2nd ガード] pretooluse_guard.py    │
│ （PreToolUse hook）                 │
│                                     │
│  危険パターン検知 → 強制ブロック        │
│  正常パターン    → 通過              │
└─────────────────────────────────────┘
      │
      ▼
実行
```

**deny 対象の代表例**:
- `curl`, `wget`, `ssh`（外部通信）
- `sudo`（権限昇格）
- `git push origin main/develop`（保護ブランチへの直 push）
- `git push --force`（強制 push）
- `.env` / `*.pem` / `*.key` の読み書き（シークレット保護）

---

## ファイル間の依存関係

```
CLAUDE.md（起点）
  │
  ├─ 参照 ──→ docs/runbooks/*.md（詳細ルール）
  │             ├─ workflow.md
  │             ├─ plan-writing-rules.md  ←── /plan が必読
  │             ├─ issue-flow.md          ←── /issue-bootstrap が参照
  │             ├─ backend-check.md       ←── /implement が実装後に実行
  │             ├─ review-rules.md        ←── /plan, /implement, /close が参照
  │             └─ ...
  │
  ├─ 参照 ──→ rules/*.md（コーディング規約）
  │             ├─ ultimate_django_coding_standards.md  ←── /plan, /implement が必読
  │             └─ react-coding-standards-integrated.md ←── /plan, /implement が必読
  │
  └─ 参照 ──→ .claude/settings.json（権限）
                └─ hooks → scripts/claude/hooks/pretooluse_guard.py
```
