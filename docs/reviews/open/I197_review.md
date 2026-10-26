# I197 レビュー: 実装の検証（レビュー）の仕組みを白紙から作り直す

## 変更概要
- 敵対的レビューを、裏で動くサブエージェント＋15 分のタイマーから、スクリプト `scripts/claude/adversarial-review.sh` が起動する別プロセス（読むだけのレビュー役 3 観点・実験役は auto＋承認なし）に作り直す
- 計画の段階で「必ず確かめる項目」の一覧を作り、項目ごとの結果（実験で確認／読んで確認／未実施）から判定を決定論で出す。未検証・報告なし・時間切れ・拒否は合格にしない
- 全部の `claude -p` の検証に `--permission-prompts none`（承認が要る操作は待たずに拒否して記録）
- （実装後に更新）

## 変更点
- （実装後に記入）

## 影響範囲
- ハーネス（`.claude/`・`scripts/claude/`・`docs/runbooks/`・テンプレート）。アプリのコード・DB・`.claude/settings.json`・見張りは変えない

## テスト結果
- gate-check: OK（`I197_code_review_20261027_0140.md`・VERDICT OK・REVIEWED_COMMIT 36d24b1 以降は記録の場所だけ）
- CI: review-gate の 3 周目で全ジョブ OK（Harness Tests を含む）。test-gate に回された重いテストは無し
- 手動テスト（すべて Claude）: No.1〜5 OK（`docs/tests/open/I197_manual_test.md`）。No.1 は新しい敵対的レビューを I197 自身に通し、人の応答待ち 0・188 秒・11 項目すべて確認済み・VERDICT OK（`I197_adversarial_review_20261027_0153.md`）。No.5 で台帳が 4 → 1 → 0 で収束したことを確かめた
- 判定の記録: check-frontend-evidence は対象外（frontend/src を変えていない）・check-manual-test-executor は合格

## 計画との差分
- （実装後に記入）

## ロールバック
- PR を revert する（計画 §7）

## 振り返り

### かんたんなまとめ

**良かった点**
- 敵対的レビューが黙って止まらなくなった。実際の Claude で I197 自身に通して、人の応答待ち 0・188 秒・確かめる項目 11 件すべての結果が記録に残った（理由: レビュー役は読むだけ・実験は別の Claude が承認なしで実行・合否は一覧から機械的に決める、という作りにしたため）
- レビューが収束する形になった。途中から入れた「台帳」と「直した差分だけを見るやり直し」で、止める指摘が 4 件 → 1 件 → 0 件と周ごとに減って終わった（理由: 以前はやり直すたびにブランチ全体を一から探し直していて、前の周に見ていなかった穴が毎回出ていた）
- 実装の前に組み込みのレビューを「計画書だけの範囲」で試したら、新しい設計の穴を 10 件先に見つけられた（理由: 範囲を渡せるかの確認が、そのまま設計のレビューにもなった）

**今回の問題への直接の対処**
- 台帳に残った Medium・Low の指摘（F5〜F19）と、整理のときに見送った重複の共通化が残っている。止める基準（High 以上）より軽いので I197 では直していない。→ まとめて 1 つの後続イシューで片付ける（新しく起票）

**同じ問題を次回から防ぐ改善**
- 手元のテストが CI と食い違い、CI で 3 回落ちた。① 手元に shellcheck が無いと、その検査が黙って飛ばされて「合格」に見えた ② 直したところに関係するテストを記憶で選び、文章を固定しているテストを取りこぼした。→ 「変えたファイルの名前から関係するテストを機械的に選んで流すスクリプト」と「shellcheck が無いときは飛ばさず不合格にする（または pre-commit が入れたものを使う）」を足し、fix-loop・implement の手順から呼ぶ（新しく起票）
- 見送り: 新しいスクリプトの本体を丸ごと動かすテストが無く、実際のレビューで初めてスクリプトが止まった — その場で捕まり、丸ごと動かすテスト（R14）も足して手戻りは小さかったため、手順は足さない

