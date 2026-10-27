# I207 自動テスト: 台帳の残りを捨てるときに目印・重大度が消える穴を直し、軽い指摘は後続イシューにせず一覧へ回す

実行コマンド（例）: アプリのコード変更が無いため `docker compose exec backend python -m pytest`・`docker compose exec frontend npm test`・E2E は非該当（CI では今までどおり動く）

結果:
- backend: 非該当
- frontend: 非該当

## テストケース

合否はすべて終了コード（合格=exit 0・不合格=非ゼロ）。否定の判定（「消えない」「戻らない」「落ちない」「増えない」）には失敗注入（FG: 本体の一時コピーの判定の要を壊す／指示ファイルの写しから行を消すと、対応する項目が不合格になることを確かめる）を付ける。実際の claude は使わない。

| TC | 内容 | 期待値 | 結果 |
|---|---|---|---|
| TC-01 | `bash scripts/claude/tests/test_i202_ledger_cleanup.sh`（「I207」の節を足す）。下の P1〜P6・D1〜D3 と FG、既存の R・L・W・A・G・D・N | exit 0・`fail=0`（ベースライン pass=106） | implement で実行（2026-10-27）: 実装前（Red）pass=115 fail=13（P1〜P6・D1・D3・FG-L6・FG-N2 と「FG の写しがすべて作れた」。D2 は正規表現だけの確認なので実装前でも合格）→ 実装後 pass=128 fail=0。P3・P4・P6 の入力は計画変更記録 2 で直した |
| TC-02 | 影響を受けうるテスト: `test_i205_stop_criteria.sh`（D4: retro の拾うコマンドと「最優先」）・`test_i197_review_ledger.sh`（台帳の更新）・`test_i180_retro_triage.sh`（retro の文言） | どれも exit 0（ベースライン 2026-10-27・develop 8b8c923: pass=91・pass=64・13/13） | implement で実行（2026-10-27）: pass=91・pass=64・13/13（fail=0）。文言を読むほかのテスト 7 本（i193・i181・i185・i114・i182_docs・i179・adversarial_trigger）も `TEST_DIR` で選んで流し、すべて合格 |
| TC-03 | `bash scripts/claude/tests/run-all.sh`（CI の Harness Tests ジョブで確かめる。手元では流し直さない） | CI の Harness Tests が pass | review-gate で確認（2026-10-27）: `CI_WAIT: OK`（Harness Tests を含む全ジョブ pass・HEAD 538aa78） |

### TC-01 の項目（I207 の節）
一時の git リポジトリ（既存の `$R`: `backend/x.py`・`scripts/claude/a.sh`・`.github/workflows/ci.yml`〔20 行ずつ〕。行の塊は各 10 行目）と、手書きの FINDING 行・台帳で確かめる。前の台帳は次の 2 つを使う。
- `p_app`: `LEDGER: F2 SEV=Low STATUS=open SCOPE=outside KIND=app STOP=- REPRO=yes RISK=- SECURITY=no | 残り`（台帳の残り）
- `l6_prev`（既存）: `F1 SEV=High … KIND=harness STOP=flow REPRO=yes`（止める）・`F2 SEV=Low STATUS=open SCOPE=delta KIND=harness STOP=- REPRO=no`（台帳の残り）

