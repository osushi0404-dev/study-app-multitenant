# I639 計画書: イシューのコメントを流れの入力に入れ、計画の「別イシュー」の番号を確かめる

## 基本情報
- **計画書ID**: plan_I639
- **関連イシュー**: #639
- **Draft PR**: #646
- **作成根拠資料**: docs/issues/open/I639.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I639_review.md
- **作成日**: 2026-11-27

## 1. 背景/目的
- 入口: `/grill-me`・`/plan-issue` はイシューの本文だけを読む。同梱・訂正はコメントで届くので、計画の入力に入らない（I546・I593 で 2 回）
- 出口: 計画で「別イシュー」「後続」と決めた項目を、起票しないまま close まで進んだ（I466）
- 目的: コメントを流れの入力に入れる。計画の「別イシュー」に番号が付いているかを、決定論のスクリプトで確かめる

### 調査結果
**原因の概要**: イシューに後から足した話はコメントにある。でも流れが読むのは本文だけだった。また、計画で「後でやる」と決めたことに番号が付いたかを、誰も機械で確かめていなかった。

**詳細**:
1. `scripts/claude/issue-source.sh:53` は `gh issue view N --json url,title,body` だけを読む。`body`・`snapshot` の出力にコメントは入らない（`grep -n comments scripts/claude/issue-source.sh` は 0 件）。同じ指摘が一覧 `docs/reviews/backlog/I221.md` F9 に残っている
2. コメントの JSON の形（2026-11-27 に `gh issue view 547 --json comments` で確かめた）: 項目は `author{login}`・`authorAssociation`・`body`・`createdAt`・`isMinimized`・`minimizedReason` など。#547 は 12 件で、全部 `osushi0404-claude`・`CONTRIBUTOR`。`gh issue view` は `comments` を求めると全件をページ送りで読む（`preloadIssueComments`）
3. リポジトリは公開（`gh repo view --json visibility` = `PUBLIC`）。誰でもコメントを書けるので、コメントをそのまま計画の入力に入れると、外の人の書いた指示が入りうる。本文は今も作者を問わず読んでいるが、コメントは書ける人がずっと多い
4. 本文を使う箇所（`grep -rn issue-source scripts .claude docs/runbooks`）:
   - `body`: `.claude/skills/grill-me/SKILL.md:18`（読む）・`.claude/skills/plan-issue/SKILL.md:11`（読む）。**grill-me の手順 4 は、手順 1 の本文を下書きにして `gh issue edit --body-file` で GitHub に書き戻す**。`body` にコメントを付けると、コメントが本文に二重に入る
   - `snapshot`: plan-issue だけ。写しのファイルは、計画レビュー役などが読み、`scripts/claude/check-memo-body-paths.sh` が `## 実装対象（既知のもの）`・`## 影響範囲（想定）` の節を `## ` の見出しで切り出す（同ファイル:45-52）。コメントの中の `## ` の見出しや、最後の節に続くコメントの中のパスが、本文の節として数えられうる
   - `path`・`gh-number`: `check-memo-body-paths.sh:36`・`scripts/claude/issue-review.sh:25`・スキル。出力は変えないので影響なし
