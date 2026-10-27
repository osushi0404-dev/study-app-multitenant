# I205 自動テスト: レビューで止める基準を変更の種類で分ける・差分の中かどうかを行で決める

実行コマンド（例）: アプリのコード変更が無いため `docker compose exec backend python -m pytest`・`docker compose exec frontend npm test`・E2E は非該当（CI では今までどおり動く）

結果:
- backend: 非該当
- frontend: 非該当

## テストケース

合否はすべて終了コード（合格=exit 0・不合格=非ゼロ）。否定の判定（「止まらない」「合格になる」「範囲の外」）には失敗注入（FG: `code-review.sh` の一時コピーの判定の要を壊すと、対応する項目が不合格になることを確かめる）を付ける。実際の claude は使わない（`CLAUDE_BIN` にスタブを渡す。`test_i197_review_ledger.sh` の R14 と同じやり方）。

| TC | 内容 | 期待値 | 結果 |
|---|---|---|---|
| TC-01 | `bash scripts/claude/tests/test_i205_stop_criteria.sh`（新設）。下の H・L・K・B・W・D の各項目と FG | exit 0・`fail=0` | implement で実行: pass=78 fail=0（2026-10-27）。計画変更記録 2 の実装後: pass=86 fail=0（H7〜H9・B7 の追加・FG-H7〜H9 を含む。手元の git 2.43.0。CI でも確かめる） |
| TC-02 | `bash scripts/claude/tests/test_i197_review_ledger.sh`（FINDING 行を新しい形に付け替え。項目の意味は変えない。R11 の語を新しい決まりに付け替え） | exit 0・`fail=0`（ベースライン pass=64 fail=0） | implement で実行: pass=64 fail=0 |
| TC-03 | 影響を受けうるテスト: `bash scripts/claude/tests/test_adversarial_trigger.sh`・`test_i114_retro_plain_output.sh`・`test_i180_retro_triage.sh`・`test_i181_review_slim.sh`・`test_fix_review.sh`・`test_i193_official_flow.sh`・`test_i185_harness_docs.sh`・`test_i197_adversarial_process.sh`・`test_i182_docs.sh`・`test_review_verdict.sh` | どれも exit 0 | implement で実行: すべて exit 0（`test_fix_review.sh` の TC-22・TC-26 と `test_i193_official_flow.sh` の S19 は語を付け替えた後） |
| TC-04 | `bash scripts/claude/tests/run-all.sh`（CI の Harness Tests ジョブで確かめる。手元では流し直さない） | CI の Harness Tests が pass | OK: review-gate の CI 待ちで Harness Tests を含む全ジョブが pass（`CI_WAIT: OK`・HEAD 7f3167e） |

## 再発防止記録（fix-loop・F11・2026-10-27）
- なぜ失敗したか: git は空白を含むパスの `+++ b/<パス>` の行末にタブを付ける。塊を読む処理がそのタブをパスに含め、塊の行が 4 列になり、台帳の作成（3 列と決めつけた読み方）が落ちて、レビューが毎回 BLOCKER になりえた（診断: `docs/reviews/I205_fix_diagnosis_20261027_1320.md`）
- 何を変えたか: `_HUNKS_PY` で行末のタブを取り除いた。`ledger_update` は塊の行を後ろから 2 列で読む（パスにタブが入っても落ちない）
- セキュリティ: 関係しない（止まる向きの崩れ）
- 次回どう防ぐか: TC-01 の H10（空白を含むパス・4 列の行）と FG-H10・FG-H10b で固定
- 確かめた結果: `bash scripts/claude/tests/test_i205_stop_criteria.sh` → pass=90 fail=0。`bash scripts/claude/tests/test_i197_review_ledger.sh` → pass=64 fail=0

## 実行記録
- 2026-10-27 review-gate（`code-review.sh` の決定論ゲート実走・HEAD 7f3167e）: 「## 決定論ゲート（自動実走）」の 12 本すべて exit=0（heavy で test-gate に委譲したものは無い）。記録 `docs/reviews/I205_code_review_20261027_1123.md`
- 2026-10-27 test-gate: `bash scripts/claude/gate-check.sh I205` → exit 0（GATE_CHECK: OK）
- 2026-10-27 review-gate 3 周目（HEAD 6e58f73・計画変更記録 2 と F11 の修正の後）: 決定論ゲート 12 本すべて exit=0・CI 全ジョブ pass。記録 `docs/reviews/I205_code_review_20261027_1322.md`
- 2026-10-27 test-gate（2 回目）: `bash scripts/claude/gate-check.sh I205` → exit 0（GATE_CHECK: OK）

### TC-01 の項目
一時の git リポジトリ（develop に `backend/x.py`〔20 行〕・`scripts/claude/a.sh`〔20 行〕・`Docs/up.md`〔大文字の場所。casefold の確認用〕を置き、feature ブランチで行を変える）と、手書きの FINDING 行・台帳で確かめる。

