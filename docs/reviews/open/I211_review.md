# I211 レビュー: ハーネスのテストの python・PyYAML・pre-commit の版を CI と手元でぴったり揃える

## 変更概要
- ハーネスのテストの python の道具の版の正を uv の公式のファイル（`scripts/claude/tests/.python-version`・`uv.lock`・`pyproject.toml` の `required-version`）にし、手元も CI も `bash scripts/claude/tests/run-all.sh` が uv の環境で流す

## 変更点
- 新規 `scripts/claude/tests/pyproject.toml`・`.python-version`（3.11.18）・`uv.lock`（PyYAML 6.0.3・pre-commit 4.7.0）・`test_i211_version_pin.sh`
- `run-all.sh`: uv の環境の外なら `uv run --locked` で流し直す・引数で一部のテストを流す
- `check-tools.sh`・`required-tools.txt`: 版の列を `-`／`lock`（正とぴったり）にし、`--pip-specs` をやめた。出力が空のときの字下げの空行を出さない
- `.github/workflows/ci.yml`（Harness Tests）: setup-python と pip install をやめ、`astral-sh/setup-uv@v10.3.3`（`version-file: scripts/claude/tests/pyproject.toml`）に
- `test_i204_tool_sync.sh`: 4 列の一覧・CI が版の正だけを読むことの確かめ（install の検出の強化・setup-uv の版の形）
- `docs/runbooks/onboarding.md`: 初回の準備・一部のテストの流し方・版を上げる手順
- `docs/reviews/backlog/I204.md`: F2・F3・F5 を同梱して消した

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.github/workflows/ci.yml`（harness-tests ジョブ）・手元の開発環境（pipx の uv）

## テスト結果
- 自動: 決定論ゲート 4 本 exit 0（review-gate）。CI 全ジョブ pass（run 40717058976・Harness Tests `run-all: pass=48 fail=0`）。基本レビュー OK（止める指摘 0・Low 6）・敵対的レビュー OK（未検証 0・新しい Critical/High 0）
- 手動: No.1〜No.4 OK（すべて Claude・Human の項目なし）

## 計画との差分
- あり: 計画変更記録 1〜3（失敗したテストの案内の形・ロックの版の記録・/simplify の整理）と fix-loop 2 回（setup-uv の版を細かい版のタグで書く・FG-K2 の `--offline` を外す）。方式・範囲・受け入れ条件は変えていない

## ロールバック
- PR を revert。手元の uv は `pipx uninstall uv`

## 自律判断の記録
- [plan] 版の正を uv の公式のファイルにし、入口の `run-all.sh` が uv の環境で流し直す形にした — 公式の仕組みがずれを止め、許可ルールを変えずに済む（計画書 9 の D1・D2）
- [plan] 手元の uv は Claude が `pipx install uv==0.13.6` で入れる — 設計確認メモの「ユーザーが入れる」よりユーザーの手間が少なく、pipx で戻せる（D3）
- [plan] `run-all.sh` に引数で一部のテストを流す形を足した — 一部のテストも同じ版の環境で流すため（D6）
- [plan-review] Warning（setup-uv が runner で required-version と python を読めるか未実証）は計画のステップ 3・手動 No.1・R1 のまま進める — 実際の runner でしか確かめられず、確かめる手順と失敗時の対応が計画にある
- [plan-review] Warning（setup-uv を SHA に固定していない）は直さない — 既存の `actions/*@v4` と同じ運用。SHA 固定はリポジトリ全体の方針として扱う
- [plan-review] Info（`OK: uv uv 0.13.6` の名前の重複表示）は直さない — 既存の git の行（`OK: git git version`）と同じ表示で、見た目だけ
- [design-security-review] Blocker・High なし。Medium（setup-uv の浮動タグ）は残余リスクとして retro へ — 既存の action と同じ運用で、harness-tests は秘密情報を持たない
- [implement] 手元に `pipx install uv==0.13.6` で uv を入れた — 計画の D3 どおり（`pipx uninstall uv` で戻せる）
- [implement] /simplify の点検（4 観点）で、テスト専用の抜け道（`pyproject.toml` が無ければ流し直さない）を消し、場所の書き方・変数の渡し方・K1・`--offline`・runbook を整理した（計画変更記録 3）。見送り: 版の確かめを uv に任せて `check-tools.sh` の lock の行をやめる案（AC4 の止まり方と CI のログでの版の確認〔手動 No.1〕が無くなる）／install の検出をやめる案（AC7 と I204 の敵対的レビューの指摘に反する）／setup-uv の `with` を緩める案（版の正を迂回する入力を通さないため今の固定のまま）／テストの一時のリポジトリの準備を共通にする案（テストのファイルは自分の中で完結させるのがこのリポジトリの書き方）／CI で python もキャッシュする案（数秒のための ci.yml の変更は範囲外）
- [fix-loop] CI の失敗（setup-uv に `v10` の動くタグが無い）を案 A（細かい版 `v10.3.3` で書く＋`ci_check` で版の形を確かめる）で直した — 配布元の版の付け方どおりで粗く確実。SHA 固定（案 B）はリポジトリ全体の方針として残余リスクのまま（診断レビュー PASS: docs/reviews/I211_fix_diagnosis_review_20261029_0014.md）
- [fix-loop] CI の FG-K2 の失敗（`--offline` で別の理由の失敗になった）を、FG-K2 だけ `--offline` を外して直した — 確かめたい失敗（ロックのずれ）を確実に起こすため（診断レビュー PASS: docs/reviews/I211_fix_diagnosis_review_20261029_0029.md）
- [fix-loop] ユーザーの指示（Actions の承認は秘密・個人情報が出うる書き換えだけに）を I200（#335）の設計確認メモ・解決方針・受け入れ条件に同梱した — I200 が「見張りの確認を本当に危ない操作だけに絞る」イシューで目的が同じ。I211 の範囲（版揃え）は変えない

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
STAGE_DONE: design-security-review NEXT: implement
STAGE_DONE: implement NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: fix-loop
STAGE_DONE: fix-loop NEXT: review-gate
STAGE_DONE: review-gate NEXT: test-gate
STAGE_DONE: test-gate NEXT: retro
