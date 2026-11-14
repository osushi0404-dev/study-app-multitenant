# I512 計画書: 計画で受け入れた残余リスクを、後続イシュー・最優先から外して一覧へ回す

## 基本情報
- **計画書ID**: plan_I512
- **関連イシュー**: #512
- **Draft PR**: #514
- **作成根拠資料**: docs/issues/open/I512.md（GitHub #512 の本文の写し）
- **実装後評価**: docs/reviews/open/I512_review.md
- **作成日**: 2026-11-14

## 1. 背景/目的
- I430 の retro で、計画書で受け入れると書いた残余リスク 3 件（F1〜F3・Medium・再現なし）が、`code-review.sh --route issue` で後続イシューに回り、F1・F2 は `SECURITY=yes` のため「次のハーネスの作業で最優先」になった。見張り・安全装置のイシューは脅威モデルが事故なので残余リスクを受け入れることが多く、この形が毎回出て連鎖が止まらない
- 目的: 計画書の決まった場所で受け入れた残余リスク（Medium 以下・再現なし）は、レビュー役の目印と計画書の照合（決定論）で一覧（`docs/reviews/backlog/`）に回す。止める判定（STOP）は変えない。I430 の F1〜F3 は受け入れのまま一覧に回す

## 調査結果

### 原因の概要
振り分けのスクリプトは台帳の欄（重さ・再現・セキュリティ・種類）だけで後続イシューか一覧かを決めている。台帳に「計画で受け入れ済みか」の欄が無いので、受け入れた残余リスクも、受け入れていない穴と同じく後続イシュー・最優先になる。さらに、計画書の「受け入れる」の記述が決まった場所に無いので、機械で照合できない。

### 詳細な原因分析
1. code-reviewer は FINDING 行（`.claude/agents/code-reviewer.md:220`）に、重さ・セキュリティ・止める条件だけを書く。受け入れ済みかを書く欄が無い
2. `code-review.sh` の台帳（`_LEDGER_PY` の `FIND`・`LEDG`・657・660 行）にも、その欄が無い
3. `route_reasons()`（759〜773 行）は「`SECURITY=yes` で Medium 以上」「guard の Medium 以上」を後続イシューにする。I430 の F1〜F3 は KIND=guard・Medium・再現なしなので必ず後続イシューになり、F1・F2 は理由に `SECURITY=yes` が付く
4. retro 4-0（`.claude/skills/retro/SKILL.md:163`）は、理由に `SECURITY=yes` がある行を「最優先」にする
5. plan_I430 の受け入れは 4-1 の表・4-2 の本文・8 の R2 に散らばっている（F1 は R2、F2・F3 は 4-1 を根拠にしている）

### 確かめたこと（2026-11-14）
- `bash scripts/claude/code-review.sh --route issue I430`: F1（理由 `SECURITY=yes・guard の Medium 以上`）・F2（同じ）・F3（`guard の Medium 以上`）の 3 行が出る
- 台帳の行の形を読むのは `scripts/claude/code-review.sh` だけ（`grep -rln "LEDGER\|--route"` で、ほかはテストと retro・review-rules の文書だけ）。`gate-check.sh`・`adversarial-review.sh` は台帳の行を読まない
- 振り分けのテストは `scripts/claude/tests/test_i202_ledger_cleanup.sh` の Q1〜Q10（`ledger_route` を関数だけ読み込んで呼ぶ）。CI は `scripts/claude/tests/run-all.sh` が `test_*.sh` を全部流す（`.github/workflows/ci.yml:203`）
- ベースライン: `bash scripts/claude/tests/test_i202_ledger_cleanup.sh` pass=163 fail=0（変更前）
- 環境: `python3`・`bash`・`git` はホストにある（上のテストが通る）。新しい道具は要らない

