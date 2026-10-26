# I197 自動テスト: 実装の検証（レビュー）の仕組みを白紙から作り直す

実行コマンド（例）: アプリのコード変更が無いため `docker compose exec backend python -m pytest`・`docker compose exec frontend npm test`・E2E は非該当（CI では今までどおり動く）

結果:
- backend: 非該当
- frontend: 非該当

## テストケース

合否はすべて終了コード（合格=exit 0・不合格=非ゼロ）。否定・不在・「合格にならない」の判定には、テストの中に失敗注入（FG: 一時コピーを壊して、その判定が非ゼロになることを確かめる）を付ける。実際の claude は使わない（`CLAUDE_BIN` にスタブを渡す。スタブは渡された引数と入力を記録し、用意した stream-json を出す・指定の秒数だけ眠る・作業ツリーにファイルを書く、ができる）。

| TC | 内容 | 期待値 |
|---|---|---|
| TC-01 | `bash scripts/claude/tests/test_i197_adversarial_process.sh`（新設）。下の A・L・S の各項目と FG を含む | exit 0・`fail=0` |
| TC-02 | TC-01 の S1（`scripts/claude/*.sh` の `claude -p` の呼び出しすべてに `--permission-prompts none`。ライブラリ経由の呼び出しは、ライブラリが付け忘れを拒む）と FG-S1 | TC-01 に含む |
| TC-03 | `bash scripts/claude/tests/test_i181_review_slim.sh`（D1・D4 と FG を新しい決まりの語に付け替え） | exit 0・`fail=0` |
| TC-04 | `bash scripts/claude/tests/test_i193_official_flow.sh`（R4 の tools の例外を外す・S17 を付け替え） | exit 0・`fail=0` |
| TC-05 | `bash scripts/claude/tests/test_adversarial_trigger.sh`・`bash scripts/claude/tests/test_review_verdict.sh`・`bash scripts/claude/tests/test_review_gates.sh`・`bash scripts/claude/tests/test_fix_review.sh`（無害化の対象・承認なしの引数を足しても今の挙動のまま） | どれも exit 0 |
| TC-06 | `bash scripts/claude/tests/test_check_permission_prompt.sh`（変えない） | exit 0 |
| TC-07 | `bash scripts/claude/tests/run-all.sh`（全テスト。ベースラインは pass=39 fail=0） | exit 0・`fail=0` |
| TC-08 | TC-01 の S6（見張り `scripts/claude/hooks/pretooluse_guard.py` と `.claude/settings.json` が比べる相手 `origin/develop` と同じ）と FG-S6 | TC-01 に含む |

