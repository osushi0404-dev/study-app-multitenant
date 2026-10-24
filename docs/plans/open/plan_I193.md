# I193 計画書: 開発の流れを公式の道具を土台に組み直す

## 基本情報
- **計画書ID**: plan_I193
- **関連イシュー**: #326
- **Draft PR**: #327
- **作成根拠資料**: docs/issues/open/I193.md（起点イシュー）・docs/proposals/I193_official_base_flow.md（設計書・本計画と同時に作成）
- **実装後評価**: docs/reviews/open/I193_review.md
- **作成日**: 2026-10-24

## 1. 背景/目的
- 背景: 開発の流れ（/plan-issue → /implement → /code-review → /test → /retro → /close）は自作を積み上げて作ってきた。I185 は「今の自作を公式で置き換えられるか」から点検したため、公式を土台にした流れが描かれず、`/simplify` などは候補にも載らなかった。ユーザーの確認も 4 か所（イシュー・計画の承認・人の手動テスト・マージ）に残っている。
- 目的: 計画からクローズまでを、公式の道具を土台に組み直す。自作は公式だけでは止まらない漏れを止める部分だけにする。ユーザーの確認は「人がやる手動テスト」と「マージ」だけにし、途中で止めて聞くのは 3 つの条件のときだけにする（イシュー I193 設計確認メモ）。

## 2. 受け入れ条件
イシュー I193 の「受け入れ条件」14 項目をそのまま採用する（この計画で項目を足したり削ったりしない）。各項目と確かめ方の対応は §6 の表に書く。

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra:
  - `.claude/skills/`（12 本。改名 4・新設 1・書き直し）
  - `.claude/review-agents/` → `.claude/agents/`（7 本を移動）
  - `scripts/claude/`（`code-review.sh`・`plan-issue-review.sh`・`issue-review.sh`・`fix-review-lib.sh` の変更、`gate-check.sh`・`flow-stage.sh` の新設）
  - `scripts/claude/tests/`（新設 2 本・更新 9 本前後・fixtures）
  - `.github/workflows/ci.yml`（Harness Tests ジョブを追加。GitHub Actions の変更）
  - `CLAUDE.md`・`docs/runbooks/`（workflow・issue-flow・onboarding・review-rules・plan-writing-rules・danger-ops・mcp-usage・worktree）
  - `docs/plans/templates/plan_template.md`・`docs/tests/templates/auto_test_template.md`・`docs/claude-code-structure.md`・`scripts/migration_verify/lint_skills.py`（必要な場合）
  - `docs/proposals/I193_official_base_flow.md`（新設の設計書）
- 変更しないもの: `.claude/settings.json`（今の許可・フックで足りる。変更が要るとわかったら計画変更記録に書いてから行う）・`scripts/claude/hooks/`・アプリのコード・他のイシューの記録（`docs/issues/open/I043.md`・`I044.md` などの古い計画や提案書は当時の記録なので書き換えない）

## 4. 調査結果

### 4.1 環境
- Claude Code 2.1.310。`claude -p`・`gh`・`git`・`python3`・`bash`・`timeout` を使う（いずれもこのワークツリーで実行して確認済み）
- GitHub の既定のブランチは `develop`（`gh repo view --json defaultBranchRef`）
- ハーネスのテスト: `scripts/claude/tests/*.sh` 33 本のうち 31 本合格・2 本不合格（2026-10-24、このブランチ＝develop 最新）
  - `test_i181_review_slim.sh` D8: review-rules の節にある `.claude/settings.local.json` がワークツリー（と CI）に無い
  - `test_i182_docs.sh` DOC6: danger-ops が `docs/issues/open/I181.md` を指すが、closed へ移動済み
  - I185 では「P12 の別イシューに同梱」として未起票だった。本イシューで直す（設計書 §9）
- ハーネスのテストは CI でも pre-commit でも動いていない（棚卸し・`.github/workflows/ci.yml` を確認）

### 4.2 スパイク（計画確定前に実際に動かした結果）

| No | 確かめたこと | 結果 |
|---|---|---|
| S1 | Claude が Skill ツールで `code-review` を呼んだとき、組み込みと自作のどちらが動くか | 組み込みが動いた（自作は `disable-model-invocation: true` のため Skill ツールからは見えない）。ただし対象を省くと、手元の古い `develop`（`origin/develop` より 97 コミット遅れ）と比べ、無関係の 113 ファイルを見た。`low` では文書・スキルを読み飛ばした |
| S2 | サブエージェント定義で読み取り専用にできるか（`claude -p --agents … --agent …`） | `disallowedTools: [Write, Edit, Bash, NotebookEdit]` は書き込みを止めたが、Agent・Skill・Workflow・GitHub 書き込みの MCP などが残った。`tools: [Read, Grep, Glob]`（許可リスト）では 3 つだけになり、ToolSearch で増やすこともできなかった。ファイルは作られなかった（`ls -A` で確認） |
| S3 | 組み込み `/code-review` を `claude -p` で動かしたときの出力（練習用リポジトリ・わざと不具合を入れた差分） | 指摘 6 件を JSON（file・line・summary・failure_scenario）で返した。合否の判定（VERDICT）や重大度は返さない。計画・受け入れ条件は入力に取らない |
| S4 | 組み込み `/simplify` を `claude -p --permission-mode acceptEdits` で動かす | 重複した関数 2 つを自動で整理して書き換えた。正しさのバグは「`/code-review` の対象」として触らなかった |
| S5 | 組み込み `/verify` を `claude -p` で動かす | 動いたが、実行の許可が無く、コードを読んだ判断だけになった（「許可が却下され、ランタイムの出力は取れていません」）。`.claude/skills/verify/SKILL.md` を書いて組み込みを置き換える仕様（skills.md） |
| S6 | ユーザー用スキルから `user-invocable: false` のスキルを Skill ツールで呼べるか／ユーザーが直接打つと動くか／ファイル定義のサブエージェントを `claude -p --agent` で呼べるか／標準入力で文脈を渡せるか | 呼べた（`INNER_STAGE_RAN args=I999`）。直接打つと何も動かなかった（出力なし）。`.claude/agents/ro-file.md` を `--agent ro-file` で呼べ、最終行 `VERDICT: HIGH` を返した。標準入力の文脈も読めた（`VERDICT: OK`） |
| S8 | 組み込みのレビューを plan モード（読み取り専用）で動かせるか: このワークツリーで `claude -p --permission-mode plan "/review medium origin/develop...HEAD"`（`/review` は組み込みの別名で、自作の同名スキルに隠されない） | 動いた。差分（計画書・設計書・イシュー）を読み、設計の抜け 10 件を file・line・failure_scenario つきで返した（文書も読んだ）。書き込みは起きていない。指摘 10 件は本計画に取り込んだ（計画変更記録 2） |
| S7 | このリポジトリで `claude -p "/code-review medium origin/develop...HEAD"` を実行 | **自作の `/code-review`（code-review.sh）が動いた**。同名の自作スキルは、`claude -p` で打っても組み込みを隠す。自作がレビュー記録をコミットし、PR #327 にレビューコメントを投稿した（ローカルのコミットは push 前に取り消し、記録ファイルは削除。PR のコメントは残っている） |

