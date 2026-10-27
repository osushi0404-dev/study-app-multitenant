# I206 計画書: I202 のレビューの残り（台帳の番号の合流と、中身の無い指摘の増え方を最優先で直す）

## 基本情報
- **計画書ID**: plan_I206
- **関連イシュー**: #344
- **Draft PR**: #345
- **作成根拠資料**: docs/issues/open/I206.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I206_review.md
- **作成日**: 2026-10-27

## 1. 背景/目的
- I202 で、止めない指摘も「台帳の残り」として差分のレビューの入力に出すようにした。I202 自身の review-gate で、実物のレビュー役が台帳の残りを直していないのに `STATUS=open` で書き直した。その結果、振り直した番号がレビュー役の新しい番号と合流し、合流しなかった 5 件が中身の無い open の指摘（F15〜F19）として台帳に残った
- 目的: 台帳の更新（`scripts/claude/code-review.sh` の `_LEDGER_PY` の `update`）を決定論で直し、番号が合流しない・中身の無い指摘が増えない状態にする。I197-F1 の守り（見せた番号の使い回しで、差分の中の新しい止める指摘が止まらなくなることを防ぐ）は弱めない。あわせて、I202 の台帳の残り 21 件の採否を決めて片付ける
- 「確かめる 2 点」の測定は I206 では行わず、I196（#331）の retro へ引き継ぐ（設計確認メモ）

### 調査結果
- **原因の概要**: 台帳の更新が、振り直し先の番号を「前の台帳の最大の次」から振る。レビュー役も同じ周に新しい指摘を同じ「次」から付けるので、番号が重なって 1 件にまとめられる。さらに、台帳の残りを「直していない」と open で書き直すと、毎回新しい番号に振り直すため、中身の無い指摘が増える
- **詳細な原因分析**（`scripts/claude/code-review.sh`・develop 0d8cbf3）:
  1. 718 行 `next_id = max([int(k[1:]) for k in led] or [0]) + 1`: 前の台帳だけを見る
  2. 入力（1013 行）はレビュー役に「台帳の最大の番号: F<n>（新しい指摘はこの次から）」と伝える。レビュー役の新しい番号と振り直し先の番号は同じ範囲から振られる
  3. 744〜752 行: 台帳の残りの番号を open で書いた行は `keep` が偽なので振り直し、振り直し先の番号を `seen` に入れる。その後にレビュー役の同じ番号の新しい指摘が来ると `fid in seen` で「同じ指摘の書き直し」とみなされ、合流する（重大度は上の側・要約は後の行で上書き。先に来た側の中身が消えうる）
  4. 台帳の残りの open の書き直しには「振り直す」以外の扱いが無い（I202 計画変更記録 2 で、受け付けると前の SCOPE を引き継いで I197-F1 の穴が戻るため、振り直しにした）
- **再現（スパイク・2026-10-27・成立）**: `REVIEW_LIB_SOURCE_ONLY=1` で `ledger_update` を呼ぶスクリプト（scratchpad）で、前の台帳 F1・F2（台帳の残り）に対し、レビュー役が F1・F2 を「今回の差分では直していない。」で open に書き直し、新しい F3（High・STOP=flow）を書く → 出力は F1・F2（元のまま）・F3（F1 の振り直し先と新しい F3 が合流）・F4（F2 の振り直し先。中身の無い指摘）。イシューの F1・F8 をそのまま再現した
- **環境前提**: `python3` 3.12.3・`flock`（util-linux 2.39.3）・`git` はある。`flock` だけを除いた PATH（`/usr/bin/*` へのリンクから flock を除く）を作れることをスパイクで確かめた（F10 のテストの作り方）
- **既存テストのベースライン**（2026-10-27・develop 0d8cbf3）: `test_i202_ledger_cleanup.sh` pass=72（24 秒）・`test_i197_review_ledger.sh` pass=64・`test_i205_stop_criteria.sh` pass=91・`test_i193_official_flow.sh` pass=160・`test_i197_adversarial_process.sh` pass=115（どれも fail=0）
- **テストの文字列の参照（消費箇所）**: 変える行を写しの置き換え前の文字列に使っているテスト
  - `test_i202_ledger_cleanup.sh` 76 行 `print("YES" if any(e[8] == "up"`（先頭は変えないので、そのまま一致する）・102 行 `if (not body or body.casefold() in NO_REPRO)`（F7 で変わる → 新しい文字列に直す）
  - `test_i197_review_ledger.sh` 299 行 `FILES_NOTE=""; [ "$REVIEW_KIND" = "delta" ] && FILES_NOTE="（差分のレビューの範囲）"`（F20 で変わる → 新しい文字列に直す）
  - `test_i197_review_ledger.sh` R15・`test_i202_ledger_cleanup.sh` L6（台帳の残り・止めない既存の番号を、止める新しい中身に使うと振り直す）: 新しい扱いでも振り直す側なので、期待値は変わらない
  - `changed_outside_records` は `code-review.sh` の 2 か所と `test_i193_official_flow.sh` C14（0/1 の戻り値）だけが使う。`gate-check.sh` は使っていない（挙動を変えない制約に触れない）

