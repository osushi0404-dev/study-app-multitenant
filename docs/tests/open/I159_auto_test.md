# I159 自動テスト: frontend 依存の critical 脆弱性（proxy-addr / shell-quote）を npm audit fix で解消

対象: frontend/package-lock.json（`npm audit fix` 適用後）
実行ディレクトリ: リポジトリルート（frontend 側のコマンドは `--prefix frontend` または `frontend/` を明記）
`$S` = Claude セッションの scratchpad ディレクトリ（TC 用スクリプト・ビルド出力の置き場。リポジトリには置かない）

合否はすべて **exit code**（合格 = exit 0・不合格 = 非ゼロ）で判定する。TC-10 のみ件数の記録を兼ねる（合否は critical 0 件の exit code）。

## 結果
- 計画時（2026-10-15）: origin/develop の package.json / package-lock.json を `$S` にコピーし、`npm audit fix --package-lock-only` を模擬適用した lockfile で TC-01〜TC-05 を実行。**修正前（または失敗注入入力）で不合格・模擬適用後で合格**を確認済み（false-green でない）。詳細は各 TC の「失敗注入」欄。
- **実装時（2026-10-15）: 全 TC PASS**
  - TC-00: (1) exit 1 / (2) exit 1 / (3) exit 1（2.0.7・1.8.4 を NG）/ (4) exit 1・`critical 2・total 85`＝計画時と同一（ドリフトなし）
  - `npm audit fix --prefix frontend`: `changed 34 packages`（コマンド自体は残存 high 以下の報告で exit 1。想定どおり）
  - TC-01: exit 0
  - TC-02: exit 0（3 GHSA とも不在）
  - TC-03: exit 0（proxy-addr 2.0.8 / shell-quote 1.12.0）
  - TC-04: #1 exit 0 / #2 exit 0
  - TC-05: exit 0・`changed=34 ng=0`。計画時の模擬適用との差は **qs のみ 6.16.0 → 6.16.1**（模擬適用後に公開されたパッチ版。他 33 件は版まで一致）
  - TC-06: exit 0
  - TC-07: exit 0（frontend ディレクトリで実行）
  - TC-08: exit 0・3 suites / 10 tests 全 PASS（65.3s・ベースラインと同数）
  - TC-09: exit 0（`Compiled successfully.`）
  - TC-10: exit 0・`low 3 / moderate 34 / high 57 / critical 0（total 94）`＝計画時の模擬適用と一致

## TC 用スクリプト（実行前に `$S` へ保存する）

`$S/tc02.js`（対象 GHSA の不在判定。監査結果の JSON を読み、advisory の URL で構造的に照合する）:
```js
const target = ['GHSA-jqcg-44mw-7w3h', 'GHSA-395f-4hp3-45gv', 'GHSA-pqg4-j6r4-53mv'];
const v = JSON.parse(require('fs').readFileSync(0)).vulnerabilities || {};
const hits = [];
for (const [name, info] of Object.entries(v)) for (const x of info.via)
  if (typeof x === 'object' && target.some(t => x.url.endsWith(t))) hits.push(`${name} ${x.url}`);
console.log(hits.length ? 'NG: ' + hits.join(', ') : 'OK: target advisories absent');
process.exit(hits.length ? 1 : 0);
```

`$S/tc02.sh`（パイプを 1 コマンドに含めないためのラッパー）:
```bash
#!/bin/bash
# usage: tc02.sh <package-lock.json があるディレクトリ>
S="$(cd "$(dirname "$0")" && pwd)"
cd "$1" || exit 2
npm audit --omit=dev --json 2>/dev/null | node "$S/tc02.js"
```

`$S/tc03.js`（最低版の判定。lockfile 内のすべての proxy-addr / shell-quote を対象にする）:
```js
const p=JSON.parse(require("fs").readFileSync(process.argv[2])).packages;
const min={"proxy-addr":[2,0,8],"shell-quote":[1,11,0]};let ok=true,seen={};
for(const [k,v] of Object.entries(p)){const n=k.split("node_modules/").pop();if(!min[n])continue;seen[n]=1;
const a=v.version.split(".").map(Number),m=min[n];const ge=a[0]!==m[0]?a[0]>m[0]:a[1]!==m[1]?a[1]>m[1]:a[2]>=m[2];
console.log(k,v.version,ge?"OK":"NG");if(!ge)ok=false}
if(Object.keys(seen).length!==2){console.log("NG: package missing");ok=false}
process.exit(ok?0:1);
```

