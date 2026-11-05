# 計画書: I225 GitHub の鍵が画面に出る・漏れたときの手順と、テスト用のセッションの抜け道を塞ぐ

## 基本情報
- **計画書ID**: plan_I225
- **関連イシュー**: #415
- **Draft PR**: #416
- **作成根拠資料**: docs/issues/open/I225.md（I223 の retro からの起票。台帳 `docs/reviews/closed/I223_code_review_20261105_1440.md` の F7・F9・F13・F14・F15）
- **実装後評価**: docs/reviews/open/I225_review.md
- **作成日**: 2026-11-06

## 1. 背景/目的
I223 で Claude の GitHub の名義を GitHub App にし、テスト用のセッションには読み取りだけの鍵（`GH_APP_READONLY=1`）を渡すようにした。I223 の test-gate で、手順書どおり `--json` なしで `auth status` を流したら、書き込みのできる App の鍵の大部分が画面と会話の記録に出た（`gh` は鍵の最後の部分しか伏せない）。I223 では手順書の確かめ方だけを直し、次の残りを I225 に回した。

- **目的**: 鍵が画面に出る書き方を決定論で締め出す。鍵が出たときの手順を、漏れた鍵そのものを失効させる形に正す。テスト用のセッションが、MCP・`PATH` の違いで読み取りだけの鍵を迂回する抜け道を塞ぐ。

## 2. 受け入れ条件
イシュー `docs/issues/open/I225.md` の受け入れ条件と同じ（§9 の計画で絞った点を反映済み）。
1. `--json`・`-t`/`--show-token` なしの `gh auth status` を入口の `gh` で流すと、鍵の欄が出ず、名義・鍵の出どころ・状態だけが表示される（F15）
2. 手順書・スキル・エージェント・ハーネスのスクリプト・テンプレートに、`--json` なし（または `-t`/`--show-token` 付き）の `gh auth status` を書くと、静的な検査（CI）で落ちる（F15）
3. 手順書の失効の手順が、漏れた鍵そのものを失効させ、2 つの控え（`token`・`token-readonly`）を消す形になっている（F13）
4. 総点検の一覧の古い鍵の点検コマンドを、そのままコピーして流せる（F14）
5. テスト用のセッション（`scripts/claude/` の `claude -p`・`tui-capture.sh`）が、MCP・`PATH` の違いによって読み取りだけの鍵を迂回しない（F7・F9）
6. 既存のハーネステスト・CI がすべて pass する

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: `scripts/claude/gh-app/`（入口 `gh` の変更・失効のスクリプト `revoke.sh` の追加）・`scripts/claude/` の Claude の起動の行（`--strict-mcp-config`）・`scripts/claude/tui-capture.sh`・`scripts/claude/tests/`・`docs/runbooks/github-app-setup.md`・`docs/runbooks/harness-audit.md`
- 見張り `scripts/claude/hooks/pretooluse_guard.py`・`.claude/settings.json`・`.github/` は変えない（止めて聞く条件 2 の安全装置に当たらない）
- 端末の外の仕組み: 入口 `gh` はリポジトリの版を `install.sh` で `~/.local/bin/gh` に入れる。実装の後に `install.sh` を流し直して、この端末に入れる（M-01）

## 調査結果

### 原因の概要
`gh` の `auth status` は鍵の伏せ字が昔の短い鍵向けで、App の長い鍵では大部分を出す。今はそれを「手順書に書かない」という決まりだけで防いでいて、打ってしまえば出る。漏れたときの手順も、そのとき入口が渡す鍵を失効させるだけで、漏れた鍵と同じとは限らない。テスト用のセッションの守りは「`gh` の入口を通る」ことが前提で、入口を通らない経路（MCP・tmux サーバーの `PATH`）が残っている。

### 詳細（箇所）
- **F15**: `scripts/claude/gh-app/gh` は引数を見ずに本物の `gh` へ渡す（13 行目 `exec "$REAL_GH" "$@"`）。見張りが確認にするのは `auth token`・`--show-token`・`auth status -t` だけ（`pretooluse_guard.py:2259-2260`）。`--json` なしの `auth status` を止める決定論のチェックは無い
- **F13**: `docs/runbooks/github-app-setup.md:47` の失効の手順 `gh api -X DELETE installation/token` は入口を通るので、そのとき入口が渡す鍵（控え `token`、`GH_APP_READONLY=1` なら `token-readonly`、期限間際なら取り直した新しい鍵）を失効させる。消す控えも `token` だけ。控えの仕組みは `gh-app-token:13-19`（読み取りだけは `token-readonly`）・`:24`（残り 10 分を切ったら取り直す）
- **F14**: `docs/runbooks/harness-audit.md:29` は表の中に jq の式を書いていて、`|` を `\|` で逃がしているため、コピーすると jq の構文エラーになる。`GH_APP_DISABLE=1` は `GH_APP_READONLY` があると入口で無視される（`gh:6`）。`.tokenSource` が無く、環境変数の鍵と保存されたログインを区別できない
- **F7**: `--strict-mcp-config` があるのは `check-permission-prompt.sh:70`（bash の判定だけ）と `adversarial-review.sh:181`（実験役だけ）。`code-review.sh:154`・`review-process-lib.sh:29`（レビュー役・敵対的レビュー役）・`issue-review.sh:40`・`plan-issue-review.sh:131`・`fix-review-lib.sh:81`・`test-session.sh:7`・`tui-capture.sh:45` には無い。`check-permission-prompt.sh` の mcp の判定は `--mcp-config .mcp.json` だけで、ほかの MCP の設定も読む
- **F9**: `tui-capture.sh:45` は `tmux new-session` に `-e GH_APP_READONLY=1` だけを渡す。tmux サーバーが先に立っていると、中の `claude` の `PATH` はサーバーの環境になり、`~/.local/bin` が無ければ `gh` は本物の `/usr/bin/gh` になる（入口を通らない）

### 環境・前提の確認（2026-11-06）
- `gh` 2.88.1: `auth status` に `-a`・`-h`・`--json hosts`・`--jq`・`--template`・`-t` がある。`--json hosts` の各要素の欄は `active`・`gitProtocol`・`host`・`login`・`state`・`tokenSource`（失敗時は `error`）で、鍵の欄は `--show-token` を付けたときだけ入る
- スパイク（成立）: `gh auth status -a -h github.com --json hosts --jq '.hosts[][] | .host + " " + .login + " " + .tokenSource + " " + .state + (if .active then " (active)" else "" end)'` → `github.com osushi0404-claude[bot] GH_TOKEN success (active)`（鍵は出ない。`-a`・`-h` は `--json` と併用できる）
- `--json` を付けると、`auth status` は認証の問題があっても終了コード 0（`gh auth status --help`）。置き換えでは終了コードを自分で決める（4-1）
- 元のリポジトリの `.mcp.json` に `github` は無い（`grep -c github` が 0）。F7 の今の実害は小さいが、手元の設定に GitHub の MCP が戻ったときの抜け道として塞ぐ
- tmux 3.4（`-e` は 3.2 以上）・`python3`・`/usr/bin/gh` あり
- 既存テストのベースライン（実装前・develop の 2026-11-06 時点）: `test_i223_gh_app.sh` 18/18・`test_tui_capture.sh` 37/37・`test_check_permission_prompt.sh` 26/26・`test_i197_adversarial_process.sh` 113/113・`test_fix_review.sh` 66/66・`test_i193_official_flow.sh` 174/174。CI は `scripts/claude/tests/run-all.sh`（`.github/workflows/ci.yml:169`）

## 修正アプローチ
鍵を出す書き方は、打った時点（入口）と書いた時点（CI の静的な検査）の 2 か所で決定論に止める。入口では「断る」のではなく「鍵を出さない表示に置き換える」ので、打った人も Claude も打ち直しの往復なしに必要な情報を得られる。漏れたときの手順は、控えにある 2 つの鍵を直接失効させ、失効を確かめてから控えを消すスクリプトにする（手順書の散文で手を動かすと取り違えるので、1 コマンドにしてテストで守る）。テスト用のセッションは、Claude を起こす行すべてに `--strict-mcp-config` を付け、tmux の中の `claude` には入口のある `PATH` を渡す。

## 4-5. 変更点一覧と実装手順

### 4-1. 入口 `gh` で `auth status` を置き換える（F15・受け入れ条件 1）
**修正方針**: 引数が `auth status` で、`--json`・`--jq`・`--template`・`-t`・`--show-token`（`-at` のように短いオプションをまとめた中の `t` を含む）のどれも無いときだけ、本物の `gh` を `auth status <元の引数> --json hosts` で呼び、名義の行だけを出す。`-t`/`--show-token` はわざと鍵を見る操作なので置き換えない（Claude からは見張りの S23・S35 が確認にする）。