H `delta_hunks`（行の塊）:
- H1 既存のファイルの 10 行目を変え、15 行目の後に 2 行足す → `backend/x.py\t10\t10` と `backend/x.py\t16\t17`
- H2 5 行目を消しただけ → `\t4\t4`（消した位置の 1 行）
- H3 新しいファイル（3 行）→ `\t1\t3`
- H4 バイナリのファイルを変えた → `\t1\t999999999`
- H5 差分のレビュー（起点あり）: 起点の後に develop を取り込んで入った行は塊に入らない。起点の後にブランチが変えた行だけが入る
- H6 全体のレビュー（起点なし）: merge-base からブランチが変えた行だけ（develop 側だけの変更は入らない）
- H7（計画 4.11・F1）一時のリポジトリに `git config diff.noprefix true` と `diff.mnemonicPrefix true` を設定しても、H1 と同じ塊（`backend/x.py\t10\t10`）が出る
- H8（4.11・F6）中身が `++ /dev/null` の行（diff では `+++ /dev/null`）と `-- a` の行を足したファイルでも、そのファイルの塊が消えず、足した行が塊に入る
- H9（4.11・F2）`hunks_from_diff` に、対象のファイル `a.txt`・`b.txt` と、`a.txt` だけの塊を含む diff を渡す → `b.txt\t1\t999999999` が出る。差分のレビュー（diff を 2 つ）で、両方に出て重なりが無いファイルは塊なしのまま

L 行で決める範囲（`ledger_update` の SCOPE）:
- L1 塊（10〜10）の中の行 `LINE=10` → delta
- L2 塊の後ろ 3 行（`LINE=13`）→ delta。4 行（`LINE=14`）→ outside
- L3 範囲 `LINE=1-9`（塊の 3 行前の 7 行目と重なる）→ delta
- L4 `LINE=-` → delta。`LINE=abc` → delta（読めない行は止める側）
- L5 `FILE=-` → delta
- L6 ブランチで触っていない行（`LINE=1`）でも `STOP=ac:2` → delta
- L7 範囲の外のファイル（ブランチが変えていない実在のファイル）→ outside。リポジトリに無いパス・リポジトリの外 → delta
- L8 casefold（F16）: 範囲が `docs/up.md`（小文字）で、実在のファイルが `Docs/up.md` のとき、`FILE=Docs/up.md LINE=<塊の行>` → delta
- L9 全体のレビュー（1 周目）でも、ブランチが変えたファイルの触っていない行の指摘は outside

K 変更の種類（`kinds` モード）:
- K1 `backend/x.py`・`frontend/src/a.tsx`・`e2e/a.spec.ts`・`docker-compose.yml`・`README.md`・`scripts/db_backup.sh`・`nginx/a.conf` → app。`.claude/skills/x/SKILL.md`・`.claude/agents/x.md`・`scripts/claude/x.sh`・`docs/runbooks/x.md`・`rules/x.md`・`CLAUDE.md`・`.mcp.json`・`.worktreeinclude` → harness。`.github/workflows/ci.yml`・`.github/CODEOWNERS`・`.pre-commit-config.yaml`・`.secrets.baseline`・`scripts/claude/hooks/pretooluse_guard.py`・`.claude/settings.json`・`.claude/settings.local.json` → guard
- K2 guard の集合と `path_risk_trigger()` が一致: K1 の全パスについて「`path_risk_trigger` が YES」⇔「種類が guard」
- K3 `FILE=-` の種類: ブランチが guard のファイルを変えていれば guard、無くて app があれば app、どちらも無ければ harness

B 止める基準（`ledger_verdict`・`ledger_blocking`。SCOPE は L のとおりに決まる行で作る）:
- B1 app・High・delta・再現あり → HIGH
- B2 app・Medium・delta・再現あり → HIGH
- B3 app・Low・delta・再現あり → OK
- B4 app・Medium・outside・再現あり → OK（台帳に `STATUS=open SCOPE=outside` で残る）
- B5 app・High・delta・再現なし → OK（台帳に残る）
- B5b app・`SEV=Low STOP=ac:1`・触っていない行・再現あり → HIGH（受け入れ条件の未達は重大度に関係なく止める）
- B6 app・Blocker・SECURITY=yes・outside・再現あり → BLOCKER
- B7 app・Blocker・SECURITY=yes・outside・再現なし → OK。台帳に `SECURITY=yes`・`STATUS=open` で残る（retro 4-0 が拾い、後続のイシューで最優先になる）
- B8 harness・`SEV=Low STOP=flow`・delta・再現あり → HIGH（重大度を見ない）
- B9 harness・`SEV=High STOP=-`・delta・再現あり → OK（台帳に残る）
- B10 harness・`STOP=flow`・delta・再現なし → OK
- B11 harness・`STOP=ac`（番号なし）・`STOP=other`・delta・再現あり → OK
- B12 harness・`STOP=ac:3`・触っていない行・再現あり → HIGH。`STOP=leak`・`STOP=github` も delta・再現ありで HIGH
- B13 harness・Blocker・SECURITY=yes・`STOP=-`・outside・再現あり → BLOCKER
- B14 guard・High・delta・再現なし → HIGH。guard・Medium → OK
- B15 書き直し: 前の周で `STOP=flow REPRO=yes` の open の指摘を、同じ番号で `STOP=-`・再現なしの open に書き直しても、止める指摘のまま（HIGH）
- B16 前の形（I197 の形・KIND などの欄なし）の台帳の行 `LEDGER: F1 SEV=Medium STATUS=open SCOPE=delta SECURITY=no | m` → 止める側の既定値（app・`STOP=-`・`REPRO=yes`）で読み、HIGH
- B17 `ledger_blocking` の出力が、`ledger_verdict` が数えた止める指摘と同じ番号の集合

