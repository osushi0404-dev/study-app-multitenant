# I494 計画書: 学ぶ科目を後から選び直せるようにする

## 基本情報
- **計画書ID**: plan_I494
- **関連イシュー**: #494
- **Draft PR**: #529
- **作成根拠資料**: docs/issues/open/I494.md（GitHub #494 の本文の写し）
- **実装後評価**: docs/reviews/open/I494_review.md
- **作成日**: 2026-11-16

## 1. 背景/目的
- 利用者が学ぶ科目（`UserSubjectAccess`）は会員登録のときにしか作れず、後から変える画面も API も無い。科目が 0 件の人はダッシュボードで「組織の管理者に科目の登録を依頼してください」と案内されるが、組織に科目があって本人が選んでいないだけの場合も同じ案内で、自分では直せない（行き止まり）
- 目的: 設定画面の「学ぶ科目」のカードで、会員登録の後でも自分の組織の科目から選び直せるようにする。ダッシュボードの科目 0 件の案内を、組織に科目があればこのカードへの導線にする

### 調査結果
- **原因の概要**: 科目の割り当てを「会員登録のときに 1 回だけ決めるもの」として作り、後から変える API・画面を作っていない
- **詳細**:
  - 書く処理は会員登録の `backend/accounts/serializers.py:98-114`（`UserSubjectAccess.objects.bulk_create`）だけ。読む API は `GET /api/user/subjects/`（`backend/api/views/user_subjects.py`・関数のビュー・`subject_service.get_user_selected_subjects(user, use_cache=True)` の `id`・`name`）だけ
  - 選んだ科目を使う場所: ダッシュボードの科目の選択・「学習を開始」（`frontend/src/hooks/useUserSubjects.ts`・React Query のキー `['user-subjects', userId]`）・`frontend/src/components/SubjectSelector.tsx`（開くたびに取得）・ダッシュボードのおすすめ（`backend/dashboard/selectors.py:158`）・学習統計の科目別（`backend/studylogs/views.py:257-259`）
  - キャッシュ: `get_user_selected_subjects` は `user_subjects_cache_key(user.id, org_id, annotate_count)` に科目を入れる（`backend/core/subject_service.py:20`・`:137-162`）。消すのは `backend/problems/signals.py` の `post_save`・`post_delete`。`QuerySet.delete()` は 1 件ずつ `post_delete` を送るが、`bulk_create` は `post_save` を送らない。どちらもトランザクションの中で消すので、確定の前に別の読み取りが古い値を入れ直す隙がある
  - 組織の科目の一覧: `GET /api/subjects/`（`SubjectViewSet.list`）はページ分け（20 件）・問題数の集計つきで、選ぶ画面には重い。会員登録の `GET /api/organizations/subjects/public/?slug=` は未認証用で slug が要る
  - `backend/problems/permissions.py` の `AccessPermissionChecker` はどこからも import されていない（問題を解く権限には効いていない）
  - 応答の形: 例外は `core.exceptions.custom_exception_handler` が `{"error": {"main_message", "sub_message", "details"}}` に変える（400 は `main_message: "入力内容にエラーがあります"`・`sub_message` は最初の項目のエラー）
  - 横断のテナント境界テスト（`backend/core/tests/test_I446_cross_api_tenant_isolation.py`）は、URL の全経路が表（`ROUTE_TABLE`）に載っていないと落ちる。新しい経路を表に足す
  - API の契約（I493）: `backend/core/openapi.py` の `CONTRACT_PATHS` に入れた経路だけが `backend/openapi.yaml`・`frontend/src/types/api/schema.d.ts` に出る（作り直し忘れは CI が止める）
  - E2E の `e2e/tests/dashboard-layout.spec.ts` の TC-27 が、科目 0 件の `e2e_user_c`（組織 A・組織 A には科目がある）で今の「管理者に依頼」の文言を見ている。`seed_e2e` は `e2e_user_c` を毎回作り直す（科目 0 件に戻る）
  - キャッシュの置き場は Redis（`IGNORE_EXCEPTIONS: True`）。`cache_service.default_cache` は使うたびに `caches['default']` を引くので、テストで `override_settings(CACHES=LocMem)` が効く
- **環境の前提**（2026-11-16 に確かめた）: `docker compose ps` で backend・db・frontend・redis が稼働。drf-spectacular 0.30.0・@tanstack/react-query 5.104・react-router-dom 6.26（追加の依存なし）
- 既存テストの事前実行・lint の事前計測: CI・lint の変更ではないので省く（pytest・Jest・E2E は CI が PR ごとに流す）

