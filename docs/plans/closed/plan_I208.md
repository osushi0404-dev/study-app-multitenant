# I208 計画書: 台帳の残りの振り分けと一覧の行をスクリプトが出すようにし、テストを実物の一覧に依存させない

## 基本情報
- **計画書ID**: plan_I208
- **関連イシュー**: #348
- **Draft PR**: #350
- **作成根拠資料**: docs/issues/open/I208.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I208_review.md
- **作成日**: 2026-10-27

## 1. 背景/目的
- 背景: I207 で、台帳の残りを「後続イシュー」と「軽い指摘の一覧」に分ける正規表現を retro の手順書に書き、Claude が流す形にした。初めて使った I207 の retro で、要約の中の `KIND=app` の文字に当たって F2 を取り違えた。一覧に書く `FILE=` は台帳の行に無いので FINDING 行を手でたどる。I207 のテスト D2・D3 は実物の記録・一覧の行数を確かめるので、一覧の決まりどおり行を消すと CI が落ちる
- 目的: ①振り分けと一覧の行を、台帳と同じスクリプト（`_LEDGER_PY`）が欄の値から決定論で出す ②一覧を使う通常の手順でテストが落ちないようにする

### 調査結果
- 原因の概要: 台帳の欄を読む仕組みがスクリプトにあるのに、振り分けだけ手順書の正規表現で行を文字列として読み直していた。そのため、欄と要約の区別・ファイル名の持ち方・止める判定との整合が手作業に残った。テストは使うたびに変わる実物のファイルを入力にしていた
- 詳細:
  1. 取り違え（I207 台帳 F2）: retro 4-0 の `grep -E 'KIND=app|SECURITY=yes|SEV=(Blocker|High|Medium) .*REPRO=yes'` は行全体に当てる。`docs/reviews/closed/I207_code_review_20261027_1942.md` の F2 は欄が `KIND=harness REPRO=no` だが、要約に `KIND=app` があるので後続イシュー側に当たる（このイシュー自身がその結果）
  2. ファイル名（I207 一覧 F5・F4）: `ledger_line()`（`scripts/claude/code-review.sh` 678 行）は `FILE=` を書かない。retro は FINDING 行をたどり、振り直した番号では別の指摘の FILE を拾う。見つからなければ `FILE=-` で、plan-issue の `grep -F "FILE=<パス>"` に当たらず残り続ける
  3. 前方一致（I207 一覧 F3）: plan-issue の `grep -rnF -e "FILE=<パス>"` は `FILE=<パス>.bak` やフォルダの下の行にも当たる
  4. guard（I207 一覧 F1）: 正規表現では guard の再現なしの High は一覧に落ちる。止める判定 `blocking()`（682 行）は guard では再現を問わない
  5. テスト（I207 一覧 F8）: `test_i202_ledger_cleanup.sh` の D2 は `docs/reviews/closed/I206_code_review_20261027_1815.md` の行を読み、D3 の `d3_bl` は `docs/reviews/backlog/I206.md` に F3〜F6 の 4 行があることを確かめる
- 台帳の行の形を変えたときの波及（grep で全件を確認した）:
  - 台帳の行（`LEDGER: F`）を読むのは `code-review.sh` の `_LEDGER_PY` と `review_mode`・`MAX_ID`（`^LEDGER: F[0-9]+` の番号だけ）だけ。`gate-check.sh`・`adversarial-review.sh`・フック・エージェントの定義・CI は台帳の行を読まない
  - テストで台帳の行の欄の並びに依存するのは、`test_i202_ledger_cleanup.sh` の R1（57 行 `RISK=up SECURITY=no \| 目印$`）・P1（543 行 `SECURITY=yes \| 残り$`）・`f2_same`（448 行。前の台帳 `l6_prev` の行と 1 字も違わない）。`test_i197_review_ledger.sh`・`test_i205_stop_criteria.sh` は前方の欄だけを見る（`SECURITY=` の後ろには依存しない）
  - retro 4-0 の文言を確かめるのは `test_i202` の D1 と `test_i205_stop_criteria.sh` の D4（`grep -h '^LEDGER: .*STATUS=open'` と「最優先」）。`test_i180`・`test_i114`・`test_i193` は 4-0 を見ない
