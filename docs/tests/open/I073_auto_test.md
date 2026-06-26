# I073 自動テスト計画（バックエンド結合テスト）

- **関連イシュー**: #150 / **計画書**: docs/plans/open/plan_I073.md
- **対象**: `backend/problems/tests/test_I073_image_update.py`（新規）
- **方式**: pytest（`@pytest.mark.django_db`）＋ DRF `APIClient`。既存 `problems/tests/` のパターンを踏襲。
- **実行**: `docker compose exec backend python -m pytest problems/tests/test_I073_image_update.py -v`
- **MEDIA_ROOT**: 各テストで `settings.MEDIA_ROOT = str(tmp_path)`。科目ディレクトリ（`org/<slug>/subjects/<slug>/{problem,explanation}`）をフィクスチャで作成（`check_directory_exists` を満たすため）。
- **画像生成ヘルパ**: PIL で実画像バイト列を生成し `SimpleUploadedFile(name, content, content_type)` で渡す（`validate_image_file` の MIME/マジックナンバー/ピクセル検証を通すため、ダミーバイトではなく実 PNG を生成する）。

```python
# 画像生成ヘルパ（テスト内）
import io
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile

def make_png(name="img.png", size=(10, 10)):
    buf = io.BytesIO()
    Image.new("RGB", size, (123, 222, 64)).save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")
```

共通フィクスチャ: 組織 `org`・管理ユーザ・`subject`（slug 付き）・MEDIA ディレクトリ作成・`APIClient().force_authenticate(user)`。
「問題＋画像」の初期データは PUT 経由でなく `ProblemService.create_problem_with_images()` または作成 API（POST `/api/problems/`）で用意する。

---

## テストケース一覧

