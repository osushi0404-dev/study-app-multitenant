# I455 自動テスト: 学習記録まわりのモデルに組織の境界つきの取り出し方を持たせる

- 関連: docs/issues/open/I455.md / docs/plans/open/plan_I455.md / GitHub #455 / Draft PR #462
- 対象: `backend/studylogs/tests/test_I455_org_scoped_querysets.py`（新規）と、守りにする既存のテスト（I431・I166・#446。ファイルは変えない）
- 実行場所: app-1 ワークツリーのコンテナ（`docker compose exec -T backend ...`）。全テストは CI（PR #462）が正。手元では下の TC のファイルだけを流す
- 合否は終了コード（合格=0・不合格=非ゼロ）。否定・不在の TC は失敗の注入（FG）で非ゼロになることを確かめる

結果:
- backend: （実装後に記入）
- frontend: 対象外（変更なし）

## 実行記録
| 日時 | コマンド | 終了コード | 結果 |
|---|---|---|---|
| 2026-11-12 | TC-05（実装前） | 1 | 実装前のため不合格（`backend/studylogs/`・`backend/dashboard/` に `scope_to_user_org` などが残る）。実装後に 0 になることを確かめる |
| 2026-11-12 | TC-10（実装前） | 0 | `No changes detected`（ベースライン） |
| 2026-11-12 | TC-13（実装前） | 0 | 差分なし（ベースライン） |
| 2026-11-12 | TC-05 の正規表現の自己検証（scratchpad の使い捨てのファイル） | 0 / 1 | 4-3 の形のクラス属性（`subject_paths = (...)`・`allow_null = True`）だけのファイルでは exit 0（当たらない）。`scope_to_user_org(q)` の行を足すと exit 1（FG） |

## TC 一覧

