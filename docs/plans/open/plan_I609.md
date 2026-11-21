# I609 計画書: 問題の解説を任意にし、出典の欄を足す（過去問を登録するための前提）

## 基本情報
- **計画書ID**: plan_I609
- **関連イシュー**: #609
- **Draft PR**: #614
- **作成根拠資料**: docs/issues/open/I609.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I609_review.md
- **作成日**: 2026-11-21

## 1. 背景/目的
- I586 で IPA の公開過去問（午前Ⅱ）を登録する。公開されている情報（問題・選択肢・正解・出典）だけを登録したいが、今のアプリは解説が必須で、出典を書く決まった場所も無い
- 目的: 問題を解説なしで登録・表示できるようにし、出典を問題の専用の項目として登録・表示できるようにする

### 調査結果
**原因の概要**: 問題の項目が「利用者が自分で作る、解説つきの問題」だけを前提に作られている。解説は DB の列・問題管理の入力画面の両方で必須で、出典を入れる項目が無い。あわせて、取り込みの道具 `import_problems` は、今は 1 問も登録できない状態だった。

**詳細**:
1. 解説を必須にしている箇所（全件）
   - DB の列: `backend/problems/models.py:96` `explanation = models.TextField(blank=False)`。ModelSerializer はここから `allow_blank=False`・`required=True` の欄を作るので、API でも空の解説と、解説を送らない作成を 400 で断る
   - 問題管理の入力画面: `frontend/src/pages/QuizManagement.tsx:78` `explanation: yup.string().required('解説は必須です')`
   - `import_problems` は空の解説をそのまま渡す（`import_problems.py:182` の `fields.get('解説', '')`）。`Problem.objects.create` はモデルの検証を通らないので、空の解説で落ちることはない
2. 解説を読むほかの箇所（全件・grep `explanation`。画像の欄は除く）
   - `frontend/src/pages/QuizSession.tsx:634-655`: 解説の欄は「解説の文か解説の画像があるとき」だけ出し、見出し「解説:」は文があるときだけ出す。**今のままで、空の解説で欄も見出しも出ない**（このイシューではテストで固定するだけ）
   - `frontend/src/components/ProblemPreview.tsx:124-137`: `showExplanation && problem.explanation` のときだけ解説の欄を出す。空の解説で見出しは出ないが、**解説の画像だけがある問題では画像も出ない**（クイズの画面と食い違う）
   - `frontend/src/components/AIQuestionGenerator.tsx:390`: `problem.explanation &&` で囲んであり、空でも崩れない。AI の生成は解説を作り続ける（`backend/problems/ai_generator.py:200` で必須）ので変えない。出典は空のまま
   - `backend/problems/admin.py:23` の `search_fields`・`backend/accounts/management/commands/seed_e2e.py:122`・`backend/dashboard/verify_data.py:286`: 解説を入れて作る側。空を許しても変わらない
   - 型: `frontend/src/services/types.ts:94,117`・`frontend/src/types/quiz.ts:47,61` は `explanation?: string`。`frontend/src/types/quiz.ts:110`（`CreateProblemRequest`）だけ `explanation: string`
3. 出典の欄が無い: `Problem`（`backend/problems/models.py:72-118`）に列が無い。`import_problems` は `**出典**：…` の行を読んでも `metadata` に入れて捨てる（`import_problems.py:185-188`）
4. **`import_problems` は今、1 問も登録できない**（イシューに無い発見）
   - `import_problems.py:353` が `Problem.objects.create(..., points=10, ...)` を渡すが、`points` の列は `problems/migrations/0017_remove_problem_points.py` で消えている。`Problem() got unexpected keyword arguments: 'points'` で全問がエラーになり、例外は 1 問ずつ握られて「エラー: N 問」と出るだけ
   - 作る問題に組織（`Problem.organization`）を付けていない。問題管理の画面から作る問題は科目の組織を付ける（`backend/problems/services/problem_service.py:74-82`）。画像の読み取り（`backend/problems/selectors.py:16`）は組織が空の問題の画像を返さない
   - 受け入れ条件「`import_problems` で登録できる」を満たすには、この 2 点を直す必要がある。テストは今 1 本も無い
