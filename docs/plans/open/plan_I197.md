# I197 計画書: 実装の検証（レビュー）の仕組みを白紙から作り直す

## 基本情報
- **計画書ID**: plan_I197
- **関連イシュー**: #332
- **Draft PR**: #336
- **作成根拠資料**: docs/issues/open/I197.md（起点イシュー・設計確認メモあり）
- **実装後評価**: docs/reviews/open/I197_review.md
- **作成日**: 2026-10-26

## 1. 背景/目的
- I166 の敵対的レビュー第 1 周で、裏で動くサブエージェント 3 体が確認画面で約 11.5 分止まり、時間切れのまま「通過」になった。今の develop（I193 後）も「裏のサブエージェント＋15 分のタイマー」の形は同じで、止まれば「15 分×2 回待って HIGH」で止まる（時間の無駄・人の判断待ち）。
- 目的: ①黙って止まる経路を構造的に無くす ②証拠が無いことを合格にしない ③確かめる項目の網羅を決定論で保証する ④1 周 10 分以内でサクサク回す。公式の道具（`claude -p`・`--agent`・`--permission-prompts none`・`--permission-mode auto`・`--resume`・`stream-json`）を土台にし、自作は公式に無い「段取り（並列起動・実験の受け渡し）と決定論の判定・記録」だけにする（I193 の方針）。

## 調査結果

### 原因の概要
敵対的レビューだけが「親の会話の中で裏で動くサブエージェント」で、実行の道具（Bash）を持っている。サブエージェントが承認の要る操作をすると、親からは「確認待ちか」を知る手段が無く、タイマーが鳴るまで気づけない。さらに報告が最後に 1 回だけなので、止まった体の調べた内容は消え、判定はレビュー役の自己申告（`NEW_HIGH: 0`）だけで決まる。

### 詳細な原因分析
1. `.claude/skills/review-gate/SKILL.md` 3-1 の 4: Agent ツールの `subagent_type: adversarial-reviewer` を `run_in_background: true` で起動し、`scripts/claude/review-timer.sh 900` で待つ。
2. `.claude/agents/adversarial-reviewer.md` の `tools: Read, Grep, Glob, Bash`。Bash の実験が見張り（`pretooluse_guard.py` の確認）や本体のワークツリー隔離チェックに当たると、確認画面が出て止まる（I166 の第 1・2 周）。
3. 判定は SKILL 3-2 の「3 体が報告し、`NEW_CRITICAL`＋`NEW_HIGH` が 0」だけ。何を確かめたか（項目ごとの実験の有無）は集計していない。
4. 時間切れの体は Task を止めるだけで、最後のツール呼び出し・結果・待ち時間は残らない（原因を推測で説明した: イシューの問題 5）。
5. 他のレビュー役（code-reviewer など）は既に `claude -p --agent … --tools "Read,Grep,Glob"` の別プロセスで、時間切れは BLOCKER に倒れる。ただし `--permission-prompts none` は付いていない（読む道具だけなので今は止まる経路が見つかっていないが、仕組みとして保証していない）。

### スパイク（最小実証・2026-10-26・このワークツリーで実行。スクリプトは scratchpad の `spike/s1.sh`〜`s4.sh`）
| No | 確かめたこと | 結果 |
|---|---|---|
| S1 | `claude -p --agent adversarial-reviewer --tools "Read,Grep,Glob" --permission-mode manual --permission-prompts none --output-format json` で、読むだけのレビュー役を別プロセスで動かし、Bash を使えと指示する | **成立**。12 秒・約 $0.07 で報告を返した。Bash は「Bash is disabled for this session」で使えず（道具そのものが無い）、止まらずに続けた。出力に `session_id`・`permission_denials`（配列）・`result`（本文）がある。`--json-schema` は `--agent` と組み合わせると `structured_output` が空だった（`StructuredOutput` を `--tools` に足しても同じ）→ 構造化出力は使わず、行頭の機械可読行（今の方式）で受け取る |
| S2 | S1 の `session_id` を `claude -p --resume <id> --agent adversarial-reviewer --tools "Read,Grep,Glob"` で続け、実験の結果を渡す | **成立**。7 秒。前回の文脈（C1 の結論）を覚えたまま結論を更新し、`NEW_CRITICAL`・`NEW_HIGH` の 2 行で終えた |
| S3 | 実験を実行する役（`--tools "Bash"`・`--model haiku`・`--setting-sources user --settings .claude/settings.json`・`--permission-prompts none`）を、通常モード（manual）と自動承認モード（auto）で起動し、普通の実験コマンドを 1 回ずつ実行させる | manual: `docker compose exec -T backend python -c 'print(1+1)'` は拒否（`permission_denials` に入る。待たない）。auto: 同じコマンド・`bash -c 'ulimit -v …; timeout 5 bash scripts/claude/review-timer.sh …'`・波かっこを含む heredoc で /tmp にファイルを書いて実行、がすべて**承認なしで実行**。見張りが確認を求める `docker compose cp …` は auto でも**待たずに拒否**され `permission_denials` に入った。→ 実験役は auto＋承認なしで起動する。普通の実験は通り、承認が要るものは待たずに拒否されて記録に残る。本体のワークツリー隔離チェック（I166 第 2 周の「too complex to verify」）は、別プロセスでは heredoc に当たらなかった |
| S4 | 読むだけのレビュー役を `timeout 25` で打ち切り、`--output-format stream-json --verbose` の途中の出力から最後のツール呼び出しを取り出す | **成立**。exit 124 で止まった後も 61 行が残り、最後の `tool_use`（Read・ファイル名）と、その `tool_result` の先頭を取り出せた |

### 既存テストのベースライン
- `bash scripts/claude/tests/run-all.sh`（2026-10-26・develop にマージ済みの I166 ブランチで実行）: `run-all: pass=39 fail=0`・exit 0

### 今の仕組みを参照している箇所（消費箇所の全件・grep で確認）
- 敵対的レビューの起動・タイマー: `.claude/skills/review-gate/SKILL.md`（3 節）・`scripts/claude/review-timer.sh`（呼び出し元は review-gate だけ）
- レビュー役の定義: `.claude/agents/adversarial-reviewer.md`
- 文言を固定しているテスト: `scripts/claude/tests/test_i181_review_slim.sh`（D1: `15 分`・`review-timer.sh 900`・`TaskStop`・`run_in_background` など／D4: `12 分`・`15 分`・`ulimit -v`・`timeout 60`／FG-D1）・`scripts/claude/tests/test_i193_official_flow.sh`（adversarial-reviewer だけ `Read, Grep, Glob, Bash`／S17: `review-timer.sh 900`・review-timer.sh の引数）
- 決まりの文: `docs/runbooks/review-rules.md`「高リスク変更の敵対的レビューステージ」（上限の行）・`docs/runbooks/workflow.md`（流れの 4 番目の行）
- `claude -p` の呼び出し（`--permission-prompts none` の有無）: `scripts/claude/code-review.sh`（2 か所）・`scripts/claude/plan-issue-review.sh`・`scripts/claude/issue-review.sh`・`scripts/claude/fix-review-lib.sh`・`scripts/claude/check-permission-prompt.sh`（付いている）
- 敵対的レビューの記録を読む側: `scripts/claude/gate-check.sh`（最新の記録の `VERDICT`・`REVIEWED_COMMIT` だけを読む。形を保てば変更不要）

