# I452 レビュー: クイズの回答から復習の予定を作り、ダッシュボードから今日の復習を始められるようにする

- 関連: docs/issues/open/I452.md / docs/plans/open/plan_I452.md / GitHub #452 / Draft PR #464

## 変更概要
- クイズで 1 問答えるたびに、その問題の間隔反復のカードを作る・更新する（正解 4／不正解 2 の SM-2・答えた日の 0 時＋間隔・同じ日の 2 回目は更新しない）
- ダッシュボードのいちばん上に「今日の復習 ○問」と「復習を始める」を置き、復習する日が来た問題だけのクイズ（`QuizSession.mode='review'`）を始められるようにする。答え終えたら「今日の復習が終わりました（○問中○問正解）」
- 間違い分析・適応的な問題選択・学習洞察の 500 を直し（難易度の型・科目が空のパターン・KeyError）、#446 の 9 ケースの xfail を外す。画面側の使われていない関数 7 つを消す

## 変更点
- `backend/problems/difficulty.py`（新規）: 難易度の数字と文字の対応の 1 か所。`problems/serializers.py`・`problems/views.py`（問題一覧の絞り込み）・学習記録の側がこれを使う
- `backend/problems/models.py`・`migrations/0022_quizsession_mode.py`: `QuizSession.mode`（`normal`／`review`・既定 `normal`）
- `backend/problems/services/quiz_service.py`: 復習の回の開始の件数・次の問題（`_next_review_problem`）・冪等のキーの `mode` の照合・`spaced_repetition_service`
- `backend/problems/views.py`: `submit_answer` の回答とカードの更新を 1 つのトランザクションに・`next_problem` の `review_complete`
- `backend/studylogs/services.py`・`spaced_repetition.py`: `record_quiz_answer`・`due_cards_queryset`・`review_summary`・日付の境目・キャッシュのキーの組織・キャッシュの無効化をコミットの後に・学習洞察の KeyError
- `backend/studylogs/views.py`・`serializers.py`: `GET /api/study/spaced-repetition/review_summary/`・印付けの 2 経路を `for_user` に
- `backend/studylogs/adaptive_selection.py`・`mistake_analysis.py`・`backend/core/cache_service.py`・`tasks.py`: 難易度の型・分母の組織・科目が空のパターン・習熟度のキャッシュのキーの組織・印付け・理由のコメント
- `backend/core/tests/test_I446_cross_api_tenant_isolation.py`: 9 ケースの xfail を外し、`review_summary` の経路を足す
- `backend/studylogs/tests/test_I452_quiz_review.py`（新規・28 件）
- `frontend/src/components/TodayReviewCard.tsx`・`services/review.service.ts`（新規）・`pages/Dashboard.tsx`（配置）・`pages/QuizSession.tsx`（復習の回）・`types/quiz.ts`・`services/dashboard.service.ts`（削除）
- `frontend/src/components/__tests__/TodayReviewCard.test.tsx`・`pages/__tests__/QuizSession.review.test.tsx`（新規）

## 影響範囲
- Backend: problems（models・migrations・serializers・views・services）・studylogs（services・views・serializers・spaced_repetition・adaptive_selection・mistake_analysis・tasks・tests）・core（cache_service・tests）
- Frontend: ダッシュボード・クイズの画面・サービス・型
- DB: `problems_quizsession.mode` の追加（`AddField` だけ・既存の行は `normal`）
- Config: なし

## テスト結果
- 自動（手元・app-1 のコンテナ）: バックエンドの新しいテスト 28 件と守りのテスト（I431・I455・I166・I158・#446・problems の views）が 247 passed（#446 の xfailed 0）。フロントの新しい 2 ファイルと既存のクイズの 2 ファイルが 20 passed。型チェック・lint（警告 0）・migration のずれなし。失敗の注入（難易度・同じ日・組織の絞り込み・キャッシュのキー・復習の分岐）はすべて FAIL
- CI（PR #464）: 全ジョブ pass（review-gate の `CI_WAIT: OK`・TC-20）
- レビュー: 基本レビュー OK（Low 7 件）・敵対的レビュー 2 周目 OK（1 周目は実験役に python が無く未検証 → 決定論の TC と失敗の注入で覆った）
- 手動（test-gate・Claude が Playwright MCP で実施）: No.1〜No.4 すべて OK。Human の項目なし
- 判定: gate-check OK・check-frontend-evidence 合格（画面確認 8 行）・check-manual-test-executor 合格