5. 出典を出す API
   - クイズの出題: `GET /api/quiz/{id}/next_problem/`（`views.py:757`）は `ProblemDisplaySerializer`（`serializers.py:312`）。答える前の応答なので、正解・解説は入れていない（I078・#476）。出典は答える前から見せる決まり（イシューの設計確認メモ）なので、ここに `source` を足す
   - 問題管理: `ProblemViewSet`（`/api/problems/`・`ProblemAdminSerializer`）。プレビューは一覧の応答の問題をそのまま使う（`QuizManagement.tsx:910`）
   - 回答の応答: `POST /api/quiz/{id}/submit_answer/`（`views.py:878`）の `AnswerExplanationSerializer` は解説を返す。出典は足さない（出題のときに出ている）
6. OpenAPI の契約: 問題・クイズの API は `backend/core/openapi.py:6` の `CONTRACT_PATHS` に入っていない。`backend/openapi.yaml`・`frontend/src/types/api/schema.d.ts` の作り直しは要らない
7. 範囲外で見つけたもの（このイシューでは直さない）: `backend/problems/views.py:457-490` の `_save_ai_problem_to_db` は、`Problem` に無い `title`・`description`・`estimated_time_minutes` を渡しており、呼ばれると落ちる。AI 生成の保存の経路で、出典・解説の任意化とは関係しない。retro で扱いを決める
8. 規約との照合
   - 「無い」を空の文字で表す: Django の文字列の列は `null=True` を避け空の文字で表すのが公式の推奨（https://docs.djangoproject.com/en/5.2/ref/models/fields/#null）。イシューの設計確認メモで確定済み
   - マイグレーション: `rules/ultimate_django_coding_standards.md` §4（マージしたマイグレーションは書き換えない・新しいマイグレーションを足す）。データの書き換えは無いので `RunPython` は要らない
   - フォーム: 規約 §8 は React Hook Form＋Zod だが、yup から Zod への移行は #552 の範囲（規約 §16）。この画面は yup のまま、項目を足すだけにする
   - テスト: 規約 §14 は Vitest＋MSW だが、移行は #551・#511 の範囲。既存の Jest＋`jest.mock('../../services/api')` の書き方にそろえる
9. 依存の追加・更新は無い

## 2. 受け入れ条件
- [ ] AC1: 解説を空にして、問題管理の画面（作成・編集）と `import_problems` の両方で問題を登録できる
- [ ] AC2: 出典を、問題管理の画面（作成・編集）と `import_problems` で登録できる
- [ ] AC3: 問題管理の作成・編集の画面で、出典の入力欄が問題用画像のすぐ下（科目の上）にあり、ラベルが「出典（任意）」・入力例「令和6年度 春期 データベーススペシャリスト試験 午前Ⅱ 問1」が出る。2001 文字以上は画面でも API でも `import_problems` でも登録できない（2000 文字は登録できる）。解説の欄のラベルは「解説（任意）」
- [ ] AC4: クイズの画面とプレビューで、出典が問題文のすぐ下（画像があれば画像の下・選択肢の上）に「出典：<登録した本文>」の形で灰色の小さい文字で表示され、答える前から見える。出典が空の問題では何も出ない
- [ ] AC5: 解説が空の問題を解いたとき、解説の欄（見出し「解説:」を含む）が出ず、正誤の表示・正しい選択肢の印・採点は今までどおり動く。プレビューでも解説が空なら見出しを出さない
- [ ] AC6: `import_problems` で、`解説` の見出しが無い・値が空の Markdown と、`出典` の見出しのある Markdown を取り込める。試し実行（`--dry-run`）の件数と本番の登録件数が合う。取り込んだ問題には科目の組織が付く
- [ ] AC7: API の応答（問題管理・クイズの出題・回答）で、解説・出典が無いときは `""`（null にならない）
- [ ] AC8: 既存の問題（解説つき・出典なし）の表示と登録が変わらない
- [ ] AC9: マイグレーションが非破壊（既存の行の解説が消えない・変わらない。既存の行の出典は `""`）

