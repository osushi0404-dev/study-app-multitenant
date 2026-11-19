# I583 計画書: 番号のテストを本物のリポジトリの記録に頼らない形にする

<!-- 各節に何を書くかは docs/runbooks/plan-writing-rules.md「計画書の節（形はひな形）」 -->

## 基本情報
- **計画書ID**: plan_I583
- **関連イシュー**: #583
- **Draft PR**: #589
- **作成根拠資料**: docs/issues/open/I583.md（起点イシュー・GitHub #583 の本文の写し）
- **実装後評価**: docs/reviews/open/I583_review.md
- **作成日**: 2026-11-19

## 1. 背景/目的
- I569 で足した `scripts/claude/tests/test_i569_issue_number_digits.sh` の TC-02・TC-03・TC-05 が、本物のリポジトリに I1000 の記録が「まだ無い」ことに頼っている。#1000 のブランチができると結果が変わり、TC-03 は本物の敵対的レビュー（別プロセスの `claude -p`）を起動しうる
- 目的: どの番号のブランチで流しても同じ結果になり、別プロセスの `claude` を起動しないこと。「番号の確かめを通る」を、期待する止まり方まで確かめること

### 調査結果
**原因の概要**: テストが、本物のリポジトリにまだ無い番号（I1000）の記録を「無い」前提にして、スクリプトが別の理由で止まることを使っていた。番号が #1000 に届くと前提が崩れる。

**詳細**:
1. 3 本のスクリプトは、どれも起動した場所の `git rev-parse --show-toplevel` に移ってから記録を読む（`scripts/claude/gate-check.sh:22-23`・`scripts/claude/adversarial-review.sh:496-497`・`scripts/claude/check-manual-test-executor.sh:22-23`）。テストは本物のリポジトリの根で起動している（`test_i569_issue_number_digits.sh:10-11,46,51,62`）ので、本物の記録を読む
2. `adversarial-review.sh` は、イシューファイルと計画書があれば `ADVERSARIAL_ERROR: FILES`（`:510`）を越えて、一覧の読み込み → 差分 → `run_perspective` で `${CLAUDE_BIN:-claude}`（`scripts/claude/review-process-lib.sh:29`）を起動する
3. 判定が弱い: TC-02・TC-05 は出力に「使い方」が無いことだけを見ている（`:47,63`）。読み込みの失敗など、確かめの手前の別の理由で終わっても合格になる。TC-03 は `FILES|FLOCK` のどちらでも合格にしている（`:53`）
4. 部品はそろっている: 3 本ともスクリプト自身の場所から部品を読む（`adversarial-review.sh` は `ADV_SCRIPT_DIR`・`gate-check.sh` は `GATE_CHECK_LIB` で差し替えられる・`check-manual-test-executor.sh` は読み込みなし）。なので、スクリプトを写さず、本物のスクリプトを一時の git リポジトリの中から起動すれば、記録はその一時のリポジトリから読む
5. スパイク（2026-11-19・このセッションで実行・成立）: `git init` と空のコミットだけの一時のリポジトリの中から起動した結果
   - `GATE_BASE=HEAD GATE_CHECK_LIB=<本物>/scripts/claude/code-review.sh bash <本物>/scripts/claude/gate-check.sh I1000` → exit 1・`GATE_CHECK: FAIL REASON=missing`
   - `bash <本物>/scripts/claude/adversarial-review.sh I1000`（差し替えの `claude` を `PATH` の先頭と `CLAUDE_BIN` に置く）→ exit 2・`ADVERSARIAL_ERROR: FILES`・差し替えは呼ばれない
   - `bash <本物>/scripts/claude/check-manual-test-executor.sh I1000` → exit 2・`[check-manual-test-executor] 判定できない: I1000_manual_test.md がありません`
   - 一時のリポジトリに `docs/issues/open/I1000.md` と「## 必ず確かめる項目」のある `docs/plans/open/plan_I1000.md` を置いてコミットし、`ADV_BASE=HEAD`・短い締め切りで流す → FILES を越えて差し替えの `claude` が呼ばれた（exit 3・`ADVERSARIAL_VERDICT: HIGH`）。印のファイルで「呼ばれた」を検出できることを確かめた
