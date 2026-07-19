# I132 自動テスト（FE テストの axios 内部構造依存解消・モックアダプタ実経路検証）

- 関連: docs/issues/open/I132.md / docs/plans/open/plan_I132.md / GitHub #240 / Draft PR #243
- 対象: `frontend/src/services/__tests__/api.test.ts`（書き換え）・`frontend/src/services/api.ts`（最小 DI）・`frontend/package.json`（dev 依存追加）
- 実行: `npm --prefix frontend test -- --watchAll=false`（個別は `--testPathPattern=api.test` を付与）
- テストレベル: FE 結合（axios 実リクエスト〜インターセプタ連鎖〜`handleApiError`〜toast 呼び出しの配線検証）＋決定論 TC（grep 不在チェック・audit 閾値・バンドル不変）

## fixture / ヘルパ方針

- 各 TC は `beforeEach` で `axios.create()` した**新品のインスタンス**に `MockAdapter` を装着し、それを注入した `new ApiClient(instance)` を使う（シングルトン非依存・テスト間の状態漏れなし・読み込み順序非依存）。`afterEach` で `mock.restore()`。
- `react-hot-toast` は現行同様 `jest.mock` でモックし `toast.error` の呼び出しを assert。
- URL は `/auth/` スキップ（`api.ts` の `handleApiError` 冒頭）を踏まない `/api/subjects/` を基本に使い、TC-03 のみ `/api/auth/login/` を使う。
- TC-03 は **500 を使う**（401 はトークンリフレッシュ分岐に入り、検証対象である `handleApiError` の `/auth/` スキップへ到達しないため・計画 調査結果参照）。

## テストケース

| TC | 内容 | 手順 | 期待値 | 実施者 |
|----|------|------|--------|--------|
| TC-01 | 429 でレート制限トースト（実経路・I127 TC-FE-01 相当の維持） | `mock.onGet('/api/subjects/').reply(429)` → `client.get('/api/subjects/')` | Promise が `{response: {status: 429}}` で reject・`toast.error` が `'リクエストが多すぎます。しばらく待ってから再試行してください'` で **1 回**呼ばれる | Claude |
| TC-02 | 500 トーストの退行なし（I127 TC-FE-02 相当の維持） | `mock.onGet('/api/subjects/').reply(500)` → `client.get('/api/subjects/')` | Promise が `{response: {status: 500}}` で reject・`toast.error` が `'サーバーエラーが発生しました'` で **1 回**呼ばれる（`toHaveBeenCalledTimes(1)`・plan-review Warning 対応で TC-01 と対称化） | Claude |
| TC-03 | `/auth/` URL のエラーでトーストを表示しない（新規・実経路化で通り道に入るスキップ分岐の固定） | `mock.onPost('/api/auth/login/').reply(500)` → `client.post('/api/auth/login/')` | Promise が `{response: {status: 500}}` で reject・`toast.error` が **呼ばれない** | Claude |
| TC-04 | axios 内部構造・`as any` 参照の不在（AC-1・決定論 grep） | (a) `! grep -q "interceptors.response.handlers" frontend/src/services/__tests__/api.test.ts` (b) `! grep -qF "as any" frontend/src/services/__tests__/api.test.ts` | (a)(b) とも **exit 0**（不在＝合格） | Claude |
| TC-05 | FE 全体回帰 | `npm --prefix frontend test -- --watchAll=false` | **3 suites / 10 passed**（既存 QuizSession 6＋App 1＋本ファイル 3。baseline 9 → 10 は TC-03 追加分） | Claude |
| TC-06 | npm audit ベースライン非増加（AC・依存追加直後に判定） | `npm --prefix frontend audit --json \| node -e "let s='';process.stdin.on('data',d=>s+=d).on('end',()=>{const v=JSON.parse(s).metadata.vulnerabilities;process.exit(v.total<=18&&v.critical===0?0:1)})"`（一時ファイル不使用・自己完結。plan-review Info 対応でプレースホルダ廃止） | **exit 0**（total ≤ 18 かつ critical = 0。2026-07-19 実測ベースライン: low 9 / moderate 4 / high 5 = 18 件・critical 0） | Claude |
| TC-07 | プロダクションバンドル不変（dev 依存がビルド成果物に混入しない） | `npm --prefix frontend run build` → `bash -c '[ -d frontend/build/static/js ] && ! grep -rq "axios-mock-adapter" frontend/build/static/js/'` | build が exit 0 で成功し、ガード付き不在チェックが **exit 0**（ディレクトリ存在ガードは build 未実行時に grep のエラー終了（exit 2）が `!` 反転で偽合格になるのを防ぐため） | Claude |

注:
- 決定論 TC（TC-04/06/07）の合否判定インターフェースは **exit code に統一**（合格=exit 0）。不在判定は `! grep -q` 形式・数値判定は node で exit code へ畳み込む。
- TC-05 の期待スイート/件数は baseline（2026-07-19: 3 suites / 9 passed・84 秒）からの差分（+1 件）として明示。
- TC-01/02 は検証内容（status→文言の対応）を I127 の TC-FE-01/02 から維持しつつ、検証経路をハンドラ直接呼び出し→実リクエストへ変更したもの（AC-2）。

## false-green 自己検証

### 計画時に前倒し実施済み（2026-07-19・不在 grep 2 本）
TC-04 の 2 本を「失敗条件が存在する現状態（書き換え前の api.test.ts）」に対して実行し、**両方 NG（exit 1）** を確認済み:
- (a) `! grep -q "interceptors.response.handlers" ...` → **exit 1**（参照が存在するため不合格＝正しく検知）
- (b) `! grep -qF "as any" ...` → **exit 1**（同上）
→ 実装完了後に exit 0 へ転じることをもって AC-1 達成と判定する。

### 実装後に失敗注入で確認（ステップ3）
- **注入検証1（TC-01・イシュー AC の false-green 検証）**: `frontend/src/services/api.ts` の `case 429:` 分岐を一時的にコメントアウト → TC-01 が **RED**（default 節の `'予期しないエラーが発生しました'` が呼ばれ文言不一致）になることを確認 → Edit で復元。
- **注入検証2（TC-03・新規分岐）**: `api.ts` の `handleApiError` 冒頭の `/auth/` スキップ（`if (error.config?.url?.includes('/auth/')) { return; }`）を一時的にコメントアウト → TC-03 が **RED**（`toast.error` が呼ばれる）になることを確認 → Edit で復元。
- **注入検証3（TC-06・audit 閾値判定ロジック・✅ 計画時に前倒し実施済み 2026-07-19）**: `echo '{"metadata":{"vulnerabilities":{"total":19,"critical":0}}}'` を TC-06 の node 判定式へパイプで食わせ → **exit 1（NG）** を実測（total 超過の検知）。`{"total":18,"critical":1}` でも **exit 1** を実測（critical 検知）。合格側 `{"total":18,"critical":0}` は **exit 0** を実測。ダミーファイル不要・実装後の再実施不要。
- **注入検証4（TC-07・バンドル不在 grep）**: `frontend/build/static/js/` に文字列 `axios-mock-adapter` を含むダミーファイルを一時作成 → TC-07 のガード付き grep が **exit 1（NG）** になることを確認 → ダミー削除（build 全体の再実行は不要・判定ロジックの検知能力のみを注入検証する）。
- **復元は必ず Edit ツールで注入前の内容に戻す**（`git restore` 禁止＝実装差分保護。ダミーファイルは削除）。復元後に `git diff -- frontend/src/services/api.ts` が実装差分（変更点2 の 2 箇所）のみであることを確認する。
- 記録欄（2026-07-19 /implement ステップ3 実施 ✅）:
  - 注入検証1: `api.ts` の `case 429` 3 行をコメントアウト → TC-01 **RED**（default 節の `'予期しないエラーが発生しました'` を実測・文言不一致で FAIL）→ Edit で復元。
  - 注入検証2: `/auth/` スキップの early return をコメントアウト → TC-03 **RED**（`toast.error` が `'サーバーエラーが発生しました'` で 1 回呼ばれる＝TC-03 の合格がスキップ分岐由来であることを弁別）→ Edit で復元。
  - 注入検証4: コンテナ経由で `build/static/js/__i132_injection_dummy.js`（文字列 `axios-mock-adapter` 入り）を作成 → TC-07 **exit 1（NG）** → ダミー削除 → **exit 0** 復帰。
  - 復元後 `git diff -- frontend/src/services/api.ts` = 変更点2 の 2 箇所のみ・`--testPathPattern=api.test` → **3 passed** を確認。

## 実施記録
- 2026-07-19（/implement 実施 ✅）:
  - TC-01〜03: `npm --prefix frontend test -- --watchAll=false --testPathPattern=api.test` → **1 suite / 3 passed**（ステップ2 ゲート通過＝モックアダプタとインターセプタ連鎖の協調成立）。
  - TC-04: (a) `interceptors.response.handlers` 不在 → **exit 0** (b) `as any` 不在 → **exit 0**（計画時の NG 実証 exit 1×2 から合格へ転化＝AC-1 達成）。
  - TC-05: `npm --prefix frontend test -- --watchAll=false` → **3 suites / 10 passed**（baseline 9＋TC-03 追加分・計画どおり）。
  - TC-06: audit パイプ判定 → **exit 0**（`npm install` 出力でも 18 件のままベースライン同値・low 9 / moderate 4 / high 5）。
  - TC-07: build 成功＋ガード付き不在 grep → **exit 0**。**実行環境注記**: ホストの `npm --prefix frontend run build` は既存 `frontend/build/static` が root 所有（過去のコンテナ内ビルド由来）のため EACCES で失敗 → `docker compose exec frontend npm run build` に切り替えて成功（I127 と同じ docker 実行様式・検証内容は同一。コンテナ側 node_modules へは `docker compose exec frontend npm install` で依存同期済み）。
