# 計画書: I221 イシューの正を GitHub に一本化する

## 基本情報
- **計画書ID**: plan_I221
- **関連イシュー**: #425（I189 #321 を吸収）
- **Draft PR**: #426
- **作成根拠資料**: docs/issues/open/I221.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I221_review.md
- **作成日**: 2026-11-08

## 1. 背景/目的
イシューの中身と番号を「GitHub」と「手元の `docs/issues/open/I###.md`」の 2 か所に持っているため、全ワークツリーをまたぐ自前の採番（`next-issue-num.sh`）・同時起票の番号の衝突（I189）・手元のファイルを未コミットで置く決まり・`gh issue edit` の手作業の同期・ワークツリー間の持ち運びが要っている。設計確認メモ（2026-10-30・11-08）で次が決まっている:
- 新しいイシューは手元のイシューファイルを作らず、GitHub のイシューを唯一の正にする。作成済みのイシューファイルはそのまま
- 番号は「I＋GitHub の番号」（#427 → I427）。記録のファイル名・ゲートのスクリプトの I### の形はそのまま使う
- 起票の入口は薄くした `/issue-bootstrap`（`gh issue create`）。GitHub 画面用のイシューフォームは作らない
- `/plan-issue` が計画を始めるときに GitHub の本文を 1 回だけ手元に写し、計画書と一緒にコミットする（同期しない・正は GitHub）

## 2. 受け入れ条件
イシューの受け入れ条件（7 項目）をそのまま使う。対応する検証:
| AC | 中身 | 検証 |
|---|---|---|
| AC1 | 新しいイシューを手元のファイルなしで起票し、`/plan-issue` の最初のコミットまで手作業の同期・持ち運びなしで通した実走の記録 | 手動 M-01・M-03 |
| AC2 | 根本原因 ①〜③ の失うもの・補う方法をスパイクで確かめて計画書に書く | 本書「調査結果 3」（実施済み） |
| AC3 | 新しいイシューで `/plan-issue` を始めると本文の写しが計画書と一緒にコミットされる | 手動 M-03・自動 TC-01（S3） |
| AC4 | 既存のイシューファイルがあるイシューが、移行の後も今の流れ（`/plan-issue`・`/proceed`・close）で動く | 自動 TC-01（S1・S6）・手動 M-04（I221 自身が既存ファイルの流れで最後まで通る） |
| AC5 | 手元のイシューファイルを読んでいた所が、GitHub の本文を読む形（または既存のファイルがあるときだけ読む形）になっている | 本書「調査結果 2」の全件表・自動 TC-02（古い採番が残っていない・入口のスキルが `issue-source.sh` を呼ぶ）・手動 M-03（`/plan-issue` の手順が `issue-source.sh` で写しを作る） |
| AC6 | I189 の扱いが決まっている | 本書「9. 確定事項」（吸収して取り下げ） |
| AC7 | 既存のハーネステスト・CI がすべて pass | 自動 TC-03・CI |

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: ハーネス（スキル・レビュー役・スクリプト・runbook・ひな形）。既存のイシューファイル（`docs/issues/open|closed/`）は消さず、読み方も変えない

## 調査結果

### 1. 環境前提
- `gh`（GitHub App の鍵で動く・I225）・`python3`・`git` が使える。`jq` は入っていない（実装で判明・計画変更記録 2）（本計画の作成中に `gh issue view`・`gh api graphql`・`gh pr create` を実行して確認）
- `.claude/settings.json` は `Bash(gh issue *)` を許可済み（起票・本文の読み取り・grill-me の本文の書き換えで承認画面は出ない）

### 2. 手元のイシューファイルを読む所（全件・2026-11-08 に `docs/issues|next-issue-num|イシューファイル|issue_template` で grep）
写しを `docs/issues/open/I###.md` に置く（下の「修正アプローチ」）ため、`/plan-issue` より後の段階は写しを読めば足り、読み方を変えなくてよい。変えるのは `/plan-issue` より前（起票・grill-me）と、写しを作る `/plan-issue` だけ。

| 読む所 | いつ動くか | 対応 |
|---|---|---|
| `.claude/skills/issue-bootstrap/SKILL.md` | 起票 | 書き換え（採番・ファイル作成をやめ `gh issue create`） |
| `scripts/claude/next-issue-num.sh`・`scripts/claude/tests/test_next_issue_num.sh` | 起票の採番 | 削除（使う所が無くなる） |
| `scripts/claude/issue-review.sh`・`.claude/agents/issue-reviewer.md` | 起票（登録前のレビュー） | `--file <下書き>` を足す・レビュー役は渡された本文だけを見る |
| `docs/issues/templates/issue_template.md` | 起票 | 本文のひな形として残す（1 行目の `# I###: <title>` を外す。題名は GitHub の題名が持つ） |
| `.claude/skills/grill-me/SKILL.md` | 計画の前 | 既存ファイルが無いときは GitHub の本文を読み書きする手順を足す |
| `scripts/claude/check-memo-body-paths.sh` | grill-me | `--file <パス>` を足す（GitHub の本文を書き戻す前の下書きを検査する） |
| `.claude/skills/plan-issue/SKILL.md` | 計画の開始 | 写しを作ってから最初のコミット・`Closes #` の番号を新しい補助スクリプトで得る |
| `.claude/skills/design-security-review/SKILL.md`（`docs/issues/open/$ARGUMENTS.md`） | 計画の後 | 変えない（写しがある） |
| `scripts/claude/plan-issue-review.sh`・`code-review.sh`・`adversarial-review.sh`（`find_file issues`） | 計画の後 | 変えない（写しがある） |
| `.claude/agents/plan-reviewer.md`・`code-reviewer.md` | 計画の後 | 変えない（写しがある） |
| `.claude/skills/close/SKILL.md`（open → closed の移動） | close | 変えない（写しを同じく移す。③ の補いになる） |
| `.claude/skills/retro/SKILL.md`（ハンドオフ invariant） | retro の起票 | 新しいイシューは手元に何も残らない旨に書き換え |
| `scripts/claude/check-issue-background.sh` | 手で流す点検 | 変えない（写しも本文のひな形から作るので **背景**/**目的** を持つ） |
| `scripts/claude/gate-check.sh`・`code-review.sh` の「記録の場所」判定 | review-gate | 変えない（写しは `docs/issues/` にある） |
| `docs/runbooks/workflow.md`・`issue-flow.md`・`worktree.md`・`dependency-audit.md`・`onboarding.md` | 説明 | 書き換え |
| `scripts/claude/hooks/sessionstart_context.py`（最新イシューの題名から I### を取り出す） | セッション開始 | 変えない。新しいイシューの題名には I### が無いので `#427 -` と出る。番号そのものが ID になるので足りる |
| `docs/claude-code-structure.md` | 説明 | 対象外。すでに古い作り（`in_progress/`・`ls` での採番）のままで、点検は I222 の範囲（9 に記録） |
| テスト（`test_i107_track_label_docs.sh`・`test_i179_worktree_docs.sh`・`test_i185_harness_docs.sh`・`test_i193_official_flow.sh`・`test_i224_push_points.sh`・`test_review_verdict.sh`、仮の `docs/issues/open/I900.md` を作る `test_i193_official_flow.sh`・`test_i197_review_ledger.sh`・`test_i197_adversarial_process.sh`・`test_i202_ledger_cleanup.sh`・`test_i205_stop_criteria.sh`・`test_i212_review_base.sh`） | CI | 変えない。仮の I900.md を作るテストは、変えないスクリプト（`code-review.sh`・`adversarial-review.sh`・`gate-check.sh`）の `find_file` を使うだけなので、手元では流さず CI に任せる。文言を固定しているもの（i107: `track:app`/`track:harness` の行数・i179: `wt-harness` 固定が無い・i185: onboarding の流れ図・フィクスチャ `workflow_stop_guidance.txt`）に当たらないように書き換える |

### 3. スパイク（AC2・根本原因 ①〜③）
2026-11-08 にこのセッションで実行した。

| 理由 | 案 1 で失うもの | 補う方法 | スパイクの結果 |
|---|---|---|---|
| ① 本文の変更を差分として残す | 起票〜grill-me の本文の変更が PR の差分に出ない | (a) GitHub が本文の全版を残す: `gh api graphql` の `issue.userContentEdits` で版ごとの日時と本文が取れる。(b) `/plan-issue` の写しが計画開始時点の本文を PR に残す。計画開始の後の範囲・受け入れ条件の変更は、今と同じく計画変更記録と写しに書く（GitHub へは戻さない・I224 の書き込みの時点を増やさない） | 成立: #425 で `totalCount=3`・版ごとに `editedAt` と本文（7.5〜7.8 千字）が返った |
| ② ネットワークに頼らずスクリプトが本文を読む | 計画を始める前（起票・grill-me）は GitHub が要る | 計画を始めた後の段階（計画レビュー・review-gate・敵対的レビュー・close）は写しを読むので要らない。起票・grill-me はもともと GitHub に書く段階なので、GitHub が要るのは今と同じ | 成立: 後の段階のスクリプトは `find_file issues I###.md` で写しを読む（`code-review.sh:1010`・`plan-issue-review.sh:101`・`adversarial-review.sh:385`） |
| ③ close で open → closed に移し、完了を git の履歴に残す | 新しいイシューにはもともとのファイルが無い | 写しが `docs/issues/open/` にあるので close の移動はそのまま動く。GitHub 側も `Closes #番号` で PR のマージ時に閉じる | 成立: #422（I227）が PR #424 のマージで `stateReason=COMPLETED`・`closedByPullRequestsReferences=[#424]` |
| 番号の取り違え | — | `gh issue view <番号>` は PR の番号でもエラーにならずに返る（下の補助スクリプトで url の `/issues/` を確かめる） | 確認: `gh issue view 426`（PR）が成功し、url が `/pull/426` |
| 見えないイシュー | — | bot が作ったイシュー（#321 など）は `Could not resolve` で読めない。新しいイシューは GitHub App で作るので同じ形の停止の心配は小さい（設計確認メモ） | 確認: `gh issue view 321` が終了コード 1 |

### 4. 番号の重なり
- 自前の I### の最大は I228（#423）。GitHub の番号は #426（この PR）まで進み、次は #427 以降
- 新しい形かどうかの境目を **I427** に置く（I427 以上＝GitHub の番号・I426 以下＝手元のファイルで管理する番号）。#426 以下はすべて既存の GitHub の番号（自前の I### のイシュー・PR）なので、新しい形として読むと既存のイシューを別の番号で写してしまう（例: #422 は I227）。計画レビュー（Warning 1）で 400 から改めた
- 境目を置く理由: 境目が無いと、既存ファイルが別のワークツリーにしか無いとき（例: app-1 の未追跡の I196.md を harness-1 で `/plan-issue I196`）、GitHub の #196（別の古いイシュー）を黙って読んで写してしまう
- 境目だけでは足りない所: I221 のマージより前に今の流れで起票されたイシュー（題名が `I229: …` のような形）は #427 以降の番号を取りうる。そこで GitHub から読むときに題名が `^I[0-9]{3,}: ` で始まるものは「自前の番号で管理するイシュー」として 2 で止める（4-1）。新しい形の題名には `I###:` を付けない（4-4）ので、この 2 つで見分けられる

### 5. 既存テストのベースライン
- ハーネスのテストは CI（Harness Tests）が PR ごとに全部流す。develop の最新（PR #424 マージ時点）は全緑。手元では関係するテストだけを流す（TC-03）

## 4. 変更点一覧（修正アプローチ）

**修正アプローチ**: 番号から「手元のファイルか GitHub か」を決め、本文を読む・写すを 1 本の補助スクリプト `scripts/claude/issue-source.sh` にまとめる。写しは既存のイシューファイルと同じ場所・同じ名前（`docs/issues/open/I###.md`）に置くので、`/plan-issue` より後の段階は何も変えずに動く。変えるのは、起票（`/issue-bootstrap`）・grill-me・`/plan-issue` の入口と、説明の文書だけ。

### 4-1. 新規 `scripts/claude/issue-source.sh`
**修正方針**: 「I### がどこにあるか」の判断を 1 か所に置き、境目（I427）・PR 番号の取り違え・本文のこわれを決定論で防ぐ。
- 引数の形: `^I[0-9]{3,}$`（それ以外は終了コード 2。パスを組み立てない）
- 定数: `NEW_ISSUE_MIN=427`（環境変数で上書きしない）
- サブコマンド:
  - `path I###`: `docs/issues/open/I###.md` → `docs/issues/closed/I###.md` の順で探し、あればパスを出して 0。無ければ 1
  - `body I###`: 手元のファイルがあれば中身を出す。無く、番号が 427 以上なら GitHub の本文を出す（下の「GitHub から読む」）。無く、427 未満なら「I### は手元のイシューファイルで管理する番号。ファイルのあるワークツリーで実行する」と出して 2（GitHub を読まない）
  - `snapshot I###`: 手元のファイルがあればそのパスを出して 0（GitHub を読まない・上書きしない）。無く、427 以上なら GitHub から読んで `docs/issues/open/I###.md` に写しを書き、パスを出して 0。無く、427 未満なら 2
  - `gh-number I###`: 手元のファイルがあれば最初の `GitHub Issue: #(数字)` を出す（無ければ 2）。無く、427 以上なら番号そのもの。427 未満なら 2
- GitHub から読む: `gh issue view <N> --json url,title,body` を 1 回だけ呼んで一時ファイルに置き、`python3 -I` の json で取り出す。url が `/issues/<N>` で終わらなければ（PR の番号など）2。題名が `^I[0-9]{3,}: ` で始まれば（自前の番号で起票したイシュー）2。`gh` が失敗したら 2。どのときもファイルを書かない
- 基準のフォルダ: カレントディレクトリの `git rev-parse --show-toplevel`（スクリプトの置き場所ではない）。別のリポジトリのスクリプトを呼んでも、書くのは今いるリポジトリ（M-03 の使い捨ての clone の使い方）
- 写しの形（本文は python3 で取り出した文字列を、末尾に改行を足さずにそのままファイルに書く。シェルの展開を通さない）:
  ```
  # I427: <GitHub の題名>

  > GitHub #427 の本文の写し（2026-11-08 10:00 UTC に /plan-issue が作成）。正は GitHub のイシュー。この写しは同期しない。
  > - GitHub Issue: #427

  <本文そのまま>
  ```
- 書き込みは一時ファイルに書いてから `mv`（途中で失敗しても半端なファイルを残さない）

### 4-2. `scripts/claude/check-memo-body-paths.sh`
**修正方針**: grill-me が GitHub の本文を書き戻す前に、下書きのファイルを同じ検査にかけられるようにする。
- `--file <パス>` を受け付ける（そのファイルを ISSUE_FILE にする。ファイルが無ければ 2）。`I###` の形は今のまま。引数の形の検査を `^I[0-9]{3,}$` に広げる（I1000 以降に備える）

### 4-3. `scripts/claude/issue-review.sh`・`.claude/agents/issue-reviewer.md`
**修正方針**: 番号が決まる前（GitHub に登録する前）の下書きをレビューできるようにする。
- `issue-review.sh --file <下書き>` を足す。このときは「イシュー番号: （登録前の下書き）」として本文を渡し、結果を `docs/reviews/` に保存しない（番号が無く、未追跡のファイルを手元に残さない。結果は画面に出し、判定の 1 行は起票のスキルが本文に書く）。`I###` で呼ぶ形は今のまま
- `issue-reviewer.md` の「読むべきファイル」を「渡されたコンテキストの『### イシューファイル』の本文をレビューする。I### が渡され、そのファイルが手元にあるときはそれを Read してもよい」に直す

### 4-4. `.claude/skills/issue-bootstrap/SKILL.md`（薄くする）
**修正方針**: 採番とファイル作成をやめ、下書き → 自己完結度レビュー →（必要なら質問）→ `gh issue create` → 番号の報告、にする。
1. リポジトリ確認（今のまま）
2. 下書き: `docs/issues/templates/issue_template.md` をセッションのスクラッチパッド（リポジトリの外。無ければ `mktemp`）に写して書く。リポジトリの中に置かない
3. 自己完結度レビュー: `bash scripts/claude/issue-review.sh --file <下書き>`。判定（十分／要補足）の 1 行を下書きの「## 関連資料」に `- 自己完結度レビュー（issue-review・YYYY-MM-DD）: 十分／要補足` で書く
4. 会話の中の起票で、要件・基本設計・UI/UX の質問が残るときは、ここで質問して止まる。下書きはスクラッチパッドに残っているので、答えをもらったら下書きの「## 設計確認メモ（/grill-me）」に書いて 5 から続ける（採番が無いので、やり直しても番号は変わらない・台帳 I220 F1）
5. 登録: `gh issue create --title "<題名>" --body-file <下書き> --label <種別> --label <トラック>`。題名に `I###:` を付けない（番号は GitHub が振る）。出力の URL の末尾の数字を番号 N にする（`gh issue list --limit 1` で取らない・台帳 I220 F3）。登録したら下書きを消す
6. 報告: `I<N>（#<N>）・題名`。次の案内は `/grill-me I<N>`／`/plan-issue I<N>`。retro からのときは I<N> を retro に返す
- ラベルの決まり（2 軸）・公開リポジトリの決まり（出力・ログを貼らない）は残す。トラックラベルの例に `.github/` を足し、どちらの例にも当たらないときは主目的側に 1 つ付ける旨を書く（台帳 I209 F7）

### 4-5. `docs/issues/templates/issue_template.md`
- 1 行目 `# I###: <title>` と続く空行を消す（GitHub の本文には題名が要らない。写しは補助スクリプトが題名の行を付ける）

### 4-6. `.claude/skills/grill-me/SKILL.md`
**修正方針**: 既存ファイルの有無で 2 つの経路を同じ粒度で書く（plan-writing-rules「条件分岐のコマンド粒度パリティ」）。
- 手順 1: `bash scripts/claude/issue-source.sh body $ARGUMENTS`（どちらの経路でも動く）
- 手順 4（回答の書き込み）:
  - 既存ファイルがある（`issue-source.sh path` が 0）: 今のまま（ファイルを直す → `check-memo-body-paths.sh I###` → `gh issue edit <番号> --body-file <ファイル>`。番号は `issue-source.sh gh-number`）
  - 既存ファイルが無い（I427 以上）: `issue-source.sh body I###` の出力をスクラッチパッドの `I###_body.md` に書く → Edit で設計確認メモと本文整合 → `check-memo-body-paths.sh --file <下書き>` → `gh issue edit <N> --body-file <下書き>` → 下書きを消す
- description の「イシューファイルに記録する」を「イシュー（既存のファイル、または GitHub の本文）に記録する」に直す

### 4-7. `.claude/skills/plan-issue/SKILL.md`
**修正方針**: 最初のコミットの前に写しを作る。既存ファイルの経路と新しい経路を 1 つのコマンドでそろえる。
- 必読の 1 行目を `bash scripts/claude/issue-source.sh body $ARGUMENTS` の出力に変える
- 手順 1 の後に `ISSUE_FILE=$(bash scripts/claude/issue-source.sh snapshot "I${ISSUE_NUM}")`（既存ファイルならそのパス・新しいイシューなら写しを書いてそのパス）。終了コードが 0 でなければ止まる（出力をそのまま報告）
- 手順 2 の `git add` を `"$ISSUE_FILE"` に、コミットの題を新しいイシューでは `docs: create issue I###（GitHub #N の本文の写し）` に
- 手順 3 の `Closes #` は `bash scripts/claude/issue-source.sh gh-number "I${ISSUE_NUM}"` の出力を使う
- 「前提（invariant）」に、新しいイシューは手元に未コミットのファイルを持たない（写しは `/plan-issue` が作ってすぐコミットする）ことを足す。既存ファイルの扱いは今のまま

### 4-8. `.claude/skills/retro/SKILL.md`
- 「ハンドオフ invariant」を「issue-bootstrap は GitHub にだけ起票し、手元にファイルを作らない。I427 未満の既存のイシューファイル（未コミットのもの）は今までどおりコミットしない」に直す

### 4-9. 説明の文書
- `docs/runbooks/workflow.md`:
  - 4 行目（`/issue-bootstrap` の説明）・20 行目（フロー 1）を新しい起票に合わせる
  - 「## 記録とつなぎ（決定論）」の後に「## イシューの置き場所（I221）」を足す: 正は GitHub／I＋GitHub の番号／境目 I427 と理由／`/plan-issue` の写し（同期しない・計画開始の後の範囲の変更は計画変更記録と写しに書く）／既存のイシューファイル（I426 以下）は今の流れのまま／① の補い（`userContentEdits` で本文の全版が取れる）／既存イシューに同梱するときは、新しいイシューなら `gh issue comment`、計画を始めた後なら写しは直さずコメントだけ（台帳 I220 F6）
  - 「## GitHub への書き込みの時点」の 58 行目（plan-issue の最初のコミット）に「新しいイシューでは本文の写しのコミット」を足す
  - 72 行目（範囲・受け入れ条件の変更は `docs/issues/open/[番号].md` も更新）を「イシューファイル（新しいイシューでは写し）も更新する。GitHub の本文には戻さない」に直す
  - 92 行目（1 件ずつ順に・採番の衝突を避ける）を消す（番号は GitHub が振るので衝突しない）
  - 「### 各段階で止まったときの案内」は変えない（フィクスチャで固定。`/plan-issue I###` の案内はそのまま正しい）
- `docs/runbooks/issue-flow.md`: 「イシュー新規作成時の採番ルール」と「イシュー作成時の自動実行フロー」（6〜86 行）を新しい起票（下書き → レビュー → `gh issue create` → I＋番号）に書き換える。フェーズ1（99〜108 行・162〜201 行）とステップ5（210〜221 行の `git add`）とステップ24（331〜346 行）と 414 行（読むファイル）を、写し・`issue-source.sh` に合わせる。`track:app`/`track:harness` の行は 2 か所以上残す（test_i107）
- `docs/runbooks/worktree.md`: §3（82〜83 行）に「新しいイシューは手元のファイルが無いので持ち越すものは無い」を足す。§8「採番の一貫性」を「番号は GitHub が振る（I221）。既存のイシューファイル（I426 以下）は今までどおり、そのファイルのあるワークツリーで扱う」に書き換え、`next-issue-num.sh` の説明を消す（§11 の旧方式の移行の記述は歴史として残す）
- `docs/runbooks/dependency-audit.md` 16 行目・21 行目: 自動起票されたイシューは、そのまま I＋番号として `/plan-issue` できる（ローカルの起票は要らない）に直す。誰が起票するかは書かない（台帳 I220 F5）
- `docs/runbooks/onboarding.md` 31 行目: `/issue-bootstrap` の説明を「下書き・自己完結度レビュー・GitHub 登録（番号は GitHub が振る）」に。24 行目の流れ図は変えない（TC-14⑦）

### 4-10. 削除
- `scripts/claude/next-issue-num.sh`・`scripts/claude/tests/test_next_issue_num.sh`（使う所が無くなる。消すのは PR の差分なので revert で戻せる）

### 4-11. テストの追加
- `scripts/claude/tests/test_i221_issue_source.sh`（新規）: TC-01 の S1〜S9（auto_test 参照）。`gh` は PATH の先頭に置いた仮のコマンドで差し替え、呼ばれた回数と引数を記録する

## 5. 実装手順
- ステップ1（未知のリスクを先に）: 4-1 の `issue-source.sh` と 4-11 のテストを作る（→ TC-01）。PR の番号の取り違え・境目は、スパイクで挙動を確かめ済み
- ステップ2: 4-2・4-3（検査とレビューの `--file`）（→ TC-01 S9）。ステップ1 と並行してよい
- ステップ3: 4-4〜4-8（スキルとひな形）。ステップ1・2 が前提
- ステップ4: 4-9・4-10（説明の文書・削除）（→ TC-02・TC-03）。ステップ3 が前提
- サービスの再起動は要らない（ハーネスの文書とスクリプトだけ）

## 6. テスト計画
- 自動: `docs/tests/open/I221_auto_test.md`（TC-01 補助スクリプトの決定論テスト・TC-02 現役の文書に古い採番が残っていない・TC-03 関係するテストの実行。全体は CI）
- 手動: `docs/tests/open/I221_manual_test.md`（M-01〜M-04。すべて Claude が実施）
- テストのレベル: 補助スクリプトは単体（仮の gh）。流れは実走（本物の GitHub に 1 件起票・使い捨ての clone で `/plan-issue` の最初のコミットまで）

## 7. ロールバック
- PR を revert する。消した `next-issue-num.sh` も戻る。M-01 で起票したイシューは本物の作業（I222 の登録し直し）なので戻さない。ロールバック後にそのイシューを着手するときは、本文を手元のファイルに写して I### を振り直す（または I221 を入れ直す）

## 8. Risk & 回避策
| リスク | 回避策 |
|---|---|
| 既存ファイルが別のワークツリーにしか無い I### で、GitHub の別のイシューを黙って読む | 境目 I427（`NEW_ISSUE_MIN`）。427 未満は手元のファイルだけを見て、無ければ止まる（TC-01 S2・失敗の注入つき） |
| PR の番号を `/plan-issue I<N>` に渡して PR の本文を写す | url の `/issues/<N>` を確かめる（TC-01 S4・失敗の注入つき） |
| `Closes #` に別の番号が入り、マージで別のイシューが閉じる | `gh-number` を 1 か所で決める（TC-01 S6） |
| 本文の `$(...)`・バッククォート・引用符が写しで壊れる | python3 で取り出した本文をファイルに直接書く（TC-01 S3 で 1 バイト単位で比べる） |
| 写しを正と思って直し、GitHub とずれる | 写しの先頭に「正は GitHub・同期しない」を書く。計画開始の後の変更は計画変更記録と写しに書くと workflow.md に明記（今の既存ファイルの扱いと同じ） |
| 下書きがスクラッチパッドに残る・消える | 登録の後に消す。会話の中で質問して止まったときは残して再開に使う。スクラッチパッドが消えても GitHub に未登録なだけで、作り直せる |

## 9. 確定事項と自律判断
イシューに明記されていること:
- 新しいイシューは GitHub だけで管理・作成済みのファイルはそのまま（設計確認メモ 10-30）
- 番号は I＋GitHub の番号・自前の採番は新しいイシューで使わない（同）
- 起票の入口は薄くした `/issue-bootstrap`・イシューフォームは作らない・自己完結度レビュー・2 軸のラベル・公開リポジトリの決まりは残す（同）
- `/plan-issue` が計画開始時に本文を 1 回だけ写してコミット・同期しない（設計確認メモ 11-08）

Claude が技術的に決めたこと（仮定）と理由（要件・基本設計・UI/UX の価値判断に当たるものは無い）:
- 写しの置き場所は `docs/issues/open/I###.md`（既存ファイルと同じ）— 後の段階（計画レビュー・review-gate・敵対的レビュー・close・レビュー役）を変えずに済み、close の移動で ③ も補える。別の場所に置くと読む所を全部直すことになり、得るものが無い
- 境目は I427（GitHub の、I221 の PR #426 の次の番号）＋自前の題名（`I###: `）の拒否 — #426 以下は既存の番号で、新しい形として読むと既存のイシューを写し違える。マージ前に今の流れで起票されたイシューは題名で止める
- 補助スクリプトを 1 本にまとめる — 境目・PR の取り違えの判断を 1 か所に置き、テストで守る（I213 の基準: 気づきにくく被害が大きい）
- `next-issue-num.sh` は消す — I221 の後は使う所が無い。残すと誤って使われる
- 新しいイシューの題名に `I###:` を付けない — 番号が決まる前に題名を作るため。付けるには登録の後にもう 1 回書き込みが要る。SessionStart の表示は `#427 -` になるが番号で足りる
- 自己完結度レビューの結果は `docs/reviews/` に保存せず、判定の 1 行を本文に書く — 番号が決まる前で名前を付けられず、未追跡のファイルを手元に残すと、なくしたい持ち運びが戻るため。記録は GitHub の本文（とその全版）に残る
- I189（#321・同時起票の採番の衝突）は吸収して取り下げる — 番号を GitHub が振るので衝突が起きない。#321 は bot の停止で見えず今は閉じられないので、bot が戻った後のやり残し（`docs/reviews/backlog/I221.md` に close で書く）に入れる
- I220（起票は Claude が実行する決まり）の見直しは、workflow.md の「Claude が会話の中で起票するとき」の 92 行目（採番の衝突を避ける）を消すだけ。ほかの決まりは起票の形が変わっても成り立つ
- 実走（M-01）で起票する本物のイシューは「I222 の登録し直し」— I222（#402）は bot の停止で GitHub で見えず、どのみち登録し直しが要る。I222 は I221 の後に点検するイシューなので、I221 の後の形で登録するのが筋。登録した後、app-1 の未追跡の `docs/issues/open/I222.md` は使われなくなる（消すかはユーザーの片付けに任せ、close で伝える）
- `docs/claude-code-structure.md` は直さない — I221 の前から古い作りのままで、I222 の点検の範囲
- `check-memo-body-paths.sh` の番号の形を 3 桁以上に広げる — I1000 以降で止まらないように（`--file` を足すついで）。`close/SKILL.md` の `^[0-9]{3}$` は 3 桁の間は動くので今回は変えない
- 写しの書き込みは一時ファイル → `mv` — 失敗で半端な写しが残り、次の実行で「既存ファイル」と誤認されるのを防ぐ

台帳の残りの一覧:
- 一覧 I209 F2（grill-me・バグの兄弟の箇所の grep）: 残す — I221 の範囲（イシューの置き場所）と関係しない
- 一覧 I209 F7（issue-bootstrap・トラックラベルの例に `.github/`）: 同梱 — 同じ節を書き換えるので 1 行で済む（4-4）
- 一覧 I209 F9（grill-me・質問の出し方）: 残す — 質問の書き方の改善で I221 と関係しない
- 一覧 I211 F7・A3・A1（onboarding・python の版の手順）: 残す — 関係しない
- 一覧 I213 F7・F10・F11（dependency-audit・Dependabot の例外）: 残す — 関係しない
- 一覧 I219 F1（worktree.md・打ち切りの合図）: 残す — 関係しない
- 一覧 I224 F5（workflow.md・送り忘れの安全網）: 残す — 関係しない
- 一覧 I224 F9（FILE=-・push の回数の実測）: 残す — I224 の計画どおり別に測る
- 一覧 I220 F1（issue-bootstrap・質問で止まった後の再開で別の番号を採る）: 同梱 — 採番が無くなり、下書きから再開する手順を書く（4-4 の 4）
- 一覧 I220 F2（workflow.md・段階の途中の起票の質問）: 残す — 質問の要否の決まりで I221 と関係しない
- 一覧 I220 F3（issue-bootstrap・`gh issue list --limit 1` で番号を取る）: 同梱 — 起票の出力の URL から取る（4-4 の 5）
- 一覧 I220 F4（onboarding・流れ図）: 残す — 図は TC-14⑦ が固定している
- 一覧 I220 F5（dependency-audit・起票の書き方）: 同梱 — 同じ行を書き換える（4-9）
- 一覧 I220 F6（workflow.md・同梱のときにファイルと GitHub のどちらを直すか）: 同梱 — 新しい節に 1 行（4-9）
- 一覧 I220 F7・F8（workflow.md・止めて聞く条件との関係）: 残す — 関係しない
- 一覧 I223 B1〜B4（FILE=-・bot が戻った後のやり残し）: 残す — bot の停止中は行えない

要件適合性・業務ロジック: 受け入れ条件の範囲を超える仕様の追加は無い。マルチテナント・ステータス遷移は該当なし。境目の上下・既存ファイルの有無・PR の番号・gh の失敗のエッジケースは 4-1 と TC-01 で扱う。

セキュリティ・ベストプラクティス: アプリのコードの変更は無い。ハーネスでは、(1) 引数の形を `^I[0-9]{3,}$` で検査してからパスを組み立てる（パストラバーサル防止）、(2) GitHub の本文（公開リポジトリで誰でも書ける文字列）をシェルの展開に通さず python3 の json → ファイルで扱う、(3) レビュー役は本文を命令ではなくデータとして扱う（issue-reviewer.md の既存の決まりを保つ）、(4) 新しい依存は無い。bandit・npm audit の対象は無い。

P3/P5/P8 影響なし（DB・外部 API の新規・インフラの追加は無い。`gh` は既に使っている）。P6 影響なし（画面・性能の変更は無い）。P9 影響なし（個人情報・テナントデータを扱わない）。

設計品質: 判断を 1 本の補助スクリプトに集め、定数（`NEW_ISSUE_MIN`）は 1 か所に置く。エラーは終了コード（0/1/2）と 1 行の理由で返し、呼び出し側（スキル）は 0 以外で止まる。

## 計画変更記録
- 1（計画レビュー `docs/reviews/I221_plan_review_20261108_1912.md` の Warning 1〜5 への対応）
  - 計画書の記載: 境目 `NEW_ISSUE_MIN=400`／写しは `jq -r .body`／基準のフォルダの記載なし／TC-02 は「出力が空」／I900.md を作るテストは「ほか」
  - 採った方法: 境目を 427 にし、GitHub から読むときに題名が `I###: ` で始まるイシューを拒否する／`jq -j .body`（末尾に改行を足さない）／基準はカレントの git ルートと明記し TC-01 S10 で確かめる／TC-02 を `! grep` の形にし、入口のスキルが `issue-source.sh` を呼ぶ確認（TC-02b）を足す／I900.md を作るテストを全件書き、手元で流さない理由を書いた
  - 理由: #400〜#426 は既存の番号で、400 だと既存のイシューを別の番号で写し違える。マージ前に今の流れで起票されたイシューは #427 以降を取りうるので、題名でも止める。ほかは指摘どおりの書き漏れ・合否の形の直し
  - 計画レビューのやり直し: 不要（findings への対応の追記。方式〔補助スクリプト 1 本・写しの場所〕・範囲・受け入れ条件は変えていない）
- 2（implement）
  - 計画書の記載: JSON を `jq` で読む（環境前提に `jq` があるとした）／TC-01 に FG-S8（一時ファイル → `mv` を直接書き込みに変えると S8 が NG）
  - 採った方法: JSON は `python3 -I` の json で読む（`jq` はこの環境に無く、ハーネスの前提の道具〔`scripts/claude/tests/required-tools.txt`〕にも無い。python3 は前提にある）。gh の出力は一時ファイルに置き、終了時に消す。FG-S8 はやめる（S8 は gh の失敗で書き込みの前に止まる場面で、書き込みの仕方を壊しても結果が変わらない。書き込みの途中の失敗は、わざと起こす自然な方法が無い）。一時ファイル → `mv` の作りは残す
  - 理由: 前提の道具だけで動かす。注入しても NG にならない FG は守りの力が無い（plan-writing-rules「否定・回帰系の決定論テストの自己検証」）
  - 計画レビューのやり直し: 不要（取り出しの道具の差し替えとテストの 1 項目の削除。方式・範囲・受け入れ条件は変えていない）
- 3（implement の /simplify）
  - 計画書の記載: 4-2・4-3 は `check-memo-body-paths.sh`・`issue-review.sh` に `--file` を足すだけで、I### のときの open → closed の探索はそれぞれに残す
  - 採った方法: 2 本とも、I### のときの探索を `issue-source.sh path` の呼び出しに替える（`--file` は計画どおり）。`issue-source.sh` は手元のファイルの探索を 1 回にまとめ、題名は取り出した 1 回を使い回し、一時ファイルの後片付けを最初に 1 回だけ決める。テストは「終了コード 2」の確認を補助関数にまとめ、S5 が S3 の状態を自分で作るようにし、S9 に I### の経路（`issue-source.sh path` 経由で見つかる）を足した
  - 理由: 置き場所の判断を 1 か所に置く（I221 の狙い）。/simplify の 4 観点のうち、再利用・簡素化・高度の点検が同じ重複を挙げた
  - 見送り: (a) grill-me の 2 経路を 1 本にする `edit-target` の命令（新しい命令を足すことになり、計画の範囲を広げる。2 経路は同じ粒度で書いてある）、(b) 新しいイシューの目印を題名ではなくラベルにする（GitHub の画面から起票したイシューの扱いを決める必要があり、計画の判断〔題名＋境目〕で足りる）、(c) 境目の数字 427 を文書に書かない（値は今後変わらない。正は workflow.md と issue-source.sh）、(d) gh の `--jq` を使う（gh を 1 回だけ呼んで本文の末尾を変えない、という条件を守りにくい）。`code-review.sh`・`plan-issue-review.sh` の `find_file` も変えない（今回変えないファイル）
  - 計画レビューのやり直し: 不要（中の作りの整理。方式・範囲・受け入れ条件は変えていない）

## レビュー結果
- [20261108_1912 判定: ✅ 完了](../../reviews/closed/I221_plan_review_20261108_1912.md)
