# I545 自動テスト: コードの書き方の決まりをベストプラクティスのあるべき状態に見直す

実行コマンド: 文書だけの変更のため、pytest・Jest・E2E は CI に任せる（このイシューでは足さない）。

結果:
- backend: 対象外（変更なし）
- frontend: 対象外（変更なし）

## テストケース
| TC | 確かめること | 合否 | 失敗の注入（FG） |
|---|---|---|---|
| TC-01 | 規約 2 本の冒頭に「前提の版」の節がある | 下のゲートの 1〜2 行目が exit 0 | 実装前の今の規約で実行し、exit 1（不合格）になることを確認 |
| TC-02・TC-03 | `rules/` の下（`rules/bk/` などの下のフォルダを含む）に、正の 2 本のほかに中身のあるファイルが無い（正でない古い規約 4 本・控えの 4 本を含む） | ゲートの 3 行目が exit 0（内側の grep が「一致なし」の exit 1。ほかにファイルがあれば exit 0 で不合格、`rules/` が無ければ exit 2 で不合格） | 実装前の今（8 本がある）と、`rules/bk/react-coding-standards.md` を置いた写しで、内側の grep が exit 0（不合格）になることを確認。0 バイトのファイルは捕まえない（規約として読まれないので受け入れる・fix-loop の診断メモ） |
| TC-04 | `docs/runbooks/issue-flow.md` が「`/rules/` 配下の関連ルールファイル」と書かず、正の 2 本を名指ししている | ゲートの 4〜6 行目が exit 0 | 実装前の今の `issue-flow.md` で実行し、4 行目が exit 1 になることを確認 |
| TC-05 | `docs/runbooks/backend-check.md` に curl で API を叩く手順（`curl -X`・`curl -s`・`curl http…` の形のどれも）が残っていない | ゲートの 7〜8 行目が exit 0（`|` を使わない 2 行。ゲートの行に `|` を書くと実走されない） | 変更前の backend-check.md で 7 行目の内側が exit 0（不合格）、`curl http://x` を入れた写しで 8 行目の内側が exit 0（不合格）を確認 |
| TC-06 | `docs/runbooks/ux-rules.md` に計画書の UX の節のひな形が残っていない | ゲートの 9 行目が exit 0 | 実装前の今（ひな形がある）で実行し、exit 1 になることを確認 |
| TC-07 | `.secrets.baseline` に `docs/runbooks/backend-check.md` の登録が無く、その元の文字列（`testpass`）が `docs/runbooks/backend-check.md` に無い | ゲートの 10〜11 行目が exit 0 | 実装前の `origin/develop` の 2 ファイルの写しで実行し、exit 1 になることを確認 |

FG の記録（計画の時点・実装前）: 下の「FG の実行記録」に書く。

## 決定論ゲート（自動実走）
```bash
grep -q "前提の版" rules/ultimate_django_coding_standards.md
grep -q "前提の版" rules/react-coding-standards-integrated.md
! grep -rq --exclude=ultimate_django_coding_standards.md --exclude=react-coding-standards-integrated.md "" rules
! grep -q "配下の関連ルールファイル" docs/runbooks/issue-flow.md
grep -q "rules/ultimate_django_coding_standards.md" docs/runbooks/issue-flow.md
grep -q "rules/react-coding-standards-integrated.md" docs/runbooks/issue-flow.md
! grep -q "curl -" docs/runbooks/backend-check.md
! grep -q "curl http" docs/runbooks/backend-check.md
! grep -q "### 改善後のユーザー体験" docs/runbooks/ux-rules.md
! grep -q "docs/runbooks/backend-check.md" .secrets.baseline
! grep -q "testpass" docs/runbooks/backend-check.md
```

