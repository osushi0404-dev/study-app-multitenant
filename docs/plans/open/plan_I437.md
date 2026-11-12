# 計画書: I437 監視の記録から利用者のメールアドレスを外す（個人情報をログに残さない）

## 基本情報
- **計画書ID**: plan_I437
- **関連イシュー**: #437
- **Draft PR**: #482
- **作成根拠資料**: docs/issues/open/I437.md（GitHub #437 の本文の写し）
- **実装後評価**: docs/reviews/open/I437_review.md
- **作成日**: 2026-11-12

## 1. 背景/目的
イシューの「背景/目的」と同じ。学習アプリの利用者には未成年も含まれうるので、ログに個人を特定できる値（メールアドレス・氏名・ログイン ID）や秘密（パスワード・リフレッシュトークン）を残さない。ログは調べものの途中で外に出やすい（イシューへの貼り付け・外部の監視サービスへの送信）。利用者は ID（`User.id`）で追えるようにする。

### 調査結果
**原因の概要**: ログを書くコードの多くが、利用者そのもの（`user.email`・`str(user)`。`User.__str__` はメールアドレスを返す）や、送られてきた内容をそのまま書いている。「ログには ID だけを書く」決まりが無かった。

**ログの出力先**（`backend/core/settings.py:311-314` → `backend/core/enhanced_logging.py:276-357`）: `backend/logs/` の `django.log`・`django_detailed.jsonl`・`errors.jsonl`（30 日分を日ごとに回す）と標準出力（コンテナのログ）。`core.monitoring`・`core.subject_service` は root、`accounts/views.py`・`RequestLoggingMiddleware` は `django`、`ErrorContextMiddleware` は `django.request`（`propagate=False`）に書く。

**個人情報を書いている所（2026-11-12 に `backend/` の本番コード〔tests・migrations を除く〕の logger・print を全件 grep して読んだ結果）**:
| No | 場所 | 書いているもの | いつ |
|---|---|---|---|
| P1 | `backend/core/monitoring.py:173`（`ErrorTracker.log_error`） | `'user_email': user.email` | 想定外のエラーのたび（`MonitoringMiddleware.process_exception`） |
| P2 | `backend/core/monitoring.py:382`（`UserActivityMonitor.log_user_activity`） | `'user_email': user.email` | 問題の一覧・学習記録などの API のたび（`MonitoringMiddleware.process_response`。DRF が認証後の利用者を元の request にも入れるので、JWT の利用者でも入る）・AI の問題作成（`backend/problems/views.py:401・537`） |
| P3 | `backend/core/middleware.py:221`（`RequestLoggingMiddleware.process_request`） | `User: {request.user.email}` | `/api/` の呼び出しのたび（セッションでログインした利用者。JWT はこの時点ではまだ匿名） |
| P4 | `backend/accounts/views.py:90`（`UserRegistrationView.create`） | `Registration attempt with data: {mutable_data}` — **送られた内容を丸ごと書くので、メールアドレス・ログイン ID・パスワード・パスワード確認が平文で入る** | 新規登録のたび（grill-me の後の全件確認で新しく見つかった） |
| P5 | `backend/accounts/views.py:106`（同） | `User created successfully: {user.email}` | 新規登録の成功のたび |
| P6 | `backend/accounts/views.py:178`（`send_verification_email`） | `print(f"Email verification token for {user.email}: {token}")` | 開発環境（`DEBUG`）での新規登録のたび |
| P7 | `backend/core/subject_service.py:43・91`（`SubjectService.get_user_subjects`・`get_subject_by_id`） | `User {user} has no organization_id`（`str(user)` = メールアドレス） | 組織の無い利用者が科目を取るたび（grill-me の後の全件確認で新しく見つかった） |
| P8 | `backend/core/enhanced_logging.py:228-231`（`ErrorContextMiddleware._safe_body`） | 4xx・5xx になった POST の本文。伏せる欄が `password` などだけで、`email`・`first_name`・`last_name`・`user_id`・`refresh` はそのまま | 4xx・5xx の POST のたび（下の注） |
| P9 | `backend/core/enhanced_logging.py:180`（`_log_exception`）→ `:83-92`（`DetailedFormatter._get_error_context`） | `include_locals: True` を常に付け、その場の変数を全部 `str(v)[:200]` で書く（`request.user` を持つ変数などからメールアドレス、登録の処理ならパスワードも入りうる）。コメントは「デバッグモード時のみ」だが本番でも付く。**implement の Red で分かったこと**: 書く側の変数の探し方（`tb.tb_frame` から外側へたどり、行番号で突き合わせる）が合わず、今は本番でも開発でも変数は 1 つも書かれていない（実際の漏れは無い）。付ける側を `DEBUG` だけにして、探し方が直ったときに本番で書かれないようにしておく | 想定外のエラーのたび |

