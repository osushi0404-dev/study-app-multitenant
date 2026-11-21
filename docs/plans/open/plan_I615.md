# I615 計画書: 外で動く入口をレビュー済みの写しで動かし、人に `!` を頼まなくする

## 基本情報
- **計画書ID**: plan_I615
- **関連イシュー**: #615
- **Draft PR**: #624
- **作成根拠資料**: docs/issues/open/I615.md（GitHub #615 の本文の写し・正は GitHub）
- **実装後評価**: docs/reviews/open/I615_review.md
- **作成日**: 2026-11-22

## 1. 背景/目的
- I599 から、外で動く必要のある入口（`OUTSIDE_SCRIPTS` の 16 本。コードレビュー・計画レビューなど）は、`scripts/claude/` にレビュー前の中身が 1 つでもあると外で動かず、ユーザーに `!` を頼む。ハーネスのイシューでは 1 イシューで 2〜4 回、流れに人の手が入る
- 目的: 入口を、フックと同じく「develop から分かれた時点（BASE）の写し」で動かし、`scripts/claude/` を変えたブランチでも Claude が人の手なしに起動できるようにする。守り（書き換えた中身をレビュー前に外で動かさない）は保つ
- 同梱: I610 のレビューの残り F1（写しの作成の競合）・F2（フックの子の python に `-I` が無い）と、I586 で起きた「git の更新をほかのコマンドとつないで流し、サンドボックスの中で途中まで書き換えて止まる」事故の予防

### 調査結果
**原因の概要**: 起動役は「作業ツリーの `scripts/claude/` がまるごとレビュー済みか」で外に出すかを決めているので、1 ファイルでも変えると全部の入口が止まる。フックの起動役（I610）のように、レビュー済みの写しを動かす形にしていなかった。

**詳細**:
1. 起動役の判定: `.claude/hooks/unreviewed.py:219-244`（`run`）が `dirty()`（BASE との差・未追跡・無視されるファイル。`:95-113`）が空でないと exit 3 で止まり、`! bash scripts/claude/<名前> …` を案内する
2. フックの起動役: `.claude/hooks/reviewed-hook.sh:36-57` が `git archive $base scripts/claude` の写しを `~/.cache/claude-reviewed-hooks/<BASE>/` に作り、いつも写しでフックを動かす。写しの作り方は、このファイルにしか無い
3. F1（I610 の台帳）: `.claude/hooks/reviewed-hook.sh:49` が `rm -rf "$snap"` してから `mv -T` するので、同時に起動した別の起動役が置いた写しを消し、その間にその写しで動こうとした起動役が開けずに exit 2（PreToolUse では止める扱い）になりうる
4. F2（I610 の台帳）: `scripts/claude/hooks/sessionstart_context.py:200` が子を `[sys.executable, abspath(__file__), "--sync-primary"]` で起こし、`-I` が無い（親の `-I` は子に引き継がれない）。`posttooluse_check.py:55` は `bash` を起こすだけで python ではない
5. I586 の事故（イシューのコメント 2026-11-22）: `git merge --ff-only origin/develop 2>&1 | tail -2` はつなぎがあるのでサンドボックスの中で動き、git が `.claude/hooks/reviewed-hook.sh`（中から書けない）を書き換えられずに途中で止まった。戻すにはユーザーの `! git reset --hard` が要った
6. **入口を写しから動かしても動くか（スパイク・2026-11-22・成立）**: BASE の `git archive` を一時フォルダに広げ、作業フォルダをリポジトリの最上位にして `bash <写し>/scripts/claude/issue-source.sh path I610` → `docs/issues/closed/I610.md`（exit 0）。`bash <写し>/scripts/claude/code-review.sh --lint-auto-test docs/tests/closed/I610_auto_test.md` → exit 0。`REVIEW_LIB_SOURCE_ONLY=1` で読み込むと `review-process-lib.sh` を写しの側から読む（`gate_reviewed` が定義される）。入口は、同じフォルダの部品を `$(dirname "${BASH_SOURCE[0]}")` から、リポジトリを作業フォルダの `git rev-parse --show-toplevel` から求めるので、写しから動かしても作業ツリーの記録・計画書を読む
7. **入口が作業ツリーのスクリプトを動かす箇所（全件 grep）**: 16 本と、それが読む `review-process-lib.sh`・`fix-review-lib.sh` で、`(bash|python3|source|.) "$REPO_ROOT/scripts/claude/…"` か素の `scripts/claude/…` を動かすのは 2 か所だけ
   - `scripts/claude/fix-diagnosis-review.sh:10`: `source "$REPO_ROOT/scripts/claude/fix-review-lib.sh"`（作業ツリーの部品を読む）→ 同じフォルダから読む形に直す（4-4）
   - `scripts/claude/code-review.sh:441-458`（`run_declared_gates`）: 自動テスト文書のゲートの `bash scripts/claude/tests/test_*.sh` を作業ツリーで流す。`gate_reviewed`（`unreviewed.py dirty`）がレビュー前の中身があるときは流さない（I599）。この判定は残す（`dirty` の CLI は変えない）
   - `gh` は `~/.local/bin/gh`（リポジトリの外に入れた写し）で、作業ツリーを読まない