## 2. 受け入れ条件
- AC1: 計画書の「## 8. Risk & 回避策」で処遇が `受け入れ` の R 番号を `ACCEPTED=` に持つ、Medium 以下かつ `REPRO=no` の台帳の行が、`code-review.sh --route issue` で後続イシューに出ず、`--route backlog` に「計画で受け入れ（R<番号>）」の理由つきで出る（`SECURITY=yes`・`KIND=guard` の行も含む。決定論のテスト・失敗の注入つき）
- AC2: 目印の無い Medium 以上・`SECURITY=yes` の行は、今までどおり後続イシュー・最優先になる（テストで確かめる）
- AC3: 目印があっても High 以上か `REPRO=yes` の行は、今までどおり後続イシューになる（テストで確かめる）
- AC4: 止める判定（STOP）は目印で変わらない（テストで確かめる）
- AC5: 目印があっても、計画書が無い・節が無い・その R 番号の行が無い・処遇が `受け入れ` でないときは、今までどおり後続イシューに振り分けられる（照合の失敗の注入つきのテスト）
- AC6: 前の形（`ACCEPTED=` の欄の無い）の FINDING・LEDGER 行も今までどおり読め、振り分けが変わらない（テストで確かめる）
- AC7: `docs/plans/templates/plan_template.md` の「## 8. Risk & 回避策」の表に「処遇」の列がある
- AC8: `docs/reviews/backlog/I430.md` に F1〜F3 の行がある
- 同梱（一覧から・AC の外。理由は §9）: 一覧の I480 F1（`--route backlog` の行に `SECURITY=` の欄を足す・`FILE=… |` の並びは変えない＝R4・`test_i202_ledger_cleanup.sh` の D3）と I208 F3（`--route` の第 3 引数を `^I[0-9]+$` で確かめる・TC-05）

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra（ハーネス）:
  | ファイル | 種類 | 変更 |
  |---|---|---|
  | `scripts/claude/code-review.sh` | harness（判定の仕組み） | FINDING・LEDGER の `ACCEPTED=` の欄・計画書との照合・`route_reasons()`・`--route` の入口 |
  | `.claude/agents/code-reviewer.md` | harness | `ACCEPTED=R<番号>` を付ける決まり |
  | `scripts/claude/tests/test_i512_accepted_risk.sh`（新規） | harness | AC1〜AC6 の決定論テスト |
  | `scripts/claude/tests/test_i202_ledger_cleanup.sh` | harness | 一覧の行に `SECURITY=` を足したことに合わせて Q3・Q8・Q9 の期待の行と `BL_FORM` を直す（一覧の I480 F1 の同梱） |
  | `docs/plans/templates/plan_template.md` | harness | 8 の表に「処遇」の列 |
  | `.claude/skills/retro/SKILL.md` | harness | 4-0 に目印の扱い |
  | `docs/runbooks/review-rules.md` | harness | 「検証の全体設計」の振り分けの要約に目印の扱い |
  | `docs/reviews/backlog/I430.md` | harness（記録） | F1〜F3 の行を足す |
  | `docs/reviews/backlog/I480.md`・`docs/reviews/backlog/I208.md` | harness（記録） | 同梱して直した行（I480 F1・I208 F3）を消す（行が無くなったファイルは消す） |
- 依存関係ファイルの変更: なし

## 4. 変更点一覧（具体）

### 修正アプローチ
レビュー役が「この指摘は計画書の R<番号> で受け入れたもの」という目印を FINDING 行に書き、台帳にそのまま残す。retro が使う振り分け（`--route`）の時点で、スクリプトがそのイシューの計画書の「## 8. Risk & 回避策」の表を読み、その R 番号の行があって処遇が `受け入れ` のときだけ目印を有効にする（照合できなければ目印を無視する＝今までどおり）。目印が有効で、かつ Medium 以下・再現なし・アプリ本体でない行は、`SECURITY=yes`・`guard の Medium 以上` の理由を外して一覧に回す。止める判定（`blocking()`）は目印を読まない。

照合を台帳を書く時（review-gate）ではなく振り分けの時（retro）にする理由: 目印を使うのは振り分けだけなので、使う時点の計画書で 1 回だけ確かめれば足りる（2 か所で確かめると食い違いの元になる）。台帳には、レビュー役が書いたままの目印を残す。

### 4-1. 計画書の受け入れの欄（`docs/plans/templates/plan_template.md`）
修正方針: 受け入れの記述を 1 か所（8 の表）に集め、機械で読める形にする。
- 「## 8. Risk & 回避策」の `-` を、次の表に置き換える（コメントで書き方を添える）:
  ```markdown
  ## 8. Risk & 回避策
  <!--
    処遇: 回避（計画で手を打つ）か 受け入れ（残余リスクとして受け入れる）。
    受け入れの行は、retro の振り分け（scripts/claude/code-review.sh --route）が、レビュー役の目印 ACCEPTED=R<番号> と照らし合わせて、
    Medium 以下・再現なしの指摘を後続イシューにせず一覧（docs/reviews/backlog/）へ回す（止める判定は変えない）。
    受け入れは、ほかの節（4 の表・本文など）ではなく、この表の行に書く。リスクの欄は R<番号>: で始める。
  -->
  | リスク | 回避策 | 処遇 |
  |---|---|---|
  | R1: | | 回避 |
  ```
- 読み方（4-2 の `accepted_risks()`）: 「## 8.」で始まる見出しの行から次の「## 」の見出しの行までの、表の行（`|` で始まる行）のうち、最初のセルが `R<数字>` の後に `:`・`：` が続く形で始まり、最後のセル（前後の空白を除く）が `受け入れ` と完全に一致するもの。その R 番号の集合を返す

### 4-2. `scripts/claude/code-review.sh`（`_LEDGER_PY` と `--route` の入口）
修正方針: 目印の欄を足し（無い前の形の行も読む）、振り分けで計画書と照らし合わせる。止める判定・台帳の合否・敵対的レビューの判定は変えない。
1. `FIND`（657 行）: `STOP=(\S+)(?: RISK=(up))?` の後ろに `(?: ACCEPTED=(R[0-9]+))?` を足す。`ACCEPTED=` の値が `R<数字>` でない（`ACCEPTED=`・`ACCEPTED=x`）行は今までどおり形の崩れ（exit 2）
2. `read_findings()`（721 行）のコメントの並びに ACCEPTED を足す。`parse` モード（778 行）は `g[:7] + g[9:]` にする（RISK と ACCEPTED の欄は出さず、列は今までどおり）
3. `LEDG`（660 行）: `(?: RISK=(up|-))?` の後ろに `(?: ACCEPTED=(R[0-9]+))?` を足す（KIND の欄のある形の中だけ）。`read_ledger()`（731 行）は台帳の項目の 11 番目（`e[10]`）に `accepted or "-"` を入れる
4. `ledger_line()`（736 行）: `RISK={risk}` の後ろに、目印があるときだけ ` ACCEPTED={acc}` を書く（`-` のときは書かない。目印の無い行は今までと 1 文字も変わらない）
5. `update` モード: FINDING 行の目印を新しい台帳の項目の `e[10]` に入れる。`merged()`（821 行）の目印は「今回の行の値」（同じ番号の書き直しでは最新のレビュー役の判断を使う。書き直しで目印を外せば `-` になり、振り分けは後続イシュー側＝安全側に倒れる）
6. 新しい関数 `accepted_risks(plan_path)`: 4-1 の読み方で R 番号の集合を返す。パスが空・ファイルが無い・読めない・節が無いときは空の集合
7. 新しい関数 `accepted_why_not(e, acc_set)`: 目印が効かない理由を返す（効くなら空）。効くのは `e[10] in acc_set and RANK[e[0]] <= 1 and e[5] == "no" and e[3] != "app"` のとき
8. `route_reasons(e)` は変えない（共有の関数に旗を足さない・/simplify で決定）。`route` モードで、目印が効く行（`ok`）だけ、理由の一覧から `ACCEPTED_DROPS`（「`SECURITY=yes`」「`guard の Medium 以上`」）を除く。「止める指摘」「再現のある Medium 以上」「アプリ本体」は今までどおり（目印が効く行では、もともとこの 3 つに当たらない＝効く条件で除いている）。アプリ本体を効く条件から除くのは、アプリ本体の Medium・`SECURITY=yes` の行の理由から `SECURITY=yes` が消えて最優先から外れるのを防ぐため（アプリ本体の行は目印に関係なく後続イシュー）
9. `route` モード: 引数を `route <issue|backlog> <台帳> [<計画書>]` にする（計画書の引数が無い・空なら目印は効かない＝今までどおり。既存のテストの呼び方はそのまま動く）。行ごとに `why_not = accepted_why_not(e, acc_set)`（目印の無い行は「目印なし」）を 1 回だけ求め、空なら `ok`
   - 一覧の行（backlog）: `- {fid} SEV= REPRO= KIND= SECURITY={e[6]} FILE= | 要約 | 一覧に回した理由: <Low／再現なし／計画で受け入れ（R<番号>）>`（`ok` のとき理由の最後に `計画で受け入れ（R<番号>）` を `／` でつなぐ）。`SECURITY=` を足すのは一覧の I480 F1 の同梱（受け入れた `SECURITY=yes` の行が一覧に来るので、一覧の中でもセキュリティの指摘と分かるように）。`FILE=… |` の並びは変えない（`/plan-issue` の `grep -F "FILE=<パス> |"` がそのまま当たる）
   - 目印があるのに `ok` でない open の行は、標準エラーに `目印を使わない: F<n> ACCEPTED=R<n>（<理由: 計画書に無い／処遇が受け入れでない／High 以上／再現あり／アプリ本体>）` を 1 行出す（振り分けは今までどおり）