| TC | 内容 | コマンド | 期待値 | 対応 AC |
|---|---|---|---|---|
| TC-01 | `test_for_user_scopes_by_org`（8 モデルでパラメータ化）: `user_a`（組織 A）の自組織の記録・他組織の科目（問題）を指す記録・科目が空の記録（空を許すモデルだけ）と、`user_a2`（組織 A の別の利用者）の記録を作り、`<Model>.objects.for_user(user_a)` を取る | `docker compose exec -T backend python -m pytest studylogs/tests/test_I455_org_scoped_querysets.py -q -k scopes_by_org` | exit 0。各モデルで、返る ID の集合が「自組織の記録」＋（StudyLog・QuizSession・MistakePattern・LearningSuggestion だけ）「科目が空の記録」と一致する。他組織の記録と `user_a2` の記録は含まれない | AC1・AC5 |
| TC-02 | `test_for_user_noorg_user`（8 モデル）: 組織に属さない利用者 `user_noorg` の、組織 A の科目を指す記録と科目が空の記録で `for_user(user_noorg)` を取る | `... -k noorg_user` | exit 0。空を許すモデルは科目が空の記録の ID だけ、ほかは空（`[]`） | AC1・AC5 |
| TC-03 | `test_learning_suggestion_both_paths`: 提案（subject・パターンの subject）の組を (自・自)・(自・他)・(他・自)・(空・空)・(自・空) で作る | `... -k both_paths` | exit 0。`for_user(user_a)` が返すのは (自・自)・(空・空)・(自・空) の 3 件だけ | AC1・AC5 |
| TC-04 | `test_base_without_subject_paths_raises`: 属性を書かない `OrgScopedQuerySet` で `for_user` を呼ぶ | `... -k without_subject_paths` | exit 0（`ImproperlyConfigured` が出ることを `pytest.raises` で確かめる） | AC1 |
| TC-05 | 呼び出し側に境界の指定（`scope_to_user_org` の呼び出し・`subject_path=`・`allow_null=` のキーワード引数）が残らない。QuerySet のクラス属性 `subject_paths = …`・`allow_null = …`（4-3）は「=」の前に空白があるので当たらない | 下の「TC-05 のコマンド」 | exit 0（1 行も当たらない）。FG: `backend/dashboard/views.py` に `# scope_to_user_org` の行を一時的に足すと exit 1。戻す | AC2 |
| TC-06 | `test_unscoped_reads_have_reason_comment`（基準の行はモデル名が書かれた行＝`<モデル>.objects` の `ast.Attribute` の `lineno`。複数行の呼び出しでも先頭の行）: `backend/studylogs/`・`backend/dashboard/` のテスト以外の `.py` で、8 モデルの `objects.<メソッド>`（`for_user`・`create`・`get_or_create`・`update_or_create`・`bulk_create` 以外）の行と直前 3 行に `組織で絞らない` がある | `... -k reason_comment` | exit 0 | AC3 |
| TC-07 | TC-06 の FG（3 種）: (a) `backend/studylogs/views.py` の `update_progress` の `組織で絞らない` のコメントを 1 つ消す (b) `backend/dashboard/views.py` に `StudyLog.objects.filter(user=user).count()` の行をコメントなしで一時的に足す (c) 同じ場所に、複数行に分けた `StudyLog.objects.filter(\n    user=user,\n).count()` をコメントなしで一時的に足す | `... -k reason_comment` を各 FG で | いずれも exit 1 で、失敗の文に注入したファイル名と行番号が出る。Edit で戻した後に exit 0 | AC3 |
| TC-08 | 守りの既存テスト（I431・I166・#446）と新しいテスト | 下の「TC-08 のコマンド」 | exit 0（failed 0。#446 の xfail はそのまま xfailed） | AC4 |
| TC-13 | 守りのテストのファイルを変えていない（基点はこのブランチの起点の develop のコミット `99b17757` に固定） | 下の「TC-13 のコマンド」 | exit 0（差分なし）。FG: I166 のテストのファイルの末尾に空行を一時的に足すと exit 1。戻す | AC4 |
| TC-09 | TC-01〜TC-03 の FG（3 種）: (a) `StudyLogQuerySet.allow_null` を `False` にする (b) 土台の `OrgScopedQuerySet.for_user` から `self.filter(user=user)` を外す（`self` のまま絞る） (c) `LearningSuggestionQuerySet.subject_paths` から `'mistake_pattern__subject'` を消す | `docker compose exec -T backend python -m pytest studylogs/tests/test_I455_org_scoped_querysets.py -q` を各 FG で | (a) TC-01・TC-02 の StudyLog が FAIL (b) TC-01 の 8 モデルすべてが FAIL（`user_a2` の記録が混ざる） (c) TC-03 が FAIL。いずれも exit 1。Edit で戻した後に exit 0 | AC5 |
| TC-10 | migration が増えない | `docker compose exec -T backend python manage.py makemigrations --check --dry-run` | exit 0（`No changes detected`）。FG: `backend/studylogs/models.py` の StudyLog の `objects = StudyLogQuerySet.as_manager()` を一時的に `objects = type('_M', (models.Manager.from_queryset(StudyLogQuerySet),), {'use_in_migrations': True})()` に置き換えると exit 1（Manager の変更を検出）。Edit で戻す | AC6 |
| TC-11 | CI の全テスト | `gh pr checks 462` | 全ジョブ pass（`Backend Tests` に `test_I455_org_scoped_querysets.py` の結果が出る） | AC7 |
| TC-12 | /simplify の後の流し直し | TC-05・TC-08・TC-10・TC-13 のコマンド | すべて exit 0 | AC2・AC4・AC6 |

## コマンド（表のセルに入れると `|` が崩れるため、ここに書く）

TC-05 のコマンド:
```bash
bash -c '! grep -rnE "scope_to_user_org|scope_learning_suggestions|subject_path=|allow_null=" backend/studylogs backend/dashboard --include=*.py --exclude-dir=tests'
```

TC-08 のコマンド:
```bash
docker compose exec -T backend python -m pytest studylogs/tests/ problems/tests/test_I166_quiz_tenant_isolation.py core/tests/test_I446_cross_api_tenant_isolation.py -q
```

TC-13 のコマンド:
```bash
git diff --exit-code 99b17757 -- backend/studylogs/tests/test_I431_studylogs_tenant_isolation.py backend/problems/tests/test_I166_quiz_tenant_isolation.py backend/core/tests/test_I446_cross_api_tenant_isolation.py
```
