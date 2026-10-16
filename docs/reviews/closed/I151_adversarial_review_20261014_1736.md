# 敵対的レビュー [I151] ── 2026-10-14

- 起動条件: `/code-review I151`（`docs/reviews/closed/I151_code_review_20261014_1548.md`）が `RISK: YES` / `FINAL_VERDICT: OK` → `ADVERSARIAL_STAGE: REQUIRED`
- 周回: 3 周（上限）・サブエージェント 12 体（各周 4 体＝固定 3 観点＋動的 1 観点「記録と実体の整合」）
- 結果: **上限到達・未収束**（第 3 周で新規 High 2 件が残存）→ 最終判定を HIGH に固定し、ユーザーへエスカレーション
- findings は依頼側（メインセッション）が自分で再実証してから扱った

## 周回サマリ

| 周 | 観点（エージェント数） | NEW_CRITICAL | NEW_HIGH | 是正コミット |
|---|---|---|---|---|
| 1 | ロジック回避 / false-green / 要件網羅 / 記録整合（4） | 0 | 4 | 5ed75ec ＋ PR #269 タイトル修正 |
| 2 | 同上（4） | 0 | 3 | 01e006d ＋ GitHub #267・#272 本文同期 |
| 3 | 同上（4） | 0 | 2 | （未是正・エスカレーション） |

依存更新（Django 5.2 / DRF 3.18 / django-filter 26.1 / django-redis 7 / CORS 4.9 / guardian・extensions 削除）が**原因の抜け道は 3 周とも見つからなかった**（ロジック回避観点は 3 周とも反証失敗）。High はすべてテスト判定式と記録の不備。

## 第 1 周 findings（High 4）と対応

| # | 重大度 | 指摘 | 対応 |
|---|---|---|---|
| 1-1 | High | TC-AUTO-03 が teardown error / xpassed 混入でも合格（pytest exit 1 でも合格） | サマリ行の完全一致 1 本に改め、合格 3 形・不合格 9 形で検証。pytest 再実行（94 passed）で合格 |
| 1-2 | High | 計画書 AC 表にイシュー受け入れ条件 2 件（psycopg2 動作・マイグレーション 2 経路の明記）が欠落／code-review 記録間で AC 番号体系が 3 通り | AC-22/23 を追補し、3 記録との番号対応表を 1 行ずつ照合して追加 |
| 1-3 | High | PR #269 タイトルが「6 件の CVE」（実 7 件）・django-extensions 削除の記載なし | `gh pr edit` でタイトル修正（件数を外し extensions を追記）。本文は `/close` で書き直す |
| 1-4 | High | （既存・I151 起因でない）クイズ作成で他組織の科目・問題が取得できる（テナント境界不備） | 別イシュー化（ユーザー承認済み方針）。manual_test No.7 の「組織越境は担保済み」の記述を訂正 |
| — | Medium | TC-06/07 の pathspec が cwd 依存・TC-15 パターンの緩さ・TC-07 の false-green 検証が旧方式・ロールバック（revert PR）が CI 必須チェックで不可・gunicorn 22.0.0 の CVE 可能性 | 判定式を `:(top)`・`-x`・大文字小文字/区切り両対応へ。§8 を前方修正へ訂正。gunicorn は別イシュー候補 |
| — | Low | TC-14 が 0 件で合格・AC-18 一覧に I102/I115 漏れ・行番号 41→40・plan-reviewer.md に guardian 観点残存・openai×httpx 非互換（既存）ほか | TC-14 に件数判定、AC-18 に 2 モジュール追加（13 passed を実測）、行番号修正。他は別イシュー候補／既存 |

## 第 2 周 findings（High 3）と対応

| # | 重大度 | 指摘 | 対応 |
|---|---|---|---|
| 2-1 | High | 計画書 §11 に旧文言「revert PR で行う」が残存（§8 と矛盾） | 前方修正へ書き換え |
| 2-2 | High | イシュー本文（#267）のロールバック項が「revert PR で戻す」のまま | ローカル・GitHub 本文とも前方修正へ訂正 |
| 2-3 | High | `test_I115_public_unauth.py` を「未認証 401」と記載（実体は未認証 200 の回帰テスト） | 計画書・manual_test の説明を訂正（401 拒否は I102 側が担保と明記） |
| — | Medium | 7→9 モジュールの件数不一致・AC-22/23 が TC 側から辿れない・前方修正にも行き止まり（I152 依存の未記載）・guardian 残置データ（AnonymousUser 1・contenttype 2・auth_permission 8）が I155 範囲外・TC-06/07 の `!` が実行エラーを合格に反転・TC-12 が suite 失敗を見逃す | すべて是正（TC-06/07 は「exit 1 のみ合格」、TC-12 は Test Suites 行と Tests 行の完全一致 2 本、I155 に範囲追加し #272 本文同期） |
| — | Low | TC-16 が 1 段目の照合なし・TC-15 の行頭アンカーで editable 形式を見逃す・TC-05 が requirements-dev.txt 対象外・rules/ に shell_plus 残骸・dependabot に LTS 除外なし | TC-16 判定 4 追加・TC-15 アンカー除去・TC-05 対象追加。残りは別イシュー候補 |
| — | （既存） | 登録処理が平文パスワードを INFO ログに出力（`accounts/views.py:90`）・UserSerializer の `is_email_verified` が書き込み可 | 別イシュー候補（I151 起因でない） |

