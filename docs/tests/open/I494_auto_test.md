# I494 自動テスト: 学ぶ科目を後から選び直せるようにする

実行コマンド（例）: `docker compose exec backend pytest problems/tests/test_I494_user_subjects.py core/tests/test_I446_cross_api_tenant_isolation.py core/tests/test_I493_openapi_contract.py` / `docker compose exec frontend npm test -- --watchAll=false LearningSubjectsCard Settings Dashboard`（pytest・Jest・E2E は CI が PR ごとに流す。手元では流し直さない）

結果（implement 段階の手元の確認。正は CI）:
- backend: `test_I494_user_subjects.py` 12 passed・`test_I446_cross_api_tenant_isolation.py` の新しい行と経路の表 4 passed・`test_I493_openapi_contract.py` 11 passed。TC-05 は確定の後の消去を抜くと落ちることを確かめた（失敗の注入）
- frontend: `LearningSubjectsCard.test.tsx` 10 passed（TC-28b を足した）・`Settings.test.tsx` 4 passed・`Dashboard.test.tsx` 40 passed・`tsc --noEmit` 通過
- e2e: CI で確かめる

## 共通の準備（backend）
- 組織 A（科目 数学・英語・物理）・組織 B（科目 B数学）・組織の無い全体共有の科目「共有科目」（`organization=None`）を作る。利用者 `user_a`（組織 A・role user・数学を選んでいる）・`user_none`（組織なし）
- `client = APIClient(); client.force_authenticate(user_a)`
- 本文は `format='json'`

## API（`backend/problems/tests/test_I494_user_subjects.py`）
| TC | 内容 | 期待値 |
|---|---|---|
| TC-01 | `user_a` が `PUT /api/user/subjects/` 本文 `{"subject_ids": [数学, 英語]}` | 200・本文 `[{"id": 数学, "name": "数学"}, {"id": 英語, "name": "英語"}]`（名前の順。DB の並びで「数学」が先）・`UserSubjectAccess` の `user_a` の `subject_id` の集合が `{数学, 英語}`・英語の行の `granted_by` が `user_a` |
| TC-02 | `user_a`（数学・英語）が `{"subject_ids": [英語]}` | 200・本文 `[{"id": 英語, "name": "英語"}]`・集合が `{英語}` |
| TC-03 | `user_a`（数学）が `{"subject_ids": [数学, B数学]}`、`{"subject_ids": [数学, 共有科目]}`、`{"subject_ids": [数学, 4949999]}`（存在しない） | 3 つとも 400・`body["error"]["sub_message"] == "選択された科目の一部が無効です"`・`body["error"]["details"] == {"subject_ids": ["選択された科目の一部が無効です"]}`・3 つの本文が同じ・集合が `{数学}` のまま |
| TC-04 | `{"subject_ids": []}`、`{}`（キーなし） | どちらも 400・`body["error"]["details"]["subject_ids"] == ["科目を最低1つ選択してください"]`・集合が `{数学}` のまま。201 件の番号 → 400・`["選べる科目の数を超えています"]` |
| TC-05 | `override_settings(CACHES=LocMem)` で、`GET /api/user/subjects/` → キー `user_subjects_cache_key(user_a.id, A.id, False)` に値が入っていることを確かめる（正の対照）→ `subject_service.get_user_selected_subjects(user_a, annotate_count=True)` も一度読む → `PUT {"subject_ids": [数学, 物理]}`（足すだけ＝シグナルでは消えない形・`django_capture_on_commit_callbacks(execute=True)`）→ `GET` | 2 回目の `GET` が `[{"id": 数学, "name": "数学"}, {"id": 物理, "name": "物理"}]`・2 つのキー（`False`・`True`）がどちらも空 |
| TC-06 | `{"subject_ids": [英語, 英語]}` | 200・本文 `[{"id": 英語, "name": "英語"}]`・集合 `{英語}` |
| TC-07 | 未認証で `PUT /api/user/subjects/`・`GET /api/user/subjects/available/` | どちらも 401 |
| TC-08 | `user_a` が `GET /api/user/subjects/available/`。組織 A に科目を足して計 25 件にしてからも読む | 200・各要素のキーが `{"id", "name", "description"}`・組織 A の科目が名前の順で全件（25 件・ページ分けなし）・B数学・共有科目を含まない |
| TC-09 | `user_none` が `PUT {"subject_ids": [数学]}`・`PUT {"subject_ids": [共有科目]}`・`GET .../available/`。サービスを直接 `replace_user_subjects(user=user_none, subject_ids=[共有科目])` | `PUT` はどちらも 400・`sub_message == "選択された科目の一部が無効です"`・`user_none` の行 0 件（サービスを直接呼んでも 0 件）。`available` は 200・`[]`（共有科目が出ない） |
| TC-10 | `user_a`（数学）が `{"subject_ids": [数学]}` を 2 回 | どちらも 200・`[{"id": 数学, "name": "数学"}]`・数学の行の `pk` と `granted_at` が前と同じ（触っていない） |
| TC-10b | サービスを直接 `replace_user_subjects(user=user_a, subject_ids=[英語, B数学, 共有科目])` | 例外なし・集合が `{英語}`（B数学・共有科目は書かれない・数学は外れる） |
| TC-11 | `mock.patch.object(UserSubjectAccess.objects, 'bulk_create', side_effect=RuntimeError)` の中で `replace_user_subjects(user=user_a, subject_ids=[英語])` | `RuntimeError`・集合が `{数学}` のまま（外した行が戻る） |