## 3. 影響範囲
- Backend: `problems` のモデル・シリアライザ（`ProblemSerializer`・`ProblemAdminSerializer`〔継承〕・`ProblemDisplaySerializer`）・`import_problems`
- Frontend: 問題管理（作成・編集の入力欄）・クイズの画面（出典の表示）・問題のプレビュー（出典・解説の画像の表示）・型定義
- DB: `problems_problem` に `source varchar(2000) NOT NULL` を 1 列足す（既存の行は `''`）。`explanation` は Python 側の既定値 `''` と `blank=True` を付ける（DB の型・NOT NULL は変わらない）
- Config/Infra: なし（依存の変更なし・Dockerfile/docker-compose への波及なし。OpenAPI の契約の外）
- ほかのワークツリー: develop を取り込むと起動のたびに migrate が流れる（#579）。列の追加だけで、データは消さない

## 4. 変更点一覧（具体）

### 修正アプローチ
- 「無い」は空の文字 `''` だけで表す（null を使わない）。DB・API・画面の型がすべて `string` のまま
- 出典は問題の専用の列に持ち、画面が頭に「出典：」を付けて出す（保存するのは本文だけ）
- 表示は、クイズの画面の今の作り（解説の文が無ければ見出しを出さない）にプレビューをそろえる
- `import_problems` は、出典を読むのに加えて、今 1 問も登録できない原因（消えた列 `points`・組織の付け忘れ）を直す

### 4-1. 解説を任意にし、出典の列を足す（DB）
- `backend/problems/models.py` `Problem`:
  - `explanation = models.TextField(blank=True, default='')`
  - 上限は 1 か所で持つ: `Problem.SOURCE_MAX_LENGTH = 2000`（クラスの定数）。シリアライザはモデルの `max_length` から欄を作るので直書きしない。`import_problems` は `Problem.SOURCE_MAX_LENGTH` を読む
  - `source = models.CharField(max_length=SOURCE_MAX_LENGTH, blank=True, default='', verbose_name='出典', help_text='公開の過去問などの出どころ（例: 令和6年度 春期 データベーススペシャリスト試験 午前Ⅱ 問1）。画面が頭に「出典：」を付けて出す')`
- `backend/problems/migrations/0028_problem_source_optional_explanation.py`（`makemigrations problems` で作る）: `AddField(problem.source)`・`AlterField(problem.explanation)` の 2 つだけ。依存は `0027_remove_subject_image_directory`

### 4-2. API で解説を任意にし、出典を読み書きする
- `backend/problems/serializers.py`
  - `ProblemSerializer.Meta.fields` に `'source'` を足す（`ProblemAdminSerializer` は継承で入る）。欄はモデルから作られる: `explanation` は `required=False, allow_blank=True`、`source` は `required=False, allow_blank=True, max_length=2000`（前後の空白は DRF の既定 `trim_whitespace=True` で取る）
  - `ProblemDisplaySerializer.Meta.fields` に `'source'` を足す（読み取りだけ。答える前の応答に出してよい項目）
  - `AnswerExplanationSerializer`・ビュー・サービスは変えない（`ProblemService.create_problem_with_images` は `validated_data` をそのまま渡すので、`source` も入る）
- API の一覧（変えるのは本文の項目だけ。URL・メソッド・権限は今のまま）