| TC | 種別 | 目的 | 手順（要点） | 期待結果（具体値） |
|----|------|------|------------|------------------|
| TC-AUTO-00 | 回帰 | 作成フロー（`_process_images` リファクタ後）が従来通り画像を作成する | POST `/api/problems/` に `question_image_1/2` を multipart 送信 | 201。`ProblemMediaAsset` が usage_kind='problem' で2件、position=1,2。`MediaAsset` 2件、物理ファイル2個存在。 |
| TC-AUTO-01 | 追加 | 既存1枚の問題に新規1枚を追加 | 既存問題（problem画像1枚, asset A, pos1）に対し PUT、`question_images_order=[{"existing":A},{"new":"question_image_1"}]`＋`question_image_1`=新PNG | 200。problem画像の有効 link 2件（pos1=A, pos2=新B）。GET 再取得で `question_images` 長さ2、順序 A,B。 |
| TC-AUTO-02 | 無変更（テキストのみ） | order フィールド非送信時は画像を変更しない | 既存問題（画像2枚）に対し PUT で `question_text` のみ変更、`*_images_order` を**送らない** | 200。`question_images` は2枚のまま不変。`question_text` 更新済み。 |
| TC-AUTO-03 | 全削除 | 空配列 `[]` 送信で当該種別を全削除 | 既存問題（problem画像2枚・共有なし）に PUT、`question_images_order=[]` | 200。problem の有効 link 0件。両 `MediaAsset.is_deleted=True`、物理ファイル削除済み。explanation 画像は未送信なら不変。 |
| TC-AUTO-04 | 並び替え | 既存3枚 [A,B,C] を [C,A,B] に並び替え | PUT `question_images_order=[{"existing":C},{"existing":A},{"existing":B}]` | 200。position 再採番: C=1,A=2,B=3。UNIQUE 制約違反が起きない（例外なし）。GET 順序 C,A,B。物理ファイル・MediaAsset は削除されない。 |
| TC-AUTO-05 | 共有画像の削除 | 他問題と共有するアセットの削除は紐づけ解除のみ | asset S を problem1・problem2 が共有。problem1 に PUT `question_images_order=[]` | 200。problem1 の link 解除。`MediaAsset(S).is_deleted=False`、物理ファイル**残存**。problem2 から S は引き続き取得可能。 |
| TC-AUTO-06 | 認可（テナント） | 他組織ユーザは編集不可 | org2 のユーザで org1 の問題に PUT | 404（queryset スコープ）。org1 問題の画像・テキストは不変。 |
| TC-AUTO-07 | atomic（新規保存失敗・物理削除遅延の検証） | 途中失敗で部分更新が残らず、**残すべき物理ファイルも消えない** | 既存問題（画像2枚 A,B）に PUT、order で既存B削除＋不正な新規ファイル（非画像/サイズ超過）を `{"new":...}` で追加 | 400。**ロールバック＋物理削除未到達**: 既存2枚（A,B）の link・MediaAsset.is_deleted=False・**物理ファイル2個が全て元のまま**（B も削除されていない）。※物理削除を全工程の最後に遅延する設計（plan §10）が正しく実装されていれば成立。 |
| TC-AUTO-08 | atomic（不正order） | 不正 order で全ロールバック | 既存問題に PUT、`question_images_order` が不正JSON or 6要素（上限超過） | 400（不正JSON or 「最大5枚」）。画像・選択肢・テキストいずれも変更なし。 |
| TC-AUTO-09 | 認可（横断混入） | 他問題のアセットUUIDを existing 指定で拒否 | problem1 に PUT、`existing` に problem2 のアセット UUID を指定 | 400（「本問題に紐づいていません」）。problem1 の画像不変。 |
| TC-AUTO-10 | 解説画像 | explanation 種別でも追加・削除・並び替えが機能 | TC-01/03/04 相当を `explanation_images_order`＋`explanation_image_*` で実施（problem 種別の order は未送信） | 各 200・具体値: ①追加=explanation link 2件 pos1=既存A/pos2=新B、②空配列削除=explanation link 0件・該当 MediaAsset.is_deleted=True×（非共有分）・物理削除済み、③並び替え [A,B,C]→[C,A,B]=position C=1,A=2,B=3。いずれも **problem 種別の画像は不変**。 |
| TC-AUTO-11 | 差し替え（AC直結） | 1リクエストで既存除外＋新規追加（existing/new 混在）が反映 | 既存問題（problem画像2枚 A,B）に PUT、`question_images_order=[{"existing":A},{"new":"question_image_1"}]`＋`question_image_1`=新C（=B を差し替え） | 200。有効 link 2件: pos1=A, pos2=新C。B は紐づけ解除（非共有なら is_deleted=True＋物理削除）。GET 順序 A,C。 |
| TC-AUTO-12 | 認可（テナント・SEC-1） | 自組織の問題を他組織 subject に付け替える越境を拒否 | org1 ユーザが org1 の自問題に PUT、`subject`=org2 の subject id を指定（＋新規画像 `question_image_1` を同送） | 400（subject の組織不一致）。problem の subject は org1 のまま不変。**他組織ストレージ配下に新規ファイルが書き込まれていない**（org2 ディレクトリにファイル増加なし）。画像 link も不変。 |
| TC-AUTO-10b | 解説画像（削除・並び替え） | AC#5 完全性: explanation 種別でも削除・並び替えが機能 | explanation 画像3枚 [A,B,C] を [C,A,B] に並び替え→空配列で全削除 | 並び替え 200: position C=1,A=2,B=3。全削除 200: link 0件・3アセット is_deleted=True・物理削除済み。 |
| TC-AUTO-13 | 入力検証（重複existing） | 同一既存UUID重複指定で unique違反の500を防止 | PUT `question_images_order=[{existing:A},{existing:A}]` | 400（「同じ既存画像を重複して指定できません」）。画像不変（Aのみ）。 |
| TC-AUTO-14 | 入力検証（両キー） | existing/new 同時指定を拒否（孤児アセット防止） | PUT `question_images_order=[{existing:A, new:question_image_1}]`＋ファイル | 400（「existing と new を同時に指定できません」）。画像不変（Aのみ）。 |
| TC-AUTO-15 | 共有（別usage_kind） | 同一アセットが problem/explanation 両方に共有される場合、片方削除で物理削除しない | 同一アセットを problem(pos1)・explanation(pos1) に紐づけ→problem を空配列で全削除（explanation は order 未送信） | 200。problem link 0件。explanation link 残存。**アセット is_deleted=False・物理ファイル残存**（別 usage_kind 共有を考慮）。 |
| TC-AUTO-16 | キャッシュ無効化 | `invalidate_problems_cache` が実際に problems キャッシュをクリアする | `set_problems_cache`(subject指定/None) → `invalidate_problems_cache(sid)` → `get` | 双方 `None`（旧実装は KEY_PREFIX 二重付与＋subject 限定パターン不一致でクリアされなかった）。 |
| TC-AUTO-17 | 結合（キャッシュ越し反映） | 一覧 API（キャッシュ経由）でも追加画像が反映される | GET `/api/problems/`（キャッシュ生成）→ PUT で画像追加 → 再 GET | 再 GET の `question_images` が 1→2 に増える（無効化が効かないと古い一覧が返り FAIL）。実機で観測された不具合の回帰テスト。 |

