# I525 計画書: 敵対的レビューの延長を引数で受け取り、Claude の Bash からサンドボックスの外で起動できるようにする

## 基本情報
- **計画書ID**: plan_I525
- **関連イシュー**: #525
- **Draft PR**: #527
- **作成根拠資料**: docs/issues/open/I525.md（起点イシュー）
- **実装後評価**: docs/reviews/open/I525_review.md
- **作成日**: 2026-11-16

## 1. 背景/目的
- 背景: I468 で、敵対的レビューの延長（通算 3 周目）を review-gate の手順どおり `ADV_ROUND_LIMIT=3 bash scripts/claude/adversarial-review.sh I468` で起動すると、2 回続けて `ADVERSARIAL_ERROR: DIRTY` で止まった。作業ツリーはきれいだった。ユーザーが `!` で同じコマンドを流すと通った
- 目的: ユーザーが延長を承認したら、Claude が手順どおりに延長の周を起動できるようにする（ユーザーに `!` で打ってもらう必要をなくす）

### 調査結果
- **原因の概要**: 延長の値を「環境変数を前に付ける」形でしか渡せない。この形は、サンドボックスの外で動かす形の一覧（`.claude/settings.json` の `sandbox.excludedCommands` にある `bash scripts/claude/*`）に当たらない。そのためサンドボックスの中で動き、サンドボックスが差し込む装置ファイルを「コミットしていない変更」と数えて止まる
- **詳細な原因分析**:
  1. `scripts/claude/adversarial-review.sh:31` は `ADV_ROUND_LIMIT` を環境変数だけで受け取る（既定 2）。引数は `I###` の 1 つだけ（`:476-477`）
  2. Claude の Bash は呼び出しの間で環境を持ち越さないので、延長は `ADV_ROUND_LIMIT=3 bash scripts/claude/...` と前に付けて渡すしかない（`.claude/skills/review-gate/SKILL.md:66`・`:85`）
  3. `excludedCommands` は `docker *`・`docker-compose *`・`gh *`・`git *`・`bash scripts/claude/*` の形で照合される。`ADV_ROUND_LIMIT=3 bash ...` は `bash` で始まらないので当たらず、サンドボックスの中で動く
  4. サンドボックスの中では、書き込みを止める場所に装置ファイルが差し込まれる。`dirty_outside_records`（`:114-120`。`git status --porcelain=v1 -z --untracked-files=all`）はそれを未追跡と数え、`:508-514` で `ADVERSARIAL_ERROR: DIRTY`・exit 2 になる
  5. この道は上限を使い切ったときだけ使う珍しい道で、決定論のテスト（`test_i197_adversarial_process.sh` の A9。テストの中では環境変数で渡している）でも、実際の起動でも通っていなかった
- **スパイク（計画の前に実機で確かめた・2026-11-16・このセッションの Bash＝Claude Code のサンドボックス）**:
  - `git status --porcelain=v1 --untracked-files=all`（`git *` に当たる＝外）→ 何も出ない
  - `SPIKE=1 git status --porcelain=v1 --untracked-files=all`（前置きあり＝中）→ `.bash_profile`・`.bashrc`・`.claude/commands`・`.claude/hooks`・… `.zshrc` の 18 件が `??` で出る（イシューの DIRTY の一覧と同じ）→ **成立**（前置きでサンドボックスの中に入り、装置ファイルが見える）
  - `bash scripts/claude/gate-check.sh I525`（`bash scripts/claude/*` に当たる・引数つき）→ 作業ツリーの汚れの確かめ（`gate-check.sh:113-119`。同じ `git status`）を通り、その先の「コードレビューの記録がありません」で止まった → **成立**（`bash scripts/claude/<スクリプト> <引数…>` の形はサンドボックスの外で動く。`*` は後ろの引数をすべて含むので、`--round-limit 3 I###` を足しても同じ形）
