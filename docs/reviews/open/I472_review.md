# I472 レビュー: 解説画像がある問題へのクイズの回答の 500 を直し、新しい形式の解説画像と問題の画像もクイズで表示する

- 関連: docs/issues/open/I472.md / docs/plans/open/plan_I472.md / GitHub #472 / Draft PR #474

## 変更概要
- クイズの回答の応答（`POST /api/quiz/<id>/submit_answer/`）で、古い形式の解説画像の URL を他の経路と同じ `get_explanation_image_url()` で作る（`.url` の 500 を直す）。新しい形式の解説画像 `explanation_images` を応答に足す
- 応答の組み立てを、回答・回の集計・復習の予定と同じトランザクションの中に入れる（組み立てに失敗したら何も残さない）
- クイズの画面の問題画像・解説画像を、問題管理のプレビューと同じ選び方（新しい形式があれば新しい形式だけ・無ければ古い形式）と並べ方で出す。解説文が無くても解説画像は出す。選び方と並べ方はプレビューから切り出して共有する

## 変更点
- `backend/problems/serializers.py`: 新しい形式の画像の応答の共通関数 `serialize_media_assets`（既存の 4 か所も使う）・回答の解説の `AnswerExplanationSerializer`
- `backend/problems/views.py`（`submit_answer`）: 応答を `transaction.atomic()` の中で組み立て、解説の 3 つの欄を `AnswerExplanationSerializer` から入れる
- `backend/problems/tests/test_I472_quiz_answer_explanation_image.py`（新規・6 件）: 古い形式の 200（TC-01）・新しい形式の表示順（TC-02）・応答のキー（TC-03）・組み立ての失敗で何も残らない（TC-04・2 点）・serializer の共有（TC-05）
- `backend/studylogs/tests/test_I452_quiz_review.py`: 応答のキーの集合に `explanation_images` を足す
- `frontend/src/utils/problemImages.ts`（新規）: 選び方 `pickImageUrls`
- `frontend/src/components/ProblemImageList.tsx`（新規）: 並べ方（プレビューの `renderImages` を移した）
- `frontend/src/components/ProblemPreview.tsx`: 上の 2 つを使う（見え方は同じ）
- `frontend/src/pages/QuizSession.tsx`: 問題画像・解説画像を上の 2 つで出す。解説の枠は解説文か画像があれば出す
- `frontend/src/types/quiz.ts`: `question_images`・`explanation_images`（`Problem`・`QuizResult`）、古い形式の欄を `string | null`
- テスト: `problemImages.test.ts`・`ProblemImageList.test.tsx`・`ProblemPreview.test.tsx`（新規）・`QuizSession.test.tsx`（7 件追記）

## 影響範囲
- Backend: problems（serializers・views・tests）・studylogs（I452 のテストの期待値）
- Frontend: クイズの画面・問題管理のプレビュー（見え方は同じ）・共通の関数と部品
- DB: なし（migration なし）
- Config: なし

## テスト結果
（test-gate の後に書く）

## 計画との差分
- I452 のテストの応答のキーの期待値を更新した（`explanation_images` の追加に伴う・計画変更記録）
- /simplify で、動きを変えずに serializer の 1 行化・部品の列数の式・画面の三項演算・テストの確かめを整理した（計画変更記録）
- ほかは計画どおり

## ロールバック
PR を revert する（コードだけの変更。DB の形は変えない）。

## 自律判断の記録
- [plan] 「保存されたのに 500」は、応答の組み立てを I452 のトランザクションの中に入れる形にした — 応答の回の欄は保存の後の値で、保存の前には作れないため。組み立てのどこで失敗しても全部巻き戻る
- [plan] 画面の画像の選び方（関数）と並べ方（部品）を問題管理のプレビューから切り出し、プレビューとクイズで共有する — 「プレビューと同じ見え方」を作りで保証するため。プレビューの見え方を変えないことを新しいテスト（TC-10）で固定する
- [plan] 手動確認の dev のデータは、確認の後に問題を 1 件ずつ論理削除する — 物理削除は危険操作に当たるため
- [plan-review] Warning 2 件（手動テストのデータの渡し方があいまい・No.1 の不要な文言）を直し、再レビューはしなかった — 方式・範囲・受け入れ条件を変えないため
- [implement] I452 のテストの応答のキーの期待値に `explanation_images` を足した — イシューで決めた欄の追加で、テストの意図（回答の応答の欄が今と同じ）は変わらないため
- [implement] pre-commit の ESLint のフックが手元に eslint が無く exit 127 で止まった。同じ `npm run lint`（--max-warnings 0）をフロントのコンテナで流して 0 件を確かめ、画面側のコミットだけ `SKIP=eslint` にした — I452 と同じ扱い。同じ検査を別の場所で済ませ、CI でも流れる（根本対応は #468）
- [implement] 手動確認の画像は `backend/media/`（git 管理のフォルダ）に一時的に写し、コミットに入れない。後片付けで 1 枚ずつ消す — 画像の種類が 1 つしか無く、新旧の見分けは `src` の URL で行った
- [implement] /simplify の指摘のうち、古い形式の getter の mixin 化・正解の選択肢の 2 回の取り出しは #470、テストの `asset()` の共通化は見送り — 応答の作りの整理は #470 の範囲で、正誤の判定を変えるのは本イシューの範囲外のため

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
