# plan_I097: 同時スタック起動対応 — ポート環境変数化 + worktree ごとの `.env` オフセット

## 基本情報
- **計画書ID**: plan_I097
- **関連イシュー**: #183
- **Draft PR**: #187
- **作成根拠資料**: docs/issues/open/I097.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I097_review.md
- **作成日**: 2026-07-02

---

## 1. 背景/目的

worktree ごとにコンテナ・named volume は `COMPOSE_PROJECT_NAME`（既定＝ディレクトリ名）で分離されるが、**ホストの publish ポートは共有**される。`docker-compose.yml` の db/redis/backend/frontend が固定ホストポート（5432/6379/8000/3000）をハードコードしているため、2 つの worktree で同時に `docker compose up` するとポート衝突で片方が起動失敗する。

worktree の本来の狙い（複数トラックの**並行**作業）が「編集は並行できるがスタックの同時起動・同時テストはできない」形で制約されている。本イシューでポートを環境変数化し、worktree ごとの直下 `.env` で分離することで**同時 up を可能**にする。

### 根本原因
`docker-compose.yml` のホストポートが環境変数でテンプレート化されておらず、worktree ごとにオフセットできない（`worktree.md` §6 が「別イシューで仕組み化する」と繰り越していた項目）。

### 調査結果
- **環境前提確認**: `docker compose version` → `Docker Compose version v5.1.0`（利用可）。`git` 利用可。
- **スパイク実証（未知リスク＝compose の変数展開挙動）**: throwaway compose（`ports: ["${BACKEND_PORT:-8000}:8000"]`）に対し `docker compose config` を実行し、以下を**実行可能な確認で再現**した（成立）:
  - `docker compose config` は **Docker デーモン無しでレンダリングできる**（config はパース/展開のみ）。
  - 変数未設定時は既定値（`published: "8000"` / `"3000"`）で展開される（後方互換の裏付け）。
  - compose ファイルのディレクトリ（＝worktree root）に置いた `.env`（`BACKEND_PORT=8010`）を読み、`published: "8010"` に変わる（per-worktree 分離機構の裏付け）。
  - → **AC#2/#5・決定論テスト② は達成可能**と確定。
- **既存テストのベースライン**: `bash scripts/claude/tests/test_wt_lifecycle.sh` → `pass=55 fail=0`（回帰基準）。
- **`.env.example` の追跡可否**: `git check-ignore .env.example` → exit 1（＝ignore されない＝追跡可能）。root `.env` は `.gitignore` の `.env` / `*.env` で ignore 済み（per-worktree・非共有）。
- **frontend↔backend 接続の自己解決**: `frontend/src/setupProxy.js` は `BACKEND_URL=http://backend:8000`（docker 内部ネットワーク名）へプロキシし、compose では `REACT_APP_API_BASE_URL=`（空）＝相対パス。ホスト publish ポートのオフセットで docker 内部接続は壊れない → `frontend/.env.*`・`setupProxy.js` は変更不要。e2e も内部ネットワーク（`BASE_URL=http://frontend:3000`）のため影響なし。

---

## 2. 受け入れ条件（Acceptance Criteria）

（起点イシュー I097 の AC を継承）

- [ ] AC1: `docker-compose.yml` の db/redis/backend/frontend のホストポートが既定値付き環境変数になっており、変数未設定時は現行ポート（5432/6379/8000/3000）で起動する（後方互換）
- [ ] AC2: `wt-new.sh` が未指定時に衝突しないオフセットを自動割当し、`--port-offset N` で上書きでき、既存 worktree と衝突する場合は fail する
- [ ] AC3: 2 つの worktree で異なるオフセットを与えると**同時に `docker compose up` してもポート衝突しない**（決定論テスト②=`docker compose config` レンダリングで publish ポート重複なしを立証）
- [ ] AC4: worktree ごとに `COMPOSE_PROJECT_NAME`（既定＝ディレクトリ名）でコンテナ/volume が分離されたまま維持される
- [ ] AC5: 決定論テスト①（オフセット/衝突ロジック）②（compose レンダリング・docker 無しは skip）が green
- [ ] AC6: `docs/runbooks/worktree.md` §6 が同時起動可能な手順に更新されている
- [ ] AC7: 既存の単一スタック運用（オフセット無し）が従来どおり動作する（既存 test_wt_lifecycle.sh が 55/55 のまま）

---

## 3. 影響範囲（Backend/Frontend/DB/Config）

