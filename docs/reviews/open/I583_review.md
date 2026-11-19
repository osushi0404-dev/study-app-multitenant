# I583 レビュー: 番号のテストを本物のリポジトリの記録に頼らない形にする

## 変更概要
- `test_i569_issue_number_digits.sh` の TC-02・TC-03・TC-05 を、一時の git リポジトリの中から本物のスクリプトを起動する形にし、期待する止まり方と終了コードまで確かめる。差し替えの `claude` で別プロセスの起動を防ぎ・検出する

## 変更点
- `scripts/claude/tests/test_i569_issue_number_digits.sh`: 部品 `tgit`・`iso_repo`・`stops`・差し替えの `claude` を足し、TC-02・TC-03・TC-05 を一時のリポジトリで流して止まり方まで確かめる。TC-10・FG-05〜FG-07 を足す

## 影響範囲
- Backend/Frontend/DB/Config: ハーネスのテスト 1 本だけ

## テスト結果
- 自動: `test_i569_issue_number_digits.sh` pass=84 fail=0（implement で実行・review-gate の決定論ゲートで実走・CI OK）
- 手動: No.1 OK（本物のワークツリーに I1000 の記録を置いても pass=84・claude の起動なし）

## 計画との差分
- あり（小）: `/simplify` の指摘で `stops` に git の環境変数を外す処理と git の探索の上限を足し、作者付きの git を `tgit` にまとめた（計画変更記録に記載・方式と範囲は同じ）

## ロールバック
- このイシューのコミットを revert する

## 自律判断の記録
<!-- 各段階が、止めずに自分で決めたことを `- [段階] 決めたこと — 理由` で足す。段階の結線の行（STAGE_DONE:）はこのファイルの末尾に足す -->
- [plan] スクリプトを写さず、本物のスクリプトを一時のリポジトリの中から起動する — 記録の場所は起動した場所の git の根で決まり、部品はスクリプト自身の場所から読むため（スパイクで成立）
- [plan] TC-03 は `ADVERSARIAL_ERROR: FILES` だけを合格にする（FLOCK を外す）— CI・手元に flock があり、FLOCK で止まると番号の後の止まり方を確かめられないため
- [plan-review] Warning 2 件（flock が無いときの原因の表示・手動テスト No.1 の中断時の後始末）を計画書とテスト文書に足し、再レビューはしない — 方式・範囲・受け入れ条件を変えない追記のため
- [implement] `/simplify` の指摘のうち 5 件を採った（git の環境変数を外す・git の探索を一時の場所で止める・作者付きの git を 1 か所に・FG-06 の前に印を消す・パスの変数をそろえる・LIB の置き場所）— 判定と範囲を変えずに守りと読みやすさが上がるため
- [implement] `/simplify` の指摘のうち 2 件は採らなかった: `stops` の照合の仕方（line/text）の一本化 — `GATE_CHECK: FAIL REASON=missing` などは行全体で照合する設計のため／FG-06 で一時リポジトリを使い回す — ケースの順番に頼る形になり、損が数十 ms と小さいため

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