| 項目 | 入力 | 期待値 | FG（失敗注入） |
|---|---|---|---|
| P1（F1・AC1） | 前 `p_app`。`FINDING: F2 SEV=Medium STATUS=open FILE=backend/x.py LINE=15 SECURITY=yes STOP=- RISK=up \| 書き直し \| 再現: r`（行 15 は塊〔10±3〕の外＝outside・止めない中身） | 台帳に `F3` が無い。F2 は `SEV=Medium STATUS=open SCOPE=outside KIND=app … REPRO=yes RISK=up SECURITY=yes \| 残り`（要約は前のまま）。`ledger_risk` が YES・`ledger_verdict` が OK | FG-P1: 合流の行 `led[fid] = merged(o, sev, o[1], stop, repro, sec, o[7], risk)` を `pass` にすると、F2 が `RISK=-`・`ledger_risk` が NO（P1 が不合格） |
| P2（F2・AC2） | 前 `l6_prev`。同じ回に `F2 … STATUS=resolved \| 直した` → `F2 SEV=Low STATUS=open FILE=scripts/claude/a.sh LINE=10 SECURITY=no STOP=- \| まだ` | F2 は `STATUS=resolved`（要約は `直した`）。`F3` が無い | FG-P2: 合流の `o[1]` を `st` にすると、F2 が `STATUS=open`（P2 が不合格） |
| P3（I197-F1 の守り・AC1） | 前 `l6_prev`。同じ回に `F1 … STATUS=resolved`・`F2 … STATUS=resolved \| 直した` → `F2 SEV=High STATUS=open FILE=scripts/claude/a.sh LINE=10 SECURITY=no STOP=flow \| 新しい穴 \| 再現: r` | F2 は `STATUS=resolved`。新しい `F3 SEV=High STATUS=open SCOPE=delta`。`ledger_verdict` が HIGH | FG-P3: resolved の扱いの `continue` の前に `seen.add(fid)` を足すと（前の `seen` の近道に戻す）、F3 が無い（P3 が不合格） |
| P4（AC1） | 前 `l6_prev`。同じ回に `F2 SEV=High STATUS=open … STOP=flow \| 新しい穴 \| 再現: r` → `F2 … STATUS=resolved \| 直した` | F2 は `STATUS=resolved`。`F3 SEV=High STATUS=open`（resolved にならない）。`ledger_verdict` が HIGH | FG-P4: resolved の分岐の前に、振り直した番号なら `fid = remap[fid]` にする行を足すと（振り直し先に付く前の形）、F3 が resolved・OK（P4 が不合格） |
| P5（合流は止める側に倒れる・AC1） | 前 `LEDGER: F2 SEV=Low STATUS=open SCOPE=delta KIND=harness STOP=- REPRO=yes RISK=- SECURITY=no \| 残り`。`FINDING: F2 SEV=Low STATUS=open FILE=scripts/claude/a.sh LINE=10 SECURITY=no STOP=flow \| 書き直し`（再現なし＝止めない中身） | `F3` が無い。F2 は `STOP=flow REPRO=yes`・`ledger_verdict` が HIGH | （P1 の FG と同じ合流の行。FG-P5: 合流の行を `pass` にすると OK） |
| P6（同じ回の順序・AC1） | 前 `l6_prev`。同じ回に `F2 SEV=High STATUS=open … STOP=flow \| 新しい穴 \| 再現: r` → `F2 SEV=Low STATUS=open FILE=scripts/claude/a.sh LINE=10 SECURITY=no STOP=- \| まだ` | `F3 SEV=High STATUS=open`（止める・`\| 新しい穴`）。F2 は前の行のまま（`STATUS=open`・`\| 残り`）。`F4` が無い。`ledger_verdict` が HIGH | FG-P6: 止めない中身の分岐に `and fid not in remap` を足して 2 行目を振り直し先へ流すと、F3 の要約が `まだ` になる（P6 が不合格） |
| D1（AC3） | `.claude/skills/retro/SKILL.md` | 次をすべて含む: `grep -h '^LEDGER: .*STATUS=open'`・振り分けの正規表現 `KIND=app\|SECURITY=yes\|SEV=(Blocker\|High\|Medium) .*REPRO=yes` を `grep -E` と `grep -vE` の両方で使う行・`docs/reviews/backlog/$ARGUMENTS.md`・「最優先」。「まとめて 1 か所に振り分ける」を含まない | FG-D1: 写しから `grep -vE` の行を消すと不合格・`docs/reviews/backlog/` の行を消すと不合格 |
| D2（AC3・C8） | D1 の正規表現（テストに持つ文字列＝retro に書いた文字列）を、I206 の実物の台帳の F1〜F6（`docs/reviews/closed/I206_code_review_20261027_1815.md` の LEDGER 行）と代表の行に当てる | 後続イシュー: I206 F1（Medium・REPRO=yes）・`KIND=app` の Low・`KIND=harness` の Low で `SECURITY=yes`・`KIND=guard` の High で `REPRO=yes`。一覧: I206 F2〜F6・`KIND=harness` の Medium で `REPRO=no`・`KIND=guard` の Low | FG-D2: 正規表現から `SECURITY=yes\|` を除くと、SECURITY=yes の Low が一覧に落ちる（不合格） |
| D3（AC4） | `docs/reviews/backlog/I206.md`・`.claude/skills/plan-issue/SKILL.md`・`docs/runbooks/review-rules.md` | 一覧に F3〜F6 の行（`- F<n> SEV=… FILE=…` で `受け入れ:` を含む）が 4 行あり、F1・F2 の行が無い。plan-issue に「台帳の残りの一覧」と `grep -rnF -e "FILE=` と `docs/reviews/backlog/`。review-rules に `docs/reviews/backlog/` | FG-D3: plan-issue の写しから `docs/reviews/backlog/` の行を消すと不合格・一覧の写しから F6 の行を消すと不合格 |

既存の項目の置き換え前の文字列の更新（FG の写しが作れることは既存の「FG の写しがすべて作れた」で確かめる。期待値は変えない）:
- FG-L6: `keep = fid in seen or fid in shown or (fid in rest_ids and st == "resolved")` → 新しい形（台帳の残りの resolved の扱いを外す置き換え）
- FG-N2: 捨てる条件の行 → 新しい「止めない中身」の分岐を外す置き換え
- FG-N3: 「止める中身かを見ずに捨てる」置き換え → 新しい分岐の `if not blocking(fresh):` を `if True:` にする

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i202_ledger_cleanup.sh
bash scripts/claude/tests/test_i205_stop_criteria.sh
bash scripts/claude/tests/test_i197_review_ledger.sh
bash scripts/claude/tests/test_i180_retro_triage.sh
```

## 実行記録
- 2026-10-27 test-gate: `bash scripts/claude/gate-check.sh I207` → exit 0（GATE_CHECK: OK）。決定論ゲート 4 本は review-gate（`docs/reviews/I207_code_review_20261027_1942.md`）で実走し、すべて exit 0。test-gate に委譲された heavy のゲートは無し。CI は Harness Tests を含む全ジョブ pass（`CI_WAIT: OK`）
