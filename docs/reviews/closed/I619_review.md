# I619 レビュー: パスキーでログイン

## 変更概要
- パスキー（WebAuthn）の登録・一覧・名前の変更・削除（登録・削除は 5 分の本人確認つき）と、パスキーだけでのログインを足す。移行期間はパスワードのログインも残す（計画: docs/plans/closed/plan_I619.md・PR #625）

## 変更点
- Backend: `accounts/models.py`（Passkey・WebAuthnChallenge・`User.record_failed_login`）・`accounts/passkeys.py`（サービス）・`accounts/permissions.py`（HasRecentReauth）・`accounts/checks.py`（システムチェック）・`accounts/serializers.py`・`accounts/views.py`・`accounts/urls.py`・`accounts/signals.py`・`accounts/apps.py`・マイグレーション 0024・`core/settings.py`・`core/throttling.py`・`core/openapi.py`・`openapi.yaml`・`requirements.txt`（webauthn 3.0.1）
- Frontend: `pages/Login.tsx`・`pages/Settings.tsx`・`contexts/AuthContext.tsx`・`services/passkey.service.ts`・`hooks/usePasskeys.ts`・`hooks/usePasskeyReauth.ts`・`components/settings/PasskeysCard.tsx`・`PasskeyReauthDialog.tsx`・`PasskeyRenameDialog.tsx`・`utils/passkeyErrors.ts`・`types/api`・`package.json`（@simplewebauthn/browser 14.0.0）
- テスト: `accounts/tests/test_I619_passkeys.py`・`webauthn_soft_authenticator.py`・画面の 4 ファイル・`e2e/tests/passkey.spec.ts`・既存の `test_I446`・`test_I127`・`Settings.test.tsx` に追記
- Config・手順書: `docker-compose.yml`・`backend/.env.example`・`docs/runbooks/frontend-verify.md`

## 影響範囲
- Backend/Frontend/DB/Config: 計画の 3 のとおり。加えて、パスワードのログインの応答の組み立てと last_login の更新を `complete_login` に、ロックの規則を `User.record_failed_login` に寄せた（振る舞いは同じ。ロックの期限切れの数え直しだけ直った）

## テスト結果
- 自動: CI（backend・frontend・E2E・Harness）がすべて通過（review-gate の code-review.sh が確かめた・2026-11-24）。手元の追加の実走は無し（auto_test の決定論ゲートは無い）
- 手動（Claude・2026-11-24・0cfabd25）: No.1〜9・11 は OK、No.10 は NG（一覧の行の鉛筆・ごみ箱のボタンが 40×40px で、押す的の 44px に足りない）→ fix-loop で直し、ee7e957d で No.10 を再確認して OK
- 手動（人・No.12・2026-11-26）: OK。実際の端末（Windows・Chrome）で登録・パスキーでのログイン・削除ができた

## 計画との差分
- あり（計画書の「計画変更記録」の 5 行）: plan-review の Warning 対応・design-security-review の守りの追加・implement（既定の origin・経路の表・e2e の `--env-file`・確認のダイアログの見出し）・/simplify（ロックの規則の共有・complete_login・OpenAPI の詳細の経路）。どれも方式・範囲・受け入れ条件を変えない

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
- [fix-loop] 止める指摘 F1（PATCH の空の本文で 500）は案 A（シリアライザの validate で 400）、F2（ロックの期限切れで回数が戻らない）は案 A（`record_failed_login` で期限切れなら数え直す）で直した。診断レビュー PASS（docs/reviews/closed/I619_fix_diagnosis_review_20261124_0232.md）。F2 の直しはパスワードのログインのロックにも効く（元からの欠陥・ログインの成否と応答の形は変わらない）。台帳の Low（F3〜F7）は直さない — fix-loop が直すのは止める指摘だけ
- [test-gate] Claude の手動テストで No.10 が NG（MUI の IconButton の既定が 40px で、ux-rules §6 の 44px に足りない）。コードを直す必要があるので fix-loop に回す。人の手動テスト（No.12）は、直してレビューを通った後にまとめて依頼する
- [fix-loop] No.10 の NG は案 A（2 つの IconButton を 44px にする）で直した。診断レビュー PASS（docs/reviews/closed/I619_fix_diagnosis_review_20261124_0257.md）。全画面のテーマで直す案 C は範囲を超えるので採らず、既存の画面のアイコンのボタンの点検は retro で後続にするかを決める
- [retro] 台帳の残り F3・F4・F5・F6・F7・F8・F9・F10（どれも Low・再現なし・アプリ本体）→ #629（I629「I619 のレビューの残り」）にまとめて起票。一覧（`docs/reviews/backlog/I619.md`）に回るものは 0 件
- [retro] アイコンのボタンの押す的（テーマで 44px・E2E で測る）→ #629 に同梱（F10 と同じ根本原因）
- [retro] 端末に残るパスキーの片付け（Signal API）→ #629 に同梱（採否は grill-me で確認）
- [retro] 前置きの環境変数つきの docker がサンドボックスの外に出ず、手順書 frontend-verify.md:75 がまだその形を案内している → #600 にコメントで同梱
- [retro] 見送り: 認証手段の追加に本人確認とロックを求める観点を grill-me・計画レビューに足す案（design-security-review がその場で Medium として見つけ、計画に入れた。捕まって手戻りも無い）／Write ツールが一時使えず、heredoc が「複雑すぎる」で拒まれた件（原因を確かめられず、`printf` で入れ物を作って Edit する回り道で実害なし）／レビューで見つかった F1（PATCH の空の本文）・F2（ロックの期限切れ）の予防（どちらも review-gate で捕まり、fix-loop で直して TC を足した）
- [close] develop への追従は不要（mergeStateStatus=BLOCKED・承認待ち）。gate-check OK。記録を closed へ移し、計画書のレビュー結果のリンクを closed 向きに直した。記録の中の診断レビューの記録の参照（時刻の誤り 0256→0257）を直した。変更点・影響範囲・計画との差分の空欄を埋めた

