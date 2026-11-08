# I221 自動テスト: イシューの正を GitHub に一本化する

実行コマンド（例）: アプリのテスト（pytest・Jest・E2E）は対象外（アプリの変更なし）。ハーネスのテスト全体は CI（Harness Tests）が流す。

結果:
- backend: 対象外
- frontend: 対象外

## TC 一覧

### TC-01 `issue-source.sh` の決定論テスト（`scripts/claude/tests/test_i221_issue_source.sh`・新規）
一時ディレクトリに git リポジトリを作り、`gh` は PATH の先頭に置いた仮のコマンド（呼ばれた引数をファイルに追記し、決めた JSON を返す）にする。合格=exit 0。

| ID | 入力 | 期待値 |
|---|---|---|
| S1 | `docs/issues/open/I123.md` がある状態で `snapshot I123`・`path I123`・`body I123` | `snapshot`・`path` は `docs/issues/open/I123.md` を出して exit 0。`body` はファイルの中身と同じ。仮の gh は 1 回も呼ばれない |
| S1b | `docs/issues/closed/I124.md` だけがある状態で `path I124` | `docs/issues/closed/I124.md` を出して exit 0 |
| S2 | ファイルの無い `I123`（400 未満）で `body`・`snapshot`・`gh-number` | どれも exit 2。仮の gh は呼ばれない。`docs/issues/open/I123.md` は作られない |
| S3 | ファイルの無い `I427` で `snapshot`。仮の gh は url `https://github.com/o/r/issues/427`・title `題 "x"`・body（`$(echo pwned)`・バッククォート・`"`・末尾の改行なしを含む）を返す | exit 0・出力は `docs/issues/open/I427.md`。1 行目が `# I427: 題 "x"`、`> - GitHub Issue: #427` の行があり、空行の後の部分が仮の gh の body と 1 バイト単位で同じ（`cmp`）。gh の呼び出しは 1 回 |
| S4 | ファイルの無い `I428` で `snapshot`。仮の gh は url `https://github.com/o/r/pull/428` を返す | exit 2・`docs/issues/open/I428.md` は作られない |
| S5 | S3 の後にもう一度 `snapshot I427`（仮の gh は別の body を返す） | exit 0・同じパス・ファイルの中身は変わらない・gh は呼ばれない |
| S6 | `gh-number`: (a) `GitHub Issue: #402` を含む `I222.md` がある → `402`／(b) ファイルの無い `I430` → `430`（gh は呼ばれない）／(c) `GitHub Issue:` の行が無い `I125.md` → exit 2 | 期待どおりの出力と終了コード |
| S7 | 引数 `I12`・`I427x`・`../I427`・空・`X427` | どれも exit 2・ファイルは作られない |
| S8 | ファイルの無い `I431` で `snapshot`。仮の gh は exit 1 | exit 2・`docs/issues/open/I431.md` も一時ファイルも残らない |
| S9 | `check-memo-body-paths.sh --file <下書き>`: (a) メモにだけあるパスを含む下書き → exit 1／(b) 本文にも書いた下書き → exit 0／(c) 無いファイル → exit 2 | 期待どおりの終了コード |

失敗の注入（FG・テストの中で、スクリプトの写しを `sed` で壊して流し、その S が NG になることを確かめる）:
- FG-S2: `NEW_ISSUE_MIN=400` を `NEW_ISSUE_MIN=0` にした写しで S2 → NG（gh が呼ばれる）
- FG-S4: url の `/issues/` の確認を消した写しで S4 → NG（写しが作られる）
- FG-S3: `jq -r .body` の出力を `echo` 経由に変えた写しで S3 → NG（`cmp` が不一致）
- FG-S8: 一時ファイル → `mv` を、直接書き込みに変えた写しで S8 → NG（半端なファイルが残る）

実装前のため未実行。

### TC-02 現役の文書・スキルに古い採番の手順が残っていない（実装の後に 1 回だけ流して記録する）
決まりの文言の有無は、意図的な変更でしか変わらないので常設のテストにしない（plan-writing-rules「決定論テストの対象の選び方」）。実装の後に次を流し、出力が空であることを記録する:
`grep -rn "next-issue-num" .claude scripts/claude docs/runbooks CLAUDE.md`
- 失敗の注入: 流す前に、同じ grep が今（実装前）は `issue-bootstrap/SKILL.md`・`issue-flow.md`・`worktree.md`・`dependency-audit.md` などに当たることを確認済み（2026-11-08・計画の調査結果 2）

実装前のため未実行。

### TC-03 関係するテスト（手元で選んで流す。全体は CI）
- 下の決定論ゲートの各行。`test_i221_issue_source.sh` のほか、文言を固定しているテスト（i107・i179・i185）と、イシューファイルを仮に作るテスト（review_verdict・i224）

実装前のため未実行。

## 決定論ゲート（自動実走）
```bash
bash scripts/claude/tests/test_i221_issue_source.sh
bash scripts/claude/tests/test_i107_track_label_docs.sh
bash scripts/claude/tests/test_i179_worktree_docs.sh
bash scripts/claude/tests/test_i185_harness_docs.sh
bash scripts/claude/tests/test_i224_push_points.sh
bash scripts/claude/tests/test_review_verdict.sh
bash -n scripts/claude/issue-source.sh
bash -n scripts/claude/check-memo-body-paths.sh
bash -n scripts/claude/issue-review.sh
```
