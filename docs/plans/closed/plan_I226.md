# I226 計画書: I225 のレビューの残り: 失効の確かめの取り違え・鍵を出す書き方の検査の狭さ

## 基本情報
- **計画書ID**: plan_I226
- **関連イシュー**: #417
- **Draft PR**: #418
- **作成根拠資料**: docs/issues/open/I226.md（起点イシュー・設計確認メモあり）
- **実装後評価**: docs/reviews/open/I226_review.md
- **作成日**: 2026-11-06

## 1. 背景/目的
- I225 で作った失効のスクリプト `scripts/claude/gh-app/revoke.sh` は、もともと無効な鍵（末尾の欠け・打ち間違い・失効済み）でも「失効を確認しました」と出して exit 0 になる（F1）。本物の鍵が有効なまま残っても、利用者は「失効できた」と取り違える
- 鍵を出す書き方の静的な検査（`scripts/claude/tests/test_i223_gh_app.sh` の G10）は `gh auth status` だけを見ていて、鍵を丸ごと出す `gh auth token` を通す。行末の `\` で分けた `--json` 付きの書き方は誤って落とす（F6）
- 同梱（grill-me で確定）: I225 の軽い指摘の F2（ログインなしの `auth status` の置き換えが exit 0）・F4（`plan-writing-rules.md` の記述漏れ）、自動テスト文書の見出しの検査（omission-lint）を早い時点で流す
- F5（控えを消すときの競合）は grill-me で見送り（実害がほぼなく、「ふつうの書き方の事故」の範囲外）

### 調査結果
- **原因の概要（F1）**: 「鍵が無効になった」ことだけを確かめていて、「その鍵はもともと有効だった」ことを確かめていない。だから最初から無効な鍵でも「失効できた」に見える
- **詳細（F1）**: `revoke_one`（`revoke.sh:19-24`）は DELETE の結果を捨て（`> /dev/null 2>&1`）、続く `installation/repositories` の読みが `HTTP 401` なら 0 を返す。最初から無効な鍵は DELETE も読みも 401 になるので、0（成功）になる
- **原因の概要（F6）**: 検査の対象を「`auth status` の書き方」に限っていて、鍵の値を出す別のコマンド（`gh auth token`）を数えていない。行の区切りを物理行で取っているので、`\` で続けた次の行の `--json` を見ない
- **詳細（F6）**: `g10()`（`test_i223_gh_app.sh:112-149`）は `re.finditer(r"gh auth status", text)` の後ろを、次の改行かバッククォートまでで切る
- **F2 の前提のスパイク（2026-11-06・成立）**: 空の `GH_CONFIG_DIR` で `/usr/bin/gh auth status --json hosts` を流すと、標準エラーに `You are not logged into any GitHub hosts. To log in, run: gh auth login`、標準出力に `{"hosts":{}}`、exit 0。置き換え（`scripts/claude/gh-app/gh:23`）は標準出力だけを取るので、案内の文はすでに画面に出る。足りないのは終了コード（1 にする）だけ
- **omission-lint の現状（実走・2026-11-06）**: `scripts/claude/code-review.sh` の `omission_lint` を `docs/tests/{open,closed}/*_auto_test.md` の全 136 件に流すと、HIGH は 15 件（open の `I034_auto_test.md` と closed の 14 件。どれも I084 より前の古い文書）。CI の `pre-commit/action` は `--all-files` で流すので、pre-commit に載せると古い open の I034 で CI が落ちる。また `.pre-commit-config.yaml`・`.github/` は高リスク判定のパス（`path_risk_trigger()`）に当たり、敵対的レビューと設計のセキュリティレビューが要る。→ 流す場所は PostToolUse のフック（`scripts/claude/hooks/posttooluse_check.py`・Edit/Write の直後に動く・高リスクのパスでない）にする（§9）
- **環境前提**: `bash`・`python3`・`/usr/bin/gh`・`pre-commit 4.5.1` があることを確かめた（ツールの追加なし）
- **既存テスト**: `test_i223_gh_app.sh`・`test_posttooluse_check.sh`・`test_review_gates.sh` は develop の CI（Harness Tests）で全緑（PR #416 マージ時）。手元での全体の流し直しはしない（CI が正）
- **G10 の対象範囲の grep（2026-11-06）**: `CLAUDE.md`・`docs/runbooks`・`.claude/skills`・`.claude/agents`・`scripts/claude`（tests を除く）・`docs/*/templates` に `gh auth token` の書き方は無い（`pretooluse_guard.py:2259` は `["auth", "token"]` の配列で、文字列 `gh auth token` を含まない）。直してすぐ G10 が落ちることはない

## 2. 受け入れ条件
- [ ] `revoke.sh`（控え・`--stdin` とも）が、もともと無効な鍵を「失効を確認」と表示しない。`--stdin` は「最初から無効」と出して exit 1、控えは「もともと無効」と出して控えを消し成功扱い（F1）→ TC-02（G9 g・h）・M-01
- [ ] 手順書などに `gh auth token` を書くと G10 で落ちる。行末の `\` で分けた `--json` 付きの書き方は落ちない（F6）→ TC-02（G10 の FG）
- [ ] ログインなしのとき、置き換えた `gh auth status` が exit 1 になる（本物の `gh` の「ログインしていない」の案内はそのまま出る）（F2）→ TC-02（G8）・M-03
- [ ] `plan-writing-rules.md` に `--strict-mcp-config`・tmux の `PATH`・G7 の記述がある（F4）→ TC-04
- [ ] 自動テスト文書の見出しの検査（omission-lint）が push の前にも流れる（自動テスト文書を Edit/Write した直後に PostToolUse のフックが流し、宣言漏れなら Claude に知らせる）→ TC-03・M-02
- [ ] 既存のハーネステスト・CI がすべて pass する → TC-01・CI

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: `scripts/claude/gh-app/revoke.sh`・`scripts/claude/gh-app/gh`・`scripts/claude/code-review.sh`・`scripts/claude/hooks/posttooluse_check.py`・`scripts/claude/tests/test_i223_gh_app.sh`・`scripts/claude/tests/test_posttooluse_check.sh`・`docs/runbooks/github-app-setup.md`・`docs/runbooks/plan-writing-rules.md`・`docs/reviews/backlog/I225.md`・`CLAUDE.md`（PostToolUse の説明の 1 文）
- 入れ直し: `~/.local/bin/gh` は `install.sh` が置く写し。マージの後に入れ直す（§8）

## 4. 変更点一覧（具体）

### 修正アプローチ
- F1: 失効させる前に同じ鍵で 1 回読み、「有効」を確かめてから DELETE する。前もって 401 なら「もともと無効」として分けて扱う
- F6: G10 を「論理行（行末の `\` でつないだ行）」で見るようにし、対象のコマンドに `gh auth token` を足す
- F2: 置き換えの Python で、アカウントが 1 つも無いときは exit 1 にする
- F4: `plan-writing-rules.md` の該当の 1 文に、I225 で足した決まり（`--strict-mcp-config`・tmux の `PATH`・G7）を書き足す
- omission-lint: 判定の本体（`code-review.sh` の `omission_lint`）は 1 か所のまま、`code-review.sh --lint-auto-test <ファイル>…` の入口を足し、PostToolUse のフックが自動テスト文書のときだけ呼ぶ

### 4-1. `scripts/claude/gh-app/revoke.sh`（F1）
修正方針: 読みの判定を関数 `token_state` にまとめ、失効の前と後で同じ判定を使う。返す値で「失効させて確かめた／もともと無効／確かめられない」を分ける。

```bash
# token_state <鍵>: その鍵で読みに行く。0=有効（読めた）・1=無効（HTTP 401）・2=確かめられない（通信の失敗など）
token_state() {
  local out
  out="$(GH_TOKEN="$1" "$REAL_GH" api installation/repositories --silent 2>&1 > /dev/null)" && return 0
  [[ "$out" == *"HTTP 401"* ]] && return 1
  return 2
}

