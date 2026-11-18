# I569 レビュー: イシューの番号の検査が 3 桁固定で、I1000 から流れ全体が止まる

## 変更概要
- 番号を受け付ける判定 8 か所（bash 5 本・見張り・開始時のフック・close のスキル）を「I＋数字 3 つ以上」にそろえ、3 桁固定の書き方を CI で止める走査のテストを足す

## 変更点
- `scripts/claude/flow-stage.sh`・`gate-check.sh`・`adversarial-review.sh`・`check-frontend-evidence.sh`・`check-manual-test-executor.sh`: `^I[0-9]{3}$` → `^I[0-9]{3,}$`（gate-check.sh は shellcheck の注記も 1 つ足した）
- `scripts/claude/hooks/pretooluse_guard.py`: `_EVIDENCE_FILE_RE` の番号を `{3,}` に（ほかは変えない）
- `scripts/claude/hooks/sessionstart_context.py`: `ISSUE_ID` を `{3,}` に
- `.claude/skills/close/SKILL.md`: 番号の確かめを `^[0-9]{3,}$` に・「3桁」の文言
- `.claude/skills/plan-issue/SKILL.md`: ブランチ名の「イシュー番号3桁」
- `scripts/claude/tests/test_i569_issue_number_digits.sh`（新規）: 動きのテストと 3 桁固定の走査（CI で毎回）
- `docs/reviews/backlog/I221.md`: F7 の行を消した

## 影響範囲
- Backend/Frontend/DB: なし
- Config: ハーネスのスクリプト・フック・スキル・ハーネスのテスト

## テスト結果
- 自動: 決定論ゲート 6 本 exit 0（review-gate の実走）・CI 成功・コードレビュー OK・敵対的レビュー 1 周 OK
- 手動: Claude 1 件 OK（3 桁の I569 で flow-stage・gate-check が今までどおり）。人の手動テストは無し

## 計画との差分
- あり（小）: gate-check.sh の shellcheck の注記・FG-03 の注入の書き方・TC-02〜TC-05 の不正な値に `I1000x` を足した（計画変更記録）

## ロールバック
- この PR を revert する

## 自律判断の記録
- [plan] 再発を断つ仕組みは「8 か所を直す＋3 桁固定の書き方の走査を CI で毎回流す」にした。判定を共通の関数に寄せる案は、bash・Python・スキルの 3 種にまたがり覆えないため採らない — 言語によらず新しいファイルも止められる
- [plan] 走査の範囲から記録の場所（`docs/`）を外した — 記録は古い形を説明として書くもので、判定は無い（イシューの AC 3 の「closed の記録を除く」の読み替え）
- [plan] `.claude/skills/plan-issue/SKILL.md` のブランチ名の「イシュー番号3桁」を同梱した — イシューは I546 で直すとしていたが残っていた。同じ食い違いの 1 行
- [plan] 一覧（台帳の残り）は `I221.md` の F7 だけ同梱し、ほかは別の話なので残す（計画書 9）
- [plan-review] 計画レビューは Info 3 件だけで HIGHRISK（見張りの変更）。Info は計画書に理由が書いてあり直しは不要 — 方式・範囲を変えない
- [design-security-review] Blocker・High なし（Low 3 件・シナリオ Low 4 件はどれも計画の TC で覆う）。番号の確かめに上限の桁数は付けない — 数字だけでパスの外へ出られず、長い列はファイルが無いだけで害が無い
- [implement] FG-03 の注入を `..` の名前から入れ子・絶対パスに変えた — 見張りは `..` を正規表現とは別にも止めるので、`..` では正規表現を緩めた写しでも止まり、注入が働かない（自動テスト文書の FG-03 も同じに直した。方式は変えない）
- [implement] `/simplify`（4 観点）: 簡素化の指摘（不正な値のループ 5 つの重複・YES/NO の書き方の重複・同じ並びの 2 重ループ・1 回だけの変数）を反映。TC-02〜TC-05 の不正な値に `I1000x` も入れて TC-01 とそろえた。再利用・効率は指摘なし。直す深さの指摘のうち `code-review.sh` の `^I[0-9]+$`（`I12` も通す）・走査を許可の側に替える案・bash の共通関数は見送り — どれも I1000 は通り、計画の範囲外（3 桁固定ではない）。走査の形は計画 R3 で受け入れ済み
- [implement] テストのファイルは 100644（ほかのテストと同じ。`bash` で呼ぶ）
- [review-gate] コードレビュー OK（止める指摘なし・決定論ゲート 6 本 exit 0）・敵対的レビュー 1 周で OK（V1〜V4 確認済み）。台帳の F1（Medium・テストが「実在しない番号」に `I1000` を使い、#1000 が実在すると TC-03 が本物の敵対的レビューを起動しうる）は止める指摘ではないので fix-loop に回さず、retro で #1000 より前に直す後続にする — OK の周の後に差分を足すと gate-check が通さず、周の上限も使う
- [test-gate] 重いゲートの委譲は無く、手元で流し直すものは無し。Claude の手動テスト 1 件 OK・人の手動テストは無いので retro へ

STAGE_DONE: plan NEXT: plan-review

STAGE_DONE: plan-review NEXT: design-security-review

STAGE_DONE: design-security-review NEXT: implement

STAGE_DONE: implement NEXT: review-gate

STAGE_DONE: review-gate NEXT: test-gate

STAGE_DONE: test-gate NEXT: retro
