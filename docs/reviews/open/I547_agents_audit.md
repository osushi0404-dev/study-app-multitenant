# I547 点検の結果の表: レビュー役 5 つ（`.claude/agents/`）

計画書 `docs/plans/open/plan_I547.md` の変更点の正。ファイルごと・節ごとに「そのまま／直す／消す／足す」と根拠を書く。実装で確定した結果は「結果」列に足す。

## §0 基準

### §0.1 照らした出典（照合日 2026-11-27）
| 記号 | 出典 | 使った要点 |
|---|---|---|
| S1 | Claude Code「Create custom subagents」 https://code.claude.com/docs/en/sub-agents | 前置きの必須は `name`・`description` だけ。知らない項目は警告なしで無視される。`tools` で道具を絞る（読み取り専用の例は `Read, Glob, Grep`）。`model` は `sonnet`・`opus`・`haiku`・`fable`・完全な ID・`inherit`。description は「いつ任せるか」を短く、詳しいことは本文に。本文がそのままシステムプロンプトになり、Claude Code 本体のシステムプロンプトは渡らない。`--agents` の JSON は `prompt` が本文 |
| S2 | Anthropic「Prompting best practices」 https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices | 明確で直接的に書く・理由を添えると一般化できる・「しないこと」より「すること」を書く・強い強調（CRITICAL・MUST）は今のモデルでは過剰に反応させるので普通の言い方にする・一貫した XML タグ・役割は 1 文で足りる・出力の形は具体的に |
| S3 | 公式の記事「サブエージェントをメインのループに組み込むタイミング」 https://claude.com/ja/resources/articles/building-agents-when-to-fold-subagents-into-your-main-agent-loop （2026-10-22） | 失敗の型: 継ぎはぎの指示（各所から足した文が矛盾する）・役の重なり・乱立。確かめ役のサブエージェントは残してよい用途 |
| S4 | 公式ブログ https://claude.dev/blog/how-the-claude-code-team-thinks-about-verification/ | 決まり・手順は放っておくと増えるので定期的に刈る |
| S5 | Anthropic「Harness design for long-running application development」 https://www.anthropic.com/engineering/harness-design-long-running-apps （2026-03-24） | モデルが変わったら部品を 1 つずつ外して要るかを確かめる。評価役はモデル単独では確実にこなせない仕事にだけ価値がある |
| 内部 | このリポジトリの記録（`ファイル:行` で示す） | |

### §0.2 正の置き場所の決め方
- **決まり**（何をしてよい・いけない・条件）は手順書・規約に置く。レビュー役は「何を見て、どう判定するか」を持つ
- **レビューの判定の基準**は、レビュー役の定義の中に 1〜2 行で自己完結させ、出どころ（手順書の節名）を添える。詳しい説明・例は写さない。理由: 審査はブランチが分かれた時点の写しの版で動き（I593）、写しに入るのはレビュー役の定義と `docs/runbooks/review-rules.md` だけ（`scripts/claude/reviewer-agents-lib.sh:28`〜`:62`）。判定の基準を `plan-writing-rules.md` などへの参照だけにすると、ブランチで書き換えた手順書がそのブランチ自身の審査の基準になる（#640 の 1）
- **2 つのレビュー役が同じ一覧を持つもの**（高リスク判定の条件）は `docs/runbooks/review-rules.md` に 1 つだけ置き、両方から参照する。`review-rules.md` は写しに入り、参照のパスは写しのパスに置き換わる（`reviewer-agents-lib.sh:55`〜`:56`）
- スキルの点検の表（`review-rules.md`「スキルファイル変更時の Claude Code ベストプラクティス準拠」）は写しに入るので、計画レビュー役は写さずに参照する