## 2. 受け入れ条件
- [ ] AC1: 設定画面の「学ぶ科目」のカードで、自分の組織の科目を追加・解除して保存でき、保存した内容がダッシュボードの科目の選択・「学習を開始」に反映される（裏側のキャッシュ・画面の React Query のキャッシュが残って古い一覧が出ない）。API テスト TC-01・TC-02・TC-05、画面のテスト TC-21、手動 No.2〜No.4
- [ ] AC2: 他組織の科目・存在しない科目の番号を送っても割り当てられず、どちらも同じ 400 の応答になる（TC-03・TC-12）
- [ ] AC3: 0 件では保存できない。画面は保存ボタンを押せず「科目を最低1つ選択してください」を出し、API は 400（`details.subject_ids` が `["科目を最低1つ選択してください"]`）で断る（TC-04・TC-22）
- [ ] AC4: 保存の失敗がカードの中に残る表示（toast だけにしない）で出て、選んだ内容は消えない（TC-23・TC-24）
- [ ] AC5: ダッシュボードで科目が 0 件の人に、組織に科目があれば「学ぶ科目がまだ選ばれていません。設定画面で学ぶ科目を選んでください」と「学ぶ科目を選ぶ」（`/settings#learning-subjects` へ）が出る。組織に科目が 1 つも無ければ「科目がまだ登録されていません。組織の管理者に科目の登録を依頼してください」が出る（TC-40・TC-05・E2E TC-27・手動 No.1・No.5）
- [ ] AC6: 既存の機能に退行が無い（既存の pytest・Jest・E2E が通る）

## 3. 影響範囲
- Backend: 利用者の科目の API（`GET`・`PUT /api/user/subjects/`・`GET /api/user/subjects/available/`）・書き換えのサービス・API の契約（`openapi.yaml`）
- Frontend: 設定画面の「学ぶ科目」のカード（新しい部品）・ダッシュボードの「学習を開始」のカードの科目 0 件の案内・`subjectService.ts`・フック・画面の型（`schema.d.ts`・`types/api/index.ts`）
- DB: なし（既存の `UserSubjectAccess` を使う。マイグレーションなし）
- Config/Infra: なし（依存の追加なし）
- 変えないもの: `backend/problems/signals.py` の受け手の仕組み（消し方に「確定の後にもう一度消す」を足すだけ・計画変更記録）・`backend/problems/permissions.py`（使われていない）・`backend/studylogs/views.py`・`backend/dashboard/selectors.py`（外した科目を出さない今の作り）・`backend/accounts/serializers.py`（会員登録は変えない）・`frontend/src/components/SubjectSelector.tsx`（開くたびに取り直すので古くならない）

## 4. 変更点一覧（具体）

### 修正アプローチ
裏側は「選んだ科目の一覧を丸ごと置き換える」`PUT` を足し、組織の境界は DB の条件で掛け、書き換えは 1 つのトランザクションで行って確定の後にキャッシュを消す。組織の科目の一覧は、選ぶ画面用の軽い `GET .../available/` を足す。画面は設定画面に「学ぶ科目」のカードを独立した部品で足し、取得・保存を React Query で行い、保存の応答でダッシュボードが使うキャッシュを書き換える。ダッシュボードは、選んだ科目が 0 件のときだけ組織の科目を読み、案内を分ける。

### 4-1. 裏側の API
修正方針: 関数のビューをクラスのビュー（`APIView`）に置き換え、`GET` は今と同じ応答、`PUT` は検証をシリアライザ・書き換えをサービスに任せる（薄いビュー）。

| ファイル | 変更 |
|---|---|
| `backend/api/views/user_subjects.py` | `get_user_subjects` を `UserSubjectsView(APIView)` に置き換える。`permission_classes = [IsAuthenticated]`。`get`: 今と同じ（`get_user_selected_subjects(user, use_cache=True)` を `UserSubjectSerializer(many=True)` で `[{"id", "name"}]`）。`put`: `UserSubjectSelectionSerializer(data=request.data, context={'request': request})` → `is_valid(raise_exception=True)` → `replace_user_subjects(user=request.user, subject_ids=serializer.validated_data['subject_ids'])` → 200 で `get_user_selected_subjects(user, use_cache=False)` を同じ形で返す。`AvailableSubjectsView(APIView)`（`IsAuthenticated`）: `get` は `Subject.objects.filter(organization_id=user.organization_id).order_by('name')` を `AvailableSubjectSerializer(many=True)`（`id`・`name`・`description`）で返す（ページ分けなし。組織が無い利用者は `[]`）。各メソッドに `@extend_schema(request=…, responses={200: …})` |
| `backend/problems/serializers.py` | `UserSubjectSerializer(ModelSerializer)`（`Subject`・`fields=('id','name')`）・`AvailableSubjectSerializer`（`fields=('id','name','description')`）・`UserSubjectSelectionSerializer(Serializer)`: `subject_ids = ListField(child=IntegerField(min_value=1), min_length=1, max_length=MAX_SELECTABLE_SUBJECTS, error_messages={'required': '科目を最低1つ選択してください', 'min_length': '科目を最低1つ選択してください', 'max_length': '選べる科目の数を超えています'})`。`validate_subject_ids`: 重複を除き（並びを保つ）、`Subject.objects.filter(id__in=ids, organization_id=request.user.organization_id)` の件数が合わなければ `ValidationError('選択された科目の一部が無効です')`（他組織も存在しない番号も同じ文言。会員登録と同じ）。`MAX_SELECTABLE_SUBJECTS = 200`（モジュールの定数・大きすぎる本文を断るだけの上限） |
| `backend/problems/services/user_subject_service.py`（新規） | `replace_user_subjects(*, user, subject_ids: list[int]) -> None`。`@transaction.atomic`: `User.objects.select_for_update().get(pk=user.pk)`（同じ利用者の同時の保存を順に並べる）→ 今の `subject_id` の集合と比べ、外したものを `UserSubjectAccess.objects.filter(user=user, subject_id__in=removed).delete()`、足したものを `bulk_create([UserSubjectAccess(user=user, subject_id=i, granted_by=user) …], ignore_conflicts=True)`（変わらない行は触らない＝`granted_at` を保つ）→ `transaction.on_commit(lambda: invalidate_user_subjects_cache(user))` → `logger.info('user subjects replaced', extra={'user_id': user.id, 'organization_id': user.organization_id, 'added': len(added), 'removed': len(removed)})`（科目の番号は出さない）。組織の確かめはシリアライザが済ませている前提だが、念のためサービスでも `Subject.objects.filter(id__in=subject_ids, organization_id=user.organization_id)` の id だけを使う（呼び出し元に依らず組織の外を書かない） |
| `backend/problems/signals.py` | `_invalidate_user_subjects_cache` を公開の名前 `invalidate_user_subjects_cache` にして、サービスから使う（同じ消し方を 1 か所に保つ。シグナルの受け手は今のまま） |
| `backend/problems/urls.py` | `path('user/subjects/', UserSubjectsView.as_view(), name='user-subjects')`・`path('user/subjects/available/', AvailableSubjectsView.as_view(), name='user-subjects-available')` |
| `backend/core/openapi.py` | `CONTRACT_PATHS` に `'/api/user/subjects/'`・`'/api/user/subjects/available/'` を足す（I494: 設定画面の学ぶ科目） |
| `backend/openapi.yaml`・`frontend/src/types/api/schema.d.ts` | `docs/runbooks/common-commands.md`「API の形を変えたとき」の手順で作り直す（手で直さない） |