- P8 の注: Django のミドルウェアが受け取る `request`（`WSGIRequest`）には `.data` が無いので、今は `request.POST`（フォームで送った本文）だけが入り、JSON の本文は `{}` になる。今の画面は JSON で送るので実際に入るのはフォームの送信だけだが、伏せる欄は送り方に関係なく効かせる（設計確認メモの決定）
- 直さない（理由）: `backend/core/subject_service.py:125`（未ログインの分岐で `str(AnonymousUser)` = `AnonymousUser`。個人情報でない）・`backend/accounts/views.py:143・163・224`（組織名）・`backend/accounts/views.py:95`（`serializer.errors`。DRF の文言で入力の値を含まない）・`backend/core/storage_service.py:58`（上げたファイルの名前。利用者を指す値の欄ではない）・`backend/problems/management/commands/import_problems.py:351`（運用者が打つコマンドの画面表示）・`backend/core/monitoring.py:242-243` と `middleware.py:55-56` の `user_agent`・`ip_address`（不正アクセスを調べるのに要る。イシューの範囲〔メールアドレス・氏名〕の外）・例外の文言（`str(e)`。DB の重複エラーなどに値が入る可能性はあるが、どこで起きるか決まらず、一律には直せない。R3）・`ErrorContextMiddleware` の `query_params`（`dict(request.GET)`。今の backend に `email` などを GET で受ける API は無い〔2026-11-12 の grep〕）・同 `user_actions`（`X-User-Actions` ヘッダー。送る側の `frontend/src/utils/userActionLogger.ts` の `useActionLogger` は今どの画面からも使われておらず、ヘッダーは届かない。ただし送る側の伏せ字〔`sanitizeValue`・`sanitizeFormData`〕は `email` を伏せないので、使い始めると漏れうる。扱いは retro で決める）
- 使われていないコード: `backend/core/logging_decorators.py`（`log_api_call` など）はどこからも使われていない（2026-11-12 `grep -rn "log_api_call\|log_db_operation\|log_celery_task\|mask_sensitive_data" backend`: 定義の中だけ）。中の `mask_sensitive_data` も `email` を伏せないが、動かないので本イシューでは直さない（9 章）
- 記録を読む側: `frontend/src/pages/Monitoring.tsx` と `backend/core/views.py` の集計（`get_error_summary`・`get_activity_summary`）は `user_email` を使わない（集計は `user_id` と件数だけ。2026-11-12 `grep -rn user_email backend frontend/src`: 当たるのは `monitoring.py:173・382` だけ）

**根本原因（コード）**: 上の P1〜P9。どれも「利用者そのもの・送られた内容をそのまま書く」書き方。

### 環境前提
- app-1 のコンテナ（backend・db・frontend・redis）が動いている（2026-11-12 `docker compose ps`）。テストの DB は PostgreSQL（CI も同じ）。pytest-django はテストのとき `DEBUG=False` にする
- `gh` は Draft PR #482 の作成で確認済み
- テストは CI が正。手元では新しいテストと、守りにする既存のテストのファイルだけを流す

## 2. 受け入れ条件（Acceptance Criteria）
イシューの受け入れ条件を、調べた結果に合わせて番号を付けた。
- AC1: 監視の記録（P1・P2）にメールアドレスが入らず、`user_id` は入る（テストで確かめる）
- AC2: API の呼び出しのログ（P3）と新規登録のログ（P4・P5）にメールアドレスが入らず、利用者 ID で追える。新規登録のログにパスワードも入らない（テストで確かめる）
- AC3: エラーの送信内容の記録（P8）で、`email`・`first_name`・`last_name`・`user_id`・`refresh` が `[REDACTED]` になる。今まで伏せていた欄も `[REDACTED]` のまま。ほかの欄は残る（テストで確かめる）
- AC4: `settings.DEBUG` が偽のとき、想定外のエラーの記録にその場の変数を書く印（`include_locals`）が付かず、変数（`locals`）も入らない。真のときは印が付く（テストで確かめる。変数そのものが書かれないのは今の書く側の不具合で、直すのは本イシューの範囲外・計画変更記録）
- AC5: `backend/` のほかの logger の呼び出しを調べた結果（1 章の表と「直さない」）が計画書に記録され、個人情報を書いている所（P6・P7）も直っている
- AC6: 全テストが通る（CI）