`$S/tc05.js`（範囲内更新の判定: 追加・削除なし・メジャー更新なし・react-scripts 5.0.1）:
```js
// usage: node tc05.js <base package-lock.json> <new package-lock.json>
const fs=require("fs");const [a,b]=process.argv.slice(2).map(f=>JSON.parse(fs.readFileSync(f)).packages);
let ng=0,chg=0;
for(const k of new Set([...Object.keys(a),...Object.keys(b)])){if(!k)continue;const va=a[k]&&a[k].version,vb=b[k]&&b[k].version;
if(va===vb)continue;
if(!va||!vb){console.log("NG add/remove",k,va,vb);ng++;continue}
chg++;const major=v=>v.split(".")[0];
if(major(va)!==major(vb)||(major(va)==="0"&&va.split(".")[1]!==vb.split(".")[1])){console.log("NG major",k,va,"->",vb);ng++}}
const rs=b["node_modules/react-scripts"];if(!rs||rs.version!=="5.0.1"){console.log("NG react-scripts",rs&&rs.version);ng++}
console.log(`changed=${chg} ng=${ng}`);process.exit(ng?1:0);
```

`$S/tc10.js`（critical 件数の判定と件数の表示）:
```js
const m=JSON.parse(require("fs").readFileSync(0)).metadata.vulnerabilities;
console.log(JSON.stringify(m));process.exit(m.critical===0?0:1);
```

`$S/tc10.sh`（パイプを Bash ツールの 1 コマンドに含めないためのラッパー。tc02.sh と同じ形）:
```bash
#!/bin/bash
# usage: tc10.sh <package-lock.json があるディレクトリ>
S="$(cd "$(dirname "$0")" && pwd)"
cd "$1" || exit 2
npm audit --omit=dev --json 2>/dev/null | node "$S/tc10.js"
```

## テストケース

### TC-00: 適用直前の Red 確認・ドリフト確認（計画 ステップ1）
| 項目 | 内容 |
|------|------|
| 実行タイミング | `npm audit fix` の**前** |
| コマンド | (1) `npm audit --audit-level=critical --omit=dev --prefix frontend` (2) `bash $S/tc02.sh frontend` (3) `node $S/tc03.js frontend/package-lock.json` (4) `bash $S/tc10.sh frontend` |
| 期待値 | (1)(2)(3)(4) とも **非ゼロ終了**（修正前は不合格）。(4) の表示が `"critical":2`（計画時と同じ）であること。critical が 2 以外の場合は計画 ステップ1 に従い停止して報告 |

### TC-01: CI ゲート同一条件の監査（AC-1）
| 項目 | 内容 |
|------|------|
| コマンド | `npm audit --audit-level=critical --omit=dev --prefix frontend` |
| 期待値 | **exit 0** |
| 失敗注入 | 修正前の lockfile で exit 1・模擬適用後で exit 0（2026-10-15 実測） |

### TC-02: 対象 3 advisory の消失（AC-2）
| 項目 | 内容 |
|------|------|
| コマンド | `bash $S/tc02.sh frontend` |
| 期待値 | **exit 0**（GHSA-jqcg-44mw-7w3h / GHSA-395f-4hp3-45gv / GHSA-pqg4-j6r4-53mv が監査結果にない） |
| 失敗注入 | 修正前の lockfile で exit 1・模擬適用後で exit 0（2026-10-15 実測）。code-review 指摘（omission-lint）対応で文字列検索から JSON 構造照合に書き換えた後も、修正前の lockfile で exit 1（3 件とも NG 表示）・修正後の frontend で exit 0 を再実測（2026-10-15） |

### TC-03: 修正版以上への更新（AC-2）
| 項目 | 内容 |
|------|------|
| コマンド | `node $S/tc03.js frontend/package-lock.json` |
| 期待値 | **exit 0**（proxy-addr ≥ 2.0.8・shell-quote ≥ 1.11.0。模擬適用では proxy-addr 2.0.8 / shell-quote 1.12.0） |
| 失敗注入 | 修正前の lockfile で exit 1（2.0.7 / 1.8.4 を NG と表示）・模擬適用後で exit 0（2026-10-15 実測） |