## FG の実行記録
- 2026-11-17（計画の時点・実装前）: ゲートの 15 行を 1 行ずつ `bash -c` で実行し、15 行すべて exit 1（不合格）。実装前の状態（前提の版の節が無い・古い規約と控えがある・issue-flow が名指ししていない・backend-check に curl の手順・ux-rules にひな形）を捕まえることを確認した
- 同日・合格側の確認: 無いファイルに `! grep -qs ""` が exit 0、無い文言に `! grep -q` が exit 0（直した後の状態で合格する形であることを確認）
- 同日・計画レビューの Warning で TC-05 を `curl +(-|http)` に広げた: 今の backend-check.md で exit 1、`TOKEN=$(curl -s http://x)` と `curl http://x` を入れた写しで exit 1、「curl で API を叩く手順は使わない」という文だけの写しで exit 0（文中の言及は捕まえない）
- 同日・実装の後に TC-07 を足した: `origin/develop` の `.secrets.baseline` と `docs/runbooks/backend-check.md` の写しで 16・17 行目がどちらも exit 1、今の 2 ファイルでどちらも exit 0
- 同日・実装の後に 1〜15 行目を流し直し、すべて exit 0
- 実装後の合否は review-gate の決定論ゲートの実走で記録する

## 再発防止記録（fix-loop・2026-11-17）
- なぜ失敗したか: review-gate の実走（`scripts/claude/code-review.sh` の `run_one_gate()`）は、`! grep` の行を内側の grep が exit 1（一致なし）のときだけ合格にし、exit 2（ファイルが無いなど）を不合格にする。名指ししたファイルの不在を `! grep -qs "" <ファイル>` で見る 8 行は、ファイルが無いと exit 2 になり、実走で 8 行とも不合格になった（F1）。計画の時点の失敗の注入を、手元の `bash -c` で `!` をそのまま評価して確かめたため、実走の判定との違いに気づかなかった。あわせて、React 規約 §8 のフォームの例に検証の時機（`mode`）が無く、ux-rules §3 と食い違っていた（F2）
- 何を変えたか: 8 行を `! grep -rq --exclude=<正の 2 本> "" rules` の 1 行にした（`rules/` の下のどこにでも、正でないファイルがあれば捕まえる）。React 規約 §8 に `mode: 'onTouched'` の決まりと例を足した
- セキュリティ上の考慮点: なし（文書と文書のテスト）
- 次回どう防ぐか: 決定論ゲートの失敗の注入は、`run_one_gate()` と同じ判定（`! grep` は内側の exit が 1 のときだけ合格）で確かめる。手元の確かめの道具（スクラッチパッドの `run_gate.sh`）をその判定に直した
- 確かめた結果: 直したゲート 10 行を `run_one_gate()` と同じ判定で流し、すべて合格。3 行目は、`rules/bk/react-coding-standards.md` を置いた写しで内側の grep が exit 0（不合格）になることを確認

## 再発防止記録（fix-loop 2 回目・2026-11-17）
- なぜ失敗したか: TC-05 を正規表現の選択肢 `(-|http)` で 1 行にまとめた。`scripts/claude/code-review.sh` の `classify_gate()` は、`|` を含む行をチェーンの疑いとして実走せず（fail-closed）、ゲートの判定が BLOCKER になった。手元の確かめの道具がこの分類をまねていなかった
- 何を変えたか: `|` を使わない `! grep -q "curl -"` と `! grep -q "curl http"` の 2 行に分けた
- セキュリティ上の考慮点: なし
- 次回どう防ぐか: 手元の確かめの道具（スクラッチパッドの `run_gate.sh`）に `classify_gate()` と同じ「実走しない文字」（`;`・`|`・`&`・バッククォート・`$(`・`>`）の分類を足し、古い 1 行が UNSAFE になることを確かめた
- 確かめた結果: 直したゲート 11 行を、`classify_gate()`・`run_one_gate()` と同じ判定で流してすべて合格。7 行目は変更前の backend-check.md で、8 行目は `curl http://x` を入れた写しで、内側の grep が exit 0（不合格）になることを確認