5. grill-me は、手元にファイルがあると（`path` が exit 0）そのファイルを直して GitHub に書き戻す。新しいイシューで `/plan-issue` の後に `/grill-me` すると、写しのファイル（見出しと注記つき）が本文として書き戻される（今もある穴。コメントを写しに入れると、もっと大きくなる）
6. 出口: 直近 25 本の計画書（`docs/plans/closed/`）で、番号（`#数字`・`I数字 3 桁以上`）の無い行を語ごとに数えた。`別イシュー`・`別のイシュー` は 12 行、`後続` は 1 行、`起票` は 36 行。`起票` は「起票と同梱」「起票したイシューは閉じれば戻る」など話題としての出現がほとんどで、拾うと誤検出が多い。`別の?イシュー`・`後続` の 13 行は、多くが本当に後に回した項目（I466 の 165 行「表の削除は別イシュー」・I609 の 174 行・I539 の 198 行など）。残りは仮の話（I609 の 177 行「要るなら別イシュー」）
7. 外と中の境目: `issue-source.sh` は今も `OUTSIDE_SCRIPTS` にある（`.claude/hooks/unreviewed.py:48-53`・gh を使う）。一覧は変えない。新しいスクリプトは gh・claude・docker を使わないので、中で動く（一覧に足さない）。中で書くのは標準出力だけで、`$TMPDIR` の外に書かない。なお、このブランチでは `issue-source.sh` を変えるので、その入口は周ごとに 75 で止まる（`docs/runbooks/danger-ops.md`・I615）。実物の gh で確かめるのは手動テスト No.1 だけ
8. 台帳の残りの一覧（9 の「一覧」の行）

## 2. 受け入れ条件
- [ ] AC1: コメントのある新しいイシューで `issue-source.sh body` を流すと、本文の後ろにコメント（日時・書いた人・本文）が出る。`snapshot` の写しのファイルにも同じものが入る。コメントの無いイシューと手元のイシューファイルは、今までと同じ出力になる
- [ ] AC2: コメントを付けても、本文の節の切り出し（`check-memo-body-paths.sh` の節）の結果は変わらない。コメントの中の見出し・パスが本文の節として数えられない
- [ ] AC3: 公開リポジトリの外の人（立場が OWNER・MEMBER・COLLABORATOR・CONTRIBUTOR のどれでもない人）のコメントと、隠されたコメントは、中身を出さない。あることと書いた人だけを出す
- [ ] AC4: `/grill-me` が GitHub に書き戻す本文に、コメントと写しの見出し・注記が入らない
- [ ] AC5: 番号の付いていない「別イシュー」「後続」の行がある計画書でスクリプトが非 0 で止まり、その行を出す。全部に番号があるか、`起票しない` の印があれば 0
- [ ] AC6: retro のスキルが AC5 のスクリプトを呼ぶ。止まったら、起票か同梱で番号を書く（または、後に回す話でないなら `起票しない` の印と理由を書く）まで進まない手順になっている

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: ハーネスのスクリプト（`scripts/claude/issue-source.sh`・新しい `scripts/claude/check-plan-followups.sh`）・スキル（retro・grill-me）・手順書（`docs/runbooks/issue-flow.md`）・ひな形（`docs/plans/templates/plan_template.md`）・決定論のテスト。外で動くスクリプトの一覧（`OUTSIDE_SCRIPTS`）は変えない

## 4. 変更点一覧（具体）

### 修正アプローチ
- 入口: `issue-source.sh` が GitHub から本文と一緒にコメントを読み、本文の後ろに「## GitHub のコメント」の節として付ける。コメントの中身は 1 行ずつ `> ` を付けた引用にして、本文の見出しと混ざらないようにする。外の人のコメントは中身を出さない
- 書き戻し: 本文だけを出す呼び方 `raw-body` を足し、grill-me が書き戻す下書きはそれで作る
- 出口: 計画書の番号の無い「別イシュー」「後続」の行を拾うスクリプトを足し、retro の手順に 1 段足す