応答（成功）:
- `GET /api/user/subjects/` → 200 `[{"id": 1, "name": "数学"}]`（名前の順・今と同じ）
- `PUT /api/user/subjects/`（本文 `{"subject_ids": [1, 2]}`）→ 200 `[{"id": 1, "name": "数学"}, {"id": 2, "name": "英語"}]`（保存の後の選んだ科目・名前の順）
- `GET /api/user/subjects/available/` → 200 `[{"id": 1, "name": "数学", "description": "…"}]`（組織の全科目・名前の順・ページ分けなし）

組織に属さない利用者（`organization_id` が None）の扱い（design-security-review で足した）: `Subject.organization` は空を許し、組織の無い「全体共有」の科目がある。`filter(organization_id=None)` はこの共有科目に当たるので、3 か所すべてで組織が無いときは先に打ち切る。シリアライザの `validate_subject_ids` は組織が無ければ照合せずに「選択された科目の一部が無効です」、サービスは何も書かずに戻る、`AvailableSubjectsView` は `Subject.objects.none()` を返す（`get_user_selected_subjects` の「組織に属さないユーザーは空」と同じ）。組織の条件は 3 か所とも `organization_id=user.organization_id` の完全一致だけで、共有科目（組織なし）は組織のある利用者にも出さない・選ばせない

応答（失敗）: 未認証 401。検証の失敗は 400 `{"error": {"main_message": "入力内容にエラーがあります", "sub_message": "<下の文言>", "details": {"subject_ids": ["<下の文言>"]}}}`。文言: 0 件・本文に無い →「科目を最低1つ選択してください」、他組織・存在しない番号 →「選択された科目の一部が無効です」、201 件以上 →「選べる科目の数を超えています」

### 4-2. 画面の取得・保存
| ファイル | 変更 |
|---|---|
| `frontend/src/types/api/index.ts` | `UserSubject`・`AvailableSubject`・`UserSubjectSelection` の短い名前を足す |
| `frontend/src/services/subjectService.ts` | `getAvailableSubjects(): Promise<AvailableSubject[]>`（`GET /api/user/subjects/available/`・`getUserSubjects` と同じく失敗は `Error` に包む）。`updateUserSubjects(subjectIds: number[]): Promise<UserSubject[]>`（`PUT /api/user/subjects/`・本文 `{ subject_ids }`。失敗は包まずに投げ直す〔画面が 400 と `sub_message` を読むため〕） |
| `frontend/src/hooks/useAvailableSubjects.ts`（新規） | `availableSubjectsKey = (userId) => ['available-subjects', userId]`。`useAvailableSubjects(userId, { enabled })` は `useUserSubjects` と同じ 3 つの状態（`loading`・`error`・`success`）と `retry` を返す |
| `frontend/src/hooks/useUserSubjects.ts` | `useSaveUserSubjects(userId)` を足す（`useMutation`。`onSuccess(data)`: `await queryClient.cancelQueries({ queryKey: userSubjectsKey(userId) })` → `setQueryData(userSubjectsKey(userId), data)`（I487 F7・F10 と同じ手順）→ `invalidateQueries({ queryKey: ['dashboard'] })`（おすすめが選んだ科目で変わる）。`onError`: 400 なら `invalidateQueries({ queryKey: availableSubjectsKey(userId) })`（組織の科目が変わった場合に一覧を取り直す）） |

### 4-3. 設定画面の「学ぶ科目」のカード
修正方針: 設定画面（614 行）を大きくしないよう、カードを独立した部品にし、設定画面は置くだけにする。チェックの状態は画面の中だけの一時的な状態（`useState`）、取得と保存は React Query。