- **既存のテスト**: 環境変数 `ADV_ROUND_LIMIT` を使うテストは `test_i197_adversarial_process.sh` の A9（`:241`）・A34（`:645`）・FG-A9（`:470`）と、既定値の行をそのまま照合する `test_i202_ledger_cleanup.sh:583`。どれも環境変数を残せば変わらない
- **手順書の中の同じ形**: `.claude/skills/` の中で環境変数を前に付けて `bash scripts/claude/` を起動する書き方は、`review-gate/SKILL.md` の 2 か所（延長）だけ。`docs/runbooks/worktree.md:100`・`:102`（`DANGER_OK=1`・`KEEP_DATA=1 bash scripts/claude/wt-remove.sh`）にも同じ形があるが、別のスクリプト・別の確かめ（撤去の対象の別のワークツリーを見る）で、このイシューの範囲外（§9 に書く）

## 2. 受け入れ条件
- [ ] AC1: 上限を使い切ったイシューで、Claude の Bash から review-gate の手順どおりに延長の周を起動すると、作業ツリーがきれいなら DIRTY で止まらずに周が始まる（→ TC-01 の A9e、TC-02、手動 No.1・No.2）
- [ ] AC2: 延長の値を渡さないときは、今までどおり通算 2 周で止まる（→ 既存の TC-01 の A9a。加えて A9g・A9h で、値の誤りでは上限を外さない）
- [ ] AC3: 作業ツリーに本物の未追跡のファイルがあるときは、今までどおり DIRTY で止まる（→ TC-01 の A9i・既存の A11）

## 3. 影響範囲
- Backend: なし
- Frontend: なし
- DB: なし
- Config/Infra: なし（`.claude/settings.json` は変えない。ハーネスのスクリプト・手順書・テストだけ）

## 4. 変更点一覧（具体）
| ファイル | 変更内容 |
|---|---|
| `scripts/claude/adversarial-review.sh` | (1) 引数の読み取り（`:476-477`）を、`--round-limit <N>` と `I###` を受け取る形にする (2) 上限の値（引数 → 環境変数 → 既定 2 の順）を正の整数か確かめ、違えば `ADVERSARIAL_ERROR: USAGE`・exit 2 (3) 冒頭のコメント（`:2`・`:13-14`）に引数を書く |
| `.claude/skills/review-gate/SKILL.md` | `:66`・`:85` の延長の起動を `bash scripts/claude/adversarial-review.sh --round-limit 3 "$ARGUMENTS"` に直し、「環境変数を前に付けない（サンドボックスの外に出る形 `bash scripts/claude/*` から外れる）」を 1 文足す |
| `scripts/claude/tests/test_i197_adversarial_process.sh` | A9 に A9e〜A9i を足し、FG を 2 つ足す（§6・auto_test の TC-01） |
| `scripts/claude/tests/test_i525_skill_sandbox_form.sh`（新規） | 手順書（`.claude/skills/*/SKILL.md`）の `bash scripts/claude/` の起動に環境変数の前置きが無いこと・延長の起動が `excludedCommands` の形に当たること（auto_test の TC-02） |

### 修正アプローチ
延長の値をスクリプトの引数でも受け取れるようにし、手順書の延長の起動を `bash scripts/claude/adversarial-review.sh --round-limit 3 I###` にする。これは今の `excludedCommands` の `bash scripts/claude/*` に当たるので、サンドボックスの設定を変えずに外で動く。作業ツリーの確かめ（DIRTY）は変えない（緩めない）。

### 4-1. `adversarial-review.sh` の引数（修正方針: 延長を前置きなしで渡せるようにし、誤った値では上限を外さない）
`REVIEW_LIB_SOURCE_ONLY` の後（`:476` の位置）を次の形にする（関数だけを読み込むテストの道は変えない）:

```bash
usage_error() { echo "⛔ 使い方: $0 [--round-limit <N>] I###（$1）"; echo "ADVERSARIAL_ERROR: USAGE"; exit 2; }
ISSUE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --round-limit)
      [ $# -ge 2 ] || usage_error "--round-limit の値がありません"
      ADV_ROUND_LIMIT="$2"; shift 2 ;;
    -*) usage_error "知らないオプション: '$1'" ;;
    *)  [ -z "$ISSUE" ] || usage_error "イシューは 1 つだけ: '$ISSUE' と '$1'"
        ISSUE="$1"; shift ;;
  esac
done
[[ "$ISSUE" =~ ^I[0-9]{3}$ ]] || usage_error "受け取った値: '${ISSUE}'"
[[ "$ADV_ROUND_LIMIT" =~ ^[1-3]$ ]] || usage_error "周回の上限は 1〜3（延長は 1 周だけ）: '${ADV_ROUND_LIMIT}'"
```

