## 基本情報
- **計画書ID**: plan_I132
- **関連イシュー**: #240
- **Draft PR**: #243
- **作成根拠資料**: docs/issues/open/I132.md（起点イシュー・grill-me 設計確認メモ確定済み）
- **実装後評価**: docs/reviews/open/I132_review.md
- **作成日**: 2026-07-19

---

## 1. 背景/目的

I127 で追加した FE 回帰テスト `frontend/src/services/__tests__/api.test.ts` が axios の**内部構造**（`(apiClient as any).instance.interceptors.response.handlers[0].rejected`）に直接依存しており、I127 コードレビューで Low 指摘を受けた。axios のバージョンアップやインターセプタの追加/並び替えで、テストが実装と無関係に壊れる・別ハンドラを掴んで false-green になるリスクがある。

- **原因の概要**: HTTP モックライブラリが未導入だったため、インターセプタのエラーハンドラを「配列の 0 番目」という内部実装の知識で直接取り出して呼ぶ暫定方式を採用した（plan_I127「設計判断の明示」に記録済みの意図的な妥協）。
- **詳細な原因分析**:
  1. `api.test.ts:18` が `(apiClient as any).instance.interceptors.response.handlers[0].rejected` を参照。`handlers` 配列・`rejected` プロパティ名は axios の非公開実装であり、公開 API 契約の外。
  2. さらに根本には「`ApiClient`（`api.ts:5`）が axios インスタンスを `private` で内部生成し、外から差し替え不能」という設計があり、モックライブラリを導入しても取り付け先がないという構造問題がある（テストのための小細工が要る＝設計の歪みのシグナル）。
- **根本原因（コードレベル）**: `api.ts` の `ApiClient` コンストラクタが依存（axios インスタンス）を注入不能な形で抱え込んでいること＋HTTP モックライブラリの不在。

## 調査結果

### 環境前提確認（2026-07-19 実施）
- `node --version` → v24.14.1・`npm --version` → 11.11.0（ホストで npm 実行可能）。`frontend/package-lock.json` 存在（npm ci 経路）。
- I127（PR #236）は **develop へマージ済み**（`gh pr view 236` → MERGED・2026-07-19T04:02Z）。前提の `case 429` 実装・トースト文言は develop 上に存在（`api.ts:184-186`）。

### ライブラリ互換性（grill で実測確定）
- `npm view axios-mock-adapter version peerDependencies` → **2.1.0**・peer `axios >= 0.17.0`。本体 axios `^1.17.0` と互換。
- msw は不採用（CRA の Jest 27・jsdom 16 でポリフィル追加が多数必要。axios 専用の本用途には axios-mock-adapter が軽量で十分・grill 設計確認メモ）。

### npm audit ベースライン（2026-07-19 実測・AC 判定基準）
- `npm --prefix frontend audit` → **18 件**（low 9 / moderate 4 / high 5・critical 0）。**すべて react-scripts 系の開発時 transitive 依存**（jest 27 系・serialize-javascript・uuid/sockjs 系）で本イシューと無関係。
- → AC は「**total ≤ 18 かつ critical = 0**（ベースラインから増えない）」として機械判定する（TC-06）。axios-mock-adapter 2.1.0 の依存は fast-deep-equal / is-buffer のみで既知脆弱性報告なし。

### 既存テスト baseline（事前実行・2026-07-19）
- Frontend: `npm --prefix frontend test -- --watchAll=false` → **3 suites / 9 passed**（api.test.ts 2・QuizSession 6・App 1。約 84 秒・クリーン）。
- Backend: 変更なしのため未実行（本イシューは FE のみ・BE への影響ゼロ）。

### 決定論 TC の false-green 自己検証（計画時に前倒し実施済み・2026-07-19）
不在チェック 2 本を「失敗条件が存在する現状態」に対して実行し、**両方 NG（exit 1）** を確認済み＝false-green でない:
- `! grep -q "interceptors.response.handlers" frontend/src/services/__tests__/api.test.ts` → exit 1（現行ファイルに参照が存在するため不合格＝正しく検知）
- `! grep -qF "as any" frontend/src/services/__tests__/api.test.ts` → exit 1（同上）
実装完了後は両方 exit 0（合格）に転じることが AC-1 の判定（TC-04）。

