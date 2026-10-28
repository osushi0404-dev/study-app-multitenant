# I209 手動テスト: ハーネスの古いイシューを棚卸しし、今の流れで不要なものを閉じる

一覧: `docs/reviews/open/I209_triage.md`（close の後は closed）。すべて test-gate で Claude が `gh` を使って確かめる（GitHub の状態は CI から見られない）

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | 一覧で「閉じる」「統合」の 41 件について、1 件ずつ `gh issue view <番号> --json state,stateReason,comments` を流す | 41 件すべて `state` が `CLOSED`。`stateReason` は、基準 ② を含む閉じる件が `COMPLETED`、① ④ だけの閉じる件が `NOT_PLANNED`、統合 4 件が `DUPLICATE`。どの件にも本文が「I209（#349）の棚卸しで閉じます。」で始まるコメントがあり、その中の「判定:」と「理由:」が一覧の行と同じ | Claude |  | AC2・AC3・AC5（#319・#325 を含む） |
| 2 | 一覧で「残す」の 11 件について、1 件ずつ `gh issue view <番号> --json state --jq .state`、`cat docs/reviews/open/I209_original_bodies/<番号>.header.md docs/reviews/open/I209_original_bodies/<番号>.md > docs/reviews/open/I209_original_bodies/<番号>.expect.md`、`gh issue view <番号> --json body --template "{{.body}}" > docs/reviews/open/I209_original_bodies/<番号>.now.md`、`cmp docs/reviews/open/I209_original_bodies/<番号>.expect.md docs/reviews/open/I209_original_bodies/<番号>.now.md` を流す（終わったら `.expect.md`・`.now.md` を消す） | 11 件すべて `OPEN`。`cmp` が exit 0（今の本文＝読み替えの節＋`---`＋追記の前の本文と 1 字も違わない）。`.header.md` の 1 行目が `## 今の流れでの読み替え（I209・2026-10-28）` で、一覧の「読み替え」と「まだ残っている作業」の中身がある | Claude |  | AC3 |
| 3 | 統合先の #180・#250・#268・#335 の本文の読み替えの節を読む | #180 に #189・#289・#294・#230、#250 に #279、#268 に #226、#335 に #172 の番号と中身が書かれている。統合元 4 件（#172・#189・#226・#279）の閉じるコメントに統合先の番号がある | Claude |  | AC4 |
| 4 | `docs/reviews/open/I209_review.md` の「ユーザー確認」の行の commit の時刻（`git log -1 --format=%cI -S 'ユーザー確認: 閉じる・統合する一覧' -- docs/reviews/open/I209_review.md`）と、No.1 の 41 件の I209 のコメントの `createdAt` のうち最も早いものを比べる | ユーザー確認の commit の時刻が、最も早い閉じるコメントより前 | Claude |  | AC2 |
| 5 | `gh issue list --state open --label track:harness --limit 200 --json number` で開いている番号を取る | 開いているのは #349 と残す 11 件だけ（このテストの時点で新しく起票されたものがあれば、それは一覧の対象外として備考に番号を書く） | Claude |  | AC1 |
