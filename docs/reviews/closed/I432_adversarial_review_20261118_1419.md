# 敵対的レビュー [I432]（別プロセス・2026-11-18 14:19）

- 見た範囲: b3c3c1751e2869663df79e22ad949817e5d670d4...5a3089a7221fea5a0322f2834d61720c7746df01
- 所要時間: 16 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- コンテナ: 確かめていない（ブランチに backend/ の変更なし）
- 一覧: docs/plans/open/plan_I432.md の「## 必ず確かめる項目」（4 項目）
- 引き継ぎ: 引き継ぐ項目なし（I432_adversarial_review_20261118_1351.md で実験により確認済みの項目が無い）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V2 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V3 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V4 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 11 秒 | 0 | 0 | $0.1231 | ― | ― | ― |
| 2 | 報告あり | 11 秒 | 0 | 0 | $0.1142 | ― | ― | ― |
| 3 | 報告あり | 12 秒 | 0 | 0 | $0.1194 | ― | ― | ― |

## 実験

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I432] ── 観点: 1. ロジック回避・実機 repro

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| なし | - | 反証失敗（新規指摘なし） | - | 静的読解 |

反証失敗（新規指摘なし）。探索した仮説は次の 2 つ。

1. **e2e.yml の守りの緩み**
   - `permissions: contents: read` は 10〜11 行目にある。
   - `::add-mask::`（25 行目）は `GITHUB_ENV` への書き込み（26 行目）より先にある。
   - action は 3 つとも SHA 固定のままだった。
   - `secrets.` を使う行は無かった。
   - 差分は `node-version: '26'` の 1 行だけ。
2. **docker-compose のイメージ指紋**
   - `docker-compose.yml:197` は `playwright:v1.65.1-jammy@sha256:b0ee5ce5e14ac42c394c0564a0a30adbda052153c611561bb2d31263593d6dd8` で、固定は保たれている。
   - 計画書 64 行目の #376 の値と全文が一字一句一致している。

> ITEM: V1 RESULT=read
> ITEM: V2 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

> ITEM: V1 RESULT=read
> ITEM: V2 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I432] ── 観点: 2. テストの false-green・tautology

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Medium | false-green | 手動 No.1 の期待結果は、導入の段で止まった赤と 0 件の緑を不合格にしている。また `N` が 19 以上で `failed` が無く `passed` があることを求めている。しかし `skipped`・`did not run`・`interrupted` が 0 件であることは求めていない。そのため、18 件がスキップされて 1 件だけ通った場合でも、`Running 19 tests`・`1 passed`・`failed` 無しで合格になる。今回の実結果は `19 passed` なので実害は無い。ただし期待結果の書き方としては、`passed`＋`flaky` が N と一致する（`skipped` が 0）ことまで求めないと、ユーザーの指示（スキップで緑を合格にしない）を表現しきれていない。既知 findings の観点 2 の指摘と実質同一なので、新規には数えない。 | docs/tests/open/I432_manual_test.md 手動 No.1 の期待結果／plan_I432.md V3 | 静的読解。今回の実結果（run 44239178761・`Running 19 tests` → `19 passed`）は skipped が無い。 |
| Low | tautology | TC-03 は「conclusion が SUCCESS」だけを見る。ジョブ全体の SUCCESS は、E2E のテスト段が 0 件でも成立しうる。ただし手動 No.1 が補っている。 | docs/tests/open/I432_auto_test.md TC-03 | 静的読解 |

V3 の主旨は満たしている。AC2・AC5 の確かめは、CI の実ログの `Running 19 tests`・`19 passed` に基づいている。導入の段の赤は不合格で、TC-28 以外の flaky も NG にしている。実結果の記録も `Running 19 tests using 2 workers` → `19 passed (36.5s)`・flaky なし・failed なしで、スキップで緑にはなっていない。

今回の差分は記録の場所のみで、`e2e/tests/` やテストコードの変更は無い。新規の Critical/High は無い。

> ITEM: V3 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I432] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
反証失敗（新規指摘なし）。探索した仮説は次の 3 つ。

- **Node.js 26 の影響が E2E 以外へ広がる経路**
  - `node-version` の 26 は `e2e.yml:43` だけです。
  - `ci.yml` の 4 か所（101・118・138・157 行）と `dependency-audit.yml:67` は `'18'` のままです。
  - 画面のビルド・テスト・依存の監査は Node.js 18 のままで、影響を受けません。
- **規約 §16 の文言と計画 §9 の読み方の食い違い**
  - `rules/react-coding-standards-integrated.md:207` の #551 の行に、「E2E のジョブ〔`e2e/`・画面と別に動く〕は先に 26 にした」という例外が入っています。
  - 画面の Node.js 18 は #551 の対象として残っています。
  - 計画 §9 の「E2E のジョブは対象外」と同じ内容です。
- **依存の監査が E2E の依存に Node.js 18 で当たる経路**
  - `dependency-audit.yml` の grep では `node-version` の行が 1 つだけでした。この確認は E2E の依存を扱うかまでは見ていません。
  - E2E の `npm audit` は TC-04 が実行して 0 件を確認しています。
  - 新たな Critical/High にあたる事象は見つかりませんでした。

実験案はありません。

> ITEM: V4 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: 5a3089a7221fea5a0322f2834d61720c7746df01
ROUNDS: 1
VERDICT: OK
