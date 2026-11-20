# I590 計画書: I587 のレビューの残り（移行 0025 の依存・配信の 412 の見出し・`Subject.image_directory` の削除）

## 基本情報
- **計画書ID**: plan_I590
- **関連イシュー**: #590
- **Draft PR**: #596
- **作成根拠資料**: docs/issues/open/I590.md（起点イシュー）・#590 のコメント（2026-11-20・I587 の追加の直しからの更新）
- **実装後評価**: docs/reviews/open/I590_review.md
- **作成日**: 2026-11-20

## 1. 背景/目的
- I587 で画像の中身を DB に移した。そのレビューの台帳に残った軽い指摘を片付ける
- イシューの本文が挙げた F4・F5・F6・F7 は、イシューを書いた後の I587 の追加の直し（PR #588 のコミット 08919b28）で直っていた。#590 のコメントで、残りは F3・`Subject.image_directory`・新しく出た F9 の 3 つになった

### 調査結果
**原因の概要**: 画像の移行の処理が、後で変わりうるアプリの共通の部品を読んでいる（F3）。画像を返す API が、まれな「条件付きの読み取り」の失敗の応答にだけ守りの見出しを付けていない（F9）。科目の表に、もう読む所の無い列が残っている。

**詳細**:
1. **F4〜F7 は済み**（受け入れ条件 1〜3・5 は満たされている）:
   - F4: `backend/problems/views.py:607` の `upload_image` と `:632` の `delete_image` は `ProblemService.add_image`・`remove_image`（`backend/problems/services/problem_service.py:184`・`:216`。どちらも `@transaction.atomic`）を呼ぶだけ。ビューに `transaction.atomic` の呼び出しも `_save_image_as_asset`・`_discard_asset` の呼び出しも無い（`views.py:6` の `from django.db import transaction` は、クイズの回答の記録〔`views.py:832`〕が使うので残す）
   - F5: 入力は `ImageUploadSerializer`（`serializers.py:108`）、紐づけが無いときは `NotFound`（`problem_service.py:236`）。どちらも `custom_exception_handler` の形になる
   - F6: `test_I587_media_migration.py:142` は行単位の完全一致（`deleted_lines == [...]`）
   - F7: `remove_image` は `is_deleted=False` と組織で絞る（`problem_service.py:224-234`）
   - これらのテストは I587 で足した `test_I587_media_in_db.py` にある（I587 の TC-09・TC-10）。このイシューでは足さない
2. **F3**: `backend/problems/migrations/0025_move_media_files_to_db.py:11` が `problems.media_migration` を読み、`backend/problems/media_migration.py:15` が `problems.utils` の `ALLOWED_IMAGE_FORMATS`・`detect_mime` を読む。後で作成・更新で許す形式（`utils.py:14`）や判定を変えると、新しい環境で `migrate` を最初から流したときの 0025 の「画像でなければ止める」判定が変わる。`media_migration` は 0025 と管理コマンド `check_media_migration` の両方から使われる（`media_migration.py:3`）
   - `0025` の中の `from core.cache_service import cache_service` は `try/except Exception` の中にあり、消えても警告のログで済む（`0025:33-37`）
3. **F9**: `views.py:671-688` の `MediaAssetContentView.get` は、Django の `get_conditional_response` が応答を返したとき（304 か 412）、守りの見出し（`MEDIA_SECURITY_HEADERS`: `X-Content-Type-Options: nosniff`・`Content-Security-Policy: default-src 'none'; sandbox`・`Content-Disposition: inline`）を付けない。`get_conditional_response` は `If-Match`・`If-Unmodified-Since` も見るので、`If-Match: "x"` 付きの GET は本文の空の 412 になる（Django 5.2 の `django/utils/cache.py`。組織の絞り込み〔`get_object`〕の後なので境界は越えない）
4. **`Subject.image_directory`**（`backend/problems/models.py:52-58`。`CharField(max_length=200, blank=True, default='')`）: 読む所は無い。`grep -rn image_directory`（backend・frontend/src・`backend/openapi.yaml`・`frontend/src/types`）で、当たるのはモデルの定義と過去のマイグレーション（0009〜0011）・`accounts/migrations/0021` の `dependencies` の名前だけ。シリアライザ・管理画面・API の契約にも出ない
   - 開発の DB（app-1）: 科目 11 件、値のある行 0 件（2026-11-20 に `Subject.objects.exclude(image_directory='')…count()` で数えた）。本番は無い
