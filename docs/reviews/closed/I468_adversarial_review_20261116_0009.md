# 敵対的レビュー [I468]（別プロセス・2026-11-16 00:09）

- 見た範囲: 40cdf01b1864d420603a5454b2591d2bcbd07728...e70e90894c6f923df811a81407b597b372c77bc7
- 所要時間: 21 秒（上限 600）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 0 件は下の表）
- コンテナ: 確かめていない（ブランチに backend/ の変更なし）
- 一覧: docs/plans/open/plan_I468.md の「## 必ず確かめる項目」（4 項目）
- 引き継ぎ: 引き継がない（I468_adversarial_review_20261115_1122.md の REVIEWED_COMMIT 40cdf01b1864d420603a5454b2591d2bcbd07728 から HEAD までに記録の場所の外が変わった: .claude/skills/implement/SKILL.md .claude/skills/test-gate/SKILL.md backend/dashboard/management/__init__.py backend/dashboard/management/commands/__init__.py backend/dashboard/management/commands/seed_dashboard_verify.py backend/dashboard/tests/test_I513_seed_dashboard_verify.py backend/dashboard/verify_data.py docs/runbooks/frontend-verify.md frontend/src/components/dashboard/DashboardCharts.tsx frontend/src/components/dashboard/DashboardStatCards.tsx frontend/src/components/dashboard/StartQuizCard.tsx frontend/src/components/dashboard/weeklySummary.ts frontend/src/pages/Dashboard.tsx frontend/src/pages/__tests__/Dashboard.test.tsx frontend/src/types/dashboard.ts）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |
|---|---|---|---|---|---|
| V1 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V2 | 2 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V3 | 1 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |
| V4 | 3 | 読んで可 | 読んで確認 | ― | 確認済み（読んで） |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 費用 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |
|---|---|---|---|---|---|---|---|---|
| 1 | 報告あり | 19 秒 | 0 | 0 | $0.3005 | ― | ― | ― |
| 2 | 報告あり | 19 秒 | 0 | 0 | $0.2908 | ― | ― | ― |
| 3 | 報告あり | 11 秒 | 0 | 0 | $0.2454 | ― | ― | ― |

## 実験

## 各観点の報告（本文。機械が読む行は無害化した）

### 観点 1: ロジック回避・実機 repro（ガード・判定・分岐の抜け道を実験で確かめる）

# 敵対的レビュー [I468] ── 観点: 1. ロジック回避・実機 repro

## findings
反証失敗（新規指摘なし）。探索した仮説:
- **`docker version` は成功するが `docker compose ps` が失敗する場合**（compose プラグインが無いときなど）。
  - `running` が空になり、`run --build` に進む。
  - この `run` も失敗して非 0 で終わるので、止まる側に倒れる。黙って通る経路は無い。
- **ホストに eslint があり、Docker のデーモンだけ止まっている場合。** ホストの eslint で流し、`exec npm run lint` で終了コードをそのまま返す。FG-03 で壊した写しが不合格になる。
- **TC-04 の2経路（Docker 停止・docker コマンド無し）。**
  - どちらも lint を呼ばず、`ESLint を流せません` を出し、exit 1 になる。
  - 最後の `exit 1` を `exit 0` にした写し（FG-04）は、`RC -eq 1` の判定で不合格になる。
  - `NODOCKER` の PATH には bash・git・grep・env しか入れていない。そのため偽の docker が混ざる穴は無い。
- **TC-05 でフックの設定とラッパーがつながっているか。**
  - `.pre-commit-config.yaml` の eslint フックは `entry: bash scripts/claude/lint-frontend.sh`、`pass_filenames: false`、`files: ^frontend/src/` で、テストが本物の設定を読み取って使う。
  - `entry` を `true` にした設定（FG-05）では、lint の失敗でもコミットが進む。`RC -ne 0` と `MOVED=no` の両方を求めているので不合格になる。
  - pre-commit か python の yaml が無い場合は `ng` で大きく落ちる。静かに素通りすることは無い。