### 環境前提
- `claude`（`--permission-prompts`・`--permission-mode auto`・`--resume`・`--agent`・`stream-json` あり。`claude --help` で確認）・`python3`・`git`・`gh`（認証済み）・`timeout`。docker は実験役が使う場合だけ（無くても実験が失敗するだけで、判定は止まる側）

## 2. 受け入れ条件
イシューの受け入れ条件と同じ（docs/issues/open/I197.md）。各条件の確かめ方は §6 と auto_test・manual_test に対応させる。
- [ ] AC1 検証の全体設計（何を・どの段階で・何で確かめるか、決定論と LLM の分担）が文書化されている → §4.1・`docs/runbooks/review-rules.md`
- [ ] AC2 独立した目の方式を比較した結果（採用・捨てた方式と理由・実証の結果）が計画書に記録されている → §4.2・調査結果のスパイク
- [ ] AC3 検証する側が確認画面で黙って止まる経路が無いことをハーネステストで固定（承認が要る操作は待たずに「未検証」として記録）→ TC-01・TC-02
- [ ] AC4 時間切れ・報告なし・拒否で終わった検証は合格にならず、最後のツール呼び出し・結果・待ち時間が記録に残ることをハーネステストで固定 → TC-01
- [ ] AC5 確かめる項目の一覧から判定を決定論で出し、未実施が残ると合格にならないことをハーネステストで固定 → TC-01
- [ ] AC6 新しい仕組みで高リスク相当の検証を通しで行い、①人の応答待ち 0 ②1 周 10 分以内 ③項目ごとの結果、が記録されている → 手動 No.1・No.2
- [ ] AC7 本体のワークツリー隔離チェックが残っていても、検証する側がそれに頼らず終えられる → §4.3・手動 No.2
- [ ] AC8 I194 は統合して取り下げ・レビュー時間の原因調査は起票せず統合。理由が計画書にあり、I194 の GitHub にコメント → §4.6・手動 No.4
- [ ] AC9 公式の道具を土台にする方針に沿う（自作は公式に無い部分だけ・根拠が計画書にある）→ §4.2・§9
- [ ] AC10 既存のハーネステスト（`run-all.sh`）・CI がすべて pass → TC-07・CI
- [ ] AC11 見張り（`scripts/claude/hooks/pretooluse_guard.py`）と `.claude/settings.json` を変えていない → TC-08

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: `.claude/skills/review-gate/SKILL.md`・`.claude/agents/adversarial-reviewer.md`・`.claude/agents/plan-reviewer.md`（1 行）・`scripts/claude/`（新規 2・変更 4・削除 1）・`scripts/claude/tests/`（新規 1・変更 2）・`docs/runbooks/review-rules.md`・`docs/runbooks/workflow.md`・`docs/plans/templates/plan_template.md`。`.claude/settings.json` と見張りは変えない（I200 が担当）
- 依存関係ファイル（requirements*.txt / package*.json）: 変更なし

## 4. 変更点一覧（具体）

### 4.1 検証の全体設計（AC1。`docs/runbooks/review-rules.md` に「検証の全体設計」として書く）
| 層 | 何を確かめる | 何で | いつ（段階） | 止まり方 |
|---|---|---|---|---|
| 1 決定論 | テスト（pytest・Jest・E2E・ハーネステスト）・lint・型・注入（守りを壊すとテストが落ちるか＝false-green の検査）・計画が宣言した決定論ゲート・レビュー後の変更の有無 | CI・`code-review.sh` の決定論ゲート実走・`gate-check.sh` | implement の後・review-gate・test-gate・close | 失敗＝不合格（exit code） |
| 2 基本レビュー（独立した目） | 受け入れ条件・計画との照合・BP・セキュリティの見落とし | 組み込み `/code-review`（高リスク時は `/security-review`）・`code-reviewer`。どちらも別プロセスの `claude -p`・読むだけ・承認なし | review-gate 1 | 時間切れ・失敗・空は BLOCKER（今のまま） |
| 3 敵対的レビュー（高リスク時・独立した目） | 「合格」の反証。決定論で見られないこと（脅威モデル・要件の漏れ・設計の筋）と、確かめる項目の一覧の各項目 | 新しい `scripts/claude/adversarial-review.sh`: 読むだけのレビュー役 3 観点を別プロセスで並列に起動し、実験案は実験役（別プロセス・auto・承認なし）が実行して結果を `--resume` で返す。判定は一覧からスクリプトが決定論で出す | review-gate 3 | 未検証・未報告・時間切れ・拒否は合格にしない |
| 4 人 | 価値判断・操作感 | 手動テスト（Human の行）・マージ | test-gate・close | 人の返事 |

- **LLM に任せるのは層 2・3 の「読んで判断すること」だけ**。実行（実験）は実験役が行い、実行したかどうかは実験役の記録（`stream-json` の `tool_use`/`tool_result`/`permission_denials`）で決定論に確かめる。レビュー役の「実験した」という自己申告は判定に使わない。
- **実装した本人の確認と独立した目の分け方**: 実装セッション（親）は段取りを呼ぶだけで、判定に自分の読みを混ぜない。独立した目は別プロセス（親の会話の文脈を持たない）。
- **決定論を厚くする**: 一覧の「実験必須」の項目は、できるものは auto_test の TC（注入つき）にして層 1 で覆うことを計画の段階で考える（テンプレートの説明に書く）。層 1 で覆った項目も、層 3 では「その TC が本当にその項目を確かめているか」を読む（I166: 注入で見落としたテストの穴を延長周の読みが見つけた。両方要る）。

### 4.2 独立した目の方式の比較（AC2・AC9）
| 方式 | 止まらないか | 独立性 | 速さ・費用 | 実験 | 結論 |
|---|---|---|---|---|---|
| (a) 裏で動くサブエージェント（今） | ✗ 確認画面で黙って止まる。親から「確認待ちか」を知る公式の手段が無い（I166 第 1 周で 11.5 分） | ○ | 安い | 体の中で実行（止まる元） | **捨てる** |
| (b) 読むだけのサブエージェント＋親が実験（I166 延長周） | △ 定義から Bash を外せば体は止まらないが、親が実験を実行するとき親の会話に確認画面が出うる（親が自動承認モードでなければ人を待つ） | ○ | 速い（1〜2 分） | 親が実行 | 形（読むだけ・実験は別が実行）は採る。**ただし体も実験も親の会話の外（別プロセス）に出す** |
| (c) メイン側（実装したセッション）がレビュー | ○ | ✗ 自己レビューは追認に引っぱられる（過去の教訓） | 速い | 親 | **捨てる**（敵対的レビューの代わりにしない） |
| (d) 別プロセス `claude -p --agent` | ○ `--permission-prompts none` で承認が要る操作は待たずに拒否され `permission_denials` に残る（S1・S3）。読む道具だけなら実行の道具そのものが無い | ○ 親の文脈を持たない | 12 秒〜（S1）。並列は親が background で起動するだけ | 実験役も別プロセス（auto＋承認なし・S3）。結果は `--resume` で返す（S2） | **採る（軸）** |
| (e) 組み込み `/code-review`・`/security-review` | ○（plan モードの別プロセス。承認なしを足す） | ○ | 速い | なし | **併用**（層 2。一覧での判定・実験はできないので層 3 の代わりにはならない） |
| (f) GitHub 側 | ○ | ○ | Claude を Actions で動かすのは API 費用がかかる | ― | 決定論のテストは既存の `Harness Tests` ジョブで流す（新しいジョブ・Claude の実行は足さない） |

