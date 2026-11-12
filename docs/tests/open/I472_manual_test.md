# I472 手動テスト: 解説画像がある問題へのクイズの回答の 500 を直し、新しい形式の解説画像と問題の画像もクイズで表示する

- 関連: docs/plans/open/plan_I472.md / Draft PR #474
- 実施: test-gate 段階で Claude が行う（画面は Playwright MCP・`docs/runbooks/frontend-verify.md`）。アカウントは `e2e_user_a@example.com`（組織 A・管理者。問題管理のプレビューも開けるため）
- 確認用のデータ（No.1 で作る）: 組織 A に科目「I472確認用」（slug `i472-check`）を作り、次の 3 問を入れる。画像は `backend/media/org/personal/subjects/aws-saa/problem/q02_problem.png` を写して使う
  - P1「I472 新しい形式」: 問題用 MediaAsset 1 枚・解説用 MediaAsset 2 枚（`position` 1・2）・古い形式の `explanation_image` も入れる
  - P2「I472 古い形式」: 古い形式の `question_image`・`explanation_image` だけ（ファイルは `org/<組織 A の slug>/subjects/i472-check/problem/`・`explanation/` に写す）
  - P3「I472 解説文なし」: `explanation=''`・解説用 MediaAsset 1 枚だけ

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `docker compose exec -T backend python manage.py shell` に確認用のデータを作るコードを渡す（上の P1〜P3・選択肢は正解 1・不正解 1。`.delete()`・一括 `update()` は使わない）。続けて `GET /api/quiz/` 相当の確かめとして、科目「I472確認用」で回を始められること（No.2 で確かめる） | シェルの出力に科目の ID と P1〜P3 の問題の ID・MediaAsset の ID が出て、例外が出ない | Claude |  |  |
| 2 | `npm run typecheck` を通した後、e2e_user_a でログインし、ダッシュボードから科目「I472確認用」のクイズを始める。出た問題ごとに選択肢「正解」を押して回答し、「次の問題」で 3 問を答える | P1: 回答の前に問題文の下へ「問題画像 1」が 1 枚。回答後「正解です！」の下の解説の枠に「解説:」と解説文、画像が 2 列で「解説画像 1」「解説画像 2」（古い形式の画像は出ない）。P2: 「問題画像 1」が 1 枚・回答後「解説画像 1」が 1 枚（横幅いっぱい・高さ 300 まで）。P3: 回答後の解説の枠に「解説:」の文字は無く、「解説画像 1」だけが出る。どの回答でも「回答の送信に失敗しました」のトーストは出ない。コンソールに新しい `error` が無い（既知の `/api/settings/` の 401 を除く） | Claude |  |  |
| 3 | No.2 の P1 の回答後に「解説画像 2」をクリックし、閉じる。次に「解説画像 1」に Tab でフォーカスを当てて Enter を押す | クリックで黒い背景の拡大の画面（ダイアログ）が開き、押した画像が大きく出る。右上の閉じるボタンで閉じる。Enter でも同じ拡大の画面が開く | Claude |  |  |
| 4 | 問題管理（`/quiz-management`）で科目「I472確認用」の P1 と P3 のプレビューを開く | P1: 「問題画像 1」・解説の下に「解説画像 1」「解説画像 2」（No.2 のクイズと同じ並び・同じ画像）。P3: 解説文が無いので解説画像は出ない（今までどおり） | Claude |  |  |
| 5 | 後片付け: `manage.py shell` で P1〜P3 を 1 件ずつ取り出し、`is_deleted = True` にして `save()` する | 出力に 3 件の ID と `is_deleted=True` が出る。`/quiz?subject=<科目「I472確認用」の ID>` を開くと「この科目には問題が登録されていません」のトーストが出てダッシュボードに戻る | Claude |  | 物理削除は危険操作に当たるため論理削除にする（計画 7 章）。科目・MediaAsset の行と写した画像は dev に残る |

## 画面確認
| 日時 | コミット | 画面と操作 | アカウント | 期待した結果 | 実際の結果 | 画像 |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

結論: OK / NG