## テナント境界の横断（`backend/core/tests/test_I446_cross_api_tenant_isolation.py`）
| TC | 内容 | 期待値 |
|---|---|---|
| TC-12 | 表に `"PUT api/user/subjects/"`（`IdCheck` 本文 `subject_ids` の一覧・400・`writes=("count", "UserSubjectAccess")`・`own_status=200`）と `"GET api/user/subjects/available/": LIST` を足す | `test_id_check`: 他組織・全体共有の科目の番号が、存在しない番号と同じ 400 の本文で、`UserSubjectAccess` の件数が変わらない。自組織の科目なら 200。`test_list_check`: 他組織の中身が出ない。`test_route_table_matches_urlconf` が通る（表と経路が一致） |

## API の契約
| TC | 内容 | 期待値 |
|---|---|---|
| TC-13 | 既存の `core/tests/test_I493_openapi_contract.py` と CI の `API Types Up To Date` | `backend/openapi.yaml` に `/api/user/subjects/`（get・put）と `/api/user/subjects/available/`（get）があり、作り直したものと同じ。`schema.d.ts` も同じ |

## 設定画面のカード（`frontend/src/components/settings/__tests__/LearningSubjectsCard.test.tsx`）
準備: `subjectService` をモック。組織の科目 `[{id:1,name:'数学'},{id:2,name:'英語',description:'英文法'},{id:3,name:'物理'}]`・選んだ科目 `[{id:1,name:'数学'}]`。`QueryClientProvider`・`MemoryRouter` で包む。

