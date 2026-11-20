# バックエンドを変えたときの確かめ方

バックエンド（モデル・ビュー・シリアライザー・サービス）を変えたときに、何をどう確かめるか。

- 書き方の決まり（組織の境界・権限・入力の検証・必ず書くテスト）は `rules/ultimate_django_coding_standards.md` が正。ここは確かめる手順だけを書く
- 確かめは、残る形（自動テスト）で行う。手で API を叩いて目で見る確かめはしない（Claude は curl を使えず、残らないため）
- マイグレーション・OpenAPI のコマンドは `docs/runbooks/common-commands.md` が正

## 1. 自動テストで確かめる（必須）

1. 変えた振る舞いの API テストを、アプリの `tests/test_I<番号>_<内容>.py` に書く。中身は規約 §13 の「必ず書くテスト」（組織の境界は §5）
2. 手元では、変えたところに関係するテストのファイルだけを流す（全部は CI が流す）
   - `docker compose exec -T backend python -m pytest <テストのファイル>`
3. 画面が受け取る形を変えたときは、`docs/runbooks/common-commands.md` の「API の形を変えたとき（型の作り直し・I493）」の手順で OpenAPI と画面の型を作り直す

## 2. マイグレーション

- モデルを変えたら、`docs/runbooks/common-commands.md` の「モデル変更時の必須手順（migration drift 防止）」でマイグレーションを作り、コミットに含める。作り忘れは CI の `makemigrations --check` が止める
- 外部キーを足すときの `dependencies` の決まりは規約 §4

## 3. モデルと DB が食い違ったときの診断

次のエラーが出たら、モデルの定義と DB の表が食い違っている。

- `Cannot resolve keyword '<名前>' into field`
- `AttributeError: '<Model>' object has no attribute '<名前>'`
- `django.db.utils.ProgrammingError: column ... does not exist`
- `django.core.exceptions.FieldError`

診断の順番（`docker compose exec -T backend python manage.py <コマンド>` で流す）:
1. 流していないマイグレーションがあるか: `showmigrations <アプリ>`（`[ ]` が流していないもの）。あれば `migrate` で流す
2. モデルにあってマイグレーションに無い変更があるか: `makemigrations --check --dry-run`。あればマイグレーションを作る
3. 設定とモデルの誤り: `check`
4. それでも直らなければ、ログを見る: `docker compose logs --tail=100 backend`

直したら、その食い違いを再現するテスト（または `makemigrations --check` が通ること）で確かめ、計画書の調査結果に原因を書く。

## 4. 止める判定のあるマイグレーションが止まったとき（I602）

値の残った列を消すマイグレーションには、値があれば黙って消さずに `RuntimeError` で止まるものがある（0026・0027）。止まったときの進め方:

- マイグレーションは書き換えない（規約 §4）。DB の値を直してから `migrate` し直す
- 値を空にするのは DB の書き換えなので、先に控えを取り、人の承認を得る（`docs/runbooks/danger-ops.md`「破壊的な DB の操作の前の控え（I597）」）
- 空にする前に、値の使い道を確かめる

### 0027（`I590: image_directory に値のある科目が N 件あります`）

止まった時点で、モデルにはもう `image_directory` が無い。ORM では値を見られないので、生の SQL で見る（backend のイメージには `postgresql-client` が入っている）。

1. 控えを取る: `bash scripts/claude/db-backup.sh <イシュー番号>_before`（単体で流す）
2. 値を確かめる: `docker compose exec -T backend python manage.py dbshell -- -c "SELECT id, name, image_directory FROM problems_subject WHERE image_directory <> ''"`
3. 使い道を確かめる: 画像は I587 から DB に保存していて、`image_directory` はどこからも読まれない（0010 が古い列から写した値の残り）。値を残したい事情があれば、空にする前に控えとは別に書き留める
4. 空にする（人の承認の後）: `docker compose exec -T backend python manage.py dbshell -- -c "UPDATE problems_subject SET image_directory = '' WHERE image_directory <> ''"`（この SQL は 0027 のテスト `backend/problems/tests/test_I590_review_leftovers.py` の `CLEAR_IMAGE_DIRECTORY_SQL` と同じ文。変えるときは両方をそろえる）
5. 流し直す: `docker compose exec -T backend python manage.py migrate problems`

0026（`I587: 古い画像の列に値のある問題が N 件あります`）も同じ進め方で止まる。0026 は NULL でも空文字でもない値を数えるので、空にする対象は `problems_problem` の `question_image`・`explanation_image`（NULL にする。画像を `MediaAsset` に移すのが先なら、移してから）。

## 5. 報告に書くこと

§1〜§3 で行ったこと（足した・直したテストのファイル、組織の境界のテストの有無、型の作り直しの有無、マイグレーションの有無）。
