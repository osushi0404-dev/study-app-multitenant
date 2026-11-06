# I226 レビュー: I225 のレビューの残り: 失効の確かめの取り違え・鍵を出す書き方の検査の狭さ

## 変更概要
- F1: `revoke.sh` が失効の前に鍵の有効を確かめ、もともと無効な鍵を「失効を確認」と出さない
- F6: G10 が `gh auth token` を落とし、行末の `\` で分けた `--json` 付きの書き方を通す
- 同梱: F2（ログインなしの `auth status` の置き換えを exit 1 に）・F4（`plan-writing-rules.md` の記述）・omission-lint を自動テスト文書を書いた直後に PostToolUse のフックで流す
- F5 は grill-me で見送り

## 変更点
- `scripts/claude/gh-app/revoke.sh`: `token_state`（0=有効・1=401・2=確かめられない）を足し、`revoke_one` が失効の前にも読む。もともと無効は 3 を返し、`--stdin` は「最初から無効」で exit 1、控えは「もともと無効」で控えを消して成功扱い
- `scripts/claude/gh-app/gh`: 置き換えた `auth status` は、アカウントが 0 件のとき exit 1
- `scripts/claude/code-review.sh`: `--lint-auto-test <ファイル>…` の入口（既存の `omission_lint` を呼ぶだけ）
- `scripts/claude/hooks/posttooluse_check.py`: `docs/tests/open/I<数字>_auto_test.md` の Edit/Write の直後に上の入口を呼び、宣言漏れなら exit 2 で知らせる
- `scripts/claude/tests/test_i223_gh_app.sh`: G8 に空の hosts、G9 に g・h・i、G10 に `gh auth token` と行末の `\` のつなぎ、それぞれの FG
- `scripts/claude/tests/test_posttooluse_check.sh`: TC-10g〜i
- 文書: `github-app-setup.md`（失効の新しい表示）・`plan-writing-rules.md`（F4）・`CLAUDE.md`（PostToolUse の説明の 1 文）・`docs/reviews/backlog/I225.md`（F2・F4 の行を消した）

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `scripts/claude/gh-app/revoke.sh`・`scripts/claude/gh-app/gh`・`scripts/claude/code-review.sh`・`scripts/claude/hooks/posttooluse_check.py`・`scripts/claude/tests/test_i223_gh_app.sh`・`scripts/claude/tests/test_posttooluse_check.sh`・`docs/runbooks/github-app-setup.md`・`docs/runbooks/plan-writing-rules.md`・`docs/reviews/backlog/I225.md`・`CLAUDE.md`

## テスト結果
- 自動: （test-gate で記入）
- 手動: （test-gate で記入）

## 計画との差分
- 振る舞いの差分なし。コードの形は計画変更記録 2 のとおり整理した（/simplify）

## ロールバック
- PR を revert する。手元の入口を入れ直していれば `bash scripts/claude/gh-app/install.sh` をもう一度流す

## 自律判断の記録
- [plan] omission-lint を流す場所を PostToolUse のフックにした — pre-commit は CI の `--all-files` で古い open の I034 が落ち、避けると `ci.yml` も直すことになり高リスクのパスに当たる。スキルの手順は流し忘れる。フックは決定論で最も早く、高リスクのパスでない（plan_I226.md §9）
- [plan] F2 は終了コードだけ直す — スパイクで本物の `gh` が「ログインしていない」の案内を標準エラーに出すことを確かめた（文を足すと 2 回出る）
- [plan-review] PLAN_VERDICT: OK（20261106_2128）。Warning 3 件は計画書・テスト文書に反映し、再レビューはしない — 方式・範囲・受け入れ条件を変えない追記だけ（計画変更記録 1）。Info の戻り値の定数化は見送り — コメントで足りる
- [implement] テストを先に書き、本体を直す前に落ちることを確かめてから直した（TC-02・TC-03 の記録） — 新しいケースが false-green でないことを、直す前の版で示すため
- [implement] フックがこのワークツリーの版を動かすことを、実装の直後に M-02 の手順で確かめた（宣言漏れの知らせが届き、見出しを直すと消えた。確かめ用のファイルは消した） — 計画レビューの Warning 1。新しいセッションでの確かめは要らなかった
- [implement] /simplify の 4 つの観点の指摘のうち、G10 の結合の写し・フックの出口が 2 本・`revoke_one` の余計な変数・偽の gh の余計なファイルは直した。`omission_lint` を別のライブラリに出す案（高さの観点・Low）は見送った — `--route` と同じ入口の形にそろえてあり、本体が壊れたときは TC-10g が捕まえる
- [implement] shellcheck は手元に無いので、commit 時の pre-commit と CI に任せた

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