8. **入口の部品を機械で見分けられるか（スパイク・2026-11-22・成立）**: 写しの入口の本文から、注釈の行（`#`）と表示の行（`echo`・`printf` で始まる）を除き、`scripts/claude/` の直下のファイル名とレビュー役の名前（`.claude/agents/<名前>.md`）が語として出てくるものをたどると、16 本の部品は次のとおりで、実際の読み込み・呼び出しと一致した（注釈まで数えると、`code-review.sh` が注釈で触れる `gate-check.sh`・`adversarial-review.sh` なども部品になり、見張りや関所を直すたびに `!` が要る）
   - `adversarial-review.sh` → `code-review.sh`・`review-process-lib.sh`・adversarial-reviewer・code-reviewer ／ `code-review.sh` → `review-process-lib.sh`・code-reviewer ／ `pr-base-sync.sh` → `code-review.sh`・`review-process-lib.sh`・code-reviewer ／ `fix-diagnosis-review.sh` → `fix-review-lib.sh`・fix-diagnosis-reviewer ／ `issue-review.sh` → `issue-source.sh`・issue-reviewer ／ `plan-issue-review.sh` → plan-reviewer ／ ほかの 10 本は部品なし
9. 公式の機能で表せないか（`docs/runbooks/plan-writing-rules.md`「規約と依存の照合」）: サンドボックスの外に出すかは `sandbox.excludedCommands` の型（コマンドの文字）で決まり、「どの版の中身を動かすか」「つないだら止める」を表す設定は無い。フックの起動役（I610）と同じく、`.claude/hooks/` の起動役で表す
10. 見張りに判定を足す決まり（`docs/runbooks/danger-ops.md:105-108`）: (1) 公式で表せない（上の 9。つないだ形を止める deny／ask の型は無い。`Bash(git merge *)` の deny では単独の形も止まる）(2) 事故の例: I586 の /plan-issue（2026-11-22）の上の 5 (3) 意図的な回避（変数で git を組み立てる等）の指摘は Low として一覧に回す
11. 外と中の境目（`plan-writing-rules.md`「外と中の境目を動かす計画」）: 外に出す型・`OUTSIDE_SCRIPTS` は変えない。外で動く中身の版が変わる（作業ツリー → BASE の写し）だけ。外に出る必要の根拠は I599 から変わらない
12. 環境: Python 3.12.3（`-I` は `-E -s -P` を含む）・git 2.43.0・bash 5.2

## 2. 受け入れ条件
- [ ] AC1: `scripts/claude/` にレビュー前の中身（書き換え・追跡していない新規・無視されるファイル）があっても、流す入口とその部品・レビュー役の定義を変えていなければ、起動役は入口を外で動かし、終了コードは入口のもの（人に `!` を頼まない）（TC-01・manual No.1）
- [ ] AC2: そのとき外で動く入口・部品は BASE の写しのもので、作業ツリーで書き換えた中身は外で動かない。流す入口・その部品・使うレビュー役の定義のどれかを BASE から変えていれば、起動役は何も動かさずに終了コード 75 で止まり、`! bash scripts/claude/<名前> <引数>` を案内する（新しい版をユーザーに流してもらい、その結果をその周の正式な結果にする）（TC-02・manual No.2）
- [ ] AC3: 基準（`git merge-base HEAD origin/develop`）を求められない・写しを作れないときは、作業ツリーの版を外で動かさずに終了コード 75 で止まり、`!` を案内する（TC-03）
- [ ] AC4: 写しの作り方・置き場所は 1 か所（`.claude/hooks/reviewed-snapshot.sh`）にあり、フックの起動役と入口の起動役は同じ BASE で同じ写しを使う（TC-04・manual No.4）
- [ ] AC5: 写しを作る処理は、ほかの起動役が置いた写しを消さない（F1・TC-05）。フックが起こす python は子のプロセスも含めてすべて `-I`（F2・TC-06）
- [ ] AC6: 作業ツリーを書き換える git の操作を、サンドボックスの中で動く形（git・gh・docker 以外とのつなぎ・`|`・`>`・`<`・`&`・かっこ・`$(…)`・バッククォート・前置きの代入）で流そうとすると、見張りが止めて単独で流すよう案内する。単独の形と git どうしのつなぎ、読み取りだけの git は今までどおり通る（TC-07・manual No.5）
- [ ] AC7: 手順書の「ユーザーに `!` で流してもらう」は、写しを作れないとき・入口か部品を変えたとき・git の更新が途中で止まったときの戻しの 3 つの場面だけになっている（manual No.6）

