# I228 計画書: 敵対的レビューで、実験必須の項目が中身と関係なく未検証になって周を失うのを無くす

## 基本情報
- **計画書ID**: plan_I228
- **関連イシュー**: #423
- **Draft PR**: #485
- **作成根拠資料**: docs/issues/open/I228.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I228_review.md
- **作成日**: 2026-11-13

## 1. 背景/目的
- 敵対的レビュー（`scripts/claude/adversarial-review.sh`）は、計画書の「## 必ず確かめる項目」の実験必須の項目が実験で確かめられないと合格にしない。中身と関係のない理由で未検証になり、周を 1 つ失う（上限に当たるとユーザーへの確認が要る）回が続いている（I213・I431・I446・I452・I455・I463・I469）
- 目的: 次の 3 つの損失を無くす
  1. 前の周に実験で確かめた項目が、記録だけを直した次の周で「未検証」に戻る（I213・I469）
  2. アプリのテストを `python …` でホストに流そうとして空振りし、それでも「実行した」と数えられたうえで、レビュー役が読んで済ませて未検証になる（I431・I446・I452・I455）
  3. 機械で毎回確かめられる性質を「実験必須」にしていて、実験が走らないと周を失う（I446 の V6・I463 の V1）

### 調査結果
- **原因の概要**: スクリプトは毎周、前の周の結果を一切見ずに全項目を確かめ直させる。実験の案はレビュー役が書くが、その案内にアプリのテストはコンテナで流すことが書かれていない。計画の書き方の手順書と計画レビュー役には、「決定論の TC で覆える性質は実験必須にしない」決まりが無い（計画書のひな形と `review-rules.md` には一文あるが、計画を書くときに読む手順書と、それを確かめる関所に無い）
- **詳細**:
  - 項目の判定は `item_verdict()`（`scripts/claude/adversarial-review.sh:338`）が、その周のレビュー役の ITEM 行と実験役の記録だけから出す。前の周の記録（`counted_records()`・`:86`）は「見る範囲の起点」（`review_base()`・`:98`）と「既知 findings」にしか使っていない
  - 記録の場所（`is_record_path()`・`scripts/claude/code-review.sh:138`）は `docs/issues|reviews|tests|plans/`。計画書は記録の場所なので、「記録の場所の外が変わっていない」だけを条件にすると、計画書の項目の文言を変えた周でも前の結果を引き継いでしまう → 項目の行（id・観点・確かめ方・内容）が前の周の `REVIEWED_COMMIT` の時点の計画書と同じであることも条件に入れる
  - 実験の結果の「実行した」（`ran`）は、実験役が同じコマンドを呼んで結果が返ったかだけで決まる（`claude_log_ran`・`scripts/claude/review-process-lib.sh:121`）。I455 の記録（`docs/reviews/closed/I455_adversarial_review_20261112_0952.md:34-76`）では、出力が `timeout: failed to run command ‘python’: No such file or directory` だけの実験が「実行した」になっている
  - 同じ記録の P1-E6（`:79-100`）では `docker compose exec -T backend python -m pytest …` が承認なしで実行され、182 件が pass している。実験役（`--permission-mode auto --settings .claude/settings.json`）の下で、コンテナ経由のテストは今でも流せる（`.claude/settings.json` の allow に `Bash(docker compose exec *)`）。足りないのは案内だけ
  - 「締め切りで実験が走らない」（I200）は、2026-11 の 15 回で最長 185 秒（上限 600 秒）で再発していない（grill-me で範囲から外した）
- **環境前提**: `flock`・`python3`・`git` は既存の敵対的レビューのテストで使っているもの（新しい道具は無い）。手動テスト No.1 は `docker compose` を使う（コンテナが止まっていても、承認画面が出るかの判定はできる）

