# I492 レビュー: 古い学習記録の表（StudyLog など）の片付け

## 変更概要
- 使われなくなった古い学習記録の表（`StudyLog`・`DailyStudySummary`・`StudyGoal`・`ProblemAttempt`）と、それを読む・書くコード（学習記録の API・管理画面・学習リマインダーのメール・呼ばれていない 2 つのタスク）を消し、`SpacedRepetitionReview.study_session` の列と 4 つのテーブルを消すマイグレーションを足す（Danger Ops）。夜 2 時の学習分析の更新の対象を、クイズの答えか復習で判定する形にする

## 変更点
- `backend/studylogs/tasks.py`: `update_daily_analytics_task` の対象を、直近 7 日に `QuizAnswer` か `SpacedRepetitionReview` がある利用者（2 つの `id__in` の副問い合わせ）にした。`send_study_reminders_task`・`export_user_data_task` を消した
- `backend/core/tasks.py`: `generate_system_report_task` を消した。`backend/core/celery.py`: `send-study-reminders` の登録を消した
- `backend/studylogs/views.py`・`urls.py`・`serializers.py`: 学習記録・統計・目標の 3 つの API と 7 つのシリアライザを消した。`submit_review`・`services.review_card` から `study_session` を外した
- `backend/studylogs/admin.py`: 4 モデルの登録しか無かったのでファイルごと消した
- `backend/studylogs/models.py`: `StudyLog`・`DailyStudySummary`・`StudyGoal`・`ProblemAttempt` と 2 つの QuerySet、`SpacedRepetitionReview.study_session` を消した
- `backend/studylogs/migrations/0002_remove_legacy_study_logs.py`（新規・Danger Ops）: 列の削除と 4 モデルの削除の 5 つの操作。開発の DB にはまだ流していない
- テスト: `test_I492_remove_legacy_study_logs.py`（新規・TC-05〜TC-08）。I446・I431・I455・I466・I473 のテストを、消したモデル・経路に合わせて直した

## 影響範囲
- Backend/Frontend/DB/Config: Backend（`studylogs`・`core/tasks.py`・`core/celery.py` とテスト）・DB（列 1 つとテーブル 4 つ〔と多対多の表〕の削除）・Config（Celery の定期処理の登録から `send-study-reminders` を外す）。Frontend なし

## テスト結果
- 自動: 手元で backend 全件 passed（768 件・/simplify の前）。決定論ゲート 4 行とも exit 0。CI は review-gate で記入
- 手動: （test-gate で記入）

## 計画との差分
- あり（計画書の計画変更記録のとおり。方式・範囲・受け入れ条件は変えていない）: I431・I455 のテストの直し方の具体化と訂正、`update_daily_analytics_task` のクエリの書き方（副問い合わせ）、`admin.py` をファイルごと削除、新しいテストで共有の `answer` を使用

## ロールバック
- 計画書 `docs/plans/open/plan_I492.md` の 7

