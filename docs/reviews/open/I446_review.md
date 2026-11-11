# I446 レビュー: 問題・科目と本人の記録を扱う全 API の横断の越境テスト

- 関連: docs/issues/open/I446.md / docs/plans/open/plan_I446.md / GitHub #446 / Draft PR #456

## 変更概要
- アプリの全経路（Django の管理画面を除く）を表に載せた横断のテストを足し、他組織・同じ組織の別の利用者・全体共有の番号が存在しない番号と同じ応答で断られること、一覧・集計に他組織・別の利用者の中身が出ないこと、表に無い経路が増えたら落ちることを CI で毎回確かめる
- テストで見つかった越境（計画書の S1〜S6）と、セキュリティ設計レビューで見つけた D1（組織が空の組織管理者）を、1 か所の絞り込みの追加で直す

## 変更点
- `backend/core/tests/test_I446_cross_api_tenant_isolation.py`（新規・129 件〔うち xfail 9〕）: 経路の収集・表（`ROUTE_TABLE`・`OUT_OF_SCOPE`）・4 種類の確かめ方（`IdCheck`・`ListCheck`・`OwnCheck`・`StaffOnlyCheck`）・TC-06
- `backend/problems/serializers.py`: `OrgSubjectField` を `ProblemSerializer` の前に移し、`ProblemSerializer.subject` に使う（S1・S2）
- `backend/problems/views.py`: `ProblemViewSet.get_queryset` の土台を `available_problems`（D1）・`generate_ai`／`generate_adaptive` の科目を `available_subjects` から探し 403 の分岐を消す（S3・S4）・`QuizSessionViewSet.get_queryset` を組織で絞り、詳細・終了では回答を組織の問題に絞る（S5・S6）・作成・更新の組織の確かめのコメントを多層防御に直す
- `backend/problems/tests/test_I103_cross_org_create.py`: 他組織の科目での作成は存在しない科目と同じ 400、AI 生成は 404 に期待値を直す（4-5）
- `backend/problems/tests/test_I166_quiz_tenant_isolation.py`: TC-09 を、存在しない回と同じ 404 に期待値を直す（4-5）

## 影響範囲
- Backend: core/tests（新規）・problems（serializers・views）・problems/tests（I103・I166 の期待値）
- Frontend: なし
- DB: なし
- Config: なし

## テスト結果
- 自動（手元・app-1 のコンテナ）:
  - TC-20（RED）: 修正前に 9 failed（計画の予想 8 件＋TC-06 と一致）・9 xfailed
  - TC-24: 修正後に新しいテスト＋`problems/tests/`＋`studylogs/tests/` が 263 passed・9 xfailed（45 秒）
  - TC-21〜TC-23（失敗注入）: 表の行の漏れ 2 種・組織の絞り込みを外す 2 種・本人の絞り込みを外す 1 種・回答の先読みを外す 1 種がすべて FAIL。すべて Edit で戻した
  - CI・手動: review-gate・test-gate で記入

## 計画との差分
- 回答の先読みを、回答を出す詳細・終了のときだけにした（/simplify・計画変更記録）
- 下準備で、他組織の問題への回答を持つ回を進行中にした（1 人 1 つの制約で、終了の経路の確かめが先に 400 で返っていたため・計画変更記録）
- 経路の収集で、DRF が足す HEAD と `<drf_format_suffix:format>` の書き方を除いた（計画変更記録）
- テストの利用者のパスワードを暗号化しない・使わない設定を消した（/simplify・計画変更記録）

## ロールバック
- PR #456 の revert（コードとテストだけ。マイグレーション・データの変更なし）

## 自律判断の記録
- [plan] 対象の経路を `api/` の下から、Django の管理画面以外の全経路に広げた — `api/` の外に足された経路にも気づけるようにするため（fail-closed）。今は 8 行増えるだけ
- [plan] 下調べで見つかった越境 S1〜S6 をこのイシューで直す — どれも 1 か所の絞り込みの追加で、境界の判定の置き場所を変えない（イシューのスコープ「含む」の条件）
- [plan] 問題の作成・AI 生成で他組織の科目を指定したときの応答を、403 から存在しない科目と同じ 400・404 に変える（I103 の決まりを変える）— 受け入れ条件 AC1 の物差しで、grill-me で確定した方針
- [plan] `dashboard/analytics` の 0 で割る不具合は直さず、retro で新しいイシューに起票する。`learning_insights` の KeyError は #452 に同梱する — どちらも境界と関係なく、このイシューの範囲外
- [plan-review] 1 回目の Blocker（高リスクの必須節が無い）を、「必ず確かめる項目」V1〜V8 を足して直し、やり直しで HIGHRISK（Blocker なし）になった — 計画レビューの指摘どおり
- [plan-review] 画面からの AI 生成が今も 415 になる件（画面が JSON で送る）を見つけた。直さず retro で扱う — 境界と関係なく、画面とバックエンドにまたがる
- [plan-review] 2 回目の Warning に対応し、番号の確かめに正の対照（自分の番号の詳細は 200）を足した。計画レビューはやり直さない — findings への対応の追記だけで、方式・範囲・受け入れ条件は変えない
- [design-security-review] 組織が空の組織管理者が全体共有の科目の問題を見られる穴（D1・Medium）を実測し、4-6 として同梱した。計画レビューはやり直さない — 同じファイルの 1 か所の絞り込みで、境界の判定の置き場所を変えない（I431 の同種の対応と同じ扱い）
- [design-security-review] Blocker・High なし。Low 4 件は記録だけ（応答時間の差・数字でない番号の 500 など、範囲外か既存のまま）
- [implement] /simplify の指摘のうち、回答の先読みの絞り込み・テストの使わない設定とパスワードの暗号化の削除を取り込んだ。共通の関数化・多層防御の削除・差分の外の画像の確かめは見送った — このリポジトリの書き方・計画の決定・範囲の外のため（計画変更記録に一覧）
- [implement] RED の取り直しで、終了の経路の自分の記録の確かめが通ってしまう下準備の誤りを見つけ、進行中の回にして直した — 計画の予想（8 件）と RED が合わなかったので、原因を切り分けた
- [implement] 失敗注入は Edit で入れて Edit で戻し、`git status` で backend の変更が計画どおりの 5 ファイルだけであることを確かめた — `git checkout`・`git restore` を使わない（計画レビューの Warning）

- [review-gate] コードレビュー（20261112_0215）は OK（Low 6 件・台帳に残す）。敵対的レビュー 1 周目は新しい指摘 0 で、V6 だけ実験役の環境に python が無く未検証 → TC-07（失敗注入を CI で毎回行う決定論のテスト）を足して V6 を「読んで可」に下げ、2 周目で確かめる — review-gate 3-3 の決まり
STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