公式文書で確かめたこと（出典は設計書）:
- 同名のプロジェクトスキルは組み込みを置き換えるが、別名（`/review`）は組み込みのまま（skills.md・code-review-local.md）
- `/verify`・`/code-review` 系は `disable-model-invocation` 相当で、Claude が勝手に始めないものがある。`/simplify` を Skill ツールで呼べるかは、実装ステップ 1 で確かめる（未実証）
- 組み込み `/security-review` は既定のブランチ（develop）との差分を見る
- サブエージェントは CLAUDE.md を読み込む（`omitClaudeMd` で外せる）。今の `claude -p --system-prompt` 呼び出しも CLAUDE.md を読み込むので、読み込み方は変わらない

### 4.3 原因の概要
自作を足すとき・見直すときの出発点が、いつも「今ある自作」だった。そのため公式だけで組んだ流れが一度も描かれず、公式と同名の自作が組み込みを隠したまま（S7）、人の承認を前提にした止めが各工程に残った。

### 4.4 今の流れで、人の承認を外すと止まらなくなる漏れ（I185 敵対的レビューから）
- 種類 B: 自動の修正が、実際の差分を誰もレビューしないまま先へ進む（`docs/reviews/closed/I185_adversarial_review_20261024_1905.md`）
- 種類 C: レビューの判定行が無い出力が OK 扱いになる。`scripts/claude/code-review.sh:29-36`（`detect_code_verdict`）は VERDICT も表の印も無いと `OK` を返す
- CI 待ちの打ち切り: `scripts/claude/code-review.sh:284-286` は 10 分で打ち切った後も先へ進む

## 5. 修正対象と具体的変更内容

### 修正アプローチ
設計書 `docs/proposals/I193_official_base_flow.md` のとおり、公式だけで組んだ流れ（§2）を土台にし、そこで止まらない漏れ L1〜L14（§3）だけを自作で載せる。ユーザーが打つコマンドは `/issue-bootstrap`・`/grill-me`（任意）・`/plan-issue`・`/proceed` の 4 つにし、それ以外の段階は「ユーザーには見えない段階のスキル」（`user-invocable: false`）にして、`/plan-issue` と `/proceed` が順に呼ぶ。段階のつなぎは記録の `STAGE_DONE:` 行と 2 つの決定論スクリプト（`flow-stage.sh`・`gate-check.sh`）で決める。

### 5.1 レビュー役を公式のサブエージェント定義に移す（L7・L8）
- 方針: 書き込み禁止を文章ではなく仕組みで効かせ、時間切れで必ず止まるようにする
- `git mv .claude/review-agents/<name>.md .claude/agents/<name>.md`（7 本: issue-reviewer・plan-reviewer・code-reviewer・adversarial-reviewer・fix-diagnosis-reviewer・fix-implementation-reviewer・fix-test-reviewer）
- 各ファイルの先頭に frontmatter を足す:
  ```yaml
  ---
  name: code-reviewer
  description: I### のコードレビュー（受け入れ条件・計画・セキュリティ・BP の照合）。scripts/claude/code-review.sh と review-gate から呼ぶ。
  tools: Read, Grep, Glob
  model: sonnet
  ---
  ```
- スクリプトの呼び出しを置き換える（`code-review.sh:343-346`・`plan-issue-review.sh`・`issue-review.sh`・`fix-review-lib.sh`）:
  ```bash
  # 変更前
  printf '%s' "$CONTEXT" | claude -p --model claude-sonnet-4-6 --system-prompt "$(cat "$REVIEWER")" --tools "Read,Grep,Glob"
  # 変更後（時間上限はスクリプトごとの環境変数・既定 900 秒。fix 系は今の 300 秒のまま）
  printf '%s' "$CONTEXT" | timeout "${REVIEW_TIMEOUT:-900}" claude -p --agent code-reviewer
  ```
  `timeout` で止まったとき（終了コード 124）は、記録に「時間切れ」と書き、判定を BLOCKER にする（fix 系は今の SKIP の扱いを保つ）
- 敵対的レビュー役は、`review-gate` が Agent ツールの `subagent_type: adversarial-reviewer` で呼ぶ。今のプレースホルダ（{ISSUE} など）は、呼ぶときのプロンプトに値として書く形に変える
- `.claude/review-agents/` は空になるので無くなる

### 5.2 同名スキルの改名と、レビュー段階の作り直し（L1〜L6・L11・L14・S7）
- 方針: 組み込みの `/code-review`・`/security-review` を隠さないようにし、レビュー段階で組み込みを使い、自作は公式に無い部分だけ足す
- 改名（`git mv`）:
  | 元 | 新 | 区分 |
  |---|---|---|
  | `.claude/skills/code-review/` | `.claude/skills/review-gate/` | 段階 |
  | `.claude/skills/security-review/` | `.claude/skills/design-security-review/` | 段階 |
  | `.claude/skills/test/` | `.claude/skills/test-gate/` | 段階 |
  | `.claude/skills/plan-issue-review/` | `.claude/skills/plan-review/` | 段階 |