- 公式の道具で済むもの: 別プロセス化（`claude -p`）・定義の再利用（`--agent`）・道具の制限（`--tools`）・承認なし（`--permission-prompts none`）・自動承認の判定（`--permission-mode auto`）・続き（`--resume`）・途中の記録（`stream-json`）。
- 自作するもの（公式に無いもの）: 3 観点の並列起動と 10 分の締め切り・実験案の受け渡し・一覧からの決定論の判定・記録の形（gate-check が読む行）。公式の `/code-review` には「計画の一覧の項目ごとに実験の有無で合否を出す」機能が無い。
- (a) をやめて失うもの: 親の会話の中で起動できる手軽さ・Agent ツールの通知。代わりにスクリプト 1 本を background で呼び、完了の通知を受ける（code-review.sh と同じ形）。失って困るものは無い（I166 で (a) の問題を実証済み）。

### 4.3 新規 `scripts/claude/adversarial-review.sh I###`（層 3 の段取り）
修正方針: 敵対的レビューの 1 周を、人の応答を一度も待たずに 10 分以内で終え、判定と記録をスクリプトが決定論で出す。

処理の流れ:
1. 引数 `I###` を確かめる。`REVIEW_LIB_SOURCE_ONLY=1` で `scripts/claude/code-review.sh` を読み込み、`neutralize_machine_lines`・`commit_review_artifact`・`is_record_path` を使う（同じ規則を 2 か所に書かない）。新しいライブラリ `scripts/claude/review-process-lib.sh`（§4.4）も読み込む。
   - このスクリプト自身も、関数の定義の後・本体の前に `if [ "${REVIEW_LIB_SOURCE_ONLY:-}" = "1" ]; then return 0; fi` を置き、テストと手動 No.2 が関数だけを読み込めるようにする（code-review.sh・fix-review-lib.sh と同じ形）。主な関数: `read_checklist <計画書>`（一覧を `V<n>\t<観点>\t<確かめ方>\t<内容>` で出す・形の誤りで 2）・`run_reviewer <観点> <入力> <ログ> [<session_id>]`（レビュー役の 1 回の呼び出し）・`run_experiment_agent <観点> <実験の一覧ファイル> <ログ>`（実験役の 1 回の呼び出し）・`parse_report <本文>`（`ITEM:`・実験案・`NEW_*` を取り出す）・`item_verdict`・`final_verdict`・`write_record`
2. 周回の数え方（今の SKILL 3-1 の 1・2 をスクリプトに移す）: `docs/reviews/[closed/]I###_adversarial_review_*.md` の `ROUNDS:` の合計（行が無い記録は 1）が `ADV_ROUND_LIMIT`（既定 2。ユーザーが延長を承認したときだけ SKILL が 3 を渡す）以上なら、起動せずに `ADVERSARIAL_VERDICT: LIMIT` を出して exit 4。見る範囲 `REVIEW_BASE` は、周に数えた（`ROUNDS:` が 1 以上・行が無い記録は 1）最新の記録の `REVIEWED_COMMIT`、無ければ `origin/develop`（`ROUNDS: 0` の記録は飛ばす。計画変更記録 4）。`git diff` が失敗したら `ADVERSARIAL_ERROR: DIFF` で exit 2。
3. 前提の確認: 計画書 `docs/plans/open/plan_I###.md`（無ければ closed）の一覧の節を読む。節の見出しは、コードブロック（```）の外の行で、行全体が `## 必ず確かめる項目` か、その直後に全角の `（` で始まる括弧書きが続くもの（例: `## 必ず確かめる項目（I197 自身の敵対的レビューが使う）`）だけを認める（`###` などの別の階層・文言の違いは認めない）。節は次の `## ` の見出しまで。その中の表の行（見出しと区切りの行を除く）を読む。1 行の形は `| V<n> | <観点 1〜3> | <実験必須 か 読んで可> | <内容> |`。表が無い・0 行・形の違う行がある → `ADVERSARIAL_ERROR: CHECKLIST` を出して exit 2（記録は作らない。gate-check は記録が無いので通さない）。記録の場所の外にコミットしていない変更がある → exit 2（実験役が作業ツリーを変えたかを比べられないため）。HEAD を `REVIEWED_COMMIT` として控える。
4. 3 観点（今の固定 3 観点: 1 ロジック回避・実機 repro／2 テストの false-green・tautology／3 要件・脅威モデルの網羅漏れ）を並列に起動する（スクリプト内の background。親の会話は 1 本の background の Bash を待つだけ）。各観点:
   - レビュー役: `claude -p --agent adversarial-reviewer --tools "Read,Grep,Glob" --permission-mode manual --permission-prompts none --output-format stream-json --verbose --max-budget-usd ${ADV_REVIEW_BUDGET:-2}`。入力（標準入力に渡す 1 つの文章）は ISSUE・PERSPECTIVE・REVIEW_BASE・その観点の項目・全項目・過去の記録のパス（既知 findings として Read させる）・実験の約束に加えて、スクリプトが取った「変更ファイルの一覧」（`git -c core.quotePath=false diff --name-status --no-renames <REVIEW_BASE>...HEAD`）と「差分」（`git diff <REVIEW_BASE>...HEAD` の先頭 100KB。切ったときは「差分は 100KB で切った。続きは一覧のファイルを Read で読む」と書き足す）を含める（レビュー役は Bash を持たず `git diff` を実行できないため。code-review.sh が code-reviewer に差分を渡す形と同じ）。イシューファイルと計画書のパスも渡し、Read で読ませる。
   - 実験案があり、往復が `ADV_EXPERIMENT_ROUNDS`（既定 2）未満で、締め切りまで `ADV_MIN_STEP`（既定 60 秒）以上残っていれば、実験役を起動する: `claude -p --model haiku --tools "Bash" --permission-mode auto --permission-prompts none --setting-sources user --settings .claude/settings.json --strict-mcp-config --no-session-persistence --max-budget-usd ${ADV_EXEC_BUDGET:-0.5} --output-format stream-json --verbose`（S3 と同じ形）。入力は「各実験のコマンドを、変えずに Bash で 1 回ずつ実行し、ほかの道具は使わない」。
   - 実験の結果（実験ごとに 実行した／拒否された／呼ばれなかった、出力の先頭 2000 字、`is_error`）を、`claude -p --resume <session_id>`（レビュー役と同じ引数）で渡して続きを書かせる。
   - 各呼び出しの時間上限は「締め切りまでの残り」と `ADV_STEP_TIMEOUT`（既定 300 秒）の小さい方。締め切りは起動から `ADV_DEADLINE`（既定 600 秒＝1 周 10 分）。