- 対象: `scripts/claude/gh-app/gh`（鍵を受け取った後、`exec` の前に足す）
- 表示: 1 アカウント 1 行 `<host> <login> <tokenSource> <state>`、使用中のものには ` (active)`。`error` の欄は出さない（文言に鍵の一部が入りうるため）
- 標準エラーに 1 行: `gh: 鍵を画面に出さないよう、auth status を --json の形で表示しました（I225）`
- 終了コード: `state` がすべて `success` なら 0、1 つでも違えば 1（`--json` なしの元の動きに合わせる。`gh auth status` の終了コードで認証を確かめる書き方を壊さない）。本物の `gh` が失敗したらその終了コード
- JSON の整形は `python3 -I`（`gh-app-token` と同じ。jq に頼らない）
- コード例:
  ```bash
  if [ "${1:-}" = auth ] && [ "${2:-}" = status ]; then
    plain=1
    for a in "${@:3}"; do
      case "$a" in --json*|--jq*|--template*|--show-token|-t|-[!-]*t*) plain=0 ;; esac
    done
    if [ "$plain" = 1 ]; then
      echo "gh: 鍵を画面に出さないよう、auth status を --json の形で表示しました（I225）" >&2
      json="$("$REAL_GH" auth status "${@:3}" --json hosts)" || exit $?
      printf '%s' "$json" | python3 -I -c '<hosts を 1 行ずつ出し、state が success でないものがあれば 1>'
      exit $?
    fi
  fi
  ```
- この端末への反映: `bash scripts/claude/gh-app/install.sh`（M-01）
- → TC-02 の G8 参照

### 4-2. 失効のスクリプトを足し、手順書を直す（F13・受け入れ条件 3）
**修正方針**: `scripts/claude/gh-app/revoke.sh` を新しく作る。控えのフォルダ（`GH_APP_CACHE_DIR`、既定 `~/.cache/github-app`）の `token`・`token-readonly` の 2 つについて、控えの鍵を `GH_TOKEN` にして本物の `gh`（`GH_APP_REAL_GH`、既定 `/usr/bin/gh`。入口を通さない＝入口が別の鍵に差し替えない）で `api -X DELETE installation/token` を呼ぶ。続けて同じ鍵で `api installation/repositories` を呼び、失敗する（＝鍵が無効）ことを確かめてから控えを消す。

- 鍵の値は引数・画面に出さない（`GH_TOKEN` の環境変数で渡す・出力は控えの名前と結果だけ）
- 結果: 各控えについて `token: 失効を確認して控えを消しました`／`控えがありません`。DELETE の後も読めた（無効にならなかった）控えがあれば、控えは消さずに exit 1 で「App の設定画面で確かめる」よう案内する（`github-app-setup.md`「8.」）
- 終了コード: 0=すべて無効を確認（控えが無いものを含む）・1=無効にならなかった鍵がある・2=使い方の誤り（引数を取らない）
- 手順書 `docs/runbooks/github-app-setup.md`「5.」: 鍵が画面・記録に出たら `bash scripts/claude/gh-app/revoke.sh` を流すことにする。控えが取り直された後に気づいたときの古い鍵は、取り直しの決まり（残り 10 分で取り直す）から残り 10 分未満で切れることを書く。秘密の鍵ファイル（`app.pem`）が漏れたときは「8.」の作り直し
- 入口と同じく `install.sh` では入れない（リポジトリから流す。鍵が出たときだけ使うため）
- → TC-02 の G9 参照

### 4-3. 鍵を出す書き方の静的な検査（F15・受け入れ条件 2）
**修正方針**: `scripts/claude/tests/test_i223_gh_app.sh` に G10 を足す。対象は `CLAUDE.md`・`docs/runbooks/`・`.claude/skills/`・`.claude/agents/`・`scripts/claude/` の下（`scripts/claude/tests/` を除く）・`docs/*/templates/`。各ファイルで `gh auth status` が出るたびに、そのあとから行末か次のバッククォートまでの語を見て、`--json` で始まる語が無い、または `--show-token`・`-t`（短いオプションをまとめた中の `t` を含む）がある書き方を不合格にする。

- 個々のイシューの記録（`docs/issues/`・`docs/plans/`・`docs/tests/open|closed/`・`docs/reviews/`）は対象外（§9）
- 今の手順書の散文 `github-app-setup.md:47`（`--json` を付けない `gh auth status` は使わない）は検査に当たるので、4-2 で書き直す（`auth status` は `--json` を付けて使う、の形）
- → TC-02 の G10 参照

