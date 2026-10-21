確認完了。`_DESTROY_PREFIXES = ("env", "sudo", "command", "exec", "time", "nohup", "nice", "timeout", "stdbuf", "ionice", "doas")` — `rm` は含まれておらず、`_head_candidates` の前置コマンド分岐が `rm` 自体に誤って適用されない設計であることを確認。

---

# 実装レビュー [I074]

## 指摘一覧

| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| Info | スコープ | `docs/issues/open/I093〜I181` および `docs/reviews/I0##_issue_review_*.md` 系のファイル（計 30 件超）が「未追跡新規ファイル」として差分に含まれている。これらは I179 の変更スコープ（guard.py・worktree.md・wt-remove.sh・テスト）に直接関係しない既存ローカルファイル群であり、今回の修正によって追加・変更されたものではないと判断できる。追加のみで既存コードへの副作用はなく、ブロッカーには当たらない。 | `docs/issues/open/I093.md`〜`docs/reviews/I179_issue_review_*.md` |
| Info | 回帰・副作用 | `_head_candidates` は先頭トークンが `_DESTROY_PREFIXES`（sudo/env/timeout 等）のとき、以降のトークン列中に現れる `_KNOWN_HEADS` の全位置を候補にする。`sudo -u git rm ...` のようなコマンドでは "git" と "rm" の 2 候補が生成される。"git" 候補は `git rm（現在ワークツリー上）` として解釈されるが `_destroy_blocked` で自ワークツリーへの操作として非ブロック、"rm" 候補は正しくブロック対象に到達する。誤ブロック・誤許可ともに発生しないが、意図より多い候補が処理される点は把握しておくと良い。 | `_head_candidates` / `_KNOWN_HEADS` |

## false-green 評価の再確認

- `_DESTROY_PREFIXES` に `rm` が含まれないことを実ファイルで確認。`rm` 単独コマンドは常に単一候補として処理される（スコープ外分岐に落ちない）。
- `_glob_split` の展開文字を `[*?\[{]` へ拡張（中かっこ追加）、`_destroy_blocked` の `fnmatch` 廃止と段数判定への切り替えが、F1〜F2 の根本原因（bash展開規則の再現漏れ）を構造的に塞いでいることを差分で確認。
- サブシェル括弧の積み戻し（`sub_stack`）と `outer`/`cwd` の管理が、cd の外部持ち越し禁止の意図に沿って正しく実装されている。
- `wt-remove.sh` と `worktree.md` の手順書修正（§2 コピー先・§4 登録なし `.git` 手順・§9 回避説明）は、F5 の消費箇所更新漏れを対処している。

VERDICT: OK
