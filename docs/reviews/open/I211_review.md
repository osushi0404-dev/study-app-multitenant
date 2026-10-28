# I211 レビュー: ハーネスのテストの python・PyYAML・pre-commit の版を CI と手元でぴったり揃える

## 変更概要
- ハーネスのテストの python の道具の版の正を uv の公式のファイル（`scripts/claude/tests/.python-version`・`uv.lock`・`pyproject.toml` の `required-version`）にし、手元も CI も `bash scripts/claude/tests/run-all.sh` が uv の環境で流す（計画中）

## 変更点
- （実装後に記入）

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.github/workflows/ci.yml`（harness-tests ジョブ）・手元の開発環境（pipx の uv）

## テスト結果
- 自動:
- 手動:

## 計画との差分
- なし / あり（理由）

## ロールバック
- PR を revert。手元の uv は `pipx uninstall uv`

## 自律判断の記録
- [plan] 版の正を uv の公式のファイルにし、入口の `run-all.sh` が uv の環境で流し直す形にした — 公式の仕組みがずれを止め、許可ルールを変えずに済む（計画書 9 の D1・D2）
- [plan] 手元の uv は Claude が `pipx install uv==0.13.6` で入れる — 設計確認メモの「ユーザーが入れる」よりユーザーの手間が少なく、pipx で戻せる（D3）
- [plan] `run-all.sh` に引数で一部のテストを流す形を足した — 一部のテストも同じ版の環境で流すため（D6）
- [plan-review] Warning（setup-uv が runner で required-version と python を読めるか未実証）は計画のステップ 3・手動 No.1・R1 のまま進める — 実際の runner でしか確かめられず、確かめる手順と失敗時の対応が計画にある
- [plan-review] Warning（setup-uv を SHA に固定していない）は直さない — 既存の `actions/*@v4` と同じ運用。SHA 固定はリポジトリ全体の方針として扱う
- [plan-review] Info（`OK: uv uv 0.13.6` の名前の重複表示）は直さない — 既存の git の行（`OK: git git version`）と同じ表示で、見た目だけ

STAGE_DONE: plan NEXT: plan-review
STAGE_DONE: plan-review NEXT: design-security-review