10. `--route` の入口（957〜964 行）:
    - 第 3 引数が `^I[0-9]+$` でなければ exit 2（一覧の I208 F3 の同梱。計画書のパスを組み立てるので、`../` や glob を通さない）
    - 計画書は `docs/plans/open/plan_$3.md`、無ければ `docs/plans/closed/plan_$3.md`、どちらも無ければ空。標準エラーに `計画書: <パス|なし>` を出す
    - `ledger_route "$2" "$rec" "$plan"` を呼ぶ

### 4-3. `.claude/agents/code-reviewer.md`
修正方針: レビュー役が目印を付ける条件と書式を決める。
- 「止める指摘の書き方」の後に「計画で受け入れた残余リスク（I512）」の小節を足す: 計画書の「## 8. Risk & 回避策」の表で処遇が `受け入れ` の R 番号の行と同じ中身の指摘には、FINDING 行に `ACCEPTED=R<番号>` を付ける。付けても止める判定は変わらない。振り分けでは、スクリプトが計画書と照らし合わせ、Medium 以下・再現なし・アプリ本体でない指摘だけを一覧に回す。ほかの節（4 の表・本文など）に書いた受け入れには付けない
- 出力フォーマットの FINDING 行（220 行）に `[ ACCEPTED=R<番号>]` を `[ RISK=up]` の後ろに足す。欄の説明（236 行の後）に `ACCEPTED=R<番号>`（任意・`RISK=up` の後ろ、無ければ `STOP=` の後ろに半角の空白 1 つで続ける。`R<数字>` 以外の値は形の崩れ）を足す

### 4-4. `.claude/skills/retro/SKILL.md` 4-0（154・158・162・163 行）
修正方針: 振り分けの説明を新しい決まりに合わせる。
- 後続イシューの条件（154 行）の後ろに「ただし、計画書の『## 8. Risk & 回避策』で処遇が `受け入れ` の R 番号の目印（`ACCEPTED=R<番号>`）があり、Medium 以下・再現なし・アプリ本体でない行は、`SECURITY=yes`・guard の Medium 以上でも一覧（I512。照合はスクリプトが計画書で行い、合わなければ今までどおり。標準エラーに `目印を使わない:` が出る）」を足す
- 一覧の行の形（162 行）を `- <番号> SEV=<…> REPRO=<…> KIND=<…> SECURITY=<…> FILE=<パス|-> | <要約> | 一覧に回した理由: <Low／再現なし／計画で受け入れ（R<番号>）>` にする
- 最優先の条件（163 行）は文言を変えない（理由に `SECURITY=yes` が付かなくなるので、受け入れた行は自然に最優先にならない）。末尾に「（計画で受け入れた行は一覧に回るので、ここに来ない・I512）」を足す

### 4-5. `docs/runbooks/review-rules.md`「検証の全体設計」（70 行）
- 振り分けの要約の後に「計画書の『## 8. Risk & 回避策』で処遇が `受け入れ` の R 番号の目印（`ACCEPTED=R<番号>`・code-reviewer が付け、`--route` が計画書と照合する）があり、Medium 以下・再現なし・アプリ本体でない行は一覧に回す（I512）。目印は振り分けだけに効き、止める判定には効かない」を足す

### 4-6. `docs/reviews/backlog/I430.md`
- F1〜F3 の行を足す（新しい一覧の行の形・`SECURITY=` つき）。plan_I430 は 8 の表に処遇の列が無く、F2・F3 の根拠は 4-1 なので、`--route` の照合には乗らない。過去の計画書は書き直さず、この 3 行だけ手で足す:
  - `- F1 SEV=Medium REPRO=no KIND=guard SECURITY=yes FILE=.claude/settings.json | <台帳の要約のまま> | 一覧に回した理由: 再現なし／計画で受け入れ（plan_I430 の R2）`
  - `- F2 SEV=Medium REPRO=no KIND=guard SECURITY=yes FILE=.claude/settings.json | <台帳の要約のまま> | 一覧に回した理由: 再現なし／計画で受け入れ（plan_I430 の 4-1）`
  - `- F3 SEV=Medium REPRO=no KIND=guard SECURITY=no FILE=.claude/settings.json | <台帳の要約のまま> | 一覧に回した理由: 再現なし／計画で受け入れ（plan_I430 の 4-1）`
