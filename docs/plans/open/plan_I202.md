# 計画書: I202 I197・I205 の台帳に残った指摘と、見送った共通化を片付ける

## 基本情報
- **計画書ID**: plan_I202
- **関連イシュー**: #338
- **Draft PR**: #343
- **作成根拠資料**: docs/issues/open/I202.md（起点イシュー・設計確認メモ 3 件）
- **実装後評価**: docs/reviews/open/I202_review.md
- **作成日**: 2026-10-27

## 1. 背景/目的
I197・I205 で基本レビューを「台帳＋差分のレビュー＋止める基準は変更の種類ごと」に作り直した。止めない指摘（Medium・Low・ハーネスの `STOP=-`）は台帳に残り、この I202 にまとまっている。その中に次がある。
- セキュリティの穴 F5: 計画の段階で「高リスクではない」とされた変更に、実装で認可・テナント境界の変更が入っても、敵対的レビューに入る経路が無い
- 判定の仕組みの穴: I205-F3（guard のファイルの変えていない行の High が止まらない）・I205-F4（変更の種類の判定が大文字・小文字を区別する）・台帳の限界（止めない指摘は、直しても台帳で open のまま残る）
- 細かな穴と重複（I197 の F6〜F19、I205 の残り、記録の探し方などの重複）

目的: F5 と判定の仕組みの穴を直し、残りは直すか見送るかを 1 件ずつ決めて理由を残す。直すことで大きな新しいコードを足さない（I197 の教訓。粗く確実な形を優先する）。

## 調査結果

### 原因の概要
I197 で「高リスクかどうか」を計画の段階だけで決めるようにしたので、実装が計画の見立てを超えたときの逃げ道が無くなった。ほかの指摘は、I197・I205 で止めない側に分けたため、直されずに残っている。