## 2. 受け入れ条件
- [ ] AC1: 前の周（周に数えた最新の記録）で「確認済み（実験）」または「確認済み（前の周から引き継ぎ…）」の項目は、①その記録の `REVIEWED_COMMIT` が HEAD の祖先で、②そこから HEAD までに記録の場所の外のファイルが 1 つも変わっておらず、③その項目の行（id・観点・確かめ方・内容）が `REVIEWED_COMMIT` の時点の計画書と同じなら、「確認済み（前の周から引き継ぎ: <元の記録>）」として数えられ、記録に引き継ぎの行が書かれる。どれかが欠ければ引き継がない（TC-01 の A29〜A35・FG で固定）
- [ ] AC2: レビュー役への案内（`.claude/agents/adversarial-reviewer.md` とスクリプトの「## 実験の約束」）に、アプリのテスト・管理コマンドは `docker compose exec -T backend <コマンド>` で流すことが書かれ、実験役の設定の下でそのコマンドが承認なしで通る（手動 No.1）。出力が「コマンドが見つからない」形の行だけの実験は「実行した」に数えない（TC-01 の A36〜A38・FG）
- [ ] AC3: `docs/runbooks/plan-writing-rules.md` と `.claude/agents/plan-reviewer.md` に、決定論の TC で覆える性質を実験必須にしない決まりと、その確かめが入っている（手動 No.2）
- [ ] AC4: 既存のハーネステスト・CI がすべて pass する（TC-01・TC-02・CI）

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: `scripts/claude/adversarial-review.sh`（敵対的レビューの判定）・`.claude/agents/adversarial-reviewer.md`・`.claude/agents/plan-reviewer.md`・`.claude/skills/review-gate/SKILL.md`・`docs/runbooks/review-rules.md`・`docs/runbooks/plan-writing-rules.md`・`scripts/claude/tests/test_i197_adversarial_process.sh`
- 変更しない（確かめるだけ）: `.claude/settings.json`（`Bash(docker compose exec *)` は allow 済み）・`scripts/claude/code-review.sh`（`changed_outside_records`・`record_reviewed_commit` を読み込んで使うだけ）・`scripts/claude/gate-check.sh`（最後の記録の `VERDICT` を読むだけで、項目の判定には関わらない）

## 4. 変更点一覧（具体）

### 修正アプローチ
前の周の結果を「決まった条件がそろったときだけ」引き継ぐ判定を、スクリプトの起動時（レビュー役を呼ぶ前）に 1 回だけ出す。引き継いだ項目はレビュー役に「引き継ぎ済み・実験不要」と伝え、判定では ITEM 行より先に引き継ぎを見る。あわせて、コマンドが見つからないだけの実験を「実行した」から外し、レビュー役への案内にコンテナでの流し方を足す。計画の書き方と計画レビュー役に、決定論で覆える性質を実験必須にしない決まりを足す。

### 4-1. `scripts/claude/adversarial-review.sh`: 前の周の確認の引き継ぎ（AC1）
**修正方針**: 引き継ぎの条件をすべて決定論（git と記録の表）で出す。レビュー役の判断は使わない。条件が 1 つでも読めない・欠けるときは引き継がない（止める側）。

- 新しい関数 `record_item_verdicts <記録>`: 記録の「## 確かめる項目の結果」の節（次の `## ` まで）の表の行から `V<n>\t<判定>` を出す。各観点の報告の本文（別の節）に同じ形の行があっても読まない
- 新しい関数 `carry_items`（出力: `V<n>\t<元の記録のファイル名>`、理由は `$RUN/carry_note` に 1 行）:
  1. `prev=$(counted_records | tail -1)`。無ければ何も出さない（注記も無し）
  2. `sha=$(record_reviewed_commit "$prev")`。空、または `git merge-base --is-ancestor "$sha" HEAD` が失敗 → 引き継がない（注記: REVIEWED_COMMIT が無い・HEAD の祖先でない）
  3. `changed_outside_records "$sha" HEAD` が 0 以外 → 引き継がない（注記: 記録の場所の外が変わった＋ファイル名。2=git の失敗も同じ扱い）
  4. `git show "$sha:$PLAN_FILE"` を一時ファイルに出して `read_checklist` で読む。どちらかが失敗 → 引き継がない（注記: その時点の計画書の一覧を読めない）
  5. `record_item_verdicts "$prev"` の判定が `確認済み（実験）` または `確認済み（前の周から引き継ぎ` で始まり、今の一覧（`$RUN/checklist.tsv`）の行と、その時点の一覧の行が 4 列とも同じ項目だけを出す
  6. 注記: 引き継いだ項目があれば「`<prev>` の REVIEWED_COMMIT `<sha>` から HEAD までに記録の場所の外の変更なし → `V2 V3` を引き継いだ」。項目の行が変わって外したものがあれば「行が変わったため引き継がない: `V1`」も書く
