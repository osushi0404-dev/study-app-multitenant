# I209 自動テスト: ハーネスの古いイシューを棚卸しし、今の流れで不要なものを閉じる

実行コマンド（例）: アプリのテスト（pytest・Jest・E2E）は非該当（コードを変えない）。小さな指摘の一覧の行の形は CI の Harness Tests（`scripts/claude/tests/test_i202_ledger_cleanup.sh` の D3）が確かめる

結果:
- backend: 非該当
- frontend: 非該当

## テストケース
| TC | 対象 | 手順 | 期待値（合否は exit code） | 失敗注入 | 結果 |
|---|---|---|---|---|---|
| TC-01 | AC1: 一覧の番号が 52 件そろう | 下の「TC-01 の確かめ」をスクラッチに置き、`bash <スクリプト> docs/reviews/open/I209_triage.md` | exit 0・`OK: 52 件一致` | `#233` の行を消した写しで exit 1・`NG: 不一致`（2026-10-28 確認済み） | 2026-10-28 計画時に実行: exit 0（OK: 52 件一致） |
| TC-02 | AC4: 小さな指摘の一覧の行の形 | CI の Harness Tests（`test_i202_ledger_cleanup.sh` の D3「実物の一覧のどの行も決まった形」）が `docs/reviews/backlog/I209.md` を含めて確かめる | D3 が pass | FG-D3（同じテストの中で、形の崩れた行を足した写しが不合格になる）が既にある | 実装前のため未実行 |
| TC-03 | AC4: 一覧に F1〜F9 がある | `grep -c '^- F[1-9] SEV=' docs/reviews/backlog/I209.md` の値が 9（`[ "$(grep -c … )" -eq 9 ]` の形で exit code に畳む） | exit 0 | F9 の行を消した写しで exit 1 | 実装前のため未実行 |

### TC-01 の確かめ（スクラッチに置くスクリプト）
```text
#!/usr/bin/env bash
# 一覧（判定一覧の表の 1 列目）の番号が、2026-10-28 の開いている track:harness（#349 を除く 52 件）とちょうど一致するか
set -u
f="${1:?一覧のファイル}"
expected="10 153 154 168 172 173 175 176 177 179 180 189 191 197 206 207 208 214 216 222 226 227 230 231 233 237 244 245 247 250 252 255 258 259 268 278 279 280 283 289 290 291 294 295 296 316 319 321 324 325 335 337"
actual=$(awk '/^## 判定一覧/{on=1;next} /^## /{on=0} on && /^\| *[0-9]+ *\|/{gsub(/ /,"",$0); split($0,a,"|"); print a[2]}' "$f" | sort -n | tr '\n' ' ' | sed 's/ $//')
exp_sorted=$(echo "$expected" | tr ' ' '\n' | sort -n | tr '\n' ' ' | sed 's/ $//')
if [ "$actual" = "$exp_sorted" ]; then echo "OK: 52 件一致"; exit 0; fi
echo "NG: 不一致"; echo "期待: $exp_sorted"; echo "実際: $actual"; exit 1
```

## 決定論ゲート（自動実走）
<!-- このイシューはコードを変えないので、review-gate が流す決定論ゲートは置かない（GitHub の状態は手動テスト〔実施者 Claude〕で確かめる。計画書 9） -->