6. `flock`: CI の Harness Tests は `test_i197_adversarial_process.sh` などで `adversarial-review.sh` を流しており、`flock` がある前提で動いている。TC-03 は FILES だけを合格にする（FLOCK で止まる環境では、番号の確かめの後の止まり方を確かめられないので不合格にする）
7. 台帳（`docs/reviews/backlog/`）で当たった行: `I569.md` F2（TC-09 の走査の形）・`FILE=-` の行（I223 B1〜B4・I224 F9）。9 節に処遇を書く

## 2. 受け入れ条件
- [ ] `docs/issues/open/I1000.md`・`docs/plans/open/plan_I1000.md`・`docs/reviews/open/I1000_review.md` が本物のリポジトリにあっても、`test_i569_issue_number_digits.sh` が同じ結果で合格し、別プロセスの `claude` を起動しない
- [ ] TC-02・TC-03・TC-05 の「I1000 は番号の確かめを通る」が、期待する止まり方（`GATE_CHECK: FAIL REASON=missing`・`ADVERSARIAL_ERROR: FILES`・手動テスト文書が無いときの文言）と終了コードまで確かめ、確かめの手前で別の理由で終わった場合に不合格になる（失敗の注入で確かめる）

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: ハーネスのテスト `scripts/claude/tests/test_i569_issue_number_digits.sh` だけ（CI の Harness Tests が流す・`run-all.sh` が拾う）

## 4. 変更点一覧（具体）

### 修正アプローチ
- 番号の確かめを通った後の止まり方を見る 3 つの TC を、テストが作る一時の git リポジトリ（`git init` と空のコミットだけ）の中から本物のスクリプトを起動する形にする。スクリプトは写さない（写すと本物との食い違いを見落とす）
- 起動のたびに、印のファイルを作る差し替えの `claude` を `PATH` の先頭と `CLAUDE_BIN` に置く。万一記録を読んでも本物のレビュー役を起動しない（二重の守り）
- 止まり方の判定を関数にまとめ、TC と失敗の注入（FG）が同じ関数を呼ぶ（判定を 2 か所に書かない）

- ファイル/関数: `scripts/claude/tests/test_i569_issue_number_digits.sh`
  - 追加する部品（ファイルの冒頭の部品の並びに置く）
    - `iso_repo <dir>`: `git init -q` と `git -c user.name=t -c user.email=t@t commit -q --allow-empty -m init` で一時のリポジトリを作る（CI の git に作者の設定が無くても動く）
    - 差し替えの `claude`: `$TMP/stub/claude`（呼ばれたら `$TMP/claude_called` を作って exit 1）。`STUB=(env "PATH=$TMP/stub:$PATH" "CLAUDE_BIN=$TMP/stub/claude")` を起動の前に付ける
    - `stops <dir> <期待する exit code> <期待する行・文字> <コマンド…>`: `<dir>` に移ってコマンドを起動し、終了コードが一致し、かつ出力が期待を含めば YES、どちらかが違えば NO（期待の照合は `grep -qF`。`GATE_CHECK:`・`ADVERSARIAL_ERROR:` の行は `grep -qxF` で行全体を照合する）
  - TC-02: `stops "$ISO" 1 'GATE_CHECK: FAIL REASON=missing'`（行全体）で `GATE_BASE=HEAD GATE_CHECK_LIB=$REPO_ROOT/scripts/claude/code-review.sh bash $REPO_ROOT/scripts/claude/gate-check.sh I1000` → YES
  - TC-03: `stops "$ISO" 2 'ADVERSARIAL_ERROR: FILES'`（行全体）で `bash $REPO_ROOT/scripts/claude/adversarial-review.sh I1000` → YES（`FLOCK` は合格にしない）
  - TC-05: `stops "$ISO" 2 '判定できない: I1000_manual_test.md がありません'` で `bash $REPO_ROOT/scripts/claude/check-manual-test-executor.sh I1000` → YES
  - 3 つとも、今の「使い方が出ない」確かめ（`ck … NO "$(has "$out" "使い方")"` 等）は `stops` に置き換える（期待する行があれば使い方では止まっていない）
  - TC-10（新規）: TC-02〜TC-05 の後に `$TMP/claude_called` が無い
  - FG-05（新規）: `GATE_CHECK_LIB` を無いパスにすると（確かめの後・記録を読む手前で「読み込めません」で終わる）、TC-02 の判定が NO
  - FG-06（新規）: I1000 のイシューファイルと「## 必ず確かめる項目」のある計画書をコミットした一時のリポジトリ（`$TMP/fg6`）では、TC-03 の判定が NO・差し替えの `claude` が呼ばれて `$TMP/claude_called` ができる（本物の記録ができたときを写した状態で、①TC-03 の判定がそれを捕まえる ②印で起動を検出できる、を確かめる）。締め切りを短くする（`ADV_BASE=HEAD ADV_DEADLINE=30 ADV_STEP_TIMEOUT=10 ADV_MIN_STEP=1`）
  - FG-07（新規）: git の外の一時のフォルダから起動すると（確かめの後に「git のワークツリー内で実行してください」で終わる）、TC-05 の判定が NO
  - 冒頭のコメントのケースの範囲を「TC-01〜TC-10・FG-01〜FG-07」に直す
  - 不正な値を断る `rejects`（TC-02・TC-03・TC-05 の後半）は今のまま（番号の確かめで止まり、記録を読まない）

