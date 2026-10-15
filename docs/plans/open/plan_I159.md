# plan_I159: frontend 依存の critical 脆弱性（proxy-addr / shell-quote）を npm audit fix で解消し CI を復旧

## 基本情報
- **計画書ID**: plan_I159
- **関連イシュー**: #276（docs/issues/open/I159.md）
- **Draft PR**: #277
- **作成根拠資料**: docs/issues/open/I159.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I159_review.md
- **作成日**: 2026-10-15

## 1. 背景/目的

### 原因の概要
リポジトリのコードは何も変えていないのに、frontend が間接的に使っている 2 つのパッケージ（proxy-addr / shell-quote）に critical の脆弱性が新しく公開された。CI の監査チェックが critical を 1 件でも見つけると失敗する設定のため、**すべての PR の CI が赤になっている**。

### 詳細な原因分析
- CI「Frontend Lint & Security」ジョブ（`.github/workflows/ci.yml:123-125`）の `npm audit --audit-level=critical --omit=dev` が exit 1（I151 の PR #269・run 38564774555・2026-10-14）。
- 2 件とも CRA（react-scripts 5.0.1）の開発サーバー経路の推移的依存:
  - proxy-addr 2.0.7（GHSA-jqcg-44mw-7w3h・影響範囲 `>=1.1.0 <2.0.8`）: react-scripts → webpack-dev-server 4.15.2 → express 4.22.2 → proxy-addr
  - shell-quote 1.8.4（GHSA-395f-4hp3-45gv・`<=1.8.4`／GHSA-pqg4-j6r4-53mv・`>=1.8.4 <1.11.0`）: react-scripts → react-dev-utils 12.0.1 → shell-quote ／ webpack-dev-server → launch-editor 2.14.1 → shell-quote
- react-scripts が package.json の `dependencies` にあるため、`--omit=dev` でも監査対象に入る。
- 構造的な原因は CRA（メンテ停止）への依存。根治の CRA → Vite 移行は本イシューの範囲外。

### 目的
`npm audit fix`（`--force` なし）で package-lock.json だけを更新し、critical を 0 件にして CI を復旧する。I151 と相互に待ち合っている状態を、下記「マージ経路」で解消する。

## 2. 調査結果（2026-10-14〜15 実測・すべて本セッションで実走）

### 環境前提確認
- node v24.14.1 / npm 11.11.0（ホスト WSL2）。frontend/node_modules はインストール済み（`npm ls` で proxy-addr 2.0.7 / shell-quote 1.8.4 / axios 1.17.0 / react-router-dom 6.30.4 を確認）。
- Docker デーモンは本セッション時点で停止中。開発サーバー確認はホストの `npm start` で行う（AC は「`npm start` / docker compose の frontend」のいずれか）。
- `frontend/build/static` が root 所有（2026-07-19 作成・pre-existing）のため、ホストでの `npm run build` は EACCES で失敗する。ビルド回帰確認は `BUILD_PATH` を scratchpad に向けて実行する（下記ベースラインで成功を確認済み）。
- CI 定義: `ci.yml` / `e2e.yml` とも `pull_request: branches: [develop, main]` のみで起動。**develop/main 以外を向いた PR では CI が走らない**（マージ経路の判断材料）。
- リポジトリのマージ方式: 直近の develop 履歴はすべて merge commit（`Merge pull request #...`）。

### マージ経路（2026-10-15 ユーザー決定）
I151（PR #269）と本イシューは CI 上で相互に待ち合っている:
- I151 の PR → 本イシューの critical 2 件で Frontend Lint & Security が失敗（PR #269 の現状: 6 チェック中 Frontend Lint & Security のみ FAILURE）
- develop 起点の本イシューの PR → develop に残る Django 4.2 / anyio の CVE で Backend Lint & Security（pip-audit）が失敗

**決定: 独立 PR ＋ I151 ブランチへの取り込み**
1. 本イシューは develop 起点の独立ブランチ `feature/I159-fix-frontend-critical-vulns`・PR #277（develop 向け）で実装・記録する。
2. 本ブランチを I151 のブランチ `feature/I151-django-52-lts-upgrade` へ merge（`--no-ff`・force push なし）し、PR #269 で 6 チェックすべて SUCCESS を確認する。
3. PR #269（I151）を先に develop へマージする。merge commit 方式のため本ブランチのコミットも develop に入り、PR #277 は GitHub により「マージ済み」になる。
4. PR #277 単体の Backend Lint & Security の失敗は既知（I151 で解消）として扱う。

不採用案: I151 ブランチ起点の積み上げ PR（PR 先が develop 以外のため CI が一切走らない）／I151 の PR へ直接同梱（1 イシュー 1 ブランチ原則から外れ記録が混ざる）。

### 更新方法の比較（scratchpad に origin/develop の package.json / package-lock.json をコピーして模擬適用・リポジトリ無改変）
| 項目 | 修正前 | `npm audit fix --package-lock-only` | `npm update proxy-addr shell-quote --package-lock-only` |
|---|---|---|---|
| CI ゲート（`--audit-level=critical --omit=dev`） | exit 1 | **exit 0** | exit 0 |
| 件数表示 | 85（3 low / 14 moderate / 66 high / 2 critical） | 94（3 low / 34 moderate / 57 high / 0 critical） | 83（3 low / 14 moderate / 66 high / 0 critical） |
| lockfile の変更 | — | 34 パッケージ変更（追加 0・削除 0・メジャー更新 0） | 2 パッケージ変更 |
| package.json | — | 無変更 | 無変更 |
| 解消した advisory（GHSA 単位・重複除去） | — | 57 件（critical 2 / high 31 / moderate 22 / low 2。本番バンドルに入る axios の high 8・moderate 14 を含む） | 3 件（critical 2・shell-quote high 1） |
| 新たに出た advisory | — | **0 件**（advisory ID の差分で確認） | 0 件 |

**決定（2026-10-15 ユーザー決定）: `npm audit fix`**。本番の画面で使う axios（1.17.0 → 1.20.0・宣言 `^1.17.0` の範囲内）の high 8 件・moderate 14 件を含めて解消でき、新しく出る advisory はゼロ。範囲内更新のため回帰は Jest・型チェック・ESLint・ビルド・E2E で確認する。

**件数表示が 85 → 94 に増える理由**（新しい脆弱性ではない）: postcss-selector-parser 6.1.4 に残る moderate（GHSA-rj75-hqrm-r3gf・`<7.1.6`）は、修正前は「`npm audit fix` で直せる」扱いだったため依存元が数えられていなかった。fix 後は範囲内で直せる版が残っていないと判定され、依存元（postcss-preset-env・cssnano 等 25 パッケージ）が moderate として数えられるようになった。advisory ID 単位では fix 後にだけ現れるものは 0 件。

### 34 パッケージの変更一覧（模擬適用の実測）
本番バンドルに入るもの: axios 1.17.0→1.20.0、react-router 6.30.4→6.30.6、react-router-dom 6.30.4→6.30.6、@remix-run/router 1.23.3→1.23.4。
その他（ビルド・開発サーバー・lint のツールチェーン）: proxy-addr 2.0.7→2.0.8、shell-quote 1.8.4→1.12.0、express 4.22.2→4.22.3、body-parser 1.20.5→1.20.8、compression 1.8.1→1.8.2、qs 6.15.2→6.16.0（実装時は 6.16.1・後述）、side-channel 1.1.0→1.1.1、side-channel-list 1.0.0→1.0.1、fast-uri 3.1.2→3.1.8、js-yaml（3.15.0→3.15.2／4.3.0→4.3.2 ×2）、brace-expansion（1.1.14→1.1.21／2.1.0→2.1.7 ×2）、browserslist 4.28.2→4.29.3、caniuse-lite、electron-to-chromium、node-releases、update-browserslist-db、baseline-browser-mapping、colord 2.9.3→2.10.0、nanoid 3.3.11→3.3.20、postcss 8.5.12→8.5.30、postcss-selector-parser（6.1.2→6.1.4／7.1.0→7.1.6 ×2）、svgo 2.8.2→2.8.4、source-map-js 1.2.1→1.2.2、tailwindcss 3.4.17→3.4.19。