### 実経路化で新たにテストの通り道に入るコードの安全性確認
- リクエストインターセプタ（`api.ts:24-53`）が `localStorage`・`userActionLogger.getActionsForAPI()` を呼ぶ。jsdom は localStorage/sessionStorage を提供し、`getActionsForAPI` はメモリ配列の JSON 化のみ（`userActionLogger.ts:133-135`）→ テスト環境で副作用なし。
- 429/500 は 401 リフレッシュ分岐（`api.ts:80`）に入らないため、リフレッシュ経路の副作用（localStorage 書き換え・リダイレクト）は発火しない。`/auth/` TC も 500 を使い 401 を避ける。

### 適用規約（rules/ より抽出）
- React 規約: `any` 型の排除（現行テストの `as any` 撤去は規約準拠の改善）・テストは Jest + Testing Library 構成に追随・型は公開 API（`ApiClient` クラス・`AxiosInstance`）のみ使用。
- Django 規約: 対象外（Backend 変更ゼロ）。

## 2. 受け入れ条件（Acceptance Criteria）
イシューの AC をそのまま採用（判定の機械化を付記）:
- [ ] `api.test.ts` に axios 内部構造（`interceptors.response.handlers` 等）および `as any` でのプライベートプロパティ参照が存在しない（TC-04 の grep 2 本・合格=exit 0）
- [ ] 429 トースト・500 トーストの検証内容（TC-FE-01/02 相当）が維持され、実リクエスト経路（インターセプタ連鎖）で検証される（TC-01/02）
- [ ] `/auth/` URL の場合にトーストを表示しないスキップ分岐が 1 ケース検証される（TC-03）
- [ ] `api.ts` の DI 変更後もシングルトン `apiClient` の既定動作が不変（TC-05 全体回帰＋TC-07 バンドル不変＋変更点差分レビュー）
- [ ] FE テストスイート全 PASS・`npm audit` がベースライン 18 件から増えない（TC-05・TC-06）
- [ ] false-green 検証: `api.ts` の 429 分岐を一時破壊するとテストが FAIL することを確認（注入検証 1）

## 3. 影響範囲
- **Backend**: なし
- **Frontend**: `frontend/src/services/api.ts`（最小 DI 変更・挙動不変）・`frontend/src/services/__tests__/api.test.ts`（書き換え）・`frontend/package.json` + `frontend/package-lock.json`（devDependencies 追加）
- **DB**: なし
- **Config/Infra**: なし。依存関係ファイル（package.json/package-lock.json）変更の波及: `frontend/Dockerfile` は `npm install`（dev 含む）・CI は `npm ci` でロックファイルから解決するため**手当不要**（devDependencies 追加はどちらも自動で取り込まれる）。プロダクションバンドルは不変（dev 依存はビルド成果物に入らない・TC-07 で機械確認）

## 4. 変更点一覧

**修正アプローチ**: 「テスト都合の回避策を積む」のではなく、根本原因である「依存の注入不能」を api.ts 側の最小 DI（コンストラクタ注入・省略時は現行同等）で解消する。その上でテストは、モックアダプタを装着した axios インスタンスを注入した `new ApiClient(instance)` に対して**実際にリクエストを発行**し、インターセプタ連鎖を実経路で通してトースト表示を検証する方式へ書き換える。

| # | ファイル | 対象 | 変更内容 |
|---|---------|------|---------|
| 1 | `frontend/package.json`（+lock） | devDependencies | `axios-mock-adapter: ^2.1.0` を追加（`npm install --save-dev axios-mock-adapter` で lock 同時更新） |
| 2 | `frontend/src/services/api.ts` | `ApiClient` クラス宣言（:5）とコンストラクタ（:10-20） | `export class ApiClient` に変更＋`constructor(instance?: AxiosInstance)`（未指定時は現行と同一設定で内部生成）。**他は一切変更しない**（インターセプタ・メソッド・シングルトン export 不変） |
| 3 | `frontend/src/services/__tests__/api.test.ts` | 全体 | 内部構造参照を廃し、モック装着インスタンス注入方式へ書き換え（TC-01/02 維持＋TC-03 追加・下記コード例） |

### 実装コード例