### §0.3 変えない約束（流れを止めないため）
- **前置きは `name`・`description`・`tools`・`model` の 4 つだけ**。審査の入口は前置きをこの 4 つしか受け付けず、ほかの項目があると変換に失敗して審査が止まる（`reviewer-agents-lib.sh:47`〜`:48`。`effort`・`maxTurns`・`disallowedTools` などは S1 にあるが足さない。足すかは #640 にコメントで渡す）
- **出力の形はスクリプトが読む**ので変えない: 計画レビューの `VERDICT:` 行と「判定: Yes / No」（`scripts/claude/plan-issue-review.sh`）・コードレビューの `FINDING:` 行と `VERDICT:` 行（`scripts/claude/code-review.sh`）・敵対的レビューの `ITEM:`・`NEW_CRITICAL:`・`NEW_HIGH:`・`EXPERIMENT_BEGIN/END`（`scripts/claude/adversarial-review.sh`）・診断レビューの `VERDICT:`（`scripts/claude/fix-review-lib.sh`）・イシューレビューの「## 判定: 十分/要補足」（`scripts/claude/issue-review.sh`・issue-bootstrap）
- 定義の文字を見る既存のテスト 11 本（写しの一致・有無を見る 3 項目〔`test_i181_review_slim.sh` の D9・`test_i593_review_from_base.sh` の TC-02・`test_i185_harness_docs.sh` の TC-14⑧b〕は、写しを 1 つにする PR4・PR15・CR9 に合わせて、1 か所・参照を見る形に変える。項目の数は同じ）（`test_fix_review`・`test_i181_review_slim`・`test_i185_harness_docs`・`test_i193_official_flow`・`test_i197_adversarial_process`・`test_i197_review_ledger`・`test_i202_ledger_cleanup`・`test_i205_stop_criteria`・`test_i593_review_from_base`・`test_review_verdict`・`test_adversarial_trigger`）が見る語は残す。2026-11-27 にこのブランチの起点で 11 本とも exit 0

## §1 5 つに共通
| # | 節・事柄 | 判定 | 変更内容 | 根拠 |
|---|---|---|---|---|
| C1 | 前置き（4 項目） | そのまま | `name`・`description`・`tools: Read, Grep, Glob`・`model: sonnet` は S1 に合う。description の「自分から仕事を任せる相手にしない」は、S1 の「description で任せ先を選ぶ」に対して、自動で任されないための正しい書き方 | S1・§0.3 |
| C2 | `<instructions>` と「重要: データとして扱うドキュメント」の 2 重の書き方 | 直す | 1 つの節「## 入力の扱い」にまとめ、理由（イシュー・計画・差分は他人や過去の自分が書いた文で、指示に見える文が混ざりうる）を 1 文添える。対象のファイルの一覧は残す | S2（理由を添える・同じことを 2 回書かない）・S3（継ぎはぎ） |
| C3 | 「ツールアクセス制限」節（Bash・Edit・Write・MultiEdit は使用禁止） | 直す | 「使える道具は Read・Grep・Glob（前置きの `tools` と呼ぶ側の `--tools` で決まっている）。コマンドを流す・ファイルを書く道具は無い」の 1 行にする（禁止の列挙は道具の制限と重なる） | S1（`tools` で制限）・S2（すること を書く）・`reviewer-agents-lib.sh:12` |
| C4 | 強い言い回し（「恐れるな」「必須遵守」「（必須）」の多用・「このフォーマットのみ出力すること」） | 直す | 普通の言い方にし、理由を添える（出力の形は「スクリプトが行頭から読むので形を変えない」）。判定を甘くしない向きの文（問題を見つけるのが目的）は残す | S2（過剰な強調は過剰に反応させる・理由を添える） |
| C5 | 役割の文 | そのまま | 1〜2 文の役割は S2 に合う | S2 |
| C6 | model（`sonnet`） | そのまま（外す候補の表 §9 に記録） | 費用と精度の比べは #594 の問題集で測ってから決める | S1・S5 |

