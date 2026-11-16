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
| TC-20b | 表示（触る前と、「数学」を外して 0 件にした後） | `getByRole('group', { name: '学ぶ科目' })` の中にチェックボックス 3 つ。説明は「ダッシュボード・クイズ・学習統計に出す科目です。最低1つ選んでください」、0 件にした後は注意「科目を最低1つ選択してください」も続く（`aria-labelledby` を外すと落ちることを確かめた） |
| TC-21 | 「英語」をチェックして「学ぶ科目を保存」。`updateUserSubjects` は `[{id:2,name:'英語'},{id:1,name:'数学'}]` を返す | `updateUserSubjects` が `[1, 2]` で 1 回呼ばれる・toast.success が「学ぶ科目を保存しました」・`queryClient.getQueryData(['user-subjects', userId])` が応答と同じ・`['dashboard']` で始まるキーが invalidate される・保存の後「学ぶ科目を保存」が disabled |
| TC-22 | 「数学」を外して 0 件 | 「科目を最低1つ選択してください」が出る・「学ぶ科目を保存」が disabled・`updateUserSubjects` は呼ばれない |
| TC-23 | `updateUserSubjects` が 500 の axios のエラーで失敗 | `role="alert"` に「学ぶ科目を保存できませんでした。時間をおいてもう一度お試しください」・「英語」は checked のまま |
| TC-24 | `updateUserSubjects` が 400・`response.data.error.sub_message = '選択された科目の一部が無効です'` で失敗 | `role="alert"` に「選択された科目の一部が無効です」・`getAvailableSubjects` が取り直される（2 回目の呼び出し）。その後チェックを変えると alert が消える |
| TC-24b | 「物理」にチェック → 保存が 400 → 取り直した組織の科目から「物理」が消える → 「英語」にチェックして保存 | 「物理」の行が消え、2 回目の `updateUserSubjects` は `[1, 2]`（消えた 3 を送らない）・成功の toast（F1。突き合わせを外すと `[1, 3, 2]` で落ちることを確かめた） |
| TC-22b | 選んだ科目 0 件で開く（何も触らない） | 「科目を最低1つ選択してください」が出ない・「学ぶ科目を保存」は disabled |
| TC-25 | 組織の科目 `[]` | 「この組織には選べる科目がありません。組織の管理者に科目の登録を依頼してください」・「学ぶ科目を保存」ボタンが無い |
| TC-26 | `getAvailableSubjects` が失敗 | 「科目を読み込めませんでした」・「再読み込み」を押すと `getAvailableSubjects` がもう一度呼ばれる |
| TC-27 | 選んだ科目に組織に無い番号（99）が混ざる | 3 つのチェックのうち「数学」だけ checked・「英語」を足して保存すると `[1, 2]`（99 を送らない） |
| TC-28 | `MemoryRouter initialEntries={['/settings#learning-subjects']}`・`Element.prototype.scrollIntoView` をモック | 一覧が出た後に `scrollIntoView` が呼ばれ、見出し「学ぶ科目」に focus がある |
| TC-28b | ハッシュなしで開く | `scrollIntoView` が呼ばれない |

## 設定画面（`frontend/src/pages/__tests__/Settings.test.tsx`）
| TC | 内容 | 期待値 |
|---|---|---|
| TC-29 | 設定画面を表示（`subjectService` をモック） | 見出し「学ぶ科目」が出る。既存の設定画面のテストがすべて通る |
| TC-29b | 設定画面を表示 | `getByRole('form', { name: '学習設定' })` の中に「保存」があり、「学ぶ科目を保存」は無い。見出し「設定」が level 1、「アカウント情報」「学習設定」「学ぶ科目」「表示設定」「通知設定」が level 2 |

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

