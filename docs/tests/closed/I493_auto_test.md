# I493 自動テスト: API のスキーマから画面の型を作る（ダッシュボードの overview から）

実行コマンド（例）: `docker compose exec backend pytest core/tests/test_I493_openapi_contract.py` / `docker compose exec frontend npm run typecheck`（pytest・Jest・型検査・lint・`api-types` ジョブは CI が PR ごとに流す。手元では流し直さない）

結果:
- backend: 手元（implement・2026-11-13）で `pytest core/tests/test_I493_openapi_contract.py dashboard/tests/test_I473_overview.py` が 33 passed（整理の後に I493 の 11 件を流し直して 11 passed）。CI の Backend Tests が成功（review-gate の `CI_WAIT: OK`・コミット 5c543f82）
- frontend: 手元（implement）で `tsc --noEmit` 終了コード 0・`npm run lint` 違反 0・`Dashboard.test.tsx` 10 passed。CI の Frontend Type Check・Frontend Lint & Security・Frontend Tests・API Types Up To Date（TC-20〜TC-22）が成功（同上）
- TC-21 の失敗の注入: 手元で CI と同じ手順を流し、`--check` が終了コード 1（「Generated types are not up-to-date!」）
- 決定論ゲート（TC-13）: review-gate の `code-review.sh` が実走して exit=0

## 実行記録
| 日時 | 段階 | コマンド | 終了コード |
|---|---|---|---|
| 2026-11-13 12:33 | review-gate | `bash scripts/claude/code-review.sh I493`（CI 待ち・決定論ゲート TC-13 の実走を含む） | 0（`CI_WAIT: OK`・`FINAL_VERDICT: OK`） |
| 2026-11-13 12:47 | test-gate | `bash scripts/claude/gate-check.sh I493` | 0（`GATE_CHECK: OK`） |
| 2026-11-13 12:48 | test-gate | test-gate に回された重いテストは無い（pytest・Jest・api-types は CI が流した） | — |

## テストケース

### backend（pytest・`backend/core/tests/test_I493_openapi_contract.py`）
| TC | 内容 | 期待値 | レベル | AC |
|---|---|---|---|---|
| TC-01 | コードから作ったスキーマ（`call_command('spectacular', '--file', <tmp>, '--validate', '--fail-on-warn')`）と `backend/openapi.yaml` の中身が同じ | 例外なく作れ（警告 0）、2 つの文字列が一致する。違えば `AssertionError` で、文に作り直すコマンド（`docker compose exec -T backend python manage.py spectacular --file openapi.yaml --validate --fail-on-warn`）が出る | 結合 | AC1・AC3 |
| TC-02 | 失敗の注入: 作り直したスキーマに 1 行（`# stale`）足した写しを `tmp_path` に書き、`assert_schema_file_matches` に渡す（本物のファイルは書き換えない。YAML の書式に頼らない注入にする） | `pytest.raises(AssertionError)` が成り立つ | ユニット | AC3 |
| TC-03 | コードから作ったスキーマを `yaml.safe_load` で読み、overview の形を確かめる | (1) `paths['/api/dashboard/overview/']['get']['responses']['200']` の `$ref` が `#/components/schemas/DashboardOverview`。(2) `DashboardOverview.required` が `{has_data, today, streak, totals, last_7_days, weak_subjects, recommendations}`、`has_data` が boolean、`last_7_days`・`weak_subjects`・`recommendations` が array で、要素の `$ref` が `DashboardDay`・`DashboardWeakSubject`・`DashboardRecommendation`。(3) `DashboardToday.required` が `{answered_count, correct_count, accuracy_rate, study_seconds}`・`DashboardTotals.required` が `{answered_count, correct_count, accuracy_rate}`、どちらも `accuracy_rate` が `type: number`・`nullable: true`。(4) `DashboardWeakSubject.accuracy_rate` は `nullable` が無い（null 不可）。(5) `DashboardDay.date` が `type: string`・`format: date`。(6) `DashboardStreak.required` が `{current_days}`。(7) `DashboardRecommendationKindEnum.enum` が `['weak_subject', 'unstudied_subject']`。(8) クエリの `subject_id` が `schema.type: integer` で `required` が無い。(9) 部品の名前 `DashboardToday` と `DashboardTotals` が両方ある（継承で同じ名前になっていない） | ユニット | AC1 |
| TC-04 | コードから作ったスキーマの `paths` のキーの集まりが `core.openapi.CONTRACT_PATHS` と同じ | `set(schema['paths']) == set(CONTRACT_PATHS)`（一覧に無い API が入らない） | ユニット | AC1 |
| 既存 | `backend/dashboard/tests/test_I473_overview.py`（他組織・未ログイン・科目の指定を含む） | 変更なしで通る（応答の中身・権限を変えていない） | 結合 | AC6 |

### frontend（CI の frontend-typecheck・frontend-test・frontend-lint）
| TC | 内容 | 期待値 | レベル | AC |
|---|---|---|---|---|
| TC-10 | `npm run typecheck`（TypeScript 4.9.5 で、作った `schema.d.ts`・`index.ts` と、それを使う `Dashboard.tsx`・`dashboard.service.ts` を検査） | 終了コード 0 | 静的 | AC2 |
| TC-11 | `CI=true npm test`（`Dashboard.test.tsx` の TC-22「形の違う応答・キーの欠けた応答はエラーの文を出し、0 で埋めた数字を出さない」を含む） | 全部通る | 結合 | AC4・AC6 |
| TC-12 | `npm run lint`（作った `frontend/src/types/api/schema.d.ts` も対象） | 終了コード 0・警告 0 | 静的 | AC6 |
| TC-13 | 手書きの overview の型が `frontend/src/services/types.ts` に残っていない（決定論ゲート） | `! grep -q "DashboardOverview" frontend/src/services/types.ts` が終了コード 0。失敗の注入: 置き換え前（2026-11-13・計画時）に流して終了コード 1 を確認済み | 静的 | AC2 |

### 道具・CI（CI の api-types・backend-lint）
| TC | 内容 | 期待値 | レベル | AC |
|---|---|---|---|---|
| TC-20 | `npm run check`（`tools/api-types`。`backend/openapi.yaml` から作り直した型と `frontend/src/types/api/schema.d.ts` を比べる） | 終了コード 0 | 静的 | AC2・AC3 |
| TC-21 | 失敗の注入: 型の写しの最後に 1 行足して `--check` をかける（ジョブの中の一時フォルダ・本物は書き換えない） | `--check` が非ゼロで、ステップが成功する。`--check` が 0 ならステップが `::error::` で落ちる。計画時のスパイク 4 で、ずれた写しで終了コード 1 を確認済み | 静的 | AC3 |
| TC-22 | `npm audit --audit-level=high`（`tools/api-types`） | 終了コード 0（計画時の実走で 0 件） | 静的 | AC5 |
| TC-23 | `pip-audit -r requirements.txt`（既存の backend-lint） | 終了コード 0（計画時に `drf-spectacular==0.30.0` と依存で 0 件） | 静的 | AC5 |

## 決定論ゲート（自動実走）
```bash
! grep -q "DashboardOverview" frontend/src/services/types.ts
```
