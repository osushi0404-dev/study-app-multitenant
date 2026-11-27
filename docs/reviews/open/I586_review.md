# I586 レビュー: 勉強用の環境と DB スペシャリスト午前Ⅱ（令和6年度秋期）の過去問の登録

## 変更概要
- 勉強用のワークツリー（`study`）に本人の利用者・科目「データベーススペシャリスト」を作り、令和6年度 秋期 DB 午前Ⅱ の 25 問（出典・難易度・Claude 作成の解説付き・図表 8 問は画像）を登録した。リポジトリには手順書と記録だけを入れた

## 変更点
- `docs/runbooks/worktree.md` §11（勉強用のワークツリーの作り方・使い方の決まり・控え・本人の利用者での操作・過去問の扱い・道具の注意）
- `docs/issues/open/I586.md`・`docs/plans/open/plan_I586.md`・`docs/tests/open/I586_*.md`・`docs/reviews/`（記録）

## 影響範囲
- Backend/Frontend/DB/Config: コードの変更なし。データは `study` の DB にだけある（問題の Markdown・画像・PDF は `.evidence/I586/exam/`〔git の対象外〕）

## テスト結果
- 自動: 決定論ゲートなし（`I586_auto_test.md` に理由）
- 手動: MT-01〜MT-13 は OK（`I586_manual_test.md`）。MT-14（Human・本人の使い心地）はユーザーに依頼中
- test-gate: `gate-check.sh` OK・記録の判定 2 つ OK（2026-11-24）

## 使いにくさの候補
- 一覧は `docs/tests/open/I586_manual_test.md`「## 使いにくさの候補」（画像の選択肢の見比べ・画像が小さく拡大が画面に収まらない・正解数の表示が遅れる・プレビューの記号の重複・管理一覧の並び・DB を直接直したときの一時保存）。MT-14 の感想を足し、retro で起票か同梱かを決める

## 計画との差分
- あり: 会員登録をユーザーではなく Claude が Playwright で行った（ユーザーの指示）。問3 の解説の言い換え（`⇄` が化けるため・意味は同じ）

## ロールバック
- リポジトリは docs だけなので revert。`study` の DB のデータは、問題管理の画面で消す（多くを消すときは danger-ops の承認制・先に `bash scripts/claude/db-backup.sh`）

## 自律判断の記録
<!-- 各段階が、止めずに自分で決めたことを `- [段階] 決めたこと — 理由` で足す。段階の結線の行（STAGE_DONE:）はこのファイルの末尾に足す -->
- [plan] ブランチは既にあった `feature/I586-study-worktree-past-exams` を使い、最新の develop（853a6283）にそろえた — skill の `git checkout -b` の代わり。そろえる途中、`git merge` を後ろにつないで流したためサンドボックスの中で動き `.claude/hooks/` を書けず止まった。ユーザーに `! git reset --hard origin/develop` を流してもらった（#615 に事例のコメント）
- [plan] 手順書は `docs/runbooks/worktree.md` に §11 を足す — 新しいファイルにすると `CLAUDE.md` の参照先も増えるため
- [plan] 作業の置き場所は `.evidence/I586/exam/`（git の対象外）— サンドボックスの中から書け、`$TMPDIR` と違って消えないため
- [plan] 図の切り出しは使い捨てのコンテナの `pdftoppm` — ホストに道具が無く、スパイクで成立を確かめた
- [plan] 決定論ゲートは置かない — 手順書と記録だけの変更で、守る決まりは `.gitignore` が担うため
- [plan-review] 計画レビューの Warning 4 件を直した（解説の変更を計画変更記録に書く・画像を渡せるかをステップ 3 で先に試す〔MT-04b〕・（一部改変）の問の表を作業の記録に足し MT-10 で突き合わせる・MT-02 に選択肢と正解の数）。再レビューはしない — 方式・範囲・受け入れ条件を変えないため。Info 2 件はそのまま（MT-11 の拡大は、できなければ使いにくさの候補に入れる）
- [implement] 会員登録は Claude が Playwright で行った（ユーザー ID とメールは本人のもの）— ユーザーが「playwright であなた自身でできるんじゃないの？」と指示。開発の設定（DEBUG）ではメールは送られない（`send_verification_email` が出力するだけ）。ID とメールは記録に書かない
- [implement] `--secrets` の値が空と読まれて名前のまま入った 2 回は、登録ボタンを押さずに欄を空に戻した。値の中身は見ず、名前と同じか・8 文字以上かだけを真偽で確かめた — パスワードを会話に出さないため
- [implement] MT-10 は `APIClient` を本人の利用者で認証して `/api/problems/` を読む形にした — 計画の「API から読み出す」を、トークンを扱わずに満たすため。難易度は API が名前で返すので名前で比べた
- [implement] 問3 の解説の `⇄` を言い換え、DB は `manage.py shell` で 1 行だけ直して一覧の一時保存を消した — 画面で直すより確実に同じ文にできる。意味は変えていないので点検（MT-06）はやり直さない
- [implement] MT-11 の 5 問目まででクイズを「終了」した — 計画の「5 問以上・図 2 問以上」を満たしたため

- [implement] /simplify は点検役を起こさず 4 観点を自分で見た — 差分が文書 3 ファイル・45 行だけのため。高さの指摘 1 件（`.env.e2e` の値を `'` で囲む・つなぎ直す話は `--secrets` 全般の話なので `frontend-verify.md` §9 が本来の置き場所）は計画の範囲外なので直さず、retro で同梱か起票かを決める

- [review-gate] 基本レビューは OK（`docs/reviews/I586_code_review_20261124_0257.md`・CI OK・敵対的レビューは不要）。Low 4 件（F1 計画書のフォルダのパス・F2 `.env.e2e` が backend にも読まれる・F3 `'` を含むパスワードの書き方・F4 計画変更記録の事後の行）は止めない指摘なので直さず retro へ — 台帳の決まり（I197）

- [test-gate] Claude 担当の MT-01〜MT-13 は implement の中で済ませた結果をそのまま使う — レビュー済みの HEAD 以降はコードもデータの手順も変えていないため

- [fix-loop] MT-14 の NG（記号と本文がくっついて見える）は、ユーザーが選んだ「データで区切る＋アプリは起票」で直した（診断メモ `docs/reviews/I586_fix_diagnosis_20261127_1436.md`・診断レビュー PASS `I586_fix_diagnosis_review_20261127_1440.md`。その前の 1437 の記録は、コマンドを後ろにつないでサンドボックスの中で動き未実施〔SKIP〕になった回）。計画の受け入れ条件・方式・範囲は変えないので計画レビューは通り直さない（計画変更記録に書いた）
- [fix-loop] アプリの改善を #645（記号を本文と分けて出す・選んだ誤答に印）、画面に primary のエラーが重なる件を #644（自動更新の通信路のポート）に起票した — どちらも I586 の範囲（データと手順書）の外
- [fix-loop] クイズの画面での確かめはせず、問題管理のプレビューと API の照らし合わせで確かめた — ユーザーが解いている途中のクイズの記録を壊さないため。画面の見え方は MT-14 の再テストでユーザーが見る

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: human-test
STAGE_DONE: human-test NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