- 一覧の確認（plan-issue の「台帳の残りの一覧」。実装対象 6 ファイルで grep）: `docs/reviews/backlog/I206.md` の F4（code-review.sh）・F5（test_i202）、`docs/reviews/backlog/I207.md` の F1・F3・F4・F5・F6・F7・F8 が当たった（扱いは 9）
- 環境の前提: `python3`・`bash`・`git` は既存の台帳とテストで使っている（新しい道具は無い）。`bash scripts/claude/*` は `.claude/settings.json` の allow にある
- ベースライン: `bash scripts/claude/tests/test_i202_ledger_cleanup.sh` → pass=128 fail=0（2026-10-27・develop 4e1ddcb）

## 2. 受け入れ条件
イシューの AC と同じ（番号を振る）。
- AC1: 振り分けがスクリプトの出力で決まり、要約に `KIND=app`・`SECURITY=yes`・`REPRO=yes` などの文字がある行でも欄の値だけで決まることを、失敗注入つきのハーネステストで固定している
- AC2: guard の Medium 以上の行は再現が無くても後続イシュー側になることを、失敗注入つきのハーネステストで固定している
- AC3: 一覧に書く行の `FILE=` が台帳の行から出る（振り直した番号でも、その指摘の FILE になる）ことを、ハーネステストで固定している。前の形（FILE の欄の無い）台帳の行も読める
- AC4: retro 4-0 が、スクリプトの出力を使う手順になっていて、手順書の正規表現・FINDING 行をたどる手作業が無い
- AC5: テストが実物の一覧の行数に依存せず、`docs/reviews/backlog/` の行を消しても CI が落ちない
- AC6: I207 の振り分けの既存の期待値（I206 の F1〜F6 と代表の行。guard の再現なしの High を除く）が変わらない
- AC7: 既存のハーネステスト（`bash scripts/claude/tests/run-all.sh`）・CI がすべて pass する

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra（ハーネス）: `scripts/claude/code-review.sh`・`scripts/claude/tests/test_i202_ledger_cleanup.sh`・`scripts/claude/tests/test_i205_stop_criteria.sh`・`.claude/skills/retro/SKILL.md`・`.claude/skills/plan-issue/SKILL.md`・`docs/runbooks/review-rules.md`・`docs/reviews/backlog/I207.md`
- `path_risk_trigger()` の集合（`.github/`・`.pre-commit-config.yaml`・`.secrets.baseline`・見張り・settings）には触れない

## 4. 変更点一覧（具体）

### 4.1 台帳の行に `FILE=` の欄を持たせる（AC3）
修正方針: 台帳の行が、その指摘のファイルを自分で持つ。新しい指摘のときは FINDING 行の `FILE=` を入れ、既にある指摘の書き直しでは前の値を変えない。前の形の行（欄が無い）は `FILE=-` として読む。

`scripts/claude/code-review.sh` の `_LEDGER_PY`:
- `LEDG`: `SECURITY=(yes|no)` の後ろに省略できる `(?: FILE=(\S+))?` を足す（欄の位置は `SECURITY=` の後ろ・要約の ` | ` の前）
  - 位置の理由: 前方の欄の並び（`SEV`〜`SECURITY`）を変えないので、前方の欄を見る既存の照合（i197・i205 と i202 の大半）がそのまま通る。`SECURITY=… \|` の隣り合わせに依存する 2 か所（R1・P1）だけを直す
