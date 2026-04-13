# I043 手動テスト: レビュースキルに停止条件・重大度区分・高リスク判定を追加する

## テスト方針
スキルファイルはドキュメントのため、自動テストは行わない。
各スキルファイルの内容を読み取り、受け入れ条件との一致を確認する。

---

## テストケース

| No | 確認内容 | 操作手順 | 期待結果 | 実施者 | 実結果 | 備考 |
|---:|---------|---------|---------|--------|--------|------|
| 1 | plan-issue-review に重大度テーブルの出力指示があること | `.claude/skills/plan-issue-review/SKILL.md` を読む | Blocker/High/Medium/Low の4段階と列定義（重大度・観点・指摘内容・該当箇所・対応）が記載されている | Claude | | |
| 2 | plan-issue-review に Blocker 停止条件があること | `.claude/skills/plan-issue-review/SKILL.md` を読む | 「Blocker がある場合は STOP し `/implement` を案内しない」旨の記述がある | Claude | | |
| 3 | plan-issue-review に高リスク判定セクションがあること | `.claude/skills/plan-issue-review/SKILL.md` を読む | 高リスク条件10項目と「Yes/No・該当条件・推奨アクション」の出力形式が定義されている | Claude | | |
| 4 | code-review の受け入れ条件テーブルに重大度列があること | `.claude/skills/code-review/SKILL.md` を読む | テーブルの列定義に「重大度」が含まれている | Claude | | |
| 5 | code-review に Blocker 停止条件があること | `.claude/skills/code-review/SKILL.md` を読む | 「Blocker がある場合は STOP し `/test` を案内しない」旨の記述がある | Claude | | |
| 6 | test に停止条件が明文化されていること | `.claude/skills/test/SKILL.md` を読む | 「自動テスト失敗時・手動テスト NG 時は `/retro` や `/close` を案内しない」旨が明示されている | Claude | | |
| 7 | grill-me の質問観点に2項目が追加されていること | `.claude/skills/grill-me/SKILL.md` を読む | 「実装する価値があるか」「既存方針との衝突がないか」が観点リストに含まれている | Claude | | |
| 8 | 全スキルファイルが500行以内であること | 各 SKILL.md の行数を確認 | plan-issue-review・code-review・test・grill-me 全て500行以内 | Claude | | |
| 9 | 重大度定義（Blocker/High/Medium/Low）の説明が適切か | `.claude/skills/plan-issue-review/SKILL.md` を読む | 各重大度の定義（次工程ブロック・修正推奨・チケット化推奨・改善提案）が明確に記載されている | Human | | |
| 10 | 高リスク条件10項目の内容が意図通りか | `.claude/skills/plan-issue-review/SKILL.md` を読む | 提案資料（docs/proposals/review_design_proposal.md）のセクション4と一致している | Human | | |
