# I225 レビュー: GitHub の鍵が画面に出る・漏れたときの手順と、テスト用のセッションの抜け道を塞ぐ

## 変更概要
- `gh` の入口が、`--json` なしの `auth status` を鍵の出ない表示に置き換える。手順書などへの書き戻しは CI（G10）で止める
- 鍵が出たときの失効をスクリプト `revoke.sh` にした（控えの 2 つ・`--stdin` で控えに無い鍵）。失効は HTTP 401 で確かめる
- テスト用のセッションの起動にすべて `--strict-mcp-config`、tmux の中の `claude` に入口のある `PATH` を渡す

## 変更点
- `scripts/claude/gh-app/gh`（auth status の置き換え）・`scripts/claude/gh-app/revoke.sh`（新規）
- `scripts/claude/` の起動の行: `code-review.sh`・`review-process-lib.sh`・`issue-review.sh`・`plan-issue-review.sh`・`fix-review-lib.sh`・`test-session.sh`・`check-permission-prompt.sh`・`tui-capture.sh`（`adversarial-review.sh` の重複した `--strict-mcp-config` を消した）
- テスト: `test_i223_gh_app.sh`（G7〜G10・g6/g7 の共通化）・`test_tui_capture.sh`（T1・FG-T1b・FG-T8）
- 手順書: `github-app-setup.md`（1.・5.・漏れたときの手順）・`harness-audit.md`（古い鍵の点検コマンド）
- 台帳: `backlog/I223.md` の F11・F12、`backlog/I195.md` の F5 を消した

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `scripts/claude/gh-app/`・`scripts/claude/` の Claude の起動の行・`scripts/claude/tui-capture.sh`・`scripts/claude/tests/`・`docs/runbooks/github-app-setup.md`・`docs/runbooks/harness-audit.md`

## テスト結果
- 自動: review-gate（fb4b563a）で CI 全緑・決定論ゲート 6 本とも exit 0（`test_i223_gh_app.sh` 33/33 ほか）。TC-03 OK
- 手動（test-gate・22ae10d4）: M-01〜M-04 すべて OK（すべて Claude。Human の項目なし）

## 計画との差分
- なし

## 振り返り

### かんたんなまとめ
- 良かった点:
  - 鍵を出す書き方を、打った時（入口の置き換え）と書いた時（CI の検査）の 2 か所で、機械的に止められるようになった（理由: 決まりを読んで守るだけの形だと、I223 のように手順書へ書き戻されて再発するため）
  - 計画レビューが「控えに無い漏れた鍵が失効しない」穴を実装の前に見つけ、`--stdin` を足してから作れた（理由: 実装後に見つかると、作り直しとレビューのやり直しが要る）
  - テストを先に書き、手順書に残っていた鍵を出す書き方をその検査で見つけてから直せた
- 今回の問題への直接の対処:
  - 自動テスト文書の見出しが決まりの形と 1 語違い、レビューが「テストの宣言なし」と判定して 1 回差し戻された。前のイシューの文書を見て書き、ひな形から作らなかったため。→ 見出しを直してレビューを通し直した（レビューの機械的な判定がその場で捕まえ、直しは 1 行で済んだので、新しい手順は足さない）
- 同じ問題を次回から防ぐ改善:
  - レビューで止めなかった指摘のうち、セキュリティに関わる 3 件（失効の表示の取り違え・控えを消すときの競合・検査の取りこぼし）を、後続のイシュー I226（#417）にまとめて起票した。止める条件には当たらないが、鍵の扱いの穴なので次のハーネスの作業で最優先にする

### 詳細
- 良かった点: 上のとおり
- 是正処置（Corrective）

| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | 予期しない問題 | 自動テスト文書をひな形（`docs/tests/templates/auto_test_template.md`）からでなく前のイシューの文書から作り、決定論ゲートの見出しが違った | fix-loop で見出しを直した（診断メモ 20261106_0100・review-gate 2 回目 OK） |

- 予防処置（Preventive）

| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| P1 | セキュリティ（台帳の残り） | 鍵を扱うスクリプトの「確かめた」の表示が、前の状態（もともと有効だったか）を確かめていない・控えの読み書きに排他が無い・静的な検査の対象が 1 つのコマンドの書き方に限られる | 後続イシュー I226（#417）で直す（次のハーネスの作業で最優先） | `scripts/claude/gh-app/revoke.sh`・`scripts/claude/tests/test_i223_gh_app.sh` |

- 5 Whys（C1）:
  - Why 1: なぜ review-gate が HIGH にしたか → auto_test の見出しがスクリプトの探す文字列と違い、ゲートが「宣言なし」になった
  - Why 2: なぜ見出しが違ったか → ひな形ではなく前のイシュー（I223）の文書の形を見て書いた（I223 の文書はゲートの節の見出しが違う形だった）
  - Why 3: なぜ計画の段階で気づかなかったか → plan-issue の文書品質ゲートは、見出しがスクリプトの読む形かを機械的には見ていない。見るのは review-gate の omission-lint が最初
  - 根本原因: 決まった見出しを機械が読む文書を、ひな形以外から作れてしまう。ただし review-gate の決定論の判定がその場で捕まえ、手戻りは 1 行の直しと 1 回のレビューだけだった