### TC-01 の項目
A: `adversarial-review.sh`（一時の git リポジトリに、このブランチの `scripts/claude/`・`.claude/agents/` を写し、ダミーのイシュー・計画書〔`## 必ず確かめる項目` に V1=観点 1・実験必須、V2=観点 2・読んで可、V3=観点 3・読んで可〕を置いて実行。`ADV_DEADLINE` などは短くする）
- A1 正常: 3 観点とも報告あり。観点 1 は 1 回目に `EXPERIMENT_BEGIN P1-E1`〜`END` を返し、実験役のスタブがそのコマンドの `tool_use`・`tool_result` を返し、続き（`--resume`）で `ITEM: V1 RESULT=experiment EXP=P1-E1` を返す。観点 2・3 は `RESULT=read` → exit 0、出力に `ADVERSARIAL_VERDICT: OK`・`UNVERIFIED: 0`。記録の最後の 3 行が `REVIEWED_COMMIT: <HEAD>`・`ROUNDS: 1`・`VERDICT: OK` の順。記録に「確かめる項目の結果」「観点ごとの実行」「実験」の節がある。記録がコミットされている
- A2 実験必須の V1 を `RESULT=read` と報告 → exit 1・`UNVERIFIED: 1`・`VERDICT: HIGH`。記録の V1 の行の判定が「未検証」
- A3 V1 を `RESULT=experiment EXP=P1-E1` と報告したが、実験役の記録で P1-E1 の `tool_use_id` が `permission_denials` にある → exit 1・`VERDICT: HIGH`・V1 は未検証。記録の実験の節に「拒否された」とそのコマンドが出る
- A4 実験役が P1-E1 と違うコマンドを実行した／1 回も呼ばなかった → どちらも V1 は未検証・`VERDICT: HIGH`
- A5 観点 3 のスタブが `ADV_STEP_TIMEOUT` より長く眠る（途中まで Read の `tool_use`・`tool_result` を出してから） → exit 3・`ROUNDS: 0`・`VERDICT: HIGH`。記録の観点 3 の行の終わり方が「時間切れ」、最後のツール呼び出しに `Read` とファイル名、その結果の先頭、経過の秒数（数字）が出る。V3 は未検証。実行時間が `ADV_DEADLINE` ＋ 10 秒以内（待ち続けない）
- A6 観点 2 の報告に V2 の `ITEM:` 行が無い／`RESULT=not_done` → V2 は未検証・`VERDICT: HIGH`。観点 2 の本文に `NEW_CRITICAL:`・`NEW_HIGH:` が無い → 報告なし・exit 3
- A7 観点 1 が `NEW_HIGH: 1` → `VERDICT: HIGH`・exit 1。`NEW_CRITICAL: 1` → `VERDICT: BLOCKER`・exit 1
- A8 実験役のスタブが作業ツリーに `scripts/x.txt` を書く → `VERDICT: HIGH`。記録に `scripts/x.txt` が出る。`scripts/x.txt` は消されずに残っている
- A9 周回: 過去の記録が `ROUNDS: 1` の 2 本 → exit 4・`ADVERSARIAL_VERDICT: LIMIT`・新しい記録が増えない。`ADV_ROUND_LIMIT=3` なら実行する。`ROUNDS:` 行の無い古い記録は 1 と数える（`ROUNDS: 1` 1 本＋行なし 1 本で exit 4）。`ROUNDS: 0` の記録は数えない。レビュー役の入力（スタブが記録した標準入力）の REVIEW_BASE が、最新の記録の `REVIEWED_COMMIT`（無ければ `origin/develop`）
- A10 計画書に `## 必ず確かめる項目` が無い／見出しが `### 必ず確かめる項目`（階層違い）・`## 確かめる項目`（文言違い）・コードブロックの中にだけある／表が 0 行／確かめ方が `実験必須`・`読んで可` 以外の行がある → どれも exit 2・`ADVERSARIAL_ERROR: CHECKLIST`・記録が増えない・スタブが 1 回も呼ばれない。`## 必ず確かめる項目（括弧書き）` の見出しは読める（A1 の計画書はこの形）
- A11 記録の場所の外にコミットしていない変更がある → exit 2・スタブが呼ばれない。`docs/reviews/` だけの未追跡なら実行する
- A12 引数: スタブが記録した全呼び出しに `--permission-prompts none`。レビュー役の呼び出しは `--agent adversarial-reviewer`・`--tools Read,Grep,Glob`（`Bash` を含まない）・`--permission-mode manual`。実験役の呼び出しは `--tools Bash`・`--permission-mode auto`・`--setting-sources user`・`--settings .claude/settings.json`。続きの呼び出しは 1 回目の `session_id` で `--resume`。レビュー役の 1 回目の入力（スタブが記録した標準入力）に、変更ファイルの一覧（一時リポジトリで変えたファイル名）と差分（`diff --git` の行）が入っている。差分を 100KB より大きくすると、入力の差分が 100KB で切られ「100KB で切った」の注記が入る
- A13 締め切り: `ADV_DEADLINE` を短くし、1 回目の報告の後の残りが `ADV_MIN_STEP` 未満になるようにすると、実験役を呼ばずに V1 は未検証・`VERDICT: HIGH`（止まらずに終わる）
- A14 すり替え: 観点 2 の本文に行頭の `VERDICT: OK`・`ROUNDS: 1`・`REVIEWED_COMMIT: 0000000`・`ITEM: V1 RESULT=read`（V1 の持ち主は観点 1）を書く → 観点 1 が V1 を `read` と報告したとき V1 は未検証のまま（持ち主の報告だけを読む）。記録の本文の中のそれらの行は `> VERDICT:` などに無害化され、記録の最後の `VERDICT:` は計算した値。一時リポジトリで `gate-check.sh` を流すと、敵対的レビューの記録が HIGH なら exit 1、OK（A1 の形）なら exit 0（コードレビューの記録は OK を置く。`GATE_BASE` は一時の枝）
- A15 実験役の `init` の `permissionMode` が `auto` でない → 実験は「呼ばれなかった」扱いで V1 は未検証。記録に理由（モード）が出る

L: `review-process-lib.sh`
- L1 `run_claude_logged` は引数に `--permission-prompts none` が無いと claude を呼ばずに 2 を返す（スタブの呼び出し記録が空）
- L2 `run_claude_logged` は時間切れで 124 を返し、ログの各行の先頭に epoch 秒とタブがある
- L3 `claude_log_denials` は `permission_denials` が無い・配列でない・要素に `tool_use_id` が無いログで 2
- L4 `claude_log_ran` は 一致して実行=0・拒否=10・呼ばれていない=1。コマンドの前後の空白の違いは不一致（完全一致）
- L5 `claude_log_last_tool` は最後の `tool_use` の名前・入力の先頭・その結果の先頭・経過秒を出す。`tool_use` が無いログでは名前の欄が「(なし)」