- 見出しの「一覧に回した決まり」の行に「F1〜F3 は I512 で受け入れのまま一覧へ（締めない・grill-me で確定）」を足す

### 4-7. テスト（`scripts/claude/tests/test_i512_accepted_risk.sh` 新規・`test_i202_ledger_cleanup.sh` の追従）
- 新しいテストは `test_i202_ledger_cleanup.sh` と同じく、`code-review.sh` を関数だけ読み込み（`REVIEW_LIB_SOURCE_ONLY=1`）、一時のディレクトリの台帳と計画書で `ledger_route`・`ledger_update`・`ledger_verdict`・`parse_findings` を呼ぶ。失敗の注入は、テストの中で `code-review.sh` の写しを壊して流す（本物は書き換えない）。中身は auto_test の TC-01〜TC-05
- `test_i202_ledger_cleanup.sh`: 一覧の行に `SECURITY=` が入るので、Q3（691 行）・Q8（741〜743 行）・Q9（756 行）の期待の行に `SECURITY=no` を足し、`BL_FORM`（651 行）を `KIND=(app|harness|guard) (SECURITY=(yes|no) )?FILE=` にする（今ある一覧のファイルの行は `SECURITY=` が無いので省略を許す）

### 4-8. 一覧の同梱分の後片付け
- `docs/reviews/backlog/I480.md` の F1・`docs/reviews/backlog/I208.md` の F3 の行を消す（実装で直したら。行が無くなったファイルは消す）

## 5. 実装手順（ステップ）
1. `code-review.sh` の欄の追加（4-2 の 1〜5）と、新しいテストの TC-04（前の形の行・形の崩れ）と TC-03（止める判定が変わらない）→ TC-03・TC-04 参照。未知のリスク（正規表現の欄を足すことで前の形の行の読み方が変わる）を先に潰す
2. 照合と振り分け（4-2 の 6〜10）と、TC-01・TC-02・TC-05・`test_i202_ledger_cleanup.sh` の追従（4-7）→ TC-01・TC-02・TC-05・TC-06 参照。ステップ 1 が前提
3. 計画書の雛形・レビュー役の指示・retro・review-rules（4-1・4-3・4-4・4-5）→ manual_test No.1 参照。ステップ 2 と並行してよい
4. 一覧（4-6・4-8）→ manual_test No.4 参照。ステップ 2 の後（一覧の行の形をスクリプトの出力に合わせる）
5. `/simplify` で整理し、push する（implement 段階）

## 6. テスト計画
### 自動（`docs/tests/open/I512_auto_test.md`）
- テストレベル: シェルの決定論テスト（`scripts/claude/tests/`）。pytest・Jest・E2E は対象のコードが無いので対象外。CI の `scripts/claude/tests/run-all.sh` が全部流す
- TC-01（AC1）: 目印が効く行が一覧に回り、理由に「計画で受け入れ（R<番号>）」が付く（`SECURITY=yes`・guard を含む）
- TC-02（AC2・AC3）: 目印の無い行・High 以上・再現あり・アプリ本体の行は今までどおり
- TC-03（AC4）: 止める判定（`ledger_verdict`・`ledger_blocking`）が目印で変わらない
- TC-04（AC6）: 前の形の FINDING・LEDGER 行が今までどおり読め、`parse` の列が変わらない・目印の無い行の LEDGER 行が 1 文字も変わらない・`ACCEPTED=x` は形の崩れ
- TC-05（AC5）: 照合の失敗（計画書なし・節なし・行なし・処遇違い・別の R 番号）では後続イシュー
- TC-06（既存の回帰）: `test_i202_ledger_cleanup.sh`・`test_i205_stop_criteria.sh` が exit 0
- AC8（I430 の一覧の F1〜F3）は CI で毎回確かめない（一覧は直したら行を消す運用で、毎回確かめると将来の罠になる・下の「対象の選び方」）。manual_test No.4 で 1 回確かめる。一覧の行の形は既存の `test_i202_ledger_cleanup.sh` の D3 が全一覧に対して確かめる
- 決定論テストの対象の選び方（plan-writing-rules）: 照合の失敗で安全側に倒れること（TC-05）と、止める判定が変わらないこと（TC-03）は、壊れても気づきにくく被害が大きい（受け入れていない穴が黙って一覧に落ちる）のでテストにする。雛形・手順書の文言はテストにしない（意図的な変更でしか消えない・manual_test No.1 で読む）
### 手動（`docs/tests/open/I512_manual_test.md`・実施者はすべて Claude）
- No.1: 雛形・code-reviewer・retro・review-rules の説明が `route_reasons()`・`accepted_risks()` の実装と食い違わない（読んで突き合わせる）
- No.2: この計画書（plan_I512）の 8 の表を `accepted_risks()` で読むと `R3` が出る（新しい形で書いた計画書が実際に読める）
- No.3: 本物の入口 `bash scripts/claude/code-review.sh --route issue I430`・`--route backlog I430` が動き、標準エラーに `計画書: docs/plans/closed/plan_I430.md` が出る（I430 は目印の無い台帳なので振り分けは今までどおり）