## 3. 影響範囲
| 区分 | 内容 |
|---|---|
| Backend・Frontend・DB | なし |
| 起動役（安全装置・`.claude/hooks/`） | 新規 `.claude/hooks/reviewed-snapshot.sh`（写しの作り方の正）・`.claude/hooks/reviewed-hook.sh`（すべてのフックの起動役。このセッションのフックも即座にこれで動く）・`.claude/hooks/unreviewed.py`（入口の起動役） |
| 見張り（安全装置） | `scripts/claude/hooks/pretooluse_guard.py`（git の更新をつないだ形を止める）・`scripts/claude/tests/guard_must_stop_cases.txt`（止める形を足す） |
| フック | `scripts/claude/hooks/sessionstart_context.py`（子に `-I`） |
| 入口 | `scripts/claude/fix-diagnosis-review.sh`（部品を同じフォルダから読む） |
| テスト | `scripts/claude/tests/i599_cases.py`（I615 の TC を足し、止める形から写しで動く形に直す） |
| 文書 | `docs/runbooks/danger-ops.md`・`docs/runbooks/harness-audit.md` |
| 意図的に変えない | `.claude/settings.json`（外に出す型・フックの呼び方は同じ）・`OUTSIDE_SCRIPTS` の一覧・`.claude/agents/*.md`（部品として読むだけ）・`.claude/skills/`（下の 9。案内は起動役の出力と danger-ops.md に置く）・`docs/runbooks/workflow.md`（`!` の案内の記述が無い）・`scripts/claude/code-review.sh`（`gate_reviewed` は `dirty` のまま） |
| 依存 | 追加なし |

## 4. 変更点一覧（具体）

### 修正アプローチ
写しの作り方を新しい `.claude/hooks/reviewed-snapshot.sh` の 1 か所にまとめ（置き場所を新しい名前にし、F1 の `rm -rf` をやめる）、フックの起動役と入口の起動役の両方がそれを使う。入口の起動役は、作業ツリーがレビュー済みかを問わず、BASE の写しの入口を、作業フォルダをリポジトリの最上位にして動かす。ただし、流す入口・その部品・使うレビュー役の定義のどれかがブランチで変わっていれば、動かさずに `!` を案内する（その入口だけ今までどおり）。部品は写しの入口の本文から機械でたどる。見張りには、作業ツリーを書き換える git の操作を中で動く形で流すのを止める判定を足す。

### 4-1. 新規 `.claude/hooks/reviewed-snapshot.sh`（写しの作り方の正）
達成すること: BASE を求め、写しが無ければ作り、写しの最上位の場所を返す。ほかの起動役が置いた写しを消さない。
- 関数 `reviewed_snapshot <root>`: 標準出力に写しの最上位（`<cache>/<BASE>`。その下に `scripts/claude/…`）を出す。戻り値 0＝写しあり／3＝基準を求められない／4＝写しを作れない（理由は標準エラーに `[reviewed-snapshot] …`）
  - `GIT_` の環境変数を外し、`git -c core.fsmonitor=false -c core.hooksPath=/dev/null -c submodule.recurse=false -C <root>`（今の `reviewed-hook.sh:26-27` を移す）で `merge-base HEAD origin/develop`
  - 置き場所: `${HOME}/.cache/claude-reviewed-snapshots/<BASE>`（新しい名前。I610 までの `claude-reviewed-hooks` には、F1 の競合で `.complete` の無い写しが残りうるので使わない。古い場所は使わなくなり、消してよい〔手順書に書く〕）
  - 写しがあれば（`.complete` がある）すぐ返す（git は `merge-base` の 1 回だけ）
  - 無ければ作成の処理（内部の関数 `_reviewed_snapshot_make <root> <base> <cache>`。TC-05 が有無の確かめを飛ばして直接呼ぶ）で、`mktemp -d "$cache/.tmp.XXXXXX"` に `git archive "$base" scripts/claude | tar -x` → `touch .complete` → `mv -T "$tmp" "$snap"`。**`rm -rf "$snap"` はしない**。`mv -T` が失敗したら（先に別の起動役が置いた）自分の一時の写しだけを消し、置かれた写しの `.complete` を見る。`.complete` の無いものが置き場所にあれば（この版の作り方では生じない）、消さずに 4 を返す
- 直接実行したとき（`bash reviewed-snapshot.sh <root>`）は関数を呼んで同じ終了コードで終わる。読み込んだとき（`. reviewed-snapshot.sh`）は関数を定義するだけ（`[[ "${BASH_SOURCE[0]}" == "$0" ]]` で分ける）

### 4-2. `.claude/hooks/reviewed-hook.sh`
達成すること: 写しの作り方を 4-1 に任せ、動き（基準なし・写しを作れないときは理由を出して作業ツリーのフック・それ以外は写し・いつも `python3 -I`）は変えない。
- `. "$(dirname "${BASH_SOURCE[0]}")/reviewed-snapshot.sh"` で読み込み、`snap=$(reviewed_snapshot "$root")` の戻り値で分ける（3・4 は今の 2 つの理由の文を出して `exec python3 -I "$root/$rel"`）。読み込めないときも理由を出して作業ツリー（フック全体を止めない。I599 R4 のまま）
- 引数の確かめ（`scripts/claude/hooks/*.py`・`..` を禁じる）と冒頭の説明は残し、説明に「写しの作り方の正は reviewed-snapshot.sh（I615）」を足す