### 4-4. 総点検の点検コマンド（F14・受け入れ条件 4）
**修正方針**: `docs/runbooks/harness-audit.md` の表の「手元に残る古い鍵」の行は「下のコードブロック」を指すだけにし、表の後にコードブロックで次を置く。
```bash
grep -c -E '^[[:space:]]*export[[:space:]]+(GITHUB_PERSONAL_ACCESS_TOKEN|GH_TOKEN|GITHUB_TOKEN)=' ~/.bashrc ~/.profile
GH_APP_READONLY= GH_APP_DISABLE=1 gh auth status --json hosts --jq '.hosts["github.com"][] | .login + " " + .tokenSource + " " + .state'
```
- 1 行目は値を出さずに数える（今の行の「`grep -c` で数える」を具体化）。`~/.profile` が無いときのエラーは数の判断に影響しない
- 2 行目は `GH_APP_READONLY` を空にして（入口は空を「指定なし」と読む・`gh:6` の `-n`）`GH_APP_DISABLE` を効かせ、入口から鍵を渡さずに本物の `gh` の保存されたログイン・環境変数の鍵を、出どころ（`.tokenSource`）つきで見る。`env -u GH_APP_READONLY …` の形は、ワークツリーのセッションの見張りが「`env` が何を動かすか読めない」として止める（2026-11-06 の計画の段階で発生）ので使わない
- 計画の段階で 2 行とも流して確かめた（2026-11-06）: 1 行目は `.profile:0`・`.bashrc:1`、2 行目は `osushi0404-bot /home/tacic/.config/gh/hosts.yml error`（exit 0・jq のエラーなし・鍵の値は出ない）
- → TC-03 参照（コピーして流せることを実行で確かめる）

### 4-5. テスト用のセッションの MCP の抜け道（F7・受け入れ条件 5）
**修正方針**: `scripts/claude/` の Claude を起こす行すべてに `--strict-mcp-config` を書く（MCP は `--mcp-config` で渡したものだけになる）。
- `code-review.sh:154`・`review-process-lib.sh:29`（`run_claude_logged`。敵対的レビュー・コードレビューの検証役が通る）・`issue-review.sh:40`・`plan-issue-review.sh:131`・`fix-review-lib.sh:81`・`test-session.sh:7`・`tui-capture.sh:45`（`claude --permission-mode manual --strict-mcp-config`）
- `check-permission-prompt.sh`: 起動の行に `--strict-mcp-config` を直接書き、`MCP_ARGS` は mcp の判定のときの `--mcp-config .mcp.json` だけにする（mcp の判定もワークツリーの `.mcp.json` だけを読む）
- `adversarial-review.sh:181` の実験役の `--strict-mcp-config` は、`run_claude_logged` が付けるので消す（同じオプションを 2 回渡さない）
- `test-session.sh` の呼び出し元が `--mcp-config` を渡せば、その MCP だけは使える
- → TC-02 の G7 参照

### 4-6. tmux の中の `claude` に入口のある `PATH` を渡す（F9・受け入れ条件 5）
**修正方針**: `tui-capture.sh:45` の `tmux new-session` に `-e "PATH=$HOME/.local/bin:$PATH"` を足す（`-e GH_APP_READONLY=1` と同じく、tmux サーバーの環境に関係なく新しいセッションに入る）。入口は `install.sh` が `~/.local/bin/gh` に入れる。
- 起動するコマンドは固定のまま（T8）
- → TC-01（`test_tui_capture.sh` の T1・FG-T1b）参照

### 4-7. 台帳の残りの同梱（§9）と手順書の文言
- `docs/runbooks/github-app-setup.md`「1.」: 「Claude を起こす行はすべて G6 が止める」を、G6・G7 が見る範囲（`scripts/claude/` 直下の `.sh` の `claude -p` と、tmux で `claude` を起こす行）に合わせる（一覧 I223 F12）。`--strict-mcp-config` と `PATH` の決まりを 1 文足す
- `test_i223_gh_app.sh` 冒頭のコメントを G1〜G10 にする（一覧 I223 F11）
- `docs/reviews/backlog/I223.md` の F11・F12、`docs/reviews/backlog/I195.md` の F5 を消す