- 引数と環境変数の両方があるときは**引数を採る**（コマンドの行に書いた値が、その起動で意図した値。環境変数は前の操作の残りでありうる）
- 環境変数 `ADV_ROUND_LIMIT` は残す（テスト・ユーザーが `!` で流す既存の書き方の後方互換）。`:31` の既定値の行は変えない（`test_i202_ledger_cleanup.sh:583` が行全体を照合している）
- 値の確かめは、引数・環境変数のどちらから来た値にも掛ける。今は `ADV_ROUND_LIMIT=abc` のとき `[ "$USED" -ge abc ]` が誤りになり if が偽 → **上限を外して周を始める**（fail-open）。直した後は exit 2 で止まる（fail-closed）。0 も「必ず上限」になり意味が無いので誤りにする
- 使い方の誤りの終了コードと行（exit 2・`ADVERSARIAL_ERROR: USAGE`）は今と同じ（review-gate の 3-2 の exit 2 の扱いがそのまま効く）

### 4-2. `review-gate/SKILL.md`（修正方針: 延長の起動をサンドボックスの外に出る形にし、理由を 1 文残す）
- `:66` を次に置き換える:
  > ユーザーが延長（下の「上限到達」の 2）を承認したときだけ、`bash scripts/claude/adversarial-review.sh --round-limit 3 "$ARGUMENTS"` で実行する（`ADV_ROUND_LIMIT=3` を前に付けない。前に環境変数を付けた形はサンドボックスの外に出る形〔`.claude/settings.json` の `sandbox.excludedCommands` の `bash scripts/claude/*`〕に当たらず、サンドボックスの中で動いて `ADVERSARIAL_ERROR: DIRTY` で止まる・I525）。
- `:85` の「`ADV_ROUND_LIMIT=3` で起動する」を「3-1 の `--round-limit 3` で起動する」にする

### 4-3. テスト（→ auto_test の TC-01・TC-02）
- `test_i197_adversarial_process.sh` の `run` は引数を `I900` に固定しているので、スクリプトに引数を渡す `run_args <名前> <引数…>` を足す（環境変数は `run` と同じ）

## 5. 実装手順（ステップ）
1. `scripts/claude/adversarial-review.sh` の引数の読み取りと上限の値の確かめ（4-1）→ TC-01 参照
2. `scripts/claude/tests/test_i197_adversarial_process.sh` に A9e〜A9i と FG を足す（4-3）→ TC-01 参照（ステップ 1 の後）
3. `.claude/skills/review-gate/SKILL.md` の 2 か所（4-2）と、`scripts/claude/tests/test_i525_skill_sandbox_form.sh` の新規（→ TC-02 参照）。ステップ 1 とは独立
- 未知のリスク（前置きの有無でサンドボックスの中外が決まること・引数つきの `bash scripts/claude/*` が外で動くこと）は §1 のスパイクで先に確かめた

## 6. テスト計画
### 自動
- テストのレベル: どれもハーネスの決定論テスト（bash・一時のリポジトリ・`claude` はスタブ）。アプリのテストは無い（アプリのコードを変えない）
- TC-01 `bash scripts/claude/tests/test_i197_adversarial_process.sh`（既存に追加。詳細は auto_test）: 引数での延長（A9e）・引数と環境変数の優先（A9f）・引数の誤り（A9g）・環境変数の誤り（A9h）・引数つきでも本物の未追跡で DIRTY（A9i）。FG で、引数を読まない写し・値を確かめない写しが落ちることを確かめる
- TC-02 `bash scripts/claude/tests/test_i525_skill_sandbox_form.sh`（新規）: 手順書に前置きの起動が無い・延長の起動が `excludedCommands` の形に当たる。FG つき
- 再発防止: TC-02 が、手順書に前置きの起動を書き戻したら CI で落とす（このバグの根本原因 1 を、延長以外の手順にも広げて止める）
### 手動
- No.1・No.2（実施者 Claude・このセッションの Bash＝実際の Claude Code のサンドボックス）: 前置きの形が実機で DIRTY になること（失敗の注入）と、引数の形が実機で DIRTY にならず周が始まること（詳細は manual_test）