| API | メソッド | 権限（`permission_classes`） | 変わるところ |
|---|---|---|---|
| `/api/problems/` | GET（一覧・配列）/ POST（multipart・201 で問題の JSON） | `IsAuthenticated`・`IsOrgAdmin` | 要求: `explanation` を省略・空で可、`source`（任意・2000 文字まで）。応答: `source: string` を足す |
| `/api/problems/{id}/` | GET / PUT / PATCH（multipart・200 で問題の JSON）/ DELETE | `IsAuthenticated`・`IsOrgAdmin` | 同上。他組織の問題は今までどおり 404 |
| `/api/quiz/{id}/next_problem/` | GET（200 で `ProblemDisplaySerializer` の JSON） | `IsAuthenticated` | 応答に `source: string` を足す。正解・解説は今までどおり入れない |
| `/api/quiz/{id}/submit_answer/` | POST（200） | `IsAuthenticated` | 変更なし（解説が無いとき `explanation: ""`） |

- エラー: 出典が 2001 文字以上 → 400、本文は `core.exceptions.custom_exception_handler` の形 `{"error": {"main_message": "入力内容にエラーがあります", "sub_message": "…", "details": {"source": ["…"]}}}`

### 4-3. 問題管理の入力画面
- `frontend/src/pages/QuizManagement.tsx`
  - 上限は `frontend/src/constants/problem.ts`（新規）の `PROBLEM_SOURCE_MAX_LENGTH = 2000` で持つ（API の上限と同じ値。食い違いは TC-22 と TC-04 で気づける）
  - スキーマ: `explanation: yup.string()`（必須を外す）・`source: yup.string().max(PROBLEM_SOURCE_MAX_LENGTH, `出典は${PROBLEM_SOURCE_MAX_LENGTH}文字以内で入力してください`)`
  - 既定値 `source: ''`、編集を開くとき `source: problem.source || ''`
  - 作成・更新の送信で `formData.append('source', data.source || '')`
  - 入力欄: 問題用画像（`ImageUploadArea label="問題用画像"`）の `Grid` のすぐ後、科目の前に、1 行の `TextField`（`label="出典（任意）"`・`placeholder="令和6年度 春期 データベーススペシャリスト試験 午前Ⅱ 問1"`・`error`/`helperText` は検証の結果）
  - 解説の欄の `label` を「解説（任意）」にする
- 並び（作成・編集で同じ）: 問題文 → 問題用画像 → 出典（任意） → 科目 → 難易度 → 問題タイプ → 選択肢 → 解説（任意） → 解説用画像

### 4-4. クイズの画面とプレビューの表示
- 出典の表示は 2 画面で同じ形にする。`frontend/src/components/ProblemSource.tsx`（新規・小さな表示の部品）: `source` が空（空白だけを含む）なら何も描かない。あれば `<Typography variant="caption" component="p" color="text.secondary">出典：{source}</Typography>`。React のテキストとして出す（HTML として解釈しない・URL もリンクにしない）。長い URL が画面からはみ出さないよう `sx={{ mt: 1, overflowWrap: 'anywhere' }}` で折り返す
- `frontend/src/pages/QuizSession.tsx`: 問題画像（`ProblemImageList alt="問題画像"`）のすぐ後・回答の入力（選択肢）の前に `<ProblemSource source={currentProblem.source} />`。解説の欄は変えない（今の作りで AC5 を満たす。テストで固定する）
- `frontend/src/components/ProblemPreview.tsx`
  - 問題画像のすぐ後・選択肢の前に `<ProblemSource source={problem.source} />`
  - 解説の欄を、クイズの画面と同じ条件にそろえる: `showExplanation && (problem.explanation || explanationImages.length > 0)` のときに区切りの線と欄を出し、見出し「解説:」と本文は `problem.explanation` があるときだけ出す。解説の画像は文が無くても出す
- 型: `frontend/src/services/types.ts` の `Problem`・`CreateProblemRequest` と `frontend/src/types/quiz.ts` の `Problem` に `source?: string` を足す。`frontend/src/types/quiz.ts` の `CreateProblemRequest.explanation` を `explanation?: string` にし、`source?: string` を足す