**実装時の差（2026-10-15）**: 実適用でも `changed 34 packages`。模擬適用との差は qs の解決版のみ（6.16.0 → 6.16.1・模擬適用後に公開されたパッチ版で `^` 範囲内）。TC-05 の許容範囲（advisory DB／レジストリの変化による前後）として記録し、計画は変更しない。

### 残存（fix 後 94 件・critical 0）のスコープ外根拠
- いずれも `npm audit fix --force`（react-scripts@0.0.0 への破壊的変更）でしか解消できない、または範囲内に修正版がないもの（webpack-dev-middleware・postcss-selector-parser 系・serialize-javascript 系・jest/jsdom 系 等）。
- CI の閾値は critical。high 以下はイシューのスコープ外（「含まない」に明記）。根治は CRA → Vite 移行（未起票の別イシュー）。

### 既存テスト・静的検査のベースライン（修正前・2026-10-15 実測）
| 検査 | コマンド | 結果 |
|---|---|---|
| Jest | `CI=true npm test`（frontend） | **3 suites / 10 tests 全 PASS**（74.7s）。act() 警告は pre-existing |
| 型チェック | `npx tsc --noEmit`（frontend） | exit 0 |
| ESLint | `npx eslint src/ --ext .ts,.tsx --max-warnings 0`（frontend） | exit 0 |
| ビルド | `BUILD_PATH=<scratchpad>/build-base npm run build`（frontend） | 成功 |
| E2E | CI の「E2E Tests (Playwright)」 | PR #269 で SUCCESS（frontend は develop と同一） |
| Backend | 変更なしのため対象外 | — |

### 決定論 TC の失敗注入（false-green 確認・2026-10-15 実測）
| TC | 修正前（または破壊入力） | 模擬適用後 |
|---|---|---|
| TC-01 ゲート | exit 1 | exit 0 |
| TC-02 対象 GHSA 不在 | exit 1 | exit 0 |
| TC-03 最低版チェック | exit 1（2.0.7 / 1.8.4 を NG） | exit 0 |
| TC-04 package.json 無変更 | axios 宣言を書き換えた入力で exit 1 | exit 0 |
| TC-05 メジャー更新なし・追加削除なし・react-scripts 5.0.1 | axios 2.0.0・react-scripts 0.0.0 を注入した入力で exit 1 | exit 0（changed=34） |

## 3. 受け入れ条件（イシューの AC を転記）
- [ ] AC-1: `frontend/` で `npm audit --audit-level=critical --omit=dev` が exit 0 → TC-01
- [ ] AC-2: `npm ls proxy-addr` が 2.0.8 以上、`npm ls shell-quote` が GHSA-395f-4hp3-45gv / GHSA-pqg4-j6r4-53mv の修正版以上（1.11.0 以上） → TC-02・TC-03
- [ ] AC-3: `frontend/package.json` の直接依存は変わっていない → TC-04・TC-05
- [ ] AC-4: 本イシューの変更と I151 の変更がそろった状態で、CI の 6 チェックがすべて SUCCESS（Frontend Lint & Security を含む） → M2
- [ ] AC-5: フロントエンドのテスト・型チェック・ビルド・E2E が更新前と同じく通る → TC-06〜TC-09・M1・M2
- [ ] AC-6: 開発サーバー（`npm start` / docker compose の frontend）が起動し、画面が表示される → M3・M4a〜M4c

