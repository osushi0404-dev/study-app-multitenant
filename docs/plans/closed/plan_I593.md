# I593 計画書: 判定の仕組みを変える PR を変更前の版で審査する

## 基本情報
- **計画書ID**: plan_I593
- **関連イシュー**: #593
- **Draft PR**: #635
- **作成根拠資料**: docs/issues/open/I593.md（起点イシュー・設計確認メモ 2026-11-26）
- **実装後評価**: docs/reviews/open/I593_review.md
- **作成日**: 2026-11-26

## 1. 背景/目的
- レビュー役の定義・レビューの決まり・判定のスクリプトを変える PR が、変えた後の版で自分を審査できる。これを、変更前（ブランチが develop から分かれた時点＝BASE）の版で審査するようにし、変更前の版で動かせない部分を変えた PR は必ず高リスク（敵対的レビュー）にする。あわせて、テストを消す・スキップする・弱める差分を決定論で拾い、レビュー役に必ず見せる。

### 調査結果
**原因の概要**: レビューを流すスクリプトは I615 から変更前の写しで動くが、レビュー役の定義は作業ツリー（ブランチ）から読まれる。そのため、定義を変えたブランチでは自動で流さず、人が新しい版を流している。新しい版が自分を審査する形が残っている。

**詳細**:
1. 起動役 `.claude/hooks/unreviewed.py` の `run()`（:289〜320）は、BASE の写し（`.claude/hooks/reviewed-hook.sh` の `reviewed_snapshot`。写しの中身は `git archive "$base" scripts/claude` だけ・:33）の入口を、作業フォルダをリポジトリの最上位にして動かす。入口・部品・使うレビュー役の定義（`.claude/agents/*.md`）のどれかがブランチで変わっていれば 75 で止め、人に `!` で新しい版を流してもらう（:313〜317）
2. 写しの入口は `claude -p --agent <名前>` で起こす（`scripts/claude/code-review.sh:1330`・`scripts/claude/adversarial-review.sh:175`・`scripts/claude/plan-issue-review.sh:131`・`scripts/claude/issue-review.sh:48`・`scripts/claude/fix-review-lib.sh:81`）。`--agent` は作業フォルダからたどる `.claude/agents/` の定義を読むので、写しで動いても定義はブランチの版になる。レビューの決まり `docs/runbooks/review-rules.md` は、レビュー役が Read で作業ツリーから読む（`.claude/agents/code-reviewer.md:171`・`.claude/agents/plan-reviewer.md:220` が参照）
3. **スパイク（成立・2026-11-26）**: `--agents <ファイル>`（JSON）で `code-reviewer` を定義して `--agent code-reviewer` で起こすと、同じ名前のプロジェクトの定義（`.claude/agents/code-reviewer.md`）より `--agents` の定義が使われた（`claude -p` 2.1.332・出力 `CANARY_FROM_AGENTS_FLAG`）。`claude --help` は「with --print the path to a file that holds one」と説明する。このため、写しの定義を `--agents` のファイルで渡せば、作業ツリーの定義を読ませずに済む。公式の説明（https://code.claude.com/docs/en/sub-agents.md・2026-11-26 に確認）: `--agents` の JSON は `prompt`（本文と同じ）と前書きの欄 `description`・`tools`・`model` などを受け付け、`tools` の例は配列（`["Read", "Grep", "Glob"]`）、`model` は `sonnet` などの別名か完全なモデル ID。同じ名前の定義は「Managed settings > `--agents` > `.claude/agents/`」の順で上が勝つ。読み取り専用の制限は、今までどおり呼ぶ側が渡す `--tools "Read,Grep,Glob"` でも効かせる（定義の `tools` だけに頼らない）。実起動の確かめは、承認の画面を出す `test-session.sh --agents` を繰り返さず、この PR の review-gate で人が `!` で流す新しい版の実際のレビュー（手動テスト No.2）で行う
4. 高リスクの決定論の判定 `path_risk_trigger()`（`scripts/claude/code-review.sh:309`〜`318`）の集合は「GitHub から復旧できない例外」だけ。同じ集合が変更の種類 `guard`（:699・I205。止め方が厳しい）と、止めて聞く条件 2 の安全装置の集合（`docs/runbooks/workflow.md`・テスト `test_i193_official_flow.sh` の S12）に使われている
5. 変更前の版で動かせない判定の部品: (a) 起動役そのもの（`.claude/hooks/`。作業ツリーから動く）(b) 本体の会話が作業ツリーから読むスキル（審査の段階: review-gate・test-gate・fix-loop・plan-review）(c) `scripts/claude/gate-check.sh`（test-gate・close が手元のサンドボックスの中で作業ツリーの版を流す。外に出す一覧に無い）。さらに gate-check.sh は判定の関数を作業ツリーの `scripts/claude/code-review.sh` から読む（:26）
6. 費用（直近 60 件のマージ）: (a)(b)(c) のどれかを変え、今の集合に当たらないものは 7 件（約 12%）。集合を判定の仕組み全部（定義・スキル・決まり・スクリプト）に広げると 24 件
7. テストの置き場所（`git ls-files`）: `scripts/claude/tests/`（76 本）・`backend/<app>/tests/`・`frontend/src/**/__tests__/`・`e2e/`（`e2e/tests/` を含む）。ハーネスのテストの確かめの行は `ck`・`ckd`・`ck_true` など `ck` で始まる関数（約 2,700 行）。今あるスキップの目印は 7 か所（差分だけを見るので影響しない）
8. 止める指摘の種類は `STOP_RE`（`scripts/claude/code-review.sh:696`: `flow|leak|github|ac:[0-9]+`）。テストを弱める差分に理由が無いときに止める種類は無い
9. 外と中の境目: このイシューは `OUTSIDE_SCRIPTS` も外に出す型も変えない（plan-writing-rules「外と中の境目を動かす計画」の対象外）。写しの中身にレビュー役の定義と決まりの 1 ファイルを足すだけ
10. このイシュー自身の審査: この PR の BASE の写しには新しい部品（下の 4-2）が無いので、起動役は従来どおり 75 で止め、人が `!` で新しい版を流す（4-1 の「古い写しの扱い」）。新しい仕組みが自動で効くのはマージの後で、この PR の確かめは CI の決定論のテスト

## 2. 受け入れ条件
- [ ] AC1: 判定の仕組みのファイル（少なくとも `.claude/agents/*.md`・`scripts/claude/code-review.sh`・`scripts/claude/adversarial-review.sh`・`scripts/claude/fix-review-lib.sh`・`scripts/claude/plan-issue-review.sh`・`docs/runbooks/review-rules.md`）を変えたブランチで、審査の入口（`code-review.sh`・`adversarial-review.sh`・`plan-issue-review.sh`・`fix-diagnosis-review.sh`・`issue-review.sh`）を流すと、75 で止まらず、BASE の写しの入口・部品・レビュー役の定義・レビューの決まりで動く（ブランチの版の定義は使われない）
- [ ] AC2: 写しの版で動かせないとき（写しに入口が無い・写しを作れない・写しに新しい仕組みが無い）だけ 75 で止まり、人が `!` で流した作業ツリーの版のコードレビューの記録は、高リスク判定が必ず YES になる
- [ ] AC3: `.claude/skills/review-gate/`・`.claude/skills/test-gate/`・`.claude/skills/fix-loop/`・`.claude/skills/plan-review/` の配下・`scripts/claude/gate-check.sh`・`.claude/hooks/` の配下を変える差分で `path_risk_trigger()` が YES、ほかのスキル・スクリプトだけの差分では NO。gate-check.sh は判定の関数を BASE の版から読む
- [ ] AC4: テストを弱める差分（テストファイルの削除・テスト関数や確かめの行の数の減少・`skip`・`xfail`・`.only`・`.skip`・`todo`・`fixme` の追加）が、どの周のコードレビューでも決定論で拾われ、レビュー役の入力と記録に必ず載る。レビュー役は、計画書に理由が無いものを止める指摘（`STOP=test`）にし、スクリプトはその指摘で止める
- [ ] AC5: 上の方式が、失敗の注入つきの決定論のテストで固定されている（守りを外すと落ちる）
- [ ] AC6: 安全装置・高リスクの集合を書いている場所（`scripts/claude/code-review.sh`・`.claude/agents/code-reviewer.md`・`.claude/agents/plan-reviewer.md`・`docs/runbooks/workflow.md`・`docs/runbooks/review-rules.md`）が食い違っていない

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: ハーネスのレビューの流れ。`.claude/hooks/unreviewed.py`・`.claude/hooks/reviewed-hook.sh`（承認が要る場所）・審査の入口 5 本と部品・`scripts/claude/gate-check.sh`・レビュー役の定義 3 本・手順書 3 本・テスト。高リスクの周が直近 60 件で 7 件ぶん増える。審査の入口・定義を変えたブランチの毎周の `!` は、マージの後はなくなる