### 4-5. `import_problems`
- `backend/problems/management/commands/import_problems.py`
  - `ParsedProblem` に `source: str = ""` を足し、`__post_init__` で `len(self.source) > Problem.SOURCE_MAX_LENGTH` なら `ValueError("出典が長すぎます（2000文字以下）: N文字")`（その問題は取り込まず警告を出す。試し実行の件数にも入らない）
  - `_parse_problem_section`: `source = fields.get('出典', '').strip()`。`metadata` から外すキーに `'出典'` を足す
  - `Problem.objects.create`: `points=10` を消す・`source=parsed_problem.source` と `organization=subject.organization` を渡す
  - 1 問でも登録したら、ループの後で `cache_service.invalidate_problems_cache(subject.id)` を 1 回呼ぶ（問題管理の一覧のキャッシュを消す。API の作成の経路と同じ・試し実行と 0 問のときは呼ばない）
  - 試し実行の「最初の3問」の表示に、出典があれば `   出典: …` の行を足す（取り込む前に出典の読み取りを確かめるため）
  - `解説` の見出しが無い・値が空（`**解説**：` だけの行は `FIELD_PATTERN` の `.+` に当たらず見出し無しと同じ）のときは `explanation=''` で登録する（今の読み取りのまま。テストで固定する）
- Markdown の形（1 問の例）:
  ```
  ### Q1
  **問題文**：…
  **選択肢**：
  - A. …
  - B. …
  **正解**：A
  **出典**：令和6年度 春期 データベーススペシャリスト試験 午前Ⅱ 問1
  ```

### 4-6. テスト
- `backend/problems/tests/test_I609_optional_explanation_source.py`（新規）: API・シリアライザ・`import_problems`・マイグレーション（→ 自動テスト文書 TC-01〜TC-14）
- `frontend/src/pages/__tests__/QuizManagement.source.test.tsx`（新規）: 入力欄の並び・ラベル・入力例・検証・送信（→ TC-20〜TC-23）
- `frontend/src/pages/__tests__/QuizSession.source.test.tsx`（新規）: 出典の表示・解説が無いとき（→ TC-24〜TC-26）
- `frontend/src/components/__tests__/ProblemPreview.test.tsx`（足す）: 出典の表示・解説が無いとき・解説の画像だけのとき・空白だけの出典（→ TC-27〜TC-30）

## 5. 実装手順（ステップ）
1. DB → API → 画面の縦の 1 本目（出典の列・API・型・問題管理の入力欄）: 4-1・4-2・4-3・4-4 の型 → TC-01〜TC-10・TC-14・TC-20〜TC-23
2. 表示（クイズの画面・プレビュー・`ProblemSource`）: 4-4 → TC-24〜TC-30。ステップ 1 の後（API の `source` と型を使う）
3. `import_problems`: 4-5 → TC-11〜TC-12。ステップ 1 の後（`source` の列を使う）。ステップ 2 と並行してよい
4. マイグレーションのテスト: → TC-13。ステップ 1 の後
- マイグレーションを足すので、実装後に backend の再起動（`docker compose restart backend` で起動時の migrate が流れる）が要る

## 6. テスト計画
### 自動
- テストの階層: モデル・API・シリアライザ・コマンド・マイグレーションは pytest（結合: API を `APIClient` で呼ぶ）、画面の表示・入力・検証は Jest＋Testing Library（部品）。E2E は足さない（下の 9 の理由）。既存のクイズの E2E（`e2e/tests/quiz-session.spec.ts`）が回帰を見る
- 認可・テナント: 権限の決まりは変えないが、新しい項目の書き込みの経路として「他組織の管理者が出典を書き換えられない（404）」「一般の利用者は 403」「未ログインは 401」を TC-10 で確かめる
- 再発防止: `import_problems` が登録できなかった不具合（`points`）は、TC-11 が先に落ちることを確かめてから直す
- 詳細は `docs/tests/open/I609_auto_test.md`
### 手動
- 実際のアプリで、Claude が Playwright MCP で画面を確かめ、`import_problems` を開発の DB で流す（`docs/tests/open/I609_manual_test.md`。人の分は無い）