5. 実験役の後と全観点の終了後に、作業ツリー（記録の場所の外のファイル・HEAD・ブランチ）を起動時と比べ、変わっていたら周全体の実験をすべて「無効（作業ツリーを変えた）」にし、変わったものを記録に書く（実験は同じ作業ツリーで並列に動くので、どの観点が変えたかは決めない。消さない・戻さない。VERDICT は HIGH。計画変更記録 4）。往復を始めるのは、実験役と続きの 2 回分（`2 × ADV_MIN_STEP`）の時間が残っているときだけ。続きの呼び出しが終わらなかったときは、前に成功した呼び出しの本文で判定する。止められたとき（EXIT・INT・TERM）は背景の観点と子プロセスを `kill_tree` で止める。
6. 判定（決定論。§4.3.1）を出し、記録 `docs/reviews/I###_adversarial_review_<YYYYMMDD_HHMM>.md` を書いて `commit_review_artifact` でコミットする。標準出力の最後に機械可読行 `ADVERSARIAL_RECORD: <path>`・`UNVERIFIED: <件数>`・`NEW_CRITICAL: <合計>`・`NEW_HIGH: <合計>`・`ADVERSARIAL_VERDICT: <OK|HIGH|BLOCKER>` を出す。
7. 終了コード: 0=OK／1=HIGH か BLOCKER（指摘・未検証あり。3 観点とも報告した）／3=報告の無い観点がある（時間切れ・失敗・機械可読行が無い。記録は `ROUNDS: 0`）／4=周回の上限／2=実行できない（引数・一覧・作業ツリー）。

#### 4.3.1 判定の規則（AC4・AC5）
- レビュー役の報告は、最後の応答の本文の行頭の機械可読行だけを読む（アンカー付きの完全一致。`reference_string_token_match_anchoring`）:
  - `ITEM: V<n> RESULT=<experiment|read|not_done>[ EXP=<id>[,<id>…]]`
  - 実験案: `EXPERIMENT_BEGIN <id>` の次の行から `EXPERIMENT_END <id>` の前の行までがコマンド（複数行可）
  - 最後の 2 行: `NEW_CRITICAL: <数>`・`NEW_HIGH: <数>`
- 観点の終わり方: 「報告あり」＝最後の呼び出しが exit 0 で、`result` の行の `subtype` が `success`、本文に `NEW_CRITICAL:`・`NEW_HIGH:` の行がある。それ以外（時間切れ 124・失敗・空・行が無い）は「報告なし」で、その観点の項目はすべて未検証。
- 項目ごとの判定（項目の持ち主は一覧の観点の列）:
  - `実験必須`: 持ち主の報告が `RESULT=experiment` で、`EXP=` の実験のうち 1 つ以上が、実験役の記録で「実行した」（`tool_use` の `command` がコマンドと完全一致し、その `tool_use_id` が `permission_denials` に無く、`tool_result` がある）、かつこの周の実験が作業ツリーを変えていない → 確認済み（実験）。実験のコマンドが非ゼロで終わった（`is_error=true`）ことは未検証の理由にしない（反証の実験は「拒否されることを確かめる」形が多く、結果の解釈はレビュー役の読み。出力の先頭は記録に残る）。それ以外 → 未検証。
  - `読んで可`: 持ち主の報告が `RESULT=read` か、上の条件を満たす `RESULT=experiment` → 確認済み。それ以外 → 未検証。
  - 報告に項目の行が無い・`not_done` → 未検証。
- VERDICT: `NEW_CRITICAL` の合計が 1 以上 → BLOCKER。そうでなく `NEW_HIGH` の合計が 1 以上・未検証が 1 件以上・報告なしの観点がある・作業ツリーを変えた → HIGH。どれも無ければ OK。
- `ROUNDS:` は、3 観点とも報告ありなら 1、報告なしの観点があれば 0（周として数えない。SKILL が 1 回だけやり直す）。

#### 4.3.2 記録の形（gate-check が読む行は今と同じ）
```
# 敵対的レビュー [I###]（別プロセス・<YYYY-MM-DD HH:MM>）
- 見た範囲: <REVIEW_BASE>...<HEAD>
- 所要時間: <秒>（上限 <ADV_DEADLINE>）
- 人の応答待ち: 0（レビュー役・実験役はすべて --permission-prompts none で起動。拒否 <件数> 件は下の表）

## 確かめる項目の結果
| 項目 | 観点 | 確かめ方 | 報告 | 実験 | 判定 |

## 観点ごとの実行
| 観点 | 終わり方 | 所要 | 実験の往復 | 拒否 | 最後のツール呼び出し | その結果（先頭） | 最後の出来事からの経過 |

## 実験（観点ごと・実行した／拒否された／呼ばれなかった・出力の先頭）

## 各観点の報告（本文。機械可読行は無害化して貼る）

NEW_CRITICAL_TOTAL: <数>
NEW_HIGH_TOTAL: <数>
UNVERIFIED: <数>
REVIEWED_COMMIT: <SHA>
ROUNDS: <0|1>
VERDICT: <BLOCKER|HIGH|OK>
```
- 「最後のツール呼び出し」「その結果」「最後の出来事からの経過」は、報告ありの観点では「―」、報告なしの観点では `stream-json` から取り出す（S4）。経過は、ライブラリが各行に付けた受け取り時刻から出す（§4.4）。
- 各観点の本文は `neutralize_machine_lines` で行頭の `VERDICT:` などを無害化して貼る（レビュー役の本文や引用が判定の行として読まれない）。`ITEM:`・`EXPERIMENT_BEGIN` も同じ関数の対象に足す。

### 4.4 新規 `scripts/claude/review-process-lib.sh`（別プロセスのレビュー役を起動し、記録を読む関数）
修正方針: `claude -p` を「時間上限つき・承認なし・途中の出力をすべて残す」形で起動し、その記録から結果・拒否・最後の呼び出しを取り出す処理を 1 か所にまとめる（adversarial-review.sh と code-review.sh が使う）。
- `run_claude_logged <秒> <ログ> <入力ファイル> <claude の引数…>`: `timeout <秒> "${CLAUDE_BIN:-claude}" -p <引数…> --output-format stream-json --verbose < <入力>` を実行し、標準出力の各行の先頭に受け取り時刻（epoch 秒）とタブを付けてログに書く（python3 -I -u の小さなフィルタ）。claude の終了コードを返す（124 は時間切れ）。`--permission-prompts none` が引数に無ければ呼ばずに 2 を返す（承認なしを付け忘れた呼び出しを仕組みで止める）。
- `claude_log_result <ログ>`: 最後の `type=result` の `result`（本文）を出す。無ければ何も出さず 1。
- `claude_log_session <ログ>`: `session_id`。
- `claude_log_denials <ログ>`: `permission_denials` の各要素を `<tool_use_id>\t<コマンドの先頭>` で出す。読めなければ 2（形が変わったら「拒否なし」と言わない）。
- `claude_log_ran <ログ> <コマンド>`: そのコマンドと完全一致する Bash の `tool_use` があり、拒否されておらず、`tool_result` がある → 0。出力の先頭 2000 字と `is_error` を出す。拒否 → 10。呼ばれていない → 1。
- `claude_log_last_tool <ログ>`: 最後の `tool_use` の名前と入力の先頭 120 字・その `tool_result` の先頭 120 字・最後の行の時刻からログを閉じた時刻までの秒数を、タブ区切りで出す。
- テスト用: `CLAUDE_BIN` で claude を差し替えられる（スタブが渡された引数を記録し、用意した stream-json を出す）。