## 2. 受け入れ条件
- [ ] AC1: 1 回のレビューの中で、振り直した番号とレビュー役の新しい番号が合流しないことを、失敗注入つきのハーネステストで固定している（TC-01 N1・FG-N1）
- [ ] AC2: 台帳の残りを直していないのに open で書き直しても、中身の無い指摘が台帳に増えないこと（N2・FG-N2）と、I197-F1 の守りが弱まっていないこと（N3・FG-N3）を、失敗注入つきのハーネステストで固定している
- [ ] AC3: 残りの指摘について、直した／見送ったの一覧と理由が計画書にある（4.0 の表）
- [ ] AC4: 確かめる 2 点の引き継ぎ（測る 2 点・基準「どちらも 1 件でもあれば直す／起票する」・見る記録）が I196 のイシュー（ローカル `docs/issues/open/I196.md` と GitHub #331）に書いてある（手動 No.2）
- [ ] AC5: 既存のハーネステスト（`bash scripts/claude/tests/run-all.sh`）・CI がすべて pass する（TC-02・TC-03）

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: `scripts/claude/code-review.sh`・`scripts/claude/adversarial-review.sh`・`.claude/agents/code-reviewer.md`・`.claude/skills/review-gate/SKILL.md`・`docs/runbooks/workflow.md`・`docs/runbooks/review-rules.md`・`scripts/claude/tests/test_i202_ledger_cleanup.sh`・`scripts/claude/tests/test_i197_review_ledger.sh`。記録の場所の外ではない引き継ぎ: `docs/issues/open/I196.md`（未追跡・このブランチではコミットしない）と GitHub #331 の本文
- `gate-check.sh`・`path_risk_trigger()`・`.claude/settings.json`・見張りは変えない

## 4. 変更点一覧（具体）

### 4.0 台帳の残り 21 件の採否（AC3）
方針: 止める判定を見逃す向き（fail-open）と、台帳の質を落とすものは直す。直しが数行で済み、新しい分岐をほとんど足さないものは直す。止める側（余計に止まる）に倒れていて、直すと新しいコードが大きくなるものは見送る（I197・I202 の教訓: 足したコードが次の周の指摘の元になる）。

