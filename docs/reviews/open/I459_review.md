# I459 レビュー: 学習統計の画面が、解いた問題が 0 件の日があると 500 になる不具合を直す（dashboard/analytics）

- 関連: docs/issues/open/I459.md / docs/plans/open/plan_I459.md / GitHub #459 / Draft PR #478

## 変更概要
`GET /api/dashboard/analytics/` の週ごとの正答率を週の合計で割る形にして、0 問の日がある利用者で 500 になる不具合を直した。`days` を確かめ、不正な値を 400 にした。

## 変更点
- `backend/dashboard/views.py`: `_accuracy_percent`（新規・モジュールの関数）・`DashboardAnalyticsView.get` の `days` の確かめと 400・`_get_performance_trends` の正答率を `Sum`/`Sum` で 1 回だけ割る形に
- `backend/dashboard/serializers.py`（新規）: `AnalyticsQuerySerializer`（`days` 1〜365・省略時 30）
- `backend/dashboard/tests/__init__.py`・`test_I459_analytics_zero_division.py`（新規）: TC-01〜TC-06（13 件）
- `backend/core/tests/test_I446_cross_api_tenant_isolation.py`: 下準備に 0 件の日のまとめを 1 件足し、避ける注記を外した

## 影響範囲
- API: `performance_trends[].avg_accuracy` の値の意味（週の合計で割る）と丸め（小数第 2 位）。`days` の不正な値は 500 → 400。キー・型は変わらない
- 画面: 変わらない（`performance_trends` を読まず `days` も送らない）。統計の画面が 500 で読み込みに失敗しなくなる
- DB・依存: 変更なし

## テスト結果
- 手元: 新しいテスト 13 件と #446・I431 が 172 passed。Red（直す前に 8 件 FAIL）と FG（おすすめの絞り込みを外すと TC-05 FAIL）を確認（`docs/tests/open/I459_auto_test.md` の実行記録）
- CI: PR #478（`41b84ec4`）の 7 ジョブすべて pass
- コードレビュー: `docs/reviews/I459_code_review_20261112_1837.md`（OK・Low 2 件・敵対的レビュー不要）
- 手動テスト: No.1〜No.3 すべて OK（Claude。dev で 0 件の日を持つ `e2e_user_c` の統計の画面が 200 で開く・不正な `days` が 400）

## 計画との差分
- /simplify で `_accuracy_percent` を 1 行にし、400 の `sub_message` の上限を定数から作るようにした（動き・文言は同じ。計画変更記録）

## ロールバック
PR を revert する（コードとテストだけ・DB の形は変えない）。

## 振り返り

### かんたんなまとめ

#### 良かった点
- 計画を書く前に、使い捨てのテストで 500 を実際に起こして原因の行まで確かめた（理由: 「おすすめの割り算も危ないのでは」という疑いを、読むだけでなく実際に流して「0 で割らない」と確かめられ、直す範囲を正しく絞れた）
- テストを先に書き、直す前のコードで 8 件落ちることを確かめてから直した。直さないおすすめについても、守りの条件を一時的に外すとテストが落ちることを確かめた（理由: テストが本当に不具合を捕まえることを、合格だけでなく失敗でも確かめられた）
- 計画レビュー・コードレビューとも 1 回で通り、手戻りが無かった

#### 今回の問題への直接の対処
- コードレビューの軽い指摘 2 件（`days=1.0` のような小数点つきの整数も受けること、正答率が 0 のときだけ型が整数になること）。どちらも「API の受け渡しの形」の話で、ダッシュボードの作り直しで形を決め直すときに一緒に扱うのが自然。→ #473 にコメントで同梱した

#### 同じ問題を次回から防ぐ改善
- 作業中の整理で、学習記録の API にも「クエリの数字を確かめずに変換して、数字でない値で 500 になる」書き方が 7 か所残っていると分かった。今回直した不具合と同じ種類で、決まった確かめ方が既存の画面の API に広がっていなかったのが原因。→ 新しいイシュー I479（#479）を起票した（今回と同じ「クエリ用の Serializer ＋ 400」の形で直す）

#### 見送ったもの
- 設計確認のときに「画面は 7・30・90・365 日を使う」と言い間違えた件: 書き込む前に自分で調べ直して訂正し、手戻りは無かったので、手順は足さない
- 統計の画面のコンソールの `key` の警告: 今回の変更と関係ない既存のもの。統計の画面の作り直しを扱うかは #473 で決めるので、別に起票しない