### 4.5 既存ファイルの変更
| ファイル | 変更内容 |
|---|---|
| `.claude/skills/review-gate/SKILL.md` §3 | 3-0〜3-4 を書き直す。Agent ツールでの起動・タイマー・`TaskStop` をやめ、`bash scripts/claude/adversarial-review.sh "$ARGUMENTS"` を Bash ツールの `run_in_background: true` で 1 回呼ぶ。終了コードで分岐: 0→通過／1→3-3 で直し、基本レビュー（1.）を通り直してから次の周／3→同じ周を 1 回だけやり直し、2 回続けば止める（止める条件 3）／4→上限到達（今の選択肢の出し方のまま）／2→原因が記録の場所で直せる（一覧を計画に足す・形を直す）なら直して 1 回だけやり直し、直せなければ止める／`ADVERSARIAL_VERDICT:` 行が無い→1 回だけやり直し、2 回続けば止める。未検証の項目の直し方: 実験が拒否された・時間が足りなかった項目は、その項目を確かめる決定論の TC（注入つき）を auto_test に足し、一覧のその行の内容に `TC-xx` を書き足して次の周へ（一覧の確かめ方を「読んで可」に下げるのは、決定論の TC で覆ったときだけ。計画変更記録に 1 行。方式・範囲・受け入れ条件は変えないので計画レビューは通り直さない）。上限・延長・受け入れの記録・PR コメント（`post-review-comment.sh`）・最終判定 = max(基本レビュー, 敵対的レビュー) は今のまま |
| `.claude/agents/adversarial-reviewer.md` | `tools: Read, Grep, Glob`（Bash を外す）。「時間と攻め筋の上限」を「1 周 10 分（スクリプトが締め切る）・攻め筋は最大 3 本・実験の往復は 2 回まで」に。「ツール境界」「実機 repro」を「実験は自分で実行せず、実験案（`EXPERIMENT_BEGIN`/`END`）で返す。実験役が変えずに実行し、結果が次の入力で返る。作業ツリーに書く実験は無効になる（/tmp か scratchpad に書く）。資源の上限（`ulimit -v 2097152`・`timeout 60`）は実験のコマンドに含める」に。出力の形に `ITEM:` 行（項目ごと・全項目）を足す。守る範囲（I181）はそのまま |
| `.claude/agents/plan-reviewer.md` | 高リスク判定に当たりうる計画（code-reviewer の高リスク条件・`path_risk_trigger()` のパス）に `## 必ず確かめる項目` の表が無い、または確かめ方が `実験必須`／`読んで可` 以外の行がある → High、を 1 項目足す |
| `scripts/claude/code-review.sh` | ①組み込みのレビュー（`run_official_review`）の `claude -p` に `--permission-prompts none` を足す ②code-reviewer の呼び出しを `run_claude_logged`（§4.4）に変え、本文は `claude_log_result` で受け取る。時間切れ・失敗・空のときの BLOCKER の記録に、最後のツール呼び出し・結果・経過（`claude_log_last_tool`）を足す ③`neutralize_machine_lines` の対象に `ITEM`・`EXPERIMENT_BEGIN`・`EXPERIMENT_END`・`UNVERIFIED`・`ADVERSARIAL_VERDICT`・`NEW_CRITICAL_TOTAL`・`NEW_HIGH_TOTAL` を足す |
| `scripts/claude/plan-issue-review.sh`・`scripts/claude/issue-review.sh`・`scripts/claude/fix-review-lib.sh` | `claude -p` に `--permission-prompts none` を足すだけ（作り直さない。設計確認メモ 6。読む道具だけでも、作業フォルダの外を読むときなどに承認を求める経路が残らないよう、全部の呼び出しで仕組みとして保証する） |
| `scripts/claude/review-timer.sh` | 削除（呼び出し元は review-gate 3-1 だけで、新しい形では使わない） |
| `scripts/claude/tests/test_i181_review_slim.sh` | D1・D4 と FG-D1・FG-D4 の固定する語を新しい決まり（`adversarial-review.sh`・`10 分`・`実験の往復は 2 回`・`ITEM:`・`EXPERIMENT_BEGIN`・`ulimit -v`・`timeout 60`・周回の数え方）に付け替える。守る範囲（D4_SCOPE）はそのまま |
| `scripts/claude/tests/test_i193_official_flow.sh` | R4 の tools の確認から adversarial-reviewer の例外（Bash）を外す（7 本すべて `Read, Grep, Glob`）。S17 を「review-gate は `bash scripts/claude/adversarial-review.sh` を呼び、`review-timer.sh`・`subagent_type`・`TaskStop` が無い・PR コメントはスクリプト経由」に付け替える（review-timer.sh の引数のテストは削除） |
| `docs/runbooks/review-rules.md` | 「高リスク変更の敵対的レビューステージ」の上限の行を新しい形に書き直し、その前に「検証の全体設計（I197）」の節（§4.1 の表と分担）を足す |
| `docs/runbooks/workflow.md` | 流れの 4 番目の行の「高リスクなら敵対的レビュー」を「高リスクなら敵対的レビュー（別プロセス・読むだけ・1 周 10 分・確かめる項目の一覧で判定。`scripts/claude/adversarial-review.sh`）」に |
| `docs/plans/templates/plan_template.md` | §9 の後に `## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）` の節と表の見出し（`| 項目 | 観点 | 確かめ方 | 内容 |`）・書き方の注（観点 1〜3 の意味・`実験必須`／`読んで可`・決定論の TC で覆える項目は TC を先に考える・高リスクに当たりうる計画では必須）を足す |
| `docs/tests/templates/auto_test_template.md` | 変更しない（一覧は計画書に置き、TC は今の書き方のまま参照する。イシューの「欄を足す」はテンプレートの計画書側で満たす） |
| `scripts/claude/gate-check.sh` | 変更しない（新しい記録も最後の `VERDICT`・`REVIEWED_COMMIT` の行を同じ形で書くため。互換は TC-01 で確かめる） |

### 4.6 I194・レビュー時間の原因調査の扱い（AC8）
- I194（#328・敵対的レビューの範囲を例外ファイルに絞る）: 統合して取り下げる。理由: 「何を確かめるか」を例外ファイルで決める考え方は、本イシューの「計画の段階で確かめる項目の一覧を作り、その項目だけを判定に使う」に含まれる（範囲は一覧で絞られる）。実装の最後に #328 にコメント（統合先 #332 と理由）を書き、`not planned` で閉じる。I194 のイシューファイルは harness-2 ワークツリーに未追跡で残っているため、このセッションからは触らない（トラックの境界。close の報告でユーザーに伝える）。
- レビュー時間の原因調査（I193 後に起票予定）: 起票しない。理由: 新しい記録が観点ごとの所要時間・往復・最後の呼び出しを毎回残すので、上限（10 分）と比べれば原因が記録から分かる。デスクトップの起票コマンドの扱いは close の報告でユーザーに伝える。