**変更点2** `frontend/src/services/api.ts`（差分イメージ・変更はこの 2 箇所のみ）:
```typescript
// :5 クラス宣言に export を追加
export class ApiClient {
  private instance: AxiosInstance;
  private refreshingToken = false;
  private refreshPromise: Promise<string> | null = null;

  // :10 コンストラクタに省略可能な注入引数を追加（未指定時は現行と同一の内部生成）
  constructor(instance?: AxiosInstance) {
    this.instance =
      instance ??
      axios.create({
        baseURL: process.env.REACT_APP_API_BASE_URL ?? '',
        timeout: parseInt(process.env.REACT_APP_API_TIMEOUT || '10000'),
        headers: {
          'Content-Type': 'application/json',
        },
      });

    this.setupInterceptors();
  }
  // 以降は不変更。末尾の
  //   export const apiClient = new ApiClient();
  //   export default apiClient;
  // も不変更（引数なし＝従来と同一挙動）
```
（注入されたインスタンスにも `setupInterceptors()` が適用されるため、テストは本番と同一のインターセプタ連鎖を通る）

**変更点3** `frontend/src/services/__tests__/api.test.ts`（全文置き換え）:
```typescript
/**
 * I132: handleApiError のトースト分岐の回帰テスト（実リクエスト経路）。
 *
 * axios-mock-adapter を装着したインスタンスを ApiClient に注入し、
 * インターセプタ連鎖（401 リフレッシュ分岐→handleApiError）を実経路で通して検証する。
 * TC 詳細: docs/tests/open/I132_auto_test.md
 */
import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';
import { toast } from 'react-hot-toast';

import { ApiClient } from '../api';

// jest.mock は babel-jest により import より先に巻き上げられる
jest.mock('react-hot-toast', () => ({
  toast: { error: jest.fn() },
}));

describe('api client handleApiError (I132)', () => {
  let mock: MockAdapter;
  let client: ApiClient;

  beforeEach(() => {
    const instance = axios.create();
    mock = new MockAdapter(instance);
    client = new ApiClient(instance);
    jest.mocked(toast.error).mockClear();
  });

  afterEach(() => {
    mock.restore();
  });

  it('TC-01: 429 でレート制限トーストを表示する', async () => {
    mock.onGet('/api/subjects/').reply(429);
    await expect(client.get('/api/subjects/')).rejects.toMatchObject({
      response: { status: 429 },
    });
    expect(toast.error).toHaveBeenCalledTimes(1);
    expect(toast.error).toHaveBeenCalledWith(
      'リクエストが多すぎます。しばらく待ってから再試行してください'
    );
  });

  it('TC-02: 既存の 500 トーストが退行しない', async () => {
    mock.onGet('/api/subjects/').reply(500);
    await expect(client.get('/api/subjects/')).rejects.toMatchObject({
      response: { status: 500 },
    });
    expect(toast.error).toHaveBeenCalledTimes(1);
    expect(toast.error).toHaveBeenCalledWith('サーバーエラーが発生しました');
  });

  it('TC-03: /auth/ URL のエラーではトーストを表示しない', async () => {
    mock.onPost('/api/auth/login/').reply(500);
    await expect(client.post('/api/auth/login/')).rejects.toMatchObject({
      response: { status: 500 },
    });
    expect(toast.error).not.toHaveBeenCalled();
  });
});
```
（TC-03 が 500 を使うのは、401 だとトークンリフレッシュ分岐に入り検証対象（`handleApiError` の `/auth/` スキップ）へ到達しないため。テストごとに新品のインスタンス＋クライアントを生成するため、シングルトンの状態（`refreshingToken` 等）や読み込み順序に依存しない）

## 5. 実装手順（ステップ）

未知リスク先行原則: 本計画で唯一の不確実要素「axios-mock-adapter が注入インスタンスのインターセプタ連鎖と正しく協調するか」をステップ1〜2で最初に検証する（ライブラリ導入前の in-session スパイクは package.json 変更＝承認前コード変更になるため実施せず、実装ステップ1に前倒し配置。ステップ2の結果を後続を止めるゲートとする）。

- **ステップ1: 依存導入（未知リスクの検証準備）**
  1. `npm --prefix frontend install --save-dev axios-mock-adapter`（package.json + lock 更新）。
  2. TC-06（npm audit ベースライン非増加）を実行 → NG ならこの時点で中断・依存選定を再検討。