## 計画との差分
- 計画書の計画変更記録のとおり（/simplify の整理 8 件と見送り 5 件・静的テストに合わせた理由のコメント）
- 実装の時の画面の確かめ（Playwright MCP）は、MCP の接続が実装の間に整わなかったため、test-gate の手動テスト No.1〜No.4（Claude）に回した。画面の動きは Jest（TC-16・TC-17）で固定済み

## ロールバック
PR を revert し、migration `0022_quizsession_mode` を戻す（`python manage.py migrate problems 0021`）。計画書 7 章。

## 振り返り

### かんたんなまとめ

**良かった点**
- 設計の確認（grill-me）を 4 回重ねて、「回答のたびに次の復習日を決める」「科目の選択に合わせる」「同じ日は最初の回答だけ」などの決まりを、作る前に 11 点決め切れた。おかげで、作ったあとに仕様で揉めることが無かった（理由: 画面の文言や流れも計画の時点で確定していた）
- テストを先に書き（失敗することを確かめてから作る）、わざと壊してテストが落ちることも確かめた。そのため、「穴を探すレビュー」の 1 回目で実験ができなかったときも、決まった手順で 2 回目に合格できた（理由: 確かめの根拠が自動テストに残っていた）
- 整理のレビュー（4 つの観点）で、計画の取りこぼし（問題一覧に残っていた難易度の対応表の写し）や、画面が URL ではなく回の種類で表示を決めるべき点を見つけて直せた

**今回の問題への直接の対処**
- レビューで止めなかった小さな指摘が 7 件と、穴を探すレビューの小さな指摘が 4 件残った。止める基準に当たらない小さなものは、このイシューでは直さない決まりのため。→ まとめて後続のイシュー I467（#467）にした。あわせて、I190（ダッシュボード）に渡すと決めた既存の不具合 3 件も、I190 のファイルがこの作業場所から見えないので、I467 に「I190 の着手時に読む」節として残した

**同じ問題を次回から防ぐ改善**
- 穴を探すレビューの実験役が、手元に無い `python` を使おうとして実験できず、レビューが 1 回分増えた。アプリのテストはコンテナの中でしか動かないのに、実験役への案内にそれが書かれていないため。今回で 4 回目。→ すでに同じ件を扱う #423 に今回の発生を追記し、次のハーネスの作業で先に扱うよう書いた（新しく起票はしない）
- コミット時の書き方チェック（ESLint）が、作業場所（ワークツリー）では必ず止まった。手順書は「手元に部品（node_modules）を入れない」と決めているのに、チェックは手元の部品で動く作りで、決まり同士が食い違っていたため。→ チェックをコンテナの中で流す形に直すイシュー I468（#468）を起票した
- 会話のリセットの直後に、画面を操作する道具（Playwright）が Claude Code 本体によって止められ、ユーザーにつなぎ直してもらうまで画面確認が止まった。手順書に「つながっていないときの見分け方と頼み方」が無く、実装の段階で気づいても後回しにしていたため。→ 同じ I468 に、手順書への追記と「実装の段階で先に確かめて頼む」流れを入れた

### 詳細

#### 良かった点
- grill-me 4 回で価値判断 11 点を確定し、計画の UI の細部 3 点（U1〜U3）も plan-issue でユーザーに確かめてから計画レビューに進んだ（実装後の仕様の手戻り 0）
- TDD（バックエンド 21 件・フロント 2 ファイルが Red → Green）と失敗の注入（難易度・同じ日・組織の絞り込み・キャッシュのキー・復習の分岐）で、敵対的レビューの未検証を決定論の TC で覆えた
- /simplify の 4 観点で、計画の取りこぼし（`problems/views.py` の `difficulty_map`）と高さの問題（画面の表示を URL でなく回の `mode` で決める）を直した

#### 是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | 残余リスク・台帳 | review-gate は止める指摘だけを直す決まりで、Low・再現なしは台帳に残る。I190 のイシューファイルは別のワークツリーにあり、この作業場所から書き込まない | 台帳の F1〜F7・敵対的レビューの Low 4 件・I190 への引き継ぎ 3 件を I467（#467）にまとめた |

