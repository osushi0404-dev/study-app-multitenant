# I472 手動テスト: 解説画像がある問題へのクイズの回答の 500 を直し、新しい形式の解説画像と問題の画像もクイズで表示する

- 関連: docs/plans/open/plan_I472.md / Draft PR #474
- 実施: test-gate 段階で Claude が行う（画面は Playwright MCP・`docs/runbooks/frontend-verify.md`）。アカウントは `e2e_user_a@example.com`（組織 A・管理者。問題管理のプレビューも開けるため）
- 確認用のデータ（No.1 で作る）: 組織 A に科目「I472確認用」（slug `i472-check`）を作り、次の 3 問を入れる。画像は `backend/media/bk/problems/aws-saa/questions/q02_problem.png` を写して使う（中身の違う png がこれ 1 種類だけのため、新旧は `src` の URL で見分ける）
  - P1「I472 新しい形式」: 問題用 MediaAsset 1 枚・解説用 MediaAsset 2 枚（`position` 1・2）・古い形式の `explanation_image` も入れる
  - P2「I472 古い形式」: 古い形式の `question_image`・`explanation_image` だけ（ファイルは `org/<組織 A の slug>/subjects/i472-check/problem/`・`explanation/` に写す）
  - P3「I472 解説文なし」: `explanation=''`・解説用 MediaAsset 1 枚だけ

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | 確認用のデータを作るコード（上の P1〜P3・選択肢は正解 1・不正解 1。`.delete()`・一括 `update()` は使わない）をスクラッチパッドの `i472_seed.py` に書き、`docker compose cp <その絶対パス> backend:/tmp/i472_seed.py` で送り、`docker compose exec -T backend python manage.py shell --command "exec(open('/tmp/i472_seed.py').read())"` で 1 コマンドずつ実行する（ヒアドキュメント・パイプでまとめない） | シェルの出力に科目の ID と P1〜P3 の問題の ID・MediaAsset の ID が出て、例外が出ない | Claude | OK | 16:14 実施（implement）。出力 `subject 20 I472確認用`・`problems 41 42 43`・MediaAsset 4 件の ID。例外なし |
| 2 | `npm run typecheck` を通した後、e2e_user_a でログインし、ダッシュボードから科目「I472確認用」のクイズを始める。出た問題ごとに選択肢「正解」を押して回答し、「次の問題」で 3 問を答える | P1: 回答の前に問題文の下へ「問題画像 1」が 1 枚。回答後「正解です！」の下の解説の枠に「解説:」と解説文、画像が 2 列で「解説画像 1」「解説画像 2」（古い形式の画像は出ない）。P2: 「問題画像 1」が 1 枚・回答後「解説画像 1」が 1 枚（横幅いっぱい・高さ 300 まで）。P3: 回答後の解説の枠に「解説:」の文字は無く、「解説画像 1」だけが出る。どの回答でも「回答の送信に失敗しました」のトーストは出ない。コンソールに新しい `error` が無い（既知の `/api/settings/` の 401 を除く） | Claude | OK | 16:35 実施（レビュー済みの `b63ddcdb` の画面）。P3 → P2 → P1 の順に出た。P1: 「問題画像 1」・回答後「解説:」「P1 の解説」と「解説画像 1」「解説画像 2」（2 列・`390px 390px`）、`i472_p1_legacy.png` は出ない。P2: 「問題画像 1」（`i472_p2_qlegacy.png`）・回答後「解説画像 1」（`i472_p2_elegacy.png`・1 列 `788px`）。P3: 結果の枠は「正解です！」と「解説画像 1」だけ（「解説:」なし）。失敗のトーストなし。コンソールの error は開発サーバーの自動再読み込みの接続（`ws://localhost:3000/ws`）だけで、既知の環境の事情 |
| 3 | No.2 の P1 の回答後に「解説画像 2」をクリックし、閉じる。次に「解説画像 1」に Tab でフォーカスを当てて Enter を押す | クリックで黒い背景の拡大の画面（ダイアログ）が開き、押した画像が大きく出る。右上の閉じるボタンで閉じる。Enter でも同じ拡大の画面が開く | Claude | OK | 16:35 実施。クリックで `i472_p1_e2.png` の拡大の画面、Esc で閉じた。「解説画像 1」にフォーカスして Enter で `i472_p1_e1.png` の拡大の画面が開いた。Tab の代わりに要素の `focus()` でフォーカスを当てた（Tab の回数は画面の部品の数で変わるため） |
| 4 | 問題管理（`/quiz-management`）で科目「I472確認用」の P1 と P3 のプレビューを開く | P1: 「問題画像 1」・解説の下に「解説画像 1」「解説画像 2」（No.2 のクイズと同じ並び・同じ画像）。P3: 解説文が無いので解説画像は出ない（今までどおり） | Claude | OK | 16:35 実施。P1: 「問題画像 1」「解説画像 1」「解説画像 2」（クイズと同じ URL）。P3: 画像 0 枚 |
| 5 | 後片付け: No.1 と同じ渡し方（`i472_cleanup.py` を `/tmp/` に送って `manage.py shell --command`）で P1〜P3 を 1 件ずつ取り出し、`is_deleted = True` にして `save()` する | 出力に 3 件の ID と `is_deleted=True` が出る。`/quiz?subject=<科目「I472確認用」の ID>` を開くと「この科目には問題が登録されていません」のトーストが出てダッシュボードに戻る | Claude | OK | 16:35 実施。出力 `41 I472 新しい形式 is_deleted=True`・42・43 も同じ。`/quiz?subject=20` で「この科目には問題が登録されていません」が出て `/dashboard` に戻った。物理削除は危険操作に当たるため論理削除にした（計画 7 章）。科目・MediaAsset の行は dev DB に残る。写した画像 7 枚は、git の対象のフォルダに残さないよう作業ツリーの外（スクラッチパッド）へ移した |