### 詳細版

#### 良かった点
- 敵対的レビュー: 別プロセス・読むだけ・実験役は auto＋承認なし・一覧から決定論の判定。手動 No.1 で人の応答待ち 0・188 秒・V1〜V11 確認済み・VERDICT OK（`I197_adversarial_review_20261027_0153.md`）
- 基本レビュー: 台帳（累積）＋差分のレビュー＋Blocker/High だけ止める＋高リスクは計画の段階。台帳の 1 周目 F1〜F4（High）→ 2 周目 F2 だけ → 3 周目 0 で OK（手動 No.5）
- スパイク S6 で組み込み `/code-review` の範囲指定を確かめ、同時に §4.8 の設計の穴 10 件を実装前に拾えた（計画変更記録 9）
- FG（壊すと落ちること）が空振りしていたのを見つけて、写しが作れないときは全体を不合格にする形にした（TC-01・TC-09）

#### 是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | ベストプラクティス・セキュリティ | 台帳の止める基準（High 以上）より軽い指摘は直さない設計なので、Medium・Low が台帳に残る（F5: 計画の見立てを超えた認可・テナント境界の変更が敵対的レビューに入る経路・F6 並列の実験の汚染・F7 adversarial の review_base の祖先確認・F8 拒否件数の 0 件化・F9 parse_findings のデッドコード・F10 連番の並び・F11 表の中だけの High・F12 同じ番号の重複・F13〜F15・F16 大文字小文字・F17〜F19）。/simplify で見送った共通化（記録の探し方・REVIEWED_COMMIT の読み方・ブランチが変えたファイルの定義を gate-check.sh・adversarial-review.sh と共有・set_risk_line と add_reviewed_commit・範囲が空の差分のレビューの近道）、敵対的レビューの記録の「報告あり（）」の表示 | 後続イシュー（新規起票）で、SECURITY=yes の F5・F16 を先に、残りはまとめて片付ける |

#### 予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| P1 | プロセス・スキル | 手元のテストの選び方と道具の有無が CI と食い違っても、手元では「合格」に見えた（道具が無い検査は黙って SKIP・関係するテストは記憶で選ぶ）。CI で初めて落ち、往復が 3 回増えた | ① 変えたファイルの名前で `scripts/claude/tests/` を検索して関係するテストを選んで流すスクリプトを足し、implement・fix-loop の「テストを流す」手順から呼ぶ ② shellcheck など CI が使う道具が手元に無いときは、SKIP せず不合格にするか、pre-commit が入れたものを使う | `scripts/claude/`（新規スクリプト）・`.claude/skills/implement/SKILL.md`・`.claude/skills/fix-loop/SKILL.md`・`scripts/claude/tests/test_review_commit_lifecycle.sh` |

#### 5 Whys
**レビューが収束しなかった（I197 で根本対応済み）**
- Why 1: やり直しのたびに新しい High が出た → Why 2: やり直しがブランチ全体を一から探し直していた → Why 3: 「どこまで確かめたら終わりか」を先に決めず、終わりの条件が無いループだった
- 根本原因: 検証のループに、終わりの条件（台帳）と、やり直しの範囲（直した差分）が無かった。→ §4.8 で直した（予防は実装済み）

**手元のテストが CI と食い違った（P1）**
- Why 1: CI で初めて落ちた → Why 2: 手元ではその検査を流していなかった（道具が無く SKIP／テストを記憶で選んだ） → Why 3: 手元で流すテストの選び方と道具の有無が、機械的に決まっていなかった
- 根本原因: implement・fix-loop の「テストを流す」手順に、関係するテストの決定論の選び方と、道具が無いときの止まり方が無かった。抽象化テスト: 特定のテスト名・ツール名を除いても成立する → 予防処置

