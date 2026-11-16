# I545 レビュー: コードの書き方の決まりをベストプラクティスのあるべき状態に見直す

## 変更概要
- コードの書き方の決まり 4 本（`rules/` の Django・React 規約、`docs/runbooks/ux-rules.md`・`docs/runbooks/backend-check.md`）を、最新化・漏れ・最適化の観点で「あるべき姿」に書き直した
- 規約の冒頭に前提の版（LTS 優先・点検した日 2026-11-17・出典つき）、最後に今のコードとの差（移行・直しのイシュー）を置いた
- 正でない古い規約 4 本と `rules/bk/` を消した
- 規約と今のコードの差を、新しいイシュー 13 件（#551〜#563）と既存イシュー 9 件へのコメントに振り分けた
- 節ごとの点検の結果・漏れの点検・振り分けは `docs/reviews/open/I545_rules_audit.md`

## 変更点
- `rules/ultimate_django_coding_standards.md`: 1,710 行 → 約 250 行。§0 前提の版・§1 使う道具・§2 構成・§5 組織の境界・§6 API（既定 `IsAuthenticated`・`get_permissions` と `@action`・クエリの値の検証・OpenAPI が正）・§9 日付・§10 セキュリティ（トークン・廃止された設定・CSP）・§13 必ず書くテスト・§16 今のコードとの差 など
- `rules/react-coding-standards-integrated.md`: 2,150 行 → 約 210 行。Vite・Vitest・MSW 3・TanStack Query・MUI・React Router 8・RHF＋Zod に決め、選択肢の列挙を無くした。トークンの保存場所・日付・アクセシビリティ（ラジオのまとまりの名前）などを足した
- `docs/runbooks/ux-rules.md`: 利用者から見た原則だけにし、計画書の UX の節のひな形を消して `plan-writing-rules.md` 13) を正にした
- `docs/runbooks/backend-check.md`: curl の手順を消し、自動テスト・マイグレーション・食い違いの診断の手順に書き直した
- `docs/runbooks/issue-flow.md`・`docs/claude-code-structure.md`: 参照と説明を新しい中身に合わせた
- `docs/reviews/backlog/I209.md`: F8（`get_permissions` の注意）を規約に書いたので行を消した
- 消した: `rules/` 直下の正でない 4 本・`rules/bk/` の 4 本

## 影響範囲
- Backend/Frontend/DB/Config: なし（文書だけ）。計画レビュー役・コードレビュー役が照合に使う規約の中身が変わる。レビュー役は差分だけを照合するので、関係の無い PR が今のコードの違反で止まることはない

## テスト結果
- 自動: 決定論ゲート 15 行がすべて exit 0（実装の前は 15 行すべて exit 1 で、失敗を捕まえることを確認済み）。書き換えた 5 本の文書のパスの参照 54 件がすべて実在
- 手動: test-gate で実施

## 計画との差分
- あり（計画変更記録に記録）: MSW は 3、移行のイシューは見込みの 8 件から 13 件に。どれも計画の方針どおり

## ロールバック
- PR を revert する（文書だけ・消した古い規約は git の履歴から戻せる）。起票したイシューは閉じる