### 依存関係
- 4-1 → 4-3（入口の変更と同じテストファイル）。4-2 の手順書の書き直しは 4-3 の検査の前提
- 4-5・4-6 は 4-1〜4-3 と独立（並行可）。4-5 の G7 と 4-6 の T1 は同じ `tui-capture.sh:45` を触るので 1 回の編集にまとめる
- 実装の最後に `install.sh` を流し直す（M-01 の前提）

## 6. テスト計画
- 自動（決定論）: `docs/tests/open/I225_auto_test.md`
  - TC-01: 起動の行を触るファイルを見ている既存のテスト（`test_tui_capture.sh`・`test_check_permission_prompt.sh`・`test_i197_adversarial_process.sh`・`test_fix_review.sh`・`test_i193_official_flow.sh`）が合格する
  - TC-02: `test_i223_gh_app.sh` の G1〜G10（新しく G7〜G10）。各 G に FG
  - TC-03: 4-4 の点検コマンドをそのまま流して exit 0・jq の構文エラーが無い
- 手動: `docs/tests/open/I225_manual_test.md`（すべて Claude。入れ直した入口での `auth status`・失効のスクリプトの本物の GitHub での確かめ・tmux の中の `claude` の MCP と `gh`）
- テストのレベル: 入口・失効・検査は偽物の `gh` を使うユニット相当（決定論）。本物の GitHub・tmux・claude での確かめは手動テスト（Claude）
- 再発防止: G8（打っても出ない）・G10（書いても CI で落ちる）・G9（失効の取り違え）・G7（MCP の付け忘れ）

## 7. ロールバック
- PR を revert する。端末の入口は `install.sh` が `~/.cache/github-app/backup/` に前の版を写すので、revert 後に `install.sh` を流し直せば戻る
- データ・GitHub の設定は変えない

## 8. Risk & 回避策
| リスク | 回避策 |
|---|---|
| 入口の置き換えが、`auth status` の終了コードで認証を確かめる書き方を壊す | `state` がすべて `success` のときだけ 0 にする（G8 で 0 と 1 の両方を確かめる） |
| `-t` の判定が `-h` の値（ホスト名）に当たる | `-` で始まる語だけを見る。ホスト名は `-` で始まらない |
| 失効のスクリプトが、まだ使っている書き込みの鍵を失効させる | 失効の後は控えを消すので、次の `gh` で取り直す（作業は止まらない）。鍵が出たときだけ流す |
| `--strict-mcp-config` で、MCP が要る判定（Playwright など）が動かなくなる | MCP が要る判定は `check-permission-prompt.sh mcp` で `--mcp-config .mcp.json` を渡す（今どおり）。レビュー役は MCP を使わない（`--tools "Read,Grep,Glob"`）。M-03 で確かめる |
| 静的な検査が散文の言及にも当たり、手順書が書きにくくなる | 対象を決まりの置き場（手順書・スキル・エージェント・スクリプト・テンプレート）に絞る。散文は「`auth status` は `--json` を付けて使う」の形で書ける |

## 9. 確定事項と自律判断
### イシューに明記されていること（grill-me で確定・2026-11-06）
- F15 は入口で置き換える（断らない）＋静的な検査。見張りは変えない。`-t`/`--show-token` の明示は置き換えない。予防策は新しい決まりを足さず決定論のチェックで代える
- F13 は漏れた鍵そのものを失効させ、`token`・`token-readonly` の両方を消す。F14 はコードブロックに出し `GH_APP_READONLY` を外し `.tokenSource` を足す。F7 は `--strict-mcp-config`。F9 は `-e PATH=…`

