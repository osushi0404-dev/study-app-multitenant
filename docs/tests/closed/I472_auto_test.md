# I472 自動テスト: 解説画像がある問題へのクイズの回答の 500 を直し、新しい形式の解説画像と問題の画像もクイズで表示する

- 関連: docs/issues/open/I472.md / docs/plans/open/plan_I472.md / GitHub #472 / Draft PR #474
- 対象: `backend/problems/tests/test_I472_quiz_answer_explanation_image.py`（新規）・`frontend/src/utils/__tests__/problemImages.test.ts`（新規）・`frontend/src/components/__tests__/ProblemImageList.test.tsx`（新規）・`frontend/src/components/__tests__/ProblemPreview.test.tsx`（新規）・`frontend/src/pages/__tests__/QuizSession.test.tsx`（追記）と、守りにする既存のテスト
- 実行場所: app-1 ワークツリーのコンテナ（`docker compose exec -T backend ...`・`docker compose exec -T frontend ...`）。全テストは CI（PR #474）が正。手元では下の TC のファイルだけを流す
- 合否は終了コード（合格=0・不合格=非ゼロ）。回帰を止める TC は失敗の注入（FG）で非ゼロになることを確かめる
- 下の表の `PYT` は `docker compose exec -T backend python -m pytest problems/tests/test_I472_quiz_answer_explanation_image.py -q`、`JEST` は `docker compose exec -T frontend npx react-scripts test --watchAll=false` の略

結果:
- backend: 新しいテスト 6 件と守りのテスト（I166・I158・problems の serializers・views・I073・I452・#446）が 236 passed。Red（直す前の 500・500 なのに回答が残る）と FG（応答の組み立てを外に戻すと TC-04 が 2 件とも FAIL）を確かめた。CI は review-gate で確かめる
- frontend: 新しい 3 ファイルと追記を含むクイズの画面の 3 ファイルが 34 passed。Red と FG（解説画像の選び方を古い形式だけに戻すと 3 件 FAIL）を確かめた。型チェック・lint（警告 0）も合格

## 決定論ゲート（自動実走）
決定論ゲート（grep などの文字の確かめ）は置かない。守る決まり（URL の作り方・トランザクションの範囲・画面の選び方）は、動きを確かめる pytest・Jest（TC-01〜TC-10）が CI で毎回止める。

## 実行記録
| 日時 | コマンド | 終了コード | 結果 |
|---|---|---|---|
| 2026-11-12 | TC-06（実装前・ベースライン） | 0 | 230 passed（develop `616f003b` 相当・I472 の変更なし） |
| 2026-11-12 | TC-01〜TC-05・TC-07〜TC-13（実装前） | — | 実装前のため未実行 |
| 2026-11-12 16:02 | Red: `PYT`（serializer も無い状態） | 2 | `AnswerExplanationSerializer` の読み込みで収集エラー |
| 2026-11-12 16:03 | Red: `PYT`（serializer だけ足し、view は直す前） | 1 | 5 failed・1 passed。TC-01 は 500（`AttributeError: 'str' object has no attribute 'url'`・`views.py:988`）、TC-04 (b) は 500 なのに QuizAnswer が 1 件残る。通った 1 件は TC-05（serializer だけで決まる） |
| 2026-11-12 16:03 | Green: `PYT` | 0 | 6 passed |
| 2026-11-12 16:04 | FG: 応答の組み立て（`result = {...}`）を `with transaction.atomic():` の外に戻して `PYT -k build_failure` | 1 | 2 failed（どちらも QuizAnswer が 1 件残る）。直した版に戻した |
| 2026-11-12 16:05 | TC-06（初回） | 1 | I452 の `test_submit_answer_updates_card` が応答のキーの集合に `explanation_images` が無いことで FAIL（計画変更記録）。期待するキーを足して 236 passed |
| 2026-11-12 16:09 | TC-10（切り出す前のプレビュー） | 0 | 4 passed（今の見え方をテストで固定してから切り出した） |
| 2026-11-12 16:10 | Red: TC-07・TC-08（関数・部品が無い状態） | 1 | 2 suites が読み込みで FAIL |
| 2026-11-12 16:11 | Green: TC-07・TC-08・TC-10 | 0 | 3 suites・14 passed |
| 2026-11-12 16:12 | Red: TC-09（クイズの画面を直す前） | 1 | 6 failed・8 passed（既存の 7 件と「問題画像が無ければ出さない」） |
| 2026-11-12 16:13 | Green: TC-09・TC-11（Jest 6 ファイル・型チェック・lint） | 0 | 34 passed・`tsc --noEmit` 合格・`eslint --max-warnings 0` 合格 |
| 2026-11-12 16:13 | FG: `QuizSession.tsx` の解説画像を `pickImageUrls(undefined, result.explanation_image)` に一時的に変えて TC-09 | 1 | 3 failed（新しい形式の解説画像・解説文なし・拡大）。戻した |
| 2026-11-12 16:25 | TC-13（/simplify の後）: TC-06・Jest 6 ファイル・型チェック・lint | 0 | 236 passed・34 passed・型チェックと lint 合格 |
| 2026-11-12 16:23 | review-gate: `bash scripts/claude/code-review.sh I472`（CI 待ちを含む） | 0 | `CI_WAIT: OK`・`FINAL_VERDICT: OK`（Low 4 件）・`ADVERSARIAL_STAGE: NOT_REQUIRED` |
| 2026-11-12 16:34 | TC-12: `gh pr checks 474`（`b63ddcdb`） | 0 | 7 ジョブすべて pass（Backend Tests・Frontend Tests・E2E Tests・型チェック・lint と検査 2 つ・Harness Tests） |

