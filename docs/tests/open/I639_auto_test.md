# I639 自動テスト: イシューのコメントを流れの入力に入れ、計画の「別イシュー」の番号を確かめる

実行コマンド: 下の「決定論ゲート（自動実走）」（CI の Harness Tests も流す）。pytest・Jest・E2E は対象外（アプリを変えない）

結果:
- backend: 対象外
- frontend: 対象外
- harness: 2026-11-27 implement で手元で実行。test_i639_issue_comments.sh（13 場面・FG 6）・test_i639_plan_followups.sh（11 場面・FG 4）・test_i221_issue_source.sh はすべて PASS（exit 0）。bash -n も OK。正式な結果は CI の Harness Tests

## テストケース

仮の gh は PATH の先頭に置き、決めた JSON（`url`・`title`・`body`・`comments`）と終了コードを返す（`test_i221_issue_source.sh` と同じ形）。各テストは空の git リポジトリを一時フォルダに作って、そこで流す。

### TC-01 `issue-source.sh` のコメントの出力（AC1・AC2）— `test_i639_issue_comments.sh`
| 場面 | 入力 | 期待（全部 exit 0 で合格） |
|---|---|---|
| S1 | 新しいイシュー #500・コメント 2 件（OWNER と CONTRIBUTOR）・本文の末尾に改行なし | `body` の出力 = 本文 + `\n\n## GitHub のコメント（2 件・読んだ時点 …・同期しない）\n\n### 2026-11-01T00:00:00Z @alice（OWNER）\n\n> 1 行目\n>\n> 3 行目\n\n### … @bob（CONTRIBUTOR）\n\n> x\n`（読んだ時点の日時の部分だけ正規表現で照合し、ほかは完全一致） |
| S2 | コメント 0 件（`comments: []`）と `comments` の項目が無い JSON | `body` の出力が本文と完全一致（`cmp`）。`snapshot` の写しの 6 行目以降も本文と完全一致 |
| S3 | S1 と同じで `snapshot` | 写しの 1〜4 行目は今までの見出しと注記。6 行目以降が S1 の `body` の出力と完全一致 |
| S4 | コメントの中身に `## 受け入れ条件`・`## 影響範囲（想定）`・`` `scripts/claude/x.sh` `` を含む。本文の最後の節が `## 影響範囲（想定）` | 写しで `^## 受け入れ条件` の行が本文の 1 行だけ（`grep -c` が 1）。写しに対する `check-memo-body-paths.sh` の節の切り出し（`awk` で `## 影響範囲（想定）` の節）に `scripts/claude/x.sh` が入らない |
| S5 | 本文とコメントの改行が CRLF | `body` の出力に `\r` が無い（`! grep -q $'\r'`） |
| S6 | 手元にイシューファイルがある I123 | `body` は今までどおりファイルの中身。gh は呼ばれない（呼び出しの記録が 0 行） |

### TC-02 立場と隠されたコメントの絞り（AC3）— `test_i639_issue_comments.sh`
| 場面 | 入力 | 期待 |
|---|---|---|
| S7 | コメント 3 件: 立場 `NONE` で中身 `SECRET-NONE`、`FIRST_TIME_CONTRIBUTOR` で `SECRET-FTC`、`OWNER` で `isMinimized: true`・`minimizedReason: "SPAM"`・中身 `SECRET-MIN` | `body` の出力にも `snapshot` の写しにも `SECRET-` が無い。各コメントの見出し行（`@login（立場）`）はある。中身の代わりに `> （中身は出さない: 立場が NONE の人のコメント。要るならユーザーに確かめる）`・`> （中身は出さない: 隠されたコメント（SPAM））` がある |
| S8 | `author` が `null` のコメント（立場 `OWNER`） | 見出しが `@ghost（OWNER）` |

### TC-03 `raw-body`（AC4）— `test_i639_issue_comments.sh`
| 場面 | 入力 | 期待 |
|---|---|---|
| S9 | 新しいイシュー（コメント 2 件）・手元にファイル無し | `raw-body` の出力が本文と完全一致（コメントの節が無い） |
| S10 | S9 の後に `snapshot` で写しを作ってから `raw-body` | 出力が GitHub の本文と完全一致（写しの見出し・注記・コメントが無い）。gh が 1 回呼ばれる |
| S10b | S10 の写しの 3 行目の注記を書き換えてから `raw-body` | 出力が写しのファイルの中身（今までのイシューファイルとして扱う）。gh は呼ばれない |
| S11 | 手元に今までのイシューファイル I123（写しでない） | 出力がファイルの中身。gh は呼ばれない |
| S12 | PR の番号（url が `/pull/`）・題名が `I229: ` のイシュー・手元にファイルの無い I123 | どれも exit 2 |