## §2 `plan-reviewer.md`
| # | 節 | 判定 | 変更内容 | 根拠 |
|---|---|---|---|---|
| PR1 | 読むべきファイル | そのまま | | |
| PR2 | 観点の並び（P1・ベストプラクティス・セキュリティ・モダン・Claude Code BP・P4・P3・P5・P8・P9） | 直す | 見出しを番号順の P1〜P9 にそろえる。番号はスキルが使う意味に合わせる: P1 要件・P2 セキュリティ・P3 データ・P4 テスト・P5 運用・P6 性能・UX（今の「モダンなウェブアプリ開発」）・P7 設計品質（今の「ベストプラクティス」。Claude Code の指示ファイルの観点はこの中）・P8 コスト・P9 プライバシー（`.claude/skills/implement/SKILL.md:47`・`:53`・`:58`・`.claude/skills/plan-issue/SKILL.md:160`、P9 の「P2 との境界」が P2＝セキュリティを前提にしている） | S2（一貫した構造）・内部 |
| PR3 | P7 の規約照合（「重要原則に反する設計」・`:65`） | 直す（同梱 B） | 「`rules/` の 2 本の規約の節（§5 組織の境界・§6 API・§10 セキュリティなど）に照らす。§16（今のコードとの差）の表の行に当たる決まりは、その行のイシュー以外では NG にしない。それ以外の決まりは、計画が新しく書くコードに当てはめる」 | 内部（#547 の I545 の retro・`docs/reviews/backlog/I545.md` F7） |
| PR4 | P7 の Claude Code BP（スキル点検の 7 項目の写し・`:100`〜`:108`） | 直す（同梱 C） | 7 項目の写しを消し、「`docs/runbooks/review-rules.md`「スキルファイル変更時の Claude Code ベストプラクティス準拠」の表に照らす」の参照 1 行にする（写しの項目 2・4 は古い）。分岐パリティ・概念変更の消費箇所・設計メモ↔本文整合の 3 項目は判定の基準なので残す | §0.2・内部（#547 の I546 の引き継ぎ 3） |
| PR5 | P7 の外部挙動依存の (a)(b)(c)（`:75`） | 直す | 「プレーン default の新規セッション」→「通常モード（Manual）の新しいセッション」（I546 で手順書の言い方を変えた・`docs/runbooks/plan-writing-rules.md:52`） | 内部 |
| PR6 | P7 の規約・命名の是正の網羅性・コマンド衛生・破壊的取り消し | そのまま | 判定の基準として 1 行ずつ。手順書（`plan-writing-rules.md`「規約是正時の消費箇所の全件列挙」）と内容が合っている | §0.2 |
| PR7 | P1 に「受け入れのリスクの根拠」 | 足す（同梱 E） | 「計画の Risk の処遇が受け入れの行のうち、ユーザーのデータを失うもの・ほかの環境（ほかのワークツリー・ほかの人の環境）に及ぶものは、設計確認メモ（grill-me の回答）に根拠があるか。無ければ Blocker（計画レビューの前にユーザーに確かめる・`docs/runbooks/workflow.md`「止めて聞く条件」1）」。Blocker にするのは、レビューを通ると実装まで止まる場所が無いため | 内部（I587 の retro・`docs/reviews/closed/I587_review.md`） |
| PR8 | P2 セキュリティの DEFAULT_PERMISSION_CLASSES の行 | 直す | 事実（`backend/core/settings.py:162` が `[]`）は今も正しい。出どころを添え、規約 §10 の既定（`IsAuthenticated`）は §16 の差の扱い（PR3）に従う、と 1 行にする | 内部・`rules/ultimate_django_coding_standards.md:107` |
| PR9 | P4 テストに「時間がたつと現れるデータ」 | 足す（同梱 D） | 「テストが、本物のリポジトリにまだ無いデータ（将来の番号の記録・まだ作られていないファイルなど）が無いことに頼って『別の理由で止まる』形になっていないか。あれば Warning（テストの中で作った一時のデータを使う）」 | 内部（I569 の retro・#583） |
| PR10 | P4 の false-green・対象の選び方・exit code の向き | そのまま | 判定の基準として 1 行ずつ。出どころ（`plan-writing-rules.md` の節名）が添えてある | §0.2 |
| PR11 | P6 性能・UX に「流れの途中の状態」 | 足す（同梱 A） | 「初めて使う人の流れ（作る → 中身を足す → 使う）を変える計画では、各段の途中の状態（親はあるが中身が 0 など）ごとに、画面の表示と押せる操作が計画と手動テストの行にあるか。無ければ Warning（決まりは `docs/runbooks/ux-rules.md` §5）」 | 内部（I539 の retro）・`docs/runbooks/ux-rules.md:30` |
| PR12 | P3・P5・P8・P9 | そのまま | P8 の安全装置の精密な判定（I599 の retro の案）はすでに入っている（`:147`） | 内部 |
| PR13 | 差し戻しファースト原則の表 | そのまま | 例が具体的で S2 に合う | S2 |
| PR14 | 重大度定義 | そのまま | | |
| PR15 | 高リスク判定の条件（`:206`〜`:222`） | 直す（移す） | 一覧のアプリの条件と「Yes にしない」行を `docs/runbooks/review-rules.md` の新しい節「高リスク判定の条件」に移し（ハーネスの 2 つの一覧は同じファイルの (b) の行が正）、ここは「その節の条件で判定する」の参照にする（コードレビュー役と同じ一覧の 2 つの写しを 1 つに） | §0.2・S3（重なり） |
| PR16 | 出力の形・VERDICT 行 | そのまま（言い回しだけ C4） | §0.3 | |