## 5. 実装手順（ステップ）
1. 部品（`iso_repo`・差し替えの `claude`・`stops`）を足し、TC-02・TC-03・TC-05 を一時のリポジトリで流す形に直し、TC-10 を足す → TC-A1
2. FG-05〜FG-07 を足す（ステップ 1 の後）→ TC-A1
3. 本物のリポジトリに I1000 の記録を一時的に置いて流しても同じ結果で、`claude` が起動しないこと → 手動テスト No.1（test-gate で Claude が行う）

## 6. テスト計画
### 自動
- `bash scripts/claude/tests/test_i569_issue_number_digits.sh`（決定論ゲート・TC-A1）。テストのレベルはハーネスの結合（本物のスクリプトを別の git リポジトリから起動する）
- 再発防止: TC-10 と FG-06（記録がある状態で、判定が捕まえ・起動が印に出る）
- 失敗の注入: FG-05〜FG-07（それぞれ TC-02・TC-03・TC-05 の判定が、確かめの手前の別の理由で終わると NO になる）
### 手動
- No.1: 本物のリポジトリ（このワークツリー）に I1000 の 3 つの記録を一時的に置いてテストを流し、合格と `claude` の不起動を確かめて記録を消す（Claude）

## 7. ロールバック
- このイシューのコミットを revert する（テスト 1 本だけの変更。アプリ・データへの影響なし）