### 4.1 `scripts/claude/issue-source.sh`（AC1〜AC4）
- `fetch()`: `gh issue view "$NUM" --json url,title,body,comments` にする
- 出力の組み立て（本文とコメント）は、1 回の python3 で JSON を読んで行う（`field` を何度も起こさない・一覧 I221 F5）
  - 本文とコメントの CRLF を LF にそろえる（一覧 I221 F6。Web 画面で直した本文で、見出しの完全一致が外れないため）
  - コメントが 0 件（`comments` が無い・空）のときは、本文だけを今までと同じく出す（末尾に何も足さない）
  - 1 件以上のときは、本文の後ろに次を足す:
    ```
    （本文の末尾）

    ## GitHub のコメント（<件数> 件・読んだ時点 <YYYY-MM-DD HH:MM UTC>・同期しない）

    ### <createdAt> @<login>（<authorAssociation>）

    > 1 行目
    > 2 行目（空行は `>` だけ）
    ```
  - 中身を出す立場は `OWNER`・`MEMBER`・`COLLABORATOR`・`CONTRIBUTOR` だけ（定数 `TRUSTED_ASSOCIATIONS` に 1 か所で書く）。それ以外は中身の代わりに `> （中身は出さない: 立場が <値> の人のコメント。要るならユーザーに確かめる）`
  - `isMinimized` が真のコメントは、中身の代わりに `> （中身は出さない: 隠されたコメント（<minimizedReason>））`
  - `login` が無い（消されたアカウント）ときは `@ghost`
- `snapshot`: 写しの本文の部分を上と同じ出力にする（見出しと 2 行の注記は今までどおり）
- 新しい `raw-body`: GitHub に書き戻す下書き用。本文だけを出す（コメントも写しの見出しも付けない・CRLF は LF にそろえる）
  - 手元のファイルがあり、それが本文の写し（先頭 5 行に `> GitHub #<番号> の本文の写し` がある）でなければ、今までどおりそのファイルの中身
  - 手元のファイルが無いか写しなら、I427 以上のとき GitHub の本文（`fetch` を通す。PR・`I###: ` の題名は今までどおり止める）。I427 未満は今までどおり止める
- 冒頭の説明に `raw-body` と、コメントの扱いを足す。番号の決まりの参照先を `docs/runbooks/issue-flow.md「イシューの番号と置き場所（I221）」` に直す（一覧 I546 F9）

### 4.2 `.claude/skills/grill-me/SKILL.md`（AC4）
- 手順 1 の説明に「新しいイシューは、本文の後ろに GitHub のコメント（立場で絞ったもの）が付く」を 1 文足す
- 手順 4 の分け方を、ファイルの有無から次に変える:
  - **今までのイシュー**（`issue-source.sh path` が exit 0 で、そのファイルが本文の写しでないもの）: 今までどおり
  - **新しいイシュー**（`path` が exit 1、またはファイルが本文の写し）: 下書きの中身は「手順 1 で出た本文」でなく `bash scripts/claude/issue-source.sh raw-body $ARGUMENTS` の出力にする。写しのファイルは直さない（計画を始めた後の変更は計画変更記録と写しに書く・`docs/runbooks/issue-flow.md`）

### 4.3 新しい `scripts/claude/check-plan-followups.sh`（AC5）
- 使い方: `bash scripts/claude/check-plan-followups.sh I###`（計画書は git ルートの `docs/plans/open/plan_I###.md`、無ければ `docs/plans/closed/`）
- 拾う行: 次の全部に当たる行
  - `別イシュー`・`別のイシュー`・`後続` のどれかを含む（定数 `DEFER_RE`。調査結果 6: `起票` は誤検出が多いので入れない）
  - 自分の番号（`I###`）を除いて、`#数字` も `I数字 3 桁以上` も含まない
  - `起票しない` を含まない（後に回す話でない行に付ける印。理由を同じ行に書く）
  - ``` で囲んだコードの中でない
- 出力: 拾った行ごとに `<計画書のパス>:<行番号>: <行>`。最後に直し方を 1 行（番号を書く／起票しないなら `起票しない: 理由`）
- 終了コード: 0=拾う行なし／1=拾う行あり／2=使えない（引数の形が `^I[0-9]{3,}$` でない・計画書が無い・git の外）
- gh・ネットワークを使わない。書くのは標準出力・標準エラーだけ

### 4.4 `.claude/skills/retro/SKILL.md`（AC6）
- 手順 4-0 の後に 4-1 を足す:
  - `bash scripts/claude/check-plan-followups.sh $ARGUMENTS` を流す
  - exit 1 なら、出た行ごとに、手順 4 の「採用（新規起票）」か「既存イシューに同梱」をして、その行に `#番号` を書き足して commit する。後に回す話でない行（仮の話・範囲の説明）には `（起票しない: <理由>）` を書き足す。exit 0 になるまで流し直す
  - exit 2 は止めて調べる
  - 「## 自律判断の記録」に、行ごとの行き先（`#番号`・起票しない）を書く