---

## 否定・回帰系 TC の false-green 自己検証（実装時に必須）

計画書ルール「否定・不在・回帰系の決定論テストは失敗条件を注入して実際に NG になることを確認してから採用する」に従い、以下の TC は**検証対象を一時的に壊して NG になること**を実装時に確認してから採用する。確認結果は `/test` 実行記録に残す。

| TC | 注入する故障（一時的に壊す） | 期待: 注入時に FAIL すること |
|----|------------------------------|------------------------------|
| TC-AUTO-02（無変更） | `_reconcile_images` が `order is None` でも reconcile を走るよう改変 | 画像が消える/変わるため assert で FAIL |
| TC-AUTO-04（並び替え） | delete→recreate を「インプレース position 更新」に差し替え | UNIQUE 制約違反 or 順序不一致で FAIL |
| TC-AUTO-05（共有） | 共有チェック（`exclude(problem=...).exists()`）を無効化し常に物理削除 | 共有ファイルが消えるため「残存」assert が FAIL |
| TC-AUTO-06（他組織404） | get_queryset の組織スコープを一時撤廃 | 200/編集成功になり「404・不変」assert が FAIL |
| TC-AUTO-07（atomic／物理削除遅延） | (a) `@transaction.atomic` を一時除去、または (b) 物理削除を手順4の前（新規保存より先）に戻す | (a)で DB 部分更新が残り、(b)で B の物理ファイルが消えるため「全て元のまま」assert が FAIL |
| TC-AUTO-09（横断混入） | existing UUID 検証を一時除去 | 他問題アセットが紐づき「400・不変」assert が FAIL |
| TC-AUTO-11（差し替え／差し替え後 B 不在） | 共有チェックを無効化、または物理削除ステップ6を削除 | 差し替えで除外した B の `is_deleted=True`・物理削除の不在 assert が FAIL（B が残ってしまう） |
| TC-AUTO-12（越境 subject 拒否） | SEC-1 の subject org 検証ガードを一時除去 | 越境付け替えが 200 で通り「400・subject 不変・他組織にファイル不在」assert が FAIL |
| TC-AUTO-13（重複existing） | step3 の重複existingチェックを一時除去 | unique違反で500になり「400」assert が FAIL |
| TC-AUTO-14（両キー） | step3 の existing/new 同時指定チェックを一時除去 | existing として処理され200になり「400」assert が FAIL |
| TC-AUTO-15（別usage_kind共有） | step6 共有チェックに `.exclude(problem=problem)` を復活 | 別 usage_kind 共有が見落とされ物理削除され「is_deleted=False・ファイル残存」assert が FAIL |
| TC-AUTO-16/17（キャッシュ無効化） | `invalidate_problems_cache` を旧実装（手書きKEY_PREFIX＋subject限定パターン）に戻す | 無効化が効かず get が旧値を返す/再GETが古い一覧を返すため双方 FAIL |

