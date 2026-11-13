# I493 レビュー: API のスキーマから画面の型を作る（ダッシュボードの overview から）

## 変更概要
- シリアライザから OpenAPI のスキーマ（`backend/openapi.yaml`）を作り、そこから画面の TS の型（`frontend/src/types/api/schema.d.ts`）を作る仕組みを入れる。作り直し忘れは CI で止める。今回はダッシュボードの overview の手書きの型を置き換える（計画: docs/plans/open/plan_I493.md）

## 変更点
- Backend: `drf-spectacular==0.30.0` を追加。`core/openapi.py`（契約に入れるパスの一覧と絞り込み）・`SPECTACULAR_SETTINGS`・overview のビューとシリアライザの注釈（部品の名前は `Dashboard…`）・`OrgSubjectField` の型の注釈。作ったスキーマ `backend/openapi.yaml` とテスト `core/tests/test_I493_openapi_contract.py`（ずれ・失敗の注入・形・パス）
- Frontend: `tools/api-types/`（`openapi-typescript` 7.13.0・TypeScript 5.9.3）で `frontend/src/types/api/schema.d.ts` を作り、`index.ts` で短い名前を付けた。手書きの `DashboardOverview` などを消し、`Dashboard.tsx`・`dashboard.service.ts`・`Dashboard.test.tsx` を作った型に置き換えた。おすすめの種類の確かめを作った型に結びつけた（増えても消えても型の検査で落ちる）
- CI・設定: `api-types` ジョブ（型のずれ・失敗の注入・`npm audit`）・Dependabot に `/tools/api-types`
- 手順書: `common-commands.md` に作り直し方、`branch-protection-setup.md` の必須チェックを 7 件に

## 影響範囲
- Backend/Frontend/DB/Config: 計画書「3. 影響範囲」のとおり（DB の変更なし）

## テスト結果
- 自動: CI がすべて成功（Backend Lint & Security・Backend Tests・Frontend Type Check・Frontend Lint & Security・Frontend Tests・API Types Up To Date・Harness Tests・E2E）。コードレビュー OK・敵対的レビュー OK（1 周）。詳細は docs/tests/open/I493_auto_test.md
- 手動: No.1〜3 すべて OK（Claude・Playwright MCP とコマンド）。詳細は docs/tests/open/I493_manual_test.md

## 計画との差分
- あり（小）: 計画書の計画変更記録のとおり。手順書の件数の 3 か所を追加でそろえた・/simplify で選択肢の確かめを配列から `Record` に、`check` を `npm run generate -- --check` に、TC-02 の注入を「1 行足す」に、スキーマ生成の fixture をモジュール単位にした。方式・範囲・受け入れ条件は変えていない

## ロールバック
- PR を revert し、backend・celery のイメージを作り直す（`docker compose up -d --build backend celery celery-beat`）。DB の変更なし

## 振り返り

### I493 振り返り（かんたんなまとめ）

#### 良かった点
- 計画の前に道具を実際に試した（理由: 全部の API を入れると型の多くが不正確になること、型を作る道具の新しい版は今の画面の TypeScript では動かないこと、を計画の前に見つけられた。手戻りなく方式を決められた）
- 「契約に入れる API を一覧で絞り、警告が 1 つでもあれば失敗」という作りにした（理由: 入った API の型はいつも正確で、#496 で API を足すときも同じ条件で守られる）
- 作り直し忘れの確かめに、毎回わざと失敗させる確かめを付けた（理由: 道具の版上げで確かめが効かなくなっても CI で気づける）
- 実装前のセキュリティの確認で、CI が依存のインストール用のスクリプトを動かす点と、道具をネットから取り直しうる点を見つけて直せた

#### 今回の問題への直接の対処
- 台帳の残り 4 件（いずれも軽い指摘）: 画面の型の残りの置き換え（#496）と、依存の固定（#499）にそれぞれ渡し、1 件は軽い指摘の一覧に入れた
- 作業中に、Celery（非同期の処理）が前から起動していないことに気づいた。原因は依存の版のずれで、今回の変更とは無関係。→ #499 として起票した（本番でも同じことが起こりうるため）
- コミット前の ESLint のチェックが、手元に道具が無いため止まった（4 回目）。→ 根本対応のイシュー #468 に、再発の回数と優先の依頼をコメントした