## TC 一覧

| TC | 内容 | コマンド | 期待値 | 対応 AC |
|---|---|---|---|---|
| TC-01 | `test_legacy_explanation_image_returns_200`: 組織 A（slug `org-i472-a`）の科目（slug `subj-i472`）の問題に `explanation_image='sample.png'` を入れ、回を始めて `POST /api/quiz/<id>/submit_answer/` で正解を送る | `PYT -k legacy_explanation_image` | exit 0。応答 200・`is_correct` が `true`・`explanation_image` が `"/media/org/org-i472-a/subjects/subj-i472/explanation/sample.png"`（`problem.get_explanation_image_url()` と同じ）・`explanation_images` が `[]`。QuizAnswer が 1 件・回の `completed_problems` が 1。FG（Red）: 直す前のコード（`views.py:988` の `.url`）では 500（`AttributeError`）で exit 非ゼロ | AC1 |
| TC-02 | `test_new_format_explanation_images`: 同じ問題に、解説用の MediaAsset 2 枚（`position` 2 → 1 の順に作る）・問題用 1 枚を紐づけ、`explanation_image='legacy.png'` も入れて回答する | `PYT -k new_format_explanation_images` | exit 0。応答 200。`explanation_images` は解説用の 2 枚だけで `position` 1・2 の順。各要素のキーは `id`・`url`・`usage_kind`・`original_filename`・`mime_type`・`file_size_bytes`・`created_at`、`url` は `"/media/<storage_key>"`、`usage_kind` は `"explanation"`。`explanation_image` は `"/media/org/org-i472-a/subjects/subj-i472/explanation/legacy.png"` | AC3 |
| TC-03 | `test_response_keys_without_images`: 画像の無い問題に回答する | `PYT -k response_keys_without_images` | exit 0。応答 200・`explanation_image` が `null`・`explanation_images` が `[]`・`explanation` が問題の解説文。応答のキーの集合が `{"is_correct","explanation","explanation_image","explanation_images","correct_choices","session_complete","session","session_stats"}`。`correct_choices` が正解の選択肢 1 件の `id`・`text`、`session.completed_problems`・`session_stats.completed` が 1 | AC1・AC7 |
| TC-04 | `test_build_failure_leaves_nothing`（2 ケースでパラメータ化）: `APIClient(raise_request_exception=False)` で、(a) `Problem.get_explanation_image_url` を `RuntimeError` を出す関数に差し替える (b) `QuizSessionSerializer.to_representation` を `RuntimeError` を出す関数に差し替える（pytest の `monkeypatch`）。それぞれ回答を送り、差し替えを戻して同じ問題に答え直す | `PYT -k build_failure` | exit 0。差し替え中の応答は 500。その回の QuizAnswer が 0 件・DB から読み直した回の `completed_problems` が 0・`correct_answers` が 0・その利用者と問題の `SpacedRepetitionCard` が 0 件・`SpacedRepetitionReview` が 0 件。差し替えを戻した後の答え直しは 200（`{"error": "Problem already answered"}` の 400 にならない）。FG: 応答の組み立て（`result = {...}`）を `with transaction.atomic():` の外に戻すと、(a)(b) とも残りが 0 件の確かめで FAIL（exit 非ゼロ）。戻す | AC2 |
| TC-05 | `test_serializers_share_media_assets`: 問題用 2 枚・解説用 1 枚を持つ問題で、`ProblemDisplaySerializer`・`ProblemSerializer`（`context` に request なし）・`AnswerExplanationSerializer` を作る | `PYT -k serializers_share_media_assets` | exit 0。`ProblemDisplaySerializer`・`ProblemSerializer` の `question_images` は問題用 2 枚の `id` を `position` の順、`explanation_images` は解説用 1 枚の `id`。`AnswerExplanationSerializer(problem).data["explanation_images"]` が `ProblemDisplaySerializer(problem).data["explanation_images"]` と等しい | AC3・AC7 |
| TC-06 | 守りの既存テスト（問題・クイズの回答・I166・I158・I452・#446） | 下の「TC-06 のコマンド」 | exit 0（failed 0） | AC7 |
| TC-07 | `problemImages.test.ts`: `pickImageUrls` の (a) 新 2 枚（url `/media/a.png`・`/media/b.png`）＋古 `/media/legacy.png` → `["/media/a.png", "/media/b.png"]` (b) 新 `[]`＋古 → `["/media/legacy.png"]` (c) 新 `undefined`＋古 `null` → `[]` (d) 新 1 枚＋古 `undefined` → `["/media/a.png"]` | `JEST src/utils/__tests__/problemImages.test.ts` | exit 0 | AC4・AC6 |
| TC-08 | `ProblemImageList.test.tsx`: (a) 1 枚 → `ul` の `grid-template-columns` が `repeat(1, 1fr)`・`img` の `alt` が「解説画像 1」・`aria-label` が「解説画像 1枚目。クリックで拡大表示」・`role="button"`・`tabindex="0"`・`src` が `getMediaUrl("/media/a.png")` (b) 2 枚 → `repeat(2, 1fr)` (c) 4 枚 → `repeat(3, 1fr)`・`img` が 4 つ (d) 1 枚目のクリック・Enter・スペースで `onImageClick` が `getMediaUrl("/media/a.png")` で 1 回ずつ呼ばれ、`a` キーでは呼ばれない (e) 空配列 → 描いたものが空（`container` が空） (f) `https://cdn.example.com/x.png` → `src` がそのまま | `JEST src/components/__tests__/ProblemImageList.test.tsx` | exit 0 | AC4 |
| TC-09 | `QuizSession.test.tsx` に追記: 既存の `mockSession`・`mockProblem` で単一選択の選択肢を押し、`apiClient.post` の応答を変えて (a) `explanation_images` 2 枚（`/media/e1.png`・`/media/e2.png`）＋`explanation_image: '/media/legacy.png'` → `answer-result` の中に「解説画像 1」「解説画像 2」が `e1`・`e2` の URL で出て、`legacy.png` を `src` に持つ `img` は無い (b) `explanation_image: '/media/legacy.png'` だけ → 「解説画像 1」が `legacy.png` の URL で 1 枚 (c) `explanation: ''`・`explanation_images` 1 枚 → `answer-result` の中に「解説画像 1」があり、「解説:」の文字は無い (d) (a) で「解説画像 1」を押す → `role="dialog"` が開き、その中の `img` の `src` が `e1` の完全な URL (e) 問題に `question_images` 1 枚（`/media/q1.png`）＋`question_image: '/media/qlegacy.png'` → 回答の前に「問題画像 1」が `q1` の URL で出る (f) `question_image` だけ → 「問題画像 1」が `qlegacy` の URL (g) どちらも無い（既存の `mockProblem`）→ `alt` が「問題画像」で始まる `img` が無い | `JEST src/pages/__tests__/QuizSession.test.tsx` | exit 0。既存の 7 件も pass。FG: 4-6 で解説画像の選び方を `result.explanation_image` だけに戻すと (a)(c) が FAIL。戻す | AC3〜AC6 |
| TC-10 | `ProblemPreview.test.tsx`（新規・プレビューの見え方の守り）: (a) `explanation_images` 2 枚＋`explanation_image` → 「解説画像 1」「解説画像 2」が新しい形式の URL (b) `explanation_image` だけ → 「解説画像 1」が古い形式の URL (c) `explanation: ''`・`explanation_images` 1 枚 → `alt` が「解説画像」で始まる `img` が無い (d) `question_images` 1 枚 → 「問題画像 1」を押すと `role="dialog"` が開く | `JEST src/components/__tests__/ProblemPreview.test.tsx` | exit 0。切り出しの前（今のコード）でも (a)〜(d) が pass する（ステップ 2 の最初に、切り出す前に流して確かめる） | AC4 |
| TC-11 | クイズの画面の既存のテストと、型・lint | `JEST src/pages/__tests__/QuizSession.review.test.tsx src/pages/__tests__/QuizSession.start.test.tsx`、`docker compose exec -T frontend npm run typecheck`、`docker compose exec -T frontend npm run lint` | すべて exit 0（lint の警告 0） | AC7 |
| TC-12 | CI の全テスト | `gh pr checks 474` | 全ジョブ pass（`Backend Tests` に `test_I472_quiz_answer_explanation_image.py`、`Frontend Tests` に新しい 3 ファイルと追記の結果が出る） | AC7 |
| TC-13 | /simplify の後の流し直し | TC-01〜TC-11 のコマンド | すべて exit 0 | AC1〜AC7 |

### TC-06 のコマンド
```
docker compose exec -T backend python -m pytest problems/tests/test_I472_quiz_answer_explanation_image.py problems/tests/test_I166_quiz_tenant_isolation.py problems/tests/test_I158_quiz_session_start.py problems/tests/test_serializers.py problems/tests/test_views.py problems/tests/test_I073_image_update.py studylogs/tests/test_I452_quiz_review.py core/tests/test_I446_cross_api_tenant_isolation.py -q
```
- 合否は exit code だけで決める。実装前のベースラインは I472 のファイルを除いて流す（ファイルがまだ無いため）