5. **台帳の残りの一覧**: 当たるのは `FILE=-` のハーネスの 5 行（I223・I224）だけ（9 に書く）

## 2. 受け入れ条件
- [ ] AC1: `upload_image`・`delete_image` がサービスの公開の関数を呼ぶだけで、ビューに `transaction.atomic`・サービスの非公開の関数の呼び出しが無い（I587 で達成済み。このイシューではコードを変えない）
- [ ] AC2: 2 つの action のエラーが `{"error": {"main_message", ...}}` の形で返る（I587 で達成済み・I587 のテストで固定）
- [ ] AC3: `delete_image` が論理削除済みの紐づけを対象にしない（I587 で達成済み・I587 のテストで固定）
- [ ] AC4: 作成・更新で許す画像の形式や判定の関数を後で変えても、0025 の判定（どの中身を「画像でない」として止めるか）が変わらない。その方法と理由が計画書にある（TC-01・TC-02）
- [ ] AC5: `test_I587_media_migration.py` の出力の確かめが行全体の比べになっている（I587 で達成済み）
- [ ] AC6: `Subject.image_directory` がモデルと DB から無くなる。値のある科目が 1 件でもある DB では、黙って消さずにマイグレーションが止まる。流す前に値の入った行の数を見せてユーザーの承認を得た記録がある（TC-04・M1〜M3）
- [ ] AC7（F9）: 画像の配信の API が返すどの応答（200・304・412）にも、`X-Content-Type-Options: nosniff` と `Content-Security-Policy: default-src 'none'; sandbox` が付く（TC-03）

## 3. 影響範囲
- Backend: `problems`（`media_migration.py`・`views.py`・`models.py`・新しいマイグレーション 0027・テスト）
- Frontend: なし
- DB: `problems_subject.image_directory` の列の削除（Danger Ops）
- Config/Infra: なし。依存（`requirements*.txt`）は変えない（`python-magic` は今も入っている）
- 変えないもの: `0025_move_media_files_to_db.py`（マージしたマイグレーションは書き換えない・規約 §4）・`check_media_migration.py`・API の形（`backend/openapi.yaml` は変わらない）

## 4. 変更点一覧（具体）

### 修正アプローチ
- 0025 は書き換えず、0025 が読む `media_migration` を「0025 のための凍った部品」にする。アプリの共通の部品（`problems.utils`）を読まず、許す形式と判定を自分の中に持つ。将来アプリ側を変えても 0025 の動きが変わらない
- 配信の API は、Django の条件付きの判定（304・412）をそのまま使い、守りの見出しを応答の種類によらず付ける
- `image_directory` は、値があれば止まるマイグレーションで外す（I587 の 0026 と同じ形）

### 4-1. `backend/problems/media_migration.py`（F3）
- 達成すること: 0025 の判定を、アプリの部品の変更から切り離す
- `from problems.utils import ALLOWED_IMAGE_FORMATS, detect_mime` を消し、次を自分の中に置く
  ```python
  import magic
  # 0025 の時点（I587）で許した形式。0025 が読むので、作成・更新の決まり（problems.utils）が変わってもここは変えない
  MIGRATION_ALLOWED_MIMES = frozenset({'image/png', 'image/jpeg', 'image/webp'})
  MIGRATION_SNIFF_BYTES = 2048

  def _detect_mime(data: bytes) -> str:
      return magic.from_buffer(data[:MIGRATION_SNIFF_BYTES], mime=True)
  ```
- `_checked_content` はこれを使う（判定の中身は今と同じ: 先頭 2048 バイトを `python-magic` で判定し、3 形式以外なら止める）
- 冒頭の説明に「0025 が読む。アプリのモジュール（`problems.*`）を読まない・中身の判定を変えない」を足す

### 4-2. `backend/problems/views.py`（F9）
- 達成すること: 304・412 にも守りの見出しを付ける
- `get` の `for header, value in MEDIA_SECURITY_HEADERS.items(): response[header] = value` を、`if response is None:` の中から外に出し、どの応答にも付ける。`Content-Disposition: inline` も一緒に付く（本文の無い応答では意味を持たないが害も無い）
- 6 行目の `from django.db import transaction` は消さない（`views.py:832` のクイズの回答の記録が使う）