## 3. 影響範囲
| 区分 | 対象 | 内容 |
|---|---|---|
| Backend | `backend/core/monitoring.py` | `ErrorTracker.log_error`・`UserActivityMonitor.log_user_activity` から `user_email` を外す |
| Backend | `backend/core/middleware.py` | `RequestLoggingMiddleware.process_request` の `User:` を利用者 ID に |
| Backend | `backend/accounts/views.py` | `UserRegistrationView.create` の 2 行（P4・P5）・`send_verification_email` の `print`（P6） |
| Backend | `backend/core/subject_service.py` | 43・91 行目の `{user}` を利用者 ID に |
| Backend | `backend/core/enhanced_logging.py` | `_safe_body` の伏せる欄を足す・`_log_exception` の `include_locals` を `settings.DEBUG` に |
| Backend | `backend/core/tests/test_I437_no_pii_in_logs.py`（新規） | 回帰テスト |
| Frontend | なし | `frontend/src/pages/Monitoring.tsx` は `user_email` を使わない |
| DB | なし | マイグレーションなし |
| Config/Infra | なし | ログの出力先・依存は変えない |
| 変更しない（参照だけ） | `backend/core/views.py`・`backend/core/logging_decorators.py` | 記録を読む側（`user_email` を使わない）・使われていないコード |

ログの形の変化: P1・P2 の JSON から `user_email` のキーが無くなる（`user_id` は今もある）。P3 の `User:` の値がメールアドレスから利用者 ID（UUID）になる。API の応答・画面は変わらない。

## 4. 変更点一覧

### 修正アプローチ
ログには利用者そのものではなく `user.id` だけを書く。送られた内容を書く所は、個人情報と秘密の欄を伏せ字にする（新規登録の行は内容そのものを書くのをやめる）。その場の変数を書くのは開発環境だけにする。

### 4-1. 監視の記録（`backend/core/monitoring.py`）
**修正方針**: `user_email` の行を消す。`user_id` は両方とも既にある。
```python
        error_data = {
            ...
            'user_id': str(user.id) if user else None,
        }
```
```python
        activity_data = {
            'timestamp': timezone.now().isoformat(),
            'user_id': str(user.id),  # UUIDを文字列に変換
            'activity_type': activity_type,
            'details': details or {}
        }
```

### 4-2. API の呼び出しのログ（`backend/core/middleware.py:219-221`）
```python
            user_info = 'anonymous'
            if hasattr(request, 'user') and request.user.is_authenticated:
                user_info = str(request.user.id)
```

### 4-3. 新規登録（`backend/accounts/views.py`）
**修正方針**: 送られた内容を丸ごと書くのをやめ、組織 ID だけを書く（P4）。成功のログと開発時の `print` はメールアドレスを利用者 ID にする（P5・P6）。開発時の `print` のトークンは、メールを送らない開発環境で認証を進めるのに使うので残す。
```python
            logger.info(f"Registration attempt for organization_id: {organization.id}")
```
```python
                logger.info(f"User created successfully: user_id={user.id} with organization_id: {user.organization_id}")
```
```python
            print(f"Email verification token for user_id={user.id}: {token}")
```

### 4-4. 科目の取得（`backend/core/subject_service.py:43・91`）
**修正方針**: `user` が `None` のこともあるので `getattr` で ID だけを取る。
```python
            logger.warning(f"User {getattr(user, 'id', None)} has no organization_id")
```

### 4-5. エラーの送信内容の記録（`backend/core/enhanced_logging.py:_safe_body`）
**修正方針**: 伏せる欄に個人情報の欄（`email`・`first_name`・`last_name`・`user_id`）と `refresh` を足す。今までと同じく欄の名前の完全一致で伏せる（`dict(request.POST)` の欄の名前は API の欄の名前そのまま）。一覧は既存の秘密と個人情報に分けてモジュールの定数にする。
```python
# エラーの送信内容の記録で伏せる欄（秘密）
SENSITIVE_BODY_FIELDS = (
    'password', 'password_confirm', 'token', 'secret',
    'api_key', 'current_password', 'new_password', 'refresh',
)
# エラーの送信内容の記録で伏せる欄（個人情報・I437）
PERSONAL_BODY_FIELDS = ('email', 'first_name', 'last_name', 'user_id')

    def _safe_body(self, request):
        ...
            for field in SENSITIVE_BODY_FIELDS + PERSONAL_BODY_FIELDS:
                if field in body:
                    body[field] = '[REDACTED]'
```