| # | 場所 | 要約 | 採否 | 理由・直し方 |
|---|---|---|---|---|
| F1 | code-review.sh | 振り直し先の番号とレビュー役の新しい番号が合流する | 直す（最優先） | 4.1 |
| F8 | code-review.sh | 台帳の残りを open で書き直すたびに中身の無い指摘が増える | 直す（最優先） | 4.2 |
| F15〜F19 | I202 の台帳 | F6〜F10 の書き直しの重複（中身なし） | そのまま残す | I202 は閉じたイシューで、記録（`docs/reviews/closed/`）は当時の出来事の記録として書き換えない。台帳は I### ごとなので I206 以降の判定に影響しない。台帳から除く手段は、使う場面が無いので作らない |
| F6 | code-review.sh | `risk` モードが種類を見ずに `RISK=up` で YES にする | 直す | 4.3。`KIND=app` の行の目印だけを数える（code-reviewer.md の「ハーネスだけの変更では付けない」をスクリプトで強制。1 行の条件） |
| F7 | code-review.sh | 「なし（理由）」「なし。」は再現ありになる | 直す | 4.4。先頭が「なし」などで、その後が終わり・句読点・括弧・空白のときも再現なし |
| F12 | code-review.sh | `changed_outside_records` が git の失敗を検知しない（fail-open で NO_DELTA=1・レビューを飛ばす） | 直す | 4.5。git の出力を一時ファイルに受け、失敗なら 2 を返す。呼び出し元 2 か所は「0 以外＝変わった」の側（レビュー役を呼ぶ・BLOCKER）に倒れるので、呼び出し元は変えない |
| F14 | code-review.sh | 早期 exit で一時ファイルが残る | 直す | 4.6。一時フォルダを先頭で 1 つ作り、既存の `trap cleanup_official EXIT` をそこへ移す。一時ファイルはその中に作る |
| F20 | code-review.sh | 入力の見出し「変更ファイル一覧（差分のレビューの範囲）」が取り消したファイルを含む一覧と食い違う | 直す | 4.7。見出しの文言だけ |
| F21 | code-review.sh | 見せるファイルの一覧の作成の失敗（comm・sort）を `\|\| true` で握りつぶす | 直す | 4.7。空行の除去を `sed '/^$/d'`（空でも 0）にし、失敗は ⛔ で止める |
| F9 | code-review.sh・説明 | 台帳の目印で YES になっても同じ周の `/security-review` は走らない（review-gate の説明「高リスク時は /security-review も」と食い違う） | 説明を直す | 4.8。`/security-review` は I193 からパスの判定（`RISK_PATH`）が YES のときだけ走る作り（計画レビューの Yes でも走らない）。目印で上がった分は敵対的レビューが受け持つ。コードは変えず、3 つの文書の「高リスク時は」を「パスの判定が YES のとき」に直す |
| F3 | adversarial-review.sh | `check_worktree` が flock の外で、ほかの観点の実験の途中の状態を拾いうる | 直す | 4.9。`check_worktree` を鍵の中（実験役の直後）へ移す |
| F5 | adversarial-review.sh | 鍵を取った後の締め切りの確認（1 回分）が鍵の前（2 回分）より緩い | 直す | 4.9。鍵の後も `2 * ADV_MIN_STEP` で比べる |
| F10 | adversarial-review.sh | `flock` の存在確認が無い | 直す | 4.9。起動時に `command -v flock` を確かめ、無ければ `ADVERSARIAL_ERROR: FLOCK`・exit 2（実行できない） |
| F23 | テスト | `mixed()` の `git push 2>/dev/null` が push の失敗を隠す | 直す | `2>/dev/null` を外すだけ（テストの切り分けやすさ） |
| F4 | adversarial-review.sh | 読めないログが 1 つで周全体が HIGH | 見送り | 止める側の誤り。result 行の無いログができるのは、実験の結果を返す続きの呼び出しが時間切れになったときで、そのときはその観点の実験必須の項目が「未検証（実験が実行されていない）」になり、読めないログが無くても HIGH になる。判定が変わる場面がほぼ無いのに、ログごとの扱いを分ける分岐が要る |
| F13 | code-review.sh | develop の取り込みだけの周でもレビュー役を呼ぶ | 見送り | 費用と入力の質の問題で、止める判定は変わらない。I202 で「直したものが無ければ呼ばない」の判定を細かくして止める指摘が 2 件（F2・F11）出た。同じ場所をさらに細かくするのは同じ危険をくり返す |
| F22 | code-review.sh | 100KB で切ると後ろの取り消しの差分が落ちうる | 見送り | 100KB で切るのはすべてのレビューに共通の既存の上限。取り消しの差分が見えないと止める指摘が resolved にならない（止まり続ける側）で、見逃す向きではない |

### 4.1 番号の合流（F1・AC1）
- 修正方針: 振り直し先の番号を「前の台帳と今回のレビューの FINDING 行の番号の最大の次」から振る。今回のレビューの番号を先に全部読めば、振り直し先がレビュー役の番号と重ならない
- `_LEDGER_PY` の `update`:
  ```python
  findings = read_findings(cur)
  # 振り直し先は、前の台帳と今回のレビューの番号のどちらとも重ならない番号から振る（I206 F1: 合流を防ぐ）
  next_id = max([int(k[1:]) for k in led] + [int(g[0][1:]) for g in findings] or [0]) + 1
  for fid, sev, st, path, line, sec, stop, risk, rest in findings:
  ```
  ループの中の `next_id = max(next_id, int(fid[1:]) + 1)` は要らなくなるので消す（今回の番号はすべて最初の最大に含まれる）
- 入力の「台帳の最大の番号: F<n>（新しい指摘はこの次から）」は変えない（レビュー役の番号の付け方は今のまま）

### 4.2 中身の無い指摘の増え方（F8・AC2）
- 修正方針: 台帳の残りの番号を open で書いた行は、その行だけで判定し直す。止める指摘に当たれば今までどおり新しい番号に振り直す（I197-F1 の守り: 新しい止める指摘を前の SCOPE で隠さない）。止める指摘に当たらなければ、その行を捨てる（前の台帳の行をそのまま残す）
- 止めない新しい指摘が台帳の残りの番号に紛れたときは台帳に入らないが、止めない指摘は合否に関係しない（止める判定は変わらない）。入力でレビュー役に「直していないものは書かない・新しい指摘は新しい番号で」と伝える（4.10）
- `_LEDGER_PY` の `update` のループ:
  ```python
      title, repro = split_repro(rest or "")
      k = branch_kind(branch_files) if path == "-" else kind_of(norm_path(path))
      fresh = [sev, st, scope_of(path, line, stop), k, stop, repro, sec, title, risk]
      # I206 F8: 台帳の残りを open で書いた行は、止める中身のときだけ新しい指摘として振り直す（I197-F1 の守り）。
      # 止めない中身（「直していない」の書き直しなど）は捨てて、前の行のまま残す（中身の無い指摘を増やさない）
      if fid in rest_ids and st == "open" and fid not in remap and fid not in seen and not blocking(fresh):
          continue
      keep = ...（今のまま）
      ...（振り直し・seen は今のまま）
      if fid in led:
          ...（今のまま）
      else:
          led[fid] = fresh
  ```

### 4.3 目印の種類（F6）
- `risk` モード: `any(e[8] == "up" and e[3] == "app" for ...)`。harness・guard の行の目印は数えない（guard はパスの判定で既に YES。harness は code-reviewer.md で「付けない」と決めたもの）
- 前の記録（rebase 後の全体のレビュー）を読むときも同じ条件で読む（一度 YES になった app の目印は戻らない、は変わらない）

### 4.4 「なし（理由）」（F7）
- `split_repro`: `NO_REPRO` の完全一致に加えて、先頭が `なし`・`無し`・`none`・`n/a` で、その直後が行の終わり・`（`・`(`・`。`・`、`・`.`・`,`・`:`・`：` のときも再現なし
  ```python
  NO_REPRO_HEAD = re.compile(r"(?:なし|無し|none|n/a)(?:$|[（(。、.,:：])")
  ...
  return ..., "no" if (not body or body.casefold() in NO_REPRO or NO_REPRO_HEAD.match(body.casefold())) else "yes"
  ```
  「なしでも落ちる」（直後が文字）・「なし 入力 x」（直後が空白）は再現あり（空白の後に再現が続く書き方を再現なしにしない・計画レビュー Warning 1）。`-` は完全一致だけ（箇条書きの「- 入力…」を再現なしにしない）

