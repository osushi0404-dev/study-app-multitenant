# I455 レビュー: 学習記録まわりのモデルに組織の境界つきの取り出し方を持たせる

- 関連: docs/issues/open/I455.md / docs/plans/open/plan_I455.md / GitHub #455 / Draft PR #462

## 変更概要
- 学習記録まわりの 8 モデル（StudyLog・ProblemAttempt・SpacedRepetitionCard・SpacedRepetitionReview・MistakePattern・LearningSuggestion・LearningWeakness・QuizSession）に、組織の境界つきの取り出し方 `objects.for_user(user)` を持たせる。境界の決まり（科目への経路・科目が空の記録を残すか）はモデルごとの QuerySet の属性 1 か所に書く
- 呼び出し側の `scope_to_user_org(..., subject_path=..., allow_null=...)` を `for_user` に置き換える。絞らずに読む箇所には理由のコメントを書き、付け忘れを静的テストで止める。振る舞いは変えない

## 変更点
（実装後に記入）

## 影響範囲
- Backend: problems（querysets 新規・tenant_scope・models の QuizSession・views の QuizSession）・studylogs（models・views・services・mistake_analysis・adaptive_selection・tasks・tests）・dashboard（views）
- Frontend: なし
- DB: なし（migration なし・TC-10）
- Config: なし

## テスト結果
（test-gate で記入）

## 計画との差分
（実装後に記入）

## ロールバック
PR を revert する（コードだけの変更。DB の形は変えない）。

## 自律判断の記録
- [plan] 既定の `objects` を絞らず、別名のメソッド `for_user(user)` にした — 既定の取り出し口は利用者を受け取れず、絞るには暗黙の「今の利用者」が要る。絞らない読み出しは静的テストで止める
- [plan] `scope_to_user_org` を `problems/querysets.py` に移し `tenant_scope.py` から公開し続ける — QuizSession の循環 import を避け、I431 のテストのファイルを変えないため
- [plan] `problems/views.py` の QuizSession の一覧も `for_user` にした — 同じモデルの境界を 2 か所に残さないため（イシューの表に無い 1 か所の追加・結果は同じ）
- [plan] `export_user_data_task` は件数だけを返すので絞らずに理由のコメント — `for_user` にすると件数が変わり、「振る舞いを変えない」に反するため
- [plan] 付け忘れを止める静的テスト（TC-06）を CI に常設 — #446 は API の経路だけを見て、サービスの内部・非同期処理を見ないため
- [plan-review] 3 回目で HIGHRISK（Blocker なし）。Warning は TC-10 の失敗の注入の手順の具体化だけ直し、再レビューはしない — 方式・範囲・受け入れ条件を変えないため

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: design-security-review