- 呼ぶ場所: `REVIEW_BASE` を決めた後・レビュー役を起動する前に `carry_items > "$RUN/carry.tsv"`
- `run_perspective()` の入力: 「## あなたが判定を持つ項目」で、引き継ぐ項目には「（前の周から引き継ぎ済み・実験不要・ITEM 行は判定に使わない）」を付ける
- `item_verdict()`: 最初に `$RUN/carry.tsv` を見て、当たれば `引き継ぎ\t<元の記録>\t確認済み（前の周から引き継ぎ: <元の記録>）` を返す（観点の報告の有無にかかわらず。報告の無い観点がある周は `ROUNDS: 0`・HIGH なので合格にはならない）
- 記録: 冒頭の箇条書きに `- 引き継ぎ: <carry_note>`（前の周の記録があるときだけ）
- 引き継いだ項目は `UNVERIFIED` に数えない。`NEW_CRITICAL`・`NEW_HIGH`・報告なし・作業ツリーの変更・拒否の記録を読めない、による HIGH は今のまま（引き継ぎは項目の判定だけを変える）

### 4-2. `scripts/claude/adversarial-review.sh`: コマンドが見つからない実験を「実行した」に数えない（AC2）
**修正方針**: 出力の中身で「実行できなかった」と分かる狭い形だけを外す。広く取ると正しい実験（`ls` で無いことを確かめる等）まで外すので、行の形を固定する。外した実験はレビュー役に理由つきで返り、残りの往復（既存の `ADV_EXPERIMENT_ROUNDS`）で言い直せる。往復の数は増やさない。

- 新しい関数 `exp_not_executable <出力のファイル>`（python3 -I）: 先頭の `is_error=…` の行・空行・`Exit code <数>` の行を除いた残りが 1 行以上あり、そのすべてが次の形なら exit 0
  ```
  ^(?:(?:/\S*/)?(?:bash|sh|timeout|env|nice|xargs)(?:: line \d+)?: )?(?:[^\s:]+: (?:command not found|No such file or directory)|failed to run command \S+: No such file or directory)$
  ```
  （`ls: cannot access 'x': No such file or directory` のような、コマンドの中身の結果は当たらない）
- `run_perspective()` の結果の振り分け: `st=ran` の後、`exp_not_executable "$d/exp/$id.out"` が 0 なら `st=noexec`。レビュー役への結果には「コマンドが見つからない（実行できなかった）。アプリのテスト・管理コマンドは `docker compose exec -T backend <コマンド>` で」と 1 行足す
- 記録の「## 実験」のラベル: `noexec) label="実行できなかった（コマンドが見つからない）"`
- `item_verdict()` は `ran` だけを確認に数えるので、`noexec` は自然に未検証になる（変更不要）

### 4-3. 実験の案内（AC2）
- `scripts/claude/adversarial-review.sh` の「## 実験の約束」に 1 文: 「アプリのテスト・管理コマンドは `docker compose exec -T backend <コマンド>` で流す（ホストに python は無い。コンテナの中の /app は作業ツリーそのものなので、書き換える実験はしない。守りを外して落ちるかは `mock.patch` などのテストの中で確かめる）」
- `.claude/agents/adversarial-reviewer.md`「ツール境界と実験」に同じ内容の箇条書きと、「出力がコマンドの見つからない形だけの実験は実行できなかったに数えられる」を足す
- `.claude/skills/review-gate/SKILL.md` §3-1: アプリ（`backend/`）を変えたイシューでは、起動の前に `docker compose up -d backend` で起こす（動いていれば何もしない。コンテナが止まっていると、案内どおりの実験も空振りするため）