### 4.7 I197 自身の一覧
- I197 自身の敵対的レビューが使う一覧は、スクリプトが読む形のまま、この計画書の `## 必ず確かめる項目（I197 自身の敵対的レビューが使う）` の節（計画変更記録の前）に置く。

## 5. 実装手順（ステップ）
未知リスク（S1〜S4）は計画の前にスパイクで成立を確かめた（調査結果）。手順は「1 周を通しで動かす最小の形」を先に作る（垂直スライス）。

1. **ライブラリと段取りの最小形**: `scripts/claude/review-process-lib.sh` と `scripts/claude/adversarial-review.sh`（§4.3・§4.4）を作る。スタブの claude で 1 周（報告→実験→続き→判定→記録）を通すテスト `scripts/claude/tests/test_i197_adversarial_process.sh` を同時に作る（→ TC-01）。
2. **レビュー役の定義**: `.claude/agents/adversarial-reviewer.md` を §4.5 のとおり直す（ステップ 1 の入力の約束と合わせる。ステップ 1 が前提）。
3. **review-gate の手順**: `.claude/skills/review-gate/SKILL.md` §3 を書き直し、`scripts/claude/review-timer.sh` を消す（ステップ 1・2 が前提）。
4. **他の `claude -p` の承認なし**: `code-review.sh`・`plan-issue-review.sh`・`issue-review.sh`・`fix-review-lib.sh` を §4.5 のとおり直す（→ TC-02。ステップ 1 のライブラリが前提。ステップ 2・3 と並行してよい）。
5. **文書・テンプレート・計画レビュー役**: `review-rules.md`・`workflow.md`・`plan_template.md`・`plan-reviewer.md`（§4.1・§4.5）。
6. **既存テストの付け替え**: `test_i181_review_slim.sh`・`test_i193_official_flow.sh`（→ TC-03・TC-04）。全テスト（→ TC-07）。
7. **I194 の取り下げ**: #328 にコメントして閉じる（§4.6。→ 手動 No.4）。
8. 実地の通し（AC6）は test-gate の手動テスト No.1・No.2 で行う（実装の後でないと動かない）。

## 6. テスト計画
### 自動（詳細は docs/tests/open/I197_auto_test.md）
- TC-01 新設 `test_i197_adversarial_process.sh`（スタブの claude・一時の git リポジトリ。判定・記録・止まり方・gate-check との互換と、その FG）
- TC-02 全部の `claude -p` に `--permission-prompts none`（TC-01 の中の静的な検査＋FG）
- TC-03〜TC-06 既存テストの付け替え・そのまま通ること
- TC-07 `run-all.sh`、TC-08 見張り・settings.json を変えていない
- テストレベル: ハーネスの単体（関数）と結合（スクリプト全体をスタブで通す）。実際の claude を使う通しは手動テスト（Claude が実施）
### 手動（詳細は docs/tests/open/I197_manual_test.md・実施者はすべて Claude）
- No.1 実際の claude で I197 に adversarial-review.sh を通す（AC6 ①②③）
- No.2 実験役に、許可される実験（波かっこを含む heredoc）と見張りが確認を求める実験を渡し、待たずに実行／拒否が記録される（AC3・AC7）
- No.3 review-gate の手順を読み、終了コードごとの分岐が §4.5 と一致する
- No.4 #328 のコメントと閉じた状態（AC8）

## 7. ロールバック
- PR を revert する（ハーネスの文書・スクリプトだけ。データの変更なし）。revert で `review-timer.sh` と今の SKILL §3 が戻る。
- 新しい仕組みが実地で動かないとき（手動 No.1 が不成立）は、計画をやり直す（I166 延長周の形で回す運用に戻る）。

## 8. Risk & 回避策
| リスク | 回避策 |
|---|---|
| 実験役（auto・Bash あり）が、レビュー役の書いた実験案（リポジトリの文章に誘導されたものを含む）で危ない操作をする | 実験役は `--setting-sources user --settings .claude/settings.json` で、見張り（PreToolUse）・settings の deny（curl・push の develop/main・force など）・auto の判定がそのまま効く（S3 で見張りの確認が拒否になることを確認）。承認が要るものは待たずに拒否。作業ツリーの変化は判定で HIGH にする（消さない）。守る範囲は「普通の書き方の事故」（I181。わざと回避する書き方は対象外）。I166 延長周では親（auto）が同じ実験を実行していたので、危なさは今より増えない |
| `--permission-mode auto` が使えない環境（アカウント・バージョン） | 実験役の `init` の `permissionMode` が `auto` でなければ、その実験はすべて「呼ばれなかった」扱い（実験必須の項目は未検証＝止まる側）。記録に理由を書く |
| claude の出力の形（`stream-json`・`permission_denials`）が変わる | 読めないときは「拒否なし」「実行した」と言わず、判定できない側（未検証・報告なし）に倒す（check-permission-prompt.sh と同じ考え方） |
| 10 分では足りず未検証が増え、サクサク進まない | 往復・上限は環境変数で調整できる。未検証の直し方（決定論の TC で覆う）を SKILL に書く。実測は手動 No.1 で記録し、retro で見直す |
| レビュー役が `ITEM:` 行を書き忘れる | 未検証になり HIGH（止まる側）。定義に出力の約束を明記し、入力にも項目の一覧と行の書き方を毎回渡す |
| 3 観点の並列で費用が増える | 1 呼び出しごとに `--max-budget-usd`（レビュー役 2・実験役 0.5。最悪の合計は §12）。今の Agent ツールの 3 体と同じ数。追加の有料サービスは無い |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 方式は (d) 別プロセス `claude -p --agent adversarial-reviewer`・tools は Read/Grep/Glob・`--permission-prompts none`・実験は実験案として返し親が実行（1 体 2 往復まで）。(a) は捨てる・(c) は代わりにしない・(e) は併用・(f) は費用のかからない決定論だけ
- 1 周 10 分以内。超えた観点は未検証
- 一覧は計画の段階で作り、項目ごとに「実験必須／読んで可」。未検証が 1 件でも残れば合格にしない
- 見張りと `.claude/settings.json` は変えない（I200）
- I194 は統合して取り下げ・レビュー時間の原因調査は起票せず統合
- 計画レビュー・イシューレビューは作り直さない（テンプレートへの欄の追加まで）