## 7. ロールバック
- このブランチの PR を revert する（スクリプト・文書・テストだけ。データの変更なし）。台帳の `ACCEPTED=` の欄は前のスクリプトでは読めないが、前のスクリプトの `LEDG` は fullmatch なので、目印のある行は読み飛ばされる（その行は振り分けにも出ない）。revert するときは、目印のある記録が develop にあるかを `grep -rl ' ACCEPTED=R' docs/reviews/` で確かめ、あれば目印を消してから revert する

## 8. Risk & 回避策
<!-- 処遇: 回避 か 受け入れ。受け入れの行は --route の照合で使う（I512 で足した形） -->
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: 正規表現に欄を足して、前の形の FINDING・LEDGER 行の読み方が変わり、止める判定が変わる | 欄は省略できる形で足し、目印の無い行の LEDGER 行は 1 文字も変えない。TC-03・TC-04 と既存の `test_i202_ledger_cleanup.sh`・`test_i205_stop_criteria.sh`（TC-06）で固定する | 回避 |
| R2: レビュー役が受け入れていない穴に目印を付け、一覧に落ちる | 目印は計画書の 8 の表の `受け入れ` の行と照合し、合わなければ無視する（TC-05）。効くのは Medium 以下・再現なし・アプリ本体でない行だけ（TC-02）。止める判定には効かない（TC-03） | 回避 |
| R3: 計画書の書き手が、本当は締めるべき穴を「受け入れ」と書き、一覧に回る | 計画は計画レビュー（plan-reviewer）を通る。一覧の行は、そのファイルを触るイシューの計画で見直す。後のレビューで再現ありや High 以上で出直せば、目印は効かず後続イシューに戻る（TC-02）。脅威モデル（事故）の範囲では受け入れる | 受け入れ |
| R4: 一覧の行に `SECURITY=` を足して、`/plan-issue` の拾い方（`grep -F "FILE=<パス> |"`）が当たらなくなる | `FILE=… |` の並びは変えず、`SECURITY=` は `KIND=` と `FILE=` の間に入れる（`test_i202_ledger_cleanup.sh` の D3 で固定） | 回避 |
| R5: 目印のある記録が develop に入った後に revert すると、前のスクリプトがその行を読み飛ばす | 7. ロールバックの手順で目印を消してから revert する | 回避 |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 目印が効くのは Medium 以下かつ `REPRO=no` の行だけ。High 以上・再現ありは今までどおり。効く行では `SECURITY=yes`・guard の Medium 以上の理由も外す。止める判定は目印を見ない
- 受け入れは計画書の「## 8. Risk & 回避策」の表の「処遇」の列に `受け入れ` と書いた R 番号の行だけ。目印は `ACCEPTED=R<番号>`。スクリプトが計画書と照合し、合わなければ目印を捨てる（fail-closed）。LEDGER 行にも欄を持たせる
- 受け入れ後に穴と分かったときは、一覧の理由「計画で受け入れ（R<番号>）」と今の「台帳の残りの一覧」で拾う。定期の見直しの場は作らない
- I430 の F1〜F3 は締めず、`docs/reviews/backlog/I430.md` に手で足す