- `scripts/claude/code-review.sh` に足す・直すこと:
  0. 最初に `git fetch origin develop` を実行する（比べる相手を最新にする。S1 で古い develop と比べた反省）。fetch に失敗したら exit 1
  1. CI 待ちが 10 分で終わらなければ `CI_WAIT: TIMEOUT` を出して exit 3、CI が失敗していれば `CI_WAIT: FAIL` を出して exit 1（今は打ち切り後に先へ進む）。直近の CI は CI 約 2 分・E2E 約 3.5 分（`gh run list` で確認）なので 10 分で足りる。待ち時間と確認の間隔は環境変数（`CI_WAIT_TIMEOUT`・`CI_POLL_INTERVAL`、既定 600・15 秒）で変えられるようにする（テスト S9 で数秒に縮めるため）
  2. 組み込み `/code-review` を **plan モード（読み取り専用）** で実行し、出力を記録に残して自作レビュー役に渡す:
     ```bash
     run_official_review() {   # 出力: グローバル OFFICIAL_FINDINGS（失敗・時間切れは "(実行できず: <理由>)"）
       OFFICIAL_FINDINGS=$(timeout "${OFFICIAL_REVIEW_TIMEOUT:-900}" claude -p --permission-mode plan \
         "/code-review medium origin/develop...HEAD" 2>&1) || OFFICIAL_FINDINGS="(実行できず: exit=$?)"
     }
     ```
     - `--permission-mode plan` にする理由: `claude -p` にはプロジェクトの settings の許可（`Bash(git push *)`・`Bash(rm *)` など）がそのまま効くので、差分の中の文章に誘導されて書き込み・push をしないよう、編集と実行を仕組みで止める。plan モードでも組み込みのレビューが差分を読んで指摘を返すことは、このワークツリーで `/review`（組み込みの別名）を使って確かめた（計画 §4.2 S8）
     - 終了コード 0 でも、出力に変更ファイルの名前が 1 つも出てこず、指摘の配列（`[`）も「指摘なし」に当たる文も無いときは、「対象を読めていない可能性」と記録に書く（S5 のように、許可が無く読めなかった出力を「指摘なし」と取り違えないため）
     - 自作レビュー役への文脈に「### 組み込み /code-review の指摘（file・line・summary・failure_scenario）」として入れる。`code-reviewer.md` に「指摘ごとに、採用（重大度をつけて表に載せる）か、理由つきで不採用かを書く。組み込みが実行できなかった・読めていない可能性があるときは、その旨を記録に書き、自分のレビュー（文書・スキルを含む全ファイル）だけで判定する」を足す。受け入れ条件・計画・文書の確認（L1・L2）は自作レビュー役が主で、組み込みは補助
  3. 高リスク判定 YES のとき、組み込み `/security-review` を同じく `--permission-mode plan`・`timeout` つきで実行し、出力を記録の「### 組み込み /security-review の指摘」に残す。指摘の扱いは 2 と同じく自作レビュー役が判定に入れる（実行の順は、自作レビュー役の前に 2 と 3 をそろえてから渡す。RISK のパス判定は LLM の前に決まるので、パス判定が YES のときに実行する）
  4. `detect_code_verdict`: VERDICT 行も表の印も無いときは `BLOCKER` を返す（今は `OK`。L14）
  5. 記録の末尾に `REVIEWED_COMMIT: <レビューした HEAD>` を書く（L13）
  6. 最後の案内文から `/test`・`/fix-loop`・`/code-review` のコマンド名を消し、段階のスキルが読む機械可読行（`FINAL_VERDICT:` など）だけにする
- `review-gate/SKILL.md`: 今の `code-review/SKILL.md` の 1〜3（基本レビュー・機械判定・敵対的レビュー）を引き継ぐ。変えるのは次のとおり
  - `code-review.sh` は Bash ツールの `run_in_background: true` で実行し、完了の通知で結果を受け取る（CI 待ち 10 分＋組み込み 2 本＋自作レビューで、Bash ツールの上限 10 分を超えうるため）
  - `code-review.sh` の終了コードの扱い: exit 3（CI 待ちの時間切れ）は 1 回だけ実行し直す。2 回続けば止める条件 3（安全側の選択肢が無い）として止める。exit 1 で `CI_WAIT: FAIL` なら `NEXT: fix-loop`（CI の失敗を直す）。それ以外の exit 1 はスクリプトの失敗として記録し、止める条件 3 の判定へ
  - 敵対的レビュー（`ADVERSARIAL_STAGE: REQUIRED`）の周回:
    - 周で Critical/High が出て直したら、`code-review.sh` を実行し直し（直した差分を基本レビューに通す。L13）、上限（通算 2 周。I181 のまま）の範囲で次の周を、直した差分に対して起動する
    - Critical/High が 0 の周（VERDICT OK）の後に差分を足してはいけない（足すと、その差分を見た OK の周が無くなる）。High に直結する Medium を直したいときは、上限が残っていれば次の周に回す。上限が残っていなければ直さずに記録し、振り返りで扱う
    - 通算 2 周で Critical/High が残ったら止める（止める条件 3。セキュリティにかかわる指摘を受け入れて進む判断は Claude だけではしない）。選択肢を出すときの並べ方は今の `code-review/SKILL.md` 3-2 のまま
  - 設計判断が要る指摘は、要件・基本設計・UI/UX に関わるときだけ止める（止める条件 1）
  - 最後に `STAGE_DONE: review-gate NEXT: test-gate`（OK）か `NEXT: fix-loop`（BLOCKER・HIGH）を書く
- `design-security-review/SKILL.md`: 今の `security-review` の中身（実装前の設計レビュー）を引き継ぎ、`user-invocable: false` にする。Blocker が残ったときは、計画を直して `plan-review` を呼び直し、直せないときだけ止める（止める条件 1〜3 のどれかとして）。最後に `STAGE_DONE: design-security-review NEXT: implement`

### 5.3 段階をつなぐ仕組み（L12・L13）
- 方針: 長い自律実行が途中で切れても続きから再開でき、修正の後は必ずレビューを通り直す
- 記録の書き方: `docs/reviews/open/I###_review.md` の末尾に、各段階が次の 1 行を足す
  ```
  STAGE_DONE: <段階> NEXT: <次の段階>
  ```
  段階: `plan`・`plan-review`・`design-security-review`・`implement`・`review-gate`・`fix-loop`・`test-gate`・`human-test`・`retro`・`close`。NEXT にはこれに加えて `human-test`（人の手動テスト待ち）・`merge`（マージ待ち）を書ける
- 同じファイルに「## 自律判断の記録」節を置き、各段階が `- [段階] 決めたこと — 理由` を足す
- `scripts/claude/flow-stage.sh I###`（新設・約 40 行）:
  - `docs/reviews/open/I###_review.md` の最後の `STAGE_DONE:` 行から NEXT を取り出し、`NEXT_STAGE: <名前>` を出して exit 0
  - `STAGE_DONE:` 行が無い（古い流れのイシュー）・ファイルが無い・NEXT が上の一覧に無いときは、理由を出して exit 2