## 7. ロールバック
- PR を revert し、`docker compose exec backend python manage.py migrate problems 0027` でマイグレーションを戻す
- 戻すと `source` の列が消え、入れた出典は失われる（解説は消えない。空の解説の問題はそのまま残るが、戻した後の画面では編集の保存で「解説は必須です」になる）。I586 の登録の前に戻すなら失うものは無い

## 8. Risk & 回避策
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: 出典を答える前の応答に足すことで、答えの手がかりを漏らす | 出典は年度・試験区分・問番号だけで答えを含まない。イシューの設計確認メモで「答える前から見える」と確定済み。正解・解説は今までどおり出題の応答に入れない（TC-08 で確かめる） | 回避 |
| R2: 出典に HTML・スクリプトを入れられる（XSS） | React のテキストとして出す（`dangerouslySetInnerHTML` を使わない）。長さは 2000 文字で DB・API・画面・`import_problems` で止める。URL もただの文字として出し、リンクにしない（`javascript:` などの形を開かせる心配が無い） | 回避 |
| R3: マイグレーションで既存の行の解説が変わる・ほかのワークツリーで起動に失敗する | 列の追加と Python 側の既定値だけで、データを書き換えない。TC-13 で、流す前の行の解説が残り、出典が `''` になり、戻すと列が消えることを確かめる | 回避 |
| R4: `import_problems` に組織を付けることで、全体共有の科目（組織が空）の取り込みが変わる | `subject.organization` をそのまま付けるので、全体共有の科目では今までどおり空。管理の画面からは全体共有の科目に問題を作れない（`ProblemService` が断る）が、コマンドは運用者が流すもので今の動きを変えない | 回避 |
| R5: 範囲外の `_save_ai_problem_to_db` の不具合（調査結果 7）を残す | このイシューの受け入れ条件と関係しない。retro で起票するかを決める | 受け入れ |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 「無い」は空の文字で表す（`blank=True`・`default=''`・null は使わない）。出典の列も同じ。出典は `CharField`（上限は 2000 文字。イシューの設計確認メモの 200 文字から、計画のときにユーザーが変えた。下の「ユーザーに確かめた」を参照）
- 出典は問題の専用の列（画像ごとの出典は今回足さない）
- 入力欄の並び: 問題文 → 問題用画像 → 出典 → 科目 → 難易度 → 形式 → 選択肢 → 解説 → 解説用画像。ラベル「出典（任意）」「解説（任意）」。出典は 1 行・入力例「令和6年度 春期 データベーススペシャリスト試験 午前Ⅱ 問1」
- クイズの画面・プレビュー: 出典は問題文のすぐ下（画像があれば画像の下）に灰色の小さい文字で、画面が頭に「出典：」を付けて答える前から出す。空なら何も出さない。解説が無いときは解説の欄ごと出さない
- 問題管理の一覧の表に出典の列を足すのは別イシュー。絞り込み・検索・画像ごとのクレジットも範囲外
ユーザーに確かめた（計画のとき・2026-11-21）:
- 出典の上限は 2000 文字 — ユーザーの指摘「出典が URL の場合に 200 文字を超えることがある」。ブラウザが扱える URL の長さ（約 2,000）まで入り、間違って長い文章を貼り付けたときは止める
- 出典に URL が入っても、ただの文字として出す（押して開くリンクにはしない。要るなら別イシュー）。長い URL は画面の幅で折り返す
- プレビューで、解説の文が無く解説の画像だけがある問題は、見出しなしで画像だけを出す（クイズの画面にそろえる）
Claude が決めた（技術的な選択と理由）:
- `import_problems` の `points=10` を消し、組織を科目の組織にそろえる — 今は 1 問も登録できず、AC1・AC2・AC6 を満たせないため。組織は管理の画面から作る問題（`ProblemService`）と同じ決め方にそろえる（C4）
- 出典の表示を小さな部品 `ProblemSource` に切り出す — クイズの画面とプレビューで同じ表示を 2 回書かないため（規約 §4 の部品の分け方）
- 文字の大きさは MUI の `caption`（12px）・色は `text.secondary` — 「灰色の小さい文字」を MUI の既定の書き方で表す。`text.secondary` は白地でコントラスト比 4.5:1 以上
- 2001 文字以上の出典の画面のエラーの文言「出典は2000文字以内で入力してください」 — 同じ画面の既存の文言（「問題文は必須です」など）の形にそろえる
- 入力欄に `maxLength` で打てなくする作りにはしない — 貼り付けで切れたことに気づけず、出典の一部が黙って消えるため。検証のエラーで知らせる
- 出典は答える前の応答（`ProblemDisplaySerializer`）にだけ足し、回答の応答（`AnswerExplanationSerializer`）には足さない — 出題のときにもう出ているため
- 出典の前後の空白は DRF の既定（`trim_whitespace=True`）で取る。空白だけなら `''` になり、表示されない
- フォームは yup のまま・テストは Jest のまま — Zod・Vitest・MSW への移行は #552・#551・#511 の範囲（規約 §16）
- E2E は足さない — 変える表示はすべて Jest の部品のテストで決まった値まで確かめられ、問題の作成から出題までのつながりは Claude が実際のアプリで確かめる（手動テスト）。E2E の種のデータ（`seed_e2e`）に出典つきの問題を足すと、ほかの E2E の問題の数に響く。問題管理の作成の E2E が無いことは既知の負債で、このイシューで埋めない
- OpenAPI の作り直しはしない — 問題・クイズの API は契約（`CONTRACT_PATHS`）の外のため
- 取り込みの Markdown の形の説明書は作らない — 説明書の置き場（`import_problems.py` の冒頭が指す `docs/detailed_design/backend/problem_data_management/`）がもう無く、形は計画書 4-5 とコマンドの読み取りのテストで残す
- 一覧 I223.md B1〜B4・I224.md F9（`FILE=-`）: 残す — どれもハーネス・bot の後片付けで、このイシューの対象のファイルと関係しない
セキュリティ・ベストプラクティス:
- 入力の検証: 出典は DB（`varchar(2000)`）・API（`max_length=2000`）・画面（yup `max(2000)`）・`import_problems`（`ParsedProblem`）で止める。解説は今までどおり長さの上限なし（TextField）
- 認証・認可: 変えない（問題管理は `IsAuthenticated`＋`IsOrgAdmin`、クイズは `IsAuthenticated`。組織の境界は `available_problems`・`OrgSubjectField` のまま）
- 機密データ: 出典は公開の出どころの文字で、個人情報を含まない
- OWASP: XSS は R2。SQL は ORM だけ。CSRF は今の設定のまま
- 静的解析の基準: bandit は MEDIUM 以上を直す（LOW は `# nosec` と理由）、npm audit は high/critical を直す。依存の追加なし
P3/P5/P8（データ整合性・運用・コスト）: DB の変更があるので 10 を書く。外部 API・非同期・新しいインフラは無い（11・12 は影響なし）
P6（性能・UX）: 画面の変更があるので 13 を書く
P9（プライバシー）: 影響なし（個人情報・未成年データを扱う変更なし。テナントの境界は今のまま）
Danger Ops:
- 無（列の追加と Python 側の既定値だけで、既存のデータを消さない・書き換えない。`docs/runbooks/danger-ops.md` の破壊的なマイグレーションに当たらない）