> 上記は「正常系で OK を返すだけ」の見かけゲートでないことを担保する。各 TC は具体的な DB 件数・position 値・is_deleted・物理ファイル有無・HTTP ステータスを assert する（単なる「例外が出ない」ではない）。

---

## 完了条件
- TC-AUTO-00〜17（10b 含む）が全て PASS。
- 上表の故障注入で対象 TC が FAIL することを確認（false-green でない）。
- `flake8` / `bandit`（MEDIUM 以上）に新規違反がないこと。

---

## 実行記録（/test I073 — 2026-06-24）

- 環境: Docker（`docker compose exec backend python -m pytest`）。pytest.ini（`--no-migrations`）。
- **backend 専用 TC（auto_test 正）**: `problems/tests/test_I073_image_update.py` → **18 passed**（TC-AUTO-00〜15 を 18 テスト関数で網羅）。
- **backend 全体（回帰）**: **43 passed**, 0 failed。
- **frontend Jest（回帰）**: 2 suites / **7 passed**, 0 failed（passWithNoTests）。
- **lint/scan**: ruff / bandit / tsc / ESLint(--max-warnings 0) すべてクリーン（pre-commit 通過）。
- **false-green 自己検証**: 否定/認可系 TC（02/04/05/06/07/09/12/13/14/15）に故障注入し、全件で NG（FAIL）検出を確認済み（見かけゲートなし）。
- **手動 TC-MAN-09（Claude実施）**: aria-label 付与を確認 → OK。
- 手動 TC-MAN-01〜08（Human・ブラウザ操作）は別途実施。

---

## 再発防止記録（/fix-loop I073 — 2026-06-26｜キャッシュ無効化バグ）

- **なぜ失敗したか**: 編集で画像を追加・保存しても参照/一覧に反映されなかった。保存自体は成功（DB 反映済み）だが、`core/cache_service.py` の `invalidate_problems_cache` が機能しておらず、`fetchProblems()` が古い問題一覧キャッシュを返していた。要因は (1) `delete_pattern` へ渡すパターンに KEY_PREFIX（`learning_app_problems:`）を手書き → django-redis が自動付与するため二重付与で永久に不一致、(2) `subject_id` 限定パターンが実キー（`problems_difficulty_*_subject_id_*_user_id_*`）と構造不一致＋全件リスト（subject_id=None）未対応。
- **なぜ自動テストで漏れたか**: 既存 TC が **DB 状態のみ** を assert し、一覧 API（キャッシュ経路）を経由していなかった。
- **何を変えたか**: `invalidate_problems_cache` を `_delete_by_pattern(self.problems_cache, "problems_*")` に修正（プレフィックス除去＋全変種一括クリア）。`_delete_by_pattern` に「パターンに KEY_PREFIX を含めない」契約 docstring を追記。
- **回帰テスト追加**: TC-AUTO-16（`cache_service` 直: set→invalidate→get が None）／TC-AUTO-17（結合: GET→PUT追加→再GET で `question_images` が 1→2）。いずれも旧実装に戻すと FAIL することを故障注入で確認（false-green なし）。
- **次回どう防ぐか**: 「保存後の再取得で反映される」系 AC は **DB だけでなく API（キャッシュ経路）越し**で検証する。`_delete_by_pattern` 利用時はパターンに KEY_PREFIX を含めない（docstring に明記）。
- **セキュリティ考慮**: 無効化範囲を広げても、キャッシュは user_id 別・データは組織スコープ queryset のためテナント越境・情報漏洩は発生しない。認証/認可/注入/XSS いずれにも非該当。
- **未対応（別イシュー）**: `analytics`/`spaced_repetition` 等の同型 KEY_PREFIX 二重付与バグ（提案4）。`is_correct` write_only による正解表示・編集UX（提案3）。
