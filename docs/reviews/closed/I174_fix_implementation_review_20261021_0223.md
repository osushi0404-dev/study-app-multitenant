# 実装レビュー [I074]

## 指摘一覧

| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| Info | 方針一致 | `_is_rm_rf` の変更（`-f` 不要化）により関数名と意味が乖離。ただし `_cmd_hard` 内に `any(t in ("/", "/*") for t in toks[1:])` ガードが存在し、非ルートパスの `rm -r` は `_cmd_danger`（DANGER_OK=1 経路）へ正しく流れるため機能的回帰なし | `pretooluse_guard.py` `_is_rm_rf` / `_cmd_hard` |
| Info | 回帰・副作用 | `_git_revert_target_on_dirty` が `_danger_reasons`（文字列レベル）と `_cmd_danger`（コマンドレベル）の両方から呼ばれる二重呼び出しは `list(dict.fromkeys(reasons))` による重複排除で吸収済み。機能的問題なし | `pretooluse_guard.py` `_danger_reasons` / `_analyze` |
| Info | スコープ | 未追跡新規ファイル（I074.md〜I173.md・dashboard proposal）はイシュードキュメント類であり実装本体と無関係。スコープ逸脱なし | `docs/issues/open/` 以下 |

VERDICT: OK
