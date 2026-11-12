# I455 自動テスト: 学習記録まわりのモデルに組織の境界つきの取り出し方を持たせる

- 関連: docs/issues/open/I455.md / docs/plans/open/plan_I455.md / GitHub #455 / Draft PR #462
- 対象: `backend/studylogs/tests/test_I455_org_scoped_querysets.py`（新規）と、守りにする既存のテスト（I431・I166・#446。ファイルは変えない）
- 実行場所: app-1 ワークツリーのコンテナ（`docker compose exec -T backend ...`）。全テストは CI（PR #462）が正。手元では下の TC のファイルだけを流す
- 合否は終了コード（合格=0・不合格=非ゼロ）。否定・不在の TC は失敗の注入（FG）で非ゼロになることを確かめる

結果:
- backend: 新しいテスト（20 件）と守りのテスト（I431・I166・#446）が 182 passed・9 xfailed（#446 の既知の xfail）。失敗の注入（TC-05・TC-07・TC-09・TC-10・TC-13）はすべて非ゼロ終了。CI は review-gate で確かめる
- frontend: 対象外（変更なし）

## 実行記録
| 日時 | コマンド | 終了コード | 結果 |
|---|---|---|---|
| 2026-11-12 | TC-05（実装前） | 1 | 実装前のため不合格（`backend/studylogs/`・`backend/dashboard/` に `scope_to_user_org` などが残る）。実装後に 0 になることを確かめる |
| 2026-11-12 | TC-10（実装前） | 0 | `No changes detected`（ベースライン） |
| 2026-11-12 | TC-13（実装前） | 0 | 差分なし（ベースライン） |
| 2026-11-12 | TC-05 の正規表現の自己検証（scratchpad の使い捨てのファイル） | 0 / 1 | 4-3 の形のクラス属性（`subject_paths = (...)`・`allow_null = True`）だけのファイルでは exit 0（当たらない）。`scope_to_user_org(q)` の行を足すと exit 1（FG） |
| 2026-11-12 | ステップ 1 の後に TC-10 | 0 | `No changes detected`（8 モデルの Manager を足しても migration は出ない） |
| 2026-11-12 | TC-01〜TC-04（`-k "not reason_comment"`） | 1 → 0 | 初回はテストのデータの作り方の誤り（問題の作成者が必須・進行中のクイズの回は利用者ごとに 1 つ）で 8 failed。データを直して 18 passed |
| 2026-11-12 | TC-09 FG (a) `StudyLogQuerySet.allow_null = False` | 1 | TC-01・TC-02 の StudyLog の 2 件が FAIL。Edit で戻した |
| 2026-11-12 | TC-09 FG (b) `for_user` の `self.filter(user=user)` を `self` に | 1 | TC-01 の 8 モデルすべてが FAIL。Edit で戻した |
| 2026-11-12 | TC-09 FG (c) `LearningSuggestionQuerySet.subject_paths` から `'mistake_pattern__subject'` を消す | 1 | TC-03 が FAIL。Edit で戻した後 18 passed |
| 2026-11-12 | TC-05（置き換えの後・旧い正規表現） | 1 | `backend/studylogs/serializers.py` の DRF の `OrgSubjectField(..., allow_null=True)` などに当たった（境界の指定ではない）。正規表現から `allow_null=` を外した（計画変更記録） |
| 2026-11-12 | TC-05（直した正規表現） | 0 | 当たらない |
| 2026-11-12 | TC-05 FG（`backend/dashboard/views.py` に `# scope_to_user_org` の行を足す） | 1 | その行に当たった。Edit で戻した |
| 2026-11-12 | TC-06 | 0 | 1 passed |
| 2026-11-12 | TC-07 FG (a) `update_progress` のコメントを 1 つ消す | 1 | `['studylogs/views.py:327']` で FAIL。Edit で戻した |
| 2026-11-12 | TC-07 FG (b)(c) `dashboard/views.py` に 1 行の呼び出しと複数行の呼び出しをコメントなしで足す | 1 | `['dashboard/views.py:295', 'dashboard/views.py:296']` で FAIL（両方を検出）。Edit で戻した |
| 2026-11-12 | TC-08 | 0 | 181 passed・9 xfailed（26 秒） |
| 2026-11-12 | TC-10・TC-13 | 0 | `No changes detected`・差分なし |
| 2026-11-12 | TC-10 FG（StudyLog の Manager を `use_in_migrations=True` のものに差し替え） | 1 | `0002_alter_studylog_managers.py`（Change managers on studylog）を検出（`--dry-run` なのでファイルは作られない）。Edit で戻して `No changes detected` |
| 2026-11-12 | TC-13 FG（I166 のテストの末尾に空行を足す） | 1 | 差分を検出。Edit で戻して exit 0 |
| 2026-11-12 | /simplify の後に TC-12（TC-05・TC-08・TC-10・TC-13） | 0 | すべて exit 0。TC-08 は 182 passed・9 xfailed（静的テストの対象モデルを登録から集める変更で 1 件増えた） |
| 2026-11-12 | 敵対的レビュー 1 周目（20261112_0952）の Medium への対応の後に `-k reason` | 0 | 2 passed（本番のコードは理由が直前の行にあり、窓を狭めても合格） |
| 2026-11-12 | TC-07 FG: 窓を「直前 3 行」に戻す | 1 | `[5, 8, 9] == [3, 4, 5, 8, 9]` で FAIL（共有された行 3・4 を見落とす）。Edit で戻した |
| 2026-11-12 | TC-07 FG: `models.X` の形の検出を外す | 1 | `[3, 5, 8, 9] == [3, 4, 5, 8, 9]` で FAIL（行 4 を見落とす）。Edit で戻した |
| 2026-11-12 | 直した後に TC-08 | 0 | 183 passed・9 xfailed（35 秒） |

