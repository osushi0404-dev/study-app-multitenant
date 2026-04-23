# I050 手動テスト計画

## 対象
plan_I050: migration チェーンの型不整合を修正し CI フレッシュ DB で migrate を通す

## 手動テストケース

手動テストはなし。

変更は `problems/0004` の `dependencies` メタデータのみであり、UI/API の振る舞いに変化はない。
フレッシュ DB での動作確認は CI（`ci.yml`）で代替する。