### 4-4. 計画の段階で決定論の TC に寄せる（AC3）
- `docs/runbooks/plan-writing-rules.md`: 「決定論テストの対象の選び方」の後に節「高リスクの計画の「必ず確かめる項目」（I228）」を足す。中身: 実験必須にする前に決定論の TC（失敗の注入つき・本物のファイルを書き換えない。`mock.patch`・一時の写し）で覆えないかを書く。覆えるなら TC を書いて内容に `TC-xx` を書き、`読んで可` にする。特に「守りを外すと落ちる（失敗注入）」「表と外部の正（`--help` など）の突き合わせ」は実験必須にしない（I446 の V6・I463 の V1）
- `.claude/agents/plan-reviewer.md` P4 の高リスクの行の次に: 「`実験必須` の項目に、決定論の TC で覆える性質（失敗注入・表と外部の正の突き合わせなど）が無いか。あれば Medium（TC にして `読んで可` に）」
- `docs/runbooks/review-rules.md`: 「網羅は計画の段階で決める」の行に `plan-writing-rules.md` の新しい節への参照を足し、「上限」の行に引き継ぎの 1 文（「前の周に実験で確かめた項目は、記録の場所の外と項目の行が変わっていなければ引き継ぐ。I228」）を足す
- `.claude/skills/review-gate/SKILL.md` §3-0 の上限の箇条と §3-3 の未検証の項目の箇条に、引き継ぎの 1 文（正はスクリプト）を足す

### 4-5. `scripts/claude/tests/test_i197_adversarial_process.sh`（TC-01）
- スタブの実験役: `$STUB_DIR/out_<id>` があれば、その中身を結果の本文にする（コマンドが見つからない形の出力を作るため）
- 新しいヘルパー `round2 <名前>`: 1 周目（A1 と同じ）を流した後、2 周目のスタブ（`p1_2.txt` 〜）を置いて流す
- A29〜A38 と FG を足す（中身は auto_test の TC-01 の表）

## 5. 実装手順（ステップ）
1. テスト（4-5）を先に足し、今の本体で A29（引き継ぐ）・A36（`noexec`）が落ちることを確かめる → TC-01 参照（未知のリスクは無いので、テスト先行で進める）
2. 本体の引き継ぎ（4-1）を入れる → TC-01 参照（ステップ 1 が前提）
3. 本体の `noexec`（4-2）と実験の約束の文（4-3 の 1 つ目）を入れる → TC-01 参照（ステップ 2 と並行可）
4. 文書（4-3 の残り・4-4）を直す → 手動 No.2 参照（ステップ 2・3 の後。説明を実装に合わせるため）
5. 全体のハーネステストの関係分を流す → TC-01・TC-02 参照

## 6. テスト計画
### 自動
- TC-01: `bash scripts/claude/tests/test_i197_adversarial_process.sh`（A1〜A28 の既存＋A29〜A38・FG。レベル: スクリプト全体を一時の git リポジトリで流す結合テスト。claude はスタブ）
- TC-02: `bash scripts/claude/tests/test_i193_official_flow.sh`・`bash scripts/claude/tests/test_i202_ledger_cleanup.sh`（`adversarial-review.sh` を読み込む既存のテスト・回帰）
- 全体は CI（`scripts/claude/tests/run-all.sh`）。手元では関係するテストだけを流す
### 手動
- No.1（Claude・`claude -p の判定`）: 実験役と同じ設定で `docker compose exec -T backend python -m pytest --version` が承認なしで通る
- No.2（Claude）: 文書の決まりが入っている・参照先が実在する

## 7. ロールバック
- PR を revert する（スクリプト・文書・テストだけ。データの変更は無い）。引き継ぎの行は記録の箇条書きと判定の欄だけなので、古いスクリプトに戻しても過去の記録はそのまま読める（`count_rounds`・`record_reviewed_commit` の読み方は変えない）

