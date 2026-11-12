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
- 自動（手元・app-1 のコンテナ）:
  - TC-01〜TC-04: 8 モデルの `for_user`・提案の 2 経路・土台の設定漏れ。失敗の注入 TC-09（allow_null の取り違え・本人の絞り込みを外す・提案の経路を 1 つにする）はすべて FAIL
  - TC-05・TC-06・TC-07: 呼び出し側に境界の指定が残らない・絞らない読み出しに理由のコメントがある・検出器が付け忘れ（コメントの共有・`models.X`・複数行・行末コメントの共有・文字列の中の印）を見落とさない。失敗の注入はすべて非ゼロ終了
  - TC-08・TC-13: I431・I166・#446 のテストがファイルを変えずに 183 passed・9 xfailed
  - TC-10: migration なし（FG で Manager の変更を検出することを実測）
- CI（PR #462・04c892c3）: 7 ジョブすべて pass。`Backend Tests` で新しいテスト 21 件を含む 306 passed・9 xfailed（TC-11）
- 手動（test-gate・Claude が Playwright MCP で実施）: No.1 ダッシュボード・学習統計の表示 OK、No.2 クイズの開始・回答・ダッシュボードの最近のクイズ（API の応答で確認）OK。Human の項目なし
- 判定: gate-check OK・check-frontend-evidence 対象外（frontend/src の変更なし）・check-manual-test-executor 合格

## 計画との差分
- TC-05 の正規表現から `allow_null=` を外した（DRF の入力欄の設定に当たる誤検出の直し・計画変更記録）
- 静的テストの対象モデルを登録から集め、表との一致のテストを 1 件足した（/simplify・計画変更記録）
- ほかは計画どおり（(B) の 9 か所はコードで確かめ直し、(C) に戻したものは無い）

## ロールバック
PR を revert する（コードだけの変更。DB の形は変えない）。

## 振り返り

### かんたんなまとめ
**良かった点**
- 境界の決まりがモデルごとに 2 行（科目への経路・空を許すか）にまとまり、呼び出し側の約 30 か所から指定が消えた（理由: 付け忘れや取り違えが起きる場所そのものを無くせた）
- 前のイシューのテスト（I431・I166・#446）をファイルを変えずに守りにして、振る舞いが変わっていないことを機械で確かめ続けられた（理由: 置き換えの誤りが入ればすぐ落ちる）
- 付け忘れを止める静的テストを、レビューの指摘に合わせて 3 回締め直し、最後は検出器そのものを確かめるテストまで CI に常設できた（理由: 「見張りが本当に効くか」も毎回確かめられる）

**今回の問題への直接の対処**
- レビューで止めなかった軽い指摘（書き出しの処理のコメントの言い回し・既存の NULL の不具合・静的テストの細かいすり抜け・重ねがけの結合の増加など 9 件）と、方式を変える提案（`owned_by` のようなメソッド・設定漏れを読み込み時に検出）を、同じ周辺を次に直す #452 にまとめて書いた。→ 次に同じファイルを触るときにまとめて扱えば、手戻りが少ないため

**同じ問題を次回から防ぐ改善**
- 敵対的レビューの実験役の環境に python が無く、テストの実験が空振りして、確認項目が「未検証」になり直しの周が 1 回増えた。実験役への案内に「アプリのテストはコンテナで動かす」が無いのが原因。→ 案内に足す改善を、敵対的レビューの実験の仕組みを直す #423 に同梱した
- コードレビューのやり直しのとき、前の回の記録のコミットを送っていないせいで「送っていない」と止まり、実行が 1 回むだになった。スクリプトが記録をコミットするのに、次の回は「送った状態」を求めるのが原因。→ 記録の場所だけの差なら通すように判定を直す改善を、review-gate の往復を直す #435 に同梱した

**見送ったもの（理由つき）**
- 文字列の確認（TC-05）が関係のない `allow_null=True` に当たった件: 実装の途中で捕まり、確認の正規表現を直すだけで済んだ（手戻りは数分）。新しい手順は足さない
- 静的テストの判定が 3 回締め直しになった件: レビューの流れの中で捕まって収束した。普通の書き方の事故を止める範囲という割り切り（R5）は計画どおりで、新しい手順は足さない
- 手動テストの期待結果に、画面に無い欄（最近のクイズ）を書いた件: test-gate で Claude がその場で気づき、API の応答で確かめ直せた（手戻りなし）。I446 でも似た直しがあったが、どちらもその場で直せており、観点を足すほどの損失は出ていない

### 詳細
#### 良かった点
- 8 モデルの境界の決まりを `OrgScopedQuerySet` のクラス属性に集約（AC1）。呼び出し側の `scope_to_user_org` 22 か所＋(B) 9 か所を `for_user` に置き換えた
- I431・I166・#446 のテストを無変更で守りにした（TC-08・TC-13）。失敗の注入（TC-05・TC-07・TC-09・TC-10・TC-13）をすべて実測
- 静的テスト（TC-06）と検出器の自己テスト（TC-07）を CI に常設

#### 是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | ベストプラクティス・技術選択 | 台帳の残り F1〜F5・F8〜F11（Low・KIND=app）と、範囲外にした方式の変更案が、同じ周辺の次のイシューで扱う内容 | #452 にコメントで同梱（`docs/reviews/I455_code_review_20261112_1020.md` の台帳・敵対的レビュー 2 周目の Low・/simplify の見送り） |