## 再発防止記録（fix-loop・2026-11-16）
- なぜ失敗したか: CI の E2E `settings.spec.ts` の TC-28 が `getByRole('button', { name: '保存' })` で「学習設定」の保存ボタンを探していた。Playwright の `name` は文字列だと既定で部分一致なので、I494 で同じ画面に足した「学ぶ科目を保存」にも当たり、strict mode で 2 つに当たって落ちた（画面の不具合ではない）
- 何を変えたか: `e2e/tests/settings.spec.ts:19` を `{ name: '保存', exact: true }` にした（診断メモ `docs/reviews/I494_fix_diagnosis_20261116_1202.md`・案 A）
- セキュリティ上の考慮点: なし（テストの探し方だけ）
- 次回どう防ぐか: 画面に、既存のボタン・見出しの名前を含む新しい要素を足すときは、E2E（Playwright・既定は部分一致）の `getByRole(..., { name })` を `grep -rn "name: '<名前>'" e2e/tests` で探し、部分一致で当たるものを `exact: true` にする。Jest（Testing Library・文字列は既定で完全一致）の結果だけで E2E も通ると見なさない
- 確かめた結果: `grep -rn "name: '保存'" e2e/tests frontend/src` で、部分一致の探し方は `settings.spec.ts:19` だけ（Jest の 3 か所は完全一致）。E2E の実行は CI で確かめる（手元では流し直さない）

## 再発防止記録（fix-loop 2 回目・2026-11-16）
- なぜ失敗したか: (F1) チェックの状態（`checked`）を組織の科目の一覧と突き合わせずに使っていたので、保存の 400 の後に一覧を取り直すと、消えた科目の番号が見えないまま残り、保存が毎回 400 になった。(E2E) 前の回の `exact: true` は名前の偶然に頼る直しで、画面に「どのまとまりの保存か」を示す名前が無いことが根にあった
- 何を変えたか: 選択を毎回一覧と突き合わせる（TC-24b）。触る前は赤い注意を出さない（TC-22b）。「学習設定」の form に名前を付け、E2E はその中の「保存」を押す。設定画面の見出しの段を h1・h2・h3 にそろえた（TC-29b）
- セキュリティ上の考慮点: F1 は裏側が 400 で断っていた（組織の境界は保たれていた）。今回の直しは表示とテストだけ
- 次回どう防ぐか: 取り直しで変わる一覧に対して手元の選択の状態を持つときは、表示・送信の前に一覧と突き合わせる（状態は一覧から導く）。同じ画面に同じ働きのボタンを足すときは、まとまり（form）に名前を付け、テストはまとまりの中で探す
- 確かめた結果: Jest の `Settings.test.tsx`・`LearningSubjectsCard.test.tsx`・`Dashboard.test.tsx` 57 passed。TC-24b は突き合わせを外すと落ちることを確かめた。ESLint・`tsc --noEmit` 通過。Playwright MCP で、`/settings#learning-subjects` の画面で `getByRole('form', { name: '学習設定' })` の中の「保存」に当たること・触る前に赤い注意が出ないことを確かめた（`.evidence/I494/settings-c-5.png`）。E2E は CI で確かめる

## 実行記録（test-gate・2026-11-16）
- `bash scripts/claude/gate-check.sh I494` → exit 0（`GATE_CHECK: OK`。コードレビュー `I494_code_review_20261116_1216.md`・敵対的レビュー `I494_adversarial_review_20261116_1224.md` とも OK）
- pytest・Jest・E2E: PR #529 の CI で成功（review-gate の `CI_WAIT: OK`。手元では流し直さない）。決定論ゲートは無し

## 再発防止記録（fix-loop 3 回目・2026-11-16）
- なぜ見落としたか: 計画の 13 章（アクセシビリティ）が、個々のチェックボックスのラベルと注意の出し方までしか書いておらず、まとまりの名前（グループ）を決めていなかった。送り先の目印は、置き場（`constants/`）が無かったので送り先の部品の中に置いた
- 何を変えたか: チェックボックスのまとまりに見出しを名前として結び付け、説明と注意も結び付けた（TC-20b）。送り先を `frontend/src/constants/routes.ts` に移した
- セキュリティ上の考慮点: なし（表示とモジュールの置き場だけ）
- 次回どう防ぐか: 選択肢のまとまり（チェックボックス・ラジオ）を足すときは、見える見出しをグループの名前に結び付ける。画面をまたぐ道筋・目印は `constants/` に置く
- 確かめた結果: Jest の `LearningSubjectsCard.test.tsx` 13 passed・`Settings.test.tsx`・`Dashboard.test.tsx` も通過（計 58）。TC-20b は `aria-labelledby` を外すと落ちることを確かめた。ESLint・`tsc --noEmit` 通過。Playwright MCP で `/settings#learning-subjects` の「学ぶ科目」のグループを確かめた（`.evidence/I494/no1-settings-c-group.png`）
