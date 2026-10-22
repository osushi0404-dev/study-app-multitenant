# plan_I183: djangorestframework を 3.18.0 から 3.18.2 に更新する — CVE-2026-114136・114137・114138 による pip-audit 失敗（develop 宛て全 PR の停止）の解消

## 基本情報
- **計画書ID**: plan_I183
- **関連イシュー**: #309（docs/issues/open/I183.md）
- **Draft PR**: #310
- **作成根拠資料**: docs/issues/open/I183.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I183_review.md
- **作成日**: 2026-10-23

## 1. 背景/目的

### 原因の概要
アプリ側は何も変えていないのに、使っている djangorestframework 3.18.0 に脆弱性が 3 件公開されたため、CI の依存監査（pip-audit）が不合格になり、develop 宛ての PR がすべてマージできなくなっている。

### 詳細な原因分析
- CI「Backend Lint & Security」ジョブ（`.github/workflows/ci.yml:26-28`）の `pip-audit -r requirements.txt`（working-directory: backend）が exit 1 で失敗する（run 39856491985・PR #308。I182 の変更とは無関係）。
- 依存は `backend/requirements.txt` でバージョン固定しているため、公開後の脆弱性は手で上げるまで残る。
- PR ゲートの pip-audit は「その PR で持ち込んだ脆弱性」ではなく「既存の全脆弱性」で失敗するため、無関係な PR まで止まる（根本の是正は I152 #268・本計画の対象外）。

### 目的
`backend/requirements.txt` の djangorestframework を修正版 3.18.2 に上げて pip-audit を通し、develop 宛ての PR の CI を緑に戻す。アプリの正常な動作（API・認証・テスト）は変えない。

## 2. 調査結果（2026-10-23 実測・本セッションで実行）

### 環境前提確認
- ベースブランチ: `origin/develop`（cc7904e）。`backend/requirements.txt` 2 行目は `djangorestframework==3.18.0`、3 行目は `djangorestframework-simplejwt==5.5.1`（I183 作成時から変化なし）。
- Docker: `docker compose ps` で backend / celery / celery-beat / db / redis が稼働中。稼働中 backend コンテナの版は DRF 3.18.0・simplejwt 5.5.1（`pip show`）。
- backend コンテナに `pip-audit 2.10.0`（`requirements-dev.txt` 3 行目で固定＝CI と同じ版）・`pytest 9.0.3` あり。ホスト WSL には pip が無いため、監査とテストは backend コンテナで実行する。
- 対話シェルの `grep` はラッパー（ugrep）で `-x` が誤動作する（`grep -qx` が不一致でも exit 0 を返すことを本セッションで再現）。TC では `/usr/bin/grep` をフルパスで使う。

### 監査の再現（CI と同条件）
- 現状: `docker compose exec backend pip-audit -r requirements.txt` → **exit 1**・CI と同じ 3 件（CVE-2026-114136・114137・114138、Fix Versions 3.18.2）。
- 模擬適用: DRF の行だけを `==3.18.2` にした写し（作業用フォルダ・リポジトリ無改変）を同じコンテナで監査 → **`No known vulnerabilities found`（exit 0）**。ほかの依存に新しい脆弱性は無い（/grill-me 時の結果と一致・advisory DB のドリフトなし）。

### 3.18.0 → 3.18.2 の変更内容（GitHub の 3.18.0...3.18.2 比較・リリースノートで確認）
3.18.1（2026-09-07）と 3.18.2（2026-10-06）の 2 リリース分が入る。

