# I208 自動テスト: 台帳の残りの振り分けと一覧の行をスクリプトが出すようにし、テストを実物の一覧に依存させない

実行コマンド（例）: アプリのコード変更が無いため `docker compose exec backend python -m pytest`・`docker compose exec frontend npm test`・E2E は非該当（CI では今までどおり動く）

結果:
- backend: 非該当
- frontend: 非該当

## テストケース

合否はすべて終了コード（合格=exit 0・不合格=非ゼロ）。否定の判定（「一覧に落ちない」「変わらない」「落ちない」）には失敗注入（FG: 本体の一時コピーの判定の要を壊す／指示ファイル・一覧の写しから行を消す・足すと、対応する項目が不合格になることを確かめる）を付ける。実際の claude は使わない。

| TC | 内容 | 期待値 | 結果 |
|---|---|---|---|
| TC-01 | `bash scripts/claude/tests/test_i202_ledger_cleanup.sh`（I207 の節の D1〜D3 を書き換え・「I208」の節 Q1〜Q9 を足す）。既存の R・L・W・A・G・D・N・P も | exit 0・`fail=0`（ベースライン pass=128） | implement で実行（2026-10-27）: 実装前（Red）pass=123 fail=25（R1・N2・N3・P1・P6〔FILE の欄〕・D1・D3・Q1〜Q9 と「FG の写しがすべて作れた」）→ 実装後 pass=148 fail=0 |
| TC-02 | 影響を受けうるテスト: `test_i205_stop_criteria.sh`（D4 を `--route` に変える）・`test_i197_review_ledger.sh`（台帳の更新・前の形の行）・`test_i180_retro_triage.sh`・`test_i114_retro_plain_output.sh`・`test_i193_official_flow.sh`（retro の文言） | どれも exit 0 | implement で実行（2026-10-27）: pass=91・pass=64・13/13・14/14・pass=160（fail=0） |
| TC-03 | `bash scripts/claude/tests/run-all.sh`（CI の Harness Tests ジョブで確かめる。手元では流し直さない） | CI の Harness Tests が pass | 実装前のため未実行 |

### TC-01 の項目（I208 の節）
一時の git リポジトリ（既存の `$R`: `backend/x.py`・`scripts/claude/a.sh`・`.github/workflows/ci.yml`〔20 行ずつ〕。行の塊は各 10 行目）と、手書きの FINDING 行・台帳の行で確かめる。振り分けは `ledger_route <issue|backlog> <台帳のファイル>`（一時のファイル）で確かめ、実物の記録・一覧は読まない（D3 の形の確認を除く）。