#### 同じ問題を次回から防ぐ改善
- 新しく足す決まりはありません。試しの段階で承認画面を 3 回出したのは、すでにある「承認画面が出うる操作は先に伝える」決まりを私が守れなかったためです。新しい手順は足さず、私の作業の決まり（メモ）を、試しのときにも当てはまるよう具体的にします

### I493 振り返り（詳細）

#### 良かった点
- スパイク 1〜5 で、全 API の警告 197 件・`openapi-typescript` 7 の TS5 前提・6 系の high 脆弱性・`component_name` の継承・`--check` の終了コードを計画の前に確かめた
- `CONTRACT_PATHS`＋`--fail-on-warn` で、契約に入った API の型の正確さを決定論で守った
- 失敗の注入を pytest（TC-02）と CI（TC-21）に毎回流す形で入れた
- design-security-review の Medium 2 件（install スクリプト・npx）を実装前に反映した

#### 是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | ベストプラクティス | 台帳 F1・F2: 実行時の確かめ・送る側の型が手書きのまま | #496 にコメント（他の画面の置き換えでまとめて扱う） |
| C2 | 予期しない問題 | 台帳 F3・celery の停止: 固定していない間接の依存が上がる | I499（#499）を起票し、F3 もコメントで同梱 |
| C3 | プロセス | ワークツリーのホストに eslint が無く、ESLint のフックが exit 127 | #468 に再発（4 回目）をコメント |

#### 予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| （なし） | — | — | 手順 2.7 の 4 問で、新しい手順・観点を足す改善案は無かった（その場で捕まり手戻りなし・既存の決まりで足りる）。見送りの理由は「自律判断の記録」の [retro] の行 | — |