| 区分 | 内容 | このアプリへの影響 |
|------|------|-------------------|
| 脆弱性（3.18.2） | GHSA-33wh-fxxf-88vv: 巨大な `Accept` ヘッダによるコンテンツネゴシエーションの負荷を抑える | 全 API に効く（防御の強化）。独自のネゴシエーションクラスは無い（`DEFAULT_CONTENT_NEGOTIATION_CLASS` 未設定）。通常のクライアントの `Accept` には影響なし |
| 脆弱性（3.18.2） | GHSA-3547-9m27-7rxg: `Content-Type` の charset に bz2_codec 等の非テキスト codec を指定させない（小さな本文が展開されてメモリ上限を超える問題） | 全 API に効く（防御の強化）。パーサは標準の `JSONParser`・`MultiPartParser` のみ（`core/settings.py:157-160`）で独自パーサ・`parser_context` の直接参照は無い。utf-8 の通常リクエストには影響なし |
| 脆弱性（3.18.2） | GHSA-xw6w-gcfp-cf8m: admin の `TokenProxy` 削除が実際にトークンを消さない | `rest_framework.authtoken` は `INSTALLED_APPS` に無い（認証は simplejwt の JWT のみ）ため該当しない |
| 不具合修正（3.18.1） | `FloatField` が入力の nan / inf を拒否する | 入力を受ける `FloatField` に nan/inf が来た場合だけ 400 になる（従来は受理）。`studylogs/serializers.py` の明示 `FloatField` はすべて統計の出力用（`Serializer` の集計値・`read_only=True`）。不正値を弾く方向の修正で、正常な入力の振る舞いは変わらない |
| 不具合修正（3.18.1/3.18.2） | 一意制約の検証の修正（`blank=True` の欄が必須扱いされる問題・条件付き `UniqueConstraint`・`many=True` 時の一意制約） | アプリは `unique_together` を使用（`problems/models.py`・`studylogs/models.py`）。条件付き `UniqueConstraint` は無い。誤検知を直す方向の修正で、既存テストで回帰を確認する（TC-05） |
| 不具合修正（3.18.1） | `GenericIPAddressField` の重複エラー・OpenAPI スキーマの int64 判定 | 該当機能を使っていない |
| その他（3.18.1） | `LIST_SERIALIZER_ERRORS_AS_DICT` 設定の追加（既定 `True`＝3.18.0 と同じ形式） | 設定していないので 3.18.0 の挙動のまま |
| その他（3.18.1） | 非推奨警告クラスの整理 | `pytest.ini` に警告をエラー化する設定は無い（`addopts = --no-migrations` のみ）。テストの合否に影響しない |

### simplejwt 5.5.1 との共存
- /grill-me（2026-10-23）で pip-audit の依存解決がエラー無く通ることを確認済み。実装後はコンテナ内で `pip check`（依存の不整合なし）を TC-06 で確認する（現状のベースライン: `No broken requirements found.`）。

### 既存テストの事前実行（ベースライン）
- `docker compose exec backend pytest -q -p no:cacheprovider` → **103 passed, 5 warnings（20.93s・exit 0）**。警告は `core/storage_service.py` の `imghdr` 非推奨（既存・DRF と無関係）。

### Dockerfile・docker-compose への波及
- `backend/Dockerfile` 18〜19 行目で `requirements.txt` を COPY して `pip install` する（base ステージ）。dev / production の両ステージが base を継承するので、どちらも新しい版で作られる。Dockerfile 自体の変更は不要。
- docker-compose.yml で同じ backend イメージ（`context: ./backend`・`target: dev`）を使うサービス: `backend`・`celery`・`celery-beat`・`e2e-init`。手元はこれらのイメージの作り直しが要る（CI は毎回 `pip install -r requirements.txt` するので作り直し不要）。

## 3. 受け入れ条件（イシューの AC を転記）
- [ ] `backend/requirements.txt` の djangorestframework が 3.18.2 になっている → TC-01・TC-02
- [ ] `pip-audit -r backend/requirements.txt` が既知の脆弱性 0 件で終わる（CI の `Backend Lint & Security` が成功）→ TC-03・M1
- [ ] backend のテスト（CI の `Backend Tests`）と E2E が成功する → TC-05・M1
- [ ] 本イシューの PR の必須チェックがすべて緑になる → M1（マージ後の PR #308 への develop 取り込みと緑の確認は I182 側の作業・M3 は参考記録）

## 4. 影響範囲
| 領域 | 影響 |
|------|------|
| Backend | `backend/requirements.txt` 1 行のみ。アプリのコードは変更しない。DRF の振る舞いの変化は §2 の表のとおり（不正な入力を弾く方向のみ） |
| Frontend | なし |
| DB | なし（マイグレーション無し・TC-07 で確認） |
| Config/Infra | CI 定義・監査条件は変更しない。`backend/Dockerfile` は変更不要（requirements.txt を COPY してインストールするため自動で追従） |
| Docker（手元） | `backend`・`celery`・`celery-beat`・`e2e-init` が同じイメージを使うため、作り直しと再起動が要る（ステップ 2） |

## 5. 変更点一覧
| ファイル | 変更内容 |
|---------|---------|
| `backend/requirements.txt` | 2 行目 `djangorestframework==3.18.0` → `djangorestframework==3.18.2` |

