# I645 自動テスト: 選択肢の記号（ア・イ・ウ・エ）と選んだ誤答の印

実行コマンド（例）: `docker compose exec -T -e CI=true frontend npm test -- <テストのファイル>` / E2E は CI（E2E Tests）が流す

結果:
- backend: 変更なし
- frontend: 実装前のため未実行

| TC | レベル | ファイル | 確かめること | 期待値 | 結果 |
|---|---|---|---|---|---|
| TC-01 | ユニット | `frontend/src/utils/__tests__/choiceLabel.test.ts` | 順番から記号を出す | `choiceLabel(0)`=`'ア'`・`(1)`=`'イ'`・`(3)`=`'エ'`・`(4)`=`'オ'`・`(45)`=`'ン'`・`(46)`=`'47'`。`CHOICE_LABELS.length`=46 | 実装前のため未実行 |
| TC-02 | 部品 | `frontend/src/components/__tests__/QuizChoices.test.tsx` | 単一選択で、記号と本文が別の要素で出て、入力の名前に記号が付く | 選択肢 3 つ（本文「本文1」〜「本文3」）で、`getByText('ア')`・`getByText('イ')`・`getByText('ウ')` がそれぞれあり、`getByText('本文1')` とは別の要素（`getByText('ア')` の要素の `textContent` が `'ア'`）。`getByRole('radio', { name: 'ア 本文1' })`・`{ name: 'ウ 本文3' }` がある。`queryByText(/^A\./)` が無い | 実装前のため未実行 |
| TC-03 | 部品 | 同上 | 複数選択でも同じ記号と名前 | `getByRole('checkbox', { name: 'イ 本文2' })` がある | 実装前のため未実行 |
| TC-04 | 部品 | 同上 | 単一選択で誤答を選んで答えた後: 選んだ誤答に×の印、正解にチェックの印 | `showResult=true`・`selectedChoices=['c2']`・`correctChoiceIds=['c1']` で、c2 の行（`getByRole('radio', { name: 'イ 本文2' })` を含む `data-testid="choice-option"` の要素）の中に `CancelIcon` があり `CheckCircleOutlineIcon` が無い。c1 の行の中に `CheckCircleOutlineIcon` があり `CancelIcon` が無い。c3 の行にはどちらも無い | 実装前のため未実行 |
| TC-05 | 部品 | 同上 | 正解を選んで答えた後: ×の印はどこにも出ない | `selectedChoices=['c1']`・`correctChoiceIds=['c1']` で `queryAllByTestId('CancelIcon')` の数が 0、`getAllByTestId('CheckCircleOutlineIcon')` の数が 1 | 実装前のため未実行 |
| TC-06 | 部品 | 同上 | 複数選択で、選んだ誤答だけに×、選び漏れた正解にはチェック | `selectedChoices=['c1','c3']`・`correctChoiceIds=['c1','c2']` で、c3 の行に `CancelIcon`、c1 と c2 の行に `CheckCircleOutlineIcon`、`CancelIcon` の数は 1 | 実装前のため未実行 |
| TC-07 | 部品 | `frontend/src/components/__tests__/ProblemPreview.test.tsx` | プレビューに記号が出て「A. 」が出ない（既存の TC-27 の `getByText('A. 正解')` も直す） | `getByText('ア')`・`getByText('イ')` があり、`queryByText(/^[AB]\. /)` が無い。TC-27 の並びの確かめは `getByText('ア')` で行い、`true` | 実装前のため未実行 |
| TC-08 | E2E | `e2e/tests/quiz-session.spec.ts` | 本物のブラウザで、選んだ誤答の文字が赤く（灰色に負けず）、×の印が付く。正解の文字は緑 | ダッシュボードからクイズを始め、「不正解の選択肢」の行（`[data-testid="choice-option"]` の 2 つ目）を押す。`[data-testid="answer-result"]` が出た後、その行の `.MuiFormControlLabel-label` の `color` が `rgb(211, 47, 47)`（`error.main`）、行の中に `[data-testid="CancelIcon"]` が 1 つ。1 つ目の行の `.MuiFormControlLabel-label` の `color` が `rgb(46, 125, 50)`（`success.main`）。1 つ目の行に「ア」、2 つ目の行に「イ」の文字が見える | 実装前のため未実行 |
| TC-09 | 部品 | `frontend/src/pages/__tests__/QuizSession.test.tsx` ほか（既存） | 切り出しの後も、単一選択は押してすぐ送る・複数選択は「回答する」で送る（名前を `ア 選択肢1` に直した既存のテストがそのまま通る） | 既存のテスト（`QuizSession.test.tsx`・`QuizSession.source.test.tsx`・`QuizSession.review.test.tsx`・`QuizSession.start.test.tsx`・`QuizSession.weak.test.tsx`）が全部通る | 実装前のため未実行 |

補足:
- TC-08 の色の判定は E2E だけで行う。jsdom はセレクタの強さによる上書きを本物のブラウザと同じには計算しないので、部品のテスト（TC-04〜TC-06）は印の有無だけを判定にする（計画書 6）
- TC-08 の色は、E2E の画面がライトモード（既定）であることが前提。E2E の利用者 A のテーマの設定は変えない
- TC-04〜TC-06 の失敗の注入: 誤答の印を出す条件を外した版（`Cancel` を出さない）で TC-04・TC-06 が落ちることを、実装のときに一度確かめて結果をこの表に書く
- TC-08 の失敗の注入: `.Mui-disabled` のセレクタを外した版で、色の判定が `rgba(0, 0, 0, 0.38)` になり落ちることを、実装のときに手元の E2E で一度確かめて書く