## 自律判断の記録
- [plan-review] 計画レビューは HIGHRISK（DB スキーマの重要な変更・API 経路の削除）。Warning 2 件（TC-04 の記録・R1 の確かめの追加）は計画書とテスト文書に追記し、方式・範囲を変えないので再レビューしない — 計画変更記録のとおり
- [design-security-review] Blocker・High・Medium は無し、Low 4 件（バックアップの置き場所・既存の `str(e)`・利用者の選び方・管理画面の削除）は計画のままで守れるので計画を変えない — 計画書「## セキュリティレビュー結果」
- [implement] ステップ 1: 実装の前の開発の DB の件数は StudyLog 0・DailyStudySummary 0・StudyGoal 0・ProblemAttempt 0・SpacedRepetitionReview 6（study_session あり 0）。バックアップは `.evidence/I492/legacy_backup.json`（0 件・gitignore 済み）— Danger Ops の消す前の記録（AC7）
- [implement] `makemigrations` が出した 12 個の細かい操作を、同じ結果になる 5 つ（列の削除→4 モデルの削除）に書き直した — 計画の 4 の表のとおり。`makemigrations --check` が「No changes detected」で、状態が同じことを確かめた
- [implement] I431 の TC-22 の材料を `StudyLog` から `QuizSession` に、I446 の失敗の注入を目標の経路から復習の記録の経路に、I455 の例文のモデル名を残るモデルに替えた — 消したモデル以外の確かめ（境界の関数・絞り込みを外すと落ちること・コメントの検査）を失わないため（計画変更記録）
- [implement] /simplify の結果: 共有のテスト用データ `problems.tests.i466_data.answer` を使う・利用者の選び方を副問い合わせにする・空の `admin.py` を消す・定期処理のコメントを決まりだけにする、を直した。直さなかったもの: TC-07 の操作の比べを `describe()` の文字列にする案と、`LEGACY_TABLES` をモデルから導く案 — 手で書いた一覧のほうが、マイグレーションと独立した確かめになるため
- [implement] 開発の DB には `0002` を流していない（M3 で `[ ] 0002` を確認）。コンテナも起こし直していない — 計画書 8 の R1・9 の Danger Ops
- [review-gate] 1 回目: CI の E2E Tests (Playwright) が失敗（run 44207144182）。ほかの CI のジョブは通過。`CI_WAIT: FAIL` なので fix-loop へ回す — 手順どおり
- [fix-loop] E2E の失敗の原因は I492 の変更ではない: 2026-11-17 午後から `ubuntu-latest` が Ubuntu 26.04 になり、`@playwright/test` 1.59.1（26.04 に非対応。1.65.1 は対応）がブラウザを入れる段で止まる。I492 の中では直さず、既存の #432（Dependabot #377 の Playwright の版上げを取り込む）を最優先に前倒しして直す。I492 はここで止め（STAGE_DONE を書かない）、#432 のマージの後に develop を取り込んで `/proceed I492` で再開する — ユーザーの方針「ハーネス・ループの BP の観点でベストなやり方で」（2026-11-18）。実行環境を古い版に固定する案はユーザーの指摘（古い版でテストし続けるのは BP ではない）で採らない。#432 に経緯をコメント済み
- [fix-loop・ユーザーの BP・UI/UX の確認（2026-11-18）] 設定画面の「メール通知」の切り替えは前から読まれておらず、I492 でメールの機能も無くなったので、何もしない切り替えになる。ユーザーの決定で別イシュー #574（I574）で画面から消す（同じく読まれていないプッシュ・実績・リマインダーの切り替えの扱いは #574 の grill-me）。I492 の範囲（バックエンドだけ）は変えない。retro で一覧に回すもの: 復習の提出の `str(e)` を応答に入れる箇所・定期処理の f-string のログ。本番ができた後の表の削除は、コードの削除と表の削除を別のデプロイに分けるのが BP（今回は本番が無く 1 回で行う）

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
- [fix-loop] 案 A（develop をマージで取り込む）で直した — 診断レビュー PASS（docs/reviews/I492_fix_diagnosis_20261118_1520.md）。rebase は送り済みのコミットを書き換え強制の push が要るので採らない。1 回目の取り込みは、私がパイプをつないでサンドボックスの中で動かし `docker-compose.yml` を置き換えられず中止になった。途中で書き出された I432 の記録の写し 13 個は develop と同じ中身と確かめて消し、つながない形で取り込み直した
STAGE_DONE: fix-loop NEXT: review-gate
- [review-gate] 2 回目（develop の取り込みの後）: CI_WAIT: OK（E2E を含む全ジョブ成功・I492 の変更込みで E2E が初めて通った）・FINAL_VERDICT: OK（Low 6 件・止める指摘なし。retro で振り分ける）・敵対的レビュー OK（docs/reviews/I492_adversarial_review_20261118_1528.md・新しい Critical/High なし・未検証 0）
STAGE_DONE: review-gate NEXT: test-gate
- [test-gate] M3 の確かめ直しで、開発の DB に `0002_remove_legacy_study_logs` が流れていた（`showmigrations` が `[X]`）。backend のログで 2026-11-18 15:27:54 に「Applying studylogs.0002_remove_legacy_study_logs... OK」。review-gate の `adversarial-review.sh` が、ブランチに backend/ の変更があるので確かめ用に backend のコンテナを起こし、起動の `migrate`（docker-compose.yml:70）が流した＝計画書 8 の R1 がハーネスの手順で起きた。被害: 消えた 4 つの表は M1 で 0 件・バックアップ（`.evidence/I492/legacy_backup.json`・空）あり。`SpacedRepetitionReview` の `study_session` の列は 0 件が入っていた（6 行は残る）。本番は無い。承認の前に Danger Ops が実行されたので、止めてユーザーに確かめる（止める条件 2）。STAGE_DONE は書かない
- [test-gate] 開発の DB に承認の前に 0002 が流れた件は、ユーザーの判断「このまま進める (Recommended)」（2026-11-18・選択肢: このまま進める／開発用の DB を元に戻す／I492 をここで止める）で受け入れた。Danger Ops の承認（danger-approved）はマージ依頼のときに改めてお願いし、この経緯も報告する。仕組みの穴（adversarial-review.sh のコンテナの起動が、承認の前のマイグレーションを流す）は retro でハーネスの最優先として起票する
STAGE_DONE: test-gate NEXT: retro
- [retro] 台帳の残り: F1・F2・F3・F5・F6（アプリ本体の Low）→ #580（I580・I492 のレビューの残り）。F4（見張りの語の表・計画 R7 で受け入れ）→ `docs/reviews/backlog/I492.md`。判定の仕組みに関わる行・SECURITY=yes の行は無い
- [retro] 改善案「検証のスクリプト（adversarial-review.sh）が backend のコンテナを起こすと、起動の migrate が承認の前の危険なマイグレーションを開発の DB に流す」→ 採用（新規起票 I579・#579・次のハーネスの作業で最優先）— 実害あり（承認の前に Danger Ops が実行された。今回はデータの損失なし）・計画の R1 の回避策が手順の約束だけで、ハーネス自身の手順が破った。決定論の守りで塞げる・同梱できる既存のイシューが無い
- [retro] 改善案「CI の E2E が実行環境の切り替え（Ubuntu 26.04）で止まった」→ 既存の対応で済み（I432・PR #575 で直した。必須チェック化は #576・action の版上げは #577）
- [retro] 改善案「私が `git merge` にパイプをつないでサンドボックスの中で動かし、取り込みが途中で止まって未追跡のファイルが残った」→ 見送り — develop と同じ中身と確かめて消し、つながない形で取り込み直して手戻りは小さい。書き方の問題は #538 の範囲（手順書の側）で、私の書き方を決定論で止める先が無い
- [retro] 残余リスク処遇: 計画・セキュリティ設計レビューの残りは計画どおり（R1 は起きたがユーザーの判断で受け入れ・再発防止は #579）
- [retro] 設計ルール昇格: #579 の計画で、計画レビュー役（plan-reviewer）の観点に「Danger Ops を含む計画で、ハーネスの手順（検証のスクリプト）がコンテナ・DB に触れるか」を足すかを決める（#579 の本文の根本原因 3 点目）