Claude が決めた（技術的な選択と理由）:
- アプリ本体（`KIND=app`）の行には目印を効かせない — アプリ本体は「指摘 0 が目標」で後続イシューにする決まり（I205）。理由「アプリ本体」は最優先にならないので、連鎖の原因ではない。効く範囲を狭める側（安全側）なので、設計確認メモの範囲の中の決定
- 照合は振り分けの時（`--route`）に 1 回だけ — 目印を使うのは振り分けだけ。台帳を書く時にも確かめると 2 か所で食い違いうる
- LEDGER 行の目印は、あるときだけ書く（`RISK=` の後ろ） — 目印の無い行を 1 文字も変えず、既存のテスト・記録との互換を保つ
- 書き直し（同じ番号）での目印は最新の行の値 — 最新のレビュー役の判断を使う。外れれば後続イシュー側（安全側）
- 計画書は既存の `find_plan_file()`（連番の最新・同じ番号なら open）で選ぶ — レビュー役が読む計画書と同じものを照合する（/simplify で `plan_I###.md` だけを読む案から変更）
- テストは新しいファイル（`test_i512_accepted_risk.sh`） — `test_i202_ledger_cleanup.sh` は 780 行を超え、I202 の項目と混ざる。新しいファイルにすれば CI（`run-all.sh`）がそのまま流す
- 照合に使えなかった目印は標準エラーに出す — retro が「受け入れのつもりが効いていない」ことに気づける。振り分けの出力（標準出力）の形は変えない
- 一覧 I480 F1（一覧の行に SECURITY の欄が無い）: 同梱 — 受け入れた `SECURITY=yes` の行が一覧に来るので、一覧の中でもセキュリティの指摘と分かる必要がある（このイシューの目的に直結）
- 一覧 I208 F3（`--route` の第 3 引数を `I[0-9]+` で確かめない）: 同梱 — 第 3 引数から計画書のパスを組み立てるようになるので、`../` などを通さないため
- 一覧 `scripts/claude/code-review.sh` のほかの行（I206 F4・I208 F2・F5・I207 F6・F7・I212 F2・F3・F4・F6・I227 F1・F2・F4・F5・R1）: 残す — 台帳の書き直し・記録の一時ファイル・組み込みのレビューの読み方の話で、振り分けの目印とは関係しない
- 一覧 `FILE=-` の行（I224 F9・I223 B1〜B4）: 残す — 実測の約束・bot の停止中の作業で、このイシューと関係しない
- 一覧のほかの実装対象（`.claude/agents/code-reviewer.md`・`docs/plans/templates/plan_template.md`・`.claude/skills/retro/SKILL.md`・`docs/runbooks/review-rules.md`・`docs/reviews/backlog/I430.md`・新しいテスト）: 一覧の該当なし

要件適合性・業務ロジック: 受け入れ条件の範囲を超える仕様の追加は無い（アプリ本体を除くのは効く範囲を狭める側）。マルチテナント・ステータス遷移は該当なし

セキュリティ・ベストプラクティス:
- 入力: `--route` の第 3 引数を `^I[0-9]+$` で確かめてから計画書のパスを組み立てる（パスの操作を通さない）。計画書の中身は表の行の文字列として読むだけで、実行しない
- 目印はレビュー役（LLM）の自己申告だけで効かない（計画書の照合・fail-closed）。止める判定には効かない
- バックエンド・フロントエンドのコード変更なし。依存の追加なし。bandit・npm audit の対象なし
- P3/P5/P8 影響なし（DB・外部 API・非同期・新しいインフラなし）。P6 影響なし（UI・データ量の懸念なし）。P9 影響なし（個人情報・テナントデータを扱わない）

設計品質: 欄の省略・空（`-`）の扱いは今の `RISK=` と同じに揃える。計画書が読めないときは空の集合（例外で止めない・安全側）

Danger Ops（有無/手順/ロールバック）:
- 無（判定の仕組みの振り分けの変更。止める判定・GitHub の設定・データの削除なし）

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | 受け入れていない穴に目印を付けても一覧に落ちない（照合の失敗の 5 通りすべてで後続イシュー）: TC-05 が、計画書なし・節なし・行なし・処遇違い・別の R 番号の 5 通りを確かめ、照合を外した写しで不合格になる |
| V2 | 1 | 読んで可 | 目印で止める判定が変わらない: TC-03 が、目印つきの止める指摘（guard の High・harness の STOP=flow 再現あり）で `ledger_verdict` が HIGH のままであることを確かめ、`blocking()` に目印を足した写しで不合格になる |
| V3 | 2 | 読んで可 | TC-01・TC-02 が false-green でない: 効く条件（Medium 以下・再現なし・アプリ本体でない）の各項を 1 つずつ外した写しで、それぞれ不合格になる |
| V4 | 3 | 読んで可 | 前の形の行（I197・I205・I202・I208 の形）の読み方と、目印の無い行の LEDGER 行が変わらない: TC-04・TC-06 |

