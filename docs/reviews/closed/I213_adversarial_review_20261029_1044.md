# 敵対的レビュー [I213]（別プロセス・2026-10-29 10:44）

- 見た範囲: d4dc801d038f5c8855511b7a67d1aca3fdf113b9...ebaf797077172ce192466b60ce30275185cce84d
- 所要時間: 23 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- 一覧: docs/plans/open/plan_I213.md の「## 必ず確かめる項目」（6 項目）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V2 | 1 | 実験必須 | 読んで確認 | ― | 未検証（実験必須を読んで確認しただけ） |
| V3 | 1 | 実験必須 | 読んで確認 | ― | 未検証（実験必須を読んで確認しただけ） |
| V4 | 2 | 実験必須 | 実験で確認 | P2-E1=なし  | 未検証（実験が実行されていない・無効） |
| V5 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V6 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 18 秒 | 0 | 0 | $0.1556 | ― | ― | ― |
| 2 | 報告あり | 14 秒 | 0 | 0 | $0.1330 | ― | ― | ― |
| 3 | 報告あり | 13 秒 | 0 | 0 | $0.1451 | ― | ― | ― |

## 実験

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I213] ── 観点: 1. ロジック回避・実機 repro

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | V3 | `ci.yml` の `services:` にある postgres・redis は指紋なしで、I1 の検査範囲外にある。runbook で例外と明記済み(計画変更記録 6)で、既知 findings(F9・F11)と実質同一。Dependabot が更新しない理由で固定しないと決めており、新規の High ではない。 | .github/workflows/ci.yml:46,62 | 静的読解 |
| Low | V2 | W1 の正規表現は `uses: ./local` や `docker://` を許さない。ローカル action を足すと誤検知で止まるが、方向は安全側。 | test_i213_dependabot.sh:42-43 | 静的読解 |
| Low | V1 | W2 は `secrets.` の部分一致だけを見る。`secrets['X']` や `secrets: inherit` は検出できない。既知 F4 と実質同一。 | test_i213_dependabot.sh:54 | 静的読解 |

読んで確かめたこと(この周には実験の結果が無い。前周の P1-E1 は `pass=1 fail=0`):
- V2: W1 の `OK` は `@[0-9a-f]{40}` と `#\s+v\d+...` を `fullmatch` で要求する。`@v4`・`@v10.3.3`・`@main` はどれも `OK` に一致せず、`uses:` 行は `USES` に一致するので不合格になる。FG-W1a・FG-W1b・FG-W1c はそれぞれ `@v4`、`@v10.3.3`、版コメントの欠落を注入する。FG-W1ok は、版コメントの後ろに説明が付く正しい書き方が合格することを確かめる。
- V3: I1 は 3 つの Dockerfile の `FROM` と compose の `image:` で `@sha256:<64 桁>` を要求する。`FROM` の `as` で付けた段の名前は例外として許す。FG-I1a・FG-I1b は指紋を外して不合格を確かめる。
- V1: e2e.yml では、`E2E_TEST_PASSWORD=` と `GITHUB_ENV` を含む step がちょうど 1 つで、その前に `::add-mask::` があることを W3 が見る。pull_request で動くワークフローに `secrets.` が無いことは W2 が見る。FG-W2・FG-W3a・FG-W3b がそれぞれを壊して不合格になる。
- FG の弱さ(例外による exit 1 を区別できない、F5)は既知。

反証失敗(High 以上の新規指摘なし)。探索した仮説: 正規表現を通す `@main` 系、`FROM` の段の名前を使った指紋逃れ、`on:` の解釈、secrets の別表記。

> ITEM: V1 RESULT=read
> ITEM: V2 RESULT=read
> ITEM: V3 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I213] ── 観点: 2. テストの false-green・tautology

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| — | — | 反証失敗（新規指摘なし） | — | — |

反証失敗（新規指摘なし）。探索した仮説:
- **V4（V1 判定）が常に OK になる可能性。**
  - `test_i213_dependabot.sh:126` の FG は、`postgres_data` の次の行に名前の無い保存領域 `/var/lib/postgresql/extra` を足した写しを作る。
  - この写しに対して V1 が不合格（exit 1）になることを `fg` で要求している。
  - 不合格にならなければ `ck` が FAIL を出す。
  - 前回の敵対的レビューの P2-E1 は `pass=1 fail=0` で、実物は合格し、FG も期待どおり不合格になった。
  - 実物の `docker-compose.yml` では、DB・redis は名前付き（`postgres_data`・`redis_data`）。名前の無い保存領域は frontend の `/app/node_modules` だけ。
  - よって `--renew-anon-volumes` で消えるのは node_modules だけで、DB・redis の中身は残る。
  - 前回結果の再利用なので、今回新しく実験は取っていない。
- **実装の写しになっていないか。** V1 は「消えてよい名前の無い保存領域は frontend の node_modules だけ」という不変条件を見ている。保存領域の名前の写しではない。
- **V5（D2）の実物。**
  - D2 は `updates` の各要素に `target-branch` があるかを見る。
  - FG（行 114）は先頭の `schedule:` の前に `target-branch` を注入し、不合格になることを要求している。
  - 前回の読解では、`dependabot.yml` に `target-branch` は無く、8 対象すべてに `applies-to: security-updates` の group がある。
- **既知の弱点は再報告しない。** FG が検出による exit 1 と例外による exit 1 を区別できない点は、F5 として既知。

> ITEM: V4 RESULT=experiment EXP=P2-E1
> ITEM: V5 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I213] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | V6 | runbook の「セキュリティの修正（major でも）」と「major（セキュリティの修正以外）」の区別は、イシュー Q3 の決定と食い違っていない。ただし、PR が security update かどうかを見分ける方法が書かれていない。例えば PR の種類を示すラベルなのか、タイトルなのかが分からない。運用上の曖昧さが残るが、受け入れ条件を満たさないほどではない。 | docs/runbooks/dependency-audit.md:62-66 | 静的読解 |

反証失敗（新規の High 以上の指摘なし）。探索した仮説は次のとおり。

- **uv を見張らない理由が runbook にあるか**
  - あった。`dependency-audit.md:52` に、Dependabot の uv と `required-version` がぶつかること、版は onboarding.md の手順で手で上げることが書かれている。
  - これはイシュー 31 行目の決定と一致する。
- **PR の通し方がイシューの決定と食い違わないか**
  - 食い違いはない。イシュー 59 行目の内容と runbook の表は同じ。
  - 自動マージを使わないこと、CI が赤い PR と major の PR はイシューを立てることも一致している。
- **target-branch と宛先の注意**
  - 書いてある。イシューと食い違わない。
- **取り込んだあと手元でやることの抜け**
  - 見つからなかった。

> ITEM: V6 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 3
REVIEWED_COMMIT: ebaf797077172ce192466b60ce30275185cce84d
ROUNDS: 1
VERDICT: HIGH
