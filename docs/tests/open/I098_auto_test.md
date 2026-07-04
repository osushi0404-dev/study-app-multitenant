# I098 自動テスト: 全 worktree 横断採番スクリプト

対象: `scripts/claude/next-issue-num.sh` / `scripts/claude/tests/test_next_issue_num.sh`

実行コマンド: `bash scripts/claude/tests/test_next_issue_num.sh`（決定論ゲートとして下記「## 決定論ゲート（自動実走）」で実走）

結果:
- backend: N/A（bash スクリプトのみ・Django 非関与）
- frontend: N/A

## テストケース

隔離方式: `test_wt_port_offset.sh` と同様、temp の bare origin + primary clone + linked worktree を作り、docs/issues を作り込んで `next-issue-num.sh` を実行する。docker 非依存・read-only。

| TC | 目的 | セットアップ | 期待値 |
|----|------|-------------|--------|
| TC-N1 | 再現ケース（横断で他 worktree の高番号 untracked を拾う）＝中核 AC | primary に `docs/issues/open/I050.md`（untracked）、linked wt に `I030.md`（untracked） | primary/linked どちらから実行しても stdout `051`・exit 0 |
| TC-N2 | git 履歴最大（削除済みも使用済み扱い） | `I060.md` を commit → 削除して commit。FS 上の最大は `I040.md` | stdout `061`・exit 0 |
| TC-N3 | I094 decoy（部分一致）を誤カウントしない | 実 issue `I040.md` ＋ decoy `draft-I200.md`・`I055-backup.md`・`plan_I010_2.md`・`templates/issue_template.md` を配置 | stdout `041`（`200`/`055`/`010` に釣られない）・exit 0 |
| TC-N4 | I094 decoy（subject 非近接）を誤カウントしない | 実 issue `I040.md`。commit message に「I900」等の高番号を含める（docs/issues のファイルは触らない） | stdout `041`・exit 0 |
| TC-N5 | 出力契約（stdout は 3 桁 1 行のみ） | 任意の正常系 | stdout が `^[0-9]{3}$` に一致する 1 行のみ・余分な行なし・rc=0 |
| TC-N6 | CWD 非依存（回帰）＋ false-green 反証 | 削除済み `I060` が履歴に在る repo。repo root と `docs/` サブディレクトリから実行 | 両者とも同一 `061`。decoy: pathspec を相対 `'docs/issues'` に差し替えた複製をサブディレクトリで実行すると履歴を落として**異なる（低い）値**を返す＝`:/` 固定が停止要因である反証 |
| TC-N7 | 横断スキャンの false-green 反証 | FS 走査行（`find ... update_max`）を `sed` で無効化した複製を、他 worktree に高番号 untracked が在る状態で実行 | 複製は低い番号を返す（横断が実体の入力である反証）／本体は正しい高番号 |
| TC-DOC1 | issue-flow.md 置換 | 実ファイル | `next-issue-num.sh` が3箇所以上出現・`FS_MAX=$(find docs/issues` が0件 |
| TC-DOC2 | SKILL.md 置換 | 実ファイル | `next-issue-num.sh` 出現・`FS_MAX=$(find docs/issues` が0件 |
| TC-DOC3 | worktree.md §8 更新 | 実ファイル | `next-issue-num.sh`・「権威」出現／旧「primary で行うか」不在 |
| TC-DOC4 | 消費箇所の全件置換 | repo 全体 | 旧採番 bash `FS_MAX=$(find docs/issues` が0件 |

## 決定論ゲート（自動実走）
<!--
  code-review.sh がこの見出し直後の単一 ```bash ブロックを 1 行 1 コマンドで抽出・実走する。
  test_next_issue_num.sh は決定論（docker 非依存）なのでここで実走してよい。
-->
```bash
bash scripts/claude/tests/test_next_issue_num.sh
```