| TC | 内容 | 期待値 |
|---|---|---|
| TC-20 | 表示 | 見出し「学ぶ科目」・「ダッシュボード・クイズ・学習統計に出す科目です。最低1つ選んでください」。チェックボックス「数学」が checked、「英語」「物理」が not checked。「英文法」が出る。「学ぶ科目を保存」が disabled（変わっていない） |
| TC-21 | 「英語」をチェックして「学ぶ科目を保存」。`updateUserSubjects` は `[{id:2,name:'英語'},{id:1,name:'数学'}]` を返す | `updateUserSubjects` が `[1, 2]` で 1 回呼ばれる・toast.success が「学ぶ科目を保存しました」・`queryClient.getQueryData(['user-subjects', userId])` が応答と同じ・`['dashboard']` で始まるキーが invalidate される・保存の後「学ぶ科目を保存」が disabled |
| TC-22 | 「数学」を外して 0 件 | 「科目を最低1つ選択してください」が出る・「学ぶ科目を保存」が disabled・`updateUserSubjects` は呼ばれない |
| TC-23 | `updateUserSubjects` が 500 の axios のエラーで失敗 | `role="alert"` に「学ぶ科目を保存できませんでした。時間をおいてもう一度お試しください」・「英語」は checked のまま |
| TC-24 | `updateUserSubjects` が 400・`response.data.error.sub_message = '選択された科目の一部が無効です'` で失敗 | `role="alert"` に「選択された科目の一部が無効です」・`getAvailableSubjects` が取り直される（2 回目の呼び出し）。その後チェックを変えると alert が消える |
| TC-25 | 組織の科目 `[]` | 「この組織には選べる科目がありません。組織の管理者に科目の登録を依頼してください」・「学ぶ科目を保存」ボタンが無い |
| TC-26 | `getAvailableSubjects` が失敗 | 「科目を読み込めませんでした」・「再読み込み」を押すと `getAvailableSubjects` がもう一度呼ばれる |
| TC-27 | 選んだ科目に組織に無い番号（99）が混ざる | 3 つのチェックのうち「数学」だけ checked・「英語」を足して保存すると `[1, 2]`（99 を送らない） |
| TC-28 | `MemoryRouter initialEntries={['/settings#learning-subjects']}`・`Element.prototype.scrollIntoView` をモック | 一覧が出た後に `scrollIntoView` が呼ばれ、見出し「学ぶ科目」に focus がある |
| TC-28b | ハッシュなしで開く | `scrollIntoView` が呼ばれない |

## 設定画面（`frontend/src/pages/__tests__/Settings.test.tsx`）
| TC | 内容 | 期待値 |
|---|---|---|
| TC-29 | 設定画面を表示（`subjectService` をモック） | 見出し「学ぶ科目」が出る。既存の設定画面のテストがすべて通る |

## ダッシュボード（`frontend/src/pages/__tests__/Dashboard.test.tsx`）
| TC | 内容 | 期待値 |
|---|---|---|
| TC-05（直す） | 選んだ科目 0 件・組織の科目 0 件 | 「科目がまだ登録されていません。組織の管理者に科目の登録を依頼してください」・「学ぶ科目を選ぶ」が無い・「クイズを始める」が disabled |
| TC-40 | 選んだ科目 0 件・組織の科目 `[{id:1,name:'数学'}]` | 「学ぶ科目がまだ選ばれていません。設定画面で学ぶ科目を選んでください」・リンク「学ぶ科目を選ぶ」の `href` が `/settings#learning-subjects`・「組織の管理者に科目の登録を依頼してください」が無い・「クイズを始める」が disabled |
| TC-41 | 選んだ科目 0 件・`getAvailableSubjects` が失敗 | 「科目を読み込めませんでした」と「再読み込み」・押すと `getAvailableSubjects` がもう一度呼ばれる |
| TC-42 | 選んだ科目 1 件以上 | `getAvailableSubjects` が呼ばれない |

## E2E（`e2e/tests/dashboard-layout.spec.ts`）
| TC | 内容 | 期待値 |
|---|---|---|
| TC-27（直す） | `e2e_user_c`（組織 A・科目 0 件）で `/dashboard` | 「学ぶ科目がまだ選ばれていません。設定画面で学ぶ科目を選んでください」が見える・「クイズを始める」が disabled・「組織の管理者に科目の登録を依頼してください」が 0 件。「学ぶ科目を選ぶ」を押すと URL が `/settings#learning-subjects` で、見出し「学ぶ科目」が見える（保存はしない） |

## 決定論ゲート（自動実走）
- 無し（守る決まりは pytest・Jest・E2E が CI で確かめる。文言・ファイルの有無を grep で見るゲートは作らない＝plan-writing-rules.md「決定論テストの対象の選び方」）