## 4. 影響範囲
| 領域 | 影響 |
|------|------|
| Backend | なし |
| Frontend | `frontend/package-lock.json` のみ（範囲内更新 34 パッケージ。うち本番バンドルに入るのは axios / react-router / react-router-dom / @remix-run/router）。package.json・ソースコードは無変更 |
| DB | なし |
| Config/Infra | CI 定義・監査条件は変更しない |
| Docker | `frontend/Dockerfile` は `npm ci --only=production`、`Dockerfile.dev` は `npm install` で lockfile に従うため定義の変更は不要。docker compose の `frontend` は `/app/node_modules` を匿名ボリュームで持つため、既存コンテナは古い node_modules を使い続ける。反映には `docker compose up -d --build -V frontend`（再ビルド＋匿名ボリューム作り直し）が必要（M4c の手順に記載）。`frontend-test` は起動時の `npm install` で追従 |
| 他ブランチ | `feature/I151-django-52-lts-upgrade` に本ブランチを merge する（ユーザー決定のマージ経路）。I151 のファイルは変更しない |

## 5. 変更点一覧
| ファイル | 変更内容 |
|---------|---------|
| frontend/package-lock.json | `npm audit fix` による範囲内更新（34 パッケージ・一覧は §2） |
| docs/issues/open/I159.md | 「関連資料」に Draft PR #277 を追記（plan-issue で実施済み） |

package.json は変更しない（模擬適用で無変更を実証済み）。変更が出た場合は計画との不一致として停止・報告する。

## 6. 実装手順

### 修正アプローチ
frontend で `npm audit fix`（`--force` なし）を 1 回実行し、package-lock.json の範囲内更新だけで critical を 0 件にする。模擬適用で結果を実証済みのため、残る未知リスクは advisory DB の変化（実装時に新しい advisory が増えている可能性）のみ。そのため適用直前に再監査を置く（未知リスク先行）。その後、ユーザー決定のマージ経路どおり I151 のブランチへ取り込み、両方がそろった状態の CI を確認する。

### ステップ1: 適用直前の再監査（ドリフト確認）
- **修正方針**: 計画時と advisory の状況が変わっていないことを確かめ、修正前の不合格状態（Red）を記録する。→ TC-00 参照
- critical が 2 件以外に増えている・増えた critical が `npm audit fix` で直せない場合は**停止してユーザーへ報告**（計画との不一致）。

### ステップ2: npm audit fix の適用（ステップ1 完了が前提・唯一の変更ステップ）
- **修正方針**: 範囲内更新で lockfile と node_modules を同時に更新する（`npm audit fix` はインストールを伴うため追加操作不要）。
- 実行: `npm audit fix --prefix frontend`（`--force` は使わない。単体コマンドで実行し `&&` で結合しない）
- package.json に変更が出た・変更パッケージが §2 の 34 件と大きく異なる（追加・削除・メジャー更新がある）場合は**停止して報告**。→ TC-04・TC-05 参照

### ステップ3: 検証（ステップ2 完了が前提）
- ゲート・対象 GHSA の消失・最低版・非破壊性・回帰（型チェック・ESLint・Jest・ビルド）・残存件数を TC-01〜TC-10 で検証し、docs/tests/open/I159_auto_test.md に記録する。

### ステップ4: コミット・プッシュ・PR #277 の CI 確認（ステップ3 完了が前提）
- lockfile をコミットし PR #277 へ push する。→ M1 参照（Backend Lint & Security のみ pip-audit で失敗・他 5 チェック SUCCESS が期待値）

### ステップ5: I151 ブランチへの取り込みと PR #269 の CI 確認（ステップ4 完了が前提）
- **修正方針**: 両方の変更がそろった状態で 6 チェックすべてが通ることを示す（AC-4）。
- `git checkout feature/I151-django-52-lts-upgrade` → `git pull` → `git merge --no-ff origin/feature/I159-fix-frontend-critical-vulns` → `git push`（force push なし）。衝突が出た場合は停止して報告（I151 は frontend を変更していないため想定しない）。
- → M2 参照
- 本ステップ後に I159 側の修正が発生した場合は、修正を I159 ブランチへコミットし、本ステップを再実施する。
- 記録だけのコミット（テスト・レビュー・close の docs）も I159 ブランチに積まれるため、**#269 をマージする直前に I159 ブランチの最新を I151 ブランチへもう一度取り込む**（#277 が「マージ済み」になる条件は、#277 の最新コミットが develop に入ること）。