### 4-3. `backend/problems/models.py`・`backend/problems/migrations/0027_remove_subject_image_directory.py`
- 達成すること: 読む所の無い列を外す。値がある DB では黙って消さない
- モデルから `image_directory` の定義（`models.py:51-58` のコメント 1 行と定義）を消す
- `makemigrations problems --name remove_subject_image_directory` で 0027 を作り、`RemoveField` の前に `RunPython` を足す。作った 0027 の `operations` が `RemoveField(subject.image_directory)` 1 つだけであること（ほかのモデルの差分が混ざっていないこと）を確かめる（`makemigrations --check` が CI で通る＝差分の取り残しも無い）
  ```python
  def refuse_if_image_directory_set(apps, schema_editor):
      Subject = apps.get_model('problems', 'Subject')
      count = Subject.objects.exclude(image_directory='').count()  # 列は NOT NULL
      if count:
          raise RuntimeError(
              f'I590: image_directory に値のある科目が {count} 件あります。'
              '値の使い道を確かめて空にしてから、もう一度 migrate してください')

  operations = [
      migrations.RunPython(refuse_if_image_directory_set, reverse_code=migrations.RunPython.noop),
      migrations.RemoveField(model_name='subject', name='image_directory'),
  ]
  ```
- 戻すと列は `default=''` で戻る（止める判定があるので、流れたときは全行が空だった＝戻しで値は失われない）

### 4-4. テスト `backend/problems/tests/test_I590_review_leftovers.py`（新規）
- TC-01〜TC-04（auto_test）

## 5. 実装手順（ステップ）
1. **Danger Ops の準備と承認**（コードを変える前。ステップ 3 の前提・ゲート）
   - 開発の DB の科目の数と、`image_directory` に値のある科目の数を読むだけで数え、レビュー文書に書く → 手動 M1
   - #597 で作る控えの入口（`scripts/claude/` のスクリプト）で開発の DB の控えを取り、大きさを記録する → 手動 M2。#597 のマージまでこのステップで待つ（`scripts/db_backup.sh` はサンドボックスの中で `.env` を読めず止まる）
   - **ここで止めてユーザーに承認を求める**（止める条件 2）。見せるもの: 値のある科目の数・消す列・控えの場所・戻し方（7）。承認の言葉と日付をレビュー文書に書く。承認が無ければステップ 3 に進まない（マイグレーションのファイルを書くとコンテナの起こし直しで流れるため・R1）
   - ステップ 2 はこの承認を待たずに進めてよい（DB を変えない）
2. **F3・F9 の縦の 1 本**（ステップ 1 と並行してよい）: 4-1・4-2
   - TC-01・TC-03 を先に書き、今のコードで落ちることを確かめてから直す → TC-01・TC-02・TC-03
3. **列の削除**（ステップ 1 の承認の後）: 4-3 → TC-04
4. **app-1 で移行を流す**（ステップ 3 の後）: `docker compose exec -T backend python manage.py migrate problems`（前進の `migrate` は見張りの判定の対象外・承認はステップ 1 で得る）。出力と列が無くなったことを記録する → 手動 M3

## 6. テスト計画
### 自動
- テストのレベル: どれも pytest（結合。DB と HTTP のクライアントを使う）。画面の変更が無いので E2E は足さない。CI（pytest）が PR ごとに流す
- TC-01: `media_migration` がアプリのモジュール（`problems.` で始まるもの）を読まない（AST で読み込みを数える）。失敗の注入: 同じ関数に `from problems.utils import detect_mime` を含む文字列を渡すと 1 件になることもテストで確かめる
- TC-02: 0025 の判定が `problems.utils` の変更に引きずられない。`monkeypatch.setitem` で `problems.utils.ALLOWED_IMAGE_FORMATS`（辞書。今の `media_migration` は同じ物を読んでいる）に `text/plain` を足しても、文字の中身は「画像ではありません」で止まる（今のコードでは止まらず通る＝落ちる）。あわせて `monkeypatch.setattr(problems.utils, 'detect_mime', lambda data: 'image/png')` の下でも文字の中身が止まる（判定の関数の差し替えにも引きずられない）
- TC-03: 配信の API の 200・304・412 の応答に `nosniff` と CSP が付く。412 は `If-Match: "x"`、304 は `If-None-Match: <ETag>`
- TC-04: 0027 は、値のある科目があれば `RuntimeError`（件数を含む）で止まり列が残る。空なら列を外す。戻すと列が `''` で戻る
- 既存: `test_I587_media_migration.py`（0025 の移行と食い違いで止まる）・`test_I587_media_in_db.py`（配信・2 つの action）がそのまま通ること（CI）
- 認可・組織の境界: 変えない（配信の組織の絞り込み〔`visible_media_assets`〕と 2 つの action の権限は I587 のテストが固定している）。TC-03 は自分の組織の画像で確かめる
### 手動
- M1〜M3（Danger Ops の数え・控え・移行の実行）。実施者は Claude（コマンドの出力で確かめる）