- `read_ledger()`: 台帳の項目（リスト）の最後（添字 9）に `file or "-"` を足す
- `ledger_line()`: `… SECURITY={sec} FILE={file}` + 要約
- `update` の新しい指摘（`fresh`）: `FILE=` は `"-"` ならそのまま、ほかは `norm_path(path)`（`:行番号` を除いたリポジトリのルートからの相対パス。`kind_of` と同じ正規化）
- `merged()`: 引数に `path` を足す。結果の FILE は「前の値が `-` でなければ前の値、`-` なら今回の値」。3 か所の呼び出し（resolved・止めない中身の合流・既存の指摘の書き直し）すべてに渡す
  - 理由: 前の値を変えない（同じ指摘のファイルが周ごとに揺れない）。前の形の行（`-`）だけは、書き直しの機会に埋める
- 先頭の説明コメント（464 行）の台帳の行の形に `FILE=<パス|->` を足す

### 4.2 振り分けのモード `route`（AC1・AC2・AC3・AC6）
修正方針: 振り分けは欄の値だけを見る関数 `route_of(e)` で決める（要約は見ない）。台帳の残りの行ごとに、後続イシュー側か一覧側かと、一覧に貼る 1 行をスクリプトが出す。

`_LEDGER_PY` に足す:
```python
def route_reasons(e):
    # 後続イシューにする理由（欄の値だけで決める。要約は見ない・I208）。空なら一覧
    sev, st, scope, kind, stop, repro, sec = e[:7]
    r = []
    if blocking(e): r.append("止める指摘")
    if RANK[sev] >= 1 and repro == "yes": r.append("再現のある Medium 以上")
    if sec == "yes": r.append("SECURITY=yes")
    if kind == "app": r.append("アプリ本体")
    if kind == "guard" and RANK[sev] >= 1: r.append("guard の Medium 以上")
    return r
```
- モード `route <issue|backlog> <台帳のファイル>`: `STATUS=open` の行（止める指摘も含む。上限到達でユーザーが受け入れて残った止める指摘を落とさないため）を番号順に見て、
  - `issue`: 理由がある行を `- <番号> SEV=… REPRO=… KIND=… SECURITY=… FILE=… | <要約> | 後続イシューにする理由: <理由を「・」でつなぐ>` で出す
  - `backlog`: 理由が無い行を `- <番号> SEV=… REPRO=… KIND=… FILE=… | <要約> | 一覧に回した理由: <Low／再現なし>` で出す（理由は `SEV=Low` なら「Low」、`REPRO=no` なら「再現なし」。両方なら「Low／再現なし」）。この行がそのまま `docs/reviews/backlog/<起点>.md` に貼れる形
  - 1 つ目の引数が `issue`・`backlog` 以外なら exit 2
- シェルの関数 `ledger_route() { python3 -I -c "$_LEDGER_PY" route "$@"; }`

### 4.3 retro から 1 つのコマンドで呼べる入口（AC4）
修正方針: retro が記録を探す手作業も無くす。`code-review.sh` に、レビューを動かさずに振り分けだけを出す入口を足す。`bash scripts/claude/*` は allow にあるので、単体のコマンドで承認画面が出ない（手動 No.2 で確かめる）。

`scripts/claude/code-review.sh` の `REVIEW_LIB_SOURCE_ONLY` のガード（850 行）の直後、`review-process-lib.sh` を読む前に:
```bash
# I208: 台帳の残りの振り分け（retro 4-0 が使う）: --route <issue|backlog> <I###>。レビューは動かさない。
# 台帳のある最新のコードレビューの記録（ledger_records の最後）を読み、記録のパスは標準エラーに出す。記録が無ければ 2
if [ "${1:-}" = "--route" ]; then
  [ $# -eq 3 ] || { echo "Usage: $0 --route <issue|backlog> I###" >&2; exit 2; }
  cd "$(git rev-parse --show-toplevel)" || exit 2
  rec=$(ledger_records "$3" | tail -1)
  [ -n "$rec" ] || { echo "台帳のあるコードレビューの記録がありません: $3" >&2; exit 2; }
  echo "記録: $rec" >&2
  ledger_route "$2" "$rec"; exit $?
fi
```

