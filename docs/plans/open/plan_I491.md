# I491 計画書: I473 のレビューの残り（科目のキャッシュ・連続日数の読み出しの上限・E2E の比べ方・学習時間の上限の境界値・QuizAnswer を組織の境界の見張りへ）

## 基本情報
- **計画書ID**: plan_I491
- **関連イシュー**: #491
- **Draft PR**: #537
- **作成根拠資料**: docs/issues/open/I491.md（GitHub #491 の本文の写し。設計確認メモあり）
- **実装後評価**: docs/reviews/open/I491_review.md
- **作成日**: 2026-11-16

## 1. 背景/目的
- I473 で、ダッシュボードの数字の出どころをクイズの答えの記録（`QuizAnswer`）に 1 本化した。レビューで止める重さに当たらない Low の指摘が 5 件（F5・F8・F7・F6・B1）残り、`QuizAnswer` を組織の境界の見張りに入れるか（Q1）も決めていなかった
- 目的: 5 件を直す（F8 は直さない理由を記録する）。`QuizAnswer` を組織の境界の見張りに入れる

### 調査結果
**原因の概要**: どれも、I473 の計画が前提に入れていなかった境目（組織を移る利用者・長く使い続ける利用者・E2E の並列実行・上限ちょうどの値）での扱いの穴。今、他組織のデータが出ることは無い。

1. **F5 科目のキャッシュ**（`backend/core/subject_service.py:20-23` の `user_subjects_cache_key`・`:112-164` の `get_user_selected_subjects`・`backend/problems/signals.py:18-22`）
   - キーが `user_subjects_{user_id}_org_{organization_id}_count_{annotate_count}`。消す側（signals）は利用者の今の組織のキーだけを消す。組織 A で作ったキャッシュは、組織 B に移った後の選び直しで消えず、期限（`CACHE_TIMEOUTS['subject_list']` = 7200 秒）の間に A へ戻ると古い選択が返る
   - **計画の調査で新しく分かったこと**: キャッシュに入るのは「今の組織で絞った後の科目」（`:159-161` が絞った `queryset` を保存する）。そのため、イシューの設計確認メモどおりに「キーから組織を外すだけ」にすると、A で作ったキャッシュ（A の科目の番号だけ）を B で読み、B の条件で絞って空になる。B で選んだ科目が期限まで出ない、新しい不具合になる。直すには、キャッシュの中身を「本人が選んだ科目の番号の全部（組織で絞る前）」に変える必要がある
   - 組織を変える画面・API は無い（組織は登録のときに `backend/accounts/serializers.py:100-108` で決まるだけ。`backend/accounts/admin.py` の `UserAdmin` の項目にも組織が無い）。起きるのは運用者が DB を直接書き換えたときだけ
   - キーの関数の使い手（grep `user_subjects_cache_key`）: `core/subject_service.py:137`・`problems/signals.py:22`・`dashboard/tests/test_I473_overview.py:423`・`problems/tests/test_I494_user_subjects.py:143`。ほかに無い
2. **F8 旧組織の進行中の学習記録**（`backend/studylogs/views.py` の `StudyLogViewSet.create`）: `StudyLog` に画面から書く経路は無い（#492 の調査・2026-11-13）。#492 で API・表ごと消す
3. **F7 連続日数**（`backend/dashboard/selectors.py:105-119` の `_current_streak`）: 答えのある日付を全期間から読む（1 年で最大約 365 行）。画面の 7 日ごとの節目（`frontend/src/utils/dashboardAchievements.ts:129-141`）は `streak.current_days` をそのまま使う
4. **F6 E2E**（`e2e/tests/quiz-session.spec.ts:36-53`）: 共有の利用者 A の解答数が「前の値 + 1」かを厳密に比べる。`e2e/playwright.config.ts` は `workers`・`fullyParallel` を決めていない（ファイルの間は並列・同じファイルの中は順番）。今、クイズに答える spec はこのファイルだけ（grep `choice-option`・`/api/quiz/` は `quiz-session.spec.ts` だけ）なので今は落ちないが、答える spec を足すと落ちうる
5. **B1**（`backend/dashboard/tests/test_I473_overview.py:160-172`）: 上限 300 秒を 400 秒の答えだけで確かめている
6. **Q1**（`backend/studylogs/tests/test_I455_org_scoped_querysets.py:199-298`）: 見張りの対象は「既定の取り出し口が `OrgScopedQuerySet` のモデル」を登録から集めたもの。`OrgScopedQuerySet.for_user`（`backend/problems/querysets.py:41-49`）は `filter(user=user)` で持ち主を決めるので、持ち主が `session__user` の `QuizAnswer` は載せられない
   - 見張りの範囲（`studylogs`・`dashboard` のテスト・マイグレーション以外）での `QuizAnswer` の使い方: `dashboard/selectors.py:33`（`_answers`・絞っている）・`dashboard/verify_data.py:315`（`bulk_create`・書き込み）・`:325`（`bulk_update`・理由のコメントが無い。対象に入れると見張りが止める）
