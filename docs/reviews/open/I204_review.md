# I204 レビュー: ハーネスのテストが頼る道具を CI と手元で同期する

- 計画書: docs/plans/open/plan_I204.md
- イシュー: docs/issues/open/I204.md（#340）
- Draft PR: #354

## 変更概要
ハーネスのテストが頼る道具と版の一覧（`scripts/claude/tests/required-tools.txt`）を正にし、`run-all.sh` の冒頭で `check-tools.sh` が確かめる（足りなければテストを流さずに不合格・入れ方を出す）。CI の Harness Tests は一覧の pip の列を読んで入れる。道具が無ければ黙って SKIP する 3 か所をやめ、shellcheck は pre-commit 経由で `.pre-commit-config.yaml` の固定の版を使う。一覧と CI の食い違い・SKIP の分岐の再発を止めるテストを足した。

## 変更点
- 新規 `scripts/claude/tests/required-tools.txt`（6 つの道具・版の下限・CI で pip で入れるもの・入れ方）・`scripts/claude/tests/check-tools.sh`（確かめる・`--pip-specs`）
- `scripts/claude/tests/run-all.sh`: 冒頭で `check-tools.sh`
- `scripts/claude/tests/test_review_commit_lifecycle.sh`: TC-C1 を `pre-commit run shellcheck`（`Passed` の行まで見る）に。SKIP を消した
- `scripts/claude/tests/test_compose_ports.sh`・`scripts/claude/tests/guard_bash_oracle.py`: 道具が無ければ SKIP する分岐を消した
- `.github/workflows/ci.yml`: Harness Tests の「Install test dependencies」の 1 step を、一覧から読んで入れる形に
- 新規 `scripts/claude/tests/test_i204_tool_sync.sh`（一覧・`run-all.sh` の冒頭・TC-C1・CI との食い違い・SKIP の分岐の規則。失敗注入つき）
- `docs/runbooks/onboarding.md`: 「手元の準備（ハーネスのテスト）」

## 影響範囲
- ハーネスだけ（計画書 3）。アプリ本体・DB の変更なし。`.github/workflows/ci.yml` は Harness Tests の 1 step だけ

## テスト結果
- 自動: TC-01 `test_i204_tool_sync.sh` pass=29（4.5・4.6 の前は S1 が 2 か所に当たって不合格）・TC-02 `PASS=31 FAIL=0`（SKIP なし）・TC-03 pass=13・TC-04 見逃し=0・TC-05 pass=174・TC-06 CI 全緑（Harness Tests `run-all: pass=47 fail=0`）
- gate-check: GATE_CHECK OK（2026-10-28）
- 手動: No.1 CI のログで一覧の確認 6 行 OK（python 3.11.17・pre-commit 4.7.0・固定の shellcheck が Passed）・No.2 docker が通らないとテストを流さず exit 1・No.3 手元で 6 行 OK。すべて Claude 実施・Human の項目なし

## 計画との差分
- 計画変更記録 1（計画レビューの Warning 対応）・2（shellcheck の行の確認の形・一覧の誤りを標準エラーへ）・3（`/simplify` の整理）。どれも方式・範囲・受け入れ条件は変えない

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

- [test-gate] 手動 3 件はすべて Claude で実施し OK。No.1 は最後のコードのコミット（c14293c。その後は記録だけ）の CI のログで確かめた — HEAD の CI は記録だけの変更で中身が同じ。Human の項目は無いので retro へ
STAGE_DONE: test-gate NEXT: retro
