# I220 手動テスト: イシューの起票は Claude が実行して事後に報告する決まり

共通の準備（M-03・M-04）: 本物のイシューを作らず、app-1 の作業ツリーも汚さないため、レビュー済みの HEAD で一時ワークツリーを作って流す。`git worktree add --detach <セッションのスクラッチパッド>/wt-i220 HEAD` → その中で `claude -p --permission-mode default --disallowedTools "Bash(gh issue:*)" "Bash(gh api:*)" --output-format stream-json --verbose "<入力>"` を流し、出力を一時ファイルに保存して読む → 終わったら `git worktree remove --force <その一時ワークツリー>` で片付ける（テストが作った未追跡のイシューファイル・レビューの記録ごと消える）。

| No | 手順 | 期待結果 | 実施者 | 実施環境 | 実結果 | 備考 |
|---:|------|----------|--------|----------|--------|------|
| M-01 | `bash -c '! grep -nE "/issue-bootstrap.*を入力してください" docs/runbooks/workflow.md .claude/skills/issue-bootstrap/SKILL.md'; echo "exit=$?"` 相当を、終了コードを明示して流す（Bash ツールは grep の exit 1 を表示しないため） | exit 0（該当行が 0 行。「`/issue-bootstrap [タイトル]` を入力してください」と案内する決まりが無い） | Claude | 手元のファイル | | 受け入れ条件 1 の後半 |
| M-02 | `workflow.md` の「スキル呼び出しルール」「Claude が会話の中で起票するとき」「各段階で止まったときの案内」と、`issue-bootstrap/SKILL.md` の description・「## 呼ばれ方」・手順 6 を読む | 次がすべて書かれている: Claude が Skill ツールで `issue-bootstrap` を呼ぶ／明らかに価値が低いものは起票せず、直すか同梱して報告する／確認なしで起票し、聞くのは価値が低いか迷うものと要件・基本設計・UI/UX の判断が要るものだけ／判断が要る点は GitHub に起票する前（手順 4 の前）に聞く／起票した後に `I###（#番号）・タイトル・なぜ起票したか` を報告する／何件も起票するときは 1 件ずつ／retro からの起票は今のまま。`CLAUDE.md:9`・`onboarding.md:21` が「起票は Claude が行う」形 | Claude | 手元のファイル | | 受け入れ条件 1・2 |
| M-03 | 共通の準備のとおり、入力「I220 の作業中です。ログイン画面で、パスワードを間違えたときのエラー文が英語のまま出る不具合を見つけました。表示する文言は『メールアドレスまたはパスワードが違います』にします。I220 の範囲外なので別イシューにします。」で流す | 出力の中に、Claude が Skill ツールで `issue-bootstrap` を呼んだ記録（`"name":"Skill"` と `issue-bootstrap`）がある。最後の返答に「`/issue-bootstrap` を入力してください」のようにユーザーにコマンドを打たせる案内が無い（GitHub への書き込みは `--disallowedTools` で止まるので、登録が止められた旨の報告になる見込み。止められた記録があっても合否には使わない） | Claude | claude -p の判定 | | 受け入れ条件 3。新しいセッションが毎回読む CLAUDE.md とスキルの description だけで自分で呼ぶかを見る |
| M-04 | 共通の準備のとおり、入力「I220 の作業中です。ダッシュボードに学習時間のグラフを足す改善を思いつきました。I220 の範囲外なので別イシューにします。」で流す（グラフの種類・置き場所・期間は決めていない） | 出力の中に、Skill ツールで `issue-bootstrap` を呼んだ記録（`"name":"Skill"` と `issue-bootstrap`）があり、`gh issue create` を流そうとした記録が無く、最後の返答に、グラフの種類・置き場所・期間など、決めてもらうことの質問がある（GitHub に起票する前に止まって聞いている） | Claude | claude -p の判定 | | 設計確認メモの「起票の前に止めて聞く」 |
| M-05 | 片付けの後、`git worktree list` と GitHub の最新のイシュー（`gh issue list --limit 3`）を見る | 一時ワークツリーが無い。M-03・M-04 で新しいイシューができていない | Claude | 手元のファイル | | 本物のイシューを作らない手当て（計画 R2）の確かめ |

結論: OK / NG