7. **範囲外の発見**: `backend/problems/views.py:571-575`（`_analyze_user_performance`・`generate_adaptive` から呼ぶ）が `QuizAnswer` に無い項目 `created_at` で絞っている。呼ばれると必ず失敗する。#460（AI 生成が 415）を直すと表に出るので、retro で #460 に同梱する（このイシューでは直さない）

### 環境前提
- `docker compose ps`（2026-11-16）: backend・db・frontend・redis が動いている。テストの DB は PostgreSQL（`backend/core/settings.py:90`）
- pytest・Jest・E2E・`makemigrations --check` は CI（`.github/workflows/ci.yml:38` など）が PR ごとに流す。手元では流し直さない

## 2. 受け入れ条件
- [ ] F5: 組織 A でキャッシュを作る → B へ移る → 科目の選択を外す → A へ戻る、で外した科目が返らない。B へ移った直後に、B で選んでいる科目が出て A の科目が出ない（TC-01・TC-02）
- [ ] F8: 直さない理由（画面から書く経路が無い・#492 で消す）が計画書（9 章）に記録されている
- [ ] 連続日数は頭打ちにせず正確に数え、1 回の読み出しの行数は 365 日分まで。窓の日数ちょうど・窓を超える連続で正しい日数が出る（TC-04・TC-05）
- [ ] E2E の解答数のテストが「前の値より大きい」で比べる（TC-07）
- [ ] 学習時間の上限のテストに、299・300・301 秒の答えがある（TC-06）
- [ ] `QuizAnswer` が組織の境界の見張りの対象になり、絞らない読み出しを見張りが止める（失敗の注入つき・TC-08・TC-09）
- [ ] 既存のテストに退行が無い（CI）

## 3. 影響範囲
- Backend: `core/subject_service.py`・`problems/signals.py`・`problems/querysets.py`・`problems/models.py`・`dashboard/selectors.py`・`dashboard/verify_data.py`（理由のコメント 1 行）・テスト 3 ファイル
- Frontend: なし（`streak.current_days` の形・意味は変えない）
- E2E: `e2e/tests/quiz-session.spec.ts`
- DB: なし（マネージャーの差し替えは `use_in_migrations` を付けないのでマイグレーションは出ない。CI の `makemigrations --check` で確かめる）
- Config/Infra: なし。キャッシュのキーの名前が変わるので、古いキーの値は使われずに期限（2 時間）で消える