## TC 一覧

| TC | 内容 | コマンド | 期待値 | 対応 AC |
|---|---|---|---|---|
| TC-01 | `test_for_user_scopes_by_org`（8 モデルでパラメータ化）: `user_a`（組織 A）の自組織の記録・他組織の科目（問題）を指す記録・科目が空の記録（空を許すモデルだけ）と、`user_a2`（組織 A の別の利用者）の記録を作り、`<Model>.objects.for_user(user_a)` を取る | `docker compose exec -T backend python -m pytest studylogs/tests/test_I455_org_scoped_querysets.py -q -k scopes_by_org` | exit 0。各モデルで、返る ID の集合が「自組織の記録」＋（StudyLog・QuizSession・MistakePattern・LearningSuggestion だけ）「科目が空の記録」と一致する。他組織の記録と `user_a2` の記録は含まれない | AC1・AC5 |
| TC-02 | `test_for_user_noorg_user`（8 モデル）: 組織に属さない利用者 `user_noorg` の、組織 A の科目を指す記録と科目が空の記録で `for_user(user_noorg)` を取る | `... -k noorg_user` | exit 0。空を許すモデルは科目が空の記録の ID だけ、ほかは空（`[]`） | AC1・AC5 |
| TC-03 | `test_learning_suggestion_both_paths`: 提案（subject・パターンの subject）の組を (自・自)・(自・他)・(他・自)・(空・空)・(自・空) で作る | `... -k both_paths` | exit 0。`for_user(user_a)` が返すのは (自・自)・(空・空)・(自・空) の 3 件だけ | AC1・AC5 |
| TC-04 | `test_base_without_subject_paths_raises`: 属性を書かない `OrgScopedQuerySet` で `for_user` を呼ぶ | `... -k without_subject_paths` | exit 0（`ImproperlyConfigured` が出ることを `pytest.raises` で確かめる） | AC1 |
| TC-05 | 呼び出し側に境界の指定（`scope_to_user_org`・`scope_learning_suggestions` の呼び出しと、その引数 `subject_path=`）が残らない。QuerySet のクラス属性 `subject_paths = …`（4-3）は「=」の前に空白があるので当たらない。`allow_null=` は DRF の入力欄の設定（`serializers.py` の `OrgSubjectField(..., allow_null=True)` など）にも当たるので探さない（`scope_to_user_org` の呼び出しが無ければ、その引数としての `allow_null=` も無い） | 下の「TC-05 のコマンド」 | exit 0（1 行も当たらない）。FG: `backend/dashboard/views.py` に `# scope_to_user_org` の行を一時的に足すと exit 1。戻す | AC2 |
| TC-06 | `test_unscoped_reads_have_reason_comment`（基準の行はモデル名が書かれた行＝`<モデル>.objects` の `ast.Attribute` の `lineno`。複数行の呼び出しでも先頭の行）: `backend/studylogs/`・`backend/dashboard/` のテスト以外の `.py` で、8 モデルの `objects.<メソッド>`（`for_user`・`create`・`get_or_create`・`update_or_create`・`bulk_create` 以外）の行と直前の 1 行のどちらかに `組織で絞らない` がある（`StudyLog`・`models.StudyLog` のどちらの書き方も見る） | `... -k reason_comment` | exit 0 | AC3 |
| TC-07 | `test_reason_check_catches_unmarked_reads`（CI で毎回）: 合成したコードで、検出器が付け忘れの行（離れたコメントを共有する呼び出し・`models.X` の形・複数行の呼び出し・`filter(**kw)`・`.all()`）だけを返し、`for_user`・`create`・直前の行や同じ行に理由のある呼び出しを返さない。あわせて TC-06 の FG（3 種）: (a) `backend/studylogs/views.py` の `update_progress` の `組織で絞らない` のコメントを 1 つ消す (b) `backend/dashboard/views.py` に `StudyLog.objects.filter(user=user).count()` の行をコメントなしで一時的に足す (c) 同じ場所に、複数行に分けた `StudyLog.objects.filter(\n    user=user,\n).count()` をコメントなしで一時的に足す | `... -k reason_comment` を各 FG で | いずれも exit 1 で、失敗の文に注入したファイル名と行番号が出る。Edit で戻した後に exit 0 | AC3 |
| TC-08 | 守りの既存テスト（I431・I166・#446）と新しいテスト | 下の「TC-08 のコマンド」 | exit 0（failed 0。#446 の xfail はそのまま xfailed） | AC4 |
| TC-13 | 守りのテストのファイルを変えていない（基点はこのブランチの起点の develop のコミット `99b17757` に固定） | 下の「TC-13 のコマンド」 | exit 0（差分なし）。FG: I166 のテストのファイルの末尾に空行を一時的に足すと exit 1。戻す | AC4 |
| TC-09 | TC-01〜TC-03 の FG（3 種）: (a) `StudyLogQuerySet.allow_null` を `False` にする (b) 土台の `OrgScopedQuerySet.for_user` から `self.filter(user=user)` を外す（`self` のまま絞る） (c) `LearningSuggestionQuerySet.subject_paths` から `'mistake_pattern__subject'` を消す | `docker compose exec -T backend python -m pytest studylogs/tests/test_I455_org_scoped_querysets.py -q` を各 FG で | (a) TC-01・TC-02 の StudyLog が FAIL (b) TC-01 の 8 モデルすべてが FAIL（`user_a2` の記録が混ざる） (c) TC-03 が FAIL。いずれも exit 1。Edit で戻した後に exit 0 | AC5 |
| TC-10 | migration が増えない | `docker compose exec -T backend python manage.py makemigrations --check --dry-run` | exit 0（`No changes detected`）。FG: `backend/studylogs/models.py` の StudyLog の `objects = StudyLogQuerySet.as_manager()` を一時的に `objects = type('_M', (models.Manager.from_queryset(StudyLogQuerySet),), {'use_in_migrations': True})()` に置き換えると exit 1（Manager の変更を検出）。Edit で戻す | AC6 |
| TC-11 | CI の全テスト | `gh pr checks 462` | 全ジョブ pass（`Backend Tests` に `test_I455_org_scoped_querysets.py` の結果が出る） | AC7 |
| TC-12 | /simplify の後の流し直し | TC-05・TC-08・TC-10・TC-13 のコマンド | すべて exit 0 | AC2・AC4・AC6 |