## 7. ロールバック
- マージ前: ブランチを捨てる。app-1 で 0027 を流した後なら `DANGER_OK=1 docker compose exec -T backend python manage.py migrate problems 0026`（列が `''` で戻る。ユーザーの承認の後）
- マージ後: 上の巻き戻しの後に PR を revert する。列の値は流した時点で全行が空（0027 の判定）なので、控えから戻すものは無い。控え（ステップ 1）は念のため残す
- F3・F9 はコードだけの変更で、revert で戻る

## 8. Risk & 回避策
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: 0027 を書いた後に backend のコンテナが起こし直され（review-gate の敵対的レビューなど）、承認の前に開発の DB に流れる | ステップ 1 で控えを取り、承認を得てから 0027 を書く。値があれば 0027 が止まる（TC-04） | 回避 |
| R2: 他のワークツリーの DB に `image_directory` の値があり、develop を取り込んだときに黙って消える | 0027 は値があれば止まる（TC-04）。止まったら値の使い道を確かめる | 回避 |
| R3: `media_migration` に判定を写したことで、作成・更新の判定と 0025 の判定が将来ずれる | ずれるのが目的（0025 は I587 の時点の決まりで固定）。0025 は既に流れた環境では再び流れない。冒頭の説明に理由を書く | 回避 |
| R4: 412 の応答の本文は空で、見出しが付いても付かなくても中身は漏れない。304 に `Content-Disposition` が付くのは RFC 9110 の「304 に送るべき見出し」の外 | 害の無い見出し（ブラウザは 304 で保存済みの応答の見出しを更新するだけ）。全部の応答に同じ見出しを付けるほうが漏れが起きにくい | 受け入れ |
| R5: 0025 の `core.cache_service` の読み込みが将来壊れる | `try/except` の中で警告のログだけになる（0025:33-37）。0025 は書き換えない | 受け入れ |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- `Subject.image_directory` は消す（2026-11-20 ユーザー回答）。流す直前に値の入った行の数を見せて承認を得る（Danger Ops）
- 2 つの action は消さない・画面は変えない・`IsOrgAdmin` の置き場（#557）と `Subject.slug` は範囲の外
Claude が決めた（技術的な選択と理由）:
- F4〜F7 は I587 で直っていたので、コードを変えずに受け入れ条件 1〜3・5 を「達成済み」として扱う。根拠は #590 のコメントと 1 の調査結果 1（ファイル:行）。grill-me の時点ではコメントを読んでおらず、本文だけで質問を作った（聞いた 1 点は今も有効）
- F3: 0025 を書き換えない（規約 §4「マージしたマイグレーションは書き換えない」）。代わりに 0025 が読む `media_migration` をアプリの部品から切り離す。比べた案: (a) 0025 の中に処理を写して `media_migration` と管理コマンドを消す — 規約 §4 に反し、管理コマンドの試しも失う (b) 今のままにして、許す形式を変えるときに写す — 変える人が 0025 との関係に気づかない。(c) を選び、TC-01 で読み込みを固定する（普通の書き方〔共通の部品を使い回す〕で気づかずに壊しうるため、テストにする価値がある）
- F9: 412 を残し（Django の標準の判定を使う・RFC 9110 どおり）、見出しをどの応答にも付ける。比べた案: 304 以外の判定の結果を捨てて 200 を返す — 標準の判定を部分的に上書きすることになり、`If-Match` の意味を変える
- 0027 は値があれば止める（I587 の 0026 と同じ形・C7）。戻しは `RunPython.noop`＋列の再作成
- テストは新しいファイル `test_I590_review_leftovers.py` に置く（規約 §2 の命名）
- セキュリティ: 入力の検証・認可・組織の境界は変えない。F9 で守りの見出しを増やすだけ（OWASP: 応答の見出し）。秘密・個人情報は扱わない。依存は増やさない。bandit は MEDIUM 以上を直し LOW は `# nosec` で抑える（今回の変更で増える見込みは無い）
- 要件適合性: 受け入れ条件の外の仕様の追加は無い。マルチテナント・状態の遷移は変えない
- P3（データ整合性）: 10 に書く。P5・P8（運用・コスト）: 影響なし（外部 API・非同期・新しいインフラなし）。P6（性能・UX）: 影響なし（画面なし・クエリは増えない）。P9（プライバシー）: 影響なし（個人情報を扱わない）
- 設計品質: Fat View を増やさない（ビューの変更は見出しの付け方だけ）。定数は `media_migration` の中に名前を付けて置く
- 一覧 I223 B1〜B4・I224 F9（`FILE=-`）: 残す — どれもハーネス（bot・測定）のことで、このイシューの範囲（`problems` のアプリ）と関係しない
Danger Ops（有無。有りのときは 影響範囲・代替案・ロールバック・実行コマンド を書く）:
- 有: `problems_subject.image_directory` の列の削除（0027）
- 影響範囲: 開発の DB（app-1 の `app-1-db-1`。科目 11 件・値のある行 0 件〔2026-11-20〕）。本番は無い。ほかのワークツリーは develop を取り込んで `migrate` したときに同じ判定で流れる（値があれば止まる）
- 代替案: 列を残して「使わない」と注記する — grill-me でユーザーが選ばなかった
- 承認: ステップ 1 で、件数・消す列・控え・戻し方を見せてユーザーに承認を求める（承認の言葉と日付をレビュー文書に残す）。マージ依頼のときに PR に `danger-approved` を付けてもらう
- 実行コマンド: `docker compose exec -T backend python manage.py migrate problems`（ステップ 4・前置きなし。前進の `migrate` は見張りの判定の対象外）
- ロールバック: 7

