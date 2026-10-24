# I187 敵対的レビュー記録（2026-10-25・BP 基準の最終周）

- 起動元: `/code-review I187` の続き。3 周目（`I187_adversarial_review_20261025_0040.md`・VERDICT: HIGH・上限到達）の後のユーザー判断
- ユーザー判断（2026-10-25）: 「レビューはする。ただしループエンジニアリング、ハーネスエンジニアリングのベストプラクティスと開発をサクサク進めるという観点で見て、問題なければ OK とする」
- 判定の基準（ユーザー指定）: High に数えるのは、(a) Claude が自分でできる確認を人に頼む流れに戻る (b) 誤って合格・「承認なし」を返して事故につながる (c) 普通の運用で誤って止まり開発が毎回詰まる、のどれかに実害があるものだけ。列挙を増やせば塞がる類・わざと回避する書き方・理論上の穴は Low
- 範囲: `cb3182a...HEAD`・開始 HEAD 83f4512・3 体（固定 3 観点）・時間切れなし（3 体とも 2〜3 分で報告）

## 4 周目（BP 基準）

| 観点 | 時間切れ | 新規 Critical | 新規 High |
|---|---|---|---|
| ロジック回避・実機 repro | なし | 0 | 1 |
| テストの false-green・tautology | なし | 0 | 0 |
| 要件・設計の妥当性 | なし | 0 | 0 |

### findings
| 重大度 | 指摘 | 該当箇所 | 対応 |
|---|---|---|---|
| High（c） | 3 周目で言い換えを列挙で増やした結果、言葉が当たる範囲が広がりすぎた。GitHub の PR の Approve・対話の `claude --worktree` の終了時の確認・アプリのダイアログの操作感など、Claude Code の承認画面と関係のない正当な Human の行が止まる。理由を正しく書くほど当たり、言い換えて避けるしかない（実在の I178 No.5・I179 No.6・I184 No.4 で確認） | `check-manual-test-executor.sh` の `PROMPT_WORDS` | 修正（方式の見直し）: 言葉が当たっても、理由に `check-permission-prompt.sh` では確かめられないわけ（スクリプトの名前を含む）が書いてあれば通す。考えずに Human に振った行は止まり、本当に人にしかできない行は理由を書けば通る。X16（Approve・理由あり → 0）・X17（理由にスクリプトの名前なし → 1）を追加し、足す前の本体で X16 が不合格になることを確認。`plan-writing-rules.md` の Human の欄にも書いた |
| Medium | `claude -p` に渡す引数（`--setting-sources user` など）を守るテストが無い。消しても全テストが合格する | `check-permission-prompt.sh`・テスト | 修正: 起動する claude を `CLAUDE_BIN` で差し替えられる形にし、引数を書き出す偽物で確かめる Q18 を追加（足す前の本体で不合格を確認） |
| Medium | 判定できない（2）が出たときの次の手が書かれていない | `test/SKILL.md` | 修正: 「もう 1 回流す。それでも 2 なら NG として止めて報告する（人に聞かない）」を `/test` の手順とスクリプトの説明に書いた |
| Medium | 言葉の誤検知（「イシュー承認後」「編集ダイアログ」） | `check-manual-test-executor.sh` | 上の High と同じ修正で対処（ダイアログの画面確認は Playwright で Claude の行にするのが正しい） |
| Low | bash の判定でも MCP サーバーを起動していて遅い | `check-permission-prompt.sh` | 修正: bash の判定では `--strict-mcp-config` で MCP を起動しない（本物の lint 0・build 10 を再確認） |
| Low | Q14 は確認の行を消しても例外で 2 になり、行そのものを守っていない・⑤d に `npx`・`sh -c` が無い・`permission prompt` と大文字小文字のケースが無い・実施者が `Claude（…）＋ Human（…）` の行を見ない | 各所 | 見送り（記録のみ。fail-closed または件数が少ない） |

3 周目のテストへの変異（`\|` の扱い・列なし・太字・「ユーザー」・言い換え・`subtype`・拒否の行との突き合わせ・広い exec の許可）は、すべてテストに捕まった（false-green なし）。

## 判定
ユーザーの基準で High 1 件は方式を変えて修正し、Medium も対処した。修正後、決まった確認 59/59・`test_check_manual_test_executor.sh` 23/23・`test_check_permission_prompt.sh` 20/20 が合格、本物の判定（lint 0・build 10）も確認した。ユーザーの指定どおり、この基準で問題なしとして OK とする（修正を反証する周回は行わない）。

REVIEWED_COMMIT: 83f4512c634b56e4dcd1da1ed9cbd9d48b21af64
ROUNDS: 1
VERDICT: OK
