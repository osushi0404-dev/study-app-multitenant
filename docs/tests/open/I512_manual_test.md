# I512 手動テスト: 計画で受け入れた残余リスクを、後続イシュー・最優先から外して一覧へ回す

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `docs/plans/templates/plan_template.md` の 8、`.claude/agents/code-reviewer.md` の「計画で受け入れた残余リスク（I512）」と FINDING 行の欄の説明、`.claude/skills/retro/SKILL.md` 4-0、`docs/runbooks/review-rules.md`「検証の全体設計」の振り分けの要約を Read で読み、`scripts/claude/code-review.sh` の `accepted_risks()`・`accepted_why_not()`・`route` モードの `ACCEPTED_DROPS` と突き合わせる | 4 つの文書のどれも、(a) 受け入れは 8 の表の処遇の列が `受け入れ` の R 番号の行だけ (b) 目印は `ACCEPTED=R<番号>` (c) 効くのは Medium 以下・再現なし・アプリ本体でない行 (d) 照合に合わなければ今までどおり (e) 止める判定には効かない、と食い違わない。retro の一覧の行の形が `--route backlog` の出力の形（`SECURITY=` つき）と同じ | Claude |  | 文言の固定テストは作らない（plan §6） |
| 2 | スクラッチパッドに、目印だけが違う Medium・再現なし・harness・`SECURITY=yes` の 5 行（目印が効かなければ理由 `SECURITY=yes` で issue 側になる行）（`ACCEPTED=R1`〜`R5`）の台帳を作り、`REVIEW_LIB_SOURCE_ONLY=1` で `code-review.sh` を読み込んで `ledger_route backlog <台帳> docs/plans/open/plan_I512.md` と `ledger_route issue <台帳> docs/plans/open/plan_I512.md` を流す | R3 が受け入れとして読まれ、一覧の行の理由が `再現なし／計画で受け入れ（R3）`。R1・R2・R4・R5（処遇が回避）の目印では issue 側 | Claude |  | 新しい形で書いた本物の計画書が読めることを見る |
| 3 | 本物の入口で `bash scripts/claude/code-review.sh --route issue I430` と `bash scripts/claude/code-review.sh --route backlog I430` を流す | どちらも exit 0。標準エラーに `記録: docs/reviews/closed/I430_code_review_20261113_1911.md` と `計画書: docs/plans/closed/plan_I430.md`。I430 の台帳には目印が無いので、issue 側は今までどおり F1〜F3、backlog 側の行には `SECURITY=` の欄が入る | Claude |  | 目印の無い過去の台帳で振り分けが変わらないことを本物の記録で見る |

## 画面確認
<!-- frontend/src を変えないイシューなので該当なし -->
| 日時 | コミット | 画面と操作 | アカウント | 期待した結果 | 実際の結果 | 画像 |
|---|---|---|---|---|---|---|
|  |  | 理由: 画面の変更なし（ハーネスのスクリプトと手順書だけ） |  |  |  |  |

結論:
