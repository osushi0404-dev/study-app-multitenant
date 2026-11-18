# I432 レビュー: Dependabot #377（@playwright/test 1.64.1）で E2E が落ちる原因を直して取り込む

## 変更概要
- CI の E2E のジョブの Node.js を 18 → 26 に上げ、`@playwright/test` を 1.59.1 → 1.65.1、手元の E2E のコンテナのイメージを v1.65.1-jammy に上げる。#377・#376 は取り込み済みとして閉じる（計画: docs/plans/open/plan_I432.md）

## 変更点
- `.github/workflows/e2e.yml`: `node-version` '18' → '26'（1 行だけ）
- `e2e/package.json`・`e2e/package-lock.json`: `@playwright/test` 1.59.1 → 1.65.1（lock は `@playwright/test`・`playwright`・`playwright-core` の版・integrity・engines と、1.65 で外れた任意の依存 `fsevents` の削除だけ）
- `docker-compose.yml`: e2e のイメージを `v1.65.1-jammy@sha256:b0ee5ce5…6dd8`（#376 と同じ値）
- `docs/runbooks/frontend-verify.md:13`: `playwright@1.65.1`
- `rules/react-coding-standards-integrated.md:207`: §16 の #551 の行に E2E のジョブを対象外とする文言

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.github/workflows/e2e.yml`・`e2e/package.json`・`e2e/package-lock.json`・`docker-compose.yml`（e2e のイメージ）・`docs/runbooks/frontend-verify.md`・`rules/react-coding-standards-integrated.md`（§16 の #551 の行の文言）

## テスト結果
- 自動: TC-01 pass=17 fail=0・TC-02 pass=54 fail=0・TC-04 npm audit 0 件（implement）。TC-03 は CI（review-gate）
- 手動: Claude 5 件すべて OK（CI の E2E は Ubuntu 26.04・Node.js v26.13.1・19 件すべて合格・flaky なし／ほかの CI 全部合格／手元の新しいイメージで 1.65.1・ブラウザ同梱／1.59.1 の残りなし／#377・#376 を閉じた）。Human の項目なし

## 計画との差分
- なし

## ロールバック
- PR #575 の revert（設定とロックファイルだけ）

## 自律判断の記録
- [plan] 取り込み方は「このブランチで同じ版上げ・#377/#376 は閉じる」にした — Node.js とイメージと npm の版を 1 本の PR でそろえて確かめられ、#377（1.65.0）と #376（1.65.1）の版のずれも無くせるため（計画書 §9）
- [plan] E2E のジョブの Node.js は 26（規約 §0）にし、画面の Node.js 18 は #551 に残した — E2E のジョブは `e2e/` の別の package で画面と別に動き、規約 §16 の #551 の行は画面のコードとの差の表と読んだため（計画書 §9）
- [plan] 1.65 での E2E の事前の確かめは手元でせず CI に任せた — 手順書の `RATELIMIT_ENABLE=false docker compose …` は前置きがあるためサンドボックスの外で動く対象に当たらず `.env` を読めずに止まった。前置きなしではログインの制限で落ちる（計画書 §1 スパイク）。手順書の形がサンドボックスの中で動かないことは retro で扱う
- [plan] `.github/` を変えるが止めて聞かずに進めた — 変えるのは Node.js の版の 1 行だけで守りを緩めない（TC-01・TC-02）。直し方は grill-me の報告でユーザーに示した後に `/plan-issue` が打たれ、マージはユーザーが承認する（計画書 §9）
- [plan] #377・#376 を閉じるのは test-gate の手動 No.5 にした — CI が緑と確かめた後に行い、AC4 を close の前に満たすため
- [plan-review] 判定 HIGHRISK（`.github/workflows/e2e.yml`）。Warning 3 件（規約 §16 の文言・No.4 の判定コマンド・TC-28 以外の flaky の扱い）は計画書・手動テストを直して対応し、再レビューはしない — 方式・受け入れ条件を変えない findings への対応のため（計画変更記録）
STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
- [design-security-review] Blocker・High・Medium なし（Low 4 件・シナリオ Low 3 件。どれも既存の決定論ゲート・npm audit・指紋の固定で手を打ってある）。前からあるパスワードの環境変数の件（I213 F3）は変えない — 本イシューの目的と別で、一覧に残っているため（計画書「セキュリティレビュー結果」）
STAGE_DONE: design-security-review NEXT: implement
- [implement] lock の変更で `fsevents`（macOS 用の任意の依存）が消えたのはそのまま受け入れた — 1.65 の `playwright` が任意の依存から外したもので、計画書 §4 の想定の範囲（Linux の CI・コンテナに影響なし）
- [implement] `/simplify` は 4 人のレビュー役を起こさず自分で 4 観点を当てた（直す点なし）— 差分が版の数字 6 か所とロックファイルだけで、起こす費用に見合わないため
- [implement] `docker-compose.yml` は `sed -i` が置き換えに失敗（サンドボックスで 1 ファイルだけ書ける場所のため）したので Edit で直した — 結果は同じ
STAGE_DONE: implement NEXT: review-gate
- [review-gate] 基本レビューは CI_WAIT: OK（E2E を含む全ジョブ成功）・FINAL_VERDICT: OK・Low 5 件（F1〜F5・止める指摘なし）。F4（この記録の 2 行のつながり）は記録の場所なのでその場で直した。ほかの Low は retro で振り分ける — 止める指摘ではなく、記録の外の差分を足すと OK の周が無くなるため
- [review-gate] 敵対的レビュー 1 周目 OK（V1〜V4 確認済み・新しい Critical/High なし・未検証 0）
STAGE_DONE: review-gate NEXT: test-gate
- [test-gate] #377・#376 をコメント付きで閉じた（手動 No.5）。グループの版上げは閉じても無視されないと分かったので、計画書の計画変更記録に R5 の補足を書いた — マージ後は develop が同じ版になり、作り直されても自動で閉じられるため害はない
- [test-gate] 敵対的レビューの PR コメントは `post-review-comment.sh` が「開いている PR を取れません」で投稿しなかった（止めない決まり）。記録はファイルにある — 原因は retro で扱う
STAGE_DONE: test-gate NEXT: retro
- [retro] 台帳の残り: F1・F2・F3・F5 → `docs/reviews/backlog/I432.md`（Low・再現なし）。F4 は review-gate で直したので載せない。後続イシュー行き 0 件
- [retro] 改善案「手順書の `RATELIMIT_ENABLE=false docker compose …` がサンドボックスの中で動かない」→ 既存イシューに同梱（#538 にコメント）— 実害あり（計画の事前確かめが 1 回できなかった）・#538 と同じ根本原因（頭の形で外に出す対象を決める）で、決定論のテストもそこで足せる
- [retro] 改善案「画面側の Node.js 18 と版の置き場所の分散（F3・F5）」→ 既存イシューに同梱（#551 にコメント）— #551 が画面側を 26 にするので、そのときに 1 か所で決める形と §16 の括弧書きの片付けを計画で決めれば足りる
- [retro] 改善案「Dependabot の赤い PR が 3 週間取り込まれなかった」→ 見送り — 決まりどおり 11-10 に #432 を起票済みで、止まっていたのは着手順の問題。E2E を必須チェックに足す設定（ユーザーが GitHub の画面で行う・本イシューの範囲外）が根本の守りなので、close の報告でユーザーにお願いする
- [retro] 改善案「CI の `ubuntu-latest` の切り替えを事前に知る仕組み」→ 見送り — ユーザーの方針（古い環境に固定しない）どおり、切り替わった日に CI が止めて気づけた（その場で捕まった）
- [retro] 改善案「私（Claude）が `gh`・スクリプトの後ろに `| tail`・`2>&1`・`cd … &&` をつないで鍵を読めずに失敗した（6 回ほど・敵対的レビューの PR コメントの投稿失敗を含む）」→ 見送り — どれもその場で単体の形に直して手戻りなし。書き方の決まりは #538 の範囲（手順書の側）で、私の書き方は決定論で止める先が無い
- [retro] 改善案「計画の R5（閉じた版上げは Dependabot が無視する）の誤り」→ このイシューで直した（計画変更記録に補足）— グループの版上げは無視されない。実害なし
- [retro] 残余リスク処遇: セキュリティ設計レビューの Low 4 件・シナリオ Low 3 件はすべて受け入れ（既存の決定論ゲート・指紋の固定・npm audit で手を打ってある。I213 F3 は一覧に残っている）
- [retro] 設計ルール昇格: なし — 今回の穴（依存が求める実行環境の版と CI の版のずれ）は、CI の E2E が導入の段で必ず落として気づける。レビュー観点に足しても二重の守りになるだけ
- [retro] 指示ファイル（plan-reviewer・code-reviewer）の更新: なし（同上）

## 振り返り

### かんたんなまとめ
- 良かった点: 設計確認の段階で CI の失敗ログを読み、本当の原因（CI の Node.js が古く、新しい Playwright を入れられない）を早くつかめた。そのおかげで、計画は 1 回で通り、CI も 1 回で全部通った（理由: 「Ubuntu 26.04 に非対応」という前の見立てのまま #377 を取り込んでいたら、CI でもう一度落ちていた）
- 今回の問題への直接の対処: E2E の CI の Node.js を 26 に上げ、Playwright を 1.65.1 にそろえた。手元の E2E のコンテナ・手順書・規約の記載もそろえた（理由: 古い版に固定するのではなく、新しい実行環境に対応した版に上げるのが本筋だから）
- 同じ問題を次回から防ぐ改善:
  - 手順書にある「レート制限を切って E2E を流す」書き方が、今の安全の仕組み（サンドボックス）の中では動かなかった。仕組みを入れる前に書いた手順で、確かめる仕組みも無かったため → 同じ種類の問題を直す既存の #538 に加えた（手順書の書き方を機械で確かめる対象に入れる）
  - Node.js の版を書いた場所が CI に 6 か所あり、ばらばらに古くなる → 画面側を 26 に上げる #551 で、1 か所で決める形にするかを決めてもらうよう引き継いだ
- 見送ったもの: 赤い Dependabot の PR が 3 週間残った件は、決まりどおりイシュー（#432）が立っていて、着手が後回しになっただけ。本当の守りは「E2E をマージの必須条件に足す」設定（GitHub の画面でユーザーが行う）なので、マージ依頼のときにお願いする

### 詳細
#### 良かった点
- grill-me で失敗ログを実際に読み（ツール実行による完了基準の確定）、原因を前の見立て（Ubuntu 26.04 非対応）から更新できた。計画レビュー 1 回・CI 1 回・敵対的レビュー 1 周で通った

#### 是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | 技術選択 | `e2e.yml` の Node.js 18 が Playwright 1.65 の `engines.node >=20` を満たさない | E2E のジョブを Node.js 26 に・`@playwright/test` 1.65.1・イメージ v1.65.1-jammy（PR #575） |
| C2 | ドキュメント | 計画 R5 の Dependabot の挙動の見立て違い（グループの版上げは閉じても無視されない） | 計画変更記録に補足（このイシューで直した） |

#### 予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| P1 | スキル・規約 | 手順書のコマンドがサンドボックスの外に出る形かを確かめる決定論のチェックが無い（前置きの環境変数つきの `docker compose`） | #538 の書き換えと決定論のテストの対象に、手順書の「環境変数を前に付けた `docker compose`」を入れる（#538 に同梱） | `docs/runbooks/frontend-verify.md`・`docs/runbooks/common-commands.md` |
| P2 | 技術選択 | 実行環境の版を CI の複数の場所に書いていて、一部だけ古くなる | #551 の計画で、版を 1 か所で決める形（例: `node-version-file`）にするかを決める（#551 に同梱） | `.github/workflows/*.yml` |

#### 5 Whys: 手元の E2E の事前確かめができなかった
- Why 1: 手順書の `RATELIMIT_ENABLE=false docker compose …` が `.env` を読めずに止まった
- Why 2: 前置きの環境変数があると、サンドボックスの外に出す対象（頭の形で当たる）に当たらず、中で動いた
- Why 3: 手順書は、サンドボックスを入れる前に書かれ、書き方が外に出る形かを確かめる決定論のチェックが無い
- 抽象化: 「手順書のコマンドの形と、外に出す仕組みの当たり方を突き合わせる仕組みが無い」は他の手順書でも成り立つ → 予防処置（#538）
STAGE_DONE: retro NEXT: close
