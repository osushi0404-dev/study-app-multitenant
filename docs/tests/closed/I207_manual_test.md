# I207 手動テスト: 台帳の残りを捨てるときに目印・重大度が消える穴を直し、軽い指摘は後続イシューにせず一覧へ回す

一覧ファイルと、計画で一覧を見るコマンドが実際に働くことを確かめる（このイシュー自身の retro で新しい振り分けを使ったことは、test-gate の後の retro で行うので、ここでは確かめない。close の報告に振り分け先を含める）。承認画面の有無は確かめる対象に含まない（スクリプトの起動のしかた・許可・見張りは変えない）。

| No | 手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|------|----------|--------|--------|------|
| 1 | `docs/reviews/backlog/I206.md` を読む。続けて plan-issue の新しい節のコマンドを、実装対象を `scripts/claude/adversarial-review.sh` 1 つとして流す: `grep -rnF -e "FILE=scripts/claude/adversarial-review.sh" docs/reviews/backlog/` | 一覧に F3〜F6 の 4 行があり、各行に `SEV=`・`REPRO=`・`KIND=`・`FILE=`・要約・`受け入れ:` の理由がある。見出しに記録のパスと見る場所がある。コマンドの出力は F3・F6 の 2 行（`docs/reviews/backlog/I206.md:<行>:- F3 …` と `- F6 …`） | Claude | OK（2026-10-27）: 一覧に F3〜F6 の 4 行があり、各行に SEV・REPRO・KIND・FILE・要約・`受け入れ:` の理由がある。見出しに記録のパス・一覧に回した決まり・見る場所がある。コマンドの出力は `docs/reviews/backlog/I206.md:7:- F3 …` と `docs/reviews/backlog/I206.md:10:- F6 …` の 2 行 | AC4。計画で一覧を見る決まりが実際に行を拾えるか |

結論: OK（No.1 OK・2026-10-27。Human の項目なし）
