# I609 自動テスト: 問題の解説を任意にし、出典の欄を足す

実行コマンド（例）: `docker compose exec backend python -m pytest problems/tests/test_I609_optional_explanation_source.py` / `docker compose exec frontend npm test -- --watchAll=false QuizManagement.source QuizSession.source ProblemPreview`

結果:
- backend: 実装前のため未実行
- frontend: 実装前のため未実行

## バックエンド（`backend/problems/tests/test_I609_optional_explanation_source.py`）

前提のデータ: 組織 A（管理者 `admin_a`・一般 `user_a`・科目 `subject_a`）、組織 B（管理者 `admin_b`・科目 `subject_b`）。問題の作成は multipart（`format='multipart'`）で `/api/problems/` に送る。

| TC | 内容 | 期待値 |
|---|---|---|
| TC-01 | `Problem.objects.create` に `explanation`・`source` を渡さずに作る | 例外なし。`explanation == ''`・`source == ''`（None でない） |
| TC-02 | `admin_a` が `explanation=''`・`source='令和6年度 春期 データベーススペシャリスト試験 午前Ⅱ 問1'` で作成 | 201。本文 `explanation == ""`・`source == "令和6年度 春期 データベーススペシャリスト試験 午前Ⅱ 問1"`。DB の行も同じ値 |
| TC-03 | `admin_a` が `explanation`・`source` のキーを送らずに作成 | 201。本文 `explanation == ""`・`source == ""` |
| TC-04 | `source` が 2001 文字 | 400。`body["error"]["main_message"] == "入力内容にエラーがあります"`・`"source" in body["error"]["details"]`。問題は増えない |
| TC-05 | `source` が 2000 文字ちょうど | 201。`len(body["source"]) == 2000` |
| TC-06 | 解説つき・出典なしの問題を、`admin_a` が PUT で `explanation=''`・`source='出典X'` に更新 | 200。DB の `explanation == ''`・`source == '出典X'` |
| TC-07 | 出典 `'出典X'` の問題を、`source` のキーを送らずに PATCH（問題文だけ変える） | 200。DB の `source == '出典X'` のまま |
| TC-08 | 出典つき・解説つきの問題で回を始め、`GET /api/quiz/{id}/next_problem/` | 200。本文 `source == "出典X"`。本文に `explanation` のキーが無く、`choices` の各要素に `is_correct` のキーが無い |
| TC-09 | 解説が空の問題に `POST /api/quiz/{id}/submit_answer/` で正解を答える | 200。`is_correct is True`・`explanation == ""`・`correct_choices` に正解の選択肢の id がある。`QuizAnswer` が 1 件でき、回の `correct_answers` が 1 増える |
| TC-10 | 組織 A の問題の出典の書き換えを、`admin_b`（PATCH）・`user_a`（PATCH）・未ログイン（PATCH）で試す | それぞれ 404・403・401。DB の `source` は変わらない |
| TC-11 | `import_problems --file <一時ファイル> --subject-id <subject_a>`（Markdown 3 問: ① `解説` の見出しなし・`出典` あり ② `**解説**：` の値が空 ③ 解説あり・出典なし） | 3 問ができる（`stdout` に `成功: 3問`・エラー 0）。① `source == '令和6年度 春期 データベーススペシャリスト試験 午前Ⅱ 問1'`・`explanation == ''` ② `explanation == ''` ③ `explanation == '<書いた解説>'`・`source == ''`。全問 `organization == subject_a.organization`。**修正前（`points=10` のまま）は 0 問で落ちることを先に確かめる** |
| TC-12 | TC-11 と同じファイルに ④ 出典 2001 文字の問題を足し、`--dry-run` と本番を続けて流す | 試し実行の `stdout` に `パースされた問題: 3問` と `出典: 令和6年度 …` の行。本番の後の問題の数が 3（④ は入らない） |
| TC-13 | マイグレーション: `0027` まで流した表に解説 `'既存の解説'` の行を入れ、`0028` を流し、その後戻す（`problems/tests/migration_helpers.py`） | 流した後: 行の `explanation == '既存の解説'`・`source == ''`。戻した後: `problems_problem` に `source` の列が無く、`explanation == '既存の解説'` |
| TC-14 | 既存の形の問題（解説つき・出典なし）を `admin_a` が GET（一覧・詳細） | 200。`explanation == "<元の解説>"`・`source == ""`。ほかの項目（`question_text`・`choices`・`difficulty`）は作ったときの値 |

## フロントエンド

### `frontend/src/pages/__tests__/QuizManagement.source.test.tsx`（新規）
| TC | 内容 | 期待値 |
|---|---|---|
| TC-20 | 作成のダイアログを開く | `getByRole('textbox', { name: '出典（任意）' })` があり、`placeholder` が `令和6年度 春期 データベーススペシャリスト試験 午前Ⅱ 問1`。DOM の順で「問題用画像」の欄の後・「科目」の欄の前。`getByRole('textbox', { name: '解説（任意）' })` がある |
| TC-21 | 問題文・科目・選択肢 2 つ（正解 1 つ）・出典 `出典X` を入れ、解説を空のまま「作成」 | 「解説は必須です」が出ない。`apiClient.post` が `/api/problems/` に 1 回呼ばれ、`FormData` の `explanation === ''`・`source === '出典X'` |
| TC-22 | 出典に 2001 文字を入れて「作成」 | 「出典は2000文字以内で入力してください」が出て、`apiClient.post` は呼ばれない |
| TC-23 | 出典 `出典X` の問題の編集を開いて「更新」 | 出典の欄の値が `出典X`。`quizService.updateProblem` の `FormData` の `source === '出典X'` |

### `frontend/src/pages/__tests__/QuizSession.source.test.tsx`（新規）
| TC | 内容 | 期待値 |
|---|---|---|
| TC-24 | 出題の応答が `source: '出典X'`・問題画像 1 枚 | 答える前に `出典：出典X` の文がある。DOM の順で問題画像の後・最初の選択肢の前 |
| TC-25 | 出題の応答が `source: ''` | `出典：` を含む文が無い（`queryByText(/出典：/)` が null） |
| TC-26 | 答えの応答が `is_correct: true`・`explanation: ''`・`explanation_images: []` | 「正解です！」が出て、正解の選択肢に印がある。「解説:」が無い |

### `frontend/src/components/__tests__/ProblemPreview.test.tsx`（足す）
| TC | 内容 | 期待値 |
|---|---|---|
| TC-27 | `source: '出典X'`・問題画像 1 枚 | `出典：出典X` が問題画像の後・選択肢「A.」の前。`source: ''` では `出典：` を含む文が無い |
| TC-28 | `explanation: ''`・解説画像なし | 「解説:」が無い |
| TC-29 | `explanation: ''`・解説画像 1 枚 | 解説画像（`alt` が解説画像）が出て、「解説:」は無い |
| TC-30 | `source: '   '`（空白だけ） | `出典：` を含む文が無い |