## レビュー結果
- [20261114_0117 判定: ✅ 完了](../../reviews/closed/I512_plan_review_20261114_0117.md)

## 計画変更記録
- 2026-11-14 計画レビュー 1 回目（OK・Warning 2・Info 2）への対応: 一覧からの同梱 2 件（I480 F1・I208 F3）を §2 に AC の外として明記・manual_test No.2 の手順を ledger_route の 1 通りに決め、行を SECURITY=yes にした（目印が効かないと issue 側になる形）。方式・範囲・受け入れ条件は変えないので計画レビューはやり直さない
- 2026-11-14 implement: (1) test_i202_ledger_cleanup.sh の追従は Q3・Q8・Q9・BL_FORM に加えて、FG の壊し方の元の文字列（SEC_COND・guard の条件・merged() の呼び出し 3 か所）も新しい形に合わせた（同じ FG のまま） (2) 一覧 I208 F3 の後半（種類の誤りを記録を探した後でしか検出しない）も直すため、--route の入口で種類を記録を探す前に確かめるようにし、F3 の行を消した (3) /simplify（整理役 4 体）の結果で、accepted_by_plan() をやめて accepted_why_not() を 1 回だけ呼ぶ形にし、route_reasons() に旗を足さず呼ぶ側で理由を除く形にし、計画書の探し方を既存の find_plan_file() にした（連番の計画書も読む）。台帳の行を名前で引く形にする提案（namedtuple）は範囲の外なので見送り、retro で一覧に回す (4) 一覧 I480 F2・F3 と I208 F4・F6（FILE=scripts/claude/tests/test_i202_ledger_cleanup.sh）は残す — 計画の拾い方で新しいテストのファイル名だけを当てていて漏れていた。どれも既存の FG の書き方の改善提案で、目印とは関係しない。計画レビューのやり直し: 不要（方式・範囲・受け入れ条件を変えない）
- 2026-11-14 retro → fix-loop: コードレビューの台帳 F1（同じ R 番号の回避と受け入れ・HTML コメントの中の行）を、このイシューの目的（fail-closed の照合・AC5）の穴としてこの PR で直した。accepted_risks() は受け入れでない同じ番号を引き、コメントの中を読まない。TC-05 に 2 通りと FG-05e・FG-05f を足した。計画レビューのやり直し: 不要（AC5 の範囲の中の直し）
- 2026-11-14 review-gate 3 回目 → fix-loop: 台帳 F7〜F10（F1 と同じ計画書の読み方の穴）を、行ごとの特例をやめた粗い fail-closed で直した（閉じたコメントは全文から取り除く・閉じていない <!-- から後ろは読まない・8 の節にコードの囲みがあれば受け入れは全部効かせない）。共有のテストの計画書を雛形と同じ複数行のコメントつきにし、TC-05 を 15 通りに・FG-05f〜i を足した。これで収まらなければ、止める指摘でない限り一覧・後続に回して打ち切る。計画レビューのやり直し: 不要（AC5 の範囲の中）
- 2026-11-14 review-gate 4 回目 → fix-loop: 台帳 F11（前の節の囲みの中の 8 の例を読む）・F12（囲みの中の <!-- で切れる）を、囲みを全文から先に取り除く一般形（strip_fences）で直した。8 の節の中の囲みの特例は消した（囲みは先に取り除くので要らない）。TC-05 を 17 通り・囲みの肯定（fok）と FG-05h の置き換え。以降の同種は止める指摘でない限り直さない。計画レビューのやり直し: 不要（AC5 の範囲の中）
- 2026-11-14 close の後 → fix-loop: TC-07（I430 の一覧の行を CI で毎回確かめる）を外し、AC8 は manual_test No.4 で確かめる形にした（plan-writing-rules「決定論テストの対象の選び方」の「作らない」に当たり、将来一覧の行を正しく消すと CI が落ちる罠になるため）。台帳 F4 と同じ中身。計画レビューのやり直し: 不要（AC8 を確かめる手段を変えるだけ）

## 完了情報
- **完了日時**: 2026-11-14
- **対応者**: Claude Code
- **レビュー結果**: OK（コードレビュー `docs/reviews/closed/I512_code_review_20261114_1209.md`・CI 全合格・手動テスト 4 件 OK）