## 第 3 周 findings（High 2・未是正）

| # | 重大度 | 指摘 | 該当箇所 | 再実証 |
|---|---|---|---|---|
| 3-1 | High | TC-AUTO-06/07 を「exit 1 のみ合格」に変えたのに、同じ TC 本文の false-green 根拠が旧形式の exit code のまま（「痕跡を検出（exit 1）」「exit 1（正しく不合格）」）。現判定式では逆（痕跡あり＝exit 0＝不合格）。記述どおりに再検証すると判定式が壊れていると誤判断する | `docs/tests/closed/I151_auto_test.md` 181・194 行 | 該当 2 行を確認（メインセッション） |
| 3-2 | High | TC-AUTO-13 のローカル手順 `docker compose --profile e2e run --rm e2e` はイメージを再ビルドしない。手元の `e2e-init` イメージは 5 か月前（Django 4.2.7・guardian 2.4.0）のままで、開発 DB `learning_app` に migrate する。それでも exit 0 で合格し、「まっさらな DB への migrate」も担保しない。記録上の合格は CI 実行（毎回ビルド）なので実害は未発生 | `I151_auto_test.md` TC-AUTO-13・`docker-compose.yml` e2e-init | `docker images` で e2e-init = 5 months ago・backend = 7 weeks ago を確認（メインセッション） |
| — | Medium | 「合格 = exit 0」の冒頭原則・手動 No.1 の期待結果・計画書 §7/テスト方針の「非ゼロ終了を確認」が TC-06/07 の例外と食い違う | `I151_auto_test.md` 7-8 行・`I151_manual_test.md` No.1・`plan_I151.md` §7 | — |
| — | Medium | E2E の `retries: 2` で flaky が exit 0 になる（`--fail-on-flaky-tests` 未使用） | `e2e/playwright.config.ts:15` | — |
| — | Medium | TC-AUTO-16 が「2 段目＝pytest 単独」を照合しない（2 段目が空コミットでも合格） | `I151_auto_test.md` TC-AUTO-16 | — |
| — | Medium | I155 の AnonymousUser 削除で `UserSettings` 1・`StudyStreak` 1 が CASCADE で連鎖削除されるのに、バックアップ・AC・Danger Ops・ロールバックが 2 テーブル前提のまま | `docs/issues/open/I155.md` | — |
| — | Medium | §8 の「branch protection 一時解除」に、元へ戻す手順・復元確認・期限が無い（danger-ops.md も対象外） | `plan_I151.md` §8・R6 | — |
| — | Low | イシュー本文のロールバック項に前方修正の行き止まり（I152 依存）が無い・TC-15 注記の参照先消失・PBKDF2 反復 1,000,000 化（次回ログイン時の再ハッシュ書き込み）の記載漏れ・管理画面 `format_html()` 引数なし呼び出しが `RemovedInDjango60Warning`（既存コード） | 各所 | — |
| — | （既存） | 管理画面の QuizSession 検索が 500（`search_fields` の `user__username` 不在）・`QuizAnswerAdmin.session_user` が `.username` 参照 | `problems/admin.py` | — |

## 別イシュー候補（I151 の範囲外・未起票）

1. クイズ作成で他組織の科目・問題が取得できるテナント境界の不備を修正（既存・セキュリティ・優先度高）
2. 登録処理のログに平文パスワードが出力される問題を修正（既存・セキュリティ）
3. gunicorn 22.0.0 の既知脆弱性（CVE-2024-6827）の確認と 23 系への更新
4. 削除済み依存（guardian / django-extensions）を前提とするレビュー観点・規約文書の記述を除去（`.claude/review-agents/plan-reviewer.md`・`rules/`）＋ dependabot に Django LTS 方針の除外設定（harness）
5. UserSerializer の `is_email_verified` を読み取り専用にする（既存）
6. 管理画面の不具合（QuizSession 検索 500・`.username` 参照・`format_html()` 引数なし）

VERDICT: HIGH