- `scripts/claude/gate-check.sh I###`（新設・約 60 行）:
  - 「レビューの後に変えてよい場所」を `docs/reviews/`・`docs/tests/`・`docs/issues/`・`docs/plans/` の 4 つとする（以下「記録の場所」）
  - 次を全部満たせば exit 0:
    1. 最新の `docs/reviews/I###_code_review_*.md` の最後の `VERDICT:` が `OK` で、その `REVIEWED_COMMIT:` から HEAD までの差分が記録の場所の中だけ
    2. その記録の `RISK:` が `YES` なら、最新の `docs/reviews/I###_adversarial_review_*.md` の最後の `VERDICT:` が `OK` で、その `REVIEWED_COMMIT:` から HEAD までの差分も記録の場所の中だけ（OK の周の後に足した差分を通さない）
    3. 作業ツリーに、記録の場所の外のコミットしていない変更（未追跡のファイルを含む。`git status --porcelain`）が無い
  - 差分のファイル名は `git -c core.quotePath=false diff --name-only --no-renames` で取る（日本語のファイル名・名前の変更で判定をすり抜けない。`code-review.sh` の `path_risk_trigger` と同じ。I086・I181）
  - どれかが欠ける・読めない・違うときは理由を出して exit 1（fail-closed）
  - `docs/plans/` をレビューの後に変えてよい場所に入れる理由: close の open→closed の移動と、レビュー記録へのリンク・完了情報の追記があるため。計画書の中身（方式・範囲・受け入れ条件）を変えたときは、`plan-review` → `review-gate` を通り直す（各段階のスキルに書く）。計画書の中身の変更そのものは gate-check では止めない（止めるのはコードの変更）
  - レビューの後に変えてよい場所を 4 つに絞るのは意図どおり（それ以外〔`docs/proposals/`・`docs/runbooks/`・`.claude/`・`scripts/` など〕を変えたら、レビューを通り直す）。`test-gate`・`retro`・`close` が書くのは `docs/reviews/`・`docs/tests/`・`docs/issues/`・`docs/plans/` だけと各スキルに書き、振り返りで手順書や設計書を直すときは、直した後に `review-gate` を通り直す
  - `test-gate` と `close` の最初に実行し、exit 1 なら `review-gate` に戻る

### 5.4 段階のスキルの書き直し（承認待ちをなくす）
共通: 各スキルの frontmatter は `user-invocable: false`（`disable-model-invocation` は外す）・`argument-hint: "I###"`、description に「/plan-issue・/proceed の流れの中でだけ呼ぶ」と書く。最後に `STAGE_DONE:` を書いて終わる。途中で止めて聞くのは、設計確認メモの 3 条件に当たるときだけ（3 条件の文はスキルごとに書かず `docs/runbooks/workflow.md` の 1 か所に置き、各スキルからそこを指す）。

| スキル | 変えること |
|---|---|
| `plan-review` | 今の `plan-issue-review`（スクリプト実行）を引き継ぐ。終わり方は 3 通り: ① OK → `NEXT: implement` ② HIGHRISK → `NEXT: design-security-review` ③ BLOCKER → 自分で直して再実行し、その結果で①②③を判定し直す。同じゲートで 2 回続けて BLOCKER なら止める条件 3 の判定へ（安全側が取れればそれを選んで記録） |
| `implement` | 「/plan-issue の承認だけでは開始しない・/implement を待つ」（:22-24）を消す。計画外の実装が要るときは、計画書を直して `plan-review` を呼び直す（要件・基本設計・UI/UX を変えるときだけ止める）。テストのフレームワークの導入・形式の変更の承認（:19-20）は、依存関係の追加（`requirements*.txt`・`package*.json` は settings の ask）を伴うので残す。最後に組み込み `/simplify` を Skill ツールで呼び、直したものを含めて commit/push。`NEXT: review-gate` |
| `test-gate` | 最初に `gate-check.sh`。既定の pytest・Jest・E2E の手元の流し直しをやめる（CI が正。CI 待ちは `code-review.sh` が fail-closed で行う）。auto_test.md の「決定論ゲート」で HEAVY（docker・npm・pytest など）と分類されたものだけここで実行する。Claude 担当の手動テストを実行して記録する。人の分があれば提示して `NEXT: human-test` で止まる。無ければ `NEXT: retro` |
| `fix-loop` | 手順 4 のユーザー承認待ち・軽微例外の承認をやめ、診断レビュー（3.5）が PASS した案で進める。複数案の選択が要件・基本設計・UI/UX の価値判断になるときだけ止める。終わりは必ず `NEXT: review-gate`（戻り先を 1 か所にする。今の「/code-review に戻る／/test に戻る」の 2 通りをやめる） |
| `retro` | 予防処置・是正処置の「ユーザーの判断を待つ」（:150・:172-186）をやめ、Claude が採否を決める。直すものはこのイシューで直し、起票が要るものは既存イシューへのコメント同梱を先に探し、無理なものだけ `issue-bootstrap` を Skill ツールで呼ぶ。採否の一覧（見送りを含む）を「## 自律判断の記録」に書く。自動で書くイシューの本文・コメントには、コマンドの出力・ログ・環境変数・記録（JSONL）の中身を貼らず、要約と `ファイル:行` だけにする（公開リポジトリのため）。`NEXT: close` |
| `close` | 最初に `gate-check.sh`。`pr-base-sync.sh` の exit 1（食い違いなど）は自分で解決を試み、要件に関わるときだけ止める。exit 2（状態が分からない）は 1 回やり直し、続けば報告に書いて進める。最後に、自律判断の記録と振り返りの一覧をまとめて Approve & Merge を依頼し、`NEXT: merge` |