W 本体の通し（gh・claude はスタブ）:
- W1 アプリ本体の全体のレビュー: スタブの code-reviewer が `VERDICT: OK` を書き、FINDING 行は `FILE=a.py LINE=<ブランチが変えた行> SEV=Medium … | m | 再現: x` → `FINAL_VERDICT: HIGH`（LLM の VERDICT を合否に使わない）
- W2 全体のレビュー: スタブが `VERDICT: HIGH` を書き、FINDING 行は Low だけ → `FINAL_VERDICT: OK`
- W3 W1 の記録に `## 止める指摘（スクリプトが決めた` の節と、その下に `LEDGER: F1`。台帳の行に `KIND=app`
- W4 code-reviewer への入力に `変更の種類` の節があり、`app` と `a.py` が同じ行にある
- W5 全体のレビューで `VERDICT: HIGH` なのに読める FINDING 行が無い → `FINAL_VERDICT: BLOCKER`
- W6 ハーネスの通し（変えたファイルが `scripts/claude/h.sh`）: 1 周目で `STOP=-` の High（再現あり）だけ → `FINAL_VERDICT: OK`、台帳に `KIND=harness` で残る

D 指示ファイル（静的）:
- D1 `.claude/agents/code-reviewer.md` に `LINE=`・`STOP=`・`| 再現:`・`flow`・`leak`・`github`・`ac:` があり、`## コード品質・セキュリティ指摘` の見出しが無い
- D2 `.claude/skills/review-gate/SKILL.md` に `最後の安全網` と `止める指摘（スクリプトが決めた` と、§3-2 のアプリ本体の Medium の扱い（`イシューに関係する Medium`）がある
- D3 `.claude/skills/fix-loop/SKILL.md` に `止める指摘（スクリプトが決めた` があり、`止める指摘（Blocker・High）` が無い
- D4 `.claude/skills/retro/SKILL.md` に `grep -h '^LEDGER: .*STATUS=open'` と `最優先` がある
- D5 `docs/runbooks/review-rules.md` に `関所の穴` と `最後の安全網` があり、`止めるのは High 以上だけ` が無い

FG（失敗注入。一時コピーを壊すと、その項目が不合格になる）:
- FG-B5 再現の検査（`if repro != "yes"`）を消す → B5 が HIGH になる
- FG-B6 差分の外のセキュリティの Blocker の扱いを消す → B6 が OK になる
- FG-B8 ハーネスを重大度で決める形（`RANK[sev] >= 2`）に戻す → B8 が OK になる
- FG-B11 STOP の検査を「何でも当たる」にする → B11 が HIGH になる
- FG-L2 前後の行数を 0 にする → L2 の 13 行目が outside になる
- FG-L8 casefold を外す → L8 が outside になる
- FG-L9 全体のレビューで範囲を作らない（今の `in_scope is None` の形に戻す）→ L9 が delta になる
- FG-K1 harness の場所の一覧から `.claude/` を外す → K1 の `.claude/skills/x/SKILL.md` が app になる
- FG-W2 全体のレビューで LLM の VERDICT を合否に使う形に戻す → W2 が HIGH になる
- FG-H7 `--src-prefix=a/ --dst-prefix=b/` を外す → H7 で塊が出ない
- FG-H8 見出しを読むのを最初の `@@` までに限る判定を外す → H8 でそのファイルの塊が消える
- FG-H9 読めなかった対象のファイルをファイル全体にする処理を外す → H9 で `b.txt` が出ない
- FG-D1〜D5 対象のファイルの写しから語を 1 つ消す → その D が不合格

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i205_stop_criteria.sh
bash scripts/claude/tests/test_i197_review_ledger.sh
bash scripts/claude/tests/test_adversarial_trigger.sh
bash scripts/claude/tests/test_i114_retro_plain_output.sh
bash scripts/claude/tests/test_i180_retro_triage.sh
bash scripts/claude/tests/test_i181_review_slim.sh
bash scripts/claude/tests/test_fix_review.sh
bash scripts/claude/tests/test_i193_official_flow.sh
bash scripts/claude/tests/test_i185_harness_docs.sh
bash scripts/claude/tests/test_i197_adversarial_process.sh
bash scripts/claude/tests/test_i182_docs.sh
bash scripts/claude/tests/test_review_verdict.sh
```