- 既知 findings の F8（FG-05 は `calls` の比較だけで落ちる）は、再報告しない。

静的読解だけで、実験案は出していない。判定は、止める側に倒れる設計とテストの対の確認に基づく。

> ITEM: V1 RESULT=read
> ITEM: V3 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 2: テストの false-green・tautology（失敗条件で本当に落ちるか・実装の再確認になっていないか）

# 敵対的レビュー [I468] ── 観点: 2. テストの false-green・tautology

## findings
反証失敗（新規指摘なし）。探索した仮説:
- **TC-01〜TC-03 が終了コードを確かめているか**
  - `expect_lint`（`scripts/claude/tests/test_i468_lint_frontend.sh` 83〜92 行）は、偽の lint の終了コードを 0 と 1 の両方で当てています。
  - 判定は「ラッパーの終了コードが同じ」かつ「lint の呼び出しがちょうど 1 回で、期待した引数と作業フォルダ」です。
  - そのため、終了コードを定数にする写しは、0 か 1 のどちらかで必ず落ちます。
  - 呼び出しの完全一致も見ているので、lint を呼ばない写しも落ちます。
- **FG-01・FG-02b・FG-03（`|| true; exit 0` に差し替えた写し）**
  - 偽の lint が 1 のとき、ラッパーは 0 で終わります。TC の `RC -eq rc` が崩れるので、`check_wrapper` は 1 を返します。
  - `fg` は「不合格になるはず」を期待しています。落ちなければ false-green と報告する作りです。
- **FG-02a（部分一致の `grep -q frontend`）**
  - TC-02 の ps に `frontend-old` を含めています。
  - 部分一致の写しは `exec` 側に入ります。呼び出しが `RUN_LINE` と一致せず、落ちます。
- **偽物がテストを素通りさせる経路**
  - 偽の docker は `version` と `compose ps` を処理し、それ以外は `STUB_RC` で終わります。
  - 環境変数の付け方は `STUB_DAEMON_RC=1 expect_lint ...` で、子プロセスに渡ります。
  - `lint_calls` は `exec|run|npm` の行だけを拾うので、`version` や `ps` の呼び出しを lint と取り違えません。
  - 作業フォルダは `pwd -P` で、`root` と同じ形に正規化して比べています。
- **`fg` の置き換え前の文字列が本体に無いとき**
  - `fg` は「写しを作れない」として `ng` を返すので、本体を書き換えても黙って通りません。

実験は不要と判断しました。静的読解で、いずれの写しにも false-green の穴は見つかりませんでした。

> ITEM: V2 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

### 観点 3: 要件・脅威モデルの網羅漏れ（受け入れ条件の抜け・想定攻撃・エッジケース）

# 敵対的レビュー [I468] ── 観点: 要件・脅威モデルの網羅漏れ

## findings
反証失敗（新規指摘なし）。

探索した仮説:
- V4: 差分の変更ファイル一覧に `.github/` 配下のファイルが 1 つも無い。そのため、CI の ESLint の段と pre-commit の段の `SKIP: eslint` は変わっていない。
- 変更されたワークフロー設定ファイル（`.github/workflows/*`）は一覧にも差分にも無い。`SKIP: eslint` の扱いに触れる変更が入った形跡は無い。
- 差分の中身は、I513 の取り込み、§11 から §12 への改番、記録ファイルの移動（`closed/` 配下）、`docs/plans/open/plan_I468.md` の追記、ダッシュボードのアプリのコードだけ。CI の設定に影響する変更は無い。

実験は不要と判断した。確かめたのは、差分の一覧に `.github/` が無いことだけだ。実際のファイルは開いていない。

> ITEM: V4 RESULT=read
> NEW_CRITICAL: 0
> NEW_HIGH: 0

NEW_CRITICAL_TOTAL: 0
NEW_HIGH_TOTAL: 0
UNVERIFIED: 0
REVIEWED_COMMIT: e70e90894c6f923df811a81407b597b372c77bc7
ROUNDS: 1
VERDICT: OK
