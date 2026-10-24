# I158 敵対的レビュー記録（高リスク判定 YES・code-review 20261024_1738 の FINAL_VERDICT: OK を受けて実施）

- 対象: feature/I158-prevent-duplicate-quiz-session（Draft PR #317）
- 上限: 1 体 15 分・攻め筋 1 体 3 本まで・1 周 3 体（固定 3 観点）・イシュー全体 2 周まで
- 結果: 第 1 周で新規 High 1 件 → 修正 → 第 2 周（修正差分のみ）で新規 Critical/High 0 件 → **ステージ通過**

## 第 1 周（範囲: `origin/develop...7d9ba67`）

| 観点 | 時間切れ | NEW_CRITICAL | NEW_HIGH | 主な結果 |
|------|---------|-------------|---------|---------|
| ロジック回避・実機 repro | なし | 0 | 0 | 12 スレッド同時開始（同じキー／キー無し／毎回違うキー＋直後の end）で 500 / 409 なし・同じキーは同じ id・有効は常に 1 件以下。作成・有効化の経路は `start_session` のみ。フロントのガードの抜け道なし |
| テストの false-green・tautology | なし | 0 | 1 | 下表 |
| 要件・脅威モデルの網羅漏れ | なし | 0 | 0 | 下表（Low 1） |

### findings

| 重大度 | 観点 | 指摘 | 対応 |
|--------|------|------|------|
| High | false-green | TC-18 がテスト内で `update_fields` を書いているだけで `views.py` を通らず、`submit_answer`／`end` を `session.save()` に戻す回帰を検出できない。それを捕まえる TC-19（grep）は CI に入っていない | **修正**: TC-18 を `get_object` に古い実体を返して実際の `submit_answer` を通す形に変更。TC-19 を pytest（`inspect.getsource(QuizSessionViewSet)`）に移し CI で毎回実行。`submit_answer` を `session.save()` に戻すと TC-18（`IntegrityError`）・TC-19 とも RED を確認（b70cc66） |
| Medium | false-green | TC-14／TC-21 は本物のマイグレーション順（0019→0020→0021・重複データあり）を CI で通らない（`--no-migrations`） | 受け入れ（High に直結しない）。TC-21 は /test で再実行、dev DB（重複 5 件あり）への適用で実経路を確認済み（手動 No.1〜3）。CI に重複ありのマイグレーション試験を足すかは /retro で判断 |
| Low | false-green | TC-19 の文字列は変数名を変えた全列保存を検出しない | 受け入れ（わざと回避する書き方に近い） |
| Low | 要件 | 計画にデプロイ順序の記述がない（旧コードと新スキーマの共存で一時的な 500・0020/0021 の隙間） | **修正**: 計画「8. Risk & 回避策」リスク7 に追記（b70cc66・第 2 周で手順を訂正） |
| （code-review Medium） | 要件 | 「もう一度挑戦」後も完了画面のまま | **修正**: `createNewSession` 冒頭で `setSessionComplete(false)`・TC-34 に画面切り替えを追加（b70cc66） |

## 第 2 周（範囲: `7d9ba67...b70cc66`・修正差分のみ）

| 観点 | 時間切れ | NEW_CRITICAL | NEW_HIGH | 主な結果 |
|------|---------|-------------|---------|---------|
| ロジック回避・実機 repro | なし | 0 | 0 | `setSessionComplete(false)` の副作用なし（初回・失敗・StrictMode・連打・表示分岐順）。テストの変更に副作用なし |
| テストの false-green・tautology | なし | 0 | 0 | 注入で確認: `submit_answer` を全列保存 → TC-18・TC-19 RED／`update_fields` に `is_active` → TC-18 RED／`end` を全列保存 → TC-19 RED／`setSessionComplete(false)` 削除 → TC-34 RED。TC-19 は CI の pytest で収集される |
| 要件・脅威モデルの網羅漏れ | なし | 0 | 0 | 下表（Medium 2） |

### findings

| 重大度 | 観点 | 指摘 | 対応 |
|--------|------|------|------|
| Medium | 要件 | 完了画面の URL（`/quiz/<id>`）には `?subject` が無いので「もう一度挑戦」が科目なしで開始され、`setSessionComplete(false)` の追加で他の科目（科目なしの出題は全組織＝I166 の穴）の問題が画面の普通の操作から出るようになった。TC-34 は実際には起きない `id`＋`?subject` の組み合わせで隠していた | **修正**: `createNewSession(subject, key)` に変更し、再挑戦は `subjectId ?? session?.subject`。TC-34 は `?subject` なしのモックで「終えたセッションの科目で開始」を検証（`subjectId` だけ渡すと RED を確認） |
| Medium | 脅威モデル | リスク7 の回避策「`migrate` を再実行すれば 0020 が再び重複を解消する」は成り立たない（0020 は適用済みとして記録される。backend は `migrate && runserver` のため起動失敗が続く） | **修正**: 計画のリスク7 を「0020 の関数を shell で実行して重複を解消してから再実行」に訂正 |
| Low | false-green | `end` の `update_fields` に件数列を足す回帰は検出されない（`is_active` は常に False を書くため復活は起きず、既知の 2 タブ同時回答の取りこぼしと同種） | 受け入れ |

## 修正後の確認
- Backend: 全体 123 passed（第 1 周修正後）。Frontend: 4 suites / 13 passed・`tsc --noEmit` exit 0・eslint exit 0（第 2 周修正後）。
- 第 2 周の Medium 修正は High に直結しないため、周回の追加はしない（上限 2 周に到達済み）。

REVIEWED_COMMIT: b70cc662a7fd48668698f8ed26640015560cb9d0
ROUNDS: 2
VERDICT: OK