## 8. Risk & 回避策
- **引き継ぎで確かめが甘くなる**: 条件は git の差分・祖先関係・計画書の行の一致だけで決め、レビュー役の判断を使わない。読めない・失敗はすべて引き継がない側に倒す。祖先でない（rebase の後）・コードが 1 行でも変わった・項目の文言が変わった、はどれも引き継がない（A30〜A33・FG）
- **記録の表の偽の行**: 各観点の本文（レビュー役の文）に表の行の形を書かれても、読むのは「## 確かめる項目の結果」の節だけ（A35）。記録を手で書き換えることは、わざとの回避として対象外（見張りの脅威モデルと同じ「普通の書き方の事故」まで。記録はスクリプトがコミットし、差分はコードレビューに出る）
- **`noexec` の取りすぎ**: 行の形を固定し、すべての行が当たるときだけにする。正しい実験の出力（`ls: cannot access …`）は当たらない（A37）。取りすぎても未検証側（止まる側）に倒れる
- **過去の記録との互換**: 引き継ぎの行が無い古い記録も、表の判定の欄は同じ形なので読める。`確認済み（前の周から引き継ぎ` はこのイシューで新しく出る値

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 範囲は「確認済み（実験）の引き継ぎ」「コンテナでテストを流す案内（空振りの扱い含む）」「決定論の TC への寄せ（plan-writing-rules と plan-reviewer の両方）」。締め切りの分離と `/security-review` の読めたかの確かめは外す（後者は I483 #483）
- 引き継ぐ条件は、前の周の `REVIEWED_COMMIT` から HEAD までに記録の場所の外のファイルが 1 つも変わっていないこと（全体で見る）。祖先でないときは引き継がない

Claude が決めた（技術的な選択と理由）:
- 項目の行（id・観点・確かめ方・内容）が前の周の時点の計画書と同じことも条件に足す（仮定で決めた・技術）— 計画書は記録の場所なので、grill-me の条件だけだと項目の文言を変えた周でも引き継いでしまう。止める側への追加で、ユーザーの決めた条件を緩めない
- 引き継ぎの元にするのは「周に数えた最新の記録」だけ（仮定で決めた・技術）— 見る範囲の起点（`review_base`）と同じ記録を使い、決まりを 2 つにしない。引き継いだ項目は次の周でも元にできる（連鎖）。連鎖しても、各区間で記録の場所の外が変わっていないので、最初に実験した時点のコードと同じ
- 引き継ぐのは「確認済み（実験）」と「確認済み（前の周から引き継ぎ…）」だけ。「確認済み（読んで）」は引き継がない（仮定で決めた・技術）— 読んで可の項目は確かめ直しの費用が小さく、イシューの損失の原因でもない
- 空振りした実験の言い直しのために往復を足さない（仮定で決めた・技術）— 既存の往復（1 観点 2 回）の中で、理由つきの結果を返せば言い直せる。上限を増やさないのは I197・I205 の方針
- コマンドが見つからない形は行の形を固定して判定する（仮定で決めた・技術）— 「No such file」を含むだけで外すと、無いことを確かめる正しい実験まで外れる（`docs/runbooks/` の「文字列トークン判定はアンカー/完全一致」の考え方）
- review-gate §3-1 で、アプリを変えたイシューは起動の前に backend のコンテナを起こす（仮定で決めた・技術）— 案内どおりの実験も、コンテナが止まっていれば空振りするため。`docker compose up -d` は `.claude/settings.json` の allow の `Bash(docker compose up *)` に当たり、承認画面は出ない（手動 No.1 の exec と同じ allow の並び。起こすとコンテナが実際に立ち上がるので、手動テストでは流さない）
- テストは既存の `test_i197_adversarial_process.sh` に足す（仮定で決めた・技術）— スタブの claude と一時のリポジトリの道具をそのまま使え、写しを作らない
- 文書の決まり（4-4）には決定論テストを足さない — 消えるのは意図的な変更のときだけで、レビューで見る（`plan-writing-rules.md`「決定論テストの対象の選び方」）
- 要件・基本設計・UI/UX の仮定は無い（範囲・条件・決まりの置き場所は grill-me で確定済み）