### 4.5 `docs/runbooks/issue-flow.md`・`docs/plans/templates/plan_template.md`（決まりとひな形）
- `issue-flow.md`「イシューの番号と置き場所（I221）」: 本文の写しの項目に「コメントも付く（立場で絞る）・GitHub に書き戻すのは `raw-body`」を 1 文で足す。「既存イシューに同梱するとき」の項目に「コメントは次の `/grill-me`・`/plan-issue` の入力に入る」を足す
- `plan_template.md` 9 の節のコメント: 「別イシュー・後続にする項目には `#番号` を書く（起票は retro。後に回す話でない行は `起票しない: 理由`。retro の `check-plan-followups.sh` が確かめる）」を 1 行足す

### 4.6 決定論のテスト（AC1〜AC5）
- 新しい `scripts/claude/tests/test_i639_issue_comments.sh`（`issue-source.sh`。仮の gh は `test_i221_issue_source.sh` と同じ形でコメントの JSON を返す）
- 新しい `scripts/claude/tests/test_i639_plan_followups.sh`（`check-plan-followups.sh`）
- 既存の `scripts/claude/tests/test_i221_issue_source.sh` は直さずにそのまま通ること（仮の gh の JSON に `comments` が無い＝コメント 0 件の扱い）を確かめる

### 4.7 一覧の片付け
- `docs/reviews/backlog/I221.md` の F5・F6・F9 と `docs/reviews/backlog/I546.md` の F9 を、直したら消す

## 5. 実装手順（ステップ）
1. `issue-source.sh` のコメントの出力と `raw-body`（4.1）と、そのテスト（4.6 の 1 本目）→ TC-01・TC-02・TC-03
2. grill-me の手順 1・4（4.2）。ステップ 1 の後（`raw-body` に頼る）→ TC-04
3. `check-plan-followups.sh`（4.3）とテスト（4.6 の 2 本目）。ステップ 1・2 と並行してよい → TC-05
4. retro の 4-1（4.4）。ステップ 3 の後 → TC-06
5. 手順書・ひな形（4.5）と一覧の片付け（4.7）。ステップ 1〜4 の後 → TC-07
6. 実物の GitHub での確かめ（手動 No.1）は test-gate で行う

## 6. テスト計画
### 自動
- 決定論: `test_i639_issue_comments.sh`・`test_i639_plan_followups.sh`・既存の `test_i221_issue_source.sh`（`docs/tests/open/I639_auto_test.md`）。失敗の注入（FG）つき。テストのレベルはスクリプト単体（仮の gh を PATH の先頭に置く。ネットワークを使わない）
- pytest・Jest・E2E は対象外（アプリを変えない）
### 手動
- No.1: 実物の GitHub で、コメントのある #547 の `body` に 12 件のコメントが出て、コメントの無いイシューは本文だけになる（`docs/tests/open/I639_manual_test.md`）
- No.2: 実物の計画書（`docs/plans/closed/plan_I466.md`）で、165 行が拾われる

## 7. ロールバック
- この PR のコミットを revert する。GitHub のデータ・DB は変えない（`issue-source.sh` は読むだけ。写しはコミットしたファイルで、revert で消える）

