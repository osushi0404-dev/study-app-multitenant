# I480 手動テスト: SECURITY=yes でも Low・再現なしの指摘は軽い指摘の一覧に回す

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `.claude/skills/retro/SKILL.md` の手順 4-0（後続イシューの条件の行と「最優先」の行）と `docs/runbooks/review-rules.md` の振り分けの要約を Read で読み、`scripts/claude/code-review.sh` の `route_reasons()` と突き合わせる | retro の後続イシューの条件に「`SECURITY=yes` で再現ありか Medium 以上（Low かつ再現なしは一覧）」とあり、「重さに関係なく」が無い。最優先の条件が「出力の理由に `SECURITY=yes` が付いた行」。review-rules の要約も「`SECURITY=yes` で再現ありか Medium 以上」。3 つが `route_reasons()` の条件と食い違わない | Claude |  | TC-03 |
| 2 | このブランチの台帳の無い状態で、Q10 と同じ 6 行の台帳を一時ファイルに書き、`REVIEW_LIB_SOURCE_ONLY=1` で `code-review.sh` を読み込んで `ledger_route issue`・`ledger_route backlog` を流す | issue 側に F3・F4・F5・F6（F5 の理由は `アプリ本体` だけ）、backlog 側に F1・F2（理由 `Low／再現なし`）が出る | Claude |  | TC-01 を実際の出力の形で見る |

## 画面確認
<!-- frontend/src を変えないイシューなので該当なし -->
| 日時 | コミット | 画面と操作 | アカウント | 期待した結果 | 実際の結果 | 画像 |
|---|---|---|---|---|---|---|
|  |  | 理由: 画面の変更なし（ハーネスのスクリプトと手順書だけ） |  |  |  |  |

結論:
