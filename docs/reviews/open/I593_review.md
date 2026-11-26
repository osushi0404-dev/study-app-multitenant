# I593 レビュー: 判定の仕組みを変える PR を変更前の版で審査する

## 変更概要
-

## 変更点
-

## 影響範囲
- Backend/Frontend/DB/Config:

## テスト結果
- 自動:
- 手動:

## 計画との差分
- なし / あり（理由）

## ロールバック
-

## 自律判断の記録
<!-- 各段階が、止めずに自分で決めたことを `- [段階] 決めたこと — 理由` で足す。段階の結線の行（STAGE_DONE:）はこのファイルの末尾に足す -->
- [plan] 定義の渡し方を `--agents <ファイル>` にした — スパイクで同じ名前のプロジェクトの定義より優先されると確かめた（plan_I593.md 調査結果 3）
- [plan] `.claude/hooks/` と `scripts/claude/gate-check.sh` を高リスクの集合に足した — 設計確認メモ「変更前の版で動かせない部分は必ず高リスク」の具体化（増えるのは 60 件で 7 件）
- [plan] 変更の種類 guard と止めて聞く条件 2 の集合は広げない — 審査の段階のスキルを直すたびに止めて聞くことになり開発の速さを落とすため
- [plan] 一覧から I615 F3・F5 を同梱、ほかは残す — 写しの作り方と写しの入口の安全に直接かかわるものだけ
- [plan-review] 計画レビュー（OK）の Warning 1 の実起動のスパイクは、承認の画面を出す test-session.sh --agents を繰り返さず、公式の説明での確かめと、この PR の review-gate で人が流す新しい版の実際のレビュー（手動テスト No.2）で代える — ユーザーから「必須でない承認は出さない」と指示があったため
- [plan-review] Warning・Info をすべて計画書・テスト文書に反映し、再レビューはしない — 方式・範囲・受け入れ条件を変えない追記だけ（計画変更記録）
- [implement] 審査の入口を丸ごと流す既存のテストは、本番と同じく写しから入口を流す形に直した（新しい道具 lib_test_snapshot.sh）— 作業ツリーから流すと 4-3 で高リスクに倒れ、期待が変わるため（計画変更記録）
- [implement] fix-review-lib.sh の claude を ${CLAUDE_BIN:-claude} にした — TC-04 の差し替えのため。ほかの入口と同じ形
- [implement] /simplify の指摘のうち、小さく挙動を変えないもの（git の起動を減らす・弱める差分の計算を組み込みのレビューの起動の後へ移す・写しの道具のループ化・一時フォルダの後片付けを 1 つに・関数の位置）を直した。見送ったもの: 写しに docs/runbooks/ 全体を入れる（設計確認メモで review-rules.md だけと決めた）・計画レビューの高リスクを記録の 1 行と plan_risk の OR に変える・gate-check を写しから読む・テストの道具（ck・broken・lib）の共通化 — どれも仕組みを変えるか差分が広がるので retro で後続にするか判断する
- [implement] run-all のうち test_compose_ports・test_guard_corpus_diff・test_i211_version_pin はサンドボックスの中で落ちる（~/.cache に書けない・docker が無い）。このブランチで触っていないファイルなので CI で確かめる

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: implement