## 4. 変更点一覧（具体）

### 修正アプローチ
- 審査する側を「写しの版」にそろえる。写しに、レビュー役の定義（`.claude/agents/`）とレビューの決まり（`docs/runbooks/review-rules.md`）を足し、審査の入口は写しの定義を `--agents` のファイルで渡す（作業ツリーの定義を読まない）。起動役は、審査の入口に限り、ブランチで入口・部品・定義を変えていても写しで流す（75 にしない）
- 写しで動かせない部分（起動役・審査の段階のスキル・gate-check.sh）は、パスの判定で必ず高リスクにする。写しで流せず人が作業ツリーの版を流したときは、その記録の高リスク判定を YES にする
- テストを弱める差分は、ブランチ全体（merge-base から HEAD）を毎周決定論で数え、レビュー役の入力と記録に載せる。止めるかはレビュー役が計画書の理由と照らして `STOP=test` で書き、スクリプトが止める

### 4-1. 起動役（`.claude/hooks/unreviewed.py`・承認が要る）
何を達成するか: 審査の入口は、ブランチで変えていても写しの版で流す。写しが古くて新しい仕組みを持たないときは今までどおり 75。
- 定数 `REVIEW_ENTRIES = frozenset({"code-review.sh", "adversarial-review.sh", "plan-issue-review.sh", "fix-diagnosis-review.sh", "issue-review.sh"})` と `REVIEWER_LIB = "reviewer-agents-lib.sh"` を足す
- `run()`: 写しの入口があることを確かめた後、`name in REVIEW_ENTRIES` かつ写しに `scripts/claude/reviewer-agents-lib.sh` があるときは、部品の差（`parts() & _unreviewed_files()`）で 75 にしない。差があれば `[unreviewed run] ブランチで変えた審査の仕組み（…最大 5 件）は使わず、変更前の版で審査します（マージの後に効く・I593）` を標準エラーに出して写しの入口を動かす。写しに `reviewer-agents-lib.sh` が無いとき（このイシューのマージ前の BASE）と、ほかの入口は今までどおり（差があれば 75）
- 冒頭の説明（:2〜21）を合わせて直す

### 4-2. 写しの中身と定義の渡し方
何を達成するか: 写しの版のレビュー役の定義と決まりで審査する。
- `.claude/hooks/reviewed-hook.sh`（承認が要る）`_reviewed_snapshot_make`: `git archive "$base" scripts/claude` を `git archive "$base" scripts/claude .claude/agents docs/runbooks/review-rules.md` にする。一覧の I615 F3 を同梱: `$snap` が `.complete` の無いフォルダとして残っているときは、`mv -T` の前にそのフォルダを `"$cache/.stale.<名前>.XXXXXX"` へ移してから置く（置いてある写し〔`.complete` あり〕は今までどおり消さない・動かさない）
- 新しい部品 `scripts/claude/reviewer-agents-lib.sh`（審査の入口が `$(dirname "${BASH_SOURCE[0]}")` から読む）:
  - `reviewer_src_root`: このファイルの 2 つ上（写しから動けば写しの最上位、作業ツリーから動けばリポジトリの最上位）を出す
  - `reviewer_from_snapshot`: 最上位に `.complete` があり、最上位がリポジトリの最上位（`git rev-parse --show-toplevel`）と違うとき真
  - `reviewer_agent_args <名前> <一時フォルダ>`: `<最上位>/.claude/agents/<名前>.md` を `python3 -I` の小さな変換で `--agents` 用の JSON（`{"<名前>": {"description": …, "prompt": <本文>, "tools": [...], "model": …}}`）にして `<一時フォルダ>/agents.json` に書き、グローバルの配列 `REVIEWER_ARGS=(--agents <ファイル> --agent <名前> --add-dir <最上位>)` を作る（作業ツリーから動くときは `--add-dir` を付けない）。呼ぶ側の `--tools "Read,Grep,Glob"`・`--permission-prompts none` などはそのまま残す（読み取り専用の制限を定義だけに頼らない）。前書きは `name`・`description`・`tools`・`model` の 4 つだけを受け付け、ほかの鍵・形の崩れ・定義が無いときは非 0 で終わる（fail-closed。写しの定義が無い＝古い形の写しのときは「`~/.cache/claude-reviewed-snapshots/<BASE>` を消してやり直す」案内を出す）。写しから動くときは、本文の `docs/runbooks/review-rules.md` を `<最上位>/docs/runbooks/review-rules.md`（写しの版）に置き換える
- 呼ぶ側（`--agent <名前>` を `"${REVIEWER_ARGS[@]}"` に置き換える）:
  - `scripts/claude/code-review.sh`（:1330 の `run_claude_logged` の引数・:1108 の `REVIEWER_AGENT`）
  - `scripts/claude/adversarial-review.sh`（:175 の `run_reviewer`）
  - `scripts/claude/plan-issue-review.sh`（:131）
  - `scripts/claude/issue-review.sh`（:36 の有無の確かめ・:48）
  - `scripts/claude/fix-review-lib.sh`（:69 の有無の確かめを最上位の定義にする・:81）
  - `scripts/claude/fix-diagnosis-review.sh`（:15 の `REVIEWER` のパスの説明だけ。読み込みは fix-review-lib.sh）

### 4-3. 写しで動かせなかったときの高リスク（AC2）
何を達成するか: 人が `!` で作業ツリーの版を流した周は、記録の高リスク判定が必ず YES。
- `scripts/claude/code-review.sh` に関数 `reviewer_source_risk`（`reviewer_from_snapshot` が偽なら YES、真なら NO）を足し、本体で `RISK_FINAL=$(combine_risk "$RISK_FINAL" "$RISK_SOURCE")` に入れる。証跡に `- 審査の版: 写し <BASE> / 作業ツリー（写しで動かせなかった → 高リスク）` を書く
- `scripts/claude/plan-issue-review.sh` も同じく、作業ツリーから動いたときは出力の RISK を YES にする（計画の段階の高リスクが code-review の `plan_risk` に入る）

### 4-4. パスの判定と集合（AC3・AC6）
何を達成するか: 写しで動かせない判定の部品を変えた PR を必ず高リスクにする。変更の種類 `guard` と止めて聞く条件 2 の集合は今のまま（GitHub から復旧できない例外）にする。
- `scripts/claude/code-review.sh`:
  - 今の `case` を関数 `guard_path_trigger()`（GitHub から復旧できない例外。今の集合そのまま）に移す
  - 関数 `review_mechanism_trigger()`（新しい集合: `.claude/hooks/*`・`.claude/skills/review-gate/*`・`.claude/skills/test-gate/*`・`.claude/skills/fix-loop/*`・`.claude/skills/plan-review/*`・`scripts/claude/gate-check.sh`）を足す
  - `path_risk_trigger()` は両方の OR（入出力は今のまま。呼ぶ側 :1188・gate-check.sh:134 は変えない）
  - 変更の種類（:699 付近）の `guard` は `guard_path_trigger()` の集合のまま
- `scripts/claude/gate-check.sh`: `GATE_CHECK_LIB` が無いときは、判定の関数を作業ツリーの `scripts/claude/code-review.sh` でなく、`git show <merge-base>:scripts/claude/code-review.sh` を一時ファイルに書いて読む（取れなければ `fail base`）。テストの差し替え `GATE_CHECK_LIB` は残す
- 集合の説明をそろえる: `.claude/agents/code-reviewer.md`（:171 の行に新しい集合の行を足す・:172 の「Yes にしない」から新しい集合を除く）・`.claude/agents/plan-reviewer.md`（:220 の行に新しい集合の行を足す・:221 の「Yes にしない」から新しい集合を除く）・`docs/runbooks/review-rules.md`「高リスク変更の敵対的レビューステージ」・`docs/runbooks/workflow.md`（止めて聞く条件 2 は `guard_path_trigger` と同じと書き直す）・`scripts/claude/tests/fixtures/i185/workflow_stop_conditions.txt`（workflow.md「止めて聞く条件」の節の写しで、`scripts/claude/tests/test_i185_harness_docs.sh:61` が一致を確かめるので、同じ文に直す）

### 4-5. テストを弱める差分（AC4）
何を達成するか: ブランチ全体のテストを弱めうる差分を、毎周の入力と記録に必ず載せ、計画書に理由の無いものを止める。
- `scripts/claude/code-review.sh` に関数 `test_weakening_report <base> <head>`（`git -c core.quotePath=false diff --no-renames` と `git show <rev>:<path>` で決定論に数える）:
  - テストのファイル: `scripts/claude/tests/` の配下・`backend/` の配下で `tests/` の中か `test_*.py`・`frontend/` の配下で `__tests__/` の中か `*.test.*`・`*.spec.*`・`e2e/` の配下
  - 出す行（1 行 1 件）: `TEST_WEAKENING: deleted <パス>`（消したテストのファイル）／`TEST_WEAKENING: fewer-tests <パス> <前>-><後>`（テストの定義の数が減った: Python `def test_`・JS/TS `it(`・`test(`）／`TEST_WEAKENING: fewer-checks <パス> <前>-><後>`（確かめの数が減った: Python `assert`・`self.assert`、JS/TS `expect(`、シェル行頭の `ck` で始まる関数）／`TEST_WEAKENING: skip <パス>:<HEAD の行> <行の中身>`（足した行の目印: `@pytest.mark.skip`・`pytest.skip(`・`skipIf`・`skipUnless`・`@unittest.skip`・`xfail`・`.skip(`・`.only(`・`.todo(`・`.fixme(`・`xit(`・`xdescribe(`、シェルのテストでは語の `skip`・`SKIP`）
  - 無ければ `TEST_WEAKENING: なし` の 1 行
  - 範囲はいつも `merge-base(origin/develop, HEAD)` から HEAD（差分のレビューの周でも全体を出す）
- 本体: コンテキストに節「### テストを弱めうる差分（決定論・I593。全件について、計画書に理由があるかを確かめる）」を足し、証跡（`GATE_EVIDENCE`）にも同じ行を書く（記録に残る）
- 止める種類 `test` を足す: `STOP_RE`（:696）を `flow|leak|github|test|ac:[0-9]+` にし、台帳の止め方（種類によらず、再現ありの `STOP=test` は止める）を `flow` などと同じ扱いにする
- `.claude/agents/code-reviewer.md`: 「提供されるコンテキスト」に新しい節を書き、P4 に「入力の `TEST_WEAKENING` の各行について、計画書（変更点・確定事項）に理由があるか確かめる。理由が無いものは `STOP=test`・再現に該当の行を書く」を足す。「止める指摘の書き方」の一覧に `test` を足す
- `docs/runbooks/review-rules.md`: 止める条件の一覧と、テストを弱める差分の扱いを書く。正当な整理で数が減るときの計画書への書き方の例（「4. 変更点に `<テストのファイル>` のテストを `<移した先>` へ移す・重複を消す、と書く」）を添える（計画レビューの Info）

### 4-6. 手順書
- `docs/runbooks/danger-ops.md`（:44・:48）: 審査の入口は、ブランチで変えていても写しの版で流す（75 にしない）。75 は写しに入口が無い・写しを作れない・写しに新しい仕組みが無いときだけ。審査の入口の引数・出力の形を変えるときは、古い形も受ける版を先にマージする（2 段で変える）
- `docs/runbooks/review-rules.md`: 審査は変更前の版で動くこと・新しい審査役はマージの後に効くこと・高リスクの集合（4-4）・テストを弱める差分（4-5）

### 4-7. 一覧から同梱
- I615 F3（`.claude/hooks/reviewed-hook.sh`）: 4-2 で直す
- I615 F5（`scripts/claude/code-review.sh`。写しから動く入口が `python3 -` を `-I` 無しで起こす）: `code-review.sh` の `python3 -` / `python3 -c` を `python3 -I` にする（作業フォルダの `yaml.py` などを読み込まない）

## 5. 実装手順（ステップ）
1. 4-2 の `reviewer-agents-lib.sh` と変換（未知のリスク: JSON の `tools`・`model` の受け付け）を先に作る → TC-03。不成立なら計画を直す
2. 4-2 の呼ぶ側 5 本の置き換え（ステップ 1 の後）→ TC-04
3. 4-3 の高リスク（ステップ 1 の後）→ TC-06
4. 4-4 のパスの判定・gate-check.sh・集合の説明（ステップ 2・3 と並行してよい）→ TC-01・TC-02・TC-10
5. 4-5 のテストを弱める差分（ステップ 2・3 と並行してよい）→ TC-07・TC-08・TC-09
6. 4-1・4-2 の起動役と写し（`.claude/hooks/`。承認の画面が出る。ステップ 1〜5 の後）→ TC-05・TC-11
7. 4-6 の手順書・4-7 の同梱 → TC-12
8. 全体の検査 → TC-13

## 6. テスト計画
### 自動
- 新しい `scripts/claude/tests/test_i593_review_from_base.sh`（TC-01〜TC-11。一時の git リポジトリと `CLAUDE_BIN` の差し替えで、本物のファイルを書き換えない）。既存の `test_i181_review_slim.sh`・`test_i193_official_flow.sh`（S12）・`test_i205_stop_criteria.sh`（K2）・`test_adversarial_trigger.sh`・`test_i599_unreviewed_scripts.sh`・`i599_cases.py` の集合・起動役の期待を直す
- レベル: すべてユニット／小さな結合（一時リポジトリ）。アプリのテストは無し（CI が流す）
- 各 TC に失敗の注入（FG）を付ける
### 手動
- M-1（Claude）: この PR の review-gate で、起動役が 75 を出し（写しに新しい仕組みが無い）、`!` で流した作業ツリーの版のコードレビューの記録の証跡に「審査の版: 作業ツリー」と高リスク判定 YES が出る
- マージ後の実測（retro で約束し、次のハーネスの PR で測る）: 審査の入口・定義を変えたブランチで 75 が出ず、記録に「審査の版: 写し」が出る

## 7. ロールバック
- PR を revert する。写しの置き場所（`~/.cache/claude-reviewed-snapshots/`）の写しは BASE ごとなので、revert 後の BASE では新しく作られる（古い写しは消さなくてよい）

## 8. Risk & 回避策
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: スキルが写しの入口に無い引数を使うと、写しの入口が使い方の誤りで止まる | 手順書に「入口の形を変えるときは 2 段」と書く。止まっても誤りで終わるだけで、通らない側に倒れる | 回避 |
| R2: `--agents` の優先や JSON の欄の受け付けが Claude Code の版で変わる | TC-03 は変換の形を固定。版の変わり目の確かめは `docs/runbooks/harness-audit.md` の点検に任せる（`--agents` の優先は版ごとに 1 回確かめる行を足す） | 受け入れ |
| R3: 組み込みの `/code-review`・`/security-review`（`code-review.sh:188`）は作業ツリーの CLAUDE.md などを読む | 組み込みの `/code-review` は合否に使わない参考。`/security-review` は動いたかだけを使う。この 2 つを写しにそろえる手段は公式に無い | 受け入れ |
| R4: 本体の会話が読むスキルのうち、審査の段階の 4 つ以外（proceed・close など）は作業ツリーの版で動く | ユーザーの決定（設計確認メモ ii）。最後の守りは人のマージ。close が流す gate-check.sh は高リスクの集合に入れ、判定の関数は BASE から読む | 受け入れ |
| R5: 写しの版で審査するので、審査役を直す PR の新しい審査役はその PR では動かない | ユーザーの決定（設計確認メモ A）。新しい版は CI の決定論のテストで確かめ、マージの後に効く | 受け入れ |
| R6: テストを弱める差分の数え方は数の比較なので、同じ数のまま中身を弱める変更は拾えない | レビュー役の P4 の観点（tautology・false-green）が引き続き見る。拾えるものは必ず見せる | 受け入れ |
| R7: 古い形の写し（定義を持たない）が同じ BASE に残ると、審査の入口が止まる | 新しい仕組みを持つ BASE の写しは新しい起動役しか作らないので生じない。生じても止まる側で、案内（写しを消してやり直す）を出す | 回避 |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 方式 A（審査はいつも写しの版で自動。新しい審査役はマージの後。写しで動かせないときだけ 75 → `!`、その PR は必ず高リスク）
- レビューの決まり（`docs/runbooks/review-rules.md`）は写しの版を読ませる
- 審査の段階のスキル 4 つは `path_risk_trigger()` で高リスク。ほかのスキルは高リスクにしない
- テストを弱める差分の範囲と扱い（レビュー役に必ず見せる・記録に載せる・計画書に理由が無いものはレビュー役が止める・高リスクにはしない）
Claude が決めた（技術的な選択と理由）:
- 定義の渡し方は `--agents <ファイル>`（スパイクで、同じ名前のプロジェクトの定義より優先されると確かめた）。作業フォルダを写しに変える案は、レビュー役が作業ツリーのファイルを相対で読めなくなるので採らない
- 審査の入口の一覧 `REVIEW_ENTRIES` を起動役に置く（承認が要る場所。ブランチから変えにくい）
- 写しに新しい仕組みがあるかを `reviewer-agents-lib.sh` の有無で決める（このイシューのマージ前の BASE で、古い写しの入口がブランチの定義を読むのを防ぐ）
- 「写しで動かせない部分」として `.claude/hooks/`（起動役そのもの）と `scripts/claude/gate-check.sh`（手元で作業ツリーの版が流れる判定）を高リスクの集合に入れる。設計確認メモの「変更前の版で動かせない部分は必ず高リスク」の具体化で、増えるのは直近 60 件で 7 件（4 つのスキルを含む）
- gate-check.sh は判定の関数を BASE の `code-review.sh` から `git show` で読む（ブランチの `code-review.sh` が gate-check の判定を変えないように）
- 変更の種類 `guard` と止めて聞く条件 2 の集合は広げない（`guard_path_trigger` に分ける）。広げると審査の段階のスキルを直すたびにユーザーに聞くことになり、開発の速さを落とすため。高リスク（敵対的レビュー）だけを広げる
- 写しで動かせなかった周の高リスクは、code-review.sh が自分の置き場所（写しか作業ツリーか）で決める
- テストを弱める差分は「数の減少」と「足した目印」で数える（行の削除の一覧より雑音が少ない。中身の弱め方はレビュー役が見る）。止める種類は新しい `STOP=test`
- 一覧 docs/reviews/backlog/I615.md F3: 同梱 — 写しの作り方を直すので同じ場所
- 一覧 docs/reviews/backlog/I615.md F5: 同梱 — 写しの入口を常に外で動かすので、作業フォルダの読み込みを断つ価値が上がる
- 一覧 docs/reviews/backlog/I615.md F2: 残す — 審査の入口は部品の差で止めなくなり、ほかの入口でも見落としは古い版が動くだけ
- 一覧 docs/reviews/backlog/I206.md F3・F4・F6／I207.md F6・F7／I208.md F2・F5／I209.md F6／I210.md F1／I212.md F2・F3・F4・F6／I227.md F1・F2・F4・F5・R1／I228.md F3・F5／I430.md F8／I486.md F2〜F5・F7・F8／I512.md F2・F3・F6・F14・F15／I525.md F5・F6／I546.md F3・F5／I597.md F2／I599.md F5・F6・F9・F27／I610.md F4: 残す — このイシューの目的（審査の基準を変更前の版にする）と別の箇所で、同梱すると差分とレビューの周が増える
- 一覧 FILE=- の行（I223.md B1〜B4・I224.md F9）: 残す — bot の停止・別のイシューの実測で、このイシューと関係が無い
- 必読の規約（`rules/ultimate_django_coding_standards.md`・`rules/react-coding-standards-integrated.md`）: アプリのコードを変えないので当たる節なし
- セキュリティ影響: 守りを強める変更。入力（定義の前書き）は決まった 4 つの鍵だけを受け付け、ほかは止める。秘密情報・認可・OWASP・依存の追加は無い（Python 標準ライブラリだけ）。bandit・shellcheck は CI の pre-commit（bandit MEDIUM 以上を直す）
- P3/P5/P8 影響なし（DB・非同期・新しいインフラ無し。費用は高リスクの周が 60 件で 7 件ぶん増える分だけで、3. に書いた）。P6 影響なし（画面なし）。P9 影響なし（個人情報を扱わない）
- 設計判断の区別: 要件・UI/UX の仮定は無い（すべて設計確認メモで確定、ほかは技術的な選択）
Danger Ops（有無。有りのときは 影響範囲・代替案・ロールバック・実行コマンド を書く。条件と手順は docs/runbooks/danger-ops.md）:
- 無（`.claude/hooks/` の編集は承認が要るが、危険操作ではない）

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | 写しに新しい仕組みがあるとき、ブランチで審査の入口・部品・定義を変えても、起動役は写しの入口を動かし、写しの定義が `--agents` で渡る（作業ツリーの定義が使われない）。TC-04・TC-05 |
| V2 | 1 | 読んで可 | 写しで動かせないとき（入口なし・写しを作れない・写しに新しい仕組みなし）だけ 75 になり、作業ツリーの版で流した記録の高リスクが YES。TC-05・TC-06 |
| V3 | 2 | 読んで可 | 新しい集合の各パスで YES・似た名前とほかのスキルで NO、集合を 1 つ外すと TC が落ちる。guard の種類と止めて聞く条件 2 の集合は変わらない。TC-01・TC-02 |
| V4 | 2 | 読んで可 | テストを弱める差分の各種類が拾われ、テストでないファイルの `skip` や同じ数のままの移動は拾わない。判定を外すと TC が落ちる。TC-07・TC-08・TC-09 |
| V5 | 3 | 読んで可 | gate-check.sh が BASE の判定の関数を使い、ブランチの `code-review.sh` で高リスクを NO にしても敵対的レビューの OK を求める。TC-10 |
| V6 | 3 | 読んで可 | 定義の変換が前書きの未知の鍵・崩れ・定義なしで止まり、決まりの参照が写しの版に置き換わる。TC-03 |

