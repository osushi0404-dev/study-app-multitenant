# 計画書 I079: 実装フェーズの編集承諾を削減（backend/frontend を permissions.allow に追加）

## 基本情報
- **計画書ID**: plan_I079
- **関連イシュー**: #158
- **Draft PR**: #159（`feature/I079-relax-edit-permissions` → develop。旧 PR #157 を置き換え・クローズ済み）
- **作成根拠資料**: docs/issues/open/I079.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I079_review.md
- **作成日**: 2026-06-27

## 1. 背景/目的
承認済みの実装フェーズに入った後も、`backend/**`・`frontend/**` のソースコードを編集するたびに承諾プロンプトが出る。実装してよいかの価値判断は「計画承認＋`/implement`」というワークフローゲートで既に取得済みであり、その後の1ファイルごとのツール権限プロンプトは二重確認＝機械的ノイズになっている。

機械的確認（編集の実行）と価値判断（方針）を権限レイヤーで分離し、アプリコードの編集ノイズを除去する。一方で「変更が重く価値判断寄り」のファイル（依存・スキーマ・インフラ）はプロンプトを残す。

### 調査結果
- 現状 `.claude/settings.json` の `permissions.allow` で `Write`/`Edit` は `docs/**` のみ許可（コードパスは未許可 → 毎回 ask）。
- 既存 `deny` は機密ファイル（`.env`/`.env.*`/`secrets/**`/`*.pem`/`*.key`）を Write/Edit/Read で保護済み。`deny` は `allow` に優先する。
- 高リスク対象の実在を確認済み（全て存在）: `backend/requirements.txt`・`backend/requirements-dev.txt`・`backend/pyproject.toml`・`backend/init-db.sql`・`backend/Dockerfile`・`frontend/package.json`・`frontend/package-lock.json`・`frontend/Dockerfile`・`frontend/Dockerfile.dev`・`frontend/nginx.conf`。
- マイグレーションディレクトリ: `backend/{problems,studylogs,accounts}/migrations`。
- **環境前提**: アプリコード変更なしのため pytest/eslint ベースライン・lint 計測・依存監査（pip-audit/npm audit）は非該当。
- **先行実装の現状**: feature ブランチ `feature/I079-relax-edit-permissions`（Draft PR #159）に `Write/Edit(backend/**)`・`Write/Edit(frontend/**)` の allow がコミット済み（commit `166d21f`、旧 chore ブランチから引き継ぎ）。`Bash(bash scripts/claude/*)` の allow は作業ツリーに未コミットで存在。`deny` 群は未追加。旧 PR #157 は #159 へ置き換えクローズ。

## 重大な発見（fix-loop I079・2026-06-27）— deny>allow が成立しない
`/test` の挙動検証で、本設計の前提（broad allow ＋ deny 例外で高リスク群を保護）が**この Claude Code 環境で成立しない**ことが判明した。

- **再現/実測（default モード）**:
  - `backend/Dockerfile`（`Edit(backend/**)` allow ＋ `Edit(backend/Dockerfile)` deny の重複）→ 編集が**ブロックされず成功**（期待: ブロック）。
  - `backend/problems/migrations/0001_initial.py`（allow ＋ `Edit(**/migrations/*.py)` deny の重複）→ 同じく**成功**。
  - 対照: `./.env`（`Read(./.env)` deny のみ・allow と重複なし）の Read は **"denied by your permission settings" でブロック**。
- **確定した根本原因**: Edit/Write では、**パスが allow と deny の両方に一致すると allow が優先**され、deny は上書きしない。deny が実効的に効くのは **allow と重複しないパスだけ**（`.env` がブロックされたのは何も allow していないため）。
- **影響**: 高リスク群は全て `backend/**`・`frontend/**`（broad allow）配下にあるため、deny を列挙しても**保護されない**。AC#2/#4 は「エントリが存在する（設定）」は満たすが「ブロックする（挙動）」は**未達**。
- **対応方針（fix-loop・確定＝案D）**: 高リスク群の保護を **settings の `deny` から PreToolUse フック（`pretooluse_guard.py`）に移す**。理由: 設定 `deny` は (1) Edit/Write で重複 allow に勝てず (2) 我々が挙動を自動テストできない（fail-open かつ検証不能）。フックなら **決定論的・我々が制御・失敗注入でテスト可能・fail-safe**。broad allow は維持（I079 主目的のアプリコード無確認を保つ）。
  - 検討した代替: 案A（`deny` を `./`アンカー化）＝fail-open かつ自動検証不能で却下／案B（narrow allow）＝冗長・migrations ネスト依存で次善／案C（deny撤去）＝保護喪失で却下。
  - 機密ファイル（`.env`/`secrets`/`*.pem`/`*.key`）の `deny` は **重複 allow がなく実効（`.env` Read ブロックを実測）かつ Read も守る**ため settings 側に維持。フックは Edit/Write の高リスク群（依存/スキーマ/インフラ）を担当。