#### 見送り
- 本体を丸ごと動かすテストが無かった（set -e の誤りが実際のレビューで出た）: その場で捕まり、R14 を足して手戻りは小さい。手順・観点は足さない（`feedback_retro_no_rule_inflation`）
- PC のスリープで 13 時間止まった: 仕組みの問題ではない
- 確認の PATH の取り違え（pre-commit の仮想環境の python）: 一回きりの手違いで、P1 のスクリプトで道具の選び方を決めれば起きない

#### 残余リスク処遇
- security-review（組み込み）は高リスク判定 NO（パス NO）のため走っていない。設計段階の design-security-review も対象外。台帳の SECURITY=yes の Medium（F5・F16）は C1 の後続イシューで先に扱う

## 自律判断の記録
- [plan] I197 は track:harness だが app-1 で計画した — `docs/runbooks/worktree.md` §10「ワークツリーはトラックに固定しない」。ユーザーが app-1 で /plan-issue を実行した
- [plan] 「親が実験を実行」は、親の会話ではなく、スクリプトが起動する実験役の別プロセス（auto＋承認なし）で行う — 親の会話で実行すると確認画面で人を待ちうる。設計確認メモの形（レビュー役は読むだけ・実験は別が実行）は変えない（計画 §9）
- [plan-review] 1 回目 BLOCKER 2 件（一覧の見出し・差分の受け渡し）を直して 2 回目 OK。2 回目の Warning のうち FG の追加・S1 の論理行・数の訂正は直し、再レビューはしない — 方式・範囲・受け入れ条件を変えないため（計画変更記録 2）。高リスク判定 No なので design-security-review は通らない
- [implement] I194（#328）を GitHub でコメントして not planned で閉じた — 設計確認メモでユーザーが決めた統合・取り下げ（計画 §4.6）。I194 のイシューファイルは harness-2 にあり、このセッションからは触らない
- [implement] 07:23〜20:32（JST）の約 13 時間、作業が止まっていた — 記録では、Claude の次の返事を作る通信を出したまま進んでいない。ユーザーによると PC のスリープ。確認画面やテストの待ちではない
- [implement] /simplify（4 観点）の指摘のうち、動きを変えない整理（既定値の一元化・run_step・exp_ids の廃止・判定の分け方・テストの重複）は直した。費用の列を記録に足した。範囲を外れる・方式を変える指摘は見送り、retro で扱う（計画変更記録 3）
- [review-gate] 基本レビュー 1 回目は CI の Harness Tests が失敗（test_review_commit_lifecycle.sh の TC-C1-shellcheck。手元に shellcheck が無く、手元の run-all ではこの項目が通っていた）— 手順どおり fix-loop へ
- [fix-loop] 案 A（読み込み行に `disable=SC1091` を足す）で直した。診断・実装・テストのレビューはすべて PASS。直したファイルは 2 本なので軽微例外は使わなかった — 既存の書き方と同じで挙動を変えない。手元と CI の検査の食い違い（手元に shellcheck が無いと黙って SKIP）と、コメントだけの修正にも 3 つのレビューがかかる重さは、ユーザーとの対話（10-26）を踏まえて retro で扱う
- [review-gate] 基本レビュー 2 回目（`I197_code_review_20261026_2124.md`）は BLOCKER（Blocker 1・High 1・Medium 6・Low 2。RISK: NO で敵対的レビューの対象外）— fix-loop へ（review-gate ⇄ fix-loop は 2 回目）
- [fix-loop] 2 回目は診断メモ `I197_fix_diagnosis_20261026_2140.md` の推奨案で、指摘 1〜5・7〜9 を直した（診断・実装・テストのレビューはすべて PASS）。指摘 6（非ゼロで終わった実験を未検証にする）は採らなかった — 反証の実験は非ゼロの終了を期待する形が多く、誤った未検証が増える。結果の解釈はレビュー役の読みで、出力は記録に残る。指摘 10 は retro
- [review-gate] 基本レビュー 3 回目（`I197_code_review_20261026_2159.md`）は HIGH（High 1・Medium 6・Low 2）— fix-loop へ（3 回目）。直すのは High 1 と、それに直結する Medium 3（コマンド末尾の改行で「呼ばれなかった」になり周を空費・last_tool の欄ずれで記録が誤る・実験が記録の場所〔計画書・過去の記録〕を書き換えても気づかない）。見送り: 非ゼロ終了の区別（2 回目で採らない判断済み）・auto の関門の記録（計画 §8 に記載済み・手動 No.2 で確かめる）・最後の比較の後の子プロセス（全観点の wait の後に比べており、残るのは timeout 後の孫プロセスだけで普通の書き方の事故の範囲外）・Low 2 件（retro）— `feedback_fixloop_not_excessive`
- [fix-loop] 3 回目は診断メモ `I197_fix_diagnosis_20261026_2210.md` で直した。診断レビュー 1 回目は差し戻し（status の文字列の比較では、起動前から変更済みの計画書の上書きを見逃す。正しい指摘）→ 中身のハッシュも比べる案に直して PASS。実装・テストのレビューは PASS
- [fix-loop] 手元の全体のテスト（run-all）は流さず、直したところの TC-01 だけを流した — push の後に CI の Harness Tests が同じものを流し、review-gate がその合格を待つため（ユーザーの指摘 10-26「意味あるか？」）。手元で全体を流すのは、push の前に失敗に気づける見込みが高いときだけにする
- [review-gate] 基本レビュー 4 回目（`I197_code_review_20261026_2347.md`）は HIGH（High 2・Medium 4・Low 3。RISK: YES）— fix-loop へ。review-gate ⇄ fix-loop は 4 回目なので、決まりどおり直すのは High 2 件だけにし、Medium・Low は retro に回す（実験 id の上書きの拒否・実験役の時間の取り分・背景の実行の timeout の明示・拒否を読めないときの「不明」・ignored のファイル・auto が使えない環境・記録の走査の共通化）。直した後は敵対的レビューの段階へ進む
- [fix-loop] 4 回目は High 2 件だけを診断メモ `I197_fix_diagnosis_20261027_0000.md` で直した（診断・実装・テストのレビューはすべて PASS）。High 2（見張りのブロックが permission_denials に入らないおそれ）は、実際の claude で試して（スパイク S5）入ることを確かめたうえで、出力の形の変化に備える二重の守りだけを足した。あわせて、TC-01 の FG-A16 が置き換え前の文字列の不一致で空振りしていたのを見つけ、FG の写しが作れないときは TC-01 全体を不合格にする形にした
- [review-gate] 5 回目の基本レビューを途中で止めた — ユーザーの指示（10-27「レビュー構成の見直しをしているのに悪化している。レビューが正常化するように根本解決したい」）で、基本レビューと fix-loop を収束する形に作り直すことにしたため（古い形の結果になる）。範囲は I197 に含める・差分の外の新しい指摘はセキュリティの Blocker だけ止める、はユーザーが選んだ（設計確認メモに追記）
- [plan-review] 計画変更記録 7 の計画レビュー（`I197_plan_review_20261027_0016.md`）は OK。Warning 4 件は計画変更記録 8 で直し、再レビューはしない（方式・範囲・受け入れ条件を変えない）。組み込み `/code-review` に範囲を渡せるかは、実装の前にスパイク S6 で確かめる
- [implement] スパイク S6 は成立（範囲のファイルだけを見た）。範囲が計画書だったので組み込みのレビューが §4.8 の設計の穴を 10 件出し、9 件を実装の前に計画へ取り込んだ（計画変更記録 9）。I197 の高リスク判定は計画レビューの「No」のまま（I181 の方針どおり。4 周目の YES は揺れ）
- [implement] §4.8 を実装した（台帳・差分のレビュー・Blocker と High だけ止める・高リスクは計画の段階・fix-loop の実装/テストのレビューと 4 ファイルを削除）。/simplify（1 観点 5 分の上限）の指摘のうち、判定の重複（止める指摘）・記録の書き換えの重なり・使わない RISK 行・使わない引数は直し、gate-check.sh との共有は範囲外として retro に回した（計画変更記録 10）。手元では関係するテストだけを流した
- [fix-loop] 5 回目（§4.8 の後の CI の失敗・test_i185_harness_docs の固定の文章）は、テストを新しい fix-loop の文に合わせて直した（診断レビュー PASS）。手元の関係するテストは、変えたファイルの名前で検索して 16 本を選んで流した（記憶で選んで取りこぼした反省）
- [review-gate] 新しい code-review.sh が CI_WAIT: OK の後に理由を出さずに止まった（set -e の下の `$( [ … ] && … )`）。review-gate の「それ以外の exit 1」として、直せる原因なので直して実行し直す。あわせて追加した本体を丸ごと動かすテスト（R14）が、同じ分の 2 回目の実行で前の記録を上書きして台帳を失う不具合も見つけたので直した（auto_test の再発防止記録）
- [review-gate] 新しい仕組みの全体のレビュー（`I197_code_review_20261027_0102.md`・台帳の 1 周目）は HIGH。台帳は F1〜F10（High 4・Medium 3・Low 3）。fix-loop で直すのは止める指摘の F1〜F4 だけ。Medium 以下（F5〜F10）は台帳に残り retro で扱う
- [fix-loop] F1〜F4 を診断メモ `I197_fix_diagnosis_20261027_0110.md`（診断レビュー PASS）の推奨案で直した。どれも「迷ったら止めない側」の経路を止める側に倒す粗い規則。F1 の修正で、前の周に範囲の外だった指摘でも、その周に該当ファイルを直していれば新しい指摘として止める（R6 の期待を合わせた）
- [review-gate] 差分のレビュー（`I197_code_review_20261027_0118.md`・台帳の 2 周目・範囲 4 ファイル）は HIGH。止める指摘は F2 だけ（F1・F3・F4 は resolved）。新しい F11〜F15 は Medium・Low で止めない。止める指摘は 4 → 1 に減った（収束している）
- [fix-loop] F2 は、形を列挙せずリポジトリからの相対パスに揃える粗い規則で直した（診断メモ `I197_fix_diagnosis_20261027_0125.md`・診断レビュー PASS）
- [review-gate] 差分のレビュー（`I197_code_review_20261027_0140.md`・台帳の 3 周目・範囲 2 ファイル）は OK。F2 は resolved、新しい F16〜F19 は Medium・Low で止めない。止める指摘は 4 → 1 → 0 で収束した（§4.8 の実地の確認・手動 No.5）。高リスク判定 NO（計画レビュー No・パス NO）なので敵対的レビューのステージは無し。敵対的レビューの実地の通し（AC6）は test-gate の手動 No.1 で行う
- [test-gate] 手動テスト No.1〜5 はすべて Claude が実施し OK。No.1 の記録で「報告あり（）」と空の括弧が出る見た目の不具合を見つけた（note のファイルが改行だけでも中身ありと判定）。判定には影響しないので直さずに retro で扱う（この段階はコードを直さない）
- [retro] 改善案の振り分け: 予防 P1（手元のテストの選び方・CI の道具の有無の食い違い）→ 新規起票 I201（#337。実害あり〔CI で 3 回落ちた〕・同梱先が無い・決定論のスクリプトで直せる）。是正 C1（台帳の Medium・Low〔F5〜F19〕と見送った共通化）→ 新規起票 I202（#338。セキュリティの F5・F16 を含む・同梱先が無い）。見送り: 本体を丸ごと動かすテストが無かった（その場で捕まり R14 を足して手戻り小）・PC のスリープ（仕組みの問題でない）・PATH の取り違え（P1 で起きなくなる）。イシューファイル I201・I202 は未コミットのまま（各自の /plan-issue が初コミットする）

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
STAGE_DONE: retro NEXT: close