### 4-3. `.claude/hooks/unreviewed.py`（入口の起動役 `run`）
達成すること: 入口を BASE の写しで動かし、入口・部品・レビュー役の定義を変えたときと写しを作れないときだけ止めて `!` を案内する。
- 終了コードを足す: `NEED_HUMAN = 75`（人に `!` で流してもらう。今の 3 は、`code-review.sh` の CI 待ちの時間切れなど入口の終了コードと重なるので使わない）。2（名前の誤り）・4（中で動いた）は変えない。冒頭の CLI の説明も直す
- `run` の流れ:
  1. 中で動いた・一覧に無い名前は今までどおり（4・2）
  2. `bash <root>/.claude/hooks/reviewed-snapshot.sh <root>` を引数の配列で起こし、写しの場所を受け取る（`GIT_` の環境変数を外す・時間の上限 60 秒）。0 以外なら 75 と理由（基準を求められない／写しを作れない）
  3. 写しに入口が無い（ブランチで足した入口）→ 75
  4. 部品（`parts(snap, name)`）と、ブランチで変わったファイル（`changed(root, base)`）が重なれば 75。案内: `この入口か部品（<名前…>）をブランチで変えているので、レビュー済みの版では流しません。新しい版をユーザーに ! bash scripts/claude/<名前> <引数> で流してもらい、その結果をこの周の結果にしてください`（引数は `shlex.join`）
  5. `os.chdir(root)` → `os.execvp("bash", ["bash", f"{snap}/scripts/claude/{name}", *args])`
- `parts(snap, name) -> set[str]`: 写しの `scripts/claude/<name>` から始め、読んだファイルの本文の、注釈の行（`#` で始まる）・表示の行（`echo`・`printf` で始まる）・行末の ` # …` を除いた部分に、写しの `scripts/claude/` の直下のファイル名、または写しの側ではなく作業ツリーの `.claude/agents/*.md` の名前（拡張子なし）が語として（前後が英数字・`.`・`-`・`_` でない）出てきたら部品に足す。`scripts/claude/` のファイルはさらにたどる（深さの上限なし・一度読んだものは読まない）。返す名前はリポジトリ相対（`scripts/claude/x.sh`・`.claude/agents/x.md`）。写しの本文だけを読む（入口を変えていなければ作業ツリーの入口は写しと同じ。変えていれば 4. で止まる）
- `changed(root, base) -> set[str]`: `_unreviewed_files` を `scripts/claude/` と `.claude/agents/` の 2 か所に広げたもの（BASE との差・未追跡・無視されるファイル）。今の `dirty` の CLI と `code-review.sh` の `gate_reviewed` は `scripts/claude/` だけのまま
- 判定の失敗（git の失敗・読めない）は 75（安全側）
- `route()`（見張りが使う付け替え）は変えない

### 4-4. `scripts/claude/fix-diagnosis-review.sh`
達成すること: 部品を、写しから動いたときも写しの側から読む。
- `:10` を `source "$(dirname "${BASH_SOURCE[0]}")/fix-review-lib.sh"` にする（`adversarial-review.sh:21-27`・`code-review.sh:1088` と同じ書き方）

### 4-5. `scripts/claude/hooks/sessionstart_context.py`（F2）
- `:200` を `[sys.executable, "-I", os.path.abspath(__file__), "--sync-primary"]` にする

### 4-6. `scripts/claude/hooks/pretooluse_guard.py`（git の更新を中で動く形で流すのを止める）
達成すること: I586 の「つないだ git の更新が中で途中まで書き換えて止まる」を、流す前に止める。
- 関数 `_git_update_inside(cmd) -> str | None` を足し、`main()` の `_route` の止める判定（`:2858-2859`）の直後に置く。`DANGER_OK=1` で始まるコマンドはこの判定にかけない（危険操作の承認の流れを変えない。R5）
- 判定:
  - 作業ツリーを書き換える git の操作 = `git` の命令（`_git_sub` で求める）が `am`・`apply`・`checkout`・`cherry-pick`・`merge`・`pull`・`rebase`・`reset`・`restore`・`revert`・`switch`・`stash`（`list`・`show` を除く）。コマンドの中にこれが 1 つも無ければ何もしない
  - 中で動く形 = 次のどれか: 引用符の外の `|`・`>`・`<`・`&`（`&&` を除く）・`(`・`)` がある／`$(` かバッククォートがある（引用符の中も含む・安全側）／`&&`・`||`・`;`・改行で区切った命令のどれかの最初の語が `git`・`gh`・`docker`・`docker-compose` でない（前置きの代入〔`X=1 git …`〕・`cd`・`timeout` などを含む）
  - 両方に当たれば止める（exit 2）。理由: `作業ツリーを書き換える git の操作（<命令>）を、ほかのコマンドとのつなぎ・振り向け・前置きつきで流すと、サンドボックスの中で動いて途中で止まります。git を単体で（git どうしのつなぎは可）流してください（docs/runbooks/danger-ops.md「外に出すコマンドの書き方」・I615）`