## 自律判断の記録
- [plan] 2 本の規約と 2 本の手順書を 1 つの PR で扱う — 同じ形と前提の版を共有し、分けると食い違うため
- [plan] 道具の確定（Vite・Vitest・MSW v2・Zod・MUI・TanStack Query・psycopg 3 など）を計画で決め、実装のステップ 1 で公式の文書で裏付ける — 選択肢を残さないというイシューの方針（AC6）のため
- [plan] `rules/bk/` も消す — 参照が無く git の履歴に残る。控えを 2 か所に置かない
- [plan] 点検の結果の表は `docs/reviews/open/I545_rules_audit.md` に置く — close の移動の対象に入り、計画書を太らせない
- [plan] 決定論ゲートだけ足し、テストのスクリプトは足さない — 守る対象が意図的な変更でしか壊れないため（plan-writing-rules「決定論テストの対象の選び方」）
- [plan-review] Warning 5 件を直し、再レビューはしない — 方式・範囲・受け入れ条件を変えない追記だけのため（計画変更記録に記録）。Info 2 件は対応しない — 計画どおりで妥当・実害が無い
- [implement] MSW は 3 の形で書いた（計画は v2 の見込み） — 点検した日の最新の安定版が 3.0 で、方針（最新の安定版）どおり
- [implement] TypeScript は 7.0（`tsc`）＋道具用の 6.x とした — 7.0 は API を持たず、typescript-eslint などには 6.0 を並べるのが公式の勧めのため
- [implement] 移行のイシューを 13 件に分けた — 触る場所・失敗の影響・戻し方がそろう単位（Vite は Node.js の版上げと同時でないと動かないので #551 に 1 つ。React と TypeScript は同時・MUI と Router はその後）
- [implement] 移行のイシューの issue-review はすべて「要補足」だったが登録した — 判定は助言で、共通の指摘（根本原因が経緯の言い換え）は登録の前に直した。残りは各イシューの計画で決める細部
- [implement] `docs/claude-code-structure.md` の名前の型の例（`XXX` の置き字）が参照の確かめで「無い」と出たが直さない — 実在のファイルへの参照ではなく、古い名付けの説明の見直しは I546 の範囲
- [implement] ux-rules の「入力中にリアルタイムで指摘」を「欄を離れたときに確かめる」に直した — 公式の出典は無く Claude の判断（点検の表に明記）
- [implement] /simplify の 4 観点の指摘のうち、重複の整理・参照への置き換え・必ず書くテストの一般化・非推奨の API の原則を直し、§0 の表の列を減らす案・I050 の決まりを消す案・MSW の例を短くする案は見送った — 表の形は設計確認メモの決定と AC2、I050 は `--no-migrations` で CI が順番を確かめないため、MSW の例はこれ以上削れないため（計画変更記録）
- [implement] 規約の決まりのうち機械で止められるもの（Ruff・pytest の非推奨の警告・`check --deploy`）を #563 に起票し、ESLint で止められるものの一覧を #517 にコメントした — /simplify の直す深さの観点の指摘で、規約を文のまま残すより仕組みで止めるほうが根本のため
- [implement] commit の前の detect-secrets のフックが `.secrets.baseline` を書き換えたので、計画書に足し（必ず確かめる項目 V1・V2・TC-07）、計画レビューをやり直した — 高リスクのファイルが範囲に入ったため。判定は HIGHRISK なので design-security-review を通す（実装はコミット済みで、その段階の結果で直しが要れば implement に戻る）
- [implement] `.secrets.baseline` の、消したファイル（`rules/backend-django-coding-standards.md`・`rules/bk/…`）の古い登録は残した — フックが外さなかった登録で、無いファイルの登録は害が無い。手で消すと高リスクのファイルの手作業の変更が増える
- [fix-loop] F1 は 8 行のゲートを `rules/` 全体を正の 2 本を除いて探す 1 行にした（診断メモ 案 A） — 実走は `! grep` のエラー（ファイルが無い）を不合格にするので、名指しのファイルの不在はこの形で確かめられない。フォルダ全体を見る形なら名指しの漏れも無い。0 バイトのファイルを捕まえない弱みは、規約として読まれないので受け入れた
- [fix-loop] F2 は React 規約 §8 に `mode: 'onTouched'` を足した（案 A） — ux-rules §3 の「欄を離れたときに確かめる」と同じ意味で、直している最中に誤りが消える（onBlur より使い勝手がよい）
- [fix-loop] 止める指摘でない台帳の指摘（§16 の「差が直る前から規約に従う」が今の依存では守れない決まりを含む・§16 の差の表の漏れ・`.secrets.baseline` に消したファイルの登録が残る など）は直さない — fix-loop が直すのは止める指摘だけ。retro が振り分ける
- [fix-loop] 2 回目: TC-05 の正規表現の `|` で 1 行が実走対象外になったので、`|` を使わない 2 行に分けた（診断メモ `docs/reviews/I545_fix_diagnosis_20261117_0404.md` 案 A） — 読んで分かり、捕まえる範囲もほぼ同じ
- [test-gate] 手動 No.1 で範囲でしか書いていなかった 7 行、No.6 で #499 を、点検の表（記録の場所）に足してから判定した — 表の書き方の漏れで、規約の中身ではないため
- [test-gate] 手動 No.5 を NG にして fix-loop に回す（選択肢の列挙 2 か所・§16 の「差が直る前から従う」の食い違い） — 規約の本文を直す必要があり、この段階では直せないため。§16 はレビューの台帳にもあった指摘で、全文を読んで実際に両立しないことを確かめた

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: fix-loop