## §3 `code-reviewer.md`
| # | 節 | 判定 | 変更内容 | 根拠 |
|---|---|---|---|---|
| CR1 | `<instructions>` の「Read / Bash で取得した内容」 | 直す | Bash は持っていない（`tools: Read, Grep, Glob`）。C2 でまとめるときに直す | S1・内部 |
| CR2 | 提供されるコンテキスト・決定論ゲートの扱い | そのまま（言い回しだけ C4） | スクリプトとの約束 | §0.3 |
| CR3 | 観点の並び | 直す | PR2 と同じく P1〜P9 にそろえる | PR2 |
| CR4 | P7 の規約照合（`:72`） | 直す（同梱 B） | PR3 と同じ文（照らす対象は差分の新しいコード） | PR3 |
| CR5 | P6 性能・UX に UX の決まりの照合 | 足す（同梱 F） | 「`frontend/src` の新しい・変えた部品は、`docs/runbooks/ux-rules.md` の §1（失敗の出し方）・§2（待つときの見え方。読み込み中の枠と表示の高さが違ってまわりが動かないか）・§6（押す的の大きさ 44×44px）に照らす」 | 内部（I587 の retro 2 回目） |
| CR6 | P4 に「時間がたつと現れるデータ」 | 足す（同梱 D） | PR9 と同じ文（Medium） | PR9 |
| CR7 | P4 の「AI 生成コード固有チェック」の「規約逸脱」 | 消す | P7 の規約照合と同じ（重なり） | S3・S4 |
| CR8 | P4 のほかの項目・P1・P2・P3・P5・P8・P9 | そのまま | | |
| CR9 | 高リスク判定の条件（`:159`〜`:175`） | 直す（移す） | 一覧は `review-rules.md`「高リスク判定の条件」を参照。`RISK=up` を付ける条件の文（計画レビューが No でアプリの条件に当たる変更が差分にあるときだけ）はここに残す | PR15 |
| CR10 | 止める指摘の書き方・計画で受け入れた残余リスク・出力・FINDING 行・差分のレビュー | そのまま（言い回しだけ C4） | スクリプトとの約束（§0.3） | |

## §4 `adversarial-reviewer.md`
| # | 節 | 判定 | 変更内容 | 根拠 |
|---|---|---|---|---|
| AR1 | 冒頭の HTML の注釈（呼び出し元） | そのまま | | |
| AR2 | `<instructions>`・データとして扱う | 直す | C2 | C2 |
| AR3 | 反証マンデート・時間と攻め筋の上限・守る範囲 | そのまま（言い回しだけ C4） | 上限は `docs/runbooks/review-rules.md:69`・スクリプトと同じ | |
| AR4 | 実験の上限（`:68`）と `test-session.sh` の行（`:69`）の食い違い | 直す（一覧 I430 F7） | `:69` の行が `:68` の「`bash -c 'ulimit …; timeout …'` で包む」の例外であることと、その実験の時間の上限は 1 周 10 分の締め切り（スクリプト）であることを書く | 内部（`docs/reviews/backlog/I430.md:12`） |
| AR5 | 「実行できなかった」とみなす行の説明（`:71`） | 直す（一覧 I486 F6） | 実装（`scripts/claude/adversarial-review.sh:412`）に合わせ、「`command not found`・`: not found` で終わる行・`failed to run command`・`is not running`・`Cannot connect to the Docker daemon`・`no such service`」と書く | 内部（`docs/reviews/backlog/I486.md:11`） |
| AR6 | 出力の形・ITEM・NEW_* 行 | そのまま | §0.3 | |