| ファイル | 変更 |
|---|---|
| `frontend/src/components/settings/LearningSubjectsCard.tsx`（新規） | 下の表示。`id="learning-subjects"` を `Card` に付け、`useLocation().hash === '#learning-subjects'` で取得が済んだら見出しへ `scrollIntoView({ block: 'start' })`・`focus()`（見出しに `tabIndex={-1}`） |
| `frontend/src/pages/Settings.tsx` | 「アカウント情報」「学習設定」の次の行に `<Grid item xs={12}><LearningSubjectsCard /></Grid>` を置く（「表示設定」「通知設定」はその下） |

カードの表示（上から）:
- 見出し「学ぶ科目」（`h6`・`component="h2"`）、説明「ダッシュボード・クイズ・学習統計に出す科目です。最低1つ選んでください」（`body2`・`text.secondary`）
- 読み込み中: `CircularProgress`（`aria-label="学ぶ科目を読み込み中"`）。組織の科目・選んだ科目のどちらかが読み込み中なら出す
- 読み込みの失敗: 「科目を読み込めませんでした」と「再読み込み」（失敗したほうを取り直す）
- 組織の科目が 0 件: `Alert severity="info"`「この組織には選べる科目がありません。組織の管理者に科目の登録を依頼してください」（保存ボタンは出さない）
- 科目の一覧: 組織の科目ごとに `FormControlLabel` + `Checkbox`（ラベルは科目名、説明があれば下に `body2` で）。初めの状態は選んだ科目の番号（組織の科目にあるものだけ）
- 0 件のとき: 「科目を最低1つ選択してください」（`FormHelperText error`）
- 「学ぶ科目を保存」（`Save` のアイコン・`variant="contained"`）: 0 件・初めの状態から変わっていない・保存中は押せない。保存中は `CircularProgress size={20}`
- 保存の成功: toast「学ぶ科目を保存しました」。初めの状態を保存の応答に合わせる
- 保存の失敗: カードの中に `Alert severity="error" role="alert"`。400 で `error.sub_message` が文字列ならその文、それ以外は「学ぶ科目を保存できませんでした。時間をおいてもう一度お試しください」。チェックの状態は残す。次に保存を押すかチェックを変えたら消す

### 4-4. ダッシュボードの科目 0 件の案内
| ファイル | 変更 |
|---|---|
| `frontend/src/pages/Dashboard.tsx` | `const noSelected = subjects.state.status === 'success' && subjects.state.subjects.length === 0`。`const available = useAvailableSubjects(userId, { enabled: noSelected })` を足し、`StartQuizCard` に `availableSubjects={available.state}`・`onRetryAvailable={available.retry}` を渡す |
| `frontend/src/components/dashboard/StartQuizCard.tsx` | 選んだ科目が 0 件のときの案内を分ける。組織の科目が 1 件以上: `Alert severity="info" role="status"`「学ぶ科目がまだ選ばれていません。設定画面で学ぶ科目を選んでください」と、その下に `Button variant="outlined" component={RouterLink} to="/settings#learning-subjects"`「学ぶ科目を選ぶ」。組織の科目が 0 件: 今の「科目がまだ登録されていません。組織の管理者に科目の登録を依頼してください」。組織の科目の読み込み中: 案内を出さない（ボタンは今どおり押せない）。失敗: 「科目を読み込めませんでした」と「再読み込み」（今の選んだ科目の失敗と同じ形）。部品の先頭のコメントを直す |

### 4-5. テスト
| ファイル | 変更 |
|---|---|
| `backend/problems/tests/test_I494_user_subjects.py`（新規） | TC-01〜TC-11 |
| `backend/core/tests/test_I446_cross_api_tenant_isolation.py` | `MODELS` に `"UserSubjectAccess": UserSubjectAccess`。`ROUTE_TABLE` に `"PUT api/user/subjects/": [IdCheck("user", "body", "subject_ids", "subject", 400, list_param=True, writes=("count", "UserSubjectAccess"), own_status=200)]`・`"GET api/user/subjects/available/": LIST`（TC-12） |
| `frontend/src/components/settings/__tests__/LearningSubjectsCard.test.tsx`（新規） | TC-20〜TC-28 |
| `frontend/src/pages/__tests__/Settings.test.tsx` | `subjectService` をモックし（今のテストがカードの取得で実際の通信をしないように）、TC-29 を足す |
| `frontend/src/pages/__tests__/Dashboard.test.tsx` | `subjectService` のモックに `getAvailableSubjects` を足す。TC-05 を「組織の科目も 0 件」にし、TC-40〜TC-42 を足す |
| `e2e/tests/dashboard-layout.spec.ts` | TC-27 を新しい案内に直し、「学ぶ科目を選ぶ」で `/settings#learning-subjects` に移り「学ぶ科目」のカードが見えるところまで見る（保存はしない。`e2e_user_c` の 0 件を保つ） |

