# 診断レビュー [I599]
## 指摘一覧
| 重大度 | 観点 | 指摘内容 | 該当箇所 |
|--------|------|---------|---------|
| Info | 根本原因 | 原因として成立している。フックの `command` を起動役経由に変えたのに、古い形との完全一致を見るテストが 2 本残っていた。CI の失敗内容とも整合する。事実は `test_i187_frontend_verify_config.sh:154` の `h.get("command") == GUARD_CMD` で確認できた。計画時の調査が `test_settings_permissions.sh` だけで、古い形の文字列でリポジトリ全体を grep しなかったことが直接の原因という説明も妥当。 | 根本原因 |
| Info | 対応方針 | 案 A の推奨は妥当。案 B は範囲が広がる。案 C は TC-16 と食い違い、起動役を通らない形を許す。どちらも退けた理由が成立している。案 A でも「起動役を通す形」を完全一致で見るため、守りの検証は弱まらない。 | 対応方針 |
| Info | 影響調査 | 修正時は 2 本の期待値を、`settings.json` の実際の `command` と同じ形に揃えること。`GUARD_CMD` のような定数があれば、そちらを 1 か所直せば済む。直したあとは run-all.sh を通しで流して他に影響がないか確認すること。 | test_i187_frontend_verify_config.sh / test_sessionstart_context.sh |

## 影響調査の網羅性評価
- 古い形の文字列でリポジトリ全体を grep しており、範囲は十分。
- 当たりは次の 3 種類だった。
  - 失敗している 2 本。
  - `test_settings_permissions.sh:184` の意図的な使い方。失敗を注入するために古い形へ戻しており、問題ない。
  - 過去の記録文書（`docs/*/closed`）。履歴なので直す必要はない。
- `code-review.sh:431`、`test_i569` の 145 行目、`test_pretooluse_container_guard.sh` の F9/P81 も確認した。いずれも `settings.json` の登録文字列を見るものではなく、フックを直接呼ぶ使い方なので影響しない。
- `"command"` の比較を持つ `scripts/claude` 配下のコードも見た。ほかに `settings.json` のフック登録を完全一致で検証するものは見当たらなかった。メモの「同型は当たりなし」という結論は妥当。

VERDICT: OK