| 項目 | 入力 | 期待値 | FG（失敗注入） |
|---|---|---|---|
| Q1（AC3） | 全体のレビュー。`FINDING: F1 SEV=Low STATUS=open FILE=./scripts/claude/a.sh:10 LINE=10 SECURITY=no STOP=- \| 一` と `FINDING: F2 SEV=Low STATUS=open FILE=- LINE=- SECURITY=no STOP=- \| 二` | 台帳の F1 が `… SECURITY=no FILE=scripts/claude/a.sh \| 一`、F2 が `… SECURITY=no FILE=- \| 二` | FG-Q1: `ledger_line()` から ` FILE={…}` を除いた写しで、F1 の行が不合格 |
| Q2（AC3） | 前の台帳: `LEDGER: F1 SEV=High STATUS=open SCOPE=delta KIND=harness STOP=flow REPRO=yes RISK=- SECURITY=no FILE=scripts/claude/a.sh \| 止める` と前の形の `LEDGER: F2 SEV=Low STATUS=open SCOPE=delta KIND=harness STOP=- REPRO=no RISK=- SECURITY=no \| 残り`。差分のレビューで `F1 … STATUS=open FILE=backend/x.py …` と `F2 … STATUS=open FILE=scripts/claude/a.sh LINE=10 … STOP=- \| まだ`（止めない中身） | F1 は `FILE=scripts/claude/a.sh` のまま。F2 は `FILE=scripts/claude/a.sh`（前の `-` を埋める）。新しい番号が無い | FG-Q2: `merged()` の FILE を常に今回の値にした写しで、F1 が `FILE=backend/x.py`（不合格） |
| Q3（AC3） | 前の台帳: `F2 … STATUS=resolved … FILE=scripts/claude/a.sh \| 直した`。差分のレビューで `FINDING: F2 SEV=Low STATUS=open FILE=scripts/claude/b.sh LINE=3 SECURITY=no STOP=- \| 別件`（見せていない番号 → 振り直し）。その台帳を `ledger_route backlog` | 台帳: F2 は `FILE=scripts/claude/a.sh`、F3 が `FILE=scripts/claude/b.sh \| 別件`。一覧側の出力に `- F3 SEV=Low REPRO=no KIND=harness FILE=scripts/claude/b.sh \| 別件 \| 一覧に回した理由: Low／再現なし` | （Q1・Q2 の FG で固定） |
| Q4（AC3・Risk） | 前の形の 3 種（I197 形 `LEDGER: F1 SEV=High STATUS=open SCOPE=delta SECURITY=no \| a`・I205 形〔RISK なし〕・I202 形〔FILE なし〕）と、新しい形の止める指摘 `… KIND=harness STOP=flow REPRO=yes RISK=- SECURITY=no FILE=scripts/claude/a.sh \| x` | 前の形は今までどおり読める（I197 形の High は HIGH・I205/I202 形の Low は OK）。`ledger_route backlog` で前の形の行は `FILE=-`。新しい形の止める指摘だけの台帳は `ledger_verdict` が HIGH | FG-Q4: `LEDG` から FILE の欄を除いた写しで、新しい形の行が読めず OK（不合格） |
| Q5（AC1） | `LEDGER: F1 SEV=Low STATUS=open SCOPE=delta KIND=harness STOP=- REPRO=no RISK=- SECURITY=no FILE=scripts/claude/a.sh \| 要約に KIND=app SECURITY=yes SEV=High REPRO=yes の文字` | 一覧側に F1 が出て、後続イシュー側は空 | FG-Q5: `route_reasons()` の `sec == "yes"` を「行の文字に `SECURITY=yes` がある」にした写しで、F1 が後続イシュー側（不合格） |
| Q6（AC2） | `KIND=guard` の `SEV=High REPRO=no SCOPE=outside`（F1）・`SEV=Medium REPRO=no`（F2）・`SEV=Low REPRO=yes`（F3） | 後続イシュー側が F1・F2（理由に「guard の Medium 以上」）、一覧側が F3 | FG-Q6: guard の条件を外した写しで、F1・F2 が一覧側（不合格） |
| Q7（AC6） | I206 の実物の台帳の F1〜F6 の行をテストの中に写した文字列（実物は読まない）と、代表の行（app の Low・harness の Low で SECURITY=yes・guard の High で REPRO=yes・harness の Medium で REPRO=no・guard の Low）、止める指摘（`SEV=High … STOP=flow REPRO=yes SCOPE=delta KIND=harness`）、resolved の行 | 後続イシュー: F1・F7・F8・F9・止める指摘。一覧: F2〜F6・F10・F11。resolved は出ない | FG-Q7: `SECURITY=yes` の条件を外した写しで、F8 が一覧側（不合格） |
| Q8（AC3） | 一覧側の理由の文言: `SEV=Low REPRO=no`・`SEV=Medium REPRO=no`・`SEV=Low REPRO=yes` | それぞれ `一覧に回した理由: Low／再現なし`・`再現なし`・`Low`。後続イシュー側の行は `後続イシューにする理由: ` を含む | — （出力の形の固定。不在の判定ではない） |
| Q9（AC4） | 一時のリポジトリに `docs/reviews/I900_code_review_20260101_0000.md`（`LEDGER_ROUND: 1` と台帳の行）と、後の時刻の `LEDGER_ROUND:` の無い記録を置き、`bash code-review.sh --route backlog I900` | 台帳のある記録の一覧側の行が出て exit 0、標準エラーに `記録: docs/reviews/I900_code_review_20260101_0000.md`。`--route other I900` は exit 2。引数の足りない `--route backlog` は exit 2。記録の無い `I901` は exit 2。どれも claude・gh を呼ばない | FG-Q9: 入口の `ledger_records … \| tail -1` を `head -1` にした写しは、2 つの記録のうち古い方を読むので不合格（2 つとも台帳のある記録を置いた形で確かめる） |
| D1（AC4） | `.claude/skills/retro/SKILL.md` | `bash scripts/claude/code-review.sh --route issue $ARGUMENTS`・`bash scripts/claude/code-review.sh --route backlog $ARGUMENTS`・`docs/reviews/backlog/$ARGUMENTS.md`・「最優先」・「guard」を含む。`grep -vE`・`grep -h '^LEDGER: .*STATUS=open'`・`FINDING 行（同じイシュー` を含まない | FG-D1: 写しから `--route backlog` の行を消すと不合格・前の `grep -vE` の行を足すと不合格 |
| D3（AC5） | `docs/reviews/backlog/*.md`（実物。無ければ合格）・`.claude/skills/plan-issue/SKILL.md`・`docs/runbooks/review-rules.md` | 一覧の `- F` で始まる行が、どれも `- F<n> SEV=… REPRO=… KIND=… FILE=<\S+> \| … \| (一覧に回した理由\|受け入れ): …` の形。plan-issue に「台帳の残りの一覧」と `-e "FILE=<実装対象のパス1> \|"` と `-e "FILE=- \|"`。review-rules に `code-review.sh --route` と `guard` | FG-D3: 一覧の写しに形の崩れた行（`- F9 SEV=Low FILE=x`）を足すと不合格・plan-issue の写しから `FILE=- \|` の行を消すと不合格。D3b: 一覧の写しから `- F` の行を全部消しても合格（行を消しても落ちない） |

既存の項目の照合の更新（期待の意味は変えない）:
- R1: `RISK=up SECURITY=no FILE=backend/x.py \| 目印$`
- P1: `… RISK=up SECURITY=yes FILE=backend/x.py \| 残り$`（前の `p_app` は前の形〔FILE なし＝`-`〕なので、止めない中身の合流で今回の値に埋まる）
- `f2_same [<FILE>]`: F2 の行が、前の台帳（`l6_prev`・前の形）の F2 の行の ` | ` の前に ` FILE=<FILE>`（既定 `-`）が入った形と 1 字も違わない（要約・STATUS は前のまま）。N2（書き直しが `FILE=-`）・N3（F2 は書き直さない）は `-`、P6（止めない中身の `FILE=scripts/claude/a.sh` が前の `-` を埋める）は `scripts/claude/a.sh`
- FG-P1〜P3 の置き換え前の文字列（`merged(…)` の呼び出し）に、新しい引数 `file` を足す（期待値は変えない）
- `test_i205_stop_criteria.sh` の D4・FG-D4: `grep -h '^LEDGER: .*STATUS=open'` → `bash scripts/claude/code-review.sh --route`

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i202_ledger_cleanup.sh
bash scripts/claude/tests/test_i205_stop_criteria.sh
bash scripts/claude/tests/test_i197_review_ledger.sh
bash scripts/claude/tests/test_i180_retro_triage.sh
```

## 実行記録
