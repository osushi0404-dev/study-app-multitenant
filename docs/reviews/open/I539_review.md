# I539 レビュー: 招待なしの会員登録を完了できるようにする（利用者ごとの個人用の組織）

## 変更概要
- （実装後に記入）

## 変更点
- （実装後に記入）

## 影響範囲
- Backend/Frontend/DB/Config: 計画書 `docs/plans/open/plan_I539.md` の 3 を参照（実装後に実際の差分で更新）

## テスト結果
- 自動: （CI の結果を記入）
- 手動: （test-gate 段階で記入）

## 計画との差分
- なし（実装後に更新）

## ロールバック
- PR を戻す。データマイグレーション 0022 の逆向きは何もしない（移した利用者は専用の組織の管理者のまま残る・計画書の 7）

## 自律判断の記録
- [plan] 個人用の組織でも AI での問題作成を使えることは、/plan-issue の途中でユーザーに確認して決めた（「使えるようにする」）。料金が増えうるリスクは計画書の 8 の R4 に受け入れとして記録 — 費用の方針は止めて聞く条件 1
- [plan] 組織は登録の入力から受け取らない（`organization_id` をシリアライザから消す）。招待で引き当てる組織は `Organization.objects.invitable()` 1 か所の条件にする — 入力でテナントを決めない・3 つの入口の条件のずれを防ぐ
- [plan] 共有の組織の利用者の移し替えは、管理コマンドではなくデータマイグレーション（逆向きは何もしない）— デプロイで確実に 1 回走り、手作業が要らない。戻すと利用者の作った科目が消えうるので自動では戻さない
- [plan] 登録画面: 科目選びの段が無いときは段の表示を出さず、ボタンを「登録する」にする。招待の科目は React Query で 1 段目の時点で読み、読めなければ「再読み込み」を出して送らせない — ユーザーの指示「BP、UI/UX の観点でベストなやり方で」・規約 6.3
- [plan] ダッシュボード: 管理者の案内に「科目を作る」「問題を作る」の 2 つのボタンを並べる。管理者でない人は「科目がまだ用意されていません。管理者が科目を用意するまでお待ちください」— 次の操作を 1 回で届かせる・何が足りないかを先に言う
- [plan] `SubjectManagement.tsx` は変えない — 学ぶ科目への追加は裏側で済み、ダッシュボードは開くたびに取り直す
- [plan] API の仕様書（`backend/openapi.yaml`）は作り直さない — 今回変える経路が載っていない（CI の契約のテストで確かめる）
- [plan-review] 計画レビューは高リスク Yes（ロールの付与・テナント境界・未認証の API・データマイグレーション）。Warning 2 件・Info 1 件は計画変更記録に書いて直した（slug の重なりの処理を分けて乱数を差し替えずに確かめる・slug の形を 1 つの正規表現で両方確かめる・R4 の後続は retro で決める）。方式・範囲・受け入れ条件は変えないので再レビューはしない — workflow.md「findings への対応の追記だけなら通り直さない」
- [design-security-review] Blocker: 「本人ひとりの組織」を種類 `type='personal'` で見分ける設計は、種類の既定が `personal` の招待用の組織（開発の DB の `e2e-org-a`・`e2e-org-b`）の招待を壊す。列 `is_individual`（`db_default=False`）で見分ける設計に直し、AC6 を同じ意味に言い直した（写しも）。High: `context` の渡し忘れは `ImproperlyConfigured` で止める。方式・DB を変えたので計画レビューからやり直す — design-security-review の手順 6・ユーザーの決定（個人用の組織に他人が入れない）は変えないので止めて聞かない
- [plan-review] 2 回目（20261116_2118）も高リスク Yes・Blocker なし。Warning（本番にカテゴリが無いと 0023 がデプロイを止める）はマージ依頼の確かめに足した。Warning（R4 の後続）は retro で決めて報告に載せる（計画どおり）— findings への対応の追記だけなので再レビューしない
- [design-security-review] 2 回目は Blocker・High なし。Low（後から手で作る組織と slug が重なりうる）は既存の slug の設計の範囲として計画に記録 — slug の一意化は今回の受け入れ条件の外
- [implement] 登録画面で、ボタンが無効でも入力欄の Enter で科目なしの送信が起きることを TC-33 で見つけ、1 段目の送信の処理でも止めた（計画変更記録に記録・止め方を外すと落ちることを確認）— 計画の意図「読めないときは科目なしで送らない」を守るため
- [implement] `/simplify`（4 観点）の指摘のうち、使われなくなった `getSubjectsWithLoading` の削除・登録画面の読み込み中／失敗の条件の名前付け・使われない型の削除・`'personal'` の定数化を反映。見送り: 道筋の定数を既存の画面でも使う（計画の外）・共有の組織への `is_individual` の付与（意味が合わない）・`public` の既定の slug を消す（計画が残すと決めた）・並列の取得（計画は確認の後に読む fail-closed）・`get_or_create` を `create` に（重複に強いほうを残す）
- [implement] 画面の確かめ（Playwright MCP）: 招待なしの登録 → ログイン → 管理者の案内 → 科目・問題の作成 → クイズの開始まで動いた（`.evidence/I539/` に 4 枚）
- [review-gate] 1 回目: CI の E2E Tests (Playwright) が失敗（`CI_WAIT: FAIL`・run 43868042699）。手順どおり fix-loop へ

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