### 詳細
#### I459 振り返り

##### 良かった点
- 計画前の使い捨てテストで 500（analytics・`days=abc`）と、おすすめの非再現（HAVING の後）を実測し、範囲を `views.py:246-248` と `days` に絞れた
- TDD: Red 8 件 → Green 13 件。TC-05 は FG（`.filter(total_problems__gt=0)` を外すと 500）で false-green でないことを確かめた
- plan-review OK（Info 3）・code-review OK（Low 2・止める指摘なし）・CI 7 ジョブ pass。fix-loop なし

##### 是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | ベストプラクティス | レビューの Low 2 件（`IntegerField` が `1.0` を受ける・`_accuracy_percent` の int/float の混在）。API 契約がまだ 1 本に決まっていない | #473 にコメントで同梱（API 契約・`has_data`・比率の単位を決めるときに型もそろえる） |

##### 予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| P1 | セキュリティ・モダン開発 | クエリの値を確かめる決まった形（クエリ用の Serializer ＋ `create_error_response` の 400）が I452・I459 でできたが、既存のビューには広がっていない。数字でない値・範囲外の値を通るテストが無い | I479（#479）で `backend/studylogs/views.py` の 7 か所をクエリ用の Serializer に置き換え、400 のテストを足す | `backend/studylogs/views.py`・クエリ用の serializer・`backend/studylogs/tests/` |

##### 2.7 の判定
- P1: 実害（数字でない値で 500・上限なし）あり／その場では捕まらない（画面から呼ばれていないので見えない）／決定論のチェックで代わりにならない（ビューごとのテストが要る）／同梱先: #473 は dashboard だけ、#466 は画面につなぐ作業で範囲が違う → 新規起票
- 見送り: grill-me での「7・30・90・365 日」の言い間違い（書き込む前に自分で訂正・手戻りなし）／`Statistics` の `key` の警告（既存・#473 の統計の画面の扱いで決まる）

##### 残余リスク処遇・設計ルール昇格
- security-review は動いていない（高リスク判定なし）。スキップ

## 自律判断の記録
- [plan] 週ごとの正答率の割り算を、集計の後に Python で 1 回だけ行う形にした（データベースの中で `NullIf` で割る案は採らない） — 0 の扱いが 1 行で読め、overview の週のまとめと同じ書き方
- [plan] `days` の確かめを DRF の serializer（`dashboard/serializers.py`・新規）にし、400 の文言を「期間の指定が正しくありません／日数は 1〜365 の整数で指定してください」にした — I452 の `review_summary` と同じ形。画面は `days` を送らないので利用者の目に触れない
- [plan] 正答率を小数第 2 位で丸める — ほかの正答率の欄と同じ
- [plan] 集計のサービス層への移動・overview の同じ計算の共通化はしない — #473 が作り直す
- [plan] おすすめの割り算は直さず回帰テスト（TC-05）だけ足す — 再現で 0 で割らないことを確かめた（HAVING の後）
- [implement] /simplify の 4 観点を 2 体にまとめて回した — 差分が 40 行ほどで、4 体は過剰。見送った指摘は計画変更記録に書いた
- [test-gate] 手動テスト No.3 を、計画の `browser_evaluate`（承認画面が出る操作）から、dev の backend のコンテナで `APIClient.force_authenticate` して呼ぶ形に変えた — 確かめたいのは dev で動くコードの応答で、承認なしで同じことを確かめられる。期待結果は同じ
- [test-gate] 統計の画面のコンソールに出た 2 件の error（開発サーバーの WebSocket・`Statistics` の一覧の `key` の警告）は今回と関係ない既存のものとして扱った — どちらも analytics の応答と無関係で、変更前からある
- [retro] 台帳の残り: F1 → #473（コメント）・F2 → #473（コメント）。どちらも `--route issue`（アプリ本体）。判定の仕組み・`SECURITY=yes` に関わる指摘は無いので「最優先」の注記は付けない。一覧（backlog）行き 0 件
- [retro] 改善案: 学習記録 API のクエリの数字の確かめ漏れ → 起票 I479（#479）。grill-me での言い間違い・`Statistics` の `key` の警告 → 見送り（理由は振り返りの 2.7 の判定）
STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
