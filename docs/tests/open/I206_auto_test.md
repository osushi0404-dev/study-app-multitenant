# I206 自動テスト: I202 のレビューの残り（台帳の番号の合流と、中身の無い指摘の増え方を直す）

実行コマンド（例）: アプリのコード変更が無いため `docker compose exec backend python -m pytest`・`docker compose exec frontend npm test`・E2E は非該当（CI では今までどおり動く）

結果:
- backend: 非該当
- frontend: 非該当

## テストケース

合否はすべて終了コード（合格=exit 0・不合格=非ゼロ）。否定の判定（「増えない」「合流しない」「止まらない」「残らない」）には失敗注入（FG: 本体の一時コピーの判定の要を壊すと、対応する項目が不合格になることを確かめる）を付ける。実際の claude は使わない（`CLAUDE_BIN`・PATH の `claude`・`gh` にスタブを渡す。`test_i202_ledger_cleanup.sh` の既存の R・W・A 群と同じやり方）。

| TC | 内容 | 期待値 | 結果 |
|---|---|---|---|
| TC-01 | `bash scripts/claude/tests/test_i202_ledger_cleanup.sh`（「I206」の節を足す）。下の N1〜N14 と FG、既存の R・L・W・A・G・D | exit 0・`fail=0`（ベースライン pass=72） | implement で実行（2026-10-27）: 実装前（Red）pass=82 fail=22（新しい振る舞いの項目と FG がすべて不合格・N3 は前の振り直しでも合格）→ 実装後 pass=106 fail=0（約 58 秒）。N9 は実装後も不合格だったため計画変更記録 3 で直した |
| TC-02 | 影響を受けうるテスト: `test_i197_review_ledger.sh`（299 行の置き換え前の文字列を直す・R15 の振り直し）・`test_i205_stop_criteria.sh`（`split_repro`・`blocking`）・`test_i193_official_flow.sh`（C14 の `changed_outside_records`）・`test_i197_adversarial_process.sh`（`adversarial-review.sh`） | どれも exit 0（ベースライン 2026-10-27・develop 0d8cbf3: 64・91・160・115 項目・fail=0） | implement で実行（2026-10-27）: `test_i197_review_ledger.sh` pass=64・`test_i205_stop_criteria.sh` pass=91・`test_i193_official_flow.sh` pass=160・`test_i197_adversarial_process.sh` pass=115（どれも fail=0・ベースラインと同じ件数） |
| TC-03 | `bash scripts/claude/tests/run-all.sh`（CI の Harness Tests ジョブで確かめる。手元では流し直さない） | CI の Harness Tests が pass | 実装前のため未実行 |

### TC-01 の項目（I206 の節）
一時の git リポジトリ（既存の `$R`: develop に `backend/x.py`・`scripts/claude/a.sh`・`.github/workflows/ci.yml`〔20 行ずつ〕。行の塊は各 10 行目）と、手書きの FINDING 行・台帳で確かめる。

N 台帳の更新（AC1・AC2）:
- N1（F1・AC1）: 前の台帳 F1（台帳の残り・harness・Low・`REPRO=no`）・F2（resolved）。今回のレビューが、先に `FINDING: F2 SEV=High STATUS=open FILE=scripts/claude/a.sh LINE=10 … STOP=flow | 中身 B | 再現: r`（resolved の番号の使い回し＝振り直し）、次に `FINDING: F3 SEV=High … STOP=flow | 中身 A | 再現: r`（レビュー役の新しい番号）を書く → 台帳に `F3 … | 中身 A` と `F4 … | 中身 B` の 2 行（合流しない）
- FG-N1: 振り直し先を前の台帳だけから振る形（`next_id = max([int(k[1:]) for k in led] or [0]) + 1`）に戻した写しでは、F4 が無い（合流する）
- N2（F8・AC2）: 前の台帳 F1（止める・harness・High・`STOP=flow`・`REPRO=yes`）・F2（台帳の残り・Low・`REPRO=no`）。今回のレビューが F1 を resolved、F2 を `FINDING: F2 SEV=Low STATUS=open FILE=- LINE=- SECURITY=no STOP=- | 今回の差分では直していない。`（I202 の実物の形）で書く → 台帳に F3 が無い・F2 の行が前の台帳の F2 の行と 1 字も違わない・F1 は resolved
- FG-N2: 捨てる条件（`if fid in rest_ids and st == "open" … and not blocking(fresh):`）を外した写しでは、F3（中身の無い指摘）ができる
- N3（I197-F1 の守り・AC2）: N2 と同じ前の台帳で、今回のレビューが F2 を止める中身（`SEV=High STATUS=open FILE=scripts/claude/a.sh LINE=10 … STOP=flow | 新しい穴 | 再現: r`）で書く → 新しい F3（`SEV=High STATUS=open SCOPE=delta`）・`ledger_verdict` は HIGH・F2 は前の行のまま
- FG-N3: 止める中身かを見ずに捨てる写し（`and not blocking(fresh)` を外す）では、`ledger_verdict` が OK（新しい止める指摘が消える）