## 10. データ整合性設計
- 制約: 列を外すだけで、ほかの制約・索引（`Subject` の `Meta`）は変えない。`image_directory` を使う索引・制約は無い
- トランザクション: PostgreSQL ではマイグレーション 1 本が 1 つのトランザクション。0027 の判定で止まれば列は残る
- 冪等・やり直し: 止まった後に値を空にして流し直せる
- 後方互換: 読む所が無いので、流した後に古いコードが動いても列を読まない。ただし古いコードの `Subject.objects.create` は列に `''` を書こうとして失敗する → マージと同時に流れるので、古いコードと新しい DB が並ぶのは手元のワークツリーの切り替えだけ（develop に戻すときは `migrate problems 0026`）

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | 配信の API のどの応答（200・304・412・ほかに `get_conditional_response` が返しうる状態）にも `nosniff` と CSP が付く（TC-03） |
| V2 | 2 | 読んで可 | TC-01・TC-02 が、`media_migration` がアプリのモジュールを読む形に戻したときに本当に落ちる（失敗の注入の確かめ） |
| V3 | 3 | 読んで可 | 0027 が値のある科目を黙って消さない（列は NOT NULL なので空文字以外の値すべて。空白だけの値も止める。TC-04）。戻しで列が戻る |

## 計画変更記録
- 2026-11-20 implement: 計画書の記載: [`bash scripts/db_backup.sh` で控えを取る] → 採った方法: #597 の控えの入口で取る（#597 のマージまで待つ） — 理由: `db_backup.sh` がサンドボックスの中で `.env` を読めず止まり、空の控えを残した（I587 と同じ）。ユーザーの指示「切り出して先に直す方向で進めて」（2026-11-20）。計画レビューのやり直し: 不要（控えの取り方の手段だけで、方式・範囲・受け入れ条件は変えない）
- 2026-11-20 plan-review: 計画書の記載: [`views.py:6` の使われない `transaction` の読み込みを消す] → 採った方法: 消さない — 理由: 計画レビューの Blocker。`views.py:832` のクイズの回答の記録が使っており、消すと回答の API が `NameError` になる。あわせて Warning の TC-02 に判定の関数の差し替えの観点を足し、4-3 に 0027 の中身の確かめを足した。計画レビューのやり直し: 要（Blocker の対応）

## レビュー結果
- [20261120_1335 判定: ✅ 完了](../../reviews/I590_plan_review_20261120_1335.md)
- [20261120_1334 判定: 差し戻し（Blocker 1件）](../../reviews/I590_plan_review_20261120_1334.md)
- 2026-11-20 plan-review（2 回目）: 計画書の記載: [0027 の判定の `.exclude(image_directory__isnull=True)`] → 採った方法: 消す — 理由: 計画レビューの Warning。列は NOT NULL で不要、残すと NULL がありうると誤解させる。計画レビューのやり直し: 不要（findings への対応の追記だけ）

