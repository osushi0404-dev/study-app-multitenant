# 敵対的レビュー [I493]（別プロセス・2026-11-13 12:46）

- 見た範囲: origin/develop...a843e90aa60dd976216a9ac768e332786555b6af
- 所要時間: 21 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- コンテナ: backend を起こして確かめた（12 秒・締め切りの外）
- 一覧: docs/plans/open/plan_I493.md の「## 必ず確かめる項目」（6 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V2 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V3 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V4 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V5 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V6 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 10 秒 | 0 | 0 | $0.2330 | ― | ― | ― |
| 2 | 報告あり | 19 秒 | 0 | 0 | $0.2504 | ― | ― | ― |
| 3 | 報告あり | 15 秒 | 0 | 0 | $0.2557 | ― | ― | ― |

## 実験

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

差分を読んだ範囲で V4・V6 を確認した。

# 敵対的レビュー [I493] ── 観点: 1. ロジック回避・実機 repro

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | CI の失敗の注入 | `openapi-typescript` が非ゼロで終了すれば何であっても成功扱いになる。道具の異常終了と、`--check` が差分を検出した場合を区別できない。既知の台帳 F4 と実質同一で、新規には数えない。 | .github/workflows/ci.yml（Failure injection ステップ） | 静的読解 |

新規の指摘はない。探索した仮説は次のとおり。

- **V4**: `api-types` ジョブには secrets の参照がない。action は `checkout` も `setup-node` も 40 桁の SHA で固定されている。ファイル全体の `permissions: contents: read` も差分に変更がない。`SERVE_INCLUDE_SCHEMA: False` で、`urls.py` は変更一覧に含まれない。そのため、スキーマを見せる URL は増えていない。
- **V6**: インストールは `npm ci --ignore-scripts` で、失敗の注入は `./node_modules/.bin/openapi-typescript` を直接呼んでいる。`npx` は使っていない。`run:` に `${{ github.event.* }}` など PR 由来の値はなく、使っているのは `$RUNNER_TEMP` だけ。`npm run check` は `package.json` の scripts 経由で、`npm run generate -- --check` を呼ぶだけ。外から取る処理はない。
- **注意点（Low）**: PR の作成者が `tools/api-types/package.json` の scripts を書き換えると、`npm run check` の中でコードが動く。ただし、secrets も書き込み権限もなく、既存の攻撃シナリオ #3 で Low と認識済みである。

> ITEM: V4 RESULT=read
> ITEM: V6 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I493] ── 観点: 2. テストの false-green・tautology

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| なし | - | 反証失敗（新規指摘なし） | - | 静的読解 |

反証失敗（新規指摘なし）。探索した仮説は次の 3 つ。いずれも静的読解だけで確かめた。実験は出していない。

1. **V1: TC-02 が実装をなぞるだけの tautology ではないか。**
   - TC-02 は `schema_text + '# stale\n'` を書いた写しを作る。これを `assert_schema_file_matches(stale_path, schema_text)` に渡し、`==` が偽になって `AssertionError` が出ることを見ている。
   - TC-01 も同じ関数を、本物の `backend/openapi.yaml` に対して使っている。比べる相手は fixture が `--fail-on-warn` で作った生成物なので、コミット済みの写し同士の比較にはなっていない。
   - この関数を常に真にする退行が入れば TC-02 が落ちる。TC-02 に意味はある。
   - TC-01 の失敗には `REGENERATE_HINT` が付く。
2. **V2: `api-types` ジョブが CI で飛ばされないか。**
   - `ci.yml` のトリガーは `push` と `pull_request`（対象は develop と main）で、`paths` の絞りは無い。
   - 差分に出ている `api-types` ジョブにも `if:` は無い。
   - `npm run check` は `generate -- --check` で、コミット済みの `schema.d.ts` と作り直した結果を比べる。
   - 失敗の注入のステップは、1 行足した写しに `--check` をかけ、通ったら `exit 1` にする。失敗の注入として成り立っている。
   - ただし、道具がクラッシュして非ゼロで終わっても注入が成功扱いになる。これは既知の Low（コードレビューの F4）なので、新規には数えない。
3. **scope 外の欠陥が混ざっていないか。**
   - 実行時の形の確かめ、型の精度、`--check` の比較先（出力ファイル）には、この観点の欠陥は見つからなかった。

> ITEM: V1 RESULT=read
> ITEM: V2 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I493] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | 網羅漏れ | `isDashboardOverview` は手書きのままで、スキーマにキーが増えても実行時の確かめに足し忘れたことをコンパイラが検知できない。`kind` の選択肢だけが `Record` で結ばれている。これは既知の F1 と同じなので、新規には数えない。 | dashboard.service.ts:34 | 静的読解 |
| Low | 網羅漏れ | `date` の形式（YYYY-MM-DD）の確かめが無く、`typeof string` だけ。`has_data` と `last_7_days` の空配列の許否は実行時だけで見ており、スキーマ側には出ない（`minItems` が無い）。画面が 0 で埋めない守りには影響しない。 | dashboard.service.ts:43-45 | 静的読解 |

V3 と V5 を読んで確かめた。

- V3: `openapi.yaml` を読んだ。必須のキー、`accuracy_rate` の `nullable`（Today と Totals は true、WeakSubject は無し）、`kind` の enum、`subject_id` が integer で省略可、という点が `OverviewSerializer` と一致している。
- V3: TC-01 は `--fail-on-warn` でスキーマを作って比べている。TC-03 は必須・型・null の可否を固定し、TC-04 は `paths` が `CONTRACT_PATHS` と同じかを見ている。
- V5: `isDashboardOverview` が残っていて、`getOverview` はその確かめに通らない応答なら例外を投げる。
- V5: TC-22 は、形の違う応答でエラーの文を出し、`0分`・`0日`・`0%` を出さないことを確かめている。
- V5: `kind` の確かめは `Record<Kind, true>` とプロパティの存在検査で、`__proto__` のような値でもすり抜けない。

網羅漏れで Critical または High になる穴は見つからなかった。

反証失敗（新規指摘なし）。探索した仮説:
- 実行時の確かめが空配列や null を通して 0 埋めになる経路。
- `accuracy_rate` の null の許否が TC-03 で固定されていないこと。
- `OrgSubjectField` の型を固定したことが、他組織の科目を弾く検証を弱めること（検証の処理は変えていない）。

> ITEM: V3 RESULT=read
> ITEM: V5 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: a843e90aa60dd976216a9ac768e332786555b6af
ROUNDS: 1
VERDICT: OK