- 区切りの読み取りは既存の `_segments_ops`（引用符の中の `|`・`;` で区切らない）を使う
- `scripts/claude/tests/guard_must_stop_cases.txt` に節「git の更新を中で動く形で流す（I615・I586）」を足す: `git merge --ff-only origin/develop 2>&1 | tail -2`・`cd sub && git checkout main`・`X=1 git pull`・`git stash pop; ls`・`git reset --hard HEAD > /tmp/x`

### 4-7. `scripts/claude/tests/i599_cases.py`
達成すること: 新しい起動役の動き・写しの作り方・F2・見張りの判定を、一時のリポジトリ（本物は書き換えない）で確かめる。
- `make_repo` に `.claude/hooks/reviewed-snapshot.sh` の写しと、部品の関係のある小さな入口を足す: `code-review.sh`（`. "$(dirname "${BASH_SOURCE[0]}")/review-process-lib.sh"` と `REVIEWER_AGENT="code-reviewer"`）・`review-process-lib.sh`（`printf 'V1 %s|' "${BASH_SOURCE[0]}" "$@" > "$MARK"`）・`.claude/agents/code-reviewer.md`
- `snap_of` を新しい置き場所（`.cache/claude-reviewed-snapshots`）に直す
- TC-07〜TC-09（I599）を新しい動きに直し、I615 の TC を足す（中身は auto_test の TC-01〜TC-07）
- FG を新しいコードの置き換え元に直す（`fg_always_stop`・`fg_no_diff`・`fg_no_ignored`・`fg_base_ok` は `run` が `dirty` を使わなくなるので、`dirty` の CLI の確かめ〔TC-11 の `gate_reviewed`〕に向け直すか、I615 の FG に置き換える）

### 4-8. 文書
- `docs/runbooks/danger-ops.md`:
  - `:44`: 起動役は BASE の写し（`~/.cache/claude-reviewed-snapshots/<コミット>/`・作り方の正は `.claude/hooks/reviewed-snapshot.sh`）の入口を、作業フォルダを最上位にして動かす。流す入口・その部品（入口が読み込む・呼ぶ `scripts/claude/` の直下のファイル）・使うレビュー役の定義のどれかをブランチで変えていれば動かさずに終了コード 75。基準を求められない・写しを作れないときも 75。サンドボックスの中で動いたら 4
  - `:48`: 「`scripts/claude/` を変えたブランチでは、マージまで起動役も外で動かない」を、「起動役が 75 で止まり `! bash scripts/claude/<名前> …` を案内したときだけ、ユーザーにそのコマンドで流してもらい、その結果をその周の正式な結果にする（入口か部品を変えたブランチでは、その入口だけ周ごとに毎回）」に書き換える
  - `:51`: 写しの置き場所を新しい名前に。古い `~/.cache/claude-reviewed-hooks/` は使わなくなったので消してよい
  - 「外に出すコマンドの書き方」の後に: 作業ツリーを書き換える git の操作を中で動く形で流すと見張りが止める（I615）。途中で止まったときの戻しは、未コミットの変更を捨てる操作になるので、今までどおりユーザーに `!` で流してもらう
- `docs/runbooks/harness-audit.md:28`: 「レビュー前の中身があると止まる」を「`scripts/claude/` に変更があっても入口は写しで動き、入口か部品を変えると 75 で止まる」に直す

## 5. 実装手順（ステップ）
1. 写しの作り方（4-1）とフックの起動役（4-2）→ TC-04・TC-05・TC-08（既存の TC-12 を含む）。最初に置く（このセッションのフックも即座にこれで動く。保存の前に文法を確かめる → TC-08。保存の後に本物の起動役で見張りが動くことを確かめる → manual No.3）
2. 入口の起動役（4-3）と入口の直し（4-4）→ TC-01・TC-02・TC-03。ステップ 1 の後（4-1 を使う）
3. F2（4-5）→ TC-06。ステップ 1・2 と並行してよい
4. 見張り（4-6）→ TC-07。ステップ 1〜3 と並行してよい
5. テスト（4-7）は各ステップと一緒に足す
6. 文書（4-8）→ manual No.6。ステップ 2・4 の後
7. `/simplify` で整理し、push する（implement 段階）。`/simplify` の後に、変えたファイルを読むテストを流し直す