## 7. ロールバック
- このブランチのコミットを `git revert` する（スクリプト・手順書・テストだけ。データ・設定は変えない）。戻した後は、延長は今までどおり `!` での起動に頼る

## 8. Risk & 回避策
| リスク | 回避策 | 処遇 |
|---|---|---|
| R1: 将来、手順書に前置きの起動を書き戻すと、同じ DIRTY がまた珍しい道でだけ起きる | TC-02 が `.claude/skills/*/SKILL.md` の前置きの起動を CI で落とす | 回避 |
| R2: 環境変数 `ADV_ROUND_LIMIT` の値が誤っていた起動が、今までは上限を外して動いていたのに、直した後は exit 2 で止まる（動きの変化） | 誤った値で上限を外すのは fail-open の穴なので止める側に倒す。正しい値（1〜3）の起動は変わらない（TC-01 の A9b・A34 がそのまま通る） | 回避 |
| R3: 環境に `ADV_ROUND_LIMIT=3` が残っていると、引数なしでも承認の無い延長になる（今と同じ動き） | Claude の Bash は環境を持ち越さないので、普通の手順では起きない。承認の決まり（ユーザーの承認のときだけ延長）は手順書で守る。このイシューは承認の決まりを変えない（イシューの「含まない」） | 受け入れ |
| R4: 引数つきの形がサンドボックスの外で動くことは Claude Code の照合の動きに頼る（将来の版で変わりうる） | §1 のスパイクで今の動きを確かめた。手動 No.2 で実機の延長の形をもう一度確かめる。変わったときは DIRTY で止まる（緩む方向ではない） | 受け入れ |

## 9. 確定事項と自律判断
イシューに明記されている（設計確認メモ・本文）:
- サンドボックスの設定（`excludedCommands`）は変えない（案 (b) は採らない）
- 周回の上限の数・延長の承認の決まりは変えない
- サンドボックスの差し込みのファイルそのものの扱い（Claude Code 本体の動き）は範囲外
- 確かめを緩めない（AC3）
Claude が決めた（技術的な選択と理由）:
- 案 (a) だけを採り、(c)（作業ツリーの確かめで装置ファイルを数えない）は採らない — (a) だけで AC1 を満たす。(c) は安全装置の確かめを緩める向きで、装置ファイルと本物の変更の見分けを誤ると、実験が作業ツリーを変えたことを見逃しうる（grill-me で報告済み）
- 引数名は `--round-limit <N>`（イシューの例のまま・環境変数の名前と対応が分かる）。位置は `I###` の前後どちらでもよい（手順書は前に書く）
- 引数と環境変数の両方があるときは引数を採る — コマンドの行の値がその起動の意図。環境変数は残りでありうる
- 環境変数は残す（後方互換）— 既存のテスト（A9・A34・FG-A9・I202 の照合）と、ユーザーが `!` で流す書き方を壊さない
- 上限の値は 1〜3 だけを受け付け、違えば exit 2（USAGE）— 今の環境変数の誤りが上限を外す fail-open の穴を同時にふさぐ。3 を上の限りにするのは、手順書の「延長は 1 周だけ」をスクリプトでも守り、桁の大きな値で比較が壊れる穴（計画変更記録 1）も同時にふさぐため（上限の数そのものは変えない）
- 確かめるテストは既存の `test_i197_adversarial_process.sh` の A9 に足す — 周回の上限のテストの置き場がそこにあり、一時のリポジトリ・スタブの仕組みをそのまま使える
- 手順書の前置きの起動の検査（TC-02）は `.claude/skills/*/SKILL.md` に限る — Claude が自分の Bash で流す手順の正はスキル。runbook の `worktree.md` は primary から人・Claude が流す別の道で、照合の対象（別のワークツリー）も違い、このイシューでは確かめていない
- 手動 No.2 の実機の確かめは、このイシュー自身の review-gate で敵対的レビューを起動するなら、1 周目を `--round-limit 2`（既定と同じ値・延長ではない）で起動して行う。起動しない判定なら test-gate で 1 回だけ同じ形で起動する — 延長の道は実機でしか確かめられない（AC1 の「Claude の Bash から」）。2 は既定値なので承認の決まりに触れない
- 範囲外として retro で扱う候補: `docs/runbooks/worktree.md:100`・`:102` の `DANGER_OK=1`・`KEEP_DATA=1 bash scripts/claude/wt-remove.sh` も前置きの形で、Claude の Bash から流すとサンドボックスの中で動く。`wt-remove.sh` の確かめが装置ファイルで誤るかは確かめていない
- 一覧 scripts/claude/adversarial-review.sh I210 F1・I206 F3・I206 F6・I486 F2〜F5・I486 F7・I486 F8・I430 F8・I228 F3・I228 F5: 残す — どれも延長の受け取り方・作業ツリーの確かめの起動の形とは別の箇所（時刻・鍵・実験の判定・コンテナ・引き継ぎ）で、触る行も違う
- 一覧 FILE=- I224 F9・I223 B1〜B4: 残す — 別のイシューの測定・bot の後片付けで無関係
- 一覧 .claude/skills/review-gate/SKILL.md・scripts/claude/tests/test_i197_adversarial_process.sh: 該当なし
- セキュリティ: アプリのコード・認証・個人情報・依存は変えない（セキュリティ影響なし。bandit・npm audit の対象の変更なし）。ハーネスの安全装置としては、周回の上限の判定を強める向き（誤った値で止める）だけで、緩める変更は無い。引数の値は正規表現で 1〜3 だけを通し、シェルに展開しない
- P3/P5/P8 影響なし（DB・非同期・インフラの変更なし）。P6 影響なし（UI・性能の変更なし）。P9 影響なし（個人情報・テナントデータを扱わない）
- 要件・基本設計・UI/UX の仮定は無い（ユーザーに確かめることは無い）
Danger Ops（有無/手順/ロールバック）:
- 無