## 5. 実装手順（ステップ）
1. **裏側の API と境界（未知リスク先行: 契約の作り直しと横断テストの表）**: 4-1 と TC-01〜TC-12 を作り、スキーマと画面の型を作り直す（→ TC-01〜TC-12・TC-13）
2. **設定画面のカード**（ステップ 1 の後。画面の型を使う）: 4-2・4-3 と TC-20〜TC-29（→ TC-20〜TC-29）
3. **ダッシュボードの案内**（ステップ 2 の後。`useAvailableSubjects` を使う）: 4-4 と TC-05・TC-40〜TC-42・E2E TC-27（→ TC-05・TC-40〜TC-42・TC-27）
4. implement 段階の画面確認（`docs/runbooks/frontend-verify.md`）: 手動 No.1〜No.5 の下見（正式な記録は test-gate）
- セキュリティの制御（組織の境界・最低 1 件）は API と同じステップ 1 で入れる。サービスの再起動は不要（backend は開発サーバーの自動の読み込み直し・frontend は再読み込み）

## 6. テスト計画
### 自動（`docs/tests/open/I494_auto_test.md`）
- テストのレベル: API は pytest（DB を使う結合のテスト。キャッシュは LocMem に差し替えて実際に入る・消えるを見る）。テナント境界は横断テストの表（I446）にも載せる。画面は Jest（部品と画面の結合のテスト・サービスはモック）。ダッシュボードから設定画面への移動は E2E（既存の TC-27 を直す）
- 認可・テナント: 他組織・存在しない番号・組織の無い利用者（TC-03・TC-09・TC-12）
- 再発防止: キャッシュが保存の後に古い一覧を返さないこと（TC-05）・途中で失敗したら元のまま（TC-11）
- pytest・Jest・E2E は CI が PR ごとに流す（手元では流し直さない）。決定論ゲートは無し
### 手動（`docs/tests/open/I494_manual_test.md`・実施者はすべて Claude）
- Playwright MCP で、`e2e_user_c` のダッシュボードの案内 → 設定画面のカード → 保存 → ダッシュボードの反映、外す・0 件・失敗の表示、組織の科目 0 件の案内（通信の差し替え）を 1440・390 で見る。終わったら `seed_e2e` で `e2e_user_c` を 0 件に戻す

## 7. ロールバック
- PR を revert する（マイグレーション・依存の変更なし）。保存された割り当ては既存の `UserSubjectAccess` の行なので、revert 後もそのまま読める

## 8. Risk & 回避策
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: 他組織・全体共有の科目を割り当てられる（テナント越境） | シリアライザが組織の条件つきで件数を照合し、サービスも組織の条件で絞った番号だけを書く（二重）。組織の無い利用者は 3 か所とも先に打ち切る（`organization_id=None` の条件が共有科目に当たるのを防ぐ）。他組織・全体共有・存在しない番号で同じ応答（TC-03・TC-09・TC-12） | 回避 |
| R2: 保存の後もキャッシュが古い一覧を返す | 確定の後（`on_commit`）に両方のキーを消す。シグナルの消し方も残す（TC-05） | 回避 |
| R3: 同じ利用者の同時の保存で、行が混ざる・一意の制約で 500 になる | 利用者の行を `select_for_update` で順に並べ、`bulk_create(ignore_conflicts=True)` | 回避 |
| R4: 外した科目の学習統計・おすすめが見えなくなり、記録が消えたと思われる | 設計確認メモで「選んだ科目だけ出す」と決めた。カードの説明に「ダッシュボード・クイズ・学習統計に出す科目です」と書く。記録は消さない | 受け入れ |
| R5: 新しい経路を横断テストの表に載せ忘れる | 表に無い経路は既存の `test_route_table_matches_urlconf` が落とす。表に足す（TC-12） | 回避 |
| R6: 契約の作り直し忘れ | CI（`test_I493_openapi_contract.py`・`API Types Up To Date`）が止める（TC-13） | 回避 |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 置き場所は設定画面の中の「学ぶ科目」のカード。チェックボックスと「保存」。メニューは増やさない
- 最低 1 つは必須（画面は「科目を最低1つ選択してください」・API は 400）
- ダッシュボードの科目 0 件の案内は、組織に科目があれば「学ぶ科目を選ぶ」ボタンで設定画面のカードへ、無ければ今の「管理者に依頼」のまま
- 外した科目は今の作りのまま学習統計の科目別・おすすめに出なくなる（記録は消さない）
- 組織の境界は DB の条件で掛ける。キャッシュ（`user_subjects_cache_key`）が確実に消える。管理者も自分の分は同じカード。他人への割り当て・会員登録の変更は範囲外

Claude が決めた（技術的な選択と理由）:
- API は「選んだ一覧を丸ごと置き換える」`PUT /api/user/subjects/`（画面がチェックの全体を送る形と合い、足す・外すの 2 本より単純で冪等）。応答は `GET` と同じ形（画面が応答でキャッシュを書き換えられる）
- 組織の科目は新しい `GET /api/user/subjects/available/`（`/api/subjects/` はページ分け 20 件・問題数の集計つきで、選ぶ画面には合わない）
- 関数のビューをクラスのビューにする（dashboard の API と同じ形で `extend_schema` を付け、契約〔I493〕に入れる）。新しい 2 つの経路を契約に入れる（画面の型を手書きしない）
- 書き換えは `problems/services/user_subject_service.py`（規約 6 章のサービス。ビューは薄く）。確定の後にキャッシュを消す（シグナルはトランザクションの中で消すので、確定の前に古い値が入り直す隙がある）。シグナルは他の書き方（管理画面など）のために残す
- 番号の重複は 400 にせず 1 つにまとめる（画面は重複を送らない。害が無い）。上限 200（大きすぎる本文だけを断る。組織の科目の数より十分大きい）
- 他組織・存在しない番号は同じ文言「選択された科目の一部が無効です」（会員登録と同じ・番号の存在を漏らさない）
- 画面のカードは独立した部品（`components/settings/LearningSubjectsCard.tsx`）。チェックは `useState`、取得・保存は React Query（規約 6.3）。保存の応答で `['user-subjects', userId]` を書き換え（I487 F7・F10 の手順）、`['dashboard']` を古いことにする（おすすめが変わる）
- 文言（設計確認メモの決定から導いた）: カードの説明「ダッシュボード・クイズ・学習統計に出す科目です。最低1つ選んでください」・成功「学ぶ科目を保存しました」・失敗「学ぶ科目を保存できませんでした。時間をおいてもう一度お試しください」・組織の科目 0 件「この組織には選べる科目がありません。組織の管理者に科目の登録を依頼してください」・ダッシュボード「学ぶ科目がまだ選ばれていません。設定画面で学ぶ科目を選んでください」と「学ぶ科目を選ぶ」（ボタンの名前はメモのまま）
- 設定画面の中の位置: 「アカウント情報」「学習設定」の次の行に横幅いっぱい（grill-me で選んだ見本の配置）。`/settings#learning-subjects` で開いたらカードまで送り、見出しにフォーカスを移す（ダッシュボードから来た人が探さずに済む・キーボードでも続けられる）
- 科目を外すのに確かめのダイアログは出さない（記録は消えず、チェックを戻して保存すれば元に戻る・保存ボタンを押すまで書かない）
- ダッシュボードは選んだ科目が 0 件のときだけ組織の科目を読む（1 件以上の人に余計な通信をしない）
- 手動の確かめは `e2e_user_c`（組織 A・科目 0 件）。終わったら `docker compose run --rm --no-deps e2e-init` で作り直して 0 件に戻す（I513 のスパイクで、この形は承認なしで流せると確かめ済み）
- 一覧 docs/reviews/backlog/I223.md B1〜B4: 残す — ハーネスの行で、本イシューの変更点と関係が無い
- 一覧 docs/reviews/backlog/I224.md F9: 残す — 同上
- セキュリティ: 認証は `IsAuthenticated`、書けるのは本人の割り当てだけ（URL・本文に利用者の番号を取らない＝他人の割り当てを書けない・最小権限）。入力は整数の一覧だけ（`IntegerField(min_value=1)`・件数の上限）で、組織は `request.user.organization_id` から取り、本文から取らない。ORM だけ（生の SQL なし）。JWT の認証なので CSRF の影響なし。画面は React の文字の差し込みだけ（`dangerouslySetInnerHTML` なし・XSS なし）。個人情報・秘密の値は扱わない。依存の追加なし。bandit は MEDIUM 以上を直す・LOW は `# nosec` で理由つきで抑える、npm audit は high/critical を直す対象（依存の変更が無いので新しく出ない）
- P3/P5/P8 影響なし（DB の構造の変更・外部 API・非同期・新しいインフラ・依存の変更なし）
- P9 影響なし（新しい個人情報を集めない。組織の科目と本人の選択だけで、テナントの境界は R1 で守る）
- 性能・UX: 13 章
- 要件・UI/UX の仮定で決めたもの: 文言と、カードの中の細かい並び（設計確認メモの決定〔置き場所・ボタン・0 件の扱い〕から導いたもので、新しい価値判断は無い）

Danger Ops（有無/手順/ロールバック）:
- 無（利用者が自分の割り当ての行を足す・消すだけ。手動の確かめの後の `seed_e2e` は開発の DB の E2E 用の利用者の作り直しで、今の運用どおり）

## 13. 性能・UX設計
- 性能: `PUT` は読み 2 回（組織の照合・今の割り当て）と書き 2 回まで（削除・まとめての作成）。`available` は組織の科目の 1 回の読み取り（ページ分けなし。組織の科目は数十件の想定）。ダッシュボードは 0 件の人だけ 1 本多く読む
- 読み込み中・空・エラー: 4-3・4-4 のとおり（読み込み中は丸い表示、空は案内、失敗は「再読み込み」、保存の失敗はカードの中に残る表示）
- 破壊的な操作: 無し（外しても記録は消えない。保存ボタンを押すまで書かない）
- アクセシビリティ: チェックボックスは科目名のラベルつき。0 件の注意は `FormHelperText`、保存の失敗は `role="alert"`。ダッシュボードの導線はリンク（`RouterLink`）で、キーボードで移れる。移った先で見出しにフォーカス