### 4.5 `changed_outside_records` の git の失敗（F12）
```bash
changed_outside_records() {   # $1=from $2=to → 0=変わっていない / 1=変わった（ファイル名を出す）/ 2=git の失敗
  local f out="" names
  names=$(mktemp) || return 2
  # git の失敗を戻り値で受けるため、一時ファイルに受ける（process substitution は失敗を返さない・I206 F12）
  git -c core.quotePath=false diff -z --name-only --no-renames "$1" "$2" > "$names" || { rm -f "$names"; return 2; }
  while IFS= read -r -d '' f; do
    is_record_path "$f" || out+="${f}"$'\n'
  done < "$names"
  rm -f "$names"
  if [ -n "$out" ]; then printf '%s' "$out"; return 1; fi
  return 0
}
```
呼び出し元（NO_DELTA の判定・レビュー中のドリフトの検査）は「0 のときだけ変わっていない」の形なので、2 は「レビュー役を呼ぶ」「BLOCKER」の側に倒れる（変えない）。ドリフトの検査の ⛔ 文言は「変わりました」のままだが、2 の場合も BLOCKER で止まる（文言の出し分けは足さない）

### 4.6 一時ファイルの後片付け（F14）
- 本体の先頭（`cd "$REPO_ROOT"` の直後）で `OFFICIAL_DIR=$(mktemp -d)`・`OFFICIAL_PIDS=()`・`cleanup_official`・`trap cleanup_official EXIT` を置く（今は 921〜928 行。中身は変えずに移す）
- `SCOPE_FILE`・`PREV_LEDGER_FILE`・`HUNKS_FILE`・`BRANCH_OWN_FILE`・`OUTSIDE_SINCE_FILE`・`SHOWN_FILES_FILE`・`LEDGER_FILE` は `"$OFFICIAL_DIR/<名前>"` にする（`mktemp` を使わない）。1139 行の `rm -f …` は要らなくなるので消す
- `PREV_LEDGER_FILE` は前の台帳があるときだけ値を入れる今の形を保つ（空なら「前の台帳なし」）

### 4.7 入力の見出しと一覧の作成の失敗（F20・F21）
- `FILES_NOTE="（差分のレビューの範囲と、取り消したファイル）"`
- 見せるファイルの一覧:
  ```bash
    { cat "$SCOPE_FILE"
      LC_ALL=C comm -12 … | LC_ALL=C comm -23 - <(LC_ALL=C sort "$SCOPE_FILE")
    } | sed '/^$/d' > "$SHOWN_FILES_FILE" || { echo "⛔ 差分のレビューで見せるファイルの一覧を作れません（起点 ${SINCE}）"; exit 1; }
  ```
  （`grep -v '^$'` は空のとき 1 を返すので `|| true` が要った。`sed` は空でも 0。process substitution の中の sort の失敗は拾えないが、外側の `cat`・`comm` の失敗は拾う）

### 4.8 `/security-review` の説明（F9）
- `.claude/skills/review-gate/SKILL.md` 3 行目（description）: 「組み込みの /code-review（高リスク時は /security-review も）」→「組み込みの /code-review（パスの判定が YES のときは /security-review も）」
- `docs/runbooks/workflow.md` 26 行: 「（高リスク時は `/security-review` も。」→「（パスの判定が YES のときは `/security-review` も。」
- `docs/runbooks/review-rules.md` 54 行: 「（高リスク時は `/security-review`）」→「（パスの判定が YES のときは `/security-review`。台帳の目印・計画レビューで高リスクになった分は敵対的レビューが受け持つ）」

### 4.9 adversarial-review.sh（F3・F5・F10）
- F3: `check_worktree` の呼び出しを、`flock 9` のブロックの中の `run_experiment_agent` の直後へ移す（鍵を持ったまま比べる。ほかの観点の実験は鍵の外では動かない）。`waited_out=1` のとき（実験役を呼ばなかった）は比べない
- F5: 鍵の後の確認を `if [ "$(remaining)" -lt $(( 2 * ADV_MIN_STEP )) ]; then waited_out=1` にする（鍵の前の 256 行と同じ）
- F10: ISSUE の形の確認の直後に
  ```bash
  if ! command -v flock >/dev/null 2>&1; then echo "⛔ flock がありません（実験役を 1 本ずつにできない）。util-linux を入れてください。"; echo "ADVERSARIAL_ERROR: FLOCK"; exit 2; fi
  ```

### 4.10 台帳の残りの書き方（入力と code-reviewer.md）
- `code-review.sh` 1017 行の入力の節の見出し: `#### 台帳の残り（止めない open の指摘。直したと差分から分かるものだけ、同じ番号で STATUS=resolved の FINDING 行を書く。直していないものは書かない〔open で書いても台帳は変わらない〕。新しい指摘は新しい番号で書く）`
- `.claude/agents/code-reviewer.md` 241 行: 「（書かなければ open のまま。この番号を open で書くと新しい指摘として振り直される）」→「（直していないものは書かない。書かなければ open のまま。この番号を open で書いても、止める指摘に当たる中身でなければ台帳は変わらない。新しい指摘は台帳の残りの番号を使わず、新しい番号で書く）」

### 4.11 確かめる 2 点の引き継ぎ（AC4）
- `docs/issues/open/I196.md`（未追跡・I196 の /plan-issue がコミットする）の「## 制約・引き継ぎ情報」に次の節を足し、`gh issue edit 331 --body-file docs/issues/open/I196.md` で GitHub と同期する（I196.md はこのブランチではコミットしない）:
  ```markdown
  ### I206 からの引き継ぎ（retro で測る・確かめる 2 点）
  - 測る記録: この I196 の `docs/reviews/I196_code_review_*.md`（台帳の `RISK=up` の行・証跡の「高リスク判定」）と、敵対的レビューが走ったときの `docs/reviews/I196_adversarial_review_*.md`（「## 実験」の「実行していない（締め切り）」）
  - ① `RISK=up` の付けすぎ: 付いた件数と理由。本来付けない場面（ハーネスだけの変更・アプリの高リスクの条件に当たらない理由）で 1 件でも付いていたら直す（起票する）
  - ② 敵対的レビューの締め切りによる未検証: 「実行していない（締め切り）」の件数。1 件でもあれば、締め切り・実験役を `flock` で 1 本ずつにした作りの見直しを起票する
  - 結果（件数・記録のパス・直す／直さない）は I196 のレビュー文書の「## 振り返り」に書く
  ```

## 5. 実装手順（ステップ）
未知リスクは無い（スパイクで 2 つの不具合の再現と、flock を除いた PATH の作り方を確かめた）。最優先の 4.1・4.2 を先にする。
1. テストを先に書く（TDD）: `test_i202_ledger_cleanup.sh` に「I206」の節（N1〜N14 と FG）を足す → TC-01（今のコードで新しい振る舞いの項目が不合格になった件数を TC-01 の結果に書く）
2. 4.1・4.2（`_LEDGER_PY` の `update`）→ TC-01 の N1〜N3
3. 4.3・4.4（`risk`・`split_repro`）。`test_i202_ledger_cleanup.sh` 102 行の FG の置き換え前の文字列を新しい形に直す → TC-01 の N4・N5・L3
4. 4.5〜4.7・4.10（`code-review.sh` の本体と入力）。`test_i197_review_ledger.sh` 299 行の置き換え前の文字列を新しい `FILES_NOTE` に直す → TC-01 の N6〜N9・N14、TC-02
5. 4.9（`adversarial-review.sh`）と F23 → TC-01 の N10〜N12、TC-02
6. 4.8（3 つの文書）・4.10（code-reviewer.md）→ TC-01 の N13・N14
7. 4.11（I196 への引き継ぎ）→ 手動 No.2
- 依存: 2 は 1 の後。3〜6 は 2 の後なら順不同（同じテストファイルに足すので順にする）。7 はいつでもよい

## 6. テスト計画
### 自動（docs/tests/open/I206_auto_test.md）
- テストのレベル: すべてハーネスの単体（`ledger_update` などの関数を `REVIEW_LIB_SOURCE_ONLY=1` で読み込む）と、スタブ（gh・claude）で本体を丸ごと動かす通し。アプリのテスト（pytest・Jest・E2E）は非該当
- 再発防止: N1（合流）・N2（中身の無い指摘）を、I202 の実物の形（`FILE=- LINE=-`・「今回の差分では直していない。」）で固定する
- 否定・不在の項目にはすべて失敗注入（FG: 本体の写しの判定の要を壊すと不合格）を付ける
- 時間に依存する項目（N10）は、余裕を持たせた値（締め切り 20 秒・`ADV_MIN_STEP=6`・実験役 9 秒）で、許される遅れ 5 秒まで結果が変わらないようにする
### 手動（docs/tests/open/I206_manual_test.md）
- No.1: このイシュー自身の review-gate の記録で、実物のレビュー役の書き方で中身の無い指摘が増えていないか（差分のレビューの周があれば）
- No.2: I196 への引き継ぎ（AC4）

## 7. ロールバック
- PR を revert する（ハーネスのスクリプト・テスト・文書だけ。データ・設定の変更は無い）。I196.md の引き継ぎの節は、I196 の側で消せばよい（GitHub #331 は本文を編集し直す）

## 8. Risk & 回避策
- 台帳の残りの番号に止めない新しい指摘が紛れると、台帳に入らない → 止める判定は変わらない（4.2）。入力と code-reviewer.md で新しい番号を使うよう伝える。止める中身なら振り直す（N3 で固定）
- `risk` を app だけにすると、guard の行の目印は数えない → guard はパスの判定で既に YES になる（`path_risk_trigger()` と `kind_of` の guard は同じ集合・既存テスト R-K2 で一致を固定）
- 「なし（理由）」を再現なしにすると、本当に再現のある指摘を「なし、ただし…」と書いたときに止まらない → 直後が句読点・括弧のときだけにし、「なしでも落ちる」は再現ありのまま（N5）。再現を書くレビュー役の決まりは「再現: <入力・手順・壊れ方>」で、「なし」で始めるのは再現が無いとき
- 時間に依存するテスト（N10）が CI で揺れる → 余裕を持たせた値にし、既存の A1b と同じ作り
- F12 の直しで、一時ファイルの作成（mktemp）自体が失敗した場合 → `names=$(mktemp) || return 2` で 2 を返す（止める側。呼び出し元が `if` の中でも `set -e` の下でも同じ）

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 確かめる 2 点は I206 では測らず、I196（#331）の retro で測る。I206 では引き継ぎ（測る 2 点・基準・見る記録）を I196 のイシューに書く
- 基準: ① `RISK=up` が本来付けない場面で 1 件でも付いていたら直す ② 締め切りによる未検証が 1 件でもあれば見直しを起票する
- I197-F1 の守りを弱めない・止める基準・変更の種類・行で決める範囲の方式は変えない・`gate-check.sh` の挙動と `path_risk_trigger()` は変えない・見張りと settings は変えない
- 粗く確実な形を優先する

Claude が決めた（技術的な選択と理由。要件・基本設計・UI/UX の仮定は無い）:
- 番号の合流は「振り直し先を今回のレビューの番号の最大の次から振る」で直す（仮定で決めた）。理由: 1 行の変更で、レビュー役の番号の付け方（入力）を変えずに済む。代わりに入力の「最大の番号」を変える案は、レビュー役が守らなければ再発するので採らない
- 台帳の残りの open の書き直しは「止める中身なら振り直す・それ以外は捨てる」（仮定で決めた）。理由: 止める判定に関わるもの（I197-F1 の守り）だけを残し、止めないものは合否に関係しないので、中身の比較（要約の文字列の比較など）のような壊れやすい判定を足さずに済む
- F15〜F19 はそのまま残す（イシューで「計画で決める」とされたもの）。理由は 4.0
- 残り 21 件の採否は 4.0 の表（イシューで「まとめて計画で決める」とされたもの）
- テストは新しいファイルを作らず、`test_i202_ledger_cleanup.sh` に「I206」の節を足す（仮定で決めた）。理由: 一時のリポジトリ・スタブ・通しの関数（`setup`・`round` など）をそのまま使え、写しを作らずに済む（イシューの実装対象にも `test_i202_ledger_cleanup.sh など` とある）
- 高リスク判定: ハーネスだけの変更で、`path_risk_trigger()` の集合（`.github/`・`.pre-commit-config.yaml`・`.secrets.baseline`・見張り・settings）に触れない。アプリの高リスクの条件（認証・認可・テナント境界・個人情報・決済など）にも当たらない → No の見立て（判定は plan-review）