## 6. テスト計画
### 自動（`docs/tests/open/I615_auto_test.md`）
- テストレベル: シェル・Python の決定論テスト（`scripts/claude/tests/`・CI の `run-all.sh` が流す）。pytest・Jest・E2E は対象のコードが無いので対象外
- TC-01〜TC-07: `test_i599_unreviewed_scripts.sh`（`i599_cases.py`）。すべて失敗の注入つき
- TC-08: `bash -n` で 2 つの起動役の文法・`py_compile` で起動役と見張り
- 見張りを直したときの 4 つのテスト（`docs/runbooks/danger-ops.md:101`）: `test_guard_must_stop_cases.sh` は CI でも流れるのでゲートに書く。`test_guard_bash_oracle.sh`・`test_pretooluse_guard_matrix.sh`・`test_guard_corpus_diff.sh`（手元の作業記録を使う）は test-gate で Claude が流す（manual No.5）
- 決定論テストの対象の選び方（plan-writing-rules）: 写しで動くこと・部品の判定・写しを作れないとき止まること・写しを消さないこと・`-I`・見張りの判定は、壊れても黙って外で書き換えた中身が動く／人の手が戻る／途中で止まるだけで気づきにくく、被害が大きいのでテストにする。「写しの作り方が 1 か所」は、意図的な変更でしか崩れないのでテストにせず、読む（manual No.4）。手順書の文言もテストにしない（manual No.6）
### 手動（`docs/tests/open/I615_manual_test.md`・実施者はすべて Claude）
- No.1: このブランチ（`scripts/claude/` を変えている）で、本物の起動役で `bash scripts/claude/issue-source.sh path I615` が外で写しから動く
- No.2: 本物の起動役で `bash scripts/claude/fix-diagnosis-review.sh`（このブランチで変えた入口）が 75 で止まり、`!` を案内する
- No.3: 本物のフックの起動役で、見張りと他の 2 つのフックが新しい写しから動く
- No.4: 写しの作り方が 1 か所にあることを読む
- No.5: 見張りの 3 つの重いテスト
- No.6: 手順書を読む

## 7. ロールバック
- この PR を revert する（起動役・見張り・フック・テスト・文書だけ。データの変更なし）。起動役は revert で「レビュー前の中身があれば止める」に戻る。`~/.cache/claude-reviewed-snapshots/` は消してよい

## 8. Risk & 回避策
<!-- 処遇: 回避 か 受け入れ。受け入れの行は --route の照合で使う（I512） -->
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: `reviewed-hook.sh`・`reviewed-snapshot.sh` を壊すと、このセッションを含むすべてのフックが動かなくなる（見張りが止まり、Claude が何もできなくなる） | 保存の前に `bash -n` で文法を確かめる（TC-08）。読み込めない・写しを作れないときは今までどおり理由を出して作業ツリーのフックで動く（フックは止まらない）。保存の後に本物の起動役で見張りが動くことを確かめる（manual No.3）。止まったらユーザーが `! git restore .claude/hooks/reviewed-hook.sh .claude/hooks/reviewed-snapshot.sh` で戻す | 回避 |
| R2: 部品の判定が、変数で組み立てた名前・注釈や表示の行だけに書いた名前で呼ぶ部品を見落とすと、書き換えた部品が作業ツリーから読まれて外で動く | 入口は部品を写しの側（`$(dirname "${BASH_SOURCE[0]}")`）から読む（4-4 で最後の 1 か所を直した）ので、見落としても読むのは写しの部品。作業ツリーのスクリプトを動かすのは `code-review.sh` のゲートだけで、`gate_reviewed`（`dirty`）が止める。部品の判定は「新しい版も要るか」の判断で、守りの本体ではない | 回避 |
| R3: 部品の判定が広すぎると、関係しない変更で `!` が増える | 注釈・表示の行を除き、直下のファイル名だけをたどる（調査結果 8。見張り・関所を直しても、レビューの入口は自動で動く）。広すぎる側に崩れても今の動きより悪くならない（安全側） | 受け入れ |
| R4: 写しの入口は BASE の中身で動くので、ブランチで足した記録・計画書の新しい書き方を読めないことがある | その書き方を読む入口・部品を変えていれば 75 で新しい版を頼む（AC2）。変えていなければ、BASE の入口が今までと同じ書き方で読む | 回避 |
| R5: `DANGER_OK=1 git …` と前置きした危険操作は、中で動いて途中で止まりうるが、見張りの新しい判定にかけない | 危険操作の承認の流れ（`DANGER_OK=1` を付けると人の承認）を変えない。承認の画面で人が見る。I586 の事故はつなぎ・振り向けの形 | 受け入れ |
| R6: 見張りの新しい判定が、作業記録の普通のコマンドで新しい停止を増やす | `test_guard_corpus_diff.sh`（新しく確認・停止になったものが記録の 1% 以下）を test-gate で流す（manual No.5）。止まっても単独で流せば通り、理由の文で分かる | 回避 |
| R7: 写しの置き場所を変えるので、マージの後の最初の 1 回だけ、BASE ごとに写しを作り直す | 1 回の `git archive`（数 MB 以下・1 秒未満）。以降は `merge-base` の 1 回で動く | 受け入れ |
| R8: 写しが BASE ごとに増え続ける（I610 F4・R7） | 今までと同じ（置き場所が変わるだけ）。片付けは今の範囲外 | 受け入れ |
| R9: 入口の終了コードの 75 が、入口そのものの終了コードと重なる | 入口（16 本と部品）が書く終了コードは 0〜4・124（時間切れ）・130（中断）だけ（`(exit\|return) [0-9]+` の grep・2026-11-22）。`test-session.sh` は `claude -p` の終了コードをそのまま返す（0・1）。75 は起動役だけが使う | 回避 |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 外で動く入口は BASE の写しから動かし、フックの起動役と写しの作り方・置き場所を共有する
- 写しを作れないとき（基準なし・作成の失敗）は止めて `!` を案内する
- #600（git・docker の穴）は含めない。写しの仕組みは #600 でも使い回せる形にする（`reviewed-snapshot.sh` は `scripts/claude` の写しを返す関数で、呼び出し側を問わない）
- I610 の F1・F2 を同梱
- I586 の事例: 作業ツリーを書き換える git の操作をつないで流すのを見張りが止める。戻し方は変えない（Claude が「BP の観点で」任された判断）
- **2026-11-22 の /plan-issue でユーザーに確認して変えた**: 設計確認メモの「レビューの道具を直したブランチでは、古い版を自動で流し、新しい版もユーザーに `!` で流してもらう（両方）」は、敵対的レビューの周の上限（1 イシュー 2 周）を 1 回で使い切ることと、2 回目の実行が「前回からの差分」だけを見て何もレビューしないことが分かったため、「流す入口かその部品・レビュー役の定義を変えたときは、その入口だけ今までどおり古い版を流さず、新しい版をユーザーに `!` で流してもらい、それを正式な結果にする（周ごとに毎回）」に変えた（イシューの設計確認メモも同じに直す）