### 4-6. その場の変数の記録（`backend/core/enhanced_logging.py:_log_exception`）
**修正方針**: 付ける側（ミドルウェア）で `settings.DEBUG` を見る。書く側（`DetailedFormatter`）は今までどおり `include_locals` が真のときだけ書くので変えない。コメントも実態に合わせる。
```python
from django.conf import settings

            "include_locals": settings.DEBUG  # ローカル変数は開発環境（DEBUG）だけ記録する（個人情報を本番のログに残さない・I437）
```
- 本番では `stack_frames` の `file`・`line`・`function`・`code` と、`exception` の `traceback` は今までどおり残る

### 4-7. テスト（`backend/core/tests/test_I437_no_pii_in_logs.py`・新規）
- 下準備: 組織（slug `org-i437`・`type="school"`）・科目（slug `subj-i437`）・利用者（`user_id="u_i437"`・`email="u_i437@example.com"`・`first_name="太郎I437"`・`last_name="山田I437"`・組織あり・`role="user"`）。登録のテストは I140 と同じく `settings.RATELIMIT_ENABLE = False`
- ログの捕まえ方: `django.request` は `propagate=False` で pytest の `caplog` に届かないので、テストの中で対象の logger に記録を集めるハンドラーを付け、後で外す（`django`・root の logger も同じ方法で捕まえる。書き方をそろえる）。P6 の `print` は `capsys`
- TC の中身は `docs/tests/open/I437_auto_test.md`

## 5. 実装手順
- ステップ 1（未知リスク先行・縦の 1 本）: 4-7 のテストを先に書き、直す前のコードで流して落ちる（Red）ことを確かめる（`DEBUG=True` で印が付く TC-06 の 2 件目・伏せたままの欄の確かめは直す前から通る）。→ TC-01〜TC-08
- ステップ 2（ステップ 1 が前提）: 4-1〜4-6 を直し、TC-01〜TC-08 を通す（Green）。→ TC-01〜TC-08
- ステップ 3（ステップ 2 と並行可）: 守りの既存テスト（I140 の登録・#446 の横断）を流す。→ TC-09
- ステップ 4: /simplify の後に流し直す。→ TC-10
- 実装の後のサービスの再起動: 不要（コードだけの変更。dev の backend は自動で読み直す）

## 6. テスト計画
- 自動: `docs/tests/open/I437_auto_test.md`。テストレベル: 監視のクラス・ミドルウェアの関数はユニットテスト（`RequestFactory`・利用者は DB に作る）、新規登録と API の呼び出しのログは `APIClient` の結合テスト（PostgreSQL）。E2E は足さない（画面は変えない）
- 再発防止: TC-01〜TC-08 が、メールアドレス・氏名・パスワード・その場の変数がログに戻ると落ちる。どれも直す前のコードで落ちる（Red）ことを確かめる
- 手動: `docs/tests/open/I437_manual_test.md`（Claude が dev のコンテナでログのファイルを見る。Human の項目なし）
- 認可・テナント: 認可・閲覧範囲は変えない（ログの書き方だけ）。テナントの境界は #446 の横断テスト（TC-09）が守る

## 7. ロールバック
コードとテストだけの変更（DB の形は変えない）。PR を revert すれば戻る。すでに出力済みのログ（`backend/logs/`）は消さない（イシューの「含まない」）。

## 8. Risk & 回避策
- R1 ログからメールアドレスが無くなり、問い合わせの調べものがしにくくなる → `user_id`（UUID）が全部の記録に残るので、管理画面（`backend/accounts/admin.py`）で ID から利用者を引ける。新規登録のログには組織 ID が残る
- R2 本番でその場の変数が記録されなくなり、想定外のエラーの原因調べの手がかりが減る → ファイル・行・関数・コードの行と traceback は残る。変数が要るときは開発環境で再現する（設計確認メモの決定）
- R3 例外の文言（`str(e)`）に値が入るエラー（DB の重複エラーなど）は残る → 新規登録のメールアドレスの重複は serializer が先に確かめて 400 にするので、DB の重複エラーになるのは同時に登録したときだけ。どこで起きるか決まらず一律に直せないので、本イシューでは扱わない（9 章）
- R4 伏せる欄の名前を完全一致にしたので、別の名前の欄（例: `mail`）は伏せない → 今の API の欄の名前（`backend/accounts/serializers.py:46・213`）は `email`・`user_id`・`first_name`・`last_name` で、全部入る。部分一致にすると `subject_ids` など関係ない欄まで伏せて原因調べに使えなくなる