## 10. データ整合性設計
- 制約: `source varchar(2000) NOT NULL`（既存の行は追加のときの既定値 `''`）。`explanation text NOT NULL` は変えない。null を使わないので、「無い」は `''` の 1 通り
- マイグレーションの安全性: `AddField` は PostgreSQL で定数の既定値つきの列の追加（11 以上は表の書き直しなし）。`AlterField(explanation)` は `blank`・Python 側の `default` だけの変更で、DB の型・制約の SQL は出ない見込み（実装で `sqlmigrate problems 0028` を確かめ、自律判断の記録に書く）
- 戻せるか: 戻すと `source` の列を消す（7）。解説は残る
- トランザクション・同時更新: 変えない（作成・更新は今の `ProblemService` のトランザクションの中）。`import_problems` は 1 問ずつ `transaction.atomic()` のまま

## 13. 性能・UX設計
- 性能: 列を 1 つ足すだけで、クエリの数は変わらない（N+1 なし）。一覧のキャッシュ（`cache_service`）は作成・更新のときに今までどおり消す
- 表示の状態: 出典が空 → 何も描かない（場所も取らない）。解説が空 → 解説の欄ごと出さない（文も画像も無いとき）
- 入力の誤り: 2001 文字以上 → 出典の欄の下に赤い文字で「出典は2000文字以内で入力してください」と出て、送信しない。API の 400 は今までどおりトーストで出す
- 削除などの確認の導線: 変えない
- アクセシビリティ: 入力欄はラベルつきの `TextField`（`getByRole('textbox', { name: '出典（任意）' })` で探せる）。出典の表示はふつうのテキストで、読み上げで「出典：…」と読まれる