Claude が決めた（技術的な選択と理由）:
- 写しの作り方の正を新しい `.claude/hooks/reviewed-snapshot.sh`（bash の関数・直接実行で CLI）にする — フックの起動役は毎回のツール呼び出しで動くので、読み込み（`.`）で新しいプロセスを増やさない。入口の起動役（python）は CLI で呼ぶ。`.claude/hooks/` はサンドボックスから書けない
- 写しの置き場所を `claude-reviewed-snapshots` に変える — F1 の競合で `.complete` の無い写しが古い置き場所に残りうる。新しい作り方は置き場所を消さないので、古いものを引き継ぐと直らない
- 「新しい版が要る」の判定は、作業ツリー全体でなく入口ごとの部品で決める（ユーザーの回答「流す入口とその部品」）。部品の一覧は手で持たず、写しの入口の本文からたどる（一覧を書き忘れると黙って古い版で動くため。調査結果 8 で実際の呼び出しと一致した）
- 部品のたどりは注釈・表示の行を除く — 含めると `gate-check.sh`・見張りなどを直すたびに `code-review.sh` に `!` が要り、目的（人の手を減らす）に反する（調査結果 8）
- 「人に `!`」の終了コードを 3 から 75 に変える — `code-review.sh` の終了コード 3（CI 待ちの時間切れ）など、スキルが入口の終了コードで分ける箇所と重ならないため（R9）
- 新しい版を頼む手順はスキルに書かず、起動役の出力（案内の文）と `docs/runbooks/danger-ops.md` に置く — どの入口でも同じ動き（75 と案内）で、入口を呼ぶスキルが 6 つあり、写しを増やさない（イシューの実装対象の「`.claude/skills/`」は、ユーザーの見直しで「その入口だけ今までどおり」になり、スキルの手順を足す必要が無くなった）
- `docs/runbooks/workflow.md` は変えない — `!` の案内の記述が無い（grep で確かめた）
- 入口の起動役は作業フォルダをリポジトリの最上位にして、写しの入口を `bash <写し>/scripts/claude/<名前>` で動かす（スパイク 6 で成立）。写しの中のファイルを動かすだけで、写しを作業ツリーに広げない
- `fix-diagnosis-review.sh` の部品の読み方を直す — 写しから動いたときに作業ツリーの部品を読む唯一の箇所（調査結果 7）
- 見張りの判定は `DANGER_OK=1` の前置きを除外する（R5）。`$(` とバッククォートは引用符の中でも中で動く形とみなす（安全側。git の更新とその文字が同じコマンドにある形は少ない）
- 見張りの「外に出る最初の語」（git・gh・docker・docker-compose）は `.claude/settings.json` の `excludedCommands` と同じものを見張りの中に書く（起動役の形は 4-6 の判定にかからない〔git の更新を含まない〕）。設定を写すテストは作らない（plan-writing-rules「決定論テストの対象の選び方」）
- 新しい TC は既存の `i599_cases.py` に足す — 一時のリポジトリ・起動役の写し・見張りの呼び出しの土台がそのまま使え、I599 の TC-07〜TC-09 は意味が変わるので同じファイルで直す
- 一覧 `docs/reviews/backlog/I610.md` F4（写しが増え続ける）: 残す — R8。置き場所を変えるだけで量は今と同じ
- 一覧 `docs/reviews/backlog/I599.md` F5・F27（`route` の位置引数・引用符の中のワイルドカード）: 残す — `route` は変えない
- 一覧 `docs/reviews/backlog/I599.md` F6（判定の git の回数と時間）: 残す — `route`（見張り）の話で、起動役の `run` は見張りの時間の上限の外
- 一覧 `docs/reviews/backlog/I599.md` F9（中身がすべて無視される新しいフォルダ）: 残す — `dirty` の数え方の話。`run` は写しで動くので、無視されるファイルは外で動かない
- 一覧 `docs/reviews/backlog/I599.md` F26・F28・F29（TC-18）: 残す — TC-18 は変えない
- 一覧 `docs/reviews/backlog/I200.md` F5・`I463.md` F4・`I492.md` F4・`I454.md` F8・F9（見張りの別の判定）: 残す — 4-6 と別の箇所
- 一覧 `docs/reviews/backlog/I221.md` F10・`I219.md` F3〜F6・`I569.md` F3（`sessionstart_context.py` の表示）: 残す — F2（`-I`）と別の箇所
- 一覧 `docs/reviews/backlog/I221.md` F9・`I546.md` F5（`workflow.md`）・`I597.md` F2（`danger-ops.md` の控え）: 残す — 4-8 で触る節と別
- 一覧 `FILE=-` の行（I224 F9・I223 B1〜B4）: 残す — 関係しない
- 一覧のほかの実装対象（`.claude/hooks/reviewed-snapshot.sh`・`scripts/claude/fix-diagnosis-review.sh`・`scripts/claude/tests/guard_must_stop_cases.txt`・`docs/runbooks/harness-audit.md`）: 一覧の該当なし

