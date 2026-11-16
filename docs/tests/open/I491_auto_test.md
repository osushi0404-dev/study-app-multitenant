# I491 自動テスト: I473 のレビューの残り（科目のキャッシュ・連続日数・E2E の比べ方・境界値・QuizAnswer の見張り）

実行コマンド（例）: `docker compose exec backend python -m pytest dashboard/tests/test_I473_overview.py problems/tests/test_I494_user_subjects.py studylogs/tests/test_I455_org_scoped_querysets.py` / E2E は CI の e2e ジョブ

結果:
- backend: 実装前のため未実行（すべて実装の後に動く TC。CI が正）
- e2e: 実装前のため未実行（CI）

テストの置き場所:
- TC-01〜TC-06・TC-10: `backend/dashboard/tests/test_I473_overview.py`（I491 の節を足す）
- TC-03 の I494 分: `backend/problems/tests/test_I494_user_subjects.py`
- TC-08・TC-09: `backend/studylogs/tests/test_I455_org_scoped_querysets.py`
- TC-07: `e2e/tests/quiz-session.spec.ts`

共通の準備: `test_I473_overview.py` の `setup`（組織 A・B、利用者 `user_a`〔A・数学/英語/理科を選択〕・`user_b`、A の科目 数学/英語/理科、B の科目「B科目」）。キャッシュを確かめる TC-01〜TC-03 は `@override_settings(CACHES=LOCMEM)` 相当で実際にキャッシュを通す（`test_I494_user_subjects.py` の `LOCMEM` と同じ形）。