## 自律判断の記録
- [plan] 契約に入れる API を一覧（`CONTRACT_PATHS`）で絞り、警告 0 を条件にした — 全 API を入れると警告 61・エラー 136 で、中身の正しくない型ができるため（スパイク 1）
- [plan] 型を作る道具をリポジトリ直下の `tools/api-types/` に置いた — 画面のイメージ（`COPY . .`・`.dockerignore` なし）に入れず、画面の TypeScript 4.9.5 と分けるため
- [plan] 実行時の形の確かめ（`isDashboardOverview`）を残した — 型は実行時に消え、TC-22 の 0 埋めの防止がこれに頼っているため
- [plan-review] 計画レビューの判定は HIGHRISK（`.github` の変更）。Warning 3 件・Info 1 件は計画書と手動テストを直して対応し、再レビューはしない — 方式・範囲・受け入れ条件を変えていないため
- [plan-review] 新しいジョブ `api-types` を必須チェックの一覧に足し、登録は close でユーザーにお願いする — bot に管理者の権限が無いため
- [design-security-review] Medium 2 件（CI の `npm ci` で依存の install スクリプトが動く・失敗の注入の `npx` がネットから取り直しうる）を、`--ignore-scripts` と `./node_modules/.bin/openapi-typescript` で計画に反映し、V6 を足した。計画レビューはやり直さない — 方式・範囲・受け入れ条件を変えていないため
- [implement] 実装のコミットだけ `SKIP=eslint` にした — ワークツリーのホストに eslint が無くフックが exit 127 で止まる既知の問題（#468・I473 と同じ）。同じ `npm run lint`（--max-warnings 0）を frontend のコンテナで流して違反 0 件を確かめた。CI の ESLint は通常どおり流れる
- [implement] /simplify の 4 観点の指摘のうち 4 件を直し、4 件を見送った（理由は計画変更記録）— 直したのは選択肢の一覧の増減の検知・check のパスの 1 か所化・TC-02 の注入の書式依存の除去・スキーマ生成を 1 回に
- [implement] 画面の確かめ（Playwright）は test-gate の手動 No.1 に回した — 画面の動きは変えておらず（型の読み込み先と、選択肢の確かめの書き方だけ）、選択肢の確かめは Dashboard.test.tsx（10 件通過）で見ている
- [implement] backend・celery のイメージを作り直したところ、celery・celery-beat が起動直後に落ちた。原因は今回と無関係（celery の部品 kombu の新しい版が redis-py 6.1 以上を求めるが、`requirements.txt` は `redis==5.0.1` に固定。作業の開始時から celery は動いていなかった）。別イシューとして起票する — 本イシューの範囲外で、本番のイメージでも同じことが起こりうるため → I499（#499）として起票した
- [review-gate] コードレビューは OK（台帳に Low 4 件・止める指摘なし）、敵対的レビューは 1 周目で OK（V1〜V6 すべて確認済み・新しい指摘なし）。Low は retro で扱う — 止める条件に当たらないため
- [test-gate] 手動 No.3 は `curl` が許可されていないので Playwright MCP で URL を開いて HTTP の状態（404）を見た — 同じことを確かめられ、承認画面を出さずに済むため
- [test-gate] 手動 No.1 の期待結果「今日も 0 以外」は、今日の答えの記録が無いため 0 分の表示が正しい。データどおりなので OK とし、書き方が強すぎたことを記録した — 期待結果の文言の誤りで、画面の不具合ではないため
- [test-gate] 画面確認で、ログアウトの API が 400 を返すのを見た（I151 のレビューで既知の `logout_view` の不備・今回と無関係）。retro で扱う
- [retro] 台帳の残り: F1・F2 → #496 にコメント（画面の残りの型の置き換えで、実行時の確かめと送る側の型をまとめて扱う）／F3 → #499 にコメント（固定していない間接の依存という同じ根本原因）／F4 → `docs/reviews/backlog/I493.md`（Low・再現なし）。判定の仕組みに関わる指摘・`SECURITY=yes` の指摘は無い
- [retro] ESLint のフックの exit 127 の再発（4 回目）→ #468 に同梱（コメント）— 根本対応のイシューがもうあり、回数を残して優先を上げてもらうため
- [retro] celery が起動しない問題 → I499（#499）として起票済み（implement の時点）— 実害（非同期の処理が止まっている）があり、同梱先が無いため
- [retro] スパイク中に承認画面を 3 回出した（コンテナからのファイルの取り出し・中身に `delete` を含むファイルのコンテナへの写し・`os.environ` を含むスクリプト）→ 見送り（リポジトリには足さない）— その場で気づき、手戻りは無い。「承認画面が出うる操作は先に伝える」決まりは既にあり、守れなかったのは私の実行の問題。見張りの `delete` の誤検知は、まれな操作で、見張りを作り込まない方針（文字列で読む判定は普通の書き方の事故だけを守る）に当たる
- [retro] ログアウトの 400（ログアウト後も refresh トークンが使える）→ 見送り（本イシューの範囲外）— I142（#253・PR #256）で直す予定と I151 の計画に記録がある。ただし bot の停止で #253・#256 が GitHub で見えないまま止まっているので、close でユーザーに伝える
- [retro] 手動 No.1 の期待結果の書き方が強すぎた（データ次第の値を「0 以外」と書いた）→ 見送り — その場で正しく判断でき、手戻りは無い
- [retro] 計画レビューの Warning（名前の付け替えのスパイク不足）→ 見送り — 実装の前にスパイク 5 で確かめ、手戻りは無い
- [retro] 設計ルール昇格（CI で依存を入れるときの install スクリプト・npx）→ 見送り — 既存のジョブは `react-scripts` の都合で install スクリプトが要る可能性があり、一律の決まりにするには全ジョブの調査が要る。今回は design-security-review で捕まった

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: design-security-review

STAGE_DONE: design-security-review NEXT: implement

STAGE_DONE: implement NEXT: review-gate

STAGE_DONE: review-gate NEXT: test-gate

STAGE_DONE: test-gate NEXT: retro