## 2. 受け入れ条件（イシュー AC を継承）
- [ ] `allow` に `Write/Edit(backend/**)`・`Write/Edit(frontend/**)`・`Bash(bash scripts/claude/*)` が含まれる（アプリコードは無確認）
- [ ] **PreToolUse フックが高リスク群（依存/ロックファイル/`**/migrations/*.py`/init-db.sql/Dockerfile/nginx.conf）への Edit/Write に `permissionDecision: "ask"` を返す**（プロンプト化・承認で編集可。案D の中核）
- [ ] フックがアプリソース（例 `backend/problems/views.py`）の Edit/Write は素通し（ask を出さない＝broad allow を阻害しない）
- [ ] フックの高リスク判定が **失敗注入で NG を返す**ことを確認済み（false-green でない）
- [ ] 危険 bash（force push 等）の既存 `exit 2` ハードブロックが維持されている
- [ ] settings の `hooks.PreToolUse` に `Edit|Write` マッチャが登録され、`pretooluse_guard.py` が呼ばれる
- [ ] 既存の機密ファイル `deny`（`.env`/`.env.*`/`secrets/**`/`*.pem`/`*.key` の Read/Edit/Write）が維持されている（settings 側・実効）
- [ ] settings から **実効しない高リスク `deny`（重複 allow 配下の Dockerfile/deps/migrations 等）を撤去**し、保護は誤解なくフックに一本化（pem/key は機密 deny として残置可）
- [ ] settings.json が有効な JSON である（`python3 -m json.tool` でパス）
- [ ] 実装開始の承認ゲート（計画承認＋`/implement`、CLAUDE.md 絶対ルール2 / `docs/runbooks/workflow.md`）は変更されていない

## 3. 影響範囲
- Backend: なし（アプリコード変更なし）
- Frontend: なし（アプリコード変更なし）
- DB: なし
- Config/Infra: `.claude/settings.json`（permissions ＋ hooks）、`scripts/claude/hooks/pretooluse_guard.py`（高リスク Edit/Write ブロック判定を追加）

## 4. 変更点一覧（案D）
対象ファイル: `.claude/settings.json`、`scripts/claude/hooks/pretooluse_guard.py`

### 4-1. `permissions.allow`（維持）
```
"Write(backend/**)", "Edit(backend/**)",
"Write(frontend/**)", "Edit(frontend/**)",
"Bash(bash scripts/claude/*)",
```

### 4-2. `permissions.deny`（機密のみ維持・実効しない高リスク群は撤去）
- 維持（重複 allow なし＝実効。Read も保護）: `Read/Edit/Write(./.env)`・`(./.env.*)`・`(./secrets/**)`、`Read(**/*.pem)`・`Read(**/*.key)`（pem/key の Edit/Write deny は残置可だが保護はフックが主）。
- **撤去**: Dockerfile / requirements*.txt / pyproject.toml / package.json / package-lock.json / `**/migrations/*.py` / init-db.sql / nginx.conf の Edit/Write deny（broad allow に負けて**実効しない**ため、誤解を生む設定を消しフックへ一本化）。

### 4-3. `settings.json` の `hooks.PreToolUse` に `Edit|Write` マッチャを追加
```jsonc
{ "matcher": "Edit|Write",
  "hooks": [{ "type": "command",
              "command": "python3 \"$CLAUDE_PROJECT_DIR\"/scripts/claude/hooks/pretooluse_guard.py" }] }
```

