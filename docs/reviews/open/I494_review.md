# I494 レビュー: 学ぶ科目を後から選び直せるようにする

## 変更概要
- 設定画面に「学ぶ科目」のカードを足し、利用者が会員登録の後でも自分の組織の科目から学ぶ科目を選び直せるようにする（`PUT /api/user/subjects/`・`GET /api/user/subjects/available/`）
- ダッシュボードの科目 0 件の案内を、組織に科目があればこのカードへの導線にする

## 変更点
- （実装後に記入）

## 影響範囲
- Backend/Frontend/DB/Config: 計画書 3 章のとおり（DB・Config の変更なし）

## テスト結果
- 自動: （CI の結果を記入）
- 手動: （test-gate で記入）

## 計画との差分
- なし

## ロールバック
- PR を revert する（マイグレーション・依存の変更なし）

## 自律判断の記録
- [plan] 書き換えの API を「選んだ一覧を丸ごと置き換える PUT」にした — 画面がチェックの全体を送る形と合い、冪等で単純
- [plan] 組織の科目の一覧は新しい `GET /api/user/subjects/available/` にした — 既存の `/api/subjects/` はページ分け 20 件・問題数の集計つきで選ぶ画面に合わない
- [plan] 新しい 2 つの経路を API の契約（I493）に入れた — 画面の型を手書きしない
- [plan] キャッシュは確定の後（on_commit）に消す — シグナルはトランザクションの中で消すので、確定の前に古い値が入り直す隙がある
- [plan] 文言とカードの中の細かい並びは設計確認メモの決定から導いた（新しい価値判断は無いので止めない）
- [plan-review] 計画レビューの Info（追跡用のログ）を取り入れた・Warning 2 件は直す所なし — 方式・範囲・受け入れ条件を変えないので再レビューしない
- [design-security-review] 組織に属さない利用者の条件が全体共有の科目に当たる穴を High として計画で塞いだ（3 か所で先に打ち切る・テストに共有科目）。Blocker にはせず計画レビューもやり直さない — 守りの条件とテストの追記だけで方式・範囲・受け入れ条件は変わらない
- [implement] 組織の境界は既存の `tenant_scope.available_subjects` を 3 か所で使った — 同じ判定を写さない
- [implement] 保存のボタンの名前を「学ぶ科目を保存」にした — 設定画面に別の「保存」があり区別できない
- [implement] 画面確認で見出しが固定のバーに隠れたので、見出しに上の余白を付け、フォーカスで送り直さないようにした
- [implement] /simplify の指摘のうち、シグナルの消し方（確定の後にも消す）・既存の関数の再利用・読み込み失敗の行の共通化・キーの頭の定数化を取り込み、効果の小さい 5 件は見送った（理由は計画変更記録）
- [fix-loop] CI の E2E の失敗（設定画面の「保存」を部分一致で探して「学ぶ科目を保存」にも当たった）を、E2E の探し方を完全一致にして直した（案 A）— 画面の文言をテストの都合で変えない。手元で E2E は流し直さない（CI が正）
- [fix-loop] F1 を、選択を毎回組織の科目の一覧と突き合わせる形で直した（案 A）— 状態を一覧から導く。ほかの選択を消さない
- [fix-loop] ユーザーとの相談（「その方針で進めて」）で決めた直しを入れた: E2E は「学習設定」の form（名前付き）の中の「保存」を押す・見出しの段をそろえる・触る前は赤い注意を出さない
- [fix-loop] 見出しのフォーカスの枠を消す案は取りやめた — 枠はアプリの「フォーカス表示強化」（既定でオン・利用者が切り替えられる）が出していて、このカードだけ打ち消すのは利用者の設定に反する

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