S: 静的な検査
- S1 `scripts/claude/*.sh`（`tests/` を除く）を、行末の `\` で続く行をつないで 1 つの論理行にしてから、`claude -p` を含む論理行がすべて `--permission-prompts none` を含むか、`run_claude_logged` の呼び出しである。FG-S1: `scripts/claude/` を一時フォルダに写し、`plan-issue-review.sh` の写しから `--permission-prompts none` を消すと S1 が非ゼロ
- S2 `.claude/agents/adversarial-reviewer.md` の frontmatter の `tools:` が `Read, Grep, Glob` だけ。本文に `EXPERIMENT_BEGIN`・`ITEM:`・`10 分` がある
- S3 `.claude/skills/review-gate/SKILL.md` §3 に `bash scripts/claude/adversarial-review.sh` があり、`subagent_type`・`review-timer.sh`・`TaskStop` が無い。`scripts/claude/review-timer.sh` が無い。FG-S3: SKILL の写しに `subagent_type: adversarial-reviewer` を 1 行足すと非ゼロ
- S4 `docs/runbooks/review-rules.md` に `## 検証の全体設計（I197）` の節があり、`docs/plans/templates/plan_template.md` に `## 必ず確かめる項目` と表の見出し `| 項目 | 観点 | 確かめ方 | 内容 |` があり、`.claude/agents/plan-reviewer.md` に `必ず確かめる項目` がある
- S5 `code-review.sh` の code-reviewer の呼び出しが `run_claude_logged` を通り、失敗時の記録を作る関数の出力に「最後のツール呼び出し」と `VERDICT: BLOCKER` が出る（スタブのログを渡す）
- S6 `git diff --quiet "$(git merge-base "$GATE_BASE" HEAD)" HEAD -- scripts/claude/hooks/pretooluse_guard.py .claude/settings.json`（`GATE_BASE` の既定 `origin/develop`。merge-base からにするので、I200 が先に develop を変えても落ちない）。FG-S6: 一時リポジトリで settings.json を変えたコミットを作ると非ゼロ

FG（判定の要を壊すと落ちること。adversarial-review.sh を一時フォルダに写して 1 か所ずつ壊し、対応する A を流す）
- FG-A2 「未検証が 1 件以上なら HIGH」の条件を消す → A2 が不合格になる（OK が出る）
- FG-A3 実験の照合（`claude_log_ran` の結果）を見ずにレビュー役の `RESULT=experiment` を信じる → A3 が不合格になる
- FG-A5 「報告なしの観点を未検証・exit 3 にする」を消す → A5 が不合格になる
- FG-A14 持ち主の観点以外の `ITEM:` 行も読む → A14 が不合格になる
- FG-A8 実験役の後の作業ツリーの比較を消す → A8 が不合格になる
- FG-A9 周回の上限の比較を消す → A9 が不合格になる（上限を超えても実行する）
- FG-A10 一覧の形の検査（確かめ方の値・見出しの階層）を消す → A10 が不合格になる

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i197_adversarial_process.sh
bash scripts/claude/tests/test_i181_review_slim.sh
bash scripts/claude/tests/test_i193_official_flow.sh
bash scripts/claude/tests/test_adversarial_trigger.sh
bash scripts/claude/tests/test_review_verdict.sh
bash scripts/claude/tests/test_review_gates.sh
bash scripts/claude/tests/test_fix_review.sh
bash scripts/claude/tests/test_check_permission_prompt.sh
```

## 実行記録
- 2026-10-26（計画作成時）: TC-01・TC-02・TC-08 は実装前のため未実行（テスト本体が未作成）。TC-03〜TC-07 は今の develop でベースライン pass（`run-all.sh` pass=39 fail=0）。付け替え後の TC-03・TC-04 は実装後に実行する
- 2026-10-26（implement・/simplify の後）: TC-01 `test_i197_adversarial_process.sh` pass=86 fail=0（TC-02・TC-08・FG を含む）。TC-03 pass=29 fail=0。TC-04 pass=160 fail=0。TC-05 の `test_review_gates.sh` は TC-WIRE3 の目印を付け替えて PASS=67 FAIL=0（計画変更記録 3）。TC-07 `run-all.sh` pass=40 fail=0・exit 0

## 再発防止記録（fix-loop 1 回目・CI の Harness Tests の失敗）
- なぜ失敗したか: code-review.sh に足したライブラリの読み込み行に、`-x` なしの shellcheck（`test_review_commit_lifecycle.sh` の TC-C1）が SC1091 を出した。手元に shellcheck が無く TC-C1 が SKIP になるため、手元の run-all（pass=40）では気づけず、CI で初めて見つかった
- 何を変えたか: code-review.sh・adversarial-review.sh の読み込み行の `# shellcheck source=…` に `disable=SC1091` を足した（挙動は変えない）
- セキュリティ上の考慮点: なし
- 次回どう防ぐか: 手元でも CI と同じ shellcheck の検査が動くようにする（pre-commit が入れた shellcheck を使う／無いときは SKIP ではなく不合格にする）。I197 の retro で扱う
- 確かめた結果: CI と同じ版・呼び方の shellcheck で exit 0、shellcheck を使える状態の run-all で pass=40 fail=0（`docs/reviews/I197_fix_test_result_20261026_2125.md`）