## 振り返り（I492・2 回目の review-gate の後）

### かんたんなまとめ
- 良かった点: CI の E2E が止まった原因が I492 ではないと切り分け、先に I432 で直してから develop を取り込んだので、I492 の変更込みの E2E が 1 回で通った（理由: 古い版に固定するなどの回り道をせず、元から直したため）
- 今回の問題への直接の対処: 古い表を消す DB の変更が、承認の前に開発用の DB に流れた。確かめのスクリプトが backend のコンテナを起こし直し、起動のたびに DB の変更を流す仕組みが動いたため。消えた表はどれも 0 件で、バックアップもあり、データの損失は無い。あなたの判断で「このまま進める」にした
- 同じ問題を次回から防ぐ改善: 計画では「コンテナを起こし直さない」という約束で防ぐつもりだったが、ハーネス自身の確かめの手順がそれを知らずに起こし直した。約束ではなく仕組みで止めるイシュー #579 を立て、ハーネスの最優先にした
- 残りの軽い指摘: アプリ側の 5 件は #580 にまとめ、見張りの 1 件は一覧に残した

### 詳細
#### 是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | 予期しない問題 | adversarial-review.sh の `ensure_backend_container` がコンテナを起こし、起動の migrate が 0002 を流した | 被害を確かめ（4 表 0 件・バックアップあり）、ユーザーの判断で受け入れた。マージ依頼で danger-approved を改めてお願いする |

#### 予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| P1 | スキル・規約 | 検証のスクリプトがコンテナを起こすときに、まだ流していない危険な DB の変更を確かめる仕組みが無い。計画の回避策が手順の約束だけだった | ハーネスのスクリプトがコンテナを起こす前に、流していないマイグレーションがあれば止める（または流さずに起こす）決定論の守りと、失敗の注入つきのテストを足す（#579） | `scripts/claude/adversarial-review.sh`・`scripts/claude/tests/` |

#### 5 Whys: 承認の前に開発の DB へ危険な変更が流れた
- Why 1: backend のコンテナが起こし直され、起動の migrate が 0002 を流した
- Why 2: review-gate の敵対的レビューのスクリプトが、実験のために backend のコンテナを起こす（I486）
- Why 3: そのスクリプトは、ブランチにまだ流していない危険なマイグレーションがあるかを見ずに起こす。計画の R1 の回避策は「このイシューの中で起こし直さない」という手順の約束で、ハーネスの手順がそれを守る仕組みが無かった
- 抽象化: 「危険操作の承認を、手順の約束でなく仕組みで守っていない場所が、ハーネスの自動の手順の中にある」は他のイシューでも成り立つ → 予防処置（#579）
STAGE_DONE: retro NEXT: close