- 2.7 の判定:
  - C1 の予防（plan-issue で omission-lint を先に流す・plan-reviewer の観点に足す）: 見送り — 既存の決定論の判定（review-gate の omission-lint）がその場で捕まえ、手戻りは小さい。同じ穴を 2 つの工程で塞がない
  - 計画レビューの Blocker（控えに無い鍵）: 見送り — 計画レビューがその場で捕まえ、実装の手戻りは無い
  - 総点検の点検コマンドの `env -u` が見張りに止められた件: 見送り — 計画の段階の試しで見つけ、別の書き方に直して手戻りは無い
  - /simplify の直す深さの指摘（Claude を起こす行を 1 つの入口にまとめる）: 見送り — 実害（付け忘れによる漏れ）は出ておらず、G6・G7 が付け忘れを CI で止める。8 か所の起動の形と既存のテストを作り直す大きさに見合わない。I226 のスコープの「含まない」に判断を残した
  - 台帳の F7（ゲートの証跡が無い）が 2 周目でも STATUS=open のまま: 見送り — 2 周目の記録の先頭に 6 本の exit 0 の証跡があり、指摘の中身は解消済み。台帳の閉じ方の件は再現が 1 回だけで、`code-review.sh` を触る他のイシューで再発したら扱う

## ロールバック
- PR を revert し、`bash scripts/claude/gh-app/install.sh` を流し直す（前の版は `~/.cache/github-app/backup/`）

## 自律判断の記録
- [plan] 失効の手順をスクリプト `scripts/claude/gh-app/revoke.sh` にし、控えの 2 つの鍵を直接失効させて確かめる — 手順書の散文では取り違え（F13）が起きる。1 コマンドなら偽物の `gh` でテストできる
- [plan] 静的な検査（G10）の対象を、決まりの置き場（手順書・スキル・エージェント・スクリプト・テンプレート）に絞り、個々のイシューの記録を外した。イシューの受け入れ条件 2 も同じ範囲に直した — 計画・テスト文書は置き換えを確かめるために `--json` なしの書き方を名指しする必要があり、打っても入口が置き換える。I223 の事故の元の手順書は対象に入る
- [plan] 総点検の点検コマンドは `env -u GH_APP_READONLY` でなく `GH_APP_READONLY=`（空）にした — 計画の段階で流したら、ワークツリーの見張りが `env` の形を止めた。入口は空を「指定なし」と読む
- [plan] GitHub への書き込みをまとめた: ブランチの push・Draft PR の作成は、計画の記録を全部コミットしてから 1 回で行う（I224 の当面の運用。段階ごとに push しない）

- [plan-review] 1 回目の Blocker（控えに無い漏れた鍵が失効しない）は revoke.sh --stdin を足して直し、2 回目で OK。残りの Warning 3 件は計画変更記録 2 で直し、再レビューはしない — 方式・範囲・受け入れ条件を変えない直しのため
- [implement] 失効の確かめを「読みに行って失敗」でなく「HTTP 401 が出る」にした（計画変更記録 3） — 通信の失敗を「無効」と取り違えて控えを消さないため。本物の `gh` で 401 の文言を確かめた
- [implement] `--strict-mcp-config` を置く位置を、既存のテスト（S1・FG-S1）が前提にする形に合わせた（`"$@"` の前・`--permission-prompts none)` の前・複数行の呼び出しは 1 行目） — テストを直すより起動の行を合わせるほうが変更が小さく、既存の守りをそのまま使える
- [implement] /simplify の指摘のうち、G6・G7 の重複（共通の関数にした）と G9 の使わない代入を直した。見送り: 起動を 1 つの入口にまとめる案（直す深さの指摘。8 か所の起動の形と既存テストを作り直すことになり、計画の方式を変えるので retro で扱う）・控えの名前と形を共通のファイルにまとめる案（`revoke.sh` の名前の一覧は FG が守り、控えの形は 1 か所でしか書かない）・G10 を狭める案（計画 §9 で決めた範囲）・失効を並行にする案（効果が 1 秒未満）
- [review-gate] 1 回目は FINAL_VERDICT: HIGH。止める指摘は 0 件で、HIGH は自動テスト文書の決定論ゲートの見出し違い（宣言なし・omission-lint）によるもの。決まりどおり fix-loop に回した — 判定はスクリプトの決定論の出力に従う
- [fix-loop] 見出しを `## 決定論ゲート（自動実走）` に直した（診断メモ 20261106_0100 の案 A・診断レビュー PASS） — テンプレートどおりの 1 行の直しで、次の review-gate がゲートを実走して証跡を残す。台帳の F1〜F7 は止める指摘ではないので直さない（retro）
- [retro] 台帳の残りの振り分け: F1・F5・F6（SECURITY=yes）→ 後続イシュー I226（#417・次のハーネスの作業で最優先）／F2・F3・F4（Low）→ `docs/reviews/backlog/I225.md`／F7 → 振り分けない（fix-loop の見出しの直しで解消済み。2 周目の記録にゲート 6 本の exit 0 の証跡がある。台帳の STATUS だけが open のまま） — 台帳の行の欄の値で `code-review.sh --route` が振り分けた結果に従い、F7 だけ中身が解消済みのため除いた
- [retro] 改善案の振り分け: 是正 C1 は fix-loop で直し済み。予防は P1 を I226 で起票。見送り 5 件（自動テスト文書の見出しの予防・計画レビューの Blocker・`env -u` の件・起動を 1 つの入口にまとめる案・台帳の F7 の閉じ方）は「## 振り返り」の 2.7 の判定に理由を書いた — どれも既存の工程がその場で捕まえ手戻りが小さいか、実害が出ていないため
- [retro] I226 のイシューファイルは未コミットのまま app-1 に残した（plan-issue の初コミットの決まり）
- [close] 最初の push と PR の説明の更新が GitHub に拒まれた（`fatal error in commit_refs`・`EOF`。読み取りは通り、githubstatus は Operational）。書き込みを重ねず 2 回で止めてユーザーに伝え、時間を置いて 1 回だけやり直して通った — 書き込みの集中で名義が止められるおそれ（I224）を避けるため

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
STAGE_DONE: retro NEXT: close
STAGE_DONE: close NEXT: merge