要件適合性・業務ロジック:
- 受け入れ条件の範囲を超える仕様の追加は無い（コンテナを起こす 1 文は AC2 の「案内どおりに流せる」を満たすための手順）。マルチテナント・ステータス遷移は該当なし

セキュリティ・ベストプラクティス:
- セキュリティ影響: 敵対的レビュー（高リスクの変更の反証の工程）の合格の条件を変える。緩める向きは「引き継ぎ」だけで、決定論の 3 条件＋項目の行の一致に限り、読めないときは引き継がない（8. Risk）。入力（記録・計画書）は git の中のファイルで、外部入力・秘密情報・認証認可の変更は無い。依存ライブラリの追加は無い（bandit・npm audit の対象外）

P3/P5/P8 影響なし（DB・外部 API・非同期・新しいインフラは無い）／P6 影響なし（UI・データ量の懸念なし）／P9 影響なし（個人情報・テナントデータを扱わない）

設計品質:
- 判定はすべて関数に分け（`record_item_verdicts`・`carry_items`・`exp_not_executable`）、既存の `changed_outside_records`・`record_reviewed_commit`・`read_checklist` を使う（同じ規則を 2 か所に書かない）。null/空の扱い: 空の SHA・読めない計画書・空の表はすべて「引き継がない」

台帳の残りの一覧:
- 一覧 docs/reviews/backlog/I210.md F1: 残す — `ADV_CLOCK_FILE` の扱いは今回の判定と別の仕組みで、Low・再現なし
- 一覧 docs/reviews/backlog/I206.md F3: 残す — `flock` の戻り値は実験役の並び方の話で、今回の判定と別。Low
- 一覧 docs/reviews/backlog/I206.md F6: 残す — 同上（締め切りの周の作業ツリーの比較）
- 一覧 docs/reviews/backlog/I209.md F1: 残す — 計画の書き方のうち、表示の受け入れ条件の話で今回と関係しない
- 一覧 docs/reviews/backlog/I224.md F9・I223.md B1〜B4（FILE=-）: 残す — 別のイシューの測定・bot の後片付けで、今回と関係しない

Danger Ops（有無/手順/ロールバック）:
- 無

## 計画変更記録
- 計画レビュー（20261113_0054）の Warning への対応: 4-3 の `docker compose up -d` が承認なしで通る根拠（allow の `Bash(docker compose up *)`）を書き足し、TC-01 の A36 の出力は I455 の記録の実物（曲線引用符のまま）と明記した。計画レビューのやり直し: 不要（findings への対応の追記だけ）
- implement の /simplify（4 観点）への対応: ①引き継ぎの条件 ① は `review_base()` と同じ決まりなので、`carry_items` は `REVIEW_BASE` を起点に使い、比べる相手（`ADV_BASE`）に戻っていれば引き継がない（祖先の判定を 2 か所に書かない）。②コンテナが止まっているときの `service "backend" is not running` も、コマンドが見つからない形と同じく「実行できなかった」に数える（4-2 の形に 1 つ足す・A36b）。③テストの重複を整理した（`item_is` を使う・A36 と FG-A36 の準備の共用）。見送り: 前の周の判定を記録末尾の機械の行で持つ案（表は同じスクリプトが書き、読めないときは引き継がない側に倒れるため・4-1 のまま）、`prev_tbl` と `prev_rec` の統合（形が違う）。計画レビューのやり直し: 不要（方式・範囲・受け入れ条件は変えない）
- fix-loop（手動テスト No.3 の NG・docs/reviews/I228_fix_diagnosis_20261113_0128.md）: §3-1 の `docker compose ps --status running --services` は allow（`Bash(docker compose ps)` の完全一致）に当たらず承認画面が出たので、確かめを省き常に `docker compose up -d backend`（冪等・allow 済み）を流す形にした。計画レビューのやり直し: 不要（方式・範囲・受け入れ条件は変えない）

## レビュー結果
- [20261113_0054 判定: ✅ 完了](../../reviews/I228_plan_review_20261113_0054.md)