## 8. Risk & 回避策
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: FG-06 で `adversarial-review.sh` を本当に先まで流すので、テストが遅くなる・時間に左右される | 締め切りを短くし（`ADV_DEADLINE=30` など）、差し替えの `claude` はすぐ exit 1 する。合否は終了コードと印だけで見て、時刻に頼らない | 回避 |
| R2: FG-06 の差し替えが外れると、本物の `claude` を起動する | `PATH` の先頭と `CLAUDE_BIN` の両方に差し替えを置く。FG-06 は一時のリポジトリの中だけで流し、`GH_APP_READONLY` などには触れない | 回避 |
| R3: `flock` の無い環境で TC-03・FG-06 が不合格になる | CI と手元は `flock` がある（他の敵対的レビューのテストが頼っている）。無い環境では止まり方を確かめられないので、不合格で知らせるのが正しい。原因が分かるよう、`flock` が無いときはテストの冒頭で `    flock がありません（TC-03・FG-06 は確かめられない）` を出す（合否は変えない） | 受け入れ |
| R4: 一時のリポジトリの作成で、CI の git に作者が無くて失敗する | 空のコミットに `-c user.name=… -c user.email=…` を付ける | 回避 |
| R5: TC-01・TC-04・TC-06〜TC-09・`rejects` は本物のリポジトリで流す | どれも番号の記録を読まない（TC-01 は一時の `REVIEW_DIR`・TC-04 は `BASE_REF=HEAD` で差分が無く対象外・`rejects` は番号の確かめで止まる）。イシューの「含まない」のとおり | 受け入れ |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ）:
- 設計確認メモは無し（/grill-me で疑問点なし・2026-11-19）
- 一時の git リポジトリで流す・期待する止まり方まで見る・失敗の注入で確かめる・TC-01/04/06〜09 は今のまま・TC-09 の走査の形と観点の追加は含まない（イシューの解決方針・スコープ）
Claude が決めた（技術的な選択と理由。要件・基本設計・UI/UX の仮定は計画レビューの前にユーザーに確認する）:
- スクリプトは写さず、本物のスクリプトを一時のリポジトリの中から起動する（仮定で決めた）— 3 本とも `--show-toplevel` で記録の場所を決め、部品は自分の場所から読むため、写さなくても本物の記録を読まない。写すと本物との食い違いが起きる（調査結果 4・5）
- 差し替えの `claude` を `PATH` と `CLAUDE_BIN` の両方に置き、印のファイルで起動を検出する（仮定で決めた）— イシューの受け入れ条件の確かめ方の例どおり。`CLAUDE_BIN` は `review-process-lib.sh` の正式な差し替え口
- TC-03 は FILES だけを合格にする（FLOCK を外す）（仮定で決めた）— 調査結果 6・R3
- 判定は `stops` 関数にまとめ、TC と FG で同じ関数を呼ぶ（仮定で決めた）— 判定を 2 か所に書くと、FG が本物の判定を確かめなくなる
- 一覧 docs/reviews/backlog/I569.md F2: 残す — イシューの「含まない」（I569 の計画の R3 で受け入れ済み）
- 一覧 docs/reviews/backlog/I223.md B1〜B4・I224.md F9（`FILE=-`）: 残す — このイシュー（テストの直し）と関係しない
- 要件適合性: 受け入れ条件の範囲を超えた追加なし。マルチテナント・ステータス遷移・業務ルールに触れない
- セキュリティ影響なし（アプリのコード・認証・依存の変更なし）。差し替えの `claude` で、テストから本物のレビュー役（GitHub の鍵を読む別プロセス）を起動しない形にする
- P3/P5/P8 影響なし・P6 影響なし・P9 影響なし（テスト 1 本の変更）
- 設計品質: 設定値は既存の環境変数（`GATE_BASE`・`GATE_CHECK_LIB`・`CLAUDE_BIN`・`ADV_*`）で渡し、スクリプト本体は変えない
- 高リスク: パス判定に当たらない（`.github/`・見張り・設定を変えない）。必ず確かめる項目は下に書く（レビュー役が高リスクと判定したとき用）
Danger Ops（有無。有りのときは 影響範囲・代替案・ロールバック・実行コマンド を書く。条件と手順は docs/runbooks/danger-ops.md）:
- 無

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | TC-02・TC-03・TC-05 の起動が、本物のリポジトリの根ではなく一時のリポジトリの中で行われ、どの起動にも差し替えの `claude` が付いているか（TC-10・FG-06） |
| V2 | 2 | 読んで可 | FG-05〜FG-07 が、TC と同じ `stops` を呼び、確かめの手前で別の理由で終わる形を入れて NO になるか（判定の写しになっていないか） |
| V3 | 3 | 読んで可 | 受け入れ条件 1 の「本物のリポジトリに記録があっても同じ結果・claude を起動しない」が、手動テスト No.1 と FG-06 で覆われているか |

## 計画変更記録
<!-- 形は docs/runbooks/plan-writing-rules.md「計画変更記録の形」 -->
- 2026-11-19 plan-review: 計画書の記載: [R3 の回避策] → 採った方法: flock が無いときに原因を示す 1 行を出す（合否は変えない）。手動テスト No.1 に中断時の後始末を足す — 理由: 計画レビューの Warning 2 件への対応。計画レビューのやり直し: 不要（findings への対応の追記だけ）
- 2026-11-19 implement: 計画書の記載: [`stops` は `<dir>` に移ってコマンドを起動する] → 採った方法: 起動の前に `GIT_DIR`・`GIT_WORK_TREE`・`GIT_INDEX_FILE` を外し、`GIT_CEILING_DIRECTORIES=$TMP` で git の探索を一時の場所で止める。作者付きの git は `tgit` 1 か所にまとめる。FG-06 の前に印を消す。`rejects` のパスを `$GATE`・`$ADV`・`$MTE` にそろえる — 理由: `/simplify` の指摘（git の環境変数が残ったシェルから流すと本物のリポジトリに届く・FG-07 の「git の外」が TMPDIR の場所に頼る・FG-06 の印が前のケースの印を持ち越す・同じ書き方の重複）。判定と範囲は変えない。計画レビューのやり直し: 不要（同じ方式の中の守りの強化と整理）

## レビュー結果
- [20261119_1526 判定: ✅ 完了](../../reviews/closed/I583_plan_review_20261119_1526.md)