## 9. 確定事項と自律判断
**イシューに明記されていること**（設計確認メモ 2026-11-12）:
- 監視の記録（P1・P2）から `user_email` を外し、利用者 ID で追う
- P3・P5 のメールアドレスを利用者 ID に、P6 の `print` のメールアドレスを利用者 ID にする（トークンは残す）
- エラーの送信内容の記録で `email`・`first_name`・`last_name`・`user_id`・`refresh` を `[REDACTED]` にする。ほかの欄は残す
- その場の変数の記録は `settings.DEBUG` が真のときだけ
- `backend/` のほかの logger の呼び出しを全件確かめ、個人情報があれば直す
- 直さない: `import_problems.py:351` の画面表示・組織名のログ・過去のログ・外部の監視サービス・`/health/`

**Claude が技術的に決めたこと（理由）**:
- P4（新規登録の送信内容を丸ごと書く）は、伏せ字ではなく内容を書くのをやめて組織 ID だけにする — パスワードが平文で入る。伏せる欄の一覧に頼ると、欄が増えたときに漏れる。どの組織への登録かが分かれば調べものに足りる（失敗の理由は 95 行目の `serializer.errors` が残す）
- P7（`subject_service.py:43・91`）を直す — 全件確認で見つかった同じ型（`str(user)` がメールアドレス）。AC5「個人情報を書いている所があれば直す」に当たる
- `subject_service.py:125`・組織名・`storage_service.py:58`・`user_agent`・`ip_address`・例外の文言は直さない — 1 章の「直さない（理由）」
- `logging_decorators.py` は直さない — どこからも使われていない。消すかどうかは別の整理（本イシューの範囲外。retro で扱いを決める）
- 伏せる欄は欄の名前の完全一致（今までと同じ）で、秘密と個人情報の 2 つのモジュールの定数に分ける — R4。今までの一覧はメソッドの中の変数だったが、テストから同じ一覧を見られ、何を伏せるかが一目で分かる
- `include_locals` は付ける側（`_log_exception`）で `settings.DEBUG` にする（書く側の `DetailedFormatter` は変えない） — 付けるのはこの 1 か所だけ。書く側でも見ると判定が 2 か所に分かれる
- テストは 1 ファイル（`backend/core/tests/test_I437_no_pii_in_logs.py`）にまとめる — 直す所は `core` と `accounts` にまたがるが、守る決まり（ログに個人情報を書かない）は 1 つ。イシューの実装対象も `backend/core/tests/`
- ログは対象の logger にハンドラーを付けて捕まえる（`caplog` を使わない） — `django.request` は `propagate=False` で `caplog` に届かない。全 TC で同じ方法にする
- 決定論ゲート（ソースの grep で「logger の行に `.email` が無い」を確かめるもの）は置かない — 書き方（`str(user)`・`{user}`・送信内容の丸ごと・`extra=`）が多様で、文字の確かめでは今回見つけた P4・P7・P9 のような形を捕まえられず、見かけだけの守りになる。守る決まりは動きを確かめる pytest（TC-01〜TC-08）が CI で毎回止める
- 手動テストのアカウントは `e2e_user_c@example.com`（組織 A・一般ユーザー。`docs/runbooks/frontend-verify.md` の表）

**要件適合性・業務ロジック**: 受け入れ条件を超える仕様の追加・変更は無い（P4・P7 は AC5 の「全件確かめて直す」の中）。閲覧範囲・ステータス遷移: 変えない。境界: 利用者なし（`user=None`・未ログイン）の分岐で `user_id` が `None`・`anonymous` のまま落ちないこと、伏せる欄が本文に無いときに足されないことを TC で確かめる。