### 4-4. `pretooluse_guard.py` に高リスク Edit/Write の ask 判定を追加
- ⚠️ **必須**: 既存の早期 return `if data.get("tool_name") != "Bash": sys.exit(0)`（L23-24）を `if data.get("tool_name") not in ("Bash", "Edit", "Write"): sys.exit(0)` に変更する（または Edit/Write 判定をこのガードより前に置く）。これを怠ると Edit/Write が常に素通りし ask が一切出ない実装ミスになる。
- `tool_name in (Edit, Write)` のとき `tool_input.file_path` を取得し、プロジェクトルート相対へ正規化（`git rev-parse --show-toplevel` 基準）。
- 高リスクパターン（正規表現）に一致したら、**stdout に JSON を出力して `permissionDecision: "ask"` を返す**（プロンプト化・承認で編集可）＋理由を添える:
  ```json
  {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
   "permissionDecisionReason": "高リスクファイル（依存/スキーマ/インフラ）。編集を確認してください: <path>"}}
  ```
  対象: `(backend|frontend)/Dockerfile(.dev)?`・`frontend/nginx.conf`・`backend/requirements.*\.txt`・`backend/pyproject.toml`・`frontend/package(-lock)?.json`・`.*/migrations/.*\.py`・`backend/init-db.sql`
- 既存の **Bash ハードブロック判定（force push 等の `exit 2`）はそのまま維持**（high-risk Edit/Write のみ ask）。
- 非該当（アプリソース等）は何も出力せず `exit 0`（素通し）。

## 5. 修正アプローチ（案D）
高リスク群の保護を **settings の `deny`（Edit で重複 allow に勝てず・自動検証不能・fail-open）から PreToolUse フックへ移管**する。フックは高リスク Edit/Write に対し `permissionDecision: "ask"` を返して**プロンプト化**（承認すれば編集可＝価値判断の確認）。判定が明示コードのため **決定論的・制御可能・失敗注入でテスト可能・fail-safe**。broad allow は維持してアプリコード無確認（I079 主目的）を保つ。機密ファイルは settings `deny` が実効かつ Read も守るため据え置き。危険 bash の既存 `exit 2`（ハードブロック）は維持。

## 6. 実装手順（案D）
- **ステップ1**: `pretooluse_guard.py` に高リスク Edit/Write の ask 判定（`permissionDecision: "ask"` を返す）を追加。→ TC-H1〜H3 参照（フック単体・失敗注入含む）
- **ステップ2**: `settings.json` の `hooks.PreToolUse` に `Edit|Write` マッチャを登録し、実効しない高リスク `deny` を撤去。JSON 妥当性確認。→ TC-A1 参照
- **ステップ3**: 実機で挙動確認（default モード）: アプリコード編集=素通し／高リスク群編集=プロンプト（ask）が出て承認で編集可。→ M1〜M4 参照
- **ステップ4**: settings.json・フック・docs をコミット・push（PR #159 更新）。

依存: ステップ2はステップ1完了が前提。ステップ3はステップ1+2完了が前提。

## 7. テスト計画（案D）
- 自動（決定論・**フック単体**）: `I079_auto_test.md` の TC-H1（高リスクパス→`ask`+exit 0）・TC-H2（アプリパス→素通し・ask なし）・TC-H3（失敗注入で ask が出ないことを確認）・TC-H4（危険 bash の `exit 2` 維持）。＋ TC-A1（JSON 妥当性）・TC-A3/A4（機密 deny 維持・実効しない高リスク deny 撤去）。
- 手動（挙動・default モード）: `I079_manual_test.md`（アプリ編集=素通し／高リスク編集=プロンプト ask が出て承認で編集可）。

## 8. ロールバック
`pretooluse_guard.py` の追加判定ブロックと、`settings.json` の `hooks.PreToolUse` Edit|Write 登録を除去。撤去した機密以外の `deny` 復元は不要（実効しなかったため）。DB・サービス影響なし、再起動不要。