| TC | 内容 | 期待値 | 失敗の注入（直す前・壊した作りで落ちること） |
|---|---|---|---|
| TC-01 | F5 の再現手順: `user_a`（組織 A）で `get_user_selected_subjects` を呼んでキャッシュを作る → `user_a.organization = B` で保存 → A の科目「英語」の `UserSubjectAccess` を消す（post_delete のシグナル） → `organization = A` に戻して保存 → `get_user_selected_subjects(user_a)` | 科目名の list が `["数学", "理科"]`（`order_by('name')` の順。英語が無い） | 直す前の作り（キーに組織）で書いて実行し、`["数学", "理科", "英語"]` 相当（英語が残る）で落ちることを実装のステップ 1 で記録する |
| TC-02 | 移った直後の取り違え: B の科目「B科目」を `user_a` が選んでいる状態（`UserSubjectAccess` を足す）で、A でキャッシュを作る → B へ移って保存 → 読む → A に戻して読む | B では科目名の list が `["B科目"]`（A の科目が出ない）。A に戻ると `["数学", "理科", "英語"]` を名前順にしたもの（B科目が出ない） | 「キーから組織を外すだけ・絞った後の値を保存」の作りで、B で `[]` になって落ちることを実装のステップ 1 で記録する（イシューのメモどおりの直し方の穴） |
| TC-03 | キャッシュのキーと中身の形: `user_subjects_cache_key(1) == "user_selected_subject_ids_1"`。`user_a` で読んだ後、キャッシュの値が選んだ科目の番号の list（番号順・組織で絞る前。TC-02 の準備なら B科目の番号も入る）。I473 の TC-16 の最後の行と I494 の TC-05 のキーを新しい形にする（I494 の TC-05 は、保存の前にキーに値があり、保存の後に消えることを今までどおり確かめる） | 値が `sorted([数学.id, 英語.id, 理科.id, B科目.id])`（TC-02 の準備のとき）。I494 の TC-05 が通る | キーの関数を古い形に戻すと I473 の TC-16 の行が落ちる（形の確かめ）。中身を辞書の list に戻すと値の比較で落ちる |
| TC-04 | F7 の窓の境目（`_current_streak(_answers(user), today, window_days=5)` を直接呼ぶ・`CaptureQueriesContext` で本数も数える）。`today = 2026-11-13`。表: (a) 今日まで 4 日続く → 4・1 本 (b) 今日まで 5 日（窓ちょうど）→ 5・2 本 (c) 今日まで 6 日 → 6・2 本 (d) 今日まで 11 日（窓 3 つ）→ 11・3 本 (e) 今日はまだ・昨日まで 5 日 → 5・2 本 (f) 今日まで 5 日・その前の 1 日が空・さらに前に 3 日 → 5・2 本 (g) `window_days=1` → `ValueError` | 各行の日数と本数が表のとおり | 窓の読み足し（`last = first - 1 日` で続ける部分）を外して `return streak` にすると (c) が 5・(d) が 5 になって落ちることを実装のステップ 3 で記録する |
| TC-05 | 既定の窓（365）を超える連続を `build_overview` で数える: 今日まで 366 日続く答え（`bulk_create` で日ごとに 1 つのセッションと答え・`bulk_update` で `answered_at` を直す）→ `build_overview(user, now=NOW)["streak"]` | `{"current_days": 366}`。365 日だけのとき `{"current_days": 365}` | 窓の読み足しを外すと 366 が 365 になって落ちる |
| TC-06 | B1 学習時間の上限の境界値: 今日に 299・300・301 秒の答え（`build_overview(user, now=NOW)["today"]`） | `study_seconds == 899`（299 + 300 + 300）・`answered_count == 3` | 上限の式を `Least` から外す（上限なし）と 900 になって落ちる。上限を 299 にすると 897 で落ちる |
| TC-07 | F6 E2E: 「クイズに答えると、ダッシュボードの解答問題数が増える」。答える前の数 `before` を読み、1 問答えてダッシュボードを開き直し、`expect.poll(() => 数字).toBeGreaterThan(before)` | 数字が `before` より大きい（CI の e2e ジョブで通る） | 答える操作を外すと `before` のままで落ちる（I473 で 0 のままだった不具合の再発防止になっていること） |
| TC-08 | Q1 `QuizAnswer.objects.for_user`: I455 の `SPECS` に `"QuizAnswer"`（作る関数: 終了済みのセッション〔利用者 u・科目 s〕と、その科目の問題への答え。`allow_null=False`）を足し、既存の `test_for_user_scopes_by_org`・`test_for_user_noorg_user` の表で確かめる。`test_specs_cover_all_scoped_models` も通る | 本人・自組織の科目の答えだけ（他組織・全体共有の科目・同じ組織の別の利用者の答えを返さない）。組織に属さない利用者は空 | `QuizAnswerQuerySet.user_path` を `'user'` のままにすると FieldError で落ちる。`subject_paths` を空にすると `ImproperlyConfigured` で落ちる |
| TC-09 | 見張りが `QuizAnswer` の絞らない読み出しを止める: `"QuizAnswer" in SCOPED_MODELS` と、`_missing_reasons("a = QuizAnswer.objects.filter(session__user=u)")` が `[1]`。既存の `test_unscoped_reads_have_reason_comment` が通る（`verify_data.py` の `bulk_update` に理由のコメントがある） | どちらも成り立つ | `verify_data.py` の足した理由のコメントを消すと `test_unscoped_reads_have_reason_comment` が `dashboard/verify_data.py:<行>` を出して落ちることを実装のステップ 2 で記録する。`QuizAnswer.objects` を既定の `models.Manager` に戻すと `"QuizAnswer" in SCOPED_MODELS` で落ちる |
| TC-10 | クエリ数: 既存の `test_query_count_is_constant`（I473 の TC-12）がそのまま通る | `large == 9` | （既存のテスト。F7 で 20 日のデータは窓の中なので本数が変わらないことを確かめる） |
| TC-11 | 退行: CI の backend のテスト全体・`makemigrations --check --dry-run`・E2E | すべて通る。マイグレーションが出ない | （CI） |

## 決定論ゲート（自動実走）
<!-- このイシューの守りは pytest（CI）で確かめる。review-gate が実走するゲートは無い -->