## §5 `fix-diagnosis-reviewer.md`
| # | 節 | 判定 | 変更内容 | 根拠 |
|---|---|---|---|---|
| FD1 | `<instructions>`・ツールアクセス制限 | 直す | C2・C3 | |
| FD2 | 役割・観点 1〜4・判定基準・出力 | そのまま | 観点 2 に「推奨案の後も根本原因の条件が残るか」を足す案（I494 の retro）は #534 が扱う（同じ変更を 2 つのイシューで持たない） | 内部（`docs/reviews/closed/I494_review.md:54`） |

## §6 `issue-reviewer.md`
| # | 節 | 判定 | 変更内容 | 根拠 |
|---|---|---|---|---|
| IR1 | description の「issue-bootstrap の step 3.5」 | 直す | 今のスキルでは「手順 3」（`.claude/skills/issue-bootstrap/SKILL.md` の「### 3. 自己完結度レビュー」） | 内部 |
| IR2 | `<instructions>`・データとして扱う・ツール | 直す | C2・C3 | |
| IR3 | 役割・レビュー対象・観点 1〜5・出力 | そのまま | | |

## §7 同梱 A〜H の処遇
| # | 処遇 | 行き先 |
|---|---|---|
| A | 足す | PR11 |
| B | 足す | PR3・CR4 |
| C | 直す | PR4（スキル点検は参照に）・PR6/PR10（判定の基準は自己完結のまま 1 行・§0.2 の理由） |
| D | 足す | PR9・CR6 |
| E | 足す | PR7 と `docs/runbooks/plan-writing-rules.md` の 8) に 1 文 |
| F | 足す | CR5 と `rules/ultimate_django_coding_standards.md` §6 に 1 文 |
| G | 観点に入れた | §1 の C2・C4、§2 の PR15、§3 の CR7・CR9（重なりと継ぎはぎを刈った） |
| H | 候補を挙げた | §9 と `docs/runbooks/harness-audit.md` に 1 行 |

## §8 漏れの点検（レビューをすり抜けた実例から）
`docs/reviews/closed/*_review.md` の振り返りで、レビュー役の観点を足す案になった行（2026-11-27 に `grep -n "plan-reviewer.md\|code-reviewer.md\|adversarial-reviewer.md\|issue-reviewer.md\|fix-diagnosis-reviewer.md"` から「足す・追加・観点」を含む行を拾った 23 行）を、今の定義に入っているかで分けた。実装の段階で `bug` ラベルの閉じたイシュー 30 件（2026-11-27 に `gh issue list --state closed --label bug --limit 100`）の題を見て、下の表の最後の 3 行を足した。
| 元 | 案 | 今の定義 | 処遇 |
|---|---|---|---|
| I539 | 流れの途中の状態 | 無い | 足す（A） |
| I545 | §16 の扱い | 無い | 足す（B） |
| I569 | 時間がたつと現れるデータ | 無い | 足す（D） |
| I587（1 回目） | 受け入れのリスクの根拠 | 無い | 足す（E） |
| I587（2 回目） | UX の決まりの照合 | 無い | 足す（F） |
| I494 | 診断で根本原因が残るか | 無い | 足さない（#534 が扱う） |
| I487 | 自作する前に規約と依存を確かめる | 無い | 足さない（#509 が扱う） |
| I599 | 安全装置の精密な判定 | ある（plan-reviewer P8） | そのまま |
| I223 | 名義と鍵 | ある（P5） | そのまま |
| I430 | 新しいセッションの起こし方 | ある（adversarial `:69`） | 直す（AR4 の食い違いだけ） |
| I446・I463 | 必ず確かめる項目の実験必須と TC | ある（P4） | そのまま |
| I187 | 画面の動きの回帰テスト | ある（code-reviewer P4） | そのまま |
| I205・I197・I202・I512・I593 | 台帳・止める条件・RISK=up・受け入れ・テストを弱める差分 | ある | そのまま |
| I062・I067・I071・I081・I086・I122・I185 | VERDICT・分岐パリティ・P9・コマンド衛生・敵対的レビュー・exit code の向き | ある | そのまま |
| #473・#488（bug・実装の段階で足した） | 画面と API の受け渡しの形の食い違い（画面の数字が 0・空） | 計画レビュー役の P1 にだけある（「画面/API/DB で業務ルールの解釈が一致」） | 足す（コードレビュー役の P1・Medium） |
| #431・#459・#472・#437（bug） | テナント境界の漏れ・0 件の日の 0 で割る・画像の無い問題の 500・ログの個人情報 | ある（P2 テナント境界・P1 エッジケース・P9 ログへの露出） | そのまま |
| 残りの bug（見張り・CI 待ち・番号の桁・サンドボックスなどハーネスの穴） | ハーネスの仕組みの穴 | レビュー役の観点ではなく、各イシューで決定論のテストを足した | そのまま |

