# I166 敵対的レビュー記録 延長周（高リスク・code-review ステージ）

- 関連: docs/issues/closed/I166.md / docs/plans/closed/plan_I166.md / Draft PR #330
- 前の記録: docs/reviews/closed/I166_adversarial_review_20261025_1249.md（第 1 周・3 体とも報告なし）・docs/reviews/closed/I166_adversarial_review_20261025_1450.md（第 2 周）
- 実施理由: 第 1 周は確認画面で 3 体とも止まり反証の結果が得られず、第 2 周も 1 体は実測できなかった。ユーザーが「問題があったのはコードレビュー」と指摘し、延長の 1 周を承認（2026-10-25「その形で延長の 1 周を回して」）
- 見直し範囲: origin/develop からの変更全体（独立した検証のやり直しのため）

## やり方（第 1・2 周からの変更）
- レビュー役 3 体は **Read・Grep・Glob だけ**を使い、コマンドを一切実行しない（確認画面で黙って止まる経路を無くす）。
- 実験が要るときは、レビュー役が実験コードを報告に書いて返し、**親がそのまま実行**して出力（RESULT 行）を同じレビュー役に送り返す。往復は 1 体 2 回まで。
- 親が使う実行の形（`docker compose cp` → `docker compose exec -T backend python manage.py shell -c "exec(open('/tmp/x.py').read())"`／注入は `docker compose exec -T -e PYTHONPATH=/tmp backend python -m pytest ... -p <プラグイン>`）は事前に動作を確認した。`check-permission-prompt.sh` では通常モードで 3 つとも承認画面が出る判定（このセッションは自動承認モードで通る）。親が前面で実行するため、確認画面が出ても黙って止まらない。
- 時間切れは合格にしない（この周は 3 体とも上限内に報告）。

| 観点 | 往復 | 結果 | NEW_CRITICAL | NEW_HIGH |
|------|------|------|-------------|----------|
| 1. ロジック回避 | 0（静的読解で確定と判断） | 反証失敗・Low 1（範囲外） | 0 | 0 |
| 2. テストの false-green | 1（実験 1 本） | **High 1（範囲内・テストの穴）** | 0 | 1 |
| 3. 要件・脅威の網羅漏れ | 1（実験 3 本） | クイズの経路は反証失敗・**High 1（範囲外・以前からの別経路）**・Low 1（範囲外） | 0 | 1（範囲外） |

## findings

| 重大度 | 範囲 | 指摘内容 | 該当箇所 | 証跡 | 対応 |
|--------|------|---------|---------|------|------|
| High | **範囲内** | 復習モードで問題を選び直す 2 か所を、組織・科目で絞らない取得（`Problem.objects.filter(id__in=answered)`）に書き間違えても、テストが全件合格する。他組織の問題への過去の回答がセッションに残っていると、復習モードで他組織の問題文が出る（TC-09 と同じ多層防御の層の穴）。実装は正しく絞っている（テストの欠け） | `quiz_service.py` 復習モード／`test_I166_quiz_tenant_isolation.py` | 親が `fg_review.py` を実行 → **12 passed**（全件合格） | **修正済み**: TC-12 を 2 パターン追加。`fg_review.py` で 2 件 RED、片方ずつ壊す `fg_branch.py` で各パターンが狙った分岐だけ RED。137 passed |
| High | **範囲外**（以前からある別の経路・I166 の差分とは無関係） | 間隔反復のカード作成 API が問題を組織で絞らない。組織 A の一般ユーザーが組織 B の問題 ID を送ると、組織 B の問題文・解説・選択肢が返り、カードの一覧・復習対象からも読み出せる | `backend/studylogs/views.py:446`（`Problem.objects.get(id=problem_id, is_deleted=False)`）・`backend/studylogs/serializers.py:111-112` | 親が `req_x1.py` を実行 → `POST /api/study/spaced-repetition/create_card/` 201・本文に `'question': 'B1'`・`'explanation': 'B1の解説'`。`/api/study/sr-cards/` と `due_cards` にも B1。親がコードも読んで確認 | **ユーザーの判断待ち**（I166 に含めるか別イシューか） |
| Low | 範囲外 | 適応的な問題選択は科目なしで全組織の問題を対象にする（今は difficulty の型の不具合で 500 になり何も返さないが、直すと漏れ始める） | `backend/studylogs/adaptive_selection.py:293-316, 170` | 親が `req_x2.py` を実行 → 500・B の情報なし（漏れは静的読解による推定） | 上の High と同じイシューで扱う候補 |
| Low | 範囲外 | `submit_answer` の応答で `problem.explanation_image.url` を呼ぶが、`explanation_image` は文字列の欄のため、解説画像のファイル名が入った問題に回答すると、回答は保存されたうえで 500 になる | `backend/problems/views.py:969`・`backend/problems/models.py:136-142` | 静的読解（親もモデルとビューを読んで確認） | 別イシューの候補（組織の境界とは無関係） |

### クイズの経路で反証できなかったもの（親が実行した実験）
- `req_x3.py`: 科目なしの開始（total 1）→ 出題 A1 → 回答（正解・A1 の解説）→ 復習モードで A1 → 終了・詳細・一覧のどれにも B1〜B3 なし・自組織の解説は詳細に出る。もう一度挑戦と Idempotency-Key の再送は 201→200 で同じセッション。組織 B 側の出題は B の問題だけ。ダッシュボード 200。
- 観点 1 の静的読解: 他組織の選択肢を混ぜた回答・回答済みの判定・text 型・`next_problem` の応答（正解の露出なし）・削除済みの復習・`end`／`retrieve`／`list`・科目の削除（CASCADE）・同時実行のいずれも、範囲判定を通った問題か本人のセッションの上でしか動かない。

## 修正内容
- `backend/problems/tests/test_I166_quiz_tenant_isolation.py`: TC-12（`test_review_mode_ignores_foreign_answers`・2 パターン）を追加。実装コードの変更なし。

REVIEWED_COMMIT: 2aae715e51cc35584699fa93c71eec2fd96ccf14
ROUNDS: 1
VERDICT: OK
