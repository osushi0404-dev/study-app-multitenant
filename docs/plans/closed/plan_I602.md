# I602 計画書: I590 のレビューの残り（テストの守りの抜け・0027 の戻し方・マイグレーションのテストの補助の集約）

## 基本情報
- **計画書ID**: plan_I602
- **関連イシュー**: #602
- **Draft PR**: #603
- **作成根拠資料**: docs/issues/open/I602.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I602_review.md
- **作成日**: 2026-11-20

## 1. 背景/目的
- I590 のレビューで止めなかった小さな指摘（テストの守りの抜け 2 つ・0027 が止まったときの案内の不足・テストの補助の写し）を片付ける。本体のコードは変えない

### 調査結果
**原因の概要**: テストが、守る対象の一部だけを手で選んで比べていた。また、マイグレーションのテストを作るたびに前のテストの補助を写してきたので、同じ処理が 3 か所に並んだ。0027 が止まったときの戻り方は、どこにも書かれていない。

**詳細**:
1. `backend/problems/tests/test_I590_review_leftovers.py:110-113`（TC-03）は `X-Content-Type-Options`・`Content-Security-Policy` だけを比べる。`backend/problems/views.py:646-650` の `MEDIA_SECURITY_HEADERS` には `Content-Disposition: inline` もあり、304・412 で抜けても通る
2. 同じファイルの `app_imports`（:60-68）は `ast.ImportFrom` の `module` だけを見る。`from .utils import x` は `module='utils'`（`problems.` で始まらない）、`from . import utils` は `module=None` で、どちらも数えない。今の `backend/problems/media_migration.py` の読み込み（:10-16）は絶対の読み込みだけなので、今は漏れていない
3. 0027（`backend/problems/migrations/0027_remove_subject_image_directory.py`）は値のある科目があると `RuntimeError`（「値の使い道を確かめて空にしてから、もう一度 migrate してください」）で止まる。止まったとき、モデルにはもう `image_directory` が無いので ORM では値を見られず、生の SQL が要る。その手順が手順書（`docs/runbooks/backend-check.md`・`danger-ops.md`）に無い。0010（`0010_consolidate_image_directory_fields.py:11-20`）が古い列の値を写したので、古い控えから戻した DB では止まりうる
4. 補助の写し（grep `SET CONSTRAINTS ALL IMMEDIATE|MIGRATION_MODULES|MigrationLoader` で backend 全体を探して、この 3 ファイルだけ）:
   - `backend/problems/tests/test_I590_review_leftovers.py:117-133`（`_loader`・`_run`・`_subject_columns`）
   - `backend/problems/tests/test_I587_media_migration.py:79-99`（`_loader`・`_run`・`_tables`・`_columns`）
   - `backend/studylogs/tests/test_I492_remove_legacy_study_logs.py:157-183`（`_tables`・`_columns`・`_run`。読み込みはテストの中に直書き :188-189）
   - 共有の前例: `backend/problems/tests/i466_data.py` を `studylogs` のテストが読む（`test_I492_remove_legacy_study_logs.py:26`）。`pytest.ini` の `python_files = test_*.py` なので、`test_` で始まらないファイルはテストとして集められない

## 2. 受け入れ条件
- [ ] 画像の配信の 200・304・412 のどれかで `MEDIA_SECURITY_HEADERS` の見出しが 1 つでも抜ける・値が違うと、テストが落ちる（見出しを足したときも、テストを直さずに新しい見出しまで比べる）
- [ ] 移行の判定（`problems/media_migration.py`）が相対の読み込み（`from .utils import x`・`from . import utils`）でアプリのモジュールを読むと、テストが落ちる
- [ ] マイグレーションを本物で流すテストの補助（読み込み・遅延の制約を即時にして流す・表と列の一覧）が 1 か所にあり、I492・I587・I590 のテストはそこから読む。3 つのテストに補助の写しが戻ると決定論のゲートが落ちる。3 つのテストは変わらず通る
- [ ] 0027 が止まったとき、人が手順書だけを見て「控えを取る → 値を確かめる → 空にする → migrate し直す」まで進める。空にする SQL は 0027 のテストが同じ文で通ることを確かめている

## 3. 影響範囲
- Backend: テストだけ（`backend/problems/tests/` の 2 ファイルと新しい補助、`backend/studylogs/tests/` の 1 ファイル）。本体のコード・マイグレーションは変えない
- Frontend: なし
- DB: なし（スキーマもデータも変えない）
- Config/Infra: なし。手順書 `docs/runbooks/backend-check.md` に節を 1 つ足す

## 4. 変更点一覧（具体）

### 修正アプローチ
- 守る対象を手で選ばず、辞書の全項目・読み込みの全形で回す。回し方が効くことを、失敗の注入（1 つ抜いた応答・相対の読み込みの文字列）で確かめる
- 補助は `test_` で始まらない 1 つのモジュールにまとめ、3 つのテストはそこから読む（前例 `i466_data.py` と同じ置き方）
- 0027 の文言は変えず（規約 §4「マージしたマイグレーションは書き換えない」）、戻り方を手順書に書く。手順書の空にする SQL は、0027 のテスト（TC-04）が同じ文を流して確かめる

### (1) 配信の見出しを全項目で比べる（I590 の TC-03）
何を達成するか: 304・412 で `Content-Disposition` などが抜けたら落ちる。見出しを足したら自動で比べる対象に入る。
- `backend/problems/tests/test_I590_review_leftovers.py`:
  - `from problems.views import MEDIA_SECURITY_HEADERS` を足す
  - 関数 `missing_security_headers(response) -> list[str]`: `MEDIA_SECURITY_HEADERS` の各項目について、応答に無いか値が違う見出しの名前を返す
  - `test_media_security_headers_on_all_statuses`: 個別の 2 行（`X-Content-Type-Options`・`Content-Security-Policy`）を `assert missing_security_headers(response) == []` に置き換える。`Cache-Control` の行は残す（辞書の外の値のため）
  - 新しいテスト `test_missing_security_headers_detects_each_header`（失敗の注入）: `MEDIA_SECURITY_HEADERS` の各見出しで parametrize し、全部を付けた `HttpResponse` からその 1 つを消すと `[その見出し]` が返る・値を変えても `[その見出し]` が返る・全部そろえば `[]`

### (2) 移行の判定の相対の読み込みも数える（I590 の TC-01）
何を達成するか: `from .x import y`・`from . import x` も「アプリのモジュールを読んだ」と数える。
- `app_imports(source)`:
  - `ast.ImportFrom` で `node.level > 0`（相対）のとき: `module` があれば `"." * level + module`、無ければ読み込んだ名前ごとに `"." * level + alias.name` を足す（`media_migration.py` は `problems` の中にあるので、相対はどれもアプリのモジュール）
  - 絶対の読み込みは今のまま（`problems` か `problems.` で始まるもの）
- `test_media_migration_imports_no_app_module` に失敗の注入を 2 つ足す: `app_imports("from .utils import x\n") == [".utils"]`・`app_imports("from . import utils\n") == [".utils"]`。今の絶対の例も残す

### (3) マイグレーションのテストの補助を 1 か所にまとめる
何を達成するか: 遅延の制約を即時にする回り道などを変えるとき、直すのが 1 か所で済む。
- 新しいファイル `backend/problems/tests/migration_helpers.py`（`test_` で始めないのでテストとして集められない）:
  - `load_migrations(settings) -> MigrationLoader`: `settings.MIGRATION_MODULES = {}`（pytest の `--no-migrations` を外す）にして `MigrationLoader(connection)` を返す
  - `run_migration(step, state)`: `SET CONSTRAINTS ALL IMMEDIATE` を流してから `connection.schema_editor()` の中で `step(state.clone(), editor)`（今の `_run` と同じ）
  - `table_names() -> set[str]`・`column_names(table) -> set[str]`（今の `_tables`・`_columns` と同じ）
  - 冒頭の説明に、使っているテスト（I492・I587・I590）と回り道の理由を書く
- `backend/problems/tests/test_I590_review_leftovers.py`: `_loader`・`_run`・`_subject_columns` を消し、補助を読む（`_subject_columns()` は `column_names("problems_subject")`）。`_without_check` はこのテストだけのものなので残す
- `backend/problems/tests/test_I587_media_migration.py`: `_loader`・`_run`・`_tables`・`_columns` を消し、補助を読む。`_attstorage` はこのテストだけのものなので残す
- `backend/studylogs/tests/test_I492_remove_legacy_study_logs.py`: `_tables`・`_columns`・`_run` と、テストの中の直書きの読み込み（`settings.MIGRATION_MODULES = {}`・`MigrationLoader(connection)`）を補助に置き換える。`_operations` はこのテストだけのものなので残す。使わなくなる `MigrationLoader`・`connection` の読み込みは消す（ruff の F401 に合わせる）
- 呼び出しの名前の置き換え以外のテストの中身（手順・比べる値）は変えない