## セキュリティレビュー結果

**実施日**: 2026-11-20

### セキュリティ設計レビュー

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| Low | ファイル操作（ダウンロード）/ OWASP（セキュリティ設定ミス） | 配信の API（`GET /api/media/<uuid>/`）の 304・412 に `nosniff`・CSP が付かない（F9）。本文は空なので中身の解釈の事故は起きないが、見出しの付け方が応答の種類で分かれていると、将来 本文のある別の分岐を足したときに付け忘れる | 必須: 見出しを応答の種類によらず 1 か所で付ける（4-2）。TC-03 で 200・304・412 を固定する |
| Low | ファイル操作（移行） | 0025 の「画像でなければ止める」判定がアプリの判定（`problems.utils`）の変更に引きずられ、新しい環境で画像でない中身を DB に入れうる（F3） | 必須: `media_migration` は `problems.*` を読まない（TC-01）。判定は I587 の時点の 3 形式で固定（TC-02）。置き場の外を指すキー・checksum の食い違いで止める判定（`_resolve_inside`・`_checked_content`）は変えない |
| なし | 認証・認可 | 変えない。配信は `IsAuthenticated`、2 つの action は I587 のまま | — |
| なし | マルチテナント | 変えない。配信は `get_object()`（`visible_media_assets(request.user)`・利用者の組織の消されていない画像だけ）の後に条件付きの判定をする。他の組織の画像は 304・412 の判定の前に 404 | 禁止: 条件付きの判定（`get_conditional_response`）を `get_object()` より前に動かさない |
| なし | 入力検証 | 新しい入力は無い。`If-Match`・`If-None-Match` の解釈は Django の標準 | — |
| なし | 機密情報 | 0027 の止める文は件数だけ（科目名・値を出さない）。`media_migration` の止める文は I587 のまま（ID・キーだけ・中身を出さない） | 禁止: 0027 の文に `image_directory` の値・科目名を入れない |
| なし | 外部通信 | 無い | — |
| なし | 依存ライブラリ | 増やさない（`python-magic` は今も入っている） | — |

### 攻撃シナリオレビュー

| # | 入口 | 想定権限 | 想定操作 | 守るべき条件 | 自動テスト化対象 | 手動確認対象 | 残余リスク | 重大度 |
|---|------|---------|---------|------------|----------------|------------|---------|--------|
| 1 | `GET /api/media/<uuid>/` | 一般（他の組織） | 他の組織の画像の ID に `If-Match`・`If-None-Match` を付けて 304/412/200 の違いから画像の有無・checksum を探る | 他の組織の画像は条件付きの判定の前に 404 | Yes: I587 の TC-07（組織の境界は 404）がそのまま通る。TC-03 は自分の組織の画像だけで 412 を出す | No | なし | Low |
| 2 | `GET /api/media/<uuid>/` | 一般（同じ組織） | `If-Match: "x"` で 412 を出し、見出しの無い応答をブラウザに直接開かせる | 412 にも `nosniff`・CSP が付く（本文は空） | Yes: TC-03 | No | なし（本文が空で、もとから中身は出ない） | Low |
| 3 | `migrate`（新しい環境） | 運用者 | 画像でない中身のファイル（`.png` の名前の HTML など）を置き場に置いた状態で 0025 を流す。後でアプリが許す形式を広げても 0025 が通す | 0025 は I587 の 3 形式以外を止める | Yes: TC-02・I587 の TC-14 | No | `python-magic`（外部のライブラリ）の判定が版で変わることは防げない | Low |
| 4 | `migrate`（他のワークツリー・将来の環境） | 運用者 | `image_directory` に値のある DB で 0027 を流し、値が黙って消える | 値があれば止まる | Yes: TC-04 | Yes: M1〜M3（app-1 での件数・控え・実行） | なし | Low |

## レビュー結果サマリー

| 重大度 | 設計レビュー | シナリオ |
|--------|------------|---------|
| Blocker | 0件 | 0件 |
| High    | 0件 | 0件 |
| Medium  | 0件 | 0件 |
| Low     | 2件 | 4件 |

### 残余リスク処遇
（retro 段階で決定する）
