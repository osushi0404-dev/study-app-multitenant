# 敵対的レビュー [I488]（別プロセス・2026-11-14 03:06）

- 見た範囲: f5ce7c350c6edd2887ac2c9e09f9db7f687c3e14...8a3fd1a695f38ebb40f3cd7ab0781c744d5a885a
- 所要時間: 27 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- コンテナ: backend を起こして確かめた（3 秒・締め切りの外）
- 一覧: docs/plans/open/plan_I488.md の「## 必ず確かめる項目」（5 項目）
- 引き継ぎ: 引き継がない（I488_adversarial_review_20261114_0223.md の REVIEWED_COMMIT f5ce7c350c6edd2887ac2c9e09f9db7f687c3e14 から HEAD までに記録の場所の外が変わった: frontend/src/components/statistics/StatisticsTrendChart.tsx frontend/src/pages/__tests__/Statistics.test.tsx）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V2 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V3 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V4 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V5 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 16 秒 | 0 | 0 | $0.1560 | ― | ― | ― |
| 2 | 報告あり | 24 秒 | 0 | 0 | $0.1751 | ― | ― | ― |
| 3 | 報告あり | 20 秒 | 0 | 0 | $0.1717 | ― | ― | ― |

## 実験

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I488] ── 観点: 1. ロジック回避・実機 repro

## findings
反証失敗（新規指摘なし）。探索した仮説は次の 3 本です。実験は実行していません。すべて読んで確かめました。

1. **他組織・他人の答えが analytics に混ざる経路**
   - 今回の差分は、正答率の `Line` に `isAnimationActive={false}` を付けたフロントの表示の直しと、テストのモックの変更だけです。backend は変えていません。
   - backend 側の `selectors.py` で `QuizAnswer` を読むのは `_answers(user)` だけです。これは `scope_to_user_org` を通ります（`selectors.py:30-32`）。
   - 内訳の `problem__subject__name`（行 125 と 258）も `answers` から派生します。他組織の科目名が出る別経路は見つかりませんでした。
2. **`subject_id` の検証**
   - `views.py:55` は `query.validated_data` から `subject_id` を取ります。
   - `serializers.py:85` では `OrgSubjectField` が検証します。数字でない値・他組織・全体共有・存在しない ID は、すべてフィールドのエラーになります。
   - ビューが返す 400 は、`days` 以外のエラーなら 1 種類です。body が違うことで存在を推測される経路は見つかりませんでした。
   - 前の周（20261114_0223）の観点 1 と同じ結論です。差分は backend に触れていないので、この確認は変わりません。
3. **今回の差分が backend の挙動を変えるか**
   - 変えません。フロントの表示の直しだけです。

> ITEM: V1 RESULT=read
> ITEM: V2 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I488] ── 観点: 2. テストの false-green・tautology

## findings
| 重大度 | 観点 | 指摘内容 | 該当箇所 | 再現証跡 |
|--------|------|---------|---------|---------|
| Low | false-green | TC-22 が欠けたキーとして試すのは `trend`・`totals`・`granularity` の 3 つだけです。`subject_breakdown` を欠く応答や、区切り・科目の各行のキー（例: `accuracy_rate`）を欠く応答は試していません。このため `isDashboardAnalytics` の該当部分を外しても TC-22 は落ちません。既知 findings の周で出た Low と同じ内容で、再報告です。 | `Statistics.test.tsx:173-185` | 静的読解 |
| Low | 追加分のテスト | fix-loop で足した TC-25 の確認は、`isAnimationActive` が `false` で渡ることだけを見ています。点が実際に描かれることは見ていません。この指摘はコードレビューの F6 と同じ内容で、モックの限界として認識済みです。 | `Statistics.test.tsx:252` | 静的読解 |

## V3・V4 の判定（どちらも合格側）
- **V3（TC-12）**:
  - 利用者 2 人（答え 1 件と 120 件）と `days`（7 と 365）の全組み合わせでクエリ数を集めています。
  - 科目指定なしと、科目指定ありの両方を回しています。
  - 比較は `len(set(counts)) == 1` で、片方だけを数える形ではありません。
  - 上限は `<= limit` でも別に確かめています。
  - 毎回キャッシュを消しているので、2 回目以降のキャッシュ命中でクエリ数が減る形にもなりません。
  - 7 日は日ごと、365 日は月ごとの区切りになります。区切りごとにクエリを撃つ実装になれば、数が変わって落ちます。
- **V4（TC-22）**:
  - `trend` を欠く・`totals` を欠く・`granularity` が未知の値、の 3 つの入力を `it.each` で与えています。
  - どれも `findByRole('alert')` に「学習統計を読み込めませんでした」が出ることを要求しています。
  - 0 分・0 問・棒グラフが出ないことも見ています。
  - 形の確かめを外すと `trend.map` などで描画が壊れるか、正常な画面が出ます。どちらでも alert が出なくなり、落ちます。正常な応答だけで通る形ではありません。

反証失敗（V3・V4 は合格側。新規の Critical/High なし）。探索した仮説:
- TC-12 が片方の軸だけを数える形になっていないか。
- TC-22 の入力が実質正常な応答で、形の確かめを外しても通らないか。
- fix-loop の TC-25 のモックが、直しを外しても通る形（tautology）になっていないか。モックは `isAnimationActive` が未指定のとき `data-animation="undefined"` を出すので、直しを外せば落ちます。tautology ではありません。

> ITEM: V3 RESULT=read
> ITEM: V4 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I488] ── 観点: 3. 要件・脅威モデルの網羅漏れ

## findings
反証失敗（新規指摘なし）。探索した仮説:
- 区切りの境目が、テストで直接確かめられているか。
- 日本時間の 0〜9 時の答えが、テストにあるか。
- 300 秒の上限が、テストにあるか。

実験は実行せず、`backend/dashboard/tests/test_I488_analytics.py` を読んで確かめた。

| 確かめた点 | テストの中身 |
|---|---|
| 週の境目 | `test_week_buckets` は日曜（11-08）と月曜（11-09）を入れている。期間の最初の日（08-17）と前日（08-16）も入れている。 |
| 月の境目 | `test_month_buckets` は 10-31 と 11-01 を入れている。期間の最初の日（2025-11-15）と前日（11-14）も入れている。 |
| 日本時間の 0〜9 時 | `test_dates_are_japan_time` は 11-14 0:30（UTC では前日）と 23:30 を別の日として確かめている。`test_expected_values_and_cap` にも 07:00 の答えがある。 |
| 300 秒の上限 | `test_expected_values_and_cap` は 400 秒の答えを 300 に切る期待値を確かめている（合計 360・当日 330）。`test_subject_breakdown_order` も 400 秒を使っている。 |

今回の差分はフロントの表示の直し（正答率の `Line` に `isAnimationActive={false}` を付けた）と、そのテストだけだ。バックエンドの集計は変えていないので、この観点で新しく増えた穴はない。

前の周の Low は、期間の最初の日の 0〜9 時の答えを直接確かめていないこと。これは既知の指摘として再報告しない。

> ITEM: V5 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: 8a3fd1a695f38ebb40f3cd7ab0781c744d5a885a
ROUNDS: 1
VERDICT: OK