# revoke_one <鍵>: 0=失効させ、無効（401）を確かめた・3=失効の前から無効（期限切れ・失効済み・貼り間違い。DELETE はしない）・
# 1=確かめられない（失効できていないのに「無効」と取り違えない）
revoke_one() {
  local before=0 after=0
  token_state "$1" || before=$?
  case "$before" in 1) return 3 ;; 2) return 1 ;; esac
  GH_TOKEN="$1" "$REAL_GH" api -X DELETE installation/token --silent > /dev/null 2>&1
  token_state "$1" || after=$?
  [ "$after" = 1 ]
}
```

呼び出し側:
- `--stdin`:
  - 0 → `渡された鍵: 失効を確認しました`・exit 0
  - 3 → 標準エラーに `渡された鍵: この鍵は最初から無効でした。貼り間違い（末尾の欠け）がないか確かめてください。すでに失効済みなら対応は不要です`・exit 1
  - それ以外 → 従来の `渡された鍵: $FAILED`・exit 1
- 控え（引数なし）:
  - 0 → 従来の `<name>: 失効を確認して控えを消しました`
  - 3 → 控えを消して `<name>: もともと無効でした（期限切れ・失効済み）。控えを消しました`（rc に影響しない）
  - それ以外 → 従来の `<name>: $FAILED（控えは残しました）`・rc=1
- 冒頭の説明（4〜8 行目）と終了コードの説明を合わせて直す（0=すべて無効を確認〔もともと無効を含む〕・1=無効を確かめられない鍵がある、または `--stdin` の鍵が最初から無効）

### 4-2. `scripts/claude/gh-app/gh`（F2）
修正方針: アカウントが 1 つも無いとき exit 1 にする。案内の文は本物の `gh` が標準エラーに出すので足さない。
```python
ok = True
n = 0
for accounts in json.load(sys.stdin).get("hosts", {}).values():
    for a in accounts:
        n += 1
        ...