### Claude が技術的に決めたこと（理由）
- 失効を手順書の散文ではなくスクリプト `revoke.sh` にする — 取り違え（F13）は手で手順を追うと起きる。1 コマンドなら Claude も人も同じ手順になり、偽物の `gh` でテスト（G9）できる。新しいファイルはイシューの実装対象に無いが、F13 の直し方の具体化で範囲は変えない
- `revoke.sh` は控えの鍵だけを失効させ、画面に出た鍵の値を受け取らない — 鍵の値をコマンドの引数・入力に渡すと、もう一度記録に出る。出た鍵はほぼ控えの鍵（控えは 1 時間・残り 10 分で取り直す）で、取り直された後の古い鍵は 10 分未満で切れる
- 失効の確かめに `api installation/repositories` を使う — App の鍵で読める最小の API。無効なら 401 で失敗する
- 入口の置き換えで `error` の欄を出さない — 文言に鍵の一部が入りうる（`state` で失敗は分かる）
- 静的な検査の対象から個々のイシューの記録（`docs/tests/open/` など）を外す — この計画書・テスト文書自体が「`--json` なしの書き方」を名指しする必要がある（M-01 は置き換えを確かめるために `--json` なしで流す）。打ったときは入口が置き換えるので、記録に書かれても鍵は出ない。I223 の事故の元は手順書の確かめ方で、手順書は対象に入る。grill-me のメモ（open のテスト文書を含む）からの絞り込みなので、イシューの受け入れ条件 2 も同じ範囲に直す（技術的な範囲の具体化で、価値判断は変わらない）
- 静的な検査は `-t`/`--show-token` 付きも不合格にする — 手順書が鍵を出す書き方を指示するのは、`--json` なしと同じ事故になる
- `--strict-mcp-config` の付け忘れを G7 で止める — 起動の所が増えたときに気づきにくく、MCP 経由で読み取りだけの鍵を迂回しうる（壊れても気づきにくく被害が大きい）。G6 と同じ論理行の読み方を使う
- `PATH` は `$HOME/.local/bin` を先頭に足す — 入口は `install.sh` がそこに入れる。呼び出し元の `PATH` に無くても入口を通る
- `adversarial-review.sh` の実験役の `--strict-mcp-config` を消す — `run_claude_logged` が付けるので 2 回渡さない
- 見張り（`pretooluse_guard.py`）・`.claude/settings.json`・`.github/` を触らない — 止めて聞く条件 2 に当たらない形で直せる

### 台帳の残りの一覧
- 一覧 I223 F11: 同梱 — `test_i223_gh_app.sh` の冒頭のコメントを直す（同じファイルを触る）
- 一覧 I223 F12: 同梱 — `github-app-setup.md`「1.」の G6 の保証の書き方を、G6・G7 の実際の範囲に合わせる（同じ節に F7 の決まりを足す）
- 一覧 I195 F5: 同梱 — tmux サーバーの環境で起動する件。鍵に関わる `PATH` を `-e` で渡す（F9 と同じ直し）。ほかの環境の差は鍵に関わらない
- 一覧 I223 F6: 残す — G6 の検出の形の狭さ。G7 も同じ読み方で、広げるのは別の作業（Low・再現なし）
- 一覧 I223 F10: 残す — tmux 3.2 未満。この端末は 3.4（Low・再現なし）
- 一覧 I195 F1・F2・F4: 残す — `tui-capture.sh` の入力・起動の待ちの件で、鍵の抜け道ではない（再現なし）
- 一覧 I200 F7（`check-permission-prompt.sh`）: 残す — write の上書き防止の件で、このイシューと関係しない
- 一覧 I208 F1〜F3・F5・I206 F4・I207 F6・F7（`code-review.sh`）: 残す — 台帳の読み方の件で、起動の行と関係しない
- 一覧 I209 F6（`fix-review-lib.sh`）: 残す — 診断レビューの SKIP の扱いで、起動の行と関係しない
- 一覧 I223 B1〜B4（`FILE=-`）: 残す — bot の停止が解けるまでできない

### チェック
- 要件適合性: 受け入れ条件の範囲を超える仕様追加なし（`revoke.sh` は F13 の直し方の具体化）。マルチテナント・ステータス遷移: 該当なし
- セキュリティ: 機密データ（App の鍵）の扱いを強める変更。鍵の値は引数・画面・記録に出さない（入口は `--json` で鍵の欄を取らない・`revoke.sh` は環境変数で渡し出力しない）。最小権限: テスト用のセッションの MCP を `--mcp-config` で渡したものだけにする。入力: 入口の判定は引数の配列で行い、シェルの文字列を読まない。OWASP: A02（秘密の露出）への対策。依存ライブラリの追加なし。bandit・npm audit の対象のコード変更なし
- テスト計画: 再発防止テスト（G8〜G10・G7・T1）あり。各 FG あり。認可・テナント境界: 該当なし
- P3/P5/P8 影響なし（DB・外部 API の新規・依存ファイルの変更なし）
- P6 影響なし（画面なし）
- P9 影響なし（個人情報・テナントデータを扱わない）
- 設計品質: 設定値は環境変数で上書きできる既定値（`GH_APP_REAL_GH`・`GH_APP_CACHE_DIR`）を使い、新しい定数を増やさない。エラー時は鍵を出さない側に倒す（入口: 本物の `gh` の失敗はその終了コードで返す・失効: 無効を確かめられなければ控えを消さず exit 1）

## 計画変更記録
（なし）