| レイヤー | 影響 |
|---------|------|
| Backend | なし（アプリコード不変・ホスト publish ポートのみ可変化） |
| Frontend | dev サーバの publish ポート可変化（内部は不変）。`frontend/.env.*`・`frontend/src/setupProxy.js` は変更不要（docker 内部ネットワーク接続のため） |
| DB | なし（backend→db は内部ネットワーク `DB_HOST=db`・接続ポート不変。ホスト publish の 5432 のみ変数化） |
| Config/Infra | `docker-compose.yml`・`scripts/claude/wt-new.sh`・`scripts/claude/tests/`（新規2本）・`docs/runbooks/worktree.md`・`docs/runbooks/common-commands.md`（ポート変数の文書化はここへ集約＝当初の `.env.example` は deny ガードにより取り止め） |

**依存関係ファイルへの波及**: requirements*.txt / package*.json の変更なし → Dockerfile・compose ビルドターゲットへの波及なし（**P3/P5/P8 影響なし**）。

---

## 4. 変更点一覧（ファイル/関数）

| ファイル | 変更内容 |
|---------|---------|
| docker-compose.yml | db/redis/backend/frontend の `ports:` を既定値付き環境変数化。nginx は対象外（後述） |
| scripts/claude/wt-new.sh | `--port-offset N` 追加。未指定時は既存 worktree の `.env` を走査して空きオフセット自動割当・衝突時 fail・直下 `.env` 生成・確定ポート表示 |
| scripts/claude/tests/test_wt_port_offset.sh（新規） | 決定論テスト①（オフセット/衝突ロジック・docker 不要）＋ false-green 注入 |
| scripts/claude/tests/test_compose_ports.sh（新規） | 決定論テスト②（`docker compose config` レンダリングで publish ポート重複なし・docker 無しは skip） |
| scripts/claude/tests/test_wt_lifecycle.sh（既存・fixture のみ） | temp repo の `.gitignore` に `.env`/`*.env` を追加（実リポと整合。wt-new 生成の直下 `.env` が dirty 扱いにならないよう）。テスト内容・形式は不変 |
| docs/runbooks/worktree.md | §6 を同時起動可能な手順に更新。**§3 のコマンド例に `[--port-offset N]` を追記**（消費箇所の取りこぼし防止） |
| docs/runbooks/common-commands.md | ポート変数・オフセット確認・同時 up 手順の追記 |

### 4-1. docker-compose.yml（修正方針）

**修正アプローチ**: ハードコードされた `"HOST:CONTAINER"` の HOST 側のみを既定値付き変数に置換する。既定値＝現行値により、変数未設定でも従来どおり動く（後方互換）。コンテナ内部ポートは不変。

```yaml
# db
ports:
  - "${DB_PORT:-5432}:5432"
# redis
ports:
  - "${REDIS_PORT:-6379}:6379"
# backend
ports:
  - "${BACKEND_PORT:-8000}:8000"
# frontend
ports:
  - "${FRONTEND_PORT:-3000}:3000"
```

- **nginx（80/443）は対象外**: production profile 配下で既定 `docker compose up` では起動せず、並行 dev に不要。変数化すると「本番同時起動を支援する」誤解を招くうえ消費者が無いため見送る（イシュー確定事項）。
- **celery / celery-beat / e2e / e2e-init**: ホスト publish ポートを持たない（内部ネットワークのみ）ため変更なし。

### 4-2. ポート変数の文書化（修正方針・変更あり）

**変更理由（実装時の逸脱対応）**: 当初は追跡ファイル `.env.example` に記載する計画だったが、`.claude/settings.json` の deny ルール `Write(./.env.*)`（env ファイル誤書き込み防止のセキュリティガード）が `.env.example` に一致し作成不可。ガードをバイパスせず、変数の自己文書化は **runbook（`worktree.md` §6 / `common-commands.md`）に集約**する方針へ変更（ユーザー承認済み・settings 変更なし）。

**修正方針**: root `.env` は gitignore 対象で worktree ごとに非共有。非 wt-new 起動や手動運用でも変数が分かるよう、runbook に以下を明記する:
- ポート変数 4 種（`DB_PORT`/`REDIS_PORT`/`BACKEND_PORT`/`FRONTEND_PORT`）と既定値（5432/6379/8000/3000）。
- オフセット規約（STEP=10・primary=0, 次=10, ...）。
- `wt-new.sh` が新規 worktree 作成時に直下 `.env` を自動生成する（`--port-offset N` で明示指定可）こと。
- COMPOSE_PROJECT_NAME は `.env` に書かず既定（ディレクトリ名）で分離する旨。

### 4-3. scripts/claude/wt-new.sh（修正方針）