**セキュリティ・BP**: 機密データの扱いを直すイシュー（パスワード・リフレッシュトークン・個人情報をログに残さない）。入力の検証・認証・認可は変えない。SQL・XSS・CSRF に関わる変更なし。依存の追加なし。bandit は MEDIUM 以上を直す・LOW は `# nosec` で抑える（P6 の `print` は今もあり、新しい指摘は出ない見込み）。npm audit は high／critical を直す（依存を変えないので対象なし）。OWASP A09（ログの不備）・A02（機密データの露出）の対策に当たる。

**P3/P5/P8 影響なし**: DB の形・外部 API・非同期処理・インフラ・依存は変えない（ログの出力先・保持期間も変えない）。
**P6 影響なし**: 画面を変えない。ログの書き方だけで性能は変わらない。
**P9（プライバシー）**: 個人情報を扱う変更なので 15 章に書く。テナントを越えるデータ・目的外の利用は新しく生まれない（ログから個人情報を減らす変更）。

**台帳の残りの一覧**:
- 一覧 I224.md F9: 残す — ハーネスの項目で、このイシューの変更点と関係しない（`FILE=-`）
- 一覧 I223.md B1〜B4: 残す — bot の停止に関する項目で、このイシューの変更点と関係しない（`FILE=-`）
- 実装対象のファイルに当たる行は無し

## 15. プライバシー・コンプライアンス設計
- 目的: ログを障害の調べもの以外の目的に使わず、調べものに要らない個人情報（メールアドレス・氏名・ログイン ID）と秘密（パスワード・リフレッシュトークン）を書かない（データの最小化）。未成年の利用者を含む前提
- 利用者の特定: ログには `user_id`（UUID）だけを書き、利用者を引くのは管理画面（権限のある運用者）に限る
- 保持期間: 今のまま（`TimedRotatingFileHandler` の 30 日）。すでに出力済みのログの削除はイシューの範囲外（過去分は 30 日で回って消える）
- テナント分離・データ所有権・同意・開示や削除の請求の導線: 変えない（ログの中身を減らすだけ）

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 実験必須 | 監視の記録・API のログ・新規登録のログ・科目の取得のログにメールアドレス・パスワードが入らず、`user_id` が入る（TC-01〜TC-05。直す前のコードで Red を実測） |
| V2 | 2 | 実験必須 | エラーの送信内容の記録で 5 つの欄が `[REDACTED]`・今までの欄も伏せたまま・ほかの欄は残る（TC-07） |
| V3 | 3 | 実験必須 | `DEBUG=False` で `include_locals` が付かず変数も記録されず、`DEBUG=True` では印が付く（TC-06） |
| V4 | 1 | 読んで可 | 1 章の全件確認の表に漏れが無い（`backend/` の logger・print の呼び出しのうち、利用者・送信内容を書くもの） |

## 計画変更記録
- plan-review（20261112_2340・OK・Warning 2 件）: 1 章「直さない（理由）」に `query_params`・`user_actions` を理由付きで足した（`user_actions` の送る側が `email` を伏せない件は retro で扱いを決める）。「必ず確かめる項目」の V4 の観点を 4 → 1 にした（有効な観点は 1〜3）。計画レビューのやり直し: 不要（方式・範囲・受け入れ条件を変えない）
- implement（Red・2026-11-12）:
  - 計画書の記載: AC4「`DEBUG` が真のときは今までどおり（その場の変数が）入る」・TC-06 の 2 件目「`DEBUG=True` で `locals` にメールアドレスがある」
  - 分かったこと: 直す前のコードで TC-06 の 2 件目が落ち、1 件目が通った。`DetailedFormatter._get_error_context`（`enhanced_logging.py:83-92`）は `tb.tb_frame`（いちばん外の枠）から `f_back` で外側へたどり、記録の時点の行番号で突き合わせるので、例外が起きた枠に届かず、どの環境でも変数を書かない
  - 選んだ案と理由: 付ける側を `settings.DEBUG` にする方針（4-6）は変えない（探し方が直ったときに本番で書かれないため・設計確認メモの決定）。AC4・TC-06・V3 を「`DEBUG` が偽なら印（`include_locals`）が付かず変数も入らない／真なら印が付く」に直す。書く側の探し方は直さない（開発だけで使う機能の不具合で、直すと開発のログにメールアドレス・パスワードが書かれるようになる。直すかは retro で扱いを決める）
  - 計画レビューのやり直し: 要（受け入れ条件 AC4 の文言を変えた）

## レビュー結果
- [20261112_2340 判定: ✅ 完了](../../reviews/I437_plan_review_20261112_2340.md)