### (4) 0027 が止まったときの戻り方を手順書に書く
何を達成するか: `I590: image_directory に値のある科目が N 件あります` で止まったとき、手順書だけで戻れる。
- `docs/runbooks/backend-check.md` に「## 4. 止める判定のあるマイグレーションが止まったとき」を足す（今の「## 4. 報告に書くこと」は「## 5.」にずらす。この番号を参照している文書が無いことは grep で確かめた: `backend-check.md` の節の番号を指す参照は無い）
  - 共通の進め方: マイグレーションは書き換えない（規約 §4）／値を空にするのは DB の書き換えなので、先に控えを取る（`danger-ops.md`「破壊的な DB の操作の前の控え」・人の承認）／値の使い道を確かめてから空にする／空にしたら `migrate` し直す
  - 0027 の具体の手順（止まった時点でモデルに `image_directory` が無いので、ORM ではなく生の SQL で見る）:
    1. 控え: `bash scripts/claude/db-backup.sh <イシュー番号>_before`
    2. 値の確かめ: `docker compose exec -T backend python manage.py dbshell -- -c "SELECT id, name, image_directory FROM problems_subject WHERE image_directory <> ''"`（backend のイメージに `postgresql-client` が入っている・`backend/Dockerfile:11`）
    3. 使い道: 画像は I587 から DB に保存しており、`image_directory` はどこからも読まれない（0010 が古い列から写した値の残り）。値を残したい事情があれば、空にする前に控えとは別に書き留める
    4. 空にする（人の承認の後）: 同じ `dbshell -- -c` の形で `UPDATE problems_subject SET image_directory = '' WHERE image_directory <> ''`
    5. `docker compose exec -T backend python manage.py migrate problems`
  - 0026（問題の古い画像の列）も同じ形で止まる。0026 の判定（`0026_remove_problem_legacy_images.py:14-18`）は NULL でも空文字でもない値を数えるので、空にする対象は `problems_problem` の `question_image`・`explanation_image`（NULL にする）と 1 行だけ書く
- `backend/problems/tests/test_I590_review_leftovers.py` の TC-04（`test_0027_refuses_values_then_removes_column`）: 値を空にする手順を、ORM の `OldSubject.objects.update(image_directory="")` から手順書と同じ SQL 文（定数 `CLEAR_IMAGE_DIRECTORY_SQL`）を `connection.cursor()` で流す形に変える。説明に手順書の節を書く（手順書の SQL を変えたらこの定数もそろえる、と書く）。`finally` の後始末は今の ORM のまま

## 5. 実装手順（ステップ）
1. 補助のモジュールを作り、3 つのテストをそこから読む形に変える（4-(3)）→ TC-03・TC-04
2. I590 の TC-03 を全項目で比べ、失敗の注入のテストを足す（4-(1)）→ TC-01・TC-04。ステップ 1 と並行してよい（同じファイルの別の場所）
3. I590 の TC-01 で相対の読み込みも数える（4-(2)）→ TC-02・TC-04。ステップ 1 と並行してよい
4. 手順書に戻り方を書き、0027 のテストの空にする手順を同じ SQL に変える（4-(4)）→ TC-05・TC-04。ステップ 1 の後（同じテストの補助の呼び出しを変えるため）

## 6. テスト計画
### 自動
- pytest（CI が流す。手元では関係する 3 ファイルだけを流してよい）: TC-01・TC-02・TC-04・TC-05（`docs/tests/open/I602_auto_test.md`）
- 決定論のゲート: TC-03（3 つのテストに補助の写しが無い。今の写しで 9 行とも exit 1 になることを確かめた＝失敗の注入済み）
- テストの段階: 全部ユニット／結合（DB を使う pytest）。画面が無いので E2E は無い。認可の変更が無いので認可のテストは足さない
- 差し替え: 失敗の注入は、本物の応答を作り替えた `HttpResponse` と文字列で行い、monkeypatch は使わない
### 手動
- `docs/tests/open/I602_manual_test.md`（Claude が CI のログで 3 ファイルの通過を確かめる・手順書の SQL とテストの定数が同じ文であることを読む）

## 7. ロールバック
- テストと手順書だけの変更なので、PR を revert すれば戻る。DB・本体には触らない

