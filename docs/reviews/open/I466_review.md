# I466 レビュー: 間違い分析と苦手を優先した出題を画面につなぐ

## 変更概要
- ダッシュボードの「間違いやすい分野（全科目）」に、難易度別の苦手と急いだ間違いの 1 行を足す
- クイズに 3 つ目のモード `weak`（苦手を優先）を足し、「学習を開始」の副ボタンとおすすめの「練習する」から始める
- 苦手の判定を `backend/problems/services/weakness.py` にまとめ、材料を `QuizAnswer` にそろえる
- 使われない分析（保存型の間違い分析・適応的な問題選択の 2 つの API・その定期処理とキャッシュ）を消す（表は残す）
- 定期処理の間隔を本番の値（`crontab`）にする

## 変更点
- （実装後に書く。計画書 `docs/plans/open/plan_I466.md` の 4 章のとおり）

## 影響範囲
- Backend/Frontend/DB/Config: 計画書 3 章のとおり（DB は `QuizSession.mode` の選択肢の追加だけ）

## テスト結果
- 自動: （CI の結果を書く）
- 手動: （test-gate で書く）

## 計画との差分
- （実装後に書く）

## ロールバック
- PR を revert し、`python manage.py migrate problems 0022` で選択肢を戻す（データの変更なし）

## 自律判断の記録
- [plan] grill-me でユーザーが「BP・UI/UX の観点でベストなやり方で」と任せたので、画面の細部（「難易度別」の小見出しを科目別の一覧の下に置く・急いだ間違いは info の 1 行・「苦手を優先」の印・終えた回の「もう一度挑戦」は同じモード・2 周目も苦手を優先の並べ方）は止めずに決めた — 任された範囲で、既存のカード・印の作りにそろえるのが最も迷わない
- [plan-review] 計画レビュー OK（Warning 3 件）。3 件とも直した（難易度の対応は既存の difficulty.py を使う・4.7 に test_I473 の更新・TC-31 を 3 本に分ける）。再レビューはしない — 方式・範囲・受け入れ条件を変えない
- [implement] 確かめ用データに上級の問題と答えを shell のループで足す手順は、見張りが「ループでの一括作成」として承認を求めたので行わず、作り直しのコマンド（seed_dashboard_verify）のデータのまま期待値を DB から別に計算して見比べた — 承認の要る操作を確かめのためだけに求めない。上級・急いだ間違いの形は単体テストが受け持つ
- [implement] 急いだ間違いの 2 本目のクエリは当てはまらなくても流す（overview のクエリ数をデータで変えない I473 の決まりに合わせ、TC-12 の本数を 8 → 11）— 計画書 13 章の「条件を満たさなければ 1」は I473 の決まりと矛盾していた
- [implement] 「苦手を優先して始める」のボタンにアイコンと minHeight: 44 を足した — 主ボタンと見た目をそろえる・360px 幅の実測 42px が ux-rules.md の 44px に届かなかった
- [implement] /simplify（4 体）で直した: quiz.ts の改行コード（CRLF に戻した）・割合と集計式と答えの読み方を weakness.py の 1 か所に（selectors の _rate・_answer_counts・別名の定数を消した）・使われない CACHE_TIMEOUTS の 2 キー・難易度の表を utils/difficulty.ts の 1 つに（形の確かめもそれを使う）・% の表示は既存の formatRate・QuizStartMode を QuizMode から作る
- [implement] /simplify で見送った: ① 苦手を優先の 2 周目に並べた問い合わせを最大 3 回評価する・最後の答えの Subquery が 2 本（Medium・効率）— 本数は候補の数で増えず（TC-15）、通常のモードと共有している回の進み方の作りを変える大きさになるため。苦手を優先の利用が増えて遅さが見えたら別イシュー ② 件数と難易度別の 2 本の準備のクエリをまとめる・(problem_id, answered_at) の索引（Low）— 今のデータ量で不要 ③ クイズ画面のモードの印を表で引く（Low）— モードは 2 つで表にする利点が小さい ④ ProblemPreview・QuizManagement・AIQuestionGenerator に残る難易度の表示名の写し・I473/I488 のテストの補助の写し（Low）— このイシューの差分の外
- [review-gate] CI の E2E（`dashboard-layout.spec.ts` の TC-21〜23・26）が失敗（CI_WAIT: FAIL・run 44029395707）。モックした overview の応答に `weak_difficulties`・`rushed_mistakes` が無く、画面の形の確かめでエラー表示になったため。fix-loop に回す
- [fix-loop] CI の E2E の失敗は、固定の応答に 2 つのキーを足す案 A で直した（診断レビュー PASS）。画面の形の確かめを緩める案は I473 の決まりに反するので採らず、固定の応答を型で縛る案は retro に回す — 粗く確実な最小の直し
- [review-gate] 2 回目: CI OK・コードレビュー HIGH（止める指摘 F1・F2。記録 docs/reviews/I466_code_review_20261117_1519.md）。fix-loop に回す
- [fix-loop] F1 は「最後の手段でも直前の 1 問は除く」を通常・苦手を優先の共通の進み方に入れて直した（モード別の分岐を足さない）。F2 は引き継ぐモードを苦手を優先だけにした（I466 以前の今日の復習の動きに戻す）。診断レビュー PASS — どちらも数行の粗く確実な直し

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
