# I132 実装レビュー（FE テストの axios 内部構造依存解消・DI + axios-mock-adapter）

- 関連: docs/issues/open/I132.md / docs/plans/open/plan_I132.md / GitHub #240 / Draft PR #243
- レビュー対象コミット: （実装後に記入）

## レビュー観点（計画に対応）

### 1. 内部構造依存の完全排除（最重要・AC-1）
- [ ] `api.test.ts` に `interceptors.response.handlers` への参照がない（TC-04(a)・grep exit 0）
- [ ] `api.test.ts` に `as any` が残っていない（TC-04(b)・grep exit 0）
- [ ] テストが公開インターフェース（`ApiClient` クラス・`client.get/post`・`toast.error` モック）のみで書かれている

### 2. api.ts の挙動不変（AC-4）
- [ ] api.ts の差分が計画 変更点2 の 2 箇所のみ（`export class` 追加＋コンストラクタ注入化。インターセプタ・メソッド・シングルトン export は無変更）
- [ ] 引数なし経路（`new ApiClient()`）の生成コードが現行と字面一致（baseURL/timeout/headers の設定値・フォールバック含めて同一）
- [ ] 本番コード（テスト以外）に `new ApiClient(` の新規使用が増えていない（シングルトン迂回の逆戻り検知・計画リスク4: `grep -rn "new ApiClient(" frontend/src --include="*.ts" --include="*.tsx"` の結果が api.ts の 1 箇所＋テストのみ）

### 3. 検証内容の維持と忠実度向上（AC-2/3）
- [ ] TC-01/02 の検証内容（429/500 → 文言）が I127 TC-FE-01/02 と同等（文言の完全一致 assert・呼び出し回数 assert）
- [ ] 実リクエスト経路（モックアダプタ→インターセプタ連鎖→handleApiError）で検証されている（rejected ハンドラの直接取り出しをしていない）
- [ ] TC-03（/auth/ スキップ）が 500 を使用している（401 ではリフレッシュ分岐に入り検証対象へ到達しない・計画 調査結果）
- [ ] テスト間の独立性: 各 TC が新品のインスタンス＋クライアントを使用し `afterEach` で `mock.restore()` している

### 4. 依存とバンドルの健全性（AC-5）
- [ ] `axios-mock-adapter` が **devDependencies** に入っている（dependencies でない）・package-lock.json が同時更新されている
- [ ] TC-06（audit: total ≤ 18 かつ critical = 0）が exit 0
- [ ] TC-07（build 成功＋成果物へ axios-mock-adapter 不在）が exit 0
- [ ] FE 全体回帰 3 suites / 10 passed（TC-05）

### 5. 計画との一致・記録の完全性
- [ ] 変更ファイルが計画の変更点一覧（変更点1〜3）のみ（計画外変更なし・manual No.1）
- [ ] false-green 注入検証 2 件（429 分岐破壊→TC-01 RED・/auth/ スキップ削除→TC-03 RED）と復元後 diff 確認が auto_test に記録済み
- [ ] 計画時前倒し実施済みの不在 grep NG 実証（2026-07-19・exit 1×2）と実装後の exit 0 転化が整合

## 敵対的レビュー観点(独立サブエージェント向け・「合格を反証せよ」)
- 「実経路で検証している」という主張を反証せよ: axios-mock-adapter は adapter 層を差し替えるが、リクエスト/レスポンス両インターセプタが本当に実行されているか（例: リクエストインターセプタの `X-User-Actions` ヘッダが mock.history のリクエストに載っているかで実証できるはず）。ハンドラ直接呼び出し時代より検証が弱くなった点はないか。
- 「挙動不変」という主張を反証せよ: コンストラクタの `instance ?? axios.create({...})` 化で、環境変数の評価タイミング・`??`/`||` の使い分け・headers の型など、現行と差が出る入力があるか。
- TC-03 の false-green を反証せよ: `/auth/` スキップではなく別の理由（例: 400 素通し・モック不一致で Network Error 扱い）で `toast.error` が呼ばれていないだけではないか（注入検証2 が本当にそれを弁別できるか）。
- TC-06 の閾値「total ≤ 18」を反証せよ: 既存 18 件のうち何かが解消されて 17 件になった場合や、audit DB 更新で件数が揺れた場合に、この TC は「axios-mock-adapter 起因の新規脆弱性」を見逃さないか（起因パッケージの確認まで必要か）。
- テスト独立性を反証せよ: `ApiClient` のモジュールスコープ副作用（import 時のシングルトン生成）や `userActionLogger` の sessionStorage 蓄積が、テスト間・スイート間で状態を持ち越す経路はないか。

## 結果

### 実装結果評価
（/code-review 実施後に記入）

### テスト結果
（/test 実施後に記入）

### 総合判定
（実施後に記入）