## 振り返り

### かんたんなまとめ（平易版）

#### 良かった点
- 計画の前に、新しいライブラリと試しの認証器で「登録→ログイン」を小さく試した（理由: 使えるかどうか分からない部分を先に確かめたので、実装で方式を変えずに済んだ。e2e コンテナで動くかだけは実装の最初に確かめ、通った）
- 画面の配置・流れ・文言は、案を見せてから計画を書いた（理由: 実装の後の作り直しが無かった）
- セキュリティの設計の確かめで、盗まれたアクセストークンでの総当たり・本番の設定の誤り・名前の見た目のなりすましを実装の前に見つけ、守りを計画に入れた（理由: 実装の後のレビューでこれらの指摘は出なかった）
- 守りをわざと外してテストが落ちることを、裏側・画面・E2E のそれぞれで確かめた（理由: テストが本当に守りを見ているかが分かる）
- 人の手動テスト（実際の端末での登録・ログイン・削除）は 1 回で OK だった

#### 今回の問題への直接の対処
- 名前の変更で中身が空の送信がサーバーのエラーになっていた。書ける項目が名前だけなのに、名前が無い送信を入力の誤りとして扱っていなかったため。→ 入力の誤り（400）として断るようにし、テストを足した（レビューで見つかり、このイシューで直した）
- パスワードの誤りのロックが、期限が切れても回数を戻さなかった。以前からの欠陥を、規則を 1 か所にまとめたときにそのまま写したため。→ 期限が切れたら数え直すようにし、パスワードのログインも同じに直した
- 一覧の行の鉛筆・ごみ箱のボタンが 40px で、押しやすさの決まり（44px）に足りなかった。部品の既定の大きさのままで、単体テストでは大きさを測れなかったため。→ 2 つのボタンを 44px にし、E2E で大きさを測るようにした
- レビューで止めなかった細かい指摘 8 件（同時の登録で上限を超えうる・ダイアログを閉じられる・本番の URL の形の確かめなど）と、全画面のアイコンのボタンの大きさ、端末に残るパスキーの片付けは、まとめて #629 に起票した（理由: 止める基準に当たらないが、放っておくと見えなくなるため）

#### 同じ問題を次回から防ぐ改善
- アイコンだけのボタンの大きさの付け忘れが、部品ごとに起きる。部品の既定が 40px で、画面全体の決まりとして大きさを決めていないため。→ #629 で、画面全体の部品の決まり（テーマ）で最小の大きさを 44px にし、E2E で主な画面のボタンの大きさを測って守る（手作業の確かめに頼らない）
- 手順書の E2E の流し方の一部が、今の環境では動かない形（前に環境変数を付けた docker のコマンド）のまま残っていた。サンドボックスが入った後も手順書の書き方を見直していなかったため。→ #600 にコメントし、手順書を動く形（環境変数のファイルを重ねる形）にそろえ、見張りが動かない形を案内するかを検討してもらう