## 9. Risk & 回避策
| Risk | 影響 | 回避策 |
|------|------|--------|
| ~~`deny` が `allow` に優先しない／migrations グロブが効かない~~ → **顕在化したが案Dで解決**: 保護をフックへ移管 | 中→解消 | 案D（フックが高リスク Edit/Write に `ask` を返しプロンプト化）。フックは決定論的・失敗注入でテスト可能（TC-H3） |
| フックのパス正規化漏れ（絶対/相対・`./`有無・OS差）で高リスク判定をすり抜ける | 中 | TC-H1 を絶対パス/相対パス両方で実施。正規化を `git rev-parse --show-toplevel` 基準に統一（既存 HEAD チェックと同方式） |
| フック自体が無効化/未登録だと保護が外れる（fail-open） | 中 | settings の `hooks.PreToolUse` 登録を AC でチェック。`scripts/claude/hooks/` の変更は PR レビュー必須（絶対ルール3）。フック未登録時に CI で検知する余地は I080 等で検討 |
| 権限を緩めたことでワークフローゲート未経由の編集が起きる | 低 | allow は権限レイヤーのみ。実装開始の承認はワークフロー（`/implement`）で担保。機密は settings `deny`（実効）＋高リスクはフックで保護 |
| `Bash(bash scripts/claude/*)` allow により、悪意あるスクリプトが `scripts/claude/` に追加された場合に無確認実行され得る | 低〜中 | `scripts/claude/` 配下の変更は PR レビュー必須（develop/main 直 push は deny で禁止・絶対ルール3）。信頼境界はリポジトリの PR レビューで担保。範囲も `scripts/*` 全体でなく `scripts/claude/*` に限定 |

## 12. コスト・保守見積もり
- 低コスト・低保守。設定 JSON への静的追記のみ。新規インフラ・外部サービスなし。
- 保守負荷: 高リスク群は明示列挙のため、対象ファイルが増えた場合に追記が必要（broad allow 側はディレクトリ単位で自動追従）。

## セキュリティ・要件適合チェック結果
- **要件適合性**: イシュー AC の範囲内。仕様追加なし。マルチテナント/ステータス遷移は非該当（アプリロジック変更なし）。
- **セキュリティ**: アプリのコード変更なし＝OWASP/入力バリデーション/認証認可ロジックへの影響なし。本変更は開発ハーネスの権限設定。機密ファイル保護（既存 deny）は維持し、依存マニフェスト/ロックファイル/スキーマ/インフラ設定はむしろ deny 追加で**保護を強化**する。依存ライブラリの追加なし → pip-audit/npm audit 非該当。「アプリのセキュリティ影響なし／ハーネス権限は緩和と局所的強化の両面」。
- **テスト計画**: バグ修正ではないが、設定の回帰防止として allow/deny エントリ存在の決定論テスト（grep）と挙動の手動テストを用意。
- **P3/P5/P8（データ整合性/運用/コスト）**: DB・外部API・非同期処理なし → 影響なし。インフラリソース追加なし。
- **P6（性能・UX）**: UI なし・データ量/外部API懸念なし → 影響なし。
- **P9（プライバシー）**: 個人情報・未成年・テナントデータを扱わない → 影響なし。
- **設計品質**: アンチパターン非該当。設定値のハードコードは「設定ファイル自体」なので妥当。

## 設計判断の明示
| 設計判断 | 出所 |
|----------|------|
| 方式 (a)（broad allow + deny 例外） | イシュー明記（grill-me 確定） |
| 高リスク群の具体パス10種 | イシュー明記（grill-me 確定） |
| マイグレーションは手書き編集のみプロンプト維持 | イシュー明記（grill-me 確定） |
| `Bash(bash scripts/claude/*)` を allow 追加 | イシュー明記（grill-me 確定） |
| ~~PR #157 を新規ブランチを切らず更新する~~（対応済: feature ブランチ運用に変更し PR #159 で代替・#157 はクローズ済み） | イシュー明記（制約・引き継ぎ）→ 後に方針変更 |
| deny パターンは Write/Edit 両方を列挙 | 仮定で決めた → プランレビューで既存実装と一致を確認（既存 deny も `Read`/`Edit`/`Write` を個別行で列挙）。承認ポイントでも確認する |

→ 「deny を Write/Edit 両方列挙」は、既存 settings.json の `deny`（`Read(./.env)`/`Edit(./.env)`/`Write(./.env)` を独立行で列挙）と一貫しており妥当（プランレビュー I079_plan_review_20260627_0256 で確認済み）。最終確認として承認ポイントでも提示する。

## レビュー結果
- [20260627_1302 判定: ✅ 完了](../../reviews/I079_plan_review_20260627_1302.md)
- [20260627_1022 判定: ✅ 完了](../../reviews/I079_plan_review_20260627_1022.md)
- [20260627_0256 判定: ✅ 完了](../../reviews/I079_plan_review_20260627_0256.md)