## §9 外す候補（#594 の問題集で 1 つずつ測ってから決める・S5）
| # | 部品 | 外せそうな理由 | 測り方の案 |
|---|---|---|---|
| X1 | code-reviewer の P2 セキュリティの一般の観点（OWASP の列挙） | review-gate はパスの判定が YES のとき組み込みの `/security-review` も流す。重なる | 問題集のセキュリティの問題で、外した版と外さない版の検出の数を比べる |
| X2 | code-reviewer の P4「AI 生成コード固有チェック」の残り（tautological・過剰抽象化・存在しない参照） | 組み込みの `/code-review` と `/simplify` が見る | 同上（テストの問題） |
| X3 | plan-reviewer の P3・P5・P9 をハーネスだけのイシューで読ませること | ハーネスのイシューが多く、毎回「対象外」と書くだけ | 問題集のハーネスの計画で、観点を外した版の Blocker の検出が落ちないか |
| X4 | issue-reviewer | 起票を止めないソフトな確かめ。指摘で本文が変わった割合が分からない | 起票の記録で「要補足」の後に本文を直した割合を数える |
| X5 | model（`sonnet`）の見直し | モデルが変わるたびに、より小さいモデルで足りるか・大きいモデルが要るかが変わる | 問題集で `haiku`・`sonnet`・`opus` を比べる |
| X6 | 前置きの `effort`・`maxTurns` | 入口が 4 項目しか受け付けない（§0.3） | #640 で入口が受け付けるようにした後、問題集で比べる |

## 結果（実装で確定したものを足す）
- §1〜§6 の「直す・消す・足す」の行は全部そのとおりに直した（2026-11-27 implement）。PR15・CR9 は、review-rules の新しい節にアプリの条件と「Yes にしない」行を置き、ハーネスの 2 つの一覧はどちらも既存の (b) の行を正にして参照する形にした（計画変更記録）
- 写しの一致・有無を見るテストの項目 4 つを、1 か所・参照を見る形に変えた: `test_i181_review_slim.sh` の D6・D9・`test_i593_review_from_base.sh` の TC-02・`test_i185_harness_docs.sh` の TC-14⑧b（`test_i593` は FG-TC-02b を足して 4 → 5、ほかは項目の数は同じ）
- §8 に bug のイシューから 1 種類（画面と API の受け渡し・#473・#488）を足し、コードレビュー役の P1 に 1 行足した
- 前置きは 5 つとも 4 項目のまま。5 つとも審査の入口と同じ変換を通り、`claude -p` で固有の出力の形を答えた（手動 No.4）
- コメント: #594（§9 の X1〜X6）https://github.com/osushi0404-dev/study-app-multitenant/issues/594#issuecomment-7206621750 ・#640（§0.2 の結果と前置きの項目）https://github.com/osushi0404-dev/study-app-multitenant/issues/640#issuecomment-7206622097
- 一覧から消した行: `docs/reviews/backlog/I430.md` F7・`I486.md` F6・`I546.md` F3