### 詳細な原因分析（今のコード・2026-10-27 の develop〔33d2e29〕）
- F5: `scripts/claude/code-review.sh:838-841` で `RISK_FINAL=combine_risk(計画レビューの判定, パスの判定)` を決め、以後変えない。`.claude/agents/code-reviewer.md:158` は「計画の見立てを超えて高リスクの条件に触れていれば Blocker として FINDING 行に書く」としているが、Blocker は「止める」だけで敵対的レビュー（`ADVERSARIAL_STAGE`）には入らない。しかも harness の Blocker は止める条件の一覧に当たらなければ止まらず、app の Blocker も再現が無ければ止まらない
- 台帳の限界: `code-review.sh:927-930` の差分のレビューの入力には、止める指摘（`ledger_blocking`）だけが出る。止めない open の指摘は入力に出ないので、レビュー役が直ったと書けない。`_LEDGER_PY` の `update`（`code-review.sh:675・705`）も、入力に見せていない既存の番号を新しい指摘として振り直す。I205-F1・F2・F6 は直したのに open のまま残った
- F12: 同じ `update` で、今回のレビューの中で初めて出た番号を 2 回書くと、2 回目は「入力に見せていない既存の番号」として振り直される（`shown` が前の台帳だけで決まる）
- I205-F3: `scope_of`（`code-review.sh:681-698`）は guard のファイルでも行で決める。guard のファイルの、ブランチで触っていない行の High は outside になり止まらない（`blocking()` の guard の行は「delta か、セキュリティの Blocker」）
- I205-F4: `kind_of`（`code-review.sh:604-609`）は大文字・小文字を区別する。`scope_of` は casefold で比べる（F16）ので、`.GitHub/workflows/ci.yml` のような表記は delta だが種類は app になり、再現の無い High が止まらない
- I205-F5: `REPRO_RE`（`code-review.sh:591`）は最初の `| 再現:` で切る。要約の中に `| 再現:` があると要約がそこで切れる（I205 の台帳の F5 は要約が「`」の 1 文字になった: `docs/reviews/closed/I205_code_review_20261027_1322.md`）。また `| 再現: なし` も中身ありとして REPRO=yes になる
- I205-F12: `branch_own_files`・`delta_files`（`code-review.sh:492-508`）は `--name-only` を `-z` なしで読む。`delta_hunks` の `git diff ... -- <ファイル>` は pathspec を glob として読む（`[`・`*` を含む名前）
- F13: 前の台帳が空のとき、`code-review.sh:928` が「台帳の最大の番号: F」と番号の無い行を入力に書く
- F14: レビュー役が失敗したとき（`REVIEW_OK=0`）も `code-review.sh:1016-1019` が「VERDICT は BLOCKER なのに読める FINDING 行が無い」と証跡に書く（失敗の記録の `VERDICT: BLOCKER` を読むため）。原因の取り違え
- F18: `code-review.sh:690` の `norm.startswith("..")` は `..foo` という名前のファイルもリポジトリの外とみなす（止める側）
- 空の範囲の差分のレビュー: `code-review.sh:819-824` は、起点の後に記録の場所の外のファイルが変わっていなくても claude を呼ぶ
- F6: `adversarial-review.sh:398` で 3 観点を並列に動かし、各観点の実験役（`run_experiment_agent`）が同じ作業ツリーで同時に動きうる。「壊して戻す」実験が重なると、片方の結果が他方の壊した状態で出る。戻した後は `check_worktree` の比較でも差が出ないので、捕まらない
- F7: `adversarial-review.sh:99-107` の `review_base` は、前の記録の `REVIEWED_COMMIT` が HEAD の祖先かを確かめない（rebase の後に、HEAD の歴史に無いコミットとの差分を見る）
- F8: `adversarial-review.sh:302-307` の拒否の件数は、ログを読めないと `claude_log_denials` の出力が空になり、黙って 0 件になる
- 「報告あり（）」: `adversarial-review.sh:297` は `note` が空でも改行を書くので、`:423` の `[ -s ]` が真になり、記録に空の括弧が出る
- 共通化: 記録の一覧（時刻順）の出し方が `code-review.sh` の `ledger_records`・`plan_risk`、`gate-check.sh` の `latest_record`、`adversarial-review.sh` の `adversarial_records` の 4 か所にある。`REVIEWED_COMMIT` の読み方が `review_mode`・`gate-check.sh` の `reviewed_commit`・`review_base` の 3 か所にある。「ブランチが変えたファイル」が `code-review.sh` の `branch_own_files`（`-z` なし）と `gate-check.sh` の `branch_files`（`-z` あり）の 2 か所にある

### 既存テストのベースライン（2026-10-27・このブランチ＝develop 33d2e29）
- `bash scripts/claude/tests/test_i205_stop_criteria.sh` → pass=90 fail=0
- `bash scripts/claude/tests/test_i197_review_ledger.sh` → pass=64 fail=0
- `bash scripts/claude/tests/test_i197_adversarial_process.sh` → pass=115 fail=0
- 全体（`run-all.sh`）は CI の Harness Tests で流す（手元では流し直さない）。影響を受けうるテスト（変える関数名・語を `grep` で参照しているもの）: `test_adversarial_trigger.sh`・`test_i193_official_flow.sh`・`test_i181_review_slim.sh`・`test_i197_review_ledger.sh`・`test_i197_adversarial_process.sh`・`test_i205_stop_criteria.sh`・`test_review_commit_lifecycle.sh`・`test_review_gates.sh`・`test_review_verdict.sh`

### 環境前提
`bash`・`python3`・`git`（2.43.0）・`flock`（`/usr/bin/flock`・util-linux。CI の ubuntu にも標準で入っている）だけを使う。新しい道具は `flock` だけで、F6 の直し方に使う。

### 消費箇所の全件（判定の決め方を変えるので、それを書いている箇所）
`grep -rn "見立て\|高リスク\|計画レビューの判定とパス" .claude docs/runbooks scripts/claude` で確認したもの:
- `.claude/agents/code-reviewer.md:158`（高リスク判定の条件の前置き）・FINDING 行の説明（`:219`・`:228-236`）・差分のレビューの説明（`:240`）
- `.claude/skills/review-gate/SKILL.md:14`（「高リスクかどうかは計画レビューの判定とパスの判定で決まり、周ごとに変わらない」）・`:48`（敵対的レビューの対象）
- `docs/runbooks/review-rules.md:59`（同じ文）・`:80-83`（高リスク判定 YES になる条件の (a)(b)）
- `scripts/claude/code-review.sh:839`・`:995`（コメント）

## 2. 受け入れ条件
イシューの受け入れ条件と同じ（番号はこの計画で振る）。
- AC1 F5 が直っている（code-reviewer が FINDING 行に「計画の見立てを超えた高リスク」の目印を付けると、計画レビューの判定が No でも `ADVERSARIAL_STAGE: REQUIRED` になる）ことを、失敗注入つきのハーネステストで固定している
- AC2 I205-F3・I205-F4・台帳の限界が直っている（または見送る理由が計画書にある）ことを、ハーネステストで固定している
- AC3 残りの Medium・Low（I197・I205 の台帳）と共通化について、直した／見送ったの一覧と理由が計画書にある（→ 4.0）
- AC4 直したものごとに、失敗注入つきのハーネステストがある
- AC5 既存のハーネステスト（`bash scripts/claude/tests/run-all.sh`）・CI がすべて pass する

## 3. 影響範囲
| 区分 | 内容 |
|---|---|
| Backend / Frontend / DB | なし |
| Config/Infra（ハーネス） | `scripts/claude/code-review.sh`・`scripts/claude/adversarial-review.sh`・`scripts/claude/gate-check.sh`（関数の置き場所だけ・挙動は変えない）・`.claude/agents/code-reviewer.md`・`.claude/skills/review-gate/SKILL.md`・`docs/runbooks/review-rules.md`・`scripts/claude/tests/test_i202_ledger_cleanup.sh`（新設）・`scripts/claude/tests/test_i197_review_ledger.sh`・`scripts/claude/tests/test_i205_stop_criteria.sh`（更新） |
| 変えないもの | `path_risk_trigger()` の中身・`gate-check.sh` の合否・見張り・`.claude/settings.json`・`.github/` |

イシューの「実装対象」に無い `.claude/skills/review-gate/SKILL.md`・`docs/runbooks/review-rules.md` は、F5 で高リスクの決め方が変わるので、同じ文を書いている消費箇所として直す（調査結果の「消費箇所の全件」）。
依存関係ファイルの変更はない（P3/P5/P8 影響なし）。UI はない（P6 影響なし）。個人情報・テナントデータは扱わない（P9 影響なし）。

## 4. 変更点一覧（具体）

### 修正アプローチ
- F5 は、FINDING 行に任意の目印 `RISK=up` を足し、台帳に残す。台帳（今回と前の周すべて）に 1 件でも `RISK=up` があれば、スクリプトが高リスクを YES にする。一度 YES になったら戻らない（止める側）。
- 判定の穴（I205-F3・F4・F5・F12、I197-F12・F18）は、`_LEDGER_PY` と git の呼び方の小さな直しで閉じる。どれも止める側に倒す向き。
- 台帳の限界は、差分のレビューの入力に「止めない open の指摘」も出し、直ったものだけ resolved と書いてもらう。
- 共通化は、記録の一覧・`REVIEWED_COMMIT` の読み方・ブランチが変えたファイルを `code-review.sh` の関数 1 か所にし、`gate-check.sh`・`adversarial-review.sh` はそれを呼ぶ（gate-check の挙動は変えない）。
- 敵対的レビューの細部（F6〜F8・空の括弧）は、各 1〜数行で直す。

### 4.0 全件の振り分け（AC3）
| 指摘 | 扱い | 理由・直し方 |
|---|---|---|
| I197-F5（Medium・SECURITY=yes） | 直す（4.1） | 設計確認メモの A 案 |
| I197-F6（並列の実験の汚染） | 直す（4.6） | `flock` で実験役の実行を 1 本ずつにする。数行で確実に閉じる |
| I197-F7（review_base の祖先確認） | 直す（4.6） | 祖先でなければ比べる相手（`origin/develop`）からにする（見る範囲が広がる＝止める側） |
| I197-F8（拒否の件数が黙って 0 件） | 直す（4.6） | 読めないときは「読めない」と書き、その観点を合格にしない |
| I197-F9（`parse_findings` が本体で未使用） | 見送り | テストが FINDING 行の読み方を確かめる入口として使っている。消すとテストが本体の内部（`_LEDGER_PY` の呼び方）に依存する |
| I197-F10（同じ分の連番の並び順 `_10` と `_9`） | 見送り | 1 回のレビューは CI 待ちを含めて数分かかるので、同じ分に 10 回は起きない |
| I197-F11 | 直した（I205） | ― |
| I197-F12（同じ番号を 2 回書くと振り直される） | 直す（4.2） | 今回のレビューで出た番号は振り直さない |
| I197-F13（空の台帳で「最大の番号: F」） | 直す（4.3） | 番号が無ければ「なし（F1 から）」と書く |
| I197-F14（失敗時に誤った原因が証跡に出る） | 直す（4.3） | レビュー役が失敗したときは、食い違いの検査をしない（失敗の理由は既に書いてある） |
| I197-F15（R17 が本体の文字列に依存・R14 と重複） | 直す（4.8） | R17・FG-R17 を消し、R14 の 3 周目（同じ振る舞いを本体の通しで確かめる）に失敗注入を付ける |
| I197-F16 | 直した（I205） | ― |
| I197-F17（`isfile` がシンボリックリンクをたどる） | 見送り | 違いは「差分の中」になる向き（止める側）だけ |
| I197-F18（`..foo` をリポジトリの外とみなす） | 直す（4.2） | `norm == ".." or norm.startswith("../")` にする（1 行） |
| I197-F19（R16 のコメントが古い・FG-R16 が個別に検知しない） | 直す（4.8） | コメントを今の方式に直し、FG を `..` と `isfile` の 2 本に分ける |
| 敵対的レビューの「報告あり（）」 | 直す（4.6） | 中身があるときだけ note を書く |
| 共通化: 記録の一覧・REVIEWED_COMMIT・ブランチが変えたファイル | 直す（4.7） | 1 か所にして 3 本が呼ぶ（gate-check の挙動は変えない） |
| 共通化: `set_risk_line` と `add_reviewed_commit` の骨組み | 見送り | どちらも 10 行の awk で、置く位置の規則が違う（REVIEWED_COMMIT は RISK 行の前）。1 つにすると引数で規則を切り替えることになり、gate-check が読む RISK 行の位置を壊す危険のほうが大きい。不具合は無い |
| 共通化: 空の範囲の差分のレビューでも claude を呼ぶ | 直す（4.3） | 範囲が空なら、レビュー役を呼ばずに前の台帳をそのまま引き継ぐ（直したものが無いので結果は同じ・費用と時間を省く） |
| I205-F1・F2・F6 | 直した（I205・台帳では open） | 4.4 の台帳の限界の直しで、次に I205 の台帳を使うことは無いので、台帳は書き換えない |
| I205-F3（guard の変えていない行の High が止まらない） | 直す（4.2） | guard のファイルは、ブランチが変えたファイルなら行に関係なく差分の中（I197 のまま＝ファイル単位）。説明と挙動をそろえる |
| I205-F4（`kind_of` が大文字・小文字を区別） | 直す（4.2） | casefold して比べる（表記違いは厳しい側の種類になる） |
| I205-F5（要約の中の `\| 再現:`・「再現: なし」） | 直す（4.2） | 最後の `\| 再現:` で分ける。中身が「なし・無し・-・none・n/a」（大文字・小文字・空白を無視）なら再現なし |
| I205-F7（消しただけの塊と旧ファイル側の行番号） | 直す（4.5・指示だけ） | code-reviewer に「消した行への指摘は、消した位置の HEAD の行番号で書く」と書く（スクリプトは変えない） |
| I205-F8（前の形の台帳を KIND=app で読む） | 見送り | 止める側に倒れる。I205 のマージ（10-27）で切り替えは終わり、前の形の台帳で途中のイシューは無い |
| I205-F9（止める指摘の節に再現が無い） | 直す（4.3） | 節の見出しの下に「再現は本文の同じ番号の FINDING 行」と 1 行書く（台帳に再現の文は持たない） |
| I205-F10（`branch_own_files` を 3 回呼ぶ） | 見送り | 1 回数十ミリ秒。引数を増やして使い回すほうが変更が大きい |
| I205-F12（`-z` なし・pathspec が glob） | 直す（4.7） | ブランチが変えたファイルを `-z` で読む（4.7 の共通化と同じ）。`delta_hunks`・差分のレビューの `git diff` に `--literal-pathspecs` を付ける |
| I205-F13（見出しのパスを推測で切り出す） | 見送り | 設計上の改善提案。読み違えても I205-F2 の直し（diff に出てこないファイルはファイル全体）で止める側に倒れる |
| I205-F14（H8 の説明とテストの中身のずれ） | 見送り | ずれているのは I205 の閉じた記録（`docs/tests/closed/I205_auto_test.md`）の文で、テストのコメントは中身と合っている。閉じた記録は書き換えない |
| I205-F15（H7 の git の設定を戻していない） | 直す（4.8） | FG-H7 の後に設定を外す |
| I205-F16（消したファイルが塊に残る） | 見送り | 台帳は `isfile` で弾くので無害 |
| I205-F17（`--no-relative` は git 2.28 以降） | 見送り | 手元 2.43・CI も同等。古い git では `delta_hunks` が 2 を返して止まる（止める側） |
| I205-F18（`FILE=(\S+)` は空白を含むパスを表せない） | 見送り | 止める側（実在しないファイル扱いで delta）に倒れるだけ |
| I205-F19（H10 は新しいファイルだけ） | 直す（4.8） | 既存のファイルの一部だけを変えた場合と、差分のレビュー（起点あり）の経路を足す |
| 台帳の限界 | 直す（4.4） | ― |
| 独立した評価の案 (1)（判定に関わるファイルの指摘を最低 High に上げる） | 見送り | I205 でハーネスは重大度を見ずに止める条件の一覧で決めるので、重大度を上げても止め方は変わらない（ラベルを下げて通す抜け道は I205 で閉じた） |
| 独立した評価の案 (2)（台帳の Medium・Low の件数に上限） | 見送り | retro の手順 4-0（I205）が台帳の残りを必ず 1 か所に振り分け、判定の仕組みの指摘は「次のハーネスの作業で最優先」と書く。上限の仕組みを足すと、それ自体が新しい判定のコードになる |

### 4.1 F5: 計画の見立てを超えた高リスクの目印（AC1）
修正方針: レビュー役が目印を付けたら、スクリプトが高リスクを YES にする。目印は止めるかどうかとは別の欄にし、`blocking()` は変えない。

FINDING 行（レビュー役）: `STOP=` の後ろに任意で ` RISK=up` を書ける。
```
FINDING: F<n> SEV=… STATUS=… FILE=… LINE=… SECURITY=… STOP=… [RISK=up] | 要約 | 再現: …
```
- 正規表現: `... STOP=(\S+)(?: RISK=(up))?(?: \| (.*))?`。`RISK=` に `up` 以外を書いた行は形の崩れ（今と同じく台帳を作らず BLOCKER）。
- 台帳の行（スクリプト）: `REPRO=… RISK=<up|-> SECURITY=…`。前の形（`RISK=` の無い行）も読む（`-` として読む）。既にある指摘を書き直すときは、`up` が残る（SECURITY と同じく止める側）。
- 新しいモード `risk <台帳のファイル…>`: どれかの台帳の行に `RISK=up` があれば `YES`、無ければ `NO`。関数 `ledger_risk`。
- 本体: 台帳を作った後（`code-review.sh:1000` の後）に、今回の台帳と、この I### の前のコードレビューの記録すべて（4.7 の `review_records`）の台帳を `ledger_risk` に渡し、`RISK_LEDGER` を得る。`RISK_FINAL=$(combine_risk "$RISK_FINAL" "$RISK_LEDGER")`。前の記録まで見るのは、rebase の後の全体のレビューで台帳が作り直されても、一度 YES になった判定を戻さないため。
- 証跡の行（`code-review.sh:996`）は台帳の後に動かし、`高リスク判定: …（計画レビュー=… / path=… / 台帳の目印=…）` にする。
- これで `set_risk_line`（記録の `RISK:` 行）と `emit_decision_lines`（`ADVERSARIAL_STAGE:` 行）が YES になる。`gate-check.sh` は記録の `RISK:` 行を読む（今のまま）ので、敵対的レビューの OK が無いと通らない。
- 計画書に「## 必ず確かめる項目」が無いイシューで目印が付くと、`adversarial-review.sh` は exit 2（`ADVERSARIAL_ERROR: CHECKLIST`）になる。これは今の review-gate §3-2 の手順（計画書に一覧を足してコミットし、1 回だけ実行し直す）でそのまま扱える。§3 にこの経路を 1 文書く（4.5）。
- 組み込みの `/security-review` は今のままパスの判定のときだけ（目印はレビュー役の後に分かるので、同じ周には間に合わない。敵対的レビューが代わりの目になる）。

### 4.2 `_LEDGER_PY` の判定の穴（AC2）
修正方針: どれも数行で、止める側に倒す。
- I205-F3（guard はファイル単位）: `scope_of` の中で、そろえたパスの種類が guard で、そのパス（casefold）が塊の一覧にある（＝ブランチが変えたファイル）なら、行に関係なく `delta`。
- I205-F4: `kind_of` は `p = path.casefold()` で比べる（`GUARD_FILES` などの集合も casefold した写しと比べる）。
- I205-F5: `REPRO_RE` をやめ、`rest.rsplit("| 再現:", 1)` で最後の `| 再現:` で分ける（要約の中の `| 再現:` で切れない）。中身を `strip()` して空、または `casefold()` が `なし`・`無し`・`-`・`none`・`n/a` のどれかなら REPRO=no。
- I197-F12: `update` で、今回のレビューの中で既に読んだ番号の集合 `seen` を持つ。`fid in led and fid not in shown and fid not in seen` のときだけ振り直す（同じ番号の 2 回目は同じ指摘の書き直しとして扱う）。
- I197-F18: `norm == ".." or norm.startswith("../")` をリポジトリの外とする。
- 台帳の限界の `shown`（4.4）。

### 4.3 `code-review.sh` の本体の細部
- I197-F13: 「台帳の最大の番号」は、番号があれば `F<n>（新しい指摘はこの次から）`、無ければ `なし（新しい指摘は F1 から）`。
- I197-F14: レビュー役が正常に終わったか（`code-review.sh:969-974` の判定）を新しい変数 `REVIEWER_RAN`（1=終わった・0=失敗）に残す。食い違いの検査（`code-review.sh:1016`）は `[ "$REVIEWER_RAN" = "1" ]` のときだけ行う（失敗したときは、失敗の記録が理由を書いている）。`REVIEW_OK` は台帳の作成の失敗でも 0 になるので、この検査には使わない。
- 空の範囲（共通化の 3 つ目）: 差分のレビューで `SCOPE_FILE` が空なら、claude を呼ばず、レビュー役の本文を固定の文（`# コードレビュー [I###]（差分なし）`・「起点の後に、記録の場所の外でブランチが変えたファイルは無い。レビュー役は呼んでいない。台帳は前の周のまま」・`## 台帳`・`指摘なし`・`VERDICT: OK`）にする。`ledger_update` は前の台帳をそのまま引き継ぐので、止める指摘が残っていれば合否は前と同じ。組み込みの `/code-review` も呼ばない（`(実行していない: 差分なし)`）。
- I205-F9: 「## 止める指摘（スクリプトが決めた…）」の節の見出しの次に `（再現は本文の同じ番号の FINDING 行）` の 1 行を書く。

### 4.4 台帳の限界（AC2）
修正方針: 止めない open の指摘もレビュー役に見せ、直ったものだけ resolved にしてもらう。直していないものを書き直させる義務は付けない（入力が増えた分の作業を増やさない）。
- 差分のレビューの入力（`code-review.sh:925-931`）に、止める指摘の節の後ろに `#### 台帳の残り（止めない open の指摘。直したと差分から分かるものだけ、同じ番号で STATUS=resolved の FINDING 行を書く。書かなければ open のまま）` を足す。中身は新しいモード `open <台帳>`（`STATUS=open` で `blocking()` が偽の行）。関数 `ledger_open_rest`。
- `update` で、台帳の残りの番号（`rest_ids`）は、`STATUS=resolved` と書いた行だけ同じ番号として受け付ける。open で書いた行は、今までどおり新しい番号に振り直す（前の SCOPE を引き継いで、差分の中の新しい指摘が止まらなくなるのを防ぐ・I197-F1 の守りを弱めない。計画変更記録 2）。止める指摘（`shown`）は今のまま。
- 止めない指摘を resolved と書き直しても、`blocking()` が偽なので合否は変わらない（止める側の指摘を resolved にするのと同じく、レビュー役の判断に頼る。今と同じ）。
- code-reviewer.md の差分のレビューの説明にも同じことを 1 文書く（4.5）。
- retro の手順 4-0（`STATUS=open` の行を拾う）は変えない。直ったものは resolved になるので拾われなくなる。

### 4.5 指示ファイル（code-reviewer・review-gate・review-rules）
- `.claude/agents/code-reviewer.md`:
  - 「高リスク判定の条件」の前置き（`:158`）: 「触れていれば Blocker として FINDING 行に書く」を「触れていれば、その指摘の FINDING 行に `RISK=up` を付ける（重大度・STOP は普段どおり。目印が 1 件でもあれば、スクリプトが敵対的レビューを必須にする）」に置き換える。目印を付けるのは、計画書の高リスク判定（計画レビューの記録）が No なのに一覧の条件に当たる変更が差分にあるときだけ、と書く。
  - 出力フォーマットの FINDING 行と欄の説明に `[RISK=up]`（任意・`STOP=` の後ろ）を足す。
  - 差分のレビューの説明に「台帳の残り（止めない open の指摘）のうち、直したと差分から分かるものは同じ番号で `STATUS=resolved` と書く」を足す。
  - LINE の説明に「消した行への指摘は、消した位置の HEAD の行番号で書く（I205-F7）」を足す。
  - `再現: なし` のように書くと再現なしとして扱う、と 1 文足す（I205-F5）。
- `.claude/skills/review-gate/SKILL.md`:
  - `:14` の「高リスクかどうか（3. を走らせるか）は計画レビューの判定とパスの判定で決まり、周ごとに変わらない」を「計画レビューの判定・パスの判定・台帳の目印（code-reviewer が計画の見立てを超えた高リスクの変更に付ける `RISK=up`）で決まる。一度 YES になったら戻らない」にする。
  - §3 の対象（`:48`）に「台帳の目印」を足し、「計画書に『## 必ず確かめる項目』が無いまま目印で REQUIRED になったときは、§3-2 の exit 2 の手順（一覧を足してコミットし、1 回だけ実行し直す）で扱う」と書く。
- `docs/runbooks/review-rules.md`: `:59` の同じ文と、`:80-83` の「高リスク判定 YES になるのは次のどちらか」に (c) 台帳の目印を足す（「どちらか」→「どれか」）。

### 4.6 `adversarial-review.sh` の細部
- F6: `run_perspective` の中の実験役の呼び出し（`run_experiment_agent`）を `flock "$RUN/exp.lock"` で包む（観点をまたいで実験役は同時に 1 本だけ。レビュー役は並列のまま）。待ち時間は締め切り（`ADV_DEADLINE`）の中に含まれる。ロックを取った直後に `remaining()` を見て、`ADV_MIN_STEP` より少なければ実験役を呼ばずにロックを放し、その周の実験 id をすべて `deadline` として `exp_status` に書いてループを抜ける（今の `reason=deadline` と同じ扱い＝未検証。記録の表示は「実行していない（締め切り）」）。ロックを取れた後の実験役の時間上限は、今のまま `run_step` の `step_timeout`（残り時間で切る）。`flock` に渡すため、実験役の呼び出しを関数のまま `flock … bash -c` ではなく、`{ flock 9; run_experiment_agent …; } 9>"$RUN/exp.lock"` の形にする（関数をそのまま使える）。
- F7: `review_base` で、`git merge-base --is-ancestor "$sha" HEAD` が偽なら `ADV_BASE` を返す（見る範囲が広がる＝止める側）。記録に「前の記録の REVIEWED_COMMIT が HEAD の祖先ではないため、比べる相手から見た」と 1 行書く（`REVIEW_BASE_NOTE`）。
- F8: 拒否の件数は、`claude_log_denials` が失敗したら `?` にし、その観点の行の拒否に `読めない` と書く。読めない観点が 1 つでもあれば、その周を合格にしない（`VERDICT=HIGH`。拒否が読めないと、承認が要る操作で止まったかを確かめられないため）。`HIGH` は今の判定の語彙（`adversarial-review.sh:428-430` の `BLOCKER`・`HIGH`・`OK`）の 1 つで、未検証・作業ツリーの変更と同じ扱い（終了コード 1）。新しい語は足さない。
- 空の括弧: `run_perspective` の最後で、`note` が空なら `note` のファイルを空のまま作る（`printf '%s' "$note"` にして改行を書かない）。`[ -s ]` は今のまま。

### 4.7 共通化（`code-review.sh` に置き、3 本が呼ぶ）
修正方針: 置き場所を 1 か所にする。gate-check の合否・出力は変えない。
- `review_records <I###> <種類>`（種類は `code_review`・`adversarial_review`・`plan_review`）: `docs/reviews` の下 2 階層までの `<I###>_<種類>_*.md` を、ファイル名の時刻順（`LC_ALL=C sort`）に出す。`ledger_records`・`plan_risk`・`gate-check.sh` の `latest_record`（`review_records … | tail -1`）・`adversarial-review.sh` の `adversarial_records` はこれを呼ぶ。
- `record_reviewed_commit <ファイル>`: 最後の `REVIEWED_COMMIT:` の SHA（無ければ空）。`review_mode`・`gate-check.sh` の `reviewed_commit`・`review_base` はこれを呼ぶ。
- `branch_own_files <比べる相手> [<rev>=HEAD]`: `git -c core.quotePath=false diff -z --name-only --no-renames <merge-base> <rev>` を `-z` で読み、記録の場所を除いて 1 行ずつ出す（今の `gate-check.sh` の `branch_files` の形。I205-F12 の `-z`）。`gate-check.sh` の `branch_files <rev>` は `branch_own_files "$GATE_BASE" "$1"` を呼ぶだけにする。
- `delta_files` の起点からの `--name-only` も `-z` で読む。`delta_hunks` の 2 つの `git diff` と、差分のレビューの `GIT_DIFF`（`code-review.sh:821`）の `git diff` に `--literal-pathspecs` を付ける（`git --literal-pathspecs -c core.quotePath=false diff …`）。
- gate-check の挙動が変わらないことは、既存の gate-check のテスト（`test_review_commit_lifecycle.sh`・`test_i193_official_flow.sh`）と新しい G 群で確かめる。

### 4.8 テストの細部
- I197-F15: `test_i197_review_ledger.sh` の R17・FG-R17（本体の文字列の grep）を消す。代わりに R14 の 3 周目（VERDICT: HIGH なのに FINDING 行が無い → BLOCKER）に FG を付ける（その検査を `if false` にした写しで、3 周目が BLOCKER にならないこと）。
- I197-F19: R16 のコメントを今の方式（`:行番号` を除いてリポジトリのルートからの相対パスにそろえる・外と実在しないファイルは delta）に直す。FG-R16 を、`..` の検査だけを外したもの（`r16e` が outside になる）と、`isfile` の検査だけを外したもの（`r16b` が outside になる）の 2 本にする。
- I205-F15: `test_i205_stop_criteria.sh` で、FG-H7 の後に `git config --unset diff.noprefix`・`--unset diff.mnemonicPrefix` を足す。
- I205-F19: H10 に、既存のファイル（空白を含むパス）の一部だけを変えた場合と、差分のレビュー（起点あり）の経路を足す。

## 5. 実装手順（ステップ）
未知リスクは小さい。いちばん不確かなのは「実験役を `flock` で 1 本ずつにしても、締め切りの中で動くか」なので、ステップ 1 に置く。

1. `adversarial-review.sh` の F6〜F8・空の括弧（4.6）→ TC-01 の A 群（`claude` のスタブで、2 観点の実験が重ならないこと・締め切りの扱い）
2. 共通化（4.7）: `review_records`・`record_reviewed_commit`・`branch_own_files` を `code-review.sh` に置き、`gate-check.sh`・`adversarial-review.sh` を付け替える → TC-01 の G 群・TC-03（ステップ 1 と並行してよい）
3. `_LEDGER_PY` の判定の穴（4.2）と台帳の限界（4.4 の `shown`・`open` モード）→ TC-01 の L 群（ステップ 2 の後。`branch_own_files` を使うため）
4. F5（4.1）: FINDING・LEDGER の `RISK=` の欄・`risk` モード・本体の配線 → TC-01 の R 群（ステップ 3 の後。同じ `_LEDGER_PY` を変えるため）
5. 本体の細部（4.3）と入力の「台帳の残り」の節（4.4）→ TC-01 の W 群（ステップ 4 の後）
6. 指示ファイル（4.5）→ TC-01 の D 群（ステップ 4 と並行してよい）
7. テストの細部（4.8）と、影響を受けうるテストの語の付け替え → TC-02・TC-03

## 6. テスト計画
### 自動（詳細は docs/tests/open/I202_auto_test.md）
- ユニット（関数）: `code-review.sh`・`adversarial-review.sh` を `REVIEW_LIB_SOURCE_ONLY=1` で読み込み、一時の git リポジトリで確かめる（新設 `test_i202_ledger_cleanup.sh`）
- 結合: `code-review.sh` を gh・claude のスタブで丸ごと動かす（`test_i205_stop_criteria.sh` の W 群と同じやり方）。F5 は「計画レビューの判定が No・パスの判定が NO で、スタブのレビュー役が `RISK=up` を書く」と `ADVERSARIAL_STAGE: REQUIRED`・記録の `RISK: YES` になり、`gate-check.sh` が敵対的レビューの記録を求めることまで通しで確かめる
- 静的: 指示ファイルの語（D 群）
- 否定の判定（止まらない・合格になる・変わらない）には失敗注入（FG）を付ける
- E2E・pytest・Jest: 非該当（アプリのコードを変えない）

### 手動（詳細は docs/tests/open/I202_manual_test.md・実施者はすべて Claude）
- 実際の code-reviewer（`claude -p`）が `RISK=up` の欄を書いても形が崩れないか、付けるべきでない変更（このイシュー自身＝ハーネスだけ）で付けないか
- このイシュー自身の review-gate の記録で、入力に「台帳の残り」の節が出ているか（差分のレビューの周があれば）

## 7. ロールバック
ハーネスのファイルだけの変更なので、PR を revert すれば戻る（GitHub が最後の守り）。前のスクリプトは `RISK=` の欄のある台帳の行を読めない（LEDG の正規表現に合わず、その行が台帳から落ちる）。戻した直後にレビューの途中のイシューがあれば、I205 の計画 §7 と同じく、新しい形で書かれたコードレビューの記録の名前を `_code_review_` を含まない名前に変えて退避し（消さない）、全体のレビューからやり直す。退避したことは自律判断の記録に書く。

## 8. Risk & 回避策
| リスク | 回避策 |
|---|---|
| レビュー役が `RISK=up` を付けすぎて、毎回敵対的レビューになる（費用・時間） | 付ける条件を「計画レビューの判定が No なのに、一覧の条件に当たる変更が差分にある」に限ると書く。付けすぎは止める側の誤りで、ユーザーが受け入れた費用（設計確認メモ） |
| レビュー役が付けるべき目印を付けない | 今と同じ（LLM の見落とし）。パスの判定と計画レビューの判定は残る。目印は経路を足すもので、ほかの判定を弱めない |
| `RISK=` の書き間違いで形が崩れ、BLOCKER になる | 任意の欄にし、`STOP=` の後ろだけに置く。手動 No.1 で実物を確かめる。形の崩れの扱いは今と同じ（review-gate が実行し直す） |
| `flock` で実験が直列になり、締め切りに間に合わない観点が増える | 締め切りの中の待ちとして今の `deadline` の扱い（未検証＝合格にしない）になる（止める側）。A 群で、待ちの後に残り時間で扱いが決まることを確かめる |
| 共通化で gate-check の挙動が変わる | 合否・出力の文は変えない。G 群で、関数を付け替えた前後で同じ一時リポジトリに対する gate-check の結果が同じことを確かめ、既存の gate-check のテストも流す |
| 台帳の残りを見せたことで、レビュー役が止めない指摘まで直そうとして周が延びる | 「直したと差分から分かるものだけ resolved と書く。書かなければ open のまま」と書き、新しい作業は求めない。止めない指摘は合否に関係しない |
| 空の範囲でレビュー役を呼ばないことで、止める指摘が直ったことを見落とす | 範囲が空＝記録の場所の外は変わっていないので、止める指摘は直りようがない。前の台帳をそのまま引き継ぐ（合否は前と同じ） |

## 9. 確定事項と自律判断
### イシューに明記されていること（設計確認メモ）
- F5 は A 案: code-reviewer が FINDING 行に「計画の見立てを超えた高リスク」の目印を付けたら、`code-review.sh` が `ADVERSARIAL_STAGE: REQUIRED` にする。ユーザーへの確認は増やさない。目印が付いた周の費用・時間が増えるのは受け入れる。パス名で見分ける案は採らない
- I197・I205 の「止める基準は変更の種類ごと＋台帳」の形は変えない
- F11・F16 は I205 で直っている
- 台帳の限界の直し方・残りの採否・独立した評価の案の採否は計画で Claude が決める

### Claude が技術的に決めたこと（理由）
- 目印の書き方 `RISK=up`（任意・`STOP=` の後ろ）: 止める欄（STOP）と混ぜず、今の正規表現に任意の欄を足すだけで済む。任意にするのは、付けない普通の指摘で形の崩れを増やさないため
- 目印は一度付いたら戻らない（前の記録まで見る）: 「周ごとに変えない」の考え方を、YES の向きにだけ広げる。直したからといって高リスクの変更が無くなったとは言えないため
- 目印は止めるかどうかを変えない（`blocking()` は変えない）: 目印の役は敵対的レビューに回すことで、止めるのは敵対的レビューの判定に任せる
- 4.0 の振り分け（直す／見送る）と理由: 表のとおり。見送るものは、止める側に倒れる・現実に起きない・直すとかえって大きくなる、のどれか
- 共通化は `code-review.sh` に置く: `gate-check.sh`・`adversarial-review.sh` は既に `code-review.sh` を関数だけ読み込んでいる（新しい読み込みを足さない）
- F6 は `flock`: 実験の衝突を数行で確実に無くせる。別の作業ツリーで実験させる案は、ワークツリーの作成・後片付けが要り、コードが大きくなる
- テストは新設の `test_i202_ledger_cleanup.sh` と、既存の 2 本の細部の直し: I202 の判定を 1 本にまとめるため
- `path_risk_trigger()`・gate-check の合否は変えない: 安全装置の判定を変えない（止めて聞く条件 2 に当たらないようにする）

### ユーザーに確認した価値判断
- F5 の方式（設計確認メモ）。ほかに価値判断に当たる仮定は無い（UI なし・受け入れ条件はイシューのまま）

### セキュリティ・BP チェック
- アプリのコードを変えないので、入力の検証・認証・認可・OWASP の影響はない（セキュリティ影響なし）。F5 は、アプリの認可・テナント境界の変更の検証の経路を増やす（強める向き）
- 判定の安全側: 目印・guard のファイル単位・casefold・「再現: なし」・`..`・祖先でない起点・拒否が読めない、はどれも止める側（または見る範囲を広げる側）に倒す。緩める向きは「再現: なし を再現なしとして扱う」だけで、これは書いた本人が再現なしと書いたものを、I205 の決まり（再現の無い指摘は止めない）どおりに扱う直し
- 依存ライブラリの追加はない。bandit・npm audit: 非該当（Python は `python3 -I -c` の埋め込みだけ）

## 必ず確かめる項目
この計画は高リスクの見込みではない（ハーネスだけ）。ただし F5 の目印で敵対的レビューが必須になったときに止まらないよう、一覧を置いておく。
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 実験必須 | 計画レビューの判定が No・パスの判定が NO のイシューで、FINDING 行に `RISK=up` を付けると `ADVERSARIAL_STAGE: REQUIRED`・記録の `RISK: YES` になり、`gate-check.sh` が敵対的レビューの記録を求める。次の周で目印の無い差分のレビュー・rebase の後の全体のレビューでも YES のまま |
| V2 | 2 | 読んで可 | F5・I205-F3〜F5・I197-F12・台帳の限界のテストが、判定の要を壊すと不合格になる（FG が本体の同じ行を壊している） |
| V3 | 3 | 読んで可 | 4.0 の見送りと 4.2 の直しのうち、緩める向き（止めるべきものが止まらなくなる）は「`再現: なし` を再現なしとして扱う」（I205-F5）の 1 件だけで、それは I205 の決まり（再現の無い指摘は止めない）と一致する |

## 計画変更記録
1. 計画レビュー（`docs/reviews/I202_plan_review_20261027_1526.md`）の Warning 3 件への対応: V3 の文言を 9 章（緩める向きは「再現: なし」の 1 件）と合わせた／4.3 の F14 の検査の条件を `REVIEWER_RAN=1` に一本化した／4.6 の F6 にロックの後で締め切りが迫ったときの手順を書き、F8 の `HIGH` が今の語彙であることを明記し、auto_test に A1b を足して A3 の期待値を具体化した。Info 2 件は対応不要（FG-D は意図どおり・見送りの理由は妥当）。計画レビューのやり直し: 不要（findings への対応の追記で、方式・範囲・受け入れ条件は変えない）
2. （implement）4.4 の `shown` の広げ方を変えた。計画の記載「`shown` を前の台帳の `STATUS=open` の番号すべてにする」→ 採った方法「台帳の残りの番号は resolved と書いた行だけ受け付け、open で書いた行は新しい番号に振り直す」。理由: open の番号をそのまま受け付けると、レビュー役が台帳の残り（SCOPE=outside など）の番号で新しい指摘を書いたとき前の SCOPE を引き継ぎ、差分の中の新しい指摘が止まらなくなる（I197-F1 と同じ穴が戻る）。台帳の限界を直すのに要るのは resolved の受け付けだけ。auto_test の L6 に「open で書くと F3 に振り直す」を足した。計画レビューのやり直し: 不要（同じ受け入れ条件の中で、止める側に倒す向きの細部の変更）
3. （implement）auto_test の G5 を、振る舞いのテストから静的な確認に変えた。理由: スパイク（scratchpad の `gt.sh`）で、git は `x[1].txt` の pathspec を glob として `x1.txt` にも当てることを確かめた。しかし `delta_hunks` の塊は「対象のファイルの一覧」と「2 本の diff の重なり」で作るので、glob で余分に拾ったファイルは出力に出ない（どの組み合わせでも結果が変わらない）。`--literal-pathspecs` は守りとして付け、3 か所すべてに付いていることを G5 で確かめ、1 か所外すと不合格になる FG-G5 を付けた。計画レビューのやり直し: 不要（テストの確かめ方の変更で、方式・範囲・受け入れ条件は変えない）

## レビュー結果
- [20261027_1526 判定: ✅ 完了](../../reviews/I202_plan_review_20261027_1526.md)