ほかの依存（simplejwt 等）は変えない。変更が必要になった場合は計画との不一致として止めて報告する。

## 6. 実装手順

### 修正アプローチ
`backend/requirements.txt` の DRF の行を 1 行だけ書き換え、手元のイメージを作り直してコンテナに新しい版を入れたうえで、監査・テスト・依存の整合を確かめる。模擬適用で監査 0 件を実証済みのため、残る未知リスクは advisory DB のドリフト（実装時に新しい脆弱性が増えている可能性）と、3.18.1 の不具合修正による既存テストの回帰だけ。

### ステップ1: requirements.txt の更新（唯一のコード変更）
- **修正方針**: DRF を修正版に上げる。依存マニフェストの編集は settings.json の `ask` で確認が出る（イシュー「制約・引き継ぎ情報」のとおり）。
- `backend/requirements.txt` 2 行目を `djangorestframework==3.18.2` に変更する → TC-01・TC-02 参照
- 変更直後に監査を実行する → TC-03 参照。新しい脆弱性が出て 0 件にならない場合は止めて報告する（スコープ「含まない」のとおり、別イシューにするかをその時点で判断）。

### ステップ2: 手元イメージの作り直しと再起動（ステップ1 完了が前提）
- **修正方針**: コンテナに 3.18.2 を入れる（イメージは requirements.txt をビルド時にインストールするため、作り直さないと 3.18.0 のまま）。
- `docker compose build backend celery celery-beat e2e-init` を実行する。
- `docker compose up -d backend celery celery-beat` で作り直したイメージに切り替える（実装後にサービス再起動が必要）。
- 版と依存の整合 → TC-04・TC-06 参照

### ステップ3: 回帰確認（ステップ2 完了が前提）
- backend のテスト・マイグレーションの差分なしを確認する → TC-05・TC-07 参照。結果を `docs/tests/open/I183_auto_test.md` に記録する。

### ステップ4: コミット・プッシュ・CI 確認（ステップ3 完了が前提）
- requirements.txt と記録をコミットし PR #310 へ push する。CI（E2E を含む）の全チェックが緑になることを確認する → M1・M2 参照。

## 7. テスト計画
- 自動: `docs/tests/open/I183_auto_test.md`
  - TC-01 版の行が 3.18.2 / TC-02 変更が 1 行だけ / TC-03 pip-audit 0 件 / TC-04 コンテナの版 / TC-05 pytest 回帰 / TC-06 依存の整合（pip check）/ TC-07 マイグレーション差分なし
- 手動: `docs/tests/open/I183_manual_test.md`
  - M1 PR #310 の CI 全チェック緑（E2E 含む）/ M2 pip-audit ステップのログ / M3（参考・I182 側）マージ後の PR #308 の CI 復旧
- テストレベル: 依存の版と監査は決定論チェック（TC-01〜04・06・07）、アプリの回帰は既存の結合テスト（pytest 103 件）と CI の E2E（Playwright）。アプリのコード変更が無く、認証・認可・テナント境界の変更も無いため、新しいテストケースの追加はしない（再発防止は I152 の PR ゲート是正と既存の定期監査 `dependency-audit.yml` の担当）。
- 失敗すべき時に失敗すること（false-green でないこと）は変更前の状態で確認済み（auto_test の各 TC の「false-green 検証」欄）。例外は回帰テストの TC-05 で、変更前でも合格するのが正しいため、3.18.0 のまま実行する誤合格を TC-04（コンテナの版の確認）で防ぐ。

## 8. ロールバック
- requirements.txt 更新コミットの revert（`git revert <commit>`）→ `docker compose build backend celery celery-beat e2e-init` → `docker compose up -d backend celery celery-beat` で 3.18.0 に戻る。データ・DB の影響なし（ただし戻すと pip-audit は再び失敗する）。