### ステップ6: 開発サーバーの起動確認（ステップ2 完了が前提・ステップ4/5 と並行可）
- → M3・M4a〜M4c 参照

### ステップ7（PR #269 マージ後）: 後始末
- PR #277 が「マージ済み」になったことを確認する（ならない場合は「#269 経由で develop に取り込み済み」とコメントして close）。→ M5 参照
- frontend の定期監査イシュー #220 を runbook（docs/runbooks/dependency-audit.md 手順 3）どおりクローズする。→ M6 参照
- I151 の `/code-review` をやり直す（I151 側の作業。本イシューでは引き継ぎのみ）。

## 7. テスト計画
- テストレベル: 依存更新のみでアプリコードの変更がないため、新しいユニットテストは追加しない。既存の Jest（ユニット/結合）・型チェック・ESLint・ビルド・CI の E2E（Playwright）を回帰確認に使い、監査結果は決定論 TC（exit code 判定）で確認する。
- 再発防止: 同種の critical 再発は CI ゲート（ci.yml）と定期監査（dependency-audit.yml）が既に検知する。構造的な解消は I152（#268）・CRA → Vite 移行に委ねる。
- 自動: docs/tests/open/I159_auto_test.md（TC-00〜TC-10）
- 手動: docs/tests/open/I159_manual_test.md（M1〜M6）
- 認可・テナント境界: 変更なしのため対象外。

## 8. ロールバック
- I151 へ取り込む前: lockfile 更新コミットを `git revert` → `npm ci --prefix frontend` で node_modules を戻す。
- I151 へ取り込んだ後・#269 マージ前: I151 ブランチで取り込みの merge commit を `git revert -m 1 <merge commit>` して push。
- develop へ入った後: develop 向けの revert PR を作成。データ・インフラへの影響なし。

## 9. Risk & 回避策
| リスク | 回避策 |
|--------|--------|
| 計画時と実装時で advisory DB が変わる（新しい critical の追加等） | ステップ1（TC-00）で再監査。新しい critical が `--force` なしで直せない場合は停止して報告 |
| axios 1.17→1.20 など本番バンドルに入るパッケージの挙動変化 | 範囲内（マイナー/パッチ）更新のみ（TC-05）。Jest（axios-mock-adapter を使う API テストを含む）・型チェック・ビルド・CI の E2E で回帰確認 |
| npm のバージョン差（ローカル 11.11.0 / CI） | fix はローカルで実行し lockfile をコミットする。CI は `npm ci` ＋判定のみのため差は出ない |
| PR #277 が自動で「マージ済み」にならない | M5 で確認し、ならない場合はコメントを付けて close |
| I151 ブランチ側との衝突 | I151 は frontend を変更していない（`git diff origin/develop origin/feature/I151-django-52-lts-upgrade -- frontend/` が空であることを確認済み）。衝突したら停止して報告 |
| docker compose の frontend が古い node_modules を使い続ける | M4c の手順で `-V` 付きで作り直す |
| `frontend/build/static` が root 所有でホストの build が失敗する（pre-existing） | `BUILD_PATH` を scratchpad に向けて実行（TC-09）。build ディレクトリの所有者是正は本イシューの範囲外 |