Claude が決めた（技術的な選択と理由）:
- 「親が実行」は、親の会話ではなく、review-gate が呼ぶスクリプト（親の段取り）が起動する実験役の別プロセス（auto＋承認なし）で行う — 親の会話で実行すると、親が自動承認モードでないときに確認画面で人を待つ（AC6 ①の 0 を仕組みで保証できない）。S3 で、普通の実験は通り承認が要るものは待たずに拒否されることを確かめた。設計確認メモの「レビュー役は読むだけ・実験は別が実行」の形は変えない（要件・基本設計の変更ではない）
- 実験役のモデルは haiku — コマンドを変えずに実行するだけで、判断はしない（check-permission-prompt.sh と同じ）
- 構造化出力（`--json-schema`）は使わず、行頭の機械可読行で受け取る — S1 で `--agent` と組み合わせると `structured_output` が空だった
- 一覧は計画書に置く（auto_test には置かない） — 計画レビューで一覧を確かめる（設計確認メモ 3）ため、計画書が正
- 報告なしの観点がある周は `ROUNDS: 0`（周に数えない）で 1 回だけやり直す — 基盤の失敗で周の上限を使い切らないため。2 回続けば止める（止める条件 3）
- 一覧が無いときは記録を作らず exit 2 — 何も確かめていない周を記録に残すと周の数え方が乱れる。gate-check は記録が無いと通さないので止まる側
- 実験役が作業ツリーを変えたら HIGH にするが、ファイルは消さない・戻さない — 戻す操作は危険操作に当たりうる。人か次の修正で扱う
- 他のレビュー役（計画・イシュー・fix）は `--permission-prompts none` を足すだけ — AC3 を全部の検証で仕組みとして保証する最小の変更。作り直しはしない（設計確認メモ 6）
- fix-loop の 3 つのレビューは時間切れで SKIP（非ブロック）のまま — fix-loop は必ず review-gate に戻り、最後の判定は review-gate が出す。最終のゲートではないので、ここで止める側に倒すと修正の往復が止まるだけになる
- `gate-check.sh` は変えない — 記録の最後の行の形を保つ（互換を TC-01 で固定）
- `review-timer.sh` は消す — 呼び出し元が無くなる。残すと古い手順に戻る足がかりになる
- 周回の数え方と REVIEW_BASE の決め方は SKILL の文からスクリプトに移す — 決定論にし、テストで固定するため

セキュリティ・ベストプラクティスチェック:
- アプリのコード変更なし。入力（レビュー役の本文・実験の出力）は判定の行だけをアンカー付きで読み、記録に貼るときは機械可読行を無害化する（V8）
- 最小権限: レビュー役は読む道具だけ。実験役は Bash だけで、許可は settings（変えない）と auto の判定・見張りに従い、承認が要るものは拒否
- 機密: 実験役も settings の `Read(**/.env)` などの deny が効く。記録に貼る出力は先頭 2000 字まで。秘密情報の push は既存の pre-commit・push protection（変えない）
- 依存ライブラリの追加なし（pip-audit / npm audit 非該当）。bandit・npm audit の重大度基準は非該当（Python・JS のアプリのコードを変えない）
- セキュリティ影響: ハーネスの検証の仕組みの変更。アプリのセキュリティ影響なし

P3/P5/P8 影響なし（DB・外部 API・非同期処理なし。`claude -p` の起動は今の code-review.sh と同じ種類）。P6 影響なし（UI・データ量なし）。P9 影響なし（個人情報・テナントデータを扱わない）。

設計判断の区別: 上の「イシューに明記」以外はすべて技術的な仮定で、要件・基本設計・UI/UX の価値判断に当たるものは無い（止めない）。

Danger Ops（有無/手順/ロールバック）:
- 無。`review-timer.sh` の削除は feature ブランチのファイル削除（revert で戻る）。#328 を閉じるのは設計確認メモでユーザーが決めた取り下げ（再オープンで戻る）

## 12. コスト・保守見積もり
- 実行の費用: 1 周で レビュー役 3 観点 ×（最初＋往復 2 回まで）＋実験役 最大 6 回。上限は呼び出しごとの `--max-budget-usd`（レビュー役 2・実験役 0.5）。最悪の合計は 2×3 観点×3 呼び出し＋0.5×6 回＝$21（実際は S1・S2 の 1 回 $0.07 前後から見てずっと小さい見込み。手動 No.1 で実際の値を記録し、retro で既定を見直す）。今の Agent ツールの 3 体と同じ契約の範囲で、追加の有料サービスは無い
- 保守: 自作はスクリプト 2 本（段取り・ライブラリ）とテスト 1 本。claude の出力の形の変化はライブラリ 1 か所で受ける。運用者の手作業は増えない（親は 1 本の background の実行を待つだけ）

## 必ず確かめる項目（I197 自身の敵対的レビューが使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 実験必須 | `RESULT=experiment` と報告しても、実験役の記録で実行されていない（拒否・不一致・呼ばれない）なら未検証になり VERDICT が OK にならない（スタブの claude で adversarial-review.sh を動かして確かめる。TC-01 A3・A4） |
| V2 | 1 | 実験必須 | 観点の 1 つが時間切れ（124）・空・機械可読行なしのとき、exit 3・`ROUNDS: 0`・VERDICT HIGH になり、記録に最後のツール呼び出し・結果・経過が出る（TC-01 A5） |
| V3 | 1 | 実験必須 | 実験役が作業ツリーを変えたとき、その観点の実験が無効になり VERDICT が HIGH になる（TC-01 A8） |
| V4 | 1 | 読んで可 | 周回の数え方（ROUNDS の合計・行の無い記録は 1・`ADV_ROUND_LIMIT`）と `REVIEW_BASE` の決め方が今の SKILL 3-1 の 1・2 と同じ（TC-01 A9） |
| V5 | 2 | 実験必須 | TC-01 の判定の要の行（未検証を HIGH にする・実験の照合・報告なしを未検証にする）を一時コピーで壊すと TC-01 が落ちる（FG） |
| V6 | 2 | 読んで可 | TC-02（全部の `claude -p` に `--permission-prompts none`）が、1 か所外した写しで落ちる |
| V7 | 3 | 読んで可 | 受け入れ条件 AC1〜AC11 のすべてに、TC か手動テストの行が対応している |
| V8 | 3 | 読んで可 | レビュー役の本文・実験の出力に `VERDICT: OK`・`ITEM:` などを書かれても、判定と gate-check の読む行がすり替わらない（無害化・アンカー・最後の行だけ） |
| V9 | 3 | 読んで可 | 実験役（auto・Bash あり）が実行してよい範囲の決まり（見張り・settings の deny・auto の判定・作業ツリーの比較）が、レビュー役の書いた実験案による事故（push・削除・作業ツリーの書き換え）を普通の書き方で止める。守る範囲は「普通の書き方の事故」（I181）で、作業ツリーの外（/tmp など）の書き込みは対象外（S3 と同じ前提・計画変更記録 1） |
| V10 | 3 | 読んで可 | レビュー役の入力に、変更ファイルの一覧と差分（100KB まで・切ったときの注記）が入っていて、レビュー役が Bash 無しで変更箇所を特定できる（TC-01 A12） |

