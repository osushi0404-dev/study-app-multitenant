# I446 レビュー: 問題・科目と本人の記録を扱う全 API の横断の越境テスト

- 関連: docs/issues/open/I446.md / docs/plans/open/plan_I446.md / GitHub #446 / Draft PR #456

## 変更概要
- アプリの全経路（Django の管理画面を除く）を表に載せた横断のテストを足し、他組織・同じ組織の別の利用者・全体共有の番号が存在しない番号と同じ応答で断られること、一覧・集計に他組織・別の利用者の中身が出ないこと、表に無い経路が増えたら落ちることを CI で毎回確かめる
- テストで見つかった越境（計画書の S1〜S6）を、1 か所の絞り込みの追加で直す

## 変更点
- （実装後に記入）

## 影響範囲
- Backend: core/tests（新規）・problems（serializers・views）・problems/tests（I103・I166 の期待値）
- Frontend: なし
- DB: なし
- Config: なし

## テスト結果
- （実装後に記入）

## 計画との差分
- （実装後に記入）

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

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