**修正アプローチ**: 既存の引数パーサに `--port-offset N` を追加し、`git worktree list` を走査して空きオフセットを決定、衝突を検出したら fail、確定ポートを新規 worktree 直下 `.env` に書き出す。既存の `.env`（backend）コピー・`--up` 等の挙動は不変。

**併せて更新する消費箇所（stale 防止・W2）**:
- `usage()` の Usage 文に `[--port-offset N]` を追記（引数パリティ）。
- 冒頭コメント（L4-8 相当）の使い方注記に `--port-offset` を追加。
- L65-66 の `# 任意 up（既定 OFF・§6 ポート衝突のため opt-in）` コメントを、I097 後の実態（§6 は同時 up 可能に変わる）に合わせて更新（例: `# 任意 up（既定 OFF・opt-in。同ホストで複数スタックを同時 up する場合は --port-offset でポート分離）`）。

**定数**:
```bash
PORT_STEP=10
# 各サービスの base（container 側と一致）
BASE_DB=5432; BASE_REDIS=6379; BASE_BACKEND=8000; BASE_FRONTEND=3000
```

**オフセット決定ロジック**（`git worktree add` の前に実行）:
1. `--port-offset N` が指定されていれば `OFFSET=N`（N は `^[0-9]+$` を検証。非整数は exit 2）。
2. 未指定なら自動割当: `git worktree list --porcelain` の各 worktree root について直下 `.env` の `BACKEND_PORT` を読み、`offset = BACKEND_PORT - BASE_BACKEND` を算出。`.env` 無し or `BACKEND_PORT` 無しは `offset=0`（＝既定ポート運用）として扱う。`OFFSET = max(collected) + PORT_STEP`。
3. **衝突検出（決定論ゲート）**: 確定ポート集合 `{BASE_* + OFFSET}` が、既存 worktree（`.env` 無しは既定ポート＝offset 0 とみなす）のいずれのポート集合とも重複しないことを検証。重複したら `exit 2`（メッセージ: `ポートが既存 worktree と衝突`）。

**`.env` 生成**（`git worktree add`・backend/.env コピーの後）:
```bash
cat > "$WT_PATH/.env" <<EOF
DB_PORT=$((BASE_DB + OFFSET))
REDIS_PORT=$((BASE_REDIS + OFFSET))
BACKEND_PORT=$((BASE_BACKEND + OFFSET))
FRONTEND_PORT=$((BASE_FRONTEND + OFFSET))
EOF
echo "[wt-new] ポート割当: offset=$OFFSET db=$((BASE_DB+OFFSET)) redis=$((BASE_REDIS+OFFSET)) backend=$((BASE_BACKEND+OFFSET)) frontend=$((BASE_FRONTEND+OFFSET))"
```

- 既定ポートを避けるため自動割当は必ず `+PORT_STEP` 以上になる（primary=offset 0 が collected に含まれるため min offset=10）。
- `--port-offset 0` を明示した場合は衝突検出が primary（既定ポート）と衝突を検知して fail する（意図的な同ポート指定を防ぐ）。

### 4-4. docs/runbooks/worktree.md §6 + §3（修正方針）

**修正方針（§6）**: 「1 スタックずつ・人手規律」の記述を「ポート変数化により同時 up 可能・wt-new が自動オフセット」に更新。ポート表は「既定値（変数未設定時）」と明記。COMPOSE_PROJECT_NAME 分離（既定＝ディレクトリ名）は維持される旨を残す。

**修正方針（§3・W1）**: §3 の `wt-new.sh` コマンド例（`... [--env-source <path>] [--up]`）に `[--port-offset N]` を追記し、実装した引数と runbook のパリティを保つ（消費箇所の取りこぼし防止）。→ TC-DOC1 で機械検証。

### 4-5. docs/runbooks/common-commands.md（修正方針）

**修正方針**: ポート変数（4 種）・オフセット確認（`docker compose config` で publish ポート確認）・同時 up 手順を追記。

---

## 5. 実装手順（ステップ）

> 各ステップの検証は auto_test.md の TC を参照（本文には検証コマンドを書かない）。

- **ステップ1（未知リスク先行・compose テンプレート化）**: `docker-compose.yml` の db/redis/backend/frontend の `ports:` を既定値付き環境変数化する。→ TC-D1/TC-D2 参照。
  - 依存: なし。最初に実施（変数展開がスパイクで実証済みだが実ファイルで再確認）。
- **ステップ2（wt-new オフセット機構）**: `wt-new.sh` に `--port-offset` 追加・自動割当・衝突検出・`.env` 生成を実装する。→ TC-P1〜TC-P6 参照。
  - 依存: ステップ1（生成する `.env` の変数がステップ1のテンプレートに対応）。