N 判定の細部:
- N4（F6）: `ledger_risk`: `KIND=harness RISK=up` だけの台帳 → NO・`KIND=guard RISK=up` だけ → NO・`KIND=app RISK=up` → YES
- FG-N4: 種類の条件（`and e[3] == "app"`）を外した写しでは、harness の台帳で YES
- N5（F7）: `| 再現: なし（理由）`・`| 再現: なし。`・`| 再現: None（x）`・`| 再現: n/a: x` → `REPRO=no`。`| 再現: なしでも落ちる`・`| 再現: なし 入力 x`・`| 再現: - 入力 x` → `REPRO=yes`（既存の L3 も合格のまま）
- FG-N5: 先頭の判定（`or NO_REPRO_HEAD.match(body.casefold())`）を外した写しでは、`なし（理由）` が `REPRO=yes`
- N6（F12）: `changed_outside_records <存在しない SHA> HEAD` → 2。記録の場所だけが変わったコミット間 → 0。記録の場所の外が変わったコミット間 → 1
- FG-N6: git の出力を process substitution で読む形（今の形）に戻した写しでは、存在しない SHA で 0（fail-open）

W 本体（スタブで通し）:
- N7（F14）: gh のスタブが「PR 無し」を返す通し（`TMPDIR` を空の一時フォルダにする）→ `CI_WAIT: NO_PR`・exit 1・`TMPDIR` の中が空（一時ファイルが残らない）
- FG-N7: `trap cleanup_official EXIT` を外した写しでは、`TMPDIR` にファイルが残る
- N8（F20）: 差分のレビュー（既存の通し m の 2 周目）の入力に `### 変更ファイル一覧（差分のレビューの範囲と、取り消したファイル）` がある
- N9（F21）: 見せるファイルの一覧の作成が失敗する写し（`{ cat "$SCOPE_FILE"` を、無いファイルも読む `{ cat "$SCOPE_FILE" /nonexistent-I206` に置き換え）で差分のレビューを動かす → 出力に `⛔ 差分のレビューで見せるファイルの一覧を作れません`・`FINAL_VERDICT:` の行が無い（止まる）
- FG-N9: 同じ失敗に加えて、止める処理を `|| true` に戻した写しでは、⛔ が無く `FINAL_VERDICT:` の行が出る（握りつぶす）
- N14a（4.10）: 差分のレビューの入力の台帳の残りの節に `直していないものは書かない` があり、`この番号を open で書くと新しい指摘として振り直される` が無い

A adversarial-review.sh（claude はスタブ）:
- N10（F5）: 2 観点の実験役が鍵を取り合い、2 本目が鍵を取った時点で残りが `ADV_MIN_STEP` 以上・`2 * ADV_MIN_STEP` 未満（`ADV_DEADLINE=20`・`ADV_MIN_STEP=6`・実験役 9 秒）→ 実験役は 1 回だけ（区間 1 つ）・記録に `実行していない（締め切り）`
- FG-N10: 鍵の後の確認を `-lt "${ADV_MIN_STEP}"` に戻した写しでは、実験役が 2 回動く（区間 2 つ）
- N11（F3）: `run_perspective` の中で、`check_worktree` の呼び出しが `flock 9` の行と `} 9>"$RUN/exp.lock"` の行の間にある（鍵の中で比べる。同時に動く 2 つの実験の途中の状態は決定論で作れないので、配置で固定する）
- FG-N11: `check_worktree` を鍵の外（`} 9>"$RUN/exp.lock"` の後）へ戻した写しでは、N11 が不合格
- N12（F10）: `flock` だけを除いた PATH（`/usr/bin`・`/usr/local/bin` のコマンドへのリンクから flock を除く）で動かす → exit 2・`ADVERSARIAL_ERROR: FLOCK`
- FG-N12: 存在確認の行を外した写しでは、exit 2 にならない

D 指示ファイル:
- N13（F9）: `.claude/skills/review-gate/SKILL.md`・`docs/runbooks/workflow.md`・`docs/runbooks/review-rules.md`・`docs/runbooks/issue-flow.md`（計画変更記録 2）に `パスの判定が YES のときは` があり、`高リスク時は /security-review`・``高リスク時は `/security-review` `` が無い
- FG-N13: 各ファイルから `パスの判定が YES のときは` の行を除いた写しでは不合格
- N14b（4.10）: `.claude/agents/code-reviewer.md` に `直していないものは書かない` があり、`この番号を open で書くと新しい指摘として振り直される` が無い
- FG-N14: `直していないものは書かない` の行を除いた写しでは不合格

既存の項目の置き換え前の文字列の更新（FG の写しが作れることは既存の「FG の写しがすべて作れた」で確かめる）:
- `test_i202_ledger_cleanup.sh` FG-L3b の置き換え前の文字列を、4.4 の新しい形に合わせる
- `test_i197_review_ledger.sh` FG-R14 の置き換え前の文字列を、新しい `FILES_NOTE` に合わせる
- `test_i202_ledger_cleanup.sh` の `mixed()` の `git push` から `2>/dev/null` を外す（F23）

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i202_ledger_cleanup.sh
bash scripts/claude/tests/test_i197_review_ledger.sh
bash scripts/claude/tests/test_i205_stop_criteria.sh
bash scripts/claude/tests/test_i193_official_flow.sh
bash scripts/claude/tests/test_i197_adversarial_process.sh
```

## 実行記録
- 2026-10-27 test-gate: `bash scripts/claude/gate-check.sh I206` → exit 0（GATE_CHECK: OK）。決定論ゲート 5 本は review-gate（`docs/reviews/I206_code_review_20261027_1815.md`）で実走し、すべて exit 0。test-gate に委譲された heavy のゲートは無し。CI は Harness Tests を含む全ジョブ pass（`CI_WAIT: OK`・HEAD 3f66d57）
