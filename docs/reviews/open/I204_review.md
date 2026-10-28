# I204 レビュー: ハーネスのテストが頼る道具を CI と手元で同期する

- 計画書: docs/plans/open/plan_I204.md
- イシュー: docs/issues/open/I204.md（#340）
- Draft PR: #354

## 変更概要
（実装後に書く）

## 変更点
（実装後に書く）

## 影響範囲
- ハーネスだけ（計画書 3）。アプリ本体・DB の変更なし。`.github/workflows/ci.yml` は Harness Tests の 1 step だけ

## テスト結果
（test-gate の後に書く）

## 計画との差分
（実装後に書く）

## ロールバック
- PR を revert する（計画書 7）

## 自律判断の記録
- [plan] 一覧は `scripts/claude/tests/required-tools.txt`、確かめるのは `check-tools.sh`（`run-all.sh` の冒頭から呼ぶ）にした — 手元で単独で流せ、写しの一覧で単体のテストができ、CI も `--pip-specs` で同じ一覧から入れられる
- [plan] PyYAML・pre-commit も python と同じく版の下限だけを書いた — 手元の PyYAML は apt のもので、版の固定には仮想環境が要る。ぴったり揃えるのは後続のイシューで python と一緒に扱う
- [plan] `guard_bash_oracle.py` の「bash が無ければ SKIP」も消す — AC3 を全件で調べて当たった同じ形
- [plan] TC-C1 は pre-commit の `Passed` の行まで合格の条件にした — スパイクで、対象外のファイルだと `Skipped` で exit 0 になることを確かめた

- [plan-review] 判定 HIGHRISK（`.github/workflows/ci.yml` の変更）。Warning 2 件（一覧の shellcheck の確認が Skipped を見逃す・依存の監査の扱い）と Info 2 件は計画に足し、runner の挙動の Warning はステップ 1 に前倒し済みで対応不要とした — 方式・範囲・受け入れ条件は変わらないので再レビューはしない

STAGE_DONE: plan NEXT: plan-review
- [design-security-review] Blocker・High・Medium なし（Low 4 件・シナリオ 3 件はすべて計画の防御とテストで覆う）。取得元の版の固定は後続のイシューへ — 今の `pip install pyyaml` と同じ水準で、ジョブに secrets が無い
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement

- [implement] ステップ 1 を先に push し、CI の runner で pre-commit が shellcheck を入れられること・docker compose があることを確かめた（Harness Tests pass・一覧の確認 6 行 OK・`run-all: pass=46 fail=0`） — 計画の未知リスク先行
- [implement] shellcheck の行の確認を、通らないとき pre-commit の出力を出す形にし、一覧の誤りの文言は標準エラーに出した（計画変更記録 2） — 原因が見える・CI の pip に誤りの文言を渡さない
- [implement] /simplify の指摘のうち、確認の重複を減らす（FG-L3 を小さな写しに）・重なったコメント・同じ計算の整理は採り、shellcheck の行を一覧から外す・CI のキャッシュ・並行の確認は採らなかった（計画変更記録 3） — 前者は振る舞いを変えない整理、後者はイシュー・計画で決めた形を変えるため
- [implement] ワークフローの書き換えで承認画面が出ることを事前に予告しなかった（ユーザーから「この承認は必須か？」と質問あり）。確認は settings.json の `Edit(.github/workflows/**)` の意図した確認と説明した — retro で扱う
STAGE_DONE: implement NEXT: review-gate

- [review-gate] 基本レビュー OK（`docs/reviews/I204_code_review_20261028_1644.md`・CI_WAIT: OK・RISK: YES）。台帳の F1〜F6 はすべて Low・再現なしで止めない — retro が一覧か後続イシューへ回す
- [review-gate] 敵対的レビュー 1 周目 OK（`docs/reviews/I204_adversarial_review_20261028_1656.md`・V1〜V5 すべて確認済み・未検証 0）。ハーネスの Medium 1 件（`ci_check` の install の検出が `apt-get -y install` などオプションを挟む形を拾わない）は次の周に進む理由にせず記録に残す — review-gate の決まり（ハーネスの Medium は retro へ）。OK の周の後に差分を足さない
STAGE_DONE: review-gate NEXT: test-gate