- **ステップ2: api.ts の最小 DI 変更＋テスト書き換え（ゲート）**（ステップ1完了が前提）
  1. 変更点2（api.ts）→ 変更点3（api.test.ts 全文置き換え）を適用。
  2. `npm --prefix frontend test -- --watchAll=false --testPathPattern=api.test` で新 3 TC の GREEN を確認 → TC-01〜03 参照。**ここで NG（モックアダプタとインターセプタの協調不成立）なら実装を止め、計画をやり直す**。
- **ステップ3: false-green 注入検証**（ステップ2完了が前提）→ 手順詳細は auto_test「false-green 自己検証」参照（429 分岐破壊→TC-01 RED・`/auth/` スキップ削除→TC-03 RED・復元は Edit で実施）。
- **ステップ4: 全体検証**（ステップ3完了が前提）→ TC-04（不在 grep 2 本）・TC-05（FE 全体回帰）・TC-07（プロダクションバンドル不変）を実行し全合格を確認。

サービス再起動: 不要（テストと dev 依存のみ。実行中の dev サーバーへの影響なし）。

## 6. テスト計画

### 自動テスト（詳細: `docs/tests/open/I132_auto_test.md`）
- テストレベル: **FE 結合テスト**（axios 実リクエスト発行〜インターセプタ連鎖〜`handleApiError`〜toast 呼び出しの配線を検証。現行のユニット（ハンドラ直接呼び出し）から検証の忠実度を引き上げる）＋**決定論 TC**（grep 不在チェック・audit 閾値・バンドル不変）。
- TDD の適用: 本イシューは「挙動を変えないテストリファクタ」のため RED→GREEN の新規振る舞い駆動ではなく、**書き換え後 GREEN＋失敗注入で RED** を確認する方式（false-green 検証がその代替ゲート）。
- 再発防止: TC-04（内部構造参照の不在 grep）が「暫定方式への逆戻り」を機械検知する。

### 手動テスト（詳細: `docs/tests/open/I132_manual_test.md`）
- 全項目 Claude 実施可能（git diff の範囲確認・PR CI 確認）。**Human 項目なし**（UI 変更ゼロのため目視確認は不要）。

## 7. ロールバック
- 変更点2・3 を元に戻し（api.ts の `export`/コンストラクタ引数を除去・api.test.ts を旧内容へ復元）、`npm --prefix frontend uninstall axios-mock-adapter` で依存を除去すれば完全に従来状態へ戻る。DB 変更なし・マイグレーション不要・サービス再起動不要。

## 8. Risk & 回避策
- **リスク1（最大の未知）: axios-mock-adapter が注入インスタンスのインターセプタ連鎖と協調しない** → 回避: ステップ2をゲート化（NG なら中断して計画見直し）。原理上はモックアダプタは axios の adapter 層（インターセプタより内側）を差し替えるため連鎖は通る設計（ライブラリの標準ユースケース）。
- **リスク2: DI 変更が本番挙動を変える** → 回避: 変更は「`export` 追加＋引数省略時に現行と同一の内部生成」の 2 点のみで、引数なし経路のコードは字面ごと現行と一致させる（変更点2コード例）。TC-05（全体回帰）＋TC-07（バンドルに axios-mock-adapter が混入しない・build 成功）で機械確認。
- **リスク3: dev 依存追加で npm audit が悪化し CI（`--audit-level=critical`）に抵触** → 回避: TC-06 で「total ≤ 18 かつ critical = 0」をステップ1直後に判定（悪化即検知）。axios-mock-adapter 2.1.0 の依存 2 件に既知脆弱性なし（調査結果）。
- **リスク4: `ApiClient` クラス export により本体シングルトンを迂回した多重インスタンス生成が本番コードに広がる** → 回避: 本番コードからの利用は従来どおり `apiClient`（default export）のみ・クラス export はテスト用途である旨を api.ts の変更部コメントには**書かない**（コード規約: 来歴コメント禁止）代わりに、逆戻り検知として通常コードでの `new ApiClient` 使用有無をレビュー観点に記載（I132_review.md 観点2）。

