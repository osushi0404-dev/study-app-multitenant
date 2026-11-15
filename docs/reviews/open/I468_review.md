# I468 レビュー: ワークツリーで ESLint のフックをコンテナで流す・Playwright MCP が切れたときの手順

## 変更概要
- pre-commit の ESLint のフックを `scripts/claude/lint-frontend.sh` 経由にし、起動中のコンテナ → 使い捨てのコンテナ → ホストの eslint → 止める、の順で流す
- `docs/runbooks/frontend-verify.md` に「11. MCP が使えないとき」を足し、implement の最初と test-gate の画面確認の前に MCP を確かめる

## 変更点
- （implement 後に記入）

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.pre-commit-config.yaml`（ESLint のフックの `entry`）
- ハーネス: `scripts/claude/lint-frontend.sh`（新規）・`scripts/claude/tests/test_i468_lint_frontend.sh`（新規）・`.claude/skills/implement/SKILL.md`・`.claude/skills/test-gate/SKILL.md`・`docs/runbooks/pre-commit.md`・`docs/runbooks/frontend-verify.md`

## テスト結果
- 自動: `test_i468_lint_frontend.sh` 合格（TC-01〜TC-05・FG-01〜FG-05）。CI 全ジョブ合格（2 回目以降）。コードレビュー OK（止める指摘なし・Low 7 件は台帳）・敵対的レビュー 2 周目 OK
- 手動（すべて Claude）: No.1〜No.4 OK（本物のワークツリーで、コンテナ停止中・起動中のどちらでも違反のコミットが止まり、違反なしは通った）。No.5 は一部（tui-capture が MCP を渡さない作りのため playwright の項目は観測できず・I452 の実績で補う）

## 計画との差分
- なし

## ロールバック
- PR を revert する（データの変更なし）

## 自律判断の記録
- [plan] 使い捨てのコンテナに `--entrypoint npm` と `--build` を付ける — スパイクで、入口のスクリプトが引数を無視して開発サーバーを起動すると分かったため・package*.json の変更に追従するため（plan_I468 の「確かめたこと」）
- [plan] test-gate のスキルにも MCP の確かめを足す — implement と手順の粒度をそろえる（イシューの実装対象の表の外・AC4 と同じ目的）
- [implement] Write ツールが使えない時間があったため、新しいファイルは 1 行の仮のファイルを作ってから Edit で中身を入れた — 中身は計画どおり
- [implement] /simplify（4 観点）で直したもの: Docker に届くかの確かめを `docker version --format` に替えた・テストの 3 つの似たループを 1 つの関数にした・失敗の注入の置き換えを python から bash にした・置き換えの文字列を変数から作る・test-gate の §11 の参照を短くした — 同じ判定のまま重複と無駄を減らすため
- [implement] /simplify で見送ったもの: 使い捨てのコンテナで compose の匿名ボリュームを使わずにイメージを直接動かす案・Dockerfile.dev を依存だけの段に分ける案・frontend/.dockerignore の追加・入口のスクリプトを `exec "$@"` に直す案 — どれも `frontend/` のアプリの起動の仕組みを変えるので計画の範囲外（計画 9）。retro で別イシューの要否を決める。pre-commit.md のコマンドの写し・implement の 0) の説明の重なりは、読む人がその場で分かるように残した
- [fix-loop] CI の S21（test_i193）の失敗は、test-gate の行の元の言い回しを残して §11 の確かめを前に置く案 A で直した — I187 の決まりの目印をこのイシューの都合で緩めない（テストを変える案 B は採らない）。診断レビュー PASS
- [review-gate] 基本レビュー 2 回目（20261115_1103）は止める指摘なし（Low 7 件は台帳に残し retro へ）。敵対的レビュー 1 周目（20261115_1112）は新しい指摘 0・V3 だけ実験の拒否で未検証 — 3-3 のとおり決定論の TC-05（本物の pre-commit と git・FG-05）を足して V3 を読んで可に下げ、ついでにテスト文書の古い変数名（台帳 F6）を直した。基本レビューを通してから 2 周目へ
- [test-gate] 違反の無い確かめは `pre-commit run` でなく本物の `git commit`（送らずに `git reset --soft` で取り消し）で行った — Claude の Bash では `pre-commit run` がサンドボックスの中で動いて Docker に届かない（`git commit`・`docker` はサンドボックスの外）。この止まり方自体が AC2 の確かめになった。retro で手順書に書くかを決める
- [test-gate] manual No.5 は「一部」で合格扱いにした — tui-capture は MCP を渡さない決まり（I225）で playwright の項目を観測できない。AC3・AC4 は No.3・No.4 の文書の中身で判定し、再接続の操作は I452 の実績で補う
- [plan-review] 計画レビューの Warning 2 件（test-gate の場所を文言で指す・後始末の確認）は計画書で対応し、再レビューは省いた — 方式・範囲・受け入れ条件を変えないため
- [retro] 台帳の残り: 後続イシュー 0 件。一覧へ F1〜F5・F7〜F11（`docs/reviews/backlog/I468.md`）。F6 は I468 の中で直したので載せない
- [retro] 開発用イメージの根本の直し（入口のスクリプトが引数を無視する・.dockerignore が無い・使い捨てのコンテナの作り直しの重さ）: #500 に同梱（コメント済み）— 画面の作りの移行で Dockerfile.dev を作り直すときに直すのが一番安い。新規起票はしない
- [retro] サンドボックスの中の `pre-commit run` が Docker に届かない件: 一覧の R1（`docs/reviews/backlog/I468.md`）— 止まり方は正しく（黙って通らない）、手順書の補いだけ。次に pre-commit.md を触るイシューで拾う
- [retro] /simplify の文言変更で I187 のテストを壊した件: 見送り — CI がその場で捕まえ、fix-loop 1 回（文言の 1 行）で直った。決定論のゲートが働いた例で、新しい手順は足さない
- [retro] V3 を「実験必須」にした件（本物の pre-commit と git の部分は決定論の TC で覆えた）: 見送り — 決まり（plan-writing-rules「高リスクの計画の必ず確かめる項目」）はすでにあり、review-gate 3-3 の流れで TC-05 に置き換わった（敵対的レビュー 1 周分の手戻り）。同じことが続けば plan-reviewer の観点にする
- [retro] 残余リスクの処遇: 計画書「セキュリティレビュー結果」の「残余リスク処遇」に記録（High 以上なし）

## 振り返り

### かんたんなまとめ

**良かった点**
- 計画の前に実際に試したことで、開発用のイメージが「lint を流して」という指示を無視する問題を、実装の前に見つけられました（理由: 試さずに書いていれば、実装後のコミットで初めて止まらない・終わらないことに気づいていたはずです）
- 本物のワークツリーで、コンテナを止めた状態・起動した状態の両方で、違反のあるコミットが止まり、違反の無いコミットが通ることを Claude が自分で確かめました。Docker に届かないときは「流せません」で止まる（黙って通らない）ことも、たまたま本物の環境で確かめられました
- テストには、わざと壊した写しでテストが落ちることの確かめを全部に付けました（理由: 安全装置のテストが「何があっても合格」になっていないことを保証するため）

**今回の問題への直接の対処**
- 整理（/simplify）で手順書の言い回しを短くしたら、前のイシューで決めた言い回しを確かめるテストが CI で落ちました。整理の前にはテストを流していましたが、整理の後に流し直していませんでした。→ 元の言い回しを残す形で直しました（テストの側を緩めると守りが弱くなるため）
- 敵対的レビューの 1 周目で、「本物の環境でコミットが止まるか」の項目が、レビュー役の実験が権限で拒否されて未確認になりました。→ 本物の pre-commit と git を使い、Docker だけを偽物にしたテストを足して確かめ、2 周目で合格しました

**同じ問題を次回から防ぐ改善**
- 開発用のイメージの根本の問題（指示を無視する起動スクリプト・送らなくてよいファイルの除外の設定が無い・コミットのたびの作り直しの重さ）は、画面の作りを移すイシュー #500 で Dockerfile を作り直すときに一緒に直すよう、#500 にコメントしました（別のイシューを増やすより、作り直す場所でまとめて直すほうが安いため）
- Claude の中から `pre-commit run` を直接流すと Docker に届かない件は、止まり方自体は正しいので、手順書に一言足すだけの軽い指摘として一覧に残しました
- 上の 2 つの「直接の対処」は、どちらもその場の仕組み（CI のテスト・敵対的レビューの決まり）が捕まえて小さな直しで済んだので、新しい手順は足しません

**約束していた測定（敵対的レビューの空振り）**
- 今回は「実験必須」の項目を持つ高リスクのイシューで、初めて測れました。1 周目の実験 1 件は、空振りの種類としては「コマンドが無い」ではなく「実験役の権限での拒否」（本物の Docker を使い、終わりにデータごと片付ける操作を含んでいた）でした。決まりどおり決定論のテストに置き換えて 2 周で合格しました。前の周の確かめの引き継ぎは、テストのファイルが変わったので「引き継がない」と正しく判定されました。コンテナの起動の失敗による停止は 0 回でした

### 詳細版

#### 良かった点
- スパイク（計画確定前の実証）で `--entrypoint` の必要性・`--build` の時間・終了コードの伝わり・サンドボックスから Docker への到達・MCP の確かめ方を実証し、計画の未実証の前提が 0 で計画レビューを通った
- manual No.1・No.2 を本物の Docker・pre-commit・git で Claude が実施（Human 0 件）。サンドボックスの中の `pre-commit run` が fail-closed で止まることも観測（AC2 の本物の確かめ）
- 決定論テストは TC-01〜TC-05 すべてに FG を付け、写しを壊して不合格を確かめた

#### 是正処置（Corrective）
| # | カテゴリ | 根本原因 | 対処内容 |
|---|---------|---------|---------|
| C1 | プロセス | /simplify の文言変更の後に、変えた文書を読むテストを流し直さなかった | test-gate の行で元の言い回しを残す（fix-loop・7e5a2d7b）。CI の S21 が捕まえた |
| C2 | テスト | V3 を実験必須にしたが、実験役は本物の Docker と片付け（`down -v`）を含む操作を拒否された | TC-05（本物の pre-commit・git・偽の docker・FG-05）を足し V3 を読んで可に（fc4dd830） |

#### 予防処置（Preventive）
| # | カテゴリ | 根本原因 | 予防策 | 対象ファイル |
|---|---------|---------|--------|------------|
| P1 | 技術選択 | 開発用イメージの入口のスクリプトが公式の入口を上書きし引数を無視する・.dockerignore が無い・使い捨てのコンテナが bind mount と `COPY . .` を二重に使う | 画面の作りの移行で Dockerfile.dev を作り直すときに、入口を `exec "$@"` 対応にし、.dockerignore を足し、lint のフックの `--entrypoint` を外す | #500 に同梱（`frontend/Dockerfile.dev`・`frontend/docker-entrypoint.sh`・`frontend/.dockerignore`・`scripts/claude/lint-frontend.sh`・`docs/runbooks/pre-commit.md`） |

#### 見送り（理由つき）
- C1 の再発防止の手順追加: CI がその場で捕まえ手戻りは 1 行（決定論のゲートが働いた）
- C2 の再発防止（plan-reviewer の観点追加）: 決まりは plan-writing-rules にすでにある。review-gate 3-3 の流れで解決した。続けば観点にする
- サンドボックスの中の `pre-commit run` の件の起票: 止まり方は正しく、手順書の一言だけ（一覧 R1）

#### 観点ごとの確認
- 成果: AC1〜AC4 を満たした（AC1・AC2 は TC と manual No.1・No.2、AC3・AC4 は manual No.3・No.4）
- セキュリティ: 新しい依存・取得先・引数なし。fail-open を TC と本物の環境で潰した。秘密情報の表示なし
- 残余リスク処遇: 計画書に記録（High 以上なし）
- 設計ルール昇格: 「安全装置のラッパーは各分岐を exec と最後の exit 1 で終える」は plan-writing-rules の決定論テストの節（FG を付ける）で足りる。昇格なし
- 指示ファイルメンテナンス: plan-reviewer・code-reviewer への追加なし（上の見送りの理由）
- モダン開発: API・UI の変更なし

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
STAGE_DONE: retro NEXT: close