## 画面確認
| 日時 | コミット | 画面と操作 | アカウント | 期待した結果 | 実際の結果 | 画像 |
|---|---|---|---|---|---|---|
| 2026-11-12 16:15 | ce52f5bb | implement: `/quiz?subject=20`（I472確認用）で P2「I472 古い形式」に回答 | e2e_user_a | 問題画像 1 枚・回答後「正解です！」と古い形式の「解説画像 1」（直す前は 500 になる問題） | 「問題画像 1」（`…/problem/i472_p2_qlegacy.png`）・回答後に「解説画像 1」（`…/explanation/i472_p2_elegacy.png`・1 列）。失敗のトーストなし | quiz-p2-question-a-1.png, quiz-p2-answer-a-2.png |
| 2026-11-12 16:15 | ce52f5bb | implement: 同じ回で P1「I472 新しい形式」に回答し、「解説画像 2」をクリック、「解説画像 1」にフォーカスして Enter | e2e_user_a | 新しい形式の問題画像 1 枚・解説画像 2 枚が 2 列（古い形式は出ない）。クリックと Enter で拡大 | 「問題画像 1」（`i472_p1_q1.png`）・「解説画像 1」「解説画像 2」（`i472_p1_e1.png`・`e2.png`・2 列）、`i472_p1_legacy.png` は無し。クリックで `e2`、Enter で `e1` の拡大の画面が開いた | quiz-p1-answer-a-3.png, quiz-p1-modal-a-4.png |
| 2026-11-12 16:16 | ce52f5bb | implement: 同じ回で P3「I472 解説文なし」に回答 | e2e_user_a | 解説の枠に「解説:」は無く「解説画像 1」だけ | 結果の枠は「正解です！」と「解説画像 1」（`i472_p3_e1.png`）だけ。コンソールの error は開発サーバーの自動再読み込みの接続（`ws://localhost:3000/ws`・ポートの違い）だけ | quiz-p3-answer-a-5.png |
| 2026-11-12 16:16 | ce52f5bb | implement: `/quiz-management` で P1 と P3 のプレビュー | e2e_user_a | P1 は問題画像 1・解説画像 2（クイズと同じ）、P3 は解説画像なし | P1: 「問題画像 1」「解説画像 1」「解説画像 2」（クイズと同じ URL）。P3: 画像なし（今までどおり） | preview-p1-a-6.png |
| 2026-11-12 16:35 | b63ddcdb | test-gate: `/quiz?subject=20` で P3「I472 解説文なし」に回答 | e2e_user_a | 解説の枠に「解説:」は無く「解説画像 1」だけ | 「正解です！」と「解説画像 1」（`i472_p3_e1.png`）だけ | tg-quiz-p3-answer-a-1.png |
| 2026-11-12 16:35 | b63ddcdb | test-gate: 同じ回で P2「I472 古い形式」に回答 | e2e_user_a | 問題画像 1 枚・回答後に古い形式の「解説画像 1」（直す前は 500 になる問題） | 「問題画像 1」（`i472_p2_qlegacy.png`）・回答後「解説画像 1」（`i472_p2_elegacy.png`）。失敗のトーストなし | tg-quiz-p2-answer-a-2.png |
| 2026-11-12 16:35 | b63ddcdb | test-gate: 同じ回で P1「I472 新しい形式」に回答し、「解説画像 2」をクリック、「解説画像 1」にフォーカスして Enter | e2e_user_a | 新しい形式の問題画像 1・解説画像 2 枚が 2 列（古い形式は出ない）。クリックと Enter で拡大 | 「問題画像 1」・「解説画像 1」「解説画像 2」（2 列）、古い形式は無し。クリックで `e2`、Enter で `e1` の拡大の画面 | tg-quiz-p1-answer-a-3.png, tg-quiz-p1-modal-a-4.png |
| 2026-11-12 16:35 | b63ddcdb | test-gate: `/quiz-management` で P1 と P3 のプレビュー | e2e_user_a | P1 は問題画像 1・解説画像 2（クイズと同じ）、P3 は解説画像なし | P1 は 3 枚（クイズと同じ URL）、P3 は 0 枚 | tg-preview-p1-a-5.png |

結論: OK（Claude の 5 項目すべて OK・Human の項目なし）
