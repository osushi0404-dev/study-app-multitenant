<!--
## 手動テスト品質基準
- 期待結果は「正常に〜できる」ではなく具体的な画面表示・動作で記載すること
- 実施者: docs/runbooks/plan-writing-rules.md「実施者の区別」で決める（原則 Claude。Human の行は備考に「試した手段: …」が必須。scripts/claude/check-manual-test-executor.sh が確かめる）
-->

# I591 手動テスト: ハーネスにグラフエンジニアリングから取り入れられるところを調べて採否を決める

対象の記録: `docs/proposals/I591_harness_graph_review.md`

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| M1 | 記録の「公式の言葉との対応」の節を Read で読む | 外部の解説 5 件（Turing Post・AI総研・AI Heartland・aibuilderclub・frankx）と渡された資料 10 件の要点ごとに、対応する Claude Code の公式の機能・言葉と、出典の URL・確認日（2026-11-20 以降の日付）が書いてある。公式で確かめられなかった要点には「未確認」と書いてある（AC1） | Claude | NG（2026-11-20・HEAD 4e30b16d 以降）: 3 節は言葉ごとの対応 8 行で、資料の要点ごと（例: 資料 4 の no look merge・資料 6 の CI・資料 9 の確かめが見ていないこと）の公式の対応も「公式の機能なし／未確認」の表示も無い |  |
| M2 | 記録の「資料ごとの要点」の節を Read で読み、イシューの関連資料の一覧と突き合わせる | 10 件（ユーザーが本文を貼った X の 5 件〔m4lkxx・0xTrackmind・sermakarevich・hanakoxbt・addyosmani〕・X のリンク先 3 件〔Zenn・Code Mode の公式ドキュメント・OpenClaw の記事〕・公式の記事 2 件〔検証のブログ・サブエージェントの記事〕）のそれぞれに節があり、要点と採否の検討が書いてある。x.com/beamnxw は「対象外」とだけ書いてある。X の投稿の原文をそのまま写した連続段落が無い（要約と短い引用だけ）（AC2・R4） | Claude | OK: 2 節に 10 件の節があり各要点と、5 節・6 節に採否がある。x.com/beamnxw は冒頭で対象外。原文を写した連続段落は無い |  |
| M3 | 記録の図を Read で読む | Mermaid のコードブロックが 1 つ以上あり、段階（plan・plan-review・design-security-review・implement・review-gate・fix-loop・test-gate・retro・close）・レビュー役（plan-reviewer・code-reviewer・adversarial-reviewer・fix-diagnosis-reviewer・issue-reviewer）・人の承認（手動テスト・マージ）・fix-loop から review-gate への戻り道・同時に流している所（組み込みのレビューと CI 待ち・敵対的レビューの 3 観点）が入っている（AC3） | Claude | NG: Mermaid の図はあり、段階・plan-reviewer・code-reviewer・fix-diagnosis-reviewer・issue-reviewer・人の手動テストとマージ・fix-loop→review-gate・同時に流す所は入っている。adversarial-reviewer の名前が無い（「敵対的レビュー adversarial-review.sh」の観点 1〜3 だけ） |  |
| M4 | 記録の比較表と採否の節を Read で読む | 表の各行に「満たしている／差がある／取り入れない」のどれか 1 つと根拠（`ファイル:行` か I###）がある。差がある行には経緯（その仕組みを入れたイシュー）と採否・理由がある。設計確認メモで決まった 4 点（A・終了報告・回数の上限・B）は、その答えのとおりに書いてある（AC4・AC5） | Claude | OK: 25 行すべてに判定と根拠、△の行に経緯、6 節に採否と理由。設計確認メモの 4 点（4・17・10・5）は答えのとおり |  |
| M5 | 記録の中の `ファイル:行`・ファイルの参照を全部抜き出し、`test -f` と `sed -n '<行>p'` で 1 件ずつ確かめる | 全件のファイルが実在し、行の参照は書いてある内容がその行（または前後 3 行）にある。切れた参照は 0 件（AC4・`docs/runbooks/plan-writing-rules.md`「参照先実在性の全件機械検証」） | Claude | OK: 記録の `ファイル:行` とファイルの参照を全件抜き出し、ファイルの実在と行の中身を確かめた。切れた参照 0 件（行の範囲のずれ 1 件は implement で直し済み・F1/F2 の訂正後の参照も確かめた） |  |
| M6 | 記録の「起票・同梱したイシュー」の節の番号ごとに `gh issue view <番号> --json number,state,labels,title` を流す | 起票したイシューが 3 件以上あり、どれも OPEN で `track:harness` のラベルが付いている。A・終了報告・B のイシューがそれぞれある。A の本文に「I547 より先」、B の本文に「毎回のレビューで流す」が書いてある（AC6） | Claude | OK: #593・#594・#595 はすべて OPEN・`track:harness`。#593 の本文に「I547 より先」、#594 の本文に「毎回のレビューで流す」がある |  |
| M7 | 同梱先として記録に書いたイシュー（I547・#523 など）に `gh issue view <番号> --comments` を流す | 記録に書いた同梱の中身のコメントが、2026-11-20 以降の日付で付いている。A を先にすることが I547 のコメントに書いてある（AC6） | Claude | OK: #547 と #523 に 2026-11-20 の I591 からの同梱コメントがあり、#547 には I593 を先に着手することが書いてある |  |

## 画面確認
<!-- frontend/src を変えたイシューでは 1 行以上必要。このイシューは文書と起票だけなので対象外 -->
| 日時 | コミット | 画面と操作 | アカウント | 期待した結果 | 実際の結果 | 画像 |
|---|---|---|---|---|---|---|
| - | - | 理由: frontend/src を変えない（文書と起票だけ） | - | - | - | - |

結論: NG（M1・M3）
