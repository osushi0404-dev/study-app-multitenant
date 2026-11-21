# I599 レビュー: サンドボックスの中から scripts/claude/ に書いたスクリプトをレビュー前に外で流せる穴を塞ぐ

## 変更概要
-

## 変更点
-

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.claude/settings.json`・`.claude/hooks/`（新規）・`scripts/claude/hooks/pretooluse_guard.py`・`scripts/claude/code-review.sh`・`docs/runbooks/danger-ops.md`・`docs/runbooks/harness-audit.md`・`scripts/claude/tests/`

## テスト結果
- 自動: `test_i599_unreviewed_scripts.sh` pass=35・`test_settings_permissions.sh`・`test_i525_skill_sandbox_form.sh`・`test_i193_official_flow.sh`（G9b。F9 の 3 件は中で uv が書けない別件）・見張りの既存テスト合格。CI（Harness Tests ほか）成功。gate-check OK（2026-11-21）
- 手動: No.3・No.4・No.5 OK。No.1・No.2（子のセッションでの実測）は保留・マージの後に I593 で測る（docs/tests/open/I599_manual_test.md）

## 計画との差分
-

## ロールバック
- PR を revert する。`~/.cache/claude-reviewed-hooks/` は消してよい

## 振り返り

### かんたんなまとめ
- 良かった点: 第 1 版が収まらなかったとき、上限で止めて「止める場所・方式の見直し」を選べた。第 2 版は「既定は中・外は起動役だけ」という単純な規則で、レビュー 2 周・敵対的レビューで新しい穴 0 で収まった（理由: 読み取りの正確さに安全を頼らない形にしたため）
- 今回の問題への直接の対処: マージ前は本物の環境で「起動役が外に出るか」を測れなかった（子のセッションは古い見張りで動くため）。→ 静的な部分はテストで覆い、マージの後の実測を I593 に頼んだ
- 同じ問題を次回から防ぐ改善:
  - 外で動いていたスクリプトを中で動かすようにしたら、中でだけ見える偽のファイルや、中で書けない場所でつまずいた（テストの段階で見つかった）。→ 境目を動かすときは、動いたスクリプトを中で 1 回流して確かめる手順を手順書に足す（I610）
  - 書き方の規則を変えたのに、スキルに古い書き方が残っていた。→ 規則を変えるときは、書き手を全部機械で確かめるテストを計画に入れる決まりを足す（I610）
  - 第 1 版で、コマンドの文字列を読んで安全を決める方式に 6 周を使った。→ 計画レビューの段階でこの形を止める観点を足す（I610）

### 詳細
#### 良かった点
- 上限到達で「方式の見直し」を先頭の選択肢に出す決まりが効き、列挙で塞ぐ方式から既定を安全側にする方式へ切り替えられた
- TC-18 のような「書き手全体を判定に通す」テストで、スキルの古い書き方と外に出る型への当たりを機械で確かめられた
- test-gate の gate-check が、マージ後に全イシューを止める回帰（ふさぎの印）をマージ前に捕まえた

#### 是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | 予期しない問題 | 外に出る型とフックの設定はセッションの起動時に読まれ、子のセッションは写しの見張りで動くので、マージ前に本物の環境で測れない | TC-18 で静的な部分を覆い、手動 No.1・No.2 のマージ後の実測を I593 にコメント |
| C2 | セキュリティ | フックの起動役が無視されるファイルを数えない（F24）・gate-check の文字デバイスの除外がリンクも除く（F30） | I610 に起票（最優先） |

#### 予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| P1 | 予期しない問題 | 計画の影響範囲の洗い出しに「外から中へ移るスクリプトが、中でだけ見える物を読まないか・中で書けない場所に書かないか」の確かめが無かった | 外に出す型・外で動くスクリプトの一覧を変えるイシューの手順に、移るスクリプトを中で 1 回流して確かめる手順を足す（I610） | `docs/runbooks/harness-audit.md` または `docs/runbooks/plan-writing-rules.md` |
| P2 | スキル・規約 | 書き方の規則を変えるとき、その規則に従う書き手を全部確かめる手順が計画の書き方に無かった | 影響範囲の書き方に「書き手を全部集めて判定に通す決定論のテストを計画に入れる」を足す（I610 に同梱） | `docs/runbooks/plan-writing-rules.md` |
| P3 | 技術選択 | 「精密な判定は採らない」が fix-loop にだけあり、計画を書く段階・計画レビューの観点に無かった | 計画レビューの観点に「安全装置の合否をコマンド文字列の解析で決める計画は、既定の安全側＋単純な許可の一覧に置き換えられないかを問う」を足す（I610 に同梱） | `.claude/agents/plan-reviewer.md` |

#### 見送り
- PR へのレビューのコメント（`post-review-comment.sh`）を流せなかった: ハーネスのブランチでだけ起きる（R5）。記録はリポジトリにあり、マージ後は起きない
- 残余リスク処遇: R1（`updatedInput` の効き方）・R3・R4・R8（I600）・R10（I600）・R11 は計画書の 8 の表のとおり。R5 は I593 に引き継いだ

## 自律判断の記録
- [plan] 中で動かす範囲を「流すスクリプトから呼ぶファイルをたどって変更に届くときだけ」にした — イシューのメモの「1 つでも違えばすべて中」では変えていないレビュー役まで中で失敗し段階ごとに人の手が要る。ユーザーに確かめ、BP と開発効率で最善のやり方で、との判断（2026-11-20）
- [plan] 判定の本体を `.claude/hooks/unreviewed.py`、フックの起動役を `.claude/hooks/reviewed-hook.sh` に置いた — `scripts/claude/` の外でサンドボックスから書けず、判定を直しても呼び元が中に回らない
- [plan] `run-all.sh`・`test-session.sh` は直さず見張りの側で入口を扱う。`code-review.sh` のゲートの実走（計画の調査で見つけた入口）を範囲に足した — イシューの実装対象から変えた。理由は計画書 9
- [plan] スパイクで「フックの書き換えの後のコマンドで外に出すかが決まる」ことを確かめた（計画書の調査結果 6）
- [plan-review] 計画レビューの Warning 2・Info 1 を直した（R9 の追加・手動 No.5・TC-20）。方式・範囲・受け入れ条件は変えないので再レビューはしない — 計画変更記録のとおり
- [design-security-review] Blocker 0。Medium 4 件の必須の防御（名前の文字を絞る・引数の `=` の形・読み取りの上限・git の安全な -c）を計画書に書き、TC-21 と TC の追加で確かめる — 計画の方式は変えない
- [implement] 判定の読み込みは `sys.modules` に登録してから行う — ファイルの場所から読み込むモジュールの dataclass は登録が無いと作れず、初回は安全側（中で動かす）に倒れた
- [implement] 当たりの規則を「`bash` のすぐ後ろが scripts/claude/ のパス」に絞った — `grep … scripts/claude/…` のような読み取り（もともと中で動く）にまで印が出て邪魔だった
- [implement] `/simplify` の指摘を取り込んだ（引数の表を一般の規則に・git の回数を減らす・写しがあれば起動役は差を見ない・見張りの読み込み失敗時の規則を写さない・TC-22）。`code-review.sh` のゲートの前置きの照合を判定に寄せる指摘は見送った — `classify_gate` が `&&` などのつなぎを UNSAFE にするので、ゲートの行は 1 つのコマンドだけ
- [implement] 手動 No.5（`.claude/hooks/` に Bash から書けない）は実装中に確かめた — `.claude/hooks/unreviewed.py` を Bash の Python で直そうとして `Read-only file system` で拒否された
- [implement] 当たりの判定を、コマンドを語に分けて「`bash` のすぐ後ろが scripts/claude/ のパス」の区切りだけにした（TC-23）— コミットのメッセージに `bash scripts/claude/…` と書いただけで `git commit` が中に回り、pre-commit が `.claude/hooks/` に書けず失敗した。読み切れないコマンドは今までどおり中で動かす
- [review-gate] `code-review.sh` はこのブランチで直したので、見張りが中で動かす。計画の R7 のとおりユーザーに `!` で流してもらった。CI の Harness Tests が落ちた（フックの登録の古い書き方を確かめる既存のテスト 2 本: test_i187_frontend_verify_config.sh ⑦・test_sessionstart_context.sh TC-11g）ので fix-loop へ
- [fix-loop] CI の 2 本の失敗は、テストの期待値を起動役の形に替えて直した（案 A・差分が最小で意図を保つ）。診断レビュー PASS
- [fix-loop] F1・F2・F4 を直した。F2 は診断の案 A の 3（同じフォルダのファイル名を見る）を実装中に「git が無視するファイルを `ls-files --ignored --directory` で数える」に替えた — 変更が無いときの早く返す道でも効き、規則が単純（無視されるフォルダはまとめて数えないので遅くならない）。方式・範囲は変えない
- [fix-loop] F7・F8 を直した（診断の案 A）。台帳の F9・F10（Low）は止める指摘でないので直さず retro に回す
- [fix-loop] F11 は列挙を足さず、置き換え・かっこを含むコマンドを読み切らずに中で動かす単純な規則にした — F1・F7・F11 と同じ種類が 3 周続いた（列挙で塞ぐ方式の限界）。普段の呼び出しは変わらない
- [review-gate] review-gate ⇄ fix-loop が 5 回目（上限）に当たり止めて聞いた。指摘の種類: 「コマンドの書き方の読み取りの取りこぼし」（F1・F7・F11）と「安全側に倒しすぎて普段の呼び出しを壊す」（F12・F13）。ユーザーの判断（2026-11-20・原文）: 「ループエンジニアリング、ハーネスエンジニアリング、グラフエンジニアリングのベストプラクティスと開発をサクサク進める(開発効率)という観点でベストなやり方で進めて。」→ 推奨の「もう 1 周だけ直す（置き換え・かっこの規則を scripts/claude/ に変更があるときだけ効かせる・当たりはコマンドの先頭の形だけ）」で進める
- [fix-loop] F12 を直した（変更があるときだけ置き換え・かっこを中に・当たりはコマンドの先頭の形）。F13 も同じ原因なので同じ直しで消えた。F14・F15（Low）は止める指摘でないので retro へ
- [review-gate] 延長の 1 周の後も HIGH（F16・F17・F18）。種類は「漏れる」と「壊す」が交互（計画書の調査結果 5）。止めて聞き、方式の見直しを推奨した。ユーザーの判断（2026-11-20・原文）: 「ループエンジニアリング、ハーネスエンジニアリング、グラフエンジニアリングのベストプラクティスと開発をサクサク進める(開発効率)という観点でベストなやり方で進めて。」→ 推奨の「方式を裏返す（既定を中に・決まったスクリプトだけを起動役が外で動かす）」で計画を第 2 版に書き直し、計画レビューからやり直す
- [implement] 第 2 版を実装した。新しいファイルを作る道具が使えない時間があったので、起動役は判定と同じ `.claude/hooks/unreviewed.py` の `run` に置いた（計画変更記録）。見張りが自分の書き込み・コミットのコマンドを止めた・起動役の呼び出しを確認に回した問題を、実装中に直した（計画変更記録）
- [implement] /simplify（第 2 版・1 回にまとめた）: 判定の git を減らす・名前の確かめの重複を消す・見張りの説明を第 2 版に・ゲートの判定を 1 回に。見送り 2 件（失敗の道での判定の読み直し・test-session の基準の再計算。どちらも軽い）
- [fix-loop] F22 は案 A（スキルの呼び出しを単体の形に直し、TC-18 で機械で確かめる）・F23 は案 A（ワイルドカードを単体でない文字に）。診断レビュー PASS（`docs/reviews/I599_fix_diagnosis_review_20261121_1500.md`）— `route()` に包んだ形を読ませる案は第 1 版の精密な判定に戻るため採らない。`> "$DRAFT"` はスクリプトに書き出しを足さず Write ツールで下書きを作る（外で動くスクリプトに任意の場所へ書ける口を作らない）。`worktree.md` の `DANGER_OK=1`・`KEEP_DATA=1` の前置きは人が primary で流す危険操作で、第 1 版の前から外に出ない形なので直さない
- [review-gate] 敵対的レビュー 1 周目は新しい指摘 0・V6 だけ未検証（HIGH）。V6 は TC-18 で静的な部分を覆って「読んで可」に下げ、本物の環境の実測はマージの後に I593 で行う（計画変更記録）— マージ前は子のセッションが develop の見張りの写しで動き、起動役の `os.environ` を確認に回すので測れない。外に出ないときは終了 4 で止まる安全側の失敗で、人の手を使わずに進める（ユーザーの任せる指示・開発効率）
- [review-gate] 敵対的レビュー 2 周目 OK（`docs/reviews/I599_adversarial_review_20261121_1539.md`・未検証 0・新規 0）。PR へのコメント（`post-review-comment.sh`）は外で動く一覧のスクリプトで、ブランチにレビュー前の中身があると起動役が止めるので流していない（失敗しても止めない手順・記録はリポジトリにある・R5）
- [test-gate] gate-check.sh が REASON=dirty で落ちた。未追跡に出たのは `.bashrc`・`.claude/worktrees` など 17 件で、どれもサンドボックスがふさぐための文字デバイス（1,3＝/dev/null）。第 2 版で gate-check.sh が中で動くようになったための回帰（前は `bash scripts/claude/*` で外で動き見えなかった）。マージ後はすべてのイシューの test-gate が止まるので、コードの直しとして fix-loop に回す
- [fix-loop] gate-check.sh の NG は案 A（未追跡の文字デバイスを数えない・G9b と失敗注入）。診断レビュー PASS（`docs/reviews/I599_fix_diagnosis_review_20261121_1545.md`）。直した後、このセッションの gate-check はふさぎの印を出さなくなった
- [fix-loop] `test_i193_official_flow.sh` の F9 の 3 件（`run-all.sh`）は、中で uv がキャッシュ（`~/.cache/uv`）に書けず exit 2 になるためで、今回の直しと無関係（CI では起きない）。ただ「第 2 版で外から中に移ったスクリプトが、中で書けない場所に書く」という同じ種類の影響なので、retro で後続に回す（直すとこの fix-loop の範囲を超える）
- [review-gate] gate-check の直しの後、基本レビュー OK（F30〜F32 は止めない指摘・retro へ）。敵対的レビューは通算 2 周を使い切っていたので延長を提案し、ユーザーが `! bash scripts/claude/adversarial-review.sh --round-limit 3 "I599"` を打った（2026-11-21・打ったことを延長の承認として扱う）。3 周目 OK（`docs/reviews/I599_adversarial_review_20261121_1602.md`）
- [test-gate] 手動 No.1・No.2（子のセッションでの実測）は保留にし、マージの後に I593 で測る。No.3・No.5 は OK — 子のセッションはこのブランチでは写しの見張り（develop）で動くので、No.1 は測れない（R5）。No.2 も子のセッションを起こすのに人の `!` が要る。静的な部分は TC-18・S23・S24 で確かめた。外に出ないときは終了 4 で止まる安全側の失敗で、手動テストの NG ではない
- [retro] 台帳の残り: F24・F30 → I610（#610・「次のハーネスの作業で最優先」）。F5・F6・F9・F10・F25・F26・F27・F28・F29・F31 → `docs/reviews/backlog/I599.md`。F32 は計画変更記録に 1 行足して直した
- [retro] 改善案の振り分け: 外から中へ移ったスクリプトの確かめ（gate-check・run-all）→ 起票 I610（#610）／規則を変えたら書き手を機械で確かめる・安全装置を文字列の解析に頼る計画を計画レビューで止める・pre-commit の end-of-file-fixer が読み取り専用で落ちる → I610 に同梱（コメント）／手動 No.1・No.2 のマージ後の実測 → I593 に同梱（コメント）／PR へのレビューのコメントを流せなかった（R5）→ 見送り（マージ後は起きない・記録はリポジトリにある）

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate

- [review-gate] 第 2 版の 1 回目の基本レビューは HIGH（止める指摘 F22・F23）。fix-loop へ回す（実装をやり直した後の 1 回目）
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
STAGE_DONE: retro NEXT: close