## 9. Risk & 回避策
| リスク | 回避策 |
|--------|--------|
| 計画時と実装時で advisory DB がドリフトし、別の依存に新しい脆弱性が出る | ステップ1 直後に TC-03 を実行。0 件にならない場合は止めて報告（スコープ外の依存更新はその時点で判断） |
| 3.18.1 の不具合修正（一意制約の検証・FloatField の nan/inf 拒否）で既存の振る舞いが変わる | TC-05（pytest 103 件）と CI の E2E で回帰を確認。§2 の調査で、変化するのは不正な入力を弾く方向だけと確認済み |
| simplejwt 5.5.1 との非互換 | /grill-me で依存解決を確認済み。TC-06（pip check）と TC-05（JWT 認証を通る API テスト）・E2E（ログイン）で実行時も確認 |
| 手元イメージを作り直し忘れ、テストが 3.18.0 のまま通ってしまう | TC-04 でコンテナの版が 3.18.2 であることを TC-05 の前に確認する |

## 10. セキュリティ・品質チェック（plan-issue 必須確認の記録）
- **要件適合性**: 変更は AC の範囲（DRF 1 行の更新と確認）のみ。仕様追加なし。マルチテナント・組織スコープ・ステータス遷移の変更なし。
- **セキュリティ**: セキュリティを改善する側の変更（3 件の脆弱性の解消）。認証・認可・機密データ・入力検証のコードは変更しない。DRF 側の入力検証は強化される方向（非テキスト charset の拒否・巨大 Accept の抑制・FloatField の nan/inf 拒否）。
  - **重大度基準**: pip-audit は既知の脆弱性 1 件以上で失敗（CI の判定どおり・修正対象は全件）。bandit は Python コードの変更が無いため対象外（基準は MEDIUM 以上を修正・LOW は `# nosec`）。npm audit は frontend 変更なしのため対象外。
  - **追加・更新する依存の既知脆弱性**: 3.18.2 で pip-audit 0 件を実測済み（§2）。
- **テスト計画**: バグ修正ではなく依存更新のため、再発防止の新規テストは無し（理由は §7）。テストレベルは §7 に明記。認可変更なし。
- **P3（データ整合性）/ P5（運用設計）/ P8（コスト）影響なし**: DB 変更・外部 API・非同期処理・新規インフラなし。依存ファイル変更に伴う Dockerfile・docker-compose への波及は §2・§4 に記載済み（Dockerfile 変更不要・手元イメージの作り直しのみ）。
- **P6（性能・UX）影響なし**: UI・アプリコードの変更なし。
- **P9（プライバシー）影響なし**: 個人情報・テナントデータの扱いを変えない（脆弱性の解消はデータ保護の前提を戻すもの・品質基準 C2）。高リスク判定の対象外。
- **設計品質**: アプリのコード変更なし（アンチパターン・null 方針・例外処理の変更なし）。版はマニフェストで固定する既存方針どおり。
- **設計判断の明示**:
  | 設計判断 | 根拠 |
  |----------|------|
  | DRF を 3.18.2 に上げる（3.18.1 経由・3.19 系には上げない） | イシューに明記（Fix Versions 3.18.2・パッチ版） |
  | ほかの依存は変えない | イシューに明記（スコープ「含まない」） |
  | CI 定義・PR ゲートは変えない | イシューに明記（I152 に分離） |
  | 手元は `backend`・`celery`・`celery-beat`・`e2e-init` のイメージを作り直す | イシューに明記（イメージの作り直しが要る）。対象サービスは docker-compose.yml の build 定義から特定 |
  | `LIST_SERIALIZER_ERRORS_AS_DICT` は設定しない（既定＝3.18.0 と同じ形式） | 仮定ではなく既定値で 3.18.0 と同じ挙動になることをリリースノートで確認 |
  | 新しいテストケースは追加しない | イシューの AC が既存テスト・E2E・pip-audit での確認を指定 |

  **仮定で決めた項目はない。**

## 11. 承認ポイント
- [ ] 変更は `backend/requirements.txt` の 1 行だけ（`djangorestframework==3.18.0` → `==3.18.2`）。ほかの依存・CI 定義・Dockerfile は変えない
- [ ] 3.18.1 の不具合修正も一緒に入る（FloatField の nan/inf 拒否・一意制約の検証の修正など）。変化は不正な入力を弾く方向だけで、既存テストと E2E で回帰を確認する
- [ ] 手元の `backend`・`celery`・`celery-beat`・`e2e-init` のイメージを作り直し、`backend`・`celery`・`celery-beat` を再起動する
- [ ] マージ後の PR #308（I182）への develop 取り込みと CI 確認は I182 側（wt-harness のセッション）で行う

## レビュー結果
- [20261023_0709 判定: ✅ 完了](../../reviews/I183_plan_review_20261023_0709.md)
