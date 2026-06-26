# 計画書 I079: 実装フェーズの編集承諾を削減（backend/frontend を permissions.allow に追加）

## 基本情報
- **計画書ID**: plan_I079
- **関連イシュー**: #158
- **Draft PR**: #157（既存・`chore/relax-impl-edit-permissions` → develop。新規作成せず本 PR を更新）
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
- **先行実装の現状**: PR #157（OPEN・未マージ）には `Write/Edit(backend/**)`・`Write/Edit(frontend/**)` の allow がコミット済み（commit `166d21f`）。`Bash(bash scripts/claude/*)` の allow は作業ツリーに未コミットで存在。`deny` 群は未追加。

## 2. 受け入れ条件（イシュー AC を継承）
- [ ] `allow` に `Write/Edit(backend/**)`・`Write/Edit(frontend/**)`・`Bash(bash scripts/claude/*)` が含まれる
- [ ] `deny` に高リスク群が `Write`/`Edit` 両方で含まれ、broad allow に優先する
- [ ] 既存の機密ファイル `deny`（`.env`/`.env.*`/`secrets/**`/`*.pem`/`*.key`）が維持されている
- [ ] settings.json が有効な JSON である（`python3 -m json.tool` でパス）
- [ ] 実装開始の承認ゲート（計画承認＋`/implement`、CLAUDE.md 絶対ルール2 / `docs/runbooks/workflow.md`）は変更されていない

## 3. 影響範囲
- Backend: なし（アプリコード変更なし）
- Frontend: なし（アプリコード変更なし）
- DB: なし
- Config/Infra: `.claude/settings.json`（Claude Code 権限設定）のみ

## 4. 変更点一覧
対象ファイル: `.claude/settings.json`

### 4-1. `permissions.allow` に追加
```
"Write(backend/**)", "Edit(backend/**)",
"Write(frontend/**)", "Edit(frontend/**)",      // ← commit 166d21f で追加済み
"Bash(bash scripts/claude/*)",                   // ← 作業ツリーに追加済み・未コミット
```

### 4-2. `permissions.deny` に追加（高リスク群・Write/Edit 両方）
```
"Edit(backend/requirements*.txt)",  "Write(backend/requirements*.txt)",
"Edit(backend/pyproject.toml)",     "Write(backend/pyproject.toml)",
"Edit(frontend/package.json)",      "Write(frontend/package.json)",
"Edit(frontend/package-lock.json)", "Write(frontend/package-lock.json)",
"Edit(**/migrations/*.py)",         "Write(**/migrations/*.py)",
"Edit(backend/init-db.sql)",        "Write(backend/init-db.sql)",
"Edit(backend/Dockerfile)",         "Write(backend/Dockerfile)",
"Edit(frontend/Dockerfile)",        "Write(frontend/Dockerfile)",
"Edit(frontend/Dockerfile.dev)",    "Write(frontend/Dockerfile.dev)",
"Edit(frontend/nginx.conf)",        "Write(frontend/nginx.conf)",
```

## 5. 修正アプローチ
broad allow（アプリコード全体を無確認）＋ deny 例外（高リスク群はプロンプト維持）の二段構成にする。「価値判断はゲートで確認・機械的編集は自動」という主旨を権限設定で表現する。narrow allow（ソースディレクトリ列挙）は新規ディレクトリ追加のたびに保守が必要なため不採用（grill-me で確定）。

## 6. 実装手順
> ⚠️ 未知リスク先行: 「deny が broad allow に優先するか」「`**/migrations/*.py` グロブが効くか」が本変更の最大の不確実性。ステップ1で実挙動を確認する。

- **ステップ1（未知リスク検証）**: `deny` 群を `.claude/settings.json` に追記し、JSON 妥当性と「deny 優先・グロブ一致」の実挙動を確認する。→ TC-A1, TC-A2, TC-M1, TC-M2 参照
- **ステップ2**: 作業ツリーに未コミットの `Bash(bash scripts/claude/*)` allow を含め、settings.json の全変更を PR #157 のブランチにコミット・push する。→ TC-A1 参照
- **ステップ3**: PR #157 の本文へ `Closes #158` を追記し、イシューと紐づける。

依存関係: ステップ2はステップ1完了が前提。ステップ3は独立。

## 7. テスト計画
- 自動（決定論）: docs/tests/open/I079_auto_test.md（JSON 妥当性・allow/deny エントリの存在 grep・既存機密 deny の不変）
- 手動（挙動）: docs/tests/open/I079_manual_test.md（アプリコード編集が無確認・高リスク群編集がプロンプト）

## 8. ロールバック
`.claude/settings.json` の追加分（allow 3系統・deny 20行）を削除して元に戻すのみ。DB・サービスへの影響なし、再起動不要。

## 9. Risk & 回避策
| Risk | 影響 | 回避策 |
|------|------|--------|
| `deny` が `allow` に優先しない実装だった場合、高リスク群が無確認編集される | 中（誤って依存/スキーマを無確認編集） | ステップ1の TC-M1 で deny 優先を実挙動確認してからコミット。NG なら narrow allow 方式に切替（計画更新→再承認） |
| `**/migrations/*.py` グロブが効かない | 中（マイグレーションが無確認に） | TC-M2 で実挙動確認。効かなければアプリ別に列挙（`backend/*/migrations/*.py`）へ修正（計画更新→再承認） |
| 権限を緩めたことでワークフローゲート未経由の編集が起きる | 低 | allow は権限レイヤーのみ。実装開始の承認はワークフロー（`/implement`）で担保。機密は deny 優先で保護 |

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
| PR #157 を新規ブランチを切らず更新する | イシュー明記（制約・引き継ぎ） |
| deny パターンは Write/Edit 両方を列挙 | 仮定で決めた（deny は動作種別ごとに必要なため。承認ポイントで確認） |

→ 「仮定で決めた」項目（deny を Write/Edit 両方列挙）について承認ポイントで確認する。