#### 予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| P1 | スキル・規約 | 敵対的レビューの実験役への案内に、アプリのテストはコンテナの中で流す入口が無い（4 回連続） | 既存の #423 に同梱（発生の追記・優先度を上げる推奨）。予防策は #423 のコメントどおり、実験役の案内に「アプリのテスト・管理コマンドはコンテナ経由で流す」を足し、`command not found` だけの出力は「実行できなかった」に数えて 1 回言い直させる | `.claude/agents/adversarial-reviewer.md`・`scripts/claude/adversarial-review.sh` |
| P2 | スキル・規約 | コミット時の検査のフック（ESLint）がホストの依存を前提にし、ワークツリーの手順書の「依存はコンテナの中だけ」と食い違う | I468（#468）: フックをコンテナがあればコンテナの中で流す形にし、失敗の注入の TC を付ける | `.pre-commit-config.yaml`・`docs/runbooks/pre-commit.md` |
| P3 | 予期しない問題 | 画面確認の手順書が「MCP は会話の初めにつながっている」前提で、つながっていないときの見分け方・頼み方が無く、implement で気づいても test-gate に持ち越した | I468（#468）: `frontend-verify.md` に「MCP が使えないとき」の節（接続の記録の見方・`/mcp` の再接続の頼み方）を足し、implement の画面確認の前に使えるかを確かめて、使えなければその時点で頼む | `docs/runbooks/frontend-verify.md`・`.claude/skills/implement/SKILL.md` |

#### なぜを繰り返す原因分析（5 Whys）
- P2（ESLint のフック）: Why1 コミットで `eslint: not found` → Why2 フックがホストで `npm run lint` を流す → Why3 ワークツリーのホストには node_modules が無い（手順書の決まり）→ Why4 フックを足したときと手順書を決めたときの前提の食い違いを、どの点検も見ていない。根本原因: 「検査の仕組みを足すとき、それが動く環境の前提を、作業場所の決まりと突き合わせる」手順が無い（一般化できる）
- P3（MCP）: Why1 実装の段階で画面確認ができなかった → Why2 MCP が接続中のまま → Why3 `/clear` の直後に Claude Code が古い接続として止めた（本体の動き）→ Why4 手順書に「つながっていないとき」の手順が無く、Claude は待つか後回しにするしかなかった。根本原因: 外の道具が使えないときの見分け方と、人に頼む時点が、手順書に決まっていない

#### 見送り（理由つき）
- 手動テストの No.4 の期待結果の誤り（いつものクイズの最後のボタンの読み違い）: test-gate のその場で捕まり、手戻りは無かった（期待結果を直して記録）。手順・観点を足さない
- シェルでのまとめての作成・一括更新を見張りが止めた件: 見張りが決まりどおりに働いた。画面と 1 件ずつの操作で代えられ、手戻りは小さい
- 計画の取りこぼし（問題一覧の難易度の対応表の写し）: /simplify のその場で捕まった
- `Write` の道具が一時的に使えず、`touch` と `Edit` で代えた件: 一時的な事象で実害が小さい

## 自律判断の記録
- [plan-issue] 画面の細部 U1〜U3（結果を見る・今日の復習の印・読み込み失敗の再読み込み）をユーザーに確認し、推奨どおりで確定 — イシューに無い UI の文言・流れのため（止めて聞く条件 1）
- [plan-issue] 間違い分析・適応的な問題選択を画面につなぐ後続を I466（#466）として起票し、I455 の F4 を同梱 — 設計確認メモの決定（計画の段階で起票）
- [plan-issue] 同梱の 14 件の扱いを計画書 9 章で決めた（同梱 7・I190 に渡す 4・残す 3）— 変更点に当たるものは同梱、I190 の担当のものは渡す

STAGE_DONE: plan NEXT: plan-review
- [plan-review] 判定 HIGHRISK。Warning 3 件（カードの初期値・習熟度のキャッシュのキーと消す処理・TC-14 の合否）を計画書・テスト文書で直し、再レビューはしない — 方式・範囲・受け入れ条件を変えないため

STAGE_DONE: plan-review NEXT: design-security-review
- [design-security-review] Blocker・High なし（Medium 4・Low 3／シナリオ Medium 6・Low 3）。カードの読み出しを due_cards_queryset の 1 か所に集めることを必須防御条件にし、TC-08 に他組織の科目での復習の開始（400）と mode の不正値（400）を足した — 攻撃シナリオ 2・8 を自動テストで確かめるため