## 14. 学習効果設計
- C1: 学びたい科目をいつでも選べ、科目が無くて学習を始められない状態をなくす。新しい測定は足さない

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | 他組織・存在しない科目の番号を含む `PUT` は 400 で、割り当てが 1 件も変わらず、2 つの応答が同じ（TC-03・TC-12。シリアライザの照合が `request.user.organization_id` を使い、本文から組織を取らないことを読む） |
| V2 | 1 | 読んで可 | サービスがシリアライザに依らず組織の条件で番号を絞ってから書く（TC-10b。サービスを直接、他組織・全体共有の番号で呼んで書かれない） |
| V5 | 1 | 読んで可 | 組織に属さない利用者が、全体共有の科目（`organization=None`）を選べず、`available` にも出ない（TC-09。3 か所とも組織が無ければ先に打ち切ることを読む）。組織のある利用者にも全体共有の科目を選ばせない（TC-03） |
| V3 | 2 | 読んで可 | キャッシュのテストが本当にキャッシュを通っている（TC-05。LocMem に差し替え、保存の前にキーに値が入っていることを確かめてから、保存の後の `GET` が新しい一覧を返す） |
| V4 | 3 | 読んで可 | 書き換えが 1 つのトランザクションで、途中の失敗で外した行が戻る（TC-11） |

## 計画変更記録
- fix-loop 2 回目（コードレビュー `docs/reviews/I494_code_review_20261116_1204.md` の F1・ユーザーとの相談で決めた直し・診断メモ `docs/reviews/I494_fix_diagnosis_20261116_1212.md`）。計画レビューのやり直し: 不要（受け入れ条件・方式・範囲は変えない。画面の見た目・文言も変えない）
  - F1: チェックの状態を、毎回いまの組織の科目の一覧と突き合わせる（400 の後に取り直して消えた科目を、見えないまま送り続けない）。TC-24b
  - 赤い注意「科目を最低1つ選択してください」は、一度触ってから 0 件にしたときだけ出す（触る前は説明文だけ。0 件では保存できない決まりは同じ）。TC-22b。4-3 の「0 件のとき」をこの形に読み替える
  - 設定画面の見出しの段をそろえる（見た目は変えない）: 「設定」= h1・各カード = h2・「ブラウザ通知の許可状況」= h3
  - 「学習設定」の form に見出しで名前を付け（`aria-labelledby`）、E2E `settings.spec.ts` は `getByRole('form', { name: '学習設定' })` の中の「保存」を押す（前の回の `exact: true` を置き換える。同じ画面にほかの保存のボタンが増えても壊れない・画面読み上げでも区別できる）。TC-29b
  - 見送り: 見出しのフォーカスの枠を消す案は、アプリの「フォーカス表示強化」（`AccessibilityProvider`・既定でオン・利用者が切り替えられる）が出している枠だったので取りやめた（利用者のアクセシビリティの設定を、このカードだけ打ち消さない）
  - 範囲の外（retro で別のイシュー）: 「学習設定」の「保存」が、表示設定・通知設定のカードの項目もまとめて保存している（ボタンの場所と保存の範囲が合っていない）
- implement での細部の変更（計画レビューのやり直し: 不要。方式・範囲・受け入れ条件は変えない）:
  - 計画書の記載:「組織が無ければ 3 か所で先に打ち切る」→ 採った方法: 既存の `problems.services.tenant_scope.available_subjects(user)`（組織なしは空・全体共有の科目を含めない）を 3 か所で使う。理由: 同じ境界の判定を写さず 1 か所に保つ
  - 計画書の記載: カードの「保存」→ 採った方法: ボタンの名前を「学ぶ科目を保存」にする。理由: 同じ設定画面の「学習設定」に「保存」があり、画面読み上げ・テストで区別できないため
  - 計画書の記載: 見出しへ `scrollIntoView`・`focus()` → 採った方法: 見出しに `scrollMarginTop`（`theme.spacing(11)`）を付け、`focus({ preventScroll: true })` にする。理由: 画面確認で、固定のアプリのバーの下に見出しが隠れたため
  - /simplify（4 体）の取り込み: シグナルの受け手も「今すぐ消し、確定の後にもう一度消す」（`invalidate_user_subjects_cache_now_and_on_commit`）にし、サービスは `bulk_create` のときだけそれを呼ぶ（確定の前に古い値が入り直す隙を、管理画面・seed などほかの書き手でも塞ぐ。今すぐ消すのは残す＝同じトランザクションの中で読み直す既存の I473 TC-16 の前提を変えない）。3 の「変えないもの」の `signals.py` はこの変更だけ例外。画面は、`useAvailableSubjects` を既存の `toLoadState` で作る・読み込み失敗の行を `components/SubjectsRetryRow.tsx` に共通化・保存の失敗の文言を既存の `extractApiErrorMessage` で取る・overview のキーの頭を `DASHBOARD_OVERVIEW_KEY_ROOT` として `useDashboardOverview.ts` から出す。見送り: 保存の応答のための読み直し（1 クエリ。応答の正を読み取りの関数 1 つに保つ）・削除のシグナルが行ごとに利用者を読む（外す数は組織の科目の数まで）・固定のバーの余白を画面全体の `scroll-padding-top` にする（送る先は今これ 1 か所）・送り先の定数の置き場・会員登録と文言の定数の共通化
  - TC-05 の保存を「足すだけ」（`[数学, 物理]`）にした。理由: 外す操作は削除のシグナルでもキャッシュが消えるので、確定の後の消去を抜いても合格してしまう（失敗の注入で、足すだけなら落ちることを確かめた）