### TC-01〜03 の失敗の注入（FG）— `test_i639_issue_comments.sh`
`issue-source.sh` を sed で壊した写しで場面を流し、不合格になることを確かめる（sed が当たらなければ FAIL）。
- FG-S4: コメントの行に `> ` を付ける処理を外す → S4 が落ちる
- FG-S7: 立場の絞りを外す（全部を信頼する）→ S7 が落ちる
- FG-S7b: 隠されたコメントの判定を外す → S7 が落ちる
- FG-S2: コメント 0 件でも節の見出しを出す → S2 が落ちる
- FG-S10: `raw-body` が写しを今までのファイルとして扱う（写しの判定を外す）→ S10 が落ちる
- FG-S5: CRLF をそろえる処理を外す → S5 が落ちる

### TC-04 grill-me の手順（AC4）— レビューで読む
- 手順 4 の新しいイシューの経路が、下書きの中身を `bash scripts/claude/issue-source.sh raw-body $ARGUMENTS` で作る。写しのファイルがあるときも新しいイシューの経路に入る
- 決定論のテストにしない（スキルの文言の有無は意図的な変更でしか消えない・`plan-writing-rules.md`「決定論テストの対象の選び方」）

### TC-05 `check-plan-followups.sh`（AC5）— `test_i639_plan_followups.sh`
計画書は一時の git リポジトリの `docs/plans/open/plan_I777.md` に置く。
| 場面 | 計画書の行 | 期待 |
|---|---|---|
| P1 | `- 残す: モデル・admin・マイグレーション。表の削除は別イシュー（Danger Ops）で行う`（I466 の 165 行と同じ形） | exit 1。出力に `docs/plans/open/plan_I777.md:<行番号>: ` とその行がある |
| P2 | P1 の行の末尾に ` → #492` | exit 0 |
| P3 | `- 要るなら別イシュー（起票しない: 仮の話）` | exit 0 |
| P4 | ``` で囲んだ中に `後続` の行 | exit 0 |
| P5 | `- I777 の後続で直す` | exit 1（自分の番号は番号に数えない） |
| P6 | `- I778 の後続で直す`・`- 別のイシュー I1000 に同梱` | exit 0 |
| P7 | 番号の無い行が 2 行（`別イシュー` と `後続`） | exit 1。出力に 2 行とも出る |
| P8 | `docs/plans/open/` に無く `docs/plans/closed/plan_I777.md` に P1 の行 | exit 1 |
| P9 | 引数 `I77`・`../I777`・空・計画書が無い `I888` | どれも exit 2 |
| P10 | 対象の語の無い計画書 | exit 0 |

FG（`check-plan-followups.sh` を sed で壊した写しで流す）:
- FG-P5: 自分の番号を取り除く処理を外す → P5 が落ちる
- FG-P4: コードの囲みを飛ばす処理を外す → P4 が落ちる
- FG-P3: `起票しない` の印の判定を外す → P3 が落ちる
- FG-P2: 番号の除外を外す → P2 が落ちる

### TC-06 retro の手順（AC6）— レビューで読む
- 手順 4-1 が `bash scripts/claude/check-plan-followups.sh $ARGUMENTS` を単体で流し、exit 1 なら起票か同梱で `#番号` を書く（または `起票しない: 理由`）まで流し直し、exit 2 で止まる。自律判断の記録に行き先を書く
- 決定論のテストにしない（TC-04 と同じ理由）

### TC-07 手順書・ひな形・一覧（4.5・4.7）— レビューで読む
- `docs/runbooks/issue-flow.md` と `docs/plans/templates/plan_template.md` に 4.5 の文がある。一覧 I221 の F5・F6・F9 と I546 の F9 が消えている

### 既存のテストの回帰
- `test_i221_issue_source.sh` を直さずに流して全部 PASS（仮の gh の JSON に `comments` が無い＝0 件の扱い。TC-01 S2 と同じ道）

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i639_issue_comments.sh
bash scripts/claude/tests/test_i639_plan_followups.sh
bash scripts/claude/tests/test_i221_issue_source.sh
bash -n scripts/claude/issue-source.sh
bash -n scripts/claude/check-plan-followups.sh
```