#### 予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| P1 | 予期しない問題・スキル | 敵対的レビューの実験役への案内に、アプリのテスト・管理コマンドをコンテナで動かすことが書かれておらず、ホストの python を前提にした実験が空振りする | 実験役の案内に「アプリのテスト・管理コマンドはコンテナ経由で実行する」を足し、「command not found / No such file」だけの実験は実行できなかったに数えて 1 回言い直させる（#423 に同梱） | `.claude/agents/adversarial-reviewer.md`・`scripts/claude/adversarial-review.sh` |
| P2 | プロセス・スキル | コードレビューのスクリプトは記録をコミットするが送らず、次の実行は「PR の最新＝手元の HEAD」を求める。直すものが無い失敗の後の実行し直しで必ず止まる | NOT_PUSHED の判定で、差が記録の場所だけなら通す（決定論）。だめならスキルの実行し直しの手順に「先に push」を足す（#435 に同梱） | `scripts/claude/code-review.sh`・`.claude/skills/review-gate/SKILL.md` |

#### 5 Whys（P1）
- Why 1: なぜ確認項目 V6 が未検証になったか → 実験役の pytest・makemigrations が `python: No such file` で動かなかった
- Why 2: なぜ動かなかったか → 実験役がホストで `python` を呼ぶ実験を作った
- Why 3: なぜホストで呼んだか → 実験役への案内に、このリポジトリのテストの動かし方（コンテナ）が書かれていない
- 抽象化: 「別プロセスの検証役に、対象の実行環境の前提（どこでどう動かすか）を渡していない」。I455 固有ではなく、アプリのテストを実験に使う敵対的レビューすべてで起こる → 予防処置

#### 5 Whys（P2）
- Why 1: なぜやり直しの実行がむだになったか → `CI_WAIT: NOT_PUSHED` で止まった
- Why 2: なぜ止まったか → 前の回の記録のコミットを送っていなかった
- Why 3: なぜ送っていなかったか → スクリプトは記録をコミットするが送らず、スキルの「1 回だけやり直す」手順にも送る手順が無い
- 抽象化: 「自動で記録をコミットする工程と、送った状態を前提にする工程の間に、送る手順が抜けている」。形の崩れ・`OFFICIAL_SECURITY: FAILED` の後のやり直しで毎回起こる → 予防処置

#### 残余リスク処遇（design-security-review）
- Medium（境界の値の取り違え・(B) の結果の変化）: TC-01〜TC-03・TC-08・TC-09 で塞いだ。残りなし
- Low（静的テストのすり抜け: 関連の取り出し・`get_or_create`・`get_object_or_404`・同じ行の 2 つの呼び出し）: R5（普通の書き方の事故が対象）として受け入れ、#452 に同梱。API の経路は #446 の横断テストが別に見る
- Low（匿名の利用者で 500）: 呼び出し元がすべて `IsAuthenticated` の後で、他組織のデータを出さない（fail-closed）。受け入れ

#### 設計ルール昇格
- 見送り: 今回のセキュリティのレビューで出た問題は、静的テストの検出の甘さ（テストの側）で、設計の確認観点にする一般的な型ではない

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
- [review-gate] 1 回目の差分のレビュー（20261112_0955）はレビュー役の出力の形の崩れで BLOCKER（台帳の周に数えない）だったので、仕組みの失敗として 1 回だけやり直した（記録のコミットの送り忘れで NOT_PUSHED になったので、送ってからもう一度）— 直すものが無い基盤の失敗のため
- [review-gate] fix-loop の後の差分のレビュー（20261112_1020）は OK、敵対的レビュー 2 周目（20261112_1031）は OK（未検証 0・新しい Critical・High 0）。残った Low（同じ行の 2 つの呼び出しが理由を共有する・空の理由・`get_object_or_404` など）は止める理由にせず retro へ — 普通の書き方の事故になりにくく、R5 の割り切りの範囲のため
- [test-gate] 手動テストの期待結果「ダッシュボードの最近のクイズの欄」を、画面に欄が無いため API の応答の直接の読み取りで確かめる形に直した — 画面のコードはこのイシューで変えておらず、確かめたいのはバックエンドの `recent_quizzes` の中身のため
- [retro] 台帳の残り F1〜F5・F8〜F11（9 件・すべて Low・KIND=app）は #452 にまとめて同梱（同じ周辺を次に直すイシューで、1 件ずつ起票するより手戻りが少ない）。一覧（`docs/reviews/backlog/`）に回るものは 0 件
- [retro] 改善案の振り分け: 敵対的レビューの実験役の環境の前提 → #423 に同梱／code-review.sh のやり直しの NOT_PUSHED → #435 に同梱／TC-05 の誤検出・静的テストの締め直し・手動テストの期待結果の画面の欄 → 見送り（どれも流れの中で捕まり、手戻りは数分。決まりを足すほどの損失が無い）。新規起票なし
- [close] develop への追従は不要（mergeStateStatus=BLOCKED＝承認待ち）。記録を closed へ移した。fix-loop の診断メモ（`docs/reviews/I455_fix_diagnosis_20261112_1010.md`）は close の回収の対象の形（`*_review_*`）でないので、手順どおり元の場所に残した — 計画書の計画変更記録がそのパスを参照しているため

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: design-security-review

STAGE_DONE: design-security-review NEXT: implement

STAGE_DONE: implement NEXT: review-gate

STAGE_DONE: review-gate NEXT: fix-loop

STAGE_DONE: fix-loop NEXT: review-gate

STAGE_DONE: review-gate NEXT: test-gate

STAGE_DONE: test-gate NEXT: retro

STAGE_DONE: retro NEXT: close

STAGE_DONE: close NEXT: merge