## 8. Risk & 回避策
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: 外の人のコメントに書かれた指示が、計画の入力に入る | 立場で絞り、外の人と隠されたコメントは中身を出さない（AC3・TC-02） | 回避 |
| R2: CONTRIBUTOR は一度でもマージされた人なら誰でもなれる | 今は本人と App の 2 つだけ。本文は今も作者を問わず読んでいるので、コメントだけ本文より強く絞らない。協力者が増えたら定数を見直す | 受け入れ |
| R3: コメントの中の見出し・パスが本文の節として数えられ、`check-memo-body-paths.sh` が素通りする | コメントを「## GitHub のコメント」の節の下に置き、中身は `> ` の引用にする（AC2・TC-01） | 回避 |
| R4: grill-me がコメントや写しの見出しを GitHub の本文に書き戻す | `raw-body` を下書きにする（AC4・TC-03・TC-04） | 回避 |
| R5: コメントが多いと出力が長くなる | 本文を読む他のスクリプトは `path` だけを使う（調査結果 4）。長さで切ると同梱の話が消えるので切らない | 受け入れ |
| R6: 計画書の「別イシュー」の拾い方の誤検出・取りこぼし（`起票` だけの行・`PR #番号` だけの行は拾わない） | 誤検出は `起票しない: 理由` の印で通す（理由が同じ行に残る）。取りこぼしは、語を増やすと誤検出が 36 行増える（調査結果 6）ので、計画レビューで見る | 受け入れ |
| R7: このブランチでは `issue-source.sh` の入口が 75 で止まる | 流れで使うのは plan-issue の最初だけで、もう済んでいる。手動 No.1 は `!` で流す（I615） | 回避 |

## 9. 確定事項と自律判断
イシューに明記されている:
- `body`・`snapshot` が本文の後ろにコメント（日時と本文）を付ける。手元のイシューファイル（I427 未満）は今までどおり
- 計画書の番号の無い「別イシュー」「後続」の行を拾うスクリプトを `scripts/claude/` に足し、retro から呼ぶ。拾い方・誤検出の扱いは計画で決める
- 外で動く入口の一覧と境目は `plan-writing-rules.md`「外と中の境目を動かす計画」に従う
Claude が決めた（技術的な選択と理由）:
- コメントを `> ` の引用にして「## GitHub のコメント」の節の下に置く（仮定で決めた）— 本文の見出しの切り出しと混ざらず、Markdown として読める。見出しを下げる案は中身を書き換えるので採らない
- 中身を出す立場を OWNER・MEMBER・COLLABORATOR・CONTRIBUTOR に絞る（仮定で決めた）— 公開リポジトリで誰でもコメントできるため（調査結果 3）。中身は出さなくても「ある」ことは出し、要るならユーザーに確かめられるようにする
- `raw-body` を足す（仮定で決めた）— AC1 で `body` にコメントを付けると grill-me の書き戻しが壊れる（調査結果 4）。`body` からコメントを外して別のコマンドにする案は、イシューの解決方針（`body` に付ける）と違うので採らない
- grill-me の分け方を「写しなら新しいイシュー」にする（仮定で決めた）— 写しのファイルを書き戻す今の穴（調査結果 5）も同時に塞げる。新しいイシューの本文の正は GitHub（`issue-flow.md`）
- 拾う語は `別イシュー`・`別のイシュー`・`後続` だけ。`起票` は入れない（仮定で決めた）— 調査結果 6 の誤検出の数
- 自分の番号は番号として数えない（仮定で決めた）— 「I466 の表の削除は別イシュー」のような行を通さないため
- 印は `起票しない`（仮定で決めた）— 新しい記号を作らず、読んで意味が分かる言葉にする。理由を同じ行に書く
- 新しいスクリプトは計画書だけを見る。レビュー文書の「自律判断の記録」は見ない（仮定で決めた）— AC の対象は計画書。retro・close が書く記録は番号つきで書く決まり
- 新しいスクリプトは `OUTSIDE_SCRIPTS` に足さない — gh・claude・docker を使わない（調査結果 7）
- 一覧 docs/reviews/backlog/I221.md F4: 残す — `gh-number` の判定はこのイシューの入口・出口と関係しない
- 一覧 docs/reviews/backlog/I221.md F5: 同梱 — 出力の組み立てを 1 回の python3 にするので、同時に直る
- 一覧 docs/reviews/backlog/I221.md F6: 同梱 — コメントは Web 画面で書くことが多く、CRLF が入りやすい。そろえるのは 1 行
- 一覧 docs/reviews/backlog/I221.md F8: 残す — issue-bootstrap の再開手順は範囲外
- 一覧 docs/reviews/backlog/I221.md F9: 同梱 — このイシューそのもの（`FILE=docs/runbooks/workflow.md` だが、直すのは `issue-source.sh`）
- 一覧 docs/reviews/backlog/I221.md F10: 残す — 開始時の表示は範囲外
- 一覧 docs/reviews/backlog/I546.md F9: 同梱 — `issue-source.sh` の冒頭の参照先を直す 1 行
- 一覧 docs/reviews/backlog/I599.md F25: 残す — 下書きを Write で写す形はそのまま（スクリプトが下書きを書く案は、外で動くスクリプトに書き込み先を渡すことになり、範囲より大きい）。後半の「手順 1 と取り違えやすい」は、手順 4 で `raw-body` のコマンドを書くので解消する
- 一覧 docs/reviews/backlog/I209.md F2・F9: 残す — grill-me の質問の出し方は範囲外（スキル 12 の見直しのイシュー）
- 一覧 docs/reviews/backlog/I223.md B1〜B4・docs/reviews/backlog/I224.md F9（`FILE=-`）: 残す — 関係しない
Danger Ops:
- 無