### 4.4 retro の手順 4-0（AC4）
`.claude/skills/retro/SKILL.md` 4-0 を次の形にする:
- 拾う・振り分けるはスクリプト:
  - 後続イシュー側: `bash scripts/claude/code-review.sh --route issue $ARGUMENTS`
  - 一覧側: `bash scripts/claude/code-review.sh --route backlog $ARGUMENTS`
  - 判定は台帳の欄の値だけ（要約は見ない）。後続イシュー: 止める指摘・再現のある Medium 以上・`SECURITY=yes`・アプリ本体（`KIND=app`）・guard の Medium 以上（再現を問わない）。ほか（Low、または再現なし）は一覧。標準エラーの「記録: …」が読んだ記録。exit 2 は記録が無い・引数の誤り（止めて調べる）
- 後続イシュー側の扱い（1 件の後続イシューにまとめるか既存のイシューに同梱・「最優先」の決まり）は今のまま
- 一覧側は、出力の行をそのまま `docs/reviews/backlog/$ARGUMENTS.md` に貼る（無ければ作る。見出しは `docs/reviews/backlog/I206.md` と同じ形で、「記録:」に標準エラーの記録のパス）
- 消すもの: `grep -h '^LEDGER: .*STATUS=open'`・`grep -E`／`grep -vE` の 2 本・「`FILE=` は、その番号の FINDING 行…を新しい順に見て」の文

### 4.5 plan-issue の「台帳の残りの一覧」（I207 一覧 F3・F4）
`.claude/skills/plan-issue/SKILL.md` のコマンドを次にする（見る場所は今の 1 か所のまま。コマンドの当て方だけ）:
```bash
grep -rnF -e "FILE=<実装対象のパス1> |" -e "FILE=<実装対象のパス2> |" -e "FILE=- |" docs/reviews/backlog/ || true
```
- 後ろの ` |` で前方一致をやめる（F3）。`FILE=- |`（ファイルの分からない行）は毎回の計画で見る（F4: 残り続けない）

### 4.6 review-rules（文言の整合）
`docs/runbooks/review-rules.md` 70 行: 振り分けは「スクリプト（`code-review.sh --route`）が欄の値だけで決める」とし、後続イシューの条件に「止める指摘」「guard の Medium 以上（再現を問わない）」を足す

### 4.7 テスト（AC1〜AC6）
`scripts/claude/tests/test_i202_ledger_cleanup.sh` の I207 の節の D1〜D3 を書き換え、「I208」の節（Q1〜Q9）を足す。項目は auto_test の TC-01 の表。あわせて:
- R1・P1 の照合を `SECURITY=… FILE=… \| …` の形に直す（期待の意味は変えない）
- `l6_prev`・`p_app`・`p5_prev` の前の台帳は今の形（FILE の欄なし）のまま残す（前の形が読めることの確認を兼ねる）。`f2_same` は「F2 の行が前の行に ` FILE=-` を足した形と 1 字も違わない」に直す
- `test_i205_stop_criteria.sh` の D4・FG-D4: retro の拾うコマンドを `bash scripts/claude/code-review.sh --route` に変える

### 4.8 一覧の行の削除
`docs/reviews/backlog/I207.md` から、このイシューで直す F1・F3・F4・F5・F8 の行を消す（F6・F7 は残す。9 を参照）

## 5. 実装手順（ステップ）
未知リスクは無い（台帳の読み書きの形と、テストが依存する照合は調査結果で全件を確かめた）。
1. テストを先に書く（TDD）: 4.7 → TC-01・TC-02（今のコードで新しい項目が不合格になった件数を記録）
2. 4.1・4.2・4.3（`code-review.sh`）→ TC-01 の Q1〜Q9・既存の R・L・N・P、TC-02
3. 4.4・4.5・4.6（指示ファイル）→ TC-01 の D1・D3、TC-02 の i205 D4
4. 4.8（一覧の行を消す）→ TC-01 の D3、手動 No.3
- 依存: 2・3・4 は 1 の後。3 は 2 の後（retro のコマンドが本体にある前提）。4 は 2・3 の後