### TC-04: package.json 無変更・変更ファイルは lockfile のみ（AC-3）
| # | コマンド | 期待値 |
|---|---------|--------|
| 1 | `git diff --quiet origin/develop -- frontend/package.json` | **exit 0**（差分なし） |
| 2 | `[ "$(git diff --name-only origin/develop -- frontend/)" = "frontend/package-lock.json" ]` | **exit 0**（frontend 配下の変更は lockfile 1 ファイルのみ。コミット前は作業ツリーとの比較、コミット後はコミット済みとの比較になる） |

失敗注入: #1 は axios の宣言を書き換えた package.json と元ファイルの比較（`git diff --quiet --no-index`）で exit 1・模擬適用後の package.json との比較で exit 0（2026-10-15 実測）。#2 は修正前（frontend 配下の差分なし）で exit 1 を実測（2026-10-15）。文字列一致の判定のため、余分なファイルが含まれる場合も出力が一致せず exit 1 になる。

### TC-05: 範囲内更新であること（AC-3・非破壊性）
| 項目 | 内容 |
|------|------|
| コマンド | `git show origin/develop:frontend/package-lock.json > $S/base-lock.json` の後、`node $S/tc05.js $S/base-lock.json frontend/package-lock.json` |
| 期待値 | **exit 0**（追加・削除なし・メジャー更新なし・react-scripts 5.0.1）。表示の `changed=` は計画時実測 34（advisory DB の変化で前後した場合は実測値を記録し、計画書 §2 の一覧と比べて差を記録する） |
| 失敗注入 | axios 2.0.0・react-scripts 0.0.0 を注入した lockfile で exit 1（NG 3 件を表示）・模擬適用後で exit 0・changed=34（2026-10-15 実測） |

### TC-06: 型チェック回帰（AC-5）
| 項目 | 内容 |
|------|------|
| コマンド | `npx --prefix frontend tsc --noEmit -p frontend` |
| 期待値 | **exit 0**（ベースライン 2026-10-15: exit 0） |

### TC-07: ESLint 回帰（AC-5・CI と同条件）
| 項目 | 内容 |
|------|------|
| コマンド | frontend ディレクトリで `npx eslint src/ --ext .ts,.tsx --max-warnings 0` |
| 期待値 | **exit 0**（ベースライン 2026-10-15: exit 0） |

### TC-08: Jest 回帰（AC-5・CI と同条件）
| 項目 | 内容 |
|------|------|
| コマンド | frontend ディレクトリで `CI=true npm test` |
| 期待値 | **exit 0・3 suites / 10 tests 全 PASS**（ベースライン 2026-10-15: 3 suites / 10 tests PASS・74.7s。act() 警告は pre-existing） |

### TC-09: 本番ビルド回帰（AC-5）
| 項目 | 内容 |
|------|------|
| コマンド | frontend ディレクトリで `BUILD_PATH=$S/build-after npm run build` |
| 期待値 | **exit 0**（`The build folder is ready to be deployed.` を表示）。`frontend/build/static` が root 所有（pre-existing）のため出力先を `$S` に向ける |
| ベースライン | 2026-10-15: `BUILD_PATH=$S/build-base` で成功 |

### TC-10: 残存件数の記録（合否は critical 0）
| 項目 | 内容 |
|------|------|
| コマンド | `bash $S/tc10.sh frontend` |
| 期待値 | **exit 0**（critical 0）。計画時の模擬適用実測: low 3 / moderate 34 / high 57 / critical 0（合計 94）。advisory DB の変化で前後した場合は実測値を記録する |
| 失敗注入 | 修正前の監査結果（critical 2）で exit 1・模擬適用後で exit 0（2026-10-15 実測） |

## 実行順序・前提
- TC-00 は `npm audit fix` の前に実行する。
- TC-01〜TC-10 は `npm audit fix` の後に実行する。TC-06〜TC-09 は node_modules の更新が前提（`npm audit fix` はインストールを伴うため通常は追加操作不要。ずれている場合のみ `npm ci --prefix frontend`）。
- E2E（Playwright）は CI で確認する（手動テスト M1・M2）。

## 決定論ゲート（自動実走）
<!-- 本イシューの TC は npm / node / docker を使う heavy 判定のため /test・実装時に実行する（code-review.sh の allowlist 外）。自動実走するゲートは無い。 -->