### 5.5 ユーザーが打つスキル
| スキル | 変えること |
|---|---|
| `plan-issue` | 承認ポイントを提示して止めるのをやめる。計画書・テスト文書・レビュー文書を作り、`STAGE_DONE: plan NEXT: plan-review` を書いたら、`proceed` を Skill ツールで呼ぶ。「仮定で決めた設計判断は先にユーザーへ確認」は、要件・基本設計・UI/UX の仮定に絞る。計画書の「## 9. 承認ポイント」は「## 9. 確定事項と自律判断」にする |
| `proceed`（新設） | `flow-stage.sh` を実行し、NEXT_STAGE の段階のスキルを Skill ツールで呼ぶことを、NEXT が `human-test`・`merge` になるか、止める条件に当たるまで繰り返す。`human-test` のときは人の手動テスト項目を提示して止まる。exit 2（古い流れのイシューなど）なら理由を報告して止まる。`disable-model-invocation` は付けない（ユーザーが手動テストの結果を返信したら、Claude が結果を記録して `STAGE_DONE: human-test NEXT: retro`〔NG なら `NEXT: fix-loop`〕を書き、`proceed` を呼んで続ける）。`argument-hint: "I###"`。description に「ユーザーが /proceed を打ったとき、`/plan-issue` から呼ばれたとき、ユーザーが手動テストの結果を返信したときだけ使う。それ以外で自分から呼ばない」と書く（誤って呼んでも `flow-stage.sh` が記録の順番どおりにしか進めない） |
| `issue-bootstrap` | `disable-model-invocation` を外す（`retro` から呼ぶため）。最後の「ユーザーがイシューファイルを確認」をやめ、要件・基本設計・UI/UX で決めてもらうことがあるときだけ、その質問をして止まる。`retro` から呼ばれたときは質問せず、未確定は「未定・grill-me で確認」と書く。本文にコマンドの出力・ログ・環境変数・記録の中身を貼らない（`retro` と同じ） |
| `grill-me` | 質問を要件・基本設計・UI/UX の価値判断に絞る（技術的なことは計画で Claude が決める）と明記する。最後の案内は `/plan-issue I###` のまま |

### 5.6 ルールと手順書
- `CLAUDE.md` §1 絶対ルール:
  - 1) 「計画書に書いていない実装は禁止（より良い案がある場合は提案→承認→計画書更新が先）」→「計画書に書いていない実装はしない。必要になったら計画書を先に直し、計画レビューを通してから行う」
  - 2) 「ユーザー承認なしにコード変更（Edit/Write/MultiEdit 等）を開始しない」→「ユーザーに確認するのは、人がやる手動テスト・マージと、止める 3 条件（`docs/runbooks/workflow.md`）に当たるときだけ。それ以外は Claude が決めて記録する」
  - 3)〜5) は変えない（直 push 禁止・危険操作の承認・記録）
- `docs/runbooks/workflow.md`: 「使うスキル」「フロー」「ゲート」「スキル呼び出しルール」「各フェーズの移行時の振る舞い」「作業実行前の確認ルール（承認の echo 記録・TodoWrite 連携）」を新しい流れで書き直す。止める 3 条件（条件 2 は安全装置そのものの変更を含む。集合は `path_risk_trigger` と同じにし、TC-01 S12 で一致を確かめる）・`STAGE_DONE:`・自律判断の記録・移行（着手済みイシューは各ワークツリーの古いスキルで最後まで）を書く
- `docs/runbooks/issue-flow.md`・`onboarding.md`・`review-rules.md`・`plan-writing-rules.md`（承認待ち宣言・ストップワード・承認ポイント・「より良い方法は提案して承認」の節）・`mcp-usage.md`・`worktree.md`（:123）: 承認・コマンド名の記載を新しい流れに合わせる。`plan-writing-rules.md` の「計画書と実装の一致性保証」は残し、「ユーザーの承認」を「計画書の更新と計画レビュー」に置き換える
- `docs/runbooks/danger-ops.md`: `docs/issues/open/I181.md` → `docs/issues/closed/I181.md`（DOC6）。危険操作の承認（DANGER_OK）は変えない
- `docs/runbooks/review-rules.md`: D8 が落ちる `.claude/settings.local.json` の扱いを直す（テスト側で「リポジトリに置かない手元のファイル」として除外するか、文書で別の書き方にするかは、実装時に D8 の意図を読んで決め、自律判断の記録に書く）
- テンプレート: `plan_template.md` の「## 9. 承認ポイント」→「## 9. 確定事項と自律判断」。`auto_test_template.md` の「/code-review」「/test に委譲」→「review-gate」「test-gate」
- `docs/claude-code-structure.md`: スキルとレビュー役の構成を新しい形に直す

### 5.7 ハーネスのテストを CI で動かす（設計書 §6・I185 P8）
- `scripts/claude/tests/run-all.sh`（新設・約 25 行）: `scripts/claude/tests/test_*.sh` を順に流し、1 本でも失敗すれば非ゼロで終わる。`TEST_DIR` 環境変数で対象のフォルダを差し替えられる（失敗を入れた確認用）
- `.github/workflows/ci.yml` にジョブ `harness-tests`（name: `Harness Tests`）を足す: `ubuntu-latest`・`contents: read`・checkout（`fetch-depth: 0`。履歴を見るテストがあるため）→ `bash scripts/claude/tests/run-all.sh`
- CI で落ちるテスト（手元の primary にしか無いファイルを前提にしているなど）が見つかったら、そのテストを直す。直せない理由があるものは計画変更記録に書く
- 必須チェックへの登録は、ユーザーが GitHub の画面で行う（bot に権限が無い）

### 5.8 テストの更新と新設
- 新設 `scripts/claude/tests/test_i193_official_flow.sh`（§6 の TC-01 の中身）
- 更新: `test_review_verdict.sh`（VERDICT 無し → BLOCKER・REVIEWED_COMMIT）・`test_review_gates.sh`・`test_adversarial_trigger.sh`・`test_fix_review.sh`・`test_i181_review_slim.sh`（パスの改名・D8）・`test_i182_docs.sh`（DOC6）・`test_i185_harness_docs.sh` と `fixtures/i185/*`（文言の固定）・`test_i114_retro_plain_output.sh`・`test_i180_retro_triage.sh`・`test_review_commit_lifecycle.sh`・`test_auto_test_template_lint.sh`（テンプレの文言）
- 文書の文言を固定するテストは、守りの部分を消す・反転する・挿入するで落ちることを、各テストの中の失敗注入（FG）で確かめる（I185 種類 A の反省）

## 5-2. 実装手順（ステップ）
未知リスク先行で、仕組みの土台（レビュー役・同名スキル・段階のつなぎ）から始める。