## 4. 変更点一覧（具体）
| ファイル | 関数など | 変更 |
|---|---|---|
| `backend/core/subject_service.py` | `user_subjects_cache_key` | 引数を `user_id` だけにし、`f"user_selected_subject_ids_{user_id}"` を返す（中身が変わるので名前も変え、古い形の値を読まない） |
| `backend/core/subject_service.py` | `SubjectService.get_user_selected_subjects` | キャッシュに入れるのを「`UserSubjectAccess` の科目の番号の全部（組織で絞る前・番号順の list[int]）」にする。組織の条件・名前順・件数の付与は読むたびに DB で掛ける（今と同じ 1 か所）。番号が空なら保存しない（今と同じ） |
| `backend/problems/signals.py` | `invalidate_user_subjects_cache` | キー 1 つを消すだけにする（`annotate_count` の繰り返しを外す） |
| `backend/problems/querysets.py` | `OrgScopedQuerySet` | 持ち主への経路 `user_path: str = 'user'` を足し、`for_user` の `self.filter(user=user)` を `self.filter(**{self.user_path: user})` にする。既存の 8 モデルは既定の `'user'` のままで動きは変わらない |
| `backend/problems/models.py` | `QuizAnswerQuerySet`（新規）・`QuizAnswer.objects` | `user_path = 'session__user'`・`subject_paths = ('problem__subject',)`・`allow_null = False`。`objects = QuizAnswerQuerySet.as_manager()` |
| `backend/dashboard/selectors.py` | `_answers` | `QuizAnswer.objects.for_user(user)` にする（使わなくなる `scope_to_user_org` の import を外す）。QuizAnswer を読むのはここ 1 か所のまま |
| `backend/dashboard/selectors.py` | `_current_streak`・定数 `STREAK_WINDOW_DAYS = 365` | 今日から 365 日の窓で答えのある日を読み、連続が窓の始まりまで届いたときだけ、その前の 365 日を読み足す（下のコード例） |
| `backend/dashboard/verify_data.py` | `_write_answers` | `QuizAnswer.objects.bulk_update` の直前に「# 組織で絞らない: …」のコメントを足す（見張りの対象に入るため。動きは変えない） |
| `backend/studylogs/tests/test_I455_org_scoped_querysets.py` | `SPECS`・新しいテスト | `QuizAnswer` の行を足す（TC-01・TC-02 の表で確かめる）。見張りが `QuizAnswer` の絞らない読み出しを止めることのテスト。docstring・失敗メッセージの「8 モデル」を「境界つきの取り出し方を持つモデル」に直す（数が増えてずれないように） |
| `backend/dashboard/tests/test_I473_overview.py` | 新しいテスト・TC-16 の最後の行 | TC-01〜TC-06 の I491 分。`user_subjects_cache_key(1, 7, False)` の行を新しい形にする |
| `backend/problems/tests/test_I494_user_subjects.py` | `test_cache_cleared_after_save`（TC-05） | キーを 1 つにする（`keys = [user_subjects_cache_key(user.id)]`）。確かめる中身は同じ |
| `e2e/tests/quiz-session.spec.ts` | 「クイズに答えると、ダッシュボードの解答問題数が 1 増える」 | 比べ方を `expect.poll(...).toBeGreaterThan(before)` にし、題を「増える」にする |

### 修正アプローチ
- **F5**: キャッシュに「組織に関係しない中身」だけを入れ、組織の境界は読むたびに DB で掛ける。そうすればキーに組織が要らず、組織を移っても消し残し・取り違えが起きない。選び直し（`UserSubjectAccess` の変更）のときに消すキーは利用者ごとに 1 つになる
- **F7**: 見え方（日数）は変えず、読み出しを窓に区切る。ふつうの利用者は今までどおり 1 回の読み出しで済み、1 年を超えて毎日続けた利用者だけ、1 年ごとに 1 回の読み出しが足される
- **Q1**: 見張りの土台（`OrgScopedQuerySet`）に「持ち主への経路」を足し、`QuizAnswer` に境界つきの取り出し口を持たせる。見張りは登録から対象を集めるので、自動で対象に入る

### コード例
F5（`core/subject_service.py`）:
```python
def user_subjects_cache_key(user_id: int) -> str:
    """利用者が選んだ科目の番号（組織で絞る前）のキャッシュのキー（無効化する signals と同じ関数で作る・I491）"""
    # 中身は他組織の科目の番号を含みうる。読むのは get_user_selected_subjects だけにし、そこで必ず組織の条件を掛ける
    return f"user_selected_subject_ids_{user_id}"

# get_user_selected_subjects の中
cache_key = user_subjects_cache_key(user.id)
# キャッシュには、選んだ科目の番号の全部（組織で絞る前）だけを入れる。組織が変わっても中身は正しいので、
# キーに組織は要らない。組織の境界・並び・件数は下の 1 か所で毎回 DB の条件で掛ける（I491）
subject_ids = cache_service.get_subjects_cache(cache_key) if use_cache else None
if subject_ids is None:
    subject_ids = sorted(UserSubjectAccess.objects.filter(user=user).values_list('subject_id', flat=True))
    if use_cache and subject_ids:
        cache_service.set_subjects_cache(subject_ids, cache_key)
queryset = Subject.objects.filter(id__in=subject_ids, organization_id=user.organization_id).order_by('name')
```