## 計画変更記録
1. 2026-10-26 計画レビュー（`I197_plan_review_20261026_0711.md`・BLOCKER 2・Warning 4・Info 1）への対応
   - B1（一覧の見出しが読む形と違う）: I197 自身の一覧を `## 必ず確かめる項目（…）` の節としてトップレベルに移し、見出しの照合規則（コードブロックの外・`## ` の階層・`必ず確かめる項目` の直後は行末か全角の `（`）を §4.3 の 3 に書いた。TC-01 A10 に見出し違い（`###`・文言違い）を足した
   - B2（レビュー役に差分を渡す方法が無い）: スクリプトが変更ファイルの一覧と差分（100KB まで）を入力に入れる、と §4.3 の 4 に書いた。一覧に V10・TC-01 A12 に確かめる項目を足した
   - W（実験役の作業ツリーの外への影響）: 守る範囲は I181 の「普通の書き方の事故」のまま（作業ツリーの外は見張り・settings の deny・auto の判定に任せる。I166 延長周で親〔auto〕が同じ実験を実行していた範囲と同じ）。精密な検知は作らない（`feedback_local_guard_github_last_line`）。V9 にその前提を書いた
   - W（手動 No.2 の関数名・読み込み方）: §4.3 の 1 に source-only の形と主な関数名（`run_experiment_agent` など）を書いた
   - W（S6 の比べる相手）: S6 を「比べる相手との merge-base から HEAD まで」に変えた（I200 が先にマージされても落ちない）
   - W（費用の上限）: 既定をレビュー役 2・実験役 0.5（ドル・1 呼び出し）に下げ、最悪の合計を §12 に書いた。実際の費用は手動 No.1 で記録し、retro で既定を見直す
   - Info（計画変更記録）: この記録を足した
   - 計画レビューのやり直し: 要（一覧の形・入力の仕様を変えたため）
2. 2026-10-26 2 回目の計画レビュー（`I197_plan_review_20261026_0713.md`・OK・Warning 4・Info 2）への対応: FG-A8・FG-A9・FG-A10 を auto_test に足した。S1 を行末の `\` でつないだ論理行で見る形にした。§3 の変更の数を 4 に直した。費用の実測は手動 No.1 で記録する（済み）。auto の挙動の差は init のモードで止まる側に倒す設計のまま。節番号の飛び（§10・§11 は条件付きの節で該当なし）はそのまま。計画レビューのやり直し: 不要（方式・範囲・受け入れ条件を変えない、テストの追加と数の訂正だけ）
3. 2026-10-26 implement（/simplify の 4 観点の後）:
   - 計画書の記載: §4.5 code-review.sh「code-reviewer の呼び出しを run_claude_logged に変える」。採った方法: review-process-lib.sh の読み込みは code-review.sh の本体（関数だけを読み込む使い方の後）に置いた。理由: 既存のテスト（test_adversarial_trigger.sh の FG-P1）は code-review.sh を別の場所に写して関数だけを読み込むため、写し先にライブラリが無く読み込みが失敗した。関数だけを使う側（gate-check・adversarial-review.sh・テスト）は、要るときに自分でライブラリを読む
   - 記録の「観点ごとの実行」の表に「費用」（各ログの total_cost_usd の合計）の列を足した。理由: 手動 No.1 で費用を記録する計画だったが、ログは一時フォルダにあり実行の後に消えるため、記録に残さないと見直しの材料が残らない
   - `scripts/claude/tests/test_review_gates.sh`（計画の一覧に無かった）の TC-WIRE3 は、code-reviewer の呼び出しの行（`claude -p --agent "$REVIEWER_AGENT"`）を目印に順番を確かめていたので、目印を `--agent "$REVIEWER_AGENT" --tools` の行に付け替えた（確かめる中身は同じ）
   - 既定値を冒頭で 1 回だけ決める・`run_step` に締め切りの処理をまとめる・重複した状態のファイル（exp_ids）をやめる、の整理をした（動きは変えない）
   - 見送り（retro で扱う）: 全部の `claude -p` を 1 つの起動口に寄せる・`neutralize_machine_lines` を語の一覧でなく形で無害化する・記録の探し方と REVIEWED_COMMIT の読み方を gate-check.sh と共有する・check-permission-prompt.sh の記録の読み方をライブラリに寄せる・実験役を使い捨てのワークツリーで動かす・テストの並列化。どれも計画の範囲（他のスクリプトの作り直し・gate-check.sh は変えない）を外れるか、方式の変更になる
   - 計画レビューのやり直し: 不要（方式・範囲・受け入れ条件を変えない）
4. 2026-10-26 fix-loop 2 回目（基本レビュー 2 回目 `I197_code_review_20261026_2124.md` の BLOCKER・診断メモ `I197_fix_diagnosis_20261026_2140.md`）:
   - 起点は `ROUNDS: 0` の記録を飛ばす（Blocker: 報告の無い周のやり直しが空の差分で OK を出しうる）。往復の前に 2 回分の時間を見る・続きの失敗で前の報告を消さない（High）。作業ツリーの比較に HEAD・ブランチを足し、観点ごとではなく周全体で無効にする。`trap` で背景の観点を止める。扱い済みの実験の id を上書きしない。`git diff` の失敗で止める。記録に貼るコマンドも無害化する（Medium・Low）。§4.3 の 2・5 と §4.3.1 の文を合わせて直した
   - 採らなかった指摘: 非ゼロで終わった実験を未検証にする（Medium 6）— 反証の実験は非ゼロの終了を期待する形が多く、誤った未検証が増えるため。gate-check.sh との共有（Low 10）— 計画変更記録 3 のとおり retro
   - テスト: TC-01 に A16〜A22 と FG-A16・A17・A18・A21・A22 を足した。FG-A3・FG-A8 の置き換え前の文字列を新しい形に合わせた
   - 計画レビューのやり直し: 不要（指摘への対応で、方式・範囲・受け入れ条件を変えない）
5. 2026-10-26 fix-loop 3 回目（基本レビュー 3 回目 `I197_code_review_20261026_2159.md` の HIGH・診断メモ `I197_fix_diagnosis_20261026_2210.md`）:
   - 続きの呼び出しが終わらなかったときは、直前の往復で実行した実験を「結果は読まれていない」（`unread`）にし、実験必須を満たさない（High）。§4.3.1 の「実行した」は `ran` だけ
   - 作業ツリーの比較を、記録の場所を除いたファイル一覧から「起動時の状態（status の各行＋中身のハッシュ）」との比較に変えた。実験が計画書・過去の記録を書き換えても（起動前から変更済みのファイルでも）周全体を無効にする（§4.3 の 5）
   - 実験案の先頭・末尾の空行を除く。`claude_log_last_tool` の空の欄を `-` で埋める
   - 見送り（自律判断の記録）: 非ゼロ終了の区別・auto の関門の記録・最後の比較の後の孫プロセス・Low 2 件
   - テスト: TC-01 に A23〜A26 と FG-A23・FG-A26
   - 計画レビューのやり直し: 不要（指摘への対応で、方式・範囲・受け入れ条件を変えない）

## レビュー結果
- [20261026_0713 判定: ✅ 完了](../../reviews/I197_plan_review_20261026_0713.md)
- [20261026_0711 判定: 差し戻し（Blocker 2件）](../../reviews/I197_plan_review_20261026_0711.md)