## 6. テスト計画
### 自動（docs/tests/open/I208_auto_test.md）
- テストのレベル: ハーネスの単体（`ledger_update`・`ledger_route`・`ledger_verdict` を `REVIEW_LIB_SOURCE_ONLY=1` で読み込む）・入口の通し（一時のリポジトリで `bash code-review.sh --route`）・指示ファイルの文言の確認。アプリのテスト（pytest・Jest・E2E）は非該当
- 再発防止: I207 の F2（要約の文字で取り違え）を Q5、F1（guard）を Q6、F5（振り直した番号の FILE）を Q3、F8（実物への依存）を D3 で固定する
- 否定・不在の項目にはすべて失敗注入（FG）を付ける
- 実物のファイルへの依存: D2・D3 は実物の記録・一覧の行数を読まない。実物の一覧は「どの行も決まった形か」だけを確かめ、行を全部消した写しでも合格することを確かめる
### 手動（docs/tests/open/I208_manual_test.md）
- No.1: 実物の I207 の記録で `--route` を流し、F2 が欄どおり一覧側に出る
- No.2: retro のコマンドが承認画面なしで通る（`check-permission-prompt.sh`）
- No.3: 行を消した後の一覧で、plan-issue の新しいコマンドが当たる行

## 7. ロールバック
- PR を revert する（ハーネスのスクリプト・テスト・文書・一覧ファイルだけ。データ・設定の変更は無い）。revert の後、このイシューの間に書かれた `FILE=` の欄のある台帳の行は、前の `LEDG` では全体一致しない（読まれない）ので、revert は周の途中のイシューが無いときに行う。revert の前に `grep -l '^LEDGER: .*STATUS=open.* FILE=' docs/reviews/*_code_review_*.md` で、open の記録（closed へ移していない）に新しい形の open の行が無いことを確かめる

## 8. Risk & 回避策
- 新しい形の台帳の行を `LEDG` が読めないと、前の周の止める指摘が消える（見逃し側） → 新しい形の行の読み戻し（Q4: 止める指摘の行が HIGH になる）と、通しの既存テスト（W・R の 2 周目以降）で固定。FG-Q4 で `FILE` の欄を読まない写しが不合格になることを確かめる
- 振り分けの条件の取りこぼし → 条件を `route_reasons()` の 1 か所に置き、I207 の期待値（Q7）と新しい条件（Q6）をテストで固定
- 止める指摘が残ったまま retro に来る（上限到達の受け入れ） → `route` は `STATUS=open` を全部見て、止める指摘は後続イシュー側に出す（Q7）
- `FILE=- |` の行が計画のたびに出て多くなる → ファイルの分からない指摘はブランチ全体の指摘で少ない（I206・I207 の一覧に 0 件）。多ければ棚卸し（I209）で扱える
- retro が出力の行を貼り違える → 出力は貼る形そのもの（手で組み立てない）

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ・解決方針）:
- 振り分けと一覧の行は、台帳を作るスクリプトが欄の値だけで出す。retro は出力を貼る・まとめるだけ
- guard は再現を問わず Medium 以上を後続イシュー。アプリ本体・ハーネスの基準（再現のある Medium 以上・`SECURITY=yes`・`KIND=app`）は I207 のまま
- 台帳の行に `FILE=` の欄（新しい指摘で FINDING 行の値・書き直しは前の値）。前の形の行も読める（足りなければ `FILE=-`）
- テストは写しで確かめ、実物の一覧は形だけ
- 止める判定（`blocking()`）・行で決める範囲・`gate-check.sh`・`path_risk_trigger()` は変えない。新しいファイルを作らない。`docs/reviews/backlog/I206.md` は直さない