## セキュリティ・ベストプラクティスチェック
- **セキュリティ影響なし**: 本番コードの挙動変更ゼロ（DI の省略時経路は現行同一）。認証・認可・入力処理・機密データの扱いに変更なし。追加依存は devDependencies のみでプロダクションバンドル不変（TC-07 で機械確認）。
- **依存ライブラリ**: axios-mock-adapter 2.1.0 — 既知脆弱性なし・TC-06 で audit ベースライン非増加を機械判定（bandit/pip-audit は対象外＝BE 変更なし）。
- **OWASP**: 該当なし（テストと型の変更のみ）。

## 高リスク判定
- **自己評価: No**。認証・認可・ロール・個人情報・テナントデータ・公開 API の変更なし。プロダクション挙動不変のテストリファクタ＋dev 依存追加のみ。最終判定は `/plan-issue-review I132` に委ねる。

## 各種チェック結果
- **P3（データ整合性/DB）影響なし**: DB 変更なし。
- **P5（運用設計）影響なし**: 外部 API・非同期処理・バッチの変更なし。
- **P6（性能・UX）影響なし**: UI 変更なし・ローディング/空状態/エラー表示の変更なし（トースト文言・分岐は不変更でテスト方式のみ変更）。
- **P8（コスト）影響なし**: 新規インフラ・外部サービスなし（dev 依存 1 件のみ）。
- **P9（プライバシー）影響なし**: 個人情報・未成年データ・テナントデータの取扱い変更なし。

## 設計判断の明示
| 設計判断 | 出所 |
|---------|------|
| api.ts への最小 DI 変更（`export class` + `constructor(instance?: AxiosInstance)`・省略時は現行同等） | イシュー明記（grill 確定・2026-07-19 ユーザー承認） |
| ライブラリ = axios-mock-adapter 2.1.0（msw 不採用理由含む） | イシュー明記（grill 確定・互換実測済み） |
| テスト範囲 = TC-01/02 維持＋TC-03（/auth/ スキップ）追加・401 リフレッシュ分岐は別イシュー候補 | イシュー明記（grill 確定） |
| npm audit AC = ベースライン 18 件から増えない | イシュー明記（grill 確定・実測基準） |
| TC-06 の判定式を「total ≤ 18 かつ critical = 0」の exit code 判定に機械化（--json + node） | **仮定で決めた**（AC の機械判定手段。critical=0 は CI の `--audit-level=critical` ゲートとの整合のため追加） |
| TC-07（プロダクションバンドル不変）を build 成功＋成果物への axios-mock-adapter 不在 grep で機械検証 | **仮定で決めた**（影響範囲の主張「バンドル不変」を散文で終わらせないための決定論ゲート追加） |
| TC-03 は 401 でなく 500 を使う（401 はリフレッシュ分岐に入り検証対象に到達しないため） | **仮定で決めた**（コード読解による技術的必然・調査結果参照） |
| ライブラリ導入前スパイクは行わず実装ステップ1〜2 に前倒し配置（ステップ2をゲート化） | **仮定で決めた**（導入自体が package.json 変更＝承認前コード変更になるため。plan-writing-rules のスパイク二分岐 (2) 相当の運用） |

→ 「仮定で決めた」4 項目は下の承認ポイントで確認する。

## 9. 承認ポイント（チェックリスト）
- [ ] api.ts の DI 変更はコード例の 2 箇所のみ（`export` 追加＋コンストラクタ注入・引数なし経路は現行と字面一致）— でよいか
- [ ] テストは全文置き換え（TC-01/02 維持＋TC-03 追加・モック装着インスタンス注入方式・コード例どおり）— でよいか
- [ ] TC-06 の audit 判定式「total ≤ 18 かつ critical = 0」（exit code 化）— でよいか
- [ ] TC-07（build 成功＋バンドルへの axios-mock-adapter 不在 grep）の追加 — でよいか
- [ ] TC-03 の `/auth/` ケースは 500 を使用（401 は検証対象へ到達しないため）— でよいか
- [ ] ライブラリ導入前スパイクなし・ステップ2 をゲートとする実装手順 — でよいか
- [ ] 手動テストは全項目 Claude 実施（Human 項目なし・UI 変更ゼロ）— でよいか
- [ ] 高リスク判定の自己評価 No（最終判定は plan-issue-review）— でよいか

## レビュー結果
- [20260719_1430 判定: ✅ 完了](../../reviews/I132_plan_review_20260719_1430.md)