## コマンド（表のセルに入れると `|` が崩れるため、ここに書く）

TC-05 のコマンド:
```bash
bash -c '! grep -rnE "scope_to_user_org|scope_learning_suggestions|subject_path=" backend/studylogs backend/dashboard --include=*.py --exclude-dir=tests'
```

TC-08 のコマンド:
```bash
docker compose exec -T backend python -m pytest studylogs/tests/ problems/tests/test_I166_quiz_tenant_isolation.py core/tests/test_I446_cross_api_tenant_isolation.py -q
```

TC-13 のコマンド:
```bash
git diff --exit-code 99b17757 -- backend/studylogs/tests/test_I431_studylogs_tenant_isolation.py backend/problems/tests/test_I166_quiz_tenant_isolation.py backend/core/tests/test_I446_cross_api_tenant_isolation.py
```

## 再発防止記録（fix-loop・2026-11-12）
- なぜ失敗したか: コードレビュー（20261112_1006）の F6（Medium）。付け忘れ防止の検出器が「直前の 1 行か同じ行に印の文字がある」だけを見ていた。前の行の呼び出しの行末コメントが、次の行の別の呼び出しの理由として使い回せた（敵対的レビュー 1 周目で窓を 3 行から 1 行に狭めた後も残った形）
- 何を変えたか: `tokenize` でコメントだけを拾い、理由を認める場所を「直前のコメントだけの行」と「同じ行のコメント」に限った。文字列の中の印も理由に数えない（`backend/studylogs/tests/test_I455_org_scoped_querysets.py` の `_missing_reasons`）。TC-07 の合成コードに、行末コメントの共有（13 行目）と文字列の中の印（14・15 行目）を足した
- セキュリティ上の考慮点: 他組織のデータの読み出しの付け忘れが CI を通る穴を塞ぐ（OWASP A01 の再発防止の作り）。普通の書き方の事故が対象（R5）
- 次回どう防ぐか: 検出器の判定を変えるときは、合成コードの TC-07 に「共有」「別の書き方」の形を足してから変える。窓や部分一致のような近似の判定は、コメントと文字列を区別する標準の仕組み（`tokenize`）で置き換える
- 確かめた結果:

| 日時 | コマンド | 終了コード | 結果 |
|---|---|---|---|
| 2026-11-12 | `docker compose exec -T backend python -m pytest studylogs/tests/test_I455_org_scoped_querysets.py -q -k reason` | 0 | 2 passed（本番のコードの理由コメントはすべてコメントだけの行で、落ちる箇所は無い） |
| 2026-11-12 | FG: 直前の行の判定から「コメントだけの行」の条件を外す・`-k catches_unmarked` | 1 | `[3, 4, 5, 8, 9, 15] == [3, 4, 5, 8, 9, 13, ...]` で FAIL（行末コメントの共有の 13 行目を見落とす）。Edit で戻した |
| 2026-11-12 | 戻した後に `studylogs/tests/test_I455_org_scoped_querysets.py` 全体 | 0 | 21 passed |