- **ステップ3（自己文書化）**: ポート変数 4 種・既定値・オフセット規約を runbook（`worktree.md` §6 / `common-commands.md`）に明記する（当初の `.env.example` は deny ガードにより取り止め）。→ TC-P7 参照。
  - 依存: ステップ1（変数名の一致）。ステップ2・5 と統合実施（runbook 更新に含める）。
- **ステップ4（決定論テスト）**: `test_wt_port_offset.sh`・`test_compose_ports.sh` を作成し全 TC を実行・記録する。→ 自動テスト文書。
  - 依存: ステップ1〜3。
- **ステップ5（runbook 更新）**: `worktree.md` §6・`common-commands.md` を更新する。→ TC-DOC1/TC-DOC2 参照。
  - 依存: ステップ1〜3（記述が実装と一致すること）。

**サービス再起動**: 本変更はファイル削除・稼働サービス停止を伴わない（既存の起動中スタックは次回 up 時に新テンプレートを反映）。

---

## 6. テスト計画（自動/手動）

### テストレベルの選択
- **決定論シェルテスト（ユニット/結合）**: wt-new のオフセット/衝突ロジック（docker 非依存・`test_wt_port_offset.sh`）。既存 `test_wt_lifecycle.sh` の隔離方式（temp repo + docker スタブ）を踏襲。
- **compose レンダリング検証（結合）**: `docker compose config` の publish ポート重複なし（`test_compose_ports.sh`・docker 無しは SKIP）。
- **回帰**: 既存 `test_wt_lifecycle.sh` が 55/55 のまま（後方互換・既定ポート運用の無改変）。
- **手動スモーク（任意）**: 実際に 2 worktree を異なるオフセットで同時 up し衝突しないことを目視（環境依存・補助）。

### 認証・認可・テナント境界テスト
- 該当なし（アプリの認証・認可・テナント境界に変更なし。ホスト publish ポートの変数化のみ）。

### false-green 自己検証（必須）
- 否定/衝突/回帰系 TC（TC-P3 衝突 fail・TC-D3 publish 重複検出）は、**失敗条件を注入して実際に NG（非ゼロ）になること**を確認してから採用する（TC-P6 が衝突ガード除去複製で衝突が素通りする＝実体の停止要因がガードである反証。TC-D3 は同一オフセットを与えると重複検出でテストが FAIL することを確認）。

詳細は docs/tests/open/I097_auto_test.md / I097_manual_test.md 参照。

---

## 7. ロールバック
- 本変更は追加・テンプレート化が中心で後方互換（既定値＝現行値）。問題時は該当コミットを revert すれば従来のハードコードポートに戻る。生成された各 worktree の root `.env`（gitignore・未追跡）は残るが、compose の既定値により削除しても従来動作に戻る。

---

## 8. Risk & 回避策

| Risk | 対策 |
|------|------|
| 既定値の書き間違いで後方互換が壊れる | AC1・TC-D1 で「変数未設定＝現行ポート」を決定論検証（最重要 AC） |
| オフセット自動割当が既存と衝突 | 衝突検出を fail ゲート化（TC-P3）。false-green 防止に除去複製注入（TC-P6） |
| `docker compose config` が CI/環境で使えない | TC-D* は docker 非在時 SKIP（非ブロック）。ロジック側は docker 非依存の TC-P* で担保 |
| root `.env` が誤って追跡される | `.gitignore` の `.env`/`*.env` で既に ignore（調査結果で確認済み）。加えて `settings.json` の deny `Write(./.env.*)` が env ファイル書き込み自体を抑止 |
| frontend↔backend 接続断 | docker 内部ネットワーク接続のため publish ポート非依存（調査結果で実証）。frontend env 不変 |

---

## 9. セキュリティ・要件適合性チェック結果（承認ポイント前セルフチェック）

- **要件適合性・業務ロジック**: AC の範囲内。仕様追加なし。マルチテナント閲覧/操作範囲・ステータス遷移に変更なし（該当なし）。
- **セキュリティ**: **セキュリティ影響なし**（インフラ設定＝ホスト publish ポートの変数化のみ・アプリコード不変）。db/redis のホスト publish は現状の既定でも公開されており、オフセットで露出面は増えない。機密情報（パスワード/トークン）を新規に扱わない。root `.env` は gitignore 済み。OWASP Top 10 該当なし（XSS/SQLi/CSRF に関わるコード変更なし）。依存ライブラリ変更なし（pip-audit/npm audit 対象外）。
  - **pre-existing の認識（レビュー I2）**: db(5432)/redis(6379) をホストへ publish する設計は本イシュー以前から存在する開発環境専用設定。本変更で新規リスクは追加されず、オフセットによる露出面の変化もない。非ローカル環境デプロイ時の注意は既存の設計課題として範囲外（本イシューでは変更しない）。