F7（`dashboard/selectors.py`）:
```python
STREAK_WINDOW_DAYS = 365  # 連続日数を数えるときに 1 回で読む日数（1 回の読み出しの行数の上限）

def _answer_days(answers, first, last) -> set:
    """first〜last（両端を含む・日本時間）の、答えのある日"""
    return set(_between(answers, first, last).annotate(day=TruncDate('answered_at'))
               .values_list('day', flat=True).order_by().distinct())

def _current_streak(answers, today, *, window_days=STREAK_WINDOW_DAYS) -> int:
    """答えのある日が今日（今日がまだなら昨日）から何日続いているか（頭打ちにしない）"""
    last = today
    cursor = None
    streak = 0
    while True:
        first = last - timedelta(days=window_days - 1)
        days = _answer_days(answers, first, last)
        if cursor is None:
            cursor = today if today in days else today - timedelta(days=1)
        while cursor >= first and cursor in days:
            streak += 1
            cursor -= timedelta(days=1)
        if cursor >= first:  # 窓の中で途切れた
            return streak
        last = first - timedelta(days=1)  # 窓の始まりまで続いた → その前の窓を読む
```
- `window_days` はテストで小さな窓を渡すための引数（既定は定数。テストのための差し替え〔monkeypatch〕をしない）。`window_days >= 2`（今日がまだのときの昨日が窓に入る）を前提にし、関数の冒頭で `ValueError` にする
- 終わる保証: 窓を読み足すのは「窓の始まりの日まで答えがある」ときだけ。最初の答えより前の窓は空なので、そこで必ず終わる

Q1（`problems/querysets.py`・`problems/models.py`）:
```python
class OrgScopedQuerySet(QuerySet):
    subject_paths: tuple[str, ...] = ()
    allow_null: bool = False
    user_path: str = 'user'  # 記録から持ち主の利用者への経路（I491）

    def for_user(self, user):
        ...
        queryset = self.filter(**{self.user_path: user})

class QuizAnswerQuerySet(OrgScopedQuerySet):
    user_path = 'session__user'
    subject_paths = ('problem__subject',)
```

## 5. 実装手順（ステップ）
1. **F5（キャッシュ）**: TC-01・TC-02 を先に書いて今のコードで落ちることを記録し（TDD）、`subject_service.py`・`signals.py` を直し、TC-03（既存の 2 テストのキーの形）を直す → TC-01〜TC-03 参照
2. **Q1（見張り）**: `querysets.py`・`models.py`・`selectors._answers`・`verify_data.py` のコメント・`test_I455` の `SPECS` と見張りのテスト → TC-08・TC-09 参照。ステップ 3 と同じ `selectors.py` を触るので、ステップ 1 の後・3 の前に行う
3. **F7（連続日数）**: `_answer_days`・`_current_streak`・定数。テストは TC-04・TC-05 参照。クエリ数（TC-12 の 9 本）は変わらない → TC-10 参照
4. **B1**: TC-06 を足す
5. **F6**: E2E の比べ方 → TC-07 参照
- ステップ 4・5 はほかと独立（並行可）。ステップ 1〜3 はこの順（同じファイルの衝突を避ける）
- F8 は実装しない（9 章）
- サービスの再起動は要らない（開発の backend はファイルの変更で読み直す）