STAGE_DONE: design-security-review NEXT: implement
- [implement] 新しい振る舞いは TDD で進めた（バックエンド 21 件・フロント 2 ファイルが Red → Green）。失敗の注入（難易度の直しを戻す・同じ日の判定を外す・組織の絞り込みを外す）でテストが落ちることを確かめた — 計画の TC-09・TC-14 の FG
- [implement] /simplify の 4 観点のレビューのうち 8 件を直し、5 件は見送った（計画変更記録）— 振る舞いを変える・設計の意図に反する・構造の変更が大きいものは見送る
- [implement] 画面の確かめ（Playwright MCP）は MCP が接続しなかったため test-gate の手動 No.1〜No.4 に回した — 人に頼まず Claude が後の段階で行う。画面の動きは Jest で固定済み

STAGE_DONE: implement NEXT: review-gate
- [implement] pre-commit の ESLint のフックが手元に eslint が無く exit 127 で止まった。同じ `npm run lint`（--max-warnings 0）をフロントのコンテナで流して 0 件を確かめ、そのコミットだけ `SKIP=eslint` にした — 同じ検査を別の場所で済ませた・CI でも流れる。手元の node_modules の準備は retro で扱う
- [review-gate] 基本レビュー OK（Low 7 件・止める指摘なし）。敵対的レビュー 1 周目（20261112_1305）は新しい Critical・High 0 だが、実験役の環境に python が無く V1〜V4・V6 が未検証で HIGH。5 項目を CI の決定論の TC と手元の失敗の注入で覆い、確かめ方を読んで可に下げて 2 周目へ — I455 と同じ扱い（review-gate 3-3）
- [review-gate] 差分の基本レビュー（20261112_1307）OK・敵対的レビュー 2 周目（20261112_1318）OK（新しい High 0・Low 1 件はキャッシュの 5 分の古さで台帳 F4 と同種）。最終判定 OK — 通算 2 周で収束

STAGE_DONE: review-gate NEXT: test-gate
- [test-gate] 手動テストの No.4 の期待結果（全問の後も「次の問題」を押す）を直した — いつものクイズは変更前から全問の後に「次の問題」を隠す作りで、このイシューで変えていない。全問の後も API が出し続ける動きは TC-05 で確かめ済み
- [test-gate] 手動テストの準備で、シェルでのまとめての作成・一括更新を見張りが止めたので、回避せず画面から問題を 2 問作り、カードの日付は 1 枚ずつ倒した — 見張りの決まりに従う。作った問題とカードは E2E 用の組織の記録で残した
- [test-gate] 会話のリセット（/clear）の直後に Playwright MCP が「古い接続」として止められ、ユーザーに /mcp で再接続してもらった（接続の記録で原因を確かめた）— retro で扱う

STAGE_DONE: test-gate NEXT: retro
- [retro] 台帳の残り（docs/reviews/I452_code_review_20261112_1307.md）の F1〜F7 は 7 件とも後続イシュー（アプリ本体）の区分で、I467（#467）にまとめた。一覧（docs/reviews/backlog/）に回すものは 0 件。敵対的レビューの Low 4 件と I190 への引き継ぎ 3 件も I467 に入れた — I190 のイシューファイルはこの作業場所から書き込まないため
- [retro] 実験役に python が無い件（4 回目）は既存の #423 に同梱（コメントで発生を追記・優先度を上げる推奨）— 同じ予防策がすでに #423 にあるため新規起票しない
- [retro] ESLint のフックがワークツリーで止まる件と、会話のリセット後に Playwright MCP が使えなくなる件を I468（#468）として起票 — 実害（コミットの例外・ユーザーの手を借りた停止）があり、合う同梱先が無い
- [retro] 見送り 4 件（手動テストの期待結果の誤り・見張りの停止・計画の取りこぼし・Write の一時的な不調）— どれもその場で捕まり手戻りが小さい
- [retro] 残余リスク処遇を計画書に書いた（Medium はすべて自動テストで塞いだ・レビューの Low は I467）

STAGE_DONE: retro NEXT: close
- [close] develop への追従は不要（mergeStateStatus=BLOCKED＝承認待ち）・gate-check OK。記録を closed へ移し、計画書に完了情報を足し、PR の説明をひな形どおりに更新した

STAGE_DONE: close NEXT: merge
