# I619 レビュー: パスキーでログイン

## 変更概要
- パスキー（WebAuthn）の登録・一覧・名前の変更・削除（登録・削除は 5 分の本人確認つき）と、パスキーだけでのログインを足す。移行期間はパスワードのログインも残す（計画: docs/plans/open/plan_I619.md）

## 変更点
- （実装後に書く）

## 影響範囲
- Backend/Frontend/DB/Config: （実装後に書く。計画の 3 を参照）

## テスト結果
- 自動: CI（backend・frontend・E2E・Harness）がすべて通過（review-gate の code-review.sh が確かめた・2026-11-24）。手元の追加の実走は無し（auto_test の決定論ゲートは無い）
- 手動（Claude・2026-11-24・0cfabd25）: No.1〜9・11 は OK、No.10 は NG（一覧の行の鉛筆・ごみ箱のボタンが 40×40px で、押す的の 44px に足りない）→ fix-loop で直し、ee7e957d で No.10 を再確認して OK
- 手動（人・No.12・2026-11-26）: OK。実際の端末（Windows・Chrome）で登録・パスキーでのログイン・削除ができた

## 計画との差分
- （実装後に書く）

## ロールバック
- PR を revert し、`python manage.py migrate accounts 0023` で表 2 つを消す。backend・frontend のイメージを作り直す

## 自律判断の記録
<!-- 各段階が、止めずに自分で決めたことを `- [段階] 決めたこと — 理由` で足す。段階の結線の行（STAGE_DONE:）はこのファイルの末尾に足す -->
- [plan] 画面の配置・流れ・文言はユーザーに案を見せて確定し、それ以外（ライブラリ・challenge を DB に置く・本人確認の印・スロットル・無効化をシグナルで消す・パスキーのログインはロックを見ない・上限 20）は Claude が決めた — 理由は計画書 9
- [plan] e2e コンテナでの RP ID `frontend` は未実証のまま実装ステップ 1 で確かめる — 作業場所の中で chromium が起動せず、Playwright MCP のブラウザは安全なコンテキストの起動オプションを持たない。CI の E2E は localhost で影響しない
- [plan-review] 計画レビュー（HIGHRISK・Blocker なし）の Warning 4 件を直した（challenge の消費を検証の前に別にコミット・スロットルの scope を分ける・V7 を読んで可・監査のログ）。再レビューはしない — 方式・範囲・受け入れ条件を変えない findings への対応の追記だけ（計画変更記録）
- [design-security-review] Blocker 0・Medium 2・Low 4。Medium 2 件（本人確認のパスワードの総当たり・本番の設定の誤り）と Low 1 件（名前の表示のなりすまし）の守りを計画に入れ、Low 2 件（印の再利用・attestation none）は受け入れ（R9・R10）、Low 1 件（XFF の偽り）は既存の扱い。計画レビューはやり直さない — 守りの追加だけで方式・範囲・受け入れ条件を変えない（計画変更記録）
- [implement] docker-compose の既定の origin を画面のポートから作る・`test_I446` の経路の表に足す・`test_I127` のレートの表に足す・`AuthContext.passkey.test.tsx` を足す・削除の確認に見出し「パスキーの削除」・e2e コンテナは `--env-file` を重ねる — 理由は計画変更記録（どれも方式・範囲・受け入れ条件を変えない）
- [implement] 実装ステップ 1（e2e コンテナで RP ID `frontend`）は通った。R3 の回避策は使わない
- [implement] 画面のテストは部品を書いた後に書いた（TDD の Red を先に確かめていない）。代わりに、本人確認を飛ばす変更を入れて 4 件が落ちることを確かめた（false-green でない）。裏側は Red（import の失敗）を確かめてから実装し、守り（challenge の消費・本人の分だけ・本人確認・無効の利用者・無効化の削除）を外すと 13 件が落ちることを確かめた
- [implement] 画面の確かめ（Playwright MCP・`localhost:3020`・e2e_user_c・仮想の認証器）: ログイン画面の並び・設定画面の欄の場所・本人確認（誤り→正しい）・登録・ログアウト→パスキーでログイン（200・最後に使った日が今日）・削除（確認→パスキーで本人確認）を確かめた。作ったパスキーは消した
- [implement] /simplify（4 観点）で直した: ロックの規則を User のメソッドに 1 つにまとめ、パスワードのログインと本人確認で共有・`complete_login` で last_login も更新・用途を user から決める・シグナルの update_fields の除外・OpenAPI の詳細の経路の抜け・本人確認の 400 以外の文・使わない export・テストの重複した 1 行 — 理由は計画変更記録
- [implement] /simplify で直さなかった: reauth の印を `signing` の `max_age` に任せる（期限切れのテストに時刻の差し替えが要るため、計画の決定どおり iat を持つ）／一覧のページ分けを外す（Django 規約 §6 の必須）／登録・名前の変更の後の取り直しをキャッシュの書き換えにする（React 規約 §5 は invalidate）／期限切れの challenge の片付けを定期の処理にする（計画の R5 の決定・行は 5 分で消える）／403 に専用の印を付ける（この経路で 403 を返すのは `HasRecentReauth` だけで、共通の例外の形を変えるのは範囲外）／`establishSession` の型を生成の型にそろえる（手書きの User と生成の型の差は既存の差）／`browserSupportsWebAuthn()` を 1 回だけにする（軽く、テストで毎回差し替えるため）／400 の文の取り出しと再読み込みの行の共通化（LearningSubjectsCard など範囲外の部品を直すことになる）
- [fix-loop] 止める指摘 F1（PATCH の空の本文で 500）は案 A（シリアライザの validate で 400）、F2（ロックの期限切れで回数が戻らない）は案 A（`record_failed_login` で期限切れなら数え直す）で直した。診断レビュー PASS（docs/reviews/I619_fix_diagnosis_review_20261124_0232.md）。F2 の直しはパスワードのログインのロックにも効く（元からの欠陥・ログインの成否と応答の形は変わらない）。台帳の Low（F3〜F7）は直さない — fix-loop が直すのは止める指摘だけ
- [test-gate] Claude の手動テストで No.10 が NG（MUI の IconButton の既定が 40px で、ux-rules §6 の 44px に足りない）。コードを直す必要があるので fix-loop に回す。人の手動テスト（No.12）は、直してレビューを通った後にまとめて依頼する
- [fix-loop] No.10 の NG は案 A（2 つの IconButton を 44px にする）で直した。診断レビュー PASS（docs/reviews/I619_fix_diagnosis_review_20261124_0256.md）。全画面のテーマで直す案 C は範囲を超えるので採らず、既存の画面のアイコンのボタンの点検は retro で後続にするかを決める

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: human-test