## 6. テスト計画
### 自動（詳細は docs/tests/open/I491_auto_test.md）
- ユニット＋結合（pytest・DB あり）: TC-01〜TC-06・TC-08〜TC-10。再発防止のテストは TC-01（F5 の再現手順そのまま）・TC-02（計画の調査で見つけた取り違え）・TC-04（窓の境目）
- 組織の境界: TC-02（B へ移った後に A の科目が出ない）・TC-08（`QuizAnswer.objects.for_user` が他人・他組織の答えを返さない）・既存の `test_only_own_answers_in_own_org`
- E2E: TC-07（CI の E2E）
- 退行: CI の全テスト・`makemigrations --check`（TC-11）
### 手動（docs/tests/open/I491_manual_test.md）
- 開発の DB の確かめ用の利用者でダッシュボードを開き、連続日数が作り直しのログの期待値と同じ（Claude・Playwright MCP）

## 7. ロールバック
- PR を revert する。DB の変更が無いので、コードを戻すだけ。キャッシュは名前が戻るので、新しい形の値（`user_selected_subject_ids_*`）は使われずに 2 時間で消える。古い形の値も期限で消えているので、戻した後は最初の読み出しで作り直される

## 8. Risk & 回避策
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: キャッシュの中身が組織の外の科目の番号を含むので、読む側で組織の条件を外すと他組織の科目が出る | 組織の条件は `get_user_selected_subjects` の 1 か所で必ず掛ける形のまま（キャッシュの有無で分けない）。TC-02 が B へ移った後に A の科目が出ないことを確かめる | 回避 |
| R2: `OrgScopedQuerySet` の変更で既存の 8 モデルの絞り方が変わる | 既定の `user_path='user'` で今と同じ式になる。既存の TC-01・TC-02（`test_for_user_scopes_by_org` などの 8 モデルの表）がそのまま通ることで確かめる | 回避 |
| R3: 窓の読み足しが終わらない | 読み足しは「窓の始まりまで答えがある」ときだけ。最初の答えより前は空で必ず終わる。TC-04 が窓を 2 つ以上またぐ場合を確かめる | 回避 |
| R4: 1 年を超えて続けた利用者は表示のクエリが 1 本増える | 1 年ごとに 1 本で、ふつうの利用者（TC-10 の 9 本）は変わらない。行数は 1 回 365 行まで | 受け入れ |
| R5: E2E を「より大きい」にすると、2 増える不具合を見逃す | この E2E の目的は「答えても 0 のまま」の再発防止（I473）。数え方の正確さは I473 の pytest（`test_values_and_seconds_cap` など）と TC-06 が確かめる | 受け入れ |
| R6: 見張りの範囲（`studylogs`・`dashboard`）の外（`problems`・`core`）の `QuizAnswer` の読み出しは見張られない | 範囲は I455 の決まりのまま（`problems` には既存の絞らない読み出しが多く、広げるとこのイシューの範囲を超える）。#492 で読み手が `core/tasks.py` に移るときは、#492 の計画で扱う | 受け入れ |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- F7 は頭打ちにせず正確に数え、読み出しの行数は作り方で抑える（ユーザー回答「BP・UI/UX の観点でベストなやり方で」）
- F8 は直さない。理由: `StudyLog` に画面から書く経路が無く、#492 で API・表ごと消す（イシューの設計確認メモ。Claude が決定）
- F5 はキーから組織を外し、組織の境界は読む側の DB の条件だけに頼る
- F6・Q1 は技術の選択として計画で決める（Q1 は入れる方向）

