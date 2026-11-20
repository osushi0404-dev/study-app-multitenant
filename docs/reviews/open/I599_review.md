# I599 レビュー: サンドボックスの中から scripts/claude/ に書いたスクリプトをレビュー前に外で流せる穴を塞ぐ

## 変更概要
-

## 変更点
-

## 影響範囲
- Backend/Frontend/DB: なし
- Config: `.claude/settings.json`・`.claude/hooks/`（新規）・`scripts/claude/hooks/pretooluse_guard.py`・`scripts/claude/code-review.sh`・`docs/runbooks/danger-ops.md`・`docs/runbooks/harness-audit.md`・`scripts/claude/tests/`

## テスト結果
- 自動:
- 手動:

## 計画との差分
-

## ロールバック
- PR を revert する。`~/.cache/claude-reviewed-hooks/` は消してよい

## 自律判断の記録
- [plan] 中で動かす範囲を「流すスクリプトから呼ぶファイルをたどって変更に届くときだけ」にした — イシューのメモの「1 つでも違えばすべて中」では変えていないレビュー役まで中で失敗し段階ごとに人の手が要る。ユーザーに確かめ、BP と開発効率で最善のやり方で、との判断（2026-11-20）
- [plan] 判定の本体を `.claude/hooks/unreviewed.py`、フックの起動役を `.claude/hooks/reviewed-hook.sh` に置いた — `scripts/claude/` の外でサンドボックスから書けず、判定を直しても呼び元が中に回らない
- [plan] `run-all.sh`・`test-session.sh` は直さず見張りの側で入口を扱う。`code-review.sh` のゲートの実走（計画の調査で見つけた入口）を範囲に足した — イシューの実装対象から変えた。理由は計画書 9
- [plan] スパイクで「フックの書き換えの後のコマンドで外に出すかが決まる」ことを確かめた（計画書の調査結果 6）
