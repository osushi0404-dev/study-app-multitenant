<!--
## 手動テスト品質基準
- 期待結果は「正常に〜できる」ではなく具体的な画面表示・動作で記載すること
- 実施者: docs/runbooks/plan-writing-rules.md「実施者の区別」で決める（原則 Claude。Human の行は備考に「試した手段: …」が必須。scripts/claude/check-manual-test-executor.sh が確かめる）
-->

# I591 手動テスト: ハーネスにグラフエンジニアリングから取り入れられるところを調べて採否を決める

対象の記録: `docs/proposals/I591_harness_graph_review.md`

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| M1 | 記録の「公式の言葉との対応」の節を Read で読む | 要点ごとに、対応する Claude Code の公式の機能・言葉と、出典の URL・確認日（2026-11-20 以降の日付）が書いてある。公式で確かめられなかった要点には「未確認」と書いてある（AC1） | Claude |  |  |
| M2 | 記録の「資料ごとの要点」の節を Read で読み、イシューの関連資料の一覧と突き合わせる | 10 件（ユーザーが本文を貼った X の 5 件〔m4lkxx・0xTrackmind・sermakarevich・hanakoxbt・addyosmani〕・X のリンク先 3 件〔Zenn・Code Mode の公式ドキュメント・OpenClaw の記事〕・公式の記事 2 件〔検証のブログ・サブエージェントの記事〕）のそれぞれに節があり、要点と採否の検討が書いてある。x.com/beamnxw は「対象外」とだけ書いてある。X の投稿の本文をそのまま写した段落（原文の英文が 5 文以上続く所）が無い（AC2・R4） | Claude |  |  |
| M3 | 記録の図を Read で読む | Mermaid のコードブロックが 1 つ以上あり、段階（plan・plan-review・design-security-review・implement・review-gate・fix-loop・test-gate・retro・close）・レビュー役（plan-reviewer・code-reviewer・adversarial-reviewer・fix-diagnosis-reviewer・issue-reviewer）・人の承認（手動テスト・マージ）・fix-loop から review-gate への戻り道・同時に流している所（組み込みのレビューと CI 待ち・敵対的レビューの 3 観点）が入っている（AC3） | Claude |  |  |
| M4 | 記録の比較表と採否の節を Read で読む | 表の各行に「満たしている／差がある／取り入れない」のどれか 1 つと根拠（`ファイル:行` か I###）がある。差がある行には経緯（その仕組みを入れたイシュー）と採否・理由がある。設計確認メモで決まった 4 点（A・終了報告・回数の上限・B）は、その答えのとおりに書いてある（AC4・AC5） | Claude |  |  |
| M5 | 記録の中の `ファイル:行`・ファイルの参照を全部抜き出し、`test -f` と `sed -n '<行>p'` で 1 件ずつ確かめる | 全件のファイルが実在し、行の参照は書いてある内容がその行（または前後 3 行）にある。切れた参照は 0 件（AC4・`docs/runbooks/plan-writing-rules.md`「参照先実在性の全件機械検証」） | Claude |  |  |
| M6 | 記録の「起票・同梱したイシュー」の節の番号ごとに `gh issue view <番号> --json number,state,labels,title` を流す | 起票したイシューが 3 件以上あり、どれも OPEN で `track:harness` のラベルが付いている。A・終了報告・B のイシューがそれぞれある。A の本文に「I547 より先」、B の本文に「毎回のレビューで流す」が書いてある（AC6） | Claude |  |  |
| M7 | 同梱先として記録に書いたイシュー（I547・#523 など）に `gh issue view <番号> --comments` を流す | 記録に書いた同梱の中身のコメントが、2026-11-20 以降の日付で付いている。A を先にすることが I547 のコメントに書いてある（AC6） | Claude |  |  |

## 画面確認
<!-- frontend/src を変えたイシューでは 1 行以上必要。このイシューは文書と起票だけなので対象外 -->
| 日時 | コミット | 画面と操作 | アカウント | 期待した結果 | 実際の結果 | 画像 |
|---|---|---|---|---|---|---|
| - | - | 理由: frontend/src を変えない（文書と起票だけ） | - | - | - | - |

結論: OK / NG