Claude が決めた（技術的な選択と理由）:
- **F5 のキャッシュの中身を「組織で絞る前の番号の全部」に変える**（仮定で決めた・技術）: 設計確認メモの「キーから組織を外す」だけでは、絞った後の値を別の組織で読んで空になる（調査結果 1）。中身を組織に関係しない値にすれば、メモの方針（キーに組織を入れない・境界は DB）がそのまま成り立つ。画面に見える動きは「組織を移っても正しい科目が出る」で、メモの目的と同じなので、価値判断の変更ではない
- **キーを利用者ごとに 1 つにする**（仮定で決めた・技術）: 件数の付与は読むたびに DB で掛けるので、中身が `annotate_count` で変わらない。消し漏れの種を減らす
- **キーの名前を変える**（仮定で決めた・技術）: 中身の形（辞書の list → 番号の list）が変わるので、古い形の値を読まないように名前を変える。古い値は期限で消える
- **F7 の窓を 365 日にする**（仮定で決めた・技術）: 1 回の読み出しを 1 年分までにする。ふつうの利用者は 1 回で済み（クエリ数 9 は変わらない）、1 年を超えた連続だけ読み足す
- **F7 は窓で読み足す方式**（仮定で決めた・技術）: SQL の窓関数で連続を数える案より、今の `_between`・`TruncDate` の組み方にそろい、読みやすい
- **F6 は「前の値より大きい」で比べる**（仮定で決めた・技術）: 専用の利用者を作る案は、シード（`seed_e2e`）・global-setup の変更が要り、この 1 本の E2E のためには重い。目的（0 のままの再発防止）は「より大きい」で守れる（R5）
- **Q1 は `OrgScopedQuerySet` に `user_path` を足して `QuizAnswer` を載せる**（仮定で決めた・技術）: 見張りは登録から対象を集めるので、モデルに載せれば自動で対象になり、表（`SPECS`）の足し忘れも `test_specs_cover_all_scoped_models` が止める。理由のコメントの見張りに `QuizAnswer` の名前を書き足す案より、取り出し口がそろう（`_answers` が `for_user` になる）
- **見張りの範囲は広げない**（仮定で決めた・技術）: R6
- **`verify_data.py` の `bulk_update` には理由のコメントを足す**（仮定で決めた・技術）: 同じ関数の `QuizSession.objects.bulk_update` と同じ書き方。`NOT_READS` に `bulk_update` を足す案は、見張りの決まりを変えるので取らない
- **範囲外の `problems/views.py:571` は直さない**（仮定で決めた・技術）: AI 生成の受け付けが直る（#460）までは呼ばれても前で失敗し、#460 で一緒に確かめるのが自然。retro で #460 に同梱する
- 一覧（`docs/reviews/backlog/`）: 実装対象のファイルに当たる行は無い。`FILE=-` の行（I223 の B1〜B4・I224 の F9）はハーネスの話で、このイシューに関係しない → 残す
- セキュリティ: 入力の検証・認証・認可の変更は無い（新しい API なし）。組織の境界は R1・R2 のとおり守り、TC-02・TC-08 で確かめる。機密データの扱いなし。依存の追加なし（pip-audit・npm audit は不要）。bandit は MEDIUM 以上を直す（CI）
- P3（データ整合性）・P5（運用）・P8（コスト）影響なし（DB の変更・非同期処理・外部サービスなし）。P6（性能）: F7 の読み出しの行数を減らす変更で、クエリ数は変えない（TC-10）。画面の変更なし。P9（プライバシー）: 個人の学習データの読み方は変えない（境界は今と同じかより強い）

Danger Ops（有無/手順/ロールバック）:
- 無

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 2 | 読んで可 | TC-01・TC-02 が、直す前の作り（キーに組織・絞った後の値を保存）で本当に落ちる形か（auto_test の「失敗の注入」の記録を読む） |
| V2 | 1 | 読んで可 | `OrgScopedQuerySet` に `user_path` を足しても、既存の 8 モデルの `for_user` の結果が変わらないこと。既存の 8 モデルの表のテスト（I455 の TC-01・TC-02）と TC-08 が、他人の記録・他組織の科目の記録を返さないことを確かめているか |
| V3 | 3 | 読んで可 | キャッシュの中身が他組織の科目の番号を含みうる作りで、読む側のどの経路でも組織の条件が外れないこと（`get_user_selected_subjects` 以外にこのキャッシュを読む所が無いことを含む）。TC-02 |
| V4 | 2 | 読んで可 | TC-04 が、窓の読み足しを外した作りで落ちる形か（「失敗の注入」の記録を読む） |

## 計画変更記録
- 計画レビュー（20261116_1716）の Info 3 件を反映: I455 のテストの「8 モデル」の表現を直す・キャッシュのキーの関数に境界のコメント・TC-01/TC-02 の並びの期待値を DB の並びと比べる形に。方式・範囲・受け入れ条件は変えないので再レビューはしない

## レビュー結果
- [20261116_1716 判定: ✅ 完了](../../reviews/I491_plan_review_20261116_1716.md)
