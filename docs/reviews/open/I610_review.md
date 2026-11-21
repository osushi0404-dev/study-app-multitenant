# I610 レビュー: フックの起動役の無視されるファイル・gate-check のリンクの見逃し・run-all の中のキャッシュ

## 変更概要
- フックの起動役は「変更があるか」を `unreviewed.py dirty` で判定し、フックを `python3 -I` で起こす（F24）
- `gate-check.sh` は `/dev/null` を指すリンクを汚れとして数える（F30）・G9b の向きを直す（F31）
- `run-all.sh` はキャッシュに書けないときだけ一時フォルダを使う
- 手順書に外と中の境目を動かすときの確かめを足す

## 変更点
- （implement 後に記入）

## 影響範囲
- Backend/Frontend/DB: なし
- フック: `.claude/hooks/reviewed-hook.sh`
- 関所・テスト: `scripts/claude/gate-check.sh`・`scripts/claude/tests/run-all.sh`・`scripts/claude/tests/i599_cases.py`・`scripts/claude/tests/test_i193_official_flow.sh`
- 文書: `docs/runbooks/plan-writing-rules.md`

## テスト結果
- 自動: （未実施）
- 手動: （未実施）

## 計画との差分
- なし

## ロールバック
- PR を revert する（データの変更なし）

## 自律判断の記録
- [plan] 起動役の「変更があるか」は `unreviewed.py dirty` を呼ぶ（シェルに git の確かめを写さない）— 定義を 1 か所にそろえるため
- [plan] `run-all.sh` のキャッシュは決定論テストにせず手動テストで確かめる — 壊れると手元のテストがすぐ落ちて気づけるため

STAGE_DONE: plan NEXT: plan-review