- 計画レビュー（`docs/reviews/I494_plan_review_20261116_1134.md`）の Info（追跡用のログ）への対応: サービスで書き換えの後に `user_id`・`organization_id`・足した数・外した数を `logger.info` に出す（4-1）。Warning 2 件は直す所なし（置き換える関数の参照元は `backend/problems/urls.py` だけと確かめ済み／他組織と存在しない番号の応答は同じクエリ 1 回で区別なし）。計画レビューのやり直し: 不要（findings への対応の追記だけ。方式・範囲・受け入れ条件は変えない）
- design-security-review の High（組織に属さない利用者の条件が全体共有の科目に当たる）への対応: 3 か所で組織が無ければ先に打ち切る（4-1）・TC-03・TC-08・TC-09・TC-10b に共有科目を足す・V5 を足す。計画レビューのやり直し: 不要（守りの条件とテストの追記だけ。方式・範囲・受け入れ条件は変えない）

## レビュー結果
- [20261116_1134 判定: ✅ 完了](../../reviews/I494_plan_review_20261116_1134.md)

## セキュリティレビュー結果

**実施日**: 2026-11-16

### セキュリティ設計レビュー

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| High（計画で解消済み） | マルチテナント | `Subject.organization` は空を許し、組織の無い全体共有の科目がある。組織に属さない利用者で `filter(organization_id=user.organization_id)` を組むと `organization_id=None` になり、共有科目を選べる・`available` に出る | 組織が無ければシリアライザ・サービス・`AvailableSubjectsView` の 3 か所で先に打ち切る（4-1 に追記）。TC-03・TC-08・TC-09・TC-10b に共有科目を入れた。V5 |
| Low | 認証・認可 | 本人の割り当てだけを書く。URL・本文に利用者の番号を取らないので他人の割り当てを書けない（IDOR なし）。管理者も自分の分だけ | `IsAuthenticated` のみで十分。利用者の番号を受け取る形にしない |
| Low | 入力検証 | 整数の一覧だけを受ける。巨大な本文・負の番号 | `IntegerField(min_value=1)`・`max_length=200`・`min_length=1`。重複は 1 つにまとめる |
| Low | 機密情報 | ログに科目の番号・名前を出すと利用者の学習内容が残る | ログは `user_id`・`organization_id`・足した数・外した数だけ |
| Low | OWASP Top 10 | 400 の `sub_message` を画面に出す（XSS） | React の文字の差し込みだけ（`dangerouslySetInnerHTML` なし）。ORM だけ（SQLi なし）。JWT の認証で CSRF の影響なし |
| なし | ファイル操作 | なし | — |
| なし | 外部通信 | なし | — |
| なし | 依存ライブラリ | 追加なし | — |

### 攻撃シナリオレビュー

| # | 入口 | 想定権限 | 想定操作 | 守るべき条件 | 自動テスト化対象 | 手動確認対象 | 残余リスク | 重大度 |
|---|------|---------|---------|------------|----------------|------------|---------|--------|
| 1 | `PUT /api/user/subjects/` | 一般 | 他組織の科目の番号を送り、他組織の問題・おすすめを見る足がかりにする | 400・割り当てが変わらない・存在しない番号と同じ応答 | Yes: TC-03・TC-12 | No | なし | High |
| 2 | `PUT /api/user/subjects/` | 一般（組織なし） | 全体共有の科目の番号を送る | 400・行 0 件 | Yes: TC-09 | No | なし | High |
| 3 | `GET /api/user/subjects/available/` | 一般（組織なし・組織あり） | 他組織・全体共有の科目の一覧を得る | 自組織の科目だけ（組織なしは `[]`） | Yes: TC-08・TC-09・TC-12 | No | なし | Medium |
| 4 | `PUT /api/user/subjects/` | 未認証 | 割り当てを書く | 401 | Yes: TC-07 | No | なし | Medium |
| 5 | `PUT /api/user/subjects/` | 一般 | 番号を大量に送る・同時に何度も送る | 201 件以上は 400。同時の保存は順に並び 500 にならない | Yes: TC-04（件数）。同時は No（`select_for_update` と `ignore_conflicts` を読んで確かめる） | No | 同時の保存の実測はしない（読んで確かめる） | Low |
| 6 | 設定画面のカード | 一般 | 応答の文字に HTML を混ぜる | 文字として出る | No（React の既定） | No | なし | Low |

### レビュー結果サマリー

| 重大度 | 設計レビュー | シナリオ |
|--------|------------|---------|
| Blocker | 0件 | 0件 |
| High    | 1件（計画で解消済み） | 2件（防御条件を計画に含む） |
| Medium  | 0件 | 2件 |
| Low     | 4件 | 2件 |

### 残余リスク処遇
- シナリオ 5（同じ利用者の同時の保存）の実測はしない: 受け入れ — `select_for_update` で順に並べ、`bulk_create(ignore_conflicts=True)` で一意の制約の 500 を避けることを、コードレビュー・敵対的レビューが読んで確かめた（Low）
- High（組織の無い利用者と全体共有の科目）: 計画で解消済み（TC-03・TC-09・TC-10b・V5。敵対的レビューで確認済み）
- 検証と保存の間の削除・前の組織の割り当ての扱い（台帳 F2・F3・Low）: #532 へ