## 8. Risk & 回避策
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: 補助へ移すときに手順が変わり、マイグレーションのテストが別のことを確かめるようになる | 補助は今の `_run`・`_tables`・`_columns` と同じ中身にし、テストの中身は名前の置き換えだけにする（4-(3)）。3 つのテストが CI で通ることを TC-04 で確かめる | 回避 |
| R2: 全項目で比べる形が、辞書から項目を消したときは落ちない（辞書と応答が一緒に変わる） | 見出しを辞書から消すのは意図的な変更でしか起きず、PR のレビューで見る（`plan-writing-rules.md`「決定論テストの対象の選び方」）。抜けの検出は失敗の注入（TC-01）で確かめる | 受け入れ |
| R3: 手順書の SQL とテストの SQL がずれる | テストの定数の説明に手順書の節を書き、両方をそろえる決まりをそこに書く。文言の一致の決定論のテストは作らない（意図的な変更でしか変わらない） | 受け入れ |
| R4: 補助を `problems/tests/` に置くと `studylogs` のテストが `problems` のテストに頼る | 前例（`i466_data.py`）と同じ形で、補助は `test_` で始めないモジュールにする。テストのファイルどうしは結びつけない | 受け入れ |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- /grill-me（2026-11-20）でユーザーに聞く点は無かった。設計確認メモは無し
- イシュー本文: 0025〜0027 を書き換えない・本番の DB は触らない・補助はテストのファイルではなく補助だけのモジュールにする
Claude が決めた（技術的な選択と理由）:
- 補助の置き場は `backend/problems/tests/migration_helpers.py` — 前例の `i466_data.py` と同じ置き方で、新しいパッケージを作らない。`core`・`common` は本体のコードの置き場（規約 §2）なのでテストの補助を置かない
- 補助の名前は `load_migrations`・`run_migration`・`table_names`・`column_names` — 別のモジュールから読むので、先頭の `_` を外し、何をするかが分かる名前にする
- 0027 の戻り方の置き場は `docs/runbooks/backend-check.md` の新しい節 — マイグレーションの診断（§3）と同じ手順書で、止まった人が最初に開く場所。テストの説明だけに書くと、テストを読まない人には届かない
- 空にする SQL を TC-04 で同じ文で流す — 手順書の SQL が正しいことを CI で確かめる（新しいテストは足さない）
- 見出しの比べは辞書から回す（イシューの解決方針どおり）。失敗の注入は応答を作り替えて行う
- 相対の読み込みは、`media_migration.py` が `problems` の中にあるのでどれもアプリのモジュールと数える
- 決定論のゲート（TC-03）は名前ではなく中身の目印（`MIGRATION_MODULES`・`SET CONSTRAINTS ALL IMMEDIATE`・`get_table_description`）で写しを探す — I492 のように関数にせず直書きした写しも捕まえる
- 台帳の残りの一覧: 実装対象のファイルに当たる行は無い。`FILE=-` の行は次のとおり、どれもハーネスの別件で、このイシューの範囲外なので残す
  - 一覧 docs/reviews/backlog/I224.md F9: 残す — 別イシュー（I224）の実測の話
  - 一覧 docs/reviews/backlog/I223.md B1〜B4: 残す — bot の停止に関わる片付けで、このイシューと関係が無い
- 要件適合性: 受け入れ条件の範囲を超える仕様の追加・変更は無い。0026 の 1 行は 0027 と同じ形で止まる別のマイグレーションへの案内で、手順書の節の中の補足に留める。マルチテナント・状態の遷移・権限は変えない
- セキュリティ影響なし: 本体のコードを変えない。テストは守りの見出しの抜けを捕まえる方向に強くなる（C8）。手順書の SQL は固定の文で、外からの値を埋め込まない。依存は変えない（pip-audit・npm audit の対象の変化なし）。bandit・ruff は今の基準（bandit: MEDIUM 以上を直す）のまま
- P3/P5/P8 影響なし: DB・外部 API・非同期処理・インフラ・依存のファイルを変えない
- P6 影響なし: 画面・性能に関わる変更は無い
- P9 影響なし: 個人情報・テナントのデータを扱う変更は無い
- 設計品質: テストの補助の重複を 1 か所にまとめる（写しの踏襲をやめる）。定数（SQL の文・見出しの辞書）は 1 か所で持つ
Danger Ops（有無）:
- 無（この PR では DB を操作しない。手順書には、人が 0027 で止まったときの控えと承認の手順を書く）

## 計画変更記録
- 2026-11-20 plan-review: 計画書の記載: [値の確かめ: `manage.py shell -c "...connection.cursor()..."`] → 採った方法: `manage.py dbshell -- -c "<SQL>"`。0026 の補足に判定の行を添えた — 理由: 計画レビューの Info 2 件（引用符の入れ子で貼り付けを誤りやすい・0026 の判定と合わせる）。方式・範囲・受け入れ条件は変えない。計画レビューのやり直し: 不要（findings への対応の追記だけ）

## レビュー結果
- [20261120_1817 判定: ✅ 完了](../../reviews/closed/I602_plan_review_20261120_1817.md)