## 10. セキュリティ・品質チェック（plan-issue 必須確認の記録）
- **要件適合性**: 変更は lockfile の範囲内更新のみでイシューの範囲内。`npm audit fix` で critical 以外も上がる点はイシューの解決方針（「差分をレビューして許容」）どおりで、差分は §2 に全件記録した。マルチテナント・ステータス遷移・業務ルールへの影響なし。
- **セキュリティ**: セキュリティを改善する側の変更（critical 2 件を含む計 57 advisory（GHSA 単位）の解消・新しい advisory 0 件）。コード変更なし・認証認可/入力検証/機密データの変更なし。追加・更新する依存の既知脆弱性は模擬適用後の `npm audit` で確認済み（fix 後にだけ現れる advisory ID は 0 件）。
- **重大度基準**: npm audit は critical を修正対象（CI ゲート）とし、`npm audit fix` で範囲内に直せる high 以下も同時に解消する。`--force` が必要な残存はスコープ外。bandit は Backend 変更なしのため対象外。
- **P3（データ整合性）/ P5（運用設計）/ P8（コスト）影響なし**: DB・外部 API・非同期処理・新規インフラなし。依存ファイルの Dockerfile / docker-compose への波及は §4 に記載。
- **P6（性能・UX）影響なし**: UI・アプリコードの変更なし（画面表示の確認は M4a〜M4c で実施）。
- **P9（プライバシー）影響なし**: 個人情報・テナントデータを扱わない。
- **設計品質**: コード変更なし。設定値・定数のハードコードなし。

### 設計判断の明示
| 設計判断 | 根拠 |
|---|---|
| `npm audit fix`（`--force` なし）を使う | イシューに明記（解決方針）＋ 2026-10-15 ユーザー決定（34 パッケージの差分を提示のうえ選択） |
| マージ経路 = 独立 PR #277 ＋ I151 ブランチへの取り込み・#269 を先にマージ | イシューで /plan-issue でのユーザー決定と明記 → 2026-10-15 ユーザー決定 |
| 変更は package-lock.json のみ・package.json 無変更 | イシューに明記（模擬適用で実証） |
| 残存（high 以下・`--force` 必須）はスコープ外 | イシューに明記（「含まない」） |
| ビルド回帰を `BUILD_PATH` で scratchpad に出力 | 仮定ではなく環境実測（build/static が root 所有）に基づく検証手段の選択。成果物・コードに影響しない |
| 開発サーバー確認は Claude が実施する: ホストの `npm start`（M3）＋ CI E2E の結果（M4b）＋ 修正前後の CSS 同一性（M4a）＋ 手元 Docker での Playwright 実行で Console エラー 0 件（M4c）。人の目視は使わない | 2026-10-15 ユーザー合意（当初は docker compose＋ブラウザを Human 確認としていたが、CI E2E が同じ経路を検証済みであり、未検証点は CSS と Console エラーと手元 Docker のみと整理して Claude 実施に変更） |
| #220（frontend 定期監査イシュー）をマージ後にクローズ | runbook（dependency-audit.md 手順 3）に明記 |

仮定で決めた項目はない。

## 11. 承認ポイント
- [ ] 更新方法は `npm audit fix`（`--force` なし）。変更は frontend/package-lock.json のみ（34 パッケージの範囲内更新。axios 1.17→1.20・react-router-dom 6.30.4→6.30.6 を含む）
- [ ] マージ経路: PR #277 は develop 向けのまま、本ブランチを I151 ブランチへ取り込み、PR #269 で 6 チェック全 SUCCESS を確認 → #269 を先にマージ（#277 はそれで develop 入り）
- [ ] PR #277 単体の Backend Lint & Security の失敗（pip-audit・I151 で解消）は既知として許容
- [ ] 残存（fix 後 94 件表示・critical 0・新しい advisory 0）はスコープ外として許容
- [ ] #269 マージ後に #277 の状態確認と #220 のクローズを行い、I151 の `/code-review` をやり直す

## レビュー結果
- [20261015_1222 判定: ✅ 完了](../../reviews/I159_plan_review_20261015_1222.md)
  - Warning（TC-10 のパイプ前提）: 対応済み。auto_test に `$S/tc10.sh` ラッパーを追加し TC-00(4)・TC-10 を `bash $S/tc10.sh frontend` に変更（修正前 lockfile で exit 1・模擬適用後で exit 0 を再実測）
  - Info（TC-04 #2 注記）: 対応不要。`git diff <commit>` は 1 引数のときコミットと作業ツリーを比較する仕様のため、「コミット前は作業ツリーとの比較」の記述は正しい（修正前の実測 exit 1 も作業ツリー比較の結果）