Claude が決めた（技術的な選択と理由。要件・基本設計・UI/UX の仮定は無い）:
- `FILE=` の位置は `SECURITY=` の後ろ（仮定で決めた）。理由: 前方の欄の並びを変えないので、既存の照合への波及が 2 か所で済む（調査結果）
- 書き直しで前の値が `-` のときだけ今回の値で埋める（仮定で決めた）。理由: イシューの「前の値のまま」を保ちつつ、前の形の行を書き直しの機会に埋めると、一覧に `FILE=-` が残りにくい
- `FILE=` の値は `norm_path()` で揃える（仮定で決めた）。理由: `./x:12` などの書き方の違いで plan-issue の grep に当たらなくなるのを防ぐ。`kind_of` の判定と同じ正規化
- 振り分けの入力は `STATUS=open` の全部（止める指摘も含む）（仮定で決めた）。理由: I207 の retro は `STATUS=open` を全部拾っていた。`is_rest()` だけにすると、上限到達で受け入れた止める指摘が後続イシューから落ちる
- 入口は `code-review.sh --route <issue|backlog> <I###>`（仮定で決めた）。理由: allow の `bash scripts/claude/*` に当たる単体のコマンドで、パイプ・複合にしない。記録の探し方は本体の `ledger_records()`（台帳のある最新の記録）と同じにして、retro の手作業を減らす
- 出力を 2 つ（issue・backlog）に分ける（仮定で決めた）。理由: どちらも貼る・まとめる単位で、`grep`・`cut` の後処理が要らない
- plan-issue の grep に ` |` と `FILE=- |` を足す（仮定で決めた）。理由: I207 一覧の F3・F4 と同じ 1 行で直り、見る場所（1 か所）は変えない
- テストは新しいファイルを作らず `test_i202_ledger_cleanup.sh` の I207 の節を書き換え・「I208」の節を足す（仮定で決めた）。理由: 一時のリポジトリ・`ledger`・`broken`・`without` をそのまま使える
- 一覧 docs/reviews/backlog/I206.md F4: 残す — イシューのスコープで I206 の一覧は直さない（`changed_outside_records` の一時ファイルの置き場所で、振り分けと関係しない）
- 一覧 docs/reviews/backlog/I206.md F5: 残す — 同上（N10 の実時間への依存で、このイシューの D 節と関係しない）
- 一覧 docs/reviews/backlog/I207.md F1: 同梱 — guard の振り分け（設計確認メモ・4.2・Q6）
- 一覧 docs/reviews/backlog/I207.md F3: 同梱 — plan-issue の grep の前方一致（4.5。同じ 1 行の直し）
- 一覧 docs/reviews/backlog/I207.md F4: 同梱 — `FILE=-` の行を毎回の計画で見る（4.5）。あわせて台帳が FILE を持つので `FILE=-` 自体が減る（4.1）
- 一覧 docs/reviews/backlog/I207.md F5: 同梱 — 一覧の FILE を台帳の行から出す（4.1・4.2・Q3）
- 一覧 docs/reviews/backlog/I207.md F6: 残す — 止める中身への合流での要約の扱いで、台帳の更新の規則（I207 の範囲）の変更になる。振り分けと関係せず、Low・再現なし
- 一覧 docs/reviews/backlog/I207.md F7: 残す — 同上（合流の SCOPE。止める側に倒れる向きで害は小さい）
- 一覧 docs/reviews/backlog/I207.md F8: 同梱 — テストの実物への依存（4.7・D3）
- 高リスク判定: `scripts/claude/code-review.sh` は判定の仕組み（台帳）で、台帳の行の読み取りを変える。読めないと止める指摘が消える向き（8 の 1 つ目）があるので、Q4 と FG で固定する。`path_risk_trigger()` の集合には触れず、アプリの高リスクの条件（認証・認可・テナント境界・個人情報・決済など）にも当たらない → No の見立て（判定は plan-review）

セキュリティ・ベストプラクティス:
- セキュリティ影響なし（アプリのコード・認証認可・個人情報・依存ライブラリを変えない。bandit・npm audit の対象の変更なし）
- `SECURITY=yes` は重さに関係なく後続イシュー（C8。Q5・Q7 で固定）。欄の値だけで決めるので、要約の書き方で振り分けが変わらない
- 入力の扱い: 台帳の行は今までどおり `LEDG` の全体一致だけを読む。新しい `FILE` の欄は空白を含まない値（`\S+`）だけ。`--route` の引数は `issue`・`backlog` 以外を exit 2 で止め、記録は `ledger_records()`（固定の場所の glob）でだけ探す
- 公開リポジトリ: 一覧に書くのは要約とファイルの参照だけ（retro の既存の決まりどおり）

