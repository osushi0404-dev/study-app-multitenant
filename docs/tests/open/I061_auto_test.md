# I061 自動テスト（依存脆弱性是正の機械検証）

対象: `frontend`。すべて `cd frontend` 前提。`/test` 実行時に Claude が自動実行できる（コマンド実行・JSON 解析）。
ベースライン（修正前・実測）: `npm audit --audit-level=critical --omit=dev` = **exit 1**（critical=1）。

| TC | 観点 | 検証コマンド | 期待結果 | 結果 |
|----|------|--------------|----------|------|
| TC-01 | critical ゲート（CI 緑化条件・回帰テスト） | `cd frontend && npm audit --audit-level=critical --omit=dev; echo "exit=$?"` | `exit=0`（critical ゼロ。修正前は exit=1） | |
| TC-02 | critical `shell-quote` 解消 | `cd frontend && npm audit --omit=dev --json \| node -e "const d=JSON.parse(require('fs').readFileSync(0));process.exit(d.vulnerabilities?.['shell-quote']?1:0)"; echo "exit=$?"` | `exit=0`（shell-quote が脆弱性一覧に無い） | |
| TC-03 | axios が非脆弱版 | `cd frontend && node -p "require('./node_modules/axios/package.json').version"` | `1.15.3` 以上（脆弱範囲 ≤1.15.2 を脱している。例: 1.17.0） | |
| TC-04 | クリーン high 6件が解消 | `cd frontend && npm audit --omit=dev --json \| node -e "const d=JSON.parse(require('fs').readFileSync(0));const t=['axios','fast-uri','underscore','@babel/plugin-transform-modules-systemjs','jsonpath','bfj'];const r=t.filter(n=>d.vulnerabilities?.[n]);console.log(r.length?('残存: '+r.join(',')):'OK');process.exit(r.length?1:0)"` | `OK`（6件すべて解消・exit 0） | |
| TC-05 | 本番ビルド成功 | `cd frontend && npm run build >/tmp/i061_build.log 2>&1; echo "exit=$?"; tail -3 /tmp/i061_build.log` | `exit=0`（ビルド成功。`Compiled successfully` 相当も併記確認） | |
| TC-06 | フロントユニットテスト | `cd frontend && CI=true npm test -- --watchAll=false --passWithNoTests 2>&1 \| tail -15` | 既存テストが全 pass（失敗0） | |
| TC-07 | 型チェック | `cd frontend && npx tsc --noEmit; echo "exit=$?"`（pipe を使わず exit code を直接取得） | 型エラーなし（exit=0） | |
| TC-08 | 残存 high = react-scripts 固着の5件のみ（risk-accept 範囲の確認） | `cd frontend && npm audit --omit=dev --json \| node -e "const d=JSON.parse(require('fs').readFileSync(0));const hi=Object.entries(d.vulnerabilities).filter(([k,v])=>v.severity==='high').map(([k])=>k).sort();console.log(JSON.stringify(hi))"` | `["react-scripts","rollup-plugin-terser","serialize-javascript","workbox-build","workbox-webpack-plugin"]`（この5件のみ。クリーン6件は含まれない） | |
| TC-09 | moderate/low の before/after 記録（--force 不要分の是正確認・再発防止） | `cd frontend && npm audit --omit=dev --json \| node -e "const d=JSON.parse(require('fs').readFileSync(0));console.log(JSON.stringify(d.metadata.vulnerabilities))"` | 修正前 `{...,"moderate":9,"low":9,...}` に対し、修正後は moderate/low が**減少**（`--force` 不要分が解消。残存は react-scripts 由来＝計画書 §9 と整合）。before/after を備考に記録 | |

## 補足
- TC-01 は CI `Frontend Lint & Security`（`npm audit --audit-level=critical`）と同条件。これが exit 0 になれば PR #127、および develop マージ後の PR #125 の当該ジョブが緑化する。
- TC-03 の axios バージョンは lockfile 実体を見る（package.json の range ではなく実インストール版）。
- TC-08 の5件は計画書 §9 の risk-accept 対象。これ以外の high が出た場合は想定外として要調査。