## 必ず確かめる項目（高リスク時の敵対的レビューが判定に使う）
| 項目 | 観点 | 確かめ方 | 内容 |
|---|---|---|---|
| V1 | 1 | 読んで可 | 引数 `--round-limit` が上限に効き、環境変数より優先し、誤った値（無い・整数でない・0・知らないオプション・イシュー 2 つ）と誤った環境変数では claude を呼ばずに exit 2 で止まる（TC-01 の A9e〜A9h）。引数を足しても上限を外す道ができていない |
| V2 | 2 | 読んで可 | TC-01 の FG（引数を読まない写し・値を確かめない写し）と TC-02 の FG（前置きを書いた写し・延長の起動を消した写し）が本当に落ちる。A9i が DIRTY を本物の未追跡のファイルで起こしている（スタブの都合で通っていない） |
| V3 | 3 | 読んで可 | AC2（引数なしは通算 2 周で止まる・A9a）と AC3（本物の未追跡で DIRTY・A9i と A11）を満たし、作業ツリーの確かめ（`dirty_outside_records`）を変えていない。手順書の延長の起動が `excludedCommands` の形に当たる（TC-02） |

## レビュー結果
- [20261116_0145 判定: ✅ 完了](../../reviews/I525_plan_review_20261116_0145.md)
- [20261116_0126 判定: ✅ 完了](../../reviews/I525_plan_review_20261116_0126.md)

## 計画変更記録
1. review-gate（コードレビュー 20261116_0134 の台帳 F1・F2）:
   - 計画書の記載: 「上限の値は 1 以上の整数だけを受け付け」（§4-1 の `^[1-9][0-9]*$`）
   - 採った方法: 受け付ける値を 1〜3（`^[1-3]$`）に限る
   - 理由: F1 桁の大きな値（例 99999999999999999999）で `[ -ge ]` が誤りになり、if が偽で上限を外して周が始まる（fail-closed と言いながら fail-open が残っていた）。F2 値に上の限りが無く、手順書の「延長は 1 周だけ」をスクリプトが守らない。1〜3 に限ると両方が 1 行でふさがる。今までの延長はどれも 3（I200・I468・I469）で、既存のテストも 3 までしか使わない。上限の数・承認の決まりは変えない（手順書の決まりをスクリプトでも守るだけ）
   - 計画レビューのやり直し: 要（受け付ける値の範囲＝仕様を変える）
   - 見送り: F3（延長の起動が承認画面なしで通る）— 延長の承認は会話の中のユーザーの選択（止める条件 3）で、前置きの形でも承認画面で守っていたかは確かめていない。上の 1〜3 の限りで延長は 1 周に限られる。retro で扱う。F4・F5 は Low（一覧へ）