### 詳細版

#### 良かった点
- 未知リスク（py_webauthn・CDP の仮想の認証器・RP ID）をスパイクで計画の前に実証し、未実証の 1 点（e2e コンテナの RP ID `frontend`）は実装ステップ 1 のゲートにした
- UI の価値判断（配置・流れ・文言）をプレビューつきで確定してから計画を書いた（plan-issue の「仮定で決めた UI は止めて聞く」どおり）
- design-security-review の Medium 2・Low 1 を必須防御条件として計画に入れた（総当たりのロック・システムチェック・Cc/Cf の拒否）
- 失敗注入（FG）を裏側 13 件・画面 4 件・E2E 1 件で実施した
- 敵対的レビュー 2 周とも未検証 0・Critical/High 0

#### 是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | 予期しない問題 | partial の PATCH で唯一の書ける項目の必須の検証が外れる | `PasskeySerializer.validate` で 400・TC-04 に空の本文（fix-loop で済み） |
| C2 | セキュリティ | ロックの期限切れを回数のリセットに結び付けていない（既存の欠陥の写し） | `User.record_failed_login` で数え直す・TC-06（fix-loop で済み） |
| C3 | モダン開発 | IconButton の既定 40px・部品で大きさを指定していない | 2 つのボタンを 44px・TC-30 で測る（fix-loop で済み） |
| C4 | ベストプラクティス | 台帳の残り F3〜F10（Low・再現なし） | #629 に起票（retro） |

#### 予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| P1 | モダン開発 | 画面の部品の押す的を、画面全体の決まり（テーマ）でなく部品ごとに決めていて、決定論のチェックも無い | テーマで最小の大きさを 44px にし、主な画面の E2E で大きさを測って fail させる（#629 に同梱） | `frontend/src` のテーマの定義・`e2e/tests/` |
| P2 | スキル・規約 | サンドボックスの外に出す判定が先頭の語で決まり、前置きつきのコマンドが外に出ないのに、手順書がその形を案内したまま | 手順書の前置きの形を `--env-file` を重ねる形にそろえ、見張りが外に出ない形を案内するかを検討する（#600 に同梱） | `docs/runbooks/frontend-verify.md`・`scripts/claude/hooks/pretooluse_guard.py` |

#### 5 Whys: アイコンのボタンの押す的の付け忘れ（P1）
- 理想の状態: 計画（13 の性能・UX 設計）に「押す的は 44px 以上」と書いた時点で、それを機械で確かめる TC が auto_test にあり、implement の時点で落ちていた
- Why 1: なぜ 40px のまま実装したか → 文字のボタンには `minHeight: 44` を付けたが、アイコンだけのボタンには付けなかった
- Why 2: なぜ付け忘れに気づかなかったか → 単体テスト（jsdom）は大きさを測れず、E2E も大きさを確かめていなかった。手動テスト（test-gate）まで見つからなかった
- Why 3: なぜ部品ごとに付ける必要があったか → 押す的の決まりを、画面全体の部品の決まり（テーマ）でなく、部品ごとの指定で満たしていた
- 抽象化テスト: 「画面全体の品質の決まりを部品ごとの手作業で満たし、決定論のチェックが無い」は I619 の固有名を外しても成り立つ
- 根本原因: 画面の品質の決まり（押す的）を、画面全体の仕組み（テーマ）と決定論のチェック（E2E で測る）で守っていない → 予防処置

#### 5 Whys: 手順書の動かない形（P2）
- Why 1: なぜ e2e コンテナの実行が失敗したか → 環境変数を前に付けた docker のコマンドがサンドボックスの中で動き、`.env` を読めなかった
- Why 2: なぜ中で動いたか → 外に出すコマンドの判定が先頭の語で決まり、前置きがあると `docker` に当たらない
- Why 3: なぜ手順書がその形のままだったか → サンドボックスを入れた後、手順書の中の外に出す必要のあるコマンドの書き方を点検していなかった
- 抽象化テスト: 「実行の環境の仕組みを変えた後、手順書の中のコマンドの形を点検していない」は I619 に固有でない
- 根本原因: 実行の環境の変更に合わせた、手順書の中のコマンドの形の点検が無い → 予防処置（#600 で手順書をそろえる）

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
STAGE_DONE: human-test NEXT: retro
STAGE_DONE: retro NEXT: close
STAGE_DONE: close NEXT: merge
