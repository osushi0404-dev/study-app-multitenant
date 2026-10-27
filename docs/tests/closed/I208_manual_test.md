# I208 手動テスト: 台帳の残りの振り分けと一覧の行をスクリプトが出すようにし、テストを実物の一覧に依存させない

実物の記録・一覧で、新しい振り分けのコマンドと計画で一覧を見るコマンドが働くことを確かめる。このイシュー自身の retro で新しい振り分けを使うことは、test-gate の後の retro で行うので、ここでは確かめない（close の報告に振り分け先を含める）。

| No | 手順 | 期待結果 | 実施環境 | 実施者 | 実結果 | 備考 |
|---:|------|----------|----------|--------|--------|------|
| 1 | `bash scripts/claude/code-review.sh --route backlog I207` と `bash scripts/claude/code-review.sh --route issue I207` を流す | 標準エラーに `記録: docs/reviews/closed/I207_code_review_20261027_1942.md`。一覧側に F1〜F8 の 8 行（I207 の台帳は前の形なので、どれも `FILE=-`。F2 は要約に `KIND=app` があっても `KIND=harness REPRO=no` のとおり一覧側で、理由は `再現なし`）。後続イシュー側は何も出ない。どちらも exit 0 | このセッション | Claude | OK（2026-10-27）: どちらも exit 0。標準エラーに `記録: docs/reviews/closed/I207_code_review_20261027_1942.md`。一覧側は F1〜F8 の 8 行（どれも `FILE=-`。F2 は `SEV=Medium REPRO=no KIND=harness`・理由 `再現なし`）。後続イシュー側は行なし | AC1・AC4。I207 の取り違え（F2）が起きないこと |
| 2 | `bash scripts/claude/check-permission-prompt.sh bash 'bash scripts/claude/code-review.sh --route backlog I207'` | exit 0（承認画面なし） | claude -p の判定 | Claude | OK（2026-10-27）: exit 0「承認なしで実行された」 | AC4。retro のコマンドが承認なしで通る（承認なしで通ると実際に実行されるが、読むだけのコマンドなので困らない） |
| 3 | 実装の後の一覧で、plan-issue の新しいコマンドを実装対象 `scripts/claude/code-review.sh` 1 つとして流す: `grep -rnF -e "FILE=scripts/claude/code-review.sh \|" -e "FILE=- \|" docs/reviews/backlog/` | 出力は `docs/reviews/backlog/I206.md` の F4 と `docs/reviews/backlog/I207.md` の F6・F7 の 3 行。`docs/reviews/backlog/I207.md` に F1・F3・F4・F5・F8 の行が無い | このセッション | Claude | OK（2026-10-27）: 出力は `docs/reviews/backlog/I206.md:8:- F4 …`・`docs/reviews/backlog/I207.md:7:- F6 …`・`docs/reviews/backlog/I207.md:8:- F7 …` の 3 行。I207.md に F1・F3・F4・F5・F8 の行は無い | AC5・一覧の同梱（計画書 9）。前方一致をやめた形で当たる |

結論: OK（No.1〜3 OK・2026-10-27。Human の項目なし）