## 計画変更記録
- 2026-11-26 plan-review: 計画レビュー（20261126_1328・OK）の Warning・Info を反映: 調査結果 3 に公式の説明での確かめと実起動の確かめ方を追記／4-2 に呼ぶ側の `--tools` を残すことを追記／4-4 の写し（fixture）と plan-reviewer.md の行を確定／4-5 に review-rules.md の書き方の例を追記／auto_test の TC-12 の判定の形と対応を直した。`.claude/hooks/`・`gate-check.sh` を集合に入れたこと（イシューの方針 (3) の 4 つのスキルを超える）は 9. の理由のとおり方針 (2) の具体化で、ユーザーの委任の範囲として close の PR 説明に明記する — 理由: 指摘への対応の追記だけで方式・範囲・受け入れ条件は変えない。計画レビューのやり直し: 不要
- 2026-11-26 implement: 計画書の記載: 「既存の `test_i181_review_slim.sh`・… を直す」 → 採った方法: (1) 審査の入口を丸ごと流す既存のテスト（`test_i197_review_ledger.sh`・`test_i202_ledger_cleanup.sh`・`test_i205_stop_criteria.sh`・`test_i212_review_base.sh`・`test_i197_adversarial_process.sh`）は、一時リポジトリに `reviewer-agents-lib.sh` と定義を写し、本番と同じく写しから入口を流す（新しいテストの道具 `scripts/claude/tests/lib_test_snapshot.sh`）。作業ツリーから流すと 4-3 で高リスクに倒れ、期待が変わるため (2) 呼び方を照らす既存のテスト（`test_i193_official_flow.sh` の R7・S12、`test_i197_adversarial_process.sh` の S1・S5、`test_fix_review.sh` の TC-16、`test_i205_stop_criteria.sh` の K2・FG-B11）を新しい呼び方・`guard_path_trigger` に合わせた (3) TC-05 は起動役の道具がある `i599_cases.py` に書いた (4) `fix-review-lib.sh` の claude を `${CLAUDE_BIN:-claude}` にした（TC-04 の差し替えのため。ほかの入口と同じ形）(5) `gate-check.sh` の一時ファイルの後片付けを既存の後片付けにまとめた (6) 写しの作り方は、BASE に定義・決まりが無いときもそれを除いて写しを作る（archive 全体を失敗させない）(7) `force_plan_highrisk` は VERDICT: OK の後に HIGHRISK の行を足す形にした — 理由: どれも計画の方式・範囲・受け入れ条件の中の実装の詳細とテストの直し。計画レビューのやり直し: 不要

## レビュー結果
- [20261126_1328 判定: ✅ 完了](../../reviews/closed/I593_plan_review_20261126_1328.md)