要件適合性・業務ロジック: 受け入れ条件の範囲を超える仕様の追加は無い。マルチテナント・ステータス遷移は該当なし

セキュリティ・ベストプラクティス:
- 外で動く中身を「作業ツリーがまるごとレビュー済みのとき」から「いつも BASE の写し」に変える。外で動くのはレビュー済みの中身だけで、守りは今より狭くならない（作業ツリーの入口が外で動く道は、ユーザーの `!` だけ）。判定の失敗は 75（安全側）
- 入力: 起動役の名前の確かめ（一覧の名前だけ・`/`・`..` を禁じる）は変えない。引数は配列で渡す（shell を通さない）。案内の文の引数は `shlex.join`
- 写しの置き場所はサンドボックスから書けない（`~/.cache`）。作成は一時フォルダから `mv -T`（置き換えの途中の写しを見せない）
- 見張りの判定は止める側を足すだけ（確認・停止を外さない）
- バックエンド・フロントエンドのコード変更なし。依存の追加なし。bandit の対象は `.claude/hooks/unreviewed.py`・`scripts/claude/hooks/*.py`（重大度の基準は変えない: bandit は MEDIUM 以上・npm audit は high/critical）
- P3/P5/P8 影響なし（DB・外部 API・非同期・新しいインフラなし）。P6 影響なし（UI なし）。P9 影響なし（個人情報・テナントデータを扱わない）

設計品質: 判定の失敗はすべて安全側（入口は 75・フックは理由を出して作業ツリー〔I599 R4 のまま〕）。置き場所・基準・git の安全な `-c` は `reviewed-snapshot.sh` の 1 か所（`unreviewed.py` の `BASE_REF`・`GIT_SAFE_OPTS` は `dirty`・`route` のために残し、TC-14 が一致を確かめる）

Danger Ops（有無/手順/ロールバック）:
- 無（スクリプト・テスト・文書の変更。データの削除・GitHub の設定の変更なし）

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | 入口の起動役が作業ツリーの入口・部品を外で動かさない: TC-01（関係しない変更があっても写しの入口が動く・写しの場所が印に出る）・TC-02（入口・部品・レビュー役の定義の書き換えで 75・何も動かない）と、写しでなく作業ツリーを動かす写し・部品の判定を外した写しの FG |
| V2 | 1 | 読んで可 | 基準なし・写しを作れないときに作業ツリーへ倒れない: TC-03 と、失敗を「写しあり」に倒した FG |
| V3 | 1 | 読んで可 | 写しの作成がほかの写しを消さない: TC-05（置いてある写しの中の印が残る）と、`rm -rf "$snap"` を戻した FG |
| V4 | 2 | 読んで可 | TC-01・TC-02 の印が、本当に写しの入口・部品から書かれたものか（`${BASH_SOURCE[0]}` の場所で区別している）・置き換え元の文字列の変更で FG が「置き換えに失敗して合格」にならない（`assert old in src`） |
| V5 | 3 | 読んで可 | 見張りの判定が I586 の形（`git merge … 2>&1 \| tail -2`）とつなぎ・振り向け・前置き・`cd` の形を止め、単独・git どうしのつなぎ・読み取りの git・`DANGER_OK=1` の前置きを止めない: TC-07 と FG |
| V6 | 3 | 読んで可 | フックが起こす python がすべて `-I`: TC-06（`scripts/claude/hooks/*.py` の `sys.executable` で起こす箇所）と FG |

## 計画変更記録
- 2026-11-22 plan: 計画書の記載: [イシューの設計確認メモ「両方流す（古い版を自動・新しい版を `!`）」] → 採った方法: 入口か部品を変えたときは、その入口だけ新しい版を `!` で流し、それを正式な結果にする — 理由: 周の上限を 1 回で使い切る・2 回目は差分だけを見て何もレビューしない、が分かり、ユーザーに確かめて変えた（2026-11-22）。計画レビューのやり直し: 不要（計画レビューの前）