## 14. 学習効果設計
- C1: 解説が無い問題でも、正誤・正しい選択肢の印・出典が出るので、学ぶ人は答え合わせと出どころの確認ができる。採点・復習の時期・苦手の判定は変えない（解説の有無を使っていない）

## 計画変更記録
- 2026-11-21 plan: イシューの記載: [出典は `CharField(max_length=200)`・201 文字以上は登録できない] → 採った方法: 上限 2000 文字 — 理由: 計画のときのユーザーの指摘（出典に URL を入れると 200 文字を超えることがある）とユーザーの選択（2000・500・上限なしから 2000）。GitHub のイシュー本文は同期しない（正は GitHub だが、この変更の正はこの計画書と 9 の「ユーザーに確かめた」）。計画レビューのやり直し: 不要（計画レビューの前に計画書へ入れ済み）
- 2026-11-21 fix-loop: 計画書の記載: [`import_problems` は出典を読み、`points` を消し、組織を付ける] → 採った方法: あわせて登録の後に問題の一覧のキャッシュを消す — 理由: 手動テスト No.7 で、取り込んだ問題が問題管理の一覧に最大 1 時間出ないと分かった（一覧は利用者ごとに 1 時間キャッシュされ、取り込みは消していなかった）。比べた案: シグナルで消す（問題ごとに Redis を走査・範囲を超える）・手順に書く（忘れる）。診断メモ `docs/reviews/I609_fix_diagnosis_20261121_1824.md`。計画レビューのやり直し: 不要（受け入れ条件 AC6 を満たすための直し・方式と範囲は変えない）
- 2026-11-21 implement: 計画書の記載: [出典の欄は `label="出典（任意）"`・`placeholder`] → 採った方法: あわせて `InputLabelProps={{ shrink: true }}` でラベルを常に上に置く — 理由: MUI の既定では欄を押すまで入力例が見えず、受け入れ条件 AC3「入力例が出る」を満たさないため（画面確認で見つけた）。見せ方の判断ではなく AC を満たす直し。計画レビューのやり直し: 不要
- 2026-11-21 implement: `/simplify` の指摘で `import_problems` の組織を `organization_id=subject.organization_id` で渡す（組織を読むクエリを 1 回減らす・結果は同じ）。計画レビューのやり直し: 不要
- 2026-11-21 plan-review: 計画レビューの Warning・Info への対応 — 上限を定数（`Problem.SOURCE_MAX_LENGTH`・`PROBLEM_SOURCE_MAX_LENGTH`）で持つ・`sqlmigrate` の結果を実装で記録する（10 のとおり）・空白だけの出典の TC-30 を足す。計画レビューのやり直し: 不要（方式・範囲・受け入れ条件を変えない）

## レビュー結果
- [20261121_1754 判定: ✅ 完了](../../reviews/I609_plan_review_20261121_1754.md)