セキュリティ・ベストプラクティス:
- セキュリティ影響なし（アプリのコード・認証認可・個人情報・依存ライブラリを変えない。bandit・npm audit の対象の変更なし）。判定の仕組みの変更は、止める判定を見逃す向き（fail-open）にしないことを N3・N6 と FG で固定する（F12 は fail-open を fail-closed に直す）
- 入力の扱い: レビュー役の FINDING 行は今までどおり `FIND` の正規表現で全体一致したものだけを読む（形の崩れは exit 2）。新しく読む値は無い
- 設定値: 時間の値（`ADV_MIN_STEP` など）は既存の環境変数のまま。新しい定数は `NO_REPRO_HEAD` だけ

要件適合性: 受け入れ条件の範囲を超えた仕様の追加は無い（4.0 の直す項目はイシューの「残りの指摘の採否と対応」の範囲）。マルチテナント・ステータス遷移は非該当

P3/P5/P8 影響なし（DB・外部 API・非同期処理・インフラの追加なし。依存関係ファイルの変更なし）。P6 影響なし（UI・データ量の懸念なし）。P9 影響なし（個人情報・未成年データ・テナントデータを扱わない）

設計品質: Python の部分は今の `_LEDGER_PY` の形（1 つの埋め込みスクリプト・モードで分ける）を保つ。シェルは `set -euo pipefail` の下で、失敗を `|| true` で握りつぶさない形にする（F21）

Danger Ops（有無/手順/ロールバック）:
- 無（データ削除・破壊的変更・強制 push は無い）

## 計画変更記録
（実装中に計画と違うことをするときに書く）
- 1（計画レビュー 20261027_1754 の Warning 対応・2026-10-27）: 4.4 の `NO_REPRO_HEAD` から空白を外し（「なし 入力 x」は再現あり・N5 に期待値を追加）、4.5 は `names=$(mktemp) || return 2` にした。方式・範囲・受け入れ条件は変えないので再レビューはしない。Warning 2（N11 は配置の確認）は N10 の通しで鍵の動作を確かめているので計画どおり
- 2（implement・2026-10-27）: 計画書の記載「4.8 … 3 つの文書の『高リスク時は』を直す」。採った方法: `docs/runbooks/issue-flow.md` 131 行にも同じ「（高リスク時は /security-review）」があったので、同じ文言に直し、N13 の対象に足した（4 つの文書）。理由: 消費箇所の取りこぼし（plan-writing-rules「規約是正時の消費箇所の全件列挙」）。計画レビューのやり直し: 不要（同じ方針の対象の追加だけで、方式・範囲・受け入れ条件は変えない）
- 3（implement・2026-10-27）: 計画書の記載「4.7 `{ cat "$SCOPE_FILE"` 改行 `LC_ALL=C comm -12 …` `} | sed …`」。採った方法: `{ cat "$SCOPE_FILE" &&` 改行 `LC_ALL=C comm -12 …`（&& でつなぐ）。理由: `{ }` の終了コードは最後のコマンドのものだけで、`cat` の失敗が外に伝わらなかった（N9 が実装後も不合格で判明）。合わせて FG-W4c の写しの置き換えを `{ cat "$SCOPE_FILE"; : ||` に直した（取り消したファイルを足さない形のまま、終了コードは 0）。計画レビューのやり直し: 不要（4.7 の目的〔失敗で止める〕の実現の細部だけ）

## レビュー結果
- [20261027_1754 判定: ✅ 完了](../../reviews/I206_plan_review_20261027_1754.md)