1. **前提の実証（ゲート）**: `.claude/agents/` に 1 本だけ移した状態で、スクリプトから `claude -p --agent` で呼んで VERDICT が読めること、組み込み `/simplify` を Skill ツールで呼べること、同名スキルを改名した後に `claude -p "/code-review medium origin/develop...HEAD"` で組み込みが動くこと → 手動テスト No.1〜No.3。どれかが不成立なら、ここで止めて計画を直す
2. **レビュー役の移動と呼び出しの置き換え**（§5.1）→ TC-02・TC-05・TC-10。ステップ 1 の後
3. **同名スキルの改名とレビュー段階**（§5.2）→ TC-01（R 系）・TC-02〜TC-04。ステップ 2 の後
4. **段階のつなぎ**（§5.3: `flow-stage.sh`・`gate-check.sh`）→ TC-01（F 系・G 系）。ステップ 3 と並行可
5. **段階のスキルとユーザー用スキルの書き直し**（§5.4・§5.5）→ TC-01（S 系）・TC-09・TC-11。ステップ 3・4 の後
6. **ルールと手順書**（§5.6）→ TC-01（D 系）・TC-06〜TC-08・TC-12。ステップ 5 の後（書いた流れに合わせるため）
7. **ハーネスのテストを CI で動かす**（§5.7・§5.8）→ TC-13・TC-14、手動テスト No.6。ステップ 6 の後（全テストが緑になってから CI に載せる）

ファイルの削除（改名で元の場所が無くなる）はあるが、サービスの停止は無い。サービスの再起動は不要。スキルの読み込みはセッション開始時に決まるため、新しいスキルの確認は新しいセッション（`claude -p`）で行う（手動テスト）。

## 6. テスト計画

### 自動（詳細は `docs/tests/open/I193_auto_test.md`）
- テストの種類: すべてハーネスの決定論テスト（bash）。アプリのコード変更が無いので pytest・Jest・E2E は非該当（CI では今までどおり動く）
- 受け入れ条件との対応:

| 受け入れ条件（イシューの順） | 確かめ方 |
|---|---|
| 1 公式だけの流れが出典つきで設計書にある | TC-01 D1（設計書の §2 と出典 URL）・手動 No.8 |
| 2 漏れの一覧と GitHub で止まるか・自作で載せるか | TC-01 D2・手動 No.8 |
| 3 自作は公式で止まらない漏れだけ | 手動 No.8（設計書 §3 と §7 の突き合わせ） |
| 4 `/simplify`・`/verify`・組み込み 2 本の採否と実証 | TC-01 D3・計画 §4.2 |
| 5 有料の道具が入っていない | TC-01 R5（`ultra`・`claude-code-action` が無い） |
| 6 ユーザーの確認は手動テストとマージだけ | TC-01 S 系（承認待ちの文言が無い）・手動 No.5 |
| 7 止めて聞くのは 3 条件だけ・自律判断の記録と報告 | TC-01 D4・S 系 |
| 8 `/plan-issue` で手動テストの手前まで進む | 手動 No.7（新しいセッションでの通し）・TC-01 F 系 |
| 9 振り返りの改善案を Claude が起票まで行う | TC-01 S6 |
| 10 CLAUDE.md が新しい流れと食い違わない | TC-01 D5 |
| 11 着手済みイシューの扱いが runbook にある | TC-01 D6 |
| 12 これまで止めていた漏れが止まる（失敗を入れて） | TC-01 の FG 系・TC-02〜TC-05・TC-13 |
| 13 同名スキルが残っていない | TC-01 R1・手動 No.3 |
| 14 古い流れの参照が残っていない | TC-01 R6 |
| （計画で足した守り）L13・L14 | TC-01 G 系・TC-02 |

### 手動（詳細は `docs/tests/open/I193_manual_test.md`）
- No.1〜No.3: ステップ 1 の前提の実証（Claude・`claude -p`）
- No.4: レビュー段階の通し（このブランチで `code-review.sh` を実行し、組み込みの指摘・REVIEWED_COMMIT・高リスク判定が記録に出る）
- No.5: 新しいセッションの `/` メニュー（Human）
- No.6: CI の Harness Tests と必須チェック登録（Human）
- No.7: 新しい流れの通し（練習用リポジトリ）
- No.8: 設計書と受け入れ条件 1〜3 の突き合わせ（Claude）

## 7. ロールバック
- ステップごとにコミットを分ける。戻すときは該当コミットを `git revert` する（改名は `git mv` なので revert で元に戻る）
- `.github/workflows/ci.yml` の Harness Tests ジョブは、そのコミットの revert で外れる。必須チェックに登録した後に外すときは、ユーザーがブランチ保護の設定から外す
- 着手済みイシューは各ワークツリーの古いスキルで動いているので、本イシューの revert の影響を受けない

## 8. Risk & 回避策
| リスク | 回避策 |
|---|---|
| 1 回の `/plan-issue` が長くなり、途中で会話が切れる | `STAGE_DONE:` と `/proceed` で続きから再開する（§5.3） |
| 人が計画を見なくなり、計画の誤りがそのまま実装される | 計画レビュー（自作）は残す。実装後のレビューで受け入れ条件と照合する。マージはユーザー |
| 自動の修正がレビューを通らずに先へ進む（I185 種類 B） | `gate-check.sh` が「最新のレビューが今の HEAD を見て OK」を確かめるまで、テスト・クローズへ進ませない |
| 組み込み `/code-review` の結果が揺れる・時間がかかる・使えない | `timeout`。失敗しても自作レビューは動き、記録に「実行できず」を残す。判定は自作レビュー役が出す |
| 段階のスキルを Claude が流れの外で勝手に呼ぶ | description に「流れの中でだけ呼ぶ」と書く。呼んでも `gate-check.sh` と `flow-stage.sh` が順番を外れた進行を止める |
| 文言を固定するテストが守りの削除を見逃す（I185 種類 A） | 守りの部分は、できるだけ挙動のテスト（`flow-stage.sh`・`gate-check.sh`・`detect_code_verdict` の単体テスト）で確かめる。文言のテストには失敗注入を付ける |
| CI でハーネスのテストが手元と違う結果になる | ステップ 7 で CI の結果を見て直す。直せないものは計画変更記録に書く |
| 受け入れ条件 8（`/plan-issue` だけで手動テストの手前まで進む）の通しを、マージ前に実地で確かめられない（GitHub のイシュー・PR の作成を伴うため、練習用リポジトリでは段階のつなぎ〔手動 No.7〕までしか通せない） | マージ前は、つなぎの決定論（`flow-stage.sh`・`gate-check.sh`・TC-01 F・G 系）と、段階のスキルを呼べること（手動 No.2・S6 のスパイク）で確かめる。マージ後の最初のイシューを実地の通しとし、その振り返りで結果を確かめることを `docs/runbooks/workflow.md` の移行の節に書く（自律判断の記録にも残す） |
| メモ（Claude の記憶）が古い承認ルールのまま残り、新しい流れでも止まってしまう | /close で、承認・コマンド待ちを前提にしたメモを新しいルールに書き換える。対象: `feedback_skill_tool_usage.md`（「プロジェクトスキルを Skill ツールで呼ばない」。段階のスキルを Skill ツールで呼ぶ新しい流れと正面から食い違う。ユーザーが打つスキルは今までどおり自分から呼ばない、段階のスキルは流れの中で呼ぶ、に書き換える）・`feedback_implement_after_explicit_command.md`・`feedback_wait_for_explicit_command.md`・`feedback_user_test_before_code_review.md`・`feedback_target_operating_model.md`（「ユーザーに残る: スキルコマンドの起動」の項）・`feedback_no_per_edit_confirmation_during_impl.md`。書き換えた一覧を自律判断の記録に残す |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 対象は計画からクローズまでの全工程・無料の範囲だけ・プルリクエスト 1 本・I188/I192 は無いものとして扱う
- ユーザーの確認は人の手動テストとマージだけ。止めて聞くのは 3 条件だけ。CLAUDE.md の承認ルールも書き換える
- 公式の道具は流れの中で Claude が自動で動かす。`/plan-issue` で手動テストの手前まで進む
- 振り返りの改善案は Claude が採否を決めて起票まで行う
- 着手済みイシューは古い流れのまま最後まで（各ワークツリーの古いスキルで動く。2026-10-24 ユーザー回答）

Claude が決めた（技術的な選択。理由は本計画・設計書）:
- 段階のスキルの名前（`review-gate`・`test-gate`・`design-security-review`・`plan-review`・`proceed`）
- `/verify`・`/goal`・Stop フックは入れない（設計書 §4）
- 段階のつなぎを `STAGE_DONE:`・`flow-stage.sh`・`gate-check.sh` で決める
- 手動テストの結果は、同じ会話での返信で続けられる（会話が切れたら `/proceed`）
- ハーネスのテストを CI で動かし、今落ちている 2 本を直す（GitHub Actions の変更。本計画の承認をもって行う）

## 10. 承認ポイント（本イシュー自身は今の流れで進める）
- [ ] 計画内容（変更点・影響・ステップ）
- [ ] `.github/workflows/ci.yml` に Harness Tests ジョブを足す（GitHub Actions の変更）
- [ ] テスト計画（自動 TC-01〜TC-14・手動 No.1〜No.8）
- [ ] Danger Ops: 無（データの削除・破壊的な変更なし。改名・移動は git で戻せる）

## 11. 運用設計（`claude -p` の自動実行）
- 時間上限: レビュー役 900 秒（`REVIEW_TIMEOUT`）・fix 系 300 秒（今のまま）・組み込み `/code-review`・`/security-review` 各 900 秒（`OFFICIAL_REVIEW_TIMEOUT`）・CI 待ち 600 秒（打ち切りで exit 1）
- やり直し: スクリプトは自動でやり直さない。時間切れ・失敗は記録に残し、自作レビューは BLOCKER（fail-closed）、組み込みは「実行できず」と書いて自作の判定に任せる
- 記録: すべて `docs/reviews/` に残す（今と同じ）。自律判断は `I###_review.md` の「## 自律判断の記録」

## 12. コスト・保守見積もり
- 費用: 無料の範囲（有料の道具は入れない）。1 イシューあたりのレビューの呼び出しは、組み込み `/code-review` が 1 回（高リスク時は `/security-review` も 1 回）増える
- 保守: 自作は減る（同名スキル 2 本の重なり・`--system-prompt` の組み立て・人の承認待ちの分岐）。増えるのは `flow-stage.sh`・`gate-check.sh`・`run-all.sh`（いずれも 60 行以内）と CI ジョブ 1 本
- 手作業: ユーザーの入力は、1 イシューあたり `/plan-issue` 1 回・手動テストの返信・マージになる（今は `/implement`・`/code-review`・`/test`・`/retro`・`/close` と各承認）

## 該当しない観点
- セキュリティ影響: アプリのコード変更なし。ハーネスの安全装置（見張り・deny・ask・危険操作の承認・ブランチ保護）は変えない。レビュー役は `tools: Read, Grep, Glob` で今より強く読み取り専用になる。`.github/workflows/ci.yml` の変更は `contents: read` のジョブ追加だけで、秘密情報を使わない
- P3/P5/P8: DB・依存関係ファイルの変更なし。Dockerfile・docker-compose.yml への波及なし
- P6: 画面・データ量の変更なし
- P9: 個人情報・未成年データ・テナントデータを扱わない

## レビュー結果
- [20261024_2239 判定: ✅ 完了](../../reviews/I193_plan_review_20261024_2239.md)

## 計画変更記録
1. 2026-10-24 計画レビュー（`I193_plan_review_20261024_2239.md`・HIGHRISK・Blocker なし）の Warning 4 件・Info 2 件に対応した: R6 の検索対象に `scripts/migration_verify/` を追加／受け入れ条件 8 の実地の通しをマージ後の最初のイシューで確かめるリスクを §8 に追加／`gate-check.sh` がレビュー後に変えてよい場所を絞る意図と、`docs/proposals/` などを変えたら通り直すことを §5.3 に明記／`plan-review` の終わり方を 3 通りで明記／段階のスキルと `proceed` に `argument-hint` を付ける／`proceed` の description で呼ぶ場面を限定。あわせて §2 の受け入れ条件の数を 14 に直した（イシューの項目数どおり）。方式・範囲・受け入れ条件は変えていないため、計画レビューはやり直さない
2. 2026-10-24 /security-review で、(a) 組み込みのレビュー（`/review`・plan モード）が出した設計の抜け 10 件（計画 §4.2 S8）と、(b) セキュリティ設計レビューの指摘（下の「セキュリティレビュー結果」）を取り込んだ。主な変更: 組み込みのレビューを plan モードで動かす／`code-review.sh` の最初に fetch／CI 待ちの時間切れを exit 3 にして review-gate が 1 回やり直す／`code-review.sh` を背景で実行する（Bash ツールの 10 分上限）／敵対的レビューの記録にも `REVIEWED_COMMIT` を求め、OK の周の後に差分を足さない／gate-check がコミットしていない変更も見る・ファイル名を `core.quotePath=false --no-renames` で取る／止める条件 2 に安全装置そのものの変更を含める／自動の起票にログ・出力を貼らない／書き換えるメモに `feedback_skill_tool_usage.md` ほかを明記／設計書の L13 の書き方とテストの本数を計画にそろえた。止める条件 2 の範囲を広げたので、計画レビューをやり直す（`plan-issue-review.sh`）