sys.exit(0 if ok and n else 1)
```
- 24 行目のコメントに「アカウントが無い（ログインなし）ときも 1」を足す

### 4-3. `scripts/claude/tests/test_i223_gh_app.sh`
- G8: `{"hosts":{}}` のケースを足す（exit 1・標準出力は空）。FG: `s/sys.exit(0 if ok and n else 1)/sys.exit(0 if ok else 1)/`（アカウントの数の確かめを消す）で G8 が NG
  - 既存の FG `s/sys.exit(0 if ok else 1)/sys.exit(0)/` は式を `s/sys.exit(0 if ok and n else 1)/sys.exit(0)/` に合わせる
- G9: 偽の本物の gh（`real-gh-revoke`）は今のまま使う（`$FAKE_REVOKED` に先に入れた鍵は、最初の読みから 401 になる）
  - g) `--stdin` に最初から無効な鍵（`$FAKE_REVOKED` に先に入れる）→ exit 1・出力に `最初から無効` があり `失効を確認` が無い・その鍵に DELETE を送っていない（`$FAKE_GH_ARGS` に `<鍵> api -X DELETE` の行が無い）・鍵の値を出さない
  - h) 控えの `token` だけ最初から無効（期限切れ）・`token-readonly` は有効 → exit 0・両方の控えが消える・`token` の行に `もともと無効` がある
  - i) 失効の前の読みは成功し、DELETE の後の読みだけが通信の失敗 → exit 1・控えは残す（偽物に `$FAKE_NET_AFTER_DELETE` を足す: DELETE を受けた鍵を `$FAKE_REVOKED.del` に書き、その鍵の読みを通信の失敗にする。`FAKE_NO_REVOKE=1` と一緒に使う）。直した後の既存の d) は失効の前の読みで終わるので、DELETE の後の分岐は i) で守る（計画レビューの Warning 2）
  - 既存の a)〜f) は変えない（a は有効な鍵なので、最初の読み → DELETE → 401 の流れで今までどおり合格する。d は失効の前の読みが通信の失敗 → DELETE を送らず exit 1 になり、V2 を守る）
  - FG: `s/case "\$before" in 1) return 3 ;; 2) return 1 ;; esac/:/`（失効の前の確かめを消す）で G9 が NG
- G10:
  - 本文を論理行に分ける（行末の `\` で次の行とつなぐ・行番号は論理行の始まりの物理行）
  - `gh auth token` を見つけたら、そのまま不合格の行にする（`--json` の有無を問わない）
  - 冒頭のコメント（109〜111 行目）を合わせて直す
  - FG（`g10_fg`）を 2 つ足す: 「`gh auth token` は不合格」（期待 1）・「行末の `\` で分けた `--json` は合格」（期待 0。`printf` で 2 行の手順書を作る）

### 4-4. `scripts/claude/code-review.sh`（omission-lint の入口）
修正方針: レビューを動かさずに omission-lint だけを流す入口を、`--route` と同じ場所（関数だけを読み込むガードの直後）に足す。判定の本体は既存の `omission_lint` のまま（写しを作らない）。
```bash
# I226: 自動テスト文書の見出しの検査だけを流す（PostToolUse のフックが使う）: --lint-auto-test <ファイル>…。レビューは動かさない。
# 決定論ゲートの見出しの外の bash ブロックにゲートのコマンドがあれば（見出しの書き違い・宣言漏れ）標準エラーに出して 1
if [ "${1:-}" = "--lint-auto-test" ]; then
  [ $# -ge 2 ] || { echo "Usage: $0 --lint-auto-test <auto_test.md>…" >&2; exit 2; }
  rc=0
  for f in "${@:2}"; do
    [ "$(omission_lint "$f")" = OK ] && continue
    echo "$f: 「## 決定論ゲート（自動実走）」の節の外の bash ブロックにゲートのコマンドがあります（見出しの書き違いか宣言漏れ）。ひな形 docs/tests/templates/auto_test_template.md の見出しに合わせてください。直さないと review-gate が HIGH にします" >&2
    rc=1
  done
  exit "$rc"
fi
```

### 4-5. `scripts/claude/hooks/posttooluse_check.py`（omission-lint を書いた直後に流す）
修正方針: 書いたファイルが `docs/tests/open/I<数字>_auto_test.md` のときだけ、上の入口を呼ぶ。不合格なら標準エラーに出して exit 2（PostToolUse で Claude に届くのは exit 2 だけ・既存のコメントどおり）。それ以外のファイルの扱いは変えない。
```python
AUTO_TEST_RE = re.compile(r"(^|/)docs/tests/open/I\d+_auto_test\.md$")
CODE_REVIEW = Path(__file__).resolve().parent.parent / "code-review.sh"

def _check_auto_test(path: str) -> str | None:
    # 判定の本体は code-review.sh の omission_lint（写しを作らない・I226）
    try:
        r = subprocess.run(["bash", str(CODE_REVIEW), "--lint-auto-test", path],
                           capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None   # 流せないときは黙って通す（review-gate がもう一度見る）
    return r.stderr.strip() or None if r.returncode == 1 else None
```
- `main()` の分岐に `elif AUTO_TEST_RE.search(path): error = _check_auto_test(path)` を足す
- 出す文は `[posttooluse] auto_test の宣言漏れ in <path>:\n<error>`（構文エラーの文と分ける）
- 先頭の docstring を「.py / .json / .yaml の構文と、自動テスト文書の決定論ゲートの宣言漏れ」に直す
- `CLAUDE.md`「3. 権限と二重ガード」の PostToolUse の説明（`.py/.json/.yaml 構文を検証する`）に「自動テスト文書の決定論ゲートの宣言漏れ」を足す

### 4-6. `scripts/claude/tests/test_posttooluse_check.sh`
- TC-10g: 見出しを 1 語違えて、ゲートのコマンドが節の外の bash ブロックにある `docs/tests/open/I999_auto_test.md`（一時フォルダの下）→ exit 2・標準エラーに `宣言漏れ`
- TC-10h: ひな形どおりの見出しの下にゲートのコマンドがある同じ名前のファイル → exit 0
- TC-10i: 同じ中身の悪い文書でも、名前が `I999_manual_test.md`（対象外）なら exit 0
- FG: 冒頭の `HOOK` の差し替えで develop の版（自動テスト文書を見ない）に当てると TC-10g が不合格になることを確かめる（TC-03 の記録に残す）

### 4-7. `docs/runbooks/github-app-setup.md`（F1 の表示の説明）
- 「5.」の 1.: 「失効を確認して控えを消しました」「控えがありません」に「もともと無効でした（期限切れ・失効済み）。控えを消しました」を足す（どれでも exit 0 で終わり）
- 「5.」の 2.: 「この鍵は最初から無効でした…」（exit 1）のときは、貼った鍵の末尾が欠けていないか確かめて貼り直す。すでに失効させた鍵なら対応は不要、を足す

### 4-8. `docs/runbooks/plan-writing-rules.md`（F4）
- 90 行目の「付け忘れは `test_i223_gh_app.sh` の G6 が止める」の後ろに、「同じ行には `--strict-mcp-config` も付け（MCP は `--mcp-config` で渡したものだけ。手元の設定の MCP が読み取りだけの鍵を迂回しないように）、tmux の中の `claude` には入口のある `PATH`（`~/.local/bin` が先頭）も渡す（I225）。付け忘れは `test_i223_gh_app.sh` の G6・G7 が止める」を足す（TC-04 は追記する文の固有の語 `G6・G7` で検査する。計画レビューの Warning 3）

### 4-9. `docs/reviews/backlog/I225.md`
- 直した F2・F4 の行を消す（F3 の行は残す）

## 5. 実装手順（ステップ）
1. F1（未知リスクが最も大きい・鍵の扱い）: 4-1 の `revoke.sh` と 4-3 の G9 のケース・FG → TC-02 参照
2. F2: 4-2 の `gh` と 4-3 の G8 のケース・FG → TC-02 参照（ステップ 1 と並行可）
3. F6: 4-3 の G10 → TC-02 参照（並行可）
4. omission-lint: 4-4 の `code-review.sh` → 4-5 のフック → 4-6 のテスト（4-5 は 4-4 が前提）→ TC-01・TC-03 参照
   - フックを直した直後に、このセッションのフックがワークツリーの版を動かすかを M-02 の手順で確かめて記録する（計画レビューの Warning 1。Bash ツールの環境には `CLAUDE_PROJECT_DIR` が無く、事前に読めなかった）。元のリポジトリの版が動くときは、M-02 を `scripts/claude/test-session.sh` で起こした新しいセッション（作業フォルダ＝このワークツリー）で行う
5. 文書: 4-5 の `CLAUDE.md` の 1 文・4-7・4-8・4-9 → TC-04 参照（ステップ 1・2 の後）
- サービスの再起動は要らない（フックは次の Edit/Write から新しい版が動く）

## 6. テスト計画
### 自動
- テストレベル: シェルの単体（偽の `gh`・一時フォルダ）。本物の GitHub と秘密の鍵ファイルは使わない
- 再発防止テスト: F1（G9 g・h）・F2（G8）・F6（G10 の FG）・omission-lint のフック（TC-10g〜i）。どれも失敗の注入（FG）で不合格になることを確かめる
- 認可・テナント境界: 該当なし（アプリのコードを変えない）
- 詳細は `docs/tests/open/I226_auto_test.md`
### 手動
- `docs/tests/open/I226_manual_test.md`（すべて Claude。本物の GitHub に、ありえない形の鍵を渡して表示を見る・フックの効き方・ログインなしの `gh`）

## 7. ロールバック
- PR を revert する（設定・データの変更なし）。入れ直した後なら `install.sh` をもう一度流す（`install.sh` は前の版を `~/.cache/github-app/backup` に写してから置き換える）

## 8. Risk & 回避策
- **失効の前の読みが増え、有効な鍵の確かめに 1 回の通信が増える**: 1 回だけで、失効は手で流す操作なので問題ない
- **失効の前の読みが通信の失敗のとき**: DELETE をしないで「確かめられない」（exit 1・控えは残す）にする。漏れた鍵が有効なまま残りうるが、利用者には失敗が見えるので流し直せる（今までの「失効を確かめられない」と同じ扱い）
- **期限切れの控えを「もともと無効」として消す**: 期限切れの鍵は使えないので、消してよい。次の `gh` が取り直す
- **フックが毎回 `code-review.sh` を起こす重さ**: 自動テスト文書の Edit/Write のときだけ。関数の定義を読んで awk を 1 回流すだけ（20 秒で打ち切り、失敗しても通す）
- **フックの検査が書きかけの文書で出る**: 知らせるだけで、編集は止めない（exit 2 は Claude に文を届けるだけ）
- **`~/.local/bin/gh` は写し（`install.sh:69` の `install -m 755`。確かめ済み）なので、入れ直すまで F2 は手元の入口に効かない**: 手動テスト（M-03）はリポジトリの版を `bash scripts/claude/gh-app/gh` で直接流して確かめる。手元の入口の入れ直し（`bash scripts/claude/gh-app/install.sh`）はマージの後に行う（close でマージ依頼と一緒に書く。`revoke.sh` は入れず、いつもリポジトリの版を流す）
- **G10 を論理行にすると、行末が `\` の散文で次の行とつながる**: つながっても見るのは `gh auth status`／`gh auth token` の後ろの語だけで、つながった先の語で `--json` が見つかる向き（合格の向き）にしか変わらない。鍵を出す `gh auth token` は語に関係なく不合格

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- F1: 失効の前に同じ鍵で読み、有効を確かめてから DELETE。前もって 401 なら `--stdin` は「最初から無効」で exit 1、控えは「もともと無効」で控えを消して成功扱い。前もっての読みが 401 以外で失敗したら従来の「確かめられない」（exit 1・控えを残す）
- F5: 見送り（`flock`・比べてから消すのどちらも入れない）
- F6: G10 に `gh auth token` を足し、行末の `\` をつないでから見る。説明の文の中の `--show-token` という語は落とさない
- 予防策: レビュー役の観点には足さず、G9 の決定論のテストで守る
- 同梱: backlog の F2・F4、omission-lint を push の前にも流す（新しい決まりは足さない）

Claude が決めた（技術的な選択と理由）:
- **omission-lint を流す場所 = PostToolUse のフック**（仮定で決めた・技術的）: 候補は (a) pre-commit (b) implement のスキルの手順 (c) PostToolUse のフック。(a) は CI の `--all-files` で古い open の `I034_auto_test.md`（HIGH）が落ち、避けるには `ci.yml` の `SKIP` を直すことになり、どちらも高リスクのパス（敵対的レビュー・設計のセキュリティレビューが要る）。(b) は手続き（書いた本人が流し忘れる）。(c) は決定論で、書いた直後（最も早い）に動き、高リスクのパスでなく、古い文書は触らない限り見ない。→ (c)
- **判定の本体は `code-review.sh` の `omission_lint` 1 か所のまま**（仮定・技術的）: フックに同じ awk を写すと 2 か所がずれる。`--route` と同じ形の入口を足して呼ぶ
- **F2 は終了コードだけ直す**（仮定・技術的）: スパイクで、本物の `gh` が案内の文を標準エラーに出すことを確かめた。同じ文を足すと 2 回出る
- **G10 の `gh auth token` は `--json` の有無を問わず不合格**（仮定・技術的）: `gh auth token` に `--json` は無く、どの書き方でも鍵を出す
- **控えの「もともと無効」は rc に影響しない**（イシューに明記・メモ）
- **`CLAUDE.md` の PostToolUse の説明の 1 文を直す**（仮定・技術的）: フックの役目が増えるので、説明を合わせる（ルールは増やさない）
- 要件・基本設計・UI/UX の仮定: なし（表示の文言はメモで確定した文をそのまま使う）

台帳の残りの一覧（`grep -rnF` で実装対象のファイルと `FILE=-` に当たった行）:
- 一覧 I225 F2（`scripts/claude/gh-app/gh`）: 同梱 — grill-me で確定
- 一覧 I225 F4（`docs/runbooks/plan-writing-rules.md`）: 同梱 — grill-me で確定
- 一覧 I225 F3（`scripts/claude/gh-app/gh`）: 残す — grill-me でスコープ外と確定（本物の `gh` が非 0 のときの扱いで、今回の直しとは別の分岐）
- 一覧 I209 F1（`docs/runbooks/plan-writing-rules.md`）: 残す — 読み取り API のテストの決まりで、今回の変更と関係しない
- 一覧 I206 F4・I207 F6・I207 F7・I208 F1・I208 F2・I208 F3・I208 F5（`scripts/claude/code-review.sh`）: 残す — どれも台帳・振り分けの処理の Low で、今回足す `--lint-auto-test` の入口と関係しない
- 一覧 I223 F6（`scripts/claude/tests/test_i223_gh_app.sh`）: 残す — G6 の検出の狭さ（Low・再現なし）で、今回の G8〜G10 と別
- 一覧 I223 B1〜B4（`FILE=-`）: 残す — bot の停止が解けるまで手を付けられない

要件適合性・業務ロジック:
- 受け入れ条件の範囲を超えた仕様の追加なし（F5 は見送りどおり入れない）。マルチテナント・ステータス遷移は該当なし
- エッジケース: 空の控え（従来どおり消す）・控えが無い（従来どおり）・`--stdin` が空（従来どおり exit 2）・前もっての読みの通信の失敗（exit 1・DELETE しない）・期限切れの控え（もともと無効として消す）

セキュリティ・ベストプラクティス:
- 機密データ: 鍵の値は引数・画面・ログに出さない（今までどおり `GH_TOKEN` の環境変数で渡す）。G9 の g・h でも出力に鍵の値が無いことを確かめる
- 入力バリデーション: `--stdin` の鍵は空白を除くだけ（形の確かめは GitHub の応答に任せる。形で弾くと本物の鍵の形の変化で誤って弾く）
- 最小権限: 変更なし（失効は App の鍵の自分自身の DELETE だけ）
- OWASP・依存ライブラリ: 該当なし（依存の追加なし。フックは標準ライブラリの `subprocess`・`re`・`pathlib` だけ）
- bandit: `posttooluse_check.py` の `subprocess.run` は引数の配列（`shell=False`）で、入力はフックの JSON のファイルのパス。bandit の B603/B404（LOW）が出たら、既存の方針どおり `# nosec` で理由を書いて抑える。MEDIUM 以上は直す
- 「ふつうの書き方の事故」の範囲: G10 はわざと回避する書き方（変数に入れる等）は対象外（I225 から引き継ぎ）

P3/P5/P8 影響なし（DB・外部 API の新規・非同期・インフラの追加なし）。P6 影響なし（UI なし）。P9 影響なし（個人情報・テナントデータを扱わない）。

設計品質:
- 判定の本体を 1 か所にする（omission-lint）。返り値で状態を分ける（`token_state` の 0/1/2・`revoke_one` の 0/1/3）
- 例外処理: フックは流せないとき黙って通す（review-gate が最後に見る）。`revoke.sh` は確かめられないとき失敗にする（安全側）
- 設定値のハードコード: 新しい値なし（パスはスクリプトの場所から求める）

Danger Ops（有無/手順/ロールバック）:
- 無。本物の鍵の失効は手動テストでも行わない（M-01 は GitHub に、ありえない形の鍵を渡すだけで、DELETE は送られない）

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 実験必須 | もともと無効な鍵（`--stdin`・控え）で「失効を確認」が出ない。`--stdin` は exit 1（TC-02 の G9 g・h） |
| V2 | 1 | 実験必須 | 失効の前の読みが通信の失敗のとき、DELETE を送らず exit 1・控えを残す（「無効」と取り違えない） |
| V3 | 2 | 実験必須 | G9 g・h・G8 の空の hosts・G10 の 2 つの FG・TC-10g が、直す前の版（失敗の注入）で不合格になる（false-green でない） |
| V4 | 3 | 読んで可 | 出力・記録に鍵の値が出る道が増えていない（`revoke.sh` の新しい表示・フックの標準エラー） |
| V5 | 1 | 実験必須 | フックは `docs/tests/open/I<数字>_auto_test.md` だけを見て、ほかのファイルの構文の検査の挙動（TC-10a〜f）を変えない |

## 計画変更記録
1. 計画レビュー（20261106_2128・OK）の Warning 3 件への対応: G9 に i)（DELETE の後の読みだけ通信の失敗）を足す・TC-04 の語を `G6・G7` にする・M-02 の前提（フックがワークツリーの版を動かすか）を実装ステップ 4 の直後に確かめ、だめなら新しいセッションで行う。Info 1（戻り値の定数化）は見送り（2 つの関数の冒頭のコメントで足り、シェルの定数はかえって読みにくい）。計画レビューのやり直し: 不要（findings への対応の追記だけで、方式・範囲・受け入れ条件は変えない）
2. 実装と /simplify での形の整理（振る舞いは計画どおり）: (a) `revoke_one` は変数 `before`/`after` を使わず `token_state "$1"; case $? in 0) ;; 1) return 3 ;; *) return 1 ;; esac` の形にし、G9 の FG の sed もこの形に合わせた (b) G10 は論理行のループを作らず、`gh auth (status|token)` の後ろを「バッククォートか、`\` の付かない改行まで」で切ってから `\`＋改行を空白にする形にした（同じファイルの `launch_lines_missing` の結合を写さない） (c) フックの出口は 1 か所のまま、文の頭（`syntax error`／`auto_test の宣言漏れ`）だけを変える (d) 偽の gh の `FAKE_NET_AFTER_DELETE` は、最初の DELETE の後に目印のファイルを 1 つ置き、それ以後の読みを通信の失敗にする (e) 既存の FG「--stdin で読んだ値を使わず控えの鍵を使う」の sed を、呼び出しの新しい形（`revoke_one "$leaked"; rc=$?`）に合わせた。計画レビューのやり直し: 不要（方式・範囲・受け入れ条件は変えない）

## レビュー結果
- [20261106_2128 判定: ✅ 完了](../../reviews/closed/I226_plan_review_20261106_2128.md)
