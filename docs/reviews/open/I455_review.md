# I455 レビュー: 学習記録まわりのモデルに組織の境界つきの取り出し方を持たせる

- 関連: docs/issues/open/I455.md / docs/plans/open/plan_I455.md / GitHub #455 / Draft PR #462

## 変更概要
- 学習記録まわりの 8 モデル（StudyLog・ProblemAttempt・SpacedRepetitionCard・SpacedRepetitionReview・MistakePattern・LearningSuggestion・LearningWeakness・QuizSession）に、組織の境界つきの取り出し方 `objects.for_user(user)` を持たせる。境界の決まり（科目への経路・科目が空の記録を残すか）はモデルごとの QuerySet の属性 1 か所に書く
- 呼び出し側の `scope_to_user_org(..., subject_path=..., allow_null=...)` を `for_user` に置き換える。絞らずに読む箇所には理由のコメントを書き、付け忘れを静的テストで止める。振る舞いは変えない

## 変更点
- `backend/problems/querysets.py`（新規）: `scope_to_user_org` の本体（`tenant_scope.py` から移設・中身は同じ）と、土台 `OrgScopedQuerySet`（`subject_paths`・`allow_null`・`for_user`）
- `backend/problems/services/tenant_scope.py`: `scope_to_user_org` を新しいモジュールから読み込んで公開し続ける（QuizAnswer の先読み・I431 のテストのため）
- `backend/problems/models.py`・`backend/studylogs/models.py`: 8 モデルの QuerySet（境界の決まりはクラス属性だけ）と `objects = XQuerySet.as_manager()`
- `backend/studylogs/views.py`・`services.py`・`mistake_analysis.py`・`adaptive_selection.py`・`backend/dashboard/views.py`・`backend/problems/views.py`: 呼び出し側を `for_user` に置き換え（(A) 22 か所・(B) 9 か所）、`scope_learning_suggestions` を消す。絞らずに読む (C) の箇所に `# 組織で絞らない: <理由>`（`tasks.py` はコメントだけ）
- `backend/studylogs/tests/test_I455_org_scoped_querysets.py`（新規・20 件）: 8 モデルの `for_user`（TC-01・TC-02）・提案の 2 経路（TC-03）・土台の設定漏れ（TC-04）・表とモデルの登録の一致・絞らない読み出しの理由のコメント（TC-06）

## 影響範囲
- Backend: problems（querysets 新規・tenant_scope・models の QuizSession・views の QuizSession）・studylogs（models・views・services・mistake_analysis・adaptive_selection・tasks・tests）・dashboard（views）
- Frontend: なし
- DB: なし（migration なし・TC-10）
- Config: なし

## テスト結果
（test-gate で記入）

## 計画との差分
- TC-05 の正規表現から `allow_null=` を外した（DRF の入力欄の設定に当たる誤検出の直し・計画変更記録）
- 静的テストの対象モデルを登録から集め、表との一致のテストを 1 件足した（/simplify・計画変更記録）
- ほかは計画どおり（(B) の 9 か所はコードで確かめ直し、(C) に戻したものは無い）

## ロールバック
PR を revert する（コードだけの変更。DB の形は変えない）。

## 自律判断の記録
- [plan] 既定の `objects` を絞らず、別名のメソッド `for_user(user)` にした — 既定の取り出し口は利用者を受け取れず、絞るには暗黙の「今の利用者」が要る。絞らない読み出しは静的テストで止める
- [plan] `scope_to_user_org` を `problems/querysets.py` に移し `tenant_scope.py` から公開し続ける — QuizSession の循環 import を避け、I431 のテストのファイルを変えないため
- [plan] `problems/views.py` の QuizSession の一覧も `for_user` にした — 同じモデルの境界を 2 か所に残さないため（イシューの表に無い 1 か所の追加・結果は同じ）
- [plan] `export_user_data_task` は件数だけを返すので絞らずに理由のコメント — `for_user` にすると件数が変わり、「振る舞いを変えない」に反するため
- [plan] 付け忘れを止める静的テスト（TC-06）を CI に常設 — #446 は API の経路だけを見て、サービスの内部・非同期処理を見ないため
- [plan-review] 3 回目で HIGHRISK（Blocker なし）。Warning は TC-10 の失敗の注入の手順の具体化だけ直し、再レビューはしない — 方式・範囲・受け入れ条件を変えないため
- [design-security-review] Blocker・High なし（Medium 2・Low 2）。Medium はどちらも計画の TC（TC-01〜TC-03・TC-08・TC-09）と V3 の確かめ直しで受けるので、計画を直さず implement へ — 新しいエンドポイントが無く、`for_user` は絞る方向にしか働かないため
- [implement] TC-05 の正規表現から `allow_null=` を外し、再レビューはしない — DRF の `allow_null=True` に当たる誤検出で、`scope_to_user_org` の呼び出しが無いことは同じ TC が確かめるため
- [implement] /simplify の指摘のうち、静的テストの対象モデルを登録から集める・理由のコメントの言い回しをそろえる、の 2 つを直した — 表への足し忘れで見張りが漏れるのを防ぐため・grep で分類しやすくするため
- [implement] /simplify の指摘のうち、見送ったもの: テストの補助（cache を消す fixture・問題と復習の作り方）の共通化 — 既存の I431・#446 と同じ「ファイルごとに自己完結」の書き方で、共通化は計画の範囲外／(B) の重ねがけで結合が 1〜2 個増える — 問い合わせの数は増えず、安全側を標準にする計画の判断のため／絞らない読み出しを `owned_by(user)` のようなメソッドにして、コメントでなく作りで示す案・`subject_paths` の設定漏れを import 時に検出する案 — 方式の変更で計画の範囲外。retro で扱う
- [review-gate] コードレビュー（20261112_0940）は OK（Low 5 件・止める指摘なし）。Low は台帳に残し retro へ — 止める条件に当たらないため
- [review-gate] 敵対的レビュー 1 周目（20261112_0952）は HIGH（新しい Critical・High は 0。V6 が未検証・Medium 3 件）。上限が残っているので Medium 2 件（理由のコメントの共有・`models.X` の形）を直し、検出器を合成コードで確かめるテストを常設した。V6 は CI の決定論の TC（TC-10・TC-08・TC-11）で覆っているので「読んで可」に下げた。problems の QuizSession を見張る範囲に入れる Medium は、イシューの「含まない」（QuizService）で AC3 の範囲外のため直さず retro へ — 直すとイシューの範囲を超えるため
- [fix-loop] F6 は診断の案 A（`tokenize` でコメントを拾い、同じ行のコメントか直前のコメントだけの行だけを理由に認める）で直した — 共有を塞ぎ文字列の中の印も拾わない、粗く確実な形で、診断レビューが PASS したため。F7〜F9（Low）は止める指摘でないので直さない

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: design-security-review

STAGE_DONE: design-security-review NEXT: implement

STAGE_DONE: implement NEXT: review-gate

STAGE_DONE: review-gate NEXT: fix-loop