## セキュリティレビュー結果

**実施日**: 2026-10-24

### セキュリティ設計レビュー
コード変更（backend・frontend）なし。対象はハーネス（スキル・スクリプト・CI・ルール）。

| 重大度 | 分類 | 設計上のリスク | 対処（禁止事項 / 必須防御条件） |
|--------|------|--------------|-------------------------------|
| High | 認証・認可（最小権限） | `code-review.sh` から `claude -p` で組み込みのレビューを動かすと、プロジェクトの settings の許可（`Bash(git push *)`・`Bash(rm *)`・`gh pr edit` など）がそのまま効く。差分の中の文章（プロンプトインジェクション）に誘導されると、レビューの途中で書き込み・push が起きうる | 組み込みの `/code-review`・`/security-review` は `--permission-mode plan` で動かす（必須）。plan モードで差分を読めることは S8 で確かめた。TC-01 S8 で、呼び出しの行に `--permission-mode plan` があることを確かめる |
| High | 認証・認可（自己変更） | 人の承認を外した流れでは、Claude が安全装置そのもの（settings の deny・hooks、見張り、CI、pre-commit、secrets の基準）を緩める変更を自分で進めうる。緩めた設定はマージ前でも手元ですぐ効く | 止める条件 2 に「安全装置そのものを変える操作」を含める（集合は `path_risk_trigger` と同じ）。TC-01 S12 で 2 つの集合の一致を確かめる。`.claude/**` の Edit は今も settings の allow に無く、権限の確認が出る（変えない） |
| Medium | 機密情報 | 振り返りが公開リポジトリにイシュー・コメントを自動で書く。人が目を通さないので、コマンドの出力・ログ・記録に混じった秘密情報や手元のパスがそのまま公開されうる | 自動で書く本文には、コマンドの出力・ログ・環境変数・記録（JSONL）の中身を貼らない。要約と `ファイル:行` だけにする（retro・issue-bootstrap に書く。TC-01 S11） |
| Medium | 入力検証 | `gate-check.sh` が差分のファイル名を読むとき、git の既定（`core.quotePath=true`）では日本語のファイル名が引用符つきになり、名前の変更は新しい名前だけが出る。判定をすり抜ける（I086・I181 で同じ穴があった） | `git -c core.quotePath=false diff --name-only --no-renames` で取る（TC-01 G10） |
| Medium | セキュリティ設定ミス | 自動の修正の後、実際の差分を誰も見ないまま先へ進む（I185 種類 B）。敵対的レビューの OK の後に足した差分・コミットしていない変更も同じ | gate-check で、コードレビューと敵対的レビューの `REVIEWED_COMMIT` から HEAD までと作業ツリーに、記録の場所の外の変更が無いことを確かめる（TC-01 G1〜G10） |
| Low | 外部通信（CI） | 追加する `Harness Tests` ジョブで、fork からの PR の中身が CI 上で動く | `pull_request` のイベント（`pull_request_target` は使わない）・`permissions: contents: read`・秘密情報を使わない。fork PR の Actions は今までどおり承認しない（workflow.md「外部（fork）からの PR の扱い」）。actions/checkout は今の ci.yml と同じ版にそろえる |
| Low | 認証・認可 | `.claude/agents/` に置いたレビュー役を、メインの Claude が自分から仕事を任せる相手に選びうる | レビュー役は `tools: Read, Grep, Glob` だけなので、任されても書き込みはできない。description に「スクリプトとレビュー段階から呼ぶ」と書く |
| Low | 依存ライブラリ | ― | 追加なし |

マルチテナント・ファイル操作（アップロード）: 該当なし。

### 攻撃シナリオレビュー

| # | 入口 | 想定権限 | 想定操作 | 守るべき条件 | 自動テスト化対象 | 手動確認対象 | 残余リスク | 重大度 |
|---|------|---------|---------|------------|----------------|------------|---------|--------|
| 1 | 差分の中の文章（コメント・文書） | リポジトリに書ける者（自分たちの PR） | 組み込みレビューへの指示の注入で、push・ファイル削除をさせる | 組み込みのレビューは plan モードで動き、編集・実行ができない | Yes: TC-01 S8（呼び出しの行） | Yes: 手動 No.4（plan モードで動き、ファイルが増えない） | 自作レビュー役の判定（VERDICT）を注入で OK に誘導されうる。決定論ゲートの実走と gate-check、マージ前のユーザーで受ける | High→対処済み |
| 2 | 自律の流れ（Claude 自身） | ― | 修正のついでに settings の deny・hooks・見張り・CI を緩める | 止める条件 2 で止まる。`.claude/**` の編集は権限の確認が出る。高リスク判定で敵対的レビューが走る | Yes: TC-01 S12 | No | 止める条件はスキルの手順（文章）なので、Claude が守らない可能性は残る。権限の確認とパス判定（決定論）で二重に受ける | High→対処済み |
| 3 | 自律の流れ | ― | 敵対的レビューの OK の後にコードを足し、レビューを通さずにクローズする | gate-check が敵対的レビューの `REVIEWED_COMMIT` 以降のコード変更で止める | Yes: TC-01 G8 | No | なし | Medium→対処済み |
| 4 | 振り返りの自動起票 | ― | 記録・ログに混じった秘密情報や手元のパスを公開イシューに書く | 本文に出力・ログ・記録を貼らない | Yes: TC-01 S11（手順の文） | No | 手順の文なので守られない可能性は残る（検査する仕組みは無い） | Medium |
| 5 | fork からの PR | 外部の第三者 | `Harness Tests` で任意のスクリプトを動かす | `pull_request`・`contents: read`・秘密情報なし・Actions を承認しない | No（ワークフローの設定） | No | なし（今の CI と同じ扱い） | Low |

### レビュー結果サマリー

| 重大度 | 設計レビュー | シナリオ |
|--------|------------|---------|
| Blocker | 0件 | 0件 |
| High    | 2件（対処を計画に反映済み） | 2件（同じ。対処済み） |
| Medium  | 3件（対処を計画に反映済み） | 2件 |
| Low     | 3件 | 1件 |

### 残余リスク処遇
（/retro で決定する）