要件適合性: 受け入れ条件を超える仕様の追加は、AC3（立場で絞る）と AC4（書き戻しを壊さない）だけ。どちらも AC1 を入れると生じる穴の手当てで、イシューの目的の中。マルチテナント・ステータス遷移は該当なし。
セキュリティ: 入力（GitHub の JSON）は python3 の `json` で読み、シェルに通さない（本文の `$(…)`・バッククォートを実行しない。既存の S3 と同じ）。外の人のコメントは中身を出さない（R1）。新しいスクリプトは計画書を読むだけで、引数は `^I[0-9]{3,}$` だけを受け付けてパスを組む（パスの逃げを防ぐ）。認証・認可・個人情報・依存の追加は無い。bandit・npm audit の対象のコードは変えない（シェルと Markdown だけ）。shellcheck は pre-commit の既定（警告で止める）。
テスト計画: バグ修正（I466 の取りこぼし・I221 F6）の再発防止は TC-05 の P1（I466 の行）・TC-01 の CRLF の場面。テストのレベルはスクリプト単体。認可の変更は無い。
P3/P5/P8 影響なし（DB・外部 API の新規・依存の変更・新しいインフラが無い。gh の読み取りの項目を 1 つ増やすだけ）。
P6 影響なし（画面なし。コメントの量は gh がページ送りで読む）。
P9 影響なし（個人情報・テナントデータを扱わない。出すのは GitHub の公開のコメントと login だけ）。
設計品質: 定数（拾う語・中身を出す立場・新しいイシューの番号の下限）はスクリプトの冒頭に 1 か所で書く。空の値（`comments` が無い・`login` が無い・`minimizedReason` が無い）の扱いは 4.1 に書いた。エラーは今までどおり exit 2 で止める。

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | 外の人・隠されたコメントの中身が `body`・`snapshot` のどこにも出ない（TC-02。FG で絞りを外すと落ちる） |
| V2 | 2 | 読んで可 | コメントの中の `## ` の見出しが写しの節の切り出しに入らない（TC-01 の S4。FG で引用を外すと落ちる） |
| V3 | 3 | 読んで可 | `raw-body` は、写しがあっても GitHub の本文だけを出し、コメント・写しの見出しを含まない（TC-03） |
| V4 | 2 | 読んで可 | 計画書の番号の無い行が拾われ、自分の番号だけの行も拾われる（TC-05。FG で除外を外すと落ちる） |

## 計画変更記録
-