要件適合性: 受け入れ条件の範囲を超えた仕様の追加は無い（4.5 の 2 つの直しは一覧の F3・F4 の同梱で、見る場所は変えない）。マルチテナント・ステータス遷移は非該当

P3/P5/P8 影響なし（DB・外部 API・非同期処理・インフラの追加なし。依存関係ファイルの変更なし）。P6 影響なし（UI・データ量の懸念なし）。P9 影響なし（個人情報・未成年データ・テナントデータを扱わない）

設計品質: Python の部分は今の `_LEDGER_PY` の形（1 つの埋め込みスクリプト・モードで分ける）を保つ。振り分けの条件は `route_reasons()` の 1 か所。設定値・定数の追加は無い（重さの比較は既存の `RANK`）

Danger Ops（有無/手順/ロールバック）:
- 無（データ削除・破壊的変更・強制 push は無い。一覧の行の削除は記録の場所の通常の手順）

## 必ず確かめる項目
（高リスク判定が Yes になったときに敵対的レビューが使う。No なら使わない）
| 項目 | 確かめ方 |
|---|---|
| 1. 新しい形（`FILE=` あり）の台帳の行を `LEDG` が全体一致で読み、止める指摘が次の周でも止める | 読んで可（Q4・既存の通し W・R） |
| 2. 振り分けが欄の値だけで決まり、要約の文字で変わらない | 読んで可（Q5） |
| 3. `SECURITY=yes`・`KIND=app`・再現のある Medium 以上・guard の Medium 以上・止める指摘が一覧側に出ない | 読んで可（Q6・Q7） |
| 4. 振り直した番号の行の FILE が、その指摘の FINDING 行の FILE | 読んで可（Q3） |

## 計画変更記録
（実装中に計画と違うことをするときに書く）
- 1（計画レビュー 20261027_2245 の Warning 対応・2026-10-27）: Warning 1 は 4.3 の入口で引数の数を先に確かめて exit 2 にし、auto_test Q9 に引数不足の場合を足した。Warning 2 は 7 に revert の前の確認を 1 行足した。Info 2 件は対応不要（高リスクは No の見立て・手動テストの期待は一致）。方式・範囲・受け入れ条件は変えないので再レビューはしない
- 2（implement・2026-10-27）: 計画書の記載「`f2_same` は『F2 の行が前の行に ` FILE=-` を足した形と 1 字も違わない』に直す」。採った方法: `f2_same` に FILE の値を引数で渡す（既定 `-`）。理由: P6 では止めない中身の書き直し（`FILE=scripts/claude/a.sh`）が前の形の `-` を埋める（4.1 の規則どおり）ので、`-` 固定では合わない。あわせて FG-P1〜P3 の置き換え前の文字列に `merged()` の新しい引数を足した（期待値は同じ）。計画レビューのやり直し: 不要（テストの比べ方の細部だけ）
- 3（implement の /simplify・2026-10-27）: 計画書の記載「4.3 の入口は `ledger_records "$3" | tail -1`」。採った方法: 同じ式が `review_mode` にもあるので `latest_ledger_record()` に 1 つにまとめ、両方で使う（FG-Q9 はこの関数を壊す形に直した）。あわせて 4.2 の `route` は、一覧に回す理由が空になる行（今の条件では起きない）が出たら exit 2 で止める（`route_reasons()` の条件を将来変えたときに黙って一覧に落とさない）。`route_reasons()` は使う欄だけを取り出す。理由: 記録の決め方を 1 か所にし、振り分けを止める側に倒す。出力・判定は変わらない（TC-01・TC-02 は同じ結果）。計画レビューのやり直し: 不要（内部の整理と止める側の守りで、方式・範囲・受け入れ条件は変えない）

## レビュー結果
- [20261027_2245 判定: ✅ 完了](../../reviews/closed/I208_plan_review_20261027_2245.md)