- **設計品質**: ハードコード回避（既定値は compose の `:-` 既定に集約＋runbook に文書化、STEP は wt-new の名前付き定数 `PORT_STEP`、base は `BASE_*` 定数）。null/空値: `.env`/`BACKEND_PORT` 不在は offset 0 として扱う方針を統一。例外処理: 衝突・不正引数は exit 2 で明示停止（既存 wt-new の契約と一致）。アンチパターン踏襲なし。
- **P3（データ整合性）/P5（運用）/P8（コスト）/P6（性能・UX）/P9（プライバシー）**: **いずれも影響なし**（DB スキーマ・マイグレーション変更なし／外部 API・非同期・バッチなし／新規インフラ・外部サービスなし／UI コンポーネント変更なし／個人情報・未成年・テナントデータを扱わない）。

### 設計判断の明示（イシュー明記 / 仮定 の区別）
| 設計判断 | 区分 |
|---------|------|
| 直下 `.env` 方式（override 不採用） | イシューに明記（設計確認メモ） |
| 対象は db/redis/backend/frontend の 4 サービス・nginx 除外 | イシューに明記 |
| 変数名 `DB_PORT`/`REDIS_PORT`/`BACKEND_PORT`/`FRONTEND_PORT`・既定＝現行値 | イシューに明記 |
| `--port-offset` 追加・未指定は自動割当・衝突 fail・STEP=10 | イシューに明記 |
| COMPOSE_PROJECT_NAME は `.env` に書かず既定（ディレクトリ名）維持 | イシューに明記（設計確認メモ2回目） |
| ポート変数の文書化を runbook へ集約（`.env.example` は deny ガードにより取り止め） | 実装時の逸脱対応・ユーザー承認済み（当初はイシュー明記の `.env.example`） |
| 決定論テスト①②の構成 | イシューに明記 |
| 自動割当を `max(既存 offset)+STEP` とする／`.env` 無しは offset 0 とみなす | 実装詳細（後方互換 AC から導出。仮定ではなく AC 整合の帰結） |
| テストを新規 2 ファイルに追加。既存 test_wt_lifecycle.sh は**fixture の .gitignore に `.env`/`*.env` を追加するのみ**（テスト内容・形式は不変） | 実装詳細＋実装時の必要変更。wt-new が直下 `.env` を生成するようになったため、temp repo を実 `.gitignore` に揃えないと生成 `.env` が dirty 扱いになり wt-remove テストが誤 abort する（実運用では `.env` は gitignore 済みで問題なし）。テスト形式/フレームワーク変更ではない |

→ **自由な仮定で決めた設計判断は無し**（すべてイシュー明記、または AC からの機械的帰結）。

---

## 承認ポイント（このチェックで OK なら実装開始）

1. **compose 変数化の範囲**: db/redis/backend/frontend の 4 サービスのホストポートを `${VAR:-現行値}` 化し、**nginx は対象外**とする方針でよいか。
2. **wt-new のオフセット挙動**: 未指定時は `max(既存offset)+10` を自動割当、`--port-offset N` で上書き、衝突時は exit 2 で fail、確定ポートを直下 `.env` に生成、という挙動でよいか。
3. **ポート変数の文書化**: （実装時変更・承認済み）`.env.example` は deny ガードにより取り止め、4 変数・既定値・オフセット規約を runbook（worktree.md §6 / common-commands.md）に集約する。
4. **テスト構成**: 決定論テストを新規 2 ファイル（ロジック用 docker 非依存 + compose レンダリング用 docker 任意 SKIP）に追加し、既存 `test_wt_lifecycle.sh` は改変しない方針でよいか。
5. **セキュリティ影響なし**の判定（インフラ設定のみ・アプリコード不変）に同意いただけるか。

## レビュー結果
- [20260702_2215 判定: ✅ 完了](../../reviews/closed/I097_plan_review_20260702_2215.md)

## 完了情報
- **完了日時**: 2026-07-02
- **対応者**: Claude Code
- **レビュー結果**: OK（plan-review OK / code-review OK・高リスク No）
- **テスト**: 自動 test_wt_port_offset.sh 34/34・test_compose_ports.sh 13/13・回帰 test_wt_lifecycle.sh 55/55、手動 No1〜8 OK（No7/No8 は実機 2 スタック同時 up スモーク）
- **逸脱対応**: `.env.example`（deny ガード）→ runbook 集約／wt-new の `.env` 生成に伴う既存 fixture 整合（いずれも計画反映・承認済み）
